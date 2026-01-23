import pandas as pd
import random
import os

# 파일 경로
TERRAIN_FILE = 'c:/POC/COA_Agent_Platform/data_lake/지형셀.xlsx'
THREAT_FILE = 'c:/POC/COA_Agent_Platform/data_lake/위협상황.xlsx'
UNIT_FILE = 'c:/POC/COA_Agent_Platform/data_lake/아군부대현황.xlsx'

# 주요 지점에 대한 좌표 DB (텍스트 기반 검색용 폴백)
LOCATION_DB = {
    "평양": {"lat": 39.0392, "lng": 125.7625},
    "개성": {"lat": 37.9704, "lng": 126.5519},
    "철원": {"lat": 38.1464, "lng": 127.3133},
    "서울": {"lat": 37.5665, "lng": 126.9780},
    "원산": {"lat": 39.1552, "lng": 127.4439},
    "강릉": {"lat": 37.7519, "lng": 128.8760},
}
DEFAULT_CENTER = {"lat": 38.0, "lng": 127.0}

def parse_coord(coord_str):
    if not isinstance(coord_str, str) or ',' not in coord_str:
        return None
    try:
        lon, lat = map(float, coord_str.split(','))
        return {"lng": lon, "lat": lat}
    except:
        return None

def apply_jitter(center_dict, range_deg=0.01):
    lat = center_dict['lat'] + random.uniform(-range_deg, range_deg)
    lng = center_dict['lng'] + random.uniform(-range_deg, range_deg)
    return f"{lng:.6f}, {lat:.6f}"

# 메인 실행
print("데이터 로드 중...")

# 1. 지형셀 좌표 로드
cell_coords = {}
if os.path.exists(TERRAIN_FILE):
    df_cell = pd.read_excel(TERRAIN_FILE)
    if '지형셀ID' in df_cell.columns and '좌표정보' in df_cell.columns:
        for _, row in df_cell.iterrows():
            cid = str(row['지형셀ID']).strip()
            cval = row['좌표정보']
            parsed = parse_coord(cval)
            if parsed:
                cell_coords[cid] = parsed
    print(f"[INFO] 지형셀 좌표 {len(cell_coords)}개 로드 완료")
else:
    print(f"[WARN] 지형셀 파일 확인 불가")

# 2. 위협상황 업데이트
if os.path.exists(THREAT_FILE):
    print(f"[PROC] 위협상황 처리 중...")
    df_threat = pd.read_excel(THREAT_FILE)
    if "좌표정보" not in df_threat.columns:
        df_threat["좌표정보"] = None
        
    count = 0
    for idx, row in df_threat.iterrows():
        # 발생위치셀ID 확인
        cell_id = str(row.get('발생위치셀ID', '')).strip()
        text = str(row.get('원시보고텍스트', ''))
        
        target_center = None
        
        # 1순위: 셀 ID 참조
        if cell_id in cell_coords:
            target_center = cell_coords[cell_id]
        
        # 2순위: 텍스트 검색
        elif text:
            for k, v in LOCATION_DB.items():
                if k in text:
                    target_center = v
                    break
        
        if target_center:
            # 겹침 방지 (0.005도 approx 500m)
            df_threat.at[idx, '좌표정보'] = apply_jitter(target_center, 0.005)
            count += 1
        else:
            # 기본값 (랜덤)
            df_threat.at[idx, '좌표정보'] = apply_jitter(DEFAULT_CENTER, 0.5) # 넓게 분산
            
    df_threat.to_excel(THREAT_FILE, index=False)
    print(f"  -> {count}개 위협 좌표 업데이트 완료")

# 3. 아군부대현황 업데이트
if os.path.exists(UNIT_FILE):
    print(f"[PROC] 아군부대현황 처리 중...")
    df_unit = pd.read_excel(UNIT_FILE)
    if "좌표정보" not in df_unit.columns:
        df_unit["좌표정보"] = None
        
    count = 0
    for idx, row in df_unit.iterrows():
        # 배치지형셀ID 확인
        cell_id = str(row.get('배치지형셀ID', '')).strip()
        name = str(row.get('부대명', ''))
        
        target_center = None
        
        # 1순위: 셀 ID 참조
        if cell_id in cell_coords:
            target_center = cell_coords[cell_id]
        
        # 2순위: 텍스트 검색
        elif name:
            for k, v in LOCATION_DB.items():
                if k in name:
                    target_center = v
                    break
        
        if target_center:
            df_unit.at[idx, '좌표정보'] = apply_jitter(target_center, 0.005)
            count += 1
        else:
            # 기본값
            df_unit.at[idx, '좌표정보'] = apply_jitter(DEFAULT_CENTER, 0.5)
            
    df_unit.to_excel(UNIT_FILE, index=False)
print(f"  -> {count}개 부대 좌표 업데이트 완료")

# 4. 적군부대현황 업데이트 (NEW)
RED_UNIT_FILE = 'c:/POC/COA_Agent_Platform/data_lake/적군부대현황.xlsx'

if os.path.exists(RED_UNIT_FILE):
    print(f"[PROC] 적군부대현황 처리 중...")
    df_red = pd.read_excel(RED_UNIT_FILE)
    if "좌표정보" not in df_red.columns:
        df_red["좌표정보"] = None
        
    count = 0
    for idx, row in df_red.iterrows():
        # 배치지형셀ID 확인
        cell_id = str(row.get('배치지형셀ID', '')).strip()
        name = str(row.get('부대명', ''))
        
        target_center = None
        
        # 1순위: 셀 ID 참조
        if cell_id in cell_coords:
            target_center = cell_coords[cell_id]
        
        # 2순위: 텍스트 검색
        elif name:
            for k, v in LOCATION_DB.items():
                if k in name:
                    target_center = v
                    break
        
        if target_center:
            # 적군은 약간 더 넓게 분산 (0.008)
            df_red.at[idx, '좌표정보'] = apply_jitter(target_center, 0.008)
            count += 1
        else:
            # 기본값 (랜덤) - 평양 주변 (39.0392, 125.7625)
            # 매핑 실패 시에만 평양 주변 배치
            default_red_center = LOCATION_DB["평양"]
            df_red.at[idx, '좌표정보'] = apply_jitter(default_red_center, 0.1) 
            
    df_red.to_excel(RED_UNIT_FILE, index=False)
    print(f"  -> {count}개 적군 부대 좌표 업데이트 완료 (북한 지형셀 기준)")

print("모든 작업 완료.")
