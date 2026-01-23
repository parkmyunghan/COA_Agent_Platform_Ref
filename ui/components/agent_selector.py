# ui/components/agent_selector.py
# -*- coding: utf-8 -*-
"""
Agent 선택 컴포넌트
"""
import streamlit as st


def render_agent_selector(agents_list):
    """Agent 선택 UI"""
    st.subheader("Agent 선택")
    
    if not agents_list:
        st.warning("등록된 Agent가 없습니다.")
        return None
    
    agent_names = [a.get("name", "Unknown") for a in agents_list]
    agent_descriptions = {
        a.get("name", "Unknown"): a.get("description", "No description")
        for a in agents_list
    }
    
    # Agent 선택
    selected_agent = st.selectbox(
        "실행할 Agent 선택",
        agent_names,
        key="agent_selector"
    )
    
    # Agent 설명 표시
    # Agent 설명 표시 (사용자 요청으로 제거)
    # if selected_agent and selected_agent in agent_descriptions:
    #     st.info(f"📝 {agent_descriptions[selected_agent]}")
    
    # Agent 상태 표시
    if "agent_status" in st.session_state:
        status = st.session_state.agent_status.get(selected_agent, {})
        if status:
            col1, col2 = st.columns(2)
            with col1:
                if status.get("status") == "completed":
                    st.success("✅ 실행 완료")
                elif status.get("status") == "running":
                    st.info("🔄 실행 중...")
                else:
                    st.warning("⚠️ 대기 중")
            
            with col2:
                if "timestamp" in status:
                    st.caption(f"마지막 실행: {status['timestamp']}")
    
    return selected_agent














