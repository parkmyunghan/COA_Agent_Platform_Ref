
import pandas as pd
import os

data_dir = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake"

def check():
    master_path = os.path.join(data_dir, "위협유형_마스터.xlsx")
    df = pd.read_excel(master_path)
    print("Master Columns:", df.columns.tolist())
    # Assuming columns are '위협유형코드' and '위협명' or similar
    print("\nMapping Sample:")
    # Detect relevant columns
    code_col = [c for c in df.columns if '코드' in c][0]
    name_col = [c for c in df.columns if '명' in c and '코드' not in c][0]
    print(df[[code_col, name_col]].head(10))
    
    # Save a JSON mapping for reference
    mapping = dict(zip(df[name_col], df[code_col]))
    print(f"\nTotal mappings: {len(mapping)}")
    print(list(mapping.items())[:5])

if __name__ == "__main__":
    check()
