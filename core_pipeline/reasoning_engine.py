# core_pipeline/reasoning_engine.py
# -*- coding: utf-8 -*-
"""
Reasoning Engine
규칙 기반 추론 엔진 모듈
팔란티어 방식: 다중 요소 기반 추론 지원
"""
from typing import Dict, List, Optional
import pandas as pd
import os
import sys

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from agents.defense_coa_agent.rule_engine import RuleEngine
    RULE_ENGINE_AVAILABLE = True
except ImportError:
    RULE_ENGINE_AVAILABLE = False
    print("[WARN] RuleEngine을 임포트할 수 없습니다. 규칙 엔진 기능이 비활성화됩니다.")


class ReasoningEngine:
    """추론 엔진 클래스"""
    
    def __init__(self, config: Optional[Dict] = None,
                 relevance_mapper=None,  # [NEW] 주입
                 resource_parser=None):  # [NEW] 주입
        """
        Args:
            config: 설정 딕셔너리 (선택적)
            relevance_mapper: RelevanceMapper 인스턴스 (주입용)
            resource_parser: ResourcePriorityParser 인스턴스 (주입용)
        """
        self.config = config or {}
        self.use_palantir_mode = self.config.get("use_palantir_mode", False)
        
        # [FIXED] 주입된 매퍼 저장
        self.relevance_mapper = relevance_mapper
        self.resource_parser = resource_parser
        
        # 규칙 엔진 초기화 (가능한 경우)
        self.rule_engine = None
        if RULE_ENGINE_AVAILABLE:
            try:
                self.rule_engine = RuleEngine()
            except Exception as e:
                print(f"[WARN] 규칙 엔진 초기화 실패: {e}")
                self.rule_engine = None
    
    # 동적 추론을 위한 규칙 정의
    DYNAMIC_RULES = {
        'terrain': {
            'Mountains': {'Mechanized': -0.3, 'Armor': -0.4, 'Infantry': 0.1, 'Air': -0.1},
            'Urban': {'Mechanized': -0.2, 'Armor': -0.3, 'Infantry': 0.2},
            'Plains': {'Mechanized': 0.1, 'Armor': 0.2, 'Infantry': -0.1},
            'River': {'Mechanized': -0.5, 'Armor': -0.5, 'Engineer': 0.3}
        },
        'weather': {
            'Rain': {'Air': -0.4, 'Mechanized': -0.1},
            'Fog': {'Air': -0.6, 'Recon': -0.5},
            'Snow': {'Mechanized': -0.2, 'Infantry': -0.2}
        }
    }

    def evaluate_scores(self, features: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
        """
        특징값과 가중치를 기반으로 점수 계산
        
        Args:
            features: {특징명: 값} 딕셔너리
            weights: {특징명: 가중치} 딕셔너리 (None이면 모두 1.0)
            
        Returns:
            계산된 점수
        """
        if weights is None:
            weights = {k: 1.0 for k in features}
        
        score = sum(features.get(k, 0) * weights.get(k, 1.0) for k in features)
        return score

    def calculate_dynamic_score(self, coa, context: Dict) -> float:
        """
        [NEW] 동적 추론 점수 계산
        지형, 기상 등 상황 변수에 따라 기본 점수를 조정합니다.
        
        Args:
            coa: COA 객체 (coa_id, coa_name, description 등 속성 필요)
            context: 상황 컨텍스트 (terrain, weather 키 포함)
            
        Returns:
            조정된 점수 (0.0 ~ 1.0)
        """
        # 1. 기본 점수 설정 (입력값이 없으면 0.5)
        base_score = context.get('base_score', 0.5)
        current_score = base_score
        
        # 2. COA 타입 추론 (이름/ID 기반 단순 추론)
        coa_name = str(getattr(coa, 'coa_name', '') or getattr(coa, 'coa_id', '')).lower()
        coa_desc = str(getattr(coa, 'description', '')).lower()
        full_text = f"{coa_name} {coa_desc}"
        
        # 부대/작전 유형 식별
        unit_types = []
        if any(x in full_text for x in ['기계화', 'mechanized', 'tank', '전차']):
            unit_types.append('Mechanized')
            unit_types.append('Armor')
        if any(x in full_text for x in ['보병', 'infantry', '특수전', 'special forces']):
            unit_types.append('Infantry')
        if any(x in full_text for x in ['항공', 'air', '헬기', 'helicopter']):
            unit_types.append('Air')
        if any(x in full_text for x in ['공병', 'engineer']):
            unit_types.append('Engineer')
        if any(x in full_text for x in ['정찰', 'recon']):
            unit_types.append('Recon')
            
        # 3. 지형(Terrain) 효과 적용
        terrain = context.get('terrain', 'Plains') # 기본값: 평지
        terrain_rules = self.DYNAMIC_RULES['terrain'].get(terrain, {})
        
        for u_type in unit_types:
            if u_type in terrain_rules:
                adjustment = terrain_rules[u_type]
                current_score += adjustment
                # print(f"[DEBUG] 지형 효과({terrain}): {u_type} -> {adjustment:+.1f}")

        # 4. 기상(Weather) 효과 적용
        weather = context.get('weather', 'Clear') # 기본값: 맑음
        weather_rules = self.DYNAMIC_RULES['weather'].get(weather, {})
        
        for u_type in unit_types:
            if u_type in weather_rules:
                adjustment = weather_rules[u_type]
                current_score += adjustment
                # print(f"[DEBUG] 기상 효과({weather}): {u_type} -> {adjustment:+.1f}")
                
        # 5. 점수 범위 제한 (0.0 ~ 1.0)
        return min(1.0, max(0.0, current_score))
    
    def run_defense_rules(self, context: Dict) -> Dict:
        """
        방어 규칙 실행
        
        Args:
            context: 컨텍스트 딕셔너리 (graph, data 등 포함 가능)
            
        Returns:
            방어 COA 결과 딕셔너리
        """
        # 팔란티어 모드 사용 여부 확인
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_defense_rules_palantir(context)
        else:
            return self._run_defense_rules_basic(context)

    def run_offensive_rules(self, context: Dict) -> Dict:
        """공격 규칙 실행"""
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_offensive_rules_palantir(context)
        else:
            return self._run_offensive_rules_basic(context)

    def run_counter_attack_rules(self, context: Dict) -> Dict:
        """반격 규칙 실행"""
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_counter_attack_rules_palantir(context)
        else:
            return self._run_counter_attack_rules_basic(context)

    def run_preemptive_rules(self, context: Dict) -> Dict:
        """선제 공격 규칙 실행"""
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_preemptive_rules_palantir(context)
        else:
            return self._run_preemptive_rules_basic(context)

    def run_deterrence_rules(self, context: Dict) -> Dict:
        """억제 규칙 실행"""
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_deterrence_rules_palantir(context)
        else:
            return self._run_deterrence_rules_basic(context)

    def run_maneuver_rules(self, context: Dict) -> Dict:
        """기동 규칙 실행"""
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_maneuver_rules_palantir(context)
        else:
            return self._run_maneuver_rules_basic(context)

    def run_information_ops_rules(self, context: Dict) -> Dict:
        """정보 작전 규칙 실행"""
        if self.use_palantir_mode or context.get("use_palantir_mode", False):
            return self._run_information_ops_rules_palantir(context)
        else:
            return self._run_information_ops_rules_basic(context)

    def run_coa_rules(self, context: Dict, coa_type: str = "defense") -> Dict:
        """
        범용 COA 규칙 실행 (타입별 분기)
        
        Args:
            context: 컨텍스트 딕셔너리
            coa_type: 방책 타입 ("defense", "offensive", "counter_attack", 등)
            
        Returns:
            COA 결과 딕셔너리
        """
        type_map = {
            "defense": self.run_defense_rules,
            "offensive": self.run_offensive_rules,
            "counter_attack": self.run_counter_attack_rules,
            "preemptive": self.run_preemptive_rules,
            "deterrence": self.run_deterrence_rules,
            "maneuver": self.run_maneuver_rules,
            "information_ops": self.run_information_ops_rules
        }
        
        rule_func = type_map.get(coa_type.lower(), self.run_defense_rules)
        return rule_func(context)
    
    def _run_defense_rules_basic(self, context: Dict) -> Dict:
        """기본 규칙 기반 추론 (YAML 규칙 파일 우선 사용)"""
        threat_level = context.get("threat_level", 0.5)
        defense_assets = context.get("defense_assets", [])
        
        # 그래프에서 위협 정보 추출 시도
        graph = context.get("graph")
        if graph is not None:
            try:
                from rdflib import URIRef, Literal
                ns = context.get("namespace")
                if ns:
                    # [REFACTORED] SPARQL 쿼리 대신 graph.triples() 사용
                    max_threat = 0.0
                    threat_level_prop = ns.ThreatLevel
                    for s, p, o in graph.triples((None, threat_level_prop, None)):
                        try:
                            val = float(str(o))
                            if val > 80 and val > max_threat:
                                max_threat = val
                        except (ValueError, TypeError):
                            continue
                    
                    if max_threat > 0:
                        threat_level = max_threat / 100.0
            except Exception:
                pass
        
        # 규칙 엔진 사용 (가능한 경우)
        if self.rule_engine is not None:
            try:
                rule_context = {
                    "threat_level": threat_level
                }
                recommended_coa = self.rule_engine.get_recommended_coa(rule_context)
                
                if recommended_coa:
                    return {
                        "COA": recommended_coa.get("coa", "Unknown"),
                        "Reason": f"Rule: {recommended_coa.get('rule_name', 'Unknown')}",
                        "ThreatLevel": threat_level,
                        "DefenseAssets": len(defense_assets),
                        "RuleApplied": True,
                        "RuleName": recommended_coa.get("rule_name")
                    }
            except Exception as e:
                print(f"[WARN] 규칙 엔진 실행 실패, 기본 로직 사용: {e}")
        
        # 폴백: 기본 규칙 (YAML 규칙 파일이 없거나 실패한 경우)
        if threat_level > 0.7:
            coa = "Main_Defense"
            reason = "High Threat Level"
        elif threat_level > 0.4:
            coa = "Moderate_Defense"
            reason = "Moderate Threat Level"
        else:
            coa = "Minimal_Defense"
            reason = "Low Threat Level"
        
        return {
            "COA": coa,
            "Reason": reason,
            "ThreatLevel": threat_level,
            "DefenseAssets": len(defense_assets),
            "RuleApplied": False
        }
    
    def _run_defense_rules_palantir(self, context: Dict) -> Dict:
        """팔란티어 방식: 다중 요소 기반 추론 + 체인 탐색"""
        from core_pipeline.coa_scorer import COAScorer
        
        # [FIXED] 주입된 매퍼 전달 (성능 최적화)
        scorer = COAScorer(
            data_manager=data_manager, 
            config=config,
            relevance_mapper=self.relevance_mapper,
            resource_parser=self.resource_parser
        )
        
        # 1. 위협 점수 계산
        threat_score = self._extract_threat_score(context)
        
        # 2. 자원 가용성 계산
        resource_availability = self._extract_resource_availability(context)
        
        # 3. 방어 자산 능력 계산
        asset_capability = self._extract_asset_capability(context)
        
        # 4. 환경 적합성 계산
        environment_fit = self._extract_environment_fit(context)
        
        # 5. 과거 성공률 계산 (RAG 결과가 있는 경우)
        historical_success = self._extract_historical_success(context)
        
        # 6. 체인 기반 COA 점수 추가 (있는 경우)
        chain_score = self._extract_chain_score(context)
        
        # 종합 점수 계산 (컨텍스트에 모든 정보 포함)
        score_context = {
            'threat_score': threat_score,
            'resource_availability': resource_availability,
            'asset_capability': asset_capability,
            'environment_fit': environment_fit,
            'historical_success': historical_success,
            'chain_score': chain_score,  # 체인 점수 추가
            # 온톨로지 매니저와 그래프 전달 (추가 점수 계산에 필요)
            'ontology_manager': context.get('ontology_manager'),
            'graph': context.get('graph'),
            'coa_uri': context.get('coa_uri'),
            'situation_id': context.get('situation_id')
        }
        score_result = scorer.calculate_score(score_context)
        
        # 체인 정보 가져오기
        chain_info = context.get("chain_info", {})
        
        # 점수에 따른 COA 결정
        total_score = score_result['total']
        if total_score > 0.7:
            coa = "Main_Defense"
            reason = f"High Comprehensive Score ({total_score:.2f})"
        elif total_score > 0.4:
            coa = "Moderate_Defense"
            reason = f"Moderate Comprehensive Score ({total_score:.2f})"
        else:
            coa = "Minimal_Defense"
            reason = f"Low Comprehensive Score ({total_score:.2f})"
        
        result = {
            "COA": coa,
            "Reason": reason,
            "ThreatLevel": threat_score,
            "DefenseAssets": len(context.get("defense_assets", [])),
            "TotalScore": total_score,
            "ScoreBreakdown": score_result['breakdown'],
            "PalantirMode": True
        }
        
        # 체인 정보가 있으면 추가
        if chain_info:
            result["ChainInfo"] = chain_info
        
        return result

    def _run_offensive_rules_basic(self, context: Dict) -> Dict:
        """공격 기본 규칙"""
        threat_level = context.get("threat_level", 0.5)
        # 간단한 로직 예시
        if threat_level > 0.6:
            coa = "Main_Offensive"
            reason = "High Opportunity for Attack"
        else:
            coa = "Limited_Offensive"
            reason = "Limited Opportunity"
            
        return {
            "COA": coa,
            "Reason": reason,
            "ThreatLevel": threat_level,
            "RuleApplied": False
        }

    def _run_offensive_rules_palantir(self, context: Dict) -> Dict:
        """공격 팔란티어 규칙"""
        # Defense와 유사하게 구현하되 가중치만 다르게 적용될 예정
        # 여기서는 재사용성을 위해 _run_generic_palantir 호출 권장하지만,
        # 일단 독립적으로 구현하거나 기존 로직 활용
        return self._run_generic_palantir(context, "offensive")

    def _run_counter_attack_rules_basic(self, context: Dict) -> Dict:
        """반격 기본 규칙"""
        return {"COA": "Counter_Attack_Alpha", "Reason": "Basic Rule", "RuleApplied": False}

    def _run_counter_attack_rules_palantir(self, context: Dict) -> Dict:
        return self._run_generic_palantir(context, "counter_attack")

    def _run_preemptive_rules_basic(self, context: Dict) -> Dict:
        return {"COA": "Preemptive_Strike", "Reason": "Basic Rule", "RuleApplied": False}

    def _run_preemptive_rules_palantir(self, context: Dict) -> Dict:
        return self._run_generic_palantir(context, "preemptive")

    def _run_deterrence_rules_basic(self, context: Dict) -> Dict:
        return {"COA": "Show_Of_Force", "Reason": "Basic Rule", "RuleApplied": False}

    def _run_deterrence_rules_palantir(self, context: Dict) -> Dict:
        return self._run_generic_palantir(context, "deterrence")

    def _run_maneuver_rules_basic(self, context: Dict) -> Dict:
        return {"COA": "Flanking_Maneuver", "Reason": "Basic Rule", "RuleApplied": False}

    def _run_maneuver_rules_palantir(self, context: Dict) -> Dict:
        return self._run_generic_palantir(context, "maneuver")

    def _run_information_ops_rules_basic(self, context: Dict) -> Dict:
        return {"COA": "Cyber_Disruption", "Reason": "Basic Rule", "RuleApplied": False}

    def _run_information_ops_rules_palantir(self, context: Dict) -> Dict:
        return self._run_generic_palantir(context, "information_ops")

    def _run_generic_palantir(self, context: Dict, coa_type: str) -> Dict:
        """범용 팔란티어 모드 실행"""
        from core_pipeline.coa_scorer import COAScorer
        
        # [FIXED] 주입된 매퍼 전달 (성능 최적화)
        scorer = COAScorer(
            data_manager=data_manager, 
            config=config, 
            coa_type=coa_type,
            relevance_mapper=self.relevance_mapper,
            resource_parser=self.resource_parser
        )
        
        # 점수 요소 추출 (기존 메서드 재사용)
        threat_score = self._extract_threat_score(context)
        resource_availability = self._extract_resource_availability(context)
        asset_capability = self._extract_asset_capability(context)
        environment_fit = self._extract_environment_fit(context)
        historical_success = self._extract_historical_success(context)
        chain_score = self._extract_chain_score(context)
        
        score_context = {
            'threat_score': threat_score,
            'resource_availability': resource_availability,
            'asset_capability': asset_capability,
            'environment_fit': environment_fit,
            'historical_success': historical_success,
            'chain_score': chain_score,
            'ontology_manager': context.get('ontology_manager'),
            'graph': context.get('graph'),
            'coa_uri': context.get('coa_uri'),
            'situation_id': context.get('situation_id')
        }
        
        score_result = scorer.calculate_score(score_context)
        total_score = score_result['total']
        
        # 결과 구성
        result = {
            "COA": f"Best_{coa_type.capitalize()}", # 임시 명칭
            "Reason": f"High Score ({total_score:.2f})",
            "ThreatLevel": threat_score,
            "TotalScore": total_score,
            "ScoreBreakdown": score_result['breakdown'],
            "PalantirMode": True,
            "COAType": coa_type
        }
        
        if context.get("chain_info"):
            result["ChainInfo"] = context.get("chain_info")
            
        return result
    
    def _extract_threat_score(self, context: Dict) -> float:
        """위협 점수 추출"""
        # context에서 직접 threat_level 가져오기 (우선순위 높음)
        threat_level = context.get("threat_level")
        
        # threat_level이 이미 제공되었으면 정규화 후 반환
        if threat_level is not None and isinstance(threat_level, (int, float)):
            if threat_level > 1.0:
                threat_level = threat_level / 100.0
            return min(1.0, max(0.0, threat_level))
        
        # threat_level이 없으면 기본값 사용
        threat_level = 0.5
        
        # 그래프에서 위협 정보 추출 시도 (보조적, context의 값보다 낮으면 사용하지 않음)
        graph = context.get("graph")
        if graph is not None:
            try:
                ns = context.get("namespace")
                if ns:
                    # [REFACTORED] SPARQL 대신 graph.triples() 사용
                    max_val = 0.0
                    threat_level_prop = URIRef("http://coa-agent-platform.org/ontology#ThreatLevel")
                    for s, p, o in graph.triples((None, threat_level_prop, None)):
                        try:
                            val = float(str(o))
                            if val > max_val:
                                max_val = val
                        except (ValueError, TypeError):
                            continue
                    
                    if max_val > 0:
                        graph_threat = max_val / 100.0 if max_val > 1.0 else max_val
                        if graph_threat > threat_level:
                            threat_level = graph_threat
            except Exception:
                pass
        
        return min(1.0, max(0.0, threat_level))
    
    def _extract_resource_availability(self, context: Dict) -> float:
        """자원 가용성 추출 (로깅 및 검증 강화)"""
        ontology_manager = context.get("ontology_manager")
        situation_id = context.get("situation_id")
        coa_uri = context.get("coa_uri")  # 실제 COA URI 사용
        
        # 직접 제공된 자원 가용성 사용
        if "resource_availability" in context:
            return float(context["resource_availability"])
        
        if not ontology_manager or not hasattr(ontology_manager, 'execute_template_query'):
            from common.utils import safe_print
            safe_print("[WARN] OntologyManager 또는 execute_template_query 메서드가 없습니다. 기본값(0.5) 사용", logger_name="ReasoningEngine")
            return 0.5
        
        if not situation_id:
            situation_id = "THREAT001"  # 기본값 (위협상황 ID 형식)
            from common.utils import safe_print
            safe_print(f"[INFO] situation_id가 없어 기본값 사용: {situation_id}", logger_name="ReasoningEngine")
        
        try:
            from common.utils import safe_print
            required_resources = []
            available_resources = []
            
            # COA별 필요한 자원 조회 (coa_uri가 있는 경우)
            if coa_uri:
                safe_print(f"[INFO] 자원 가용성 조회: COA={coa_uri}, Situation={situation_id}", logger_name="ReasoningEngine")
                from rdflib import URIRef
                coa_node = URIRef(coa_uri)
                ns = ontology_manager.ns
                
                required_resources_nodes = []
                # ns:requiresResource OR ns:필요자원
                for o in ontology_manager.graph.objects(coa_node, ns.requiresResource):
                    required_resources_nodes.append(o)
                for o in ontology_manager.graph.objects(coa_node, ns.필요자원):
                    required_resources_nodes.append(o)
                
                if required_resources_nodes:
                    required_resources = [str(r) for r in required_resources_nodes]
                    safe_print(f"[INFO] 필요한 자원: {len(required_resources)}개 - {required_resources[:3]}", logger_name="ReasoningEngine")
                else:
                    # 🔥 로그 최적화: 첫 번째 COA에서만 경고 출력 (반복 방지)
                    if not hasattr(self, '_resource_warning_logged'):
                        safe_print(f"[WARN] COA {coa_uri}에 대한 필요한 자원을 찾을 수 없습니다. (이 경고는 첫 번째 COA에서만 표시됩니다)", logger_name="ReasoningEngine")
                        self._resource_warning_logged = True
            else:
                safe_print(f"[WARN] coa_uri가 없어 필요한 자원 조회를 건너뜁니다.", logger_name="ReasoningEngine")
            
            # 상황별 가용 자원 조회
            from rdflib import URIRef, RDF
            ns = ontology_manager.ns
            
            # [IMPROVED] Situation ID(위협ID)를 기반으로 관련 임무(Mission) 식별
            # THREAT001 -> 시나리오 -> 임무 -> 가용자원 연결 고리 추적
            target_mission_nodes = []
            
            # 1. 입력 ID로 직접 Mission/Scenario 노드 찾기 시도
            if "MSN" in situation_id:
                # Mission ID인 경우
                target_mission_nodes.append(URIRef(ns[f"임무정보_{situation_id}"]))
            elif "THR" in situation_id or "THREAT" in situation_id:
                # Threat ID인 경우 -> 시나리오를 통해 Mission 찾기
                # ID 정규화: THREAT001 -> THR001 (데이터 정합성 이슈 대응)
                normalized_id = situation_id.replace("THREAT", "THR")
                threat_uri_candidates = [
                    URIRef(ns[f"위협상황_{situation_id}"]), 
                    URIRef(ns[f"위협상황_{normalized_id}"])
                ]
                
                for threat_node in threat_uri_candidates:
                    # ?scenario ns:has위협상황 ?threat_node
                    for scenario in ontology_manager.graph.subjects(ns.has위협상황, threat_node):
                        # ?scenario ns:has임무정보 ?mission
                        for mission in ontology_manager.graph.objects(scenario, ns.has임무정보):
                            target_mission_nodes.append(mission)
            
            if not target_mission_nodes:
                # 매핑 실패 시 situation_id를 그대로 사용하여 폴백
                 target_mission_nodes.append(URIRef(situation_id if situation_id.startswith('http') else f"http://coa-agent-platform.org/ontology#{situation_id}"))
                 # 기본 Mission ID(MSN001) 추가 시도 (데이터 누락 대비)
                 target_mission_nodes.append(URIRef(ns["임무정보_MSN001"]))

            # [IMPROVED] 모든 관련 노드(Mission + Threat)에서 자원 수집
            search_nodes = list(target_mission_nodes)
            if "THR" in situation_id or "THREAT" in situation_id:
                # 위협 상황 노드도 검색 대상에 포함 (hasResourceSnapshot이 위협 상황에 연결될 수 있음)
                normalized_id = situation_id.replace("THREAT", "THR")
                search_nodes.append(URIRef(ns[f"위협상황_{situation_id}"]))
                if normalized_id != situation_id:
                    search_nodes.append(URIRef(ns[f"위협상황_{normalized_id}"]))

            available_nodes = set()
            for node_to_check in search_nodes:
                # 1. 연결된 가용 자원 (ns:AvailableResource ns:forScenario ?node)
                for res in ontology_manager.graph.subjects(ns.forScenario, node_to_check):
                    available_nodes.add(res)
                
                # 2. 직접 연결된 자원 
                for o in ontology_manager.graph.objects(node_to_check, ns.hasAvailableResource):
                    available_nodes.add(o)
                for o in ontology_manager.graph.objects(node_to_check, ns.has가용자원):
                    available_nodes.add(o)
                # [NEW] 가용자원 스냅샷 통합 (OntologyManagerEnhanced에서 생성한 관계)
                for o in ontology_manager.graph.objects(node_to_check, ns.hasResourceSnapshot):
                    available_nodes.add(o)

                # 3. 지형셀 기반 (Legacy)
                for loc in ontology_manager.graph.objects(node_to_check, ns.has지형셀):

                     for res, p, o in ontology_manager.graph.triples((None, ns.has지형셀, loc)):
                        available_nodes.add(res)
            
            if available_nodes:
                available_resources = [str(a) for a in available_nodes]
                # 자산/부대 카운트
                asset_count = sum(1 for a in available_nodes if (a, RDF.type, ns.아군가용자산) in ontology_manager.graph)
                unit_count = sum(1 for a in available_nodes if (a, RDF.type, ns.아군부대현황) in ontology_manager.graph)
                res_count = sum(1 for a in available_nodes if (a, RDF.type, ns.AvailableResource) in ontology_manager.graph)
                legacy_count = sum(1 for a in available_nodes if (a, RDF.type, ns.가용자원) in ontology_manager.graph)
                
                if context.get('is_first_coa', False):
                    safe_print(f"[INFO] 가용 자원: {len(available_nodes)}개 (일반: {res_count}, 자산: {asset_count}, 부대: {unit_count}, 레거시: {legacy_count})", logger_name="ReasoningEngine")

            else:
                # 🔥 로그 최적화: 첫 번째 COA에서만 경고 출력 (반복 방지)
                if not hasattr(self, '_available_resource_warning_logged'):
                    safe_print(f"[WARN] 상황 {situation_id} (Mission Candidates: {target_mission_nodes})에 대한 가용 자원을 찾을 수 없습니다. (이 경고는 첫 번째 COA에서만 표시됩니다)", logger_name="ReasoningEngine")
                    self._available_resource_warning_logged = True
            
            # 자원 매칭률 계산 (팔란티어 방식: 다층 매칭 + 품질 반영)
            if required_resources and available_resources:
                # 1. 직접 URI 매칭 시도
                matched = set(required_resources) & set(available_resources)
                
                # 2. 개념적 자원과 부대 인스턴스 매칭 (직접 매칭 실패 시)
                if len(matched) == 0:
                    matched_count = 0.0
                    for req_resource_uri in required_resources:
                        # 개념적 자원 추출 (URI에서 마지막 부분)
                        required_concept = req_resource_uri.split('#')[-1] if '#' in req_resource_uri else req_resource_uri
                        required_concept_lower = required_concept.lower()
                        
                        # 각 가용 부대와 매칭 시도 (팔란티어 방식: 신뢰도 점수 활용)
                        best_match_score = 0.0
                        best_match_unit = None
                        debug_mode = context.get('is_first_coa', False)
                        for avail_unit_uri in available_resources:
                            is_match, confidence = self._match_resource_concept_to_unit_enhanced(
                                required_concept_lower, 
                                avail_unit_uri, 
                                ontology_manager,
                                debug=debug_mode
                            )
                            if is_match:
                                if confidence > best_match_score:
                                    best_match_score = confidence
                                    best_match_unit = avail_unit_uri
                                if context.get('is_first_coa', False):
                                    safe_print(f"[INFO] 자원 매칭 성공: '{required_concept}' <-> '{avail_unit_uri}' (신뢰도: {confidence:.2f})", logger_name="ReasoningEngine")
                        
                        # 매칭 실패 시 디버깅 정보 출력 (첫 번째 COA에서만)
                        # 🔥 최적화: 매칭 실패 로그 제거 (요약 로그로 대체)
                        # if best_match_score == 0.0 and context.get('is_first_coa', False):
                        #     # 부대 속성 조회 결과 확인
                        #     if available_resources:
                        #         sample_unit = available_resources[0]
                        #         unit_props = self._get_unit_properties(sample_unit, ontology_manager)
                        #         safe_print(f"[DEBUG] 매칭 실패 분석: required='{required_concept}', sample_unit='{sample_unit}', unit_props={unit_props}", logger_name="ReasoningEngine")
                        
                        # 대체 자원 확인 (NEW: 팔란티어 방식)
                        if best_match_score < 0.5:
                            alternatives = self._find_alternative_resources(req_resource_uri, context)
                            for alt_resource in alternatives:
                                is_match, confidence = self._match_resource_concept_to_unit_enhanced(
                                    required_concept_lower,
                                    alt_resource,
                                    ontology_manager,
                                    debug=debug_mode
                                )
                                if is_match:
                                    if confidence * 0.8 > best_match_score:
                                        best_match_score = confidence * 0.8  # 대체 자원은 80% 가중치
                                        best_match_unit = alt_resource
                                    if context.get('is_first_coa', False):
                                        safe_print(f"[INFO] 대체 자원 매칭: '{required_concept}' <-> '{alt_resource}' (신뢰도: {confidence * 0.8:.2f})", logger_name="ReasoningEngine")
                        
                        # 신뢰도 점수를 누적 (부분 매칭도 반영)
                        matched_count += best_match_score
                    
                    # 매칭률 = 누적 신뢰도 점수 / 필요한 자원 수
                    match_ratio = matched_count / len(required_resources) if len(required_resources) > 0 else 0.0
                    
                    # 자원 품질 반영 (팔란티어 방식)
                    quality_score = self._calculate_resource_quality(available_resources, ontology_manager)
                    match_ratio = match_ratio * quality_score  # 매칭률 * 품질
                    
                    if context.get('is_first_coa', False):
                        safe_print(f"[INFO] 자원 매칭률: {matched_count:.2f}/{len(required_resources)} = {match_ratio:.2f} (품질 반영: {quality_score:.2f})", logger_name="ReasoningEngine")
                else:
                    # 직접 URI 매칭 성공
                    match_ratio = len(matched) / len(required_resources) if len(required_resources) > 0 else 0.0
                    # 직접 매칭된 경우에도 품질 반영
                    quality_score = self._calculate_resource_quality(available_resources, ontology_manager)
                    match_ratio = match_ratio * quality_score
                    if context.get('is_first_coa', False):
                        safe_print(f"[INFO] 자원 매칭률: {len(matched)}/{len(required_resources)} = {match_ratio:.2f} (품질 반영: {quality_score:.2f})", logger_name="ReasoningEngine")
                
                return match_ratio
            elif not required_resources and available_resources:
                # 필요한 자원 정보가 없으면 가용 자원이 있으면 높은 점수
                safe_print("[INFO] 필요한 자원 정보 없음. 가용 자원 존재로 인해 높은 점수(0.8) 사용", logger_name="ReasoningEngine")
                return 0.8
            elif required_resources and not available_resources:
                # 필요한 자원이 있지만 가용 자원이 없으면 낮은 점수
                safe_print("[WARN] 필요한 자원이 있지만 가용 자원이 없음. 낮은 점수(0.2) 사용", logger_name="ReasoningEngine")
                return 0.2
            else:
                safe_print("[WARN] 자원 정보가 없어 기본값(0.5) 사용", logger_name="ReasoningEngine")
        except Exception as e:
            from common.utils import safe_print
            safe_print(f"[ERROR] Resource availability extraction failed: {e}", logger_name="ReasoningEngine")
            import traceback
            traceback.print_exc()
        
        return 0.5  # 기본값

    def _extract_mission_type(self, context: Dict) -> Optional[str]:
        """임무 유형 추출 (Ontology 기반)"""
        ontology_manager = context.get("ontology_manager")
        situation_id = context.get("situation_id_raw") or context.get("situation_id")
        
        if not ontology_manager or not situation_id or not hasattr(ontology_manager, 'graph') or ontology_manager.graph is None:
            return None
            
        try:
            from rdflib import URIRef
            from common.utils import safe_print
            ns = ontology_manager.ns
            
            # Mission 식별 (resource_availability 로직과 동일)
            target_mission_nodes = []
            if "MSN" in situation_id:
                # Mission ID인 경우
                target_mission_nodes.append(URIRef(ns[f"임무정보_{situation_id}"]))
            elif "THR" in situation_id or "THREAT" in situation_id:
                # Threat ID인 경우 -> 시나리오를 통해 Mission 찾기
                normalized_id = situation_id.replace("THREAT", "THR")
                threat_uri_candidates = [
                    URIRef(ns[f"위협상황_{situation_id}"]), 
                    URIRef(ns[f"위협상황_{normalized_id}"])
                ]
                
                for threat_node in threat_uri_candidates:
                    # 1. Threat Node에서 직접 임무 정보 확인 (위협상황.관련임무ID 매핑)
                    for mission in ontology_manager.graph.objects(threat_node, ns.has임무정보):
                        target_mission_nodes.append(mission)
                    
                    # 2. 시나리오(Scenario)를 통해 Mission 찾기
                    # ?scenario ns:has위협상황 ?threat_node
                    for scenario in ontology_manager.graph.subjects(ns.has위협상황, threat_node):
                        # ?scenario ns:has임무정보 ?mission
                        for mission in ontology_manager.graph.objects(scenario, ns.has임무정보):
                            target_mission_nodes.append(mission)
            
            # Mission Node에서 임무종류/임무유형 추출
            for mission_node in target_mission_nodes:
                # ns:임무종류, ns:missionType 등 조회
                for p, o in ontology_manager.graph.predicate_objects(mission_node):
                    pred_name = str(p).split('#')[-1]
                    if pred_name in ['임무종류', '임무유형', 'missionType']:
                        m_type = str(o)
                        safe_print(f"[INFO] 온톨로지에서 임무 유형 추출 성공: {m_type}", logger_name="ReasoningEngine")
                        return m_type
                        
        except Exception as e:
            from common.utils import safe_print
            safe_print(f"[WARN] 임무 유형 추출 오류: {e}", logger_name="ReasoningEngine")
            
        return None

    def _get_unit_properties(self, unit_uri: str, ontology_manager) -> Dict:
        """
        부대/자산의 속성 조회 (헬퍼 메서드)
        
        Returns:
            속성 딕셔너리 (병종, 제대, 부대명, 자산종류 등)
        """
        props = {}
        try:
            # [REFACTORED] SPARQL 대신 graph.triples() 사용
            from rdflib import RDF, RDFS, URIRef
            
            # 타입 확인
            types = [str(o) for s, p, o in ontology_manager.graph.triples((URIRef(unit_uri), RDF.type, None))]
            
            is_asset = any('아군가용자산' in t for t in types)
            is_unit = any('아군부대현황' in t for t in types)
            is_legacy_resource = any('가용자원' in t for t in types) or any('AvailableResource' in t for t in types)
            
            node = URIRef(unit_uri)
            ns = ontology_manager.ns
            
            # 모든 라벨 수집 (중복 라벨 처리)
            labels = []
            for s, p, o in ontology_manager.graph.triples((node, RDFS.label, None)):
                labels.append(str(o))
            combined_label = ", ".join(labels) if labels else ""
            
            if is_asset:
                props = {'type': 'asset', '부대명': combined_label, '자산명': combined_label}
                # 자산종류
                for s, p, o in ontology_manager.graph.triples((node, ns.자산종류, None)):
                    props['자산종류'] = str(o)
            elif is_unit:
                props = {'type': 'unit', '부대명': combined_label}
                # 병종
                for s, p, o in ontology_manager.graph.triples((node, ns.병종, None)):
                    props['병종'] = str(o)
                # 제대
                for s, p, o in ontology_manager.graph.triples((node, ns.제대, None)):
                    props['제대'] = str(o)
                # 부대유형
                for s, p, o in ontology_manager.graph.triples((node, ns.부대유형, None)):
                    props['부대유형'] = str(o)
                # 전투력
                for s, p, o in ontology_manager.graph.triples((node, ns.전투력, None)):
                    props['전투력'] = str(o)
                # 사기
                for s, p, o in ontology_manager.graph.triples((node, ns.사기, None)):
                    props['사기'] = str(o)
            elif is_legacy_resource:
                props = {'type': 'legacy_resource', '부대명': combined_label, '병종': combined_label, '자산종류': combined_label}
                # 추가 정보가 있으면 수집
                for s, p, o in ontology_manager.graph.triples((node, ns.비고, None)):
                    props['비고'] = str(o)
        except Exception:
            pass
        
        return props
    
    def _match_by_attributes(self, required_concept: str, unit_props: Dict) -> bool:
        """
        속성 기반 매칭 (개선: 더 유연한 매칭 규칙)
        """
        if not unit_props:
            return False
        
        concept_lower = required_concept.lower()
        unit_type = str(unit_props.get('병종', unit_props.get('자산종류', ''))).lower()
        unit_level = str(unit_props.get('제대', '')).lower()
        unit_name = str(unit_props.get('부대명', unit_props.get('자산명', ''))).lower()
        unit_category = str(unit_props.get('부대유형', '')).lower()
        
        # 전체 텍스트 (모든 속성 결합)
        full_text = f"{unit_type} {unit_level} {unit_name} {unit_category}".strip()
        
        # 개선된 매칭 규칙: 제대 정보가 없어도 병종만으로 매칭 가능
        matching_rules = {
            '포병대대': lambda t, l, n, c, f: ('포병' in t or '포' in t) and (('대대' in l or '포병' in l) or l == ''),
            '포병여단': lambda t, l, n, c, f: ('포병' in t or '포' in t) and (('여단' in l or '포병' in l) or l == ''),
            '자주포대대': lambda t, l, n, c, f: ('자주포' in t or '포' in t) and (('대대' in l or '포' in l) or l == ''),
            '전차대대': lambda t, l, n, c, f: ('전차' in t or '기갑' in t) and (('대대' in l or '전차' in l or '기갑' in l) or l == ''),
            '보병여단': lambda t, l, n, c, f: ('보병' in t or '보' in t) and (('여단' in l or '보병' in l) or l == ''),
            '보병대대': lambda t, l, n, c, f: ('보병' in t or '보' in t) and (('대대' in l or '보병' in l) or l == ''),
            '기계화보병': lambda t, l, n, c, f: ('기계화' in t or '기계화보병' in t or '기보' in t) or ('기계화' in n or '기보' in n),
            '공병대대': lambda t, l, n, c, f: ('공병' in t or '공' in t) and (('대대' in l or '공병' in l) or l == ''),
            '기갑대대': lambda t, l, n, c, f: ('기갑' in t or '전차' in t or '기갑' in n) and (('대대' in l or '기갑' in l) or l == ''),
            '방공대대': lambda t, l, n, c, f: ('방공' in t or '방공' in n) and (('대대' in l or '방공' in l) or l == ''),
            '대전차미사일': lambda t, l, n, c, f: '대전차' in t or '미사일' in t or '대전차' in n or '미사일' in n or '대전차' in f,
            '공격헬기': lambda t, l, n, c, f: '헬기' in t or '헬기' in n or '공격헬기' in n or '헬기' in f,
            '전투기': lambda t, l, n, c, f: '전투기' in t or '전투기' in n or '항공' in t or '전투기' in f,
            '전자전부대': lambda t, l, n, c, f: '전자전' in t or '전자전' in n or '전자전' in f,
            '사이버전팀': lambda t, l, n, c, f: '사이버' in t or '사이버' in n or '사이버' in f or '전자전' in t,
            'psyops팀': lambda t, l, n, c, f: '심리전' in t or '심리전' in n or 'psyo' in f.lower() or '심리' in f,
        }
        
        # 규칙 기반 매칭
        for pattern, match_func in matching_rules.items():
            if pattern in concept_lower:
                if match_func(unit_type, unit_level, unit_name, unit_category, full_text):
                    return True
        
        # 키워드 기반 부분 매칭 (개선: 더 유연한 매칭)
        concept_keywords = set(concept_lower.replace('대대', '').replace('여단', '').replace('사단', '').split())
        unit_keywords = set(full_text.split())
        
        # 공통 키워드가 있으면 매칭
        if concept_keywords & unit_keywords:
            # 핵심 키워드 매칭 (포병, 보병, 기갑 등)
            core_keywords = {'포병', '보병', '기갑', '공병', '방공', '대전차', '헬기', '전투기', '전자전', '사이버', '심리전'}
            if concept_keywords & core_keywords & unit_keywords:
                return True
        
        # 부분 문자열 매칭
        if (concept_lower in full_text or 
            any(keyword in full_text for keyword in concept_keywords if len(keyword) > 1)):
            return True
        
        return False
    
    def _match_by_hierarchy(self, required_concept: str, unit_props: Dict) -> bool:
        """
        계층 매칭 (개선): 부대 계층 구조 활용
        예: 포병대대 -> 포병여단 (상위 계층), 포병중대 (하위 계층)
        """
        if not unit_props:
            return False
        
        concept_lower = required_concept.lower()
        unit_type = str(unit_props.get('병종', unit_props.get('자산종류', ''))).lower()
        unit_level = str(unit_props.get('제대', '')).lower()
        unit_name = str(unit_props.get('부대명', unit_props.get('자산명', ''))).lower()
        full_text = f"{unit_type} {unit_level} {unit_name}".strip()
        
        # 확장된 계층 매칭 규칙
        hierarchy_rules = {
            # 포병 계층
            '포병대대': ['포병여단', '포병사단', '포병', '자주포'],
            '포병여단': ['포병사단', '포병', '포병대대'],
            '자주포대대': ['포병여단', '포병사단', '포병', '자주포'],
            '포병': ['포병대대', '포병여단', '포병사단', '자주포대대'],
            # 보병 계층
            '보병대대': ['보병여단', '보병사단', '보병', '기계화보병'],
            '보병여단': ['보병사단', '보병', '보병대대'],
            '기계화보병': ['보병여단', '보병사단', '보병'],
            '보병': ['보병대대', '보병여단', '보병사단', '기계화보병'],
            # 기갑 계층
            '기갑대대': ['기갑여단', '기갑사단', '기갑', '전차'],
            '기갑여단': ['기갑사단', '기갑', '전차'],
            '전차대대': ['기갑여단', '기갑사단', '기갑', '전차'],
            '기갑': ['기갑대대', '기갑여단', '기갑사단', '전차대대'],
            '전차': ['기갑대대', '기갑여단', '기갑사단', '전차대대'],
        }
        
        for pattern, hierarchy in hierarchy_rules.items():
            if pattern in concept_lower:
                # 개념이 계층에 포함되는지 확인
                if any(h in full_text for h in hierarchy):
                    return True
                # 부대가 개념의 계층에 포함되는지 확인
                if pattern in full_text:
                    return True
        
        # [NEW] Fallback: 계층 매칭 실패 시 리터럴 문자열 포함 여부 확인
        if concept_lower in full_text:
            return True
            
        return False
    
    def _calculate_semantic_similarity(self, required_concept: str, unit_props: Dict) -> float:
        """
        의미 유사도 계산 (NEW): 간단한 키워드 기반 유사도
        향후 NLP 모델로 확장 가능
        """
        if not unit_props:
            return 0.0
        
        concept_lower = required_concept.lower()
        unit_type = unit_props.get('병종', unit_props.get('자산종류', '')).lower()
        unit_level = unit_props.get('제대', '').lower()
        unit_name = unit_props.get('부대명', unit_props.get('자산명', '')).lower()
        
        # 공통 키워드 추출
        concept_words = set(concept_lower.split())
        unit_words = set((unit_type + ' ' + unit_level + ' ' + unit_name).split())
        
        # 공통 키워드 비율
        common_words = concept_words & unit_words
        if len(concept_words) > 0:
            similarity = len(common_words) / len(concept_words)
        else:
            similarity = 0.0
        
        return similarity
    
    def _match_resource_concept_to_unit_enhanced(
        self, 
        required_concept: str, 
        available_unit_uri: str, 
        ontology_manager,
        debug: bool = False
    ) -> tuple:
        """
        팔란티어 방식: 다층 매칭 + 신뢰도 점수
        
        Args:
            required_concept: 필요한 자원 개념
            available_unit_uri: 가용 부대/자산 URI
            ontology_manager: 온톨로지 매니저
            debug: 디버깅 모드 (상세 로그 출력)
        
        Returns:
            (매칭 여부, 신뢰도 점수 0.0~1.0)
        """
        match_score = 0.0
        match_reasons = []
        
        # 1. 직접 매칭 (신뢰도 1.0)
        required_concept_clean = required_concept.split('#')[-1] if '#' in required_concept else required_concept
        available_unit_clean = available_unit_uri.split('#')[-1] if '#' in available_unit_uri else available_unit_uri
        
        if required_concept_clean.lower() in available_unit_clean.lower():
            if debug:
                match_reasons.append(f"직접 매칭: '{required_concept_clean}' in '{available_unit_clean}'")
            return (True, 1.0)
        
        # 2. 속성 매칭 (신뢰도 0.8)
        unit_props = self._get_unit_properties(available_unit_uri, ontology_manager)
        if unit_props and self._match_by_attributes(required_concept_clean, unit_props):
            match_score = max(match_score, 0.8)
            if debug:
                match_reasons.append(f"속성 매칭: unit_props={unit_props}")
        
        # 3. 계층 매칭 (신뢰도 0.6)
        if unit_props and self._match_by_hierarchy(required_concept_clean, unit_props):
            match_score = max(match_score, 0.6)
            if debug:
                match_reasons.append(f"계층 매칭: unit_props={unit_props}")
        
        # 4. 유사도 매칭 (신뢰도 0.4)
        if unit_props:
            similarity = self._calculate_semantic_similarity(required_concept_clean, unit_props)
            if similarity > 0.5:  # 임계값을 0.7에서 0.5로 낮춤
                match_score = max(match_score, 0.4 * similarity)
                if debug:
                    match_reasons.append(f"유사도 매칭: similarity={similarity:.2f}")
        
        # 디버깅 정보 출력 (🔥 최적화: 첫 번째 COA에서만 출력)
        # if debug and match_score == 0.0:
        #     from common.utils import safe_print
        #     safe_print(f"[DEBUG] 매칭 실패: required='{required_concept_clean}', unit='{available_unit_clean}', unit_props={unit_props}", logger_name="ReasoningEngine")
        if debug and match_score > 0.0:
            from common.utils import safe_print
            safe_print(f"[DEBUG] 매칭 성공: required='{required_concept_clean}', score={match_score:.2f}, reasons={match_reasons}", logger_name="ReasoningEngine")
        
        return (match_score > 0.0, match_score)
    
    def _match_resource_concept_to_unit(self, required_concept: str, available_unit_uri: str, ontology_manager) -> bool:
        """
        개념적 자원과 실제 부대 인스턴스 또는 아군가용자산 매칭
        
        Args:
            required_concept: 필요한 자원 개념 (예: "포병대대", "보병여단")
            available_unit_uri: 가용 부대/자산 URI (예: "ns:아군부대현황_FRU006" 또는 "ns:아군가용자산_AST001")
            ontology_manager: 온톨로지 매니저
        
        Returns:
            매칭 여부 (True/False)
        """
        try:
            # 🔥 개선: 아군가용자산과 아군부대현황 모두 지원
            # 먼저 타입 확인
            from rdflib import RDF, URIRef
            node = URIRef(available_unit_uri)
            types = [str(o) for o in ontology_manager.graph.objects(node, RDF.type)]
            
            is_asset = any('아군가용자산' in t for t in types)
            is_unit = any('아군부대현황' in t for t in types)
            is_allocation = any('임무별_자원할당' in t for t in types)
            
            # 1. 임무별_자원할당인 경우: tactical_role 속성 활용 (최우선)
            if is_allocation:
                ns = ontology_manager.ns
                tactical_role = ""
                for o in ontology_manager.graph.objects(node, ns.tactical_role):
                    tactical_role = str(o).lower()
                
                if tactical_role:
                    concept_lower = required_concept.lower()
                    if concept_lower in tactical_role or tactical_role in concept_lower:
                        return True
                    
                    # 전술적 역할 기반 매칭 (예: "화력지원" -> "포병")
                    role_matching = {
                        '화력지원': ['포병', '공충', '항공', '화력'],
                        '충격군': ['기갑', '전차', '기계화'],
                        '기동차단': ['보병', '공병', '차단'],
                        '정찰감시': ['정찰', '드론', '감시']
                    }
                    for role, keywords in role_matching.items():
                        if role in tactical_role:
                            if any(kw in concept_lower for kw in keywords):
                                return True

            # 2. 아군가용자산인 경우: 자산종류 속성 활용
            if is_asset:
                ns = ontology_manager.ns
                from rdflib import RDFS
                asset_type = ""
                for o in ontology_manager.graph.objects(node, ns.자산종류):
                    asset_type = str(o).lower()
                asset_name = ""
                for o in ontology_manager.graph.objects(node, RDFS.label):
                    asset_name = str(o).lower()
                
                if asset_type or asset_name:
                    concept_lower = required_concept.lower()
                    
                    # 자산종류 기반 매칭 규칙
                    asset_matching_rules = {
                        '포병대대': lambda t, n: '포병' in t or '포' in t or '포병' in n,
                        '포병여단': lambda t, n: '포병' in t or '포' in t or '포병' in n,
                        '보병여단': lambda t, n: '보병' in t or '보' in t or '보병' in n,
                        '보병대대': lambda t, n: '보병' in t or '보' in t or '보병' in n,
                        '공병대대': lambda t, n: '공병' in t or '공' in t or '공병' in n,
                        '기갑대대': lambda t, n: '기갑' in t or '전차' in t or '기갑' in n,
                        '방공대대': lambda t, n: '방공' in t or '방공' in n,
                        '대전차미사일': lambda t, n: '대전차' in t or '미사일' in t or '대전차' in n or '미사일' in n,
                        '공격헬기': lambda t, n: '헬기' in t or '헬기' in n or '공격헬기' in n,
                        '전투기': lambda t, n: '전투기' in t or '전투기' in n or '항공' in t,
                    }
                    
                    # 규칙 기반 매칭
                    for concept_pattern, match_func in asset_matching_rules.items():
                        if concept_pattern in concept_lower:
                            if match_func(asset_type, asset_name):
                                return True
                    
                    # 부분 매칭
                    if (required_concept.lower() in asset_type or 
                        required_concept.lower() in asset_name or
                        any(keyword in asset_type for keyword in required_concept.lower().split())):
                        return True
            
            # 아군부대현황인 경우: 기존 로직 사용
            if is_unit:
                ns = ontology_manager.ns
                from rdflib import RDFS
                unit_type = ""
                for o in ontology_manager.graph.objects(node, ns.병종):
                    unit_type = str(o).lower()
                unit_level = ""
                for o in ontology_manager.graph.objects(node, ns.제대):
                    unit_level = str(o).lower()
                unit_name = ""
                for o in ontology_manager.graph.objects(node, RDFS.label):
                    unit_name = str(o).lower()
                unit_category = ""
                for o in ontology_manager.graph.objects(node, ns.부대유형):
                    unit_category = str(o).lower()
                
                if unit_type or unit_level or unit_name or unit_category:
                    concept_lower = required_concept.lower()
                    
                    # 매칭 규칙 정의
                    matching_rules = {
                        '포병대대': lambda t, l, n, c: ('포병' in t or '포' in t) and ('대대' in l or '포병' in l or '포' in l),
                        '포병여단': lambda t, l, n, c: ('포병' in t or '포' in t) and ('여단' in l or '포병' in l),
                        '보병여단': lambda t, l, n, c: ('보병' in t or '보' in t) and ('여단' in l or '보병' in l),
                        '보병대대': lambda t, l, n, c: ('보병' in t or '보' in t) and ('대대' in l or '보병' in l),
                        '공병대대': lambda t, l, n, c: ('공병' in t or '공' in t) and ('대대' in l or '공병' in l),
                        '기갑대대': lambda t, l, n, c: ('기갑' in t or '전차' in t or '기갑' in n) and ('대대' in l or '기갑' in l),
                        '방공대대': lambda t, l, n, c: ('방공' in t or '방공' in n) and ('대대' in l or '방공' in l),
                        '대전차미사일': lambda t, l, n, c: '대전차' in t or '미사일' in t or '대전차' in n or '미사일' in n,
                        '공격헬기': lambda t, l, n, c: '헬기' in t or '헬기' in n or '공격헬기' in n,
                        '전투기': lambda t, l, n, c: '전투기' in t or '전투기' in n or '항공' in t,
                    }
                    
                    # 규칙 기반 매칭
                    for concept_pattern, match_func in matching_rules.items():
                        if concept_pattern in concept_lower:
                            if match_func(unit_type, unit_level, unit_name, unit_category):
                                return True
                    
                    # 부분 매칭 (백업)
                    if (required_concept.lower() in unit_type or 
                        required_concept.lower() in unit_level or 
                        required_concept.lower() in unit_name or
                        any(keyword in unit_type for keyword in required_concept.lower().split()) or
                        any(keyword in unit_level for keyword in required_concept.lower().split())):
                        return True
            
            return False
            
        except Exception as e:
            # 매칭 실패 시 False 반환 (에러 로그는 상위에서 처리)
            return False
    
    def _calculate_resource_quality(self, available_resources: List[str], ontology_manager) -> float:
        """
        자원 품질 점수 계산 (전투력, 사기, 상태 반영)
        팔란티어 방식: 자원의 품질을 반영하여 매칭 점수 조정
        """
        if not available_resources or not ontology_manager:
            return 0.5  # 정보 없으면 중립
        
        total_quality = 0.0
        count = 0
        
        for resource_uri in available_resources:
            try:
                # 전투력 조회
                from rdflib import URIRef
                node = URIRef(resource_uri)
                ns = ontology_manager.ns
                combat_power_list = [str(o) for o in ontology_manager.graph.objects(node, ns.전투력)]
                
                # 사기 조회
                morale_list = [str(o) for o in ontology_manager.graph.objects(node, ns.사기)]
                
                # 품질 점수 계산 (전투력 70%, 사기 30%)
                power_score = 0.5
                if combat_power_list:
                    try:
                        power_val = float(combat_power_list[0])
                        power_score = power_val / 100.0 if power_val <= 100 else 1.0
                    except (ValueError, TypeError):
                        pass
                
                morale_score = 0.5
                if morale_list:
                    try:
                        morale_val = float(morale_list[0])
                        morale_score = morale_val / 100.0 if morale_val <= 100 else 1.0
                    except (ValueError, TypeError):
                        pass
                
                quality = (power_score * 0.7) + (morale_score * 0.3)
                total_quality += quality
                count += 1
            except Exception:
                # 조회 실패 시 기본값 사용
                total_quality += 0.5
                count += 1
        
        return total_quality / count if count > 0 else 0.5
    
    def _find_alternative_resources(self, required_resource_uri: str, context: Dict) -> List[str]:
        """
        대체 자원 찾기 (팔란티어 방식)
        
        예: 포병대대 -> 포병여단, 포병사단 (상위 계층)
        예: 보병여단 -> 보병대대, 보병사단 (계층 내)
        """
        ontology_manager = context.get('ontology_manager')
        if not ontology_manager:
            return []
        
        # 필요한 자원의 개념 추출
        required_concept = required_resource_uri.split('#')[-1] if '#' in required_resource_uri else required_resource_uri
        required_concept_lower = required_concept.lower()
        
        alternatives = []
        
        # 계층 기반 대체 자원 찾기
        hierarchy_map = {
            '포병대대': ['포병여단', '포병사단', '포병'],
            '포병여단': ['포병대대', '포병사단', '포병'],
            '포병': ['포병대대', '포병여단', '포병사단'],
            '보병대대': ['보병여단', '보병사단', '보병'],
            '보병여단': ['보병대대', '보병사단', '보병'],
            '보병': ['보병대대', '보병여단', '보병사단'],
            '기갑대대': ['기갑여단', '기갑사단', '기갑'],
            '기갑여단': ['기갑대대', '기갑사단', '기갑'],
            '기갑': ['기갑대대', '기갑여단', '기갑사단'],
            '공병대대': ['공병여단', '공병사단', '공병'],
            '방공대대': ['방공여단', '방공사단', '방공'],
        }
        
        # 대체 자원 개념 찾기
        alt_concepts = []
        for pattern, hierarchy in hierarchy_map.items():
            if pattern in required_concept_lower:
                alt_concepts.extend(hierarchy)
                break
        
        # 대체 자원 URI 찾기
        if alt_concepts:
            for alt_concept in alt_concepts:
                # 온톨로지에서 대체 자원 검색
                try:
                    from rdflib import RDF, URIRef
                    ns = ontology_manager.ns
                    # 아군부대현황 및 아군가용자산 탐색
                    found_resources = []
                    
                    # ns:아군부대현황 타입인 자산 중 병종이 alt_concept을 포함하는 것
                    for s, p, o in ontology_manager.graph.triples((None, RDF.type, ns.아군부대현황)):
                        for type_val in ontology_manager.graph.objects(s, ns.병종):
                            if alt_concept.lower() in str(type_val).lower():
                                found_resources.append(str(s))
                    
                    # ns:아군가용자산 타입인 자산 중 자산종류가 alt_concept을 포함하는 것
                    for s, p, o in ontology_manager.graph.triples((None, RDF.type, ns.아군가용자산)):
                        for type_val in ontology_manager.graph.objects(s, ns.자산종류):
                            if alt_concept.lower() in str(type_val).lower():
                                found_resources.append(str(s))
                    
                    for resource_uri in found_resources[:10]:
                        if resource_uri and resource_uri not in alternatives:
                            alternatives.append(resource_uri)
                except Exception:
                    pass
        
        return alternatives
    
    def _extract_asset_capability(self, context: Dict) -> float:
        """방어 자산 능력 추출"""
        defense_assets = context.get("defense_assets", [])
        graph = context.get("graph")
        ontology_manager = context.get("ontology_manager")
        
        if defense_assets:
            if isinstance(defense_assets, list) and len(defense_assets) > 0:
                # 리스트에서 평균 계산
                firepowers = []
                for asset in defense_assets:
                    if isinstance(asset, dict):
                        if 'firepower' in asset:
                            firepowers.append(float(asset['firepower']))
                    elif isinstance(asset, (int, float)):
                        firepowers.append(float(asset))
                
                if firepowers:
                    avg = sum(firepowers) / len(firepowers)
                    return min(1.0, avg / 100.0)
        
        # 그래프에서 아군 정보 추출
        if graph is not None and ontology_manager is not None:
            try:
                ns = ontology_manager.ns
                firepowers = []
                morales = []
                
                # 모든 유닛의 전투력과 사기 조회
                for s, p, o in graph.triples((None, ns.전투력, None)):
                    try:
                        firepowers.append(float(str(o)))
                    except:
                        pass
                for s, p, o in graph.triples((None, ns.사기, None)):
                    try:
                        morales.append(float(str(o)))
                    except:
                        pass
                
                if firepowers:
                    avg_firepower = sum(firepowers) / len(firepowers)
                    return min(1.0, avg_firepower / 100.0)
                elif morales:
                    avg_morale = sum(morales) / len(morales)
                    return min(1.0, avg_morale / 100.0)
            except Exception:
                pass
        
        return 0.5  # 기본값
    
    def _extract_environment_fit(self, context: Dict) -> float:
        """환경 적합성 추출 (기상상황, 지형 정보 활용, 로깅 및 검증 강화)"""
        ontology_manager = context.get("ontology_manager")
        situation_id = context.get("situation_id")
        coa_uri = context.get("coa_uri")  # 실제 COA URI 사용
        
        # 직접 제공된 환경 적합성 사용
        if "environment_fit" in context:
            return float(context["environment_fit"])
        
        if not ontology_manager or not hasattr(ontology_manager, 'execute_template_query'):
            from common.utils import safe_print
            safe_print("[WARN] OntologyManager 또는 execute_template_query 메서드가 없습니다. 기본값(0.5) 사용", logger_name="ReasoningEngine")
            return 0.5
        
        if not situation_id:
            situation_id = "THREAT001"  # 기본값
            from common.utils import safe_print
            safe_print(f"[INFO] situation_id가 없어 기본값 사용: {situation_id}", logger_name="ReasoningEngine")
        
        try:
            from common.utils import safe_print
            if context.get('is_first_coa', False):
                safe_print(f"[INFO] 환경 적합성 조회: COA={coa_uri}, Situation={situation_id}", logger_name="ReasoningEngine")
            
            # URI 파싱: 전체 URI가 전달되면 그대로 사용, ID만 전달되면 URI 생성
            if situation_id.startswith("http://"):
                situation_uri_for_query = situation_id
            else:
                # ID만 전달된 경우 URI 생성
                situation_uri_for_query = f"http://coa-agent-platform.org/ontology#{situation_id}"
            
            # 1. 위협상황의 기상상황 조회 (개선: 위치 기반 조회)
            from rdflib import RDF, URIRef
            ns = ontology_manager.ns
            situation_node = URIRef(situation_uri_for_query)
            
            weather_results = []
            # 먼저 직접 연결된 환경 정보 조회 시도 (ns:occursInEnvironment)
            for weather_node in ontology_manager.graph.objects(situation_node, ns.occursInEnvironment):
                weather_data = {'weather': str(weather_node)}
                for state in ontology_manager.graph.objects(weather_node, ns.상태):
                    weather_data['weather_state'] = str(state)
                weather_results.append(weather_data)
            
            # 직접 연결이 없으면 위치 기반으로 기상상황 테이블 조회
            if not weather_results:
                for location_node in ontology_manager.graph.objects(situation_node, ns.has지형셀):
                    # ns:has지형셀이 location_node인 기상상황(ns:기상상황) 찾기
                    for s, p, o in ontology_manager.graph.triples((None, ns.has지형셀, location_node)):
                        if (s, RDF.type, ns.기상상황) in ontology_manager.graph:
                            weather_data = {'weather': str(s)}
                            for state in ontology_manager.graph.objects(s, ns.기상유형):
                                weather_data['weather_state'] = str(state)
                            weather_results.append(weather_data)
            # 🔥 로그 최적화: 반복되는 DEBUG 로그 제거 (각 COA마다 호출되므로)
            # safe_print(f"[DEBUG] 기상상황 조회 결과: {len(weather_results)}개", logger_name="ReasoningEngine")
            
            # 2. COA의 환경 호환성 조회
            if coa_uri:
                # URI 파싱: 전체 URI가 전달되면 그대로 사용, ID만 전달되면 URI 생성
                if coa_uri.startswith("http://"):
                    coa_uri_for_query = coa_uri
                else:
                    # ID만 전달된 경우 URI 생성
                    coa_uri_for_query = f"http://coa-agent-platform.org/ontology#{coa_uri}"
                
                coa_node = URIRef(coa_uri_for_query)
                compatibility_results = []
                for env_node in ontology_manager.graph.objects(coa_node, ns.compatibleWith):
                    comp_data = {'env': str(env_node)}
                    for score in ontology_manager.graph.objects(coa_node, ns.compatibilityScore):
                        comp_data['compatibility'] = str(score)
                    compatibility_results.append(comp_data)
                # 🔥 로그 최적화: 반복되는 DEBUG 로그 제거 (각 COA마다 호출되므로)
                # safe_print(f"[DEBUG] 환경 호환성 조회 결과: {len(compatibility_results)}개", logger_name="ReasoningEngine")
                
                # 3. 팔란티어 방식: 다차원 환경 평가 (개선)
                # 현재 환경 정보 조회
                current_env = self._get_current_environment(situation_uri_for_query, ontology_manager)
                
                # [NEW] 컨텍스트에서 직접 제공된 환경 정보로 오버라이드 (UI 입력 우선)
                if 'weather' in context and context['weather']:
                    current_env['기상'] = context['weather']
                    if context.get('is_first_coa', False):
                        safe_print(f"[INFO] 환경 정보 오버라이드: 기상 -> {context['weather']}", logger_name="ReasoningEngine")
                if 'terrain' in context and context['terrain']:
                    current_env['지형'] = context['terrain']
                    if context.get('is_first_coa', False):
                        safe_print(f"[INFO] 환경 정보 오버라이드: 지형 -> {context['terrain']}", logger_name="ReasoningEngine")
                if 'time_of_day' in context and context['time_of_day']:
                    current_env['시간'] = context['time_of_day']
                
                # 기상 유형 추출 (기상유형 컬럼 사용)
                weather_types = []
                for w in weather_results:
                    weather_state = w.get('weather_state', '')
                    if weather_state:
                        weather_types.append(str(weather_state))
                    # weather_state가 없으면 weather URI에서 추출
                    weather_uri = str(w.get('weather', ''))
                    if weather_uri and not weather_state:
                        weather_label = weather_uri.split('#')[-1] if '#' in weather_uri else weather_uri
                        weather_types.append(weather_label)
                
                if weather_types:
                    current_env['기상'] = weather_types[0]  # 첫 번째 기상 유형 사용
                
                # 환경 점수 계산 (기본값 0.5)
                score = 0.5
                match_found = False
                
                # 호환 환경 매칭 (+0.2 per match, 최대 +0.4)
                compatible_envs = []
                for c in compatibility_results:
                    env_uri = c.get('env', '')
                    if env_uri:
                        # URI에서 환경 이름 추출
                        env_name = str(env_uri).split('#')[-1] if '#' in str(env_uri) else str(env_uri)
                        compatible_envs.append(env_name.lower())
                
                compatible_match_count = 0
                for env in compatible_envs:
                    env_lower = env
                    # 현재 환경과 매칭 확인 (더 유연한 매칭)
                    for env_key, env_value in current_env.items():
                        if env_value and env_lower in str(env_value).lower():
                            score += 0.2
                            compatible_match_count += 1
                            match_found = True
                            if context.get('is_first_coa', False):
                                safe_print(f"[INFO] 환경 호환 매칭: '{env}' <-> '{env_value}' (+0.2)", logger_name="ReasoningEngine")
                            break
                    # 기상 유형과 직접 매칭
                    if weather_types and any(env_lower in wt.lower() for wt in weather_types):
                        score += 0.2
                        compatible_match_count += 1
                        match_found = True
                        if context.get('is_first_coa', False):
                            safe_print(f"[INFO] 환경 호환 매칭: '{env}' <-> 기상 '{weather_types[0]}' (+0.2)", logger_name="ReasoningEngine")
                
                # 최대 +0.4로 제한
                if compatible_match_count > 2:
                    score = 0.5 + 0.4
                else:
                    score = min(1.0, score)
                
                # 비호환 환경 확인
                incompatible_results = []
                for env_node in ontology_manager.graph.objects(coa_node, ns.incompatibleWith):
                    incompatible_results.append({'env': str(env_node)})
                incompatible_envs = []
                for i in incompatible_results:
                    env_uri = i.get('env', '')
                    if env_uri:
                        env_name = str(env_uri).split('#')[-1] if '#' in str(env_uri) else str(env_uri)
                        incompatible_envs.append(env_name.lower())
                
                # 비호환 환경 매칭 (-0.3 per match, 최대 -0.6)
                incompatible_match_count = 0
                for env in incompatible_envs:
                    env_lower = env
                    # 현재 환경과 매칭 확인
                    for env_key, env_value in current_env.items():
                        if env_value and env_lower in str(env_value).lower():
                            score -= 0.3
                            incompatible_match_count += 1
                            match_found = True
                            if context.get('is_first_coa', False):
                                safe_print(f"[INFO] 환경 비호환 매칭: '{env}' <-> '{env_value}' (-0.3)", logger_name="ReasoningEngine")
                            break
                    # 기상 유형과 직접 매칭
                    if weather_types and any(env_lower in wt.lower() for wt in weather_types):
                        score -= 0.3
                        incompatible_match_count += 1
                        match_found = True
                        if context.get('is_first_coa', False):
                            safe_print(f"[INFO] 환경 비호환 매칭: '{env}' <-> 기상 '{weather_types[0]}' (-0.3)", logger_name="ReasoningEngine")
                
                # 최대 -0.6로 제한
                if incompatible_match_count > 2:
                    score = max(0.0, score - 0.6)
                
                # 기상 정보가 있지만 COA 호환성 정보가 없는 경우 기본 점수 부여
                if not match_found and weather_types:
                    # 악천후, 안개는 낮은 점수, 맑음은 높은 점수
                    if any('악천후' in wt or '안개' in wt for wt in weather_types):
                        score = 0.4
                        if context.get('is_first_coa', False):
                            safe_print(f"[INFO] 기상 정보 기반 점수: 악천후/안개 → 0.4", logger_name="ReasoningEngine")
                    elif any('야간' in wt for wt in weather_types):
                        score = 0.6
                        if context.get('is_first_coa', False):
                            safe_print(f"[INFO] 기상 정보 기반 점수: 야간 → 0.6", logger_name="ReasoningEngine")
                    elif any('맑음' in wt for wt in weather_types):
                        score = 0.8
                        if context.get('is_first_coa', False):
                            safe_print(f"[INFO] 기상 정보 기반 점수: 맑음 → 0.8", logger_name="ReasoningEngine")
                
                # 최종 점수 반환
                return min(1.0, max(0.0, score))
            else:
                # COA URI가 없으면 환경 기반 적합 COA 조회
                from rdflib import URIRef
                situation_node = URIRef(situation_id if situation_id.startswith('http') else f"http://coa-agent-platform.org/ontology#{situation_id}")
                ns = ontology_manager.ns
                
                # find_coas_by_environment 템플릿 로직 구현
                # ?situation ns:occursInEnvironment ?weather .
                # ?situation ns:occursInEnvironment ?terrain .
                # ?coa ns:compatibleWith ?weather .
                # ?coa ns:compatibleWith ?terrain .
                env_nodes = list(ontology_manager.graph.objects(situation_node, ns.occursInEnvironment))
                suitable_coas = set()
                if env_nodes:
                    # 모든 환경 요소에 호환되는 COA 찾기 (단순화: 하나라도 호환되면 포함)
                    for env in env_nodes:
                        for coa_node, p, o in ontology_manager.graph.triples((None, ns.compatibleWith, env)):
                            suitable_coas.add(coa_node)
                
                # 환경 호환 COA가 있으면 1.0, 없으면 0.5
                return 1.0 if suitable_coas else 0.5
        except Exception as e:
            from common.utils import safe_print
            safe_print(f"[WARN] Environment fit extraction failed: {e}", logger_name="ReasoningEngine")
            import traceback
            traceback.print_exc()
        
        return 0.5  # 기본값
    
    def _get_current_environment(self, situation_uri: str, ontology_manager) -> Dict:
        """
        현재 환경 정보 조회 (기상상황 테이블 활용)
        팔란티어 방식: 다차원 환경 정보 수집
        """
        env_info = {}
        
        try:
            # 위협상황의 지형셀 조회
            from rdflib import URIRef
            ns = ontology_manager.ns
            situation_node = URIRef(situation_uri)
            terrain_results = []
            for location in ontology_manager.graph.objects(situation_node, ns.has지형셀):
                terrain_data = {'location': str(location)}
                for terrain_type in ontology_manager.graph.objects(location, ns.지형유형):
                    terrain_data['terrain_type'] = str(terrain_type)
                terrain_results.append(terrain_data)
            
            if terrain_results:
                terrain_uri = terrain_results[0].get('location')
                terrain_name = terrain_results[0].get('terrain_type', '')
                env_info['지형'] = str(terrain_name) if terrain_name else '평지'
                
                # 기상상황 조회
                weather_results = []
                for s, p, o in ontology_manager.graph.triples((None, ns.지형셀ID, URIRef(terrain_uri))):
                    for type_val in ontology_manager.graph.objects(s, ns.기상유형):
                        weather_results.append({'기상유형': str(type_val)})
                if weather_results:
                    env_info['기상'] = str(weather_results[0].get('기상유형', '맑음'))
                else:
                    env_info['기상'] = '맑음'  # 기본값
            else:
                env_info['지형'] = '평지'
                env_info['기상'] = '맑음'
            
            # 시각 및 계절 정보 (향후 확장 가능)
            from datetime import datetime
            now = datetime.now()
            hour = now.hour
            if 6 <= hour < 18:
                env_info['시각'] = '낮'
            else:
                env_info['시각'] = '야간'
            
            month = now.month
            if month in [12, 1, 2]:
                env_info['계절'] = '겨울'
            elif month in [3, 4, 5]:
                env_info['계절'] = '봄'
            elif month in [6, 7, 8]:
                env_info['계절'] = '여름'
            else:
                env_info['계절'] = '가을'
                
        except Exception:
            # 조회 실패 시 기본값
            env_info = {
                '기상': '맑음',
                '지형': '평지',
                '시각': '낮',
                '계절': '봄'
            }
        
        return env_info
    
    def _extract_historical_success(self, context: Dict) -> float:
        """과거 성공률 추출 (RAG 결과 기반)"""
        rag_results = context.get("rag_results", [])
        
        if rag_results:
            success_keywords = ['성공', '효과적', '승리', '완료', '달성']
            success_count = 0
            
            for result in rag_results:
                if isinstance(result, dict):
                    text = result.get('text', '')
                else:
                    text = str(result)
                
                if any(keyword in text for keyword in success_keywords):
                    success_count += 1
            
            if len(rag_results) > 0:
                return success_count / len(rag_results)
        
        return 0.5  # 기본값
    
    def _extract_chain_score(self, context: Dict) -> float:
        """체인 기반 점수 추출"""
        chain_info = context.get("chain_info", {})
        
        if chain_info:
            # 체인 요약에서 평균 점수 사용
            chain_summary = chain_info.get("summary", {})
            avg_score = chain_summary.get("avg_score", 0.0)
            
            # 체인 점수를 0-1 범위로 정규화
            return min(1.0, max(0.0, avg_score))
        
        return 0.5  # 기본값
    
    def run_intel_rules(self, context: Dict) -> Dict:
        """
        첩보 규칙 실행
        
        Args:
            context: 컨텍스트 딕셔너리 (intel DataFrame 등 포함 가능)
            
        Returns:
            첩보 평가 결과 딕셔너리
        """
        intel_df = context.get("intel")
        
        if intel_df is None or (isinstance(intel_df, pd.DataFrame) and intel_df.empty):
            return {
                "status": "No Intel Data",
                "TrustScore": 0.0
            }
        
        # 기본 신뢰도 계산
        if isinstance(intel_df, pd.DataFrame):
            # Reliability 또는 confidence 컬럼이 있으면 평균 계산
            if "Reliability" in intel_df.columns:
                trust_score = float(intel_df["Reliability"].mean())
            elif "confidence" in intel_df.columns:
                trust_score = float(intel_df["confidence"].mean())
            elif "신뢰도" in intel_df.columns:
                trust_score = float(intel_df["신뢰도"].mean())
            else:
                # 기본값
                trust_score = 0.75
        else:
            trust_score = 0.75
        
        # 신뢰도에 따른 상태 결정
        if trust_score > 0.8:
            status = "Reliable"
        elif trust_score > 0.5:
            status = "Moderate"
        else:
            status = "Unreliable"
        
        return {
            "TrustScore": round(trust_score, 2),
            "Status": status,
            "IntelCount": len(intel_df) if isinstance(intel_df, pd.DataFrame) else 0
        }
    
    def run_ccir_rules(self, context: Dict) -> Dict:
        """
        CCIR 추천 규칙 실행
        
        Args:
            context: 컨텍스트 딕셔너리
                - classification: 분류 결과 (PIR, FFIR, EEFI)
                - asset_recommendation: 자산 추천 결과
                - request_management: 요청 관리 결과
                - dynamic_update: 동적 갱신 결과
                - situation_id: 상황 ID
                - threat_level: 위협 수준
                
        Returns:
            CCIR 추천 결과 딕셔너리
        """
        classification = context.get("classification", {})
        asset_recommendation = context.get("asset_recommendation", {})
        request_management = context.get("request_management", {})
        dynamic_update = context.get("dynamic_update", {})
        threat_level = context.get("threat_level", 0.5)
        
        # CCIR 카테고리
        category = classification.get("category", "UNKNOWN")
        confidence = classification.get("confidence", 0.5)
        
        # 우선순위
        priority = request_management.get("priority", "MEDIUM")
        priority_score = request_management.get("priority_score", 0.5)
        
        # 추천 자산
        recommended_assets = asset_recommendation.get("recommended_assets", [])
        
        # 동적 갱신 필요 여부
        needs_update = dynamic_update.get("needs_update", False) if dynamic_update else False
        
        # 종합 평가 점수 계산
        evaluation_score = (
            confidence * 0.3 +  # 정보 품질
            priority_score * 0.25 +  # 적시성
            (len(recommended_assets) / 5.0) * 0.25 +  # 관련성 (자산 수)
            (1.0 if needs_update else 0.5) * 0.2  # 완전성 (갱신 필요 여부)
        )
        
        # 상태 결정
        if evaluation_score >= 0.8:
            status = "Excellent"
        elif evaluation_score >= 0.6:
            status = "Good"
        elif evaluation_score >= 0.4:
            status = "Moderate"
        else:
            status = "Poor"
        
        return {
            "CCIRCategory": category,
            "Confidence": round(confidence, 2),
            "Priority": priority,
            "PriorityScore": round(priority_score, 2),
            "RecommendedAssets": len(recommended_assets),
            "AssetDetails": recommended_assets[:3],  # 상위 3개만
            "NeedsUpdate": needs_update,
            "EvaluationScore": round(evaluation_score, 2),
            "Status": status,
            "ThreatLevel": threat_level,
            "Timestamp": pd.Timestamp.now().isoformat()
        }
    
    def run_custom_rules(self, context: Dict, rules: List[Dict]) -> Dict:
        """
        커스텀 규칙 실행
        
        Args:
            context: 컨텍스트 딕셔너리
            rules: 규칙 리스트 [{"condition": ..., "action": ...}]
            
        Returns:
            규칙 실행 결과
        """
        results = []
        for rule in rules:
            condition = rule.get("condition")
            action = rule.get("action")
            
            # 간단한 조건 평가 (실제로는 더 복잡한 평가 로직 필요)
            if self._evaluate_condition(condition, context):
                results.append(action)
        
        return {"applied_rules": results}
    
    def _evaluate_condition(self, condition: Dict, context: Dict) -> bool:
        """
        조건 평가 (간단한 구현)
        
        Args:
            condition: 조건 딕셔너리
            context: 컨텍스트
            
        Returns:
            조건 만족 여부
        """
        # 간단한 구현 예시
        # 실제로는 더 복잡한 조건 평가 로직 필요
        return True


    def analyze_situation_hypothesis(self, query: str, context: Optional[Dict] = None) -> List[str]:
        """
        상황 가설 분석 (Chatbot RAG 지원용)
        질문과 컨텍스트를 바탕으로 전술적 가설을 생성합니다.
        
        Args:
            query: 사용자 질문
            context: 상황 컨텍스트 (선택적)
            
        Returns:
            가설 문자열 리스트
        """
        hypotheses = []
        
        # 1. 키워드 기반 단순 가설 (Example)
        if "위협" in query or "적" in query:
            # TODO: 실제 온톨로지에서 가장 위협도가 높은 적 부대를 조회하여 동적 생성
            hypotheses.append("적 기갑부대의 접근이 예상되므로 대전차 장애물 설치와 공중 지원 요청이 효과적일 수 있습니다.")
            hypotheses.append("산악 지형을 활용한 매복 공격이 적 기동을 지연시키는 데 유리합니다.")
            
        if "방어" in query:
             hypotheses.append("현재 전력비가 열세이므로 지연 작전 후 주방어선에서 결전을 치르는 것이 교리에 부합합니다.")

        # 2. 컨텍스트 기반 가설 (날씨, 지형 등)
        if context:
            weather = context.get('weather', '')
            terrain = context.get('terrain', '')
            
            if 'rain' in str(weather).lower() or '비' in str(weather):
                 hypotheses.append("우천으로 인해 기갑 부대의 기동 속도가 70% 수준으로 감소할 것으로 판단됩니다.")
            
            if 'mountain' in str(terrain).lower() or '산' in str(terrain):
                 hypotheses.append("산악 지형은 방어자에게 유리하며, 공격자의 통신 및 관측을 제한할 수 있습니다.")
                 
        return hypotheses
