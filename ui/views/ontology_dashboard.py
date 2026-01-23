# ui/views/ontology_dashboard.py
# -*- coding: utf-8 -*-
"""
Ontology Insight Dashboard
Comprehensive dashboard for verifying ontology structure, data integrity, and reasoning capabilities.
Refactored to use the reusable ontology_dashboard_panel component.
"""
import streamlit as st
import sys
import yaml
from pathlib import Path

# Set base path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.orchestrator import Orchestrator
from ui.components.ontology_dashboard_panel import render_ontology_dashboard_panel

st.set_page_config(page_title="온톨로지 인사이트", layout="wide")

# CSS Load (Global for Page)
st.markdown("""
<style>
    /* Mimic compact header style */
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
    
    /* Compact header style */
    .compact-header {
        background-color: #0e1117;
        border-bottom: 1px solid #30363d;
        padding-bottom: 5px;
        margin-bottom: 15px;
        display: flex;
        flex-wrap: wrap;
        width: 100%;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        font-family: 'Roboto Mono', monospace; 
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #2E9AFE;
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
        Ontology Insight
    </div>
    <div class="header-subtitle">
        온톨로지 구조/건전성/추론 종합 분석 (Component-based)
    </div>
</div>
""", unsafe_allow_html=True)

# Config Loader
def load_config():
    try:
        with open("./config/global.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"설정 로드 실패: {e}")
        return {}

# Orchestrator Initialization
if "main_orchestrator" not in st.session_state:
    with st.spinner("시스템 엔진 초기화 중..."):
        config = load_config()
        st.session_state.main_orchestrator = Orchestrator(config, use_enhanced_ontology=True)
        st.session_state.main_orchestrator.initialize()

orchestrator = st.session_state.main_orchestrator

# Render the reusable dashboard panel
render_ontology_dashboard_panel(orchestrator)
