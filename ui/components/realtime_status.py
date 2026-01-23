# ui/components/realtime_status.py
# -*- coding: utf-8 -*-
"""
Realtime Status
실시간 상태 표시 컴포넌트
"""
import streamlit as st
from datetime import datetime
import time


def render_realtime_status(orchestrator):
    """실시간 상태 표시"""
    st.subheader("⚡ 실시간 상태 모니터링")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 데이터 변경 감지 상태
        if st.session_state.get("data_changed", False):
            st.warning("⚠️ 데이터 변경 감지됨")
            if st.button("🔄 추천 갱신", key="refresh_recommendations"):
                # 캐시 무효화 및 Agent 재실행
                global _cached_graph, _cached_data_hash
                _cached_graph = None
                _cached_data_hash = None
                st.session_state["data_changed"] = False
                st.session_state["last_update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.rerun()
        else:
            st.success("✅ 데이터 최신 상태")
    
    with col2:
        # 마지막 업데이트 시간
        last_update = st.session_state.get("last_update_time")
        if last_update:
            st.caption(f"마지막 업데이트: {last_update}")
        else:
            st.caption("업데이트 이력 없음")
    
    with col3:
        # 자동 갱신 토글
        auto_refresh = st.checkbox(
            "자동 갱신 활성화", 
            value=st.session_state.get("auto_refresh", False),
            key="auto_refresh_toggle"
        )
        st.session_state["auto_refresh"] = auto_refresh
        
        if auto_refresh:
            # 주기적 체크
            if "last_check_time" not in st.session_state:
                st.session_state["last_check_time"] = time.time()
            
            current_time = time.time()
            if current_time - st.session_state["last_check_time"] > 5:
                # 데이터 변경 체크
                try:
                    changes = orchestrator.core.data_watcher.force_check()
                    if any(changes.values()):
                        st.session_state["data_changed"] = True
                        st.session_state["last_update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.rerun()
                except Exception as e:
                    st.warning(f"데이터 체크 실패: {e}")
                
                st.session_state["last_check_time"] = current_time


