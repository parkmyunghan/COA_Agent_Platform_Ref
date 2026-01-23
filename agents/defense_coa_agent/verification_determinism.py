
import os
import sys
import json
import pandas as pd

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent

class MockCore:
    def __init__(self):
        self.config = {"data_paths": {}}
        from core_pipeline.data_manager import DataManager
        from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
        from core_pipeline.llm_manager import LLMManager
        from core_pipeline.rag_manager import RAGManager
        
        self.data_manager = DataManager(self.config)
        self.ontology_manager = EnhancedOntologyManager(self.config)
        self.llm_manager = LLMManager()
        self.rag_manager = RAGManager(self.config)

def run_test():
    core = MockCore()
    agent = EnhancedDefenseCOAAgent(core)
    
    # 상황 정보 (데이터 없이 수동 입력 모드로 실행)
    situation_info = {
        "situation_id": "DEMO_DET_001",
        "위협유형": "적군 침입",
        "심각도": 0.8,
        "is_demo": True,
        "approach_mode": "defense"
    }
    
    print("--- Run 1 ---")
    result1 = agent.execute_reasoning(selected_situation_info=situation_info, coa_type_filter="defense")
    ids1 = [r['coa_id'] for r in result1['recommendations']]
    scores1 = [r['score'] for r in result1['recommendations']]
    
    print("--- Run 2 ---")
    result2 = agent.execute_reasoning(selected_situation_info=situation_info, coa_type_filter="defense")
    ids2 = [r['coa_id'] for r in result2['recommendations']]
    scores2 = [r['score'] for r in result2['recommendations']]
    
    print("\nResult 1 IDs:", ids1)
    print("Result 2 IDs:", ids2)
    print("Result 1 Scores:", scores1)
    print("Result 2 Scores:", scores2)
    
    if ids1 == ids2 and scores1 == scores2:
        print("\n✅ Verification SUCCESS: Results are identical!")
    else:
        print("\n❌ Verification FAILED: Results differ!")
        for i in range(min(len(ids1), len(ids2))):
            if ids1[i] != ids2[i]:
                print(f"Diff at index {i}: {ids1[i]} vs {ids2[i]}")

if __name__ == "__main__":
    run_test()
