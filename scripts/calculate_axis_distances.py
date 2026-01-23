
import pandas as pd
from pathlib import Path
import math
import shutil

# Haversine Formula for distance between two points (lat/lon)
def haversine(coord1, coord2):
    # coord format: "lon, lat" string
    try:
        lon1, lat1 = map(float, coord1.split(','))
        lon2, lat2 = map(float, coord2.split(','))
    except (ValueError, AttributeError):
        return 0.0

    R = 6371.0 # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def calculate_distances():
    data_lake = Path("data_lake")
    axis_file = data_lake / "전장축선.xlsx"
    terrain_file = data_lake / "지형셀.xlsx"
    backup_file = data_lake / "전장축선.xlsx.bak_dist"
    
    if not axis_file.exists() or not terrain_file.exists():
        print("[ERROR] Required files not found.")
        return

    # Backup
    shutil.copy2(axis_file, backup_file)
    print(f"[INFO] Created backup: {backup_file}")

    try:
        # Load Data
        df_axis = pd.read_excel(axis_file)
        df_terrain = pd.read_excel(terrain_file)
        
        # Create Terrain Coordinate Map
        # coord format in excel: "127.1, 38.1"
        terrain_map = {}
        for _, row in df_terrain.iterrows():
            if pd.notna(row['좌표정보']):
                terrain_map[str(row['지형셀ID']).strip()] = str(row['좌표정보']).strip()
        
        print(f"[INFO] Loaded {len(terrain_map)} terrain coordinates.")
        
        # Calculate Distance for each Axis
        updates = []
        for idx, row in df_axis.iterrows():
            axis_id = row['축선ID']
            cell_list_str = row['주요지형셀목록']
            
            if pd.isna(cell_list_str):
                updates.append(None)
                continue
                
            cells = [c.strip() for c in str(cell_list_str).split(',') if c.strip()]
            
            if len(cells) < 2:
                # If only 1 cell, distance is 0 or undefined. Let's say 0.
                # Or maybe calculate diameter? Let's verify with Start/End cells if list is empty.
                # But task assumes `주요지형셀목록` defines the route.
                updates.append(0.0)
                continue
            
            total_dist = 0.0
            valid_segment_count = 0
            
            for i in range(len(cells) - 1):
                c1 = cells[i]
                c2 = cells[i+1]
                
                coord1 = terrain_map.get(c1)
                coord2 = terrain_map.get(c2)
                
                if coord1 and coord2:
                    dist = haversine(coord1, coord2)
                    total_dist += dist
                    valid_segment_count += 1
                else:
                    print(f"[WARN] Axis {axis_id}: Missing coords for {c1} or {c2}")
            
            # Round to 2 decimals
            updates.append(round(total_dist, 2))
            print(f"  - {axis_id}: {len(cells)} cells, {total_dist:.2f} km")
            
        # Update DataFrame
        df_axis['거리_km'] = updates
        
        # Save
        df_axis.to_excel(axis_file, index=False)
        print(f"[INFO] Updated distances in {axis_file}")
        
    except Exception as e:
        print(f"[ERROR] Calculation failed: {e}")
        # Restore
        shutil.copy2(backup_file, axis_file)

if __name__ == "__main__":
    calculate_distances()
