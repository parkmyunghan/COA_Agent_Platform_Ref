# ui/components/scenario_mapper.py
# -*- coding: utf-8 -*-
"""
Scenario Mapper
시스템의 논리적 데이터(위협, 방책)를 지도 시각화를 위한 물리적 데이터(GeoJSON)로 변환
"""
import json
import random
import hashlib
from typing import Dict, List, Any
try:
    import streamlit as st
except ImportError:
    st = None

# 1. 지형/위치 데이터베이스 (가상 좌표)
# 실제 온톨로지에 좌표가 없는 경우 이 매핑 테이블을 사용
LOCATION_DB = {
    # 주요 도시 및 지점 (한반도)
    "PYONGYANG": {"lat": 39.0392, "lng": 125.7625, "name": "평양"},
    "SEOUL": {"lat": 37.5665, "lng": 126.9780, "name": "서울"},
    "KAESONG": {"lat": 37.9704, "lng": 126.5519, "name": "개성"},
    "WONSAN": {"lat": 39.1552, "lng": 127.4439, "name": "원산"},
    "NAMPO": {"lat": 38.7230, "lng": 125.4215, "name": "남포"},
    "SARIWON": {"lat": 38.5085, "lng": 125.7537, "name": "사리원"},
    "CHORWON": {"lat": 38.1464, "lng": 127.3133, "name": "철원"},
    "KANGNUNG": {"lat": 37.7519, "lng": 128.8760, "name": "강릉"},
    "HAEJU": {"lat": 38.0406, "lng": 125.7147, "name": "해주"},
    "HAMHUNG": {"lat": 39.9183, "lng": 127.5358, "name": "함흥"},
    "CHONGJIN": {"lat": 41.7919, "lng": 129.7758, "name": "청진"},
    "DMZ_WEST": {"lat": 37.95, "lng": 126.67, "name": "서부전선"},
    "DMZ_CENTER": {"lat": 38.25, "lng": 127.12, "name": "중부전선"},
    "DMZ_EAST": {"lat": 38.61, "lng": 128.35, "name": "동부전선"},
    # [FIX] 시나리오별 주요 지형/위협 식별자 매핑 추가
    "TERR010": {"lat": 37.85, "lng": 126.78, "name": "파주/개성 축선 (TERR010)"},
    "TERR001": {"lat": 37.95, "lng": 126.67, "name": "서부 전방 (TERR001)"},
    "TERR002": {"lat": 38.25, "lng": 127.12, "name": "중부 전방 (TERR002)"},
    "TERR003": {"lat": 38.61, "lng": 128.35, "name": "동부 전방 (TERR003)"},

}

# 2. 유닛 템플릿 (Milsymbol SIDC 코드)
UNIT_TEMPLATES = {
    # 적군 (Red)
    "RED_HQ": {"sidc": "SHGPE-----H----", "name": "적 지휘소"},
    "RED_MISSILE": {"sidc": "SHGPEWM---H----", "name": "미사일 기지"},
    "RED_MECHANIZED": {"sidc": "SHGPEV----L----", "name": "기계화 부대"},
    "RED_ARTILLERY": {"sidc": "SHGPEF----H----", "name": "포병 부대"},
    "RED_INFANTRY": {"sidc": "SHGPEI----H----", "name": "보병 부대"},
    "RED_AIR_RECON": {"sidc": "SHAPMF----", "name": "정찰기"},  # [NEW] Recon Plane
    "RED_AIR": {"sidc": "SHAP-------", "name": "항공기"},      # [NEW] General Air
    
    # 아군 (Blue)
    "BLUE_HQ": {"sidc": "SFGPM-----H----", "name": "아군 지휘소"},
    "BLUE_AIR": {"sidc": "SFFPF-----H----", "name": "전투비행단"},
    "BLUE_MISSILE": {"sidc": "SFGPW-----H----", "name": "미사일 부대"},
    "BLUE_MECHANIZED": {"sidc": "SFGPV----L----", "name": "기계화 보병"},
    "BLUE_INFANTRY": {"sidc": "SFGPI----H----", "name": "보병 부대"},
}

class ScenarioMapper:
    """논리적 시나리오 데이터를 GeoJSON 포맷으로 변환"""
    
    @staticmethod
    def _resolve_axis_coordinates(axis_id: str) -> List[List[float]]:
        """
        Resolve axis coordinates through 3-tier lookup:
        Axis ID → Terrain Cell Path → Coordinates
        
        Args:
            axis_id: Axis identifier (e.g., "AXIS01", "ns:AXIS01", or full URI)
            
        Returns:
            List of [lat, lng] coordinate pairs (GeoJSON order: [lng, lat])
        """
        import pandas as pd
        import logging
        import os
        
        logger = logging.getLogger(__name__)
        
        try:
            # Extract local name from URI if needed
            if axis_id.startswith("http://") or axis_id.startswith("ns:"):
                axis_id = axis_id.split('#')[-1].split('/')[-1].replace('ns:', '').replace('전장축선_', '')
            
            # Step 1: Load axis definition
            axis_file = "data_lake/전장축선.xlsx"
            if not os.path.exists(axis_file):
                logger.warning(f"Axis file not found: {axis_file}")
                return []
                
            axis_df = pd.read_excel(axis_file)
            axis_row = axis_df[axis_df["축선ID"] == axis_id]
            
            if axis_row.empty:
                logger.warning(f"Axis {axis_id} not found in 전장축선.xlsx")
                return []
            
            # Step 2: Parse terrain cell path
            terrain_path = axis_row.iloc[0]["주요지형셀목록"]
            if pd.isna(terrain_path) or not str(terrain_path).strip():
                logger.warning(f"Axis {axis_id} has no terrain cell path")
                return []
                
            terrain_ids = [t.strip() for t in str(terrain_path).split(',')]
            
            # Step 3: Load terrain cell coordinates
            terrain_file = "data_lake/지형셀.xlsx"
            if not os.path.exists(terrain_file):
                logger.warning(f"Terrain file not found: {terrain_file}")
                return []
                
            terrain_df = pd.read_excel(terrain_file)
            coordinates = []
            
            for terr_id in terrain_ids:
                terr_row = terrain_df[terrain_df["지형셀ID"] == terr_id]
                
                if terr_row.empty:
                    logger.warning(f"Terrain cell {terr_id} not found in axis {axis_id} path")
                    continue
                    
                # Parse "lng, lat" format from 좌표정보
                coord_str = terr_row.iloc[0]["좌표정보"]
                if pd.isna(coord_str):
                    logger.warning(f"Terrain cell {terr_id} has no coordinates")
                    continue
                    
                parts = str(coord_str).strip().split(',')
                if len(parts) != 2:
                    logger.warning(f"Invalid coordinate format for {terr_id}: {coord_str}")
                    continue
                    
                lng, lat = float(parts[0].strip()), float(parts[1].strip())
                coordinates.append([lng, lat])  # [MOD] Standardize to [lng, lat] for GeoJSON compatibility
            
            # Metadata extraction
            metadata = {
                "name": axis_row.iloc[0]["축선명"],
                "type": axis_row.iloc[0]["축선유형"],
                "direction": axis_row.iloc[0].get("작전방향", "")  # Use .get() to avoid KeyError if column missing
            }
            
            logger.info(f"✅ Resolved axis {axis_id}: {len(coordinates)} waypoints, Name: {metadata['name']}")
            return coordinates, metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve axis {axis_id}: {e}")
            import traceback
            traceback.print_exc()
            return [], {}
    
    @staticmethod
    def _validate_coordinates(coordinates: List, entity_id: str) -> bool:
        """좌표 유효성 검증"""
        if not coordinates or len(coordinates) == 0:
            # print(f"[WARN] No coordinates for {entity_id}")
            return False
        
        # Point case: [lng, lat]
        if isinstance(coordinates[0], (int, float)):
             if len(coordinates) != 2: return False
             lng, lat = coordinates
             if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                 print(f"[ERROR] Out of range: lat={lat}, lng={lng} for {entity_id}")
                 return False
             return True

        # LineString/Polygon case: [[lng, lat], ...]
        for coord in coordinates:
            if not (isinstance(coord, (list, tuple)) and len(coord) == 2):
                print(f"[ERROR] Invalid coordinate format: {coord} for {entity_id}")
                return False
                
            lng, lat = coord
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                print(f"[ERROR] Out of range: lat={lat}, lng={lng} for {entity_id}")
                return False
        
        return True
    
    @staticmethod
    def _normalize_combat_effectiveness(value: Any) -> float:
        """
        전투력 값을 0-1 범위로 정규화
        - 0-100 범위로 저장된 경우 0-1 범위로 변환
        - 0-1 범위는 그대로 사용
        - None이나 잘못된 값은 1.0 (기본값) 반환
        """
        try:
            if value is None:
                return 1.0
            
            combat_val = float(value)
            
            # 이미 0-1 범위인 경우
            if 0.0 <= combat_val <= 1.0:
                return combat_val
            
            # 0-100 범위인 경우 0-1로 정규화
            if 1.0 < combat_val <= 100.0:
                return combat_val / 100.0
            
            # 100보다 큰 경우 1.0으로 제한
            if combat_val > 100.0:
                return 1.0
            
            # 음수인 경우 0.0으로 제한
            if combat_val < 0.0:
                return 0.0
            
            return 1.0  # 기본값
        except (ValueError, TypeError):
            return 1.0  # 기본값

    @staticmethod
    def map_threats_to_geojson(threats: List[Dict], orchestrator: Any = None, selected_id: str = None) -> Dict:
        """위협 목록을 GeoJSON FeatureCollection으로 변환"""
        features = []
        
        # 디버깅: 입력 데이터 확인
        if not threats:
            return {"type": "FeatureCollection", "features": []}
        
        for i, threat in enumerate(threats):
            # 디버깅: 각 threat 처리 확인
            if not isinstance(threat, dict):
                continue
            
            # 1. 위치 결정 (우선순위: StatusManager > Excel 좌표 > Ontology > 위치명 매핑 > 랜덤)
            base_loc = None # 초기화 (이전 루프 값 잔존 방지)
            use_exact_coords = False
            lat_val = None
            lng_val = None

            # 1-0. StatusManager에서 실시간 좌표 최우선 조회
            # [FIX] 임무 중심 모드 지원: 임무ID도 entity_id로 사용
            entity_id = (threat.get("위협ID") or threat.get("threat_id") or 
                        threat.get("situation_id") or threat.get("임무ID") or threat.get("mission_id"))
            
            # [FIX] Excel 좌표정보를 먼저 확인 (StatusManager보다 우선)
            # Excel 좌표정보가 있으면 이를 우선 사용 (StatusManager는 실시간 업데이트용)
            coord_str = threat.get("좌표정보") or threat.get("coordinates")
            status_coords = None  # 변수 초기화 (디버깅용)
            if coord_str and isinstance(coord_str, str) and str(coord_str).strip() and str(coord_str).strip() != "N/A":
                try:
                    parts = [float(x.strip()) for x in str(coord_str).split(',')]
                    if len(parts) >= 2:
                        lng_val, lat_val = parts[0], parts[1]
                        base_loc = {
                            "lat": lat_val,
                            "lng": lng_val,
                            "name": threat.get("name") or threat.get("위협명") or entity_id
                        }
                        use_exact_coords = True
                        print(f"[INFO] Excel 좌표정보 우선 적용: {entity_id} -> ({lng_val}, {lat_val})")
                except Exception as e:
                    print(f"[WARN] 좌표정보 파싱 실패 ({entity_id}): {coord_str} - {e}")
            
            # [FIX] StatusManager에서 적군부대 상태 정보 조회 (좌표뿐만 아니라 제대, 이동속도, 전투력 등)
            enemy_unit_status = {}  # 적군부대 상태 정보 저장용
            # [FIX] 좌표가 있든 없든 적군부대 상태 정보는 항상 조회
            if orchestrator and entity_id:
                # 적군부대 상태 정보 조회 (위협ID, 위협명 모두 시도)
                enemy_unit_status = orchestrator.core.status_manager.get_entity_status(entity_id) or {}
                # 위협명으로도 시도
                threat_name = threat.get("name") or threat.get("위협명")
                if not enemy_unit_status and threat_name:
                    enemy_unit_status = orchestrator.core.status_manager.get_entity_status(threat_name) or {}
                
            # 1-1. StatusManager에서 실시간 좌표 조회 (Excel 좌표정보가 없는 경우만)
            if not base_loc and orchestrator and entity_id:
                # 좌표 조회
                status_coords = orchestrator.core.status_manager.get_coordinates(entity_id)
                if status_coords:
                    base_loc = {
                        "lat": status_coords[0],
                        "lng": status_coords[1],
                        "name": threat.get("name") or threat.get("위협명") or entity_id
                    }
                    use_exact_coords = True
                    print(f"[INFO] StatusManager 좌표 적용 (실시간): {entity_id} -> {status_coords}")

            # 1-2. 개별 위도/경도 컬럼 확인 (Excel 좌표정보와 StatusManager 모두 실패 시)

            # [PRIORITY 2] 개별 컬럼 확인 (이미 파싱된 경우)
            if not base_loc and not use_exact_coords:
                lat_val = (threat.get("latitude") or threat.get("lat") or 
                        threat.get("hasLatitude") or threat.get("위도") or
                        threat.get("latitude_val") or threat.get("y_coord"))
                lng_val = (threat.get("longitude") or threat.get("lng") or 
                        threat.get("hasLongitude") or threat.get("경도") or
                        threat.get("longitude_val") or threat.get("x_coord"))
            
            if lat_val and lng_val:
                try:
                    base_loc = {
                        "lat": float(lat_val), 
                        "lng": float(lng_val), 
                        "name": threat.get("name") or threat.get("위협명") or threat.get("위협ID") or threat.get("situation_id") or entity_id or "Unknown Location"
                    }
                    use_exact_coords = True
                except (ValueError, TypeError) as e:
                    pass
            
            # 1-2. 좌표가 없는 경우: 위치명 기반 매핑 시도
            name = (threat.get("name", "") or threat.get("위협명", "") or 
                   threat.get("위협ID", "") or threat.get("situation_id", "") or f"위협_{i}")
            description = (threat.get("description", "") or threat.get("상황설명", "") or 
                         threat.get("근거", "") or threat.get("additional_context", "") or "")
            
            # 발생장소 추출
            location = (threat.get("발생장소", "") or threat.get("location", "") or 
                       threat.get("위치", "") or "")
            
            # 명시적 ID 추출 (임무 중심 모드 지원)
            tid = str(threat.get("위협ID") or threat.get("threat_id") or threat.get("situation_id") or 
                     threat.get("임무ID") or threat.get("mission_id") or "").strip()

            if not use_exact_coords:
                # 1. ID 직접 매칭 (가장 정확)
                if tid and tid in LOCATION_DB:
                    base_loc = LOCATION_DB[tid]
                    print(f"[INFO] LOCATION_DB ID 직접 매칭: {entity_id} -> {tid}")
                else:
                    # 2. 텍스트 검색 (더 엄격하게: 위치명이 정확히 일치하거나 명시적으로 언급된 경우만)
                    full_text = f"{tid} {name} {description} {location}".lower()
                    matched = False
                    for key, loc in LOCATION_DB.items():
                        loc_name = loc.get("name", "").lower()
                        # 위치명이 텍스트에 정확히 포함되고, 위협ID나 일반적인 단어가 아닌 경우만 매칭
                        if loc_name and len(loc_name) > 1 and loc_name in full_text:
                            # "서울" 같은 일반적인 단어가 우연히 포함되는 것을 방지
                            # 위협ID나 일반적인 단어가 아닌 실제 위치명인 경우만
                            if key != "SEOUL" or ("서울" in full_text and len(full_text) < 100):  # SEOUL은 더 엄격하게
                                base_loc = loc
                                matched = True
                                print(f"[INFO] LOCATION_DB 텍스트 매칭: {entity_id} -> {key} ({loc_name})")
                                break
                    if not matched:
                        print(f"[DEBUG] LOCATION_DB 텍스트 매칭 실패: {entity_id}, full_text: {full_text[:100]}")
            
            # [PRIORITY 3] 발생위치셀ID를 통한 지형셀 좌표 조회 (StatusManager/좌표정보/LocationDB 모두 실패 시)
            # 발생위치셀ID가 있으면 해당 지형셀의 좌표를 위협 위치로 사용
            if not base_loc and not use_exact_coords:
                cell_id = threat.get("발생위치셀ID") or threat.get("location_cell_id") or threat.get("배치지형셀ID")
                if cell_id and str(cell_id).strip() and str(cell_id).strip() != "N/A":
                    try:
                        import pandas as pd
                        import os
                        terrain_file = "data_lake/지형셀.xlsx"
                        if os.path.exists(terrain_file):
                            terrain_df = pd.read_excel(terrain_file)
                            cell_id_str = str(cell_id).strip()
                            terr_row = terrain_df[terrain_df["지형셀ID"] == cell_id_str]
                            
                            if not terr_row.empty:
                                coord_str = terr_row.iloc[0].get("좌표정보")
                                if pd.notna(coord_str) and coord_str:
                                    try:
                                        parts = str(coord_str).strip().split(',')
                                        if len(parts) >= 2:
                                            lng_val, lat_val = float(parts[0].strip()), float(parts[1].strip())
                                            base_loc = {
                                                "lat": lat_val,
                                                "lng": lng_val,
                                                "name": f"{name} (from Terrain Cell {cell_id_str})"
                                            }
                                            use_exact_coords = True
                                            print(f"[INFO] 지형셀 기반 위협 위치 조회: {entity_id} -> {cell_id_str} -> ({lng_val}, {lat_val})")
                                    except Exception as e:
                                        print(f"[WARN] 지형셀 좌표 파싱 실패 ({cell_id_str}): {e}")
                    except Exception as e:
                        print(f"[WARN] 지형셀 좌표 조회 실패 ({cell_id}): {e}")
            
            # [PRIORITY 4] 관련 축선 정보 활용 (발생위치셀ID도 실패 시)
            # 축선 ID가 있으면 해당 축선의 중심점을 위협 위치로 추정
            if not base_loc and not use_exact_coords:
                axis_id = threat.get("관련축선ID") or threat.get("axis_id") or threat.get("related_axis_id")
                if axis_id and str(axis_id).strip() and str(axis_id).strip() != "N/A": # related_axis_id가 존재할 때만 시도
                    # 축선 좌표 조회 (방책 매핑 로직 재사용)
                    axis_coords, _ = ScenarioMapper._resolve_axis_coordinates(str(axis_id).strip())
                    if axis_coords and len(axis_coords) > 0:
                        # 축선의 중간 지점 계산
                        mid_idx = len(axis_coords) // 2
                        mid_pt = axis_coords[mid_idx] # [lng, lat]
                        
                        base_loc = {
                            "lat": mid_pt[1], # lat is at index 1
                            "lng": mid_pt[0], # lng is at index 0
                            "name": f"{name} (Estimated from Axis)"
                        }
                        print(f"[INFO] 축선 기반 위협 위치 추정: {entity_id} -> {axis_id} -> {base_loc}")
            
            # 1-5. 좌표가 여전히 없는 경우: 기본값(평양) 사용
            if base_loc is None:
                print(f"[WARN] 위협 {entity_id}의 좌표를 찾을 수 없어 기본값(평양) 사용")
                base_loc = LOCATION_DB["PYONGYANG"]

            # 데이터 기반의 고정된 오프셋 사용 (새로고침 시 위치 변동 방지)
            seed_str = f"{threat.get('threat_id', '')}{threat.get('name', '')}{threat.get('위협ID', '')}{i}"
            seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
            random_gen = random.Random(seed_hash)
            
            # 약간의 고정된 오프셋 추가 (겹침 방지)
            offset_range = 0.005 if use_exact_coords else 0.02
            
            # base_loc이 None이 아님을 보장
            lat = base_loc["lat"] + random_gen.uniform(-offset_range, offset_range)
            lng = base_loc["lng"] + random_gen.uniform(-offset_range, offset_range)
            
            # 2. 심볼 결정
            threat_type = (threat.get("type", "") or threat.get("위협유형", "") or 
                          threat.get("threat_type", "") or "Unknown")
            sidc = UNIT_TEMPLATES["RED_HQ"]["sidc"]
            
            type_text = f"{threat_type} {name} {description}".lower()
            
            if "정찰" in type_text or "recon" in type_text:
                sidc = UNIT_TEMPLATES["RED_AIR_RECON"]["sidc"]  # [FIX] Prioritize Recon
            elif "미사일" in type_text or "missile" in type_text:
                sidc = UNIT_TEMPLATES["RED_MISSILE"]["sidc"]
            elif "기갑" in type_text or "tank" in type_text or "기계화" in type_text or "전차" in type_text:
                sidc = UNIT_TEMPLATES["RED_MECHANIZED"]["sidc"]
            elif "포병" in type_text or "artillery" in type_text or "방사포" in type_text:
                sidc = UNIT_TEMPLATES["RED_ARTILLERY"]["sidc"]
            elif "보병" in type_text or "infantry" in type_text:
                sidc = UNIT_TEMPLATES["RED_INFANTRY"]["sidc"]
            elif "항공" in type_text or "air" in type_text or "plane" in type_text or "전투기" in type_text:
                sidc = UNIT_TEMPLATES["RED_AIR"]["sidc"]
                
            # 3. Feature 생성 (Point)
            display_name = name
            if name.isdigit() or len(name) < 2:
                display_name = f"{threat_type}_{name}"
            
            # 맵 상에 표시될 짧은 레이블
            short_type = threat_type[:2] if len(threat_type) > 2 else threat_type
            label = f"{short_type}_{threat.get('위협ID') or f'T{i}'}"

            # 현재 선택된 위협/임무인지 확인 (임무 중심 모드 지원)
            is_selected = False
            curr_id = (threat.get("위협ID") or threat.get("situation_id") or threat.get("ID") or
                      threat.get("임무ID") or threat.get("mission_id"))
            if selected_id and curr_id:
                # ID 매칭 (문자열 비교)
                if str(selected_id).strip() == str(curr_id).strip():
                    is_selected = True

            # Coordinate Validation
            if not ScenarioMapper._validate_coordinates([lng, lat], curr_id or f"threat_{i}"):
                print(f"[WARN] Invalid coordinates for threat {curr_id}, using default")
                lat, lng = 39.0392, 125.7625 # Fallback to Pyongyang
            
            # [DEBUG] 최종 좌표 로깅 (상세)
            coord_source = "Unknown"
            if use_exact_coords:
                if coord_str and isinstance(coord_str, str):
                    coord_source = "Excel 좌표정보"
                elif status_coords:
                    coord_source = "StatusManager"
                elif lat_val and lng_val:
                    coord_source = "개별 컬럼"
            elif base_loc:
                if base_loc.get("name", "").endswith("(from Terrain Cell"):
                    coord_source = "지형셀"
                elif base_loc.get("name", "").endswith("(Estimated from Axis)"):
                    coord_source = "축선"
                elif base_loc.get("name") in [loc.get("name") for loc in LOCATION_DB.values()]:
                    coord_source = "LOCATION_DB"
                else:
                    coord_source = "기본값(평양)"
            print(f"[DEBUG] 위협 {curr_id} 최종 좌표: ({lng}, {lat}), 소스: {coord_source}, base_loc: {base_loc.get('name', 'N/A') if base_loc else 'None'}")

            # [NEW] 배치위치 정보 추가
            deployment_location = None
            cell_id = threat.get("발생위치셀ID") or threat.get("location_cell_id") or threat.get("배치지형셀ID")
            if cell_id:
                try:
                    import pandas as pd
                    import os
                    terrain_file = "data_lake/지형셀.xlsx"
                    if os.path.exists(terrain_file):
                        terrain_df = pd.read_excel(terrain_file)
                        cell_row = terrain_df[terrain_df["지형셀ID"] == str(cell_id).strip()]
                        if not cell_row.empty:
                            deployment_location = cell_row.iloc[0].get("지형명") or cell_row.iloc[0].get("지역") or f"셀{cell_id}"
                except Exception as e:
                    print(f"[WARN] 적군 배치지형셀ID 조회 실패: {e}")

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat] # GeoJSON [lng, lat]
                },
                "properties": {
                    "id": curr_id or f"threat_{i}",
                    "name": display_name,
                    "label": label,
                    "sidc": sidc,
                    "type": "RED",
                    "threat_type": threat_type,
                    "description": description,
                    "threat_radius": (threat.get("radius_km", 20) if threat.get("radius_km") else 20) * 1000,
                    "threat_level": threat.get("threat_level") or threat.get("위협수준_점수", 0.5),
                    "situation_id": curr_id,
                    "organization": enemy_unit_status.get("소속부대") or threat.get("소속부대", "적군"),
                    "mission": threat.get("임무", "공격"),
                    "uri": threat.get("threat_uri") or threat.get("uri") or None,
                    "selected": is_selected,  # [NEW] 선택 상태 표시
                    # [FIX] 실제 식별된 위협상황인지 배경 적군인지 구분
                    "is_identified_threat": threat.get("is_identified_threat", False),  # 기본값: False (배경 적군)
                    
                    # Korean keys
                    "위협명": display_name,
                    "위협유형": threat_type,
                    "위협수준": threat.get("위협수준", ""),
                    
                    # [FIX] StatusManager에서 가져온 적군부대 상세 정보 우선 사용
                    # MIL-STD-2525D Modifiers
                    "uniqueDesignation": enemy_unit_status.get("고유명칭") or enemy_unit_status.get("부대명") or threat.get("고유명칭") or threat.get("uniqueDesignation") or curr_id,
                    "higherFormation": enemy_unit_status.get("상급부대") or threat.get("상급부대") or threat.get("higherFormation"),
                    
                    # [FIX] 0 값을 유효한 값으로 처리하기 위한 로직
                    "direction": float(enemy_unit_status.get("이동방향") if enemy_unit_status.get("이동방향") is not None else (threat.get("이동방향") if threat.get("이동방향") is not None else (threat.get("direction") if threat.get("direction") is not None else 0.0))),
                    "speed": float(enemy_unit_status.get("이동속도_kmh") if enemy_unit_status.get("이동속도_kmh") is not None else (enemy_unit_status.get("이동속도") if enemy_unit_status.get("이동속도") is not None else (threat.get("이동속도") if threat.get("이동속도") is not None else (threat.get("speed") if threat.get("speed") is not None else 0.0)))),
                    
                    "status": enemy_unit_status.get("상태") or threat.get("상태") or threat.get("status", "Operational"),
                    "combatEffectiveness": ScenarioMapper._normalize_combat_effectiveness(
                        enemy_unit_status.get("전투력지수") or enemy_unit_status.get("전투력") or 
                        threat.get("전투력") or threat.get("combatEffectiveness", 1.0)
                    ),
                    # [FIX] 적군부대현황 테이블의 추가 필드
                    "제대": enemy_unit_status.get("제대") or threat.get("제대") or "",
                    "병종": enemy_unit_status.get("병종") or threat.get("병종") or "",
                    "감지범위_km": enemy_unit_status.get("감지범위_km") or threat.get("감지범위_km") or None,
                    
                    # [FIX] 0 값을 유효한 값으로 처리하기 위한 로직 (한글 키)
                    "이동속도": enemy_unit_status.get("이동속도_kmh") if enemy_unit_status.get("이동속도_kmh") is not None else (enemy_unit_status.get("이동속도") if enemy_unit_status.get("이동속도") is not None else (threat.get("이동속도") if threat.get("이동속도") is not None else None)),
                    "이동방향": enemy_unit_status.get("이동방향") if enemy_unit_status.get("이동방향") is not None else (threat.get("이동방향") if threat.get("이동방향") is not None else None),
                    
                    # [FIX] 전투력 값 정규화 (0-100 범위를 0-1 범위로 변환)
                    "전투력": ScenarioMapper._normalize_combat_effectiveness(
                        enemy_unit_status.get("전투력지수") or enemy_unit_status.get("전투력") or threat.get("전투력")
                    ) if (enemy_unit_status.get("전투력지수") or enemy_unit_status.get("전투력") or threat.get("전투력")) else None,
                    
                    # [NEW] 배치위치 정보
                    "deployment_location": deployment_location or "정보 없음",
                    "deployment_cell_id": cell_id,
                    
                    # 0 값 전달을 위해 원본 값 보존
                    "raw_speed": enemy_unit_status.get("이동속도_kmh") or enemy_unit_status.get("이동속도") or threat.get("이동속도"),
                    "raw_direction": enemy_unit_status.get("이동방향") or threat.get("이동방향"),
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }

    @staticmethod
    def map_coa_to_geojson(coa: Dict, threat_features: Dict, orchestrator: Any = None) -> Dict:
        """
        선택된 방책(COA)을 GeoJSON으로 변환
        아군 부대 위치(Point) 및 이동 경로(LineString) 생성
        """
        # [DEBUG] 함수 호출 추적
        coa_id = coa.get("coa_id") or coa.get("id") or "Unknown"
        has_orchestrator = orchestrator is not None
        print(f"[ScenarioMapper] map_coa_to_geojson: coa_id={coa_id}, orchestrator={'✓' if has_orchestrator else '✗'}")
        
        features = []
        
        # 위협(적군) 위치 참조를 위해 처리
        threat_locs = []
        if threat_features and "features" in threat_features:
            for f in threat_features["features"]:
                if f["geometry"]["type"] == "Point":
                    threat_locs.append(f["geometry"]["coordinates"])
        
        target_loc = threat_locs[0] if threat_locs else [125.7625, 39.0392] # 기본 평양
        
        coa_name = coa.get("coa_name", coa.get("name", "")).lower()
        coa_type = coa.get("coa_type", coa.get("type", "defense")).lower()
        coa_desc = coa.get("description", "").lower()
        full_info = f"{coa_name} {coa_type} {coa_desc}"
        full_text = full_info
        
        # 방책 타입에 따른 아군 배치 및 경로 생성
        blue_units = []
        
        # [MOD] participating_units 데이터가 있으면 이를 우선 사용
        explicit_units_raw = coa.get("participating_units", [])
        
        # 데이터 정규화 (String -> List[Dict])
        explicit_units = []
        if isinstance(explicit_units_raw, str):
            # 콤마로 구분된 부대 명칭들
            unit_names = [name.strip() for name in explicit_units_raw.split(',') if name.strip()]
            for name in unit_names:
                explicit_units.append({"name": name, "type": "unknown"})
        elif isinstance(explicit_units_raw, list):
            for u in explicit_units_raw:
                if isinstance(u, str):
                    explicit_units.append({"name": u, "type": "unknown"})
                elif isinstance(u, dict):
                    explicit_units.append(u)
        
        if explicit_units:
            # 중복 부대 제거 (명칭 기준)
            seen_names = set()
            unique_units = []
            for u in explicit_units:
                name = u.get("name", "알 수 없는 부대")
                if name not in seen_names:
                    seen_names.add(name)
                    unique_units.append(u)
            
            for idx, u in enumerate(unique_units):
                u_name = u.get("name", "알 수 없는 부대")
                u_type = u.get("type", "").lower() if u.get("type") else ""
                
                # 1. 위치 결정 (우선순위: StatusManager > 기본 위치)
                sidc = UNIT_TEMPLATES["BLUE_INFANTRY"]["sidc"]
                pos = [127.1, 37.9] # 기본값

                # [FIX] StatusManager에서 부대 상태 정보 조회 (좌표뿐만 아니라 제대, 이동속도, 이동방향 등)
                unit_id = u_name # 부대명 자체가 ID인 경우가 많음
                # [FIX] 아군부대ID도 시도 (u 객체에 ID가 있을 수 있음)
                unit_id_candidates = [
                    u.get("unit_id") or u.get("아군부대ID") or u.get("id"),
                    u_name
                ]
                unit_status = {}  # 부대 상태 정보 저장용
                if orchestrator:
                    # 부대 상태 정보 조회 (여러 ID 후보 시도)
                    for candidate_id in unit_id_candidates:
                        if candidate_id:
                            unit_status = orchestrator.core.status_manager.get_entity_status(str(candidate_id)) or {}
                            if unit_status:
                                unit_id = str(candidate_id)
                                break
                    # 좌표 조회
                    status_coords = orchestrator.core.status_manager.get_coordinates(unit_id)
                    if status_coords:
                        pos = [status_coords[1], status_coords[0]] # [lng, lat]
                        print(f"[INFO] StatusManager 부대 좌표 적용: {unit_id} -> {pos}")
                    else:
                        # 좌표가 없을 때만 기존 지터링 로직 모델 사용
                        # [MOD] COA별 위치 차별화를 위해 COA ID 기반 오프셋 추가
                        coa_seed = sum(ord(c) for c in (coa.get("coa_id") or coa_name)) 
                        
                        # 기본 지터링 (부대 인덱스 기반)
                        base_jitter_lat = (idx % 3) * 0.02
                        base_jitter_lng = (idx // 3) * 0.02
                        
                        # COA별 추가 오프셋 (겹침 방지) - 최대 0.1도 (약 10km) 변동
                        coa_offset_lat = ((coa_seed % 10) - 5) * 0.015
                        coa_offset_lng = ((coa_seed % 11) - 5) * 0.015
                        
                        final_jitter_lat = base_jitter_lat + coa_offset_lat
                        final_jitter_lng = base_jitter_lng + coa_offset_lng
                        
                        if "공전" in full_info or "공군" in full_info or "전투비행단" in u_name:
                            pos = [128.9 + final_jitter_lng, 37.7 + final_jitter_lat] if "동부" in coa_name else [126.9 + final_jitter_lng, 36.8 + final_jitter_lat]
                            sidc = UNIT_TEMPLATES["BLUE_AIR"]["sidc"]
                        elif "미사일" in full_info or "유도탄" in u_name:
                            pos = [127.5 + final_jitter_lng, 37.2 + final_jitter_lat]
                            sidc = UNIT_TEMPLATES["BLUE_MISSILE"]["sidc"]
                        elif "기계화" in full_info or "기보" in full_info or "전차" in u_name:
                            pos = [127.0 + final_jitter_lng, 37.8 + final_jitter_lat]
                            sidc = UNIT_TEMPLATES["BLUE_MECHANIZED"]["sidc"]
                        else:
                            pos = [127.1 + final_jitter_lng, 37.9 + final_jitter_lat]
                            sidc = UNIT_TEMPLATES["BLUE_INFANTRY"]["sidc"]
                else:
                    # Orchestrator가 없으면 기존 로직 유지
                    jitter_lat = (idx % 3) * 0.05
                    jitter_lng = (idx // 3) * 0.05
                    # ... (생략 가능하지만 안전을 위해 유지)
                    if "공전" in full_info or "공군" in full_info or "전투비행단" in u_name:
                        pos = [128.9 + jitter_lng, 37.7 + jitter_lat]
                    # etc... (Signatures were updated, content below continues)
                
                # [FIX] StatusManager에서 가져온 정보 우선 사용, 없으면 기본값
                # [NEW] 배치위치 정보 추가
                deployment_location = None
                if unit_status:
                    # 배치지형셀ID로 위치명 조회
                    cell_id = unit_status.get("배치지형셀ID")
                    if cell_id:
                        try:
                            import pandas as pd
                            import os
                            terrain_file = "data_lake/지형셀.xlsx"
                            if os.path.exists(terrain_file):
                                terrain_df = pd.read_excel(terrain_file)
                                cell_row = terrain_df[terrain_df["지형셀ID"] == str(cell_id).strip()]
                                if not cell_row.empty:
                                    deployment_location = cell_row.iloc[0].get("지형명") or cell_row.iloc[0].get("지역") or f"셀{cell_id}"
                        except Exception as e:
                            safe_print(f"[WARN] 배치지형셀ID 조회 실패: {e}")
                
                blue_units.append({
                    "name": u_name,
                    "sidc": sidc,
                    "pos": pos,
                    # [FIX] 제대와 병종 구분하여 저장
                    "unit_type": unit_status.get("제대") or u_type or "unknown",
                    "unit_class": unit_status.get("병종") or "",
                    "organization": unit_status.get("소속부대") or u.get("organization", "대한민국 육군"),
                    "higher_formation": unit_status.get("상급부대") or unit_status.get("소속부대") or "대한민국 육군",
                    "mission": u.get("mission", coa_type),
                    "unit_uri": u.get("uri") or u.get("unit_uri"),
                    # [NEW] 배치위치 정보
                    "deployment_location": deployment_location or "배치지 정보 없음",
                    "deployment_cell_id": unit_status.get("배치지형셀ID") or unit_status.get("배치축선ID"),
                    # [FIX] 0 값을 유효한 값으로 처리하기 위한 로직
                    "이동속도": unit_status.get("이동속도_kmh") if unit_status.get("이동속도_kmh") is not None else (unit_status.get("이동속도") if unit_status.get("이동속도") is not None else (unit_status.get("speed") if unit_status.get("speed") is not None else None)),
                    "이동방향": unit_status.get("이동방향") if unit_status.get("이동방향") is not None else (unit_status.get("direction") if unit_status.get("direction") is not None else None),
                    
                    # [FIX] 전투력 값 정규화 (0-100 범위를 0-1 범위로 변환)
                    "전투력": ScenarioMapper._normalize_combat_effectiveness(
                        unit_status.get("전투력지수") or unit_status.get("전투력") or unit_status.get("combatEffectiveness")
                    ) if (unit_status.get("전투력지수") or unit_status.get("전투력") or unit_status.get("combatEffectiveness")) else None,
                    "combatEffectiveness": ScenarioMapper._normalize_combat_effectiveness(
                        unit_status.get("전투력지수") or unit_status.get("전투력") or unit_status.get("combatEffectiveness") or 1.0
                    ),
                    "상태": unit_status.get("상태") or unit_status.get("가용상태") or unit_status.get("status") or "Operational",
                    "고유명칭": unit_status.get("고유명칭") or unit_status.get("uniqueDesignation") or u_name,
                    "제대": unit_status.get("제대") or u_type or "unknown",
                    "병종": unit_status.get("병종") or "",
                })
        
        # [FIX] 데이터가 없을 경우 기존 Fallback 유지 (하지만 가급적 데이터를 따름)
        # 모든 방책에 최소 1개 이상의 부대가 생성되도록 보장
        if not blue_units:
            if "공중" in full_text or "air" in full_text or "strike" in full_text or "선제" in full_text:
                if "강릉" in full_text or "east" in coa_name:
                    start_loc = [128.9, 37.7]
                    unit_name = "제18전투비행단"
                else:
                    start_loc = [126.9, 36.8]
                    unit_name = "제20전투비행단"
                blue_units.append({"name": unit_name, "sidc": UNIT_TEMPLATES["BLUE_AIR"]["sidc"], "pos": start_loc})
            elif "미사일" in full_text or "missile" in full_text:
                blue_units.append({"name": "유도탄사령부", "sidc": UNIT_TEMPLATES["BLUE_MISSILE"]["sidc"], "pos": [127.5, 37.2]})
            elif "반격" in full_text or "counter" in full_text or "역습" in full_text or "counterattack" in full_text:
                # 반격/역습 방책은 기계화 부대 + 포병 조합
                blue_units.append({"name": "제1기계화보병사단", "sidc": UNIT_TEMPLATES["BLUE_MECHANIZED"]["sidc"], "pos": [127.0, 37.8]})
                blue_units.append({"name": "제1포병여단", "sidc": UNIT_TEMPLATES["BLUE_MISSILE"]["sidc"], "pos": [127.2, 37.9]})
            else:
                # 기본: 기계화 보병 사단
                blue_units.append({"name": "제1기계화보병사단", "sidc": UNIT_TEMPLATES["BLUE_MECHANIZED"]["sidc"], "pos": [127.0, 37.8]})
            
        # [NEW] 고급 시각화 데이터 처리 (Advanced Visualization with Object-Centric Model)
        vis_data = coa.get("visualization_data", {})
        has_custom_graphics = False
        
        # [DEBUG] visualization_data 확인
        print(f"[ScenarioMapper] COA {coa_id} visualization_data: {bool(vis_data)}, keys: {list(vis_data.keys()) if vis_data else []}")
        
        # ==============================================================
        # PRIORITY 1: Check for axis reference (new object-centric method)
        # ==============================================================
        main_axis_id = vis_data.get("main_axis_id")
        if main_axis_id:
            print(f"[ScenarioMapper] COA {coa_id} references axis: {main_axis_id}")
            coordinates, axis_meta = ScenarioMapper._resolve_axis_coordinates(main_axis_id)
            
            if coordinates and ScenarioMapper._validate_coordinates(coordinates, main_axis_id):
                has_custom_graphics = True
                # [MOD] axis_coords are now already in [lng, lat] format
                geo_coords = coordinates
                
                # Determine proper label from metadata if available
                axis_name = axis_meta.get("name", main_axis_id)
                axis_type = axis_meta.get("type", "Axis")
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": geo_coords
                    },
                    "properties": {
                        "type": "TACTICAL_GRAPHIC",
                        "graphic_type": "Axis",
                        "style": "dashed",
                        "color": "#00a8ff",
                        "coa_id": coa.get("coa_id") or coa.get("id") or "",
                        "axis_id": main_axis_id,
                        "label": axis_name, # Use actual Excel name
                        "axis_type": axis_type, # Use actual Excel type
                        "description": f"{axis_type} - {vis_data.get('main_effort', '')}"
                    }
                })
                print(f"[ScenarioMapper] ✅ Rendered axis {main_axis_id} ({axis_name}) with {len(coordinates)} waypoints")
            else:
                print(f"[ScenarioMapper] ⚠️ Failed to resolve coordinates for axis {main_axis_id}. Will rely on fallback Blue Units generation.")
                has_custom_graphics = False # Force fallback to standard unit generation
        else:
             print(f"[ScenarioMapper] No main_axis_id found for COA {coa_id}")
        
        # ==============================================================
        # FALLBACK: Old method with hardcoded coordinates (backward compatibility)
        # ==============================================================
        if not has_custom_graphics and vis_data.get("graphics"):
            try:
                raw_g = vis_data["graphics"]
                print(f"[INFO] Using fallback hardcoded graphics: {raw_g[:50]}...")
                # Format: "Type:[(lat,lng),(lat,lng)]"
                # 예: "Axis:[(37.5,127.0),(37.9,126.8),(38.1,126.6)]"
                g_type, g_coords_str = raw_g.split(':[')
                g_coords_str = g_coords_str.rstrip(']')
                
                points = []
                # (lat,lng) 쌍 추출
                # 정규식으로 숫자 쌍 추출이 더 안전함
                import re
                matches = re.findall(r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)', g_coords_str)
                for lat_s, lng_s in matches:
                    points.append([float(lng_s), float(lat_s)]) # GeoJSON: [lng, lat]
                
                if points:
                    has_custom_graphics = True
                    propertiess = {
                        "type": "TACTICAL_GRAPHIC",
                        "graphic_type": g_type, # Axis, Block, PointTarget
                        "style": "solid", 
                        "color": "#00a8ff",  # 파란색 (청색) - 전술 그래픽 통일 색상
                        "coa_id": coa.get("coa_id") or coa.get("id") or "",
                        "label": vis_data.get("action_type", g_type),
                        "description": f"{vis_data.get('main_effort', '')} - {vis_data.get('phasing', '')}"
                    }
                    
                    # 그래픽 타입별 지오메트리 생성
                    geometry = {"type": "LineString", "coordinates": points}
                    
                    if g_type == "Block":
                        # Block은 선을 포함하는 폴리곤으로 표현 (간단히 선의 버퍼 영역)
                        # 여기선 단순화를 위해 닫힌 LineString으로 표현하거나 별도 처리
                        # 파일럿에선 굵은 선으로 처리
                        propertiess["stroke-width"] = 4
                        propertiess["style"] = "solid"
                    elif g_type == "PointTarget":
                        geometry = {"type": "Point", "coordinates": points[0]}
                    elif g_type == "Axis":
                         # 축선은 화살표 처리 (프론트엔드 스타일링 의존)
                         propertiess["style"] = "dashed" # 계획된 기동로
                    
                    features.append({
                        "type": "Feature",
                        "geometry": geometry,
                        "properties": propertiess
                    })
                    print(f"[INFO] Fallback 전술 그래픽 생성: {g_type} - {len(points)} points")
                    
            except Exception as e:
                print(f"[WARN] Fallback 전술 그래픽 파싱 실패: {e}")
        
        # 아군 Feature 생성
        for i, unit in enumerate(blue_units):
            # Validate coordinates
            if not ScenarioMapper._validate_coordinates(unit["pos"], unit.get("name")):
                print(f"[WARN] Invalid coordinates for unit {unit.get('name')}, skipping")
                continue

            # Unit Point
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": unit["pos"]
                },
                "properties": {
                    "id": f"blue_{i}",
                    "name": unit["name"],
                    "sidc": unit["sidc"],
                    "type": "BLUE",
                    # 온톨로지 URI 추가
                    "unit_uri": unit.get("unit_uri") or unit.get("uri") or None,
                    "coa_id": coa.get("coa_id", ""),
                    # 정적 정보
                    "organization": unit.get("organization", ""),
                    "unit_type": unit.get("unit_type", ""),
                    "unit_class": unit.get("unit_class", ""), # [NEW] 병종
                    "higher_formation": unit.get("higher_formation", ""), # [NEW] 상급부대
                    "deployment_location": unit.get("deployment_location", ""), # [NEW] 배치위치
                    "deployment_cell_id": unit.get("deployment_cell_id", ""), # [NEW] 배치지형셀
                    
                    # 동적 상태
                    "mission": unit.get("mission", ""),
                    "availability": unit.get("availability", "available"),
                    # 추론 연계 정보
                    "coa_exclusion_reason": unit.get("coa_exclusion_reason", ""),
                    
                    # [NEW] MIL-STD-2525D Modifiers & Kinetic Data
                    "uniqueDesignation": unit.get("고유명칭") or unit.get("uniqueDesignation") or unit.get("name"),
                    "higherFormation": unit.get("higher_formation") or unit.get("상급부대") or unit.get("higherFormation") or unit.get("organization"),
                    "direction": float(unit.get("이동방향") if unit.get("이동방향") is not None else (unit.get("direction") if unit.get("direction") is not None else 0.0)),
                    "speed": float(unit.get("이동속도") if unit.get("이동속도") is not None else (unit.get("speed") if unit.get("speed") is not None else 0.0)),
                    "status": unit.get("상태") or unit.get("status", "Operational"),
                    "combatEffectiveness": float(unit.get("combatEffectiveness") or unit.get("전투력") or 1.0),
                    # [FIX] 한글 키 추가 (팝업에서 사용)
                    "제대": unit.get("제대") or unit.get("unit_type") or "",
                    "병종": unit.get("병종") or unit.get("unit_class") or "",
                    "배치위치": unit.get("deployment_location") or "",
                    "배치지형셀ID": unit.get("deployment_cell_id") or "",
                    "전투력": float(unit.get("combatEffectiveness") or unit.get("전투력") or 1.0),
                    # 0 값 전달을 위해 원본 값 보존
                    "raw_speed": unit.get("이동속도"),
                    "raw_direction": unit.get("이동방향"),
                }
            })
            
            # Action Path (LineString) - 아군 -> 적군 (곡선 기동)
            # [MOD] 고급 그래픽(has_custom_graphics)이 있으면 개별 부대 이동선은 생략하거나 보조적으로 표시
            # 여기서는 고급 그래픽이 있으면 생략하여 깔끔하게 표현
            if not has_custom_graphics:
                # 스타일 결정 (Visualization Data 우선 적용)
                arrow_style = "dashed" 
                if "preemptive" in coa_type: arrow_style = "solid"
                
                vis_style_val = vis_data.get("style", "").lower()
                if "solid" in vis_style_val: arrow_style = "solid"
                elif "dashed" in vis_style_val: arrow_style = "dashed"
                
                # 주노력 여부에 따른 두께/색상 조정
                is_main = vis_data.get("main_effort", "N").upper() == "Y"
                
                # [NEW] 방책 명칭에서 '주공' 검색하여 자동 식별 (데이터 미흡 대비)
                if not is_main and ("주공" in coa_name or "주노력" in coa_name or "main" in coa_name):
                    is_main = True
                    
                arrow_weight = 7 if is_main else 3
                arrow_color = "#e74c3c" if is_main else "#00a8ff" # 주노력은 붉은색 강조, 기본은 청색
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": ScenarioMapper._generate_curve(unit["pos"], target_loc)
                    },
                    "properties": {
                        "type": "ARROW",
                        "style": arrow_style,
                        "color": arrow_color,
                        "weight": arrow_weight,
                        "is_main_effort": is_main,
                        "phasing": vis_data.get("phasing", "Phase 1"),
                        "coa_uri": coa.get("coa_uri") or coa.get("uri") or None,
                        "coa_id": coa.get("coa_id", ""),
                        "coa_name": coa.get("coa_name", coa.get("name", "")),
                        "coa_type": coa_type,
                        "label": "주공(Main Effort)" if is_main else "조공(Supporting)",
                        "participating_units": coa.get("participating_units", []),
                        "success_probability": coa.get("success_probability", 0.5),
                    }
                })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }

    @staticmethod
    def _generate_curve(start: List[float], end: List[float], num_points: int = 20) -> List[List[float]]:
        """두 지점 사이에 곡선(Arc) 좌표 생성"""
        import math
        
        lat1, lng1 = start[1], start[0]
        lat2, lng2 = end[1], end[0]
        
        mid_lat = (lat1 + lat2) / 2
        mid_lng = (lng1 + lng2) / 2
        
        dist = math.sqrt((lat2 - lat1)**2 + (lng2 - lng1)**2)
        
        dx = lng2 - lng1
        dy = lat2 - lat1
        
        offset_power = 0.2
        ctrl_lng = mid_lng - (dy * offset_power)
        ctrl_lat = mid_lat + (dx * offset_power)
        
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            plng = ((1-t)**2 * lng1) + (2*(1-t)*t * ctrl_lng) + (t**2 * lng2)
            plat = ((1-t)**2 * lat1) + (2*(1-t)*t * ctrl_lat) + (t**2 * lat2)
            points.append([plng, plat])
            
        return points

    @staticmethod
    def map_reasoning_to_geojson(reasoning_trace: List[Any], threat_features: Dict, blue_features: Dict, coa_id: str = None) -> Dict:
        """
        추론 체인 정보를 GeoJSON LineString으로 변환 (Reasoning Layer)
        문자열 리스트(Step-by-step)와 딕셔너리 리스트(Edge-based) 모두 지원
        """
        features = []
        if not reasoning_trace:
             return {"type": "FeatureCollection", "features": []}
            
        coord_cache = {}
        def clean_name(name):
            if not name: return ""
            name = str(name).strip()
            for prefix in ["제", "부대", "작전", "Area", "Unit", "Threat"]:
                if name.startswith(prefix) and len(name) > len(prefix):
                    name = name[len(prefix):]
            return name.strip()

        for collection in [threat_features, blue_features]:
            if collection and "features" in collection:
                for f in collection["features"]:
                    props = f.get("properties", {})
                    coords = f.get("geometry", {}).get("coordinates")
                    if coords:
                        keys = ["id", "name", "label", "위협ID", "threat_id", "coa_id", "situation_id"]
                        for key in keys:
                            val = props.get(key)
                            if val:
                                coord_cache[str(val)] = coords
                                cleaned = clean_name(val)
                                if cleaned: coord_cache[cleaned] = coords
        
        for k, v in LOCATION_DB.items():
            coord_cache[k] = [v['lng'], v['lat']]
            coord_cache[v['name']] = [v['lng'], v['lat']]
            
        if all(isinstance(x, str) for x in reasoning_trace):
            last_target_coords = None
            for i, step in enumerate(reasoning_trace):
                found_entities = []
                for entity_id in coord_cache.keys():
                    if entity_id in step and len(entity_id) > 3:
                        found_entities.append(entity_id)
                
                found_entities = sorted(list(set(found_entities)), key=len, reverse=True)
                filtered_entities = []
                for e in found_entities:
                    if not any(e != other and e in other for other in found_entities):
                        filtered_entities.append(e)
                
                if filtered_entities:
                    current_coords = coord_cache[filtered_entities[0]]
                    if last_target_coords and current_coords != last_target_coords:
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [last_target_coords, current_coords]},
                            "properties": {
                                "type": "REASONING_STEP",
                                "step_num": i + 1,
                                "description": step,
                                "color": "#2E9AFE",
                                "coa_id": coa_id
                            }
                        })
                    last_target_coords = current_coords
            
            if not features and last_target_coords:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": last_target_coords},
                    "properties": {"type": "REASONING_POINT", "description": reasoning_trace[-1], "coa_id": coa_id}
                })

        else:
            for step in reasoning_trace:
                if not isinstance(step, dict): continue
                source = step.get("from")
                target = step.get("to")
                p1, p2 = coord_cache.get(str(source)), coord_cache.get(str(target))
                if p1 and p2:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [p1, p2]},
                        "properties": {
                            "type": "REASONING_LINK",
                            "description": step.get("description", ""),
                            "color": step.get("color", "#f39c12"),
                            "coa_id": coa_id
                        }
                    })
        
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def map_reasoning_graph_to_geojson(reasoning_graph: List[Dict], threat_features: Dict, blue_features: Dict, coa_id: str = None) -> Dict:
        """
        추론 그래프 정보를 GeoJSON LineString으로 변환 (Reasoning Layer)
        Edge-based 딕셔너리 리스트를 처리
        """
        features = []
        if not reasoning_graph:
             return {"type": "FeatureCollection", "features": []}
            
        # 좌표 캐시 생성 (ID/Name -> [lng, lat])
        coord_cache = {}
        
        def clean_name(name):
            if not name: return ""
            name = str(name).strip()
            # 접두어/접미어 제거
            for prefix in ["제", "부대", "작전", "Area", "Unit", "Threat"]:
                if name.startswith(prefix) and len(name) > len(prefix):
                    name = name[len(prefix):]
            return name.strip()

        # 위협/아군 좌표 캐싱 (기존 로직 유지 및 강화)
        for collection in [threat_features, blue_features]:
            if collection and "features" in collection:
                for f in collection["features"]:
                    props = f.get("properties", {})
                    coords = f.get("geometry", {}).get("coordinates")
                    if coords:
                        # 다양한 키로 캐싱
                        keys = ["id", "name", "label", "위협ID", "threat_id", "coa_id", "situation_id"]
                        for key in keys:
                            val = props.get(key)
                            if val:
                                coord_cache[str(val)] = coords
                                cleaned = clean_name(val)
                                if cleaned: coord_cache[cleaned] = coords
        
        # LOCATION_DB 추가
        for k, v in LOCATION_DB.items():
            coord_cache[k] = [v['lng'], v['lat']]
            coord_cache[v['name']] = [v['lng'], v['lat']]
            
        for step in reasoning_graph:
            if not isinstance(step, dict): continue
            source = step.get("from")
            target = step.get("to")
            rel_type = step.get("relation_type", "relates")
            
            def find_coords(name_str):
                if not name_str: return None
                # 정확한 이름으로 검색
                if name_str in coord_cache: return coord_cache[name_str]
                
                # 특정 용어 변환 후 검색 (예: "보병" -> "INFANTRY")
                term_map = {
                    "보병": "INFANTRY", "기계화": "MECHANIZED", "기갑": "ARMOR",
                    "포병": "ARTILLERY", "미사일": "MISSILE", "항공": "AIR"
                }
                
                # 1. 변환된 용어로 검색
                for k, v in term_map.items():
                    if k in name_str.upper():
                        target_term = v
                        if target_term in coord_cache: return coord_cache[target_term]
                        # 변환된 용어가 포함된 키 검색
                        for ck, cv in coord_cache.items():
                            if target_term in ck or ck in target_term:
                                return cv

                # 2. 정규화된 이름으로 검색
                cleaned = clean_name(name_str)
                if cleaned in coord_cache: return coord_cache[cleaned]
                
                # 3. 부분 일치 검색 (보수적 일치)
                # 너무 짧은 이름(1-2글자)은 부분 일치 제외 (오매칭 방지)
                if len(name_str) >= 2:
                    for k, v in coord_cache.items():
                        if name_str in k or k in name_str:
                            return v
                        if cleaned and (cleaned in k or k in cleaned):
                            return v
                return None

            p1 = find_coords(source)
            p2 = find_coords(target)
            
            if p1 and p2:
                print(f"[DEBUG] ScenarioMapper: FOUND link {source} -> {target}")
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [p1, p2]
                    },
                    "properties": {
                        "type": "REASONING_LINK",
                        "coa_id": coa_id or "",
                        "description": f"{source} --[{rel_type}]--> {target}",
                        "rel_type": rel_type,
                        "color": "#f39c12", # 오렌지색
                        "dashArray": "5, 5",
                        "weight": 2,
                        "opacity": 0.8
                    }
                })
            else:
                print(f"[DEBUG] ScenarioMapper: FAILED to find link {source}({p1 is not None}) -> {target}({p2 is not None})")
                
        return {
            "type": "FeatureCollection",
            "features": features
        }

    @staticmethod
    def map_risk_to_geojson(threat_features: Dict) -> Dict:
        """
        위협 정보를 기반으로 위험 구역(Risk Zone) GeoJSON Polygon 생성 (Risk Layer)
        
        Args:
            threat_features: 위협 GeoJSON
        """
        features = []
        if not threat_features or "features" not in threat_features:
            return {"type": "FeatureCollection", "features": []}
            
        import math
        
        # 원형 폴리곤 생성 헬퍼
        def create_circle_polygon(center, radius_km, num_points=32):
            lng, lat = center
            points = []
            # 위도 1도 = 약 111km
            # 경도 1도 = 약 111km * cos(lat)
            lat_deg = radius_km / 111.0
            lng_deg = radius_km / (111.0 * math.cos(math.radians(lat)))
            
            for i in range(num_points + 1): # 닫힌 루프를 위해 +1
                angle = math.radians(float(i) / num_points * 360.0)
                p_lng = lng + lng_deg * math.cos(angle)
                p_lat = lat + lat_deg * math.sin(angle)
                points.append([p_lng, p_lat])
            return [points] # GeoJSON Polygon은 [[[x,y], ...]] 형태 (링)
            
        for f in threat_features["features"]:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates")
            
            if not coords or f.get("geometry", {}).get("type") != "Point":
                continue
                
            # 위협 반경 및 수준 가져오기
            # threat_radius는 미터 단위로 이미 변환되어 있음 (기존 로직)
            radius_m = props.get("threat_radius", 20000) 
            radius_km = radius_m / 1000.0
            
            # 위험도 (기본값 0.7)
            risk_level = props.get("confidence", 0.7)
            if props.get("위협수준"):
                 try:
                     # "높음", "중간" 텍스트 또는 숫자 처리
                     val = str(props.get("위협수준"))
                     if "높음" in val or "High" in val: risk_level = 0.9
                     elif "중간" in val or "Medium" in val: risk_level = 0.5
                     elif "낮음" in val or "Low" in val: risk_level = 0.3
                     else: risk_level = float(val)
                 except: pass

            # 위험 구역 Polygon 생성
            poly_coords = create_circle_polygon(coords, radius_km)
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": poly_coords
                },
                "properties": {
                    "type": "RISK_ZONE",
                    "name": f"Risk Zone ({props.get('name')})",
                    "risk_level": risk_level,
                    "associated_threat": props.get("id")
                }
            })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }

    @staticmethod
    def get_mock_scenario():
        """테스트용 Mock 데이터 생성"""
        threats = [
            {"name": "평양 미사일 기지", "type": "Missile", "radius_km": 50},
            {"name": "개성 전차 부대", "type": "Tank", "radius_km": 15},
            {"name": "원산 해군 기지", "type": "Navy", "radius_km": 30}
        ]
        
        coa = {
            "coa_type": "preemptive",
            "name": "선제 정밀 타격",
            "description": "F-35A를 이용한 적 미사일 기지 정밀 타격"
        }
        
        threat_geo = ScenarioMapper.map_threats_to_geojson(threats)
        coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geo)
        
        return threat_geo, coa_geo
