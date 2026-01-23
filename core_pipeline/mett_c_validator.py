# core_pipeline/mett_c_validator.py
# -*- coding: utf-8 -*-
"""
METT-C Validator
METT-C 기반 방책 검증 및 리포트 생성
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class METTCValidationResult:
    """METT-C 검증 결과"""
    is_valid: bool
    issues: List[str]
    recommendations: List[str]
    mett_c_scores: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'mett_c_scores': self.mett_c_scores
        }


class METTCValidator:
    """METT-C 검증기"""
    
    def validate_coa(self, coa_result: Dict) -> METTCValidationResult:
        """
        COA 결과에 대한 METT-C 검증
        
        Args:
            coa_result: COA 평가 결과 (calculate_score_with_mett_c 결과 포함)
        
        Returns:
            METTCValidationResult
        """
        issues = []
        recommendations = []
        
        mett_c_scores = coa_result.get('mett_c', {})
        
        # 각 요소별 검증
        # 1. Mission 검증
        mission_score = mett_c_scores.get('mission', 0.5)
        if mission_score < 0.5:
            issues.append(f"임무 부합성 낮음 ({mission_score:.2f})")
            recommendations.append("임무 유형에 더 적합한 방책 선택 검토")
        
        # 2. Enemy 검증
        enemy_score = mett_c_scores.get('enemy', 0.5)
        if enemy_score < 0.4:
            issues.append(f"적군 대응 능력 부족 ({enemy_score:.2f})")
            recommendations.append("아군 전투력 보강 또는 방책 조정 필요")
        
        # 3. Terrain 검증
        terrain_score = mett_c_scores.get('terrain', 0.5)
        if terrain_score < 0.4:
            issues.append(f"지형 적합성 낮음 ({terrain_score:.2f})")
            recommendations.append("지형 조건을 고려한 방책 수정 검토")
        
        # 4. Troops 검증
        troops_score = mett_c_scores.get('troops', 0.5)
        if troops_score < 0.4:
            issues.append(f"부대 능력 부족 ({troops_score:.2f})")
            recommendations.append("자원/자산 가용성 확인 및 보강 검토")
        
        # 5. Civilian 검증 (NEW)
        civilian_score = mett_c_scores.get('civilian', 1.0)
        if civilian_score < 0.5:
            issues.append(f"민간인 보호 부족 ({civilian_score:.2f})")
            recommendations.append("민간인 지역 영향 최소화 방안 검토")
        if civilian_score < 0.3:
            issues.append("⚠️ 민간인 보호 점수가 매우 낮음 - 방책 재검토 필요")
        
        # 6. Time 검증 (NEW)
        time_score = mett_c_scores.get('time', 1.0)
        if time_score == 0.0:
            issues.append("❌ 시간 제약 위반 - 방책 실행 불가")
            recommendations.append("시간 제약을 만족하는 대안 방책 검토")
        elif time_score < 0.5:
            issues.append(f"시간 제약 준수도 낮음 ({time_score:.2f})")
            recommendations.append("COA 소요 시간 단축 방안 검토")
        
        # 종합 검증
        is_valid = (
            mission_score >= 0.5 and
            enemy_score >= 0.4 and
            terrain_score >= 0.4 and
            troops_score >= 0.4 and
            civilian_score >= 0.3 and  # 민간인 보호는 최소 0.3 이상
            time_score > 0.0  # 시간 제약 위반은 불가
        )
        
        return METTCValidationResult(
            is_valid=is_valid,
            issues=issues,
            recommendations=recommendations,
            mett_c_scores=mett_c_scores
        )



