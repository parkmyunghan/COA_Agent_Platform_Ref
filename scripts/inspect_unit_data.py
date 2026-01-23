import pandas as pd
import os

data_dir = r"c:\POC\COA_Agent_Platform_Ref\data_lake"
files = ["아군부대현황.xlsx", "아군가용자산.xlsx"]

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

for f in files:
    path = os.path.join(data_dir, f)
    if os.path.exists(path):
        try:
            print(f"--- {f} ---")
            df = pd.read_excel(path)
            # Check for specific IDs
            ids_to_check = ["FR_UNIT_005", "FR_UNIT_006", "AST022", "AST023"]
            found_any = False
            
            for col in df.columns:
                if "ID" in col:
                    # check if any target ID is in this column
                    mask = df[col].isin(ids_to_check)
                    if mask.any():
                        print(f"Found target IDs in column '{col}':")
                        print(df[mask])
                        found_any = True
            
            if not found_any:
                print("No target IDs (FR_UNIT_005, FR_UNIT_006, AST003, AST004) found in this file.")
            
            # Print last 5 rows just in case
            print("\nLast 5 rows:")
            print(df.tail(5))
            print("\n")
        except Exception as e:
            print(f"Error reading {f}: {e}")
    else:
        print(f"File not found: {path}")
