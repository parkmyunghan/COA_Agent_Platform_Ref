
import pandas as pd
import os

data_dir = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake"

def check():
    master_path = os.path.join(data_dir, "위협유형_마스터.xlsx")
    mapping_path = os.path.join(data_dir, "방책유형_위협유형_관련성.xlsx")
    threat_path = os.path.join(data_dir, "위협상황.xlsx")
    
    master_df = pd.read_excel(master_path)
    mapping_df = pd.read_excel(mapping_path)
    threat_df = pd.read_excel(threat_path)
    
    # 1. Map names to codes
    name_to_code = dict(zip(master_df['위협유형명'], master_df['위협유형코드']))
    code_to_name = dict(zip(master_df['위협유형코드'], master_df['위협유형명']))
    
    # 2. Covered codes in mapping table
    # Mapping table uses names in 'threat_type'
    mapping_names = set(mapping_df['threat_type'].unique())
    covered_codes = set()
    for name in mapping_names:
        if name in name_to_code:
            covered_codes.add(name_to_code[name])
        elif name.startswith("THR_TYPE_"): # Already code
            covered_codes.add(name)
            
    print(f"Total Unique Codes in Master: {len(master_df)}")
    print(f"Total Unique Codes in Mapping Table (converted): {len(covered_codes)}")
    
    # 3. Find missing codes
    all_codes = set(master_df['위협유형코드'].unique())
    missing_codes = all_codes - covered_codes
    
    print(f"\nMissing Codes in Mapping Table ({len(missing_codes)}):")
    for code in sorted(list(missing_codes)):
        print(f"  - {code} ({code_to_name.get(code, 'N/A')})")
        
    # 4. Impacted threat instances
    impacted_threats = threat_df[threat_df['위협유형코드'].isin(missing_codes)]
    print(f"\nImpacted Threat rows in Excel: {len(impacted_threats)}")
    if len(impacted_threats) > 0:
        print("Sample impacted threats:")
        print(impacted_threats[['위협ID', '위협명', '위협유형코드']].head(10))

if __name__ == "__main__":
    check()
