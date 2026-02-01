
import pandas as pd
import os

file_path = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\지형셀.xlsx"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
else:
    try:
        df = pd.read_excel(file_path)
        print("Columns:", df.columns.tolist())
        print("-" * 30)
        
        # Check missing values
        missing = df.isnull().sum()
        print("Missing Values Check:")
        print(missing[missing > 0])
        
        print("-" * 30)
        print("Total Rows:", len(df))
        
        # Show rows with missing values
        is_missing = df.isnull().any(axis=1)
        if is_missing.any():
            print("\nSAMPLE ROWS WITH ISSUES:")
            print(df[is_missing].head(5))
            
    except Exception as e:
        print(f"Error reading excel: {e}")
