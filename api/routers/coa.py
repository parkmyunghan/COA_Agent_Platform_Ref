from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List
import pandas as pd
from api.schemas import COAGenerationRequest, COAResponse, COASummary, COADetailResponse
from api.dependencies import get_coa_service, get_global_state
from api.utils.situation_summary_generator import generate_template_based_summary
from common.situation_converter import SituationInfoConverter
from core_pipeline.coa_service import COAService
from core_pipeline.data_models import ThreatEvent, FriendlyUnit
from core_pipeline.visualization_generator import VisualizationDataGenerator

router = APIRouter(prefix="/coa", tags=["COA"])

def _enrich_situation_info(situation_info: Dict[str, Any], service: COAService, mapper) -> Dict[str, Any]:
    """
    상황 정보에 자연어 명칭(지형, 축선, 위협유형 등)을 추가합니다.
    [FIX] 이전 선택의 잔여 데이터(발생지형명 등)가 오염되지 않도록 ID 기반으로 초기화합니다.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 1. 보고용 ID 추출
    loc_id = situation_info.get('location') or situation_info.get('발생장소')
    axis_id = situation_info.get('axis_id') or situation_info.get('관련축선ID')
    threat_type_code = situation_info.get('threat_type') or situation_info.get('위협유형')
    enemy = situation_info.get('적부대') or situation_info.get('enemy_units') or 'ENU_ESTIMATED'
    
    # [FIX] 매퍼를 통한 명칭 통합 조회
    real_loc_name = loc_id
    real_axis_name = axis_id
    t_type_ko = threat_type_code or "식별된 위협"

    try:
        # 데모 시나리오 등에 대한 하드코딩 매핑 (Fallback)
        demo_mappings = {
            'SCENARIO_SCENARIO_1_1768819407953': {
                'loc_name': '파주 북단',
                'axis_name': '문산축선',
                'threat_type': '적 정찰기',
                'enemy': '미상(정찰)'
            }
        }
        
        is_demo = situation_info.get('is_demo') or (str(situation_info.get('threat_id')).startswith('SCENARIO_'))
        if is_demo and situation_info.get('threat_id') in demo_mappings:
            mapping = demo_mappings[situation_info.get('threat_id')]
            real_loc_name = mapping['loc_name']
            real_axis_name = mapping['axis_name']
            t_type_ko = mapping['threat_type']
            enemy_ko = mapping['enemy']
            logger.info(f"[정황보고] 데모 시나리오 매핑 적용: {mapping}")
        
        # 2. CodeLabelMapper를 통한 표준 명칭 변환
        else:
            if mapper:
                # 지형명 변환 (TERR...)
                if loc_id:
                    real_loc_name = mapper.get_terrain_label(loc_id)
                
                # 축선명 변환 (AXIS...)
                if axis_id:
                    real_axis_name = mapper.get_axis_label(axis_id)
                
                # 위협 유형 변환 (THR_TYPE...)
                if threat_type_code:
                    t_type_ko = mapper.get_threat_type_label(threat_type_code)
                    if t_type_ko == threat_type_code and str(threat_type_code).startswith("THR_TYPE_"):
                         t_type_ko = "식별된 위협"
            
            # 적 부대 변환
            codec_map = {
                "INFANTRY": "보병", "ARMOR": "기갑", "ARTILLERY": "포병",
                "AIR": "항공", "MISSILE": "미사일", "CBRN": "화생방",
                "CYBER": "사이버", "INFILTRATION": "침투", "UNKNOWN": "미상",
                "ENU_ESTIMATED": "식별된 적 부대",
                "HIGH": "높음", "MEDIUM": "중간", "LOW": "낮음"
            }
            enemy_ko = codec_map.get(str(enemy).upper(), enemy)
        
        # 상세 보고용 텍스트 구성 (ID와 명칭 병기 - 매퍼 포맷 사용)
        loc_display = mapper.format_with_code(real_loc_name, loc_id) if mapper else (f"{real_loc_name}({loc_id})" if loc_id else real_loc_name)
        axis_display = mapper.format_with_code(real_axis_name, axis_id) if mapper else (f"{real_axis_name}({axis_id})" if axis_id else real_axis_name)
        threat_display = mapper.format_with_code(t_type_ko, threat_type_code) if mapper else (f"{t_type_ko}({threat_type_code})" if threat_type_code else t_type_ko)

        # 상황 정보 최종 업데이트 (중요: Stale 데이터 덮어쓰기)
        situation_info.update({
            '발생지형명': real_loc_name,
            'location_name': real_loc_name,
            '관련축선명': real_axis_name,
            'axis_name': real_axis_name,
            '위협유형': t_type_ko,
            '적부대': enemy_ko,
            # 포맷팅용 가공 데이터 주입
            '_loc_display': loc_display,
            '_axis_display': axis_display,
            '_threat_display': threat_display,
            '_enemy_ko': enemy_ko
        })
        
    except Exception as e:
        logger.error(f"[정황보고] 자연어 변환 중 오류: {e}")
        
    return situation_info

@router.post("/generate", response_model=COAResponse)
def generate_coas(
    request: COAGenerationRequest,
    service: COAService = Depends(get_coa_service)
):
    """
    Generate COAs based on Threat or Mission.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    import time
    start_time = time.time()
    
    logger.info(f"[방책추천 API] 요청 수신 - mission_id: {request.mission_id}, threat_id: {request.threat_id}, "
                f"approach_mode: {request.user_params.get('approach_mode', 'threat_centered') if request.user_params else 'threat_centered'}")
    
    try:
        # Reconstruct ThreatEvent if threat_id is present but we want to be safe, 
        # or just pass threat_id. COAService expects threat_id usually.
        # But if we want to pass a modified threat_event object (e.g. from SITREP), 
        # that might need more complex request handling. 
        # For now, let's assume we pass ID or assume the object is cached/lookup works.
        
        # If user passed only threat_id
        threat_event = None
        if request.threat_data:
            # Convert Pydantic model to dataclass
            data = request.threat_data.dict()
            threat_event = ThreatEvent(
                threat_id=data.get('threat_id'),
                occurrence_time=data.get('occurrence_time'),
                threat_type_code=data.get('threat_type_code'),
                related_axis_id=data.get('related_axis_id'),
                location_cell_id=data.get('location_cell_id'),
                related_enemy_unit_id=data.get('related_enemy_unit_id'),
                threat_level=data.get('threat_level'),
                related_mission_id=data.get('related_mission_id'),
                raw_report_text=data.get('raw_report_text'),
                confidence=data.get('confidence'),
                status=data.get('status'),
                threat_type_original=data.get('threat_type_original'),
                enemy_unit_original=data.get('enemy_unit_original'),
                remarks=data.get('remarks')
            )
        elif request.threat_id:
             # Ideally we fetch it from DB or cache if it was dynamically created
             # But COAService usually loads from file if we just pass ID.
             # If it was dynamic (from SITREP), it might not be in the file.
             pass

        debug_log(logger, f"[방책추천 API] COA 생성 시작 - approach_mode: {request.user_params.get('approach_mode', 'threat_centered') if request.user_params else 'threat_centered'}")
        
        # [옵션 A] 에이전트 기반 생성 사용 (제대로 된 아키텍처)
        result = service.generate_coas_with_agent(
            mission_id=request.mission_id,
            threat_id=request.threat_id,
            threat_event=threat_event,
            user_params=request.user_params
        )
        
        if "error" in result:
            logger.error(f"[방책추천 API] COA 생성 실패: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
        
        coas_count = len(result.get("coas", []))
        evaluations_count = len(result.get("evaluations", []))
        top_coas_count = len(result.get("top_coas", []))
        # 기본 정보는 항상 기록
        logger.info(f"[방책추천 API] COA 생성 완료 - 생성된 COA: {coas_count}개, 상위 COA: {top_coas_count}개")
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[방책추천 API] 상세 결과 - 평가 완료: {evaluations_count}개")

        # Map result to COAResponse
        # result structure: {"coas": [...], "evaluations": [...], "top_coas": [...], "axis_states": [...]}
        
        # 시각화 데이터 생성기 초기화
        viz_generator = VisualizationDataGenerator()
        
        # 1.5 [FIX] 로드된 위협 이벤트 정보 사용 (threat_id만 넘어온 경우 대비)
        enriched_threat = result.get("threat_event")
        
        # 🔥 FIX: 접근 방식 확인 (임무 중심 vs 위협 중심)
        approach_mode = request.user_params.get('approach_mode', 'threat_centered')
        
        # 위협 위치 추출 (시각화 데이터 생성용)
        threat_position = None
        if enriched_threat and enriched_threat.location_cell_id:
            threat_position = viz_generator._get_terrain_cell_coordinates(enriched_threat.location_cell_id)
        elif threat_event and threat_event.location_cell_id:
            threat_position = viz_generator._get_terrain_cell_coordinates(threat_event.location_cell_id)
        elif request.threat_data and request.threat_data.location_cell_id:
            threat_position = viz_generator._get_terrain_cell_coordinates(request.threat_data.location_cell_id)
        
        # 🔥 FIX: 임무 중심 모드에서 위협 위치가 없으면 임무의 작전 지역에서 추출
        if threat_position is None and approach_mode == 'mission_centered' and request.mission_id:
            # 임무 정보에서 primary_axis_id 조회
            missions_df = service.data_manager.load_table('임무정보')
            if missions_df is not None and not missions_df.empty:
                mission_row = missions_df[missions_df['임무ID'] == request.mission_id]
                if not mission_row.empty:
                    # 컬럼명이 다를 수 있음: 주요축선ID, 주공축선ID, primary_axis_id
                    primary_axis_id = mission_row.iloc[0].get('주요축선ID') or \
                                     mission_row.iloc[0].get('주공축선ID') or \
                                     mission_row.iloc[0].get('primary_axis_id')
                    if primary_axis_id and not pd.isna(primary_axis_id):
                        primary_axis_id = str(primary_axis_id).strip()
                        # 축선의 시작점 지형셀에서 좌표 추출
                        axes_df = service.data_manager.load_table('전장축선')
                        if axes_df is not None and not axes_df.empty:
                            axis_row = axes_df[axes_df['축선ID'] == primary_axis_id]
                            if not axis_row.empty:
                                start_cell = axis_row.iloc[0].get('시작지형셀ID')
                                if start_cell and not pd.isna(start_cell):
                                    threat_position = viz_generator._get_terrain_cell_coordinates(str(start_cell).strip())
        
        # 주요 축선 ID 추출
        main_axis_id = None
        if enriched_threat and enriched_threat.related_axis_id:
            main_axis_id = enriched_threat.related_axis_id
        elif threat_event and threat_event.related_axis_id:
            main_axis_id = threat_event.related_axis_id
        elif request.threat_data and request.threat_data.related_axis_id:
            main_axis_id = request.threat_data.related_axis_id
        
        # 🔥 FIX: 임무 중심 모드에서 축선이 없으면 임무의 주 축선 사용
        if main_axis_id is None and approach_mode == 'mission_centered' and request.mission_id:
            missions_df = service.data_manager.load_table('임무정보')
            if missions_df is not None and not missions_df.empty:
                mission_row = missions_df[missions_df['임무ID'] == request.mission_id]
                if not mission_row.empty:
                    # 컬럼명이 다를 수 있음: 주요축선ID, 주공축선ID, primary_axis_id
                    axis_val = mission_row.iloc[0].get('주요축선ID') or \
                              mission_row.iloc[0].get('주공축선ID') or \
                              mission_row.iloc[0].get('primary_axis_id')
                    if axis_val and not pd.isna(axis_val):
                        main_axis_id = str(axis_val).strip()
        
        # 🔥 FIX: 그래도 main_axis_id가 없으면 axis_states에서 첫 번째 축선 사용
        if main_axis_id is None:
            axis_states = result.get("axis_states", [])
            if axis_states and len(axis_states) > 0:
                first_axis = axis_states[0]
                if hasattr(first_axis, 'axis_id') and first_axis.axis_id:
                    main_axis_id = first_axis.axis_id
        
        # 🔥 FIX: threat_position도 없으면 첫 번째 축선의 시작점에서 추출
        if threat_position is None and main_axis_id:
            threat_position = viz_generator._get_axis_start_position(main_axis_id)
        
        coas_summary = []
        top_coas = result.get("top_coas", [])
        for idx, coa_eval in enumerate(top_coas):
             # coa_eval is COAEvaluation object
             # We need to extract summary info
             summary = service.get_coa_summary(coa_eval) # returns dict with score, name etc
             
             # COA 객체에서 참여 부대 정보 추출
             coa_obj = next((c for c in result.get("coas", []) if c.coa_id == coa_eval.coa_id), None)
             friendly_units = []
             if coa_obj:
                 # unit_assignments에서 부대 정보 추출
                 if hasattr(coa_obj, 'unit_assignments') and coa_obj.unit_assignments:
                     for unit_id, assignment in coa_obj.unit_assignments.items():
                         # data_manager에서 부대 상세 정보 조회
                         unit_info = {"unit_id": unit_id}
                         try:
                             # 아군부대현황 테이블에서 부대 정보 조회
                             friendly_units_data = service.data_manager.load_table('아군부대현황')
                             if friendly_units_data is not None and not friendly_units_data.empty:
                                 # 먼저 아군부대ID로 조회
                                 unit_row = friendly_units_data[friendly_units_data['아군부대ID'] == unit_id]
                                 
                                 # ID로 찾지 못하면 부대명으로 조회 (Fallback)
                                 if unit_row.empty:
                                     unit_row = friendly_units_data[friendly_units_data['부대명'] == unit_id]
                                     
                                 if not unit_row.empty:
                                     unit_info.update({
                                         "부대명": str(unit_row.iloc[0].get("부대명", "")),
                                         "제대": str(unit_row.iloc[0].get("제대", "")),
                                         "병종": str(unit_row.iloc[0].get("병종", "")),
                                         "배치지형셀ID": str(unit_row.iloc[0].get("배치지형셀ID", "")),
                                         "배치축선ID": assignment.axis_id if hasattr(assignment, 'axis_id') else unit_row.iloc[0].get('배치축선ID', ''),
                                         "좌표정보": str(unit_row.iloc[0].get("좌표정보", "")),
                                         "전투력지수": float(unit_row.iloc[0].get("전투력지수", 0)),
                                     })
                         except Exception as e:
                             # 조회 실패 시 unit_id만 사용
                             pass
                         friendly_units.append(unit_info)
                 # participating_units가 있는 경우 (레거시 지원)
                 elif hasattr(coa_obj, 'participating_units') and coa_obj.participating_units:
                     for unit_id in coa_obj.participating_units:
                         unit_info = {"unit_id": unit_id}
                         try:
                             friendly_units_data = service.data_manager.load_table('아군부대현황')
                             if friendly_units_data is not None and not friendly_units_data.empty:
                                 unit_row = friendly_units_data[friendly_units_data['아군부대ID'] == unit_id]
                                 if unit_row.empty:
                                     unit_row = friendly_units_data[friendly_units_data['부대명'] == unit_id]
                                 
                                 if not unit_row.empty:
                                     unit_info.update({
                                         "부대명": str(unit_row.iloc[0].get("부대명", "")),
                                         "제대": str(unit_row.iloc[0].get("제대", "")),
                                         "병종": str(unit_row.iloc[0].get("병종", "")),
                                         "전투력지수": float(float(unit_row.iloc[0].get("전투력지수", 0))),
                                         "배치지형셀ID": str(str(unit_row.iloc[0].get("배치지형셀ID", ""))),
                                         "좌표정보": str(str(unit_row.iloc[0].get("좌표정보", ""))),
                                     })
                         except:
                             pass
                         friendly_units.append(unit_info)
             
             # 🔥 FIX: COA에 부대 정보가 없으면 axis_states에서 추출
             if not friendly_units:
                 axis_states = result.get("axis_states", [])
                 for axis_state in axis_states:
                     if hasattr(axis_state, 'friendly_units') and axis_state.friendly_units:
                         for unit in axis_state.friendly_units:
                             unit_info = {
                                 "unit_id": unit.friendly_unit_id if hasattr(unit, 'friendly_unit_id') else str(unit),
                                 "부대명": unit.unit_name if hasattr(unit, 'unit_name') else "",
                                 "제대": unit.echelon if hasattr(unit, 'echelon') else "",
                                 "병종": unit.branch if hasattr(unit, 'branch') else "",
                                 "전투력지수": float(unit.combat_power) if hasattr(unit, 'combat_power') and unit.combat_power else 0.0,
                                 "배치지형셀ID": unit.deployed_cell_id if hasattr(unit, 'deployed_cell_id') else "",
                                 "배치축선ID": unit.deployed_axis_id if hasattr(unit, 'deployed_axis_id') else "",
                                 "좌표정보": unit.location_coords if hasattr(unit, 'location_coords') else "",
                             }
                             # 중복 방지
                             if not any(u.get("unit_id") == unit_info["unit_id"] for u in friendly_units):
                                 friendly_units.append(unit_info)
             
             # 시각화 데이터 생성
             visualization_data = {}
             
             # 작전 경로 생성
             operational_path = viz_generator.generate_operational_path(
                 coa=summary,
                 friendly_units=friendly_units,
                 threat_position=threat_position,
                 main_axis_id=main_axis_id
             )
             path_points = []
             if operational_path:
                 visualization_data["operational_path"] = operational_path
                 # 경로 포인트 추출 (AO 생성용)
                 path_points = operational_path.get("waypoints", [])
             
             # 작전 영역 생성 (경로 포인트 전달)
             operational_area = viz_generator.generate_operational_area(
                 friendly_units=friendly_units,
                 threat_position=threat_position,
                 path_points=path_points
             )
             if operational_area:
                 visualization_data["operational_area"] = operational_area
             
             # 아군 부대 위치 GeoJSON 생성
             unit_positions_geojson = viz_generator.generate_unit_positions_geojson(friendly_units)
             
             # 에이전트 응답에서 matching recommendation 찾기 (doctrine_references, chain_info 추출용)
             agent_recommendations = result.get("recommendations", [])
             matching_rec = None
             for rec in agent_recommendations:
                 if rec.get("coa_id") == coa_eval.coa_id:
                     matching_rec = rec
                     break
             
             # COASummary 생성 (시각화 데이터 포함)
             coa_summary_dict = {
                 "coa_id": coa_eval.coa_id,
                 "coa_name": str(summary.get("coa_name", coa_eval.coa_id)),
                 "total_score": float(float(summary.get("total_score", 0.0))),
                 "rank": int(idx + 1),
                 "description": str(str(summary.get("description", ""))),
                 "combat_power_score": float(float(summary.get("combat_power_score", 0.0))),
                 "mobility_score": float(float(summary.get("mobility_score", 0.0))),
                 "constraint_score": float(float(summary.get("constraint_compliance_score", summary.get("constraint_score", 0.0)))),
                 "threat_response_score": float(float(summary.get("threat_response_score", 0.0))),
                 "risk_score": float(float(summary.get("risk_score", 0.0))),
                 "reasoning": service.generate_coa_explanation(
                     coa_evaluation=coa_eval,
                     axis_states=result.get("axis_states", []),
                     use_llm=True
                 ),
                 # NEW: RAG 참고자료 (DoctrineReferencePanel용)
                 "doctrine_references": matching_rec.get("doctrine_references", []) if matching_rec else [],
                 # NEW: 전략 체인 정보 (ChainVisualizer용)
                 "chain_info": matching_rec.get("chain_info_details", {}) if matching_rec else {}
             }
             
             # 시각화 데이터 추가 (dict로 변환하여 추가)
             if visualization_data:
                 coa_summary_dict["visualization_data"] = visualization_data
             
             # unit_positions GeoJSON 추가
             if unit_positions_geojson:
                 coa_summary_dict["unit_positions"] = unit_positions_geojson
             
             coas_summary.append(COASummary(**coa_summary_dict))
        
        # Axis states에 좌표 정보 추가
        axis_states = result.get("axis_states", [])
        axis_states_data = viz_generator.enrich_axis_states_with_coordinates(axis_states)

        # 정황보고 생성 (캐시 → LLM → 템플릿 순서로 시도)
        situation_summary = None
        
        # 상황 정보 구성 (request에서 추출)
        situation_info = {}
        if request.user_params:
            situation_info.update(request.user_params)
        
        # 위협 정보 추가
        if threat_event:
            # [FIX] SituationInfoConverter를 이용한 표준 정규화 (0.0-1.0 보장)
            normalized_level, raw_val, level_label = SituationInfoConverter.normalize_threat_level(threat_event.threat_level)
            
            situation_info.update({
                'threat_id': threat_event.threat_id,
                '위협ID': threat_event.threat_id,
                'threat_type': threat_event.threat_type_code,
                '위협유형': threat_event.threat_type_code,
                'threat_level': normalized_level,
                '위협수준': normalized_level,
                'location': threat_event.location_cell_id,
                '발생장소': threat_event.location_cell_id,
                'axis_id': threat_event.related_axis_id,
                '관련축선ID': threat_event.related_axis_id,
                'occurrence_time': threat_event.occurrence_time.isoformat() if threat_event.occurrence_time else None,
                '탐지시각': threat_event.occurrence_time.isoformat() if threat_event.occurrence_time else None,
                'raw_report_text': threat_event.raw_report_text,
                'approach_mode': result.get('approach_mode', 'threat_centered')
            })
        elif request.threat_data:
            # [FIX] SituationInfoConverter를 이용한 표준 정규화 (0.0-1.0 보장)
            normalized_level, raw_val, level_label = SituationInfoConverter.normalize_threat_level(request.threat_data.threat_level)
            
            situation_info.update({
                'threat_id': request.threat_data.threat_id,
                '위협ID': request.threat_data.threat_id,
                'threat_type': request.threat_data.threat_type_code,
                '위협유형': request.threat_data.threat_type_code,
                'threat_level': normalized_level,
                '위협수준': normalized_level,
                'location': request.threat_data.location_cell_id,
                '발생장소': request.threat_data.location_cell_id,
                'axis_id': request.threat_data.related_axis_id,
                '관련축선ID': request.threat_data.related_axis_id,
                'occurrence_time': request.threat_data.occurrence_time.isoformat() if request.threat_data.occurrence_time else None,
                '탐지시각': request.threat_data.occurrence_time.isoformat() if request.threat_data.occurrence_time else None,
                'raw_report_text': request.threat_data.raw_report_text,
                'approach_mode': result.get('approach_mode', 'threat_centered')
            })
        
        # 임무 정보 추가
        if request.mission_id:
            situation_info.update({
                'mission_id': request.mission_id,
                '임무ID': request.mission_id,
                'approach_mode': result.get('approach_mode', 'mission_centered')
            })
        
        # [FIX] 상황 정보 보강 로직 통합 호출
        mapper = get_mapper()
        situation_info = _enrich_situation_info(situation_info, service, mapper)
        
        logger.info(f"[정황보고] 자연어 변환 완료: {situation_info.get('발생지형명')}, {situation_info.get('관련축선명')}, {situation_info.get('위협유형')}")

        # [FIX] LLM 프롬프트용 변수 추출
        loc_id = situation_info.get('location') or situation_info.get('발생장소') or 'N/A'
        threat_type = situation_info.get('threat_type') or situation_info.get('위협유형') or 'UNKNOWN'
        threat_level = situation_info.get('threat_level', 0.5)
        axis_id = situation_info.get('axis_id') or situation_info.get('관련축선ID')
        
        # 정황보고 생성 (캐시 → LLM → 템플릿 순서로 시도)
        situation_summary = None
        
        # 1. 자연어가 주입된 situation_info로 캐시 조회 시도 (이미 주입됨)
        global_state = get_global_state()
        cached_summary = global_state.situation_summary_cache.get(situation_info)
        situation_summary_source = None
        if cached_summary:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("[정황보고] 캐시에서 조회됨")
            situation_summary = cached_summary
            situation_summary_source = "cache"
        # 2. LLM으로 생성 시도
        elif service.llm_manager and service.llm_manager.is_available():
            try:
                # LLM으로 정황보고 생성
                approach_mode = situation_info.get('approach_mode', 'threat_centered')
                
                # 위협 수준 변환 (0.0-1.0 기반)
                if approach_mode == "mission_centered":
                    if threat_level >= 0.8:
                        t_level_ko = "낮음"
                    elif threat_level >= 0.4:
                        t_level_ko = "보통"
                    else:
                        t_level_ko = "높음"
                else:
                    if threat_level >= 0.8:
                        t_level_ko = "매우 높음"
                    elif threat_level >= 0.6:
                        t_level_ko = "높음"
                    elif threat_level >= 0.4:
                        t_level_ko = "중간"
                    else:
                        t_level_ko = "낮음"
                
                # [FIX] 보강된 데이터 활용
                loc_display = situation_info.get('_loc_display', loc_id)
                axis_display = situation_info.get('_axis_display', axis_id)
                threat_display = situation_info.get('_threat_display', threat_type)
                enemy_ko = situation_info.get('_enemy_ko', '식별된 적 부대')

                
                
                # LLM 프롬프트 생성
                if approach_mode == "mission_centered":
                    m_id = situation_info.get('mission_id') or situation_info.get('임무ID', 'N/A')
                    m_name = situation_info.get('임무명') or situation_info.get('mission_name', 'N/A')
                    m_type = situation_info.get('임무종류') or situation_info.get('mission_type', 'N/A')
                    m_objective = situation_info.get('임무목표') or situation_info.get('mission_objective', 'N/A')
                    
                    prompt = f"""다음의 온톨로지 팩트를 기반으로 지휘관에게 보고하는 자연스러운 군사 임무 요약 문장을 생성하세요.

## 온톨로지 팩트:
- 하달시각: {situation_info.get('탐지시각', '최근')}
- 작전구역: {loc_display}
- 임무명: {m_name} ({m_id})
- 임무유형: {m_type}
- 주요축선: {axis_display}
- 성공가능성: {t_level_ko}
- 상세목표: {m_objective}

## 작문 지시사항:
1. **명칭 중심(Human-readable)**: "AXIS02", "THR105", "TERR001" 같은 **코드를 문장의 주어로 사용하지 마세요.** 반드시 **"영동축선", "적 전차대대", "백암산"** 같은 자연어 명칭을 주어로 사용해야 합니다.
2. **코드 병기 규정**: 코드는 최초 언급 시 이름 뒤 괄호 안에만 표기하세요. 예: "가칠봉(TERR007) 일대"
3. **전문적 군사 보고체**: "~가 하달됨", "~로 분석됨", "~이 예상됨" 등 명확하고 간결한 군사 보고 형식을 준수하세요.
4. **핵심 강조**: 중요한 명사(지명, 부대명, 축선명)는 **굵게** 표시하세요.
5. **분량**: 핵심 내용만 담아 **두 문장 이내**로 작성하세요.

## 예시:
- 나쁜 예: MISSION_001이 AXIS_01에서 수행됨. TERR007 확보가 목표임.
- 좋은 예: **제1보병사단**은 **서부 주공축선(AXIS_01)**을 따라 진격하여 **가칠봉(TERR007)** 고지를 확보하는 **공격 작전(MISSION_001)**을 수행함.

문장 생성:"""
                else:
                    # 🔥 IMPROVED: 원시보고텍스트를 최우선으로 활용
                    raw_report = situation_info.get('raw_report_text', '')
                    
                    prompt = f"""다음의 원시 상황보고와 온톨로지 팩트를 기반으로 지휘관에게 보고하는 자연스러운 군사 상황 요약 문장을 생성하세요.

## 원시 상황보고 (최우선 참조):
{raw_report if raw_report else '(원시보고 없음 - 온톨로지 팩트만 사용)'}

## 보완 온톨로지 팩트:
- 발생시각: {situation_info.get('탐지시각', '최근')}
- 발생위치: {loc_display}
- 위협원: {enemy_ko}
- 위협유형: {threat_display}
- 관련축선: {axis_display}
- 위협수준: {t_level_ko} ({int(threat_level*100)}%)

## 작문 지시사항:
1. **기계적 코드 노출 방지**: TERR007, THR_TYPE_001 등의 **코드를 문장의 주어로 절대 사용하지 마세요.** 반드시 **가칠봉**, **침투** 등의 이름이나 지명을 사용하여 보고 문장을 시작하세요.
2. **전문적 보고체**: 지휘관에게 드리는 정식 상황 보고 체계를 갖추어 "~이 식별되었습니다", "~로 판단됩니다" 등의 표현을 사용하세요.
3. **원시보고 중심**: 원시 상황보고에 포함된 구체적인 행동 묘사를 최대한 보존하세요.
4. **핵심 강조**: 중요 정보는 **굵게** 표시하세요.
5. **분량**: **두 문장 내외**로 간결하게 작성하세요.

## 예시:
- 나쁜 예: TERR007 지역에서 THR_TYPE_001 위협이 식별됨.
- 좋은 예: **가칠봉(TERR007) 일대**에서 **적 기동 징후(THR_TYPE_001)**가 포착되었으며, 현재 **양구-인제 축선**을 향해 이동 중인 것으로 분석됩니다.

문장 생성:"""
               
                # LLM으로 정황보고 생성 (위협 중심 및 임무 중심 모두)
                situation_summary = service.llm_manager.generate(prompt, max_tokens=256).strip()
                
                # LLM 생성 성공 로그
                import logging
                logger = logging.getLogger(__name__)
                if situation_summary:
                    logger.info(f"[정황보고] LLM으로 생성됨 (길이: {len(situation_summary)})")
                    situation_summary_source = "llm"
                    # 캐시에 저장 (SITREP이 아닌 경우만)
                    global_state.situation_summary_cache.set(situation_info, situation_summary)
                else:
                    logger.warning("[정황보고] LLM 생성 결과가 비어있음. 템플릿 기반으로 fallback합니다.")
                    situation_summary = generate_template_based_summary(situation_info)
                    situation_summary_source = "template"
            except Exception as e:
                # LLM 생성 실패 시 템플릿 기반 fallback
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[정황보고] LLM 생성 실패: {e}. 템플릿 기반으로 fallback합니다.")
                situation_summary = generate_template_based_summary(situation_info)
                situation_summary_source = "template"
        # 3. LLM 사용 불가 시 템플릿 기반 생성
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("[정황보고] LLM 사용 불가. 템플릿 기반으로 생성합니다.")
            situation_summary = generate_template_based_summary(situation_info)
            situation_summary_source = "template"

        elapsed_time = time.time() - start_time
        logger.info(f"[방책추천 API] 응답 생성 완료 ({elapsed_time:.2f}초) - COA 수: {len(coas_summary)}개")
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[방책추천 API] 응답 상세 - coas_summary 길이: {len(coas_summary)}, axis_states: {len(axis_states_data) if axis_states_data else 0}개")
        
        # [옵션 A] 에이전트가 직접 생성한 상황판단 사용
        situation_assessment = result.get('situation_assessment')
        
        logger.info(f"[방책추천 API] 상황판단: {'에이전트 생성 (' + situation_assessment[:50] + '...)' if situation_assessment else '없음'}")
        
        return COAResponse(
            coas=coas_summary,
            axis_states=axis_states_data,
            original_request=request,
            situation_summary=situation_summary,
            situation_summary_source=situation_summary_source,
            situation_assessment=situation_assessment
        )

    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"[방책추천 API] 오류 발생 ({elapsed_time:.2f}초): {str(e)}")
        logger.error(f"[방책추천 API] 상세 오류 정보:\n{traceback.format_exc()}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{coa_id}/explanation", response_model=COADetailResponse)
def get_coa_explanation(
    coa_id: str,
    # meaningful params to generate explanation... we need context (threat/mission)
    # This might be tricky if we don't have the context state.
    # We might need to pass context in body or rely on last session (which we want to avoid).
    # For now, let's assume we can generate generic explanation or we need to pass axis_states.
    # It seems COAService.generate_coa_explanation needs COAEvaluation and AxisStates.
    # Since Rest API is stateless, we should probably return explanation IN /generate response 
    # OR client must send back context.
    # Let's simplify: /generate returns minimal explanation. 
    # Detail endpoint might be just a placeholder or we require re-sending data.
    service: COAService = Depends(get_coa_service)
):
    return COADetailResponse(coa_id=coa_id, explanation="Detail explanation generation requires full context data in stateless API. Please refer to /generate response.")


@router.post("/generate-situation-summary")
def generate_situation_summary(
    request: Dict[str, Any] = Body(...),
    service: COAService = Depends(get_coa_service)
):
    """
    위협 정보만으로 정황보고를 생성합니다.
    COA 생성 없이 위협 선택 시 즉시 정황보고를 표시하기 위한 경량 엔드포인트.
    
    Request body:
    {
        "threat_id": "THR008",
        "threat_data": { ... },
        "user_params": { ... }
    }
    
    Returns:
    {
        "situation_summary": "...",
        "situation_summary_source": "llm" | "template" | "cache"
    }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 위협 정보 추출
        threat_event = None
        if request.get('threat_data'):
            data = request['threat_data']
            threat_event = ThreatEvent(
                threat_id=data.get('threat_id'),
                occurrence_time=data.get('occurrence_time'),
                threat_type_code=data.get('threat_type_code'),
                related_axis_id=data.get('related_axis_id'),
                location_cell_id=data.get('location_cell_id'),
                related_enemy_unit_id=data.get('related_enemy_unit_id'),
                threat_level=data.get('threat_level'),
                related_mission_id=data.get('related_mission_id'),
                raw_report_text=data.get('raw_report_text'),
                confidence=data.get('confidence'),
                status=data.get('status'),
                threat_type_original=data.get('threat_type_original'),
                enemy_unit_original=data.get('enemy_unit_original'),
                remarks=data.get('remarks')
            )
        elif request.get('threat_id'):
            # threat_id만 제공된 경우 데이터 로드 시도
            threats_data = service.data_manager.load_table('위협상황')
            if threats_data is not None and not threats_data.empty:
                threat_row = threats_data[threats_data['위협ID'] == request['threat_id']]
                if not threat_row.empty:
                    # [FIX] from_row를 사용하여 엑셀 컬럼명 매핑 일원화
                    threat_event = ThreatEvent.from_row(threat_row.iloc[0].to_dict())
        
        if not threat_event:
             # 데모 시나리오인 경우 request['threat_data']가 있으면 그것을 신뢰하여 진행
             if request.get('threat_data') and request.get('threat_data', {}).get('is_demo'):
                 # 이미 위에서 처리되었을 것임. threat_event가 None인 경우는 threat_id만 왔는데 DB에 없는 경우.
                 # 이 경우는 에러. 하지만 데모 시나리오 ID인 경우 Mock 데이터라도 생성해야 할 수 있음.
                 # 여기서는 일단 Pass.
                 pass
             else:
                raise HTTPException(status_code=400, detail="threat_data 또는 유효한 threat_id가 필요합니다.")
        
        # 상황 정보 구성
        situation_info = {}
        if request.get('user_params'):
            situation_info.update(request['user_params'])
        
        # 위협 정보 추가 (기존 /generate 로직과 동일)
        # [FIX] SituationInfoConverter를 이용한 표준 정규화 (0.0-1.0 보장)
        normalized_level, raw_val, level_label = SituationInfoConverter.normalize_threat_level(threat_event.threat_level)
        
        # 🔥 FIX: 프론트엔드 요청에서 approach_mode 및 임무 정보 추출
        threat_data = request.get('threat_data', {})
        user_params = request.get('user_params', {})
        
        # approach_mode 우선순위: threat_data > user_params > 기본값
        approach_mode = threat_data.get('approach_mode') or user_params.get('approach_mode') or 'threat_centered'
        
        situation_info.update({
            'threat_id': threat_event.threat_id,
            '위협ID': threat_event.threat_id,
            'threat_type': threat_event.threat_type_code,
            '위협유형': threat_event.threat_type_code,
            'threat_level': normalized_level,
            '위협수준': normalized_level,
            'location': threat_event.location_cell_id,
            '발생장소': threat_event.location_cell_id,
            'axis_id': threat_event.related_axis_id,
            '관련축선ID': threat_event.related_axis_id,
            'occurrence_time': str(threat_event.occurrence_time) if threat_event.occurrence_time else None,
            '탐지시각': str(threat_event.occurrence_time) if threat_event.occurrence_time else None,
            'raw_report_text': threat_event.raw_report_text,
            'approach_mode': approach_mode  # 🔥 FIX: 요청에서 받은 값 사용
        })
        
        # 🔥 FIX: 임무 관련 정보 추가 (임무 중심 모드에서 필요)
        mission_id = threat_data.get('related_mission_id') or threat_event.related_mission_id
        if mission_id:
            situation_info.update({
                'mission_id': mission_id,
                '임무ID': mission_id
            })
        
        # 임무명, 임무유형, 임무목표 (프론트엔드에서 전달)
        if threat_data.get('mission_name'):
            situation_info['mission_name'] = threat_data['mission_name']
            situation_info['임무명'] = threat_data['mission_name']
        if threat_data.get('mission_type'):
            situation_info['mission_type'] = threat_data['mission_type']
            situation_info['임무유형'] = threat_data['mission_type']
        if threat_data.get('mission_objective'):
            situation_info['mission_objective'] = threat_data['mission_objective']
            situation_info['임무목표'] = threat_data['mission_objective']
        
        # 데모 시나리오/수동 입력 플래그 유지
        if threat_data.get('is_demo'):
            situation_info['is_demo'] = True
        if threat_data.get('is_manual'):
            situation_info['is_manual'] = True
        
        # [FIX] 상황 정보 보강 로직 통합 호출
        from api.utils.code_label_mapper import get_mapper
        mapper = get_mapper()
        situation_info = _enrich_situation_info(situation_info, service, mapper)
        
        logger.info(f"[정황보고] 자연어 변환 완료: {situation_info.get('location_name')}, {situation_info.get('axis_name')}, {situation_info.get('위협유형')}")

        # [FIX] LLM 프롬프트용 변수 추출
        loc_id = situation_info.get('location') or situation_info.get('발생장소') or 'N/A'
        threat_type = situation_info.get('threat_type') or situation_info.get('위협유형') or 'UNKNOWN'
        threat_level = situation_info.get('threat_level', 0.5)
        axis_id = situation_info.get('axis_id') or situation_info.get('관련축선ID')
        
        # 1. 자연어가 주입된 situation_info로 캐시 조회 시도
        global_state = get_global_state()
        cached_summary = global_state.situation_summary_cache.get(situation_info)
        situation_summary = None
        situation_summary_source = None
        
        if cached_summary:
            logger.info("[정황보고] 캐시에서 조회됨")
            situation_summary = cached_summary
            situation_summary_source = "cache"
        elif service.llm_manager and service.llm_manager.is_available():
            try:
                # 🔥 FIX: situation_info에서 approach_mode 사용
                approach_mode = situation_info.get('approach_mode', 'threat_centered')
                logger.info(f"[정황보고] LLM 생성 시작 - approach_mode: {approach_mode}")
                
                # [FIX] 보강된 데이터 활용
                loc_display = situation_info.get('_loc_display', loc_id)
                axis_display = situation_info.get('_axis_display', axis_id)
                threat_display = situation_info.get('_threat_display', threat_type)
                enemy_ko = situation_info.get('_enemy_ko', '식별된 적 부대')
                raw_report = situation_info.get('raw_report_text', '')
                
                # 🔥 FIX: 임무 중심 모드인 경우 다른 프롬프트 사용
                if approach_mode == 'mission_centered':
                    # 임무 정보 추출
                    m_id = situation_info.get('mission_id') or situation_info.get('임무ID', 'N/A')
                    m_name = situation_info.get('mission_name') or situation_info.get('임무명', 'N/A')
                    m_type = situation_info.get('mission_type') or situation_info.get('임무유형', 'N/A')
                    m_objective = situation_info.get('mission_objective') or situation_info.get('임무목표', '')
                    
                    # 임무 성공 가능성 (위협 수준의 역수 개념)
                    if threat_level >= 0.8:
                        success_level_ko = "낮음"
                    elif threat_level >= 0.4:
                        success_level_ko = "보통"
                    else:
                        success_level_ko = "높음"
                    
                    prompt = f"""다음의 임무 정보와 작전 환경을 기반으로 지휘관에게 보고하는 자연스러운 임무 상황 요약 문장을 생성하세요.

## 임무 정보:
- 임무 ID: {m_id}
- 임무명: {m_name}
- 임무 유형: {m_type}
- 임무 목표: {m_objective if m_objective else '(미지정)'}

## 작전 환경:
- 작전 지역: {loc_display}
- 작전 축선: {axis_display}
- 예상 위협: {threat_display}
- 예상 위협 부대: {enemy_ko}
- 임무 성공 가능성: {success_level_ko} ({int((1-threat_level)*100) if threat_level < 1 else 50}%)

## 작문 지시사항:
1. **지휘관 보고 양식**: 지휘보고 형식을 갖추어 "~가 하달되었습니다", "~로 평가됩니다" 등 정중하고 명확한 군사적 문체를 사용하세요.
2. **이름 우선 표기**: TERR007 같은 코드보다는 **"가칠봉"** 같은 지식 그래프의 명칭을 주어로 사용하세요.
3. **핵심 강조**: 중요 정보는 **굵게** 표시하세요.
4. **분량**: **두 ~ 세 문장**으로 간결하게 작성하세요.

## 예시:
- 좋은 예: **가칠봉(TERR001)** 일대에서 **서쪽 고지 탈환(MSN001)** 임무가 하달되었습니다. 작전 축선은 **인제-양구 축선(AXIS06)**이며, 임무 성공 가능성은 **보통**으로 평가됩니다.

문장 생성:"""
                else:
                    # 위협 중심 모드
                    if threat_level >= 0.8:
                        t_level_ko = "높음"
                    elif threat_level >= 0.5:
                        t_level_ko = "중간"
                    else:
                        t_level_ko = "낮음"
                    
                    prompt = f"""다음의 원시 상황보고와 온톨로지 팩트를 기반으로 지휘관에게 보고하는 자연스러운 군사 상황 요약 문장을 생성하세요.

## 원시 상황보고 (최우선 참조):
{raw_report if raw_report else '(원시보고 없음 - 온톨로지 팩트만 사용)'}

## 보완 온톨로지 팩트:
- 발생시각: {situation_info.get('탐지시각', '최근')}
- 발생위치: {loc_display}
- 위협원: {enemy_ko}
- 위협유형: {threat_display}
- 관련축선: {axis_display}
- 위협수준: {t_level_ko} ({int(threat_level*100)}%)

## 작문 지시사항:
1. **기계적 코드 노출 방지**: TERR007, THR_TYPE_001 등의 **코드를 문장의 주어로 절대 사용하지 마세요.** 반드시 **가칠봉**, **침투** 등의 이름이나 지명을 사용하여 보고 문장을 시작하세요.
2. **전문적 보고체**: 지휘관에게 드리는 정식 상황 보고 체계를 갖추어 "~이 식별되었습니다", "~로 판단됩니다" 등의 표현을 사용하세요.
3. **원시보고 중심**: 원시 상황보고에 포함된 구체적인 행동 묘사를 최대한 보존하세요.
4. **핵심 강조**: 중요 정보는 **굵게** 표시하세요.
5. **분량**: **두 문장 내외**로 간결하게 작성하세요.

## 예시:
- 나쁜 예: TERR007 지역에서 THR_TYPE_001 위협이 식별됨.
- 좋은 예: **가칠봉(TERR007) 일대**에서 **적 기동 징후(THR_TYPE_001)**가 포착되었으며, 현재 **양구-인제 축선**을 향해 이동 중인 것으로 분석됩니다.

문장 생성:"""
                
                situation_summary = service.llm_manager.generate(prompt, max_tokens=256).strip()
                
                if situation_summary:
                    logger.info(f"[정황보고] LLM으로 생성됨 (길이: {len(situation_summary)})")
                    situation_summary_source = "llm"
                    global_state.situation_summary_cache.set(situation_info, situation_summary)
                else:
                    logger.warning("[정황보고] LLM 생성 결과가 비어있음. 템플릿 기반으로 fallback합니다.")
                    situation_summary = generate_template_based_summary(situation_info)
                    situation_summary_source = "template"
            except Exception as e:
                logger.warning(f"[정황보고] LLM 생성 실패: {e}. 템플릿 기반으로 fallback합니다.")
                situation_summary = generate_template_based_summary(situation_info)
                situation_summary_source = "template"
        else:
            logger.info("[정황보고] LLM 사용 불가. 템플릿 기반으로 생성합니다.")
            situation_summary = generate_template_based_summary(situation_info)
            situation_summary_source = "template"
        
        return {
            "threat_id": threat_event.threat_id if threat_event else situation_info.get('threat_id'),
            "situation_id": situation_info.get('situation_id'),  # 🔥 FIX: 데모 시나리오 ID 지원
            "situation_summary": situation_summary,
            "situation_summary_source": situation_summary_source
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-visualization")
def generate_coa_visualization(
    coa_data: Dict[str, Any] = Body(...),
    service: COAService = Depends(get_coa_service)
):
    """
    COA 시각화 데이터를 생성합니다.
    
    Request body:
    {
        "coa_id": "COA_Library_COA_DEF_002",
        "participating_units": ["보병여단", "포병대대"],
        "threat_position": {"latitude": 38.5, "longitude": 127.0}  // optional
    }
    
    Returns:
    {
        "unit_positions": { ... GeoJSON ...},
        "operational_path": { ... },
        "operational_area": { ... }
    }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        coa_id = coa_data.get("coa_id")
        participating_units = coa_data.get("participating_units", [])
        threat_position = coa_data.get("threat_position")
        
        logger.info(f"[시각화 API] COA {coa_id} 시각화 데이터 생성 요청")
        logger.info(f"  - participating_units: {participating_units}")
        
        # 시각화 생성기 초기화 (data_lake_path는 자동으로 설정됨)
        viz_generator = VisualizationDataGenerator()
        
        # 부대 정보 조회
        friendly_units = []
        for unit_id in participating_units:
            unit_info = {"unit_id": unit_id}
            try:
                friendly_units_data = service.data_manager.load_table('아군부대현황')
                if friendly_units_data is not None and not friendly_units_data.empty:
                    # 먼저 아군부대ID로 조회
                    unit_row = friendly_units_data[friendly_units_data['아군부대ID'] == unit_id]
                    
                    # ID로 찾지 못하면 부대명으로 조회 (COA 라이브러리 호환성)
                    if unit_row.empty:
                        unit_row = friendly_units_data[friendly_units_data['부대명'] == unit_id]
                    
                    if not unit_row.empty:
                        unit_info.update({
                            "부대명": str(unit_row.iloc[0].get("부대명", "")),
                            "제대": str(unit_row.iloc[0].get("제대", "")),
                            "병종": str(unit_row.iloc[0].get("병종", "")),
                            "배치지형셀ID": str(unit_row.iloc[0].get("배치지형셀ID", "")),
                            "좌표정보": str(unit_row.iloc[0].get("좌표정보", "")),
                            "전투력지수": float(unit_row.iloc[0].get("전투력지수", 0)),
                        })
                        logger.info(f"  - 부대 정보 조회 성공: {unit_id} → {unit_info.get('부대명', 'Unknown')}")
                    else:
                        logger.warning(f"  - 부대를 찾을 수 없음: {unit_id}")
            except Exception as e:
                logger.warning(f"  - 부대 정보 조회 실패: {unit_id} - {e}")
            friendly_units.append(unit_info)
        
        logger.info(f"  - 조회된 부대 수: {len(friendly_units)}")
        
        # 시각화 데이터 생성
        result = {}
        
        # unit_positions 생성
        unit_positions = viz_generator.generate_unit_positions_geojson(friendly_units)
        result["unit_positions"] = unit_positions
        logger.info(f"  - unit_positions 생성 완료: features 개수 = {len(unit_positions.get('features', [])) if unit_positions else 0}")
        
        # operational_path 생성
        try:
            op_path = viz_generator.generate_operational_path(
                coa={"coa_id": coa_id},
                friendly_units=friendly_units,
                threat_position=threat_position,
                main_axis_id=None
            )
            if op_path:
                result["operational_path"] = op_path
                logger.info(f"  - operational_path 생성 완료: waypoints 개수 = {len(op_path.get('waypoints', []))}")
        except Exception as e:
            logger.warning(f"  - operational_path 생성 실패: {e}")
            result["operational_path"] = None
        
        # operational_area 생성
        try:
            op_area = viz_generator.generate_operational_area(
                friendly_units=friendly_units,
                threat_position=threat_position
            )
            if op_area:
                result["operational_area"] = op_area
                logger.info(f"  - operational_area 생성 완료")
        except Exception as e:
            logger.warning(f"  - operational_area 생성 실패: {e}")
            result["operational_area"] = None
        
        return result
        
    except Exception as e:
        logger.error(f"[시각화 API] 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))
