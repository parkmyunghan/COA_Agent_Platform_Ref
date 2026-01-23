import pandas as pd
import os

def fix_axis_data():
    axis_path = "data_lake/전장축선.xlsx"
    df = pd.read_excel(axis_path)
    
    # 1. Update Names based on Geographical logic (West vs East)
    # AXIS01 (TERR001->TERR005; Lon 127.1->127.0) -> Dongbu Main
    # AXIS03 (TERR007->TERR009; Lon 126.7->126.75) -> Seobu Blocking
    # Matches current naming convention where 127 is "East" of 126.
    
    # Fix description artifacts (garbage text)
    df['축선설명'] = df['축선설명'].str.replace('First row sample:', '').str.strip()
    
    # Standardize Major Terrain List (ensure consistency)
    def update_via_points(row):
        start = row['시작지형셀ID']
        end = row['종단지형셀ID']
        via = str(row['주요지형셀목록'])
        
        # Ensure start and end are mentioned if not already
        points = [p.strip() for p in via.split(',') if p.strip()]
        if start not in points: points.insert(0, start)
        if end not in points: points.append(end)
        return ','.join(points)

    df['주요지형셀목록'] = df.apply(update_via_points, axis=1)
    
    # Specific Mismatch Fix: If a name says 'West' but Lon is > 127.5 (and vice versa)
    # Based on our TERR018 (East, 128.0)
    # Let's check AXIS08: Seobu Supporting (TERR006->TERR008; Lon 126.8->126.8) -> Seobu is correct.
    
    # Save the cleaned data
    df.to_excel(axis_path, index=False)
    print("Successfully cleaned axis data.")

if __name__ == "__main__":
    fix_axis_data()
