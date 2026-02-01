import urllib.request
import json

def run_query(query):
    url = "http://localhost:8000/api/v1/ontology/sparql"
    data = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except Exception as e:
        return {"error": str(e)}

# Check types of nodes containing '부대'
q1 = """
PREFIX def: <http://coa-agent-platform.org/ontology#>
SELECT DISTINCT ?type 
WHERE { 
  ?s a ?type . 
  FILTER(CONTAINS(STR(?s), "부대")) 
}
"""

print("Types of nodes containing '부대':")
print(json.dumps(run_query(q1), indent=2, ensure_ascii=False))

# Check groups available in /graph
def get_graph_stats():
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

print("\nGroups in graph data:")
print(json.dumps(get_graph_stats(), indent=2, ensure_ascii=False))
