import pandas as pd
from pathlib import Path
import os

paths = [
    Path("data_lake/전장축선.xlsx"),
    Path(os.getcwd()) / "data_lake" / "전장축선.xlsx",
]

for p in paths:
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
