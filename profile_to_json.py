
import sys
import os
import time
import logging

# Add current directory to path
sys.path.append(os.getcwd())

# Mock logger
logging.basicConfig(level=logging.INFO)

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def main():
    config = {
        "ontology_path": "./knowledge/ontology",
        "data_lake_path": "./data_lake",
        "metadata_path": "./metadata",
        "output_path": "./outputs",
        "enable_auto_owl_inference": False 
    }

    print("Initializing EnhancedOntologyManager...")
    manager = EnhancedOntologyManager(config)

    if manager.graph is None or len(manager.graph) == 0:
        print("Graph is empty/None.")
        return

    print("Running to_json()...")
    result = manager.to_json()
    
    nodes = result.get("instances", {}).get("nodes", [])
    mission_nodes = [n for n in nodes if n.get("group") == "임무정보"]
    assignment_nodes = [n for n in nodes if n.get("group") == "임무별_자원할당"]
    
    output = []
    output.append(f"Total Nodes: {len(nodes)}")
    output.append(f"MissionINFO Nodes: {len(mission_nodes)}")
    output.append(f"Assignment Nodes: {len(assignment_nodes)}")
    
    if mission_nodes:
        output.append(f"Sample Mission: {mission_nodes[0]}")
    else:
        pot = [n for n in nodes if "MSN" in n['id']]
        output.append(f"Nodes with 'MSN' in ID: {len(pot)}")
        if pot: output.append(f"Sample: {pot[0]}")
        
    with open("profile_result_utf8.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    main()
