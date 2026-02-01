
import pandas as pd
import os

data_dir = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake"

def check():
    threat_path = os.path.join(data_dir, "위협상황.xlsx")
    mapping_path = os.path.join(data_dir, "방책유형_위협유형_관련성.xlsx")
    
    threat_df = pd.read_excel(threat_path)
    mapping_df = pd.read_excel(mapping_path)
    
    t_codes = set(threat_df['위협유형코드'].unique())
    m_types = set(mapping_df['threat_type'].unique())
    
    print(f"Total Unique Codes in Threats Table: {len(t_codes)}")
    print(list(t_codes)[:10], "...")
    
    print(f"\nTotal Unique Types in Mapping Table: {len(m_types)}")
    print(list(m_types)[:10], "...")
    
    # Check overlap
    overlap = t_codes.intersection(m_types)
    print(f"\nOverlap count: {len(overlap)}")
    
    if len(overlap) == 0:
        print("\n[CRITICAL] ZERO OVERLAP! Threat table uses codes (THR_...) but mapping table uses names (Korean words)?")
        
    # Check if a mapping from names to codes is needed
    master_path = os.path.join(data_dir, "위협유형_마스터.xlsx")
    if os.path.exists(master_path):
        master_df = pd.read_excel(master_path)
        print("\n[Master Table Columns]:", master_df.columns.tolist())
        print(master_df.head(5))

if __name__ == "__main__":
    check()
