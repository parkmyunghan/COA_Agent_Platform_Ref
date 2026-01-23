
import requests
import json
import sys

def test_sparql_api():
    url = "http://localhost:8000/api/v1/ontology/sparql"
    # Exact query from frontend
    query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?class WHERE { 
  ?class a owl:Class 
} LIMIT 50"""
    
    payload = {"query": query}
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Sending POST request to {url}")
        print(f"Query: {query}")
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Success! Result count: {len(response.json().get('results', []))}")
            # print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print("Failed!")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sparql_api()
