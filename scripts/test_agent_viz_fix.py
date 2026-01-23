import sys
import os
from unittest.mock import MagicMock

# 경로 설정
sys.path.insert(0, os.getcwd())

import logging
logging.basicConfig(level=logging.INFO)

def test_visualization_fix():
    from api.routers.agent import convert_agent_result_to_coa_response
    
    # Mock data mimicking a dynamic scenario that lacks axis_states
    agent_result = {
        "agent": "EnhancedDefenseCOAAgent",
        "status": "completed",
        "situation_id": "THR001", # Existing threat in data_lake
        "situation_info": {
            "threat_id": "THR001",
            "임무ID": "MSN001",
            "location_cell_id": "TERR001"
        },
        "recommendations": [
            {
                "coa_id": "COA_1",
                "coa_name": "Test COA",
                "score": 0.8,
                "participating_units": "제1보병여단, 제2보병여단"
            }
        ]
    }
    
    print("Testing convert_agent_result_to_coa_response with missing axis_states...")
    result = convert_agent_result_to_coa_response(agent_result)
    
    # Check if axis_states were reconstructed
    axis_states = result.get("axis_states", [])
    print(f"Reconstructed axis_states count: {len(axis_states)}")
    
    if len(axis_states) > 0:
        print("✅ Success: axis_states reconstructed.")
        for axis in axis_states:
            if 'coordinates' in axis:
                print(f"  - Axis {axis.get('axis_id')} coordinates found.")
            else:
                print(f"  - ❌ Axis {axis.get('axis_id')} coordinates MISSING.")
    else:
        print("❌ Failure: axis_states NOT reconstructed.")

    # Check for operational_path in recommendations
    for coa in result.get("coas", []):
        viz_data = coa.get("visualization_data", {})
        if viz_data and viz_data.get("operational_path"):
            print(f"✅ Success: Operational path generated for {coa['coa_id']}.")
        else:
            print(f"❌ Failure: Operational path MISSING for {coa['coa_id']}.")
            
    # Check for unit_positions
    for coa in result.get("coas", []):
        if coa.get("unit_positions"):
            print(f"✅ Success: Unit positions generated for {coa['coa_id']}.")
        else:
            print(f"❌ Failure: Unit positions MISSING for {coa['coa_id']}.")

if __name__ == "__main__":
    test_visualization_fix()
