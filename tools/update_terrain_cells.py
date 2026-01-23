import pandas as pd
import random
import os

# 파일 경로
file_path = 'c:/POC/COA_Agent_Platform/data_lake/지형셀.xlsx'

# 데이터 로드
df = pd.read_excel(file_path)

# 주요 지점에 대한 좌표 DB (실제 지명 기반)
LOCATION_DB = {
    # 주요 도시 및 지점 (한반도)
    "개성": {"lat": 37.9704, "lng": 126.5519},
    "평양": {"lat": 39.0392, "lng": 125.7625},
    "판문점": {"lat": 37.956, "lng": 126.677},
    "철원": {"lat": 38.1464, "lng": 127.3133},
    "문산": {"lat": 37.854, "lng": 126.783},
    "연천": {"lat": 38.096, "lng": 127.075},
    "화천": {"lat": 38.106, "lng": 127.708},
    "양구": {"lat": 38.109, "lng": 127.990},
    "인제": {"lat": 38.069, "lng": 128.170},
    "고성": {"lat": 38.380, "lng": 128.468},
    "서부전선": {"lat": 37.95, "lng": 126.67},
    "중부전선": {"lat": 38.25, "lng": 127.12},
    "동부전선": {"lat": 38.61, "lng": 128.35}
}

# 기본 위치 (DMZ 인근 중앙)
DEFAULT_CENTER = {"lat": 38.0, "lng": 127.0}

# 좌표 정보 생성 함수
def generate_coordinate(row):
    name = str(row['지형명'])
    
    # 지명 기반 좌표 매핑
    center = DEFAULT_CENTER
    for loc_name, coords in LOCATION_DB.items():
        if loc_name in name:
            center = coords
            break
            
    # 랜덤 오프셋 (지형셀이므로 약간의 영역을 가짐)
    # 0.01도 = 약 1km
    lat_offset = random.uniform(-0.02, 0.02)
    lng_offset = random.uniform(-0.02, 0.02)
    
    lat = center['lat'] + lat_offset
    lng = center['lng'] + lng_offset
    
    # "경도, 위도" 형식 반환 (GeoJSON 순서)
    return f"{lng:.6f}, {lat:.6f}"

# 좌표정보 컬럼 추가
print("좌표정보 생성 중...")
df['좌표정보'] = df.apply(generate_coordinate, axis=1)

# 저장
df.to_excel(file_path, index=False)
print(f"파일이 업데이트되었습니다: {file_path}")
print(df[['지형셀ID', '지형명', '좌표정보']].head())
