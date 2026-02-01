# core_pipeline/owl_reasoner.py
# -*- coding: utf-8 -*-
"""
OWL-RL Reasoning Engine
OWL-RL 기반 온톨로지 추론 엔진

팔란티어/IBM Watson 스타일의 의미 기반 추론을 수행합니다:
1. TransitiveProperty 기반 전이적 관계 추론
2. InverseOf 기반 역관계 자동 생성
3. PropertyChainAxiom 기반 관계 체인 추론
4. SymmetricProperty 기반 대칭 관계 추론
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL
import logging
import time
import re

logger = logging.getLogger(__name__)

# OWL-RL 라이브러리 사용 가능 여부 확인
try:
    from owlrl import DeductiveClosure, OWLRL_Semantics, RDFS_Semantics
    OWLRL_AVAILABLE = True
except ImportError:
    OWLRL_AVAILABLE = False
    logger.warning("owlrl 라이브러리가 설치되지 않았습니다. pip install owlrl로 설치하세요.")


# 기본 네임스페이스
NS = Namespace("http://coa-agent-platform.org/ontology#")


class OWLReasoner:
    """
    OWL-RL 기반 추론 엔진
    
    주요 기능:
    - OWL-RL 추론 실행 (전이성, 역관계, 대칭성, 속성 체인)
    - 특정 엔티티에 대한 추론 관계 조회
    - 추론 통계 및 설명 제공
    """
    
    def __init__(self, graph: Graph, namespace: str = None):
        """
        Args:
            graph: RDF 그래프 객체
            namespace: 온톨로지 네임스페이스 (기본: COA Agent Platform)
        """
        self.original_graph = graph
        self.inferred_graph = None
        self.ns = Namespace(namespace) if namespace else NS
        self.inference_stats = {}
        self._inference_performed = False
        
    def run_inference(self, include_rdfs: bool = True) -> Optional[Graph]:
        """
        OWL-RL 추론 실행
        
        Args:
            include_rdfs: RDFS 추론 포함 여부 (기본: True, 대규모 그래프에서는 False 권장)
        
        Returns:
            추론 결과가 포함된 Graph 객체
        """
        if not OWLRL_AVAILABLE:
            logger.error("owlrl 라이브러리가 없어 추론을 수행할 수 없습니다.")
            self.inference_stats = {
                "success": False,
                "error": "owlrl library not installed"
            }
            return self.original_graph
            
        if self.original_graph is None:
            self.inference_stats = {
                "success": False,
                "error": "그래프가 None입니다."
            }
            return None
        
        start_time = time.time()
        
        # 원본 그래프의 트리플 수 측정
        original_triples_set = set(self.original_graph)
        original_count = len(original_triples_set)
        logger.info(f"OWL-RL 추론 시작: 원본 트리플 수 = {original_count}")
        
        # [PERFORMANCE] 대규모 그래프 체크 및 자동 조정 권장
        if original_count > 20000 and include_rdfs:
            logger.warning(f"대규모 그래프 감지 ({original_count} 트리플). RDFS 추론은 매우 느릴 수 있습니다. "
                           "성능 문제가 발생하면 `include_rdfs=False`로 설정하는 것을 고려하세요.")
        
        # 새로운 그래프 생성 및 데이터 복사
        self.inferred_graph = Graph()
        for triple in self.original_graph:
            self.inferred_graph.add(triple)
        
        # 네임스페이스 수동 바인딩
        for prefix, uri in self.original_graph.namespaces():
            self.inferred_graph.bind(prefix, uri)
        
        try:
            # 1. RDFS 추론 (선택적)
            if include_rdfs:
                logger.info("RDFS 추론 실행 중...")
                DeductiveClosure(RDFS_Semantics).expand(self.inferred_graph)
                rdfs_count = len(set(self.inferred_graph))
                logger.info(f"RDFS 추론 완료: {rdfs_count} triples")
            
            # 2. OWL-RL 추론
            logger.info("OWL-RL 추론 실행 중...")
            DeductiveClosure(OWLRL_Semantics).expand(self.inferred_graph)
            
            # 추론 후 결과 측정
            inferred_triples_set = set(self.inferred_graph)
            inferred_count = len(inferred_triples_set)
            new_triples = inferred_count - original_count
            elapsed_time = time.time() - start_time
            
            self.inference_stats = {
                "original_triples": original_count,
                "inferred_triples": inferred_count,
                "new_inferences": new_triples,
                "elapsed_time_ms": round(elapsed_time * 1000, 2),
                "success": True
            }
            
            self._inference_performed = True
            logger.info(f"OWL-RL 추론 완료: {new_triples}개 새로운 트리플 생성 ({elapsed_time:.2f}초)")
            
            return self.inferred_graph
            
        except Exception as e:
            logger.error(f"추론 중 예외 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.inference_stats = {
                "success": False,
                "error": str(e)
            }
            return self.original_graph

    def get_inferred_relations(self, entity_id: str, 
                              compare_with_graph: Optional[Graph] = None) -> Dict[str, Any]:
        """
        특정 엔티티에 대한 추론된 관계 반환
        """
        if not self._inference_performed or self.inferred_graph is None:
            return {"error": "추론이 실행되지 않았습니다.", "entity": entity_id}

        # 비교 대상 그래프 설정
        base_graph = compare_with_graph if compare_with_graph is not None else self.original_graph
        
        # URI 생성
        if not entity_id.startswith('http'):
            entity_uri = URIRef(f"{self.ns}{entity_id}")
        else:
            entity_uri = URIRef(entity_id)

        results = {
            "entity": str(entity_uri),
            "total_direct": 0,
            "total_inferred": 0,
            "inferred_relations": []
        }

        # 원본 관계 수집
        direct_triples = set(base_graph.triples((entity_uri, None, None)))
        direct_triples.update(set(base_graph.triples((None, None, entity_uri))))
        results["total_direct"] = len(direct_triples)

        # 추론된 관계 추출 (inferred_graph - base_graph)
        all_inferred_triples = set(self.inferred_graph.triples((entity_uri, None, None)))
        all_inferred_triples.update(set(self.inferred_graph.triples((None, None, entity_uri))))
        
        new_triples = all_inferred_triples - direct_triples
        
        for s, p, o in new_triples:
            rel = {
                "predicate": str(p),
                "relation": self._get_local_name(p),
                "confidence": 0.9 # OWL-RL 기본 신뢰도
            }
            
            if s == entity_uri:
                rel["target"] = str(o)
                rel["target_label"] = self._get_local_name(o)
                rel["direction"] = "out"
            else:
                rel["source"] = str(s)
                rel["source_label"] = self._get_local_name(s)
                rel["direction"] = "in"
                
            results["inferred_relations"].append(rel)

        results["total_inferred"] = len(results["inferred_relations"])
        return results

    def _get_local_name(self, uri: Any) -> str:
        """URI에서 로컬 이름 추출"""
        if not isinstance(uri, URIRef):
            return str(uri)
        s = str(uri)
        if '#' in s:
            return s.split('#')[-1]
        return s.split('/')[-1]

    def get_stats(self) -> Dict[str, Any]:
        """추론 통계 반환"""
        return self.inference_stats
