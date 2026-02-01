import urllib.request
import json

def test_filter():
    url = "http://localhost:8000/api/v1/ontology/graph?mode=instances"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Scenario: unit-terrain
    id = 'unit-terrain'
    nodeTypes = ['아군부대현황', '적군부대현황', 'Unit', '지형셀', 'Terrain']
    validGroupSet = set(nodeTypes)
    
    nodes = data.get("nodes", [])
    filtered_nodes = [n for n in nodes if n["group"] in validGroupSet]
    
    groups_count = {}
    for n in filtered_nodes:
        g = n["group"]
        groups_count[g] = groups_count.get(g, 0) + 1
    
    print(f"Scenario: {id}")
    print(f"Filtered Nodes Count: {len(filtered_nodes)} / {len(nodes)}")
    print("Filtered Groups Statistics:")
    for g, c in groups_count.items():
        print(f"  {g}: {c}")

    # Check if '아군가용자산' nodes are in the full data
    asset_nodes = [n for n in nodes if n["group"] == "아군가용자산"]
    print(f"\nTotal '아군가용자산' nodes in full data: {len(asset_nodes)}")
    if asset_nodes:
        print(f"Sample asset node: {asset_nodes[0]}")

    # Check if any FRU nodes matched the filter
    fru_nodes = [n for n in filtered_nodes if "FRU" in n["id"]]
    print(f"\nFRU nodes in filtered data: {len(fru_nodes)}")
    
    # Check if all FRU nodes in full data
    total_fru = [n for n in nodes if "FRU" in n["id"]]
    print(f"Total FRU nodes in full data: {len(total_fru)}")
    if total_fru:
        groups_of_fru = set(n["group"] for n in total_fru)
        print(f"Groups of all FRU nodes: {groups_of_fru}")

test_filter()
