
import pandas as pd
import os

df = pd.read_excel("c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\위협유형_마스터.xlsx")
print(f"Exact Columns: {df.columns.tolist()}")
for c in df.columns:
    print(f"  Column '{c}' (Length: {len(c)}) -> Bytes: {c.encode('utf-8')}")

print("\nData Sample (first 5):")
print(df.head(5))

# Check unique codes
code_col = df.columns[0]
print(f"\nUnique codes in Master ({len(df[code_col].unique())}):")
print(df[code_col].unique())
