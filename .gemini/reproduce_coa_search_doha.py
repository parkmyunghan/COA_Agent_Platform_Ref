
import sys
import os
import pandas as pd
import rdflib

# Add project root to path
sys.path.append(r"C:\POC\COA_Agent_Platform")
sys.path.append(r"C:\POC\COA_Agent_Platform\core_pipeline")

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.coa_engine.coa_generator_enhanced import EnhancedCOAGenerator
from core_pipeline.data_manager import DataManager

config = {
    "ontology_path": r"C:\POC\COA_Agent_Platform\data_lake",
    "metadata_path": r"C:\POC\COA_Agent_Platform\metadata",
    "data_lake_path": r"C:\POC\COA_Agent_Platform\data_lake",
    "output_path": r"C:\POC\COA_Agent_Platform\outputs"
}

dm = DataManager(config)
om = EnhancedOntologyManager(config)
om.build_from_data(dm.load_all())

generator = EnhancedCOAGenerator(om, None, None)

print("--- Searching COAs for '도하' ---")
results = generator._search_coas_from_ontology("도하")
print(f"Found {len(results)} results")
for r in results[:5]:
    print(f"  {r}")
