import pandas as pd
import os

TERRAIN_FILE = 'c:/POC/COA_Agent_Platform/data_lake/지형셀.xlsx'

# 북한 지역 지형셀 정의
new_cells = [
    {"지형셀ID": "TERR011", "지형명": "평양", "좌표정보": "125.7625, 39.0392", "설명": "북한 수도 및 지휘부 중심"},
    {"지형셀ID": "TERR012", "지형명": "개성", "좌표정보": "126.5519, 37.9704", "설명": "전방 군단 주둔지"},
    {"지형셀ID": "TERR013", "지형명": "사리원", "좌표정보": "125.7537, 38.5085", "설명": "황해북도 교통 요지"},
    {"지형셀ID": "TERR014", "지형명": "원산", "좌표정보": "127.4439, 39.1552", "설명": "동해안 해군/공군 기지"},
    {"지형셀ID": "TERR015", "지형명": "함흥", "좌표정보": "127.5358, 39.9183", "설명": "함경남도 주요 공업 도시"},
    {"지형셀ID": "TERR016", "지형명": "해주", "좌표정보": "125.7147, 38.0406", "설명": "서해안 해군 기지"},
    {"지형셀ID": "TERR017", "지형명": "철원(북)", "좌표정보": "127.3133, 38.3000", "설명": "중부 전선 요충지 (북측)"},
    {"지형셀ID": "TERR018", "지형명": "강원(북)", "좌표정보": "128.0000, 38.5000", "설명": "동부 전선 산악 지대"},
    {"지형셀ID": "TERR019", "지형명": "평안남도", "좌표정보": "126.0000, 39.3000", "설명": "평양 방어권 외곽"},
    {"지형셀ID": "TERR020", "지형명": "황해북도", "좌표정보": "126.3000, 38.7000", "설명": "전방 증원 부대 이동로"}
]

if os.path.exists(TERRAIN_FILE):
    df = pd.read_excel(TERRAIN_FILE)
    print(f"기존 데이터: {len(df)}건")
    
    # 중복 확인 (ID 기준)
    existing_ids = df['지형셀ID'].astype(str).tolist()
    to_add = []
    
    for cell in new_cells:
        if cell["지형셀ID"] not in existing_ids:
            to_add.append(cell)
            
    if to_add:
        df_new = pd.DataFrame(to_add)
        # 기존 컬럼에 맞춰 병합 (없는 컬럼은 NaN)
        df_combined = pd.concat([df, df_new], ignore_index=True)
        df_combined.to_excel(TERRAIN_FILE, index=False)
        print(f"✅ {len(to_add)}개 북한 지형셀 추가 완료!")
    else:
        print("ℹ️ 추가할 데이터가 없거나 이미 존재합니다.")
        
    print(df_combined[['지형셀ID', '지형명', '좌표정보']].tail(12))
else:
    print(f"❌ 파일이 존재하지 않습니다: {TERRAIN_FILE}")
