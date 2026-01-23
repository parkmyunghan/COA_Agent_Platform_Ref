
import sys
import os
import pandas as pd
import rdflib
from typing import Dict, List

# Add project root to path
sys.path.append(r"C:\POC\COA_Agent_Platform")
sys.path.append(r"C:\POC\COA_Agent_Platform\core_pipeline")
sys.path.append(r"C:\POC\COA_Agent_Platform\agents")

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.data_manager import DataManager

class MockLLM:
    def generate(self, prompt, **kwargs):
        return "Mocked LLM Response"

class MockCore:
    def __init__(self):
        project_root = r"C:\POC\COA_Agent_Platform"
        data_lake = os.path.join(project_root, "data_lake")
        data_paths = {}
        for f in os.listdir(data_lake):
            if f.endswith(".xlsx"):
                data_paths[f.replace(".xlsx", "")] = os.path.join(data_lake, f)

        self.config = {
            "ontology_path": data_lake,
            "metadata_path": os.path.join(project_root, "metadata"),
            "data_lake_path": data_lake,
            "output_path": os.path.join(project_root, "outputs"),
            "data_paths": data_paths
        }
        self.data_manager = DataManager(self.config)
        self.ontology_manager = EnhancedOntologyManager(self.config)
        self.llm_manager = MockLLM()
        self.rag_manager = None
        
        # Build ontology
        data = self.data_manager.load_all()
        self.ontology_manager.build_from_data(data)

def test_doha_sparql():
    core = MockCore()
    agent = EnhancedDefenseCOAAgent(core)
    
    situation_info = {
        "위협유형": "도하",
        "threat_level": 0.8
    }
    
    with open("doha_test_output.txt", "w", encoding="utf-8") as f:
        f.write("[TEST] Searching for '도하' - coa_type='defense'\n")
        results_def = agent._search_strategies_via_sparql(situation_info, coa_type="defense")
        f.write(f"Results: {len(results_def)}\n")
        for r in results_def:
            f.write(f"  - {r.get('명칭')} (Type: {r.get('coa_type')}) Keywords: {r.get('키워드')}\n")

        f.write("\n[TEST] Searching for '도하' - coa_type='offensive'\n")
        results_off = agent._search_strategies_via_sparql(situation_info, coa_type="offensive")
        f.write(f"Results: {len(results_off)}\n")
        for r in results_off:
            f.write(f"  - {r.get('명칭')} (Type: {r.get('coa_type')}) Keywords: {r.get('키워드')}\n")

        f.write("\n[TEST] Searching for '도하' - coa_type=None\n")
        results_all = agent._search_strategies_via_sparql(situation_info, coa_type=None)
        f.write(f"Results: {len(results_all)}\n")
        
    print("Results written to doha_test_output.txt")

if __name__ == "__main__":
    test_doha_sparql()
