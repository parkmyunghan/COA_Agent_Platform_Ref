import pandas as pd

# Read the Excel file
df = pd.read_excel('data_lake/아군부대현황.xlsx')

# Print columns
print("=== Columns ===")
for col in df.columns:
    print(f"  - {col}")

print("\n=== Sample Data (First Row) ===")
if len(df) > 0:
    row = df.iloc[0]
    for col in df.columns:
        print(f"{col}: {row[col]}")
        
print("\n=== Sample Data (All Rows) ===")
print(df.to_string())
