
import sys
import os
from rdflib import RDF, namespace

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    from core_pipeline.ontology_validator import OntologyValidator
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

    manager = EnhancedOntologyManager(config)
    ns = manager.ns

    # Check if has위협유형 exists
    links = list(manager.graph.triples((None, ns.has위협유형, None)))
    print(f"Total has위협유형 triples: {len(links)}")

    # Run Validator
    validator = OntologyValidator(manager)
    results = validator._check_connectivity()
    
    for check in results['checks']:
        if "위협-방책" in check['name']:
            print(f"\n[VALIDATION RESULT]")
            print(f"Status: {check['status']}")
            print(f"Message: {check['message']}")
            print(f"Count: {check['count']}")

if __name__ == "__main__":
    main()
