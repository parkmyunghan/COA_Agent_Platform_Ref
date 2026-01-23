import sys
import os
from unittest.mock import MagicMock

# 경로 설정
sys.path.insert(0, os.getcwd())

import logging
logging.basicConfig(level=logging.INFO)

def test_thr006_conversion():
    from api.routers.agent import convert_agent_result_to_coa_response
    
    # Mock data based on actual THR006 output
    agent_result = {
        "agent": "EnhancedDefenseCOAAgent",
        "status": "completed",
        "situation_id": "THR006",
        "situation_info": {
            "threat_id": "THR006",
            "임무ID": "MSN001"
        },
        "recommendations": [
            {
                "coa_id": "COA_1",
                "coa_name": "통합 방공망 가동",
                "participating_units": "방공대대, 휴대용대공미사일반",
                "reason": "현재 작전 구역에서 발생한 공중위협에 적극 대응하기 위해 방공 미사일을 가동합니다.",
                "reasoning": {"primary_axis_id": None}
            }
        ]
    }
    
    print("Testing conversion for THR006...")
    result = convert_agent_result_to_coa_response(agent_result)
    
    # Check if axis_states were reconstructed
    axis_states = result.get("axis_states", [])
    print(f"Reconstructed axis_states count: {len(axis_states)}")
    
    found_axis_id = None
    if len(axis_states) > 0:
        found_axis_id = axis_states[0].get("axis_id")
        print(f"✅ Success: axis_states reconstructed. First axis: {found_axis_id}")
    else:
        print("❌ Failure: axis_states NOT reconstructed.")

    # Check for operational_path and description in recommendations
    for coa in result.get("coas", []):
        viz_data = coa.get("visualization_data", {})
        if viz_data and viz_data.get("operational_path"):
            print(f"✅ Success: Operational path generated for {coa['coa_id']}.")
        else:
            print(f"❌ Failure: Operational path MISSING for {coa['coa_id']}")
            
        description = coa.get("description")
        if description and description != "":
            print(f"✅ Success: Description populated for {coa['coa_id']}: {description[:30]}...")
        else:
            print(f"❌ Failure: Description is EMPTY for {coa['coa_id']}")

if __name__ == "__main__":
    test_thr006_conversion()
