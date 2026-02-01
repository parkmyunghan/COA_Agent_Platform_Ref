
import pandas as pd
import os

file_path = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\위협상황.xlsx"
xl = pd.ExcelFile(file_path)
print(f"File: {os.path.basename(file_path)}")
print(f"Sheets: {xl.sheet_names}")

for sheet in xl.sheet_names:
    df = xl.parse(sheet)
    print(f"  Sheet '{sheet}' -> Rows: {len(df)}")
    if len(df) > 0:
        print(f"    Columns: {df.columns.tolist()}")
