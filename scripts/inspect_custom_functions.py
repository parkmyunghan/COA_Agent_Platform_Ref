
import rdflib
from rdflib.plugins.sparql import operators

print("Inspecting _CUSTOM_FUNCTIONS:")
for k, v in operators._CUSTOM_FUNCTIONS.items():
    print(f"  {k}: {v}")
    if hasattr(v, 'func'):
        print(f"    Implementation function: {v.func}")
