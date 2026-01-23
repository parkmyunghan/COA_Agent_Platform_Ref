# ui/components/ontology_studio/visualizer.py
# -*- coding: utf-8 -*-
"""
시각화 컴포넌트
온톨로지 구조 시각화
"""
import streamlit as st
from ui.components.ontology_dashboard_panel import (
    _get_core_schema_graph,
    _get_lineage_graph
)
from ui.components.table_column_relationship_viewer import render_table_column_relationship_viewer

def render_visualizer(orchestrator):
    """시각화 렌더링"""
    st.markdown("### 📊 시각화 (Visualization)")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if not ontology_manager or not ontology_manager.graph:
        st.warning("⚠️ 온톨로지 그래프가 없습니다.")
        return
    
    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "구조 다이어그램",
        "데이터 계보",
        "네트워크 그래프",
        "인터랙티브 탐색"
    ])
    
    with sub_tab1:
        _render_structure_diagram()
    
    with sub_tab2:
        _render_lineage_diagram(orchestrator)
    
    with sub_tab3:
        _render_network_graph(orchestrator)
    
    with sub_tab4:
        _render_interactive_exploration(orchestrator)

def _render_structure_diagram():
    """구조 다이어그램"""
    st.markdown("#### 🗺️ 핵심 클래스 관계도")
    st.info("💡 전체 온톨로지가 아닌, **방책 결심 지원을 위한 핵심 클래스** 관계도입니다.")
    
    core_schema_dot = _get_core_schema_graph()
    st.graphviz_chart(core_schema_dot, use_container_width=True)

def _render_lineage_diagram(orchestrator):
    """데이터 계보"""
    st.markdown("#### 📊 데이터-결심 연계 계보")
    st.info("💡 **실제 데이터 필드**가 어떻게 **온톨로지**로 매핑되고, 최종 **의사결정**에 기여하는지 보여주는 상세 흐름도입니다.")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    lineage_dot = _get_lineage_graph(ontology_manager)
    
    try:
        st.graphviz_chart(lineage_dot, use_container_width=True)
    except Exception as e:
        st.error(f"다이어그램 렌더링 오류: {str(e)}")

def _render_network_graph(orchestrator):
    """네트워크 그래프"""
    st.markdown("#### 🕸️ 테이블 관계 매핑")
    st.info("💡 **모든 테이블의 컬럼들이 다른 테이블들과 맺는 관계**를 인터랙티브 네트워크 그래프로 시각화합니다.")
    
    render_table_column_relationship_viewer(orchestrator)

def _render_interactive_exploration(orchestrator):
    """인터랙티브 탐색"""
    st.markdown("#### 🔍 인터랙티브 그래프 탐색")
    st.info("💡 전체 그래프를 인터랙티브하게 탐색할 수 있습니다.")
    
    # 기존 graph_viewer 재사용
    from ui.components.graph_viewer import render_graph
    render_graph(orchestrator.core, show_analysis=True)

