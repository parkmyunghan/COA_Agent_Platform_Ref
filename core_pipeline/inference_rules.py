# core_pipeline/inference_rules.py
# -*- coding: utf-8 -*-
"""
SWRL-Style Inference Rules Engine
전술 도메인 특화 추론 규칙 엔진

W3C SWRL(Semantic Web Rule Language) 스타일의 규칙을 정의하고 실행합니다.
OWL-RL이 처리하지 못하는 복잡한 도메인 규칙을 처리합니다.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)

# 기본 네임스페이스
NS = Namespace("http://coa-agent-platform.org/ontology#")


@dataclass
class InferenceRule:
    """추론 규칙 정의"""
    id: str
    name: str
    description: str
    condition_sparql: str  # WHERE 절에 해당하는 SPARQL 패턴
    conclusion_template: str  # 추론 결과 트리플 템플릿
    priority: str  # HIGH, MEDIUM, LOW
    category: str  # 규칙 카테고리 (tactical, resource, threat 등)
    enabled: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# 전술 도메인 추론 규칙 정의
# ═══════════════════════════════════════════════════════════════════════════

TACTICAL_RULES: List[InferenceRule] = [
    # ─────────────────────────────────────────────────────────────────────────
    # 교전 및 위협 관련 규칙
    # ─────────────────────────────────────────────────────────────────────────
    InferenceRule(
        id="RULE_ENGAGE_001",
        name="동일 지역 교전 추론",
        description="동일 지형셀에 적군과 아군이 위치하면 교전 가능 상황으로 추론",
        condition_sparql="""
            ?friendly a ns:아군부대현황 .
            ?friendly ns:locatedIn ?cell .
            ?enemy a ns:적군부대현황 .
            ?enemy ns:locatedIn ?cell .
        """,
        conclusion_template="?friendly ns:교전대상 ?enemy",
        priority="HIGH",
        category="tactical"
    ),
    
    InferenceRule(
        id="RULE_THREAT_001",
        name="위협 노출 추론",
        description="적군 부대와 동일 축선에 있는 아군은 위협에 노출됨",
        condition_sparql="""
            ?friendly a ns:아군부대현황 .
            ?friendly ns:has전장축선 ?axis .
            ?enemy a ns:적군부대현황 .
            ?enemy ns:has전장축선 ?axis .
        """,
        conclusion_template="?friendly ns:위협노출 ?enemy",
        priority="HIGH",
        category="threat"
    ),
    
    InferenceRule(
        id="RULE_THREAT_002",
        name="인접 지역 위협 추론",
        description="적군이 있는 지형셀과 인접한 지형셀의 아군도 위협에 노출됨",
        condition_sparql="""
            ?friendly a ns:아군부대현황 .
            ?friendly ns:locatedIn ?friendlyCell .
            ?friendlyCell ns:인접함 ?enemyCell .
            ?enemy a ns:적군부대현황 .
            ?enemy ns:locatedIn ?enemyCell .
        """,
        conclusion_template="?friendly ns:인접위협 ?enemy",
        priority="MEDIUM",
        category="threat"
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # 화력 지원 관련 규칙
    # ─────────────────────────────────────────────────────────────────────────
    InferenceRule(
        id="RULE_FIRE_001",
        name="포병 화력 지원 가능 범위",
        description="포병 부대가 담당 축선 내 모든 지형셀에 화력 지원 가능",
        condition_sparql="""
            ?artillery a ns:아군부대현황 .
            ?artillery ns:병종 "포병" .
            ?artillery ns:has전장축선 ?axis .
            ?axis ns:has지형셀 ?cell .
        """,
        conclusion_template="?artillery ns:화력지원가능 ?cell",
        priority="MEDIUM",
        category="resource"
    ),
    
    InferenceRule(
        id="RULE_FIRE_002",
        name="항공 화력 지원 가능 범위",
        description="항공 자산이 모든 축선에 화력 지원 가능",
        condition_sparql="""
            ?aircraft a ns:아군가용자산 .
            ?aircraft ns:자산유형 "항공" .
            ?axis a ns:전장축선 .
            ?axis ns:has지형셀 ?cell .
        """,
        conclusion_template="?aircraft ns:화력지원가능 ?cell",
        priority="MEDIUM",
        category="resource"
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # 부대 협력 관련 규칙
    # ─────────────────────────────────────────────────────────────────────────
    InferenceRule(
        id="RULE_COOP_001",
        name="동일 임무 협력 부대",
        description="동일 임무에 할당된 부대들은 협력 관계",
        condition_sparql="""
            ?unit1 a ns:아군부대현황 .
            ?unit1 ns:hasMission ?mission .
            ?unit2 a ns:아군부대현황 .
            ?unit2 ns:hasMission ?mission .
            FILTER(?unit1 != ?unit2)
        """,
        conclusion_template="?unit1 ns:협력관계 ?unit2",
        priority="MEDIUM",
        category="resource"
    ),
    
    InferenceRule(
        id="RULE_COOP_002",
        name="동일 축선 협력 부대",
        description="동일 축선에 배치된 부대들은 상호 지원 가능",
        condition_sparql="""
            ?unit1 a ns:아군부대현황 .
            ?unit1 ns:has전장축선 ?axis .
            ?unit2 a ns:아군부대현황 .
            ?unit2 ns:has전장축선 ?axis .
            FILTER(?unit1 != ?unit2)
        """,
        conclusion_template="?unit1 ns:상호지원가능 ?unit2",
        priority="LOW",
        category="resource"
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # 증원 관련 규칙
    # ─────────────────────────────────────────────────────────────────────────
    InferenceRule(
        id="RULE_REINF_001",
        name="인접 지역 증원 가능",
        description="인접한 지형셀에 있는 부대는 증원 가능",
        condition_sparql="""
            ?unit1 a ns:아군부대현황 .
            ?unit1 ns:locatedIn ?cell1 .
            ?cell1 ns:인접함 ?cell2 .
            ?unit2 a ns:아군부대현황 .
            ?unit2 ns:locatedIn ?cell2 .
            FILTER(?unit1 != ?unit2)
        """,
        conclusion_template="?unit1 ns:증원가능 ?unit2",
        priority="MEDIUM",
        category="resource"
    ),
    
    InferenceRule(
        id="RULE_REINF_002",
        name="예비대 증원 가능",
        description="예비대는 모든 전방 부대에 증원 가능",
        condition_sparql="""
            ?reserve a ns:아군부대현황 .
            ?reserve ns:부대유형 "예비대" .
            ?frontUnit a ns:아군부대현황 .
            ?frontUnit ns:부대유형 "전방부대" .
            FILTER(?reserve != ?frontUnit)
        """,
        conclusion_template="?reserve ns:증원가능 ?frontUnit",
        priority="MEDIUM",
        category="resource"
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # 기동 제한 관련 규칙
    # ─────────────────────────────────────────────────────────────────────────
    InferenceRule(
        id="RULE_MOBILITY_001",
        name="기갑부대 산악 기동 제한",
        description="기갑부대는 산악 지형에서 기동이 제한됨",
        condition_sparql="""
            ?armor a ns:아군부대현황 .
            ?armor ns:병종 "기갑" .
            ?armor ns:locatedIn ?cell .
            ?cell ns:지형유형 "산악" .
        """,
        conclusion_template="?armor ns:기동제한 'true'^^xsd:boolean",
        priority="HIGH",
        category="tactical"
    ),
    
    InferenceRule(
        id="RULE_MOBILITY_002",
        name="기갑부대 하천 기동 제한",
        description="기갑부대는 하천 지형에서 기동이 제한됨",
        condition_sparql="""
            ?armor a ns:아군부대현황 .
            ?armor ns:병종 "기갑" .
            ?armor ns:locatedIn ?cell .
            ?cell ns:지형유형 "하천" .
        """,
        conclusion_template="?armor ns:기동제한 'true'^^xsd:boolean",
        priority="HIGH",
        category="tactical"
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # COA(방책) 관련 규칙
    # ─────────────────────────────────────────────────────────────────────────
    InferenceRule(
        id="RULE_COA_001",
        name="방어 방책 적용 가능 지역",
        description="방어 유리도가 높은 지형에 방어 방책 적용 가능",
        condition_sparql="""
            ?coa a ns:DefenseCOA .
            ?cell a ns:지형셀 .
            ?cell ns:방어유리도 ?defense .
            FILTER(?defense >= 7)
        """,
        conclusion_template="?coa ns:적용가능지역 ?cell",
        priority="LOW",
        category="coa"
    ),
    
    InferenceRule(
        id="RULE_COA_002",
        name="공격 방책 적용 가능 지역",
        description="기동성 등급이 높은 지형에 공격 방책 적용 가능",
        condition_sparql="""
            ?coa a ns:OffensiveCOA .
            ?cell a ns:지형셀 .
            ?cell ns:기동성등급 ?mobility .
            FILTER(?mobility >= 7)
        """,
        conclusion_template="?coa ns:적용가능지역 ?cell",
        priority="LOW",
        category="coa"
    ),
]


class InferenceRulesEngine:
    """
    SWRL 스타일 추론 규칙 엔진
    
    OWL-RL이 처리하지 못하는 복잡한 도메인 규칙을 실행합니다.
    """
    
    def __init__(self, graph: Graph, namespace: str = None):
        """
        Args:
            graph: RDF 그래프
            namespace: 온톨로지 네임스페이스
        """
        self.graph = graph
        self.ns = Namespace(namespace) if namespace else NS
        self.rules = TACTICAL_RULES.copy()
        self.execution_stats = {}
        
    def add_rule(self, rule: InferenceRule):
        """규칙 추가"""
        self.rules.append(rule)
        
    def remove_rule(self, rule_id: str):
        """규칙 제거"""
        self.rules = [r for r in self.rules if r.id != rule_id]
        
    def get_rules(self, category: str = None, enabled_only: bool = True) -> List[InferenceRule]:
        """규칙 목록 조회"""
        filtered = self.rules
        
        if category:
            filtered = [r for r in filtered if r.category == category]
        
        if enabled_only:
            filtered = [r for r in filtered if r.enabled]
        
        return filtered
    
    def execute_rule(self, rule: InferenceRule) -> List[Dict[str, Any]]:
        """
        단일 규칙 실행
        
        Args:
            rule: 실행할 규칙
            
        Returns:
            추론된 트리플 목록 [{"subject": ..., "predicate": ..., "object": ...}, ...]
        """
        if self.graph is None:
            return []
        
        # SPARQL 쿼리 구성
        sparql_query = f"""
            PREFIX ns: <{self.ns}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            SELECT DISTINCT *
            WHERE {{
                {rule.condition_sparql}
            }}
        """
        
        inferred_triples = []
        
        try:
            results = self.graph.query(sparql_query)
            
            for row in results:
                # 결론 템플릿 파싱 및 바인딩
                triple = self._bind_conclusion(rule.conclusion_template, row, results.vars)
                if triple:
                    inferred_triples.append(triple)
                    
        except Exception as e:
            logger.warning(f"Rule {rule.id} execution failed: {e}")
        
        return inferred_triples
    
    def execute_all_rules(self, categories: List[str] = None, 
                          priority_filter: str = None) -> Dict[str, Any]:
        """
        모든 규칙 실행
        
        Args:
            categories: 실행할 규칙 카테고리 (None = 전체)
            priority_filter: 우선순위 필터 (HIGH, MEDIUM, LOW)
            
        Returns:
            실행 결과 딕셔너리
        """
        rules_to_execute = self.get_rules(enabled_only=True)
        
        if categories:
            rules_to_execute = [r for r in rules_to_execute if r.category in categories]
        
        if priority_filter:
            rules_to_execute = [r for r in rules_to_execute if r.priority == priority_filter]
        
        # 우선순위 순으로 정렬 (HIGH > MEDIUM > LOW)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        rules_to_execute.sort(key=lambda r: priority_order.get(r.priority, 3))
        
        all_inferred = []
        rule_results = {}
        
        for rule in rules_to_execute:
            inferred = self.execute_rule(rule)
            rule_results[rule.id] = {
                "name": rule.name,
                "description": rule.description,
                "category": rule.category,
                "priority": rule.priority,
                "inferred_count": len(inferred),
                "inferred_triples": inferred[:10]  # 최대 10개만 저장
            }
            all_inferred.extend(inferred)
        
        self.execution_stats = {
            "total_rules_executed": len(rules_to_execute),
            "total_inferred": len(all_inferred),
            "rules_by_category": self._count_by_category(rules_to_execute),
            "inferred_by_category": self._group_inferred_by_category(rule_results)
        }
        
        return {
            "stats": self.execution_stats,
            "rule_results": rule_results,
            "all_inferred": all_inferred
        }
    
    def apply_inferences_to_graph(self, inferred_triples: List[Dict]) -> int:
        """
        추론된 트리플을 그래프에 추가
        
        Args:
            inferred_triples: 추론된 트리플 목록
            
        Returns:
            추가된 트리플 수
        """
        added_count = 0
        
        for triple in inferred_triples:
            try:
                s = URIRef(triple["subject"]) if triple["subject"].startswith("http") else URIRef(f"{self.ns}{triple['subject']}")
                p = URIRef(triple["predicate"]) if triple["predicate"].startswith("http") else URIRef(f"{self.ns}{triple['predicate']}")
                
                # 객체 유형 판단 (URI vs Literal)
                obj_val = triple["object"]
                if obj_val.startswith("http"):
                    o = URIRef(obj_val)
                elif "^^" in obj_val:
                    # 타입이 지정된 리터럴 (예: 'true'^^xsd:boolean)
                    val, dtype = obj_val.split("^^")
                    o = Literal(val.strip("'\""), datatype=URIRef(dtype.replace("xsd:", "http://www.w3.org/2001/XMLSchema#")))
                else:
                    o = URIRef(f"{self.ns}{obj_val}")
                
                # 중복 체크
                if (s, p, o) not in self.graph:
                    self.graph.add((s, p, o))
                    added_count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to add triple: {triple}, error: {e}")
        
        return added_count
    
    def get_rule_explanation(self, rule_id: str) -> Optional[Dict]:
        """규칙 설명 조회"""
        for rule in self.rules:
            if rule.id == rule_id:
                return {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "category": rule.category,
                    "priority": rule.priority,
                    "condition": rule.condition_sparql.strip(),
                    "conclusion": rule.conclusion_template,
                    "enabled": rule.enabled
                }
        return None
    
    def _bind_conclusion(self, template: str, row, variables) -> Optional[Dict]:
        """
        결론 템플릿에 변수 바인딩
        
        Args:
            template: 결론 템플릿 (예: "?unit1 ns:협력관계 ?unit2")
            row: SPARQL 결과 행
            variables: 변수 목록
            
        Returns:
            바인딩된 트리플 딕셔너리
        """
        try:
            # 템플릿 파싱 (간단한 형태: ?s predicate ?o)
            parts = template.strip().split()
            if len(parts) != 3:
                return None
            
            subject_var = parts[0]
            predicate = parts[1]
            object_var = parts[2]
            
            # 변수 바인딩
            var_map = {}
            for i, var in enumerate(variables):
                var_map[f"?{var}"] = str(row[i]) if row[i] else None
            
            subject = var_map.get(subject_var, subject_var)
            obj = var_map.get(object_var, object_var)
            
            if subject is None or obj is None:
                return None
            
            # 프리디케이트에서 ns: 접두사 처리
            if predicate.startswith("ns:"):
                predicate = f"{self.ns}{predicate[3:]}"
            
            return {
                "subject": subject,
                "predicate": predicate,
                "object": obj
            }
            
        except Exception as e:
            logger.warning(f"Failed to bind conclusion template: {e}")
            return None
    
    def _count_by_category(self, rules: List[InferenceRule]) -> Dict[str, int]:
        """카테고리별 규칙 수 계산"""
        counts = {}
        for rule in rules:
            counts[rule.category] = counts.get(rule.category, 0) + 1
        return counts
    
    def _group_inferred_by_category(self, rule_results: Dict) -> Dict[str, int]:
        """카테고리별 추론 결과 수 계산"""
        counts = {}
        for rule_id, result in rule_results.items():
            cat = result["category"]
            counts[cat] = counts.get(cat, 0) + result["inferred_count"]
        return counts


# 규칙 카테고리 정의
RULE_CATEGORIES = {
    "tactical": {
        "name": "전술 규칙",
        "description": "교전, 기동 제한 등 전술적 상황 추론",
        "icon": "⚔️"
    },
    "threat": {
        "name": "위협 분석",
        "description": "위협 노출, 적 영향 범위 등 위협 관련 추론",
        "icon": "⚠️"
    },
    "resource": {
        "name": "자원 관리",
        "description": "화력 지원, 협력 관계, 증원 가능 여부 추론",
        "icon": "🔧"
    },
    "coa": {
        "name": "방책 분석",
        "description": "COA 적용 가능 지역 및 효과성 추론",
        "icon": "📋"
    }
}


def get_all_rule_categories() -> Dict[str, Dict]:
    """모든 규칙 카테고리 조회"""
    return RULE_CATEGORIES


def create_engine(graph: Graph, namespace: str = None) -> InferenceRulesEngine:
    """InferenceRulesEngine 인스턴스 생성 헬퍼"""
    return InferenceRulesEngine(graph, namespace)
