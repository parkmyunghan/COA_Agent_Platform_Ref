
import pandas as pd
import os

data_dir = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake"

def check():
    master_path = os.path.join(data_dir, "위협유형_마스터.xlsx")
    situation_path = os.path.join(data_dir, "위협상황.xlsx")
    
    m_df = pd.read_excel(master_path)
    s_df = pd.read_excel(situation_path)
    
    m_codes = set(m_df['위협유형코드'].unique())
    s_codes = set(s_df['위협유형코드'].unique())
    
    undefined = s_codes - m_codes
    
    print(f"Total Unique Codes in Situation: {len(s_codes)}")
    print(f"Total Unique Codes in Master: {len(m_codes)}")
    print(f"\n[UNDEFINED CODES] in Situation Table ({len(undefined)}):")
    print(sorted(list(undefined)))
    
    # Impact
    impacted_rows = s_df[s_df['위협유형코드'].isin(undefined)]
    print(f"\nTotal rows impacted: {len(impacted_rows)}")
    if len(impacted_rows) > 0:
        print("\nSAMPLE ROWS WITH UNDEFINED CODES:")
        print(impacted_rows[['위협ID', '위협명', '위협유형코드']].head(10))

if __name__ == "__main__":
    check()
