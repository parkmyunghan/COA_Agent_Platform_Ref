
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_failures():
    # 1. THR001
    print("\n>>> [RETEST] THR001")
    payload = {"threat_id": "THR001", "mission_id": "MSN001"}
    try:
        response = requests.post(f"{BASE_URL}/coa/generate", json=payload, timeout=120)
        if response.status_code == 200:
            print("✅ THR001 PASS")
        else:
            print(f"❌ THR001 FAIL: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ THR001 ERROR: {e}")

    # 2. MANUAL_01
    print("\n>>> [RETEST] MANUAL_01")
    payload = {
        "situation_id": "MANUAL_01",
        "situation_info": {
            "위협유형": "지상위협",
            "위협수준": "High",
            "발생장소": "전방 사격장 부근"
        },
        "agent_class_path": "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent"
    }
    try:
        response = requests.post(f"{BASE_URL}/agent/execute", json=payload, timeout=120)
        if response.status_code == 200:
            print("✅ MANUAL_01 PASS")
        else:
            print(f"❌ MANUAL_01 FAIL: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ MANUAL_01 ERROR: {e}")

if __name__ == "__main__":
    test_failures()
