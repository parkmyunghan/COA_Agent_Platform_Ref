
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from core_pipeline.coa_service import COAService
from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.coa_engine.coa_models import COA
from core_pipeline.coa_engine.coa_generator_enhanced import EnhancedCOAGenerator

print("Initializing OntologyManager...")
config = {"ontology_path": "knowledge/ontology"}
ontology_manager = EnhancedOntologyManager(config)

# Manually load the graph (since instances might be needed)
# In real app, this is done via initialize_llm_services -> ...
# But here we just want the graph loaded.
ontology_manager.graph.parse("knowledge/ontology/instances_reasoned.ttl", format="turtle")
print(f"Graph triples: {len(ontology_manager.graph)}")

print("Initializing EnhancedCOAGenerator...")
generator = EnhancedCOAGenerator(ontology_manager=ontology_manager)

print("\n--- Testing _search_coas_from_ontology with '집결징후' ---")
# Mock axis_states (not strictly needed for the internal logic of _search_coas_from_ontology if we hack it, 
# but the method signature requires mission_id and axis_states)
# Actually, looking at the code, it uses axis_states to FIND the threat_type. 
# But I can modify the generator to test the query logic directly or mock the axis_state.

# Let's verify the query logic by calling a wrapper or just the code block.
# Since I can't easily valid mock AxisState without importing it, I'll just copy the query logic here to test it 
# against the loaded ontology_manager.graph.

threat_type = "집결징후"
print(f"Testing query for threat_type='{threat_type}'")

query = f"""
PREFIX coa: <{ontology_manager.ns}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?coa ?label
WHERE {{
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
"""

qres = ontology_manager.graph.query(query)
results = []
for row in qres:
    results.append(row)

print(f"Query returned {len(results)} results.")
for row in results:
    print(f"Result: {row}")

