
import pandas as pd
import os

file_path = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\아군가용자산.xlsx"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
else:
    try:
        df = pd.read_excel(file_path)

        # Write to utf-8 file
        with open("asset_data_check_utf8.txt", "w", encoding="utf-8") as f:
            f.write(f"Columns: {df.columns.tolist()}\n")
            f.write("-" * 30 + "\n")
            f.write("Missing Values Check:\n")
            f.write(str(df.isnull().sum()) + "\n")
            f.write("-" * 30 + "\n")
            
            if "비고" in df.columns:
                f.write(f"\n Rows with missing '비고':\n")
                f.write(str(df[df["비고"].isnull()]) + "\n")
                
            target_col = "탐지범위_km"
            if target_col not in df.columns and "감지범위_km" in df.columns:
                 f.write(f"\n[NOTE] '탐지범위_km' not found, but '감지범위_km' exists.\n")
                 target_col = "감지범위_km"
                 
            if target_col in df.columns:
                 f.write(f"\n Rows with missing '{target_col}':\n")
                 f.write(str(df[df[target_col].isnull()].head(10)) + "\n")
            else:
                 f.write(f"\n[WARNING] Column '{target_col}' DOES NOT EXIST.\n")

    except Exception as e:
        print(f"Error reading excel: {e}")
