# core_pipeline/mett_c_evaluator.py
# -*- coding: utf-8 -*-
"""
METT-C Evaluator
METT-C 프레임워크 기반 종합 평가 모듈
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from core_pipeline.data_models import (
    Mission, EnemyUnit, TerrainCell, FriendlyUnit, 
    CivilianArea, Constraint, ThreatEvent
)
from core_pipeline.data_models import AxisState


@dataclass
class METTCScore:
    """METT-C 종합 점수"""
    mission_score: float  # 0-1
    enemy_score: float  # 0-1
    terrain_score: float  # 0-1
    troops_score: float  # 0-1
    civilian_score: float  # 0-1 (민간인 보호)
    weather_score: float   # 0-1 (기상 영향)
    time_score: float  # 0-1 (시간 제약 준수)
    
    total_score: float  # 가중 평균
    breakdown: Dict[str, float]  # 상세 분석
    
    def to_dict(self) -> Dict:
        return {
            'mission': self.mission_score,
            'enemy': self.enemy_score,
            'terrain': self.terrain_score,
            'troops': self.troops_score,
            'civilian': self.civilian_score,
            'weather': self.weather_score,
            'time': self.time_score,
            'total': self.total_score,
            'breakdown': self.breakdown
        }


class METTCEvaluator:
    """METT-C 종합 평가기"""
    
    # METT-C 요소별 가중치 (기본값)
    DEFAULT_WEIGHTS = {
        'mission': 0.15,
        'enemy': 0.15,
        'terrain': 0.15,
        'troops': 0.15,
        'civilian': 0.15,  # NEW
        'weather': 0.10,   # NEW
        'time': 0.15  # NEW
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: METT-C 요소별 가중치 (None이면 기본값 사용)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        # 가중치 정규화
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    def evaluate_coa(
        self,
        coa_context: Dict,
        mission: Optional[Mission] = None,
        enemy_units: Optional[List[EnemyUnit]] = None,
        terrain_cells: Optional[List[TerrainCell]] = None,
        friendly_units: Optional[List[FriendlyUnit]] = None,
        civilian_areas: Optional[List[CivilianArea]] = None,
        constraints: Optional[List[Constraint]] = None,
        axis_states: Optional[List[AxisState]] = None
    ) -> METTCScore:
        """
        COA에 대한 METT-C 종합 평가
        
        Args:
            coa_context: COA 컨텍스트 정보
            mission: 임무 정보
            enemy_units: 적군 부대 리스트
            terrain_cells: 지형셀 리스트
            friendly_units: 아군 부대 리스트
            civilian_areas: 민간인 지역 리스트 (NEW)
            constraints: 제약조건 리스트
            axis_states: 축선별 전장상태 리스트
        
        Returns:
            METTCScore 객체
        """
        # 각 요소별 점수 계산
        mission_score = self._evaluate_mission(coa_context, mission)
        enemy_score = self._evaluate_enemy(coa_context, enemy_units, axis_states)
        terrain_score = self._evaluate_terrain(coa_context, terrain_cells, axis_states)
        troops_score = self._evaluate_troops(coa_context, friendly_units, axis_states)
        civilian_score = self._evaluate_civilian(coa_context, civilian_areas, axis_states)  # NEW
        weather_score = self._evaluate_weather(coa_context, axis_states) # NEW
        time_score = self._evaluate_time(coa_context, mission, constraints)  # NEW
        
        # 가중 평균 계산
        total_score = (
            mission_score * self.weights['mission'] +
            enemy_score * self.weights['enemy'] +
            terrain_score * self.weights['terrain'] +
            troops_score * self.weights['troops'] +
            civilian_score * self.weights['civilian'] +
            weather_score * self.weights['weather'] +
            time_score * self.weights['time']
        )
        
        # 상세 분석
        breakdown = {
            'mission': {
                'score': mission_score,
                'weight': self.weights['mission'],
                'contribution': mission_score * self.weights['mission']
            },
            'enemy': {
                'score': enemy_score,
                'weight': self.weights['enemy'],
                'contribution': enemy_score * self.weights['enemy']
            },
            'terrain': {
                'score': terrain_score,
                'weight': self.weights['terrain'],
                'contribution': terrain_score * self.weights['terrain']
            },
            'troops': {
                'score': troops_score,
                'weight': self.weights['troops'],
                'contribution': troops_score * self.weights['troops']
            },
            'civilian': {
                'score': civilian_score,
                'weight': self.weights['civilian'],
                'contribution': civilian_score * self.weights['civilian']
            },
            'weather': {
                'score': weather_score,
                'weight': self.weights['weather'],
                'contribution': weather_score * self.weights['weather']
            },
            'time': {
                'score': time_score,
                'weight': self.weights['time'],
                'contribution': time_score * self.weights['time']
            }
        }
        
        return METTCScore(
            mission_score=mission_score,
            enemy_score=enemy_score,
            terrain_score=terrain_score,
            troops_score=troops_score,
            civilian_score=civilian_score,
            weather_score=weather_score,
            time_score=time_score,
            total_score=total_score,
            breakdown=breakdown
        )
    
    def _evaluate_mission(self, coa_context: Dict, mission: Optional[Mission]) -> float:
        """임무 부합성 평가"""
        if not mission:
            return 0.5  # 기본값
        
        # 기존 COAScorer의 mission_alignment_score 활용
        mission_type = mission.mission_type
        coa_type = coa_context.get('coa_type', '')
        
        # 임무-방책 부합성 매트릭스 사용 (COAScorer와 동일)
        from core_pipeline.coa_scorer import COAScorer
        alignment_matrix = COAScorer.MISSION_COA_ALIGNMENT.get(mission_type, {})
        alignment_score = alignment_matrix.get(coa_type.lower(), 0.5)
        
        # 임무 우선순위 반영
        priority = mission.priority or 5  # 기본값 5
        priority_factor = min(1.0, priority / 10.0)  # 1-10 범위를 0-1로 정규화
        
        return alignment_score * (0.7 + 0.3 * priority_factor)
    
    def _evaluate_enemy(self, coa_context: Dict, enemy_units: Optional[List[EnemyUnit]], 
                       axis_states: Optional[List[AxisState]]) -> float:
        """적군 대응 평가"""
        # 기존 threat_score 활용
        threat_score = coa_context.get('threat_score', 0.5)
        
        # 적군 전투력 대비 아군 전투력 비율
        if axis_states:
            total_enemy_power = sum(state.enemy_combat_power_total for state in axis_states)
            total_friendly_power = sum(state.friendly_combat_power_total for state in axis_states)
            
            if total_enemy_power > 0:
                power_ratio = total_friendly_power / total_enemy_power
                # 1:1 비율이면 1.0, 2:1이면 1.0, 1:2이면 0.5
                power_factor = min(1.0, power_ratio)
            else:
                power_factor = 1.0
        else:
            power_factor = 0.5
        
        return threat_score * (0.6 + 0.4 * power_factor)
    
    def _evaluate_terrain(self, coa_context: Dict, terrain_cells: Optional[List[TerrainCell]],
                         axis_states: Optional[List[AxisState]]) -> float:
        """
        지형 적합성 평가 (고도화)
        작전 유형에 따라 지형 요소(기동성, 방어이점, 관측이점, 요충지)의 가중치를 달리하여 평가
        """
        # AxisState 정보가 없으면 기본값 또는 기존 컨텍스트 값 반환
        if not axis_states:
            return coa_context.get('environment_fit', 0.5)

        coa_type = coa_context.get('coa_type', '').lower()
        score_sum = 0.0
        axis_count = 0

        for axis in axis_states:
            # 해당 축선에 지형 정보가 없으면 건너뜀
            if not axis.terrain_cells:
                continue
            
            cells = axis.terrain_cells
            cell_count = len(cells)
            if cell_count == 0:
                continue

            # 지형 요소 데이터 추출 (None 값 제외)
            mobilities = [c.mobility_grade for c in cells if c.mobility_grade is not None]
            defenses = [c.defense_advantage for c in cells if c.defense_advantage is not None]
            observations = [c.observation_advantage for c in cells if c.observation_advantage is not None]
            
            # 평균값 계산 (데이터 없으면 중간값 가정)
            avg_mob = sum(mobilities) / len(mobilities) if mobilities else 3.0
            avg_def = sum(defenses) / len(defenses) if defenses else 2.5 # 5점 만점 기준 중간
            avg_obs = sum(observations) / len(observations) if observations else 2.5
            
            # 정규화 (0.0 ~ 1.0) - 5점 만점 기준 가정
            norm_mob = min(1.0, avg_mob / 5.0)
            norm_def = min(1.0, avg_def / 5.0)
            norm_obs = min(1.0, avg_obs / 5.0)
            
            # 요충지(Key Point) 확보율 분석
            # is_key_point가 'Y', 'Yes', 'O' 인 경우
            key_point_count = sum(1 for c in cells if c.is_key_point and str(c.is_key_point).upper() in ['Y', 'YES', 'O', '예'])
            # 축선 내 요충지가 1개 이상이면 의미 있음 (최대 3개 기준 정규화)
            norm_key = min(1.0, key_point_count / 2.0) 

            # 작전 유형별 가중치 적용 점수 계산
            axis_score = 0.5
            
            if 'offensive' in coa_type or 'attack' in coa_type or '공격' in coa_type:
                # 공격 작전: 빠른 기동(Mobility)이 최우선, 요충지 확보도 중요
                # 방어유리도가 너무 높으면 오히려 험준하여 공격에 불리할 수 있음 -> 기동성에 집중
                axis_score = (norm_mob * 0.6) + (norm_key * 0.3) + (norm_obs * 0.1)
                
            elif 'defense' in coa_type or 'defend' in coa_type or '방어' in coa_type:
                # 방어 작전: 방어유리도(Cover)와 관측(Observation)이 생명
                axis_score = (norm_def * 0.4) + (norm_obs * 0.3) + (norm_key * 0.2) + (norm_mob * 0.1)
                
            elif 'recon' in coa_type or 'surveillance' in coa_type or '정찰' in coa_type or '감시' in coa_type:
                # 정찰/감시: 관측이 가장 중요, 그 다음은 기동(도주/침투)
                axis_score = (norm_obs * 0.6) + (norm_mob * 0.3) + (norm_def * 0.1)
                
            else:
                # 일반/기타: 균형 잡힌 가중치
                axis_score = (norm_mob * 0.4) + (norm_def * 0.3) + (norm_key * 0.2) + (norm_obs * 0.1)
            
            score_sum += axis_score
            axis_count += 1
            
        if axis_count == 0:
            return coa_context.get('environment_fit', 0.5)
            
        return score_sum / axis_count
    
    def _evaluate_troops(self, coa_context: Dict, friendly_units: Optional[List[FriendlyUnit]],
                        axis_states: Optional[List[AxisState]]) -> float:
        """부대 능력 평가"""
        # 기존 resources, assets 점수 활용
        resource_score = coa_context.get('resource_availability', 0.5)
        asset_score = coa_context.get('asset_capability', 0.5)
        
        return (resource_score + asset_score) / 2.0
    
    def _evaluate_civilian(self, coa_context: Dict, civilian_areas: Optional[List[CivilianArea]],
                          axis_states: Optional[List[AxisState]]) -> float:
        """
        민간인 보호 평가 (NEW)
        
        평가 기준:
        1. COA가 민간인 지역에 영향을 주는지 여부
        2. 민간인 보호 우선순위 반영
        3. 대피 경로 확보 여부
        """
        if not civilian_areas:
            return 1.0  # 민간인 지역이 없으면 최고 점수
        
        # COA의 영향 범위 추정 (coa_context에서)
        coa_impact_cells = coa_context.get('impact_terrain_cells', [])
        
        # 영향받는 민간인 지역 찾기
        affected_areas = []
        for area in civilian_areas:
            if area.location_cell_id in coa_impact_cells:
                affected_areas.append(area)
        
        if not affected_areas:
            return 1.0  # 영향 없으면 최고 점수
        
        # 보호 우선순위 기반 점수 계산
        total_penalty = 0.0
        for area in affected_areas:
            priority = area.protection_priority or 'Medium'
            if priority == 'High':
                penalty = 0.4
            elif priority == 'Medium':
                penalty = 0.2
            else:
                penalty = 0.1
            
            # 인구 밀도 반영
            density = area.population_density or 0
            if density > 1000:  # 고밀도 지역
                penalty *= 1.5
            elif density > 500:
                penalty *= 1.2
            
            # 중요 시설 반영
            if area.critical_facilities:
                penalty *= 1.3
            
            total_penalty += penalty
        
        # 최대 패널티 제한 (여러 지역 영향 시)
        max_penalty = min(0.8, total_penalty)
        
        return max(0.0, 1.0 - max_penalty)
    
    def _evaluate_weather(self, coa_context: Dict, axis_states: Optional[List[AxisState]]) -> float:
        """
        기상 영향 평가 (NEW)
        작전 유형에 따른 동적 가중치 적용
        
        평가 로직:
        1. 작전 유형별로 강수(Rain/Snow)와 시정(Fog)에 대한 민감도(Sensitivity)를 다르게 적용
           - 공격: 기동성이 생명이므로 강수(진흙탕, 미끄러움)에 민감 (민감도 > 1.0)
           - 방어: 적을 먼저 보고 사격해야 하므로 시정(안개)에 민감 (민감도 > 1.0)
           - 기습/매복: 악천후를 은폐 수단으로 활용 가능하므로 페널티 완화 (민감도 < 1.0)
        2. 축선별 최악의 기상 조건을 기준으로 평가
        """
        if not axis_states:
            return 1.0  # 정보 없으면 영향 없음
        
        coa_type = coa_context.get('coa_type', '').lower()
        
        # 1. 작전 유형별 민감도 정의
        # 튜플: (강수 민감도, 시정 민감도) - 1.0이 기준, 클수록 페널티 강화
        sensitivities = {
            'offensive': (1.3, 0.9),   # 공격: 기동성(강수)에 매우 민감
            'attack': (1.3, 0.9),
            '공격': (1.3, 0.9),
            'defense': (0.9, 1.4),     # 방어: 시정(안개)에 매우 민감 (관측 제한)
            'defend': (0.9, 1.4),
            '방어': (0.9, 1.4),
            'ambush': (0.7, 0.6),      # 기습/매복: 악천후가 아군 은폐에 유리 (페널티 완화)
            'surprise': (0.7, 0.6),
            '기습': (0.7, 0.6),
            'recon': (1.5, 1.5),       # 감시/정찰: 모든 악천후에 매우 취약
            'surveillance': (1.5, 1.5),
            '감시': (1.5, 1.5),
            'aviation': (2.0, 2.0),    # 항공: 악천후 시 작전 불가 수준
            'air': (2.0, 2.0)
        }
        
        # 기본값 (일반 작전)
        rain_sens, vis_sens = 1.0, 1.0
        
        # 매칭되는 작전 유형 찾기
        for key, (r, v) in sensitivities.items():
            if key in coa_type:
                rain_sens, vis_sens = r, v
                break
        
        # 2. 최악의 날씨 조건 탐색
        min_score = 1.0
        
        for axis in axis_states:
            if not axis.weather_conditions:
                continue
                
            for weather in axis.weather_conditions:
                w_type = str(weather.weather_type).strip() if weather.weather_type else ""
                penalty = 0.0
                current_sens = 1.0
                
                # 기본 감점 폭 설정 & 해당 유형의 민감도 선택
                if '호우' in w_type or '폭설' in w_type or '태풍' in w_type:
                    penalty = 0.4  # 심각한 악천후
                    current_sens = max(rain_sens, vis_sens) * 1.1 # 심각한 경우 민감도 가중
                elif '비' in w_type:
                    penalty = 0.15
                    current_sens = rain_sens
                elif '눈' in w_type:
                    penalty = 0.25 # 눈이 비보다 기동에 더 치명적
                    current_sens = rain_sens
                elif '안개' in w_type:
                    penalty = 0.2
                    current_sens = vis_sens
                elif '흐림' in w_type:
                    penalty = 0.05
                    current_sens = 1.0 # 흐림은 작전 유형 무관하게 경미
                    
                # 최종 점수 계산
                # 감점 = 기본감점 * 민감도
                adjusted_penalty = penalty * current_sens
                score = max(0.0, 1.0 - adjusted_penalty)
                
                if score < min_score:
                    min_score = score
                    
        return min_score

    def _evaluate_time(self, coa_context: Dict, mission: Optional[Mission],
                      constraints: Optional[List[Constraint]]) -> float:
        """
        시간 제약 평가 (NEW)
        
        평가 기준:
        1. 임무 시간 제한 준수
        2. COA 예상 소요 시간
        3. 시간 제약조건 준수
        """
        # COA 예상 소요 시간
        coa_duration_hours = coa_context.get('estimated_duration_hours', None)
        
        # 임무 시간 제한
        mission_time_limit = None
        if mission and mission.time_limit:
            # 현재 시간 기준으로 남은 시간 계산
            now = datetime.now()
            if isinstance(mission.time_limit, datetime):
                remaining = (mission.time_limit - now).total_seconds() / 3600.0
                mission_time_limit = max(0, remaining)
        
        # 시간 제약조건 확인
        time_constraints = []
        if constraints:
            for constraint in constraints:
                if constraint.constraint_type and '시간' in constraint.constraint_type:
                    time_constraints.append(constraint)
                elif constraint.time_critical:
                    time_constraints.append(constraint)
        
        # 점수 계산
        if coa_duration_hours is None:
            return 0.5  # 시간 정보 없으면 중립
        
        # 임무 시간 제한 준수
        if mission_time_limit is not None:
            if coa_duration_hours > mission_time_limit:
                return 0.0  # 시간 제한 초과 시 0점
            else:
                # 여유 시간 비율에 따라 점수 조정
                time_ratio = coa_duration_hours / mission_time_limit if mission_time_limit > 0 else 1.0
                time_score = 1.0 - (time_ratio * 0.3)  # 여유가 많을수록 높은 점수
        else:
            time_score = 0.7  # 시간 제한 없으면 기본 점수
        
        # 시간 제약조건 반영 (중요도 기반 차등 감점 적용)
        if time_constraints:
            for constraint in time_constraints:
                if constraint.max_duration_hours:
                    if coa_duration_hours > constraint.max_duration_hours:
                        # 중요도에 따른 차등 감점
                        importance = constraint.importance or 3  # 기본값: 중간
                        
                        if importance == 5:  # CRITICAL
                            penalty = 1.0  # 100% 감점 (자동 탈락)
                        elif importance == 4:  # HIGH
                            penalty = 0.7  # 70% 감점
                        elif importance == 3:  # MEDIUM
                            penalty = 0.5  # 50% 감점
                        elif importance == 2:  # LOW
                            penalty = 0.3  # 30% 감점
                        else:  # importance == 1 (OPTIONAL)
                            penalty = 0.1  # 10% 감점
                        
                        time_score *= (1.0 - penalty)
        
        return min(1.0, max(0.0, time_score))



