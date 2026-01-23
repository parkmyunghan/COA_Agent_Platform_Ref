
import pandas as pd
from pathlib import Path

def read_sample():
    file_path = Path("data_lake/COA_Library.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df.head(10))
    print("\nColumn List:")
    print(df.columns.tolist())

if __name__ == "__main__":
    read_sample()
