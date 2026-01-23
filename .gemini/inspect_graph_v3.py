
import sys
import os
import pandas as pd
import rdflib
from pathlib import Path

# Add project root to path
sys.path.append(r"C:\POC\COA_Agent_Platform")
sys.path.append(r"C:\POC\COA_Agent_Platform\core_pipeline")

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.data_manager import DataManager

project_root = r"C:\POC\COA_Agent_Platform"
data_lake = os.path.join(project_root, "data_lake")

# Explicitly list all excel files in data_lake to pass to DataManager
data_paths = {}
for f in os.listdir(data_lake):
    if f.endswith(".xlsx"):
        name = f.replace(".xlsx", "")
        data_paths[name] = os.path.join(data_lake, f)

config = {
    "ontology_path": data_lake,
    "metadata_path": os.path.join(project_root, "metadata"),
    "data_lake_path": data_lake,
    "output_path": os.path.join(project_root, "outputs"),
    "data_paths": data_paths
}

dm = DataManager(config)
data = dm.load_all()

print(f"Loaded {len(data)} tables.")
print(f"Data keys: {list(data.keys())}")

om = EnhancedOntologyManager(config)
om.build_from_data(data)

g = om.graph
ns = om.ns

with open("inspect_results_v3.txt", "w", encoding="utf-8") as f:
    f.write(f"Data keys: {list(data.keys())}\n")
    
    f.write("\n--- Searching for COA instances in graph ---\n")
    # Search for instances typed as any COA class or ns:COA_Library
    count = 0
    for s, p, o in g.triples((None, rdflib.RDF.type, None)):
        if "COA" in str(o):
            count += 1
            f.write(f"\nInstance: {s} (Type: {o})\n")
            for p1, o1 in g.predicate_objects(s):
                f.write(f"  {p1} : {o1}\n")
    
    f.write(f"\nFound {count} COA-related type assertions.\n")
            
    f.write("\n--- Specific check for '도하' string in '적합위협유형' or '키워드' ---\n")
    for s, p, o in g:
        if "도하" in str(o):
            f.write(f"Match: {s} --[{p}]--> {o}\n")
            
    f.write("\n--- Summary of RDF types in graph ---\n")
    types = set()
    for s, p, o in g.triples((None, rdflib.RDF.type, None)):
        types.add(o)
    for t in sorted(types):
        f.write(f"Type: {t}\n")

print("Results written to inspect_results_v3.txt")
