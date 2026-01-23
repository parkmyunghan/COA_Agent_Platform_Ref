import pandas as pd
import os

path = r"c:\POC\COA_Agent_Platform_Ref\data_lake\아군부대현황.xlsx"
output_path = r"c:\POC\COA_Agent_Platform_Ref\debug_unit_dump.txt"

try:
    df = pd.read_excel(path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(df.to_string())
    print(f"Dumped {len(df)} rows to {output_path}")
except Exception as e:
    print(f"Error: {e}")
