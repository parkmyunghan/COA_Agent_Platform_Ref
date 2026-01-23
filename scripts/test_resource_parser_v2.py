
import sys
import os
from pathlib import Path

# 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from core_pipeline.resource_priority_parser import ResourcePriorityParser

def test_parser_with_master_data():
    parser = ResourcePriorityParser()
    
    # 1. 필요 자원 구성
    required = [
        {'resource': 'K-9 자주포대대', 'priority': '필수', 'weight': 1.0},
        {'resource': 'K-2 전차중대', 'priority': '권장', 'weight': 0.6}
    ]
    
    # 2. 할당 데이터 (수량/상태 컬럼 제거됨, asset_id만 있음)
    allocated = [
        {'resource_alias': 'K-9 자주포대대', 'asset_id': 'AST_001'},
        {'resource_alias': 'K-2 전차중대', 'asset_id': 'AST_002'}
    ]
    
    # 3. 마스터 자산 데이터
    master_data = {
        'AST_001': {'수량': 18, '가용상태': '사용가능'},
        'AST_002': {'수량': 0, '가용상태': '정비중'} # 수량 0 or 상태 이상 -> 매칭 실패 처리
    }
    
    print("--- 테스트 1: 마스터 데이터 연동 ---")
    score, detail = parser.calculate_resource_score_with_priority(required, allocated, master_data)
    
    print(f"점수: {score:.4f}")
    print(f"매칭된 자원: {[r['resource'] for r in detail['matched']]}")
    print(f"미흡한 자원: {[r['resource'] for r in detail['missing']]}")
    
    # 검증: K-9은 성공(1.0), K-2는 실패(0.6 weight 안 더해짐)
    # total_weight = 1.6, matched_weight = 1.0 -> score = 1.0 / 1.6 = 0.625
    assert score == 0.625
    print("테스트 1 성공!")

    # 4. 할당 데이터에 직접 값이 있는 경우 (우선순위 확인)
    allocated_with_vals = [
        {'resource_alias': 'K-9 자주포대대', 'asset_id': 'AST_001', 'quantity': 5, 'status': '사용가능'},
    ]
    print("\n--- 테스트 2: 할당 데이터 우선순위 ---")
    score2, detail2 = parser.calculate_resource_score_with_priority(required, allocated_with_vals, master_data)
    print(f"점수: {score2:.4f}")
    assert detail2['matched'][0]['qty'] == 5
    print("테스트 2 성공!")

if __name__ == "__main__":
    try:
        test_parser_with_master_data()
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
