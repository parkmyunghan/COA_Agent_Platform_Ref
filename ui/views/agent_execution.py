# ui/pages/5_Agent_실행.py
# -*- coding: utf-8 -*-
"""
5단계: Agent 실행 페이지
Agent 선택, 상황 입력, 실행, 결과 확인
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import json
import re
import textwrap
import html

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

from ui.components.agent_selector import render_agent_selector
from ui.components.situation_input import render_situation_input, render_situation_summary, enrich_situation_info_with_ontology
from ui.components.palantir_mode_toggle import render_palantir_mode_toggle, render_palantir_result_info
from ui.components.chat_interface_v2 import render_chat_interface
from ui.components.report_generator import render_report_download_button
from ui.components.reasoning_explanation import render_reasoning_explanation
from ui.components.coa_execution_plan import render_coa_execution_plan
from ui.components.user_friendly_errors import render_user_friendly_error
from ui.components.tactical_map import render_tactical_map
from ui.components.scenario_mapper import ScenarioMapper
from ui.components.ontology_cop_mapper import OntologyCOPMapper
from core_pipeline.orchestrator import Orchestrator
from common.utils import safe_print
import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def translate_to_mission_terms(text):
    """위협 중심 용어를 임무 중심 용어로 변환"""
    if not text:
        return text
    mapping = {
        "위협수준": "임무 성공 가능성",
        "위협 수준": "임무 성공 가능성",
        "위협유형": "임무 유형",
        "위협 유형": "임무 유형",
        "위협원": "대능 부대",
        "식별된 적 부대": "대항군",
        "적 부대": "대항군",
        "관련축선": "주요 작전 축선",
        "정황 보고": "임무 보고",
        "위협": "임무 상황",
        "상황설명": "임무 개요",
        "임무목표": "상세 임무 목표"
    }
    for old, new in mapping.items():
        text = text.replace(old, new)
    return text


st.set_page_config(
    page_title="지휘통제/분석",
    layout="wide"
)

# ... (중략) ...

# 제목 (Compact Style Upgrade)
# 상단 여백 최소화 및 컴팩트 헤더 스타일 적용
st.markdown("""
<style>
    /* 상단 여백 최소화 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0rem !important;
    }
    /* Plan B: 헤더 전체를 숨기지 않고 투명화하여 버튼 기능 복구 */
    header[data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: none !important;  /* Streamlit 기본 구분선 제거 */
    }
    
    /* 데코레이션(줄무늬) 숨김 */
    [data-testid="stDecoration"] {
        display: none;
    }

    /* 사이드바 토글 버튼 강제 노출 */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        color: #e6edf3 !important;
    }
    
    /* 컴팩트 헤더 스타일 */
    .compact-header {
        background-color: #0e1117;
        border-bottom: 1px solid #30363d;
        padding-bottom: 5px;
        margin-bottom: 15px;
        display: flex;
        flex-wrap: wrap;  /* 작은 화면에서 줄바꿈 허용 */
        justify-content: space-between;
        align-items: center;
        width: 100%;  /* 브라우저 너비에 맞춤 */
    }
    .header-title {
        font-family: 'Roboto Mono', monospace; 
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #2E9AFE; /* Distinct Blue Color */
        text-transform: uppercase;
    }
    .header-subtitle {
        font-family: 'Roboto', sans-serif;
        font-size: 0.85rem;
        color: #8b949e;
    }
    
    /* [NEW] 진행 상황 표시 개선 스타일 */
    /* Progress bar 스타일 개선 */
    div[data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #2E9AFE 0%, #00D9FF 100%) !important;
        height: 8px !important;
    }
    
    /* Status 박스 강조 */
    div[data-testid="stStatus"] {
        background-color: rgba(46, 154, 254, 0.05) !important;
        border: 1px solid rgba(46, 154, 254, 0.3) !important;
        border-radius: 8px !important;
    }
    
    /* 진행 중일 때 애니메이션 효과 */
    div[data-testid="stStatus"][data-state="running"] {
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            border-color: rgba(46, 154, 254, 0.3);
        }
        50% {
            border-color: rgba(46, 154, 254, 0.6);
        }
    }
</style>

<div class="compact-header">
    <div class="header-title">
        지휘통제/분석
    </div>
    <div class="header-subtitle">
        Agent 선택, 상황 입력, LLM 질문 및 상호작용, 상세 분석
    </div>
</div>
""", unsafe_allow_html=True)

# 설정 파일 로드
try:
    config = load_yaml("./config/global.yaml")
    registry = load_yaml("./config/agent_registry.yaml")
    agents_list = registry.get("agents", [])
    agents_list = [a for a in agents_list if a.get("enabled", True)]
except Exception as e:
    render_user_friendly_error(e, "설정 파일 로드")
    st.stop()

# Orchestrator 초기화 (Enhanced Ontology Manager 사용)
# 이미 초기화 완료 플래그가 있으면 초기화 로직 건너뛰기
if st.session_state.get("main_orchestrator_initialized", False):
    # 이미 초기화 완료 - 아무 작업도 하지 않음
    pass
elif "main_orchestrator" not in st.session_state:
    # Orchestrator가 없으면 새로 생성 및 초기화
    # 처음 로드 시에만 확장된 상태 상자 표시
    with st.status("시스템 초기화 중...", expanded=True) as status:
        st.write("초기화 프로세스를 시작합니다...")
        
        # 콜백 함수: 상태 상자에 메시지 출력
        def update_status(msg):
            st.write(f"👉 {msg}")
            
        try:
            st.session_state.main_orchestrator = Orchestrator(config, use_enhanced_ontology=True)
            # 진행 콜백 전달
            st.session_state.main_orchestrator.initialize(progress_callback=update_status)
            st.session_state.main_orchestrator_initialized = True
            
            status.update(label="✅ 시스템 초기화 완료 (Enhanced Ontology Manager 활성화)", state="complete", expanded=False)
        except Exception as e:
            st.error(f"시스템 초기화 오류: {e}")
            render_user_friendly_error(e, "시스템 초기화")
            st.stop()
else:
    # Orchestrator는 있지만 초기화 플래그가 없는 경우
    # 실제 초기화 상태 확인 (중복 초기화 방지)
    if hasattr(st.session_state.main_orchestrator, 'core') and \
       hasattr(st.session_state.main_orchestrator.core, '_initialized') and \
       st.session_state.main_orchestrator.core._initialized:
        # 이미 초기화되었으면 플래그만 업데이트 (spinner 없이)
        st.session_state.main_orchestrator_initialized = True
    else:
        # 실제로 초기화가 필요한 경우에만 상태 표시
        # 여기서는 짧게 표시하거나 이미 로드된 것으로 간주
        with st.status("시스템 초기화 확인 중...", expanded=False) as status:
            try:
                def update_status_retry(msg):
                    st.write(f"👉 {msg}")
                    
                st.session_state.main_orchestrator.initialize(progress_callback=update_status_retry)
                st.session_state.main_orchestrator_initialized = True
                status.update(label="✅ 시스템 초기화 완료", state="complete", expanded=False)
            except Exception as e:
                render_user_friendly_error(e, "시스템 초기화")
                st.stop()

orchestrator = st.session_state.main_orchestrator

# 사이드바 설정
with st.sidebar:
    st.header("시스템 설정")
    
    # 팔란티어 모드 토글
    st.subheader("팔란티어 모드")
    
    # 체크박스 값 변경 시 session_state에 저장하는 콜백
    def update_palantir_mode():
        st.session_state["use_palantir_mode"] = st.session_state["agent_page_use_palantir_mode"]
    
    # 기본값을 True로 설정 (팔란티어 모드 활성화)
    default_palantir = st.session_state.get("use_palantir_mode", True)
    
    use_palantir = st.checkbox(
        "팔란티어 모드 활성화",
        value=default_palantir,
        key="agent_page_use_palantir_mode",
        on_change=update_palantir_mode,
        help="다중 요소 기반 종합 점수 계산 (위협, 자원, 자산, 환경, 과거, 체인) + RAG 검색 활용"
    )


    
    # session_state 동기화
    if "use_palantir_mode" not in st.session_state:
        st.session_state["use_palantir_mode"] = use_palantir
    elif st.session_state.get("agent_page_use_palantir_mode") != use_palantir:
        st.session_state["use_palantir_mode"] = use_palantir
    
    # RAG 검색은 항상 활성화 (팔란티어 모드에서 과거 성공률 계산 및 LLM 컨텍스트로 사용)
    st.info("참고: RAG 검색은 항상 활성화됩니다 (과거 사례 활용 및 LLM 컨텍스트 제공)")
    
    st.divider()

    # 방책 유형 선택 (새로 추가)
    st.subheader("방책 유형 필터")
    
    # 기본 방책 유형 목록
    coa_types = [
        "Defense", "Offensive", "Counter_Attack", 
        "Preemptive", "Deterrence", "Maneuver", "Information_Ops"
    ]
    
    # 멀티셀렉트로 선택 (기본값: 모든 유형)
    # 참고: coa_recommendation_agent는 7가지 타입을 모두 지원합니다
    selected_coa_types = st.multiselect(
        "추천받을 방책 유형 선택",
        options=coa_types,
        default=coa_types,
        help="선택한 유형의 방책만 추천 결과에 포함됩니다. coa_recommendation_agent는 7가지 타입(방어/공격/반격/선제/억제/기동/정보작전)을 모두 지원합니다."
    )
    
    # session_state에 저장
    st.session_state["selected_coa_types"] = selected_coa_types
    
    st.divider()
    
    # 파이프라인 상태
    st.subheader("파이프라인 상태")
    llm_manager = orchestrator.core.llm_manager
    selected_model_key = llm_manager.selected_model_key
    
    # 선택된 모델이 없으면 기본값 사용
    if not selected_model_key:
        if llm_manager.openai_available and llm_manager.use_openai:
            selected_model_key = 'openai'
        elif llm_manager.model is not None:
            selected_model_key = 'local'
        else:
            # 사용 가능한 첫 번째 모델 찾기
            available_models = llm_manager.get_available_models()
            for model_key, model_info in available_models.items():
                if model_info.get('available', False):
                    selected_model_key = model_key
                    break
    
    # 선택된 모델에 따라 모델명 표시
    if selected_model_key == 'openai':
        model_name = llm_manager.openai_model if llm_manager.openai_available else "OpenAI (사용 불가)"
        model_status = f"[OK] LLM 모델: {model_name} (OpenAI API)"
    elif selected_model_key == 'local':
        if llm_manager.model is not None:
            model_path = llm_manager.model_path or "로컬 모델"
            if model_path:
                import os
                model_name = os.path.basename(model_path) if model_path else "로컬 모델"
            else:
                model_name = "로컬 모델"
            model_status = f"[OK] LLM 모델: {model_name} (로컬)"
        else:
            model_status = "[WARN] LLM 모델: 로컬 모델 (미로드)"
    elif selected_model_key and selected_model_key.startswith('internal_'):
        # 사내망 모델
        model_key = selected_model_key.replace('internal_', '')
        if model_key in llm_manager.internal_models:
            model_info = llm_manager.internal_models[model_key]
            model_name = model_info.get('name', model_key)
        else:
            model_name = f"사내망 모델 ({model_key})"
        model_status = f"[OK] LLM 모델: {model_name} (사내망)"
    else:
        model_status = "[WARN] LLM 모델 미로드"
    
    # 사용 가능 여부 확인
    available_models = llm_manager.get_available_models()
    is_available = available_models.get(selected_model_key, {}).get('available', False) if selected_model_key else False
    
    if is_available:
        st.success(model_status)
    else:
        st.warning(model_status.replace("[OK]", "[WARN]"))
    
    if orchestrator.core.rag_manager.embedding_model is not None:
        st.success("[OK] 임베딩 모델 로드됨")
    else:
        st.warning("[WARN] 임베딩 모델 미로드")
    
    if orchestrator.core.ontology_manager.graph is not None:
        triples_count = len(list(orchestrator.core.ontology_manager.graph.triples((None, None, None))))
        st.success(f"[OK] RDF 그래프: {triples_count} triples")
    else:
        st.warning("[WARN] RDF 그래프 미생성")

# 분할 레이아웃 설정 전, 전체 너비 상태 표시 영역 확보
status_placeholder = st.empty()

# [UX FIX] 실행 중일 때는 좌측/우측 영역 전체를 어둡게 처리하여 비활성화 상태 표시
is_running = st.session_state.get("run_recommendation_active", False)

# style을 else 블록에서도 초기화하여 '상태 꼬임/Ghosting' 현상 방지
st.markdown(f"""
<style>
    /* 실행 중일 때 메인 UI 요소들을 어둡게 처리 (상호작용 차단) */
    div[data-testid="column"], 
    div[data-testid="stExpander"], 
    div[data-testid="stHorizontalBlock"],
    div.stTextArea,
    div.stButtonBase {{
        opacity: {"0.4" if is_running else "1"} !important;
        filter: {"grayscale(0.8) brightness(0.7)" if is_running else "none"} !important;
        pointer-events: {"none" if is_running else "auto"} !important;
        transition: opacity 0.3s ease, filter 0.3s ease;
    }}
    
    /* 사이드바도 어둡게 처리 */
    section[data-testid="stSidebar"] {{
        filter: {"grayscale(1) brightness(0.6)" if is_running else "none"} !important;
        pointer-events: {"none" if is_running else "auto"} !important;
        transition: filter 0.3s ease;
    }}
    
    /* 단, 진행상황 표시(Status) 컴포넌트는 항상 밝고 최상위에 표시 */
    div[data-testid="stStatus"] {{
        opacity: 1 !important;
        filter: none !important;
        z-index: 99999 !important;
        position: relative !important;
        pointer-events: auto !important;
        border: 1px solid #2E9AFE !important;
        box-shadow: 0 0 15px rgba(46, 154, 254, 0.3) !important;
    }}
    
    /* 실행 중일 때 Status 주변 여백 확보 */
    {"""
    div[data-testid="stStatus"] {
        background: rgba(14, 17, 23, 1) !important;
        margin-bottom: 30px !important;
        padding: 20px !important;
    }
    """ if is_running else ""}
</style>
""", unsafe_allow_html=True)

# 분할 레이아웃 설정
col_left, col_right = st.columns([4, 6])

with col_left:
    # [UX FIX] 실행 중일 때도 좌측 영역은 유지하되 비활성화 상태로 표시 (사용자가 설정 확인 가능)
    st.subheader("💬 작전 지휘 통제")
    
    # Agent 선택
    selected_agent = render_agent_selector(agents_list)
    
    st.divider()
    
    # 상황 정보 입력 및 확인 (Compact Version)
    if selected_agent and ("coa" in selected_agent.lower() and "recommendation" in selected_agent.lower()):
        situation_info = st.session_state.get("selected_situation_info")
        
        # [FIX] 화면 튐(Layout Shift) 방지를 위한 Expander 상태 제어
        is_analyzing = st.session_state.get("coa_progress_data", {}).get("state") == "running"
        should_expand = (not situation_info) or is_analyzing
        
        with st.expander("📋 상황 정보 설정", expanded=should_expand):
            new_situation_info = render_situation_input(orchestrator, use_real_data=True)
        
        # 간략한 상황 요약 표시
        curr_sit = st.session_state.get("selected_situation_info")
        active_sit = new_situation_info if new_situation_info and new_situation_info.get("situation_id") else curr_sit
        
        if active_sit:
            render_situation_summary(active_sit)
            st.markdown('<div id="situation_confirmation_area"></div>', unsafe_allow_html=True)
            
            btn_label = "🎯 방책 추천 실행"
            if curr_sit and active_sit.get("situation_id") != curr_sit.get("situation_id"):
                btn_label = "🔄 변경된 상황으로 방책 추천 실행"
            
            # 버튼 컨테이너만 여기에 유지
            btn_container = st.empty()
            
            # [FIX] 버튼 클릭 시 상태만 변경하고 리런하여 클린 상태에서 실행 (잔상/고스트 방지)
            if not st.session_state.get("run_recommendation_active", False):
                if btn_container.button(btn_label, key="run_recommendation_trigger", type="primary", use_container_width=True):
                    # 1. 실행 플래그 설정
                    st.session_state["run_recommendation_active"] = True
                    # 2. 즉시 저장 (Auto-Save)
                    st.session_state.selected_situation_info = active_sit
                    # 3. 이전 데이터 초기화
                    if "messages_v2" in st.session_state:
                        st.session_state.messages_v2 = [] 
                    # 4. 진행 상태 초기화
                    st.session_state.coa_progress_data = {
                        "label": "방책 분석 시작...",
                        "logs": [],
                        "state": "running",
                        "progress": 0
                    }
                    # 5. 리런
                    st.rerun()

            # [핵심] 리런 후 실행되는 실제 로직 - 위치를 status_placeholder(상단)로 이동
            if st.session_state.get("run_recommendation_active", False):
                # [UX FIX] 화면 포커스 상단 이동 및 기존 화면 완전히 가리기
                import streamlit.components.v1 as components
                # Streamlit iframe 샌드박스 탈출 및 부모 창 스크롤 강제 이동
                # requestAnimationFrame과 setTimeout을 조합하여 렌더링 사이클 직후 실행 보장
                js = """
                <script>
                    (function() {
                        function scrollTop() {
                            try {
                                // 부모 창 스크롤
                                if (window.parent && window.parent.window) {
                                    window.parent.window.scrollTo({ top: 0, behavior: 'smooth' });
                                }
                                // Streamlit 메인 컨테이너 스크롤
                                var main = window.parent.document.querySelector('.main');
                                if (main) { 
                                    main.scrollTo({ top: 0, behavior: 'smooth' }); 
                                }
                                // iframe 자체 스크롤
                                if (window.frameElement) {
                                    window.frameElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                }
                            } catch (e) { 
                                console.log('[Scroll] Error:', e); 
                            }
                        }
                        // 즉시 스크롤 + 지연 스크롤 (다중 안전장치)
                        scrollTop();
                        setTimeout(scrollTop, 50);
                        setTimeout(scrollTop, 100);
                        setTimeout(scrollTop, 300);
                        setTimeout(scrollTop, 500);
                    })();
                </script>
                """
                components.html(js, height=0)
                
                # 버튼 숨기기
                btn_container.empty()
                
                # [UX FIX] 상태창 생성 (전체 너비 플레이스홀더 사용, 최상단에 명확히 표시)
                # 실행 중일 때는 진행상황 바만 표시되도록 CSS 적용
                st.markdown("""
                <style>
                    /* 실행 중일 때 진행상황 바 주변 정리 */
                    div[data-testid="stStatus"] {
                        margin: 20px 0 !important;
                        padding: 20px !important;
                        border-radius: 8px !important;
                        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                with status_placeholder.status("방책을 분석하고 있습니다...", expanded=True) as status:
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    current_step_text = st.empty()
                    
                    # UI 렌더링을 위한 최소한의 양보 (기다림 없이 바로 진행하되 yield 효과)
                    import time
                    time.sleep(0.1) 
                    
                    try:
                        agent_info = next((a for a in agents_list if a.get("name") == selected_agent), None)
                        if agent_info:
                            cls_path = agent_info.get("class")
                            if cls_path:
                                AgentClass = orchestrator.load_agent_class(cls_path)
                                agent = AgentClass(core=orchestrator.core)
                                use_palantir_mode = st.session_state.get("use_palantir_mode", True)
                                
                                def on_status_update(msg, progress=None):
                                    if "coa_progress_data" not in st.session_state:
                                        st.session_state.coa_progress_data = {"label": "방책 분석 중...", "logs": [], "state": "running", "progress": 0}
                                    
                                    current_progress = progress if progress is not None else st.session_state.coa_progress_data.get("progress", 0)
                                    log_entry = f"[{current_progress}%] {msg}" if progress is not None else f"  - {msg}"
                                    label = f"방책 분석 중: {current_progress}% - {msg}" if current_progress is not None else f"방책 분석 중: {msg}"
                                    
                                    progress_bar.progress(current_progress / 100.0)
                                    progress_text.text(f"진행율: {current_progress}%")
                                    current_step_text.markdown(f"**현재 작업:** {msg}")
                                    status.update(label=label)
                                    
                                    st.session_state.coa_progress_data["logs"].append(log_entry)
                                    st.session_state.coa_progress_data["label"] = label
                                    st.session_state.coa_progress_data["progress"] = current_progress
                                    
                                agent_result = agent.execute_reasoning(
                                    situation_id=active_sit.get("situation_id"),
                                    selected_situation_info=active_sit,
                                    use_palantir_mode=use_palantir_mode,
                                    enable_rag_search=True,
                                    coa_type_filter=st.session_state.get("selected_coa_types", ["Defense"]),
                                    status_callback=on_status_update
                                )
                                
                                # 완료 처리
                                progress_bar.progress(1.0)
                                progress_text.text("진행율: 100%")
                                status.update(label="✅ 방책 분석 완료 (100%)", state="complete")
                                
                                st.session_state.coa_progress_data["label"] = "✅ 방책 분석 완료 (100%)"
                                st.session_state.coa_progress_data["state"] = "complete"
                                st.session_state.coa_progress_data["progress"] = 100
                                
                                # 결과 저장
                                if "messages_v2" not in st.session_state: st.session_state.messages_v2 = []
                                st.session_state.messages_v2.append({
                                    "role": "user",
                                    "content": f"상황 {active_sit.get('situation_id')}에 대한 방책 추천 요청",
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                st.session_state.messages_v2.append({
                                    "role": "assistant",
                                    "content": agent_result.get("summary", "방책 추천이 완료되었습니다."),
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "metadata": {"agent_result": agent_result}
                                })
                                
                                st.success("✅ 방책 추천이 완료되었습니다!")
                                st.session_state.scroll_to_result = True
                                
                                # [중요] 실행 완료 후 플래그 해제 및 리런
                                st.session_state["run_recommendation_active"] = False
                                st.rerun()
                                
                            else:
                                st.error("Agent 클래스 경로를 찾을 수 없습니다.")
                        else:
                            st.error("Agent 정보를 찾을 수 없습니다.")
                    except Exception as e:
                        st.error(f"추천 실행 오류: {e}")
                        if "coa_progress_data" in st.session_state:
                            st.session_state.coa_progress_data["state"] = "error"
                            st.session_state.coa_progress_data["label"] = f"❌ 오류 발생: {str(e)}"
                        st.session_state["run_recommendation_active"] = False # 에러 시에도 플래그 해제
            
            # [UX 개선] 방책 분석 진행/완료 상태 표시 (통합 버전)
            if "coa_progress_data" in st.session_state:
                p_data = st.session_state.coa_progress_data
                state = p_data.get("state", "running")
                
                # 버튼을 클릭한 현재 세션(실행 중)이라면 중복 표시 방지
                is_currently_running = st.session_state.get("run_recommendation_direct", False)
                
                if not is_currently_running:
                    # 완료/오류 상태를 한 줄(collapsed)로 표시하거나, 실행 중 상태가 남은 경우 표시
                    with status_placeholder.status(p_data["label"], state=state, expanded=False):
                        # 필요한 경우에만 진행율 표시
                        if state == "running" and "progress" in p_data:
                            st.progress(p_data["progress"] / 100.0)
                        
                        # 로그 표시 (확장 시 확인 가능)
                        if p_data.get("logs"):
                            for log in p_data.get("logs"):
                                st.write(log)
            else:
                st.warning("⚠️ 상황 정보를 먼저 설정하세요")
        else:
            situation_info = None

st.divider()

# Agent 실행 및 상호작용 (채팅)
st.markdown("#### 🗣️ 대화형 지휘")

# LLM-Agent 협력 모드 설정 (Compact)
use_llm_collaboration = st.checkbox(
    "LLM 협력 모드",
    value=True,
    help="LLM이 추론 과정에 참여하여 상황 분석 및 방책 평가를 보강합니다.",
    key="use_llm_collaboration"
)

if selected_agent:
    # 채팅 인터페이스 (LLM 질문 기능)
    render_chat_interface(
        orchestrator, 
        selected_agent, 
        agents_list,
        coa_type_filter=st.session_state.get("selected_coa_types", ["Defense"])
    )
else:
    st.info("Agent를 선택해주세요.")

with col_right:
    # -------------------------------------------------------------------------
    # Auto-Scroll Logic (Focusing on Results)
    # -------------------------------------------------------------------------
    # 앵커 태그 생성
    st.markdown('<div id="analysis_results_area"></div>', unsafe_allow_html=True)
    
    # 스크롤 타겟 결정
    target_scroll_id = None
    if st.session_state.get("scroll_to_result", False):
        target_scroll_id = "analysis_results_area"
        st.session_state.scroll_to_result = False
    elif st.session_state.get("scroll_to_confirmation", False):
        target_scroll_id = "situation_confirmation_area"
        st.session_state.scroll_to_confirmation = False

    # 플래그 확인 및 스크롤 실행
    if target_scroll_id:
        import streamlit.components.v1 as components
        components.html(
            f"""
            <script>
                // 렌더링 안정화를 위해 잠시 대기 후 스크롤 이동
                setTimeout(function() {{
                    const element = window.parent.document.getElementById('{target_scroll_id}');
                    if (element) {{
                        element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                    }}
                }}, 300);
            </script>
            """,
            height=0,
            width=0
        )
    # -------------------------------------------------------------------------

    st.subheader("📊 작전 분석 결과")
    
    # [Integrate] Tactical Map Visualization
    # 1. Prepare Data
    threat_geojson = None
    coa_geojson = None
    coa_recommendations = []
    situation_summary = None
    
    # Attempt to get situation info from session or result
    current_situation = st.session_state.get("selected_situation_info")
    
    # 2. Map Generation Logic
    if current_situation:
        if orchestrator:
            # 실시간 온톨로지 보강 (데이터 누락 방지 최후의 보루)
            # GeoJSON 생성 전에 실행해야 좌표가 반영됨
            current_situation = enrich_situation_info_with_ontology(current_situation, orchestrator)
            st.session_state.selected_situation_info = current_situation

        # [MOD] Load current threat AND all other enemy units for comprehensive COP
        # [FIX] 실제 위협상황과 배경 적군을 구분하여 표시
        all_threats = []
        identified_threats = []  # 실제 식별된 위협상황만 (위협식별 숫자에 포함)
        
        if current_situation:
            # 현재 선택된 위협상황은 실제 식별된 위협으로 표시
            current_situation["is_identified_threat"] = True
            all_threats = [current_situation]
            identified_threats = [current_situation]
            
        # Get all enemy units from database to show background enemy layout
        try:
            enemy_df = orchestrator.core.data_manager.load_table("적군부대현황")
            if enemy_df is not None:
                curr_id = str(current_situation.get("situation_id") or current_situation.get("ID") or current_situation.get("위협ID") or "").strip()
                
                for _, row in enemy_df.iterrows():
                    enemy_id = str(row.get("적군부대ID") or row.get("ID") or "").strip()
                    
                    # Skip if it's the same as the current selected threat (already in all_threats[0])
                    if enemy_id == curr_id:
                        continue
                        
                    enemy_entry = row.to_dict()
                    # Ensure compatible keys for map_threats_to_geojson
                    enemy_entry["위협ID"] = enemy_id
                    enemy_entry["위협명"] = row.get("적군부대명")
                    enemy_entry["위협유형"] = row.get("임무", "Enemy")
                    enemy_entry["상황설명"] = row.get("비고", "")
                    # [FIX] 배경 적군 부대는 위협식별 숫자에 포함하지 않음
                    enemy_entry["is_identified_threat"] = False
                    # [FIX] 좌표정보도 포함 (배치지형셀ID가 있으면 지형셀 좌표 조회 가능)
                    if "좌표정보" not in enemy_entry or not enemy_entry.get("좌표정보"):
                        # 배치지형셀ID가 있으면 나중에 지형셀 좌표로 조회됨
                        pass
                    
                    all_threats.append(enemy_entry)
                
                # print(f"[INFO] Loaded {len(all_threats)} total enemy units (including current threat)")
        except Exception as e:
            print(f"[WARN] Failed to load background enemy units: {e}")

        # 현재 선택된 위협 ID 식별 (하이라이트용)
        selected_id = current_situation.get("situation_id") or current_situation.get("ID") or current_situation.get("위협ID")
        
        # [DEBUG] COA 시각화 전 데이터 확인
        if all_threats:
            for idx, threat in enumerate(all_threats):
                threat_id = threat.get('위협ID') or threat.get('situation_id') or threat.get('임무ID')
                coords = threat.get('좌표정보') or threat.get('coordinates')
                name = threat.get('위협명') or threat.get('임무명')
                print(f"[DEBUG] Threat[{idx}] - ID: {threat_id}, Coords: {coords}, Name: {name}")
                # 좌표정보가 없으면 경고
                if not coords:
                    print(f"[WARN] Threat[{idx}] {threat_id} has no 좌표정보! Available keys: {list(threat.keys())[:10]}")

        # Map all threats, highlighting the selected one
        threat_geojson = ScenarioMapper.map_threats_to_geojson(all_threats, orchestrator, selected_id=selected_id)

        # [NEW] Ontology Enrichment for COP
        if orchestrator:
            try:
                from ui.views.knowledge_graph import OntologyCOPMapper
                threat_geojson = OntologyCOPMapper.enhance_threat_data_with_ontology(
                    threat_geojson, 
                    orchestrator.core.ontology_manager
                )
            except Exception as e:
                print(f"[WARN] Ontology enrichment failed: {e}")

        # 위협 상황 기반 상세 브리핑 생성 (불필요한 수식어 제거 및 정보 밀도 강화)
        sit_id = current_situation.get("situation_id", current_situation.get("ID", "Unknown"))
        threat_level = current_situation.get("위협수준", current_situation.get("threat_level", "Unknown"))
        threat_type = current_situation.get("위협유형", current_situation.get("type", "General"))
        location_id = current_situation.get("발생장소", current_situation.get("location", ""))
        location_name = current_situation.get("location_name", current_situation.get("발생지형명", ""))
        location_region = current_situation.get("location_region", current_situation.get("발생지역", ""))
        axis_id = current_situation.get("관련축선ID", current_situation.get("axis_id", ""))
        axis_name = current_situation.get("axis_name", current_situation.get("관련축선명", ""))
        enemy = current_situation.get("enemy_units", current_situation.get("적부대", ""))
        enemy = enemy if enemy and enemy != "****" else "" # **** 방지
        occ_time = current_situation.get("occurrence_time", current_situation.get("발생시각", ""))
        time_str_raw = current_situation.get("time_str") # NEW
        desc = current_situation.get("description", current_situation.get("상황설명", ""))
        
        # 상세 정보 보존 필드 추출
        threat_type_original = current_situation.get("threat_type_original")
        enemy_unit_original = current_situation.get("enemy_unit_original")
        
        # 시간 형식 정규화 (HH:MM 위주)
        t_str = None
        if time_str_raw:
            t_str = time_str_raw
        elif occ_time and occ_time != "N/A": 
            try:
                t_str = occ_time.split('T')[1][:5] if 'T' in occ_time else occ_time[:5]
            except:
                t_str = str(occ_time)
        
        # 2.5 상황 브리핑 배너 (CSS 통합)
        st.markdown(f"""
        <style>
            .situation-banner {{
                background-color: rgba(241, 196, 15, 0.1);
                border-left: 5px solid #f1c40f;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid rgba(241, 196, 15, 0.2);
            }}
            .situation-banner .banner-title {{
                margin: 0 0 10px 0;
                color: #f1c40f;
                font-size: 1.1em;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .situation-banner .banner-content {{
                margin: 0;
                color: #e6edf3;
                font-size: 1.05em;
                line-height: 1.6;
            }}
            .situation-banner .banner-desc {{
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px dashed rgba(241, 196, 15, 0.2);
                color: #c9d1d9;
                font-size: 0.9em;
                line-height: 1.5;
            }}
        </style>
        """, unsafe_allow_html=True)
    
    # Check if we have agent results for COA
    if "messages_v2" in st.session_state and st.session_state.messages_v2:
        last_msg = st.session_state.messages_v2[-1]
        if last_msg.get("role") == "assistant":
            res = last_msg.get("metadata", {}).get("agent_result")
            if res:
                # 상황 ID가 일치하는 경우에만 데이터 추출
                # res_sit_id = res.get("situation_id") or res.get("situation_info", {}).get("situation_id")
                # curr_sit_id = current_situation.get("situation_id") if current_situation else None
                
                if True: # res_sit_id == curr_sit_id: # 상황 변경 시 메시지가 초기화되므로 ID 비교 불필요 (ID 불일치 버그 방지)
                    res_sit_id = res.get("situation_id") or res.get("situation_info", {}).get("situation_id")
                    curr_sit_id = current_situation.get("situation_id") if current_situation else None
                    
                    # ID 정규화 및 비교
                    id_match = False
                    if res_sit_id and curr_sit_id:
                        id_match = str(res_sit_id).strip() == str(curr_sit_id).strip()
                
                if id_match:
                    coa_recommendations = res.get("recommendations", [])
                    # 에이전트가 생성한 서술형 요약이 있으면 이를 브리핑 문구로 사용
                    agent_summary = res.get("situation_summary") or res.get("summary")
                    if agent_summary:
                        situation_summary = agent_summary
                    
                    if coa_recommendations:
                        # [FIX] Generate GeoJSON for ALL COAs, not just top one
                        # [CRITICAL FIX] Pass orchestrator to enable StatusManager and Axis resolution
                        all_coa_features = []
                        for idx, coa in enumerate(coa_recommendations):
                            # [FIX] COA ID 일관성 보장 - 모든 가능한 필드 확인
                            coa_id = (coa.get("coa_id") or coa.get("COA_ID") or coa.get("id") or 
                                     coa.get("방책ID") or coa.get("ID") or f"COA_{idx+1}")
                            # COA 객체에도 일관된 ID 설정 (tactical_map.js에서 매칭을 위해)
                            if not coa.get("coa_id"):
                                coa["coa_id"] = coa_id
                            if not coa.get("COA_ID"):
                                coa["COA_ID"] = coa_id
                            
                            # ✅ orchestrator 전달 - StatusManager 좌표, 축선 해결 활성화
                            coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson, orchestrator)
                            
                            # Debug logging
                            if st and hasattr(st, 'session_state'):
                                feature_count = len(coa_geo.get("features", [])) if coa_geo else 0
                                print(f"[COP-VIZ] COA {coa_id}: Generated {feature_count} features")
                            
                            # Tag each feature with the COA ID (일관된 ID 사용)
                            if coa_geo and "features" in coa_geo:
                                for feature in coa_geo["features"]:
                                    # Ensure coa_id is set in properties
                                    if "properties" not in feature:
                                        feature["properties"] = {}
                                    # 모든 가능한 ID 필드에 동일한 값 설정
                                    feature["properties"]["coa_id"] = coa_id
                                    feature["properties"]["COA_ID"] = coa_id
                                    all_coa_features.append(feature)
                        
                        # Create combined GeoJSON
                        coa_geojson = {
                            "type": "FeatureCollection",
                            "features": all_coa_features
                        }
                        
                        # Debug: Log total features
                        print(f"[COP-VIZ] Total COA features generated: {len(all_coa_features)}")
                    
                    # If situation was not in session (e.g. loaded from result), try to get from result
                    if not threat_geojson and res.get("situation_info"):
                         threat_geojson = ScenarioMapper.map_threats_to_geojson([res.get("situation_info")])

    # 2.8 최종 배너 출력 (모든 데이터 취합 후 한 번만)
    if current_situation or situation_summary:
        approach_mode = current_situation.get("approach_mode", "threat_centered") if current_situation else "threat_centered"
        
        # 문구 결정 우선순위: UI 자체 생성 서술구(Rule-based)를 기본으로 사용하고, 에이전트 요약은 상세내용에 포함
        # 이유: 로컬 LLM의 경우 요약 품질이 낮거나 지시사항이 누수될 수 있음
        final_briefing = None 
        
        # 항상 Rule-based로 먼저 생성 시도
        if current_situation:
            # 0. 코드명 자연어 변환 매핑
            codec_map = {
                "INFANTRY": "보병", "ARMOR": "기갑", "ARTILLERY": "포병", 
                "AIR": "항공", "MISSILE": "미사일", "CBRN": "화생방", 
                "CYBER": "사이버", "INFILTRATION": "침투", "UNKNOWN": "미상",
                "ENU_ESTIMATED": "식별된 적 부대", "ARTILLERY_FIRE": "포탄 사격",
                "ARTILLERY_READY": "포병 준비", "SCAN": "탐지", "RECON": "정찰",
                "HIGH": "높음", "MEDIUM": "중간", "LOW": "낮음"
            }
            
            t_type_ko = codec_map.get(str(threat_type).upper(), threat_type) if 'threat_type' in locals() and threat_type else "미상"
            enemy_ko = codec_map.get(str(enemy).upper(), enemy) if 'enemy' in locals() and enemy and enemy != "N/A" else ""
            if approach_mode == "mission_centered":
                # 임무 중심에서는 위협 수준을 '성공 가능성'으로 역전시켜 해석
                if str(threat_level).upper() in ["HIGH", "높음", "H"]:
                    t_level_ko = "낮음"
                elif str(threat_level).upper() in ["MEDIUM", "중간", "M", "보통"]:
                    t_level_ko = "보통"
                elif str(threat_level).upper() in ["LOW", "낮음", "L"]:
                    t_level_ko = "높음"
                else:
                    t_level_ko = "미상"
            else:
                t_level_ko = codec_map.get(str(threat_level).upper(), threat_level) if 'threat_level' in locals() and threat_level else "미상"

            # UI 자체 서술구 생성
            t_prefix = f"**{t_str}** 현재, " if 't_str' in locals() and t_str else ""
            
            # 지형 정보 조립 (지역 정보 포함 및 ID 병기)
            full_loc_name = ""
            if location_region and str(location_region).upper() != "N/A":
                full_loc_name = f"{location_region} "
            if location_name and str(location_name).upper() != "N/A" and str(location_name).strip() != "":
                full_loc_name += location_name
            
            if full_loc_name.strip():
                loc_disp = f"**{full_loc_name.strip()}**"
                if location_id and str(location_id).upper() != "N/A":
                    # 명칭과 ID가 다를 때만 병기
                    if str(location_id).strip().upper() != str(location_name).strip().upper():
                        loc_disp += f"({location_id})"
            elif location_id and str(location_id).upper() != "N/A":
                loc_disp = f"**{location_id}**"
            else:
                loc_disp = "**작전 지역**"
            
            # 축선 정보 조립
            ax_disp = ""
            if axis_id and str(axis_id).upper() != "N/A" and str(axis_id).strip() != "":
                if axis_name and str(axis_name).upper() != "N/A" and str(axis_name).strip() != "":
                    ax_disp = f"**{axis_name}({axis_id})**"
                else:
                    ax_disp = f"**{axis_id}**"
            
            if approach_mode == "mission_centered":
                # 임무 중심 서술구 생성
                m_id = current_situation.get("mission_id") or current_situation.get("임무ID") or "N/A"
                m_name = current_situation.get("임무명") or current_situation.get("mission_name") or "기본 임무"
                m_type = current_situation.get("임무종류") or current_situation.get("mission_type") or "기본"
                m_objective = current_situation.get("임무목표") or current_situation.get("mission_objective") or ""
                
                final_briefing = f"{t_prefix}{loc_disp} 일대에서 **{m_name}**({m_id}) {m_type} 임무가 하달되었습니다. "
                if ax_disp:
                    final_briefing += f"주요 작전 축선은 {ax_disp} 방향이며, "
                
                final_briefing += f"현재 분석된 **임무 성공 가능성**은 **{t_level_ko}** 수준입니다."
                
                if m_objective:
                    desc = f"**목표:** {m_objective}\n\n{desc}" if desc else f"**목표:** {m_objective}"
            else:
                # 위협 중심 서술구 생성 (기존 로직)
                # 구체적 정보가 있으면 우선 사용
                t_type_disp = threat_type_original if threat_type_original else t_type_ko
                enemy_disp = enemy_unit_original if enemy_unit_original else enemy_ko
                
                enemy_prefix = f"**{enemy_disp}**에 의한 " if enemy_disp else "미상의 위협원에 의한 "
                type_prefix = f"**{t_type_disp}** 위협이 식별되었습니다."
                
                final_briefing = f"{t_prefix}{loc_disp} 일대에서 {enemy_prefix}{type_prefix} "
                if ax_disp:
                    final_briefing += f"{ax_disp} 방향 위협 수준은 **{t_level_ko}** 상태입니다."
                else:
                    final_briefing += f"위협 수준은 **{t_level_ko}** 상태입니다."
        
        # 임무 중심인 경우 최종 문구 재검색/치환 (에이전트 결과물 포함)
        if approach_mode == "mission_centered" and final_briefing:
            final_briefing = translate_to_mission_terms(final_briefing)

        sid = sit_id if 'sit_id' in locals() else "N/A"
        
        # 상세 내용 구성: 기본 설명 + LLM 요약 (있는 경우)
        desc_parts = []
        if 'desc' in locals() and desc:
            desc_parts.append(desc)
        if situation_summary:
            # LLM 요약이 반복적인 텍스트(오류)인지 간단히 확인
            if len(situation_summary) > 200 and len(set(situation_summary.split())) < 20:
                 # 반복 패턴이 의심되면 제외
                 pass
            elif "긴 문장은 2줄로" in situation_summary: # 사용자가 제보한 특정 오류 패턴 필터링
                 pass
            else:
                 desc_parts.append(f"\n\n**[분석 요약]**\n{situation_summary}")
        
        summary_desc = "\n".join(desc_parts)
        
        # final_briefing이 없으면 situation_summary를 사용
        if not final_briefing and situation_summary:
            final_briefing = situation_summary[:200] + "..." if len(situation_summary) > 200 else situation_summary
        
        banner_title = f"📡 {sid} 임무 보고" if approach_mode == "mission_centered" else f"📡 {sid} 정황 보고"

        # 마크다운을 HTML로 변환하는 함수 (개선된 버전)
        def markdown_to_html(text):
            """마크다운을 HTML로 변환"""
            if not text:
                return ""
            # 문자열로 변환
            text = str(text)
            
            # 볼드 처리 (**text** 또는 __text__) - 먼저 HTML 태그로 직접 변환
            def replace_bold(match):
                content = match.group(1)
                # 볼드 내용을 이스케이프하고 strong 태그로 감싸기
                escaped_content = html.escape(content)
                return f"<strong>{escaped_content}</strong>"
            
            text = re.sub(r'\*\*(.+?)\*\*', replace_bold, text)
            text = re.sub(r'__(.+?)__', replace_bold, text)
            
            # HTML 태그를 임시로 보호
            tag_placeholders = {}
            tag_counter = 0
            
            def protect_tags(match):
                nonlocal tag_counter
                tag = match.group(0)
                placeholder = f"__HTML_TAG_{tag_counter}__"
                tag_placeholders[placeholder] = tag
                tag_counter += 1
                return placeholder
            
            # HTML 태그를 플레이스홀더로 교체
            text = re.sub(r'<[^>]+>', protect_tags, text)
            
            # 나머지 텍스트만 HTML 이스케이프
            text = html.escape(text)
            
            # HTML 태그 복원
            for placeholder, tag in tag_placeholders.items():
                text = text.replace(placeholder, tag)
            
            # 줄바꿈 처리
            text = text.replace('\n', '<br/>')
            return text
        
        # 마크다운을 HTML로 변환
        final_briefing_html = markdown_to_html(final_briefing) if final_briefing else ""
        summary_desc_html = markdown_to_html(summary_desc) if summary_desc and summary_desc.strip() else ""
        
        # title 속성용 (이스케이프만, HTML 태그 없이)
        final_briefing_title = html.escape(str(final_briefing)) if final_briefing else ""

        st.markdown(f"""
        <style>
            .situation-banner .banner-content {{
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                text-overflow: ellipsis;
                max-height: 3.2em; /* Fallback */
            }}
            .situation-banner .banner-desc {{
                 max-height: 150px;
                 overflow-y: auto;
            }}
        </style>
        <div class="situation-banner">
            <div class="banner-title">{banner_title}</div>
            <div class="banner-content" title="{final_briefing_title}">
                {final_briefing_html}
            </div>
            {f'<div class="banner-desc"><b>상세내용:</b> {summary_desc_html}</div>' if summary_desc_html else ''}
        </div>
        """, unsafe_allow_html=True)

    # 3. Render Map if we have at least threat data
    if threat_geojson:
        # [NEW] Fullwidth CSS for COP
        st.markdown("""
        <style>
        .cop-fullwidth { 
            width: 100% !important; 
            max-width: 100% !important; 
        }
        .cop-fullwidth > div { width: 100% !important; }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="cop-fullwidth">', unsafe_allow_html=True)
        with st.expander("🗺️ 전술 상황도 (COP)", expanded=True):
             # [NEW] Reasoning Trace GeoJSON 생성
             reasoning_geojson = None
             if coa_recommendations:
                 all_reasoning_features = []
                 for idx, rec in enumerate(coa_recommendations):
                     trace = rec.get("reasoning_trace", [])
                     if trace:
                         c_id = rec.get("coa_id") or rec.get("id") or f"COA_{idx+1}"
                         trace_geo = ScenarioMapper.map_reasoning_to_geojson(
                             trace, 
                             threat_geojson, 
                             coa_geojson,
                             coa_id=c_id
                         )
                         if trace_geo and "features" in trace_geo:
                             all_reasoning_features.extend(trace_geo["features"])
                 
                 if all_reasoning_features:
                     reasoning_geojson = {
                         "type": "FeatureCollection",
                         "features": all_reasoning_features
                     }

             render_tactical_map(
                 coa_recommendations=coa_recommendations,
                 threat_geojson=threat_geojson,
                 coa_geojson=coa_geojson,
                 reasoning_geojson=reasoning_geojson,
                 height=700,
                 situation_summary=situation_summary # [NEW] 동기화된 상황 정보 전달
             )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Fallback empty map or placeholder
        pass

    # 최근 응답 확인
    if "messages_v2" in st.session_state and st.session_state.messages_v2:
        last_message = st.session_state.messages_v2[-1]
        
        if last_message.get("role") == "assistant":
            agent_result = last_message.get("metadata", {}).get("agent_result")
            
            # ID 비교: 현재 선택된 상황과 분석 결과의 상황 ID가 일치하는지 확인
            is_synced = False
            recommendations = []
            
            # 상황 ID 및 일치 여부 확인
            res_sit_id = None
            curr_sit_id = current_situation.get("situation_id") if current_situation else None

            if agent_result:
                res_sit_id = agent_result.get("situation_id") or agent_result.get("situation_info", {}).get("situation_id")
                if res_sit_id and curr_sit_id and res_sit_id == curr_sit_id:
                    is_synced = True

            # 상황 요약 및 추천 방책 설정
            if is_synced:
                recommendations = agent_result.get("recommendations", [])
                situation_summary = {
                    "id": curr_sit_id,
                    "phase": "방책 도출 완료 (Phase 2)",
                    "synced": True
                }
            elif agent_result:
                # 데이터 불일치 (Stale Data)
                situation_summary = None
                if current_situation:
                     situation_summary = {
                        "id": current_situation.get("situation_id"),
                        "phase": "위협 분석 단계 (Phase 1)",
                        "synced": True
                    }
            else:
                # 초기 상태 (No Result)
                situation_summary = None
                if current_situation:
                     situation_summary = {
                        "id": current_situation.get("situation_id"),
                        "phase": "위협 분석 단계 (Phase 1)",
                        "synced": True
                    }
            
            # 상세 분석 대상 방책 선택 UI (동기화된 경우에만 표시)
            if recommendations:
                # [NEW] 상세 분석 대상 방책 선택 UI
                st.markdown("---")
                coa_options = [f"{i+1}. {r.get('coa_name', 'Unknown')}" for i, r in enumerate(recommendations)]
                
                # 세션 상태에서 선택 인덱스 관리 (초기값 0)
                if "selected_coa_idx" not in st.session_state:
                    st.session_state.selected_coa_idx = 0
                    
                selected_coa_choice = st.selectbox(
                    "🔍 상세 분석할 방책 선택", 
                    options=coa_options,
                    index=st.session_state.selected_coa_idx,
                    help="선택한 방책의 상세 추론 근거와 전략 체인을 아래 패널에서 확인합니다."
                )
                
                # 선택된 인덱스 업데이트
                current_idx = coa_options.index(selected_coa_choice)
                st.session_state.selected_coa_idx = current_idx
                target_rec = recommendations[current_idx]

                # 상세 분석 패널들
                col_det1, col_det2 = st.columns([1, 1])
                
                with col_det1:
                    with st.expander(f"🧠 {target_rec.get('coa_name')} 추론 근거", expanded=True):
                        try:
                            from ui.components.reasoning_explanation import render_reasoning_explanation
                            render_reasoning_explanation(target_rec, orchestrator.core, approach_mode=approach_mode)
                        except Exception as e:
                            st.error(f"시각화 오류: {e}")
                    
                with col_det2:
                    # 1.5. 전략 체인 시각화 (Chain of Strategy) - NEW
                    # 선택된 방책에 특화된 체인 정보(chain_info_details) 우선 사용
                    chain_info = target_rec.get("chain_info_details") or agent_result.get("situation_analysis", {}).get("chain_info")
                    
                    with st.expander(f"🔗 {target_rec.get('coa_name')} 전략 연계", expanded=True):
                        if chain_info and (chain_info.get("chains") or chain_info.get("summary")):
                            from ui.components.chain_visualizer import ChainVisualizer
                            ChainVisualizer().render_chains(chain_info)
                        else:
                            st.info("전략 연계 체인 데이터가 없습니다.")


                # 2. 추천 방책 카드 (COA Cards)
                st.markdown("##### 🃏 추천 방책 목록")
                recommendations = agent_result.get("recommendations", [])
                
                if recommendations:
                    for i, rec in enumerate(recommendations):
                        # [NEW] 확장 데이터 추출
                        reasoning = rec.get('reasoning', {})
                        unit_rationale = reasoning.get('unit_rationale')
                        search_path = reasoning.get('system_search_path')
                        units = rec.get('participating_units', '')
                        if isinstance(units, list):
                            units = ", ".join(units)
                        elif not units:
                            units = rec.get('필요자원', 'N/A')
                        
                        # 지침/고려사항 포맷팅 (부대 근거 등 처리)
                        def format_clean_text(text):
                            if not text: return ""
                            return text.replace('\n', '<br>')
                        
                        # 지침/고려사항 포맷팅 (불렛 포인트 등 처리)
                        def format_bullet_text(text):
                            if not text: return ""
                            # 이미 불렛이 있으면 유지, 없으면 줄바꿈 기준으로 생성
                            lines = text.split('\n')
                            formatted_lines = []
                            for line in lines:
                                line = line.strip()
                                if not line: continue
                                if not (line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line)):
                                    line = f"- {line}"
                                formatted_lines.append(f'<div style="margin-bottom: 4px;">{line}</div>')
                            return "".join(formatted_lines)

                        with st.container():
                            # 스타일 정의
                            st.markdown(f"""
                            <style>
                            .coa-card-{i} {{
                                border-left: 6px solid #4a90e2;
                                background-color: #1a1e24;
                                border-radius: 8px;
                                padding: 15px;
                                margin-bottom: 20px;
                                box-shadow: 0 4px 15px rgba(0,0,0,0.4);
                            }}
                            .coa-header {{
                                display: flex; justify-content: space-between; align-items: center;
                                margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;
                            }}
                            .coa-title {{ color: #fff; font-size: 1.1em; font-weight: 700; margin: 0; }}
                            .coa-badge {{ font-size: 0.7em; color: #4a90e2; background: rgba(74, 144, 226, 0.1); border: 1px solid rgba(74, 144, 226, 0.3); padding: 2px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; margin-left: 8px; }}
                            .coa-units {{ font-size: 0.8em; color: #8b949e; display: flex; align-items: center; gap: 5px; }}
                            .rationale-box {{ background: rgba(74, 144, 226, 0.03); border: 1px solid rgba(74, 144, 226, 0.1); padding: 12px; border-radius: 6px; margin-bottom: 10px; }}
                            .search-box {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 6px; }}
                            </style>
                            """, unsafe_allow_html=True)

                            # 카드 컨테이너 시작
                            st.markdown(f'<div class="coa-card-{i}">', unsafe_allow_html=True)
                            
                            # 헤더 영역
                            # 방책 유형 한글 변환
                            coa_type = rec.get('coa_type', rec.get('type', 'Defense'))
                            type_map = {
                                "Defense": "방어", "Offensive": "공세", "Counter_Attack": "반격",
                                "Preemptive": "선제", "Deterrence": "억제", "Maneuver": "기동", "Information_Ops": "정보작전"
                            }
                            coa_type_ko = type_map.get(coa_type, coa_type)
                            
                            # 선정 카테고리 한글 변환
                            sel_cat = rec.get('selection_category', 'Operational Optimum')
                            cat_map = {
                                "Operational Optimum": "작전 최적", 
                                "Maneuver & Speed": "기동/속도", 
                                "Firepower Focus": "화력 집중",
                                "Sustainable Defense": "지속 방어"
                            }
                            sel_cat_ko = cat_map.get(sel_cat, sel_cat)

                            st.markdown(f"""
                            <div class="coa-header">
                                <div style="display: flex; align-items: center;">
                                    <span class="coa-title">{i+1}. {rec.get('coa_name')}</span>
                                    <span class="coa-badge">{coa_type_ko}</span>
                                    <span class="coa-badge" style="border-color: #ff9f43; background: rgba(255, 159, 67, 0.1); color: #ff9f43;">{sel_cat_ko}</span>
                                </div>
                                <div class="coa-units">
                                    <span>⚓</span> {units}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # 본문 영역 (Grid 대신 div 스택 사용으로 안정성 확보)
                            # 부대 운용 근거 -> 방책 선정 사유로 변경
                            justification = reasoning.get('justification')
                            rationale_text = justification if justification else (unit_rationale if unit_rationale else f"🛡️ <b>{rec.get('coa_name')}</b> 작전을 위해 공병(장애물), 포병(화력지원) 등 핵심 자산을 통합 운용하여 효과를 극대화합니다.")
                            
                            st.markdown(f"""
                            <div class="rationale-box">
                                <div style="font-size: 0.85em; color: #4a90e2; font-weight: 700; margin-bottom: 8px;">
                                    🛡️ 방책 선정 사유 (Recommendation Rationale)
                                </div>
                                <div style="font-size: 0.9em; color: #c9d1d9; line-height: 1.6;">
                                    {rationale_text}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # 시스템 탐색 과정
                            search_text = search_path if search_path else "🔍 국방 온톨로지의 <code>requiresResource</code> 및 <code>hasConstraint</code> 속성을 추론하여 최적의 가용 부대를 식별했습니다."
                            st.markdown(f"""
                            <div class="search-box">
                                <div style="font-size: 0.8em; color: #8b949e; font-weight: 600; margin-bottom: 5px;">
                                    🔍 시스템 탐색 과정 (Resource Discovery Path)
                                </div>
                                <div style="font-size: 0.8em; color: #8b949e; font-style: italic; line-height: 1.4;">
                                    {search_text}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 🔥 NEW: 교리 참조 인라인 표시
                            doctrine_refs = rec.get('doctrine_references', [])
                            if doctrine_refs:
                                from ui.components.doctrine_reference_display import render_doctrine_references_inline
                                render_doctrine_references_inline(rec)
                            
                            # 온톨로지 추론 흔적 (Reasoning Trace) - NEW
                            reasoning_trace = rec.get("reasoning_trace")
                            if reasoning_trace:
                                # [FIX] 리스트 내의 항목이 문자열이 아닐 경우(딕셔너리 등)를 대비하여 문자열 변환 처리
                                trace_str_list = []
                                for item in reasoning_trace:
                                    if isinstance(item, str):
                                        trace_str_list.append(item)
                                    elif isinstance(item, dict):
                                        # Edge-based trace ({from: ..., to: ..., description: ...}) 처리
                                        desc = item.get("description") or f"{item.get('from')} → {item.get('to')}"
                                        trace_str_list.append(desc)
                                    else:
                                        trace_str_list.append(str(item))
                                
                                st.markdown(f"""
                                <div style="margin-top: 10px; padding: 8px; background: rgba(46, 154, 254, 0.05); border: 1px dashed rgba(46, 154, 254, 0.2); border-radius: 4px;">
                                    <div style="font-size: 0.75em; color: #2E9AFE; font-weight: 700; margin-bottom: 4px;">🌱 온톨로지 추론 흔적 (ONTOLOGY REASONING TRACE)</div>
                                    <div style="font-size: 0.8em; color: #a5d6ff;">{" → ".join(trace_str_list)}</div>
                                </div>
                                """, unsafe_allow_html=True)

                            # 카드 컨테이너 종료
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # 상세 정보 (Expander)
                            # 상세 정보 (Expander)
                            with st.expander(f"📊 {rec.get('coa_name')} 상세 분석 결과"):
                                # 🔥 개선: 참고 자료(교리+일반) 탭 처리 로직 강화
                                doctrine_refs = rec.get('doctrine_references')
                                has_data = False
                                if isinstance(doctrine_refs, list) and len(doctrine_refs) > 0:
                                    has_data = True
                                elif doctrine_refs:
                                    has_data = True
                                
                                # 탭 레이블 정의 (4개 고정)
                                tab_labels = ["평가 세부사항", "기대 효과", "📚 참고 자료", "원본 데이터"]
                                created_tabs = st.tabs(tab_labels)
                                
                                # 1. 평가 세부사항
                                with created_tabs[0]:
                                    # 점수 상세 (DataFrame)
                                    score_breakdown = rec.get("score_breakdown", {})
                                    if score_breakdown and "reasoning" in score_breakdown:
                                        df_reason = pd.DataFrame(score_breakdown["reasoning"])
                                        if not df_reason.empty:
                                            # 컬럼 매핑: factor -> 평가요소, score -> 점수, weight -> 가중치, reason -> 근거
                                            df_display = df_reason[['factor', 'score', 'weight', 'reason']].copy()
                                            df_display.columns = ['평가요소', '산출점수', '가중치', '평가근거']
                                            # 포맷팅
                                            df_display['산출점수'] = df_display['산출점수'].apply(lambda x: f"{x:.2f}")
                                            st.dataframe(
                                                df_display, 
                                                hide_index=True,
                                                column_config={
                                                    "평가요소": st.column_config.TextColumn(width="medium"),
                                                    "평가근거": st.column_config.TextColumn(width="large"),
                                                }
                                            )
                                        else:
                                            st.info("상세 평가 데이터가 없습니다.")
                                    else:
                                        # Palantir Mode가 아니거나 데이터가 없는 경우
                                        st.write("주요 평가 항목:")
                                        st.json(score_breakdown)

                                # 2. 기대 효과
                                with created_tabs[1]:
                                    # 기대 효과 및 강점
                                    pros = rec.get('reasoning', {}).get('pros', [])
                                    if pros:
                                        for p in pros:
                                            st.markdown(f"- ✅ {p}")
                                    else:
                                        st.info("기대 효과 정보가 없습니다.")
                                
                                # 3. 교리 참조 (Index 2)
                                with created_tabs[2]:
                                    if has_data:
                                        from ui.components.doctrine_reference_display import render_doctrine_references, render_doctrine_based_explanation
                                        
                                        # 교리 참조 표시
                                        render_doctrine_references(rec)
                                        
                                        # 교리 기반 설명 표시
                                        render_doctrine_based_explanation(
                                            coa_recommendation=rec,
                                            situation_info=agent_result.get("situation_info"),
                                            mett_c_analysis=agent_result.get("situation_analysis", {}).get("mett_c", {})
                                        )
                                    else:
                                        st.info("💡 이 방책에 연관된 교리나 과거 유사 사례가 식별되지 않았습니다.")
                                
                                # 4. 원본 데이터 (Index 3)
                                with created_tabs[3]:
                                    st.caption("디버깅용 원본 데이터")
                                    st.json(rec)

                # 3. 방책 실행 계획 (Execution Plan)
                if recommendations:
                    st.divider()
                    st.subheader("📋 최우수 방책 실행 계획")
                    render_coa_execution_plan(recommendations[0], agent_result.get("situation_info"), approach_mode=approach_mode)
                
                # 4. 보고서 생성
                if last_message.get("citations"):
                    st.divider()
                    render_report_download_button(
                        agent_name=selected_agent or "Unknown",
                        summary=last_message.get("content", ""),
                        citations=last_message.get("citations", []),
                        threat_summary=None
                    )
            else:
                # 일반 대화 응답인 경우
                st.info("💡 Agent의 일반 응답입니다. 방책 추천을 원하시면 구체적인 작전 상황에 대해 질문하세요.")
                st.markdown(f"""
                <div style="padding: 15px; background-color: rgba(255,255,255,0.05); border-radius: 5px;">
                    {last_message.get("content", "")}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("⏳ Agent의 응답을 기다리고 있습니다...")
    else:
        st.info("👈 좌측 채팅창을 통해 작전 명령을 내리거나 상황을 문의하십시오.")
        
        # 빈 상태일 때 예시 이미지나 텍스트 표시
        st.markdown("""
        <div style="text-align: center; padding: 50px; color: #666;">
            <h3>작전 분석 대기 중</h3>
            <p>좌측 패널에서 Agent를 선택하고 상황을 입력한 후 명령을 내리세요.</p>
        </div>
        """, unsafe_allow_html=True)

# Force Refresh Trigger 
