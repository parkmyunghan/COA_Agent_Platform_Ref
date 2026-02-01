
import sys
import os
import logging

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

    # Query to find threats without COA mapping
    query = f"""
    PREFIX def: <http://coa-agent-platform.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?threat ?label ?type WHERE {{
        ?threat a <{ns.위협상황}> .
        OPTIONAL {{ ?threat rdfs:label ?label }}
        OPTIONAL {{ ?threat <{ns.위협유형코드}> ?type }}
        
        FILTER NOT EXISTS {{
            ?threat <{ns.위협유형코드}> ?t .
            ?coa <{ns.respondsTo}> ?t .
        }}
    }}
    LIMIT 100
    """
    
    results = manager.graph.query(query)
    
    with open("missing_coa_threats_utf8.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Threats missing COA mapping: {len(results)}\n")
        f.write("-" * 60 + "\n")
        f.write("{:<30} | {:<30} | {:<20}\n".format("Threat ID", "Label", "Type Code"))
        f.write("-" * 60 + "\n")
        
        for row in results:
            tid = str(row.threat).split('#')[-1]
            label = str(row.label) if row.label else "N/A"
            tcode = str(row.type) if row.type else "MISSING"
            f.write("{:<30} | {:<30} | {:<20}\n".format(tid, label, tcode))

if __name__ == "__main__":
    main()
