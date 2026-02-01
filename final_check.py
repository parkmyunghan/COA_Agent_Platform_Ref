import urllib.request
import json

def get_groups():
    url = "http://localhost:8000/api/v1/ontology/graph?mode=instances"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
            groups = {}
            for n in data.get("nodes", []):
                g = n.get("group", "Unknown")
                groups[g] = groups.get(g, 0) + 1
            return groups
    except Exception as e:
        return {"error": str(e)}

print(json.dumps(get_groups(), indent=2, ensure_ascii=False))
