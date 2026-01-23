
import rdflib
import os

ontology_path = r"C:\POC\COA_Agent_Platform\data_lake\ontology.ttl"
if not os.path.exists(ontology_path):
    # Try another path if exists
    potential_path = r"C:\POC\COA_Agent_Platform\ontology\ontology.ttl"
    if os.path.exists(potential_path):
        ontology_path = potential_path

g = rdflib.Graph()
g.parse(ontology_path, format="turtle")

NS = rdflib.Namespace("http://coa-agent-platform.org/ontology#")
RDF = rdflib.RDF

print("--- DefenseCOA instances ---")
for s in g.subjects(RDF.type, NS.DefenseCOA):
    print(f"ID: {str(s).split('#')[-1]}")
    for label in g.objects(s, rdflib.RDFS.label):
        print(f"  Label: {label}")
    for threat in g.objects(s, NS.적합위협유형):
        print(f"  Threat: {threat}")

print("\n--- All COA types count ---")
coa_types = ["DefenseCOA", "OffensiveCOA", "CounterAttackCOA", "PreemptiveCOA", "DeterrenceCOA", "ManeuverCOA", "InformationOpsCOA"]
for ct in coa_types:
    count = len(list(g.subjects(RDF.type, NS[ct])))
    print(f"{ct}: {count}")
