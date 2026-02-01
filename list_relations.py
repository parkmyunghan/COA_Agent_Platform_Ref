import urllib.request
import json

def list_relations():
    url = "http://localhost:8000/api/v1/ontology/graph?mode=instances"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
            links = data.get("links", [])
            rels = list(set(l.get("relation") for l in links if l.get("relation")))
            return sorted(rels)
    except Exception as e:
        return [f"Error: {e}"]

relations = list_relations()
with open("available_relations.json", "w", encoding="utf-8") as f:
    json.dump(relations, f, indent=2, ensure_ascii=False)

print(f"Extracted {len(relations)} relations.")
