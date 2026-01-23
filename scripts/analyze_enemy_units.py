
import pandas as pd
from pathlib import Path

def analyze_enemy_units():
    data_lake = Path("data_lake")
    target_file = data_lake / "적군부대현황.xlsx"
    
    if not target_file.exists():
        print(f"[ERROR] File not found: {target_file}")
        return

    try:
        # Load
        df = pd.read_excel(target_file)
        print(f"\n=== 적군부대현황.xlsx Analysis ===")
        print(f"Total Rows: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")
        
        print("\n[Column Analysis]")
        for col in df.columns:
            # Check unique count and sample values
            unique_vals = df[col].dropna().unique()
            n_unique = len(unique_vals)
            
            sample = unique_vals[:5] if n_unique > 0 else []
            
            print(f"- {col}:")
            print(f"  Type: {df[col].dtype}")
            print(f"  Unique Count: {n_unique}")
            print(f"  Null Count: {df[col].isnull().sum()}")
            if n_unique > 0:
                print(f"  Sample: {sample}")
            
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")

if __name__ == "__main__":
    analyze_enemy_units()
