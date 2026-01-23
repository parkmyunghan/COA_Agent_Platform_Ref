"""
데이터 품질 검증 자동화 스크립트
Phase 3.3: 데이터 품질 검증 로직
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.relevance_mapper import RelevanceMapper
from core_pipeline.resource_priority_parser import ResourcePriorityParser
from core_pipeline.situation_id_mapper import SituationIDMapper


class DataQualityValidator:
    """데이터 품질 검증 클래스"""
    
    def __init__(self, data_lake_path: str = "data_lake"):
        self.data_lake = Path(data_lake_path)
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_all(self) -> Dict:
        """모든 데이터 테이블 검증"""
        print("=" * 80)
        print("데이터 품질 검증 시작")
        print("=" * 80)
        
        results = {
            '위협상황': self.validate_threat_situations(),
            '관련성_테이블': self.validate_relevance_table(),
            '가용_자원': self.validate_available_resources(),
            'COA_Library': self.validate_coa_library()
        }
        
        # 요약
        total_errors = sum(r['error_count'] for r in results.values())
        total_warnings = sum(r['warning_count'] for r in results.values())
        
        print("\n" + "=" * 80)
        print("검증 완료")
        print("=" * 80)
        print(f"총 에러: {total_errors}")
        print(f"총 경고: {total_warnings}")
        
        if total_errors == 0:
            print("✅ 모든 데이터 품질 검증 통과!")
        else:
            print(f"❌ {total_errors}개 에러 발견. 수정 필요.")
        
        return results
    
    def validate_threat_situations(self) -> Dict:
        """위협상황.xlsx 검증"""
        print("\n[1] 위협상황.xlsx 검증")
        errors = []
        warnings = []
        
        file_path = self.data_lake / "위협상황.xlsx"
        if not file_path.exists():
            errors.append("파일이 존재하지 않음")
            return {'error_count': len(errors), 'warning_count': 0, 'errors': errors}
        
        df = pd.read_excel(file_path)
        
        # 필수 컬럼 확인 (통합된 위협유형코드 확인)
        required_columns = ['위협유형코드']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼 '{col}' 누락")
        
        # 위협유형코드 데이터 확인
        if '위협유형코드' in df.columns:
            null_count = df['위협유형코드'].isnull().sum()
            if null_count > 0:
                warnings.append(f"{null_count}개 행의 위협유형코드가 비어있음")
            
            # 표준 유형 확인
            valid_types = ['침투', '포격', '기습공격', '사이버', '전면공격', '국지도발', '공중위협']
            invalid = df[~df['위협유형코드'].isin(valid_types + [None])]
            if len(invalid) > 0:
                warnings.append(f"{len(invalid)}개 행이 비표준 위협유형코드 사용")
        
        # Situation ID 형식 확인
        if 'situation_id' in df.columns:
            for idx, sit_id in enumerate(df['situation_id']):
                if pd.notna(sit_id):
                    if not SituationIDMapper.is_valid_situation_id(str(sit_id)):
                        warnings.append(f"행 {idx+1}: 비표준 situation_id '{sit_id}'")
        
        print(f"  에러: {len(errors)}, 경고: {len(warnings)}")
        return {'error_count': len(errors), 'warning_count': len(warnings), 'errors': errors, 'warnings': warnings}
    
    def validate_relevance_table(self) -> Dict:
        """방책유형_위협유형_관련성.xlsx 검증"""
        print("\n[2] 방책유형_위협유형_관련성.xlsx 검증")
        errors = []
        warnings = []
        
        file_path = self.data_lake / "방책유형_위협유형_관련성.xlsx"
        if not file_path.exists():
            errors.append("파일이 존재하지 않음")
            return {'error_count': len(errors), 'warning_count': 0, 'errors': errors}
        
        df = pd.read_excel(file_path)
        
        # 필수 컬럼
        required_columns = ['coa_type', 'threat_type', 'base_relevance']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼 '{col}' 누락")
        
        if 'base_relevance' in df.columns:
            # 점수 범위 확인 (0.0 ~ 1.0)
            invalid_scores = df[(df['base_relevance'] < 0) | (df['base_relevance'] > 1)]
            if len(invalid_scores) > 0:
                errors.append(f"{len(invalid_scores)}개 행의 관련성 점수가 범위 외 (0.0~1.0)")
            
            # 극단값 확인
            very_low = df[df['base_relevance'] < 0.2]
            if len(very_low) > 0:
                warnings.append(f"{len(very_low)}개 행의 관련성이 매우 낮음 (<0.2)")
        
        # 매핑 완전성 확인 (7 COA types × 6 threat types = 42)
        expected_count = 42
        if len(df) < expected_count:
            warnings.append(f"매핑 개수 부족: {len(df)}/{expected_count}")
        
        print(f"  에러: {len(errors)}, 경고: {len(warnings)}")
        return {'error_count': len(errors), 'warning_count': len(warnings), 'errors': errors, 'warnings': warnings}
    
    def validate_available_resources(self) -> Dict:
        """가용자원.xlsx 검증"""
        print("\n[3] 가용자원.xlsx 검증")
        errors = []
        warnings = []
        
        file_path = self.data_lake / "가용자원.xlsx"
        if not file_path.exists():
            errors.append("파일이 존재하지 않음")
            return {'error_count': len(errors), 'warning_count': 0, 'errors': errors}
        
        df = pd.read_excel(file_path)
        
        # 필수 컬럼
        required_columns = ['situation_id', 'resource_name', 'available_quantity', 'status']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼 '{col}' 누락")
        
        # 시나리오별 자원 개수 확인
        if 'situation_id' in df.columns:
            scenario_counts = df['situation_id'].value_counts()
            print(f"  시나리오별 자원:")
            for scenario, count in scenario_counts.items():
                print(f"    - {scenario}: {count}개")
                if count < 5:
                    warnings.append(f"{scenario}: 자원 개수 부족 ({count}개, 최소 5개 권장)")
        
        # 수량 확인
        if 'available_quantity' in df.columns:
            negative = df[df['available_quantity'] < 0]
            if len(negative) > 0:
                errors.append(f"{len(negative)}개 행의 수량이 음수")
        
        # 상태 확인
        if 'status' in df.columns:
            valid_statuses = ['사용가능', '정비중', '제한적', '미보유']
            invalid = df[~df['status'].isin(valid_statuses)]
            if len(invalid) > 0:
                warnings.append(f"{len(invalid)}개 행이 비표준 상태값 사용")
        
        print(f"  에러: {len(errors)}, 경고: {len(warnings)}")
        return {'error_count': len(errors), 'warning_count': len(warnings), 'errors': errors, 'warnings': warnings}
    
    def validate_coa_library(self) -> Dict:
        """COA_Library.xlsx 검증"""
        print("\n[4] COA_Library.xlsx 검증")
        errors = []
        warnings = []
        
        file_path = self.data_lake / "COA_Library.xlsx"
        if not file_path.exists():
            errors.append("파일이 존재하지 않음")
            return {'error_count': len(errors), 'warning_count': 0, 'errors': errors}
        
        df = pd.read_excel(file_path)
        
        # 신규 컬럼 존재 확인
        new_columns = ['적합위협유형', '자원우선순위', '전장환경_최적조건', '연계방책', '적대응전술']
        for col in new_columns:
            if col not in df.columns:
                errors.append(f"신규 컬럼 '{col}' 누락")
        
        # 자원우선순위 형식 검증
        if '자원우선순위' in df.columns:
            parser = ResourcePriorityParser()
            invalid_count = 0
            for idx, val in enumerate(df['자원우선순위']):
                if pd.notna(val) and str(val).strip() != '':
                    try:
                        parsed = parser.parse_resource_priority(str(val))
                        if len(parsed) == 0:
                            invalid_count += 1
                    except Exception as e:
                        invalid_count += 1
            
            if invalid_count > 0:
                warnings.append(f"{invalid_count}개 행의 자원우선순위 파싱 실패")
            
            # 데이터 입력 비율
            filled_count = df['자원우선순위'].notna().sum()
            fill_rate = filled_count / len(df) * 100
            print(f"  자원우선순위 입력률: {fill_rate:.1f}% ({filled_count}/{len(df)})")
            if fill_rate < 50:
                warnings.append(f"자원우선순위 입력률 낮음 ({fill_rate:.1f}%)")
        
        print(f"  에러: {len(errors)}, 경고: {len(warnings)}")
        return {'error_count': len(errors), 'warning_count': len(warnings), 'errors': errors, 'warnings': warnings}


def main():
    """메인 실행"""
    validator = DataQualityValidator()
    results = validator.validate_all()
    
    # 상세 에러/경고 출력
    print("\n" + "=" * 80)
    print("상세 내역")
    print("=" * 80)
    
    for table_name, result in results.items():
        if result['error_count'] > 0 or result['warning_count'] > 0:
            print(f"\n[{table_name}]")
            
            if 'errors' in result and result['errors']:
                print("  에러:")
                for err in result['errors']:
                    print(f"    ❌ {err}")
            
            if 'warnings' in result and result['warnings']:
                print("  경고:")
                for warn in result['warnings']:
                    print(f"    ⚠️ {warn}")
    
    return results


if __name__ == "__main__":
    main()
