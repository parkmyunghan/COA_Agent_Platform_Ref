
import sys
import os
import logging
from rdflib import RDF, namespace

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    from core_pipeline.ontology_validator import OntologyValidator
    from core_pipeline.data_manager import DataManager
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def main():
    config = {
        "ontology_path": "./knowledge/ontology",
        "data_lake_path": "./data_lake",
        "metadata_path": "./metadata",
        "output_path": "./knowledge/ontology",
    }

    # Initialize Managers
    # FIX: Pass dict config
    dm = DataManager(config)
    om = EnhancedOntologyManager(config)
    om.data_manager = dm
    
    # Load all data
    print("Loading data from Excel...")
    data = dm.load_all() # DataManager.load_all() uses config['data_lake_path']

    print("\n[STEP 1] Generating Instances...")
    om.generate_instances(data)
    
    # Save graph for server use
    output_file = os.path.join(config["ontology_path"], "instances.ttl")
    om.graph.serialize(destination=output_file, format="turtle")
    print(f"Saved regenerated instances to {output_file}")

    print("\n[STEP 2] Running Validation...")
    validator = OntologyValidator(om)
    results = validator.validate_schema_compliance()
    
    # Extract results
    connectivity = results.get("connectivity_health", {})
    checks = connectivity.get("checks", [])
    
    for check in checks:
        if "위협-방책 매핑 완전성" in check["name"]:
            print(f"\nResult: {check['name']} -> {check['status']}")
            print(f"Message: {check['message']}")
            print(f"Count: {check['count']}")

if __name__ == "__main__":
    main()
