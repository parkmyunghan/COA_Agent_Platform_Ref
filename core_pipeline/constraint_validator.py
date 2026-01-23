# core_pipeline/constraint_validator.py
# -*- coding: utf-8 -*-
"""
Constraint Validator
제약조건 검증 및 우선순위 기반 평가 모듈
"""
from typing import Dict, Optional
from core_pipeline.data_models import Constraint
from common.logger import get_logger

logger = get_logger("ConstraintValidator")


class ConstraintValidator:
    """
    제약조건 검증 엔진
    
    제약유형별 검증 로직을 제공하고, 우선순위에 따라 차등 페널티를 적용합니다.
    """
    
    # 제약유형별 검증 메서드 매핑
    VALIDATOR_MAP = {
        '시간': '_validate_time_constraint',
        '이동금지': '_validate_movement_constraint',
        '화력제한': '_validate_firepower_constraint',
        'ROE': '_validate_roe_constraint',
        '정보': '_validate_intelligence_constraint',
        '통신': '_validate_communication_constraint',
        '장애물': '_validate_obstacle_constraint',
        '기후': '_validate_weather_constraint'
    }
    
    def validate_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """
        제약조건 검증 및 준수도 점수 계산
        
        Args:
            constraint: 검증할 제약조건
            coa: COA 객체 또는 딕셔너리
            context: 평가 컨텍스트 (추가 정보)
        
        Returns:
            0.0~1.0 준수도 점수
            - 1.0: 완전 준수
            - 0.0: 완전 위반
            - 0.5: 부분 준수 또는 판단 불가
        """
        if not constraint.constraint_type:
            logger.warning(f"제약조건 {constraint.constraint_id}에 제약유형이 없습니다.")
            return 0.5  # 유형 불명 시 중립
        
        # 검증 메서드 찾기
        validator_name = self.VALIDATOR_MAP.get(constraint.constraint_type)
        
        if not validator_name:
            logger.warning(f"알 수 없는 제약유형: {constraint.constraint_type}")
            return 0.5  # 알 수 없는 유형은 중립
        
        # 검증 메서드 실행
        try:
            validator = getattr(self, validator_name)
            compliance_score = validator(constraint, coa, context)
            
            logger.debug(
                f"제약조건 검증: {constraint.constraint_id} "
                f"({constraint.constraint_type}) -> {compliance_score:.2f}"
            )
            
            return compliance_score
        
        except Exception as e:
            logger.error(f"제약조건 검증 실패: {constraint.constraint_id} - {e}")
            return 0.5  # 오류 시 중립
    
    def get_penalty_by_importance(self, importance: Optional[int]) -> float:
        """
        중요도에 따른 페널티 비율 계산
        
        Args:
            importance: 제약조건 중요도 (1~5, 높을수록 중요)
        
        Returns:
            위반 시 적용할 페널티 비율 (0.0~1.0)
            - 중요도 5 (치명적): 1.0 (100% 감점)
            - 중요도 4 (높음): 0.7 (70% 감점)
            - 중요도 3 (중간): 0.5 (50% 감점)
            - 중요도 2 (낮음): 0.3 (30% 감점)
            - 중요도 1 (선택): 0.1 (10% 감점)
        """
        if importance is None:
            return 0.5  # 중요도 없으면 중간값
        
        # 중요도별 페널티 매핑
        penalty_map = {
            5: 1.0,   # CRITICAL: 완전 탈락
            4: 0.7,   # HIGH: 큰 감점
            3: 0.5,   # MEDIUM: 중간 감점
            2: 0.3,   # LOW: 작은 감점
            1: 0.1    # OPTIONAL: 경미한 감점
        }
        
        return penalty_map.get(importance, 0.5)
    
    # ========== 제약유형별 검증 메서드 ==========
    
    def _validate_time_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """
        시간 제약 검증
        
        검증 항목:
        1. COA 예상 소요 시간이 제약 시간 내인가?
        2. 시작/종료 시간 제약 준수 여부
        """
        # COA 예상 소요 시간
        coa_duration = context.get('estimated_duration_hours')
        
        if coa_duration is None:
            return 0.5  # 시간 정보 없으면 판단 불가
        
        # max_duration_hours 제약 확인
        if constraint.max_duration_hours:
            if coa_duration <= constraint.max_duration_hours:
                return 1.0  # 준수
            else:
                # 초과 비율에 따라 점수 감소
                overage_ratio = (coa_duration - constraint.max_duration_hours) / constraint.max_duration_hours
                penalty = min(1.0, overage_ratio)
                return max(0.0, 1.0 - penalty)
        
        # start_time, end_time 제약 확인
        if constraint.start_time or constraint.end_time:
            coa_start_time = context.get('start_time')
            coa_end_time = context.get('end_time')
            
            if coa_start_time and constraint.start_time:
                if coa_start_time < constraint.start_time:
                    return 0.0  # 시작 시간 제약 위반
            
            if coa_end_time and constraint.end_time:
                if coa_end_time > constraint.end_time:
                    return 0.0  # 종료 시간 제약 위반
            
            return 1.0  # 시간 제약 준수
        
        # 제약 내용 텍스트 기반 판단 (폴백)
        if constraint.content:
            # "H+2까지", "H+4 이전" 등 파싱 시도
            # TODO: 더 정교한 시간 표현 파싱 구현
            return 0.7  # 보수적으로 부분 준수로 판단
        
        return 0.5  # 판단 불가
    
    def _validate_movement_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """
        이동금지 제약 검증
        
        검증 항목:
        1. COA의 부대 이동 경로가 금지 구역을 포함하는가?
        2. 특정 축선 이탈 여부
        """
        # COA의 사용 축선
        coa_axes = context.get('coa_axes', set())
        
        # 제약 내용에서 금지 축선 추출 시도
        if constraint.content and '축선' in constraint.content:
            # "특정 축선 벗어나면 안됨" -> 적용대상ID가 허용 축선
            allowed_axis = constraint.target_id if constraint.target_type == '축선' else None
            
            if allowed_axis:
                # COA가 허용 축선만 사용하는지 확인
                if allowed_axis in coa_axes and len(coa_axes) == 1:
                    return 1.0  # 준수 (허용 축선만 사용)
                elif allowed_axis not in coa_axes:
                    return 0.0  # 위반 (허용 축선 미사용)
                else:
                    return 0.5  # 부분 준수 (허용 축선 + 다른 축선)
        
        # 금지 구역 확인
        forbidden_areas = context.get('forbidden_areas', set())
        coa_areas = context.get('coa_impact_areas', set())
        
        if forbidden_areas and coa_areas:
            violation_count = len(forbidden_areas & coa_areas)
            if violation_count == 0:
                return 1.0  # 준수
            else:
                # 위반 비율에 따라 점수 감소
                violation_ratio = violation_count / len(forbidden_areas)
                return max(0.0, 1.0 - violation_ratio)
        
        return 0.7  # 기본적으로 부분 준수로 간주
    
    def _validate_firepower_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """
        화력제한 제약 검증
        
        검증 항목:
        1. COA의 포병/화력 사용량이 제한 내인가?
        """
        # 제약 내용 파싱: "포병 화력 절반만 사용"
        if constraint.content and ('절반' in constraint.content or '50%' in constraint.content):
            max_firepower_ratio = 0.5
        elif constraint.content and ('30%' in constraint.content):
            max_firepower_ratio = 0.3
        else:
            max_firepower_ratio = 1.0  # 파싱 실패 시 제한 없음
        
        # COA의 실제 화력 사용량
        allocated_firepower = context.get('allocated_artillery_power', 0)
        total_firepower = context.get('total_artillery_power', 1)
        
        if total_firepower > 0:
            actual_ratio = allocated_firepower / total_firepower
            
            if actual_ratio <= max_firepower_ratio:
                return 1.0  # 준수
            else:
                # 초과 비율에 따라 감점
                overage = (actual_ratio - max_firepower_ratio) / max_firepower_ratio
                return max(0.0, 1.0 - overage)
        
        return 0.7  # 정보 부족 시 부분 준수
    
    def _validate_roe_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """
        ROE (교전규칙) 제약 검증
        
        검증 항목:
        1. 민간인 지역 보호
        2. 사격 조건 준수
        """
        # 민간인 보호 관련 ROE
        if constraint.content and '민간인' in constraint.content:
            # COA가 민간인 지역에 영향을 주는지 확인
            civilian_areas_affected = context.get('civilian_areas_affected', [])
            
            if not civilian_areas_affected:
                return 1.0  # 민간인 지역 영향 없음 (준수)
            else:
                # 영향받는 민간인 지역 수에 따라 감점
                affected_count = len(civilian_areas_affected)
                penalty = min(1.0, affected_count * 0.3)
                return max(0.0, 1.0 - penalty)
        
        # 사격 조건 ROE
        if constraint.content and '사격' in constraint.content:
            # "지형확보 전 사격금지"
            if '지형확보' in constraint.content:
                terrain_secured = context.get('terrain_secured', False)
                if terrain_secured:
                    return 1.0  # 지형 확보 후 사격 (준수)
                else:
                    # COA가 사격을 포함하는지 확인
                    includes_fire_support = context.get('includes_fire_support', False)
                    if includes_fire_support:
                        return 0.0  # 지형 미확보 상태에서 사격 (위반)
                    else:
                        return 1.0  # 사격 없음 (준수)
        
        return 0.7  # 기본적으로 부분 준수
    
    def _validate_intelligence_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """정보 제약 검증 (연막, 정찰 제한 등)"""
        # 정보 제약은 일반적으로 심각하지 않으므로 관대하게 평가
        return 0.8  # 기본 점수
    
    def _validate_communication_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """통신 제약 검증 (통신중계 유지 등)"""
        # 통신 유지 확인
        if constraint.content and '통신' in constraint.content:
            maintains_comms = context.get('maintains_communication', True)
            return 1.0 if maintains_comms else 0.5
        
        return 0.8  # 기본 점수
    
    def _validate_obstacle_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """장애물 제약 검증 (지뢰지대 우회 등)"""
        # 장애물 우회 확인
        if constraint.content and ('우회' in constraint.content or '회피' in constraint.content):
            avoids_obstacles = context.get('avoids_obstacles', True)
            return 1.0 if avoids_obstacles else 0.3
        
        return 0.8  # 기본 점수
    
    def _validate_weather_constraint(self, constraint: Constraint, coa: Dict, context: Dict) -> float:
        """기후 제약 검증 (악천후 제한 등)"""
        # 기상 조건 확인
        if constraint.content and '악천후' in constraint.content:
            weather_condition = context.get('weather_condition', 'clear')
            
            if weather_condition == 'bad':
                # 악천후 시 항공 지원 사용 확인
                uses_air_support = context.get('uses_air_support', False)
                if uses_air_support:
                    return 0.0  # 악천후에 항공 지원 사용 (위반)
                else:
                    return 1.0  # 항공 지원 미사용 (준수)
            else:
                return 1.0  # 날씨 좋음 (제약 해당 없음)
        
        return 0.8  # 기본 점수
