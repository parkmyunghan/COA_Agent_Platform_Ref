import pandas as pd
import os

RED_UNIT_FILE = 'c:/POC/COA_Agent_Platform/data_lake/적군부대현황.xlsx'

# 부대별 새로운 지형셀 매핑 (Semantic Mapping)
mapping = {
    "적 기계화보병여단1": "TERR011", # 평양 (수도 방어)
    "적 기계화보병여단2": "TERR019", # 평안남도 (외곽 방어)
    "적 전차대대1": "TERR012",      # 개성 (전방 기동)
    "적 포병여단": "TERR017",       # 철원(북) (화력 지원)
    "적 정찰중대": "TERR020",       # 황해북도 (정찰)
    "적 저격중대": "TERR018",       # 강원(북) (산악 침투)
    "적 공병중대": "TERR013",       # 사리원 (기동로 지원)
    "적 방사포대": "TERR014",       # 원산 (해안/원거리)
    "적 보병대대": "TERR016",       # 해주 (서해안)
    "적 유격부대": "TERR015",       # 함흥 (후방 교란)
}

if os.path.exists(RED_UNIT_FILE):
    df = pd.read_excel(RED_UNIT_FILE)
    print(f"기존 데이터: {len(df)}건")
    
    count = 0
    for idx, row in df.iterrows():
        name = str(row['부대명']).strip()
        if name in mapping:
            old_cell = row['배치지형셀ID']
            new_cell = mapping[name]
            df.at[idx, '배치지형셀ID'] = new_cell
            print(f"Update: {name} | {old_cell} -> {new_cell}")
            count += 1
            
    df.to_excel(RED_UNIT_FILE, index=False)
    print(f"✅ {count}개 적군 부대 재배치 완료 (북한 지역 지형셀 할당)")
else:
    print(f"❌ 파일이 존재하지 않습니다: {RED_UNIT_FILE}")
