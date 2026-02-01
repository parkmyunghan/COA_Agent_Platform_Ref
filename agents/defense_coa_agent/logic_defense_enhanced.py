# agents/defense_coa_agent/logic_defense_enhanced.py
# -*- coding: utf-8 -*-
"""
Enhanced Defense COA Agent Logic
현재 시스템의 SituationAgent, COALibraryAgent 로직 통합
"""
import os
import sys
import pandas as pd
from typing import Dict, List, Optional, Tuple
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'core_pipeline'))
sys.path.insert(0, os.path.join(BASE_DIR, 'agents'))
sys.path.insert(0, os.path.join(BASE_DIR, 'config'))

from agents.base_agent import BaseAgent
from agents.defense_coa_agent.rule_engine import RuleEngine
from api.utils.code_label_mapper import get_mapper


def safe_print(msg, also_log_file: bool = True, logger_name: Optional[str] = None):
    """안전한 출력 함수 (개선된 버전 사용)"""
    from common.utils import safe_print as _safe_print
    # logger_name이 제공되지 않으면 기본값 사용
    if logger_name is None:
        logger_name = "DefenseCOAAgent"
    _safe_print(msg, also_log_file=also_log_file, logger_name=logger_name)


class EnhancedDefenseCOAAgent(BaseAgent):
    """강화된 방책추천 에이전트 (현재 시스템 로직 통합)"""
    
    def __init__(self, core, **kwargs):
        super().__init__(core, **kwargs)
        
        # 데이터 캐시 (data_manager를 통해 로드된 데이터 재사용)
        self._data_cache = None
        
        # 추천 히스토리 (상황 변화 추적용)
        self.recommendation_history = []
        
        # 🔥 NEW: 체인 탐색 캐시 (성능 최적화)
        self._chain_cache = {}
        
        # 규칙 엔진 초기화
        self.rule_engine = RuleEngine()
        
        # 지원하는 방책 타입 정의
        self.supported_coa_types = [
            "defense", "offensive", "counter_attack", 
            "preemptive", "deterrence", "maneuver", "information_ops"
        ]
        
        # 🔥 NEW: 가독성 개선을 위한 코드-라벨 매퍼 주입
        self.mapper = get_mapper()
        
        # 콜백 함수 저장
        self.status_callback = None
        
        # 🔥 NEW: 브랜드/진행률 캐시
        self._last_progress = 0
        
        # 🔥 NEW: 교리 인용 서비스 초기화 (선택적)
        self.doctrine_ref_service = None
        if hasattr(core, 'rag_manager') and core.rag_manager:
            try:
                from core_pipeline.coa_engine.doctrine_reference_service import DoctrineReferenceService
                from core_pipeline.coa_engine.llm_services import DoctrineSearchService
                doctrine_search_service = DoctrineSearchService(core.rag_manager)
                self.doctrine_ref_service = DoctrineReferenceService(
                    rag_manager=core.rag_manager,
                    doctrine_search_service=doctrine_search_service
                )
                safe_print("[INFO] 교리 인용 서비스 초기화 완료")
            except Exception as e:
                safe_print(f"[WARN] 교리 인용 서비스 초기화 실패: {e}")

    def _report_status(self, msg: str, progress: Optional[int] = None):
        """진행 상황 보고
        
        Args:
            msg: 상태 메시지
            progress: 진행률 (0-100)
        """
        # 진행률 업데이트 또는 캐시 사용
        if progress is not None:
            self._last_progress = progress
        else:
            # progress가 None이면 이전 진행율 유지 (초기값이 없으면 0)
            if not hasattr(self, '_last_progress'):
                self._last_progress = 0
            progress = self._last_progress
            
        display_msg = f"[{progress}%] {msg}" if progress is not None else msg
        if self.status_callback:
            try:
                # 콜백이 progress 인자를 지원하는지 확인하거나, 메시지에 포함하여 전달
                import inspect
                sig = inspect.signature(self.status_callback)
                if 'progress' in sig.parameters:
                    # [FIX] progress가 None이 아니거나 이전 진행율이 있으면 항상 전달
                    self.status_callback(msg, progress=progress)
                else:
                    self.status_callback(display_msg)
                # [FIX] 디버깅: 진행상황 보고 확인
                safe_print(f"[DEBUG] _report_status: {progress}% - {msg}")
            except Exception as e:
                # [FIX] Streamlit 스레드 세이프티 처리
                # Worker Thread에서 호출될 경우 st.session_state 접근 시 에러가 발생하며, 
                # 이 에러는 스레드 환경에서 불가피하므로 사용자 경고 로그를 생략합니다.
                err_text = str(e)
                if not err_text or "session_state" in err_text.lower() or "context" in err_text.lower():
                    # 스레드 호출 오류일 가능성이 높음 - 디버그 시에만 확인
                    # safe_print(f"[DEBUG] status_callback skip (Thread context): {repr(e)}")
                    pass
                else:
                    safe_print(f"[WARN] status_callback 호출 실패: {err_text}")
        # 로거에도 남김
        safe_print(f"[STATUS] {display_msg}")
    
    def _safe_float(self, value, default=0.0):
        """안전한 float 변환 (TypeError 방지)"""
        try:
            if value is None: return default
            return float(value)
        except (ValueError, TypeError):
            return default

    def _safe_str(self, value, default=""):
        """안전한 str 변환 (TypeError 방지)"""
        if value is None: return default
        return str(value)

    def execute_reasoning(self, situation_id: Optional[str] = None, **kwargs) -> Dict:
        """
        방어 COA 추론 실행 (현재 시스템 로직 통합)
        
        Args:
            situation_id: 상황 ID (위협ID, 선택적)
            **kwargs: 추가 인자
                - use_palantir_mode: 팔란티어 모드 사용 여부
                - enable_rag_search: RAG 검색 활성화
                - use_embedding: 임베딩 사용 여부
                - use_reasoned_graph: 추론된 그래프 사용 여부
                - user_query: 사용자 질문 (situation_id가 없을 때 사용)
                - selected_situation_info: 선택한 위협상황 정보 (수동입력/데모시나리오용)
                - status_callback: 진행 상황 보고 콜백 함수
        
        Returns:
            실행 결과 딕셔너리
        """
        # 콜백 설정
        self.status_callback = kwargs.get("status_callback")
        
        # 방책 타입 필터 확인
        coa_type_filter = kwargs.get("coa_type_filter")
        if isinstance(coa_type_filter, str):
            coa_type_filter = [coa_type_filter]
        
        # UI 타입을 코드 타입으로 변환 (예: "Defense" -> "defense", "Counter_Attack" -> "counter_attack")
        ui_to_code_mapping = {
            "Defense": "defense",
            "Offensive": "offensive",
            "Counter_Attack": "counter_attack",
            "Preemptive": "preemptive",
            "Deterrence": "deterrence",
            "Maneuver": "maneuver",
            "Information_Ops": "information_ops"
        }
        
        if coa_type_filter:
            # UI 타입을 코드 타입으로 변환
            converted_types = []
            for t in coa_type_filter:
                # 이미 코드 타입인 경우 (소문자, 언더스코어)
                if t.lower() in self.supported_coa_types:
                    converted_types.append(t.lower())
                # UI 타입인 경우 변환
                elif t in ui_to_code_mapping:
                    converted_types.append(ui_to_code_mapping[t])
                # 그 외는 그대로 사용 (하위 호환성)
                else:
                    converted_types.append(t.lower() if isinstance(t, str) else t)
            target_types = converted_types
        else:
            # 기본값 변경: 모든 유형 고려 (상황에 맞는 최적 방책 찾기 위해)
            # 기존에는 defense만 고려했으나, 위협 상황에 따라 다양한 방책이 필요함
            target_types = list(self.supported_coa_types) if hasattr(self, 'supported_coa_types') else ["defense", "offensive", "counter_attack", "preemptive", "deterrence", "maneuver", "information_ops"]
        
        # 만약 "all"이 포함되어 있으면 모든 타입 대상
        if "all" in target_types:
            target_types = self.supported_coa_types
            
        try:
            self._report_status(f"방책 분석 시작 (유형: {', '.join(target_types)})", progress=0)
            
            # 0. 데이터 로드 및 온톨로지 그래프 구축 (팔란티어 방식 개선)
            # 그래프가 이미 구축되어 있는지 확인 (중복 구축 방지)
            graph = self.core.ontology_manager.graph
            if graph is None or len(list(graph.triples((None, None, None)))) == 0:
                self._report_status("온톨로지 데이터 로드 및 지식 그래프 구축 중...", progress=5)
                data = self.core.data_manager.load_all()
                # 데이터 캐시 저장 (재사용을 위해)
                self._data_cache = data
                graph = self.core.ontology_manager.build_from_data(data)
                if graph is not None:
                    triples_count = len(list(graph.triples((None, None, None))))
                    safe_print(f"[INFO] 온톨로지 그래프 구축 완료: {triples_count}개 triples")
                else:
                    safe_print("[WARN] 온톨로지 그래프 구축 실패 (계속 진행)")
            else:
                # 그래프가 이미 있으면 데이터만 캐시 (중복 로드 방지)
                if self._data_cache is None:
                    self._data_cache = self.core.data_cache if hasattr(self.core, 'data_cache') else self.core.data_manager.load_all()
                triples_count = len(list(graph.triples((None, None, None))))
                safe_print(f"[INFO] 기존 온톨로지 그래프 사용 ({triples_count}개 triples)")
            
            # 1. 상황 분석 (SituationAgent 로직)
            self._report_status("전술 상황 분석 및 위협 요소 식별 중...", progress=10)
            user_query = kwargs.get("user_query", "")
            selected_situation_info = kwargs.get("selected_situation_info")
            
            # approach_mode 확인 및 로그
            approach_mode = None
            if selected_situation_info:
                approach_mode = selected_situation_info.get("approach_mode")
                if approach_mode:
                    safe_print(f"[INFO] 접근 방식: {approach_mode}")
            
            # selected_situation_info가 있고 수동입력/데모시나리오인 경우 우선 사용
            if selected_situation_info and (selected_situation_info.get("is_manual") or selected_situation_info.get("is_demo")):
                safe_print(f"[INFO] 수동입력/데모시나리오 정보 사용: situation_id={selected_situation_info.get('situation_id')}, approach_mode={approach_mode}")
                # 테이블 조회 없이 직접 사용
                situation_analysis = {
                    "situation_info": selected_situation_info,
                    "dimension_analysis": self._analyze_situation_dimensions(selected_situation_info),
                    "related_entities": [],
                    "rag_results": []
                }
                
                # 관련 엔티티 탐색 (그래프가 있는 경우)
                if self.core.ontology_manager.graph is not None:
                    try:
                        related_entities = self._find_related_entities_enhanced(
                            selected_situation_info,
                            use_reasoned=kwargs.get("use_reasoned_graph", True)
                        )
                        situation_analysis["related_entities"] = related_entities
                        safe_print(f"[INFO] 관련 엔티티 탐색 완료: {len(related_entities)}개 발견")
                    except Exception as e:
                        safe_print(f"[WARN] 관련 엔티티 탐색 실패: {e}")
                        import traceback
                        traceback.print_exc()
                
                # RAG 검색 (선택적)
                if kwargs.get("use_embedding", True) and self.core.rag_manager and self.core.rag_manager.is_available():
                    try:
                        # [FIX] 매퍼를 사용하여 한글 위협 유형명 추출
                        t_code = selected_situation_info.get('위협유형', selected_situation_info.get('threat_type', '일반'))
                        t_name = t_code
                        if self.mapper:
                            t_name = self.mapper.get_threat_type_label(t_code)
                            
                        # 검색 쿼리 개선 (한글 + 코드 혼용)
                        threat_query = f"위협 상황 {t_name} ({t_code}) 대응 작전 교범"
                        # threat_query = f"위협 상황 {selected_situation_info.get('위협유형', selected_situation_info.get('threat_type', '일반'))}"
                        
                        situation_analysis["rag_results"] = self.core.rag_manager.retrieve_with_context(
                            threat_query,
                            top_k=5
                        )
                        safe_print(f"[INFO] RAG 검색 수행 (Query: {threat_query}): {len(situation_analysis['rag_results'])}건 발견")
                    except Exception as e:
                        safe_print(f"[WARN] RAG 검색 실패: {e}")
            # situation_id가 없거나 빈 문자열이면 바로 일반 분석 수행
            elif not situation_id or situation_id.strip() == "":
                safe_print(f"[INFO] situation_id가 없으므로 일반 분석 수행 (질문: {user_query})")
                try:
                    situation_analysis = self._analyze_situation_generic(user_query)
                    # 에러가 포함되어 있으면 다시 시도
                    if "error" in situation_analysis:
                        safe_print(f"[WARN] _analyze_situation_generic에서 에러 발생: {situation_analysis['error']}")
                        # 기본 상황 정보로 재시도
                        situation_analysis = {
                            "situation_info": {
                                "위협유형": "일반적 침입",
                                "심각도": 0.7,
                                "상황명": user_query if user_query else "일반적 적군 침입 상황"
                            },
                            "dimension_analysis": {},
                            "related_entities": [],
                            "rag_results": []
                        }
                except Exception as e:
                    safe_print(f"[ERROR] _analyze_situation_generic 예외 발생: {e}")
                    import traceback
                    traceback.print_exc()
                    # 예외 발생 시 기본 상황 정보 사용
                    situation_analysis = {
                        "situation_info": {
                            "위협유형": "일반적 침입",
                            "심각도": 0.7,
                            "상황명": user_query if user_query else "일반적 적군 침입 상황"
                        },
                        "dimension_analysis": {},
                        "related_entities": [],
                        "rag_results": []
                    }
            else:
                # selected_situation_info가 있으면 우선 사용 (situation_id가 있어도)
                if selected_situation_info:
                    safe_print(f"[INFO] selected_situation_info가 있어 우선 사용 (situation_id={situation_id}는 무시): situation_id={selected_situation_info.get('situation_id')}")
                    situation_analysis = {
                        "situation_info": selected_situation_info,
                        "dimension_analysis": self._analyze_situation_dimensions(selected_situation_info),
                        "related_entities": [],
                        "rag_results": []
                    }
                    
                    # 관련 엔티티 탐색 (그래프가 있는 경우)
                    if self.core.ontology_manager.graph is not None:
                        try:
                            related_entities = self._find_related_entities_enhanced(
                                selected_situation_info,
                                use_reasoned=kwargs.get("use_reasoned_graph", True)
                            )
                            situation_analysis["related_entities"] = related_entities
                            safe_print(f"[INFO] 관련 엔티티 탐색 완료: {len(related_entities)}개 발견")
                        except Exception as e:
                            safe_print(f"[WARN] 관련 엔티티 탐색 실패: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # RAG 검색 (선택적)
                    if kwargs.get("use_embedding", True) and self.core.rag_manager and self.core.rag_manager.is_available():
                        try:
                            threat_query = f"위협 상황 {selected_situation_info.get('위협유형', selected_situation_info.get('threat_type', '일반'))}"
                            situation_analysis["rag_results"] = self.core.rag_manager.retrieve_with_context(
                                threat_query,
                                top_k=5
                            )
                        except Exception as e:
                            safe_print(f"[WARN] RAG 검색 실패: {e}")
                else:
                    # selected_situation_info가 없을 때만 _analyze_situation 호출
                    try:
                        situation_analysis = self._analyze_situation(
                            situation_id,
                            user_query=user_query,
                            use_embedding=kwargs.get("use_embedding", True),
                            use_reasoned_graph=kwargs.get("use_reasoned_graph", True),
                            selected_situation_info=selected_situation_info  # ✅ 추가: 폴백용
                        )
                        
                        if "error" in situation_analysis:
                            # 에러 발생 시 기본 상황 정보로 진행
                            safe_print(f"[WARN] 테이블 조회 실패, 기본 상황 정보 사용: {situation_analysis['error']}")
                            situation_analysis = {
                                "situation_info": {
                                    "위협유형": "일반적 침입",
                                    "심각도": 0.7,
                                    "threat_level": 0.7,
                                    "상황명": user_query if user_query else "일반적 적군 침입 상황"
                                },
                                "dimension_analysis": {},
                                "related_entities": [],
                                "rag_results": []
                            }
                    except Exception as e:
                        safe_print(f"[ERROR] _analyze_situation 예외 발생: {e}")
                        import traceback
                        safe_print(traceback.format_exc())
                        # 예외 발생 시 기본 상황 정보 사용
                        situation_analysis = {
                            "situation_info": {
                                "위협유형": "일반적 침입",
                                "심각도": 0.7,
                                "threat_level": 0.7,
                                "상황명": user_query if user_query else "일반적 적군 침입 상황"
                            },
                            "dimension_analysis": {},
                            "related_entities": [],
                            "rag_results": []
                        }
            
            situation_info = situation_analysis.get("situation_info", {})
            safe_print(f"[DEBUG] situation_info keys: {list(situation_info.keys())}")
            safe_print(f"[DEBUG] threat_type from info: {situation_info.get('위협유형')}")
            
            if not situation_info:
                safe_print("[WARN] situation_info가 비어있습니다. 기본값으로 진행합니다.")
                situation_info = {}
            
            if not situation_info:
                safe_print("[WARN] situation_info가 비어있습니다. 기본값으로 진행합니다.")
                situation_info = {}
            
            # [NEW] 온톨로지 기반 임무 정보(임무유형) 자동 추출 및 보강
            if self.core.ontology_manager and self.core.ontology_manager.graph is not None:
                try:
                    from core_pipeline.reasoning_engine import ReasoningEngine
                    re_helper = ReasoningEngine()
                    m_context = {
                        "ontology_manager": self.core.ontology_manager,
                        "situation_id": situation_id,
                        "situation_id_raw": situation_id
                    }
                    inferred_mission_type = re_helper._extract_mission_type(m_context)
                    if inferred_mission_type and not situation_info.get('임무유형') and not situation_info.get('mission_type'):
                        situation_info['임무유형'] = inferred_mission_type
                        safe_print(f"[INFO] 온톨로지 기반 임무 유형 보강: {inferred_mission_type}")
                except Exception as e:
                    safe_print(f"[WARN] 임무 유형 자동 추출 실패: {e}")

            # 2. 방책 타입별 추천 실행
            all_recommendations = []
            
            for coa_type in target_types:
                # 대소문자 구분 없이 비교
                if coa_type.lower() not in self.supported_coa_types:
                    safe_print(f"[WARN] 지원하지 않는 방책 타입: {coa_type}")
            
            if not situation_info: # This check was duplicated, keeping the original one.
                safe_print(f"[ERROR] 위협 분석 성공했으나 situation_info가 없음: {situation_analysis}")
            
            self._report_status("임무별 최적 방책 유형 및 대응 전략 수립 중...", progress=25)
            
            # 2. 방책 추천 (Unified Search & Parallel Scoring)
            self._report_status("통합 후보 검색 및 병렬 최적화 수행 중...", progress=20)
            
            # 2.1 통합 검색 (Global Search)
            # 모든 유형의 방책을 한 번에 검색하여 후보 풀 생성
            global_candidates = self._search_strategies_via_sparql(situation_info=situation_info)
            safe_print(f"[INFO] 통합 검색 완료: 총 {len(global_candidates)}개 후보 식별")
            
            # 2.2 유형별 그룹화 (Distribute)
            candidates_by_type = {}
            for cand in global_candidates:
                ctype = cand.get('coa_type', 'defense').lower()
                if ctype not in candidates_by_type:
                    candidates_by_type[ctype] = []
                candidates_by_type[ctype].append(cand)
            
            recommendations = []

            with ThreadPoolExecutor(max_workers=max(1, min(len(target_types), 8))) as executor:
                future_to_type = {}
                for coa_type in target_types:
                    # 해당 타입의 후보군 가져오기 (없으면 빈 리스트)
                    type_candidates = candidates_by_type.get(coa_type.lower(), [])
                    
                    # 2.3 병렬 점수 계산 (Parallel Scoring)
                    future = executor.submit(
                        self._recommend_by_type, 
                        coa_type, 
                        situation_id, 
                        situation_info, 
                        situation_analysis, 
                        candidate_strategies=type_candidates, # 🔥 Pre-searched candidates passed here
                        **kwargs
                    )
                    future_to_type[future] = coa_type
                
                for i, future in enumerate(as_completed(future_to_type)):
                    coa_type = future_to_type[future]
                    try:
                        type_recs = future.result()
                        recommendations.extend(type_recs)
                        # 진행률 업데이트
                        step_progress = 25 + int(((i + 1) / len(target_types)) * 40)
                        self._report_status(f"방책 유형 분석 완료: {coa_type.upper()}", progress=step_progress)
                    except Exception as e:
                        safe_print(f"[ERROR] '{coa_type}' 방책 추천 중 예외 발생: {e}")
            
            self._report_status("추천 방책 종합 점수 계산 및 최종 순위 생성 중...", progress=70)
            all_recommendations.extend(recommendations) # Assuming 'recommendations' is the result of the loop
            
            # 3. 종합 결과 정렬 및 상위 N개 선택
            # 점수 내림차순 정렬 (동점 시 ID 기준 정렬로 일관성 유지)
            # 🔥 CRITICAL FIX: 점수와 ID를 안전하게 변환하여 str vs float 비교 오류 방지
            all_recommendations.sort(
                key=lambda x: (
                    self._safe_float(x.get('최종점수')), 
                    self._safe_str(x.get('COA_ID') or x.get('방책ID') or x.get('ID', ''))
                ), 
                reverse=True
            )
            
            top_k = kwargs.get("top_k", 3)
            
            # 🔥 [Diversity] 다양성 필터링 적용 (동일 유형 독점 방지)
            # 🔥 [Diversity] 다양성 필터링 단순화 로직 (점수 기반 공정 경쟁)
            recommendations = []
            if all_recommendations:
                # 1. 작전 최적안 (Global Best)
                best_coa = all_recommendations[0]
                best_coa['selection_reason'] = "작전 최적안"
                recommendations.append(best_coa)
                
                selected_ids = {best_coa.get('COA_ID') or best_coa.get('방책ID')}
                
                # 2. 차순위 최적안 (Next Best Alternatives)
                # 점수 순으로 상위 N개를 선택하되, 중복 제외
                for cand in all_recommendations[1:]:
                    if len(recommendations) >= top_k:
                        break
                    
                    c_id = cand.get('COA_ID') or cand.get('방책ID')
                    if c_id not in selected_ids:
                        # 태그 생성 (점수 차이에 따라)
                        score_diff = best_coa.get('최종점수', 0) - cand.get('최종점수', 0)
                        if score_diff < 0.05:
                            cand['selection_reason'] = "동등 수준 대안"
                        else:
                            cand['selection_reason'] = "차순위 대안"
                            
                        recommendations.append(cand)
                        selected_ids.add(c_id)
            else:
                recommendations = []
            
            # Phase 2: 대안 분석 추가
            if len(all_recommendations) > 1 and kwargs.get("use_palantir_mode", True):
                try:
                    from core_pipeline.coa_scorer import COAScorer
                    # 🔥 Update: Adaptive Weighting을 위해 situation_info(context) 전달
                    # [PERFORMANCE] CorePipeline의 매퍼 재사용 (중복 초기화 방지)
                    scorer = COAScorer(
                        data_manager=self.core.data_manager, 
                        config=self.core.config, 
                        context=situation_info,
                        relevance_mapper=getattr(self.core, 'relevance_mapper', None),
                        resource_parser=getattr(self.core, 'resource_parser', None)
                    )
                    # COA 결과를 scorer 형식으로 변환
                    coa_results = []
                    for rec in all_recommendations[:top_k]:
                        coa_result = {
                            'coa_id': rec.get('COA_ID') or rec.get('방책ID') or rec.get('ID', 'Unknown'),
                            'coa_name': rec.get('명칭') or rec.get('방책명') or rec.get('name', 'Unknown'),
                            'total': rec.get('최종점수', 0.5),
                            'breakdown': rec.get('score_breakdown', {}),
                            'strengths': rec.get('strengths', []),
                            'weaknesses': rec.get('weaknesses', []),
                            'confidence': rec.get('confidence', 0.5)
                        }
                        coa_results.append(coa_result)
                    
                    # 대안 분석 수행
                    alternatives_analysis = scorer.compare_alternatives(coa_results, top_n=top_k)
                    # 결과에 추가 (전체 결과에만)
                    if alternatives_analysis:
                        for rec in recommendations:
                            rec['alternatives_analysis'] = alternatives_analysis
                except Exception as e:
                    safe_print(f"[WARN] 대안 분석 실패: {e}", logger_name="DefenseCOAAgent")
            
            # 🔥 NEW: Hybrid Adaptation (LLM 기반 상황별 방책 구체화)
            # 라이브러리의 정적 템플릿을 현재 상황에 맞게 텍스트로 미세 조정(Adaptation)
            if self.core.llm_manager and kwargs.get("use_palantir_mode", True):
                self._report_status("LLM 기반 방책 구체화 (Hybrid Adaptation) 수행 중...", progress=85)
                
                # [NEW] 교리/지침 RAG 검색 추가
                doctrine_results = []
                if self.core.rag_manager and self.core.rag_manager.is_available():
                    try:
                        t_code = situation_info.get('위협유형', situation_info.get('threat_type', '적군 침입'))
                        t_name = t_code
                        if self.mapper:
                            t_name = self.mapper.get_threat_type_label(t_code)
                            
                        doctrine_query = f"{t_name} ({t_code}) 대응 작전 교범 및 지침"
                        doctrine_results = self.core.rag_manager.retrieve_with_context(doctrine_query, top_k=3)
                        safe_print(f"[INFO] 교리 RAG 검색 완료 (Query: {doctrine_query}): {len(doctrine_results)}건 발견")
                    except Exception as e:
                        safe_print(f"[WARN] 교리 RAG 검색 실패: {e}")
                
                safe_print("[INFO] Hybrid Adaptation 실행: 방책 구체화 중...")
                self._adapt_coas_with_llm(recommendations, situation_info, doctrine_results=doctrine_results)
            
            # 4. 결과 구성 (기존 로직 유지)
            # situation_id 확정 (situation_info에서 가져오기)
            final_situation_id = situation_id or situation_info.get('situation_id') or situation_info.get('위협ID') or situation_info.get('ID')
            
            # LLM 평가 사용 여부 확인
            llm_evaluations_used = any(
                s.get('llm_score') is not None or s.get('score_breakdown', {}).get('llm_score') is not None
                for s in recommendations
            )
            
            # 🔥 NEW: 교리 참조 정보 추가 (상위 추천에만)
            # 🔥 CRITICAL FIX: situation_analysis에서 실제로 사용된 RAG 결과를 우선 사용
            decision_rag_results = situation_analysis.get('rag_results', [])
            
            for i, s in enumerate(recommendations[:3]):  # 상위 3개만
                doctrine_refs = []
                
                # 1순위: decision_rag_results (실제 의사결정에 기여한 문서)
                if decision_rag_results:
                    for rag_result in decision_rag_results:
                        metadata = rag_result.get('metadata', {})
                        doctrine_id = metadata.get('doctrine_id') or rag_result.get('doctrine_id')
                        statement_id = metadata.get('statement_id') or rag_result.get('statement_id')
                        
                        # 문서 유형 판단
                        is_doctrine = bool(doctrine_id and doctrine_id != "UNKNOWN")
                        
                        ref_entry = {
                            "reference_type": "doctrine" if is_doctrine else "general",
                            "doctrine_id": doctrine_id if is_doctrine else None,
                            "statement_id": statement_id if is_doctrine else None,
                            "source": metadata.get('source') or rag_result.get('source', 'unknown'),
                            "excerpt": rag_result.get('text', '')[:200],
                            "relevance_score": float(rag_result.get('score', 0.0)),
                            "mett_c_elements": metadata.get('mett_c_elements', [])
                        }
                        doctrine_refs.append(ref_entry)
                    
                    if doctrine_refs:
                        s['doctrine_references'] = doctrine_refs[:3]  # 상위 3개만
                        safe_print(f"[INFO] COA {s.get('COA_ID', i+1)}에 {len(doctrine_refs[:3])}개 RAG 기반 참조 추가 (의사결정 기여)")
                
                # RAG 결과가 없으면 doctrine_references를 비워둠 (의사결정에 기여한 문서 없음을 정직하게 표시)
                if not doctrine_refs:
                    s['doctrine_references'] = []
                    safe_print(f"[INFO] COA {s.get('COA_ID', i+1)}: 의사결정에 기여한 RAG 문서 없음")
            
            # [FIX] 상황판단은 한 번만 생성 (모든 방책에 대해 동일하므로 중복 호출 방지)
            situation_assessment_text = None
            if recommendations:  # 최소 1개 방책이 있을 때만 생성
                try:
                    situation_assessment_text = self._generate_situation_assessment(situation_info)
                    safe_print(f"[INFO] 상황판단 생성 완료 (1회 호출, 모든 방책에 재사용)")
                except Exception as e:
                    safe_print(f"[WARN] 상황판단 생성 실패: {e}, fallback 사용")
                    situation_assessment_text = None

            # [FIX] 최종 추천된 방책(top_k)에 대해서만 LLM 기반 선정사유 생성
            safe_print(f"[INFO] 최종 추천 방책 수: {len(recommendations)}개 (top_k={top_k})")

            # [NEW] 선정사유 생성 시작 진행율 보고
            self._report_status("방책 선정사유 및 상세 정보 생성 중...", progress=90)

            # [PERFORMANCE] 병렬 처리로 선정사유 생성 (성능 최적화)
            # 각 방책에 대해 선정사유를 한 번만 생성하고 reason과 justification에 재사용
            recommendation_list = []
            
            # 병렬 처리로 선정사유 생성 (최대 3-5개 동시 처리)
            
            def generate_reason_with_progress(s, idx, total):
                """선정사유 생성 헬퍼 함수"""
                coa_name = s.get("명칭") or s.get("방책명") or s.get("name") or f"방책 {idx+1}"
                try:
                    reason = self._generate_recommendation_reason(s, situation_info)
                    return (idx, s, reason, coa_name)
                except Exception as e:
                    safe_print(f"[WARN] '{coa_name}' 선정사유 생성 실패: {e}")
                    return (idx, s, None, coa_name)
            
            # 병렬 처리 실행
            max_workers = min(len(recommendations), 3)  # 최대 3개 동시 처리 (LLM API 제한 고려)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(generate_reason_with_progress, s, idx, len(recommendations)): idx
                    for idx, s in enumerate(recommendations)
                }
                
                # 완료된 작업부터 처리 (진행율 업데이트)
                completed_count = 0
                for future in as_completed(futures):
                    completed_count += 1
                    idx, s, recommendation_reason, coa_name = future.result()
                    
                    # 진행율 업데이트 (90-95% 범위)
                    if len(recommendations) > 0:
                        item_progress = 90 + int((completed_count / len(recommendations)) * 5)
                        self._report_status(f"'{coa_name}' 선정사유 생성 완료 ({completed_count}/{len(recommendations)})", progress=item_progress)
                    
                    # 선정사유가 None인 경우 fallback
                    if recommendation_reason is None:
                        recommendation_reason = f"'{coa_name}' 방책은 현재 상황에 적합한 대응책입니다."
                    
                    recommendation_list.append({
                        "coa_id": s.get("COA_ID") or s.get("방책ID") or s.get("ID") or s.get("방책명") or "Unknown",
                        "coa_name": s.get("명칭") or s.get("방책명") or s.get("name") or "Unknown",
                        "coa_type": s.get("coa_type", "defense"), # 타입 정보 추가
                        "score": s.get("최종점수", s.get("MAUT점수", 0.5)),
                        # [PERFORMANCE] 선정사유는 병렬 처리로 생성됨
                        "reason": recommendation_reason,
                        "score_breakdown": s.get("score_breakdown", {}),
                        "llm_score": s.get("llm_score"),
                        "agent_score": s.get("agent_score"),
                    "participating_units": s.get("required_resources") or s.get("필요자원") or [],
                    "required_resources": s.get("required_resources") or s.get("필요자원") or "",
                    "visualization_data": s.get("visualization_data", {}),
                    # [NEW] 선정 유형 (지휘관 결심 지원용)
                    "selection_category": s.get("selection_reason", "작전 최적안"),
                    # 🔥 NEW: 교리 참조 정보
                    "doctrine_references": s.get("doctrine_references", []),
                    "mett_c_alignment": situation_analysis.get('mett_c', {}).get('alignment', {}) if isinstance(situation_analysis.get('mett_c', {}), dict) else {},
                    # [NEW] UI Reasoning 데이터 매핑 (상황 판단, 선정 사유, 기대효과 구분)
                    "reasoning": {
                        # [FIX] 상황판단 재사용 (중복 호출 방지)
                        "situation_assessment": s.get("adapted_assessment") or situation_assessment_text,
                        # [FIX] reason 재사용 (중복 호출 방지)
                        "justification": recommendation_reason,
                        "pros": s.get("adapted_strengths") or self._generate_expected_effects(s, situation_info),
                        # [NEW] 부대 운용 및 탐색 논리 필드 추가
                        "unit_rationale": s.get("unit_rationale") or s.get("llm_reason"),
                        "system_search_path": s.get("system_search_path")
                    },
                    # Phase 2: 설명 가능성 정보
                    "confidence": s.get("score_breakdown", {}).get("confidence", 0.5),
                    "strengths": s.get("score_breakdown", {}).get("strengths", []),
                    "weaknesses": s.get("score_breakdown", {}).get("weaknesses", []),
                    "reasoning_trace": s.get("reasoning_trace", []), # [NEW] UI Trace용
                    "chain_info_details": s.get("chain_info_details", {}) # [NEW] Chain Visualizer용
                })
            
            # [PERFORMANCE] 병렬 처리로 인해 순서가 보장되지 않으므로 점수 순으로 정렬
            recommendation_list.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # [NEW] 선정사유 생성 완료 진행율 보고
            self._report_status("방책 선정사유 생성 완료", progress=95)

            result = {
                "agent": self.name,
                "status": "completed",
                "situation_id": final_situation_id,
                "situation_analysis": situation_analysis,
                "recommendations": recommendation_list,
                # LLM-Agent 협력 정보 추가
                "llm_collaboration": {
                    "situation_analysis_used": situation_analysis.get("llm_analysis_used", False),
                    "strategy_evaluation_used": llm_evaluations_used,
                    "llm_insights": situation_analysis.get("llm_insights", {}),
                    "llm_context": situation_analysis.get("llm_context", ""),
                    "llm_threat_assessment": situation_analysis.get("llm_threat_assessment", {})
                },
                "palantir_mode": kwargs.get("use_palantir_mode", False),
                "timestamp": pd.Timestamp.now().isoformat(),
                # [NEW] 전술 상황 전체 요약 (자연어)
                "situation_summary": self._generate_overall_situation_summary(situation_info, situation_analysis),
                # Phase 2: 대안 분석 정보 추가
                "alternatives_analysis": recommendations[0].get('alternatives_analysis', {}) if recommendations and recommendations[0].get('alternatives_analysis') else {},
                # 🔥 FIX: 보강된 시각화 데이터 직접 포함 (API 라우터 중복 생성 방지)
                "axis_states": kwargs.get("axis_states", []), # _score_with_palantir_mode에서 캡처된 데이터 활용 가능 시
                "unit_positions": recommendations[0].get('unit_positions', {}) if recommendations else {} # 상위 방책의 데이터 활용
            }
            
            self._report_status("방책 분석 및 추천 완료.", progress=100)
            safe_print(f"[INFO] 결과 구성 완료: status={result['status']}, situation_id={result['situation_id']}, recommendations={len(result['recommendations'])}")
            
            # 팔란티어 모드인 경우 점수 상세 정보 추가
            # 🔥 FIX: recommendation_list에 이미 score_breakdown이 포함되어 있으므로 중복 설정 불필요
            # 다만, recommendations 원본과 동기화 확인을 위해 로그만 출력
            if kwargs.get("use_palantir_mode", False):
                for i, rec in enumerate(result["recommendations"]):
                    coa_id = rec.get('coa_id', 'Unknown')
                    existing_breakdown = rec.get("score_breakdown", {})
                    # 디버깅: breakdown 존재 여부 확인
                    if existing_breakdown and isinstance(existing_breakdown, dict) and len(existing_breakdown) > 0:
                        safe_print(f"[DEBUG] COA {i+1} ({coa_id}): breakdown 이미 존재, 키={list(existing_breakdown.keys())}")
                    else:
                        # recommendations 원본에서 찾아서 설정 시도
                        matching_rec = None
                        for orig_rec in recommendations:
                            orig_coa_id = orig_rec.get("COA_ID") or orig_rec.get("방책ID") or orig_rec.get("ID") or orig_rec.get("방책명")
                            if orig_coa_id == coa_id or orig_rec.get("coa_id") == coa_id:
                                matching_rec = orig_rec
                                break
                        
                        if matching_rec:
                            source_breakdown = matching_rec.get("score_breakdown", {})
                            if source_breakdown:
                                rec["score_breakdown"] = source_breakdown.copy() if isinstance(source_breakdown, dict) else {}
                                safe_print(f"[DEBUG] COA {i+1} ({coa_id}): breakdown 원본에서 복원, 키={list(rec['score_breakdown'].keys())}")
                            else:
                                safe_print(f"[WARNING] COA {i+1} ({coa_id}): 원본에도 breakdown이 없음!")
                        else:
                            safe_print(f"[WARNING] COA {i+1} ({coa_id}): 원본 recommendations에서 매칭되는 항목을 찾을 수 없음!")
                        # [MOD] 이미 상단에서 "reasoning" 객체를 생성했으므로 여기서 중복 생성하지 않음
                        # 단, pros(기대효과)가 누락되지 않도록 함
            
            # Summary 생성 (LLM이 자연스럽게 생성하도록 최소한의 정보만 제공)
            if recommendations:
                summary_parts = [f"총 {len(recommendations)}개의 방책을 추천했습니다:"]
                for i, rec in enumerate(recommendations[:3], 1):
                    coa_name = rec.get("명칭") or rec.get("방책명") or rec.get("name") or "Unknown"
                    coa_type = rec.get("coa_type", "defense")
                    score = rec.get("최종점수", rec.get("MAUT점수", 0.5))
                    summary_parts.append(f"{i}. [{coa_type}] {coa_name} (적합도: {score:.2f})")
                result["summary"] = "\n".join(summary_parts)
            else:
                result["summary"] = "추천할 방책을 찾지 못했습니다."
            
            # situation_info를 결과에 포함시켜 LLM이 참고할 수 있도록 함
            result["situation_info"] = situation_info
            
            # 상황 변화 감지 및 히스토리 저장
            situation_id_for_history = situation_id or situation_info.get('위협ID', situation_info.get('ID', 'UNKNOWN'))
            change_detected, change_info = self._detect_situation_change(
                situation_id_for_history, situation_info
            )
            
            if change_detected:
                # 이전 추천과 비교
                previous_rec = self._get_previous_recommendation(situation_id_for_history)
                result["change_detected"] = True
                result["previous_recommendation"] = previous_rec
                result["change_summary"] = self._compare_recommendations(
                    previous_rec, result
                )
                result["change_info"] = change_info
                safe_print(f"[INFO] 상황 변화 감지: {change_info}")
            else:
                result["change_detected"] = False
            
            # 히스토리 저장
            self._save_to_history(situation_id_for_history, result)
            
            return result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            safe_print(f"[ERROR] EnhancedDefenseCOAAgent.execute_reasoning 예외 발생: {e}")
            safe_print(f"[ERROR] 에러 상세:\n{error_trace}")
            
            # 에러 발생 시에도 selected_situation_info가 있으면 최소한의 결과 반환
            selected_situation_info = kwargs.get("selected_situation_info")
            if selected_situation_info:
                safe_print("[INFO] 에러 발생했으나 selected_situation_info가 있어 최소한의 결과 반환")
                return {
                    "agent": self.name,
                    "status": "completed",
                    "situation_id": selected_situation_info.get("situation_id"),
                    "situation_info": selected_situation_info,
                    "recommendations": [
                        {
                            "coa_id": "ERROR_FALLBACK",
                            "coa_name": "에러 발생 - 기본 방책",
                            "score": 0.5,
                            "reason": f"에러 발생으로 기본 방책 제안: {str(e)}"
                        }
                    ],
                    "error": str(e),
                    "summary": f"에러가 발생했으나 상황 정보는 확인되었습니다. 위협수준: {selected_situation_info.get('threat_level', 'N/A')}"
                }
            
            return {
                "agent": self.name,
                "status": "failed",
                "error": str(e),
                "error_trace": error_trace,
                "summary": f"에러 발생: {str(e)}"
            }

    def _adapt_coas_with_llm(self, recommendations: List[Dict], situation_info: Dict, doctrine_results: List[Dict] = None):
        """LLM을 사용하여 방책별 부대 운용 근거 및 탐색 과정을 설명 (Process Transparency)"""
        try:
            # 상황 요약
            situation_str = f"위협: {situation_info.get('위협유형', 'Unknown')}, 수준: {situation_info.get('threat_level', 0.5)}, 환경: {situation_info.get('전장환경', 'Unknown')}, 적군: {situation_info.get('적군부대', 'Unknown')}"

            # LLM 호출 함수 정의
            def adapt_coa(coa_item):
                coa_name = coa_item.get('명칭') or coa_item.get('name', '')
                participating_units = coa_item.get('필요자원') or coa_item.get('required_resources', 'N/A')
                
                # 기본값 설정 (LLM 실패 시 사용될 Fallback) - 방책 이름을 포함하여 구별되게 함
                coa_item['unit_rationale'] = f"'{coa_name}' 작전의 성공적인 수행을 위해 가용 자원을 최적화하여 할당하였습니다."
                coa_item['system_search_path'] = "Defense Ontology의 자산-임무 연관성 분석을 통해 도출됨."

                prompt = (
                    f"당신은 작전 참모이자 시스템 설계자입니다. 다음 방책(COA)에 할당된 부대(Resource)의 선정 근거와 시스템적 탐색 과정을 지휘관에게 설명하세요.\n\n"
                    f"[상황 정보]\n{situation_str}\n\n"
                    f"[선택된 방책]\n명칭: {coa_name}\n\n"
                    f"[할당된 아군 부대/자산]\n{participating_units}\n\n"
                    f"다음 두 가지 항목을 군사적 전문성과 시스템적 투명성을 담아 한글로 작성하세요:\n"
                    f"1. 부대 운용 근거 (Unit Rationale): 선택된 부대(예: 공병대대 등)가 이 작전에서 왜 필요한지, 어떤 전술적 기여를 하는지 설명 (2~3문장)\n"
                    f"2. 시스템 탐색 과정 (Search Path): 에이전트가 지식 그래프(Knowledge Graph)에서 이 부대를 어떻게 찾아냈는지 설명. "
                    f"`{search_logic}` 내용을 포함하여 논리적으로 서술 (1~2문장)\n\n"
                    f"응답 형식:\n"
                    f"[운용근거]\n...\n"
                    f"[탐색과정]\n..."
                )
                
                if hasattr(self.core, 'llm_manager') and self.core.llm_manager:
                    safe_print(f"[INFO] '{coa_name}' 부대 근거 생성 요청 중...")
                    response = self.core.llm_manager.generate(prompt, temperature=0.1, max_tokens=512)
                    if response:
                        text = response.strip()
                        safe_print(f"[DEBUG] LLM 응답 수신 ({coa_name}): {text[:50]}...")
                        try:
                            import re
                            # [운용근거], [탐색과정] 섹션 추출
                            rat_match = re.search(r'\[운용근거\](.*?)(?=\[탐색과정\]|$)', text, re.S)
                            path_match = re.search(r'\[탐색과정\](.*?)$', text, re.S)

                            if rat_match: 
                                coa_item['unit_rationale'] = rat_match.group(1).strip()
                                safe_print(f"[DEBUG] '{coa_name}' 운용근거 파싱 성공")
                            if path_match: 
                                coa_item['system_search_path'] = path_match.group(1).strip()
                                safe_print(f"[DEBUG] '{coa_name}' 탐색과정 파싱 성공")
                            
                            coa_item['llm_reason'] = coa_item.get('unit_rationale', text[:100])
                        except Exception as e:
                            safe_print(f"[WARN] LLM 응답 파싱 실패 ({coa_name}): {e}")
                            coa_item['unit_rationale'] = f"{coa_name} 실행을 위해 필요한 표준 부대 구성입니다."
                        
                        safe_print(f"[INFO] 부대 운용/탐색 근거 생성 완료: {coa_name}")


            # 🔥 FIX: recommendations가 비어있으면 ThreadPoolExecutor 생략
            if not recommendations or len(recommendations) == 0:
                safe_print("[WARN] 추천 방책이 없어 LLM Adaptation을 건너뜁니다.")
                return
                
            # 병렬 처리 실행 및 대기
            from concurrent.futures import wait
            with ThreadPoolExecutor(max_workers=min(len(recommendations), 5)) as executor:
                futures = [executor.submit(adapt_coa, rec) for rec in recommendations]
                wait(futures)
                safe_print(f"[INFO] 모든 방책 구체화(Adaptation) 완료: {len(recommendations)}건")
        except Exception as e:
            import traceback
            safe_print(f"[ERROR] _adapt_coas_with_llm 예외 발생: {e}")
            safe_print(traceback.format_exc())

    def _recommend_by_type(self, coa_type: str, situation_id: str, 
                          situation_info: Dict, situation_analysis: Dict, 
                          **kwargs) -> List[Dict]:
        """타입별 방책 추천 실행"""
        
        if kwargs.get('candidate_strategies'):
            # 🔥 NEW: Search-First 패턴 지원 - 이미 검색된 후보군 사용
            candidate_strategies = kwargs.get('candidate_strategies')
            self._report_status(f"{coa_type.upper()} 방책 점수 평가 중... (병렬 처리)")
            # safe_print(f"[INFO] {coa_type} 방책 점수 평가 시작 (Candidates: {len(candidate_strategies)})")
        else:
            # LEGACY: 함수 내 검색 직접 수행
            self._report_status(f"{coa_type.upper()} 방책 후보 탐색 중...")
            safe_print(f"[INFO] {coa_type} 방책 탐색 시작")
            candidate_strategies = self._search_strategies(
                situation_id,
                situation_info=situation_info,
                top_k=kwargs.get("top_k", 10),
                use_embedding=kwargs.get("use_embedding", True),
                inference_mode=kwargs.get("inference_mode", "hybrid"),
                coa_type=coa_type  # 🔥 방책유형 필터링 적용
            )
        
        if not candidate_strategies:
            self._report_status(f"{coa_type.upper()} 방책 후보를 찾을 수 없습니다.")
            return []
            
        # 2. 점수 계산
        use_palantir = kwargs.get("use_palantir_mode", False)
        
        if use_palantir:
            self._report_status(f"{coa_type.upper()} 방책 팔란티어 모드 점수 계산 중...")
            scored_strategies = self._score_with_palantir_mode(
                candidate_strategies,
                situation_info,
                situation_analysis,
                coa_type=coa_type # 타입 전달
            )
        else:
            self._report_status(f"{coa_type.upper()} 방책 기본 모드 점수 계산 중...")
            # 기본 모드에서도 타입별 가중치 적용을 위해 로직 개선 필요
            # 현재는 기존 로직 재사용
            scored_strategies = self._score_strategies(
                candidate_strategies,
                situation_info,
                situation_analysis
            )
            
        # 3. 결과에 타입 정보 및 추천 이유 추가
        for strategy in scored_strategies:
            strategy['coa_type'] = coa_type
            
            # 추천 이유 생성 (Week 2 개선)
            # score_breakdown이나 reasoning 로그가 있으면 활용
            reasoning = strategy.get('score_breakdown', {}).get('reasoning')
            
            # 팔란티어 모드에서는 score_result에 reasoning이 포함되어 있을 수 있음
            # _score_with_palantir_mode가 반환하는 strategy 구조에 따라 다름
            # 현재 _score_with_palantir_mode는 strategy 딕셔너리에 점수 정보를 추가함
            
            # [PERFORMANCE] 선정사유 생성 제거 - 최종 상위 방책에 대해서만 생성하도록 변경
            # execute_reasoning()에서 최종 추천된 방책(top_k)에 대해서만 선정사유를 생성하므로
            # 여기서는 생성하지 않음 (불필요한 LLM 호출 방지)
            # 추천사유는 execute_reasoning()에서 최종 상위 방책에 대해서만 생성됨
            
        return scored_strategies

    def _generate_recommendation_reason(self, strategy: Dict, situation_info: Dict) -> str:
        """
        추천 이유 자동 생성 (우선순위: LLM > 온톨로지 > 스코어 팩터 > 폴백)
        LLM을 활용하여 자연스러운 문장 생성하되, 정확한 정보(온톨로지 trace, 점수 breakdown 등)를 반영
        """
        # [REMOVED] 외부 루프(execute_reasoning)에서 이미 진행율 보고하므로 여기서는 제거
        approach_mode = situation_info.get("approach_mode", "threat_centered")
        coa_name = strategy.get('명칭') or strategy.get('name') or strategy.get('coa_name') or '이 방책'
        coa_id = strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('coa_id') or 'N/A'
        coa_description = strategy.get('설명') or strategy.get('description', '')
        coa_type = strategy.get('coa_type') or strategy.get('방책유형', '')
        coa_score = strategy.get('score') or strategy.get('최종점수', 0.0)
        
        # 1. LLM을 활용한 자연스러운 선정사유 생성 (우선순위 1)
        if self.core.llm_manager and self.core.llm_manager.is_available():
            try:
                # 구조화된 데이터 수집
                trace = strategy.get('reasoning_trace', [])
                score_breakdown = strategy.get('score_breakdown', {})
                reasoning = score_breakdown.get('reasoning', [])
                strengths = strategy.get('strengths', [])
                
                # [FIX] 상황 정보 - ID를 자연어로 변환
                threat_type_code = situation_info.get('위협유형') or situation_info.get('threat_type') or 'UNKNOWN'
                loc_id = situation_info.get('발생장소') or situation_info.get('location') or 'N/A'
                axis_id = situation_info.get('관련축선ID') or situation_info.get('axis_id', 'N/A')
                
                # [FIX] 매핑 엔진으로 실제 명칭 변환
                real_loc_name = self.mapper.get_terrain_label(loc_id) if loc_id != 'N/A' else '작전 구역'
                t_type_ko = self.mapper.get_threat_type_label(threat_type_code)
                real_axis_name = self.mapper.get_axis_label(axis_id) if axis_id != 'N/A' else '주 축선'
                
                # Display용 포맷 (이름(ID) 형식)
                loc_display = self.mapper.format_with_code(real_loc_name, loc_id)
                threat_display = self.mapper.format_with_code(t_type_ko, threat_type_code)
                axis_display = self.mapper.format_with_code(real_axis_name, axis_id)
                
                threat_level = self._extract_threat_level(situation_info)
                threat_pct = int(threat_level * 100)
                
                # 온톨로지 trace 요약 생성
                trace_summary = ""
                if trace and isinstance(trace, list) and len(trace) > 0:
                    trace_steps = []
                    for step in trace[:5]:  # 최대 5개만
                        from_node = step.get('from', '').split('#')[-1].split('/')[-1]
                        to_node = step.get('to', '').split('#')[-1].split('/')[-1]
                        rel_type = step.get('type', '').split('#')[-1].split('/')[-1]
                        trace_steps.append(f"- {from_node} → {to_node} (관계: {rel_type})")
                    if trace_steps:
                        trace_summary = "\n".join(trace_steps)
                
                # 점수 breakdown 요약
                breakdown_summary = ""
                if score_breakdown:
                    breakdown_items = []
                    for key in ['threat', 'resources', 'assets', 'environment', 'historical', 'chain']:
                        score = score_breakdown.get(key, 0)
                        if score > 0:
                            key_name = {
                                'threat': '위협 수준',
                                'resources': '자원 가용성',
                                'assets': '전력 능력',
                                'environment': '환경 적합성',
                                'historical': '과거 효과성',
                                'chain': '연계성'
                            }.get(key, key)
                            breakdown_items.append(f"- {key_name}: {score:.2f}")
                    if breakdown_items:
                        breakdown_summary = "\n".join(breakdown_items)
                
                # 상위 평가 근거
                top_reasons = []
                if reasoning:
                    sorted_factors = sorted(
                        reasoning,
                        key=lambda x: self._safe_float(x.get('weighted_score', 0)),
                        reverse=True
                    )
                    for factor in sorted_factors[:3]:
                        reason_text = factor.get('reason', '')
                        score_val = factor.get('weighted_score', 0)
                        if reason_text:
                            top_reasons.append(f"- {reason_text} (기여도: {score_val:.3f})")
                
                # [FIX] LLM 프롬프트 구성 - 자연어 명칭 사용 및 코드 노출 방지
                prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 방책 선정 사유를 자연스럽고 전문적인 한국어로 작성하세요.

## 현재 상황
- 발생 위치: {loc_display}
- 위협 유형: {threat_display}
- 위협 수준: {threat_pct}%
- 관련 축선: {axis_display}
- 접근 모드: {"임무 중심" if approach_mode == "mission_centered" else "위협 중심"}

## 추천 방책 정보
- 방책명: {coa_name}
- 방책 ID: {coa_id}
- 방책 유형: {coa_type}
- 종합 점수: {coa_score:.3f}
- 방책 설명: {coa_description if coa_description else "N/A"}

## 온톨로지 탐색 경로 (전술적 연관성)
{trace_summary if trace_summary else "온톨로지 탐색 경로 정보 없음"}

## 평가 요소별 점수
{breakdown_summary if breakdown_summary else "점수 상세 정보 없음"}

## 주요 선정 요인 (상위 3개)
{chr(10).join(top_reasons) if top_reasons else "주요 선정 요인 정보 없음"}

## 방책 강점
{chr(10).join([f"- {s}" for s in strengths[:3]]) if strengths else "강점 정보 없음"}

## 작성 요구사항
1. **자연어 명칭 의무화**: "TERR003", "THR_TYPE_001", "AXIS06" 같은 **코드를 문장에 절대 사용하지 마세요.** 반드시 **"{real_loc_name}", "{t_type_ko}", "{real_axis_name}"** 같은 자연어 명칭을 사용하세요.
2. **정확성**: 위의 수치와 정보를 정확히 반영하세요. 임의로 수치를 변경하거나 과장하지 마세요.
3. **자연스러움**: 템플릿처럼 보이지 않도록 자연스러운 문장으로 작성하세요.
4. **구조**: 다음 순서로 작성하세요:
   - 첫 문장: 방책의 핵심 특징과 현재 상황과의 연관성 (자연어 지명 사용 필수)
   - 중간 문장: 온톨로지 탐색 경로나 평가 요소 중 가장 중요한 근거 2-3개
   - 마지막 문장: 종합 평가 및 선정 이유
5. **톤앤매너**: 전문적이면서도 이해하기 쉬운 군사 작전 보고 스타일
6. **길이**: 3-5문장으로 간결하게 작성 (최대 200자)

방책 선정 사유:"""

                # [REMOVED] 외부에서 이미 진행 상황 보고하므로 여기서는 제거
                
                # LLM 호출
                response = self.core.llm_manager.generate(prompt, temperature=0.3, max_tokens=300)
                
                # [REMOVED] 외부에서 이미 진행 상황 보고하므로 여기서는 제거
                
                if response:
                    reason_text = response.strip()
                    # 기본 검증: 너무 짧거나 의미없는 경우 fallback
                    if len(reason_text) > 20 and not reason_text.startswith("죄송"):
                        safe_print(f"[INFO] LLM 기반 선정사유 생성 성공 ({coa_name}): {reason_text[:50]}...")
                        return reason_text
                    else:
                        safe_print(f"[WARN] LLM 응답이 부적절하여 fallback 사용: {reason_text[:30]}")
            except Exception as e:
                safe_print(f"[WARN] LLM 선정사유 생성 실패: {e}, fallback 사용")
        
        # 2. Fallback: 기존 템플릿 방식 (LLM 실패 시)
        # Ontology Reasoning Trace 변환
        trace = strategy.get('reasoning_trace')
        ontology_reason = ""
        
        if trace and isinstance(trace, list) and len(trace) > 0:
            try:
                safe_print(f"[DEBUG] _generate_recommendation_reason: reasoning_trace found ({len(trace)} steps)")
                narrative_parts = []
                
                threat_type_name = situation_info.get('위협유형') or situation_info.get('threat_type') or "식별된 위협"
                
                for step in trace:
                    def clean_node_name(name):
                        if not name: return ""
                        name = name.split('#')[-1].split('/')[-1]
                        
                        if "Library" in name or "library" in name or "COA_Library" in name:
                            return f"'{coa_name}' 방책 라이브러리"
                        if name in ["Defense", "defense", "방어", "DefensiveCOA"]:
                            return f"'{coa_name}'"
                        if name in ["Threat", "threat", "위협상황", "ThreatSituation"]:
                            return f"'{threat_type_name}'"
                        if name in ["Mission", "mission", "임무정보"]:
                            return "부여된 임무"

                        if '_' in name:
                            parts = name.split('_')
                            if len(parts) > 1:
                                if any(x in parts[0] for x in ['THR', 'COA', 'AST', 'LOC']): return parts[1]
                                if any(x in parts[1] for x in ['THR', 'COA', 'AST', 'LOC']): return parts[0]
                            return parts[0]
                        return name

                    src = clean_node_name(step.get('from', ''))
                    dst = clean_node_name(step.get('to', ''))
                    rel = step.get('type', '').lower()
                    
                    if any(x in rel for x in ['threatens', '위협', 'target']):
                        narrative_parts.append(f"{src}이(가) {dst}을(를) 위협하고 있어")
                    elif any(x in rel for x in ['defendedby', '방어', 'protectedby']):
                        narrative_parts.append(f"이를 방어하기 위해 {dst}이(가) 할당되었습니다")
                    elif any(x in rel for x in ['counters', '대응', 'effectiveagainst', 'countersthreat']):
                        narrative_parts.append(f"{src}은(는) {dst}에 대한 효과적인 대응 수단입니다")
                    elif any(x in rel for x in ['requires', '필요', 'uses', 'hasresource']):
                        narrative_parts.append(f"{src} 수행을 위해 {dst} 자산이 필수적입니다")
                    elif any(x in rel for x in ['locatedin', '위치', 'spatial']):
                        narrative_parts.append(f"{src}이(가) {dst} 구역에 위치하고 있습니다")
                    elif any(x in rel for x in ['hasmission', '임무', 'assignedto']):
                        narrative_parts.append(f"{src} 상황 하에서 {dst}가 부여되었으며")
                    elif any(x in rel for x in ['missiontype', '임무종류', 'typeof']):
                        narrative_parts.append(f"{src}은(는) {dst} 유형의 작전으로 분류됩니다")
                    elif any(x in rel for x in ['hasconstraint', '제약']):
                        narrative_parts.append(f"{dst} 제약 조건을 고려하여")
                    else:
                        narrative_parts.append(f"{src}과(와) {dst}의 관계({rel})를 고려하여")
                
                if narrative_parts:
                    ontology_reason = " ".join(narrative_parts) + "."
                    ontology_reason = ontology_reason.replace("..", ".")
                    ontology_reason = f"전술적 연관성 분석 결과, {ontology_reason}"
                    
            except Exception as e:
                safe_print(f"[WARN] Reasoning Trace 변환 실패: {e}")

        # 3. Reasoning 로그 (스코어링 팩터)
        score_breakdown = strategy.get('score_breakdown', {})
        reasoning = score_breakdown.get('reasoning', [])
        quant_reasons = []
        
        if reasoning:
            sorted_factors = sorted(
                reasoning, 
                key=lambda x: self._safe_float(x.get('weighted_score', 0)), 
                reverse=True
            )
            for factor in sorted_factors[:2]:
                reason_text = factor.get('reason', '')
                if reason_text:
                    if approach_mode == "mission_centered":
                        reason_text = reason_text.replace("위협", "임무 상황").replace("적군", "대항군").replace("대응", "수행")
                    quant_reasons.append(reason_text)
                    
        # 4. 방책 고유 설명 및 강점 활용
        description = strategy.get('설명') or strategy.get('description', '')
        strengths = strategy.get('strengths', [])
        
        # 5. 최종 결과 조합 (Fallback)
        final_parts = []
        
        if description:
            final_parts.append(f"본 방책은 {description}")
            if not description.endswith('.'):
                final_parts[-1] += "."
        
        if ontology_reason:
            final_parts.append(ontology_reason)
        
        if quant_reasons:
            quant_text = "주요 선정 요인은 " + ", ".join(quant_reasons) + " 입니다."
            final_parts.append(quant_text)
            
        if strengths and isinstance(strengths, list):
             unique_strengths = [s for s in strengths[:2] if s not in str(quant_reasons)]
             if unique_strengths:
                 strength_text = "또한 " + ", ".join(unique_strengths) + " 등이 장점으로 분석되었습니다."
                 final_parts.append(strength_text)
            
        if final_parts:
            return " ".join(final_parts)
        
        # 6. 최종 폴백
        threat_level = self._extract_threat_level(situation_info)
        threat_pct = int(threat_level * 100)
        threat_type = situation_info.get('위협유형') or situation_info.get('threat_type') or '식별된 위협'
        return f"'{coa_name}'은(는) 위협 수준 {threat_pct}%인 '{threat_type}' 상황에 대응하기 위해 최적화된 방책입니다."

    def _generate_situation_assessment(self, situation_info: Dict) -> str:
        """
        상황 판단 텍스트 생성 (하이브리드: LLM 우선 + 템플릿 Fallback)
        정확한 정보를 반영하면서 자연스러운 문장 생성
        """
        approach_mode = situation_info.get("approach_mode", "threat_centered")
        
        # [FIX] 매핑 엔진 활용 (ID -> 자연어)
        loc_id = situation_info.get('location') or situation_info.get('발생장소') or situation_info.get('상황위치') or 'N/A'
        threat_type_code = situation_info.get('threat_type') or situation_info.get('위협유형') or situation_info.get('상황명') or 'UNKNOWN'
        axis_id = situation_info.get('관련축선ID') or situation_info.get('axis_id', 'N/A')
        axis_name = situation_info.get('관련축선명') or situation_info.get('axis_name', 'N/A')
        enemy = situation_info.get('적부대') or situation_info.get('enemy_units', 'N/A')
        detection_time = situation_info.get('탐지시각') or situation_info.get('occurrence_time', '최근')
        description = situation_info.get('상황설명') or situation_info.get('description', '')
        
        # 전문 명칭 치환
        real_loc_name = self.mapper.get_terrain_label(loc_id) if loc_id != 'N/A' else '작전 구역'
        t_type_ko = self.mapper.get_threat_type_label(threat_type_code)
        real_axis_name = self.mapper.get_axis_label(axis_id) if axis_id != 'N/A' else axis_name
        
        codec_map = {
            "INFANTRY": "보병", "ARMOR": "기갑", "ARTILLERY": "포병", "AIR": "항공", "MISSILE": "미사일", 
            "UNKNOWN": "미상", "ENU_ESTIMATED": "식별된 적 부대"
        }
        enemy_ko = codec_map.get(str(enemy).upper(), enemy)

        threat_level = self._extract_threat_level(situation_info)
        threat_pct = int(threat_level * 100)
        
        # Display용 텍스트 구성 (이름(ID) 형식)
        loc_display = self.mapper.format_with_code(real_loc_name, loc_id)
        axis_display = self.mapper.format_with_code(real_axis_name, axis_id)

        # [FIX] 상황판단 생성 시작 진행상황 업데이트
        if self.status_callback:
            self._report_status("상황판단 생성 중...", progress=None)
        
        # 1. LLM 기반 생성 시도
        if self.core.llm_manager and self.core.llm_manager.is_available():
            try:
                if self.status_callback:
                    self._report_status("상황판단 LLM 생성 중...", progress=None)
                
                if approach_mode == "mission_centered":
                    m_id = situation_info.get('mission_id') or situation_info.get('임무ID', 'N/A')
                    m_name = situation_info.get('임무명') or situation_info.get('mission_name', 'N/A')
                    m_type = situation_info.get('임무종류') or situation_info.get('mission_type', 'N/A')
                    m_objective = situation_info.get('임무목표') or situation_info.get('mission_objective', 'N/A')
                    success_pct = int((1.0 - threat_level) * 100)
                    
                    prompt = f"""당신은 작전 참모입니다. 다음의 작전 환경 정보를 바탕으로 임무 상황에 대한 전문적인 지휘 판단을 작성하세요.

## 임무 팩트:
- 작전구역: {loc_display}
- 임무명: {m_name} ({m_id})
- 임무유형: {m_type}
- 주요축선: {axis_display}
- 성공가능성: {success_pct}%
- 상세목표: {m_objective}

## 작성 지시사항:
1. **명칭 중심 기술**: 코드를 문장의 주어로 사용하지 마세요. 반드시 **"{real_loc_name}", "{real_axis_name}"** 등의 명칭을 주어로 사용해야 합니다.
2. **군사적 통찰 반영**: 단순 정보 나열이 아닌, 성공 가능성 {success_pct}%에 대한 전술적 심각도나 기회 요인을 작전적 관점에서 서술하세요.
3. **전문 보고 문체**: "~로 평가됨", "~가 제한됨", "~이 요구됨" 등의 간결하고 명확한 군사 보고체 사용.
4. **분량**: 2-3문장으로 핵심만 요약하여 작성.

상황 판단:"""
                else:
                    prompt = f"""당신은 작전 참모입니다. 다음의 위협 정보를 바탕으로 현재 전술 상황에 대한 전문적인 지휘 판단을 작성하세요.

## 위협 팩트:
- 발생위치: {loc_display}
- 위협원: {enemy_ko}
- 위협유형: {t_type_ko} ({threat_type_code})
- 관련축선: {axis_display}
- 위협수준: {threat_pct}%
- 발생정보: {description if description else "최근 징후 포착"}

## 작성 지시사항:
1. **자연어 명칭 의무화**: "TERR", "THR_TYPE" 등의 **기계적 코드를 문장의 주어로 절대 사용하지 마세요.** 반드시 **"{real_loc_name}", "{t_type_ko}"** 등의 명칭을 주어로 삼아 브리핑을 시작하세요.
2. **심각도 중심 판단**: 위협수준 {threat_pct}%가 갖는 작전상 의미와 대응의 시급성을 군사적 식견을 담아 기술하세요.
3. **권장 대응 방향**: 판단 결과에 따른 핵심적인 대응 방향(예: 경계 강화, 타격 준비, 기동 차단 등)을 한 문장 포함하세요.
4. **전문성**: 지휘관에게 보고하는 수준의 격식을 갖춘 문장 구조 유지.

상황 판단:"""
                
                response = self.core.llm_manager.generate(prompt, temperature=0.2, max_tokens=250)
                
                if self.status_callback:
                    self._report_status("상황판단 생성 완료", progress=None)
                
                if response:
                    assessment_text = response.strip()
                    if self._validate_llm_assessment(assessment_text, situation_info):
                        safe_print(f"[INFO] LLM 기반 상황판단 생성 성공: {assessment_text[:50]}...")
                        return assessment_text
            except Exception as e:
                safe_print(f"[WARN] LLM 상황판단 생성 실패: {e}, fallback 사용")
        
        # 2. Fallback
        if approach_mode == "mission_centered":
            success_pct = int((1.0 - threat_level) * 100)
            assessment = f"'{real_loc_name}' 일대에서 하달된 '{m_name}' 임무 분석 결과, 성공 가능성은 {success_pct}%로 평가됩니다. "
            if success_pct >= 70: assessment += "현재 작전 여건이 양호하며, 계획된 절차에 따른 임무 수행이 가능할 것으로 판단됩니다."
            else: assessment += "작전적 제한 사항을 고려한 추가 자원 할당 및 세밀한 계획 수립이 요구됩니다."
        else:
            assessment = f"'{real_loc_name}' 일대에서 식별된 '{t_type_ko}' 위협은 현재 {threat_pct}%의 위협 수준을 보이고 있습니다. "
            if threat_pct >= 80: assessment += "즉각적인 대응과 전투 준비가 필요한 심각한 상황입니다."
            elif threat_pct >= 50: assessment += "관련 축선의 경계를 강화하고 유연한 대응 태세를 유지해야 합니다."
            else: assessment += "정상적인 감시 체계를 유지하며 상황 변화를 지속 추적해야 합니다."
            
        return assessment
    
    def _validate_llm_assessment(self, assessment: str, situation_info: Dict) -> bool:
        """LLM 생성 문장의 품질 검증"""
        # 1. 최소 길이 검증
        if len(assessment) < 30:
            return False
        
        # 2. 의미없는 응답 필터링
        invalid_responses = ["죄송", "알 수 없", "생성할 수 없", "오류", "죄송합니다", "죄송하지만"]
        if any(invalid in assessment for invalid in invalid_responses):
            return False
        
        # 3. 기본적인 문장 구조 확인 (너무 엄격하지 않게)
        # LLM이 다양한 표현 사용 가능하므로 최소한의 검증만 수행
        
        return True

    def _generate_overall_situation_summary(self, situation_info: Dict, situation_analysis: Optional[Dict] = None) -> str:
        """전체 전술 상황을 온톨로지 기반 서술형으로 요약 (COP 상단 노출용)"""
        approach_mode = situation_info.get("approach_mode", "threat_centered")
        
        # [FIX] 매핑 엔진 활용 (ID -> 자연어)
        loc_id = situation_info.get('발생장소') or situation_info.get('location') or 'N/A'
        threat_type_code = situation_info.get('threat_type') or situation_info.get('위협유형') or 'UNKNOWN'
        enemy = situation_info.get('적부대') or situation_info.get('enemy_units') or 'ENU_ESTIMATED'
        axis_id = situation_info.get('관련축선ID') or situation_info.get('axis_id', 'N/A')
        axis_name = situation_info.get('관련축선명') or situation_info.get('axis_name', 'N/A')
        
        real_loc_name = self.mapper.get_terrain_label(loc_id) if loc_id != 'N/A' else '작전 구역'
        t_type_ko = self.mapper.get_threat_type_label(threat_type_code)
        real_axis_name = self.mapper.get_axis_label(axis_id) if axis_id != 'N/A' else axis_name
        
        codec_map = {
            "INFANTRY": "보병", "ARMOR": "기갑", "ARTILLERY": "포병", "AIR": "항공", "MISSILE": "미사일", 
            "UNKNOWN": "미상", "ENU_ESTIMATED": "식별된 적 부대"
        }
        enemy_ko = codec_map.get(str(enemy).upper(), enemy)
        
        threat_level = self._extract_threat_level(situation_info)
        t_level_ko = "낮음"
        if approach_mode == "mission_centered":
            if threat_level >= 0.8: t_level_ko = "낮음"
            elif threat_level >= 0.4: t_level_ko = "보통"
            else: t_level_ko = "높음"
        else:
            if threat_level >= 0.8: t_level_ko = "높음"
            elif threat_level >= 0.5: t_level_ko = "중간"
            else: t_level_ko = "낮음"

        # Display용 텍스트 구성
        loc_display = self.mapper.format_with_code(real_loc_name, loc_id)
        axis_display = self.mapper.format_with_code(real_axis_name, axis_id)

        # 1. LLM 기반 요약 생성
        if self.core.llm_manager and self.core.llm_manager.is_available():
            try:
                if approach_mode == "mission_centered":
                    m_id = situation_info.get('mission_id') or situation_info.get('임무ID', 'N/A')
                    m_name = situation_info.get('임무명') or situation_info.get('mission_name', 'N/A')
                    m_type = situation_info.get('임무종류') or situation_info.get('mission_type', 'N/A')
                    m_objective = situation_info.get('임무목표') or situation_info.get('mission_objective', 'N/A')
                    
                    prompt = f"""다음의 임무 팩트를 기반으로 지휘관에게 보고하는 자연스러운 군사 임무 요약 문장을 한 문장으로 생성하세요.
                    
## 온톨로지 팩트:
- 하달시각: {situation_info.get('탐지시각', '최근')}
- 작전구역: {loc_display}
- 임무명: {m_name} ({m_id})
- 임무유형: {m_type}
- 주요축선: {axis_display}
- 성공가능성: {t_level_ko}
- 상세목표: {m_objective}

## 요구사항:
- **명칭 중심 작성**: "{m_name}", "{real_loc_name}" 등의 명칭을 주어로 사용. 코드를 문장의 주어로 사용 금지.
- 전문적인 군사 보고 톤앤매너 사용 (예: "~이 하달되었습니다", "~로 분석됩니다")
- 핵심 명사는 굵게(**) 표시
- 한 문장으로 간결하게 생성
"""
                else:
                    prompt = f"""다음의 위협 팩트를 기반으로 지휘관에게 보고하는 자연스러운 군사 상황 요약 문장을 한 문장으로 생성하세요.
                
## 온톨로지 팩트:
- 발생시각: {situation_info.get('탐지시각', '최근')}
- 발생위치: {loc_display}
- 위협원: {enemy_ko}
- 위협유형: {t_type_ko} ({threat_type_code})
- 관련축선: {axis_display}
- 위협수준: {t_level_ko}

## 요구사항:
- **자연어 우선**: 반드시 **"{real_loc_name}"**, **"{t_type_ko}"** 등의 명칭을 활용. 코드를 문장의 주어로 사용 금지.
- 전문적인 군사 보고 톤앤매너 사용 (예: "~이 식별되었습니다", "~로 분석됩니다")
- 핵심 명사는 굵게(**) 표시
- 한 문장으로 간결하게 생성
"""
                summary = self.core.llm_manager.generate(prompt, max_tokens=256).strip()
                if summary: return summary
            except Exception as e:
                safe_print(f"LLM overall summary generation failed: {e}")

        # 2. Fallback
        if approach_mode == "mission_centered":
            summary = f"**{real_loc_name}**({loc_id}) 일대에서 **{situation_info.get('임무명', '기본')}** 임무가 하달되었으며, 주요 작전 축선은 **{real_axis_name}** 방향입니다."
        else:
            summary = f"**{real_loc_name}**({loc_id}) 일대에서 **{enemy_ko}**에 의한 **{t_type_ko}** 위협이 포착되었으며, 전반적인 위협 수준은 **{t_level_ko}** 상태입니다."
            
        return summary

    def _generate_expected_effects(self, strategy: Dict, situation_info: Dict) -> List[str]:
        """방책별 기대 효과 생성 (방책 특성 반영 및 유일성 강화)"""
        # 1. LLM 구체화 데이터가 있으면 우선 사용 (가장 고품질)
        if strategy.get("adapted_strengths"):
            return strategy["adapted_strengths"]

        # Scorer에서 생성한 strengths가 있으면 사용하되, 너무 짧거나 일반적이면 heuristic 사용
        strengths = strategy.get("strengths") or strategy.get("score_breakdown", {}).get("strengths")
        valid_scorer_strengths = False
        if strengths and isinstance(strengths, list) and len(strengths) >= 2:
             # 괄호 제거 로직
             clean_strengths = []
             for s in strengths:
                 clean_s = s.split('(')[0].split(':')[ -1].strip() if ':' in s else s.split('(')[0].strip()
                 if clean_s: clean_strengths.append(clean_s)
             
             if len(clean_strengths) >= 2:
                  # [FIX] 단순 일반적 강점만 있는지 확인 (heuristic filtering)
                  if not all(s in ["자원 효율성", "환경 적합성", "높은 성공률"] for s in clean_strengths):
                       return clean_strengths[:3]
                  
        # heuristic fallback (아래 로직) 실행

            
        coa_name = strategy.get("coa_name") or strategy.get("명칭") or strategy.get("name") or "미상 방책"
        score = strategy.get("score") or strategy.get("최종점수", 0.5)
        
        # 3. 방책 명칭 기반 규칙 생성 (다양성 확보)
        effects = []
        if any(kw in coa_name for kw in ["선제", "공격", "타격", "Strike", "Counter"]):
            effects = [f"적 '{coa_name}' 위협 능력 근원적 무력화", "심리적 우위 달성 및 도발 억제", "추가 공격 의지 조기 분쇄"]
        elif any(kw in coa_name for kw in ["방어", "Defen", "차단", "Guard"]):
            effects = [f"아군 중요 자산 및 '{coa_name}' 방어선 사수", "적 진출 경로의 효과적 차단", "안정적인 방어 태세 유지"]
        elif any(kw in coa_name for kw in ["기동", "Maneuver", "우회", "Flank"]):
            effects = [f"'{coa_name}' 기동을 통한 적 허점 공략", "전술적 주도권 및 공간 확보", "적 부대 고립 및 연계 차단"]
        else:
            # 방책 이름을 활용한 동적 생성
            effects = [f"'{coa_name}' 작전을 통한 전술적 우위 확보", "아군 피해 최소화 및 작전 지속능력 보장", f"'{coa_name}' 실행으로 위협 요인 조기 제거"]
            
        # 점수에 따른 수식어 차별화
        if score > 0.85:
            return [f"방책 '{coa_name}'에 의한 극대화된 {e}" for e in effects]
        elif score > 0.7:
            return [f"방책 '{coa_name}'을 통한 확실한 {e}" for e in effects]
            
        return [f"'{coa_name}': {e}" for e in effects]
            

    
    def _analyze_situation(self, situation_id: Optional[str] = None,
                          user_query: str = "",
                          use_embedding: bool = True,
                          use_reasoned_graph: bool = True,
                          selected_situation_info: Optional[Dict] = None) -> Dict:
        """
        상황 분석 (SituationAgent 로직)
        
        Args:
            situation_id: 상황 ID (선택적)
            user_query: 사용자 질문 (situation_id가 없을 때 사용)
            selected_situation_info: 선택한 위협상황 정보 (폴백용)
        """
        # situation_id가 없거나 빈 문자열이면 일반 분석 수행
        if not situation_id or situation_id.strip() == "":
            safe_print(f"[INFO] _analyze_situation: situation_id가 없으므로 일반 분석 수행")
            return self._analyze_situation_generic(user_query)
        
        # 1. 상황 정보 로드
        situation_info = self._load_situation(situation_id)
        if not situation_info:
            # 조회 실패 시 selected_situation_info 폴백 사용
            if selected_situation_info:
                safe_print(f"[WARN] 테이블에서 상황 정보를 찾을 수 없음, selected_situation_info 사용: {situation_id}")
                situation_info = selected_situation_info
            else:
                return {"error": f"상황 정보를 찾을 수 없습니다: {situation_id}"}
        
        # 2. 다차원 분석
        dimension_analysis = self._analyze_situation_dimensions(situation_info)
        
        # 3. 관련 엔티티 탐색 (그래프 기반)
        related_entities = []
        if self.core.ontology_manager.graph is not None:
            try:
                related_entities = self._find_related_entities_enhanced(
                    situation_info,
                    use_reasoned=use_reasoned_graph
                )
                safe_print(f"[INFO] 관련 엔티티 탐색 완료: {len(related_entities)}개 발견")
            except Exception as e:
                safe_print(f"[WARN] 관련 엔티티 탐색 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 4. RAG 검색 (선택적)
        rag_results = []
        if use_embedding and self.core.rag_manager.is_available():
            try:
                threat_query = f"위협 상황 {situation_info.get('상황명', situation_id)}"
                rag_results = self.core.rag_manager.retrieve_with_context(
                    threat_query,
                    top_k=5
                )
            except Exception as e:
                safe_print(f"[WARN] RAG 검색 실패: {e}")
        
        # 5. LLM이 상황을 분석 (협력)
        llm_analysis = self._llm_analyze_situation(
            situation_info, 
            user_query,
            selected_situation_info
        )
        
        # 6. Agent가 LLM 분석을 통합
        situation_analysis = {
            "situation_info": situation_info,
            "dimension_analysis": dimension_analysis,
            "related_entities": related_entities,
            "rag_results": rag_results,
            # LLM 분석 결과 추가
            "llm_insights": llm_analysis.get("insights", {}),
            "llm_context": llm_analysis.get("context", ""),
            "llm_threat_assessment": llm_analysis.get("threat_assessment", {}),
            "llm_analysis_used": bool(llm_analysis.get("insights"))
        }
        
        # LLM 인사이트를 situation_info에 통합
        if llm_analysis.get("insights"):
            situation_info["llm_key_factors"] = llm_analysis["insights"].get("key_factors", [])
            situation_info["llm_constraints"] = llm_analysis["insights"].get("constraints", [])
        
        return situation_analysis
    
    def _analyze_situation_generic(self, user_query: str = "") -> Dict:
        """
        일반적인 상황 분석 (situation_id가 없을 때)
        사용자 질문 기반으로 일반적인 방책 분석 수행
        """
        try:
            safe_print(f"[INFO] 일반 상황 분석 시작 (질문: {user_query})")
            
            # "현재 위협상황" 질문인 경우 실제 데이터 조회
            if "위협상황" in user_query or "위협 상황" in user_query or "현재 위협" in user_query:
                all_threats = self._load_all_threats()
                if all_threats:
                    safe_print(f"[INFO] 실제 위협 상황 {len(all_threats)}개 발견")
                    # 심각도 기준으로 정렬
                    try:
                        sorted_threats = sorted(
                            all_threats,
                            key=lambda x: float(str(x.get('심각도', x.get('위협수준', 0))).replace(',', '')) if x.get('심각도') or x.get('위협수준') else 0,
                            reverse=True
                        )
                        situation_info = sorted_threats[0]  # 가장 심각한 위협 사용
                        safe_print(f"[INFO] 가장 심각한 위협 상황 사용: {situation_info.get('위협ID', 'Unknown')}")
                    except Exception as e:
                        safe_print(f"[WARN] 위협 상황 정렬 실패: {e}, 첫 번째 위협 사용")
                        situation_info = all_threats[0]
                else:
                    safe_print("[WARN] 위협 상황 데이터를 찾을 수 없습니다. 기본값 사용")
                    situation_info = self._create_default_situation_info(user_query)
            else:
                # 기본 상황 정보 생성 및 키워드 기반 위협 식별
                situation_info = self._create_default_situation_info(user_query)
                
                # 사용자 질문에서 위협 유형 추출 시도
                threat_keywords = {
                    "침투": ["침투", "침입", "intrusion", "infiltration"],
                    "포격": ["포격", "포탄", "shelling", "artillery"],
                    "기습공격": ["기습", "공격", "surprise", "attack"],
                    "사이버": ["사이버", "해킹", "cyber", "hacking"],
                    "국지도발": ["도발", "분쟁", "provocation"]
                }
                
                for threat_type, keywords in threat_keywords.items():
                    if any(word in user_query.lower() for word in keywords):
                        situation_info["위협유형"] = threat_type
                        safe_print(f"[INFO] 질문에서 위협 유형 추출 성공: {threat_type}")
                        break
            
            # 다차원 분석
            dimension_analysis = self._analyze_situation_dimensions(situation_info)
            
            # RAG 검색 (사용자 질문 기반)
            rag_results = []
            if self.core.rag_manager and self.core.rag_manager.is_available():
                try:
                    query = user_query if user_query else "적군 침입 방책"
                    safe_print(f"[INFO] RAG 검색 수행: {query}")
                    rag_results = self.core.rag_manager.retrieve_with_context(
                        query,
                        top_k=5
                    )
                    safe_print(f"[INFO] RAG 검색 결과: {len(rag_results)}개")
                except Exception as e:
                    safe_print(f"[WARN] RAG 검색 실패: {e}")
                    import traceback
                    traceback.print_exc()
            
            result = {
                "situation_info": situation_info,
                "dimension_analysis": dimension_analysis,
                "related_entities": [],
                "rag_results": rag_results
            }
            
            safe_print(f"[INFO] 일반 상황 분석 완료: situation_info 키 개수 = {len(situation_info)}")
            return result
            
        except Exception as e:
            safe_print(f"[ERROR] 일반 상황 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            # 에러가 발생해도 기본 정보는 반환
            return {
                "situation_info": {
                    "위협유형": "일반적 침입",
                    "심각도": 0.7,
                    "상황명": user_query if user_query else "일반적 적군 침입 상황"
                },
                "dimension_analysis": {},
                "related_entities": [],
                "rag_results": []
            }
    
    def _load_situation(self, situation_id: Optional[str]) -> Optional[Dict]:
        """위협상황 데이터에서 상황 정보 로드 (data_manager 사용)"""
        if situation_id is None:
            return None
        
        try:
            # 데이터 캐시가 없으면 로드
            if self._data_cache is None:
                self._data_cache = self.core.data_manager.load_all()
            
            # 위협상황 테이블 찾기
            threat_df = None
            # 1순위: '위협상황'이 정확히 포함된 테이블 (예: '위협상황', '위협상황.xlsx')
            for table_name, df in self._data_cache.items():
                if '위협상황' in table_name:
                    threat_df = df
                    break
            
            # 2순위: '위협'이 포함된 테이블 (단, '관련성'이나 '가중치' 등은 제외)
            if threat_df is None:
                for table_name, df in self._data_cache.items():
                    if '위협' in table_name and '관련성' not in table_name and '가중치' not in table_name:
                        threat_df = df
                        break
            
            if threat_df is None or threat_df.empty:
                safe_print("[WARN] 위협상황 데이터를 찾을 수 없습니다.")
                return None
            
            # 위협ID 컬럼 찾기
            id_col = None
            for col in threat_df.columns:
                if '위협ID' in str(col) or str(col) == 'ID' or str(col).lower() == 'id':
                    id_col = col
                    break
            
            if id_col:
                # 타입 불일치 해결: 문자열/숫자 모두 처리 (공백 제거 및 대소문자 무시 포함)
                try:
                    # 1. 정규화된 문자열로 변환하여 전체 비교
                    normalized_id = str(situation_id).strip().upper()
                    
                    def normalize_series(s):
                        return s.astype(str).str.strip().str.upper()

                    row = threat_df[normalize_series(threat_df[id_col]) == normalized_id]
                    
                    if row.empty:
                        # 2. 숫자 타입인 경우 직접 비교 시도
                        sit_id_str = str(situation_id)
                        if sit_id_str.isdigit():
                            row = threat_df[threat_df[id_col] == int(sit_id_str)]
                        else:
                            # 3. 원본 타입으로 단순 비교
                            row = threat_df[threat_df[id_col] == situation_id]
                    
                    if not row.empty:
                        return row.iloc[0].to_dict()
                    else:
                        safe_print(f"[WARN] 위협상황을 찾을 수 없습니다: situation_id={situation_id}, 컬럼={id_col}")
                except Exception as e:
                    safe_print(f"[WARN] 위협상황 조회 중 오류: {e}, situation_id={situation_id}")
                    # 폴백: 원본 타입으로 비교
                    try:
                        row = threat_df[threat_df[id_col] == situation_id]
                        if not row.empty:
                            return row.iloc[0].to_dict()
                    except:
                        pass
            else:
                safe_print(f"[WARN] 위협ID 컬럼을 찾을 수 없습니다. 컬럼: {list(threat_df.columns)}")
        except Exception as e:
            safe_print(f"[ERROR] 위협상황 로드 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def _load_all_threats(self, ) -> List[Dict]:
        """위협상황 데이터에서 모든 위협 상황 로드 (data_manager 사용)"""
        try:
            # 데이터 캐시가 없으면 로드
            if self._data_cache is None:
                self._data_cache = self.core.data_manager.load_all()
            
            # 위협상황 테이블 찾기
            threat_df = None
            for table_name, df in self._data_cache.items():
                if '위협상황' in table_name or '위협' in table_name:
                    threat_df = df
                    break
            
            if threat_df is None or threat_df.empty:
                safe_print("[WARN] 위협상황 데이터를 찾을 수 없습니다.")
                return []
            
            # 모든 행을 딕셔너리 리스트로 변환
            threats = []
            for _, row in threat_df.iterrows():
                threats.append(row.to_dict())
            
            return threats
        except Exception as e:
            safe_print(f"[ERROR] 위협상황 전체 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _create_default_situation_info(self, user_query: str = "") -> Dict:
        """기본 상황 정보 생성"""
        return {
            "위협유형": "일반적 침입",
            "심각도": 0.7,
            "긴급도": "중",
            "위험도": "중",
            "상황명": user_query if user_query else "일반적 적군 침입 상황",
            "적규모": "미확인",
            "적장비유형": "미확인",
            "적위치": "미확인",
            "적의도": "침입",
            "가용장비": [],
            "가용부대목록": "",
            "지원가능시간": "",
            "기상상태": "",
            "지형유형": "",
            "가시거리": "",
            "야간작전여부": False,
            "시간압박도": 0.5,
            "예상피해규모": ""
        }
    
    def _analyze_situation_dimensions(self, situation_info: Dict) -> Dict:
        """다차원 상황 분석"""
        return {
            "urgency": {
                "level": situation_info.get('긴급도', situation_info.get('중요도', '중')),
                "time_pressure": float(situation_info.get('시간압박도', 0.5))
            },
            "risk": {
                "level": situation_info.get('위험도', '중'),
                "expected_damage": situation_info.get('예상피해규모', '')
            },
            "environment": {
                "weather": situation_info.get('기상상태', ''),
                "terrain": situation_info.get('지형유형', ''),
                "visibility": situation_info.get('가시거리', ''),
                "night_operation": situation_info.get('야간작전여부', False)
            },
            "resources": {
                "available_units": situation_info.get('가용부대목록', ''),
                "available_equipment": situation_info.get('가용장비', ''),
                "support_time": situation_info.get('지원가능시간', '')
            },
            "enemy": {
                "scale": situation_info.get('적규모', ''),
                "equipment": situation_info.get('적장비유형', ''),
                "location": situation_info.get('적위치', ''),
                "intent": situation_info.get('적의도', '')
            }
        }
    
    def _find_related_entities_enhanced(self, situation_info: Dict, 
                                       use_reasoned: bool = True) -> List[Dict]:
        """그래프 기반 관련 엔티티 탐색 (개선 버전)"""
        related_entities = []
        
        if self.core.ontology_manager.graph is None:
            safe_print("[INFO] 온톨로지 그래프가 없어 관련 엔티티 탐색을 건너뜁니다.")
            return related_entities
        
        try:
            graph = self.core.ontology_manager.graph
            ns = self.core.ontology_manager.ns  # 통일된 네임스페이스 사용
            ns_legacy = self.core.ontology_manager.ns_legacy  # 기존 데이터 호환용
            
            from rdflib import URIRef, RDFS, RDF
            
            # 상황 식별자 여러 방법으로 시도
            situation_id = situation_info.get('위협ID') or situation_info.get('ID') or situation_info.get('situation_id') or situation_info.get('id')
            situation_name = situation_info.get('상황명', '')
            threat_type = situation_info.get('위협유형', '')
            
            safe_print(f"[DEBUG] 관련 엔티티 탐색 시작: situation_id={situation_id}, situation_name={situation_name}, threat_type={threat_type}")
            
            # 1. 위협ID로 직접 URI 찾기
            situation_uri = None
            if situation_id:
                # 여러 네임스페이스 시도 (새로운 네임스페이스 우선, 기존 네임스페이스 호환)
                for ns_to_try in [ns, ns_legacy]:
                    try:
                        # 위협상황_ 접두사 추가
                        situation_id_with_prefix = f"위협상황_{situation_id}" if not situation_id.startswith("위협상황_") else situation_id
                        candidate_uri = URIRef(f"{ns_to_try}{situation_id_with_prefix}")
                        # 그래프에 존재하는지 확인
                        if (candidate_uri, None, None) in graph:
                            situation_uri = candidate_uri
                            safe_print(f"[INFO] 위협ID로 상황 URI 찾음: {situation_uri}")
                            break
                    except:
                        continue
            
            # 2. RDFS.label로 찾기
            if not situation_uri and situation_name:
                for s, p, o in graph.triples((None, RDFS.label, None)):
                    if situation_name in str(o):
                        situation_uri = s
                        safe_print(f"[INFO] RDFS.label로 상황 URI 찾음: {situation_uri}")
                        break
            
            # 3. 위협상황 타입으로 찾기 (위협유형으로 필터링)
            if not situation_uri:
                # 위협상황 타입의 모든 인스턴스 찾기 (두 네임스페이스 모두 시도)
                for threat_situation_type in [ns.위협상황, ns_legacy.위협상황]:
                    for s, p, o in graph.triples((None, RDF.type, threat_situation_type)):
                        if threat_type:
                            # 위협유형으로 필터링
                            for _, pred, obj in graph.triples((s, None, None)):
                                pred_str = str(pred).lower()
                                if '위협유형' in pred_str or 'threat' in pred_str or 'type' in pred_str:
                                    if threat_type in str(obj):
                                        situation_uri = s
                                        safe_print(f"[INFO] 위협유형으로 상황 URI 찾음: {situation_uri}")
                                        break
                            if situation_uri:
                                break
                        else:
                            # 위협유형이 없으면 첫 번째 위협상황 사용
                            situation_uri = s
                            safe_print(f"[INFO] 첫 번째 위협상황 사용: {situation_uri}")
                            break
                    if situation_uri:
                        break
            
            # 4. 발생장소로 찾기 (마지막 시도)
            if not situation_uri:
                location = situation_info.get('발생장소', situation_info.get('장소', ''))
                if location:
                    # 발생장소가 있는 위협상황 찾기
                    for s, p, o in graph.triples((None, None, None)):
                        if '장소' in str(p).lower() or 'location' in str(p).lower():
                            if location in str(o):
                                # 이 엔티티가 위협상황인지 확인
                                for _, _, type_obj in graph.triples((s, RDF.type, None)):
                                    if '위협' in str(type_obj) or 'threat' in str(type_obj).lower():
                                        situation_uri = s
                                        safe_print(f"[INFO] 발생장소로 상황 URI 찾음: {situation_uri}")
                                        break
                                if situation_uri:
                                    break
                        if situation_uri:
                            break
            
            if situation_uri:
                # 1-hop: 직접 연결된 노드
                entity_map = {}  # 중복 제거용
                
                for pred, obj in graph.predicate_objects(situation_uri):
                    if isinstance(obj, URIRef):
                        entity_id = str(obj).split('#')[-1].split('/')[-1]
                        pred_name = str(pred).split('#')[-1].split('/')[-1]
                        
                        # 리터럴이 아닌 URI만 추가
                        if entity_id and entity_id not in ['None', '']:
                            if entity_id not in entity_map:
                                # 엔티티 타입 확인
                                entity_type = self._get_entity_type_from_graph(graph, obj)
                                
                                entity_map[entity_id] = {
                                    "id": entity_id,
                                    "label": entity_id,
                                    "type": entity_type,
                                    "relations": [pred_name]
                                }
                            else:
                                # 기존 엔티티에 관계 추가
                                if pred_name not in entity_map[entity_id]["relations"]:
                                    entity_map[entity_id]["relations"].append(pred_name)
                
                # 2-hop: 간접 연결된 노드 (관련 엔티티가 적을 때만)
                if len(entity_map) < 5:
                    for pred, obj in graph.predicate_objects(situation_uri):
                        if isinstance(obj, URIRef):
                            # 2-hop 탐색
                            for pred2, obj2 in graph.predicate_objects(obj):
                                if isinstance(obj2, URIRef) and obj2 != situation_uri:
                                    entity_id = str(obj2).split('#')[-1].split('/')[-1]
                                    if entity_id and entity_id not in ['None', '']:
                                        if entity_id not in entity_map:
                                            entity_type = self._get_entity_type_from_graph(graph, obj2)
                                            entity_map[entity_id] = {
                                                "id": entity_id,
                                                "label": entity_id,
                                                "type": entity_type,
                                                "relations": [str(pred2).split('#')[-1].split('/')[-1]]
                                            }
                
                related_entities = list(entity_map.values())
                safe_print(f"[INFO] 관련 엔티티 탐색 완료: {len(related_entities)}개 발견")
                
                # 🔥 찾은 situation_uri를 situation_info에 저장 (체인 탐색에서 재사용)
                if situation_uri:
                    situation_info['situation_uri'] = str(situation_uri)
            else:
                safe_print(f"[WARN] 상황 URI를 찾을 수 없습니다. situation_id={situation_id}, situation_name={situation_name}")
                # 상황 URI를 찾지 못했어도, 일반적인 관련 엔티티 검색 시도
                # 위협유형이나 발생장소로 관련 엔티티 찾기
                if threat_type or situation_info.get('발생장소'):
                    related_entities = self._find_entities_by_keywords(graph, threat_type, situation_info.get('발생장소', ''))
                
        except Exception as e:
            safe_print(f"[WARN] 관련 엔티티 탐색 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return related_entities
    
    def _get_entity_type_from_graph(self, graph, entity_uri) -> str:
        """그래프에서 엔티티 타입 추출"""
        try:
            from rdflib import RDF
            # RDF.type으로 타입 찾기
            for _, _, type_obj in graph.triples((entity_uri, RDF.type, None)):
                type_str = str(type_obj).split('#')[-1].split('/')[-1]
                if type_str and type_str not in ['None', '']:
                    return type_str
        except:
            pass
        return "기타"
    
    def _find_entities_by_keywords(self, graph, threat_type: str = "", location: str = "") -> List[Dict]:
        """키워드로 관련 엔티티 찾기 (상황 URI를 찾지 못했을 때)"""
        related_entities = []
        entity_map = {}
        
        try:
            from rdflib import RDF
            
            # 위협유형으로 관련 엔티티 찾기
            if threat_type:
                for s, p, o in graph.triples((None, None, None)):
                    if threat_type in str(o):
                        entity_id = str(s).split('#')[-1].split('/')[-1]
                        if entity_id and entity_id not in ['None', ''] and entity_id not in entity_map:
                            entity_type = self._get_entity_type_from_graph(graph, s)
                            entity_map[entity_id] = {
                                "id": entity_id,
                                "label": entity_id,
                                "type": entity_type,
                                "relations": [str(p).split('#')[-1].split('/')[-1]]
                            }
            
            # 발생장소로 관련 엔티티 찾기
            if location:
                for s, p, o in graph.triples((None, None, None)):
                    if location in str(o):
                        entity_id = str(s).split('#')[-1].split('/')[-1]
                        if entity_id and entity_id not in ['None', ''] and entity_id not in entity_map:
                            entity_type = self._get_entity_type_from_graph(graph, s)
                            if entity_id not in entity_map:
                                entity_map[entity_id] = {
                                    "id": entity_id,
                                    "label": entity_id,
                                    "type": entity_type,
                                    "relations": [str(p).split('#')[-1].split('/')[-1]]
                                }
            
            related_entities = list(entity_map.values())
            if related_entities:
                safe_print(f"[INFO] 키워드로 관련 엔티티 {len(related_entities)}개 발견")
        except Exception as e:
            safe_print(f"[WARN] 키워드 기반 엔티티 탐색 오류: {e}")
        
        return related_entities
    
    def _extract_threat_level(self, situation_info: Dict) -> float:
        """
        위협수준 추출 (통합 변환기 사용)
        
        Args:
            situation_info: 상황 정보 딕셔너리
            
        Returns:
            위협수준 (0-1 범위)
        """
        # ✅ NEW: 표준 필드 우선 사용
        if "threat_level_normalized" in situation_info:
            val = float(situation_info["threat_level_normalized"])
            # 🔥 로그 최적화: 반복되는 로그 제거 (각 COA마다 호출되므로)
            # safe_print(f"[INFO] threat_level_normalized 사용: {val:.2f}")
            return val
        
        # threat_level 필드 확인 (0-1 범위)
        threat_level = situation_info.get('threat_level')
        if threat_level is not None:
            try:
                val = float(threat_level)
                if 0.0 <= val <= 1.0:
                    return val
            except (ValueError, TypeError):
                pass
        
        # 심각도/위협수준 확인 및 변환
        severity = situation_info.get('심각도') or situation_info.get('위협수준')
        if severity is not None:
            # ✅ NEW: 통합 변환기 사용 (문자열 "High" 등 지원)
            try:
                from common.situation_converter import SituationInfoConverter
                normalized, raw, label = SituationInfoConverter.normalize_threat_level(severity)
                safe_print(f"[INFO] 위협수준 변환: '{severity}' → {normalized:.2f} ({label})")
                return normalized
            except Exception as e:
                safe_print(f"[WARN] 위협수준 변환 실패: {e}")
                # 폴백: 기존 로직
                try:
                    severity_val = float(severity)
                    return severity_val / 100.0 if severity_val > 1.0 else severity_val
                except (ValueError, TypeError):
                    pass
        
        safe_print(f"[WARN] 위협수준을 찾을 수 없어 기본값 0.7 사용")
        return 0.7  # 기본값
    
    def _match_threat_type(self, target_type: str, keywords: str) -> bool:
        """
        위협 유형 매칭 (다국어 및 유의어 지원)
        Args:
            target_type: 현재 위협 유형 (예: "Air", "항공")
            keywords: 방책 키워드 문자열 (예: "대공, 항공, 방어")
        Returns:
            매칭 여부
        """
        if not target_type:
            return True # 타겟이 없으면 매칭으로 간주 (또는 호출측에서 처리)
            
        target = target_type.lower().strip()
        kw_lower = keywords.lower()
        
        # 1. 직접 매칭
        if target in kw_lower:
            return True
            
        # 2. 동의어 매핑
        synonyms = {
            "air": ["항공", "공중", "대공", "비행", "aircraft"],
            "항공": ["air", "aerial", "aircraft"],
            "ground": ["지상", "지면", "armor", "기갑", "mechanized"],
            "지상": ["ground", "land", "surface"],
            "missile": ["미사일", "유도탄", "탄도"],
            "미사일": ["missile", "ballistic"],
            "cyber": ["사이버", "해킹", "network"],
            "사이버": ["cyber", "hacking"],
            "artillery": ["포병", "포격", "장사정포"],
            "포병": ["artillery", "cannon"],
            "infiltration": ["침투", "특수전", "게릴라", "penetration"],
            "침투": ["infiltration", "insertion", "guerrilla", "기습공격", "penetration"],
            "attack": ["공격", "정면공격", "전면공격", "기습공격", "타격", "침투"],
            "공격": ["attack", "strike", "raid", "정면공격", "전면공격", "기습공격", "침투"],
            "정면공격": ["attack", "frontal attack", "전면공격", "공격", "주공"],
            "전면공격": ["total war", "attack", "정면공격", "공격", "화력격멸"],
            "기습공격": ["surprise attack", "strike", "침투", "공격"],
            "naval": ["해상", "해군", "함정"],
            "해상": ["naval", "marine", "maritime"],
            "도하": ["하천", "강안", "river", "crossing", "river_crossing", "도섭", "방어", "defense", "공격", "offensive", "반격", "기동", "maneuver"],
            "집결징후": ["집결", "concentration", "assembly", "공격", "offensive", "포격", "타격", "선제", "preemptive"],
            "국지도발": ["도발", "provocation", "침투", "기습", "억제", "deterrence", "방어", "defense"],
            "전면전": ["전쟁", "war", "공격", "offensive", "방어", "defense", "반격", "counter"],
            "포격": ["포병", "artillery", "cannon", "화력", "방어", "defense", "반격", "counter"]
        }
        
        # 타겟의 동의어들이 키워드에 있는지 확인
        if target in synonyms:
            for syn in synonyms[target]:
                if syn in kw_lower:
                    return True
                    
        # 키워드 내 단어들에 대한 역방향 매칭확인 (Optional)
        return False

    def _extract_threat_type(self, situation_info: Dict) -> str:
        """
        위협 유형 추출 (여러 필드명 지원)
        
        Args:
            situation_info: 상황 정보 딕셔너리
            
        Returns:
            위협 유형 문자열
        """
        return (situation_info.get('위협유형') or 
                situation_info.get('threat_type') or 
                situation_info.get('위협유형', ''))
    
    def _search_strategies_via_sparql(self, situation_info: Dict, coa_type: Optional[str] = None) -> List[Dict]:
        """
        SPARQL 기반 방책 검색 (Phase 2: Ontology-Native Logic)
        엑셀 필터링 대신 온톨로지 그래프 추론을 사용합니다.
        """
        if self.core.ontology_manager.graph is None:
            safe_print("[WARN] 온톨로지 그래프가 없어 SPARQL 검색을 수행할 수 없습니다.")
            return []
            
        graph = self.core.ontology_manager.graph
        NS = self.core.ontology_manager.ns_legacy
        
        # 위협 유형 추출
        threat_type = self._extract_threat_type(situation_info) or ""
        
        safe_print(f"[INFO] SPARQL 검색 시작 (위협: {threat_type}, 타입: {coa_type})")
        # 로그 추가
        safe_print(f"[DEBUG] SPARQL Filtering using Threat Type: '{threat_type}'")
        
        # SPARQL 쿼리 작성 (타입 필터링 적용)
        type_map = {
            "defense": "DefenseCOA",
            "offensive": "OffensiveCOA", 
            "counter_attack": "CounterAttackCOA",
            "preemptive": "PreemptiveCOA",
            "deterrence": "DeterrenceCOA",
            "maneuver": "ManeuverCOA",
            "information_ops": "InformationOpsCOA"
        }
        
        if coa_type:
            # 기존 레거시 호환성 유지 (단일 타입 검색 시)
            target_class = type_map.get(coa_type.lower(), "COA")
            target_classes = [target_class]
        else:
            # 🔥 NEW: Unified Search (모든 주요 방책 유형 동시 검색)
            target_classes = ["DefenseCOA", "OffensiveCOA", "CounterAttackCOA", 
                             "PreemptiveCOA", "DeterrenceCOA", "ManeuverCOA", "InformationOpsCOA"]
            
        safe_print(f"[INFO] SPARQL 검색 타겟 클래스 목록: {target_classes}")
        
        try:
            from rdflib import URIRef, RDF, RDFS
            ns = self.core.ontology_manager.ns
            # 🔥 FIX: Don't reference target_class when using target_classes list
            # target_class_node will be set in the loop below
            coa_library_class = ns.COA_Library
            
            strategies = {}
            
            # 1. COA_Library & Target Class (새 구조) 또는 Target Class (레거시 구조) 인스턴스 찾기
            candidate_coas = set()
            
            for target_class in target_classes:
                target_class_node = ns[target_class]
                for s, p, o in graph.triples((None, RDF.type, target_class_node)):
                    candidate_coas.add(s)
            
            for coa_node in candidate_coas:
                coa_uri = str(coa_node)
                coa_id = coa_uri.split('#')[-1]
                
                # 라벨(명칭) 조회
                names = list(graph.objects(coa_node, RDFS.label))
                name = str(names[0]) if names else coa_id
                
                # 설명 조회
                desc = ""
                for d in graph.objects(coa_node, RDFS.comment): desc = str(d)
                if not desc:
                    for d in graph.objects(coa_node, ns.설명): desc = str(d)
                
                # 점수 조회
                score = 0.5
                for s_val in graph.objects(coa_node, ns.hasSuccessRateValue): score = float(s_val)
                if score == 0.5:
                    for s_val in graph.objects(coa_node, ns.워게임_모의_분석_승률): score = float(s_val)
                
                # 🔥 NEW: 시각화 데이터 조회 (Sparql 모드)
                phase_info = "Phase 1" 
                for val in graph.objects(coa_node, ns.hasPhasingInfo): phase_info = str(val)
                
                main_effort = "N" 
                for val in graph.objects(coa_node, ns.isMainEffort): main_effort = str(val)
                
                vis_style = "Default"
                for val in graph.objects(coa_node, ns.hasVisualStyle): vis_style = str(val)

                # 추가 시각화 필드 (참여부대, 전술그래픽)
                part_units = ""
                for val in graph.objects(coa_node, ns.participating_units): part_units = str(val)
                if not part_units: # fallback to hasMainEffort if it contains unit names
                    from rdflib import Literal
                    m_eff = [str(o) for o in graph.objects(coa_node, ns.hasMainEffort) if isinstance(o, Literal)]
                    if m_eff: part_units = m_eff[0]

                tactical_graphics = ""
                for val in graph.objects(coa_node, ns.hasTacticalGraphics): tactical_graphics = str(val)

                main_axis_id = None
                # hasMainAxis (Object prop)
                for val in graph.objects(coa_node, ns.hasMainAxis):
                     main_axis_id = str(val).split('#')[-1].split('/')[-1]
                
                if coa_id not in strategies:
                    strategies[coa_id] = {
                        "ID": coa_id,
                        "명칭": name,
                        "설명": desc,
                        "키워드": [],
                        "필요자원": set(),
                        "전장환경_제약": set(),
                        "예상성공률": score,
                        "participating_units": part_units,
                        "visualization_data": {
                            "phasing": phase_info,
                            "main_effort": main_effort,
                            "style": vis_style,
                            "graphics": tactical_graphics,
                            "main_axis_id": main_axis_id
                        },
                        "source": "ontology"
                    }
                
                # 다중 값 조회 (threat, resources, constraint, suitable_threats, conditions)
                for t in graph.objects(coa_node, ns.countersThreat):
                    strategies[coa_id]["키워드"].append(str(t).split('#')[-1])
                for t in graph.objects(coa_node, ns.적합위협유형):
                    strategies[coa_id]["키워드"].append(str(t))
                for t in graph.objects(coa_node, ns.적용조건):
                    strategies[coa_id]["키워드"].append(str(t))
                for r in graph.objects(coa_node, ns.requiresResource):
                    strategies[coa_id]["필요자원"].add(str(r).split('#')[-1])
                for c in graph.objects(coa_node, ns.hasConstraint):
                    strategies[coa_id]["전장환경_제약"].add(str(c).split('#')[-1])
                
                # 🔥 방책 유형(Type) 추론 및 저장 (Unified Search 필수)
                # target_class 정보를 역추적하거나 RDF.type을 다시 조회하여 할당
                # 여기서는 RDF.type 중 COA 하위 클래스를 찾아서 할당
                coa_types = []
                for t_node in graph.objects(coa_node, RDF.type):
                    t_str = str(t_node).split('#')[-1]
                    if "COA" in t_str and t_str != "COA" and t_str != "NamedIndividual":
                         coa_types.append(t_str)
                
                # 가장 구체적인 타입 하나 선택 (매핑 테이블 역참조)
                reverse_type_map = {v: k for k, v in type_map.items()}
                # 기본값
                strategies[coa_id]["coa_type"] = "defense" 
                for t in coa_types:
                    if t in reverse_type_map:
                        strategies[coa_id]["coa_type"] = reverse_type_map[t]
                        break
            
            # 리스트 변환 및 필터링
            final_list = []
            for coa in strategies.values():
                # Set/List 변환
                coa["키워드"] = ", ".join(list(set(coa["키워드"])))
                coa["필요자원"] = ", ".join(list(coa["필요자원"]))
                coa["전장환경_제약"] = ", ".join(list(coa["전장환경_제약"]))
                
                # 🔥 NEW: 키워드 매칭 점수 계산 (검색 단계에서 우선순위 부여)
                keyword_match_score = 0
                if threat_type:
                    t_lower = threat_type.lower()
                    k_lower = coa["키워드"].lower()
                    d_lower = coa["설명"].lower()
                    n_lower = coa["명칭"].lower()
                    
                    if t_lower in k_lower: keyword_match_score += 3
                    if t_lower in d_lower: keyword_match_score += 1
                    if t_lower in n_lower: keyword_match_score += 2
                    
                    # 특수 키워드 보너스
                    for spec in ["침투", "공중", "도하", "상륙", "기갑", "화생방"]:
                        if spec in t_lower and spec in k_lower:
                            keyword_match_score += 2
                
                coa["keyword_match_score"] = keyword_match_score
                
                # 위협 유형 필터링 (다국어 지원 및 로직 개선)
                if threat_type:
                    coa_keywords = coa.get("키워드", "").lower()
                    coa_desc = coa.get("설명", "").lower()
                    
                    # 1. 억제(Deterrence), 정보작전(Information_Ops) 등 범용/비물리 타입인 경우 통과
                    current_coa_type = coa.get("coa_type", "").lower()
                    
                    # 🔥 FIX: 필터링 로직 강화 - 범용 타입이라도 키워드가 있으면 검사
                    is_match = False
                    
                    # 1. 범용 방책 (Defense, Offensive 등) - 완화된 기준
                    if coa_type and coa_type.lower() in ["defense", "offensive", "maneuver"]:
                         # 키워드가 아예 없으면 통과
                         if not coa_keywords:
                             is_match = True
                         # 키워드가 있으면 검사 (단, "일반" 위협이면 통과)
                         elif "일반" in threat_type or "unknown" in threat_type.lower():
                             is_match = True
                         # 매칭 시도
                         elif self._match_threat_type(threat_type, coa_keywords) or \
                              self._match_threat_type(threat_type, coa_desc) or \
                              self._match_threat_type(threat_type, coa.get("명칭", "")):
                             is_match = True
                         # 매칭 실패해도 범용 타입은 일부 허용 (단, 점수에서 페널티) -> 여기서는 후보군 포함
                         else:
                             # 특화 키워드(침투, 도발 등)가 있는데 현재 위협과 다르면 제외
                             is_specialized = any(k in coa_keywords for k in ["침투", "도발", "테러", "특수전", "infiltration"])
                             if is_specialized and not self._match_threat_type(threat_type, coa_keywords):
                                 is_match = False
                             else:
                                 is_match = True # 그 외에는 일단 통과 (점수에서 판별)

                    # 2. 특화 방책 (Deterrence, Information_Ops 등) - 해당 타입이면 통과
                    elif coa_type and coa_type.lower() in ["deterrence", "information_ops", "preemptive"]:
                        is_match = True

                    # 3. 키워드 매칭 (기본)
                    elif self._match_threat_type(threat_type, coa_keywords) or \
                         self._match_threat_type(threat_type, coa_desc) or \
                         self._match_threat_type(threat_type, coa.get("명칭", "")):
                        is_match = True
                    
                    # 4. '일반' 위협이면 통과
                    elif "일반" in threat_type or "unknown" in threat_type.lower():
                        is_match = True

                    if not is_match:
                        # safe_print(f"[DEBUG] 위협 미매칭 제외: {coa['명칭']} (방책키워드: {coa_keywords}, 현재위협: {threat_type})")
                        continue

                # 키 정규화 (Scorer 호환성 보장)
                coa["COA_ID"] = coa["ID"]
                coa["name"] = coa["명칭"]
                coa["description"] = coa["설명"]
                coa["required_resources"] = coa["필요자원"]
                coa["expected_success_rate"] = coa["예상성공률"]
                coa["environmental_constraints"] = coa["전장환경_제약"]
                # Display용
                coa["방책명"] = coa["명칭"]

                final_list.append(coa)
                
            safe_print(f"[INFO] 온톨로지 기반 검색 성공: {len(final_list)}건 (SPARQL, 위협: {threat_type})")
            # 디버깅: 첫 번째 방책 출력
            if final_list:
                safe_print(f"[DEBUG] SPARQL Result[0]: {final_list[0].get('명칭')}")
            return final_list
            
        except Exception as e:
            safe_print(f"[ERROR] SPARQL 쿼리 실패: {e}")
            return []

    def _search_strategies(self, situation_id: Optional[str],
                          situation_info: Dict,
                          top_k: int = 10,
                          use_embedding: bool = True,
                          inference_mode: str = "hybrid",
                          coa_type: Optional[str] = None) -> List[Dict]:
        """
        방책 후보 탐색 (COALibraryAgent 로직)
        situation_id가 없거나 situation_info가 비어있으면 모든 방책 반환
        
        Args:
            coa_type: 방책 타입 필터 (예: "defense", "offensive", "counter_attack" 등)
                     None이면 모든 타입 반환
        """
        try:
            # 🔥 NEW: Ontology-Native SPARQL Search (Phase 2)
            # 온톨로지 그래프가 있고, inference_mode가 hybrid/ontology인 경우 우선 시도
            if self.core.ontology_manager.graph is not None:
                sparql_strategies = self._search_strategies_via_sparql(situation_info, coa_type)
                if sparql_strategies:
                    safe_print(f"[INFO] 온톨로지 기반 검색 성공 ({len(sparql_strategies)}건). 엑셀 검색을 건너뜁니다.")
                    return sparql_strategies

            # 데이터 캐시가 없으면 로드
            if self._data_cache is None:
                self._data_cache = self.core.data_manager.load_all()
            
            # COA 라이브러리 테이블 찾기
            df_library = None
            
            # 1순위: 정확한 이름 매칭 시도
            if 'COA_Library' in self._data_cache:
                df_library = self._data_cache['COA_Library']
            # 2순위: 'COA'가 포함된 키 탐색
            else:
                for table_name in self._data_cache.keys():
                    if 'COA' in table_name and 'Library' in table_name:
                        df_library = self._data_cache[table_name]
                        break
            
            # 3순위: '방책'이 포함되지만 '템플릿'은 제외
            if df_library is None:
                for table_name, df in self._data_cache.items():
                    if '방책' in table_name and '템플릿' not in table_name:
                        df_library = df
                        break
            
            # 4순위: 최후의 수단 (필드 확인)
            if df_library is None:
                  for table_name, df in self._data_cache.items():
                    if '명칭' in df.columns and ('방책유형' in df.columns or 'type' in df.columns):
                        df_library = df
                        break
            

            if df_library is None or df_library.empty:
                available_tables = list(self._data_cache.keys()) if self._data_cache else []
                safe_print(f"[ERROR] COA 라이브러리 데이터를 찾을 수 없습니다.")
                safe_print(f"[DEBUG] 사용 가능한 테이블 목록: {available_tables}")
                safe_print(f"[DEBUG] 검색 조건: 'COA' or '라이브러리' or '방책' (template 제외)")
                
                if df_library is not None and df_library.empty:
                    safe_print("[WARN] COA 라이브러리가 비어있지만, 기본 방책을 제공합니다.")
                else:
                    safe_print("[ERROR] COA 라이브러리 테이블을 찾을 수 없어 빈 결과를 반환합니다.")
                    return []
            
            strategies = []
            
            # 방책유형 매핑 (코드 타입 -> 데이터 컬럼 값)
            coa_type_mapping = {
                "defense": "Defense",
                "offensive": "Offensive",
                "counter_attack": "CounterAttack",
                "preemptive": "Preemptive",
                "deterrence": "Deterrence",
                "maneuver": "Maneuver",
                "information_ops": "InformationOps"
            }
            
            # 위협 유형 기반 필터링 (필드명 통일 처리)
            threat_type = self._extract_threat_type(situation_info)
            threat_level = self._extract_threat_level(situation_info)
            threat_severity = situation_info.get('심각도') or situation_info.get('위협수준') or str(int(threat_level * 100))
            
            # 위협수준 기반 우선 필터링 (위협수준이 높으면 Main_Defense 우선)
            # 방책유형 필터링 적용
            for i, (_, row) in enumerate(df_library.iterrows()):
                coa = row.to_dict()
                
                # 🔥 NEW: 방책유형 필터링 (coa_type이 지정된 경우)
                if coa_type:
                    # 방책유형 컬럼 찾기
                    coa_type_col = None
                    for col in df_library.columns:
                        if '방책유형' in str(col) or 'type' in str(col).lower() or 'coa_type' in str(col).lower():
                            coa_type_col = col
                            break
                    
                    if coa_type_col:
                        # 데이터의 방책유형 값
                        data_coa_type = str(coa.get(coa_type_col, '')).strip()
                        # 코드 타입을 데이터 타입으로 변환
                        target_type = coa_type_mapping.get(coa_type.lower(), coa_type)
                        
                        # 대소문자 구분 없이 비교
                        if data_coa_type.lower() != target_type.lower():
                            # 필터링: 타입이 일치하지 않으면 건너뛰기
                            continue
                        # safe_print(f"[DEBUG] 방책유형 필터링: {coa_type} -> {data_coa_type} (일치)")
                    else:
                        # 방책유형 컬럼이 없으면 경고만 출력하고 계속 진행
                        safe_print(f"[WARN] 방책유형 컬럼을 찾을 수 없습니다. 필터링을 건너뜁니다.")
                
                match_score = 0.5  # 기본 점수
                match_method = 'generic'
                
                coa_name = str(coa.get('명칭') or coa.get('방책명') or coa.get('name') or '').lower()
                coa_id = str(coa.get('COA_ID') or coa.get('방책ID') or coa.get('ID') or '').lower()
                combined_name = f"{coa_name} {coa_id}"
                
                # 🔥 FIX: '적합위협유형', '적용조건', '설명' 컬럼을 키워드에 포함시켜 검색 정확도 향상
                keywords_raw = str(coa.get('키워드', '') or coa.get('keywords', '')).lower()
                suitable_threats = str(coa.get('적합위협유형', '')).lower()
                apply_condition = str(coa.get('적용조건', '')).lower()
                description = str(coa.get('설명', '')).lower()
                keywords = f"{keywords_raw}, {suitable_threats}, {apply_condition}, {description}" # 합쳐서 필터링 대상 확대
                
                # 🔥 NEW: 추가 속성 매핑 (점수 계산용)
                coa['required_resources'] = str(coa.get('필요자원', '')).split(',')
                coa['expected_success_rate'] = float(coa.get('워게임_모의_분석_승률') or coa.get('예상성공률') or coa.get('Estimated_Success_Rate') or 0.5)
                coa['environmental_constraints'] = str(coa.get('전장환경_제약', ''))
                
                # 위협수준 기반 우선순위 부여
                if threat_level >= 0.95:
                    # 매우 높은 위협: Main_Defense에 높은 우선순위
                    if ('main' in combined_name or '주요' in combined_name or '강력' in combined_name or 
                        ('defense' in combined_name and 'main' in combined_name)):
                        match_score = 0.9  # 매우 높은 우선순위
                        match_method = 'high_threat_main_defense'
                    elif 'moderate' in combined_name or '중간' in combined_name:
                        match_score = 0.3  # 낮은 우선순위
                        match_method = 'high_threat_moderate_defense'
                    elif 'minimal' in combined_name or '최소' in combined_name:
                        match_score = 0.1  # 매우 낮은 우선순위
                        match_method = 'high_threat_minimal_defense'
                elif threat_level > 0.8:
                    # 높은 위협: Main_Defense 우선
                    if ('main' in combined_name or '주요' in combined_name or '강력' in combined_name or 
                        ('defense' in combined_name and 'main' in combined_name)):
                        match_score = 0.8
                        match_method = 'high_threat_main_defense'
                    elif 'moderate' in combined_name or '중간' in combined_name:
                        match_score = 0.5
                        match_method = 'high_threat_moderate_defense'
                    elif 'minimal' in combined_name or '최소' in combined_name:
                        match_score = 0.2
                        match_method = 'high_threat_minimal_defense'
                elif threat_level > 0.5:
                    # 중간 위협: Moderate_Defense 우선
                    if 'moderate' in combined_name or '중간' in combined_name:
                        match_score = 0.7
                        match_method = 'moderate_threat_moderate_defense'
                    elif ('main' in combined_name or '주요' in combined_name or '강력' in combined_name or 
                          ('defense' in combined_name and 'main' in combined_name)):
                        match_score = 0.5
                        match_method = 'moderate_threat_main_defense'
                    elif 'minimal' in combined_name or '최소' in combined_name:
                        match_score = 0.3
                        match_method = 'moderate_threat_minimal_defense'
                else:
                    # 낮은 위협: Minimal_Defense 우선
                    if 'minimal' in combined_name or '최소' in combined_name:
                        match_score = 0.7
                        match_method = 'low_threat_minimal_defense'
                    elif 'moderate' in combined_name or '중간' in combined_name:
                        match_score = 0.5
                        match_method = 'low_threat_moderate_defense'
                    elif ('main' in combined_name or '주요' in combined_name or '강력' in combined_name or 
                          ('defense' in combined_name and 'main' in combined_name)):
                        match_score = 0.3
                        match_method = 'low_threat_main_defense'
                
                # 🔥 NEW: 엑셀 검색에서도 위협 유형 필터링 적용 (Strict Filtering)
                is_threat_match = True
                
                # '침투' 등 특수 위협에 대한 필터링 로직 강화
                # 1. 일반적인 Strict Filtering (방어, 공격 등)
                if coa_type and coa_type.lower() in ['defense', 'offensive', 'maneuver']:
                    if threat_type and keywords and "일반" not in threat_type.lower():
                        if not self._match_threat_type(threat_type, keywords) and \
                           not self._match_threat_type(threat_type, coa_name):
                             # 키워드 매칭 안되면 제외 (단, 특화 키워드가 있는 경우만 엄격 적용)
                             is_specialized = any(k in keywords for k in ["침투", "도발", "테러", "특수전", "infiltration"])
                             if is_specialized:
                                 is_threat_match = False
                             else:
                                 # 특화 키워드가 없으면 일단 통과 (점수 페널티)
                                 pass
                
                if not is_threat_match:
                    continue

                # 위협 유형 매칭 (추가 가산점 대폭 상향)
                is_type_match = False
                if threat_type and (self._match_threat_type(threat_type, keywords) or self._match_threat_type(threat_type, coa_name)):
                    match_score = min(1.0, match_score + 0.3) # +0.15 -> +0.3 (강력한 가산점)
                    is_type_match = True
                
                # 불일치 시 페널티 적용 (신규)
                if not is_type_match and threat_type and "일반" not in threat_type.lower():
                     if "침투" in threat_type or "특수전" in threat_type:
                          # 침투 상황인데 침투 대응 방책이 아니면 감점
                         match_score = max(0.0, match_score - 0.2)
                
                # 심각도 매칭 (추가 보너스)
                if threat_severity and str(threat_severity).lower() in keywords:
                    match_score = min(1.0, match_score + 0.05)
                
                # 🔥 NEW: 시각화 데이터 보강 (Excel 모드)
                coa['participating_units'] = coa.get('적용부대', '')
                coa['visualization_data'] = {
                    "main_axis_id": coa.get("주요축선ID"),
                    "graphics": coa.get("전술그래픽"),
                    "phasing": coa.get("단계정보"),
                    "main_effort": coa.get("주노력여부"),
                    "style": coa.get("시각화스타일")
                }
                
                coa['적합도점수'] = match_score
                coa['filter_method'] = match_method
                strategies.append(coa)
            
            # 규칙 엔진을 통한 점수 조정 (YAML 규칙 파일 기반)
            try:
                # 컨텍스트 구성 (규칙 평가용)
                rule_context = {
                    'threat_level': threat_level,
                    'threat_type': threat_type,
                    '심각도': threat_severity
                }
                # 규칙 기반 점수 조정
                strategies = self.rule_engine.apply_rule_based_scoring(strategies, rule_context)
                safe_print(f"[INFO] 규칙 엔진 적용 완료: {len([s for s in strategies if s.get('rule_applied')])}개 방책에 규칙 적용")
            except Exception as e:
                safe_print(f"[WARN] 규칙 엔진 적용 실패: {e}")
                # 규칙 엔진 실패 시 기존 로직 유지
            
            # 적합도 점수로 정렬 (동점 시 ID 기준 정렬로 일관성 유지)
            # 🔥 CRITICAL FIX: 타입 안전성 강화
            strategies.sort(
                key=lambda x: (
                    self._safe_float(x.get('적합도점수')), 
                    self._safe_str(x.get('COA_ID') or x.get('방책ID') or x.get('ID', ''))
                ), 
                reverse=True
            )
            
            # 🔥 NEW: 결과 로그
            safe_print(f"\n[DEBUG] ========== 방책 탐색 결과 ==========")
            safe_print(f"[DEBUG] 총 발견 방책: {len(strategies)}개")
            safe_print(f"[DEBUG] threat_level={threat_level:.2f}, threat_type={threat_type}, top_k={top_k}")
            
            if not strategies:
                safe_print(f"[WARN] ❌ COA 라이브러리에서 방책을 찾지 못했습니다! (타입: {coa_type or 'All'})")
                safe_print(f"[DEBUG] df_library shape={df_library.shape if df_library is not None else 'None'}")
                safe_print(f"[DEBUG] df_library columns={list(df_library.columns) if df_library is not None else 'None'}")
            else:
                safe_print(f"[INFO] ✅ {len(strategies)}개 방책 발견 (top_{top_k} 반환)")
                for i, s in enumerate(strategies[:min(5, len(strategies))]):
                    safe_print(f"[DEBUG]   #{i+1}. {s.get('명칭', 'N/A')} (점수: {s.get('적합도점수', 0):.2f}, 방법: {s.get('filter_method', 'N/A')})")
            
            safe_print(f"[DEBUG] =====================================\n")
            
            return strategies[:top_k]
            
        except Exception as e:
            safe_print(f"방책 탐색 오류: {e}")
            return []
    
    def _score_strategies(self, strategies: List[Dict], 
                         situation_info: Dict,
                         situation_analysis: Dict = None) -> List[Dict]:
        """
        기본 점수 계산 (LLM-Agent 협력 방식)
        
        Args:
            strategies: 방책 리스트
            situation_info: 상황 정보 딕셔너리
            situation_analysis: 상황 분석 결과 (LLM 인사이트 포함, 선택적)
        """
        # 위협수준 추출
        threat_level = self._extract_threat_level(situation_info)
        
        # 1. 기본 점수 계산 (Agent)
        for strategy in strategies:
            base_score = strategy.get('적합도점수', 0.5)
            coa_name = str(strategy.get('명칭') or strategy.get('방책명') or strategy.get('name') or '').lower()
            
            # 위협수준에 따라 점수 조정
            # 방책ID도 확인 (Main_Defense, Moderate_Defense, Minimal_Defense 등)
            coa_id = str(strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('ID') or '').lower()
            combined_name = f"{coa_name} {coa_id}"
            
            if threat_level > 0.8:
                # 높은 위협 (80% 이상): 강력한 방책에 가산점
                if ('main' in combined_name or '주요' in combined_name or '강력' in combined_name or 
                    'defense' in combined_name and 'main' in combined_name):
                    base_score += 0.3
                    coa_display_name = strategy.get('명칭') or strategy.get('방책명') or strategy.get('name') or 'Unknown'
                    safe_print(f"[INFO] 높은 위협({int(threat_level*100)}%): {coa_display_name}에 +0.3 가산점")
                elif 'moderate' in combined_name or '중간' in combined_name:
                    base_score += 0.1
                elif 'minimal' in combined_name or '최소' in combined_name:
                    base_score -= 0.2
                    coa_display_name = strategy.get('명칭') or strategy.get('방책명') or strategy.get('name') or 'Unknown'
                    safe_print(f"[INFO] 높은 위협({int(threat_level*100)}%): {coa_display_name}에 -0.2 감점")
            elif threat_level > 0.5:
                # 중간 위협 (50-80%): 중간 방책에 가산점
                if 'moderate' in combined_name or '중간' in combined_name:
                    base_score += 0.2
                elif 'main' in combined_name or '주요' in combined_name:
                    base_score += 0.1
                elif 'minimal' in combined_name or '최소' in combined_name:
                    base_score -= 0.1
            elif threat_level > 0.3:
                # 낮은 위협 (30-50%): 최소 방책에 가산점
                if 'minimal' in combined_name or '최소' in combined_name:
                    base_score += 0.2
                elif 'moderate' in combined_name or '중간' in combined_name:
                    base_score += 0.1
                elif 'main' in combined_name or '주요' in combined_name:
                    base_score -= 0.2
            else:
                # 매우 낮은 위협 (30% 미만): 최소 방책에 큰 가산점
                if 'minimal' in combined_name or '최소' in combined_name:
                    base_score += 0.3
                elif 'moderate' in combined_name or '중간' in combined_name:
                    base_score -= 0.1
                elif 'main' in combined_name or '주요' in combined_name:
                    base_score -= 0.3
            
            strategy['agent_score'] = min(1.0, max(0.0, base_score))
            strategy['최종점수'] = strategy['agent_score']  # 임시로 agent_score 사용
        
        # 2. LLM이 각 방책을 평가 (협력)
        llm_evaluations = self._llm_evaluate_strategies(
            strategies, 
            situation_info,
            situation_analysis
        )
        
        # 3. Agent 점수와 LLM 평가 통합
        for i, strategy in enumerate(strategies):
            llm_eval = llm_evaluations.get(i, {})
            # 🔥 CRITICAL FIX: llm_score를 항상 float으로 보장
            llm_score = self._safe_float(llm_eval.get("score", strategy.get('agent_score', 0.5)))
            llm_reason = llm_eval.get("reason", "")
            
            # 하이브리드 점수: Agent 70% + LLM 30%
            # 🔥 CRITICAL FIX: agent_score를 항상 float으로 보장
            agent_score = self._safe_float(strategy.get('agent_score', 0.5))
            hybrid_score = (
                agent_score * 0.7 +
                llm_score * 0.3
            )
            
            strategy['최종점수'] = min(1.0, max(0.0, hybrid_score))
            strategy['MAUT점수'] = strategy['최종점수']
            strategy['llm_reason'] = llm_reason
            strategy['llm_score'] = llm_score
            strategy['score_breakdown'] = {
                'agent_score': agent_score,
                'llm_score': llm_score,
                'hybrid_score': hybrid_score
            }
            
            # 추천사유 초기화 (나중에 _generate_recommendation_reason에서 생성)
            if llm_reason:
                strategy['추천사유'] = f"[전략 구체화] {llm_reason}"
            else:
                strategy['추천사유'] = None
        
        # 점수로 정렬 (동점 시 ID 기준 정렬로 일관성 유지)
        # 🔥 CRITICAL FIX: 타입 안전성 강화
        strategies.sort(
            key=lambda x: (
                self._safe_float(x.get('최종점수')), 
                self._safe_str(x.get('COA_ID') or x.get('방책ID') or x.get('ID', ''))
            ), 
            reverse=True
        )
        return strategies
    
    def _score_with_palantir_mode(self, strategies: List[Dict],
                                  situation_info: Dict,
                                  situation_analysis: Dict,
                                  coa_type: str = "defense") -> List[Dict]:
        """팔란티어 모드 점수 계산 (COA별 개별 점수 계산)"""
        # 🔥 DEBUG & CACHE CLEAR
        safe_print(f"\n[DEBUG] _score_with_palantir_mode called for {len(strategies)} candidates")
        threat_type = self._extract_threat_type(situation_info)
        safe_print(f"[DEBUG] Scoring with Threat Type: {threat_type}")
        self._chain_cache = {} # Force clear cache

        # 🔥 NEW: axis_states 빌드 (METT-C 평가를 위해 필요)
        axis_states = []
        try:
            from core_pipeline.axis_state_builder import AxisStateBuilder
            from core_pipeline.data_models import ThreatEvent
            
            # ThreatEvent 객체 생성
            threat_event = ThreatEvent.from_row(situation_info)
            
            # AxisStateBuilder 초기화
            axis_builder = AxisStateBuilder(
                data_manager=self.core.data_manager,
                ontology_manager=self.core.ontology_manager
            )
            
            # axis_states 빌드
            mission_id = situation_info.get('관련임무ID', situation_info.get('related_mission_id'))
            axis_states = axis_builder.build_axis_states_from_threat(threat_event, mission_id=mission_id)
            
            if not axis_states:
                safe_print("[WARN] axis_states를 빌드할 수 없습니다. METT-C 평가가 제한될 수 있습니다.")
        except Exception as e:
            safe_print(f"[WARN] axis_states 빌드 실패: {e}. METT-C 평가가 제한될 수 있습니다.")
            axis_states = []

        from core_pipeline.coa_scorer import COAScorer
        
        # COA Scorer 초기화 (data_manager와 config 전달하여 Excel에서 가중치 로드)
        # coa_type 전달하여 타입별 가중치 사용
        # 🔥 Update: Adaptive Weighting을 위해 situation_info(context) 전달
        # [PERFORMANCE] CorePipeline의 매퍼 재사용 (중복 초기화 방지)
        scorer = COAScorer(
            data_manager=self.core.data_manager, 
            config=self.core.config, 
            coa_type=coa_type, 
            context=situation_info,
            relevance_mapper=getattr(self.core, 'relevance_mapper', None),
            resource_parser=getattr(self.core, 'resource_parser', None)
        )
        situation_id = situation_info.get('위협ID', situation_info.get('ID', 'THREAT001'))
        
        # 🔥 NEW: Threat Appropriateness Matrix 로드
        threat_appropriateness = scorer.THREAT_COA_APPROPRIATENESS

        
        # Pass 1: 대략적인 점수 계산 (모든 후보 대상)
        self._report_status(f"Pass 1: {len(strategies)}개 후보 방책에 대한 기초 평가 수행 중...")
        pass1_strategies = []
        for strategy in strategies:
            # COA ID 추출 (COA_ID, 방책ID, ID, coa_id 순서로 시도)
            coa_id = strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('ID') or strategy.get('coa_id')
            if not coa_id:
                safe_print(f"[WARN] COA ID를 찾을 수 없습니다: {strategy}")
                continue

            # 온톨로지 URI 변환
            coa_uri = coa_id
            if self.core.ontology_manager:
                coa_id_safe = str(coa_id).split('#')[-1] if '#' in str(coa_id) else str(coa_id)
                if hasattr(self.core.ontology_manager, '_make_uri_safe'):
                    coa_id_safe = self.core.ontology_manager._make_uri_safe(coa_id_safe)
                else:
                    import re
                    coa_id_safe = re.sub(r'\s+', '_', coa_id_safe.strip())
                    coa_id_safe = re.sub(r'[(){}\[\]<>|\\^`"\':;,?#%&+=]', '', coa_id_safe)
                if not coa_id_safe.startswith("COA_Library_"):
                    coa_uri = f"http://coa-agent-platform.org/ontology#COA_Library_{coa_id_safe}"
                else:
                    coa_uri = f"http://coa-agent-platform.org/ontology#{coa_id_safe}"

            # Pass 1에서는 chain 점수를 0.5로 설정하여 대략적인 점수 계산
            pass1_context = {
                "threat_level": self._extract_threat_level(situation_info),
                "defense_assets": situation_info.get('가용장비', []),
                "rag_results": situation_analysis.get("rag_results", []),
                "chain_info": {"score": 0.5}, # 기본값 설정
                "coa_uri": coa_uri,
                "coa_id": coa_id,
                "ontology_manager": self.core.ontology_manager,
                "required_resources": strategy.get('required_resources', []),
                "available_resources": situation_info.get('available_resources', []),  # 🔥 FIX: 가용 자원 추가 (assets 점수 계산용)
                "expected_success_rate": strategy.get('expected_success_rate', 0.5),
                "environmental_constraints": strategy.get('environmental_constraints', ''),
                "mission_type": situation_info.get('임무유형') or situation_info.get('임무종류') or situation_info.get('mission_type'),
                "coa_type": coa_type,
                "threat_type": situation_info.get('위협유형') or situation_info.get('threat_type') or situation_info.get('위협유형코드'),
                "coa_suitability": self._safe_float(strategy.get('적합도점수', 1.0)),
                "situation_id": situation_id,
                "is_first_coa": False # Pass 1에서는 모두 첫 번째 COA가 아님
            }
            
            # 🔥 NEW: Pass 1에서 적합도 점수 강제 적용 (변별력 강화)
            # COA Scorer의 매트릭스를 활용하여 위협 유형과 COA 유형 간의 궁합 점수 계산
            appropriateness_score = 0.5  # 기본값
            
            # 1. 위협 유형 매칭 (한글/영어/유사어)
            t_type_candidates = [
                pass1_context["threat_type"], 
                threat_type,
                situation_info.get('threat_type_code'),
                situation_info.get('위협유형')
            ]
            t_type_matched_key = None
            
            # 매트릭스 키와 매칭 시도
            for cand in t_type_candidates:
                if not cand: continue
                cand_str = str(cand).strip()
                if cand_str in threat_appropriateness:
                    t_type_matched_key = cand_str
                    break
                # 부분 매칭 시도 (예: "Air Threat" -> "공중위협", "Air")
                for key in threat_appropriateness.keys():
                    if key in cand_str or cand_str in key: # 상호 포함 관계
                        t_type_matched_key = key
                        break
                    # 영문/한글 매핑 (하드코딩 Fallback)
                    if cand_str.lower() in ["air", "aircraft", "helicopter", "uav"] and key == "공중위협":
                        t_type_matched_key = key
                        break
                    if cand_str.lower() in ["armor", "tank"] and key == "기갑공격":  # 매트릭스에 기갑공격이 있다면
                         pass # 현재 매트릭스에는 '정면공격' 등이 있음.
                if t_type_matched_key: break
            
            # 2. 적합도 점수 조회
            if t_type_matched_key:
                matrix = threat_appropriateness[t_type_matched_key]
                # COA Type 확인
                c_type = strategy.get("coa_type", "defense").lower()
                
                # 매트릭스에서 점수 조회 (없으면 기본값 0.5)
                appropriateness_score = matrix.get(c_type, 0.5)
                # safe_print(f"[DEBUG] 적합도 점수 적용: {t_type_matched_key} vs {c_type} -> {appropriateness_score}")
            
            # 3. Pass 1 Context에 주입 (chain 점수 대용 또는 별도 팩터)
            # 초기 평가에서는 구체적 체인이 없으므로, 이 적합도 점수를 '전술적 타당성'으로 활용
            pass1_context["chain_info"] = {"score": appropriateness_score}
            # 별도 필드로도 저장 (나중에 가중치 적용 시 활용 가능)
            pass1_context["appropriateness_score"] = appropriateness_score
            
            # [NEW] 환경 정보 주입 (UI 입력 -> Context)
            if 'environment' in situation_info:
                pass1_context.update(situation_info['environment'])
            
            # 자원/환경 정보 추출 (Pass 1에서도 필요)
            if self.core.ontology_manager and self.core.ontology_manager.graph is not None:
                try:
                    from core_pipeline.reasoning_engine import ReasoningEngine
                    reasoning_engine = ReasoningEngine()
                    pass1_context["resource_availability"] = reasoning_engine._extract_resource_availability(pass1_context)
                    pass1_context["environment_fit"] = reasoning_engine._extract_environment_fit(pass1_context)
                except Exception as e:
                    safe_print(f"[WARN] Pass 1 자원/환경 정보 추출 실패: {e}")
                    pass1_context["resource_availability"] = 0.5
                    pass1_context["environment_fit"] = 0.5
            else:
                pass1_context["resource_availability"] = 0.5
                pass1_context["environment_fit"] = 0.5

            pass1_score_result = scorer.calculate_score(pass1_context)
            strategy['pass1_score'] = pass1_score_result.get('total', 0) # Use 'total' key from COAScorer
            strategy['최종점수'] = strategy['pass1_score'] # 초기 점수 설정
            strategy['MAUT점수'] = strategy['pass1_score']
            # 🔥 FIX: Pass 1 breakdown 저장 (Pass 2에서 업데이트되기 전까지 사용)
            pass1_breakdown = pass1_score_result.get('breakdown', {})
            strategy['score_breakdown'] = pass1_breakdown.copy() if pass1_breakdown else {}
            # 디버깅: Pass 1 breakdown 로그
            safe_print(f"[DEBUG] Pass 1: COA {coa_id} breakdown = {pass1_breakdown}")
            strategy['confidence'] = pass1_score_result.get('confidence', 0.5)
            strategy['strengths'] = pass1_score_result.get('strengths', [])
            strategy['weaknesses'] = pass1_score_result.get('weaknesses', [])
            strategy['reasoning'] = pass1_score_result.get('reasoning', [])
            pass1_strategies.append(strategy)
        
        # 점수 순으로 정렬하여 상위 5개 추출 (동점 시 ID 기준 정렬로 일관성 유지)
        # 🔥 CRITICAL FIX: 타입 안전성 강화
        sorted_strategies = sorted(
            pass1_strategies, 
            key=lambda x: (
                self._safe_float(x.get('pass1_score')), 
                self._safe_str(x.get('COA_ID') or x.get('방책ID') or x.get('ID', ''))
            ), 
            reverse=True
        )
        top_k_for_pass2 = sorted_strategies[:5]
        
        # Pass 2: 정밀 점수 계산 (상위 5개 대상 - 병렬 처리 적용)
        self._report_status(f"Pass 2: 유망 후보 {len(top_k_for_pass2)}개 방책에 대한 정밀 분석 및 스코어링 중...")
        
        # 병렬 처리를 위한 헬퍼 함수
        # axis_states를 클로저로 캡처하기 위해 함수 정의 전에 변수 확인
        captured_axis_states = axis_states  # 클로저를 위한 명시적 캡처
        
        def _process_strategy_pass2(idx_strategy_tuple):
            idx, strategy = idx_strategy_tuple
            # axis_states를 캡처된 변수로 사용 (병렬 처리에서 클로저가 제대로 작동하도록)
            local_axis_states = captured_axis_states
            coa_id = strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('ID') or strategy.get('coa_id')
            
            if self.core.ontology_manager:
                coa_id_safe = str(coa_id).split('#')[-1] if '#' in str(coa_id) else str(coa_id)
                if hasattr(self.core.ontology_manager, '_make_uri_safe'):
                    coa_id_safe = self.core.ontology_manager._make_uri_safe(coa_id_safe)
                else:
                    import re
                    coa_id_safe = re.sub(r'\s+', '_', coa_id_safe.strip())
                    coa_id_safe = re.sub(r'[(){}\[\]<>|\\^`"\':;,?#%&+=]', '', coa_id_safe)
                if not coa_id_safe.startswith("COA_Library_"):
                    coa_uri = f"http://coa-agent-platform.org/ontology#COA_Library_{coa_id_safe}"
                else:
                    coa_uri = f"http://coa-agent-platform.org/ontology#{coa_id_safe}"
                
                # 상황 ID URI
                situation_id_raw = situation_info.get('위협ID', situation_info.get('ID', 'THREAT001'))
                has_make_uri = hasattr(self.core.ontology_manager, '_make_uri_safe')
                if has_make_uri:
                    sit_safe = self.core.ontology_manager._make_uri_safe(f"위협상황_{situation_id_raw}")
                else:
                    sit_safe = f"위협상황_{situation_id_raw}" # Fallback
                situation_uri = f"http://coa-agent-platform.org/ontology#{sit_safe}"
                
                safe_print(f"[DEBUG] _score_with_palantir_mode: Generated URIs - Threat: {situation_uri}, COA: {coa_uri}")
            else:
                coa_uri = coa_id
                situation_uri = situation_id_raw
                
            # 컨텍스트 재구성
            context = {
                "threat_level": self._extract_threat_level(situation_info),
                "defense_assets": situation_info.get('가용장비', []),
                "rag_results": situation_analysis.get("rag_results", []),
                "coa_uri": coa_uri,
                "coa_id": coa_id,
                "situation_id": situation_uri,
                "situation_id_raw": situation_id_raw,
                "ontology_manager": self.core.ontology_manager,
                "graph": self.core.ontology_manager.graph if self.core.ontology_manager else None,
                "required_resources": strategy.get('required_resources', []),
                "available_resources": situation_info.get('available_resources', []),  # 🔥 FIX: 가용 자원 추가 (assets 점수 계산용)
                "expected_success_rate": strategy.get('expected_success_rate', 0.5),
                "environmental_constraints": strategy.get('environmental_constraints', ''),
                "mission_type": situation_info.get('임무유형') or situation_info.get('임무종류') or situation_info.get('mission_type'),
                "coa_type": coa_type,
                "threat_type": situation_info.get('위협유형') or situation_info.get('threat_type') or situation_info.get('위협유형코드'),
                "coa_suitability": self._safe_float(strategy.get('적합도점수', 1.0)),
                "is_first_coa": (idx == 0)
            }
            
            # [NEW] 환경 정보 주입 (UI 입력 -> Context)
            if 'environment' in situation_info:
                context.update(situation_info['environment'])
            
            # 자원/환경 재추출
            if self.core.ontology_manager and self.core.ontology_manager.graph is not None:
                try:
                    from core_pipeline.reasoning_engine import ReasoningEngine
                    reasoning_engine = ReasoningEngine()
                    context["resource_availability"] = reasoning_engine._extract_resource_availability(context)
                    context["environment_fit"] = reasoning_engine._extract_environment_fit(context)
                    
                    # [NEW] 시각화 데이터 추출 (Visualization Data Retrieval)
                    # OntologyManager에서 주입한 파일럿 데이터(hasPhasingInfo 등)를 가져옴
                    g = self.core.ontology_manager.graph
                    ns = self.core.ontology_manager.ns
                    from rdflib import URIRef
                    
                    # coa_uri가 문자열이면 URIRef로 변환
                    c_uri_obj = URIRef(context['coa_uri'])
                    
                    # 속성 조회 헬퍼
                    def get_lit(prop):
                        val = g.value(c_uri_obj, URIRef(ns[prop]))
                        return str(val) if val else ""

                    # [NEW] URI 기반 속성 조회 (Object Property)
                    def get_uri(prop):
                        val = g.value(c_uri_obj, URIRef(ns[prop]))
                        if val:
                            # Extract local name (e.g. "AXIS01" from "ns:AXIS01")
                            return str(val).split('#')[-1].split('/')[-1].replace('ns:', '')
                        return None

                    # 축선 정보 조회 (여러 프로퍼티 시도)
                    main_axis = get_uri("hasMainAxis") or get_uri("has전장축선") or get_uri("hasAxis")
                    if not main_axis:
                        # Fallback 1: 위협 상황의 관련 축선 사용
                        main_axis = situation_info.get("관련축선ID") or situation_info.get("related_axis_id")
                        if main_axis:
                            # URI 형태인 경우 ID만 추출
                            if isinstance(main_axis, str) and '#' in main_axis:
                                main_axis = main_axis.split('#')[-1].split('/')[-1].replace('ns:', '')
                            # safe_print(f"[INFO] COA {coa_id} has no explicit axis. Using threat's axis: {main_axis}")
                    
                    # [FIX] Fallback 2: COA 타입/이름 기반 기본 축선 추정
                    if not main_axis:
                        coa_name_lower = (strategy.get("coa_name") or strategy.get("name") or "").lower()
                        # 방책 이름이나 타입에서 축선 정보 추출 시도
                        # 예: "서부", "동부", "중부" 등의 키워드로 기본 축선 추정
                        if "서부" in coa_name_lower or "west" in coa_name_lower:
                            main_axis = "AXIS01"  # 서부 축선 (기본값)
                        elif "동부" in coa_name_lower or "east" in coa_name_lower:
                            main_axis = "AXIS03"  # 동부 축선 (기본값)
                        elif "중부" in coa_name_lower or "center" in coa_name_lower:
                            main_axis = "AXIS02"  # 중부 축선 (기본값)
                        else:
                            # 최종 fallback: 첫 번째 사용 가능한 축선 (데이터에서)
                            try:
                                axis_df = self.core.data_manager.load_table("전장축선")
                                if axis_df is not None and len(axis_df) > 0:
                                    main_axis = str(axis_df.iloc[0].get("축선ID", ""))
                            except:
                                pass

                    vis_data = {
                        "main_effort": get_lit("hasMainEffort"),
                        "phasing": get_lit("hasPhasingInfo"),
                        "action_type": get_lit("hasActionType"),
                        "main_axis_id": main_axis,
                        "graphics": get_lit("hasTacticalGraphics"),
                        "expected_effect": get_lit("hasExpectedEffect")
                    }
                    strategy['visualization_data'] = vis_data
                    # safe_print(f"[DEBUG] 시각화 데이터 추출 ({coa_id}): main_axis={vis_data['main_axis_id']}, phasing={vis_data['phasing']}")

                except Exception as e:
                    safe_print(f"[WARN] 시각화 데이터/자원 추출 실패: {e}")
                    context["resource_availability"] = 0.5
                    context["environment_fit"] = 0.5
                    # [FIX] 예외 발생 시에도 최소한의 시각화 데이터 보장
                    fallback_axis = situation_info.get("관련축선ID") or situation_info.get("related_axis_id")
                    if not fallback_axis:
                        # COA 이름 기반 추정
                        coa_name_lower = (strategy.get("coa_name") or strategy.get("name") or "").lower()
                        if "서부" in coa_name_lower or "west" in coa_name_lower:
                            fallback_axis = "AXIS01"
                        elif "동부" in coa_name_lower or "east" in coa_name_lower:
                            fallback_axis = "AXIS03"
                        elif "중부" in coa_name_lower or "center" in coa_name_lower:
                            fallback_axis = "AXIS02"
                    strategy['visualization_data'] = {
                        "main_axis_id": fallback_axis
                    }
            else:
                context["resource_availability"] = 0.5
                context["environment_fit"] = 0.5
                strategy['visualization_data'] = {
                    "main_axis_id": situation_info.get("관련축선ID") or situation_info.get("related_axis_id")
                }
            
            # 🔥 Pass 2 핵심: 실제 체인 정보 계산
            safe_print(f"[INFO] Pass 2: {coa_id}에 대한 정밀 체인 탐색 수행...")
            if self.core.ontology_manager and self.core.ontology_manager.graph is not None:
                try:
                    chain_info = self._calculate_chain_info(
                        strategy,
                        situation_info,
                        target_coa_uri=context.get('coa_uri')
                    )
                    context["chain_info"] = chain_info
                    
                    # [NEW] Reasoning Trace 추출 (UI 시각화용)
                    # chain_info['chains']의 첫 번째 체인을 사용하여 추출
                    if chain_info and 'chains' in chain_info and chain_info['chains']:
                        raw_chains = chain_info['chains']
                        # 가장 짧고 명확한 체인 선택 (가중치: 길이 짧음 > 점수 높음)
                        best_chain = raw_chains[0] # 이미 정렬되어 있다고 가정
                        
                        trace = []
                        # 체인 구조: [노드1, 관계1, 노드2, 관계2, 노드3 ...] (트리플 리스트 형태일 수 있음)
                        # relationship_chain.py의 반환 구조에 따름 -> PathInfo 객체 또는 리스트
                        
                        # PathInfo 객체인 경우 (속성 접근)
                        if hasattr(best_chain, 'triples'):
                             for s, p, o in best_chain.triples:
                                 trace.append({
                                     "from": str(s).split('#')[-1].split('/')[-1],
                                     "to": str(o).split('#')[-1].split('/')[-1],
                                     "type": str(p).split('#')[-1].split('/')[-1]
                                 })
                        # 리스트인 경우 (튜플 리스트)    
                        elif isinstance(best_chain, list):
                             for triple in best_chain:
                                 if len(triple) >= 3:
                                     trace.append({
                                         "from": str(triple[0]).split('#')[-1].split('/')[-1],
                                         "to": str(triple[2]).split('#')[-1].split('/')[-1],
                                         "type": str(triple[1]).split('#')[-1].split('/')[-1]
                                     })
                        elif isinstance(best_chain, dict) and 'path' in best_chain and 'predicates' in best_chain:
                             path = best_chain['path']
                             preds = best_chain['predicates']
                             # path: [e1, e2, e3], preds: [p1, p2] -> triples: (e1, p1, e2), (e2, p2, e3)
                             for i in range(len(preds)):
                                 if i + 1 < len(path):
                                     trace.append({
                                         "from": str(path[i]).split('#')[-1].split('/')[-1],
                                         "to": str(path[i+1]).split('#')[-1].split('/')[-1],
                                         "type": str(preds[i]).split('#')[-1].split('/')[-1]
                                     })
                        
                        strategy['reasoning_trace'] = trace
                        strategy['chain_info_details'] = chain_info # [NEW] 상세 체인 정보 저장
                        safe_print(f"[DEBUG] Reasoning Trace 추출 완료: {len(trace)} steps (COA: {coa_id})")
                    else:
                        safe_print(f"[DEBUG] Reasoning Trace 추출 실패: chain_info에 유효한 체인이 없음 (COA: {coa_id})")
                    
                    # [FALLBACK CHECK]
                    if not strategy.get('reasoning_trace'):
                         # 체인이 없거나(if 실패) 예외가 발생했던 경우 합성 Trace 생성
                         safe_print(f"[INFO] 체인 미발견/오류. Synthetic Trace 생성.")
                         t_name = strategy.get('threat_type') or situation_info.get('위협유형') or "Unknown Threat"
                         c_name = strategy.get('coa_name') or coa_id
                         
                         strategy['reasoning_trace'] = [
                             {
                                 "from": t_name,
                                 "to": "작전 지역",
                                 "type": "threatens"
                             },
                             {
                                 "from": "작전 지역", 
                                 "to": c_name,
                                 "type": "defendedBy"
                             }
                         ]

                except Exception as e:
                    safe_print(f"[WARN] 체인 정보 계산 실패 (Pass 2): {e}")
                    context["chain_info"] = {}
                    # 예외 발생 시에도 Fallback 적용을 위해 위 로직과 동일하게 처리
                    t_name = strategy.get('threat_type') or situation_info.get('위협유형') or "Unknown Threat"
                    c_name = strategy.get('coa_name') or coa_id
                    strategy['reasoning_trace'] = [
                         {
                             "from": t_name,
                             "to": "작전 지역",
                             "type": "threatens"
                         },
                         {
                             "from": "작전 지역", 
                             "to": c_name,
                             "type": "defendedBy"
                         }
                    ]
            
            # 점수 재계산 (METT-C 평가 포함)
            # METT-C 평가기 초기화
            mett_c_evaluator = None
            try:
                from core_pipeline.mett_c_evaluator import METTCEvaluator
                mett_c_evaluator = METTCEvaluator()
            except ImportError:
                safe_print("[WARN] METTCEvaluator를 임포트할 수 없습니다. 기본 평가만 수행합니다.")
            
            # METT-C 컨텍스트 정보 추가
            if mett_c_evaluator:
                # 영향 범위 지형셀 추정
                impact_cells = self._get_impact_terrain_cells(strategy, situation_info, local_axis_states)
                context['impact_terrain_cells'] = impact_cells
                
                # 민간인 지역 정보 추가
                civilian_areas = self._get_civilian_areas_in_impact_zone(impact_cells)
                context['civilian_areas'] = civilian_areas
                
                # 시간 정보 추가
                estimated_duration = self._estimate_coa_duration(strategy, local_axis_states)
                context['estimated_duration_hours'] = estimated_duration
                
                # Mission, Enemy, Terrain, Troops 정보 추가 (axis_states에서)
                if local_axis_states:
                    # Mission 정보 (situation_info에서 추출)
                    mission_id = situation_info.get('관련임무ID', situation_info.get('related_mission_id'))
                    if mission_id and hasattr(self.core, 'data_manager'):
                        try:
                            from core_pipeline.data_models import Mission
                            df_mission = self.core.data_manager.load_table("임무정보")
                            if df_mission is not None and not df_mission.empty:
                                mission_row = df_mission[df_mission['임무ID'] == mission_id]
                                if not mission_row.empty:
                                    context['mission'] = Mission.from_row(mission_row.iloc[0].to_dict())
                        except:
                            pass
                    
                    # Enemy, Terrain, Troops 정보는 axis_states에 포함됨
                    context['axis_states'] = local_axis_states
                    context['enemy_units'] = [u for state in local_axis_states for u in state.enemy_units]
                    context['terrain_cells'] = [t for state in local_axis_states for t in state.terrain_cells]
                    context['friendly_units'] = [u for state in local_axis_states for u in state.friendly_units]
                    context['constraints'] = [c for state in local_axis_states for c in state.constraints]
            
            # METT-C 평가 포함 점수 계산
            if mett_c_evaluator:
                score_result = scorer.calculate_score_with_mett_c(context, mett_c_evaluator=mett_c_evaluator)
                
                # METT-C 필터: 민간인 보호 점수가 너무 낮으면 제외
                mett_c_score = score_result.get('mett_c', {})
                civilian_score = mett_c_score.get('civilian', 1.0)
                if civilian_score < 0.3:
                    safe_print(f"[INFO] COA {coa_id} 제외: 민간인 보호 점수 낮음 ({civilian_score:.2f})")
                    return idx, context.get("chain_info", {})  # 점수 계산 스킵
                
                # METT-C 필터: 시간 제약 위반 시 제외
                time_score = mett_c_score.get('time', 1.0)
                if time_score == 0.0:
                    safe_print(f"[INFO] COA {coa_id} 제외: 시간 제약 위반")
                    return idx, context.get("chain_info", {})  # 점수 계산 스킵
            else:
                score_result = scorer.calculate_score(context)
            
            # 후처리 로직
            calculated_threat_score = score_result['breakdown'].get('threat', 0.0)
            threat_level = context['threat_level']
            if threat_level and calculated_threat_score < threat_level - 0.05:
                 threat_bonus = (threat_level - calculated_threat_score) * 0.5
                 score_result['total'] = min(1.0, score_result['total'] + threat_bonus)
                 score_result['breakdown']['threat'] = threat_level
            
            # 보너스/페널티 로직
            coa_name = str(strategy.get('명칭') or strategy.get('방책명') or strategy.get('name') or '').lower()
            combined_name = f"{coa_name} {coa_id}"
            
            if threat_level >= 0.95:
                if ('main' in combined_name or '주요' in combined_name or '강력' in combined_name):
                    score_result['total'] = min(1.0, score_result['total'] + 0.3)
                elif 'minimal' in combined_name or '최소' in combined_name:
                    score_result['total'] = max(0.0, score_result['total'] - 0.25)
            elif threat_level > 0.8:
                if ('main' in combined_name or '주요' in combined_name or '강력' in combined_name):
                    bonus = min(0.2, (threat_level - 0.8) * 1.33)
                    score_result['total'] = min(1.0, score_result['total'] + bonus)
            
            # 결과 저장
            strategy['최종점수'] = score_result['total']
            strategy['MAUT점수'] = score_result['total']
            # 🔥 FIX: Pass 2 breakdown으로 업데이트 (상위 5개만)
            pass2_breakdown = score_result.get('breakdown', {})
            if pass2_breakdown:
                strategy['score_breakdown'] = pass2_breakdown.copy()
                # 디버깅: Pass 2 breakdown 로그
                safe_print(f"[DEBUG] Pass 2: COA {coa_id} breakdown 업데이트 = {pass2_breakdown}")
            if 'reasoning' in score_result: strategy['score_breakdown']['reasoning'] = score_result['reasoning']
            if 'confidence' in score_result: strategy['confidence'] = score_result['confidence']
            if 'confidence' in score_result: strategy['confidence'] = score_result['confidence']
            
            # [REMOVED] 제너릭한 추천사유 설정을 제거하여 _generate_recommendation_reason에서 생성하도록 유도
            # strategy['추천사유'] = f"'{coa_name}' 방책은 위협수준 {int(threat_level*100)}% 상황에서 가장 효과적인 대응책입니다. (종합 점수: {score_result['total']:.2f})"
            
            safe_print(f"[INFO] Pass 2 완료: {coa_id} 점수 갱신 -> {score_result['total']:.4f}")
            return idx, context.get("chain_info", {})

        # Pass 2: 정밀 점수 계산 (상위 5개 대상 - 병렬 처리 복구)
        with ThreadPoolExecutor(max_workers=min(len(top_k_for_pass2), 5)) as executor:
            future_to_idx = {executor.submit(_process_strategy_pass2, (i, s)): i for i, s in enumerate(top_k_for_pass2)}
            for future in as_completed(future_to_idx):
                idx, chain_info = future.result()
                if idx == 0 and chain_info:
                    situation_analysis["chain_info"] = chain_info
        
        # top_k가 아닌 나머지는 pass1 점수 그대로 유지 (이미 sorted_strategies에 있음)

        # [FINAL FALLBACK] 모든 전략에 대해 Reasoning Trace 존재 여부 확인 및 보강
        # Pass 2가 실행되지 않았거나 오류가 발생한 경우를 대비
        for strategy in strategies:
            if not strategy.get('reasoning_trace'):
                t_name = strategy.get('threat_type') or situation_info.get('위협유형') or "Unknown Threat"
                # [FIX] COA Name 대신 실제 부대명 사용 (좌표 매핑을 위해)
                target_unit = "Unknown Unit"
                
                # 1. Participating Units에서 추출
                p_units = strategy.get('participating_units', [])
                if isinstance(p_units, str):
                    p_units = [u.strip() for u in p_units.split(',') if u.strip()]
                
                if p_units and len(p_units) > 0:
                    first_unit = p_units[0]
                    if isinstance(first_unit, dict):
                        target_unit = first_unit.get('name', 'Unknown Unit')
                    else:
                        target_unit = str(first_unit)
                else:
                    # 2. COA 유형에 따른 기본 부대 할당
                    c_type = str(strategy.get('coa_type') or "").lower()
                    if "air" in c_type or "strike" in c_type or "공중" in c_type:
                        target_unit = "제18전투비행단" if "east" in c_name.lower() or "강릉" in c_name else "제20전투비행단"
                    elif "missile" in c_type or "유도탄" in c_type:
                        target_unit = "유도탄사령부"
                    else:
                        target_unit = "제1기계화보병사단"

                strategy['reasoning_trace'] = [
                    {
                        "from": t_name,
                        "to": "작전 지역",
                        "type": "threatens"
                    },
                    {
                        "from": "작전 지역", 
                        "to": target_unit,
                        "type": "defendedBy"
                    }
                ]

        # 최종 재정렬 (동점 시 ID 기준 정렬로 일관성 유지)
        # 🔥 CRITICAL FIX: 타입 안전성 강화
        strategies.sort(
            key=lambda x: (
                self._safe_float(x.get('최종점수')), 
                self._safe_str(x.get('COA_ID') or x.get('방책ID') or x.get('ID', ''))
            ), 
            reverse=True
        )
        return strategies
    
    def _calculate_chain_info(self, strategy: Dict, situation_info: Dict, target_coa_uri: Optional[str] = None) -> Dict:
        """체인 정보 계산 (개선 버전)"""
        # 🔥 Cache Key 생성 & 조회
        sit_id = situation_info.get('위협ID', situation_info.get('ID', 'UNKNOWN'))
        coa_id_key = target_coa_uri if target_coa_uri else str(strategy.get('COA_ID', strategy.get('방책ID', 'UNKNOWN')))
        cache_key = f"{sit_id}_{coa_id_key}"
        
        safe_print(f"[DEBUG] _calculate_chain_info: Start - ThreatID: {sit_id}, COA URI: {target_coa_uri}")
        
        if cache_key in self._chain_cache:
            # safe_print(f"[INFO] 체인 정보 캐시 적중: {cache_key}")
            return self._chain_cache[cache_key]
            
        if self.core.ontology_manager.graph is None:
            safe_print("[WARN] 온톨로지 그래프가 없어 체인 정보 계산을 건너뜁니다.")
            return {}
        
        try:
            graph = self.core.ontology_manager.graph
            from rdflib import URIRef, RDFS, RDF
            ns = self.core.ontology_manager.ns  # 통일된 네임스페이스 사용
            ns_legacy = self.core.ontology_manager.ns_legacy  # 기존 데이터 호환용
            
            # 이미 찾은 situation_uri가 있으면 우선 사용
            threat_uri = None
            situation_uri = situation_info.get('situation_uri') or situation_info.get('situation_id')
            
            # 1. 이미 찾은 URI 사용 (URI 형식인 경우)
            if situation_uri and isinstance(situation_uri, str) and situation_uri.startswith("http://"):
                try:
                    candidate_uri = URIRef(situation_uri)
                    if (candidate_uri, None, None) in graph:
                        threat_uri = candidate_uri
                        safe_print(f"[INFO] 위협 URI 찾음 (이미 찾은 URI 사용): {threat_uri}")
                except:
                    pass
            
            # 2. 위협ID로 직접 찾기 (여러 형식 및 대소문자 시도)
            if not threat_uri:
                situation_id = situation_info.get('위협ID', situation_info.get('ID', situation_info.get('situation_id', '')))
                if situation_id:
                    # URI 안전한 ID로 변환
                    safe_situation_id = self.core.ontology_manager._make_uri_safe(situation_id)
                    
                    # 검색할 ID 후보군 (원본, 대문자)
                    id_candidates = [safe_situation_id]
                    if safe_situation_id.upper() != safe_situation_id:
                        id_candidates.append(safe_situation_id.upper())
                    
                    for candidate_id in id_candidates:
                        for uri_format in [
                            f"{ns}위협상황_{candidate_id}",  # 새로운 네임스페이스 우선
                            f"{ns}{candidate_id}",
                            f"{ns_legacy}위협상황_{candidate_id}",  # 기존 네임스페이스 호환
                            f"{ns_legacy}{candidate_id}",
                            f"{ns}THREAT{candidate_id}",
                        ]:
                            try:
                                candidate_uri = URIRef(uri_format)
                                if (candidate_uri, None, None) in graph:
                                    threat_uri = candidate_uri
                                    safe_print(f"[INFO] 위협 URI 찾음: {threat_uri}")
                                    break
                            except:
                                continue
                        if threat_uri:
                            break
            
            # 3. 위협상황 타입으로 찾기 (두 네임스페이스 모두 시도)
            # 주의: 정확한 위협을 찾지 못했을 때 임의의 위협을 사용하는 것은 오해를 불러일으킬 수 있음
            if not threat_uri:
                # 위협유형이 일치하는 위협상황 찾기 시도
                threat_type = situation_info.get('위협유형') or situation_info.get('threat_type')
                if threat_type:
                    for s, p, o in graph.triples((None, None, None)):
                        if threat_type in str(o):
                            # 위협상황 타입인지 확인
                            is_threat_situation = False
                            for type_uri in [ns.위협상황, ns_legacy.위협상황]:
                                if (s, RDF.type, type_uri) in graph:
                                    is_threat_situation = True
                                    break
                            
                            if is_threat_situation:
                                threat_uri = s
                                safe_print(f"[INFO] 위협유형({threat_type}) 일치 위협상황 사용: {threat_uri}")
                                break
            
            if not threat_uri:
                # 🔥 로그 최적화: 첫 번째 COA에서만 경고 출력 (반복 방지)
                if not hasattr(self, '_threat_entity_warning_logged'):
                    safe_print(f"[WARN] 위협 엔티티를 찾을 수 없습니다. situation_id={situation_info.get('위협ID')} (이 경고는 첫 번째 COA에서만 표시됩니다)", logger_name="DefenseCOAAgent")
                    self._threat_entity_warning_logged = True
                # 빈 체인 정보 반환 (체인 정보가 없다는 것을 명시)
                return {
                    "chains": [],
                    "summary": {
                        "total_chains": 0,
                        "avg_score": 0.0,
                        "avg_depth": 0
                    },
                    "error": "위협 엔티티를 찾을 수 없음"
                }
            
            # 2. Path Finding with retries (Depth 3 -> 5)
            # Find specific path to the target COA
            chains = self.core.relationship_chain.find_path(
                    graph,
                    str(threat_uri),
                    str(target_coa_uri),
                    max_depth=4
                )
            
            # if not chains:
            #     safe_print(f"[INFO] Depth 3에서 체인 미발견, Depth 5로 확장 탐색 시도...")
            #     chains = self.core.relationship_chain.find_path(
            #         graph,
            #         str(threat_uri),
            #         str(target_coa_uri),
            #         max_depth=5
            #     )

            # 3. 공통 컨텍스트 탐색 (Common Node Search) - 여전히 체인이 없는 경우
            if not chains:
                safe_print(f"[INFO] 직접 경로 미발견, 공통 컨텍스트(Common Node) 탐색 시도...")
                chains = self.core.relationship_chain.find_common_node_chains(
                    graph,
                    str(threat_uri),
                    str(target_coa_uri)
                )
            
            safe_print(f"[INFO] 체인 탐색 결과: {len(chains)}개 체인 발견 (Target: {target_coa_uri})")
            
            # 결과 구성 및 캐싱
            if chains:
                chain_summary = self.core.relationship_chain.get_chain_summary(chains)
                result = {
                    "chains": chains[:5],
                    "summary": chain_summary
                }
            else:
                # 체인이 없어도 빈 정보 반환
                safe_print(f"[INFO] COA 체인을 찾을 수 없습니다. (Threat: {threat_uri} -> COA: {target_coa_uri})")
                result = {
                    "chains": [],
                    "summary": {
                        "total_chains": 0,
                        "avg_score": 0.0,
                        "avg_depth": 0
                    },
                    "info": "COA 체인 미발견 (직접적인 연결 없음)"
                }
            
            # 🔥 NEW: 결과 캐싱
            self._chain_cache[cache_key] = result
            return result
        except Exception as e:
            safe_print(f"[WARN] 체인 정보 계산 오류: {e}")
            import traceback
            traceback.print_exc()
            return {
                "chains": [],
                "summary": {
                    "total_chains": 0,
                    "avg_score": 0.0,
                    "avg_depth": 0
                },
                "error": str(e)
            }
    
    def _detect_situation_change(self, situation_id: str, situation_info: Dict) -> Tuple[bool, Dict]:
        """
        상황 변화 감지
        
        Args:
            situation_id: 상황 ID
            situation_info: 현재 상황 정보
            
        Returns:
            (변화 감지 여부, 변화 정보)
        """
        try:
            # 히스토리에서 이전 상황 찾기
            previous = self._get_previous_recommendation(situation_id)
            
            if not previous:
                return False, {}
            
            # 이전 상황 정보 가져오기
            previous_result = previous.get("result", {})
            previous_info = previous_result.get("situation_info", {})
            
            if not previous_info:
                return False, {}
            
            # 변화 감지 로직
            changes = {}
            
            # 심각도 변화 확인
            current_severity = situation_info.get("심각도")
            previous_severity = previous_info.get("심각도")
            
            if current_severity is not None and previous_severity is not None:
                try:
                    current_sev = float(current_severity)
                    previous_sev = float(previous_severity)
                    severity_change = abs(current_sev - previous_sev)
                    
                    if severity_change > 0.1:  # 10% 이상 변화
                        changes["심각도"] = {
                            "이전": previous_sev,
                            "현재": current_sev,
                            "변화량": severity_change
                        }
                except (ValueError, TypeError):
                    pass
            
            # 위협유형 변화 확인
            current_threat_type = situation_info.get("위협유형")
            previous_threat_type = previous_info.get("위협유형")
            
            if current_threat_type and previous_threat_type:
                if current_threat_type != previous_threat_type:
                    changes["위협유형"] = {
                        "이전": previous_threat_type,
                        "현재": current_threat_type
                    }
            
            # 발생장소 변화 확인
            current_location = situation_info.get("발생장소")
            previous_location = previous_info.get("발생장소")
            
            if current_location and previous_location:
                if current_location != previous_location:
                    changes["발생장소"] = {
                        "이전": previous_location,
                        "현재": current_location
                    }
            
            # 위협ID 변화 확인 (새로운 위협인 경우)
            current_threat_id = situation_info.get("위협ID")
            previous_threat_id = previous_info.get("위협ID")
            
            if current_threat_id and previous_threat_id:
                if current_threat_id != previous_threat_id:
                    changes["위협ID"] = {
                        "이전": previous_threat_id,
                        "현재": current_threat_id
                    }
            
            return len(changes) > 0, changes
            
        except Exception as e:
            safe_print(f"[WARN] 상황 변화 감지 오류: {e}")
            return False, {}
    
    def _get_previous_recommendation(self, situation_id: str) -> Optional[Dict]:
        """
        이전 추천 가져오기
        
        Args:
            situation_id: 상황 ID
            
        Returns:
            이전 추천 딕셔너리 또는 None
        """
        try:
            if not hasattr(self, 'recommendation_history') or not self.recommendation_history:
                return None
            
            # 최신부터 역순으로 검색
            for entry in reversed(self.recommendation_history):
                entry_situation_id = entry.get("situation_id")
                if entry_situation_id == situation_id:
                    return entry
            
            return None
            
        except Exception as e:
            safe_print(f"[WARN] 이전 추천 조회 오류: {e}")
            return None
    
    def _compare_recommendations(self, previous: Dict, current: Dict) -> Dict:
        """
        추천 비교
        
        Args:
            previous: 이전 추천 딕셔너리
            current: 현재 추천 딕셔너리
            
        Returns:
            비교 결과 딕셔너리
        """
        try:
            if not previous:
                return {
                    "status": "새로운 추천",
                    "이전_추천_수": 0,
                    "현재_추천_수": len(current.get("recommendations", []))
                }
            
            previous_result = previous.get("result", {})
            prev_recs = previous_result.get("recommendations", [])
            curr_recs = current.get("recommendations", [])
            
            comparison = {
                "status": "변화 감지",
                "이전_추천_수": len(prev_recs),
                "현재_추천_수": len(curr_recs),
                "변화": []
            }
            
            # 상위 추천 비교
            if prev_recs and curr_recs:
                prev_top = prev_recs[0]
                curr_top = curr_recs[0]
                
                prev_name = prev_top.get("coa_name", "Unknown")
                curr_name = curr_top.get("coa_name", "Unknown")
                prev_score = prev_top.get("score", 0.0)
                curr_score = curr_top.get("score", 0.0)
                
                if prev_name != curr_name:
                    comparison["변화"].append({
                        "항목": "1위 방책 변경",
                        "이전_1위": prev_name,
                        "현재_1위": curr_name,
                        "이전_점수": prev_score,
                        "현재_점수": curr_score
                    })
                
                # 점수 변화 확인
                score_change = abs(curr_score - prev_score)
                if score_change > 0.05:  # 5% 이상 변화
                    comparison["변화"].append({
                        "항목": "1위 점수 변화",
                        "이전_점수": prev_score,
                        "현재_점수": curr_score,
                        "변화량": score_change
                    })
            
            # 추천 개수 변화
            if len(prev_recs) != len(curr_recs):
                comparison["변화"].append({
                    "항목": "추천 개수 변화",
                    "이전": len(prev_recs),
                    "현재": len(curr_recs)
                })
            
            # 순위 변화 확인 (상위 3개)
            if len(prev_recs) >= 3 and len(curr_recs) >= 3:
                prev_names = [r.get("coa_name", "") for r in prev_recs[:3]]
                curr_names = [r.get("coa_name", "") for r in curr_recs[:3]]
                
                if prev_names != curr_names:
                    comparison["변화"].append({
                        "항목": "상위 3개 순위 변화",
                        "이전": prev_names,
                        "현재": curr_names
                    })
            
            if not comparison["변화"]:
                comparison["status"] = "변화 없음"
            
            return comparison
            
        except Exception as e:
            safe_print(f"[WARN] 추천 비교 오류: {e}")
            return {
                "status": "비교 실패",
                "error": str(e)
            }
    
    def _save_to_history(self, situation_id: str, result: Dict):
        """
        히스토리에 저장
        
        Args:
            situation_id: 상황 ID
            result: 추천 결과 딕셔너리
        """
        try:
            if not hasattr(self, 'recommendation_history'):
                self.recommendation_history = []
            
            entry = {
                "situation_id": situation_id,
                "timestamp": pd.Timestamp.now().isoformat(),
                "result": result.copy()  # 복사본 저장
            }
            
            self.recommendation_history.append(entry)
            
            # 최대 100개만 유지 (메모리 관리)
            if len(self.recommendation_history) > 100:
                self.recommendation_history = self.recommendation_history[-100:]
                safe_print(f"[INFO] 히스토리 최대 개수 도달. 오래된 항목 제거됨.")
            
        except Exception as e:
            safe_print(f"[WARN] 히스토리 저장 오류: {e}")
    
    def _format_situation_for_llm(self, situation_info: Dict, 
                                  selected_situation_info: Optional[Dict] = None) -> str:
        """
        상황 정보를 LLM이 이해하기 쉬운 텍스트로 변환
        
        Args:
            situation_info: 상황 정보 딕셔너리
            selected_situation_info: 선택된 상황 정보 (추가 컨텍스트용)
            
        Returns:
            LLM이 이해할 수 있는 텍스트 형식의 상황 설명
        """
        parts = []
        
        # 위협 정보
        threat_type = situation_info.get('위협유형') or situation_info.get('threat_type', 'N/A')
        threat_level = self._extract_threat_level(situation_info)
        
        parts.append(f"위협 유형: {threat_type}")
        parts.append(f"위협 수준: {threat_level:.2f} ({int(threat_level*100)}%)")
        
        # 위치 정보
        location = situation_info.get('발생장소') or situation_info.get('장소', 'N/A')
        if location and location != 'N/A':
            parts.append(f"발생 장소: {location}")
        
        # 축선 정보
        axis_id = situation_info.get('관련축선ID') or situation_info.get('주요축선ID', 'N/A')
        if axis_id and axis_id != 'N/A':
            parts.append(f"관련 축선: {axis_id}")
        
        # 임무 정보 (임무 중심인 경우)
        mission_id = situation_info.get('임무ID') or situation_info.get('mission_id')
        mission_name = situation_info.get('임무명') or situation_info.get('mission_name')
        if mission_id:
            parts.append(f"임무 ID: {mission_id}")
        if mission_name:
            parts.append(f"임무명: {mission_name}")
        
        # 추가 컨텍스트
        if selected_situation_info:
            additional = selected_situation_info.get('additional_context', '')
            if additional:
                parts.append(f"추가 정보: {additional}")
        
        return "\n".join(parts)
    
    def _llm_analyze_situation(self, situation_info: Dict, 
                              user_query: str,
                              selected_situation_info: Optional[Dict] = None) -> Dict:
        """
        LLM이 상황을 분석 (의미 분석 및 컨텍스트 이해)
        
        Args:
            situation_info: 상황 정보 딕셔너리
            user_query: 사용자 질문
            selected_situation_info: 선택된 상황 정보 (추가 컨텍스트용)
            
        Returns:
            {
                "insights": {
                    "key_factors": [...],
                    "constraints": [...],
                    "recommended_approach": "..."
                },
                "context": "...",
                "threat_assessment": {
                    "severity": "High/Medium/Low",
                    "urgency": 0.0-1.0
                }
            }
        """
        if not self.core.llm_manager or not self.core.llm_manager.is_available():
            return {"insights": {}, "context": "", "threat_assessment": {}}
        
        # 상황 정보를 텍스트로 변환
        situation_text = self._format_situation_for_llm(situation_info, selected_situation_info)
        
        prompt = f"""다음 상황을 분석하세요:

{situation_text}

사용자 질문: {user_query}

다음을 분석해주세요:
1. 위협의 핵심 특성 및 심각도
2. 상황의 맥락 및 배경
3. 주요 고려사항 및 제약조건
4. 권장 접근 방식

JSON 형식으로 답변:
{{
    "threat_assessment": {{
        "severity": "High/Medium/Low",
        "key_characteristics": ["특성1", "특성2"],
        "urgency": 0.0-1.0
    }},
    "context": "상황의 맥락 설명",
    "insights": {{
        "key_factors": ["요인1", "요인2"],
        "constraints": ["제약1", "제약2"],
        "recommended_approach": "접근 방식 설명"
    }}
}}"""
        
        try:
            response = self.core.llm_manager.generate(prompt, max_tokens=512, temperature=0.0, do_sample=False)
            import json
            # JSON 파싱 시도
            try:
                # JSON 부분만 추출 (응답에 추가 텍스트가 있을 수 있음)
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response[json_start:json_end]
                    llm_result = json.loads(json_text)
                else:
                    raise json.JSONDecodeError("JSON not found", response, 0)
            except json.JSONDecodeError:
                # JSON이 아닌 경우 텍스트에서 추출 시도
                safe_print(f"[WARN] LLM 응답이 JSON 형식이 아닙니다: {response[:100]}")
                # 기본 구조로 반환
                llm_result = {
                    "threat_assessment": {
                        "severity": "Medium",
                        "key_characteristics": [],
                        "urgency": 0.5
                    },
                    "context": response[:200] if len(response) > 200 else response,
                    "insights": {
                        "key_factors": [],
                        "constraints": [],
                        "recommended_approach": ""
                    }
                }
            return llm_result
        except Exception as e:
            safe_print(f"[WARN] LLM 상황 분석 실패: {e}")
            return {"insights": {}, "context": "", "threat_assessment": {}}
    
    def _llm_evaluate_strategies(self, strategies: List[Dict],
                                situation_info: Dict,
                                situation_analysis: Dict = None) -> Dict[int, Dict]:
        """
        LLM이 방책을 평가 (의미 분석 및 적합성 평가)
        
        Args:
            strategies: 방책 리스트
            situation_info: 상황 정보 딕셔너리
            situation_analysis: 상황 분석 결과 (LLM 인사이트 포함)
            
        Returns:
            {0: {"score": 0.8, "reason": "..."}, 1: {...}, ...}
        """
        if not self.core.llm_manager or not self.core.llm_manager.is_available():
            return {}
        
        llm_evaluations = {}
        
        # 상황 정보 요약
        situation_summary = self._format_situation_for_llm(situation_info, situation_analysis)
        
        # LLM 인사이트 추가
        if situation_analysis and situation_analysis.get("llm_insights"):
            insights = situation_analysis["llm_insights"]
            if insights.get('key_factors'):
                situation_summary += f"\n\n주요 고려사항: {', '.join(insights.get('key_factors', []))}"
            if insights.get('constraints'):
                situation_summary += f"\n제약조건: {', '.join(insights.get('constraints', []))}"
        
        # 각 방책을 LLM이 평가 (상위 5개만)
        for i, strategy in enumerate(strategies[:5]):
            coa_name = strategy.get('명칭') or strategy.get('방책명') or strategy.get('name') or 'Unknown'
            coa_description = strategy.get('설명') or strategy.get('방책설명') or ''
            coa_id = strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('ID', '')
            
            prompt = f"""다음 상황과 방책을 평가하세요:

상황:
{situation_summary}

방책:
- ID: {coa_id}
- 이름: {coa_name}
- 설명: {coa_description}

이 방책이 현재 상황에 얼마나 적합한지 평가하세요 (0.0-1.0).
또한 추천 사유를 간단히 설명하세요.

JSON 형식:
{{
    "score": 0.0-1.0,
    "reason": "추천 사유"
}}"""
            
            try:
                response = self.core.llm_manager.generate(prompt, max_tokens=200, temperature=0.0, do_sample=False)
                import json
                try:
                    # JSON 부분만 추출
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_text = response[json_start:json_end]
                        eval_result = json.loads(json_text)
                        
                        # 🔥 CRITICAL FIX: score 필드를 항상 float으로 변환하여 TypeError 방지
                        if 'score' in eval_result:
                            eval_result['score'] = self._safe_float(eval_result['score'], 0.5)
                        
                        llm_evaluations[i] = eval_result
                    else:
                        raise json.JSONDecodeError("JSON not found", response, 0)
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시 기본값
                    safe_print(f"[WARN] LLM 평가 응답 파싱 실패 ({i}): {response[:50]}")
                    llm_evaluations[i] = {"score": 0.5, "reason": "평가 실패"}
            except Exception as e:
                safe_print(f"[WARN] LLM 방책 평가 실패 ({i}): {e}")
                llm_evaluations[i] = {"score": 0.5, "reason": "평가 실패"}
        
        return llm_evaluations
    
    def _get_civilian_areas_in_impact_zone(
        self, 
        impact_cell_ids: List[str],
        data_manager=None
    ) -> List:
        """
        영향 범위 내 민간인 지역 조회 (METT-C의 C 요소)
        
        Args:
            impact_cell_ids: COA 영향 범위 지형셀 ID 리스트
            data_manager: DataManager 인스턴스 (None이면 self.core.data_manager 사용)
        
        Returns:
            CivilianArea 객체 리스트
        """
        try:
            from core_pipeline.data_models import CivilianArea
            
            dm = data_manager or (self.core.data_manager if hasattr(self.core, 'data_manager') else None)
            if not dm:
                return []
            
            df = dm.load_table("민간인지역")
            if df is None or df.empty:
                return []
            
            civilian_areas = []
            for _, row in df.iterrows():
                try:
                    area = CivilianArea.from_row(row.to_dict())
                    if area.location_cell_id in impact_cell_ids:
                        civilian_areas.append(area)
                except Exception as e:
                    safe_print(f"[WARN] 민간인 지역 파싱 실패: {e}")
                    continue
            
            return civilian_areas
        except ImportError:
            safe_print("[WARN] CivilianArea 모델을 임포트할 수 없습니다.")
            return []
        except Exception as e:
            safe_print(f"[WARN] 민간인 지역 조회 실패: {e}")
            return []
    
    def _estimate_coa_duration(self, coa: Dict, axis_states: Optional[List] = None) -> Optional[float]:
        """
        COA 예상 소요 시간 추정 (시간 단위) - METT-C의 C(Time) 요소
        
        Args:
            coa: COA 딕셔너리
            axis_states: 축선별 전장상태 리스트
        
        Returns:
            예상 소요 시간 (시간 단위) 또는 None
        """
        # COA 타입별 기본 소요 시간 (시간)
        default_durations = {
            'defense': 24.0,
            'offensive': 48.0,
            'counter_attack': 36.0,
            'preemptive': 12.0,
            'deterrence': 6.0,
            'maneuver': 18.0,
            'information_ops': 4.0
        }
        
        coa_type = coa.get('coa_type', coa.get('방책유형', 'defense'))
        if isinstance(coa_type, str):
            coa_type = coa_type.lower()
        
        base_duration = default_durations.get(coa_type, 24.0)
        
        # 축선 수에 따라 시간 조정
        axis_count = len(axis_states) if axis_states else 1
        duration = base_duration * (1 + 0.2 * (axis_count - 1))
        
        # COA 설명에서 시간 정보 추출 (있는 경우)
        coa_description = coa.get('설명', coa.get('description', ''))
        if coa_description:
            import re
            # "N시간", "N일" 등의 패턴 찾기
            time_patterns = [
                (r'(\d+)\s*시간', 1.0),  # N시간
                (r'(\d+)\s*일', 24.0),   # N일
                (r'(\d+)\s*h', 1.0),     # Nh
                (r'(\d+)\s*d', 24.0)     # Nd
            ]
            
            for pattern, multiplier in time_patterns:
                match = re.search(pattern, coa_description, re.IGNORECASE)
                if match:
                    hours = float(match.group(1)) * multiplier
                    # 추출된 시간이 합리적 범위 내이면 사용
                    if 1.0 <= hours <= 168.0:  # 1시간 ~ 7일
                        duration = hours
                        break
        
        return duration
    
    def _get_impact_terrain_cells(self, coa: Dict, situation_info: Dict, axis_states: Optional[List] = None) -> List[str]:
        """
        COA의 영향 범위 지형셀 ID 리스트 추정
        
        Args:
            coa: COA 딕셔너리
            situation_info: 상황 정보
            axis_states: 축선별 전장상태 리스트
        
        Returns:
            영향받는 지형셀 ID 리스트
        """
        impact_cells = []
        
        # 1. 위협 위치 기반
        threat_location = situation_info.get('발생위치셀ID', situation_info.get('location_cell_id'))
        if threat_location:
            impact_cells.append(str(threat_location))
        
        # 2. 축선 기반 (정교화: COA에 할당된 주 축선만 고려)
        if axis_states:
            main_axis_id = coa.get('visualization_data', {}).get('main_axis_id')
            for axis_state in axis_states:
                # 할당된 축선만 포함하거나, 축선 정보가 없는 경우에만 폴백으로 전체 포함
                if not main_axis_id or axis_state.axis_id == main_axis_id:
                    for terrain_cell in axis_state.terrain_cells:
                        if terrain_cell.terrain_cell_id:
                            impact_cells.append(terrain_cell.terrain_cell_id)
        
        # 3. COA 설명에서 위치 정보 추출 (있는 경우)
        coa_description = coa.get('설명', coa.get('description', ''))
        if coa_description and hasattr(self.core, 'data_manager'):
            try:
                df_terrain = self.core.data_manager.load_table("지형셀")
                if df_terrain is not None and not df_terrain.empty:
                    for _, row in df_terrain.iterrows():
                        terrain_name = str(row.get('지형명', ''))
                        if terrain_name and terrain_name in coa_description:
                            terrain_id = str(row.get('지형셀ID', ''))
                            if terrain_id and terrain_id not in impact_cells:
                                impact_cells.append(terrain_id)
            except:
                pass
        
        # 중복 제거
        return list(set(impact_cells))

