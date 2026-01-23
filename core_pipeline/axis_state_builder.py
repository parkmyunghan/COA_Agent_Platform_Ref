# core_pipeline/axis_state_builder.py
# -*- coding: utf-8 -*-
"""
Axis State Builder
축선별 전장상태 요약 객체 생성 모듈
"""
from typing import List, Dict, Optional
import pandas as pd

from core_pipeline.data_models import (
    Mission, Axis, TerrainCell, FriendlyUnit, EnemyUnit,
    Constraint, ThreatEvent, AxisState, Resource
)
from core_pipeline.threat_scoring import ThreatScorer
from core_pipeline.data_manager import DataManager
from common.logger import get_logger

logger = get_logger("AxisStateBuilder")


class AxisStateBuilder:
    """축선별 전장상태 요약 객체 빌더"""
    
    def __init__(self, data_manager: DataManager, ontology_manager=None):
        """
        Args:
            data_manager: DataManager 인스턴스
            ontology_manager: OntologyManager 인스턴스 (METT-C 평가용)
        """
        self.data_manager = data_manager
        self.ontology_manager = ontology_manager
        self._data_cache: Optional[Dict[str, pd.DataFrame]] = None
        self._model_cache: Dict[str, List] = {}
        self._threat_master_cache: Optional[Dict[str, Dict]] = None
        
        if self.ontology_manager is None:
            logger.warning("AxisStateBuilder initialized without ontology_manager. METT-C features will be limited.")
    
    def _load_data(self) -> Dict[str, pd.DataFrame]:
        """데이터 로드 (캐싱)"""
        if self._data_cache is None:
            self._data_cache = self.data_manager.load_all()
        return self._data_cache
    
    def _get_models(self, table_name: str, model_class) -> List:
        """테이블 데이터를 모델 객체 리스트로 변환 (캐싱)"""
        cache_key = f"{table_name}_{model_class.__name__}"
        if cache_key not in self._model_cache:
            data = self._load_data()
            df = data.get(table_name)
            if df is None or df.empty:
                self._model_cache[cache_key] = []
            else:
                models = []
                for _, row in df.iterrows():
                    try:
                        model = model_class.from_row(row.to_dict())
                        models.append(model)
                    except Exception as e:
                        logger.warning(f"Failed to create {model_class.__name__} from row: {e}")
                
                # [NEW] ThreatEvent인 경우 마스터 데이터 병합
                if model_class.__name__ == 'ThreatEvent':
                    self._hydrate_threat_events(models)
                    
                self._model_cache[cache_key] = models
        return self._model_cache[cache_key]

    def _load_threat_master(self) -> Dict[str, Dict]:
        """위협유형 마스터 데이터 로드 (캐싱)"""
        if self._threat_master_cache is not None:
            return self._threat_master_cache
            
        master_dict = {}
        try:
            # DataManager를 통해 로드 (파일명이 설정에 없으면 data_lake에서 자동 스캔됨)
            # data_manager.load_table('위협유형_마스터') 호출 시 config에 없으면 data_lake 우선 검색
            # 하지만 명시적으로 파일명이 다를 수 있으므로 data_lake 로드 결과를 확인하거나 직접 로드 시도
            
            # 1. load_all() 결과에서 찾기 (이미 캐시되어 있을 수 있음)
            data = self._load_data()
            df = data.get('위협유형_마스터')
            
            # 2. 없으면 직접 로드 시도
            if df is None:
                try:
                    df = self.data_manager.load_table('위협유형_마스터')
                except:
                    pass
            
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    code = row_dict.get('위협유형코드')
                    if code:
                        master_dict[str(code)] = row_dict
                logger.info(f"Loaded {len(master_dict)} threat master records")
            else:
                logger.warning("Threat master table not found or empty")
                
        except Exception as e:
            logger.warning(f"Failed to load threat master data: {e}")
            
        self._threat_master_cache = master_dict
        return master_dict

    def _hydrate_threat_events(self, threat_events: List[ThreatEvent]):
        """ThreatEvent 객체에 마스터 데이터 주입"""
        master_data = self._load_threat_master()
        if not master_data:
            return
            
        # [NEW] 이름으로도 찾을 수 있게 역인덱싱 (데이터 불일치 대응)
        master_by_name = {}
        for code, info in master_data.items():
            name = info.get('위협유형명', info.get('위협명'))
            if name:
                master_by_name[str(name).strip()] = info
            
        count = 0
        for event in threat_events:
            if not event.threat_type_code:
                continue
                
            code_key = str(event.threat_type_code).strip()
            info = None
            
            # 1. 코드로 매핑 시도
            if code_key in master_data:
                info = master_data[code_key]
            # 2. 이름으로 매핑 시도 (Fallback)
            elif code_key in master_by_name:
                info = master_by_name[code_key]
                # 코드가 이름으로 되어있는 경우, 실제 코드로 업데이트 (옵션)
                # event.threat_type_code = info.get('위협유형코드') 
            
            if info:
                # 필드 주입
                event.threat_name = info.get('위협유형명', info.get('위협명'))
                event.description = info.get('설명')
                event.keywords = info.get('대표키워드')
                event.severity = info.get('위협심도')
                count += 1
                
        if count > 0:
            logger.info(f"Hydrated {count} threat events with master data")
    
    def build_axis_states(self, mission_id: str) -> List[AxisState]:
        """
        임무ID를 입력받아 축선별 전장상태 요약 객체 리스트 생성
        
        Args:
            mission_id: 임무ID
            
        Returns:
            AxisState 객체 리스트
        """
        # 1. 임무 정보 조회
        missions = self._get_models('임무정보', Mission)
        mission = next((m for m in missions if m.mission_id == mission_id), None)
        
        if not mission:
            logger.warning(f"Mission not found: {mission_id}")
            return []
        
        # 2. 임무와 관련된 축선 조회
        axes = self._get_models('전장축선', Axis)
        related_axes = []
        
        # 방법 1: 주요축선ID가 있으면 해당 축선만 사용
        if mission.primary_axis_id:
            related_axes = [a for a in axes if a.axis_id == mission.primary_axis_id]
            if related_axes:
                logger.info(f"Using primary axis: {mission.primary_axis_id}")
        
        # 방법 2: 임무에 할당된 아군부대의 배치축선ID로 추론
        if not related_axes:
            friendly_units = self._get_models('아군부대현황', FriendlyUnit)
            mission_units = [u for u in friendly_units if u.assigned_mission_id == mission_id]
            related_axis_ids = {u.deployed_axis_id for u in mission_units if u.deployed_axis_id}
            related_axes = [a for a in axes if a.axis_id in related_axis_ids]
            if related_axes:
                logger.info(f"Found {len(related_axes)} axes from assigned units")
        
        # 방법 3: 위협상황이 있는 축선 사용 (폴백)
        if not related_axes:
            threat_events = self._get_models('위협상황', ThreatEvent)
            # 위협상황의 related_axis_id 또는 location_cell_id로 추론
            threat_axis_ids = set()
            for threat in threat_events:
                if hasattr(threat, 'related_axis_id') and threat.related_axis_id:
                    threat_axis_ids.add(threat.related_axis_id)
            related_axes = [a for a in axes if a.axis_id in threat_axis_ids]
            if related_axes:
                print(f"[INFO] Using {len(related_axes)} axes with threat events (fallback)")
        
        # 방법 4: 모든 축선 사용 (최종 폴백)
        if not related_axes:
            related_axes = axes
            print(f"[WARN] No specific axes found for mission {mission_id}, using all {len(axes)} axes (final fallback)")
        
        if not related_axes:
            print(f"[ERROR] No axes available in the system")
            return []
        
        # 3. 각 축선별로 AxisState 생성
        axis_states = []
        for axis in related_axes:
            axis_state = self._build_axis_state(axis, mission_id)
            if axis_state:
                axis_states.append(axis_state)
        
        return axis_states
    
    def build_axis_states_from_threat(
        self,
        threat_event: ThreatEvent,
        mission_id: Optional[str] = None
    ) -> List[AxisState]:
        """
        위협상황 중심으로 축선별 전장상태 빌드
        
        Args:
            threat_event: 위협상황 객체
            mission_id: 임무ID (선택적, 없으면 위협상황에서 추론)
        
        Returns:
            AxisState 객체 리스트
        """
        # 1. 위협상황의 축선 확인
        if not threat_event.related_axis_id:
            # [NEW] 지형셀 기반 축선 추론 폴백 (데이터 불완전성 대응)
            if threat_event.location_cell_id:
                try:
                    axes_candidate = self._get_models('전장축선', Axis)
                    for axis_candidate in axes_candidate:
                        if threat_event.location_cell_id in axis_candidate.related_terrain_cells:
                            threat_event.related_axis_id = axis_candidate.axis_id
                            # print(f"[INFO] 지형셀 {threat_event.location_cell_id}을 기반으로 축선 {axis_candidate.axis_id} 추론 성공")
                            break
                except Exception as e:
                    print(f"[DEBUG] 축선 추론 실패: {e}")

        if not threat_event.related_axis_id:
            logger.warning(f"위협상황 {threat_event.threat_id}에 관련축선ID가 없습니다. (지형셀 기반 추론도 실패)")
            
            # [NEW] 임무 기반 축선 추론 (Fallback)
            if mission_id:
                missions = self._get_models('임무정보', Mission)
                mission = next((m for m in missions if m.mission_id == mission_id), None)
                if mission and mission.primary_axis_id:
                    threat_event.related_axis_id = mission.primary_axis_id
                    logger.info(f"임무 {mission_id}의 주요축선 {mission.primary_axis_id}를 위협 축선으로 설정합니다.")
            
            # [NEW] 그래도 없으면 시스템의 첫 번째 축선 사용 (Last Resort)
            if not threat_event.related_axis_id:
                axes = self._get_models('전장축선', Axis)
                if axes:
                    threat_event.related_axis_id = axes[0].axis_id
                    logger.warning(f"축선을 찾을 수 없어 첫 번째 축선 {axes[0].axis_id}를 기본값으로 사용합니다.")
                else:
                    return []
        
        axes = self._get_models('전장축선', Axis)
        related_axis = next(
            (a for a in axes if a.axis_id == threat_event.related_axis_id),
            None
        )
        
        if not related_axis:
            print(f"[WARN] 축선을 찾을 수 없습니다: {threat_event.related_axis_id}")
            return []
        
        # 2. 임무ID 확인 (없으면 위협상황에서 추론)
        if not mission_id:
            if threat_event.related_mission_id:
                mission_id = threat_event.related_mission_id
            else:
                # 기본 방어임무 사용
                missions = self._get_models('임무정보', Mission)
                defense_missions = [
                    m for m in missions
                    if m.mission_type and m.mission_type in ['방어', 'defense', 'DEFENSE']
                ]
                if defense_missions:
                    mission_id = defense_missions[0].mission_id
                else:
                    print("[WARN] 방어임무를 찾을 수 없습니다.")
                    return []
        
        # 3. 해당 축선의 상태 빌드
        axis_state = self._build_axis_state(related_axis, mission_id)
        if not axis_state:
            return []
        
        # 4. 위협상황을 threat_events에 추가 (중복 체크)
        # threat_id로 중복 확인
        existing_threat_ids = {t.threat_id for t in axis_state.threat_events}
        if threat_event.threat_id not in existing_threat_ids:
            axis_state.threat_events.append(threat_event)
        
        # 5. 위협지수 재계산 (위협상황 추가 반영)
        axis_state.threat_score_total = ThreatScorer.calculate_axis_threat_score(
            axis_state.threat_events
        )
        axis_state.threat_level = ThreatScorer.determine_threat_level(
            axis_state.threat_score_total
        )
        
        return [axis_state]
    
    def _build_axis_state(self, axis: Axis, mission_id: str) -> Optional[AxisState]:
        """
        단일 축선의 전장상태 요약 객체 생성
        
        Args:
            axis: 축선 객체
            mission_id: 임무ID
            
        Returns:
            AxisState 객체
        """
        # 아군부대 조회
        friendly_units = self._get_models('아군부대현황', FriendlyUnit)
        
        # 축선 매칭: 축선 ID 또는 축선명으로 매칭 (대소문자 무시, 공백 정규화)
        axis_friendly_units = []
        
        # 축선 ID와 이름을 정규화 (대소문자 무시, 공백 제거)
        axis_id_normalized = str(axis.axis_id).strip().upper() if axis.axis_id else ""
        axis_name_normalized = str(axis.axis_name).strip().upper() if axis.axis_name else ""
        
        for u in friendly_units:
            if not u.deployed_axis_id:
                continue
            
            # 배치축선ID 정규화
            deployed_axis_normalized = str(u.deployed_axis_id).strip().upper()
            
            # 축선 매칭 확인 (정규화된 값으로 비교)
            axis_matched = False
            
            # 1. 정확한 ID 매칭
            if deployed_axis_normalized == axis_id_normalized:
                axis_matched = True
            # 2. 정확한 이름 매칭
            elif deployed_axis_normalized == axis_name_normalized:
                axis_matched = True
            # 3. 부분 매칭 (양방향)
            elif axis_name_normalized and axis_name_normalized in deployed_axis_normalized:
                axis_matched = True
            elif axis_name_normalized and deployed_axis_normalized in axis_name_normalized:
                axis_matched = True
            # 4. 축선 ID 부분 매칭
            elif axis_id_normalized and axis_id_normalized in deployed_axis_normalized:
                axis_matched = True
            elif axis_id_normalized and deployed_axis_normalized in axis_id_normalized:
                axis_matched = True
            
            if not axis_matched:
                continue
            
            # 임무 매칭 확인 (assigned_mission_id가 있으면 일치해야 함, 없으면 축선만으로도 매칭)
            if u.assigned_mission_id:
                if str(u.assigned_mission_id).strip() == str(mission_id).strip():
                    axis_friendly_units.append(u)
            else:
                # assigned_mission_id가 없으면 축선만으로 매칭 (할당되지 않은 부대도 포함)
                axis_friendly_units.append(u)
                # assigned_mission_id가 없으면 축선만으로 매칭 (할당되지 않은 부대도 포함)
                axis_friendly_units.append(u)
        
        # [NEW] 자산(Resource) 조회 및 매칭 (공간 기반)
        resources = self._get_models('아군가용자산', Resource)
        axis_resources = []
        for res in resources:
            if res.location_cell_id in axis.related_terrain_cells:
                axis_resources.append(res)
        
        # [NEW] 기동 소요 시간 계산
        # 기준: 축선 거리 / 부대 최소 이동속도 (가장 느린 부대 기준 - 제파식 기동 고려시 로직 고도화 가능)
        max_traversal_time = None
        if axis.total_distance_km and axis_friendly_units:
            # 이동속도가 있는 부대만 필터링
            valid_speeds = [u.max_speed_kmh for u in axis_friendly_units if u.max_speed_kmh and u.max_speed_kmh > 0]
            if valid_speeds:
                min_speed = min(valid_speeds)
                max_traversal_time = float(axis.total_distance_km) / float(min_speed)
                logger.debug(f"축선 {axis.axis_id} 기동시간 산출: {axis.total_distance_km}km / {min_speed}km/h = {max_traversal_time:.2f}h")
        # 디버깅: 매칭된 부대 수 로그
        if axis_friendly_units:
            total_power = sum(u.combat_power or 0 for u in axis_friendly_units)
            logger.info(f"축선 {axis.axis_id} ({axis.axis_name})에 {len(axis_friendly_units)}개 아군 부대 매칭 (총 전투력: {total_power})")
            # 매칭된 부대 상세 정보
            for u in axis_friendly_units[:5]:  # 최대 5개만 출력
                logger.debug(f"  - {u.friendly_unit_id}: 전투력={u.combat_power}, 배치축선ID={u.deployed_axis_id}, 할당임무ID={u.assigned_mission_id}")
        else:
            logger.warning(f"축선 {axis.axis_id} ({axis.axis_name})에 아군 부대가 매칭되지 않음")
            # 디버깅: 전체 아군 부대의 배치축선ID 확인
            all_deployed_axis_ids = {u.deployed_axis_id for u in friendly_units if u.deployed_axis_id}
            logger.debug(f"전체 아군 부대의 배치축선ID 목록: {all_deployed_axis_ids}")
            logger.debug(f"현재 축선 ID: {axis.axis_id}, 축선명: {axis.axis_name}")
            logger.debug(f"현재 임무 ID: {mission_id}")
            # 매칭 실패 원인 분석: 각 부대의 배치축선ID와 할당임무ID 확인
            logger.debug(f"아군 부대 상세 정보 (최대 10개):")
            for u in friendly_units[:10]:
                axis_match = "✓" if (u.deployed_axis_id == axis.axis_id or 
                                     u.deployed_axis_id == axis.axis_name or
                                     (axis.axis_name and axis.axis_name in str(u.deployed_axis_id)) or
                                     (axis.axis_name and str(u.deployed_axis_id) in axis.axis_name)) else "✗"
                mission_match = "✓" if (not u.assigned_mission_id or u.assigned_mission_id == mission_id) else "✗"
                logger.debug(f"  - {u.friendly_unit_id}: 배치축선ID='{u.deployed_axis_id}' ({axis_match}), 할당임무ID='{u.assigned_mission_id}' ({mission_match}), 전투력={u.combat_power}")
        
        # 적군부대 조회 (축선 ID 또는 축선명으로 매칭, 정규화 적용)
        enemy_units = self._get_models('적군부대현황', EnemyUnit)
        axis_enemy_units = []
        for u in enemy_units:
            if not u.deployed_axis_id:
                continue
            
            # 배치축선ID 정규화
            deployed_axis_normalized = str(u.deployed_axis_id).strip().upper()
            
            # 정규화된 값으로 매칭
            if (deployed_axis_normalized == axis_id_normalized or
                deployed_axis_normalized == axis_name_normalized or
                (axis_name_normalized and axis_name_normalized in deployed_axis_normalized) or
                (axis_name_normalized and deployed_axis_normalized in axis_name_normalized) or
                (axis_id_normalized and axis_id_normalized in deployed_axis_normalized) or
                (axis_id_normalized and deployed_axis_normalized in axis_id_normalized)):
                axis_enemy_units.append(u)
        
        # 지형셀 조회
        terrain_cells = self._get_models('지형셀', TerrainCell)
        axis_terrain_cells = [
            t for t in terrain_cells
            if t.terrain_cell_id in axis.related_terrain_cells
        ]
        
        # 제약조건 조회
        constraints = self._get_models('제약조건', Constraint)
        axis_constraints = [
            c for c in constraints
            if c.target_type == '축선' and c.target_id == axis.axis_id
        ]
        
        # 위협상황 조회 (related_axis_id 또는 related_mission_id로 매칭)
        threat_events = self._get_models('위협상황', ThreatEvent)
        axis_threat_events = [
            t for t in threat_events
            if (t.related_axis_id == axis.axis_id) or 
               (t.related_mission_id == mission_id and not t.related_axis_id)
        ]
        
        # 민간인지역 및 기상 데이터 조회 (METT-C의 C, W 요소)
        from core_pipeline.data_models import CivilianArea, Weather
        civilian_areas = self._get_models('민간인지역', CivilianArea)
        axis_civilian_areas = [
            c for c in civilian_areas
            if c.location_cell_id in axis.related_terrain_cells
        ]
        
        # [NEW] 기상 상황 조회 (METT-C의 W 요소)
        weather_conditions = self._get_models('기상상황', Weather)
        axis_weather_conditions = [
            w for w in weather_conditions
            if w.location_cell_id in axis.related_terrain_cells
        ]
        
        # 아군 전투력 지표 계산
        friendly_combat_power_total = sum(
            u.combat_power or 0 for u in axis_friendly_units
        )
        
        # 적군 전투력 지표 계산
        enemy_combat_power_total = sum(
            u.combat_power or 0 for u in axis_enemy_units
        )
        
        # 기동성/지형 요약 계산
        mobility_grades = [t.mobility_grade for t in axis_terrain_cells if t.mobility_grade is not None]
        avg_mobility_grade = sum(mobility_grades) / len(mobility_grades) if mobility_grades else None
        
        defense_advantages = [t.defense_advantage for t in axis_terrain_cells if t.defense_advantage is not None]
        avg_defense_advantage = sum(defense_advantages) / len(defense_advantages) if defense_advantages else None
        
        key_point_count = sum(
            1 for t in axis_terrain_cells
            if t.is_key_point and t.is_key_point.upper() in ['Y', 'YES', '예', 'O']
        )
        
        # 제약조건 요약
        constraint_summary = self._build_constraint_summary(axis_constraints)
        
        # 위협점수 계산
        threat_score_total = ThreatScorer.calculate_axis_threat_score(axis_threat_events)
        threat_level = ThreatScorer.determine_threat_level(threat_score_total)
        
        # AxisState 객체 생성
        axis_state = AxisState(
            axis_id=axis.axis_id,
            axis_name=axis.axis_name,
            friendly_combat_power_total=friendly_combat_power_total,
            friendly_unit_count=len(axis_friendly_units),
            friendly_units=axis_friendly_units,
            enemy_combat_power_total=enemy_combat_power_total,
            enemy_unit_count=len(axis_enemy_units),
            enemy_units=axis_enemy_units,
            terrain_cells=axis_terrain_cells,
            avg_mobility_grade=avg_mobility_grade,
            avg_defense_advantage=avg_defense_advantage,
            key_point_count=key_point_count,
            constraints=axis_constraints,
            constraint_summary=constraint_summary,
            threat_score_total=threat_score_total,
            threat_level=threat_level,
            threat_events=axis_threat_events,
            resources=axis_resources,
            max_traversal_time_hours=max_traversal_time,
            civilian_areas=axis_civilian_areas,
            weather_conditions=axis_weather_conditions
        )
        
        return axis_state
    
    def _build_constraint_summary(self, constraints: List[Constraint]) -> str:
        """
        제약조건 요약 텍스트 생성
        
        Args:
            constraints: 제약조건 리스트
            
        Returns:
            제약조건 요약 텍스트
        """
        if not constraints:
            return "제약조건 없음"
        
        summaries = []
        for constraint in constraints:
            summary = f"{constraint.constraint_type}: {constraint.content or '내용 없음'}"
            if constraint.importance:
                # 중요도: 1~5 범위, 높을수록 중요 (5=치명적, 1=선택적)
                summary += f" (중요도: {constraint.importance})"
            summaries.append(summary)
        
        return "; ".join(summaries)
    
    def get_axis_state(self, axis_id: str, mission_id: Optional[str] = None) -> Optional[AxisState]:
        """
        특정 축선의 전장상태 요약 객체 조회
        
        Args:
            axis_id: 축선ID
            mission_id: 임무ID (선택적, 없으면 해당 축선의 모든 아군부대 포함)
            
        Returns:
            AxisState 객체 또는 None
        """
        axes = self._get_models('전장축선', Axis)
        axis = next((a for a in axes if a.axis_id == axis_id), None)
        
        if not axis:
            return None
        
        # mission_id가 없으면 임의의 mission_id로 처리 (모든 아군부대 포함)
        if mission_id is None:
            # 첫 번째 임무 ID 사용 (임시)
            missions = self._get_models('임무정보', Mission)
            if missions:
                mission_id = missions[0].mission_id
            else:
                mission_id = ""
        
        return self._build_axis_state(axis, mission_id)

