
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.plugins.sparql import prepareQuery

g = Graph()
ns = Namespace("http://example.org/")
g.add((URIRef(ns.coa1), URIRef(ns.type), Literal("집결징후")))
g.add((URIRef(ns.coa2), URIRef(ns.type), Literal("적 집결")))

threat_type = "집결징후"

query = f"""
PREFIX ex: <http://example.org/>
SELECT ?s
WHERE {{
    ?s ex:type ?type .
    FILTER (regex(str(?type), "{threat_type}", "i"))
}}
"""

print(f"Querying for '{threat_type}'...")
qres = g.query(query)
count = 0
for row in qres:
    print(f"Match: {row.s}")
    count += 1

if count == 0:
    print("No match found with regex.")
else:
    print(f"Found {count} matches.")
