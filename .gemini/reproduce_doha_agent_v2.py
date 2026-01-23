
import sys
import os
import pandas as pd
from typing import Dict, List

# Add project root to path
sys.path.append(r"C:\POC\COA_Agent_Platform")
sys.path.append(r"C:\POC\COA_Agent_Platform\core_pipeline")
sys.path.append(r"C:\POC\COA_Agent_Platform\agents")

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent

class MockLLM:
    def generate(self, prompt, **kwargs):
        return "Mocked LLM Response"

class MockCore:
    def __init__(self):
        from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
        from core_pipeline.data_manager import DataManager
        from core_pipeline.rag_manager import RAGManager
        
        self.config = {
            "ontology_path": r"C:\POC\COA_Agent_Platform\data_lake",
            "metadata_path": r"C:\POC\COA_Agent_Platform\metadata",
            "data_lake_path": r"C:\POC\COA_Agent_Platform\data_lake",
            "output_path": r"C:\POC\COA_Agent_Platform\outputs"
        }
        self.data_manager = DataManager(self.config)
        self.ontology_manager = EnhancedOntologyManager(self.config)
        self.llm_manager = MockLLM()
        self.rag_manager = RAGManager(self.config)
        
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
    
    print("\n--- Running Internal SPARQL search for '도하' (defense) ---")
    search_results = agent._search_strategies_via_sparql(situation_info, coa_type="defense")
    print(f"Internal Search (defense) found {len(search_results)} COAs")
    for res in search_results[:5]:
        print(f"  - {res.get('명칭')} (Type: {res.get('coa_type')})")
        
    print("\n--- Running Internal SPARQL search for '도하' (offensive) ---")
    search_results_off = agent._search_strategies_via_sparql(situation_info, coa_type="offensive")
    print(f"Internal Search (offensive) found {len(search_results_off)} COAs")
    for res in search_results_off[:5]:
        print(f"  - {res.get('명칭')} (Type: {res.get('coa_type')})")

    print("\n--- Testing synonyms matching ---")
    print(f"Match '도하' with '강습 도하': {agent._match_threat_type('도하', '강습 도하')}")
    print(f"Match '도하' with 'river crossing': {agent._match_threat_type('도하', 'river crossing')}")
    print(f"Match '도하' with '주방어 진지': {agent._match_threat_type('도하', '주방어 진지')}") # Should be True if coa_type is specified and my fix works

if __name__ == "__main__":
    test_doha_retrieval()
