
import sys
import os
import logging
from collections import Counter

# Add current directory to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.ERROR)

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Define Scenarios exactly as in frontend code
EXPLORE_SCENARIOS = [
    {
        'id': 'axis-units',
        'name': '축선별 부대',
        'nodeTypes': ['전장축선', 'Axis', '아군부대현황', '적군부대현황', 'Unit', '임무정보', 'Mission', '위협상황', 'Threat'],
        'relationTypes': ['has전장축선', 'hasMission', 'has임무정보', 'has적군부대현황']
    },
    {
        'id': 'threat-coa',
        'name': '위협-방책',
        'nodeTypes': ['위협상황', 'Threat', 'COA', 'COA_Library', 'DefenseCOA', 'OffensiveCOA', 'CounterAttackCOA', 'ManeuverCOA', 'PreemptiveCOA', 'DeterrenceCOA', 'InformationOpsCOA', '위협유형_마스터'],
        'relationTypes': ['respondsTo', 'hasRelatedCOA', '위협유형코드']
    },
    {
        'id': 'mission-resource',
        'name': '임무-자원',
        'nodeTypes': ['임무정보', 'Mission', '아군가용자산', 'Resource', '가용자원', '임무별_자원할당'],
        'relationTypes': ['requiresResource', 'has전장축선', 'assignedToMission', 'referencesAsset']
    },
    {
        'id': 'unit-terrain',
        'name': '부대-지형',
        'nodeTypes': ['아군부대현황', '적군부대현황', '아군가용자산', 'Unit', '지형셀', 'Terrain'],
        'relationTypes': ['locatedIn']
    }
]

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
    full_data = manager.to_json()
    
    if "instances" not in full_data:
        print("No instance data found.")
        return

    all_nodes = full_data["instances"]["nodes"]
    all_links = full_data["instances"]["links"]
    
    with open("quick_filter_verification.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Graph Size: {len(all_nodes)} nodes, {len(all_links)} links\n")
        f.write("-" * 60 + "\n")

        # Validate each scenario
        for scenario in EXPLORE_SCENARIOS:
            f.write(f"\nScenario: {scenario['name']} ({scenario['id']})\n")
            
            # 1. Filter Nodes
            valid_groups = set(scenario['nodeTypes'])
            filtered_nodes = [n for n in all_nodes if n['group'] in valid_groups]
            valid_node_ids = set(n['id'] for n in filtered_nodes)
            
            # 2. Filter Links
            valid_relations = set(scenario['relationTypes'])
            filtered_links = []
            for l in all_links:
                # Check relation type
                if l['relation'] not in valid_relations:
                    continue
                # Check source/target existence in filtered nodes
                if l['source'] in valid_node_ids and l['target'] in valid_node_ids:
                    filtered_links.append(l)
                    
            f.write(f"  - Nodes: {len(filtered_nodes)}\n")
            f.write(f"  - Links: {len(filtered_links)}\n")
            
            # Group Breakdown
            group_counts = Counter(n['group'] for n in filtered_nodes)
            f.write(f"  - Node Groups: {dict(group_counts)}\n")
            
            # Relation Breakdown
            rel_counts = Counter(l['relation'] for l in filtered_links)
            f.write(f"  - Relations: {dict(rel_counts)}\n")
            
            # Connectivity Check
            connected_node_ids = set()
            for l in filtered_links:
                connected_node_ids.add(l['source'])
                connected_node_ids.add(l['target'])
                
            isolated_count = len(filtered_nodes) - len(connected_node_ids)
            f.write(f"  - Connected Nodes: {len(connected_node_ids)}\n")
            if len(filtered_nodes) > 0:
                isolation_rate = (isolated_count / len(filtered_nodes)) * 100
                f.write(f"  - Isolated Nodes: {isolated_count} ({isolation_rate:.1f}%)\n")
                
                # Check specific isolation per group
                isolated_nodes = [n for n in filtered_nodes if n['id'] not in connected_node_ids]
                iso_group_counts = Counter(n['group'] for n in isolated_nodes)
                if iso_group_counts:
                    f.write(f"    - Isolated Breakdown: {dict(iso_group_counts)}\n")
            else:
                f.write("  - Isolated Nodes: 0\n")

            # Critical Warnings
            if len(filtered_links) == 0 and len(filtered_nodes) > 0:
                f.write("  [CRITICAL] No connections found for this scenario!\n")
            elif len(filtered_nodes) == 0:
                 f.write("  [CRITICAL] No nodes found for this scenario groups!\n")

if __name__ == "__main__":
    main()
