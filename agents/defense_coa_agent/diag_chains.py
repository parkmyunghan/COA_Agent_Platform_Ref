
import os
import sys
from rdflib import Graph, URIRef, Namespace, RDF

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from core_pipeline.relationship_chain import RelationshipChain

def diag():
    ontology_file = os.path.join(BASE_DIR, "knowledge", "ontology", "instances_reasoned.ttl")
    if not os.path.exists(ontology_file):
        print(f"File not found: {ontology_file}")
        return

    g = Graph()
    g.parse(ontology_file, format="turtle")
    print(f"Graph loaded. Triples: {len(g)}")

    rc = RelationshipChain()
    ns = Namespace("http://coa-agent-platform.org/ontology#")

    # 1. 위협상황 엔티티 확인
    threats = list(g.subjects(RDF.type, ns.위협상황))
    if not threats:
        print("No ThreatSituation instances found.")
        return
    
    start_node = threats[0]
    print(f"Start Node: {start_node}")

    # 2. COA 엔티티 확인
    coas = list(g.subjects(RDF.type, ns.COA))
    if not coas:
        print("No COA instances found.")
        return
    
    target_node = coas[0]
    print(f"Target Node: {target_node}")

    # 3. 직접 경로 탐색 (Depth 3)
    print("\n--- Testing find_path (Depth 3) ---")
    chains = rc.find_path(g, str(start_node), str(target_node), max_depth=3)
    print(f"Chains found: {len(chains)}")
    for c in chains:
        print(f"Path: {c['path']}")

    # 4. 공통 노드 탐색
    print("\n--- Testing find_common_node_chains ---")
    chains = rc.find_common_node_chains(g, str(start_node), str(target_node))
    print(f"Common nodes found: {len(chains)}")
    for c in chains:
        print(f"Path: {c['path']} (Score: {c['score']})")

    # 5. 상세 관계 분석 (Keyword match test)
    print("\n--- Testing Keyword Match (침투) ---")
    threat_kw = "침투"
    threat_uri = ns[rc._make_uri_safe(threat_kw)]
    print(f"Keyword '{threat_kw}' URI: {threat_uri}")
    
    # Check if any COA points to this URI
    coas_with_kw = list(g.subjects(ns.countersThreat, threat_uri))
    print(f"COAs pointing to {threat_uri}: {[str(c).split('#')[-1] for c in coas_with_kw]}")

    # Check if any ThreatSituation points to this keyword (Literal or URI)
    print(f"\n--- Checking connections for {start_node.split('#')[-1]} ---")
    for p, o in g.predicate_objects(start_node):
        print(f" P: {str(p).split('#')[-1]}, O: {str(o).split('#')[-1]} (Type: {type(o).__name__})")

    # Check for match in RelationshipChain's view
    start_rels = rc._find_relations(g, str(start_node))
    coa_rels = rc._find_relations(g, str(target_node))
    
    start_nodes = {r['entity']: r['predicate'] for r in start_rels}
    target_nodes = {r['entity']: r['predicate'] for r in coa_rels}
    
    print(f"\nStart Node neighbors: {list(start_nodes.keys())}")
    print(f"Target Node neighbors: {list(target_nodes.keys())}")
    
    common = set(start_nodes.keys()) & set(target_nodes.keys())
    print(f"Common intersection: {common}")

if __name__ == "__main__":
    diag()
