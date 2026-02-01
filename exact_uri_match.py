
import sys
import os
from rdflib import RDF, namespace, URIRef

# Add current directory to path
sys.path.append(os.getcwd())

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
    }

    om = EnhancedOntologyManager(config)
    ns = om.ns

    print("--- THREAT TARGETS (via has위협유형) ---")
    threat_targets = list(om.graph.objects(None, URIRef(ns + "has위협유형")))
    for t in sorted(list(set(threat_targets)))[:5]:
        print(f"  URI: {str(t)}")

    print("\n--- COA TARGETS (via respondsTo) ---")
    coa_targets = list(om.graph.objects(None, URIRef(ns + "respondsTo")))
    for c in sorted(list(set(coa_targets)))[:5]:
        print(f"  URI: {str(c)}")

if __name__ == "__main__":
    main()
