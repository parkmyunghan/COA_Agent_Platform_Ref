
import pandas as pd
import os

def check_file(path, label, out):
    if os.path.exists(path):
        out.write(f"\n=== {label} ({path}) ===\n")
        df = pd.read_excel(path)
        return df
    return None

with open('data_inspection_v3.txt', 'w', encoding='utf-8') as out:
    # 1. 위협상황
    df_threat = check_file('data_lake/위협상황.xlsx', 'Threat Situations', out)
    if df_threat is not None:
        out.write(df_threat[df_threat['위협ID'].isin(['THR001', 'THR004'])].to_string() + "\n")

    # 2. 관련성 (Ground Truth)
    df_rel = check_file('data_lake/방책유형_위협유형_관련성.xlsx', 'Relevance (GT)', out)
    if df_rel is not None:
        target_threats = ['정면공격', '침투']
        c_threat = 'threat_type' if 'threat_type' in df_rel.columns else '위협유형'
        out.write(df_rel[df_rel[c_threat].isin(target_threats)].sort_values(by=c_threat).to_string() + "\n")

    # 3. 가중치
    df_weight = check_file('data_lake/평가기준_가중치.xlsx', 'Weights', out)
    if df_weight is not None:
        out.write(df_weight.to_string() + "\n")

    # 4. 방책 라이브러리
    df_lib = check_file('data_lake/COA_Library.xlsx', 'COA Library (Filtered)', out)
    if df_lib is not None:
        cols = ['COA_ID', '명칭', '방책유형', '적합위협유형']
        existing_cols = [c for c in cols if c in df_lib.columns]
        
        out.write("\nCOAs suitable for '침투':\n")
        out.write(df_lib[df_lib['적합위협유형'].str.contains('침투', na=False)][existing_cols].to_string() + "\n")
        
        out.write("\nCOAs suitable for '정면공격':\n")
        out.write(df_lib[df_lib['적합위협유형'].str.contains('정면공격|공격', na=False)][existing_cols].to_string() + "\n")

print("Done. Check data_inspection_v3.txt")
