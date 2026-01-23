import pandas as pd
import os

path = r"c:\POC\COA_Agent_Platform_Ref\data_lake\아군가용자산.xlsx"

try:
    df = pd.read_excel(path)
    print(f"Loaded {len(df)} rows.")
    
    # Search for keywords
    keywords = ["헬기", "특수", "공격"]
    for kw in keywords:
        mask = df['자산명'].str.contains(kw, na=False)
        if mask.any():
            print(f"\n--- Found '{kw}' ---")
            print(df[mask][['자산ID', '자산명', '자산종류', '수량']])
        else:
            print(f"\nNo match for '{kw}'")
            
    # Find max ID to know what to append next
    if '자산ID' in df.columns:
        # filter ASTxxx
        ids = df['자산ID'].dropna()
        max_id = "AST000"
        for i in ids:
            if i > max_id:
                max_id = i
        print(f"\nMax Asset ID: {max_id}")

except Exception as e:
    print(f"Error: {e}")
