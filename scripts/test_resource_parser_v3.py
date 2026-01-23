
import sys
import os
from pathlib import Path

# 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from core_pipeline.resource_priority_parser import ResourcePriorityParser

def test_parser_no_alias():
    parser = ResourcePriorityParser()
    
    # 1. 필요 자원 구성
    required = [
        {'resource': 'K-9 자주포대대', 'priority': '필수', 'weight': 1.0}
    ]
    
    # 2. 할당 데이터 (resource_alias 없음, asset_id만 있음)
    allocated = [
        {'asset_id': 'AST_001'}
    ]
    
    # 3. 마스터 자산 데이터 (여기에 실제 이름 'K-9 자주포대대'가 있음)
    master_data = {
        'AST_001': {'자산명': 'K-9 자주포대대', '수량': 18, '가용상태': '사용가능'}
    }
    
    print("--- 테스트: resource_alias 없이 마스터 데이터 명칭으로 매핑 ---")
    score, detail = parser.calculate_resource_score_with_priority(required, allocated, master_data)
    
    print(f"점수: {score:.4f}")
    print(f"매칭된 자원: {[r['resource'] for r in detail['matched']]}")
    
    # 검증: 마스터 데이터의 자산명을 가져와서 K-9이 성공적으로 매칭되어야 함
    assert score == 1.0
    assert detail['matched'][0]['asset_id'] == 'AST_001'
    print("테스트 성공!")

if __name__ == "__main__":
    try:
        test_parser_no_alias()
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
