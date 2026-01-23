import pandas as pd
from pathlib import Path
import os

terrain_paths = [
    Path("data_lake/지형셀.xlsx"),
    Path(os.getcwd()) / "data_lake" / "지형셀.xlsx",
    Path("c:/POC/COA_Agent_Platform_Ref/data_lake/지형셀.xlsx")
]

for p in terrain_paths:
    if p.exists():
        print(f"Found file at: {p}")
        try:
            df = pd.read_excel(p)
            print("Columns:", df.columns.tolist())
            if len(df) > 0:
                print("First row sample:", df.iloc[0].to_dict())
            break
        except Exception as e:
            print(f"Error reading {p}: {e}")
    else:
        print(f"File not found at: {p}")
