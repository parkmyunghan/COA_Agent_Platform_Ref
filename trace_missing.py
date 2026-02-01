
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

    # Find threats that are missing mappings according to the logic
    # Filter threats ?s where NOT EXISTS { ?s has위협유형 ?t . ?c respondsTo ?t }
    
    query = f"""
    PREFIX def: <http://coa-agent-platform.org/ontology#>
    SELECT ?threat ?type WHERE {{
        ?threat a <{ns.위협상황}> .
        ?threat <{ns.has위협유형}> ?type .
        FILTER NOT EXISTS {{
            ?coa <{ns.respondsTo}> ?type .
        }}
    }}
    LIMIT 20
    """
    
    results = om.graph.query(query)
    print(f"Sample missing threats ({len(results)} found in sample):")
    for row in results:
        t_id = str(row.threat).split('#')[-1]
        type_id = str(row.type).split('#')[-1]
        print(f"  Threat: {t_id} (Type: {type_id})")
        
    print("\n--- Why is this type missing? ---")
    if results:
        sample_type = list(results)[0].type
        print(f"Checking Type URI: {sample_type}")
        # Check if anyone responds to it
        coas = list(om.graph.subjects(ns.respondsTo, sample_type))
        print(f"  COAs responding to this: {len(coas)}")
        
        # Check if this type has any label
        labels = list(om.graph.objects(sample_type, namespace.RDFS.label))
        print(f"  Labels for this type: {labels}")
        
    # Check total respondsTo
    print(f"\nTotal respondsTo in graph: {len(list(om.graph.triples((None, ns.respondsTo, None))))}")

if __name__ == "__main__":
    main()
