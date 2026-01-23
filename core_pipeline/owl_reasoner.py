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
        
    def run_inference(self, include_rdfs: bool = True) -> Graph:
        """
        OWL-RL 추론 실행
        
        Args:
            include_rdfs: RDFS 추론도 함께 수행할지 여부
            
        Returns:
            추론이 적용된 그래프
        """
        if not OWLRL_AVAILABLE:
            logger.error("owlrl 라이브러리가 없어 추론을 수행할 수 없습니다.")
            self.inference_stats = {
                "success": False,
                "error": "owlrl 라이브러리가 설치되지 않았습니다."
            }
            return self.original_graph
            
        if self.original_graph is None:
            logger.error("그래프가 None입니다.")
            self.inference_stats = {
                "success": False,
                "error": "그래프가 None입니다."
            }
            return None
        
        start_time = time.time()
        
        # 원본 그래프의 트리플 수 측정 (정확한 방법)
        original_triples_set = set(self.original_graph)
        original_count = len(original_triples_set)
        logger.info(f"OWL-RL 추론 시작: 원본 트리플 수 = {original_count}")
        
        # 원본 그래프 복사
        self.inferred_graph = Graph()
        for triple in self.original_graph:
            self.inferred_graph.add(triple)
        
        # 복사 후 확인
        copied_count = len(set(self.inferred_graph))
        if copied_count != original_count:
            logger.warning(f"그래프 복사 불일치: 원본={original_count}, 복사본={copied_count}")
        
        try:
            # OWL-RL 추론 적용
            # 참고: DeductiveClosure.expand()는 idempotent해야 하지만,
            # 실제로는 그래프 상태에 따라 추가 트리플이 생성될 수 있음
            # (예: 첫 번째 추론이 완전하지 않은 경우)
            
            if include_rdfs:
                # RDFS + OWL-RL 추론
                logger.info("RDFS 추론 실행 중...")
                DeductiveClosure(RDFS_Semantics).expand(self.inferred_graph)
                rdfs_count = len(set(self.inferred_graph))
                logger.info(f"RDFS 추론 후: {rdfs_count} triples (+{rdfs_count - original_count})")
            
            logger.info("OWL-RL 추론 실행 중...")
            DeductiveClosure(OWLRL_Semantics).expand(self.inferred_graph)
            
            # 추론 후 트리플 수 측정 (정확한 방법)
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
            
            if new_triples > 0:
                logger.info(f"OWL-RL 추론 완료: {new_triples}개 새로운 트리플 생성 ({elapsed_time:.2f}초)")
                logger.info(f"  원본: {original_count} → 추론: {inferred_count} triples")
            elif new_triples == 0:
                logger.warning(f"OWL-RL 추론 완료: 새로운 트리플 없음 (추론 규칙이 적용되지 않았거나 이미 모든 관계가 존재)")
                logger.info(f"  원본: {original_count} → 추론: {inferred_count} triples")
            else:
                logger.error(f"OWL-RL 추론 이상: 트리플 수 감소 ({new_triples}개 감소)")
                logger.error(f"  원본: {original_count} → 추론: {inferred_count} triples")
                # 원본 그래프로 복원
                self.inferred_graph = Graph()
                for triple in self.original_graph:
                    self.inferred_graph.add(triple)
                logger.warning("추론 그래프를 원본으로 복원했습니다.")
            
        except Exception as e:
            logger.error(f"OWL-RL 추론 실패: {e}")
            self.inference_stats = {
                "success": False,
                "error": str(e)
            }
            self.inferred_graph = self.original_graph
        
        return self.inferred_graph
    
    def get_inferred_relations(self, entity: str, max_results: int = 50, 
                               compare_with_graph: Graph = None) -> Dict[str, Any]:
        """
        특정 엔티티의 추론된 관계 조회
        
        Args:
            entity: 엔티티 ID 또는 URI
            max_results: 최대 결과 수
            compare_with_graph: 비교할 그래프 (None이면 original_graph와 비교)
            
        Returns:
            추론된 관계 정보 딕셔너리
        """
        # 추론이 아직 수행되지 않았으면 실행
        if not self._inference_performed:
            self.run_inference()
        
        # 비교할 그래프 결정 (compare_with_graph가 있으면 사용, 없으면 original_graph 사용)
        comparison_graph = compare_with_graph if compare_with_graph is not None else self.original_graph
        
        if self.inferred_graph is None:
            return {
                "entity": entity,
                "direct_relations": [],
                "inferred_relations": [],
                "total_inferred": 0,
                "stats": self.inference_stats
            }
        
        # URI 변환 (여러 후보 시도)
        entity_uri = None
        if entity.startswith("http"):
            entity_uri = URIRef(entity)
        else:
            # 언더스코어 정규화 (연속된 언더스코어를 하나로 변환)
            normalized_entity = re.sub(r'_+', '_', entity)  # __ -> _
            if normalized_entity.startswith('_'):
                normalized_entity = normalized_entity[1:]
            if normalized_entity.endswith('_'):
                normalized_entity = normalized_entity[:-1]
            
            # 여러 URI 후보 생성 (대소문자 변형, 언더스코어 변형 등)
            candidates = [
                URIRef(f"{self.ns}{normalized_entity}"),  # 정규화된 원본
                URIRef(f"{self.ns}{entity}"),  # 원본 그대로
                URIRef(f"{self.ns}{normalized_entity.upper()}"),  # 정규화 + 대문자
                URIRef(f"{self.ns}{normalized_entity.lower()}"),  # 정규화 + 소문자
            ]
            
            # 언더스코어가 있는 경우 변형 추가
            if "_" in normalized_entity:
                parts = normalized_entity.split("_", 1)
                if len(parts) == 2:
                    prefix, suffix = parts
                    candidates.extend([
                        URIRef(f"{self.ns}{prefix}_{suffix.upper()}"),  # 접미사 대문자
                        URIRef(f"{self.ns}{prefix}_{suffix.lower()}"),  # 접미사 소문자
                    ])
            
            # 원본에도 언더스코어가 있는 경우 (정규화 전)
            if "_" in entity and entity != normalized_entity:
                parts = entity.split("_", 1)
                if len(parts) == 2:
                    prefix, suffix = parts
                    # 연속 언더스코어 제거 후 변형
                    clean_suffix = re.sub(r'_+', '_', suffix)
                    if clean_suffix:
                        candidates.extend([
                            URIRef(f"{self.ns}{prefix}_{clean_suffix.upper()}"),
                            URIRef(f"{self.ns}{prefix}_{clean_suffix.lower()}"),
                        ])
            
            from common.logger import debug_log
            
            debug_log(logger, f"[OWL Reasoner] 엔티티 검색 시작 - 입력: '{entity}', 정규화: '{normalized_entity}'")
            debug_log(logger, f"[OWL Reasoner] URI 후보 생성 완료: {len(candidates)}개")
            debug_log(logger, f"[OWL Reasoner] 그래프 크기 - 원본: {len(set(self.original_graph))} triples, 비교: {len(set(comparison_graph))} triples")
            
            # 실제 그래프에 존재하는 URI 찾기 (원본 그래프와 비교 그래프 모두 확인)
            for idx, candidate in enumerate(candidates):
                # 원본 그래프에서 확인
                found_in_original = (candidate, RDF.type, None) in self.original_graph or \
                                   (candidate, None, None) in self.original_graph or \
                                   (None, None, candidate) in self.original_graph
                # 비교 그래프에서도 확인
                found_in_comparison = (candidate, RDF.type, None) in comparison_graph or \
                                    (candidate, None, None) in comparison_graph or \
                                    (None, None, candidate) in comparison_graph
                
                if found_in_original or found_in_comparison:
                    entity_uri = candidate
                    debug_log(logger, f"[OWL Reasoner] 엔티티 URI 발견 (후보 #{idx+1}/{len(candidates)}): {entity_uri}")
                    debug_log(logger, f"[OWL Reasoner]   원본 그래프: {'✓' if found_in_original else '✗'}, 비교 그래프: {'✓' if found_in_comparison else '✗'}")
                    break
            
            # 후보 중 하나도 없으면 첫 번째 후보 사용 (디버깅을 위해)
            if entity_uri is None:
                entity_uri = candidates[0]
                logger.warning(f"[OWL Reasoner] 경고: 그래프에서 엔티티 URI를 찾지 못했습니다. 첫 번째 후보 사용: {entity_uri}")
                debug_log(logger, f"[OWL Reasoner] 입력 엔티티: '{entity}', 정규화: '{normalized_entity}'")
                debug_log(logger, f"[OWL Reasoner] 생성된 URI 후보 ({len(candidates)}개):")
                for i, cand in enumerate(candidates[:5]):  # 최대 5개만 표시
                    debug_log(logger, f"[OWL Reasoner]   [{i+1}] {cand}")
                
                # 샘플 엔티티 URI 출력 (디버깅용)
                sample_entities = []
                for s, p, o in list(self.original_graph.triples((None, RDF.type, None)))[:10]:
                    sample_entities.append(str(s))
                debug_log(logger, f"[OWL Reasoner] 원본 그래프의 샘플 엔티티 URI (최대 10개):")
                for i, uri in enumerate(sample_entities):
                    debug_log(logger, f"[OWL Reasoner]   [{i+1}] {uri}")
                
                # 비교 그래프에서도 샘플 출력
                sample_entities_comparison = []
                for s, p, o in list(comparison_graph.triples((None, RDF.type, None)))[:10]:
                    sample_entities_comparison.append(str(s))
                debug_log(logger, f"[OWL Reasoner] 비교 그래프의 샘플 엔티티 URI (최대 10개):")
                for i, uri in enumerate(sample_entities_comparison):
                    debug_log(logger, f"[OWL Reasoner]   [{i+1}] {uri}")
        
        if entity_uri is None:
            return {
                "entity": entity,
                "entity_uri": "",
                "direct_relations": [],
                "inferred_relations": [],
                "total_direct": 0,
                "total_inferred": 0,
                "confidence": 0.0,
                "stats": self.inference_stats
            }
        
        # 직접 관계 (비교 그래프에 있는 것)
        direct_relations = []
        
        # 엔티티가 subject인 경우
        direct_subject_count = 0
        for s, p, o in comparison_graph.triples((entity_uri, None, None)):
            direct_subject_count += 1
            if p not in [RDF.type, RDFS.label]:
                direct_relations.append({
                    "relation": self._get_local_name(p),
                    "target": self._get_local_name(o),
                    "type": "direct",
                    "full_predicate": str(p),
                    "full_object": str(o)
                })
        
        # 엔티티가 object인 경우
        direct_object_count = 0
        for s, p, o in comparison_graph.triples((None, None, entity_uri)):
            direct_object_count += 1
            if p not in [RDF.type, RDFS.label]:
                direct_relations.append({
                    "relation": self._get_local_name(p),
                    "source": self._get_local_name(s),
                    "type": "direct_reverse",
                    "full_predicate": str(p),
                    "full_subject": str(s)
                })
        
        from common.logger import debug_log
        
        # 기본 정보는 항상 기록
        logger.info(f"[OWL Reasoner] 직접 관계 조회 완료: {len(direct_relations)}개")
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[OWL Reasoner] 직접 관계 상세 - subject: {direct_subject_count}, object: {direct_object_count}")
        
        # 추론된 관계 (추론 그래프에만 있는 것)
        # 비교 그래프의 트리플을 set으로 변환하여 빠른 조회
        comparison_triples_set = set(comparison_graph)
        inferred_relations = []
        
        # 디버깅: 추론 그래프에서 해당 엔티티와 관련된 모든 트리플 확인
        inferred_triples_for_entity = []
        original_triples_for_entity = []
        
        # 추론 그래프에서 엔티티 관련 트리플 수집
        for s, p, o in self.inferred_graph.triples((entity_uri, None, None)):
            inferred_triples_for_entity.append((s, p, o))
        for s, p, o in self.inferred_graph.triples((None, None, entity_uri)):
            inferred_triples_for_entity.append((s, p, o))
        
        # 비교 그래프에서 엔티티 관련 트리플 수집
        for s, p, o in comparison_graph.triples((entity_uri, None, None)):
            original_triples_for_entity.append((s, p, o))
        for s, p, o in comparison_graph.triples((None, None, entity_uri)):
            original_triples_for_entity.append((s, p, o))
        
        debug_log(logger, f"[OWL Reasoner] 엔티티 URI: {entity_uri}")
        debug_log(logger, f"[OWL Reasoner] 엔티티 관련 트리플 수 - 추론 그래프: {len(inferred_triples_for_entity)}, 비교 그래프: {len(original_triples_for_entity)}")
        debug_log(logger, f"[OWL Reasoner] 전체 그래프 크기 - 비교: {len(set(comparison_graph))} triples, 추론: {len(set(self.inferred_graph))} triples")
        
        # 엔티티가 subject인 경우
        for s, p, o in self.inferred_graph.triples((entity_uri, None, None)):
            triple = (s, p, o)
            in_comparison = triple in comparison_triples_set
            is_type_or_label = p in [RDF.type, RDFS.label]
            
            # 리터럴 값은 관계가 아니므로 제외
            from rdflib import Literal
            is_literal = isinstance(o, Literal)
            
            # 자기 자신을 가리키는 sameAs 관계 제외
            is_self_reference = (p == OWL.sameAs and o == entity_uri)
            
            # 유효한 추론 관계만 추가
            if not in_comparison and not is_type_or_label and not is_literal and not is_self_reference:
                inferred_relations.append({
                    "relation": self._get_local_name(p),
                    "target": self._get_local_name(o),
                    "type": "inferred",
                    "reasoning": self._explain_inference(p, o),
                    "full_predicate": str(p),
                    "full_object": str(o)
                })
            elif not in_comparison and is_type_or_label:
                logger.debug(f"Skipping RDF.type/RDFS.label triple: ({s}, {p}, {o})")
            elif not in_comparison and is_literal:
                logger.debug(f"Skipping literal value triple: ({s}, {p}, {o})")
            elif not in_comparison and is_self_reference:
                logger.debug(f"Skipping self-reference sameAs triple: ({s}, {p}, {o})")
        
        # 엔티티가 object인 경우
        for s, p, o in self.inferred_graph.triples((None, None, entity_uri)):
            triple = (s, p, o)
            in_comparison = triple in comparison_triples_set
            is_type_or_label = p in [RDF.type, RDFS.label]
            
            # 리터럴 값은 관계가 아니므로 제외 (object가 리터럴일 수 없지만 확인)
            is_literal = isinstance(o, Literal)
            
            # 자기 자신을 가리키는 sameAs 관계 제외
            is_self_reference = (p == OWL.sameAs and s == entity_uri)
            
            # 유효한 추론 관계만 추가
            if not in_comparison and not is_type_or_label and not is_literal and not is_self_reference:
                inferred_relations.append({
                    "relation": self._get_local_name(p),
                    "source": self._get_local_name(s),
                    "type": "inferred_reverse",
                    "reasoning": self._explain_inference(p, s),
                    "full_predicate": str(p),
                    "full_subject": str(s)
                })
            elif not in_comparison and is_type_or_label:
                logger.debug(f"Skipping RDF.type/RDFS.label triple: ({s}, {p}, {o})")
            elif not in_comparison and is_literal:
                logger.debug(f"Skipping literal value triple: ({s}, {p}, {o})")
            elif not in_comparison and is_self_reference:
                logger.debug(f"Skipping self-reference sameAs triple: ({s}, {p}, {o})")
        
        # 기본 정보는 항상 기록
        logger.info(f"[OWL Reasoner] 추론 관계 조회 완료: {len(inferred_relations)}개")
        
        # 디버깅: 추론 그래프에 실제로 새로운 트리플이 있는지 확인
        # 필터링 전 원시 추론 트리플 수 확인
        raw_inferred_count = 0
        filtered_literal_count = 0
        filtered_self_ref_count = 0
        filtered_type_label_count = 0
        
        for s, p, o in self.inferred_graph.triples((entity_uri, None, None)):
            triple = (s, p, o)
            if triple not in comparison_triples_set:
                raw_inferred_count += 1
                if p in [RDF.type, RDFS.label]:
                    filtered_type_label_count += 1
                elif isinstance(o, Literal):
                    filtered_literal_count += 1
                elif p == OWL.sameAs and o == entity_uri:
                    filtered_self_ref_count += 1
        
        for s, p, o in self.inferred_graph.triples((None, None, entity_uri)):
            triple = (s, p, o)
            if triple not in comparison_triples_set:
                raw_inferred_count += 1
                if p in [RDF.type, RDFS.label]:
                    filtered_type_label_count += 1
                elif isinstance(o, Literal):
                    filtered_literal_count += 1
                elif p == OWL.sameAs and s == entity_uri:
                    filtered_self_ref_count += 1
        
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[OWL Reasoner] 필터링 상세 - 원시 추론 트리플: {raw_inferred_count}개, 제외된 항목 (RDF.type/RDFS.label: {filtered_type_label_count}개, 리터럴: {filtered_literal_count}개, 자기참조: {filtered_self_ref_count}개)")
        
        if len(inferred_relations) == 0:
            logger.warning(f"[OWL Reasoner] 경고: 엔티티 '{entity_uri}'에 대한 추론 관계를 찾지 못했습니다")
            logger.warning(f"[OWL Reasoner]   추론 그래프의 엔티티 관련 트리플: {len(inferred_triples_for_entity)}개")
            logger.warning(f"[OWL Reasoner]   비교 그래프의 엔티티 관련 트리플: {len(original_triples_for_entity)}개")
            
            # 새로운 트리플이 있는지 확인 (RDF.type/RDFS.label 제외)
            new_triples_count = 0
            new_triples_list = []
            for triple in inferred_triples_for_entity:
                s, p, o = triple
                if triple not in comparison_triples_set and p not in [RDF.type, RDFS.label]:
                    new_triples_count += 1
                    if len(new_triples_list) < 5:  # 최대 5개만 저장
                        new_triples_list.append((s, p, o))
            
            if new_triples_count > 0:
                logger.warning(f"[OWL Reasoner]   새로운 트리플 발견 (RDF.type/RDFS.label 제외): {new_triples_count}개")
                logger.warning(f"[OWL Reasoner]   새로운 트리플 샘플:")
                for i, (s, p, o) in enumerate(new_triples_list):
                    logger.warning(f"[OWL Reasoner]     [{i+1}] ({s}, {p}, {o})")
            else:
                logger.warning(f"[OWL Reasoner]   새로운 트리플 없음 (모든 트리플이 비교 그래프에 이미 존재하거나 필터링됨)")
            
            # 샘플 트리플 출력 (디버깅 모드에서만)
            if len(inferred_triples_for_entity) > 0:
                debug_log(logger, f"[OWL Reasoner] 추론 그래프의 엔티티 관련 트리플 샘플 (최대 5개):")
                for i, (s, p, o) in enumerate(inferred_triples_for_entity[:5]):
                    in_comparison = (s, p, o) in comparison_triples_set
                    is_type_or_label = p in [RDF.type, RDFS.label]
                    debug_log(logger, f"[OWL Reasoner]   [{i+1}] ({s}, {p}, {o}) - 비교그래프 포함: {in_comparison}, 타입/라벨: {is_type_or_label}")
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(
            len(direct_relations), 
            len(inferred_relations)
        )
        
        # 최종 결과 요약 로깅
        # 기본 정보는 항상 기록
        logger.info(f"[OWL Reasoner] 추론 완료 - 엔티티: {entity}, 직접 관계: {len(direct_relations)}개, 추론 관계: {len(inferred_relations)}개, 신뢰도: {confidence:.1f}%")
        
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[OWL Reasoner] ===== 추론 결과 요약 =====")
        debug_log(logger, f"[OWL Reasoner] 엔티티 URI: {entity_uri}")
        if len(inferred_relations) > 0:
            debug_log(logger, f"[OWL Reasoner] 추론 관계 유형 분포:")
            relation_types = {}
            for rel in inferred_relations:
                rel_type = rel.get("type", "unknown")
                relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
            for rel_type, count in relation_types.items():
                debug_log(logger, f"[OWL Reasoner]   {rel_type}: {count}개")
        debug_log(logger, f"[OWL Reasoner] =========================")
        
        return {
            "entity": entity,
            "entity_uri": str(entity_uri),
            "direct_relations": direct_relations[:max_results],
            "inferred_relations": inferred_relations[:max_results],
            "total_direct": len(direct_relations),
            "total_inferred": len(inferred_relations),
            "confidence": confidence,
            "stats": self.inference_stats
        }
    
    def find_transitive_paths(self, entity: str, property_uri: str, max_depth: int = 3) -> List[List[str]]:
        """
        전이적 관계의 경로 탐색
        
        Args:
            entity: 시작 엔티티
            property_uri: 탐색할 속성 URI
            max_depth: 최대 탐색 깊이
            
        Returns:
            발견된 경로 목록 [[entity1, entity2, entity3], ...]
        """
        if self.inferred_graph is None:
            self.run_inference()
            
        if not entity.startswith("http"):
            entity_uri = URIRef(f"{self.ns}{entity}")
        else:
            entity_uri = URIRef(entity)
            
        prop_uri = URIRef(property_uri) if property_uri.startswith("http") else URIRef(f"{self.ns}{property_uri}")
        
        paths = []
        visited = set()
        
        def dfs(current: URIRef, path: List[str], depth: int):
            if depth > max_depth:
                return
            
            current_name = self._get_local_name(current)
            if current_name in visited:
                return
            
            visited.add(current_name)
            path.append(current_name)
            
            # 현재 노드에서 나가는 관계 탐색
            for _, _, o in self.inferred_graph.triples((current, prop_uri, None)):
                if isinstance(o, URIRef):
                    o_name = self._get_local_name(o)
                    if o_name not in visited:
                        if len(path) > 1:  # 시작점 제외하고 2개 이상이면 경로로 저장
                            paths.append(path + [o_name])
                        dfs(o, path.copy(), depth + 1)
            
            visited.remove(current_name)
        
        dfs(entity_uri, [], 0)
        return paths
    
    def get_inference_explanation(self, subject: str, predicate: str, obj: str) -> Dict:
        """
        특정 추론 트리플에 대한 설명 생성
        
        Args:
            subject: 주어 엔티티
            predicate: 술어 (관계)
            obj: 목적어 엔티티
            
        Returns:
            추론 설명 딕셔너리
        """
        s_uri = URIRef(f"{self.ns}{subject}") if not subject.startswith("http") else URIRef(subject)
        p_uri = URIRef(f"{self.ns}{predicate}") if not predicate.startswith("http") else URIRef(predicate)
        o_uri = URIRef(f"{self.ns}{obj}") if not obj.startswith("http") else URIRef(obj)
        
        # 원본에 있는지 확인
        is_in_original = (s_uri, p_uri, o_uri) in self.original_graph
        
        if is_in_original:
            return {
                "triple": f"{subject} → {predicate} → {obj}",
                "is_inferred": False,
                "explanation": "이 관계는 원본 데이터에 직접 정의되어 있습니다.",
                "rule_applied": None
            }
        
        # 추론된 것이면 규칙 설명
        return {
            "triple": f"{subject} → {predicate} → {obj}",
            "is_inferred": True,
            "explanation": self._explain_inference(p_uri, o_uri),
            "rule_applied": self._get_rule_type(p_uri)
        }
    
    def _get_local_name(self, uri) -> str:
        """URI에서 로컬 이름 추출"""
        if uri is None:
            return ""
        uri_str = str(uri)
        if "#" in uri_str:
            return uri_str.split("#")[-1]
        elif "/" in uri_str:
            return uri_str.split("/")[-1]
        return uri_str
    
    def _explain_inference(self, predicate: URIRef, object_or_subject=None) -> str:
        """추론 규칙 설명 생성"""
        pred_name = self._get_local_name(predicate)
        
        # sameAs 관계에 대한 특별 처리
        if pred_name == "sameAs" or predicate == OWL.sameAs:
            if object_or_subject:
                obj_name = self._get_local_name(object_or_subject) if hasattr(object_or_subject, '__str__') else str(object_or_subject)
                return f"동일성 추론(owl:sameAs): {obj_name}와 동일한 엔티티로 추론됨"
            return "동일성 추론(owl:sameAs): 동일한 엔티티로 추론됨"
        
        explanations = {
            # 역관계
            "배치부대목록": "역관계(InverseOf): locatedIn의 역방향 추론",
            "소속축선": "역관계(InverseOf): has지형셀의 역방향 추론",
            "배치된부대": "역관계(InverseOf): has전장축선의 역방향 추론",
            "할당부대": "역관계(InverseOf): hasMission의 역방향 추론",
            
            # 속성 체인
            "작전가능지역": "속성체인(PropertyChain): 부대 → 축선 → 지형셀 경로 추론",
            "위협영향지역": "속성체인(PropertyChain): 적군 → 축선 → 지형셀 경로 추론",
            "임무축선": "속성체인(PropertyChain): 부대 → 임무 → 축선 경로 추론",
            "시나리오적군": "속성체인(PropertyChain): 시나리오 → 위협상황 → 적군 경로 추론",
            
            # 대칭 관계
            "인접함": "대칭관계(Symmetric): A↔B 양방향 동일",
            "협력관계": "대칭관계(Symmetric): A↔B 양방향 동일",
            "축선연결": "대칭관계(Symmetric): A↔B 양방향 동일",
            
            # 전이 관계
            "포함관계": "전이관계(Transitive): A→B→C이면 A→C",
            
            # 도메인 추론
            "교전대상": "도메인추론: 동일 지역 적/아군 위치 기반",
            "화력지원가능": "도메인추론: 포병/항공 지원 범위 기반",
            "증원가능": "도메인추론: 인접 지역 부대 기반",
            "위협노출": "도메인추론: 적 영향권 내 위치 기반"
        }
        
        return explanations.get(pred_name, "OWL-RL 표준 규칙에 의한 추론")
    
    def _get_rule_type(self, predicate: URIRef) -> str:
        """적용된 규칙 유형 반환"""
        pred_name = self._get_local_name(predicate)
        
        inverse_props = ["배치부대목록", "소속축선", "배치된부대", "할당부대"]
        chain_props = ["작전가능지역", "위협영향지역", "임무축선", "시나리오적군"]
        symmetric_props = ["인접함", "협력관계", "축선연결"]
        transitive_props = ["포함관계"]
        
        if pred_name in inverse_props:
            return "InverseProperty"
        elif pred_name in chain_props:
            return "PropertyChainAxiom"
        elif pred_name in symmetric_props:
            return "SymmetricProperty"
        elif pred_name in transitive_props:
            return "TransitiveProperty"
        else:
            return "RDFS/OWL-RL"
    
    def _calculate_confidence(self, direct_count: int, inferred_count: int) -> float:
        """
        추론 신뢰도 계산
        
        직접 관계가 많을수록 신뢰도가 높음
        추론된 관계만 많으면 신뢰도 감소
        """
        from common.logger import debug_log_debug
        
        if direct_count == 0 and inferred_count == 0:
            debug_log_debug(logger, f"[OWL Reasoner] 신뢰도 계산: 직접/추론 관계 모두 0 → 신뢰도 0.0%")
            return 0.0
        
        # 직접 관계 비율 기반 신뢰도
        total = direct_count + inferred_count
        direct_ratio = direct_count / total
        
        # 기본 신뢰도 (직접 관계가 있으면 최소 0.5)
        base_confidence = 0.5 if direct_count > 0 else 0.3
        
        # 직접 관계 수에 따른 보너스 (최대 0.3)
        direct_bonus = min(0.3, direct_count * 0.03)
        
        # 추론 관계 패널티 (너무 많으면 신뢰도 하락)
        inferred_penalty = min(0.2, inferred_count * 0.01) if inferred_count > 20 else 0
        
        confidence = base_confidence + direct_bonus - inferred_penalty
        final_confidence = max(0.0, min(1.0, round(confidence, 3)))
        
        debug_log_debug(logger, f"[OWL Reasoner] 신뢰도 계산 상세 - 직접: {direct_count}개, 추론: {inferred_count}개, "
                    f"직접비율: {direct_ratio:.2%}, 기본: {base_confidence:.2f}, 보너스: {direct_bonus:.2f}, "
                    f"패널티: {inferred_penalty:.2f} → 최종: {final_confidence:.1%}")
        
        return final_confidence
    
    def get_stats(self) -> Dict:
        """추론 통계 반환"""
        return self.inference_stats
    
    def reset(self):
        """추론 결과 초기화"""
        self.inferred_graph = None
        self.inference_stats = {}
        self._inference_performed = False


# 유틸리티 함수
def create_reasoner(graph: Graph, namespace: str = None) -> OWLReasoner:
    """OWLReasoner 인스턴스 생성 헬퍼"""
    return OWLReasoner(graph, namespace)
