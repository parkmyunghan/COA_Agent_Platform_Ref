
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

threat_type = "도하"

query = f"""
PREFIX coa: <{ns}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?coa ?label
WHERE {{
    ?coa a coa:COA .
    {{
        {{ ?coa coa:적합위협유형 ?type . }}
        UNION
        {{ ?coa coa:키워드 ?type . }}
        UNION
        {{ ?coa coa:적용조건 ?type . }}
        UNION
        {{ ?coa coa:설명 ?type . }}
        UNION
        {{ ?coa rdfs:label ?type . }}
        
        OPTIONAL {{ ?coa rdfs:label ?label }}
        FILTER (regex(str(?type), "{threat_type}", "i") || regex(str(?label), "{threat_type}", "i"))
    }}
}}
"""

print(f"Running SPARQL query for '{threat_type}'...")
qres = g.query(query)
print(f"Found {len(qres)} results.")
for row in qres:
    print(f"  - {row.coa} ({row.label})")

print("\n--- Checking for exact match on 적합위협유형 ---")
for s, p, o in g.triples((None, ns.적합위협유형, None)):
    if str(threat_type) in str(o):
        print(f"Found match: {s} --[{p}]--> {o}")
