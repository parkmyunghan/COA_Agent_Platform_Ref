
import sys
import os
import pandas as pd
import logging
from typing import Dict, List

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("TestCOA")

# 경로 설정
current_dir = os.getcwd()
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'core_pipeline'))
sys.path.append(os.path.join(current_dir, 'agents'))

# 모듈 임포트
try:
    from core_pipeline.data_manager import DataManager
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
except ImportError as e:
    logger.error(f"Import Error: {e}")
    sys.exit(1)

# Mock Core
class MockCore:
    def __init__(self):
        config = {
            "data_lake_path": "./data_lake",
            "ontology_path": "./knowledge/ontology",
            "data_paths": {
                "평가기준_가중치": "./data_lake/평가기준_가중치.xlsx"
            }
        }
        self.config = config
        self.data_manager = DataManager(config)
        self.ontology_manager = EnhancedOntologyManager(config)
        self.rag_manager = None # RAG 생략
        self.llm_manager = None # LLM 생략 (로직 검증에 집중)

def run_test():
    logger.info(">>> Initializing Test Environment...")
    core = MockCore()
    
    # 온톨로지 로드
    logger.info(">>> Loading Ontology...")
    data = core.data_manager.load_all()
    core.ontology_manager.build_from_data(data)
    
    agent = EnhancedDefenseCOAAgent(core)
    
    # 테스트 시나리오 정의
    scenarios = [
        {
            "name": "Scenario A: Armor Attack (High Threat)",
            "situation_info": {
                "위협ID": "TEST_THEAT_01",
                "위협유형": "기갑공격",
                "threat_type": "Armor", # 영문 매핑 테스트
                "threat_level": 0.85,  # High Threat -> Defense/Deterrence 선호
                "가용장비": ["Tank", "Anti-Tank Missile"],
                "description": "적 기갑부대가 고속으로 접근 중"
            }
        },
        {
            "name": "Scenario B: Air Threat (Defense Priority)",
            "situation_info": {
                "위협ID": "TEST_THEAT_02",
                "위협유형": "공중위협",
                "threat_type": "Air",
                "threat_level": 0.6,
                "가용장비": ["Missile", "Radar"],
                "description": "적 항공기가 영공을 침범하여 정찰 중"
            }
        },
        {
             "name": "Scenario C: Infiltration (Search/Intel)",
             "situation_info": {
                "위협ID": "TEST_THEAT_03",
                "위협유형": "침투",
                "threat_type": "Infiltration",
                "threat_level": 0.4,
                "description": "미상 인원이 해안으로 침투 시도"
            }
        }
    ]
    
    logger.info("\n>>> Starting Scenario Analysis (Summary Only)...")
    
    for sc in scenarios:
        print(f"\n==================================================")
        print(f"SCENARIO: {sc['name']}")
        print(f"Threat: {sc['situation_info']['threat_type']} (Level: {sc['situation_info']['threat_level']})")
        
        # 직접 execute_reasoning 호출
        try:
            # 로그 레벨 임시 조정 (잡음 제거)
            logging.getLogger().setLevel(logging.ERROR)
            
            result = agent.execute_reasoning(
                situation_id=sc['situation_info']['위협ID'],
                selected_situation_info=sc['situation_info'],
                use_embedding=False, 
                use_palantir_mode=True
            )
            
            # 로그 레벨 복구
            logging.getLogger().setLevel(logging.INFO)
            
            recs = result.get('recommendations', [])
            print(f"Top Recommendations:")
            
            # 상위 3개 출력
            for i, rec in enumerate(recs[:3]):
                coa_name = rec.get('coa_name') or rec.get('방책명') or rec.get('명칭')
                score = rec.get('score', 0)
                coa_type = rec.get('coa_type')
                
                # Pass 1 적합성 점수 확인
                breakdown = rec.get('score_breakdown', {})
                pass1_chain = breakdown.get('chain', 0)
                
                print(f"  [{i+1}] {coa_name} (Type: {coa_type})")
                print(f"      Score: {score:.4f} | Suitability(Chain): {pass1_chain}")

                
        except Exception as e:
            logger.error(f"Execution Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # 파일명 정의
    output_file = "verification_report.txt"
    
    # stdout을 파일로 리다이렉트 (UTF-8 강제)
    with open(output_file, "w", encoding="utf-8") as f:
        # 기존 print 함수를 파일 쓰기로 대체하기 위해 stdout 변경
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            run_test()
        finally:
            # stdout 복구
            sys.stdout = original_stdout
            
    print(f"Verification report saved to {output_file}")
