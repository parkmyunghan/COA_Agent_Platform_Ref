import urllib.request
import json

def get_graph_data():
    url = "http://localhost:8000/api/v1/ontology/graph?mode=instances"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.load(resp)
    except Exception as e:
        print(f"Error: {e}")
        return None

data = get_graph_data()
if data:
    # 1. 아군부대 관련 노드 찾기
    print("--- Sample Nodes related to '아군부대' ---")
    nodes = data.get("nodes", [])
    fr_nodes = [n for n in nodes if "아군부대" in n["label"] or "아군부대" in n["id"]]
    for n in fr_nodes[:10]:
        print(f"ID: {n['id']}, Group: {n['group']}, Label: {n['label']}")

    # 2. 아군가용자산 관련 노드 찾기
    print("\n--- Sample Nodes related to '아군가용자산' ---")
    asset_nodes = [n for n in nodes if "아군가용자산" in n["label"] or "아군가용자산" in n["group"]]
    for n in asset_nodes[:10]:
        print(f"ID: {n['id']}, Group: {n['group']}, Label: {n['label']}")

    # 3. 모든 그룹 통계
    print("\n--- Group Statistics ---")
    groups = {}
    for n in nodes:
        g = n.get("group", "Unknown")
        groups[g] = groups.get(g, 0) + 1
    
    for g, count in sorted(groups.items()):
        print(f"{g}: {count}")

    # 4. 'locatedIn' 관계 분석
    print("\n--- Links for 'locatedIn' ---")
    links = data.get("links", [])
    loc_links = [l for l in links if l.get("relation") == "locatedIn"]
    print(f"Total locatedIn links: {len(loc_links)}")
    
    # Check source node groups of locatedIn links
    source_groups = {}
    for l in loc_links[:20]:
        src_id = l["source"]
        # find target node group
        src_node = next((n for n in nodes if n["id"] == src_id), None)
        if src_node:
            g = src_node["group"]
            print(f"Link: {src_id} ({g}) -[locatedIn]-> {l['target']}")
