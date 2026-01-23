# core_pipeline/data_loaders/base_loader.py
# -*- coding: utf-8 -*-
"""
Base Data Loader
데이터 로더 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import pandas as pd
from pathlib import Path
import re


class BaseDataLoader(ABC):
    """데이터 로더 기본 클래스"""
    
    def __init__(self, data_path: str, config: Optional[Dict] = None):
        """
        Args:
            data_path: 엑셀 파일 경로
            config: 설정 딕셔너리
        """
        self.data_path = Path(data_path)
        self.config = config or {}
        self._schema = None
        self._data = None
        self._last_mtime = None  # 파일 수정 시간 추적
        
        # 상대 경로를 절대 경로로 변환
        if not self.data_path.is_absolute():
            base_dir = Path(__file__).parent.parent.parent
            self.data_path = base_dir / self.data_path
    
    def load(self) -> pd.DataFrame:
        """데이터 로드 (파일 변경 시 자동 재로드)"""
        if self.should_reload():
            self.invalidate_cache()
        
        if self._data is None:
            self._data = self._load_data()
            self._validate_data(self._data)
        return self._data.copy()
    
    def invalidate_cache(self):
        """캐시 무효화 (파일 변경 시 호출)"""
        self._data = None
        self._schema = None
        self._last_mtime = None
    
    def should_reload(self) -> bool:
        """파일이 변경되었는지 확인"""
        if not self.data_path.exists():
            return False
        
        current_mtime = self.data_path.stat().st_mtime
        if self._last_mtime is None:
            self._last_mtime = current_mtime
            return False  # 첫 로드는 변경이 아님
        
        if current_mtime > self._last_mtime:
            self._last_mtime = current_mtime
            return True
        
        return False
    
    def load_schema(self) -> Dict:
        """테이블정의서 로드"""
        if self._schema is None:
            self._schema = self._load_schema_from_excel()
        return self._schema.copy()
    
    def _load_data(self) -> pd.DataFrame:
        """엑셀 파일의 첫 번째 시트에서 데이터 로드"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        # [FIXED] 스키마 정보를 기반으로 dtype 매핑 생성 (1.0 등 데이터 오염 방지)
        dtype_map = {}
        try:
            schema = self.load_schema()
            if schema and 'fields' in schema:
                for field in schema['fields']:
                    # 문자열 타입인 경우 str로 강제 지정
                    if field.get('type') == 'string':
                        dtype_map[field['name']] = str
        except Exception as e:
            # 스키마 로드 실패 시 로그만 남기고 계속 진행
            print(f"[DEBUG] Schema-based dtype mapping failed (skipping): {e}")
        
        # 첫 번째 시트 로드
        try:
            # 먼저 dtype 매핑을 적용하여 로드 시도
            df = pd.read_excel(self.data_path, sheet_name=0, dtype=dtype_map)
            return df
        except Exception as e:
            # 특정 컬럼이 없거나 타입 충돌 시 fallback: 파일 컬럼과 교차 검증 후 재시도
            try:
                # 존재하는 컬럼만 필터링하여 재시도
                cols = pd.read_excel(self.data_path, sheet_name=0, nrows=0).columns
                safe_dtype_map = {k: v for k, v in dtype_map.items() if k in cols}
                return pd.read_excel(self.data_path, sheet_name=0, dtype=safe_dtype_map)
            except:
                # 최후의 수단: 기본 로딩
                return pd.read_excel(self.data_path, sheet_name=0)
    
    def _load_schema_from_excel(self) -> Dict:
        """엑셀 파일의 두 번째 시트(테이블정의서)에서 스키마 로드"""
        if not self.data_path.exists():
            return {}
        
        try:
            excel_file = pd.ExcelFile(self.data_path)
            sheet_names = excel_file.sheet_names
            
            # 테이블정의서 시트 찾기
            schema_sheet = None
            for sheet in sheet_names:
                if "정의서" in sheet or "schema" in sheet.lower() or "정의" in sheet:
                    schema_sheet = sheet
                    break
            
            if not schema_sheet:
                return {}
            
            schema_df = pd.read_excel(self.data_path, sheet_name=schema_sheet)
            return self._parse_schema(schema_df)
        except Exception as e:
            print(f"[WARN] Failed to load schema from {self.data_path}: {e}")
            return {}
    
    def _parse_schema(self, schema_df: pd.DataFrame) -> Dict:
        """스키마 DataFrame 파싱"""
        if schema_df.empty:
            return {}
        
        # 컬럼명 찾기 (유연한 매칭)
        field_col = None
        type_col = None
        desc_col = None
        pk_col = None  # PK 컬럼 추가
        fk_col = None
        relation_col = None
        
        valid_values_col = None  # 유효값목록 컬럼
        
        for col in schema_df.columns:
            col_lower = str(col).lower()
            col_str = str(col)
            if any(keyword in col_lower for keyword in ['필드', 'field', '컬럼', 'column']):
                field_col = col
            elif any(keyword in col_lower for keyword in ['타입', 'type', '데이터타입']):
                type_col = col
            elif any(keyword in col_lower for keyword in ['설명', 'description', 'desc']):
                desc_col = col
            elif col_lower == 'pk':  # PK 컬럼 찾기
                pk_col = col
            elif col_lower == 'fk':
                fk_col = col
            elif any(keyword in col_lower for keyword in ['관계', 'relation']):
                relation_col = col
            elif any(keyword in col_str for keyword in ['유효값목록', '유효값', 'valid', 'values', 'enum']):
                valid_values_col = col
        
        if not field_col:
            return {}
        
        # 스키마 정보 파싱
        schema = {
            'fields': [],
            'primary_keys': [],
            'foreign_keys': {},
            'field_types': {},
            'field_descriptions': {},
            'valid_values': {},  # 유효값목록 추가
            'value_ranges': {}   # 숫자 범위 추가
        }
        
        for _, row in schema_df.iterrows():
            field_name = str(row[field_col]).strip()
            if pd.isna(field_name) or not field_name:
                continue
            
            field_info = {
                'name': field_name,
                'type': str(row[type_col]).strip() if type_col and pd.notna(row.get(type_col)) else 'string',
                'description': str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col)) else '',
                'is_fk': False,
                'relation': None
            }
            
            # PK 확인 (PK 컬럼에서 Y 값 확인)
            if pk_col and pd.notna(row.get(pk_col)):
                pk_value = str(row[pk_col]).strip().upper()
                if pk_value in ['Y', 'YES', 'TRUE', '1', '예', 'O']:
                    schema['primary_keys'].append(field_name)
            # 하위 호환성: 설명 컬럼에서도 PK 확인 (PK 컬럼이 없을 경우)
            elif desc_col and pd.notna(row.get(desc_col)):
                desc = str(row[desc_col]).upper()
                if 'PK' in desc:
                    schema['primary_keys'].append(field_name)
            
            # FK 확인 (FK 컬럼에서 Y 값 확인)
            if fk_col and pd.notna(row.get(fk_col)):
                fk_value = str(row[fk_col]).strip().upper()
                if fk_value in ['Y', 'YES', 'TRUE', '1', '예', 'O']:
                    field_info['is_fk'] = True
                    
                    # 관계 정보 (관계 컬럼에서 "테이블명:필드명" 형식)
                    if relation_col and pd.notna(row.get(relation_col)):
                        relation_str = str(row[relation_col]).strip()
                        if relation_str:
                            field_info['relation'] = relation_str
                            schema['foreign_keys'][field_name] = relation_str
            
            # 유효값목록 파싱
            if valid_values_col and pd.notna(row.get(valid_values_col)):
                valid_values_str = str(row[valid_values_col]).strip()
                if valid_values_str:
                    # 숫자 범위 형식 확인 (예: "1~5", "1-5")
                    range_match = re.search(r'(\d+)\s*[~-]\s*(\d+)', valid_values_str)
                    if range_match:
                        min_val = int(range_match.group(1))
                        max_val = int(range_match.group(2))
                        schema['value_ranges'][field_name] = {'min': min_val, 'max': max_val}
                    else:
                        # 콤마로 구분된 값들 파싱
                        values = [v.strip() for v in valid_values_str.split(',') if v.strip()]
                        if values:
                            # 모든 값이 숫자인지 확인
                            all_numeric = True
                            numeric_values = []
                            for v in values:
                                try:
                                    numeric_values.append(float(v))
                                except ValueError:
                                    all_numeric = False
                                    break
                            
                            if all_numeric and len(numeric_values) > 1:
                                # 숫자 값들이 범위로 표현 가능하면 범위로 저장
                                schema['value_ranges'][field_name] = {
                                    'min': int(min(numeric_values)),
                                    'max': int(max(numeric_values))
                                }
                            else:
                                # 문자 값들 또는 단일 숫자 값
                                schema['valid_values'][field_name] = values
            
            schema['fields'].append(field_info)
            schema['field_types'][field_name] = field_info['type']
            schema['field_descriptions'][field_name] = field_info['description']
        
        return schema
    
    def get_foreign_keys(self) -> Dict[str, str]:
        """FK 관계 반환 {컬럼명: 참조테이블:참조컬럼}"""
        schema = self.load_schema()
        return schema.get('foreign_keys', {})
    
    def get_primary_keys(self) -> List[str]:
        """PK 컬럼 목록 반환"""
        schema = self.load_schema()
        return schema.get('primary_keys', [])
    
    def get_valid_values(self, column: str) -> Optional[List]:
        """컬럼의 유효값 목록 반환 (테이블정의서에서)"""
        schema = self.load_schema()
        return schema.get('valid_values', {}).get(column)
    
    def get_value_range(self, column: str) -> Optional[Dict]:
        """컬럼의 값 범위 반환 (테이블정의서에서)"""
        schema = self.load_schema()
        return schema.get('value_ranges', {}).get(column)
    
    def _get_required_columns(self) -> List[str]:
        """테이블정의서에서 필수 컬럼 추출 (공통 메서드)"""
        schema = self.load_schema()
        required = []
        # PK는 필수
        required.extend(schema.get('primary_keys', []))
        return required
    
    def _get_pk_column(self) -> Optional[str]:
        """테이블정의서에서 PK 컬럼 추출 (공통 메서드)"""
        schema = self.load_schema()
        pks = schema.get('primary_keys', [])
        return pks[0] if pks else None
    
    @abstractmethod
    def _validate_data(self, df: pd.DataFrame) -> None:
        """
        데이터 검증 (서브클래스에서 구현)
        
        Raises:
            ValueError: 검증 실패 시
        """
        pass
    
    def validate_primary_key(self, df: pd.DataFrame, pk_column: str) -> None:
        """PK 중복 검증"""
        if pk_column not in df.columns:
            raise ValueError(f"Primary key column '{pk_column}' not found")
        
        duplicates = df[df[pk_column].duplicated(keep=False)]
        if not duplicates.empty:
            raise ValueError(
                f"Duplicate primary key values found in '{pk_column}': "
                f"{duplicates[pk_column].unique().tolist()}"
            )
    
    def validate_required_columns(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """필수 컬럼 검증"""
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {sorted(missing_cols)}")
    
    def validate_enum_values(self, df: pd.DataFrame, column: str, valid_values: List[str]) -> None:
        """열거형 값 검증"""
        if column not in df.columns:
            return
        
        invalid = df[~df[column].isin(valid_values) & df[column].notna()]
        if not invalid.empty:
            invalid_values = invalid[column].unique().tolist()
            raise ValueError(
                f"Invalid values in '{column}': {invalid_values}. "
                f"Valid values: {valid_values}"
            )
    
    def validate_value_range(self, df: pd.DataFrame, column: str, min_val: float, max_val: float) -> None:
        """값 범위 검증"""
        if column not in df.columns:
            return
        
        out_of_range = df[((df[column] < min_val) | (df[column] > max_val)) & df[column].notna()]
        if not out_of_range.empty:
            raise ValueError(
                f"Values out of range in '{column}': "
                f"Expected [{min_val}, {max_val}], "
                f"found {out_of_range[column].min()} ~ {out_of_range[column].max()}"
            )


class GenericDataLoader(BaseDataLoader):
    """제네릭 데이터 로더 (완전 자동화 - 테이블정의서 기반)"""
    
    def __init__(self, data_path: str, config: Optional[Dict] = None):
        super().__init__(data_path, config)
        # 테이블정의서에서 자동으로 모든 검증 규칙 추출
    
    def _validate_data(self, df: pd.DataFrame) -> None:
        """테이블정의서 기반 완전 자동 검증"""
        schema = self.load_schema()
        
        # 필수 컬럼 확인 (테이블정의서에서 자동 추출)
        required_cols = self._get_required_columns()
        if required_cols:
            self.validate_required_columns(df, required_cols)
        
        # PK 중복 확인 (테이블정의서에서 자동 추출)
        pk_col = self._get_pk_column()
        if pk_col and pk_col in df.columns:
            self.validate_primary_key(df, pk_col)
        
        # 유효값 목록 검증
        for column, valid_values in schema.get('valid_values', {}).items():
            if column in df.columns:
                self.validate_enum_values(df, column, valid_values)
        
        # 값 범위 검증
        for column, range_info in schema.get('value_ranges', {}).items():
            if column in df.columns:
                self.validate_value_range(
                    df, column, 
                    range_info['min'], 
                    range_info['max']
                )

