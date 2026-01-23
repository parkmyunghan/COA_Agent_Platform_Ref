import pandas as pd
import os

data_dir = r"c:\POC\COA_Agent_Platform_Ref\data_lake"
files = ["위협상황.xlsx", "전장축선.xlsx"]

# Display all columns
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

for f in files:
    path = os.path.join(data_dir, f)
    if os.path.exists(path):
        try:
            print(f"--- {f} ---")
            df = pd.read_excel(path, nrows=2)
            print(f"Columns: {list(df.columns)}")
            print("First row data:")
            print(df.iloc[0])
            print("\n")
        except Exception as e:
            print(f"Error reading {f}: {e}")
    else:
        print(f"File not found: {path}")
