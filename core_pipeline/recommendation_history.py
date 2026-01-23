# core_pipeline/recommendation_history.py
# -*- coding: utf-8 -*-
"""
Recommendation History
추천 히스토리 관리 모듈
"""
from datetime import datetime
from typing import Dict, List, Optional
import json


class RecommendationHistory:
    """추천 히스토리 관리"""
    
    def __init__(self, max_history: int = 100):
        """
        Args:
            max_history: 최대 히스토리 개수
        """
        self.history: List[Dict] = []
        self.max_history = max_history
    
    def save_recommendation(self, situation_id: str, recommendation: Dict):
        """
        추천 저장
        
        Args:
            situation_id: 상황 ID
            recommendation: 추천 결과 딕셔너리
        """
        entry = {
            "situation_id": situation_id,
            "timestamp": datetime.now().isoformat(),
            "recommendation": recommendation,
            "situation_info": recommendation.get("situation_info", {})
        }
        self.history.append(entry)
        
        # 최대 개수 제한
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_recommendation_history(self, situation_id: str) -> List[Dict]:
        """
        특정 상황의 추천 히스토리
        
        Args:
            situation_id: 상황 ID
            
        Returns:
            해당 상황의 추천 히스토리 리스트
        """
        return [
            entry for entry in self.history
            if entry["situation_id"] == situation_id
        ]
    
    def get_latest_recommendation(self, situation_id: str) -> Optional[Dict]:
        """
        최신 추천 가져오기
        
        Args:
            situation_id: 상황 ID
            
        Returns:
            최신 추천 딕셔너리 또는 None
        """
        entries = self.get_recommendation_history(situation_id)
        return entries[-1] if entries else None
    
    def get_previous_recommendation(self, situation_id: str) -> Optional[Dict]:
        """
        이전 추천 가져오기
        
        Args:
            situation_id: 상황 ID
            
        Returns:
            이전 추천 딕셔너리 또는 None
        """
        entries = self.get_recommendation_history(situation_id)
        return entries[-2] if len(entries) >= 2 else None
    
    def compare_recommendations(self, situation_id: str) -> Optional[Dict]:
        """
        추천 비교
        
        Args:
            situation_id: 상황 ID
            
        Returns:
            비교 결과 딕셔너리 또는 None
        """
        entries = self.get_recommendation_history(situation_id)
        if len(entries) < 2:
            return None
        
        latest = entries[-1]
        previous = entries[-2]
        
        latest_rec = latest["recommendation"]
        previous_rec = previous["recommendation"]
        
        latest_coas = latest_rec.get("recommendations", [])
        previous_coas = previous_rec.get("recommendations", [])
        
        comparison = {
            "threat_change": (
                latest["situation_info"].get("심각도", latest["situation_info"].get("위협수준", 0)) - 
                previous["situation_info"].get("심각도", previous["situation_info"].get("위협수준", 0))
            ),
            "recommendation_change": self._compare_coa_lists(
                previous_coas, latest_coas
            ),
            "score_change": self._compare_scores(previous_rec, latest_rec),
            "timestamp_diff": (
                datetime.fromisoformat(latest["timestamp"]) - 
                datetime.fromisoformat(previous["timestamp"])
            ).total_seconds()
        }
        
        return comparison
    
    def _compare_coa_lists(self, previous: List[Dict], latest: List[Dict]) -> Dict:
        """COA 리스트 비교"""
        prev_top = previous[0] if previous else None
        latest_top = latest[0] if latest else None
        
        return {
            "previous_top_coa": prev_top.get("방책명", prev_top.get("coa_name", "")) if prev_top else None,
            "current_top_coa": latest_top.get("방책명", latest_top.get("coa_name", "")) if latest_top else None,
            "coa_changed": (
                prev_top.get("방책명", prev_top.get("coa_name", "")) != latest_top.get("방책명", latest_top.get("coa_name", ""))
                if prev_top and latest_top else False
            ),
            "ranking_changes": self._compare_rankings(previous, latest)
        }
    
    def _compare_rankings(self, previous: List[Dict], latest: List[Dict]) -> List[Dict]:
        """순위 변화 비교"""
        changes = []
        for i, latest_coa in enumerate(latest[:5]):
            coa_name = latest_coa.get("방책명", latest_coa.get("coa_name", ""))
            # 이전 순위 찾기
            prev_rank = None
            for j, prev_coa in enumerate(previous):
                if prev_coa.get("방책명", prev_coa.get("coa_name", "")) == coa_name:
                    prev_rank = j
                    break
            
            changes.append({
                "coa": coa_name,
                "previous_rank": prev_rank + 1 if prev_rank is not None else None,
                "current_rank": i + 1,
                "rank_change": (prev_rank - i) if prev_rank is not None else None
            })
        
        return changes
    
    def _compare_scores(self, previous: Dict, latest: Dict) -> Dict:
        """점수 비교"""
        prev_top = previous.get("recommendations", [{}])[0]
        latest_top = latest.get("recommendations", [{}])[0]
        
        return {
            "previous_score": prev_top.get("최종점수", prev_top.get("score", 0)),
            "current_score": latest_top.get("최종점수", latest_top.get("score", 0)),
            "score_change": (
                latest_top.get("최종점수", latest_top.get("score", 0)) - 
                prev_top.get("최종점수", prev_top.get("score", 0))
            )
        }
    
    def get_all_history(self) -> List[Dict]:
        """전체 히스토리 가져오기"""
        return self.history.copy()
    
    def clear_history(self, situation_id: Optional[str] = None):
        """
        히스토리 삭제
        
        Args:
            situation_id: 상황 ID (None이면 전체 삭제)
        """
        if situation_id:
            self.history = [
                entry for entry in self.history
                if entry["situation_id"] != situation_id
            ]
        else:
            self.history = []


