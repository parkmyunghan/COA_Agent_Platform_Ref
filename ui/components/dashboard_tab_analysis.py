# ui/components/dashboard_tab_analysis.py
# -*- coding: utf-8 -*-
"""
탭 2: 추천 근거 분석
"""
import streamlit as st
from datetime import datetime
from ui.components.reasoning_explanation import render_reasoning_explanation
from ui.components.recommendation_visualization import render_recommendation_breakdown
from ui.components.coa_execution_plan import render_coa_execution_plan
from ui.components.ontology_explainer import render_ontology_explainer
from ui.components.report_generator_enhanced import render_report_generator
from ui.components.approval_workflow import render_approval_workflow
from ui.components.notifications_panel import render_notifications, render_active_users


def render_analysis_tab(orchestrator):
    """탭 2: 추천 근거 분석"""
    
    st.header("추천 근거 분석")
    st.markdown("추천된 방책의 상세 근거 분석")
    
    # Agent 결과 확인 (대시보드 자동 실행 결과 또는 채팅 인터페이스 결과)
    agent_result = st.session_state.get("dashboard_agent_result")
    situation_info = st.session_state.get("dashboard_situation_info")
    
    # 폴백: 채팅 인터페이스 결과 확인
    if not agent_result and "messages_v2" in st.session_state and st.session_state.messages_v2:
        last_message = st.session_state.messages_v2[-1]
        if last_message.get("role") == "assistant":
            agent_result = last_message.get("metadata", {}).get("agent_result")
            if agent_result:
                situation_info = agent_result.get("situation_info")
    
    if not agent_result:
        st.info("💡 먼저 **탭 1: 상황 입력 및 추천**에서 Agent를 실행하여 추천 결과를 생성해주세요.")
        return
    
    # 추론 과정 상세
    with st.expander("추론 과정 상세", expanded=True):
        render_reasoning_explanation(agent_result, orchestrator.core)
    
    st.divider()
    
    # 점수 Breakdown
    recommendations = agent_result.get("recommendations", [])
    if recommendations:
        st.subheader("점수 Breakdown")
        render_recommendation_breakdown(agent_result)
    
    st.divider()
    
    # 🔥 NEW: 교리 참조 표시 (상위 추천에만)
    if recommendations:
        first_rec = recommendations[0]
        if first_rec.get('doctrine_references'):
            st.subheader("📚 교리 참조")
            from ui.components.doctrine_reference_display import render_doctrine_references, render_doctrine_based_explanation
            
            render_doctrine_references(first_rec)
            
            # 교리 기반 설명 표시
            render_doctrine_based_explanation(
                coa_recommendation=first_rec,
                situation_info=situation_info,
                mett_c_analysis=agent_result.get("situation_analysis", {}).get("mett_c", {})
            )
            
            st.divider()
    
    # 방책 실행 계획
    if recommendations:
        st.subheader("방책 실행 계획")
        render_coa_execution_plan(recommendations[0], agent_result.get("situation_info"))
    
    st.divider()
    
    # 온톨로지 관계
    with st.expander("온톨로지 관계", expanded=False):
        render_ontology_explainer(orchestrator.core.ontology_manager)
    
    st.divider()
    
    # 보고서 생성
    render_report_generator(agent_result, agent_result.get("situation_info"))
    
    st.divider()
    
    # 승인 워크플로우
    recommendations = agent_result.get("recommendations", [])
    if recommendations:
        recommendation_id = recommendations[0].get("recommendation_id") or f"REC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.subheader("승인 워크플로우")
        render_approval_workflow(recommendation_id)
    
    st.divider()
    
    # 알림 및 활성 사용자
    col1, col2 = st.columns([2, 1])
    with col1:
        render_notifications(auto_refresh=False)
    with col2:
        render_active_users()

