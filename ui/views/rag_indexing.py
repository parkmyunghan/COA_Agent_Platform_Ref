# ui/views/rag_indexing.py
# -*- coding: utf-8 -*-
"""
RAG 인덱스 구성 페이지
문서 업로드, 청킹, 임베딩, FAISS 인덱스 생성
"""
import streamlit as st
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

from ui.components.doc_manager import render_doc_manager, get_rag_index_status, render_index_status
from ui.components.citation_panel import render_citation_panel
from core_pipeline.orchestrator import Orchestrator
import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


st.set_page_config(
    page_title="RAG 인덱스 구성",
    layout="wide"
)

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
        width: 100%;  /* 브라우저 너비에 맞춤 */
        justify-content: space-between;
        align-items: center;
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
</style>

<div class="compact-header">
    <div class="header-title">
        RAG 인덱스 구성
    </div>
    <div class="header-subtitle">
        문서 업로드, 청킹, 임베딩, FAISS 인덱스 생성
    </div>
</div>
""", unsafe_allow_html=True)


# CSS 로드
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    pass  # load_css("ui/style.css") - 주석 처리: 커스텀 헤더와 충돌 방지
except FileNotFoundError:
    pass  # st.warning("ui/style.css 파일을 찾을 수 없습니다.")



# 설정 파일 로드
try:
    config = load_yaml("./config/global.yaml")
except Exception as e:
    st.error(f"설정 파일 로드 실패: {e}")
    st.stop()

# Orchestrator 초기화 (Enhanced Ontology Manager 사용)
# 이미 초기화 완료 플래그가 있으면 초기화 로직 건너뛰기
if st.session_state.get("main_orchestrator_initialized", False):
    # 이미 초기화 완료 - 아무 작업도 하지 않음
    pass
elif "main_orchestrator" not in st.session_state:
    # Orchestrator가 없으면 새로 생성 및 초기화
    with st.spinner("시스템 초기화 중..."):
        try:
            st.session_state.main_orchestrator = Orchestrator(config, use_enhanced_ontology=True)
            st.session_state.main_orchestrator.initialize()
            st.session_state.main_orchestrator_initialized = True
            st.success("[OK] 시스템 초기화 완료 (Enhanced Ontology Manager 활성화)")
        except Exception as e:
            st.error(f"시스템 초기화 실패: {e}")
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
        # 실제로 초기화가 필요한 경우에만 spinner 표시
        with st.spinner("시스템 초기화 중..."):
            try:
                st.session_state.main_orchestrator.initialize()
                st.session_state.main_orchestrator_initialized = True
            except Exception as e:
                st.error(f"시스템 초기화 실패: {e}")
                st.stop()

orchestrator = st.session_state.main_orchestrator

# 탭 레이아웃 구성
tab_docs, tab_status, tab_search = st.tabs([
    "📚 문서 관리", 
    "🏗️ 인덱스 상태", 
    "🔍 검색 테스트"
])

# Tab 1: 문서 관리
with tab_docs:
    render_doc_manager(orchestrator.core, key_prefix="doc_manager_rag_page")

# Tab 2: 인덱스 상태
with tab_status:
    st.markdown("### 📊 RAG 파이프라인 상태")
    st.info("임베딩 모델 로드 상태와 벡터 인덱스(FAISS) 구성 현황을 확인합니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🧠 모델 상태")
        if orchestrator.core.rag_manager.embedding_model is not None:
            st.success(f"[OK] 임베딩 모델 로드됨\n\n- Model: {config.get('rag', {}).get('embedding_model', 'Unknown')}\n- Device: CPU (Optimized)")
        else:
            st.warning("[WARN] 임베딩 모델 미로드")
    
    with col2:
        st.markdown("#### 🗂️ 인덱스 현황")
        index_status = get_rag_index_status(orchestrator.core.rag_manager)
        render_index_status(index_status, rag_manager=orchestrator.core.rag_manager, core=orchestrator.core, show_fix_option=True, key_prefix="rag_index_status_main")

# Tab 3: 검색 테스트
with tab_search:
    st.markdown("### 🔍 시맨틱 검색 테스트")
    st.info("구축된 지식 베이스(Knowledge Base)를 대상으로 의미 기반 검색을 수행합니다.")
    
    if orchestrator.core.rag_manager.is_available():
        with st.container():
            col_search_1, col_search_2 = st.columns([4, 1])
            
            with col_search_1:
                search_query = st.text_input(
                    "검색어 입력",
                    placeholder="예: 산악 지형 방어 전략, 기계화부대 운용 교리 등",
                    key="rag_search_query",
                    label_visibility="collapsed"
                )
            
            with col_search_2:
                top_k = st.number_input("검색 수", min_value=1, max_value=20, value=5, key="rag_search_top_k", label_visibility="collapsed")
            
            if st.button("🚀 검색 실행", type="primary", width="stretch", key="btn_rag_search"):
                if search_query:
                    try:
                        with st.spinner("지식 베이스 검색 중..."):
                            retrieved = orchestrator.core.rag_manager.retrieve_with_context(search_query, top_k=top_k)
                            
                            st.divider()
                            
                            if retrieved:
                                st.markdown(f"**✅ 검색 결과 ({len(retrieved)}건)**")
                                render_citation_panel(retrieved, highlight_query=search_query)
                            else:
                                st.warning("검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
                    except Exception as e:
                        st.error(f"문서 검색 실패: {e}")
                        import traceback
                        st.code(traceback.format_exc())
                else:
                    st.warning("검색어를 입력하세요.")
    else:
        st.error("⚠️ RAG 인덱스가 구성되지 않았습니다.")
        st.markdown("""
        1. **'문서 관리'** 탭으로 이동하여 문서를 업로드하세요.
        2. **'인덱스 재구축'** 버튼을 눌러 지식 베이스를 생성하세요.
        """)
