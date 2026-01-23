# tests/test_importance_rename.py
# -*- coding: utf-8 -*-
"""
priority → importance 리네이밍 검증 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from core_pipeline.data_models import Constraint
from core_pipeline.constraint_validator import ConstraintValidator


def test_constraint_constants():
    """상수명 변경 테스트"""
    print("\n=== 1. 상수명 변경 테스트 ===")
    
    # 새 상수 (IMPORTANCE_*)
    assert hasattr(Constraint, 'IMPORTANCE_CRITICAL')
    assert hasattr(Constraint, 'IMPORTANCE_HIGH')
    assert hasattr(Constraint, 'IMPORTANCE_MEDIUM')
    assert hasattr(Constraint, 'IMPORTANCE_LOW')
    assert hasattr(Constraint, 'IMPORTANCE_OPTIONAL')
    
    assert Constraint.IMPORTANCE_CRITICAL == 5
    assert Constraint.IMPORTANCE_HIGH == 4
    assert Constraint.IMPORTANCE_MEDIUM == 3
    assert Constraint.IMPORTANCE_LOW == 2
    assert Constraint.IMPORTANCE_OPTIONAL == 1
    
    print("✅ IMPORTANCE_* 상수 정의 확인")
    
    # 하위 호환성 상수 (PRIORITY_*)
    assert hasattr(Constraint, 'PRIORITY_CRITICAL')
    assert Constraint.PRIORITY_CRITICAL == 5
    print("✅ PRIORITY_* 상수 하위 호환성 확인")


def test_constraint_field():
    """필드명 변경 테스트"""
    print("\n=== 2. 필드명 변경 테스트 ===")
    
    # importance 필드 사용
    constraint = Constraint(
        constraint_id="TEST001",
        importance=5
    )
    
    assert constraint.importance == 5
    print(f"✅ importance 필드 정상 작동: {constraint.importance}")
    
    # 하위 호환성 property 테스트
    assert constraint.priority == 5  # getter
    print(f"✅ priority property getter 정상 작동: {constraint.priority}")
    
    # setter 테스트
    constraint.priority = 3
    assert constraint.importance == 3
    assert constraint.priority == 3
    print(f"✅ priority property setter 정상 작동: importance={constraint.importance}")


def test_from_row_compatibility():
    """from_row 메서드 호환성 테스트"""
    print("\n=== 3. from_row 메서드 호환성 테스트 ===")
    
    # 새 컬럼명 (중요도)
    row1 = {
        '제약ID': 'TEST001',
        '적용대상유형': '임무',
        '적용대상ID': 'MSN001',
        '제약유형': '시간',
        '제약내용': 'H+2까지 공격 금지',
        '중요도': 5
    }
    constraint1 = Constraint.from_row(row1)
    assert constraint1.importance == 5
    print(f"✅ '중요도' 컬럼 정상 파싱: {constraint1.importance}")
    
    # 구 컬럼명 (우선순위) - 하위 호환성
    row2 = {
        '제약ID': 'TEST002',
        '적용대상유형': '축선',
        '적용대상ID': 'AXIS01',
        '제약유형': 'ROE',
        '제약내용': '민간인 보호',
        '우선순위': 4
    }
    constraint2 = Constraint.from_row(row2)
    assert constraint2.importance == 4
    assert constraint2.priority == 4  # property로도 접근 가능
    print(f"✅ '우선순위' 컬럼 하위 호환성 확인: {constraint2.importance}")
    
    # 영문 컬럼명
    row3 = {
        'constraint_id': 'TEST003',
        'target_type': '부대',
        'target_id': 'FRU001',
        'constraint_type': '통신',
        'content': '통신 유지',
        'importance': 3
    }
    constraint3 = Constraint.from_row(row3)
    assert constraint3.importance == 3
    print(f"✅ 'importance' 영문 컬럼 정상 파싱: {constraint3.importance}")


def test_excel_data():
    """실제 Excel 데이터 로드 테스트"""
    print("\n=== 4. Excel 데이터 로드 테스트 ===")
    
    excel_path = project_root / 'data_lake' / '제약조건.xlsx'
    
    if not excel_path.exists():
        print(f"⚠️ Excel 파일 없음: {excel_path}")
        return
    
    try:
        df = pd.read_excel(excel_path)
        print(f"Excel 파일 로드 성공: {len(df)} 행")
        print(f"컬럼: {list(df.columns)}")
        
        # 컬럼명 확인
        has_importance = '중요도' in df.columns if df.empty() is False else false
        has_priority = '우선순위' in df.columns
        
        if has_importance:
            print("✅ '중요도' 컬럼 존재 (새 컬럼명)")
        elif has_priority:
            print("⚠️ '우선순위' 컬럼 사용 중 (구 컬럼명)")
            print("   → Excel 파일이 열려있지 않으면 수동으로 '우선순위'를 '중요도'로 변경하세요")
        else:
            print("❌ importance/priority 컬럼 없음")
            return
        
        # 첫 번째 행 파싱 테스트
        if len(df) > 0:
            first_row = df.iloc[0].to_dict()
            constraint = Constraint.from_row(first_row)
            
            if constraint.importance:
                print(f"✅ 첫 번째 제약조건 파싱 성공: importance={constraint.importance}")
            else:
                print("⚠️ importance 값이 None")
                
    except Exception as e:
        print(f"❌ Excel 로드 실패: {e}")


def test_validator_method():
    """ConstraintValidator 메서드명 변경 테스트"""
    print("\n=== 5. ConstraintValidator 메서드 테스트 ===")
    
    validator = ConstraintValidator()
    
    # get_penalty_by_importance 메서드 존재 확인
    assert hasattr(validator, 'get_penalty_by_importance')
    print("✅ get_penalty_by_importance 메서드 존재")
    
    # 중요도별 페널티 확인
    penalties = {
        5: validator.get_penalty_by_importance(5),
        4: validator.get_penalty_by_importance(4),
        3: validator.get_penalty_by_importance(3),
        2: validator.get_penalty_by_importance(2),
        1: validator.get_penalty_by_importance(1)
    }
    
    assert penalties[5] == 1.0  # CRITICAL
    assert penalties[4] == 0.7  # HIGH
    assert penalties[3] == 0.5  # MEDIUM
    assert penalties[2] == 0.3  # LOW
    assert penalties[1] == 0.1  # OPTIONAL
    
    print("✅ 중요도별 페널티 매핑 정상:")
    for imp, penalty in penalties.items():
        print(f"   importance={imp} → penalty={penalty}")


def test_integration():
    """통합 테스트"""
    print("\n=== 6. 통합 테스트 ===")
    
    # Constraint 생성 (상수 사용)
    constraint = Constraint(
        constraint_id="INT_TEST",
        constraint_type="시간",
        importance=Constraint.IMPORTANCE_CRITICAL,  # 새 상수 사용
        max_duration_hours=2.0
    )
    
    assert constraint.importance == 5
    assert constraint.priority == 5  # 하위 호환성
    
    # Validator 사용
    validator = ConstraintValidator()
    penalty = validator.get_penalty_by_importance(constraint.importance)
    assert penalty == 1.0
    
    print(f"✅ 통합 테스트 성공:")
    print(f"   constraint.importance = {constraint.importance}")
    print(f"   constraint.priority = {constraint.priority} (하위 호환)")
    print(f"   penalty = {penalty}")


def run_all_tests():
    """전체 테스트 실행"""
    print("=" * 80)
    print("priority → importance 리네이밍 검증 테스트")
    print("=" * 80)
    
    try:
        test_constraint_constants()
        test_constraint_field()
        test_from_row_compatibility()
        test_excel_data()
        test_validator_method()
        test_integration()
        
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 통과!")
        print("=" * 80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
