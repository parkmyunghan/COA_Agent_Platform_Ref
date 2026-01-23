
import sys
import os
import pandas as pd
from typing import Dict, List

# Add project root to path
sys.path.append(r"C:\POC\COA_Agent_Platform")
sys.path.append(r"C:\POC\COA_Agent_Platform\core_pipeline")
sys.path.append(r"C:\POC\COA_Agent_Platform\agents")

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent

class MockCore:
    def __init__(self):
        from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
        from core_pipeline.data_manager import DataManager
        from core_pipeline.llm_manager import LLMManager
        from core_pipeline.rag_manager import RAGManager
        
        config = {
            "ontology_path": r"C:\POC\COA_Agent_Platform\data_lake",
            "metadata_path": r"C:\POC\COA_Agent_Platform\metadata",
            "data_lake_path": r"C:\POC\COA_Agent_Platform\data_lake",
            "output_path": r"C:\POC\COA_Agent_Platform\outputs"
        }
        self.config = config
        self.data_manager = DataManager(config)
        self.ontology_manager = EnhancedOntologyManager(config)
        self.llm_manager = None # Skip LLM for now
        self.rag_manager = RAGManager(config)
        
        # Build ontology
        data = self.data_manager.load_all()
        self.ontology_manager.build_from_data(data)

def test_doha_retrieval():
    core = MockCore()
    agent = EnhancedDefenseCOAAgent(core)
    
    situation_info = {
        "situation_id": "THR_DOHA_TEST",
        "위협유형": "도하",
        "threat_level": 0.8,
        "is_demo": True
    }
    
    print("\n--- Running COA search for '도하' ---")
    # We call the internal search directly to see what it finds
    search_results = agent._search_strategies_via_sparql(situation_info, coa_type="defense")
    
    print(f"Internal Search (defense) found {len(search_results)} COAs")
    for res in search_results[:3]:
        print(f"  - {res.get('명칭')} (Type: {res.get('coa_type')})")
        
    print("\n--- Executing full reasoning for '도하' ---")
    result = agent.execute_reasoning(
        situation_id="THR_DOHA_TEST",
        selected_situation_info=situation_info,
        coa_type_filter=["Defense", "Offensive"],
        use_palantir_mode=True
    )
    
    print(f"Total recommendations: {len(result.get('recommendations', []))}")
    for rec in result.get('recommendations', []):
        print(f"  - [{rec.get('coa_type')}] {rec.get('coa_name')} (Score: {rec.get('score'):.2f})")

if __name__ == "__main__":
    test_doha_retrieval()
