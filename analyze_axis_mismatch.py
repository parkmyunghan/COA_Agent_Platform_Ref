import pandas as pd
import os

def analyze_axes():
    axis_path = "data_lake/전장축선.xlsx"
    terrain_path = "data_lake/지형셀.xlsx"
    
    df_axis = pd.read_excel(axis_path)
    df_terrain = pd.read_excel(terrain_path)
    
    # Create terrain lookup
    terrain_map = df_terrain.set_index('지형셀ID').to_dict('index')
    
    print(f"{'ID':<8} | {'축선명':<15} | {'시작(S_ID/Lon)':<20} | {'종단(E_ID/Lon)':<20} | {'상태'}")
    print("-" * 100)
    
    for _, row in df_axis.iterrows():
        a_id = row['축선ID']
        a_name = row['축선명']
        s_id = row['시작지형셀ID']
        e_id = row['종단지형셀ID']
        
        s_data = terrain_map.get(s_id, {})
        e_data = terrain_map.get(e_id, {})
        
        s_lon = float(str(s_data.get('좌표정보', '0,0')).split(',')[0])
        e_lon = float(str(e_data.get('좌표정보', '0,0')).split(',')[0])
        
        status = "OK"
        # Heuristic: West ~126.x, Central ~127.x, East ~128.x
        if '서부' in a_name and (s_lon > 127.3 or e_lon > 127.3):
            status = "MISMATCH (West name but East/Central coord)"
        elif '동부' in a_name and (s_lon < 127.3 or e_lon < 127.3):
            status = "MISMATCH (East name but West/Central coord)"
            
        print(f"{a_id:<8} | {a_name:<15} | {s_id}({s_lon:.2f}) | {e_id}({e_lon:.2f}) | {status}")

if __name__ == "__main__":
    analyze_axes()
