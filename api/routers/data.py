from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from api.schemas import (
    MissionListResponse, ThreatListResponse, MissionBase, ThreatEventBase,
    FriendlyUnitListResponse, FriendlyUnit, AxisListResponse, AxisItem,
    TerrainCellListResponse, TerrainCellItem
)
from api.dependencies import get_coa_service
from core_pipeline.coa_service import COAService
from core_pipeline.data_models import ThreatEvent
from common.situation_converter import SituationInfoConverter
from core_pipeline.visualization_generator import VisualizationDataGenerator

router = APIRouter(prefix="/data", tags=["Data"])

# 시각화 데이터 생성기 인스턴스 (캐시 활용을 위해 전역 세션 관리)
viz_gen = VisualizationDataGenerator()

@router.get("/missions", response_model=MissionListResponse)
def get_missions(service: COAService = Depends(get_coa_service)):
    missions_data = service.get_available_missions()
    if not missions_data:
        return MissionListResponse(missions=[])
    
    # 축선 데이터 로드 (좌표 추출용)
    axes_df = service.data_manager.load_table('전장축선')
    terrain_df = service.data_manager.load_table('지형셀')
    
    def get_axis_start_coords(axis_id: str):
        """축선의 시작점 좌표를 반환"""
        if axes_df is None or axes_df.empty or not axis_id:
            return None, None
        
        # 축선 데이터에서 시작점 지형셀 찾기
        axis_row = axes_df[axes_df['축선ID'] == axis_id]
        if axis_row.empty:
            return None, None
        
        start_cell_id = axis_row.iloc[0].get('시작지형셀ID')
        if not start_cell_id and terrain_df is not None:
            # 축선ID에 연결된 지형셀 목록에서 첫 번째 사용
            cell_list_str = axis_row.iloc[0].get('주요지형셀목록', '')
            if cell_list_str:
                cells = [c.strip() for c in str(cell_list_str).split(',')]
                if cells:
                    start_cell_id = cells[0]
        
        if start_cell_id and terrain_df is not None and not terrain_df.empty:
            cell_row = terrain_df[terrain_df['지형셀ID'] == start_cell_id]
            if not cell_row.empty:
                coord_str = cell_row.iloc[0].get('좌표정보', '')
                if coord_str:
                    try:
                        parts = str(coord_str).split(',')
                        if len(parts) == 2:
                            lon = float(parts[0].strip())
                            lat = float(parts[1].strip())
                            return lat, lon
                    except:
                        pass
        
        return None, None
    
    mission_objs = []
    for m in missions_data:
        lat, lon = None, None
        axis_id = m.get('primary_axis_id')
        
        # 🔥 FIX: 축선 시작점에서 좌표 추출
        if axis_id:
            lat, lon = get_axis_start_coords(axis_id)
        
        mission_objs.append(MissionBase(
            mission_id=m.get('mission_id', ''),
            mission_type=m.get('mission_type'),
            mission_name=m.get('mission_name'),
            primary_axis_id=m.get('primary_axis_id'),
            commander_intent=m.get('commander_intent'),
            latitude=lat,
            longitude=lon
        ))
    return MissionListResponse(missions=mission_objs)

@router.get("/threats", response_model=ThreatListResponse)
def get_threats(service: COAService = Depends(get_coa_service)):
    threats_df = service.data_manager.load_table('위협상황')
    if threats_df is None or threats_df.empty:
        return ThreatListResponse(threats=[])
    
    threat_objs = []
    for _, row in threats_df.iterrows():
        threat_event = ThreatEvent.from_row(row.to_dict())
        
        # 위협수준 정규화 (문자열 "HIGH", "MEDIUM", "LOW" 등을 숫자로 변환)
        # 기존 통합 변환기 SituationInfoConverter 사용
        threat_level_raw = threat_event.threat_level
        threat_level_normalized = None
        if threat_level_raw is not None:
            try:
                normalized, raw_val, label = SituationInfoConverter.normalize_threat_level(threat_level_raw)
                # API 스키마가 문자열을 기대하므로 0-100 범위의 정수 문자열로 변환
                # 프론트엔드에서 이 값을 파싱하여 사용
                threat_level_normalized = str(raw_val)  # 0-100 범위의 정수 문자열 (예: "85")
            except Exception as e:
                # 변환 실패 시 원본 값 유지 (프론트엔드에서 처리)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"위협수준 변환 실패 (threat_id={threat_event.threat_id}, raw={threat_level_raw}): {e}")
                threat_level_normalized = str(threat_level_raw) if threat_level_raw else None
        
        lat, lon = None, None
        if threat_event.location_cell_id:
            coords = viz_gen._get_terrain_cell_coordinates(threat_event.location_cell_id)
            if coords:
                lon, lat = coords
            else:
                import logging
                logging.getLogger(__name__).warning(f"위협 {threat_event.threat_id}의 좌표를 찾을 수 없음 (cell_id={threat_event.location_cell_id})")
        else:
            import logging
            logging.getLogger(__name__).info(f"위협 {threat_event.threat_id}에 지형셀 ID가 없음")
        
        threat_objs.append(ThreatEventBase(
            threat_id=threat_event.threat_id,
            threat_type_code=threat_event.threat_type_code,
            threat_level=threat_level_normalized or threat_event.threat_level,  # 정규화된 값 사용
            related_axis_id=threat_event.related_axis_id,
            location_cell_id=threat_event.location_cell_id,
            occurrence_time=threat_event.occurrence_time,
            latitude=lat,
            longitude=lon,
            threat_type_original=threat_event.threat_type_original,
            raw_report_text=threat_event.raw_report_text,
            confidence=threat_event.confidence,
            status=threat_event.status,
            enemy_unit_original=threat_event.enemy_unit_original,
            remarks=threat_event.remarks,
            related_mission_id=threat_event.related_mission_id  # 위협-임무 관계 추가
        ))
        
    return ThreatListResponse(threats=threat_objs)

@router.get("/units/friendly", response_model=FriendlyUnitListResponse)
def get_friendly_units(service: COAService = Depends(get_coa_service)):
    # 1. 아군부대현황 로드
    units_df = service.data_manager.load_table('아군부대현황')
    if units_df is None or units_df.empty:
        return FriendlyUnitListResponse(units=[])
    
    unique_units = {} # 중복 제거용 (ID 기준)

    for _, row in units_df.iterrows():
        unit_id = row.get('아군부대ID')
        if not unit_id or unit_id in unique_units:
            continue
            
        # 2. 위치 좌표 해결
        lat, lon = None, None
        
        # 2-1. 좌표정보 컬럼 파싱 (우선순위 1)
        coord_str = row.get('좌표정보')
        if coord_str:
            try:
                # 좌표 문자열 처리 (예: "37.123, 127.456" 또는 "(37.123, 127.456)")
                cleaned = str(coord_str).replace('(', '').replace(')', '')
                parts = cleaned.split(',')
                if len(parts) >= 2:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    
                    # 좌표계 보정 (Lat이 90을 넘으면 Lon, Lat 순서로 입력된 것으로 간주)
                    if abs(lat) > 90 and abs(lon) <= 90:
                        lat, lon = lon, lat
            except:
                pass
        
        # 2-2. 배치지형셀ID로 좌표 검색 (우선순위 2 - 좌표정보가 없거나 실패 시)
        if (lat is None or lon is None) and row.get('배치지형셀ID'):
            cell_id = row.get('배치지형셀ID')
            coords = viz_gen._get_terrain_cell_coordinates(cell_id)
            if coords:
                lon, lat = coords
            
        # 2-3. 기본값 (배치를 위해 임의 좌표 부여?? 아니면 생략)
        
        # 3. 데이터 매핑
        unit = FriendlyUnit(
            unit_id=str(unit_id),
            unit_name=str(row.get('부대명', '')),
            unit_type=str(row.get('병종', '')),
            echelon=str(row.get('제대', '')),
            location_cell_id=str(row.get('배치지형셀ID', '')) if row.get('배치지형셀ID') else None,
            latitude=lat,
            longitude=lon,
            description=str(row.get('고유명칭') or row.get('부대명', '')),
            status=str(row.get('가용상태', '가용')), # 상태 컬럼 삭제됨, 가용상태 사용
            combat_power=float(row.get('전투력지수') or 0), # 전투력 컬럼 삭제됨
            max_speed_kmh=float(row.get('이동속도_kmh') or 0), # NEW
        )
        unique_units[unit_id] = unit
        
    return FriendlyUnitListResponse(units=list(unique_units.values()))

@router.get("/axes", response_model=AxisListResponse)
def get_axes(service: COAService = Depends(get_coa_service)):
    # 1. 전장축선 테이블 로드
    axes_df = service.data_manager.load_table('전장축선')
    if axes_df is None or axes_df.empty:
        return AxisListResponse(axes=[])
        
    axes_objs = []
    for _, row in axes_df.iterrows():
        start_cell = row.get('시작지형셀ID')
        end_cell = row.get('종단지형셀ID')
        
        # 좌표 구하기
        start_coords = viz_gen._get_terrain_cell_coordinates(start_cell) if start_cell else None
        end_coords = viz_gen._get_terrain_cell_coordinates(end_cell) if end_cell else None
        
        coordinates = []
        if start_coords and end_coords:
            # Simple straight line for now: [End(Lat,Lon), Start(Lat,Lon)] ? 
            # Leaflet expects [Lat, Lon]. viz_gen returned (Lon, Lat) probably?
            # Let's check viz_gen._get_terrain_cell_coordinates source.
            # Assuming viz_gen returns (lon, lat) based on previous usage in get_threats.
            
            # get_threats: lon, lat = coords
            # So coords is (lon, lat).
            
            start_lat, start_lon = start_coords[1], start_coords[0]
            end_lat, end_lon = end_coords[1], end_coords[0]
            
            coordinates = [
                [start_lat, start_lon],
                [end_lat, end_lon]
            ]
            
        axes_objs.append(AxisItem(
            axis_id=str(row.get('축선ID')),
            axis_name=str(row.get('축선명', '')),
            axis_type=str(row.get('축선유형', 'SECONDARY')), # 기본값
            start_cell_id=start_cell,
            end_cell_id=end_cell,
            coordinates=coordinates,
            description=str(row.get('축선설명', ''))
        ))
        
    return AxisListResponse(axes=axes_objs)

@router.get("/terrain", response_model=TerrainCellListResponse)
def get_terrain_cells():
    cells_data = viz_gen.get_all_terrain_cells()
    
    cell_objs = []
    for c in cells_data:
        cell_objs.append(TerrainCellItem(
            cell_id=c['cell_id'],
            coordinates=c['coordinates'],
            name=c.get('name'),
            description=c.get('description')
        ))
        
    return TerrainCellListResponse(cells=cell_objs)
