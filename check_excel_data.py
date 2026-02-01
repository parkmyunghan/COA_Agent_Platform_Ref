
import pandas as pd
import os

def check_file(file_name, id_col, target_id):
    path = os.path.join("data_lake", file_name)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    try:
        df = pd.read_excel(path)
        print(f"\n--- Checking {file_name} ---")
        print(f"Columns: {df.columns.tolist()}")
        
        row = df[df[id_col] == target_id]
        if not row.empty:
            print(f"Found {target_id}:")
            print(row.iloc[0].to_dict())
        else:
            print(f"{target_id} not found in {id_col}")
            # Show first 5 rows for context
            print("First 5 IDs:")
            print(df[id_col].head().tolist())
    except Exception as e:
        print(f"Error checking {file_name}: {e}")

def main():
    check_file("지형셀.xlsx", "지형셀ID", "TERR007")
    check_file("위협유형_마스터.xlsx", "위협유형ID", "THR_TYPE_007")
    check_file("전장축선.xlsx", "축선ID", "AXIS06")

if __name__ == "__main__":
    main()
