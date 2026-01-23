
import pandas as pd
import os

def check_file(path, label):
    if os.path.exists(path):
        print(f"\n=== {label} ({path}) ===")
        df = pd.read_excel(path)
        return df
    return None

# 1. 위협상황
df_threat = check_file('data_lake/위협상황.xlsx', 'Threat Situations')
if df_threat is not None:
    print(df_threat[df_threat['위협ID'].isin(['THR001', 'THR004'])].to_string())

# 2. 관련성 (Ground Truth)
df_rel = check_file('data_lake/방책유형_위협유형_관련성.xlsx', 'Relevance (GT)')
if df_rel is not None:
    # '정면공격' and '침투' 관련성 확인
    target_threats = ['정면공격', '침투']
    # 컬럼명이 한글인지 영문인지 확인 필요
    c_threat = 'threat_type' if 'threat_type' in df_rel.columns else '위협유형'
    print(df_rel[df_rel[c_threat].isin(target_threats)].sort_values(by=c_threat).to_string())

# 3. 가중치
df_weight = check_file('data_lake/평가기준_가중치.xlsx', 'Weights')
if df_weight is not None:
    print(df_weight.to_string())

# 4. 방책 라이브러리 (상위 일부)
df_lib = check_file('data_lake/COA_Library.xlsx', 'COA Library (Summary)')
if df_lib is not None:
    cols = ['COA_ID', '명칭', '방책유형', '적합위협유형']
    existing_cols = [c for c in cols if c in df_lib.columns]
    print(df_lib[existing_cols].head(20).to_string())
    
    # 침투 관련 방책 검색
    print("\nCOAs suitable for '침투':")
    print(df_lib[df_lib['적합위협유형'].str.contains('침투', na=False)][existing_cols].to_string())
    
    # 정면공격 관련 방책 검색
    print("\nCOAs suitable for '정면공격':")
    print(df_lib[df_lib['적합위협유형'].str.contains('정면공격|공격', na=False)][existing_cols].to_string())
