
import pandas as pd
from pathlib import Path

data_lake = Path("data_lake")

def dump_axis():
    file_path = data_lake / "전장축선.xlsx"
    if file_path.exists():
        df = pd.read_excel(file_path)
        print("\n--- 전장축선.xlsx (Full) ---")
        print(df[['축선ID', '축선명']].to_string())
    else:
        print("전장축선.xlsx not found")

dump_axis()
