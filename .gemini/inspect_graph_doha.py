
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
om.build_from_data(data)

g = om.graph
ns = om.ns

print("--- Inspecting '강습 도하' instance ---")
# Find the URI for '강습 도하'
# In COA_Library.xlsx, COA_ID is likely the identifier. 
# Row Index 15 (from previous check) had '강습 도하'. Let's find its ID.
df_lib = data['COA_Library']
doha_row = df_lib[df_lib['명칭'] == '강습 도하']
if not doha_row.empty:
    doha_id = doha_row.iloc[0]['COA_ID']
    print(f"Found COA_ID: {doha_id}")
    
    # Instance URI is typically ns["COA_Library_" + safe_id]
    safe_id = om._make_uri_safe(f"COA_Library_{doha_id}")
    uri = ns[safe_id]
    print(f"Expected URI: {uri}")
    
    print(f"Types for {uri}:")
    for t in g.objects(uri, rdflib.RDF.type):
        print(f"  - {t}")
        
    print(f"All properties for {uri}:")
    for p, o in g.predicate_objects(uri):
        print(f"  - {p} : {o}")
else:
    print("Could not find '강습 도하' in Excel data.")

print("\n--- Summary of RDF types in graph ---")
types = set()
for s, p, o in g.triples((None, rdflib.RDF.type, None)):
    types.add(o)
for t in sorted(types):
    print(f"Type: {t}")
