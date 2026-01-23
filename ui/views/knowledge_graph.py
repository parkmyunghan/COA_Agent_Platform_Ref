# ui/views/knowledge_graph.py
# -*- coding: utf-8 -*-
"""
지식그래프 조회 페이지
SPARQL 쿼리 실행 및 그래프 탐색
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

from ui.components.graph_viewer import render_graph
from ui.components.graph_viewer_enhanced import render_enhanced_graph
from ui.components.sparql_query_panel import render_sparql_query_panel
from ui.components.node_info_panel import render_node_info_panel
from ui.components.ontology_explainer import render_ontology_explainer
from ui.components.user_friendly_errors import render_user_friendly_error
from ui.components.ontology_dashboard_panel import render_ontology_dashboard_panel
from core_pipeline.orchestrator import Orchestrator
import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


st.set_page_config(
    page_title="전술 지식 탐색",
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
        전술 지식 탐색
    </div>
    <div class="header-subtitle">
        SPARQL 쿼리 실행 및 고급 그래프 탐색
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
    render_user_friendly_error(e, "설정 파일 로드")
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
        # 실제로 초기화가 필요한 경우에만 spinner 표시
        with st.spinner("시스템 초기화 중..."):
            try:
                st.session_state.main_orchestrator.initialize()
                st.session_state.main_orchestrator_initialized = True
            except Exception as e:
                render_user_friendly_error(e, "시스템 초기화")
                st.stop()

# Orchestrator 초기화
orchestrator = st.session_state.main_orchestrator

# 탭으로 기능 분리
tab1, tab2, tab3 = st.tabs(["🔍 SPARQL 쿼리", "🕸️ 그래프 탐색", "📊 스키마 검증"])

with tab1:
    st.header("SPARQL 쿼리 실행")
    render_sparql_query_panel(orchestrator.core)

with tab2:
    st.header("그래프 탐색")
    
    # 1. 데이터 로드 및 필터링 준비
    full_data = orchestrator.core.ontology_manager.to_json()
    
    if full_data:
        # 필터링을 위한 고유 값 추출
        all_groups = set()
        all_relations = set()
        
        # 인스턴스 및 스키마 데이터에서 그룹/관계 추출
        for mode in ["instances", "schema"]:
            for node in full_data.get(mode, {}).get("nodes", []):
                all_groups.add(node.get("group", "Unknown"))
            for link in full_data.get(mode, {}).get("links", []):
                all_relations.add(link.get("relation", "Unknown"))
        
        # 2. 필터 및 검색 패널
        with st.expander("🔍 그래프 필터 및 검색", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                search_term = st.text_input("노드 검색 (ID 또는 Label)", placeholder="검색어 입력...", key="graph_search")
            
            with col_f2:
                selected_groups = st.multiselect(
                    "노드 그룹 필터", 
                    options=sorted(list(all_groups)), 
                    default=sorted(list(all_groups)),
                    key="graph_group_filter"
                )
                
            with col_f3:
                selected_relations = st.multiselect(
                    "관계 타입 필터", 
                    options=sorted(list(all_relations)), 
                    default=sorted(list(all_relations)),
                    key="graph_relation_filter"
                )
        
        # 3. 데이터 필터링 적용
        filtered_data = {"instances": {"nodes": [], "links": []}, "schema": {"nodes": [], "links": []}}
        
        for mode in ["instances", "schema"]:
            src_nodes = full_data.get(mode, {}).get("nodes", [])
            src_links = full_data.get(mode, {}).get("links", [])
            
            # 노드 필터링
            valid_node_ids = set()
            for node in src_nodes:
                # 그룹 필터
                if node.get("group", "Unknown") not in selected_groups:
                    continue
                
                # 검색어 필터
                if search_term:
                    search_lower = search_term.lower()
                    if search_lower not in node.get("id", "").lower() and \
                       search_lower not in node.get("label", "").lower():
                        continue
                
                filtered_data[mode]["nodes"].append(node)
                valid_node_ids.add(node.get("id"))
            
            # 엣지 필터링 (유효한 노드 간의 엣지 + 관계 필터)
            for link in src_links:
                if link.get("source") in valid_node_ids and \
                   link.get("target") in valid_node_ids and \
                   link.get("relation", "Unknown") in selected_relations:
                    filtered_data[mode]["links"].append(link)
    else:
        filtered_data = None

    # 범례는 graph_viewer와 graph_viewer_enhanced에서 동적으로 생성됩니다.
    # 하드코딩된 범례는 제거되었습니다 (실제 그래프 데이터와 불일치).

    # 그래프 뷰어 모드 선택
    viewer_mode = st.radio(
        "그래프 뷰어 모드",
        ["기본 뷰어 (Pyvis)", "강화 뷰어 (D3.js)"],
        horizontal=True
    )
    
    # 노드 클릭 콜백 함수
    def on_node_click_callback(node_id: str, node_label: str, node_data: dict):
        """노드 클릭 시 호출되는 콜백"""
        st.session_state.selected_node_info = {
            "id": node_id,
            "label": node_label,
            "data": node_data
        }
    
    # 그래프 시각화 (필터링된 데이터 전달)
    if viewer_mode == "기본 뷰어 (Pyvis)":
        render_graph(orchestrator.core, 
                     on_node_click=on_node_click_callback,
                     show_analysis=False,
                     graph_data=filtered_data)
    else:
        # 강화 뷰어 (D3.js 기반)
        use_reasoned = st.checkbox("추론된 그래프 사용", value=True)
        render_enhanced_graph(
            orchestrator.core,
            use_reasoned_graph=use_reasoned,
            on_node_click=on_node_click_callback,
            show_analysis=False,
            graph_data=filtered_data
        )
    
    # 선택된 노드 정보 표시
    if "selected_node_info" in st.session_state and st.session_state.selected_node_info:
        st.divider()
        node_info = st.session_state.selected_node_info
        render_node_info_panel(
            orchestrator.core,
            node_info.get("id", ""),
            node_info.get("label", "")
        )
    
    # 온톨로지 관계 설명 (그래프 탐색과 연계)
    st.divider()
    render_ontology_explainer(orchestrator.core.ontology_manager)

with tab3:
    render_ontology_dashboard_panel(orchestrator)

st.divider()
