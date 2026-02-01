
import pandas as pd
import os

file_path = r'c:\POC\COA_Agent_Platform_Ref\data_lake\COA_Library.xlsx'
if os.path.exists(file_path):
    try:
        df = pd.read_excel(file_path)
        print(f"Total rows in COA_Library.xlsx: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error reading Excel: {e}")
else:
    print("File not found.")
