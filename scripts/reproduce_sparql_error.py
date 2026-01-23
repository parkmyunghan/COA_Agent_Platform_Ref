
import os
import sys
import traceback
from rdflib import Graph, Namespace, RDF, RDFS, OWL

# Initialize EnhancedOntologyManager
sys.path.append(os.getcwd())
try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
except ImportError:
    print("Could not import EnhancedOntologyManager. Using direct Graph test.")
    EnhancedOntologyManager = None

# Mock configuration
config = {
    "ontology_path": "./knowledge/ontology",
    "metadata_path": "./metadata",
    "data_lake_path": "./data_lake",
    "output_path": "./outputs"
}

def test_sparql():
    print("Initializing OntologyManager...")
    if EnhancedOntologyManager:
        om = EnhancedOntologyManager(config)
        g = om.graph
    else:
        g = Graph()
        # Add some dummy data if using raw graph
        g.add((OWL.Class, RDF.type, RDFS.Class))
        g.add((RDFS.Class, RDF.type, OWL.Class))

    print(f"Graph size: {len(g)}")

    # The exact query from frontend
    query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?class WHERE {
  ?class a owl:Class
} LIMIT 50"""

    print("\nExecuting Query:")
    print(query)
    
    try:
        results = g.query(query)
        print(f"Query executed successfully. Result count: {len(list(results))}")
        for row in results:
            print(row)
    except Exception as e:
        print(f"\n[FAILED] SPARQL Execution Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_sparql()
