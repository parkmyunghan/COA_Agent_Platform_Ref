# ui/components/data_quality_checker.py
# -*- coding: utf-8 -*-
"""
데이터 품질 검증 컴포넌트
입력 데이터의 품질을 검증하고 문제점을 식별
엑셀 파일의 두 번째 시트(테이블정의서)를 참조하여 동적으로 검증 기준 생성
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re


def render_data_quality_checker(data_manager, config: Optional[Dict] = None):
    """
    데이터 품질 검증 패널 렌더링
    
    Args:
        data_manager: DataManager 인스턴스
        config: 설정 딕셔너리
    """
    st.subheader("🔍 데이터 품질 검증")
    
    if st.button("🔄 데이터 품질 검사 실행", type="primary"):
        with st.spinner("데이터 품질 검사 중..."):
            quality_results = perform_quality_checks(data_manager, config)
            render_quality_results(quality_results)


def perform_quality_checks(data_manager, config: Optional[Dict] = None) -> Dict:
    """
    데이터 품질 검사 수행
    
    Args:
        data_manager: DataManager 인스턴스
        config: 설정 딕셔너리
        
    Returns:
        검사 결과 딕셔너리
    """
    results = {
        "overall_status": "pass",
        "checks": [],
        "summary": {
            "total_tables": 0,
            "passed_tables": 0,
            "failed_tables": 0,
            "total_issues": 0
        }
    }
    
    try:
        # 모든 테이블 로드
        all_data = data_manager.load_all()
        results["summary"]["total_tables"] = len(all_data)
        
        # 각 테이블별 검사
        for table_name, df in all_data.items():
            if df is None or df.empty:
                results["checks"].append({
                    "table": table_name,
                    "status": "error",
                    "message": "테이블이 비어있거나 로드할 수 없습니다.",
                    "issues": []
                })
                results["summary"]["failed_tables"] += 1
                continue
            
            table_results = check_table_quality(table_name, df, config, data_manager)
            results["checks"].append(table_results)
            
            if table_results["status"] == "pass":
                results["summary"]["passed_tables"] += 1
            else:
                results["summary"]["failed_tables"] += 1
                results["summary"]["total_issues"] += len(table_results.get("issues", []))
        
        # 전체 상태 결정
        if results["summary"]["failed_tables"] > 0:
            results["overall_status"] = "warning"
        if results["summary"]["total_issues"] > 10:
            results["overall_status"] = "error"
            
    except Exception as e:
        results["overall_status"] = "error"
        results["error"] = str(e)
    
    return results


def load_table_schema(table_name: str, config: Optional[Dict] = None) -> Optional[Dict]:
    """
    엑셀 파일의 두 번째 시트(테이블정의서)를 읽어서 스키마 정보 추출
    
    Args:
        table_name: 테이블명
        config: 설정 딕셔너리
        
    Returns:
        스키마 정보 딕셔너리 또는 None
    """
    try:
        # data_lake 경로 찾기
        data_lake_path = "./data_lake"
        if config:
            data_lake_path = config.get("data_lake_path", data_lake_path)
        
        base_dir = Path(__file__).parent.parent.parent
        excel_file = base_dir / data_lake_path / f"{table_name}.xlsx"
        
        if not excel_file.exists():
            return None
        
        # 엑셀 파일의 시트 목록 확인
        excel_file_obj = pd.ExcelFile(excel_file)
        sheet_names = excel_file_obj.sheet_names
        
        # 테이블정의서 시트 찾기
        schema_sheet = None
        for sheet in sheet_names:
            if "정의서" in sheet or "schema" in sheet.lower() or "정의" in sheet:
                schema_sheet = sheet
                break
        
        if not schema_sheet:
            return None
        
        # 테이블정의서 읽기
        schema_df = pd.read_excel(excel_file, sheet_name=schema_sheet)
        
        # 컬럼명 정규화 (새로운 구조: 필드명, 타입, PK, FK, 데이터목록, 관계)
        field_col = None
        type_col = None
        pk_col = None
        fk_col = None
        data_list_col = None
        relation_col = None
        
        for col in schema_df.columns:
            col_lower = str(col).lower()
            col_str = str(col)
            if "필드" in col_str or "field" in col_lower or "컬럼" in col_str:
                field_col = col
            elif "타입" in col_str or "type" in col_lower:
                type_col = col
            elif col_str == "PK" or col_lower == "pk":
                pk_col = col
            elif col_str == "FK" or col_lower == "fk":
                fk_col = col
            elif "데이터목록" in col_str or "데이터 목록" in col_str or "data" in col_lower and "list" in col_lower:
                data_list_col = col
            elif "관계" in col_str or "relation" in col_lower:
                relation_col = col
        
        if not field_col:
            return None
        
        # 스키마 정보 추출
        schema = {
            "primary_keys": [],
            "foreign_keys": [],
            "required_columns": [],
            "column_types": {},
            "value_ranges": {},
            "constraints": {},
            "enums": {}
        }
        
        for idx, row in schema_df.iterrows():
            field_name = str(row[field_col]).strip()
            if pd.isna(field_name) or field_name == "":
                continue
            
            # 1. PK 확인 (PK 컬럼에서 Y 값 확인)
            if pk_col and pk_col in row:
                pk_value = row[pk_col]
                if not pd.isna(pk_value) and str(pk_value).upper() in ['Y', 'YES', 'TRUE', '1', '예', 'O']:
                    schema["primary_keys"].append(field_name)
                    schema["required_columns"].append(field_name)
            
            # 2. FK 확인 (FK 컬럼에서 Y 값 확인, 관계 컬럼에서 관계 정보 추출)
            if fk_col and fk_col in row:
                fk_value = row[fk_col]
                if not pd.isna(fk_value) and str(fk_value).upper() in ['Y', 'YES', 'TRUE', '1', '예', 'O']:
                    # 관계 컬럼에서 FK 관계 정보 추출
                    if relation_col and relation_col in row:
                        relation = str(row[relation_col]) if not pd.isna(row[relation_col]) else ""
                        if relation and relation.strip():
                            # 형식: 테이블명:컬럼명 또는 테이블명.컬럼명
                            # 예: 전장축선:축선ID, 지형셀:지형셀ID
                            fk_match = re.search(r'([^:.,]+)[:.,]\s*([^\s,]+)', relation)
                            if fk_match:
                                target_table = fk_match.group(1).strip()
                                target_column = fk_match.group(2).strip()
                                schema["foreign_keys"].append({
                                    "column": field_name,
                                    "target_table": target_table,
                                    "target_column": target_column
                                })
            
            # 3. 데이터 타입 추출
            if type_col and type_col in row:
                col_type = str(row[type_col]).strip().lower() if not pd.isna(row[type_col]) else ""
                if col_type:
                    schema["column_types"][field_name] = col_type
            
            # 4. 데이터목록 컬럼에서 값 범위 및 열거형 추출
            if data_list_col and data_list_col in row:
                data_list = str(row[data_list_col]) if not pd.isna(row[data_list_col]) else ""
                if data_list and data_list.strip():
                    # 값 범위 추출 (예: 0~100, 1-5)
                    range_match = re.search(r'(\d+)\s*[~-]\s*(\d+)', data_list)
                    if range_match:
                        min_val = int(range_match.group(1))
                        max_val = int(range_match.group(2))
                        schema["value_ranges"][field_name] = {"min": min_val, "max": max_val}
                    else:
                        # 열거형 값 추출 (예: 가용/손실/이동중, High/Medium/Low)
                        # 슬래시 또는 쉼표로 구분된 값들
                        enum_values = []
                        # 불필요한 단어 제거 (등, etc, 기타 등)
                        data_list_clean = re.sub(r'\s*(등|etc|기타|외|이상|이하).*$', '', data_list, flags=re.IGNORECASE)
                        data_list_clean = data_list_clean.strip()
                        
                        # 슬래시 구분
                        if '/' in data_list_clean:
                            enum_values = [v.strip() for v in data_list_clean.split('/') if v.strip()]
                        # 쉼표 구분
                        elif ',' in data_list_clean:
                            enum_values = [v.strip() for v in data_list_clean.split(',') if v.strip()]
                        
                        if enum_values:
                            schema["enums"][field_name] = enum_values
        
        return schema
        
    except Exception as e:
        print(f"[WARN] 테이블정의서 로드 실패 ({table_name}): {e}")
        return None


def check_table_quality(table_name: str, df: pd.DataFrame, config: Optional[Dict] = None, data_manager=None) -> Dict:
    """
    개별 테이블 품질 검사
    
    Args:
        table_name: 테이블 이름
        df: DataFrame
        
    Returns:
        검사 결과 딕셔너리
    """
    issues = []
    status = "pass"
    
    # 테이블정의서에서 스키마 정보 로드
    schema = load_table_schema(table_name, config)
    
    # 1. 필수 컬럼 존재 확인 (테이블정의서 우선)
    required_columns = []
    if schema and schema.get("required_columns"):
        required_columns = schema["required_columns"]
    else:
        # 폴백: 기존 로직 사용
        required_columns = get_required_columns(table_name, config=config)
    
    if required_columns:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append({
                "type": "missing_columns",
                "severity": "error",
                "message": f"필수 컬럼 누락: {', '.join(missing_columns)}"
            })
            status = "error"
    
    # 2. PK 컬럼 존재 및 고유성 확인 (테이블정의서 기반)
    if schema and schema.get("primary_keys"):
        pk_columns = [col for col in schema["primary_keys"] if col in df.columns]
        
        if pk_columns:
            for pk_col in pk_columns:
                # NULL 값 확인
                if df[pk_col].isna().any():
                    issues.append({
                        "type": "null_primary_key",
                        "severity": "error",
                        "message": f"PK 컬럼 '{pk_col}'에 NULL 값이 있습니다."
                    })
                    status = "error"
                
                # 중복 확인
                if df[pk_col].duplicated().any():
                    issues.append({
                        "type": "duplicate_primary_key",
                        "severity": "error",
                        "message": f"PK 컬럼 '{pk_col}'에 중복 값이 있습니다."
                    })
                    status = "error"
        else:
            # PK가 정의되어 있지만 컬럼이 없는 경우
            missing_pk = [col for col in schema["primary_keys"] if col not in df.columns]
            if missing_pk:
                issues.append({
                    "type": "missing_primary_key",
                    "severity": "error",
                    "message": f"PK 컬럼 누락: {', '.join(missing_pk)}"
                })
                status = "error"
    else:
        # 테이블정의서가 없거나 PK 정보가 없는 경우 기존 로직 사용
        id_columns = [col for col in df.columns if 'ID' in col.upper() or col.upper() == 'ID']
        
        if id_columns:
            id_col = id_columns[0]
            if df[id_col].isna().any():
                issues.append({
                    "type": "null_id",
                    "severity": "error",
                    "message": f"{id_col} 컬럼에 NULL 값이 있습니다."
                })
                status = "error"
            
            if df[id_col].duplicated().any():
                issues.append({
                    "type": "duplicate_id",
                    "severity": "error",
                    "message": f"{id_col} 컬럼에 중복 값이 있습니다."
                })
                status = "error"
        else:
            # ID 컬럼이 없는 경우 - 설정 테이블은 예외 처리
            id_optional_tables = ["평가기준_가중치"]
            if table_name not in id_optional_tables:
                issues.append({
                    "type": "no_id_column",
                    "severity": "warning",
                    "message": "ID 컬럼이 없습니다. 온톨로지 구축에 문제가 있을 수 있습니다."
                })
                if status == "pass":
                    status = "warning"
    
    # 3. 데이터 타입 확인 (테이블정의서 기반)
    type_issues = check_data_types(df, schema)
    if type_issues:
        issues.extend(type_issues)
        if any(issue["severity"] == "error" for issue in type_issues):
            status = "error"
        elif status == "pass":
            status = "warning"
    
    # 4. NULL 값 확인
    null_counts = df.isnull().sum()
    high_null_columns = null_counts[null_counts > len(df) * 0.5]
    if not high_null_columns.empty:
        issues.append({
            "type": "high_null_ratio",
            "severity": "warning",
            "message": f"50% 이상 NULL인 컬럼: {', '.join(high_null_columns.index.tolist())}"
        })
        if status == "pass":
            status = "warning"
    
    # 5. 중복 행 확인
    duplicate_rows = df.duplicated().sum()
    if duplicate_rows > 0:
        issues.append({
            "type": "duplicate_rows",
            "severity": "warning",
            "message": f"중복 행 {duplicate_rows}개 발견"
        })
        if status == "pass":
            status = "warning"
    
    # 6. 값 범위 검증 (테이블정의서 기반)
    range_issues = check_value_ranges(table_name, df, schema)
    if range_issues:
        issues.extend(range_issues)
        if any(issue["severity"] == "error" for issue in range_issues):
            status = "error"
        elif status == "pass":
            status = "warning"
    
    # 7. 열거형 값 검증 (테이블정의서 기반)
    enum_issues = check_enum_values(df, schema)
    if enum_issues:
        issues.extend(enum_issues)
        if any(issue["severity"] == "error" for issue in enum_issues):
            status = "error"
        elif status == "pass":
            status = "warning"
    
    # 8. FK 참조 무결성 검증 (테이블정의서 기반)
    fk_issues = check_foreign_key_integrity(table_name, df, schema, data_manager, config)
    if fk_issues:
        issues.extend(fk_issues)
        if any(issue["severity"] == "error" for issue in fk_issues):
            status = "error"
        elif status == "pass":
            status = "warning"
    
    return {
        "table": table_name,
        "status": status,
        "row_count": len(df),
        "column_count": len(df.columns),
        "issues": issues
    }


def get_required_columns(table_name: str, metadata_path: str = "./metadata", config: Optional[Dict] = None) -> List[str]:
    """
    테이블별 필수 컬럼 목록 반환 (엑셀의 "테이블정의서" 시트 우선 사용)
    
    Args:
        table_name: 테이블명
        metadata_path: 메타데이터 경로 (하위 호환성)
        config: 설정 딕셔너리 (data_paths 포함 가능)
    
    Returns:
        필수 컬럼 리스트 (없으면 빈 리스트)
    """
    # 1. 엑셀의 "테이블정의서" 시트에서 PK 필드 추출 (우선)
    try:
        schema = load_table_schema(table_name, config)
        if schema:
            # PK로 표시된 필드들을 필수 컬럼으로 반환
            required = []
            for field_info in schema.get('fields', []):
                field_name = field_info.get('name', '')
                description = field_info.get('description', '').upper()
                
                # PK 표시가 있거나 설명에 "필수"가 있으면 필수 컬럼
                if 'PK' in description or '필수' in description or 'NOT NULL' in description:
                    required.append(field_name)
            
            if required:
                return required
    except Exception as e:
        # 스키마 로드 실패 시 다음 방법 시도
        pass
    
    # 2. DataManager를 통해 로더 사용 시도
    try:
        if config:
            from core_pipeline.data_manager import DataManager
            data_manager = DataManager(config)
            loader = data_manager.get_loader(table_name)
            if loader:
                schema = loader.load_schema()
                pk_columns = loader.get_primary_keys()
                if pk_columns:
                    return pk_columns
    except Exception as e:
        # 로더 사용 실패 시 다음 방법 시도
        pass
    
    # 3. 메타데이터 파일에서 필수 컬럼 읽기 (하위 호환성)
    if config:
        metadata_path = config.get("metadata_path", metadata_path)
    
    metadata_file = Path(metadata_path) / "table_metadata.json"
    if metadata_file.exists():
        try:
            import json
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                table_meta = metadata.get("tables", {}).get(table_name, {})
                required = table_meta.get("required_columns", [])
                if required:
                    return required
        except Exception as e:
            # 메타데이터 파일 로드 실패 시 폴백
            pass
    
    # 4. 레거시 하드코딩 (하위 호환성, 점진적 제거 예정)
    # 표준 테이블명으로 매핑
    standard_table_mapping = {
        "위협상황": ["위협ID"],
        "아군부대현황": ["아군부대ID"],
        "적군부대현황": ["적군부대ID"],
        "임무정보": ["임무ID"],
        "전장축선": ["축선ID"],
        "지형셀": ["지형셀ID"],
        "제약조건": ["제약ID"],
    }
    
    # 표준 테이블명 매핑에서 찾기
    if table_name in standard_table_mapping:
        return standard_table_mapping[table_name]
    
    # 레거시 매핑 (하위 호환성)
    legacy_required_columns = {
        "위협상황": ["ID", "위협유형", "심각도", "발생장소"],
        "아군부대": ["부대명"],
        "적군부대": ["ID", "부대명", "부대유형"],
        "아군가용자산": ["자산ID", "자산명", "자산종류"],
        "기상상황": ["ID", "장소", "상태"],
        "보급상태": ["ID", "장소", "재고수준"]
    }
    
    # 레거시 매핑에서 찾기 (없으면 빈 리스트 반환 - 모든 컬럼 선택적)
    return legacy_required_columns.get(table_name, [])


def check_data_types(df: pd.DataFrame, schema: Optional[Dict] = None) -> List[Dict]:
    """데이터 타입 검증 (테이블정의서 기반)"""
    issues = []
    
    if schema and schema.get("column_types"):
        # 테이블정의서의 타입 정보로 검증
        for col_name, expected_type in schema["column_types"].items():
            if col_name not in df.columns:
                continue
            
            expected_type_lower = expected_type.lower()
            
            # 숫자 타입 검증
            if "int" in expected_type_lower or "number" in expected_type_lower:
                non_numeric = pd.to_numeric(df[col_name], errors='coerce').isna().sum()
                if non_numeric > 0:
                    issues.append({
                        "type": "invalid_data_type",
                        "severity": "error",
                        "message": f"{col_name} 컬럼은 {expected_type} 타입이어야 하지만 숫자가 아닌 값 {non_numeric}개 발견"
                    })
            
            # 날짜 타입 검증
            elif "date" in expected_type_lower or "datetime" in expected_type_lower:
                non_date = pd.to_datetime(df[col_name], errors='coerce').isna().sum()
                if non_date > 0:
                    issues.append({
                        "type": "invalid_data_type",
                        "severity": "warning",
                        "message": f"{col_name} 컬럼은 날짜 타입이어야 하지만 날짜가 아닌 값 {non_date}개 발견"
                    })
            
            # 문자열 타입 검증 (일반적으로 문제 없지만 확인)
            elif "string" in expected_type_lower or "text" in expected_type_lower:
                # 문자열 타입은 특별한 검증 불필요
                pass
    else:
        # 폴백: 기존 로직 사용
        numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_columns:
            non_numeric = pd.to_numeric(df[col], errors='coerce').isna().sum()
            if non_numeric > 0:
                issues.append({
                    "type": "invalid_data_type",
                    "severity": "warning",
                    "message": f"{col} 컬럼에 숫자가 아닌 값 {non_numeric}개 발견"
                })
    
    return issues


def check_value_ranges(table_name: str, df: pd.DataFrame, schema: Optional[Dict] = None) -> List[Dict]:
    """값 범위 검증 (테이블정의서 기반)"""
    issues = []
    
    if schema and schema.get("value_ranges"):
        # 테이블정의서의 범위 정보로 검증
        for col_name, range_info in schema["value_ranges"].items():
            if col_name not in df.columns:
                continue
            
            min_val = range_info.get("min")
            max_val = range_info.get("max")
            
            col_values = pd.to_numeric(df[col_name], errors='coerce')
            valid_values = col_values.notna()
            
            if valid_values.any():
                out_of_range = ((col_values < min_val) | (col_values > max_val)).sum()
                if out_of_range > 0:
                    issues.append({
                        "type": "out_of_range",
                        "severity": "error",
                        "message": f"{col_name} 컬럼에 {min_val}~{max_val} 범위를 벗어난 값 {out_of_range}개 발견"
                    })
    else:
        # 폴백: 기존 로직 사용
        if "심각도" in df.columns:
            severity = pd.to_numeric(df["심각도"], errors='coerce')
            if severity.notna().any():
                out_of_range = ((severity < 0) | (severity > 100)).sum()
                if out_of_range > 0:
                    issues.append({
                        "type": "out_of_range",
                        "severity": "error",
                        "message": f"심각도 컬럼에 0-100 범위를 벗어난 값 {out_of_range}개 발견"
                    })
        
        if "재고수준" in df.columns:
            stock_level = df["재고수준"].str.replace('%', '').astype(str)
            stock_level_numeric = pd.to_numeric(stock_level, errors='coerce')
            if stock_level_numeric.notna().any():
                out_of_range = ((stock_level_numeric < 0) | (stock_level_numeric > 100)).sum()
                if out_of_range > 0:
                    issues.append({
                        "type": "out_of_range",
                        "severity": "warning",
                        "message": f"재고수준 컬럼에 0-100 범위를 벗어난 값 {out_of_range}개 발견"
                    })
    
    return issues


def check_enum_values(df: pd.DataFrame, schema: Optional[Dict] = None) -> List[Dict]:
    """열거형 값 검증 (테이블정의서 기반)"""
    issues = []
    
    if schema and schema.get("enums"):
        for col_name, allowed_values in schema["enums"].items():
            if col_name not in df.columns:
                continue
            
            # NULL이 아닌 값들 중 허용되지 않은 값 찾기
            non_null_values = df[col_name].dropna()
            invalid_values = non_null_values[~non_null_values.isin(allowed_values)]
            
            if len(invalid_values) > 0:
                unique_invalid = invalid_values.unique()[:5]  # 최대 5개만 표시
                issues.append({
                    "type": "invalid_enum_value",
                    "severity": "error",
                    "message": f"{col_name} 컬럼에 허용되지 않은 값 발견: {', '.join(map(str, unique_invalid))} (허용 값: {', '.join(allowed_values)})"
                })
    
    return issues


def check_foreign_key_integrity(table_name: str, df: pd.DataFrame, schema: Optional[Dict], 
                                data_manager, config: Optional[Dict] = None) -> List[Dict]:
    """FK 참조 무결성 검증"""
    issues = []
    
    if not schema or not schema.get("foreign_keys"):
        return issues
    
    try:
        # 모든 테이블 로드 (FK 참조 확인용)
        all_tables = data_manager.load_all()
        
        for fk_info in schema["foreign_keys"]:
            fk_column = fk_info["column"]
            target_table = fk_info["target_table"]
            target_column = fk_info["target_column"]
            
            if fk_column not in df.columns:
                continue
            
            # FK 값 추출 (NULL 제외)
            fk_values = df[fk_column].dropna().unique()
            
            if len(fk_values) == 0:
                continue
            
            # 참조 대상 테이블 찾기
            target_df = None
            for t_name, t_df in all_tables.items():
                # 테이블명 매칭 (부분 일치 허용)
                if target_table in t_name or t_name in target_table:
                    if target_column in t_df.columns:
                        target_df = t_df
                        break
            
            if target_df is None:
                issues.append({
                    "type": "foreign_key_reference_not_found",
                    "severity": "warning",
                    "message": f"FK '{fk_column}'의 참조 대상 테이블 '{target_table}'을 찾을 수 없습니다."
                })
                continue
            
            # 참조 무결성 확인
            invalid_fk = fk_values[~pd.Series(fk_values).isin(target_df[target_column].values)]
            
            if len(invalid_fk) > 0:
                unique_invalid = invalid_fk[:5]  # 최대 5개만 표시
                issues.append({
                    "type": "foreign_key_integrity_violation",
                    "severity": "error",
                    "message": f"FK '{fk_column}'에 참조 대상 테이블 '{target_table}.{target_column}'에 존재하지 않는 값 {len(invalid_fk)}개 발견 (예: {', '.join(map(str, unique_invalid))})"
                })
    
    except Exception as e:
        issues.append({
            "type": "foreign_key_check_error",
            "severity": "warning",
            "message": f"FK 참조 무결성 검사 중 오류 발생: {str(e)[:100]}"
        })
    
    return issues


def render_quality_results(results: Dict):
    """품질 검사 결과 렌더링"""
    # 전체 상태 표시
    overall_status = results.get("overall_status", "unknown")
    
    if overall_status == "pass":
        st.success("✅ 모든 데이터 품질 검사를 통과했습니다!")
    elif overall_status == "warning":
        st.warning("⚠️ 일부 데이터에 경고가 있습니다. 확인이 필요합니다.")
    else:
        st.error("❌ 데이터 품질 검사에서 오류가 발견되었습니다. 수정이 필요합니다.")
    
    # 요약 정보
    summary = results.get("summary", {})
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("전체 테이블", summary.get("total_tables", 0))
    with col2:
        st.metric("통과", summary.get("passed_tables", 0), 
                 delta=f"{summary.get('passed_tables', 0)}/{summary.get('total_tables', 1)}")
    with col3:
        st.metric("실패", summary.get("failed_tables", 0))
    with col4:
        st.metric("발견된 문제", summary.get("total_issues", 0))
    
    st.divider()
    
    # 각 테이블별 상세 결과
    st.subheader("📊 테이블별 상세 결과")
    
    checks = results.get("checks", [])
    for check in checks:
        table_name = check.get("table", "Unknown")
        status = check.get("status", "unknown")
        issues = check.get("issues", [])
        
        # 상태에 따른 아이콘
        if status == "pass":
            status_icon = "✅"
            status_color = "success"
        elif status == "warning":
            status_icon = "⚠️"
            status_color = "warning"
        else:
            status_icon = "❌"
            status_color = "error"
        
        with st.expander(f"{status_icon} {table_name} ({check.get('row_count', 0)}행, {check.get('column_count', 0)}열)", 
                        expanded=(status != "pass")):
            if status == "pass":
                st.success("✅ 모든 검사를 통과했습니다.")
            else:
                # 문제점 표시
                for issue in issues:
                    severity = issue.get("severity", "info")
                    message = issue.get("message", "N/A")
                    
                    if severity == "error":
                        st.error(f"❌ {message}")
                    else:
                        st.warning(f"⚠️ {message}")
    
    # 개선 제안
    if summary.get("total_issues", 0) > 0:
        st.divider()
        st.subheader("💡 개선 제안")
        
        error_issues = [issue for check in checks for issue in check.get("issues", []) 
                       if issue.get("severity") == "error"]
        warning_issues = [issue for check in checks for issue in check.get("issues", []) 
                         if issue.get("severity") == "warning"]
        
        if error_issues:
            st.error("**즉시 수정 필요:**")
            for issue in error_issues[:5]:  # 상위 5개만
                st.write(f"- {issue.get('message', 'N/A')}")
        
        if warning_issues:
            st.warning("**개선 권장:**")
            for issue in warning_issues[:5]:  # 상위 5개만
                st.write(f"- {issue.get('message', 'N/A')}")


