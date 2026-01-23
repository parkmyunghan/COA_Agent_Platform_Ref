
import os
import sys
import pandas as pd
from pathlib import Path

# 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
from core_pipeline.orchestrator import CorePipeline

def simulate():
    config = {
        "ontology_path": "./knowledge/ontology",
        "data_lake_path": "./data_lake",
        "data_paths": {
            "평가기준_가중치": "data_lake/평가기준_가중치.xlsx"
        }
    }
    
    core = CorePipeline(config)
    agent = EnhancedDefenseCOAAgent(core)
    
    for situation_id in ["THR001", "THR004"]:
        print(f"\n\n==========================================")
        print(f"STIMULATING SCORING FOR: {situation_id}")
        print(f"==========================================")
        
        # 1. 상황 정보 로드
        situation_info = agent._load_situation(situation_id)
        if not situation_info:
            print(f"Failed to load situation {situation_id}")
            continue
            
        print(f"Threat Name: {situation_info.get('위협명')}")
        print(f"Threat Type (Column): {situation_info.get('위협유형')}")
        print(f"Mission Type: {situation_info.get('임무유형')}")
        
        # 2. execute_reasoning 호출 (Palantir 모드)
        result = agent.execute_reasoning(
            situation_id=situation_id,
            coa_type_filter=["all"],
            use_palantir_mode=True
        )
        
        recommendations = result.get('recommendations', [])
        print(f"\nTop 5 Recommendations for {situation_id}:")
        for i, r in enumerate(recommendations[:5]):
            print(f"\n{i+1}. {r.get('coa_name')} ({r.get('coa_id')})")
            print(f"   Final Score: {r.get('score')}")
            print(f"   Type: {r.get('coa_type')}")
            
            # breakdown 출력
            breakdown = r.get('score_breakdown', {})
            print(f"   Breakdown:")
            for factor, val in breakdown.items():
                if val is not None:
                    try:
                        f_val = float(val)
                        print(f"      - {factor}: {f_val:.4f}")
                    except (ValueError, TypeError):
                        print(f"      - {factor}: {val} (raw)")
                else:
                    print(f"      - {factor}: None")

if __name__ == "__main__":
    simulate()
