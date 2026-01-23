import pandas as pd
import os

# Data Lake paths
DATA_LAKE_DIR = 'data_lake'
UNIT_FILE = os.path.join(DATA_LAKE_DIR, '아군부대현황.xlsx')
ASSET_FILE = os.path.join(DATA_LAKE_DIR, '아군가용자산.xlsx')
ALLOC_FILE = os.path.join(DATA_LAKE_DIR, '임무별_자원할당.xlsx')

def process_friendly_units(file_path):
    print(f"Processing {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Legacy global variable usage cleanup if needed, but for now just use df
    # UNIT_FILE is global but we should use file_path


    print("1. Modifying '아군부대현황.xlsx'...")
    # ID Standardization
    # FR_UNIT_005 -> FRU011
    # FR_UNIT_006 -> FRU012
    id_map = {
        'FR_UNIT_005': 'FRU011',
        'FR_UNIT_006': 'FRU012'
    }
    df['아군부대ID'] = df['아군부대ID'].replace(id_map)

    # Fill missing fields for FRU011 (1항공여단)
    idx_fru011 = df[df['아군부대ID'] == 'FRU011'].index
    if not idx_fru011.empty:
        df.loc[idx_fru011, '전투력지수'] = 90
        df.loc[idx_fru011, '배치지형셀ID'] = 'TERR002'
        df.loc[idx_fru011, '이동속도_kmh'] = 200
        df.loc[idx_fru011, '탐지범위'] = 40
        df.loc[idx_fru011, '부대부호(SIDC)'] = 'SFAPMFQE--*****'

    # Update FRU012 (특수작전팀)
    idx_fru012 = df[df['아군부대ID'] == 'FRU012'].index
    
    # 2. 컬럼 통합 및 정리
    print("Consolidating columns...")
    
    # 가용상태 통합
    if '가용상태' not in df.columns:
        df['가용상태'] = None
    if '상태' in df.columns:
        df['가용상태'] = df['가용상태'].fillna(df['상태'])
    df['가용상태'] = df['가용상태'].fillna('가용')
    
    # 이동속도_kmh 통합 (기동속도, 동속도_km 등)
    if '이동속도_kmh' not in df.columns:
        df['이동속도_kmh'] = None
    
    speed_candidates = ['기동속도', '동속도_km', '이동속도']
    for col in speed_candidates:
        if col in df.columns:
            # 숫자가 아닌 값 처리 (NaN 등)
            df['이동속도_kmh'] = df['이동속도_kmh'].fillna(pd.to_numeric(df[col], errors='coerce'))
            
    # 전투력지수 통합
    if '전투력지수' not in df.columns:
        df['전투력지수'] = None

    if '전투력' in df.columns:
        # 전투력이 0~1 사이 소수점이면 100을 곱해서 지수로 변환 (가정)
        combat_power_temp = pd.to_numeric(df['전투력'], errors='coerce')
        mask_decimal = (combat_power_temp > 0) & (combat_power_temp <= 1)
        combat_power_temp[mask_decimal] = combat_power_temp[mask_decimal] * 100
        df['전투력지수'] = df['전투력지수'].fillna(combat_power_temp)
        
    df['전투력지수'] = df['전투력지수'].fillna(0) # 기본값 0

    # 3. 데이터 보완 (Legacy Units) - 병종 기반
    print("Backfilling legacy unit data...")
    
    unit_type_defaults = {
        '기갑': {'speed': 60, 'range': 10, 'sidc': 'SFG*C-------'},
        '기계화': {'speed': 60, 'range': 10, 'sidc': 'SFG*C-------'}, # 기갑과 유사하게 처리
        '보병': {'speed': 40, 'range': 5, 'sidc': 'SFG*I-------'},
        '포병': {'speed': 40, 'range': 10, 'sidc': 'SFG*F-------'},
        '수색': {'speed': 50, 'range': 20, 'sidc': 'SFG*R-------'},
        '공병': {'speed': 40, 'range': 5, 'sidc': 'SFG*E-------'},
        '방공': {'speed': 40, 'range': 15, 'sidc': 'SFG*A-------'},
        '통신': {'speed': 40, 'range': 5, 'sidc': 'SFG*U-------'},
        '의무': {'speed': 40, 'range': 0, 'sidc': 'SFG*U-------'},
        '군수': {'speed': 40, 'range': 0, 'sidc': 'SFG*U-------'},
        '항공': {'speed': 200, 'range': 50, 'sidc': 'SFA*-------'}, # 헬기 등
        '특수전': {'speed': 40, 'range': 15, 'sidc': 'SFG*F-------'} # 임시
    }

    # 탐지범위 컬럼 확인
    if '탐지범위' not in df.columns:
        df['탐지범위'] = None
    if '부대부호(SIDC)' not in df.columns:
        df['부대부호(SIDC)'] = None

    for idx, row in df.iterrows():
        unit_type = str(row.get('병종', '')).strip()
        
        # 매핑된 정보 찾기 (부분 일치 포함)
        matched_defaults = None
        for key, defaults in unit_type_defaults.items():
            if key in unit_type:
                matched_defaults = defaults
                break
        
        if matched_defaults:
            # 이동속도 채우기
            if pd.isna(row.get('이동속도_kmh')) or row.get('이동속도_kmh') == 0:
                df.at[idx, '이동속도_kmh'] = matched_defaults['speed']
                print(f"  [{row['부대명']}] 이동속도 보완: {matched_defaults['speed']}")
                
            # 탐지범위 채우기
            if pd.isna(row.get('탐지범위')):
                df.at[idx, '탐지범위'] = matched_defaults['range']
                print(f"  [{row['부대명']}] 탐지범위 보완: {matched_defaults['range']}")
                
            # SIDC 채우기
            if pd.isna(row.get('부대부호(SIDC)')):
                df.at[idx, '부대부호(SIDC)'] = matched_defaults['sidc']
                print(f"  [{row['부대명']}] SIDC 보완: {matched_defaults['sidc']}")

    # 4. 공격헬기대대 추가 (없을 경우) 또는 업데이트
    idx_fru013 = df[df['아군부대ID'] == 'FRU013'].index
    if not idx_fru013.empty:
        print("Updating existing FRU013...")
        df.loc[idx_fru013, '부대명'] = '제1공격헬기대대'
        df.loc[idx_fru013, '제대'] = '대대'
        df.loc[idx_fru013, '병종'] = '항공'
        df.loc[idx_fru013, '전투력지수'] = 85
        df.loc[idx_fru013, '배치지형셀ID'] = 'TERR006'
        df.loc[idx_fru013, '가용상태'] = '가용'
        df.loc[idx_fru013, '이동속도_kmh'] = 240
        df.loc[idx_fru013, '탐지범위'] = 50
        df.loc[idx_fru013, '부대부호(SIDC)'] = 'SFA*HA----'
    else:
        print("Adding FRU013 (Attack Helicopter Battalion)...")
        new_row = {
            '아군부대ID': 'FRU013',
            '부대명': '제1공격헬기대대',
            '제대': '대대',
            '병종': '항공',
            '전투력지수': 85,
            '배치지형셀ID': 'G005', # 임의
            '가용상태': '가용',
            '이동속도_kmh': 240,
            '탐지범위': 50,
            '부대부호(SIDC)': 'SFA*HA----',
            '비고': '신규 추가'
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # 4.5 좌표정보 정제 (Lon, Lat -> Lat, Lon 보정)
    print("Correcting coordinate format...")
    if '좌표정보' in df.columns:
        for idx, row in df.iterrows():
            coord = str(row.get('좌표정보', ''))
            if coord and ',' in coord:
                try:
                    parts = [float(p.strip()) for p in coord.split(',')]
                    if len(parts) == 2:
                        val1, val2 = parts[0], parts[1]
                        # 만약 첫 번째 값이 90보다 크면 (즉, 경도이면) 순서 교체
                        if abs(val1) > 90 and abs(val2) <= 90:
                            new_coord = f"{val2}, {val1}"
                            df.at[idx, '좌표정보'] = new_coord
                            print(f"  [{row['부대명']}] Swapped coordinates: {coord} -> {new_coord}")
                except:
                    pass

    # 5. 불필요 컬럼 삭제
    cols_to_drop = ['상태', '동속도_km', '기동속도', '전투력', '이동방향'] # 이동방향은 일단 유지? 아니면 삭제? 삭제 목록에 포함됨.
    df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)
    
    print("Columns after cleanup:", df.columns.tolist())
    
    # 저장
    try:
        df.to_excel(file_path, index=False)
        print("Successfully saved cleaned data.")
    except Exception as e:
        print(f"Error saving file: {e}")

def process_assets(file_path):
    """아군가용자산 데이터 정제"""
    print(f"Processing {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 컬럼 표준화
    if '이동속도_kmh' not in df.columns:
        df['이동속도_kmh'] = None
    if '탐지범위_km' not in df.columns: # 자산 파일에서는 보통 '_km' 붙임
         df['탐지범위_km'] = None
         
    # 필요시 보완 로직 추가 (생략)
    
    try:
        df.to_excel(file_path, index=False)
        print("Successfully saved asset data.")
    except Exception as e:
         print(f"Error saving file: {e}")

if __name__ == "__main__":
    base_dir = r"C:\POC\COA_Agent_Platform_Ref\data_lake"
    unit_file = os.path.join(base_dir, "아군부대현황.xlsx")
    asset_file = os.path.join(base_dir, "아군가용자산.xlsx")
    
    if os.path.exists(unit_file):
        process_friendly_units(unit_file)
    else:
        print(f"File not found: {unit_file}")
        
    if os.path.exists(asset_file):
        process_assets(asset_file)
    else:
        print(f"File not found: {asset_file}")
