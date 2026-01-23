# ui/components/dashboard_tab_pipeline.py
# -*- coding: utf-8 -*-
"""
탭 3: 파이프라인 상태
"""
import streamlit as st
from ui.components.pipeline_status import render_pipeline_status
from ui.components.benchmark_panel import render_benchmark_panel
from ui.components.data_quality_checker import render_data_quality_checker


def render_pipeline_tab(orchestrator, config):
    """탭 3: 파이프라인 상태"""
    
    st.header("파이프라인 상태")
    st.markdown("시스템 상태 및 성능 모니터링")
    
    # 초기 설정 완료 여부 확인
    st.subheader("초기 설정 상태")
    
    # 각 단계별 완료 상태 확인
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 1단계: 데이터 관리
        data_loaded = orchestrator.core.data_manager is not None
        if data_loaded:
            try:
                data = orchestrator.core.data_manager.load_all()
                data_status = "✅ 완료" if data else "⚠️ 데이터 없음"
            except:
                data_status = "⚠️ 오류"
        else:
            data_status = "❌ 미완료"
        st.markdown(f"**1단계: 데이터 관리** - {data_status}")
    
    with col2:
        # 2단계: 온톨로지 생성
        graph = orchestrator.core.ontology_manager.graph
        if graph is not None:
            try:
                triples_count = len(list(graph.triples((None, None, None))))
                graph_status = f"✅ 완료 ({triples_count} triples)" if triples_count > 0 else "⚠️ 그래프 비어있음"
            except:
                graph_status = "⚠️ 오류"
        else:
            graph_status = "❌ 미완료"
        st.markdown(f"**2단계: 온톨로지 생성** - {graph_status}")
    
    with col3:
        # 4단계: RAG 인덱스 구성
        rag_available = orchestrator.core.rag_manager.is_available()
        if rag_available:
            try:
                index_status = "✅ 완료"
            except:
                index_status = "⚠️ 오류"
        else:
            index_status = "❌ 미완료"
        st.markdown(f"**4단계: RAG 인덱스 구성** - {index_status}")
    
    st.info("💡 미완료된 단계는 좌측 사이드바의 해당 페이지에서 완료하세요.")
    
    st.divider()
    
    # 파이프라인 상태
    st.subheader("파이프라인 상태")
    render_pipeline_status(config, show_diagram=False)
    
    st.divider()
    
    # 성능 벤치마크
    st.subheader("성능 벤치마크")
    render_benchmark_panel(orchestrator)
    
    st.divider()
    
    # 데이터 품질 검증
    st.subheader("데이터 품질 검증")
    render_data_quality_checker(orchestrator.core.data_manager, config)


