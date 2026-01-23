# core_pipeline/ontology_validator.py
# -*- coding: utf-8 -*-
"""
Ontology Validator
온톨로지 스키마 준수 여부 및 데이터 건전성(Health)을 검증하는 모듈
"""
import pandas as pd
from typing import Dict, List, Tuple, Any
from rdflib import Graph, URIRef, RDF, RDFS, OWL
from rdflib.plugins.sparql import prepareQuery

class OntologyValidator:
    def __init__(self, ontology_manager):
        """
        Args:
            ontology_manager: EnhancedOntologyManager Instance
        """
        self.om = ontology_manager
        
    def validate_schema_compliance(self) -> Dict[str, Any]:
        """
        개선된 스키마(Advanced Schema) 준수 여부 검증
        """
        results = {
            "axis_compliance": self._check_axis_schema(),
            "connectivity_health": self._check_connectivity(),
            "reasoning_status": self._check_reasoning_capability()
        }
        
        # 종합 점수 계산
        total_checks = 0
        passed_checks = 0
        
        for category in results.values():
            for check in category.get("checks", []):
                total_checks += 1
                if check["status"] == "PASS":
                    passed_checks += 1
        
        results["overall_score"] = round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0
        return results

    def _check_axis_schema(self) -> Dict[str, Any]:
        """전장축선 스키마 검증"""
        ns = self.om.ns
        
        checks = []
        
        # 1. Axis Class 정의 확인
        count = self._get_count(ns.전장축선)
        checks.append({
            "name": "전장축선 객체화 검증",
            "desc": "전장축선이 단순 속성이 아닌 독립된 객체(Instance)로 존재하는지 확인",
            "status": "PASS" if count > 0 else "FAIL",
            "count": count,
            "message": f"총 {count}개의 전장축선 객체가 식별됨" if count > 0 else "전장축선 객체가 없음"
        })
        
        # 2. Axis - Terrain 연결 확인
        # 방법 1: has지형셀 관계 직접 확인
        has_terrain_prop = ns.has지형셀
        link_count = len(list(self.om.graph.triples((None, has_terrain_prop, None))))
        
        # 전장축선 객체에서의 관계만 카운트 (더 정확한 검증)
        axis_terrain_links = []
        for axis in self.om.graph.subjects(RDF.type, ns.전장축선):
            for terrain in self.om.graph.objects(axis, has_terrain_prop):
                axis_terrain_links.append((axis, terrain))
        
        link_count = len(axis_terrain_links)
        checks.append({
            "name": "축선-지형 연결성",
            "desc": "전장축선이 지형 정보와 공간적으로 연결되어 있는지 확인",
            "status": "PASS" if link_count > 0 else "WARNING",
            "count": link_count,
            "message": f"{link_count}개의 지형 연결 확인"
        })

        return {"score": 100 if count > 0 else 0, "checks": checks}

    def get_instance_counts(self) -> Dict[str, int]:
        """주요 클래스별 인스턴스 개수 조회"""
        counts = {}
        ns = self.om.ns
        target_classes = {
            "Threat": ns.위협상황,
            "COA": ns.COA,
            "Axis": ns.전장축선,
            "Unit": ns.아군부대현황, 
            "Terrain": ns.지형셀
        }
        
        for label, uri in target_classes.items():
            counts[label] = self._get_count(uri)
            
        return counts

    def _check_connectivity(self) -> Dict[str, Any]:
        """데이터 연결 건전성 확인 (Orphan Node 등)"""
        ns = self.om.ns
        checks = []
        
    def _check_connectivity(self) -> Dict[str, Any]:
        """데이터 연결 건전성 확인 (Orphan Node 등)"""
        ns = self.om.ns
        checks = []
        
        # 1. 고립된 노드 (Orphan Nodes) 확인 - Native Python/rdflib 집합 연산으로 최적화 (SPARQL보다 훨씬 빠름)
        all_subjects = set(self.om.graph.subjects())
        all_objects = set(self.om.graph.objects())
        
        # type(rdf:type) 이외의 실질적인 속성을 가진 주체들 추출
        subjects_with_real_props = set()
        for s, p, o in self.om.graph:
            if p != RDF.type:
                subjects_with_real_props.add(s)
        
        # 고립 노드 정의: 
        # (1) 어떤 다른 노드의 목적어(Object)로도 쓰이지 않으면서 
        # (2) 주어(Subject)로 쓰일 때도 오직 rdf:type 정보만 가지고 있는 노드
        orphans = (all_subjects - all_objects) - subjects_with_real_props
        
        # BNode(공백 노드) 제외하고 URIRef만 계산
        orphan_count = len([o for o in orphans if isinstance(o, URIRef)])
        
        checks.append({
            "name": "고립 노드(Orphan) 점검",
            "desc": "다른 데이터와 연결되지 않은 고립된 식별자 발견 (rdf:type만 정의됨)",
            "status": "PASS" if orphan_count == 0 else "WARNING",
            "count": orphan_count,
            "message": f"발견된 고립 노드: {orphan_count}개" if orphan_count > 0 else "고립 노드 없음"
        })
        
        # 2. 필수 관계 확인 - 위협-방책 매핑
        # 이 부분은 특정 패턴이므로 SPARQL이 유리할 수 있으나, 건수가 많지 않으므로 그대로 유지하거나 최적화
        query_threat_no_coa = f"""
        SELECT (COUNT(?s) as ?count) WHERE {{
            ?s a <{ns.위협상황}> .
            FILTER NOT EXISTS {{
                ?s <{ns.위협유형코드}> ?type .
                ?coa <{ns.respondsTo}> ?type .
            }}
        }}
        """
        no_coa_count = self._run_sparql_count(query_threat_no_coa)
        
        checks.append({
            "name": "위협-방책 매핑 완전성",
            "desc": "모든 위협 상황에 대해 대응 방책이 정의되었는지 확인",
            "status": "PASS" if no_coa_count == 0 else "FAIL",
            "count": no_coa_count,
            "message": f"대응 방책이 없는 위협: {no_coa_count}건" if no_coa_count > 0 else "모든 위협에 방책 매핑됨"
        })
        
        return {"checks": checks}

    def _check_reasoning_capability(self) -> Dict[str, Any]:
        """추론 엔진 동작 확인"""
        ns = self.om.ns
        query_inferred = f"""
        SELECT (COUNT(?s) as ?count) WHERE {{
            ?s <{ns.hasAdvantage}> ?o .
        }}
        """
        count = self._run_sparql_count(query_inferred)
        
        return {
            "checks": [{
                "name": "전술적 유불리 추론",
                "desc": "지형과 부대 특성을 고려하여 자동 추론된 '유불리' 관계 확인",
                "status": "PASS" if count > 0 else "INFO",
                "count": count,
                "message": f"{count}건의 전술적 판단 자동 도출됨"
            }]
        }

    def _get_count(self, class_uri: URIRef) -> int:
        """Helper to get instance count using graph API (more reliable for special chars)"""
        try:
            return len(list(self.om.graph.triples((None, RDF.type, class_uri))))
        except Exception as e:
            print(f"[OntologyValidator] Count Error: {e}")
            return 0

    def _run_sparql_count(self, query_str: str) -> int:
        """Helper for complex counts that still need SPARQL"""
        try:
            res = self.om.graph.query(query_str)
            for row in res:
                # row[0] 또는 row.count로 접근 가능하나 인덱스가 더 안전함
                return int(row[0])
            return 0
        except Exception as e:
            print(f"[OntologyValidator] SPARQL Error: {e}")
            return 0
