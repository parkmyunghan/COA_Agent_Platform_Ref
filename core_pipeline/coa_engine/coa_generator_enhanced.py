# core_pipeline/coa_engine/coa_generator_enhanced.py
# -*- coding: utf-8 -*-
"""
Enhanced COA Generator
온톨로지/AI 기능이 통합된 COA 생성기
**하이브리드 방식**: 규칙 기반 기본 생성 + 온톨로지/RAG 기반 보강
"""
from typing import List, Dict, Optional
from core_pipeline.data_models import AxisState
from core_pipeline.coa_engine.coa_models import COA
from core_pipeline.coa_engine.coa_generator import COAGenerator
from core_pipeline.coa_engine.coa_llm_adapter import COALLMAdapter


class EnhancedCOAGenerator(COAGenerator):
    """온톨로지/AI 기능이 통합된 COA 생성기
    
    하이브리드 방식:
    - 규칙 기반 기본 생성 (핵심): 신뢰성 확보
    - 온톨로지/RAG 기반 보강 (Vertical AI): 도메인 지식 활용
    """
    
    def __init__(self, ontology_manager=None, rag_manager=None, 
                 llm_manager=None, relationship_chain=None,
                 use_llm_assistance: bool = False,
                 enable_ontology_enhancement: bool = True,
                 template_loader=None):
        """
        Args:
            ontology_manager: OntologyManager 인스턴스 (추론 보강용)
            rag_manager: RAGManager 인스턴스 (추론 보강용)
            llm_manager: LLMManager 인스턴스 (보조 레이어: 설명문 생성용)
            relationship_chain: RelationshipChain 인스턴스 (추론 보강용)
            use_llm_assistance: LLM 보조 생성 사용 여부 (기본값: False)
            enable_ontology_enhancement: 온톨로지 기반 보강 활성화 여부 (기본값: True)
            template_loader: 방책템플릿 로더 인스턴스 (선택적)
        """
        super().__init__(use_llm_assistance=False, llm_manager=None, template_loader=template_loader)  # 핵심 로직은 규칙 기반만
        self.ontology_manager = ontology_manager
        self.rag_manager = rag_manager
        self.relationship_chain = relationship_chain
        self.enable_ontology_enhancement = enable_ontology_enhancement
        
        # LLM 어댑터 초기화
        self.llm_adapter = COALLMAdapter(
            llm_manager=llm_manager,
            rag_manager=rag_manager
        )
    
    def generate_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        user_params: Optional[Dict] = None
    ) -> List[COA]:
        """
        COA 생성 메서드 오버라이드
        온톨로지 기능이 활성화된 경우 generate_coas_with_ontology를 호출
        """
        if self.enable_ontology_enhancement and self.ontology_manager:
            return self.generate_coas_with_ontology(mission_id, axis_states, user_params)
        else:
            # 온톨로지 기능이 비활성화된 경우 기본 생성 메서드 사용
            return super().generate_coas(mission_id, axis_states, user_params)
    
    def generate_coas_with_ontology(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        user_params: Optional[Dict] = None
    ) -> List[COA]:
        """
        온톨로지/AI 기능을 활용한 COA 생성 (하이브리드 방식)
        
        **하이브리드 방식**:
        - 규칙 기반 기본 생성 (핵심): 신뢰성 확보
        - 온톨로지/RAG 기반 보강 (Vertical AI): 도메인 지식 활용
        
        Args:
            mission_id: 임무ID
            axis_states: 축선별 전장상태 요약 리스트
            user_params: 사용자 설정 파라미터
        
        Returns:
            COA 후보 리스트 (규칙 기반 + 온톨로지/RAG 보강)
        """
        # 1. 규칙 기반 COA 생성 (핵심 로직) - 항상 실행
        # 부모 클래스의 generate_coas를 직접 호출하여 무한 재귀 방지
        from core_pipeline.coa_engine.coa_generator import COAGenerator
        rule_based_coas = COAGenerator.generate_coas(self, mission_id, axis_states, user_params)
        
        # 2. 온톨로지 기반 COA 보강 (추론 보강, 선택적)
        all_coas = list(rule_based_coas)
        if self.enable_ontology_enhancement:
            ontology_coas = self._search_coas_from_ontology(mission_id, axis_states)
            ontology_variants = self._generate_ontology_variants(rule_based_coas, axis_states, mission_id)
            all_coas.extend(ontology_coas)
            all_coas.extend(ontology_variants)
        
        # 3. RAG 기반 과거 사례 적용 (추론 보강)
        if self.rag_manager and self.rag_manager.is_available():
            rag_references = self._get_rag_references(mission_id, axis_states, user_params)
            # RAG 참고 자료를 COA 메타데이터에 저장
            for coa in all_coas:
                if not hasattr(coa, 'rag_references'):
                    coa.rag_references = []
                coa.rag_references.extend(rag_references[:2])  # 상위 2개만
        
        # 4. 통합 및 중복 제거
        merged_coas = self._merge_and_deduplicate_coas(all_coas)
        
        # 최대 개수 제한
        max_coas = (user_params or {}).get('max_coas', 5)
        return merged_coas[:max_coas]
    
    def _search_coas_from_ontology(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        use_owl_inference: bool = True
    ) -> List[COA]:
        """온톨로지 그래프에서 COA 검색 (추론 보강)
        
        Args:
            mission_id: 임무 ID
            axis_states: 축선별 전장상태
            use_owl_inference: OWL-RL 추론 사용 여부 (기본값: True)
        """
        if not self.ontology_manager or not self.ontology_manager.graph:
            return []
        
        coas = []
        
        # 위협레벨이 높은 축선의 위협상황 ID 추출
        high_threat_axes = [a for a in axis_states if a.threat_level == 'High']
        # High가 없으면 Medium, Low 순으로 검색
        if not high_threat_axes:
            high_threat_axes = [a for a in axis_states if a.threat_level == 'Medium']
        if not high_threat_axes:
            high_threat_axes = [a for a in axis_states if a.threat_level == 'Low']
            
        if not high_threat_axes:
            return []
        
        # 첫 번째 주요 축선의 위협상황 사용
        threat_events = high_threat_axes[0].threat_events
        if not threat_events:
            return []
        
        threat_id = threat_events[0].threat_id
        # 위협 유형 가져오기 (threat_type_original 우선, 없으면 threat_type_code)
        threat_type = getattr(threat_events[0], 'threat_type_original', None) or getattr(threat_events[0], 'threat_type_code', '')
        
        # 사용할 그래프 결정 (추론 포함 여부)
        graph_to_use = self.ontology_manager.graph
        if use_owl_inference:
            try:
                from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
                
                if OWLRL_AVAILABLE:
                    namespace = str(self.ontology_manager.ns) if hasattr(self.ontology_manager, 'ns') and self.ontology_manager.ns else None
                    reasoner = OWLReasoner(self.ontology_manager.graph, namespace)
                    inferred_graph = reasoner.run_inference()
                    
                    if inferred_graph is not None:
                        graph_to_use = inferred_graph
                        print(f"[INFO] OWL-RL 추론 그래프 사용: {len(inferred_graph)} triples (원본: {len(self.ontology_manager.graph)})")
            except Exception as e:
                print(f"[WARN] OWL-RL 추론 실패, 원본 그래프 사용: {e}")
        
        # SPARQL 쿼리로 COA 검색
        try:
            results = []
            from rdflib import URIRef, RDFS, Literal
            
            # 1. 위협 유형 매칭 (문자열 매칭)
            # ?coa :적합위협유형 ?type . FILTER ...
            if threat_type:
                print(f"[DEBUG] _search_coas_from_ontology: threat_type='{threat_type}'")
                
                # [DEBUG] Check if any triples with 적합위협유형 exist
                # debug_prop = URIRef(f"{self.ontology_manager.ns}적합위협유형")
                # ... (Removed verbose usage)


                # 1단계: 직접적인 적합위협유형 또는 키워드/적용조건/설명 검색 (Regex)
                query = f"""
                PREFIX coa: <{self.ontology_manager.ns}>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT DISTINCT ?coa ?label
                WHERE {{
                    ?coa a coa:COA .
                    {{
                        {{ ?coa coa:적합위협유형 ?type . }}
                        UNION
                        {{ ?coa coa:키워드 ?type . }}
                        UNION
                        {{ ?coa coa:적용조건 ?type . }}
                        UNION
                        {{ ?coa coa:설명 ?type . }}
                        UNION
                        {{ ?coa rdfs:label ?type . }}
                        
                        OPTIONAL {{ ?coa rdfs:label ?label }}
                        FILTER (regex(str(?type), "{threat_type}", "i") || regex(str(?label), "{threat_type}", "i"))
                    }}
                }}
                """
                
                try:
                    qres = graph_to_use.query(query)
                    for row in qres:
                        res = {'coa': str(row.coa), 'coaLabel': str(row.label) if row.label else '', 'source': 'sparql_regex'}
                        results.append(res)
                except Exception as e:
                    print(f"[WARN] SPARQL Regex Query failed: {e}")

                # [FALLBACK] Regex 검색 결과가 없으면 Exact Match 시도 (더 단순한 쿼리)
                if not results:
                    print(f"[DEBUG] Regex search yielded 0 results. Trying Exact Match for '{threat_type}'...")
                    query_exact = f"""
                    PREFIX coa: <{self.ontology_manager.ns}>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    SELECT DISTINCT ?coa ?label
                    WHERE {{
                        ?coa a coa:COA .
                        ?coa coa:적합위협유형 ?type .
                        OPTIONAL {{ ?coa rdfs:label ?label }}
                        FILTER (str(?type) = "{threat_type}")
                    }}
                    """
                    try:
                        qres_exact = graph_to_use.query(query_exact)
                        for row in qres_exact:
                            res = {'coa': str(row.coa), 'coaLabel': str(row.label) if row.label else '', 'source': 'sparql_exact'}
                            results.append(res)
                        print(f"[DEBUG] Exact match found {len(results)} results.")
                    except Exception as e:
                        print(f"[WARN] SPARQL Exact Query failed: {e}")
            
            # 2. 직접 관계: respondsTo (인스턴스 직접 연결)
            threat_node = URIRef(f"{self.ontology_manager.ns}{threat_id}")
            responds_to = URIRef(f"{self.ontology_manager.ns}respondsTo")
            for coa_node, p, o in graph_to_use.triples((None, responds_to, threat_node)):
                res = {'coa': str(coa_node), 'source': 'direct_respondsTo'}
                for label in graph_to_use.objects(coa_node, RDFS.label):
                    res['coaLabel'] = str(label)
                results.append(res)
            
            # 3. OWL-RL 추론 관계 활용 (역관계, 속성체인 등)
            if use_owl_inference:
                try:
                    # 위협이 위치한 지형셀 찾기
                    threat_cell_prop = URIRef(f"{self.ontology_manager.ns}locatedIn")
                    threat_cells = list(graph_to_use.objects(threat_node, threat_cell_prop))
                    
                    # 지형셀을 통해 작전 가능한 부대 찾기 (속성체인: 부대→축선→지형셀)
                    operational_area_prop = URIRef(f"{self.ontology_manager.ns}작전가능지역")
                    for cell in threat_cells:
                        # 해당 지형셀에서 작전 가능한 부대 찾기
                        for unit, p, cell_obj in graph_to_use.triples((None, operational_area_prop, cell)):
                            # 부대가 할당된 임무 찾기
                            mission_prop = URIRef(f"{self.ontology_manager.ns}hasMission")
                            for mission in graph_to_use.objects(unit, mission_prop):
                                # 임무에 연관된 COA 찾기
                                coa_prop = URIRef(f"{self.ontology_manager.ns}hasRelatedCOA")
                                for coa_node, p2, mission_obj in graph_to_use.triples((None, coa_prop, mission)):
                                    if (coa_node, None, None) in graph_to_use:
                                        res = {'coa': str(coa_node), 'source': 'owl_inferred_chain'}
                                        for label in graph_to_use.objects(coa_node, RDFS.label):
                                            res['coaLabel'] = str(label)
                                        results.append(res)
                except Exception as e:
                    print(f"[WARN] OWL 추론 관계 검색 실패: {e}")
            
            # 중복 제거 (URI 기준)
            unique_results = {r['coa']: r for r in results}.values()
            
            for result in unique_results:
                coa_uri = result.get('coa', '')
                coa_label = result.get('coaLabel', '')
                
                if coa_uri:
                    # COA 객체 생성
                    coa = COA(
                        coa_id=coa_uri.split('#')[-1] if '#' in coa_uri else str(coa_uri),
                        coa_name=coa_label or "온톨로지 COA",
                        description=f"온톨로지 지식그래프 기반 추천 (적합위협: {threat_type})",
                        mission_id=mission_id,
                        created_by="ontology_search"
                    )
                    
                    # 추론 흔적 추가
                    source_type = result.get('source', 'unknown')
                    trace = [
                        f"1. 위협 상황 분석: 위협ID '{threat_id}', 위협유형 '{threat_type}' 식별",
                    ]
                    
                    if source_type == 'owl_inferred_chain':
                        trace.append(f"2. OWL-RL 추론: 위협→지형셀→작전가능지역→부대→임무→COA 경로 추론")
                    elif source_type == 'direct_respondsTo':
                        trace.append(f"2. 직접 관계 검색: respondsTo 속성으로 COA 발견")
                    else:
                        trace.append(f"2. 지식그래프 검색: '적합위협유형' 속성에서 '{threat_type}' 검색 ({source_type})")
                    
                    if coa_label:
                        trace.append(f"3. 방책 매칭 성공: '{coa_label}' ({coa.coa_id}) 도출")
                    else:
                        trace.append(f"3. 방책 매칭 성공: {coa.coa_id} 도출")
                        
                    coa.reasoning_trace = trace
                    
                    # 추가 속성 로드 (ontology_score 등)
                    coa.ontology_score = 0.95
                    coa.suitability_score = 0.95
                    
                    # 필요 자원 로드
                    resources = []
                    # ns.필요자원
                    needed_res_prop = URIRef(f"{self.ontology_manager.ns}필요자원")
                    for o in self.ontology_manager.graph.objects(URIRef(coa_uri), needed_res_prop):
                         resources.append(str(o))
                    
                    if resources:
                        coa.required_resources = resources
                        coa.reasoning_trace.append(f"4. 자원 추론: 필요 자원 {resources} 자동 도출")
                        
                    coas.append(coa)
        except Exception as e:
            print(f"[WARN] 온톨로지 COA 검색 실패: {e}")
        
        return coas
    
    def _generate_ontology_variants(
        self,
        rule_based_coas: List[COA],
        axis_states: List[AxisState],
        mission_id: str
    ) -> List[COA]:
        """온톨로지 속성 기반 COA 변형 제안 (추론 보강)"""
        if not self.ontology_manager or not self.ontology_manager.graph:
            return []
        
        variants = []
        
        # 규칙 기반 COA를 기반으로 온톨로지 속성 확인하여 변형 제안
        for coa in rule_based_coas[:2]:  # 상위 2개만
            try:
                coa_uri = f"http://defense-ai.kr/ontology#{coa.coa_id}"
                
                # 온톨로지에서 유사 COA 검색
                results = []
                from rdflib import URIRef, RDFS
                coa_node = URIRef(f"http://defense-ai.kr/ontology#{coa.coa_id}")
                similar_to = URIRef("http://defense-ai.kr/ontology#similarTo")
                for variant_node, p, o in self.ontology_manager.graph.triples((None, similar_to, coa_node)):
                    res = {'variant': str(variant_node)}
                    for label in self.ontology_manager.graph.objects(variant_node, RDFS.label):
                        res['variantLabel'] = str(label)
                    results.append(res)
                results = results[:2]
                
                for result in results:
                    variant_uri = result.get('variant', '')
                    variant_label = result.get('variantLabel', '')
                    
                    if variant_uri:
                        variant = COA(
                            coa_id=variant_uri.split('#')[-1] if '#' in variant_uri else str(variant_uri),
                            coa_name=f"{coa.coa_name} 변형: {variant_label or '온톨로지 변형'}",
                            description=f"온톨로지 그래프에서 발견된 {coa.coa_name}의 변형",
                            mission_id=mission_id,
                            created_by="ontology_variant"
                        )
                        variants.append(variant)
            except Exception as e:
                print(f"[WARN] 온톨로지 변형 생성 실패: {e}")
        
        return variants
    
    def _merge_and_deduplicate_coas(self, coa_lists: List[COA]) -> List[COA]:
        """COA 리스트 통합 및 중복 제거"""
        seen_ids = set()
        merged = []
        
        for coa in coa_lists:
            if coa.coa_id not in seen_ids:
                seen_ids.add(coa.coa_id)
                merged.append(coa)
        
        return merged
    
    def get_doctrine_references(
        self,
        coa: COA,
        axis_states: List[AxisState],
        top_k: int = 3
    ) -> List[Dict]:
        """
        COA에 대한 교범/지침 참고 자료 검색 (보조 레이어)
        
        Args:
            coa: COA 객체
            axis_states: 축선별 전장상태 리스트
            top_k: 반환할 상위 k개 결과
            
        Returns:
            교범/지침 참고 자료 리스트
        """
        return self.llm_adapter.search_similar_cases(coa, axis_states, top_k=top_k)
    
    def _get_rag_references(self, mission_id: str, axis_states: List[AxisState], user_params: Optional[Dict] = None) -> List[Dict]:
        """
        RAG 검색으로 과거 사례 참조 (보조 레이어: 참고 자료만)
        
        참고: 이 메서드는 COA 생성에 직접 영향을 주지 않고, 참고 자료만 반환합니다.
        """
        if not self.rag_manager or not self.rag_manager.is_available():
            return []
        
        # 위협상황 요약
        threat_summary = self._build_threat_summary(axis_states)
        
        # 작전지역 정보 확인
        operation_area = ""
        if user_params and user_params.get('operation_area'):
            operation_area = f"작전지역: {user_params['operation_area']}."
            
        # [NEW] 시간 정보 확인 및 환경 요인 추론
        time_context = ""
        if user_params and user_params.get('start_time'):
            try:
                from datetime import datetime
                # 문자열 파싱 시도 (다양한 포맷 대응)
                start_str = str(user_params['start_time'])
                dt = None
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                    try:
                        dt = datetime.strptime(start_str.split('.')[0], fmt)
                        break
                    except: pass
                
                if dt:
                    month = dt.month
                    hour = dt.hour
                    
                    # 계절 추론
                    season = "겨울" if month in [12, 1, 2] else \
                             "봄" if month in [3, 4, 5] else \
                             "여름" if month in [6, 7, 8] else "가을"
                    
                    # 주간/야간 추론
                    day_night = "야간" if hour < 6 or hour >= 19 else "주간"
                    
                    time_context = f"계절: {season}, 시간: {day_night} 작전."
            except Exception as e:
                print(f"[WARN] 시간 정보 파싱 실패: {e}")
        
        # RAG 검색 (교범/지침 검색)
        try:
            # 쿼리에 작전지역 정보 및 시간/계절 정보 추가하여 정확도 향상
            query = f"임무 {mission_id}에 대한 방어 전략. {operation_area} {time_context} {threat_summary}"
            results = self.llm_adapter.search_references(query, top_k=5)
            return results
        except Exception as e:
            print(f"[WARN] RAG 검색 실패: {e}")
            return []
    
    def _build_threat_summary(self, axis_states: List[AxisState]) -> str:
        """위협상황 요약 생성 (보조 레이어)"""
        summaries = []
        for axis in axis_states:
            if axis.threat_events:
                # [NEW] 마스터 데이터(설명) 활용
                threat_descs = []
                for t in axis.threat_events:
                    # 마스터 데이터 설명이 있으면 우선 사용
                    if t.description:
                        desc = f"{t.threat_name or t.threat_type_code}: {t.description}"
                    else:
                        desc = t.threat_type_code or "Unknown Threat"
                    threat_descs.append(desc)
                
                if threat_descs:
                    # 중복 제거
                    unique_descs = list(dict.fromkeys(threat_descs))
                    summaries.append(f"{axis.axis_name}: {', '.join(unique_descs)}")
                    
        return "; ".join(summaries) if summaries else ""

