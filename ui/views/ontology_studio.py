# ui/views/ontology_studio.py
# -*- coding: utf-8 -*-
"""
온톨로지 스튜디오
온톨로지 검증 및 관리 통합 플랫폼
"""
import streamlit as st
import sys
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

from core_pipeline.orchestrator import Orchestrator

st.set_page_config(page_title="온톨로지 스튜디오", layout="wide")

# 헤더
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0rem !important;
    }
    header[data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: none !important;
    }
    [data-testid="stDecoration"] {
        display: none;
    }
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        color: #e6edf3 !important;
    }
    .compact-header {
        background-color: #0e1117;
        border-bottom: 1px solid #30363d;
        padding-bottom: 5px;
        margin-bottom: 15px;
    }
    .header-title {
        font-family: 'Roboto Mono', monospace;
        font-size: 1.2rem;
        font-weight: 700;
        color: #2E9AFE;
        text-transform: uppercase;
    }
</style>
<div class="compact-header">
    <div class="header-title">온톨로지 스튜디오</div>
    <div style="font-size: 0.85rem; color: #8b949e;">
        온톨로지 검증 및 관리 통합 플랫폼
    </div>
</div>
""", unsafe_allow_html=True)

# 설정 파일 로드
def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

try:
    config = load_yaml("./config/global.yaml")
except Exception as e:
    st.error(f"설정 파일 로드 실패: {e}")
    st.stop()

# Orchestrator 초기화
if st.session_state.get("main_orchestrator_initialized", False):
    pass
elif "main_orchestrator" not in st.session_state:
    with st.spinner("시스템 초기화 중..."):
        try:
            st.session_state.main_orchestrator = Orchestrator(config, use_enhanced_ontology=True)
            st.session_state.main_orchestrator.initialize()
            st.session_state.main_orchestrator_initialized = True
        except Exception as e:
            st.error(f"시스템 초기화 실패: {e}")
            st.stop()
else:
    if hasattr(st.session_state.main_orchestrator, 'core') and \
       hasattr(st.session_state.main_orchestrator.core, '_initialized') and \
       st.session_state.main_orchestrator.core._initialized:
        st.session_state.main_orchestrator_initialized = True
    else:
        with st.spinner("시스템 초기화 중..."):
            try:
                st.session_state.main_orchestrator.initialize()
                st.session_state.main_orchestrator_initialized = True
            except Exception as e:
                st.error(f"시스템 초기화 실패: {e}")
                st.stop()

orchestrator = st.session_state.main_orchestrator

# 권장사항 알림 (상단에 표시)
if 'validation_recommendations' in st.session_state and st.session_state.validation_recommendations:
    unresolved = [r for r in st.session_state.validation_recommendations if not r.get('resolved', False)]
    if unresolved:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning(f"⚠️ **{len(unresolved)}개의 검증 권장사항**이 있습니다. **관계 관리** 탭에서 확인하세요.")
        with col2:
            if st.button("🔗 관계 관리 탭으로 이동", key="nav_to_rel_mgmt_main"):
                st.session_state.navigate_to_tab = "관계 관리"
                if unresolved:
                    st.session_state.navigate_to_subtab = unresolved[0].get('관련_서브탭', '관계 조회')
                st.info("👉 상단의 **관계 관리** 탭을 클릭하세요.")

# 메인 탭 구성 (워크플로우 관리 제거, 검증/관리 기능에 집중)
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏠 개요",
    "📐 스키마 관리",
    "🔗 관계 관리",
    "✅ 품질 보증",
    "📊 시각화",
    "🧠 추론",
    "📜 버전 관리",
    "🔄 피드백 및 개선"
])

with tab1:
    from ui.components.ontology_studio.overview import render_overview
    render_overview(orchestrator)

with tab2:
    from ui.components.ontology_studio.schema_manager import render_schema_manager
    render_schema_manager(orchestrator)

with tab3:
    from ui.components.ontology_studio.relationship_manager import render_relationship_manager
    render_relationship_manager(orchestrator)

with tab4:
    from ui.components.ontology_studio.quality_assurance import render_quality_assurance
    render_quality_assurance(orchestrator)

with tab5:
    from ui.components.ontology_studio.visualizer import render_visualizer
    render_visualizer(orchestrator)

with tab6:
    from ui.components.ontology_studio.inference_manager import render_inference_manager
    render_inference_manager(orchestrator)

with tab7:
    from ui.components.ontology_studio.version_control import render_version_control
    render_version_control(orchestrator)

with tab8:
    from ui.components.ontology_studio.feedback_improvement import render_feedback_improvement
    render_feedback_improvement(orchestrator)

