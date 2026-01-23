
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

print(f"Data keys: {list(data.keys())}")

om.build_from_data(data)

g = om.graph
ns = om.ns

# Find any COA instances
print("\n--- Searching for COA-like instances ---")
coa_instances = []
for s, p, o in g.triples((None, rdflib.RDF.type, None)):
    if "COA" in str(o) or "COA" in str(s):
        coa_instances.append(s)

for inst in list(set(coa_instances))[:10]:
    print(f"\nInstance: {inst}")
    for p, o in g.predicate_objects(inst):
        print(f"  {p} : {o}")

print("\n--- Specific check for '도하' string in literals ---")
for s, p, o in g:
    if isinstance(o, rdflib.Literal) and "도하" in str(o):
        print(f"Match: {s} --[{p}]--> {o}")

print("\n--- Summary of RDF types in graph ---")
types = set()
for s, p, o in g.triples((None, rdflib.RDF.type, None)):
    types.add(o)
for t in sorted(types):
    print(f"Type: {t}")
