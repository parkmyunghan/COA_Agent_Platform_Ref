# core_pipeline/data_models.py
# -*- coding: utf-8 -*-
"""
Data Models
표준 엑셀 스키마 기반 데이터 모델 (dataclass)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd


@dataclass
class Mission:
    """임무정보 모델"""
    mission_id: str
    mission_type: Optional[str] = None
    commander_intent: Optional[str] = None
    superior_guidance: Optional[str] = None
    primary_axis_id: Optional[str] = None
    # time_limit 필드는 하위 호환성을 위해 유지하되, 내부적으로는 end_time을 사용 권장
    _time_limit: Optional[datetime] = None 
    start_time: Optional[datetime] = None  # 작전개시시각
    end_time: Optional[datetime] = None    # 작전종료예상
    priority: Optional[int] = None
    operation_area: Optional[str] = None  # 작전지역 (예: '동부전선', '산악지역')
    remarks: Optional[str] = None
    
    @property
    def time_limit(self) -> Optional[datetime]:
        """하위 호환성을 위한 time_limit 속성 (end_time 반환)"""
        return self.end_time or self._time_limit

    @time_limit.setter
    def time_limit(self, value: Optional[datetime]):
        self._time_limit = value

    @classmethod
    def from_row(cls, row: Dict) -> 'Mission':
        """DataFrame 행에서 Mission 객체 생성"""
        # 시간 파싱 헬퍼
        def parse_time(val):
            if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                return None
            try:
                if isinstance(val, (pd.Timestamp, datetime)):
                    return val
                return pd.to_datetime(val)
            except:
                return None

        return cls(
            mission_id=str(row.get('임무ID', row.get('mission_id', ''))),
            mission_type=row.get('임무종류', row.get('mission_type')),
            commander_intent=row.get('지휘관의도', row.get('commander_intent')),
            superior_guidance=row.get('상급부대지침', row.get('superior_guidance')),
            primary_axis_id=row.get('주요축선ID', row.get('primary_axis_id')),
            _time_limit=parse_time(row.get('시간제한', row.get('time_limit'))),
            start_time=parse_time(row.get('작전개시시각', row.get('start_time'))),
            end_time=parse_time(row.get('작전종료예상', row.get('end_time'))),
            priority=row.get('우선순위', row.get('priority')),
            operation_area=row.get('작전지역', row.get('operation_area', row.get('구역', row.get('지역')))),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class Axis:
    """전장축선 모델"""
    axis_id: str
    axis_name: Optional[str] = None
    description: Optional[str] = None
    related_terrain_cells: List[str] = field(default_factory=list)
    importance: Optional[int] = None
    defense_priority: Optional[int] = None
    total_distance_km: Optional[float] = None  # NEW: 축선 전체 길이 (기동시간 산출용)
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'Axis':
        """DataFrame 행에서 Axis 객체 생성"""
        # 관련지형셀리스트 파싱 (쉼표 구분)
        terrain_cells_str = row.get('관련지형셀리스트', row.get('related_terrain_cells', ''))
        terrain_cells = []
        if terrain_cells_str:
            # pandas의 isna 체크 (값이 None이거나 NaN인 경우)
            try:
                import pandas as pd
                is_na = pd.isna(terrain_cells_str)
            except:
                is_na = terrain_cells_str is None or terrain_cells_str == ''
            
            if not is_na:
                terrain_cells = [cell.strip() for cell in str(terrain_cells_str).split(',') if cell.strip()]
        
        return cls(
            axis_id=str(row.get('축선ID', row.get('axis_id', ''))),
            axis_name=row.get('축선명', row.get('axis_name')),
            description=row.get('설명', row.get('description')),
            related_terrain_cells=terrain_cells,
            importance=row.get('중요도', row.get('importance')),
            defense_priority=row.get('방어우선순위', row.get('defense_priority')),
            total_distance_km=row.get('거리_km', row.get('total_distance_km')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class TerrainCell:
    """지형셀 모델"""
    terrain_cell_id: str
    terrain_name: Optional[str] = None
    terrain_type: Optional[str] = None
    mobility_grade: Optional[int] = None
    defense_advantage: Optional[int] = None
    observation_advantage: Optional[int] = None
    is_key_point: Optional[str] = None
    coordinates: Optional[str] = None
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'TerrainCell':
        """DataFrame 행에서 TerrainCell 객체 생성"""
        return cls(
            terrain_cell_id=str(row.get('지형셀ID', row.get('terrain_cell_id', ''))),
            terrain_name=row.get('지형명', row.get('terrain_name')),
            terrain_type=row.get('지형유형', row.get('terrain_type')),
            mobility_grade=row.get('기동성등급', row.get('mobility_grade')),
            defense_advantage=row.get('방어유리도', row.get('defense_advantage')),
            observation_advantage=row.get('관측유리도', row.get('observation_advantage')),
            is_key_point=row.get('요충지여부', row.get('is_key_point')),
            coordinates=row.get('좌표정보', row.get('coordinates')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class FriendlyUnit:
    """아군부대현황 모델"""
    friendly_unit_id: str
    unit_name: Optional[str] = None
    unit_level: Optional[str] = None
    unit_type: Optional[str] = None
    combat_power: Optional[int] = None
    deployed_axis_id: Optional[str] = None
    deployed_terrain_cell_id: Optional[str] = None
    availability_status: Optional[str] = None
    mission_role: Optional[str] = None
    assigned_mission_id: Optional[str] = None
    max_speed_kmh: Optional[int] = None  # NEW: 이동속도 (km/h)
    direction: Optional[int] = None      # NEW: 이동방향 (Azimuth)
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'FriendlyUnit':
        """DataFrame 행에서 FriendlyUnit 객체 생성"""
        return cls(
            friendly_unit_id=str(row.get('아군부대ID', row.get('friendly_unit_id', ''))),
            unit_name=row.get('부대명', row.get('unit_name')),
            unit_level=row.get('제대', row.get('unit_level')),
            unit_type=row.get('병종', row.get('unit_type')),
            combat_power=row.get('전투력지수', row.get('combat_power')),
            deployed_axis_id=row.get('배치축선ID', row.get('deployed_axis_id')),
            deployed_terrain_cell_id=row.get('배치지형셀ID', row.get('deployed_terrain_cell_id')),
            availability_status=row.get('가용상태', row.get('availability_status')),
            mission_role=row.get('임무역할', row.get('mission_role')),
            assigned_mission_id=row.get('할당임무ID', row.get('assigned_mission_id')),
            max_speed_kmh=row.get('이동속도_kmh', row.get('max_speed_kmh')), # 이동속도 -> 이동속도_kmh로 엑셀 마이그레이션됨
            direction=row.get('이동방향', row.get('direction')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class Resource:
    """아군가용자산 모델 (NEW)"""
    asset_id: str
    name: Optional[str] = None
    type: Optional[str] = None
    quantity: int = 0
    location_cell_id: Optional[str] = None
    status: Optional[str] = "사용가능"
    combat_power_index: Optional[int] = None
    max_speed_kmh: Optional[int] = None
    detection_range_km: Optional[float] = None
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'Resource':
        """DataFrame 행에서 Resource 객체 생성"""
        return cls(
            asset_id=str(row.get('자산ID', row.get('asset_id', ''))),
            name=row.get('자산명', row.get('name')),
            type=row.get('자산종류', row.get('type')),
            quantity=int(row.get('수량', row.get('quantity', 0))),
            location_cell_id=row.get('배치지형셀ID', row.get('location_cell_id')),
            status=row.get('가용상태', row.get('status', '사용가능')),
            combat_power_index=row.get('전투력지수', row.get('combat_power_index')),
            max_speed_kmh=row.get('이동속도_kmh', row.get('max_speed_kmh')),
            detection_range_km=row.get('감지범위_km', row.get('detection_range_km')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class EnemyUnit:
    """적군부대현황 모델"""
    enemy_unit_id: str
    unit_name: Optional[str] = None
    unit_level: Optional[str] = None
    unit_type: Optional[str] = None
    combat_power: Optional[int] = None
    deployed_axis_id: Optional[str] = None
    deployed_terrain_cell_id: Optional[str] = None
    location_confidence: Optional[int] = None
    threat_level: Optional[str] = None
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'EnemyUnit':
        """DataFrame 행에서 EnemyUnit 객체 생성"""
        return cls(
            enemy_unit_id=str(row.get('적군부대ID', row.get('enemy_unit_id', ''))),
            unit_name=row.get('부대명', row.get('unit_name')),
            unit_level=row.get('제대', row.get('unit_level')),
            unit_type=row.get('병종', row.get('unit_type')),
            combat_power=row.get('전투력지수', row.get('combat_power')),
            deployed_axis_id=row.get('배치축선ID', row.get('deployed_axis_id')),
            deployed_terrain_cell_id=row.get('배치지형셀ID', row.get('deployed_terrain_cell_id')),
            location_confidence=row.get('추정위치확실도', row.get('location_confidence')),
            threat_level=row.get('위협수준', row.get('threat_level')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class Constraint:
    """
    제약조건 모델 (시간 제약 강화)
    
    제약조건은 COA 실행 시 반드시 고려해야 하는 제한사항을 정의합니다.
    """
    
    # 중요도 상수 정의 (높은 숫자 = 높은 중요도)
    IMPORTANCE_CRITICAL = 5      # 치명적: 반드시 준수해야 함 (예: ROE, 민간인 보호)
    IMPORTANCE_HIGH = 4          # 높음: 가능한 준수 권장 (예: 시간제한, 이동제한)
    IMPORTANCE_MEDIUM = 3        # 중간: 준수 권장 (예: 화력제한, 통신유지)
    IMPORTANCE_LOW = 2           # 낮음: 참고사항 (예: 정보제한)
    IMPORTANCE_OPTIONAL = 1      # 선택: 가능하면 고려 (예: 기상상황)
    
    # 하위 호환성을 위한 별칭 (Deprecated)
    PRIORITY_CRITICAL = 5
    PRIORITY_HIGH = 4
    PRIORITY_MEDIUM = 3
    PRIORITY_LOW = 2
    PRIORITY_OPTIONAL = 1
    
    constraint_id: str
    target_type: Optional[str] = None      # 적용대상유형 (예: '임무', '축선', '아군부대')
    target_id: Optional[str] = None        # 적용대상ID (해당 테이블의 ID)
    constraint_type: Optional[str] = None  # 제약유형 (예: '시간', 'ROE', '화력제한', '이동금지')
    content: Optional[str] = None          # 제약내용 (구체적인 제약 설명)
    
    # 중요도: 1~5 범위의 정수 (높을수록 중요) - "importance"가 더 직관적
    # 5 = 치명적 (CRITICAL): 민간인 보호, ROE 등 반드시 준수
    # 4 = 높음 (HIGH): 시간제한, 이동제한 등 가능한 준수
    # 3 = 중간 (MEDIUM): 화력제한, 통신유지 등 준수 권장
    # 2 = 낮음 (LOW): 정보제한 등 참고사항
    # 1 = 선택 (OPTIONAL): 가능하면 고려
    # 예: CST005 (ROE: 민간인 밀집지역 사격 제한) → importance=5 (치명적)
    #     CST006 (정보: 연막 지역 표적 식별 제한) → importance=2 (낮음)
    importance: Optional[int] = None
    
    start_time: Optional[datetime] = None  # 제약 시작 시간
    end_time: Optional[datetime] = None    # 제약 종료 시간
    
    # NEW: 시간 제약 관련 필드 추가 (METT-C의 C 요소)
    time_critical: Optional[bool] = None       # 시간 제약이 중요한지 여부
    max_duration_hours: Optional[float] = None # 최대 허용 시간 (시간 단위)
    remarks: Optional[str] = None              # 비고
    
    @property
    def priority(self) -> Optional[int]:
        """하위 호환성을 위한 property (Deprecated: Use 'importance' instead)"""
        return self.importance
    
    @priority.setter
    def priority(self, value: Optional[int]):
        """하위 호환성을 위한 setter (Deprecated: Use 'importance' instead)"""
        self.importance = value
    
    @classmethod
    def from_row(cls, row: Dict) -> 'Constraint':
        """DataFrame 행에서 Constraint 객체 생성"""
        # time_critical 파싱 (Y/N, True/False, 1/0 등)
        time_critical = row.get('시간중요여부', row.get('time_critical'))
        if time_critical is not None:
            if isinstance(time_critical, bool):
                time_critical_bool = time_critical
            elif isinstance(time_critical, str):
                time_critical_bool = time_critical.upper() in ['Y', 'YES', 'TRUE', '1', '예', 'O']
            elif isinstance(time_critical, (int, float)):
                time_critical_bool = bool(time_critical)
            else:
                time_critical_bool = None
        else:
            time_critical_bool = None
        
        # importance 파싱 (중요도/우선순위 양쪽 지원 - 하위 호환성)
        importance_value = (row.get('중요도') or row.get('우선순위') or 
                          row.get('importance') or row.get('priority'))
        
        # max_duration_hours 파싱
        max_duration = row.get('최대소요시간', row.get('max_duration_hours'))
        if max_duration is not None:
            try:
                max_duration_float = float(max_duration)
            except (ValueError, TypeError):
                max_duration_float = None
        else:
            max_duration_float = None
        
        return cls(
            constraint_id=str(row.get('제약ID', row.get('constraint_id', ''))),
            target_type=row.get('적용대상유형', row.get('적용대상', row.get('target_type'))),
            target_id=row.get('적용대상ID', row.get('target_id')),
            constraint_type=row.get('제약유형', row.get('constraint_type')),
            content=row.get('제약내용', row.get('내용', row.get('content'))),
            importance=importance_value,  # 중요도/우선순위 양쪽 지원
            start_time=row.get('시작시간', row.get('start_time')),
            end_time=row.get('종료시간', row.get('end_time')),
            time_critical=time_critical_bool,
            max_duration_hours=max_duration_float,
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class CivilianArea:
    """민간인 밀집 지역 모델 (METT-C의 C 요소)"""
    area_id: str
    area_name: Optional[str] = None
    location_cell_id: Optional[str] = None
    population_density: Optional[int] = None  # 인구 밀도 (명/km²)
    protection_priority: Optional[str] = None  # High, Medium, Low
    evacuation_routes: List[str] = field(default_factory=list)
    critical_facilities: List[str] = field(default_factory=list)  # 병원, 학교 등
    coordinates: Optional[str] = None
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'CivilianArea':
        """DataFrame 행에서 CivilianArea 객체 생성"""
        # evacuation_routes 파싱 (쉼표 구분)
        routes_str = row.get('대피경로', row.get('evacuation_routes', ''))
        routes = []
        if routes_str:
            try:
                import pandas as pd
                if not pd.isna(routes_str):
                    routes = [r.strip() for r in str(routes_str).split(',') if r.strip()]
            except:
                routes = []
        
        # critical_facilities 파싱
        facilities_str = row.get('중요시설', row.get('critical_facilities', ''))
        facilities = []
        if facilities_str:
            try:
                import pandas as pd
                if not pd.isna(facilities_str):
                    facilities = [f.strip() for f in str(facilities_str).split(',') if f.strip()]
            except:
                facilities = []
        
        return cls(
            area_id=str(row.get('민간인지역ID', row.get('area_id', ''))),
            area_name=row.get('지역명', row.get('area_name')),
            location_cell_id=row.get('위치지형셀ID', row.get('location_cell_id')),
            population_density=row.get('인구밀도', row.get('population_density')),
            protection_priority=row.get('보호우선순위', row.get('protection_priority')),
            evacuation_routes=routes,
            critical_facilities=facilities,
            coordinates=row.get('좌표정보', row.get('coordinates')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class ThreatEvent:
    """위협상황 모델"""
    threat_id: str
    occurrence_time: Optional[datetime] = None
    threat_type_code: Optional[str] = None
    related_axis_id: Optional[str] = None
    location_cell_id: Optional[str] = None
    related_enemy_unit_id: Optional[str] = None
    threat_level: Optional[str] = None
    related_mission_id: Optional[str] = None
    raw_report_text: Optional[str] = None
    confidence: Optional[int] = None
    status: Optional[int] = None # int(0: 대기, 1: 완료 등)로 변경 가능성 대비
    threat_type_original: Optional[str] = None # NEW: 원문의 구체적인 위협/행동
    enemy_unit_original: Optional[str] = None # NEW: 원문의 구체적인 적 부대명
    
    # [NEW] 위협유형 마스터 데이터 매핑 필드
    threat_name: Optional[str] = None      # 위협유형명 (from 마스터)
    description: Optional[str] = None      # 설명 (from 마스터)
    keywords: Optional[str] = None         # 대표키워드 (from 마스터)
    severity: Optional[str] = None         # 위협심도 (from 마스터)
    
    remarks: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'ThreatEvent':
        """DataFrame 행에서 ThreatEvent 객체 생성"""
        return cls(
            threat_id=str(row.get('위협ID', row.get('threat_id', ''))),
            occurrence_time=row.get('발생시각', row.get('occurrence_time')),
            threat_type_code=row.get('위협유형코드', row.get('threat_type_code')),
            related_axis_id=row.get('관련축선ID', row.get('related_axis_id')),
            location_cell_id=row.get('발생위치셀ID', row.get('location_cell_id')),
            related_enemy_unit_id=row.get('관련_적부대ID', row.get('related_enemy_unit_id')),
            threat_level=row.get('위협수준', row.get('threat_level')),
            related_mission_id=row.get('관련임무ID', row.get('related_mission_id')),
            raw_report_text=row.get('원시보고텍스트', row.get('raw_report_text')),
            confidence=row.get('확실도', row.get('confidence')),
            status=row.get('처리상태', row.get('status')),
            threat_type_original=row.get('위협유형_원문', row.get('threat_type_original')),
            enemy_unit_original=row.get('적부대_원문', row.get('enemy_unit_original')),
            remarks=row.get('비고', row.get('remarks'))
        )


@dataclass
class AxisState:
    """축선별 전장상태 요약 객체"""
    axis_id: str
    axis_name: Optional[str] = None
    
    # 아군 전투력 지표
    friendly_combat_power_total: int = 0
    friendly_unit_count: int = 0
    friendly_units: List[FriendlyUnit] = field(default_factory=list)
    
    # 적군 전투력 지표
    enemy_combat_power_total: int = 0
    enemy_unit_count: int = 0
    enemy_units: List[EnemyUnit] = field(default_factory=list)
    
    # 기동성/지형 요약
    terrain_cells: List[TerrainCell] = field(default_factory=list)
    avg_mobility_grade: Optional[float] = None
    avg_defense_advantage: Optional[float] = None
    key_point_count: int = 0
    
    # 제약조건 요약
    constraints: List[Constraint] = field(default_factory=list)
    constraint_summary: Optional[str] = None
    
    # 위협 정보
    threat_score_total: float = 0.0
    threat_level: str = "Low"  # High, Medium, Low
    threat_events: List[ThreatEvent] = field(default_factory=list)
    
    threat_events: List[ThreatEvent] = field(default_factory=list)
    
    # NEW: 자원 정보 (Resource)
    resources: List['Resource'] = field(default_factory=list)
    max_traversal_time_hours: Optional[float] = None # NEW: 기동 소요 시간
    
    # NEW: 민간인 지역 정보 (METT-C의 C 요소)
    # NEW: 민간인 지역 정보 (METT-C의 C 요소)
    civilian_areas: List[CivilianArea] = field(default_factory=list)
    
    # [NEW] 기상 정보 (METT-C의 W 요소) - Forward Reference 사용
    weather_conditions: List['Weather'] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'axis_id': self.axis_id,
            'axis_name': self.axis_name,
            'friendly_combat_power_total': self.friendly_combat_power_total,
            'friendly_unit_count': self.friendly_unit_count,
            'enemy_combat_power_total': self.enemy_combat_power_total,
            'enemy_unit_count': self.enemy_unit_count,
            'avg_mobility_grade': self.avg_mobility_grade,
            'avg_defense_advantage': self.avg_defense_advantage,
            'key_point_count': self.key_point_count,
            'constraint_count': len(self.constraints),
            'threat_score_total': self.threat_score_total,
            'threat_level': self.threat_level,
            'threat_event_count': len(self.threat_events),
            'civilian_area_count': len(self.civilian_areas),
            'weather_condition_count': len(self.weather_conditions)
        }


@dataclass
class MissionResourceAllocation:
    """임무별 자원 할당 모델 (교리적 보완 스키마)"""
    allocation_id: str
    mission_id: str
    asset_id: str
    tactical_role: Optional[str] = "미지정"
    allocated_quantity: int = 1
    plan_status: str = "사용가능"
    note: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'MissionResourceAllocation':
        """DataFrame 행에서 MissionResourceAllocation 객체 생성"""
        return cls(
            allocation_id=str(row.get('allocation_id', '')),
            mission_id=str(row.get('mission_id', '')),
            asset_id=str(row.get('asset_id', '')),
            tactical_role=row.get('tactical_role', '미지정'),
            allocated_quantity=int(row.get('allocated_quantity', 1)),
            plan_status=row.get('plan_status', '사용가능'),
            note=row.get('note')
        )


@dataclass
class Weather:
    """기상 데이터 모델 (METT-C의 Weather)"""
    weather_id: str
    location_cell_id: str
    weather_type: str
    time: Optional[datetime] = None
    note: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: Dict) -> 'Weather':
        """DataFrame 행에서 Weather 객체 생성"""
        return cls(
            weather_id=str(row.get('기상ID', row.get('weather_id', ''))),
            location_cell_id=row.get('지형셀ID', row.get('location_cell_id')),
            weather_type=row.get('기상유형', row.get('weather_type')),
            time=row.get('시각', row.get('time')),
            note=row.get('비고', row.get('note'))
        )


