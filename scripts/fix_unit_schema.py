import pandas as pd
import os

data_dir = r"c:\POC\COA_Agent_Platform_Ref\data_lake"
unit_file = os.path.join(data_dir, "아군부대현황.xlsx")
asset_file = os.path.join(data_dir, "아군가용자산.xlsx")

# 1. Fix Unit Schema
try:
    df_unit = pd.read_excel(unit_file)
    print(f"Loaded Unit File: {len(df_unit)} rows")
    
    # Check for mismatch columns
    if '현재위치_지형셀ID' in df_unit.columns and '배치지형셀ID' in df_unit.columns:
        print("Fixing 배치지형셀ID...")
        df_unit['배치지형셀ID'] = df_unit['배치지형셀ID'].fillna(df_unit['현재위치_지형셀ID'])
        df_unit.drop(columns=['현재위치_지형셀ID'], inplace=True)
        
    if '주둔지역_축선ID' in df_unit.columns and '배치축선ID' in df_unit.columns:
        print("Fixing 배치축선ID...")
        df_unit['배치축선ID'] = df_unit['배치축선ID'].fillna(df_unit['주둔지역_축선ID'])
        df_unit.drop(columns=['주둔지역_축선ID'], inplace=True)
        
    # Save back
    df_unit.to_excel(unit_file, index=False)
    print("Saved fixed Unit File.")
except Exception as e:
    print(f"Error fixing Unit file: {e}")

# 2. Inspect Asset File for AST003, AST004
try:
    df_asset = pd.read_excel(asset_file)
    print(f"\nLoaded Asset File: {len(df_asset)} rows")
    
    targets = ["AST003", "AST004"]
    if "자산ID" in df_asset.columns:
        mask = df_asset["자산ID"].isin(targets)
        if mask.any():
            print("Found target assets:")
            print(df_asset[mask])
        else:
            print("Target assets (AST003, AST004) NOT found.")
            
            # If not found, append them now?
            # My previous script failed because it *thought* they existed?
            # Or maybe I misread the previous output.
            # Let's verify and if missing, I can propose to add them again.
    else:
        print("Column '자산ID' not found in Asset file.")

except Exception as e:
    print(f"Error inspecting Asset file: {e}")
