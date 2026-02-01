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
        
        # 2. SPARQL 기반 온톨로지 검색 (관계 추론)
        sparql_results = self._search_with_sparql(query)
        
        # 3. 구조화된 데이터 검색 (부대 현황 등)
        structured_results = self._search_structured_entities(query)
        
        # 3. RAG 검색 (문서 기반)
        rag_results = []
        if self.rag_manager.is_available():
            try:
                # 확장된 쿼리로 검색
                rag_results = self.rag_manager.retrieve_with_context(expanded_query, top_k=top_k)
                
                # SPARQL 결과 추가 (LLM 참조용)
                if sparql_results:
                    for res in sparql_results:
                        rag_results.append(res)
                
                # 구조화된 데이터 결과 추가 (LLM 참조용)
                if structured_results:
                    for res in structured_results:
                         rag_results.append(res)
                
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
        
        # 4. RAG 결과에서 엔티티 추출
        entities = self._extract_entities_from_text(rag_results)
        
        # 5. 그래프에서 관련 엔티티 찾기
        graph_results = []
        if use_graph and self.ontology_manager.graph is not None:
            graph_results = self._find_graph_entities(query, entities)
        
        # 6. 통합 점수 계산 및 정렬
        combined_results = self._combine_results(rag_results, graph_results, query)
        
        # 상위 k개 반환
        return sorted(combined_results, key=lambda x: -x['combined_score'])[:top_k]

    def _search_structured_entities(self, query: str) -> List[Dict]:
        """
        사용자 질의에서 구조화된 엔티티(부대, 자산, 위협, 지형 등) 관련 키워드 감지 시 DB/Excel 직접 조회
        이는 온톨로지의 원천 데이터를 검색하여 팩트 기반 답변을 보장함
        """
        results = []
        
        # 키워드 매핑 정의 (Intent-to-Table)
        intent_map = {
            "friendly_unit": {
                "keywords": ["아군", "우리 부대", "부대 현황", "부대 정보", "유닛", "자산", "친선", "우리 측"],
                "table": "아군부대현황",
                "title": "아군 부대 현황",
                "format_fn": self._format_friendly_unit
            },
            "threat_situation": {
                "keywords": ["위협", "적군", "적군 부대", "침투", "공격", "위험", "상황"],
                "table": "위협상황",
                "title": "현재 위협 상황",
                "format_fn": self._format_threat_situation
            },
            "terrain_cell": {
                "keywords": ["지형", "지역", "지질", "축선", "지형 정보"],
                "table": "지형셀",
                "title": "지형 정보 (셀 단위)",
                "format_fn": self._format_terrain_cell
            },
            "friendly_asset": {
                "keywords": ["가용 자산", "장비", "무기", "화력"],
                "table": "아군가용자산",
                "title": "아군 가용 자산",
                "format_fn": self._format_friendly_asset
            }
        }
        
        try:
            # OntologyManager를 통해 DataManager에 접근
            if not (hasattr(self.ontology_manager, 'data_manager') and self.ontology_manager.data_manager):
                return results

            dm = self.ontology_manager.data_manager
            
            for intent, config in intent_map.items():
                if any(kw in query for kw in config["keywords"]):
                    table_df = dm.load_table(config["table"])
                    if table_df is not None and not table_df.empty:
                        # 데이터가 너무 많으면 상위 N개만 추출 또는 요약
                        display_df = table_df.head(10)
                        
                        formatted_text = config["format_fn"](display_df)
                        
                        results.append({
                            "text": f"[{config['title']} (시스템 실시간 데이터)]\n{formatted_text}",
                            "score": 1.0,
                            "metadata": {
                                "type": f"structured_{intent}",
                                "source": "system_database",
                                "title": config["title"],
                                "doc_name": config["title"]
                            }
                        })
                        print(f"[INFO] PalantirSearch: Injected structured data from '{config['table']}'")
                        
        except Exception as e:
            print(f"[WARN] Structured search failed: {e}")
                
        return results

    def _format_friendly_unit(self, df) -> str:
        lines = []
        for _, row in df.iterrows():
            status = row.get('가용상태', row.get('상태', '가용'))
            lines.append(f"- {row.get('부대명', 'Unknown')} ({row.get('병종', '-')}): {row.get('임무역할', '-')}, {row.get('상급부대', '-')} 배속, {row.get('배치축선ID', '-')} 일대 ({status})")
        return "\n".join(lines)

    def _format_threat_situation(self, df) -> str:
        lines = []
        for _, row in df.iterrows():
            lines.append(f"- 위협(ID: {row.get('위협ID', row.get('threat_id', '-'))}): {row.get('위협명', '-')}, 유형: {row.get('위협유형', '-')}, 위협수준: {row.get('위협수준', '-')}, {row.get('발생지역', '-')} 일대")
        return "\n".join(lines)

    def _format_terrain_cell(self, df) -> str:
        lines = []
        for _, row in df.iterrows():
            lines.append(f"- {row.get('지형명', row.get('terrain_name', 'Unknown'))}: 유형: {row.get('지형유형', '-')}, 좌표: ({row.get('위도', '-')}, {row.get('경도', '-')}), 영향: {row.get('지형영향', '-')}")
        return "\n".join(lines)

    def _format_friendly_asset(self, df) -> str:
        lines = []
        for _, row in df.iterrows():
            lines.append(f"- {row.get('자산명', 'Unknown')}: 종류: {row.get('자산종류', '-')}, 화력: {row.get('화력지수', '-')}, 가용: {row.get('가용여부', '-')}")
        return "\n".join(lines)

    def _search_with_sparql(self, query: str) -> List[Dict]:
        """
        LLM을 사용하여 자연어를 SPARQL로 변환하고, 온톨로지 그래프를 쿼리한 뒤
        결과를 자연어 컨텍스트로 반환합니다.
        """
        results = []
        
        # 관계 추론이 필요한 쿼리 패턴 감지
        # 예: "~의 상급부대는?", "~에 배치된 부대는?", "~와 관련된 ~"
        relation_keywords = ["상급", "하급", "배치", "배속", "연결", "관련", "소속", "위치한", "어떤"]
        
        if not any(kw in query for kw in relation_keywords):
            return results  # 관계 질문이 아니면 스킵 (기존 방식 사용)
        
        if self.ontology_manager.graph is None:
            return results
            
        try:
            # 1. LLM을 사용하여 NL -> SPARQL 변환
            # (LLM Manager에 직접 접근하기 위해 Orchestrator를 통해 접근해야 함)
            # 현재 PalantirSearch는 ontology_manager만 가지고 있으므로,
            # 간단한 패턴 기반 SPARQL 생성을 먼저 시도
            sparql_query = self._generate_simple_sparql(query)
            
            if not sparql_query:
                return results
            
            # 2. SPARQL 실행
            print(f"[INFO] PalantirSearch: Executing SPARQL query for: {query[:50]}...")
            try:
                sparql_results = self.ontology_manager.graph.query(sparql_query)
            except Exception as e:
                print(f"[WARN] SPARQL execution failed: {e}")
                return results
            
            # 3. 결과 파싱 및 자연어로 변환
            result_lines = ["[온톨로지 관계 분석 결과(SPARQL)]"]
            row_count = 0
            for row in sparql_results:
                row_count += 1
                if row_count > 10:  # 최대 10개
                    result_lines.append(f"... 외 {len(list(sparql_results)) - 10}개 추가 결과")
                    break
                
                # 각 변수를 읽어서 라인으로 변환
                row_parts = []
                for var in sparql_results.vars:
                    val = row[var]
                    if val:
                        # URI에서 로컬 이름만 추출
                        val_str = str(val).split('#')[-1].split('/')[-1]
                        row_parts.append(f"{var}: {val_str}")
                
                if row_parts:
                    result_lines.append(f"- {', '.join(row_parts)}")
            
            if row_count > 0:
                results.append({
                    "text": "\n".join(result_lines),
                    "score": 0.95,  # 높은 신뢰도
                    "metadata": {
                        "type": "sparql_inference",
                        "source": "ontology_graph",
                        "title": "온톨로지 관계 분석",
                        "doc_name": "온톨로지 관계 분석"
                    }
                })
                print(f"[INFO] PalantirSearch: SPARQL returned {row_count} results")
            else:
                print(f"[INFO] PalantirSearch: SPARQL returned no results")
                
        except Exception as e:
            print(f"[WARN] SPARQL search failed: {e}")
            
        return results

    def _generate_simple_sparql(self, query: str) -> Optional[str]:
        """
        자연어 질문에서 간단한 SPARQL 쿼리를 패턴 매칭으로 생성합니다.
        복잡한 질문은 None을 반환하여 fallback 합니다.
        """
        ns = "http://coa-agent-platform.org/ontology#"
        
        # 패턴 1: "X의 상급부대는?" or "X 상급부대"
        if "상급부대" in query or "상급 부대" in query:
            # 부대명 추출 시도
            unit_name = None
            patterns = [r"([가-힣0-9]+(?:사단|여단|대대|중대|연대|군단))", r"([가-힣]+부대)"]
            for pat in patterns:
                match = re.search(pat, query)
                if match:
                    unit_name = match.group(1)
                    break
            
            if unit_name:
                return f"""
PREFIX def: <{ns}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?unit ?unitName ?superior WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?unitName .
  ?unit def:상급부대 ?superior .
  FILTER(CONTAINS(?unitName, "{unit_name}"))
}}
"""
        
        # 패턴 2: "X에 배치된 부대" or "X 축선의 부대"
        if "배치된" in query or "축선" in query:
            axis_match = re.search(r"([가-힣]+축선|AXIS\d+)", query)
            if axis_match:
                axis_name = axis_match.group(1)
                return f"""
PREFIX def: <{ns}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?unit ?unitName ?axisName WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?unitName .
  ?unit def:has전장축선 ?axis .
  ?axis rdfs:label ?axisName .
  FILTER(CONTAINS(?axisName, "{axis_name}"))
}}
"""
        
        # 패턴 3: "위협 수준이 높은" or "고위협"
        if "위협" in query and ("높은" in query or "고위협" in query or "심각" in query):
            return f"""
PREFIX def: <{ns}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?threat ?threatName ?level ?location WHERE {{
  ?threat a def:위협상황 .
  ?threat rdfs:label ?threatName .
  ?threat def:위협수준 ?level .
  OPTIONAL {{ ?threat def:발생장소 ?location }}
  FILTER(?level = "High" || ?level = "심각")
}}
"""
        
        # 패턴 4: 일반적인 부대 정보 조회
        if "어떤" in query and ("부대" in query or "병력" in query):
            return f"""
PREFIX def: <{ns}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?unit ?unitName ?type ?role ?superior WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?unitName .
  OPTIONAL {{ ?unit def:병종 ?type }}
  OPTIONAL {{ ?unit def:임무역할 ?role }}
  OPTIONAL {{ ?unit def:상급부대 ?superior }}
}} LIMIT 10
"""
        
        return None
    
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
