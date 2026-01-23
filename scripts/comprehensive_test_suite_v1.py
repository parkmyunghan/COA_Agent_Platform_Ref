import requests
import json
import pandas as pd
import time
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

def test_threat_coas(threat_ids: List[str]):
    results = []
    print(f"\n--- Testing 10 Threat Situations ---")
    for tid in threat_ids:
        print(f"Testing {tid}...")
        try:
            # Note: The actual endpoint might be /coa/recommend or similar
            payload = {"threat_id": tid, "mission_id": "MSN001"}
            response = requests.post(f"{BASE_URL}/coa/recommend", json=payload)
            if response.status_code == 200:
                data = response.json()
                coas = data.get("coas", [])
                viz_count = sum(1 for c in coas if c.get("visualization_data"))
                results.append({"id": tid, "status": "PASS", "coas": len(coas), "viz": viz_count})
            else:
                results.append({"id": tid, "status": "FAIL", "error": f"HTTP {response.status_code}"})
        except Exception as e:
            results.append({"id": tid, "status": "ERROR", "error": str(e)})
    return results

def test_scenarios(scenario_ids: List[str]):
    results = []
    print(f"\n--- Testing 10 Scenarios via Agent ---")
    for sid in scenario_ids:
        print(f"Testing {sid}...")
        try:
            # The agent execution flow usually takes situation_id and situation_info
            payload = {
                "situation_id": sid,
                "situation_info": {"situation_id": sid, "id": sid},
                "agent_id": "defense_coa_agent"
            }
            response = requests.post(f"{BASE_URL}/agent/execute", json=payload)
            if response.status_code == 200:
                data = response.json()
                coas = data.get("coas", [])
                results.append({"id": sid, "status": "PASS", "coas": len(coas)})
            else:
                results.append({"id": sid, "status": "FAIL", "error": f"HTTP {response.status_code}"})
        except Exception as e:
            results.append({"id": sid, "status": "ERROR", "error": str(e)})
    return results

# Add SITREP and Manual Input tests...

if __name__ == "__main__":
    # Load IDs from actual data if needed, or hardcode for now
    # ...
    print("Comprehensive Test Suite Initialized.")
