
import pandas as pd
import os

files = [
    'data_lake/위협상황.xlsx',
    'data_lake/COA_Library.xlsx',
    'data_lake/방책유형_위협유형_관련성.xlsx',
    'data_lake/평가기준_가중치.xlsx'
]

for f in files:
    if os.path.exists(f):
        print(f"\n--- {f} ---")
        try:
            df = pd.read_excel(f)
            print(df.head(10).to_string())
            if '위협상황' in f:
                print("\nFiltering for THR001 and THR004:")
                print(df[df['위협ID'].isin(['THR001', 'THR004'])].to_string())
        except Exception as e:
            print(f"Error reading {f}: {e}")
    else:
        print(f"\n[MISSING] {f}")
