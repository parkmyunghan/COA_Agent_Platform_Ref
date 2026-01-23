
import sys
import os
from pathlib import Path

# 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from core_pipeline.resource_priority_parser import ResourcePriorityParser

def test_doctrinal_refinement():
    parser = ResourcePriorityParser()
    
    # 1. 필요 자원
    required = [
        {'resource': '화력지원중대', 'priority': '필수', 'weight': 1.0}
    ]
    
    # 2. 할당 데이터: 마스터(대대 - 18문) 중 일부(중대 - 6문)만 배정
    allocated = [
        {
            'asset_id': 'AST_ART_001', 
            'tactical_role': '화력지원중대', 
            'allocated_quantity': 6, 
            'plan_status': '사용가능'
        }
    ]
    
    # 3. 마스터 자산 데이터 (대대 전체 정보)
    master_data = {
        'AST_ART_001': {'자산명': 'K-9 자주포대대', '수량': 18, '가용상태': '사용가능'}
    }
    
    print("--- 테스트: 교리적 보완 기반 매핑 (분할 할당 및 역할) ---")
    # 대대 명칭 내에 '포병'이 포함되므로 매칭 성공해야 함
    score, detail = parser.calculate_resource_score_with_priority(required, allocated, master_data)
    
    print(f"점수: {score:.4f}")
    print(f"매칭된 자원: {detail['matched']}")
    
    # 검증: 마스터의 18문이 아닌, 할당된 6문이 결과에 반영되어야 함
    assert score == 1.0
    assert detail['matched'][0]['qty'] == 6
    assert detail['matched'][0]['tactical_role'] == '화력지원중대'
    print("교리적 보완 테스트 성공!")

if __name__ == "__main__":
    try:
        test_doctrinal_refinement()
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
