# core_pipeline/palantir_search.py
# -*- coding: utf-8 -*-
"""
Palantir Search
팔란티어 방식 검색: RAG + 그래프 하이브리드 검색 (Enhanced)
"""
from typing import Dict, List, Optional, Set
import re


class PalantirSearch:
    """팔란티어 방식 검색 클래스 (고도화됨)"""
    
    def __init__(self, rag_manager, ontology_manager, semantic_inference, reasoning_engine=None):
        """
        Args:
            rag_manager: RAG Manager 인스턴스
            ontology_manager: Ontology Manager 인스턴스
            semantic_inference: Semantic Inference 인스턴스
            reasoning_engine: Reasoning Engine 인스턴스 (가설 수립용)
        """
        self.rag_manager = rag_manager
        self.ontology_manager = ontology_manager
        self.semantic_inference = semantic_inference
        self.reasoning_engine = reasoning_engine
    
    def search(self, query: str, top_k: int = 5, use_graph: bool = True) -> List[Dict]:
        """
        팔란티어 방식 검색: RAG + 그래프 통합
        
        절차:
        1. 온톨로지 기반 질의 확장 (Query Expansion)
        2. 전술적 가설 수립 (Tactical Hypothesis)
        3. RAG 검색 (확장된 쿼리 활용)
        4. 그래프 엔티티 매칭 및 보강
        5. 결과 통합 및 재순위화
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 k개 결과
            use_graph: 그래프 검색 사용 여부
        
        Returns:
            통합 검색 결과 리스트
        """
        # 1. 온톨로지 기반 질의 확장 & 가설 수립
        expanded_query = query
        tactical_hypothesis = []
        
        if use_graph and self.ontology_manager.graph is not None:
            try:
                # 질의 확장
                expanded_terms = self._expand_query_with_ontology(query)
                if expanded_terms:
                    # 원본 쿼 뒤에 확장 용어 추가 (가중치는 낮을 수 있음)
                    expanded_query = f"{query} {' '.join(expanded_terms)}"
                
                # 가설 수립
                tactical_hypothesis = self._generate_tactical_hypotheses(query)
            except Exception as e:
                print(f"[WARN] Ontology preprocessing failed: {e}")
        
        # 2. RAG 검색 (문서 기반)
        rag_results = []
        if self.rag_manager.is_available():
            try:
                # 확장된 쿼리로 검색
                rag_results = self.rag_manager.retrieve_with_context(expanded_query, top_k=top_k)
                
                # 가설 정보를 메타데이터에 추가 (LLM 참조용)
                if tactical_hypothesis:
                    hypothesis_text = "\n".join(tactical_hypothesis)
                    # 가짜 검색 결과로 추가하여 LLM에 전달
                    rag_results.append({
                        "text": f"[전술적 추론 가설]\n{hypothesis_text}",
                        "score": 0.9, # 높은 신뢰도 부여
                        "metadata": {
                            "source": "ReasoningEngine",
                            "type": "hypothesis",
                            "title": "전술적 추론 가설",
                            "doc_name": "전술적 추론 가설"
                        }
                    })
            except Exception as e:
                print(f"[WARN] RAG search failed: {e}")
        
        # 3. RAG 결과에서 엔티티 추출
        entities = self._extract_entities_from_text(rag_results)
        
        # 4. 그래프에서 관련 엔티티 찾기
        graph_results = []
        if use_graph and self.ontology_manager.graph is not None:
            graph_results = self._find_graph_entities(query, entities)
        
        # 5. 통합 점수 계산 및 정렬
        combined_results = self._combine_results(rag_results, graph_results, query)
        
        # 상위 k개 반환
        return sorted(combined_results, key=lambda x: -x['combined_score'])[:top_k]
    
    def _expand_query_with_ontology(self, query: str) -> List[str]:
        """
        온톨로지를 활용한 질의 확장
        질문 속 키워드와 연관된 온톨로지 용어(Label, Alias)를 찾음
        """
        expanded_terms = set()
        keywords = self._extract_keywords(query)
        
        if not self.ontology_manager.graph:
            return []
            
        # 간단한 매칭 로직 (향후 SPARQL이나 벡터 검색으로 고도화 가능)
        # 여기서는 SemanticInference의 키워드 매핑 활용
        for kw in keywords:
            # 1. 사전 정의된 매핑 확인
            for cat, synonyms in self.semantic_inference.keyword_mappings.items():
                if kw in synonyms or kw == cat:
                    expanded_terms.add(cat)
                    expanded_terms.update(synonyms)
            
            # 2. 온톨로지 레이블 검색 (간단 구현)
            # 실제로는 SPARQL로 rdfs:label이나 skos:altLabel을 검색해야 함
            # 여기서는 성능을 위해 생략하고 SemanticInference 매핑에 의존
        
        # 원본 키워드 제외
        for kw in keywords:
            if kw in expanded_terms:
                expanded_terms.remove(kw)
                
        return list(expanded_terms)[:5] # 최대 5개로 제한

    def _generate_tactical_hypotheses(self, query: str) -> List[str]:
        """
        전술적 가설 수립 (Reasoning-to-RAG)
        질문의 의도에 맞는 전술적 추론 결과를 생성
        """
        hypotheses = []
        
        if self.reasoning_engine:
            # ReasoningEngine의 가설 생성 기능 활용
            # (날씨나 지형 컨텍스트를 아직 전달하지 못하므로 None 처리)
            # 향후 Orchestrator나 StateManager를 통해 컨텍스트 획득 필요
            context = None
            try:
                hypotheses = self.reasoning_engine.analyze_situation_hypothesis(query, context)
            except Exception as e:
                print(f"[WARN] Hypothesis generation failed: {e}")

        return hypotheses

    def _extract_entities_from_text(self, rag_results: List[Dict]) -> List[str]:
        """RAG 결과에서 엔티티 추출"""
        entities = []
        
        for result in rag_results:
            text = result.get('text', '')
            
            # URI 패턴 찾기
            uri_pattern = r'http://[^\s<>"]+'
            uris = re.findall(uri_pattern, text)
            entities.extend(uris)
            
            # 로컬 이름 패턴 찾기 (예: "Enemy_5th_Tank", "Friendly_1st_Armored")
            local_pattern = r'[A-Z][a-zA-Z0-9_]+'
            local_names = re.findall(local_pattern, text)
            entities.extend(local_names)
            
            # 한글 엔티티 패턴 (예: "적 5전차", "아군 1기갑")
            korean_pattern = r'[가-힣]+\s*\d+[가-힣]*'
            korean_entities = re.findall(korean_pattern, text)
            entities.extend(korean_entities)
        
        # 중복 제거
        return list(set(entities))
    
    def _find_graph_entities(self, query: str, entities: List[str]) -> List[Dict]:
        """그래프에서 관련 엔티티 찾기"""
        graph_results = []
        
        if self.ontology_manager.graph is None:
            return graph_results
        
        try:
            # 쿼리에서 키워드 추출
            query_keywords = self._extract_keywords(query)
            
            # 각 엔티티에 대해 그래프 검색
            for entity in entities:
                try:
                    # 의미 기반 관계 추론
                    relations = self.semantic_inference.infer_relations(
                        self.ontology_manager.graph,
                        entity,
                        max_depth=1
                    )
                    
                    # 직접 관계의 관련 엔티티
                    for rel in relations.get('direct', []):
                        related_entity = rel.get('entity', '')
                        if related_entity:
                            # 관련도 계산
                            relevance = self._calculate_relevance(
                                query_keywords,
                                related_entity,
                                relations.get('confidence', 0.5)
                            )
                            
                            
                            # Predicate 정리 (단순화)
                            pred_name = str(rel.get('predicate', '')).split('#')[-1]
                            entity_short = str(entity).split('#')[-1]
                            related_short = str(related_entity).split('#')[-1]
                            
                            description = f"[{entity_short}] --({pred_name})--> [{related_short}]"
                            
                            graph_results.append({
                                'entity': related_entity,
                                'relation': rel.get('predicate', ''),
                                'relevance': relevance,
                                'confidence': relations.get('confidence', 0.5),
                                'description': description, # 설명 추가
                                'type': 'graph'
                            })
                except Exception as e:
                    # 개별 엔티티 검색 실패는 무시
                    continue
        
        except Exception as e:
            print(f"[WARN] Graph search failed: {e}")
        
        return graph_results
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 한글 단어
        korean_words = re.findall(r'[가-힣]+', text)
        # 영문 단어
        english_words = re.findall(r'[A-Za-z]+', text)
        
        return korean_words + [w.lower() for w in english_words]
    
    def _calculate_relevance(self, query_keywords: List[str], entity: str, 
                            confidence: float) -> float:
        """관련도 계산"""
        entity_keywords = self._extract_keywords(entity)
        
        # 키워드 매칭률
        matched = set(query_keywords) & set(entity_keywords)
        if query_keywords:
            keyword_score = len(matched) / len(query_keywords)
        else:
            keyword_score = 0.0
        
        # 신뢰도와 결합
        relevance = keyword_score * 0.7 + confidence * 0.3
        
        return min(1.0, max(0.0, relevance))
    
    def _combine_results(self, rag_results: List[Dict], graph_results: List[Dict], 
                        query: str) -> List[Dict]:
        """RAG와 그래프 결과 통합"""
        combined_results = []
        
        # RAG 결과 추가
        for rag_item in rag_results:
            rag_score = rag_item.get('score', 0.0)
            
            # 그래프 컨텍스트 찾기
            graph_context = self._find_graph_context(rag_item.get('text', ''), graph_results)
            
            # 통합 점수 계산
            combined_score = (
                0.6 * rag_score +  # RAG 점수 (60%)
                0.4 * graph_context.get('relevance', 0.0)  # 그래프 관련도 (40%)
            )
            
            # 메타데이터에 title 보장
            metadata = rag_item.get('metadata', {})
            if 'title' not in metadata:
                if 'source' in metadata:
                    metadata['title'] = str(metadata['source']).split('/')[-1].split('\\')[-1]
                elif metadata.get('type') == 'hypothesis':
                     metadata['title'] = "전술적 추론 가설"
                else:
                    metadata['title'] = f"Doc {metadata.get('doc_id', '?')}"
            
            # 프론트엔드(ChatInterface.tsx) 호환성을 위해 doc_name 추가
            metadata['doc_name'] = metadata['title']
            
            combined_results.append({
                'text': rag_item.get('text', ''),
                'rag_score': rag_score,
                'graph_context': graph_context,
                'combined_score': combined_score,
                'type': metadata.get('type', 'rag'),
                'metadata': metadata
            })
        
        # 그래프 결과 추가 (RAG에 없는 경우)
        for graph_item in graph_results:
            entity = graph_item.get('entity', '')
            description = graph_item.get('description', f"그래프 엔티티: {entity}")
            
            # 이미 RAG 결과에 포함되어 있는지 확인
            already_included = any(
                entity in result.get('text', '') or entity in str(result.get('graph_context', {}))
                for result in combined_results
            )
            
            if not already_included:
                
                graph_title = f"지식 그래프 ({str(entity).split('#')[-1]})"
                
                combined_results.append({
                    'text': description,
                    'rag_score': 0.0,
                    'graph_context': {
                        'entity': entity,
                        'relation': graph_item.get('relation', ''),
                         'relevance': graph_item.get('relevance', 0.0)
                    },
                    'combined_score': graph_item.get('relevance', 0.0) * 0.4,  # 그래프만 있으면 점수 감소
                    'type': 'graph',
                    'metadata': {
                        'source': 'ontology', 
                        'entity': entity,
                        'title': graph_title,
                        'doc_name': graph_title # 프론트엔드 호환성
                    }
                })
        
        return combined_results
    
    def _find_graph_context(self, text: str, graph_results: List[Dict]) -> Dict:
        """텍스트에서 그래프 컨텍스트 찾기"""
        text_lower = text.lower()
        
        best_match = {
            'entity': '',
            'relation': '',
            'relevance': 0.0
        }
        
        for graph_item in graph_results:
            entity = graph_item.get('entity', '')
            relevance = graph_item.get('relevance', 0.0)
            
            # 텍스트에 엔티티가 포함되어 있는지 확인
            if entity.lower() in text_lower or text_lower in entity.lower():
                if relevance > best_match['relevance']:
                    best_match = {
                        'entity': entity,
                        'relation': graph_item.get('relation', ''),
                        'relevance': relevance
                    }
        
        return best_match
