# core_pipeline/coa_engine/coa_evaluator.py
# -*- coding: utf-8 -*-
"""
COA Evaluator
COA 평가 및 비교 모듈
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from core_pipeline.data_models import AxisState
from core_pipeline.coa_engine.coa_models import COA


@dataclass
class COAEvaluationResult:
    """COA 평가 결과"""
    coa_id: str
    coa_name: Optional[str] = None
    
    # 세부 점수 (0-1 범위)
    combat_power_score: float = 0.0  # 전투력 우세도
    mobility_score: float = 0.0  # 기동 가능성
    constraint_compliance_score: float = 0.0  # 제약조건 준수도
    threat_response_score: float = 0.0  # 위협 대응도 (축선 위협지수 반영)
    risk_score: float = 0.0  # 예상 손실/위험도 (낮을수록 좋음, 1-risk_score로 변환)
    
    # 종합 점수
    total_score: float = 0.0
    
    # 가중치
    weights: Dict[str, float] = field(default_factory=dict)
    
    # 요약 메시지
    summary: str = ""
    details: Dict[str, str] = field(default_factory=dict)
    
    # 참고 자료 (Optional)
    doctrine_references: List[Dict] = field(default_factory=list)
    similar_cases: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'coa_id': self.coa_id,
            'coa_name': self.coa_name,
            'scores': {
                'combat_power': round(self.combat_power_score, 4),
                'mobility': round(self.mobility_score, 4),
                'constraint_compliance': round(self.constraint_compliance_score, 4),
                'threat_response': round(self.threat_response_score, 4),
                'risk': round(self.risk_score, 4),
            },
            'total_score': round(self.total_score, 4),
            'weights': self.weights,
            'summary': self.summary,
            'details': self.details,
            'doctrine_references': self.doctrine_references,
            'similar_cases': self.similar_cases
        }


class COAEvaluator:
    """COA 평가기"""
    
    # 기본 가중치
    DEFAULT_WEIGHTS = {
        'combat_power': 0.25,
        'mobility': 0.15,
        'constraint_compliance': 0.20,
        'threat_response': 0.30,  # 위협 대응이 가장 중요
        'risk': 0.10
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: 평가 기준별 가중치 (None이면 기본값 사용)
        """
        if weights:
            # 가중치 정규화
            total = sum(weights.values())
            if total > 0:
                self.weights = {k: v / total for k, v in weights.items()}
            else:
                self.weights = self.DEFAULT_WEIGHTS.copy()
        else:
            self.weights = self.DEFAULT_WEIGHTS.copy()
    
    def evaluate_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        coa_list: List[COA]
    ) -> List[COAEvaluationResult]:
        """
        COA 리스트 평가
        
        Args:
            mission_id: 임무ID
            axis_states: 축선별 전장상태 요약 리스트
            coa_list: 평가할 COA 리스트
            
        Returns:
            평가 결과 리스트 (점수 순으로 정렬)
        """
        results = []
        
        for coa in coa_list:
            result = self.evaluate_single_coa(mission_id, axis_states, coa)
            results.append(result)
        
        # 종합 점수 순으로 정렬 (높은 점수 우선)
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # 순위 추가
        for i, result in enumerate(results, 1):
            result.details['rank'] = str(i)
        
        return results
    
    def evaluate_single_coa(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        coa: COA
    ) -> COAEvaluationResult:
        """
        단일 COA 평가
        
        Args:
            mission_id: 임무ID
            axis_states: 축선별 전장상태 요약 리스트
            coa: 평가할 COA
            
        Returns:
            평가 결과
        """
        result = COAEvaluationResult(
            coa_id=coa.coa_id,
            coa_name=coa.coa_name,
            weights=self.weights.copy()
        )
        
        # 축선별 상태를 딕셔너리로 변환 (빠른 조회)
        axis_state_map = {axis.axis_id: axis for axis in axis_states}
        
        # 1. 전투력 우세도 점수 계산
        result.combat_power_score = self._calculate_combat_power_score(coa, axis_state_map)
        
        # 2. 기동 가능성 점수 계산
        result.mobility_score = self._calculate_mobility_score(coa, axis_state_map)
        
        # 3. 제약조건 준수도 점수 계산
        result.constraint_compliance_score = self._calculate_constraint_compliance_score(coa, axis_state_map)
        
        # 4. 위협 대응도 점수 계산 (축선 위협지수 반영)
        result.threat_response_score = self._calculate_threat_response_score(coa, axis_state_map)
        
        # 5. 예상 손실/위험도 점수 계산
        result.risk_score = self._calculate_risk_score(coa, axis_state_map)
        
        # 종합 점수 계산 (가중치 적용)
        result.total_score = (
            result.combat_power_score * self.weights.get('combat_power', 0.25) +
            result.mobility_score * self.weights.get('mobility', 0.15) +
            result.constraint_compliance_score * self.weights.get('constraint_compliance', 0.20) +
            result.threat_response_score * self.weights.get('threat_response', 0.30) +
            (1.0 - result.risk_score) * self.weights.get('risk', 0.10)  # 위험도는 낮을수록 좋음
        )
        
        # 요약 메시지 생성
        result.summary = self._generate_summary(result)
        result.details = self._generate_details(result, coa, axis_state_map)
        
        return result
    
    def _calculate_combat_power_score(
        self,
        coa: COA,
        axis_state_map: Dict[str, AxisState]
    ) -> float:
        """전투력 우세도 점수 계산"""
        total_friendly_power = 0
        total_enemy_power = 0
        
        # COA에 배치된 축선들의 전투력 합계
        for axis_id in coa.axis_assignments.keys():
            if axis_id in axis_state_map:
                axis_state = axis_state_map[axis_id]
                total_friendly_power += axis_state.friendly_combat_power_total
                total_enemy_power += axis_state.enemy_combat_power_total
        
        # 전투력 비율 계산 (아군/적군)
        if total_enemy_power > 0:
            power_ratio = total_friendly_power / total_enemy_power
            # 비율이 1.0 이상이면 우세, 0.5 미만이면 열세
            # 0-1 범위로 정규화: 0.5 → 0.0, 1.0 → 0.5, 2.0 → 1.0
            if power_ratio >= 2.0:
                score = 1.0
            elif power_ratio >= 1.0:
                score = 0.5 + (power_ratio - 1.0) * 0.5  # 1.0~2.0 → 0.5~1.0
            elif power_ratio >= 0.5:
                score = (power_ratio - 0.5) * 1.0  # 0.5~1.0 → 0.0~0.5
            else:
                score = 0.0
        else:
            # 적군이 없으면 최고 점수
            score = 1.0
        
        return min(1.0, max(0.0, score))
    
    def _calculate_mobility_score(
        self,
        coa: COA,
        axis_state_map: Dict[str, AxisState]
    ) -> float:
        """기동 가능성 점수 계산"""
        mobility_scores = []
        
        for axis_id in coa.axis_assignments.keys():
            if axis_id in axis_state_map:
                axis_state = axis_state_map[axis_id]
                if axis_state.avg_mobility_grade is not None:
                    # 기동성등급: 1(우수) ~ 5(불량)
                    # 점수: 1 → 1.0, 5 → 0.0
                    mobility_score = 1.0 - (axis_state.avg_mobility_grade - 1) / 4.0
                    mobility_scores.append(mobility_score)
        
        if mobility_scores:
            return sum(mobility_scores) / len(mobility_scores)
        else:
            return 0.5  # 기본값
    
    def _calculate_constraint_compliance_score(
        self,
        coa: COA,
        axis_state_map: Dict[str, AxisState]
    ) -> float:
        """
        제약조건 준수도 점수 계산 (우선순위 기반 개선)
        
        개선사항:
        - ConstraintValidator를 사용한 제약별 검증
        - 우선순위 가중치 반영
        - 준수/위반 여부 실제 확인
        """
        # ConstraintValidator 초기화
        try:
            from core_pipeline.constraint_validator import ConstraintValidator
            validator = ConstraintValidator()
            use_validator = True
        except ImportError:
            use_validator = False
        
        weighted_scores = []
        total_weight = 0.0
        
        for axis_id in coa.axis_assignments.keys():
            if axis_id not in axis_state_map:
                continue
            
            axis_state = axis_state_map[axis_id]
            
            for constraint in axis_state.constraints:
                # 중요도 가중치 계산 (1~5 → 0.2~1.0)
                importance = constraint.importance or 3  # 기본값: 중간
                weight = importance / 5.0  # 1→0.2, 5→1.0
                
                if use_validator:
                    # ConstraintValidator 사용
                    context = {
                        'coa_axes': set(coa.axis_assignments.keys()),
                        'axis_id': axis_id,
                        # 추가 컨텍스트는 필요 시 확장
                    }
                    
                    compliance_score = validator.validate_constraint(
                        constraint, coa, context
                    )
                else:
                    # 폴백: 기존 간단한 로직
                    if len(axis_state.constraints) == 0:
                        compliance_score = 1.0
                    elif len(axis_state.constraints) <= 2:
                        compliance_score = 0.7
                    else:
                        compliance_score = 0.5
                
                # 가중 점수 계산
                weighted_score = compliance_score * weight
                weighted_scores.append(weighted_score)
                total_weight += weight
        
        # 가중 평균 계산
        if total_weight > 0:
            final_score = sum(weighted_scores) / total_weight
            return final_score
        else:
            # 제약조건이 없으면 최고 점수
            return 1.0
    
    def _calculate_threat_response_score(
        self,
        coa: COA,
        axis_state_map: Dict[str, AxisState]
    ) -> float:
        """위협 대응도 점수 계산 (축선 위협지수 반영)"""
        threat_scores = []
        
        for axis_id, assignment in coa.axis_assignments.items():
            if axis_id in axis_state_map:
                axis_state = axis_state_map[axis_id]
                
                # 위협레벨에 따른 점수
                threat_level_score = {
                    'High': 0.3,  # 고위협 축선에 배치하면 낮은 점수 (위험)
                    'Medium': 0.6,
                    'Low': 1.0  # 저위협 축선에 배치하면 높은 점수 (안전)
                }.get(axis_state.threat_level, 0.5)
                
                # 위협레벨이 높은 축선에 방어 역할 배치하면 가산점
                if axis_state.threat_level == 'High' and assignment.role.value in ['방어', 'DEFENSE']:
                    threat_level_score = 0.7  # 고위협 축선 방어는 적절
                
                # 위협점수 합계 반영 (낮을수록 좋음)
                threat_score_normalized = 1.0 - min(1.0, axis_state.threat_score_total / 10.0)
                
                # 두 점수의 평균
                combined_score = (threat_level_score + threat_score_normalized) / 2.0
                threat_scores.append(combined_score)
        
        if threat_scores:
            return sum(threat_scores) / len(threat_scores)
        else:
            return 0.5  # 기본값
    
    def _calculate_risk_score(
        self,
        coa: COA,
        axis_state_map: Dict[str, AxisState]
    ) -> float:
        """예상 손실/위험도 점수 계산 (0-1, 높을수록 위험)"""
        risk_factors = []
        
        for axis_id in coa.axis_assignments.keys():
            if axis_id in axis_state_map:
                axis_state = axis_state_map[axis_id]
                
                # 위협레벨 기반 위험도
                threat_risk = {
                    'High': 0.8,
                    'Medium': 0.5,
                    'Low': 0.2
                }.get(axis_state.threat_level, 0.5)
                
                # 전투력 비율 기반 위험도 (적군이 많을수록 위험)
                if axis_state.enemy_combat_power_total > 0:
                    power_ratio = axis_state.friendly_combat_power_total / axis_state.enemy_combat_power_total
                    if power_ratio < 0.5:
                        power_risk = 0.9  # 전투력 열세
                    elif power_ratio < 1.0:
                        power_risk = 0.6
                    else:
                        power_risk = 0.3
                else:
                    power_risk = 0.1
                
                # 두 위험도의 평균
                combined_risk = (threat_risk + power_risk) / 2.0
                risk_factors.append(combined_risk)
        
        if risk_factors:
            return sum(risk_factors) / len(risk_factors)
        else:
            return 0.5  # 기본값
    
    def _generate_summary(self, result: COAEvaluationResult) -> str:
        """요약 메시지 생성"""
        parts = []
        
        if result.combat_power_score >= 0.7:
            parts.append("전투력 우세")
        elif result.combat_power_score < 0.3:
            parts.append("전투력 열세")
        
        if result.threat_response_score >= 0.7:
            parts.append("위협 대응 우수")
        elif result.threat_response_score < 0.3:
            parts.append("위협 대응 부족")
        
        if result.risk_score < 0.3:
            parts.append("위험도 낮음")
        elif result.risk_score > 0.7:
            parts.append("위험도 높음")
        
        if parts:
            return ", ".join(parts)
        else:
            return "균형잡힌 COA"
    
    def _generate_details(
        self,
        result: COAEvaluationResult,
        coa: COA,
        axis_state_map: Dict[str, AxisState]
    ) -> Dict[str, str]:
        """상세 정보 생성"""
        details = {}
        
        details['combat_power'] = f"전투력 우세도: {result.combat_power_score:.2%}"
        details['mobility'] = f"기동 가능성: {result.mobility_score:.2%}"
        details['constraint_compliance'] = f"제약조건 준수도: {result.constraint_compliance_score:.2%}"
        details['threat_response'] = f"위협 대응도: {result.threat_response_score:.2%}"
        details['risk'] = f"위험도: {result.risk_score:.2%}"
        details['total_score'] = f"종합 점수: {result.total_score:.4f}"
        
        # 축선별 정보
        axis_info = []
        for axis_id in coa.axis_assignments.keys():
            if axis_id in axis_state_map:
                axis_state = axis_state_map[axis_id]
                axis_info.append(
                    f"{axis_state.axis_name}({axis_state.threat_level})"
                )
        if axis_info:
            details['axes'] = ", ".join(axis_info)
        
        return details
    
    def update_weights(self, new_weights: Dict[str, float]):
        """가중치 업데이트"""
        total = sum(new_weights.values())
        if total > 0:
            self.weights.update({k: v / total for k, v in new_weights.items()})
    
    def get_weights(self) -> Dict[str, float]:
        """현재 가중치 반환"""
        return self.weights.copy()

