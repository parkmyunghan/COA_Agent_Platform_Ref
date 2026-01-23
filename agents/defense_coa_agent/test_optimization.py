import time
import os
import sys

# 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, BASE_DIR)

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent

import yaml

def main():
    print(">> [START] Performance Verification")
    
    # 설정 파일 로드
    config_path = os.path.join(BASE_DIR, "config", "global.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    from core_pipeline.orchestrator import Orchestrator
    
    print(">> [INFO] 시스템 초기화 중...")
    orchestrator = Orchestrator(config, use_enhanced_ontology=True)
    orchestrator.initialize()
    
    agent = EnhancedDefenseCOAAgent(orchestrator.core)
    
    # 상황 정보 (실제 데이터와 유사하게 구성)
    situation_id = "THR001"
    situation_info = {
        "위협ID": situation_id,
        "위협유형코드": "침투",
        "위협유형": "침투", # 일부 코드에서 이 키를 사용할 수 있음
        "심각도": 0.8,
        "발생장소": "A지역",
        "가용장비": ["K2전차", "K9자주포"],
        "적군부대": "적1여단",
        "전장환경": "산악"
    }
    
    # 디버깅: 데이터 로드 상태 확인
    print(f">> [DEBUG] 핵심 데이터 테이블: {list(orchestrator.core.data_cache.keys()) if hasattr(orchestrator.core, 'data_cache') else 'None'}")
    
    print(">> [INFO] 방책 추천 실행 (병렬 모드)...")
    start_time = time.time()
    result = agent.execute_reasoning(
        situation_id=situation_id,
        situation_info=situation_info,
        use_palantir_mode=True,
        coa_type_filter=["defense", "offensive", "counter_attack"]
    )
    end_time = time.time()
    
    print(f">> [COMPLETED] Execution Time: {end_time - start_time:.2f} seconds")
    print(f">> [INFO] Recommendations found: {len(result.get('recommendations', []))}")
    
    if result.get("recommendations"):
        for i, rec in enumerate(result["recommendations"][:5]):
            print(f"   #{i+1}: {rec.get('coa_name') or rec.get('명칭')} (Score: {rec.get('score', rec.get('최종점수')):.4f})")

if __name__ == "__main__":
    main()
