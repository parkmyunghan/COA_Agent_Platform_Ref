# core_pipeline/semantic_inference.py
# -*- coding: utf-8 -*-
"""
Semantic Inference
의미 기반 관계 추론 모듈
팔란티어 방식: 키워드 유사도 기반 관계 발견
"""
from typing import Dict, List, Optional, Set, Tuple
import re


class SemanticInference:
    """의미 기반 관계 추론 클래스"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.similarity_threshold = config.get("similarity_threshold", 0.3)
        
        # 키워드 매핑 (의미적으로 유사한 키워드)
        self.keyword_mappings = {
            '위협': ['threat', '위험', '공격', '적', 'enemy'],
            '방어': ['defense', '보호', '수비', '아군', 'friendly'],
            '자원': ['resource', '자산', 'asset', '물자'],
            '위치': ['location', '장소', '좌표', 'grid', '지역'],
            '화력': ['firepower', '공격력', '무기', 'weapon'],
            '사기': ['morale', '기 morale', '전투력'],
            '상황': ['situation', '상태', '상황', 'condition'],
            '방책': ['coa', 'course', 'action', '전략', 'strategy']
        }
    
    def infer_relations(self, graph, entity: str, max_depth: int = 2) -> Dict:
        """
        의미 기반 관계 추론
        
        Args:
            graph: RDF 그래프 객체
            entity: 엔티티 URI 또는 로컬 이름
            max_depth: 최대 탐색 깊이
        
        Returns:
            {
                'direct': [직접 관계 리스트],
                'indirect': [간접 관계 리스트],
                'depth': 탐색 깊이,
                'confidence': 신뢰도 (0-1)
            }
        """
        if graph is None:
            return {
                'direct': [],
                'indirect': [],
                'depth': 0,
                'confidence': 0.0
            }
        
        # 1단계: 직접 관계 찾기
        direct_relations = self._find_direct_relations(graph, entity)
        
        # 2단계: 간접 관계 찾기 (키워드 유사도 기반)
        indirect_relations = []
        if max_depth > 1:
            indirect_relations = self._find_indirect_relations(
                graph, entity, direct_relations, max_depth - 1
            )
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(entity, direct_relations, indirect_relations)
        
        return {
            'direct': direct_relations,
            'indirect': indirect_relations,
            'depth': max_depth,
            'confidence': confidence
        }
    
    def _find_direct_relations(self, graph, entity: str) -> List[Dict]:
        """직접 관계 찾기"""
        relations = []
        
        try:
            from rdflib import URIRef
            
            print(f"[DEBUG] _find_direct_relations called with entity: {entity}")
            print(f"[DEBUG] Graph has {len(graph)} triples")
            
            # URI 변환
            if not entity.startswith('http://'):
                # [FIXED] Use unified namespace instead of hardcoded defense-ai.kr
                namespace = self.config.get("namespace", "http://coa-agent-platform.org/ontology#")
                # 모든 종류의 공백을 언더바로 치환 (URI 유효성 확보)
                safe_entity = re.sub(r'\s+', '_', entity)
                entity_uri = URIRef(f"{namespace}{safe_entity}")
            else:
                # 이미 URI인 경우에도 공백이 있으면 처리
                safe_entity = re.sub(r'\s+', '_', entity)
                entity_uri = URIRef(safe_entity)
            
            print(f"[DEBUG] Searching for entity_uri: {entity_uri}")
            
            # [FIX] SPARQL 쿼리 파싱 오류 방지를 위해 graph.triples() 사용
            for s, p, o in graph.triples((entity_uri, None, None)):
                if isinstance(o, URIRef):
                    relations.append({
                        'entity': str(o),
                        'predicate': str(p),
                        'type': 'direct'
                    })
            
            for s, p, o in graph.triples((None, None, entity_uri)):
                if isinstance(s, URIRef):
                    relations.append({
                        'entity': str(s),
                        'predicate': str(p),
                        'type': 'direct'
                    })
                
            # 최대 50개까지만 유지
            if len(relations) > 50:
                relations = relations[:50]
            
            print(f"[DEBUG] Found {len(relations)} direct relations")
        
        except Exception as e:
            print(f"[WARN] Direct relation search failed: {e}")
        
        return relations
    
    def _find_indirect_relations(self, graph, entity: str, direct_relations: List[Dict], 
                                 max_depth: int) -> List[Dict]:
        """간접 관계 찾기 (키워드 유사도 기반)"""
        indirect_relations = []
        
        # 직접 관계의 엔티티에서 키워드 추출
        entity_keywords = self._extract_keywords(entity)
        
        for direct_rel in direct_relations:
            related_entity = direct_rel.get('entity', '')
            related_keywords = self._extract_keywords(related_entity)
            
            # [MOD] 키워드 유사도 확인 + 전이적 관계 허용
            # 특정 관계(위치, 소속 등)는 의미 유사도와 상관없이 추론에 포함
            is_transitive = False
            pred_lower = str(direct_rel.get('predicate', '')).lower()
            if any(p in pred_lower for p in ['location', 'partof', 'belongsto', 'has', 'related']):
                is_transitive = True
            
            if is_transitive or self._has_semantic_similarity(entity_keywords, related_keywords):
                # 2단계 관계 탐색
                second_level = self._find_direct_relations(graph, related_entity)
                
                for second_rel in second_level:
                    second_entity = second_rel.get('entity', '')
                    
                    # 중복 및 자기 참조 제거
                    if second_entity != entity and second_entity != related_entity:
                        indirect_relations.append({
                            'entity': second_entity,
                            'predicate': second_rel.get('predicate', ''), 
                            'type': 'indirect',
                            'path': [entity, related_entity, second_entity],
                            'depth': 2
                        })
        
        return indirect_relations

    def _should_exclude_inference(self, entity: str, predicate: str, related_entity: str) -> bool:
        """
        추론에서 제외해야 할 관계인지 확인 (과도한 추론 방지)
        """
        # [NEW] 특정 엔티티 ID 패턴에 대해 민감한 타입 추론 방지
        entity_local = entity.split('#')[-1]
        
        # 기상(WTH), 지형(TERR) 등은 부대(Unit)나 자원(Resource) 타입을 가질 수 없음
        if any(prefix in entity_local for prefix in ['WTH', 'TERR', 'AXIS', 'MSN']):
            # RDF type 추론 제외
            if 'type' in predicate.lower() or predicate.endswith('#type'):
                # 허용된 타입만 패스 (자기 자신 클래스 등)
                allowed_types = ['기상상황', '지형셀', '전장축선', '임무정보', 'Thing', 'NamedIndividual']
                related_local = related_entity.split('#')[-1]
                if related_local not in allowed_types:
                    return True
                    
        return False

    
    def _extract_keywords(self, text: str) -> Set[str]:
        """텍스트에서 키워드 추출"""
        keywords = set()
        
        # URI에서 로컬 이름 추출
        local_name = text.split('#')[-1].split('/')[-1]
        
        # 한글, 영문, 숫자 분리
        korean_words = re.findall(r'[가-힣]+', local_name)
        english_words = re.findall(r'[A-Za-z]+', local_name)
        numbers = re.findall(r'[0-9]+', local_name) # [MOD] 숫자도 키워드로 포함 (ID 매칭 등을 위해)
        
        keywords.update(korean_words)
        keywords.update([w.lower() for w in english_words])
        keywords.update(numbers)  # [FIX] 숫자 추가
        
        return keywords
    
    def _has_semantic_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> bool:
        """키워드 유사도 확인"""
        if not keywords1 or not keywords2:
            return False
        
        # 직접 매칭
        if keywords1 & keywords2:
            return True
        
        # 매핑 기반 유사도 확인
        for kw1 in keywords1:
            for kw2 in keywords2:
                if self._are_similar_keywords(kw1, kw2):
                    return True
        
        return False
    
    def _are_similar_keywords(self, kw1: str, kw2: str) -> bool:
        """두 키워드가 의미적으로 유사한지 확인"""
        # 키워드 매핑에서 확인
        for category, synonyms in self.keyword_mappings.items():
            if kw1 in synonyms and kw2 in synonyms:
                return True
            if kw1 == category and kw2 in synonyms:
                return True
            if kw2 == category and kw1 in synonyms:
                return True
        
        # 부분 문자열 매칭
        if kw1 in kw2 or kw2 in kw1:
            return True
        
        return False
    
    def _calculate_confidence(self, entity: str, direct_relations: List[Dict], 
                              indirect_relations: List[Dict]) -> float:
        """신뢰도 계산"""
        # 직접 관계가 많을수록 높은 신뢰도
        direct_score = min(1.0, len(direct_relations) / 10.0)
        
        # 간접 관계는 신뢰도 감소
        indirect_penalty = min(0.3, len(indirect_relations) * 0.05)
        
        confidence = direct_score - indirect_penalty
        return max(0.0, min(1.0, confidence))
    
    def find_related_entities(self, graph, entity: str, entity_type: Optional[str] = None) -> List[str]:
        """
        관련 엔티티 찾기 (간단한 버전)
        
        Args:
            graph: RDF 그래프
            entity: 엔티티 URI 또는 로컬 이름
            entity_type: 엔티티 타입 필터 (선택적)
        
        Returns:
            관련 엔티티 URI 리스트
        """
        relations = self.infer_relations(graph, entity, max_depth=1)
        
        related_entities = []
        for rel in relations['direct']:
            related_entity = rel.get('entity', '')
            if related_entity:
                related_entities.append(related_entity)
        
        return related_entities
    
    def add_keyword_mapping(self, category: str, synonyms: List[str]):
        """키워드 매핑 추가"""
        if category not in self.keyword_mappings:
            self.keyword_mappings[category] = []
        self.keyword_mappings[category].extend(synonyms)














