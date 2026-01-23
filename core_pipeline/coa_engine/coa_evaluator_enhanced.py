# core_pipeline/coa_engine/coa_evaluator_enhanced.py
# -*- coding: utf-8 -*-
"""
Enhanced COA Evaluator
온톨로지/AI 기능이 통합된 COA 평가기
**하이브리드 방식**: 규칙 기반 기본 점수 (60-70%) + 추론 보강 점수 (30-40%)
"""
from typing import List, Dict, Optional
from core_pipeline.data_models import AxisState
from core_pipeline.coa_engine.coa_models import COA
from core_pipeline.coa_engine.coa_evaluator import COAEvaluator, COAEvaluationResult
from core_pipeline.coa_engine.coa_llm_adapter import COALLMAdapter


class EnhancedCOAEvaluator(COAEvaluator):
    """온톨로지/AI 기능이 통합된 COA 평가기
    
    하이브리드 방식:
    - 규칙 기반 기본 점수 (60-70%): 신뢰성 확보
    - 추론 보강 점수 (30-40%): Vertical AI (온톨로지/RAG/체인/LLM)
    """
    
    # 추론 보강 점수 가중치 (기본값)
    DEFAULT_REASONING_WEIGHTS = {
        'ontology': 0.40,      # 온톨로지 기반 효과성 (40%)
        'historical': 0.30,    # RAG 기반 과거 성공률 (30%)
        'chain': 0.20,         # 관계 체인 점수 (20%)
        'llm_fitness': 0.10    # LLM 기반 상황 적합성 (10%)
    }
    
    def __init__(self, ontology_manager=None, rag_manager=None, 
                 llm_manager=None, relationship_chain=None,
                 reasoning_engine=None,  # [NEW] ReasoningEngine 추가
                 weights: Optional[Dict[str, float]] = None,
                 base_score_weight: float = 0.7,
                 reasoning_weights: Optional[Dict[str, float]] = None):
        """
        Args:
            ontology_manager: OntologyManager 인스턴스
            rag_manager: RAGManager 인스턴스
            llm_manager: LLMManager 인스턴스
            relationship_chain: RelationshipChain 인스턴스
            reasoning_engine: ReasoningEngine 인스턴스 (동적 추론용)
            ...
        """
        super().__init__(weights)
        self.ontology_manager = ontology_manager
        self.rag_manager = rag_manager
        self.llm_manager = llm_manager
        self.relationship_chain = relationship_chain
        self.reasoning_engine = reasoning_engine # [NEW] 저장
        
        # 가중치 설정
        self.base_score_weight = base_score_weight
        self.reasoning_score_weight = 1.0 - base_score_weight
        
        # 추론 보강 점수 가중치 설정
        if reasoning_weights:
            total = sum(reasoning_weights.values())
            if total > 0:
                self.reasoning_weights = {k: v / total for k, v in reasoning_weights.items()}
            else:
                self.reasoning_weights = self.DEFAULT_REASONING_WEIGHTS.copy()
        else:
            self.reasoning_weights = self.DEFAULT_REASONING_WEIGHTS.copy()
        
        # LLM 어댑터 초기화
        self.llm_adapter = COALLMAdapter(
            llm_manager=llm_manager,
            rag_manager=rag_manager
        )

    def evaluate_single_coa(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        coa: COA
    ) -> COAEvaluationResult:
        """단일 COA 평가 (참고 자료 수집 및 추론 보강 점수 반영)"""
        # 1. 기본 평가 수행 (부모 클래스)
        result = super().evaluate_single_coa(mission_id, axis_states, coa)
        
        # 2. 추론 보강 점수 계산
        ontology_score = self._get_ontology_effectiveness_score(coa, axis_states, mission_id)
        historical_score = self._get_historical_success_rate(coa, axis_states)
        chain_score = self._get_chain_score(coa, axis_states, mission_id)
        llm_score = self._get_llm_fitness_score(coa, axis_states)
        
        # 3. 가중치 적용하여 추론 점수 합산
        reasoning_score = (
            ontology_score * self.reasoning_weights.get('ontology', 0.4) +
            historical_score * self.reasoning_weights.get('historical', 0.3) +
            chain_score * self.reasoning_weights.get('chain', 0.2) +
            llm_score * self.reasoning_weights.get('llm_fitness', 0.1)
        )
        
        # 4. 최종 점수 계산 (기본 점수 + 추론 점수)
        final_score = (
            result.total_score * self.base_score_weight +
            reasoning_score * self.reasoning_score_weight
        )
        
        # 5. 결과 업데이트
        result.total_score = final_score
        
        # 상세 점수 정보 추가
        result.details.update({
            'base_score_raw': f"{result.total_score:.4f}",
            'ontology_score': f"{ontology_score:.4f}",
            'historical_score': f"{historical_score:.4f}",
            'chain_score': f"{chain_score:.4f}",
            'llm_score': f"{llm_score:.4f}",
            'reasoning_score_total': f"{reasoning_score:.4f}"
        })
        
        # 6. 참고 자료 수집 및 주입
        try:
             refs = self._collect_reference_info(coa, axis_states)
             if refs:
                 result.doctrine_references = refs.get('doctrine_references', [])
                 result.similar_cases = refs.get('similar_cases', [])
        except Exception as e:
             print(f"[WARN] 참고 자료 수집 중 오류: {e}")
            
        return result

    # ... [중간 생략] ...

    def _get_ontology_effectiveness_score(
        self,
        coa: COA,
        axis_states: List[AxisState],
        mission_id: str
    ) -> float:
        """온톨로지 기반 효과성 점수 (동적 추론 적용 + 추론결과 반영)"""
        base_effectiveness = 0.5
        inferred_bonus = 0.0  # [NEW] 추론 결과 기반 보너스
        
        if self.ontology_manager and self.ontology_manager.graph:
            try:
                # SPARQL 쿼리로 COA 속성 조회 (기본 효과성)
                coa_id = coa.coa_id
                # Extract ID if it's a URI
                coa_id_raw = str(coa_id).split('#')[-1] if '#' in str(coa_id) else str(coa_id)
                
                if not coa_id_raw.startswith("COA_Library_"):
                    safe_id = f"COA_Library_{coa_id_raw}"
                else:
                    safe_id = coa_id_raw
                    
                coa_uri = f"http://coa-agent-platform.org/ontology#{safe_id}"
                
                # [NEW] ontology_manager가 있을 때 _make_uri_safe가 있다면 적용
                if hasattr(self.ontology_manager, '_make_uri_safe'):
                    # URI 자체를 safe하게 만드는 게 아니라 path를 safe하게
                    safe_name = self.ontology_manager._make_uri_safe(safe_id)
                    coa_uri = f"http://coa-agent-platform.org/ontology#{safe_name}"
                
                results = []
                from rdflib import URIRef
                coa_node = URIRef(coa_uri)
                effectiveness_prop = URIRef("http://coa-agent-platform.org/ontology#effectiveness")
                for val in self.ontology_manager.graph.objects(coa_node, effectiveness_prop):
                    results.append({'effectiveness': str(val)})
                if results and results[0].get('effectiveness'):
                    effectiveness = float(results[0]['effectiveness'])
                    # 0-100 범위를 0-1로 정규화
                    if effectiveness > 1.0:
                        effectiveness = effectiveness / 100.0
                    base_effectiveness = min(1.0, max(0.0, effectiveness))
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # [NEW] 추론 결과(ns:적용가능지역) 활용
                # 온톨로지 스튜디오에서 실행한 도메인 규칙 추론 결과를 반영합니다.
                # RULE_COA_001, RULE_COA_002에 의해 ns:적용가능지역 관계가 추론됨
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                applicable_regions_prop = URIRef("http://coa-agent-platform.org/ontology#적용가능지역")
                applicable_regions = list(self.ontology_manager.graph.objects(coa_node, applicable_regions_prop))
                
                if applicable_regions:
                    # 현재 축선의 지형셀과 비교
                    current_terrain_cells = set()
                    for axis_state in axis_states:
                        if hasattr(axis_state, 'terrain_cells') and axis_state.terrain_cells:
                            for cell in axis_state.terrain_cells:
                                cell_id = getattr(cell, 'terrain_cell_id', None) or str(cell)
                                current_terrain_cells.add(cell_id)
                        # 대안: axis_id에서 지형셀 추출 시도
                        if hasattr(axis_state, 'axis_id'):
                            # 해당 축선의 지형셀 조회 (온톨로지 그래프에서)
                            axis_uri = URIRef(f"http://coa-agent-platform.org/ontology#전장축선_{axis_state.axis_id}")
                            terrain_cell_prop = URIRef("http://coa-agent-platform.org/ontology#has지형셀")
                            for cell in self.ontology_manager.graph.objects(axis_uri, terrain_cell_prop):
                                cell_str = str(cell).split('#')[-1] if '#' in str(cell) else str(cell)
                                current_terrain_cells.add(cell_str)
                    
                    if current_terrain_cells:
                        # 적용가능지역과 현재 지형셀 일치 비율 계산
                        applicable_set = set()
                        for region in applicable_regions:
                            region_str = str(region).split('#')[-1] if '#' in str(region) else str(region)
                            applicable_set.add(region_str)
                        
                        matching_regions = applicable_set.intersection(current_terrain_cells)
                        if matching_regions:
                            # 일치하는 지역이 있으면 보너스 점수 (최대 0.2)
                            match_ratio = len(matching_regions) / len(current_terrain_cells)
                            inferred_bonus = min(0.2, match_ratio * 0.3)
                            print(f"[INFO] COA {coa_id}: 추론 결과 적용가능지역 {len(matching_regions)}개 일치, 보너스 +{inferred_bonus:.2f}")
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                
            except Exception as e:
                print(f"[WARN] 온톨로지 효과성 점수 조회 실패: {e}")
        
        # [NEW] 동적 추론 적용 (ReasoningEngine 사용)
        if self.reasoning_engine:
            try:
                # 컨텍스트 구성 (실제로는 지형/기상 정보를 AxisState나 환경 변수에서 가져와야 함)
                # 여기서는 시뮬레이션을 위해 일부 값을 추정하거나 AxisState에서 추출
                context = {
                    'base_score': base_effectiveness + inferred_bonus,  # [MODIFIED] 추론 보너스 포함
                    'terrain': 'Plains', # 기본값
                    'weather': 'Clear'   # 기본값
                }
                
                # AxisState에서 지형 정보 추출 시도
                if axis_states:
                    # 첫 번째 축선의 지형 정보를 사용한다고 가정
                    # 실제로는 더 정교한 로직 필요 (축선별 지형 분석)
                    first_axis = axis_states[0]
                    # axis_name이나 속성에서 지형 유추 (예시)
                    if '산악' in str(first_axis.axis_name) or '험지' in str(first_axis.axis_name):
                        context['terrain'] = 'Mountains'
                    elif '도시' in str(first_axis.axis_name):
                        context['terrain'] = 'Urban'
                
                dynamic_score = self.reasoning_engine.calculate_dynamic_score(coa, context)
                return min(1.0, dynamic_score + inferred_bonus)  # [MODIFIED] 보너스 합산
            except Exception as e:
                print(f"[WARN] 동적 추론 실패: {e}")
                return min(1.0, base_effectiveness + inferred_bonus)  # [MODIFIED]
        
        return min(1.0, base_effectiveness + inferred_bonus)  # [MODIFIED]

    
    def _get_historical_success_rate(
        self,
        coa: COA,
        axis_states: List[AxisState]
    ) -> float:
        """RAG 기반 과거 성공률"""
        if not self.rag_manager or not self.rag_manager.is_available():
            return 0.5  # 기본값
        
        try:
            # COA 관련 문서 검색
            query = f"{coa.coa_name or coa.coa_id} 성공 사례"
            results = self.rag_manager.retrieve_with_context(query, top_k=5)
            
            if results:
                # 성공 키워드 비율 계산
                success_keywords = ['성공', '효과적', '승리', '완료', '달성', '효과']
                success_count = sum(
                    1 for r in results
                    if any(kw in str(r.get('text', '')).lower() for kw in success_keywords)
                )
                return success_count / len(results) if results else 0.5
            
            return 0.5
        except Exception as e:
            print(f"[WARN] 과거 성공률 계산 실패: {e}")
            return 0.5
    
    def _get_chain_score(
        self,
        coa: COA,
        axis_states: List[AxisState],
        mission_id: str
    ) -> float:
        """관계 체인 점수"""
        if not self.relationship_chain or not self.ontology_manager:
            return 0.5  # 기본값
        
        try:
            # 위협상황 ID 추출
            threat_events = []
            for axis in axis_states:
                threat_events.extend(axis.threat_events)
            
            if not threat_events:
                return 0.5
            
            threat_id = threat_events[0].threat_id
            graph = self.ontology_manager.graph
            
            if not graph:
                return 0.5
            
            # 위협 엔티티 URI 구성 (온톨로지의 '위협상황_' 접두어 반영)
            threat_uri = f"http://coa-agent-platform.org/ontology#위협상황_{threat_id}"
            
            # COA 체인 탐색
            chains = self.relationship_chain.find_coa_chains(graph, threat_uri)
            
            # 체인 점수 계산
            if chains:
                # 해당 COA와 관련된 체인 찾기
                coa_id = coa.coa_id
                # Extract ID if it's a URI
                coa_id_raw = str(coa_id).split('#')[-1] if '#' in str(coa_id) else str(coa_id)
                
                if not coa_id_raw.startswith("COA_Library_"):
                    safe_id = f"COA_Library_{coa_id_raw}"
                else:
                    safe_id = coa_id_raw
                
                if hasattr(self.ontology_manager, '_make_uri_safe'):
                    safe_id = self.ontology_manager._make_uri_safe(safe_id)
                
                coa_uri = f"http://coa-agent-platform.org/ontology#{safe_id}"
                coa_chains = [
                    c for c in chains
                    if coa_uri in str(c.get('target', '')) or coa.coa_id in str(c.get('target', ''))
                ]
                
                if coa_chains:
                    avg_score = sum(c.get('score', 0.5) for c in coa_chains) / len(coa_chains)
                    return min(1.0, max(0.0, avg_score))
                else:
                    # 관련 체인이 없으면 평균 점수 사용 (간접 관계 반영)
                    if chains:
                        avg_score = sum(c.get('score', 0.5) for c in chains) / len(chains)
                        return min(1.0, max(0.0, avg_score * 0.7))  # 간접 관계는 70% 가중치
            
            return 0.5
        except Exception as e:
            print(f"[WARN] 체인 점수 계산 실패: {e}")
            return 0.5
    
    def _get_llm_fitness_score(
        self,
        coa: COA,
        axis_states: List[AxisState]
    ) -> float:
        """LLM 기반 상황 적합성 점수"""
        # self.llm_manager를 직접 사용 (llm_adapter를 통하지 않음)
        if not self.llm_manager or not self.llm_manager.is_available():
            return 0.5  # 기본값
        
        try:
            # 위협상황 요약
            threat_summary = []
            for axis in axis_states:
                if axis.threat_events:
                    threat_types = [t.threat_type_code for t in axis.threat_events if t.threat_type_code]
                    if threat_types:
                        threat_summary.append(f"{axis.axis_name}: {', '.join(set(threat_types))}")
            
            # LLM 프롬프트 구성
            prompt = f"""다음 COA가 현재 상황에 얼마나 적합한지 0-100 점수로 평가하세요.

COA: {coa.coa_name or coa.coa_id}
설명: {coa.description or 'N/A'}

현재 상황:
{'; '.join(threat_summary) if threat_summary else 'N/A'}

점수만 숫자로 응답하세요 (예: 75)"""
            
            response = self.llm_manager.generate(prompt, max_tokens=10)
            
            # 점수 추출
            import re
            score_match = re.search(r'\d+', response)
            if score_match:
                score = int(score_match.group())
                return min(1.0, max(0.0, score / 100.0))
            
            return 0.5
        except Exception as e:
            print(f"[WARN] LLM 적합성 점수 계산 실패: {e}")
            return 0.5
    
    def _collect_reference_info(self, coa: COA, axis_states: List[AxisState]) -> Dict:
        """
        참고 자료 수집 (메타데이터) - UI 표시용 포맷팅 포함
        
        참고: 이 메서드는 점수에 영향을 주지 않고, 참고 자료만 수집합니다.
        """
        reference_info = {
            'doctrine_references': [],
            'similar_cases': []
        }
        
        all_refs = []
        
        # 1. 교범/지침 참고 자료 검색
        try:
            # 쿼리 한국어 명시 및 번역 강화
            coa_name = coa.coa_name or coa.coa_id
            
            # 간단한 영-한 번역 매핑 (검색 품질 향상용)
            term_map = {
                "Defense": "방어 작전", "Main_Defense": "주방어 작전", "Delay": "지연 작전",
                "Offense": "공격 작전", "Counter_Attack": "반격 작전", "Maneuver": "기동 작전",
                "Ambush": "매복 작전", "Blocking": "차단 작전", "Screening": "경계 작전"
            }
            
            # 이름에 영어가 포함되어 있으면 번역 시도
            search_term = coa_name
            for eng, kor in term_map.items():
                if eng.lower() in coa_name.lower():
                    search_term = kor
                    break
            
            query_str = f"{search_term} 수행 절차 및 교리 지침"
            
            doctrine_refs = self.llm_adapter.search_references(
                query=query_str,
                top_k=3,
                coa_context=coa
            )
            
            for r in doctrine_refs:
                meta = r.get('metadata', {})
                # 메타데이터에서 값 우선 추출, 없으면 결과 자체에서 추출 (llm_services 수정 사항 반영)
                statement_id = meta.get('statement_id') or r.get('statement_id') or meta.get('id') or meta.get('chunk_id', 'REF')
                doctrine_id = meta.get('doctrine_id') or r.get('doctrine_id') or meta.get('source', 'Unknown Doc')
                mett_c = meta.get('mett_c_elements') or r.get('mett_c_elements') or meta.get('mett_c', [])
                
                all_refs.append({
                    'reference_type': 'doctrine',
                    'text': r.get('text', ''),
                    'excerpt': r.get('text', '')[:300] + ("..." if len(r.get('text', '')) > 300 else ""),
                    'relevance_score': r.get('score', 0.0),
                    'statement_id': statement_id,
                    'doctrine_id': doctrine_id,
                    'mett_c_elements': mett_c,
                    'source': r.get('source', 'doctrine') # source 필드 명시적 추가
                })
            
                
        except Exception as e:
            print(f"[WARN] 교범 참고 자료 검색 실패: {e}")
        
        # [FALLBACK] 검색 결과가 없거나 실패했을 경우 기본 교리 데이터 제공 (명확한 출처 표기)
        if not all_refs:
            # search_term이 정의되지 않았을 수 있으므로 안전하게 가져오기
            term_map = {
                "Defense": "방어 작전", "Main_Defense": "주방어 작전", "Delay": "지연 작전",
                "Offense": "공격 작전", "Counter_Attack": "반격 작전", "Maneuver": "기동 작전",
                "Ambush": "매복 작전", "Blocking": "차단 작전", "Screening": "경계 작전"
            }
            coa_name_safe = getattr(coa, 'coa_name', '') or getattr(coa, 'coa_id', 'Unknown')
            search_term_safe = coa_name_safe
            for eng, kor in term_map.items():
                if eng.lower() in coa_name_safe.lower():
                    search_term_safe = kor
                    break
                    
            fallback_refs = [
                {
                    'reference_type': 'doctrine',
                    'excerpt': f"[시스템 예시] 실제 RAG 검색 결과가 없습니다. 이 내용은 기능 확인을 위한 예시입니다.\n'{search_term_safe}' 수행 시 지휘관은 가용 부대의 전투력을 통합하여 적의 중심을 타격해야 한다.",
                    'relevance_score': 0.0,
                    'statement_id': 'EXAMPLE-001',
                    'doctrine_id': '검색 결과 없음 (예시 데이터)',
                    'mett_c_elements': ['Mission', 'Resources']
                },
                {
                    'reference_type': 'doctrine',
                    'excerpt': "[시스템 예시] 방어 작전의 성공 요건은 적절한 예비대 운용과 적의 공격 기세를 꺾는 시적절한 화력 집중이다.",
                    'relevance_score': 0.0,
                    'statement_id': 'EXAMPLE-002',
                    'doctrine_id': '작전 일반 (예시)',
                    'mett_c_elements': ['Troops', 'Time']
                }
            ]
            all_refs.extend(fallback_refs)
        
        # 2. 유사 작전 사례 검색
        try:
            similar_cases = self.llm_adapter.search_similar_cases(coa, axis_states, top_k=3)
            
            formatted_cases = []
            for r in similar_cases:
                meta = r.get('metadata', {})
                case_item = {
                    'reference_type': 'general',
                    'source': meta.get('source', '과거 전훈 분석'),
                    'text': r.get('text', ''),
                    'excerpt': r.get('text', '')[:300] + ("..." if len(r.get('text', '')) > 300 else ""),
                    'relevance_score': r.get('score', 0.0),
                    'mett_c_elements': meta.get('mett_c', [])
                }
                all_refs.append(case_item)
                formatted_cases.append(case_item)
            
            reference_info['similar_cases'] = formatted_cases
            
        except Exception as e:
            print(f"[WARN] 유사 사례 검색 실패: {e}")
        
        # UI는 'doctrine_references' 리스트에 통합된 데이터를 기대함
        reference_info['doctrine_references'] = all_refs
        
        return reference_info

