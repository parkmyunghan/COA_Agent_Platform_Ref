# common/relation_mappings_validator.py
# -*- coding: utf-8 -*-
"""
관계 매핑 파일 검증 유틸리티
relation_mappings.json 파일의 유효성을 검증
"""
import json
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class RelationMappingsValidator:
    """관계 매핑 파일 검증 클래스"""
    
    def __init__(self, metadata_path: str = "./metadata", data_paths: Optional[Dict] = None):
        """
        Args:
            metadata_path: 메타데이터 경로
            data_paths: 데이터 파일 경로 딕셔너리 (테이블명 검증용)
        """
        self.metadata_path = metadata_path
        self.data_paths = data_paths or {}
        self.rel_mapping_path = os.path.join(metadata_path, "relation_mappings.json")
    
    def validate(self) -> Dict:
        """
        관계 매핑 파일 전체 검증
        
        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "info": List[str]
            }
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        # 1. 파일 존재 확인
        if not os.path.exists(self.rel_mapping_path):
            result["errors"].append(f"파일이 존재하지 않습니다: {self.rel_mapping_path}")
            result["valid"] = False
            return result
        
        # 2. JSON 문법 검증
        try:
            with open(self.rel_mapping_path, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)
        except json.JSONDecodeError as e:
            result["errors"].append(f"JSON 문법 오류: {str(e)}")
            result["valid"] = False
            return result
        except Exception as e:
            result["errors"].append(f"파일 읽기 오류: {str(e)}")
            result["valid"] = False
            return result
        
        # 3. 구조 검증
        structure_errors = self._validate_structure(mapping_data)
        result["errors"].extend(structure_errors)
        if structure_errors:
            result["valid"] = False
        
        # 4. 내용 검증
        content_errors, content_warnings, content_info = self._validate_content(mapping_data)
        result["errors"].extend(content_errors)
        result["warnings"].extend(content_warnings)
        result["info"].extend(content_info)
        if content_errors:
            result["valid"] = False
        
        return result
    
    def _validate_structure(self, data: Dict) -> List[str]:
        """구조 검증"""
        errors = []
        
        # 최상위 레벨이 딕셔너리인지 확인
        if not isinstance(data, dict):
            errors.append("최상위 레벨은 객체({})여야 합니다.")
            return errors
        
        # 각 테이블별 구조 검증
        for src_table, col_mappings in data.items():
            if not isinstance(col_mappings, dict):
                errors.append(f"'{src_table}': 값은 객체여야 합니다.")
                continue
            
            for col_name, mapping_value in col_mappings.items():
                # 추론 관계 검증
                if col_name.startswith("추론:"):
                    if not isinstance(mapping_value, dict):
                        errors.append(f"'{src_table}.{col_name}': 추론 관계는 객체여야 합니다.")
                    else:
                        # 필수 필드 확인
                        if "target" not in mapping_value:
                            errors.append(f"'{src_table}.{col_name}': 'target' 필드가 필요합니다.")
                        if "column" not in mapping_value:
                            errors.append(f"'{src_table}.{col_name}': 'column' 필드가 필요합니다.")
                        if "confidence" not in mapping_value:
                            errors.append(f"'{src_table}.{col_name}': 'confidence' 필드가 필요합니다.")
                # 단순 관계 검증
                else:
                    if not isinstance(mapping_value, str):
                        errors.append(f"'{src_table}.{col_name}': 단순 관계는 문자열이어야 합니다.")
        
        return errors
    
    def _validate_content(self, data: Dict) -> Tuple[List[str], List[str], List[str]]:
        """내용 검증"""
        errors = []
        warnings = []
        info = []
        
        # 테이블명 목록 가져오기
        available_tables = set(self.data_paths.keys()) if self.data_paths else set()
        
        for src_table, col_mappings in data.items():
            # 소스 테이블 존재 확인
            if available_tables and src_table not in available_tables:
                warnings.append(f"'{src_table}': data_lake에 해당 테이블 파일이 없을 수 있습니다.")
            
            for col_name, mapping_value in col_mappings.items():
                # 추론 관계 내용 검증
                if col_name.startswith("추론:"):
                    if isinstance(mapping_value, dict):
                        target = mapping_value.get("target")
                        column = mapping_value.get("column")
                        confidence = mapping_value.get("confidence")
                        
                        # 타겟 테이블 확인
                        if available_tables and target and target not in available_tables:
                            warnings.append(f"'{src_table}.{col_name}': 타겟 테이블 '{target}'가 data_lake에 없을 수 있습니다.")
                        
                        # 신뢰도 범위 확인
                        if confidence is not None:
                            if not isinstance(confidence, (int, float)):
                                errors.append(f"'{src_table}.{col_name}': 'confidence'는 숫자여야 합니다.")
                            elif confidence < 0 or confidence > 1:
                                warnings.append(f"'{src_table}.{col_name}': 'confidence'는 0.0 ~ 1.0 사이여야 합니다. (현재: {confidence})")
                        
                        # 컬럼명 확인 (실제 테이블 파일 확인 불가 시 경고만)
                        if column:
                            info.append(f"'{src_table}.{col_name}': 컬럼 '{column}'가 실제 테이블에 존재하는지 확인하세요.")
                
                # 단순 관계 내용 검증
                else:
                    if isinstance(mapping_value, str):
                        target = mapping_value
                        if available_tables and target not in available_tables:
                            warnings.append(f"'{src_table}.{col_name}': 타겟 테이블 '{target}'가 data_lake에 없을 수 있습니다.")
                        info.append(f"'{src_table}.{col_name}': 컬럼 '{col_name}'가 실제 테이블에 존재하는지 확인하세요.")
        
        return errors, warnings, info
    
    def validate_and_print(self) -> bool:
        """
        검증 후 결과 출력
        
        Returns:
            검증 통과 여부
        """
        result = self.validate()
        
        if result["valid"]:
            print("✅ 관계 매핑 파일 검증 통과")
        else:
            print("❌ 관계 매핑 파일 검증 실패")
        
        if result["errors"]:
            print("\n[오류]")
            for error in result["errors"]:
                print(f"  - {error}")
        
        if result["warnings"]:
            print("\n[경고]")
            for warning in result["warnings"]:
                print(f"  - {warning}")
        
        if result["info"]:
            print("\n[정보]")
            for info_msg in result["info"][:10]:  # 최대 10개만 표시
                print(f"  - {info_msg}")
            if len(result["info"]) > 10:
                print(f"  ... 외 {len(result['info']) - 10}개")
        
        return result["valid"]


def validate_relation_mappings(metadata_path: str = "./metadata", 
                               data_paths: Optional[Dict] = None) -> Dict:
    """
    관계 매핑 파일 검증 (간편 함수)
    
    Args:
        metadata_path: 메타데이터 경로
        data_paths: 데이터 파일 경로 딕셔너리
    
    Returns:
        검증 결과 딕셔너리
    """
    validator = RelationMappingsValidator(metadata_path, data_paths)
    return validator.validate()


if __name__ == "__main__":
    # 직접 실행 시 검증 수행
    import sys
    from pathlib import Path
    
    # 프로젝트 루트 경로 설정
    project_root = Path(__file__).parent.parent
    metadata_path = project_root / "metadata"
    
    # 설정 파일에서 data_paths 로드 시도
    data_paths = None
    try:
        import yaml
        config_path = project_root / "config" / "global.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                data_paths = config.get("data_paths", {})
    except Exception:
        pass
    
    validator = RelationMappingsValidator(str(metadata_path), data_paths)
    validator.validate_and_print()

