
import pandas as pd
import os

s_df = pd.read_excel("c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\위협상황.xlsx")
m_df = pd.read_excel("c:\\POC\\COA_Agent_Platform_Ref\\data_lake\\위협유형_마스터.xlsx")

s_codes = s_df['위협유형코드'].astype(str).str.strip().unique()
m_codes = m_df['위협유형코드'].astype(str).str.strip().unique()

print(f"Master Codes ({len(m_codes)}): {sorted(list(m_codes))}")
print(f"Situation Codes ({len(s_codes)}): {sorted(list(s_codes))}")

# Check diffs
only_s = set(s_codes) - set(m_codes)
print(f"\nCodes ONLY in Situation ({len(only_s)}): {sorted(list(only_s))}")

# Distribution
print("\nDistribution in Situation Table:")
print(s_df['위협유형코드'].value_counts())
