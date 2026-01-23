import pandas as pd
import numpy as np
import os

def fix_coordinates():
    file_path = "data_lake/지형셀.xlsx"
    if not os.path.exists(file_path):
        print("File not found.")
        return

    df = pd.read_excel(file_path)
    print(f"Loaded {len(df)} rows from {file_path}")
    
    # Identify coordinate column
    coord_col = [c for c in df.columns if '좌표' in str(c)][0]
    print(f"Using column: {coord_col}")

    fixed_count = 0
    mismatch_count = 0

    # Reference coordinate ranges (approximate)
    geo_ranges = {
        '평양': {'lon': (125.5, 126.0), 'lat': (38.8, 39.2)},
        '개성': {'lon': (126.3, 126.7), 'lat': (37.8, 38.1)},
        '파주': {'lon': (126.6, 126.9), 'lat': (37.7, 37.9)},
        '문산': {'lon': (126.7, 126.8), 'lat': (37.8, 37.9)},
        '철원': {'lon': (127.1, 127.5), 'lat': (38.0, 38.4)},
        '동두천': {'lon': (127.0, 127.1), 'lat': (37.8, 38.0)},
        '연천': {'lon': (127.0, 127.2), 'lat': (38.0, 38.2)},
        '원산': {'lon': (127.3, 127.6), 'lat': (39.0, 39.3)},
        '의정부': {'lon': (127.0, 127.1), 'lat': (37.7, 37.8)},
        '김포': {'lon': (126.4, 126.7), 'lat': (37.5, 37.7)},
        '양주': {'lon': (126.9, 127.1), 'lat': (37.7, 37.9)},
        '포천': {'lon': (127.1, 127.3), 'lat': (37.8, 38.0)},
    }

    def process_row(row):
        nonlocal fixed_count, mismatch_count
        val = str(row[coord_col])
        if ',' not in val or 'nan' in val.lower():
            return row[coord_col]

        try:
            parts = [float(p.strip()) for p in val.split(',')]
            if len(parts) != 2:
                return val
            
            v1, v2 = parts
            
            # 1. Standardize Order (Lon, Lat)
            # Longitude in Korea is ~124-131, Latitude is ~33-43
            lon, lat = (v1, v2) if v1 > 100 else (v2, v1)
            
            # Check if order was swapped
            if v1 < 100:
                fixed_count += 1
            
            # 2. Check Geographical Mismatch
            name = str(row['지형명'])
            for key, ranges in geo_ranges.items():
                if key in name:
                    lon_range = ranges['lon']
                    lat_range = ranges['lat']
                    
                    if not (lon_range[0] <= lon <= lon_range[1] and lat_range[0] <= lat <= lat_range[1]):
                        print(f"Mismatch detected for {name} ({row['지형셀ID']}): {lon}, {lat} -> correcting to center of {key}")
                        lon = (lon_range[0] + lon_range[1]) / 2
                        lat = (lat_range[0] + lat_range[1]) / 2
                        mismatch_count += 1
                        break
            
            # Special case for TERR008 (하천둔치) related to AXIS04 (Western)
            # If TERR008 is in the East (128.5) but AXIS04 is Western, and user points it out:
            if row['지형셀ID'] == 'TERR008' and lon > 128:
                print(f"Special Case Fix: TERR008 ({name}) has East coord {lon}, but belongs to Western path. Correcting to West.")
                lon = 126.8 # Near Munsan/Paju area
                mismatch_count += 1

            return f"{lon:.4f}, {lat:.4f}"
            
        except Exception as e:
            return val

    df[coord_col] = df.apply(process_row, axis=1)
    
    # Save back to Excel
    df.to_excel(file_path, index=False)
    print(f"Successfully processed {len(df)} rows.")
    print(f"Standardized Order (Lat/Lon swap): {fixed_count} cases")
    print(f"Geographical Mismatches Corrected: {mismatch_count} cases")

if __name__ == "__main__":
    fix_coordinates()
