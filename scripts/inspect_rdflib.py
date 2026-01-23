
import rdflib
from rdflib.plugins.sparql import operators

print(f"rdflib version: {rdflib.__version__}")

# Try to find where custom functions are stored in this version
try:
    from rdflib.plugins.sparql.operators import CUSTOM_FUNCTIONS
    print("CUSTOM_FUNCTIONS found in operators.")
    for k, v in CUSTOM_FUNCTIONS.items():
        print(f"  {k}: {v}")
except ImportError:
    print("CUSTOM_FUNCTIONS NOT found in operators.")
    # In newer rdflib it might be in rdflib.plugins.sparql.function
    try:
        from rdflib.plugins.sparql import function
        print("Function registry found in rdflib.plugins.sparql.function")
        # In newer versions, it's often a dict called 'custom_functions' or registered via decorators
    except ImportError:
        print("Function registry NOT found in rdflib.plugins.sparql.function")

# Let's inspect 'operators' module members
print("\nOperators module members:")
for name in dir(operators):
    if not name.startswith("__"):
        print(f"  {name}")
