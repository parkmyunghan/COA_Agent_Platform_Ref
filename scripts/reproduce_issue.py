
# scripts/reproduce_issue.py
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

API_URL = "http://localhost:8000/api/v1/coa/generate-situation-summary"

payload = {
  "threat_id": "SCENARIO_SCENARIO_1_TEST", 
  "threat_data": {
    "threat_id": "SCENARIO_SCENARIO_1_TEST",
    "threat_type_code": "정찰", 
    "threat_level": 0.75,
    "location_cell_id": "경계지역", # Not a TERR code
    "related_axis_id": "AXIS01",
    "occurrence_time": "2026-01-19T19:43:00",
    "threat_type_original": "미상",
    "enemy_unit_original": "미상",
    "raw_report_text": "경계지역 일대 미상 위협(정찰) 식별"
  },
  "user_params": {
    "approach_mode": "mission_centered"
  }
}

def test_api():
    print(f"Sending request to {API_URL}...")
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        summary = data.get("situation_summary")
        source = data.get("situation_summary_source")
        
        print("\n--- API Response ---")
        print(f"Source: {source}")
        print(f"Summary: {summary}")
        print("--------------------")
        
        # Check for expected Natural Language terms
        failures = []
        if "THR_TYPE_007" in summary and "식별된 위협" not in summary and "미상 (THR_TYPE_007)" in summary:
             failures.append("Threat Type not resolved (Still '미상 (THR_TYPE_007)')")
             
        if "TERR007" in summary and "(" not in summary.split("TERR007")[1]:
             # Simple check: if TERR007 is there but not followed by parens of ID, or preceded by Name
             # Actually, my format is "Name(ID)". So "TERR007" will be there.
             # But if it's JUST "TERR007 일대", then fail.
             if "TERR007 일대" in summary and "산악" not in summary and "지형" not in summary: 
                  failures.append("Location Name not resolved")

        if "AXIS06" in summary and "축선" not in summary.split("AXIS06")[0]:
             failures.append("Axis Name not resolved")
             
        if failures:
            print("\n❌ FAILED Check:")
            for f in failures:
                print(f" - {f}")
        else:
            print("\n✅ PASSED Check: Natural language terms seem present.")
            
    except Exception as e:
        print(f"API Request Failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    test_api()
