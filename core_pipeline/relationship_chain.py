# core_pipeline/relationship_chain.py
# -*- coding: utf-8 -*-
"""
Relationship Chain
다단계 관계 체인 탐색 모듈
팔란티어 방식: 간접 관계를 통한 COA 추천
"""
from typing import Dict, List, Optional, Set, Tuple
from collections import deque


class RelationshipChain:
    """다단계 관계 체인 탐색 클래스"""
    
    @staticmethod
    def _make_uri_safe(name: str) -> str:
        """URI에 사용할 수 있도록 문자열을 변환 (공백과 특수문자 제거)"""
        import re
        if not name:
            return str(name) if name is not None else ""
        s = str(name).strip()
        s = re.sub(r'\s+', '_', s)  # 공백 -> 언더스코어
        s = re.sub(r'[(){}\[\]<>|\\^`"\':;,?#%&+=]', '', s)  # 특수문자 제거
        s = re.sub(r'_+', '_', s)  # 연속 언더스코어 정리
        s = s.strip('_')
        return s if s else "unknown"
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.max_depth = self.config.get("max_chain_depth", 3)
        self.max_paths = self.config.get("max_paths", 10)
    
    def find_relationship_chains(self, graph, start_entity: str, target_type: str, 
                                max_depth: Optional[int] = None) -> List[Dict]:
        """
        다단계 관계 체인 발견
        
        Args:
            graph: RDF 그래프 객체
            start_entity: 시작 엔티티 URI 또는 로컬 이름
            target_type: 목표 타입 (예: "def:COA", "def:FriendlyUnit")
            max_depth: 최대 탐색 깊이 (기본값: self.max_depth)
        
        Returns:
            체인 리스트 [{
                'path': [엔티티 리스트],
                'target': 목표 엔티티,
                'depth': 깊이,
                'predicates': [관계 리스트],
                'score': 체인 점수
            }]
        """
        if graph is None:
            return []
        
        if max_depth is None:
            max_depth = self.max_depth
        
        chains = []
        visited = set()
        
        # BFS로 체인 탐색
        queue = deque([(start_entity, [start_entity], [], 0)])
        visited.add(start_entity)
        
        while queue and len(chains) < self.max_paths:
            current, path, predicates, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            # 현재 엔티티의 관계 탐색
            relations = self._find_relations(graph, current)
            
            for rel in relations:
                related_entity = rel.get('entity', '')
                predicate = rel.get('predicate', '')
                
                if not related_entity:
                    continue
                
                # 목표 타입 확인
                if self._is_target_type(graph, related_entity, target_type):
                    # 체인 발견
                    chain_path = path + [related_entity]
                    chain_predicates = predicates + [predicate]
                    
                    score = self._calculate_chain_score(
                        chain_path, chain_predicates, depth + 1
                    )
                    
                    chains.append({
                        'path': chain_path,
                        'target': related_entity,
                        'depth': depth + 1,
                        'predicates': chain_predicates,
                        'score': score
                    })
                else:
                    # 중복 방지 (같은 경로는 다시 탐색하지 않음)
                    if related_entity not in visited:
                        visited.add(related_entity)
                        queue.append((
                            related_entity,
                            path + [related_entity],
                            predicates + [predicate],
                            depth + 1
                        ))
        
        # 점수 순으로 정렬
        chains.sort(key=lambda x: -x['score'])
        
        return chains
    
    def _find_relations(self, graph, entity: str) -> List[Dict]:
        """엔티티의 관계 찾기 (SPARQL 대신 direct triples lookup으로 최적화)"""
        relations = []
        
        try:
            from rdflib import URIRef
            
            # URI 변환
            if not entity.startswith('http://'):
                safe_entity = self._make_uri_safe(entity)
                entity_uri = URIRef(f"http://coa-agent-platform.org/ontology#{safe_entity}")
            else:
                entity_uri = URIRef(entity)
            
            # 1. 아웃고잉 관계 (Subject -> ?o)
            for s, p, o in graph.triples((entity_uri, None, None)):
                relations.append({
                    'entity': str(o),
                    'predicate': str(p)
                })
            
            # 2. 인커밍 관계 (?s -> Object)
            for s, p, o in graph.triples((None, None, entity_uri)):
                relations.append({
                    'entity': str(s),
                    'predicate': str(p)
                })
        
        except Exception as e:
            print(f"[WARN] Relation search failed for {entity}: {e}")
        
        return relations
    
    def _is_target_type(self, graph, entity: str, target_type: str) -> bool:
        """엔티티가 목표 타입인지 확인"""
        try:
            from rdflib import URIRef, RDF
            
            # URI 변환 (안전한 문자열로 변환)
            if not entity.startswith('http://'):
                safe_entity = self._make_uri_safe(entity)
                entity_uri = URIRef(f"http://coa-agent-platform.org/ontology#{safe_entity}")
            else:
                entity_uri = URIRef(entity)
            
            # 타입 확인 (안전한 문자열로 변환)
            if not target_type.startswith('http://'):
                # ns: 또는 def: 접두사 제거
                safe_target = self._make_uri_safe(target_type.replace('ns:', '').replace('def:', ''))
                target_uri = URIRef(f"http://coa-agent-platform.org/ontology#{safe_target}")
            else:
                target_uri = URIRef(target_type)
            
            # [REFACTORED] SPARQL ASK 대신 graph.triples() 사용 (pyparsing 오류 우회)
            return (entity_uri, RDF.type, target_uri) in graph
        
        except Exception:
            # 타입 확인 실패 시 부분 문자열 매칭
            target_name = target_type.split('#')[-1].split('/')[-1]
            entity_name = entity.split('#')[-1].split('/')[-1]
            return target_name.lower() in entity_name.lower() or entity_name.lower() in target_name.lower()
    
    def _calculate_chain_score(self, path: List[str], predicates: List[str], 
                               depth: int) -> float:
        """체인 점수 계산"""
        # 깊이가 얕을수록 높은 점수
        depth_score = 1.0 / (depth + 1)
        
        # 경로 길이 (적절한 길이일수록 높은 점수)
        path_length_score = 1.0 / (len(path) + 1)
        
        # 관계의 의미 (특정 관계일수록 높은 점수)
        predicate_score = self._calculate_predicate_score(predicates)
        
        # 종합 점수
        total_score = (
            depth_score * 0.5 +
            path_length_score * 0.3 +
            predicate_score * 0.2
        )
        
        return min(1.0, max(0.0, total_score))
    
    def _calculate_predicate_score(self, predicates: List[str]) -> float:
        """관계(프레디케이트) 점수 계산"""
        if not predicates:
            return 0.5
        
        # 의미 있는 관계일수록 높은 점수
        meaningful_predicates = [
            'hasRelation', 'relatedTo', 'requiresResource',
            'hasAvailableResource', 'hasSuitableCOA', 'compatibleWith'
        ]
        
        score = 0.0
        for pred in predicates:
            pred_name = pred.split('#')[-1].split('/')[-1]
            if pred_name in meaningful_predicates:
                score += 0.2
            else:
                score += 0.1
        
        return min(1.0, score / len(predicates))
    
    def find_path(self, graph, start_entity: str, target_entity: str, max_depth: Optional[int] = None) -> List[Dict]:
        """
        두 엔티티 간의 구체적인 경로 탐색
        
        Args:
            graph: RDF 그래프
            start_entity: 시작 엔티티 (위협)
            target_entity: 목표 엔티티 (COA)
            max_depth: 최대 깊이
            
        Returns:
            발견된 경로 리스트
        """
        if graph is None:
            return []
            
        if max_depth is None:
            max_depth = self.max_depth
            
        # 목표 엔티티가 명확하므로 BFS로 도달 가능한 모든 경로 탐색
        chains = []
        visited = set()
        
        # URI 정규화
        from rdflib import URIRef
        
        # start_entity URI
        if not start_entity.startswith('http://'):
            safe_start = self._make_uri_safe(start_entity)
            start_uri = f"http://coa-agent-platform.org/ontology#{safe_start}"
        else:
            start_uri = start_entity
            
        # target_entity URI
        if not target_entity.startswith('http://'):
            safe_target = self._make_uri_safe(target_entity)
            target_uri = f"http://coa-agent-platform.org/ontology#{safe_target}"
        else:
            target_uri = target_entity
            
        # BFS (경로 추적 포함)
        queue = deque([(start_uri, [start_uri], [], 0)])
        visited.add(start_uri)
        
        # 목표 URI의 로컬 이름 (비교 용이성을 위해)
        target_local_name = target_uri.split('#')[-1].split('/')[-1].lower()
        
        while queue and len(chains) < self.max_paths:
            current, path, predicates, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            # 현재 엔티티의 관계 탐색
            relations = self._find_relations(graph, str(current))
            
            for rel in relations:
                related_entity = rel.get('entity', '')
                predicate = rel.get('predicate', '')
                
                if not related_entity:
                    continue
                
                # 목표 도달 확인 (정확한 URI 매칭 또는 이름 포함 매칭)
                is_target = False
                if related_entity == target_uri:
                    is_target = True
                else:
                    # URI 불일치 시 로컬 이름으로 비교 (유연성)
                    related_local = related_entity.split('#')[-1].split('/')[-1].lower()
                    if related_local == target_local_name:
                        is_target = True
                    # COA ID 매칭 (ID가 포함된 경우)
                    elif target_local_name in related_local:
                        is_target = True
                
                if is_target:
                    # 경로 발견
                    chain_path = path + [related_entity]
                    chain_predicates = predicates + [predicate]
                    
                    score = self._calculate_chain_score(
                        chain_path, chain_predicates, depth + 1
                    )
                    
                    chains.append({
                        'path': chain_path,
                        'target': related_entity,
                        'depth': depth + 1,
                        'predicates': chain_predicates,
                        'score': score
                    })
                else:
                    # 순환 방지
                    if related_entity not in path and depth + 1 < max_depth:
                        # visited를 전체 공유하면 다른 경로를 못 찾으므로, 
                        # 현재 경로 내에서의 순환만 체크 (path check)
                        queue.append((
                            related_entity,
                            path + [related_entity],
                            predicates + [predicate],
                            depth + 1
                        ))
        
        # 점수 순 정렬
        chains.sort(key=lambda x: -x['score'])
        return chains

    def find_coa_chains(self, graph, threat_entity: str, target_coa: Optional[str] = None) -> List[Dict]:
        """
        위협 엔티티에서 COA까지의 체인 찾기
        
        Args:
            graph: RDF 그래프
            threat_entity: 위협 엔티티 URI
            target_coa: (선택) 특정 COA 엔티티 URI. 지정 시 해당 COA로 가는 경로만 탐색
        
        Returns:
            COA 체인 리스트
        """
        if target_coa:
            # 특정 COA로 가는 경로 탐색
            return self.find_path(
                graph,
                start_entity=threat_entity,
                target_entity=target_coa,
                max_depth=self.max_depth
            )
        else:
            # 기존 동작: 모든 COA 탐색
            return self.find_relationship_chains(
                graph,
                start_entity=threat_entity,
                target_type="ns:COA",  # 통일된 네임스페이스 사용
                max_depth=self.max_depth
            )
    
    def find_resource_chains(self, graph, coa_entity: str) -> List[Dict]:
        """
        COA에서 필요한 자원까지의 체인 찾기
        
        Args:
            graph: RDF 그래프
            coa_entity: COA 엔티티 URI 또는 로컬 이름
        
        Returns:
            자원 체인 리스트
        """
        return self.find_relationship_chains(
            graph,
            start_entity=coa_entity,
            target_type="ns:Resource",
            max_depth=2
        )
    
    def find_asset_chains(self, graph, location_entity: str) -> List[Dict]:
        """
        위치에서 방어 자산까지의 체인 찾기
        
        Args:
            graph: RDF 그래프
            location_entity: 위치 엔티티 URI 또는 로컬 이름
        
        Returns:
            자산 체인 리스트
        """
        return self.find_relationship_chains(
            graph,
            start_entity=location_entity,
            target_type="ns:FriendlyUnit",
            max_depth=2
        )
    
    def get_chain_summary(self, chains: List[Dict]) -> Dict:
        """
        체인 요약 정보
        
        Args:
            chains: 체인 리스트
        
        Returns:
            요약 딕셔너리
        """
        if not chains:
            return {
                'total_chains': 0,
                'avg_depth': 0.0,
                'avg_score': 0.0,
                'best_chain': None
            }
        
        total_chains = len(chains)
        avg_depth = sum(c['depth'] for c in chains) / total_chains
        avg_score = sum(c['score'] for c in chains) / total_chains
        best_chain = chains[0] if chains else None
        
        return {
            'total_chains': total_chains,
            'avg_depth': round(avg_depth, 2),
            'avg_score': round(avg_score, 4),
            'best_chain': best_chain
        }

    def find_common_node_chains(self, graph, start_entity: str, target_entity: str) -> List[Dict]:
        """
        두 엔티티가 공유하는 공통 노드(Context) 탐색
        Pattern: Threat -> [Common] <- COA
        
        Args:
            graph: RDF 그래프
            start_entity: 시작 엔티티 (위협)
            target_entity: 목표 엔티티 (COA)
            
        Returns:
            발견된 체인 리스트
        """
        if graph is None:
            return []
            
        chains = []
        
        # 1. Start Entity의 1-hop 관계 조회
        start_relations = self._find_relations(graph, start_entity)
        
        # 2. Target Entity의 1-hop 관계 조회
        target_relations = self._find_relations(graph, target_entity)
        
        # 3. 공통 노드 찾기
        # {entity_uri: (predicate_from_start, predicate_from_target)}
        # URI 기반 매칭뿐만 아니라 로컬 이름 기반 매칭도 지원하여 유연성 확보
        start_nodes = {r['entity']: r['predicate'] for r in start_relations}
        target_nodes = {r['entity']: r['predicate'] for r in target_relations}
        
        # URI 직접 매칭
        common_uris = set(start_nodes.keys()) & set(target_nodes.keys())
        
        # 로컬 이름 매칭 (URI가 다르더라도 이름이 같으면 동일 개념으로 간주)
        # 예: ns:침투 (URI) vs "침투" (Literal/URI mismatch)
        start_names = {idx.split('#')[-1]: idx for idx in start_nodes.keys()}
        target_names = {idx.split('#')[-1]: idx for idx in target_nodes.keys()}
        common_names = set(start_names.keys()) & set(target_names.keys())
        
        # 4. 체인 구성 (중복 제거를 위해 set 사용)
        from rdflib import URIRef
        
        # 모든 공통 노드 후보 통합
        processed_commons = set()
        
        # URI 매칭 처리
        for common in common_uris:
            processed_commons.add(common)
            self._add_chain_if_not_generic(common, start_nodes[common], target_nodes[common], start_entity, target_entity, chains)
            
        # 로컬 이름 매칭 처리 (URI 매칭에서 누락된 것들)
        for name in common_names:
            start_uri = start_names[name]
            target_uri = target_names[name]
            if start_uri not in processed_commons and target_uri not in processed_commons:
                processed_commons.add(start_uri)
                processed_commons.add(target_uri)
                self._add_chain_if_not_generic(start_uri, start_nodes[start_uri], target_nodes[target_uri], start_entity, target_entity, chains)
                
        return chains

    def _add_chain_if_not_generic(self, common, pred_start, pred_target, start_entity, target_entity, chains):
        """범용 노드가 아닌 경우 체인에 추가"""
        # Skip if common node is too generic
        common_str = str(common)
        if any(x in common_str for x in ["NamedIndividual", "Thing", "Class", "Ontology"]):
            return
            
        # Common node label for scoring
        common_local = common_str.split('#')[-1]
        
        # Score calculation
        base_score = 0.5
        if "TERR" in common_local: base_score += 0.2 # Shared Terrain
        if "Unit" in common_local: base_score += 0.2 # Shared Unit Type
        if "Threat" in common_local or "COA" in common_local: base_score += 0.1 # Domain match
        
        chains.append({
            'path': [start_entity, common_str, target_entity],
            'target': target_entity,
            'depth': 2,
            'predicates': [pred_start, f"(shared via) {pred_target}"],
            'score': min(0.9, base_score),
            'type': 'common_context'
        })














