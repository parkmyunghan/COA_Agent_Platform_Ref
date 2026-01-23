import pandas as pd
import os

data_dir = r"c:\POC\COA_Agent_Platform_Ref\data_lake"
unit_file = os.path.join(data_dir, "아군부대현황.xlsx")
asset_file = os.path.join(data_dir, "아군가용자산.xlsx")

# define new units
new_units = [
    {
        "아군부대ID": "FR_UNIT_005", # Assuming FR_UNIT series or similar, checking existing IDs would be safer but this is a reasonable start
        "부대명": "1항공여단",
        "제대": "여단",
        "병종": "항공",
        "전투력지수": 90,
        "현재위치_지형셀ID": "TERR002",
        "주둔지역_축선ID": "AXIS06",
        "상태": "가용",
        "기동속도": 100,
        "탐지범위": 20,
        "부대부호(SIDC)": "SFG*H-----*****" # Friendly Aviation
    },
    {
        "아군부대ID": "FR_UNIT_006",
        "부대명": "특수작전팀",
        "제대": "팀",
        "병종": "특수전",
        "전투력지수": 85,
        "현재위치_지형셀ID": "TERR005",
        "주둔지역_축선ID": "AXIS01",
        "상태": "가용",
        "기동속도": 40,
        "탐지범위": 10,
        "부대부호(SIDC)": "SFG*U-----*****" # Friendly SOF
    }
]

# define new assets
new_assets = [
    {
        "자산ID": "AST022", 
        "자산명": "공격헬기",
        "자산종류": "항공기",
        "수량": 6,
        "배치지형셀ID": "TERR002",
        "가용상태": "가용"
    },
    {
        "자산ID": "AST023",
        "자산명": "특수전팀",
        "자산종류": "인원",
        "수량": 4,
        "배치지형셀ID": "TERR005",
        "가용상태": "가용"
    }
]


def append_to_excel(file_path, new_data):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        df = pd.read_excel(file_path)
        existing_ids = set()
        
        # Determine ID column
        id_col = None
        if "아군부대ID" in df.columns:
            id_col = "아군부대ID"
        elif "자산ID" in df.columns:
            id_col = "자산ID"
        
        if id_col:
            existing_ids = set(df[id_col].dropna().astype(str))
        
        new_df = pd.DataFrame(new_data)
        
        # Filter duplicates based on ID
        if id_col:
            new_df = new_df[~new_df[id_col].astype(str).isin(existing_ids)]
            
        if new_df.empty:
            print(f"No new data to add to {os.path.basename(file_path)} (IDs likely exist).")
        else:
            # Align columns: only include columns that exist in target, fill missing with defaults if needed (for simplicity just match names)
            # Actually, standard pandas concat handles column alignment, filling NaNs
            
            updated_df = pd.concat([df, new_df], ignore_index=True)
            updated_df.to_excel(file_path, index=False)
            print(f"Added {len(new_df)} rows to {os.path.basename(file_path)}")
            
    except Exception as e:
        print(f"Error updating {file_path}: {e}")

# Execute updates
# print("--- Updating Unit Data ---")
# append_to_excel(unit_file, new_units)
print("\n--- Updating Asset Data ---")
append_to_excel(asset_file, new_assets)
