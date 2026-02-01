
import sys
import os
sys.path.append(os.getcwd())

try:
    from api.utils.code_label_mapper import get_mapper
    mapper = get_mapper()
    
    print("--- Final Mapping Verification ---")
    print(f"TERR007: {mapper.get_terrain_label('TERR007')}")
    print(f"THR_TYPE_007: {mapper.get_threat_type_label('THR_TYPE_007')}")
    print(f"AXIS06: {mapper.get_axis_label('AXIS06')}")
    
    # Test format_with_code
    print(f"Formatted TERR007: {mapper.format_with_code(mapper.get_terrain_label('TERR007'), 'TERR007')}")
    
except Exception as e:
    print(f"Error during verification: {e}")
    import traceback
    traceback.print_exc()
