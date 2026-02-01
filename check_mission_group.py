import urllib.request
import json

def check_group():
    url = "http://localhost:8000/api/v1/ontology/graph?mode=instances"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
            nodes = data.get("nodes", [])
            
            mission_nodes = [n for n in nodes if n['group'] == '임무정보']
            print(f"Total Nodes: {len(nodes)}")
            print(f"MissionINFO Nodes: {len(mission_nodes)}")
            
            if mission_nodes:
                print(f"Sample: {mission_nodes[0]}")
            else:
                print("CRITICAL: No '임무정보' nodes found!")
                
                # Check for ANY Mission-like nodes (e.g. by label or ID)
                potential = [n for n in nodes if "MSN" in n['id'] or "임무" in n['label']]
                print(f"Potential Mission Nodes (by ID/Label): {len(potential)}")
                if potential:
                    print(f"Sample Potential: {potential[0]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_group()
