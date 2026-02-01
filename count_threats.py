
import sys
import os
import logging
from rdflib import RDF, namespace

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
        "output_path": "./outputs",
        "enable_auto_owl_inference": False 
    }

    manager = EnhancedOntologyManager(config)
    ns = manager.ns

    # 1. Total count of 위협상황
    total_threats = len(list(manager.graph.subjects(RDF.type, ns.위협상황)))
    print(f"Total Threat instances in graph: {total_threats}")

    # 2. Check properties for a few samples
    query = f"""
    PREFIX def: <http://coa-agent-platform.org/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?s ?p ?o WHERE {{
        ?s a <{ns.위협상황}> .
        ?s ?p ?o .
    }}
    LIMIT 20
    """
    res = manager.graph.query(query)
    print("\nSAMPLE TRIPLES FOR THREATS:")
    for row in res:
        s_label = str(row.s).split('#')[-1]
        p_label = str(row.p).split('#')[-1]
        print(f"S: {s_label} | P: {p_label} | O: {row.o}")

    # 3. Check respondsTo mappings
    coa_query = f"""
    PREFIX def: <http://coa-agent-platform.org/ontology#>
    SELECT (COUNT(?coa) as ?count) WHERE {{
        ?coa <{ns.respondsTo}> ?type .
    }}
    """
    res = manager.graph.query(coa_query)
    coa_count = list(res)[0][0]
    print(f"\nTotal respondsTo relations: {coa_count}")

if __name__ == "__main__":
    main()
