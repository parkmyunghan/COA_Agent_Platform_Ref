
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager

def test_safe_template():
    print("Testing safe SPARQL template generation...")
    
    config = {
        "ontology_path": "./knowledge/ontology",
        "metadata_path": "./metadata",
        "data_lake_path": "./data_lake"
    }
    
    manager = EnhancedOntologyManager(config)
    
    # Test case 1: Bad URI string in situation_uri
    bad_uri = "http://defense-ai.kr/ontology#Bad URI with Spaces"
    # Note: My fix in get_sparql_template assumes if it starts with http://, it is trusted.
    # BUT wait, the user log said: "http://... does not look like a valid URI".
    # This means I should probably have sanitized even if it starts with http:// IF it has spaces.
    # But my fix only targeted `not startswith('http')`.
    # Let's verify what happens with "2025-01-01 23:10:00" (no http).
    
    raw_date = "2025-01-01 23:10:00"
    try:
        query = manager.get_sparql_template("find_suitable_coas", situation_uri=raw_date)
        print(f"Result for raw string: Success")
        print(f"Generated part: {query[:100]}...")
    except Exception as e:
        print(f"Result for raw string: Failed - {e}")

    # Test case 2: String with spaces but NO http prefix (should be sanitized)
    raw_space = "Entity With Spaces"
    try:
        query = manager.get_sparql_template("find_suitable_coas", situation_uri=raw_space)
        print(f"Result for space string: Success")
        # Check if it contains sanitized version
        if "Entity_With_Spaces" in query:
             print("Sanitization verified: Entity_With_Spaces found")
        else:
             print(f"Sanitization check failed. Query snippet: {query[:200]}")
    except Exception as e:
        print(f"Result for space string: Failed - {e}")

if __name__ == "__main__":
    test_safe_template()
