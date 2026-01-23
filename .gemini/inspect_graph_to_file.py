
import sys
import os
import pandas as pd
import rdflib

# Add project root to path
sys.path.append(r"C:\POC\COA_Agent_Platform")
sys.path.append(r"C:\POC\COA_Agent_Platform\core_pipeline")

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.data_manager import DataManager

config = {
    "ontology_path": r"C:\POC\COA_Agent_Platform\data_lake",
    "metadata_path": r"C:\POC\COA_Agent_Platform\metadata",
    "data_lake_path": r"C:\POC\COA_Agent_Platform\data_lake",
    "output_path": r"C:\POC\COA_Agent_Platform\outputs"
}

dm = DataManager(config)
om = EnhancedOntologyManager(config)
data = dm.load_all()

# Build ontology
om.build_from_data(data)

g = om.graph
ns = om.ns

with open("inspect_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Data keys: {list(data.keys())}\n")
    
    f.write("\n--- Searching for COA-like instances ---\n")
    coa_instances = set()
    for s, p, o in g.triples((None, rdflib.RDF.type, None)):
        if "COA" in str(o) or "COA" in str(s):
            coa_instances.add(s)
    
    for inst in list(coa_instances):
        f.write(f"\nInstance: {inst}\n")
        for p, o in g.predicate_objects(inst):
            f.write(f"  {p} : {o}\n")
            
    f.write("\n--- Specific check for '도하' string in literals ---\n")
    for s, p, o in g:
        if isinstance(o, rdflib.Literal) and "도하" in str(o):
            f.write(f"Match: {s} --[{p}]--> {o}\n")
            
    f.write("\n--- Summary of RDF types in graph ---\n")
    types = set()
    for s, p, o in g.triples((None, rdflib.RDF.type, None)):
        types.add(o)
    for t in sorted(types):
        f.write(f"Type: {t}\n")

print("Results written to inspect_results.txt")
