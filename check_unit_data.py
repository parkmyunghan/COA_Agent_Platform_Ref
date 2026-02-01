
import pandas as pd
import os

file_path = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\아군부대현황.xlsx"

try:
    df = pd.read_excel(file_path)
    
    with open("unit_data_check_utf8.txt", "w", encoding="utf-8") as f:
        f.write(f"Columns: {df.columns.tolist()}\n")
        f.write("-" * 30 + "\n")
        f.write("Missing Values Check:\n")
        f.write(str(df.isnull().sum()) + "\n")
        f.write("-" * 30 + "\n")
        
        # Custom view
        target_indices = [9, 10, 11, 12] # Row 10-13 area
        f.write("\n[Detailed Context for Rows 10-13]\n")
        f.write(df.iloc[target_indices][['아군부대ID', '부대명', '병종', '임무역할', '상급부대', '배치축선ID']].to_string() + "\n")

except Exception as e:
    print(f"Error checking unit data: {e}")
