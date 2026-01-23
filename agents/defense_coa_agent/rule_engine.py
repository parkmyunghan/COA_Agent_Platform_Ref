# agents/defense_coa_agent/rule_engine.py
# -*- coding: utf-8 -*-
"""
Rule Engine
YAML 규칙 파일 기반 동적 규칙 실행 엔진
"""
import os
import sys
import yaml
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# 전역 로그 제어 변수 (중복 로그 방지)
_rules_loaded_logged = False


def safe_print(msg, also_log_file: bool = True, logger_name: Optional[str] = None):
    """안전한 출력 함수 (개선된 버전 사용)"""
    from common.utils import safe_print as _safe_print
    if logger_name is None:
        logger_name = "RuleEngine"
    _safe_print(msg, also_log_file=also_log_file, logger_name=logger_name)


class RuleEngine:
    """규칙 엔진 클래스 - YAML 규칙 파일 기반 동적 규칙 실행"""
    
    def __init__(self, rules_path: Optional[str] = None):
        """
        Args:
            rules_path: YAML 규칙 파일 경로 (None이면 기본 경로 사용)
        """
        if rules_path is None:
            # 기본 경로: agents/defense_coa_agent/rules_defense.yaml
            rules_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'rules_defense.yaml'
            )
        
        self.rules_path = rules_path
        self.rules: List[Dict] = []
        self.weights: Dict[str, float] = {}
        self._load_rules()
    
    def _load_rules(self):
        """YAML 규칙 파일 로드 및 파싱"""
        global _rules_loaded_logged  # 함수 시작 부분에 global 선언
        
        try:
            if not os.path.exists(self.rules_path):
                safe_print(f"[WARN] 규칙 파일을 찾을 수 없습니다: {self.rules_path}")
                self.rules = []
                self.weights = {}
                return
            
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data:
                self.rules = data.get('rules', [])
                self.weights = data.get('weights', {})
                if not _rules_loaded_logged:
                    safe_print(f"[INFO] 규칙 파일 로드 완료: {len(self.rules)}개 규칙, {len(self.weights)}개 가중치")
                    _rules_loaded_logged = True
            else:
                self.rules = []
                self.weights = {}
                safe_print("[WARN] 규칙 파일이 비어있습니다.")
                
        except Exception as e:
            safe_print(f"[ERROR] 규칙 파일 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            self.rules = []
            self.weights = {}
    
    def reload_rules(self):
        """규칙 파일 재로드"""
        self._load_rules()
    
    def evaluate_condition(self, condition: Dict, context: Dict) -> bool:
        """
        조건 평가 로직
        
        Args:
            condition: 조건 딕셔너리 (예: {"threat_level": "> 0.7"})
            context: 컨텍스트 딕셔너리 (상황 정보 포함)
            
        Returns:
            조건 만족 여부
        """
        if not condition:
            return True
        
        for key, value in condition.items():
            # 컨텍스트에서 값 가져오기
            context_value = context.get(key)
            
            if context_value is None:
                # 키가 없으면 False (엄격한 평가)
                return False
            
            # 조건 문자열 파싱 및 평가
            if isinstance(value, str):
                # 문자열 조건 (예: "> 0.7", "<= 0.4", "> 0.4 and <= 0.7")
                if not self._evaluate_string_condition(context_value, value):
                    return False
            elif isinstance(value, (int, float)):
                # 숫자 비교 (기본적으로 ==)
                if context_value != value:
                    return False
            elif isinstance(value, dict):
                # 중첩된 조건 (재귀적 평가)
                if not self.evaluate_condition(value, context):
                    return False
            else:
                # 기타 타입은 직접 비교
                if context_value != value:
                    return False
        
        return True
    
    def _evaluate_string_condition(self, value: Any, condition_str: str) -> bool:
        """
        문자열 조건 평가 (예: "> 0.7", "<= 0.4", "> 0.4 and <= 0.7")
        
        Args:
            value: 평가할 값
            condition_str: 조건 문자열
            
        Returns:
            조건 만족 여부
        """
        try:
            # 숫자로 변환 시도
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    pass
            
            # "and" 또는 "or" 연산자 처리
            if " and " in condition_str.lower():
                parts = condition_str.split(" and ")
                return all(self._evaluate_single_condition(value, part.strip()) for part in parts)
            elif " or " in condition_str.lower():
                parts = condition_str.split(" or ")
                return any(self._evaluate_single_condition(value, part.strip()) for part in parts)
            else:
                return self._evaluate_single_condition(value, condition_str)
                
        except Exception as e:
            safe_print(f"[WARN] 조건 평가 오류: {condition_str}, 값: {value}, 오류: {e}")
            return False
    
    def _evaluate_single_condition(self, value: float, condition_str: str) -> bool:
        """
        단일 조건 평가 (예: "> 0.7", "<= 0.4")
        
        Args:
            value: 평가할 값 (숫자)
            condition_str: 조건 문자열
            
        Returns:
            조건 만족 여부
        """
        condition_str = condition_str.strip()
        
        # 비교 연산자 추출
        if condition_str.startswith(">="):
            threshold = float(condition_str[2:].strip())
            return value >= threshold
        elif condition_str.startswith("<="):
            threshold = float(condition_str[2:].strip())
            return value <= threshold
        elif condition_str.startswith(">"):
            threshold = float(condition_str[1:].strip())
            return value > threshold
        elif condition_str.startswith("<"):
            threshold = float(condition_str[1:].strip())
            return value < threshold
        elif condition_str.startswith("=="):
            threshold = float(condition_str[2:].strip())
            return value == threshold
        elif condition_str.startswith("!="):
            threshold = float(condition_str[2:].strip())
            return value != threshold
        else:
            # 기본적으로 == 비교
            try:
                threshold = float(condition_str)
                return value == threshold
            except ValueError:
                safe_print(f"[WARN] 알 수 없는 조건 형식: {condition_str}")
                return False
    
    def execute_action(self, action: Dict, context: Dict) -> Dict:
        """
        액션 실행 로직
        
        Args:
            action: 액션 딕셔너리 (예: {"coa": "Main_Defense", "priority": 1})
            context: 컨텍스트 딕셔너리
            
        Returns:
            실행 결과 딕셔너리
        """
        result = {
            "coa": action.get("coa"),
            "priority": action.get("priority", 999),
            "reason": action.get("reason", ""),
            "applied": True
        }
        
        return result
    
    def find_matching_rules(self, context: Dict) -> List[Dict]:
        """
        컨텍스트에 맞는 규칙 찾기
        
        Args:
            context: 컨텍스트 딕셔너리 (상황 정보 포함)
            
        Returns:
            매칭된 규칙 리스트 (우선순위 순으로 정렬)
        """
        matching_rules = []
        
        for rule in self.rules:
            condition = rule.get("condition", {})
            
            if self.evaluate_condition(condition, context):
                action = rule.get("action", {})
                result = self.execute_action(action, context)
                result["rule_name"] = rule.get("name", "Unknown")
                matching_rules.append(result)
        
        # 우선순위 순으로 정렬 (낮은 숫자가 높은 우선순위)
        matching_rules.sort(key=lambda x: x.get("priority", 999))
        
        return matching_rules
    
    def get_recommended_coa(self, context: Dict) -> Optional[Dict]:
        """
        컨텍스트에 맞는 최적의 COA 추천
        
        Args:
            context: 컨텍스트 딕셔너리 (상황 정보 포함)
            
        Returns:
            추천된 COA 딕셔너리 또는 None
        """
        matching_rules = self.find_matching_rules(context)
        
        if matching_rules:
            return matching_rules[0]  # 가장 높은 우선순위
        
        return None
    
    def get_weights(self) -> Dict[str, float]:
        """
        가중치 반환
        
        Returns:
            가중치 딕셔너리
        """
        return self.weights.copy()
    
    def apply_rule_based_scoring(self, strategies: List[Dict], context: Dict) -> List[Dict]:
        """
        규칙 기반 점수 조정
        
        Args:
            strategies: 방책 리스트
            context: 컨텍스트 딕셔너리
            
        Returns:
            점수 조정된 방책 리스트
        """
        # 매칭된 규칙 찾기
        matching_rules = self.find_matching_rules(context)
        
        if not matching_rules:
            # 규칙이 없으면 원본 반환
            return strategies
        
        # 가장 높은 우선순위 규칙 사용
        top_rule = matching_rules[0]
        recommended_coa = top_rule.get("coa")
        
        # 방책별 점수 조정
        for strategy in strategies:
            coa_id = str(strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('ID') or '').lower()
            coa_name = str(strategy.get('명칭') or strategy.get('방책명') or strategy.get('name') or '').lower()
            combined_name = f"{coa_name} {coa_id}"
            
            # 규칙에서 추천된 COA와 일치하면 가산점
            if recommended_coa and recommended_coa.lower() in combined_name:
                base_score = strategy.get('적합도점수', 0.5)
                # 우선순위가 높을수록 더 큰 가산점 (priority가 낮을수록 높은 우선순위)
                priority = top_rule.get("priority", 999)
                bonus = max(0.0, (10 - priority) * 0.05)  # 최대 0.5 가산점
                strategy['적합도점수'] = min(1.0, base_score + bonus)
                strategy['rule_applied'] = top_rule.get("rule_name")
                strategy['rule_bonus'] = bonus
            else:
                # 일치하지 않으면 감점 (작은 감점)
                base_score = strategy.get('적합도점수', 0.5)
                penalty = 0.05  # 작은 감점
                strategy['적합도점수'] = max(0.0, base_score - penalty)
        
        return strategies




