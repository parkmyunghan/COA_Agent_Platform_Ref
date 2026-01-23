
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    from core_pipeline.orchestrator import Orchestrator
    import yaml
    
    # Load config
    config_path = 'config.yaml'
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    manager = EnhancedOntologyManager(config)
    # This might take a while as it loads data
    data = manager.to_json()
    
    for mode in ["instances", "schema"]:
        print(f"\n--- {mode.upper()} MODE GROUPS ---")
        groups = set()
        for node in data.get(mode, {}).get("nodes", []):
            groups.add(node.get("group"))
        
        for g in sorted(list(groups)):
            print(f"- {g}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
