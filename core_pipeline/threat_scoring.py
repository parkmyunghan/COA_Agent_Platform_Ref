# core_pipeline/threat_scoring.py
# -*- coding: utf-8 -*-
"""
Threat Scoring Module
위협지수 계산 모듈
"""
from typing import Dict, List
from core_pipeline.data_models import ThreatEvent


class ThreatScorer:
    """위협지수 계산기"""
    
    # 위협수준 점수 매핑
    THREAT_LEVEL_SCORES = {
        'High': 3,
        'high': 3,
        'Medium': 2,
        'medium': 2,
        'Med': 2,
        'med': 2,
        'Low': 1,
        'low': 1,
        # 숫자 형식도 지원
        '1': 1,
        '2': 2,
        '3': 3,
        '4': 4,
        '5': 5,
    }
    
    # 위협유형별 가중치
    THREAT_TYPE_WEIGHTS = {
        '침투': 1.5,
        '기습공격': 1.5,
        '포병준비': 1.3,
        '공중위협': 1.3,
        '집결징후': 1.2,
        '상륙': 1.2,
        '기만징후': 0.8,
        # 기본값
        '기타': 1.0,
    }
    
    # 위협점수 합계 기준
    THREAT_SCORE_THRESHOLDS = {
        'High': 8.0,
        'Medium': 4.0,
        'Low': 0.0,
    }
    
    @classmethod
    def calculate_threat_score(cls, threat_event: ThreatEvent) -> float:
        """
        단일 위협상황의 위협점수 계산
        
        Args:
            threat_event: 위협상황 객체
            
        Returns:
            위협점수 (수준점수 × 유형가중치)
        """
        # 위협수준 점수
        threat_level = str(threat_event.threat_level or '').strip()
        level_score = cls.THREAT_LEVEL_SCORES.get(threat_level, 2)  # 기본값: Medium
        
        # 위협유형 가중치
        threat_type = str(threat_event.threat_type_code or '').strip()
        type_weight = cls.THREAT_TYPE_WEIGHTS.get(threat_type, 1.0)
        
        # 위협점수 = 수준점수 × 유형가중치
        threat_score = level_score * type_weight
        
        return threat_score
    
    @classmethod
    def calculate_axis_threat_score(cls, threat_events: List[ThreatEvent]) -> float:
        """
        축선별 위협점수 합계 계산
        
        Args:
            threat_events: 해당 축선과 관련된 위협상황 리스트
            
        Returns:
            위협점수 합계
        """
        total_score = 0.0
        
        for threat_event in threat_events:
            score = cls.calculate_threat_score(threat_event)
            total_score += score
        
        return total_score
    
    @classmethod
    def determine_threat_level(cls, threat_score_total: float) -> str:
        """
        위협점수 합계를 기준으로 위협레벨 결정
        
        Args:
            threat_score_total: 위협점수 합계
            
        Returns:
            위협레벨 ('High', 'Medium', 'Low')
        """
        if threat_score_total >= cls.THREAT_SCORE_THRESHOLDS['High']:
            return 'High'
        elif threat_score_total >= cls.THREAT_SCORE_THRESHOLDS['Medium']:
            return 'Medium'
        else:
            return 'Low'
    
    @classmethod
    def update_threat_weights(cls, weights: Dict[str, float]) -> None:
        """
        위협유형별 가중치 업데이트
        
        Args:
            weights: {위협유형: 가중치} 딕셔너리
        """
        cls.THREAT_TYPE_WEIGHTS.update(weights)
    
    @classmethod
    def update_threat_level_scores(cls, scores: Dict[str, int]) -> None:
        """
        위협수준 점수 매핑 업데이트
        
        Args:
            scores: {위협수준: 점수} 딕셔너리
        """
        cls.THREAT_LEVEL_SCORES.update(scores)
    
    @classmethod
    def update_threat_thresholds(cls, thresholds: Dict[str, float]) -> None:
        """
        위협레벨 임계값 업데이트
        
        Args:
            thresholds: {위협레벨: 임계값} 딕셔너리
        """
        cls.THREAT_SCORE_THRESHOLDS.update(thresholds)

