
import pandas as pd
from pathlib import Path
import shutil

def infer_tactical_values(name):
    """지형명을 기반으로 전술 속성 추론"""
    name = str(name).strip()
    
    # Pre-defined known locations (Specific Overrides)
    known_locations = {
        '평양': ('도시', 4.0, 4.0, 2.0, 'Y', '수도권/대도시'),
        '개성': ('도시', 4.0, 4.5, 2.0, 'Y', '주요 도시/거점'),
        '사리원': ('도시', 4.0, 4.0, 2.0, 'Y', '교통 요충지/도시'),
        '원산': ('도시', 4.0, 4.0, 3.0, 'Y', '항구 도시/거점'),
        '함흥': ('도시', 4.0, 4.0, 2.0, 'Y', '공업 도시'),
        '해주': ('도시', 4.0, 4.0, 2.0, 'Y', '항구 도시'),
        '철원(북)': ('산악', 2.0, 5.0, 4.0, 'Y', '전략적 요충지/산악'),
        '강원(북)': ('산악', 1.5, 5.0, 4.0, 'N', '험준한 산악 지형'),
        '평안남도': ('평지', 4.5, 2.0, 3.5, 'N', '개활지/평야'),
        '황해북도': ('평지', 4.5, 2.0, 3.5, 'N', '구릉지/평야'),
    }
    
    # Check exact/partial match in known locations
    for k, v in known_locations.items():
        if k in name:
            return v
            
    # Defaults
    t_type = "기타"
    mobility = 3.0
    defense = 3.0
    obs = 3.0
    key_point = "N"
    desc = "자동 추론된 지형 정보"
    
    # Heuristics (Fallback)
    if any(k in name for k in ['고지', '산', '봉', '능선', 'Hill', 'Mountain']):
        t_type = "산악"
        mobility = 2.0  # 험지
        defense = 5.0   # 고지대 방어 유리
        obs = 5.0       # 관측 유리
        key_point = "Y" # 고지는 통상 요충지
        desc = "관측과 방어에 유리한 산악 지형"
        
    elif any(k in name for k in ['평야', '들', '논', '밭', 'Plain', 'Field']):
        t_type = "평지"
        mobility = 5.0  # 기동 용이
        defense = 1.0   # 엄폐물 부족
        obs = 3.0       # 평범
        key_point = "N"
        desc = "기동에 유리한 개활지"
        
    elif any(k in name for k in ['강', '천', '호수', 'River', 'Lake']):
        t_type = "하천"
        mobility = 1.0  # 도하 필요
        defense = 3.0   # 자연 장애물
        obs = 4.0       # 시야 개방
        key_point = "N"
        desc = "기동이 제한되는 하천 장애물"
        
    elif any(k in name for k in ['도시', '마을', '시내', 'City', 'Town', 'Village', 'APT']):
        t_type = "도시"
        mobility = 4.0  # 도로망 양호 but 건물 장애물
        defense = 4.0   # 건물 엄폐
        obs = 2.0       # 건물로 인한 시야 제한
        key_point = "Y" # 거점
        desc = "엄폐가 용이한 거주 지역"
        
    elif any(k in name for k in ['교차로', 'IC', '도로', 'Bridge', 'Junction']):
        t_type = "도로"
        mobility = 5.0
        defense = 2.0
        obs = 3.0
        key_point = "Y" # 교통 요충지
        desc = "교통의 결절점"
        
    elif any(k in name for k in ['계곡', 'Valley']):
        t_type = "산악"
        mobility = 2.0
        defense = 3.0
        obs = 1.0       # 시야 제한
        key_point = "N"
        desc = "기동과 관측이 제한되는 계곡"

    return t_type, mobility, defense, obs, key_point, desc

def enrich_terrain_data():
    data_lake = Path("data_lake")
    target_file = data_lake / "지형셀.xlsx"
    backup_file = data_lake / "지형셀.xlsx.bak_enrich"
    
    if not target_file.exists():
        print("[ERROR] Target file not found.")
        return

    # Backup
    shutil.copy2(target_file, backup_file)
    print(f"[INFO] Backup created: {backup_file}")
    
    try:
        df = pd.read_excel(target_file)
        
        updated_count = 0
        
        for idx, row in df.iterrows():
            # Check if critical fields are missing OR previously defaulted to '기타'
            should_update = (
                pd.isna(row['기동성등급']) or 
                pd.isna(row['방어유리도']) or 
                row['지형유형'] == '기타'
            )
            
            if should_update:
                name = row['지형명']
                t_type, mob, def_adv, obs_adv, key, desc = infer_tactical_values(name)
                
                # Update (Overwrite if '기타' or missing)
                df.at[idx, '지형유형'] = t_type
                df.at[idx, '기동성등급'] = mob
                df.at[idx, '방어유리도'] = def_adv
                df.at[idx, '관측유리도'] = obs_adv
                df.at[idx, '요충지여부'] = key
                df.at[idx, '설명'] = desc
                    
                updated_count += 1
                print(f"[UPDATE] {name}: Type={t_type}, Mob={mob}, Def={def_adv}, Obs={obs_adv}, Key={key}")
        
        if updated_count > 0:
            df.to_excel(target_file, index=False)
            print(f"[INFO] Successfully enriched {updated_count} rows.")
        else:
            print("[INFO] No rows needed enrichment.")
            
    except Exception as e:
        print(f"[ERROR] Enrichment failed: {e}")
        shutil.copy2(backup_file, target_file)

if __name__ == "__main__":
    enrich_terrain_data()
