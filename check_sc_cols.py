
import pandas as pd
import os

df = pd.read_excel("c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\시나리오모음.xlsx")
print(f"Scenario Table Columns: {df.columns.tolist()}")
print("\nFirst row sample:")
print(df.iloc[0])
