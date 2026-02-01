
import pandas as pd
import os

data_dir = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake"

def check():
    threat_path = os.path.join(data_dir, "위협상황.xlsx")
    mapping_path = os.path.join(data_dir, "방책유형_위협유형_관련성.xlsx")
    
    if not os.path.exists(threat_path) or not os.path.exists(mapping_path):
        print("Files missing")
        return
        
    threat_df = pd.read_excel(threat_path)
    mapping_df = pd.read_excel(mapping_path)
    
    print(f"Total Threats in Excel: {len(threat_df)}")
    print(f"Total Mappings in Excel: {len(mapping_df)}")
    
    print("\n[Threat Table Columns]:", threat_df.columns.tolist())
    print("[Mapping Table Columns]:", mapping_df.columns.tolist())
    
    # Unique threat codes in threats table
    t_codes = set(threat_df['위협유형코드'].unique())
    print(f"\nUnique Threat Codes in Threats Table ({len(t_codes)}):")
    print(sorted(list(t_codes)))
    
    # Unique codes in mapping table
    # It might be '위협유형' or '위협유형코드'
    m_col = '위협유형코드' if '위협유형코드' in mapping_df.columns else '위협유형'
    m_codes = set(mapping_df[m_col].unique())
    print(f"\nUnique Codes in Mapping Table ({len(m_codes)}) using column '{m_col}':")
    print(sorted(list(m_codes)))
    
    # Missing codes
    missing = t_codes - m_codes
    print(f"\nThreat Codes NOT in Mapping Table ({len(missing)}):")
    print(sorted(list(missing)))
    
    # Count threats for each missing code
    if missing:
        missing_count = threat_df[threat_df['위협유형코드'].isin(missing)].shape[0]
        print(f"\nTotal Threat rows affected: {missing_count}")

if __name__ == "__main__":
    check()
