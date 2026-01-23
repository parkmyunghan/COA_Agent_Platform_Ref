
import pandas as pd
import numpy as np
from pathlib import Path
import random

def fill_coa_library():
    file_path = Path("data_lake/COA_Library.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    print(f"Loaded {len(df)} rows from {file_path}")

    # Helper functions for virtual data
    def get_condition(row):
        if not pd.isna(row['적용조건']):
            return row['적용조건']
        v_type = row['방책유형']
        if v_type == 'Defense':
            return "threat_level > 0.6"
        elif v_type == 'Offensive':
            return "attack_power > 0.7"
        elif v_type == 'CounterAttack':
            return "enemy_momentum < 0.4"
        elif v_type == 'Preemptive':
            return "imminent_threat == True"
        return "threat_level > 0.5"

    def get_keywords(row):
        if not pd.isna(row['키워드']):
            return row['키워드']
        base = f"{row['방책유형']}, 작전"
        if "방어" in row['명칭'] or "Defense" in row['방책유형']:
            base += ", 방어, 진지"
        if "공격" in row['명칭'] or "Offensive" in row['방책유형']:
            base += ", 공격, 기동"
        return base

    def get_incompatible(row):
        if not pd.isna(row['환경비호환성']):
            return row['환경비호환성']
        options = ["폭우", "농무", "강풍", "통신두절", "극심한 추위"]
        return ", ".join(random.sample(options, random.randint(1, 2)))

    def get_suitable_threat(row):
        if not pd.isna(row['적합위협유형']):
            return row['적합위협유형']
        v_type = row['방책유형']
        if v_type == 'Defense':
            return "기갑공격, 정찰투입"
        elif v_type == 'Offensive':
            return "적 방어진지, 화력기지"
        elif v_type == 'InformationOps':
            return "전자전, 심리전"
        return "일반 위협"

    def get_resource_priority(row):
        if not pd.isna(row['자원우선순위']):
            return row['자원우선순위']
        v_type = row['방책유형']
        if v_type == 'Defense':
            return "보병대대(필수), 포병중대(권장), 공병소대(선택)"
        elif v_type == 'Offensive':
            return "전차대대(필수), 보병여단(필수), 정찰드론(권장)"
        return "부대(필수)"

    def get_optimal_cond(row):
        if not pd.isna(row['전장환경_최적조건']):
            return row['전장환경_최적조건']
        return "주간, 가시거리 > 5km, 평지"

    def get_linked_coa(row, all_ids):
        if not pd.isna(row['연계방책']):
            return row['연계방책']
        other_ids = [i for i in all_ids if i != row['COA_ID']]
        if not other_ids:
            return None
        target = random.choice(other_ids)
        rel = random.choice(["동시", "후행", "선행"])
        return f"{target}({rel})"

    def get_counter_tactics(row):
        if not pd.isna(row['적대응전술']):
            return row['적대응전술']
        options = ["우회기동", "화력집중", "전자전 교란", "야간기습", "화학전"]
        return ", ".join(random.sample(options, random.randint(2, 3)))

    # Apply filling
    all_coa_ids = df['COA_ID'].tolist()
    
    df['적용조건'] = df.apply(get_condition, axis=1)
    df['키워드'] = df.apply(get_keywords, axis=1)
    df['전장환경_제약'] = df['전장환경_제약'].fillna("없음")
    df['환경호환성'] = df['환경호환성'].fillna("전천후, 주/야간")
    df['환경비호환성'] = df.apply(get_incompatible, axis=1)
    df['단계정보'] = df['단계정보'].fillna("Phase 1")
    df['주노력여부'] = df['주노력여부'].fillna("N")
    df['시각화스타일'] = df['시각화스타일'].fillna("Default")
    df['적합위협유형'] = df.apply(get_suitable_threat, axis=1)
    df['자원우선순위'] = df.apply(get_resource_priority, axis=1)
    df['전장환경_최적조건'] = df.apply(get_optimal_cond, axis=1)
    df['연계방책'] = df.apply(lambda r: get_linked_coa(r, all_coa_ids), axis=1)
    df['적대응전술'] = df.apply(get_counter_tactics, axis=1)

    # Save back to Excel
    try:
        df.to_excel(file_path, index=False)
        print(f"Successfully filled missing values and saved to {file_path}")
    except Exception as e:
        print(f"Error saving to Excel: {e}")

if __name__ == "__main__":
    fill_coa_library()
