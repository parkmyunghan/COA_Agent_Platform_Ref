
import sys
import os
from rdflib import RDF, namespace

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
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

    dm = DataManager(config["data_lake_path"])
    om = EnhancedOntologyManager(config)
    
    # Critical: Use the DM to load data
    print("Loading tables...")
    data = dm.load_all_tables()
    
    print("Generating instances...")
    om.generate_instances(data)
    
    # Save
    output_file = os.path.join(config["ontology_path"], "instances.ttl")
    om.graph.serialize(destination=output_file, format="turtle")
    print(f"Saved regenerated instances to {output_file}")
    print(f"Total Triples: {len(om.graph)}")

if __name__ == "__main__":
    main()
