# ui/components/realtime_simulator.py
# -*- coding: utf-8 -*-
"""
Realtime Simulator
실시간 상황 시뮬레이터 컴포넌트
"""
import streamlit as st
from datetime import datetime


def render_realtime_simulator(orchestrator):
    """실시간 시뮬레이터"""
    st.subheader("⚡ 실시간 상황 시뮬레이터")
    st.caption("개발/테스트용: 실시간 데이터 변경 시뮬레이션")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 위협 상황 업데이트")
        threat_id = st.selectbox(
            "위협 ID", 
            ["THREAT001", "THREAT002", "THREAT003"],
            key="simulator_threat_id"
        )
        new_threat_level = st.slider(
            "새 위협 수준", 0, 100, 70,
            key="simulator_threat_level"
        )
        
        if st.button("🔄 위협 상황 업데이트", key="update_threat"):
            with st.spinner("업데이트 중..."):
                try:
                    result = orchestrator.core.event_stream.simulate_threat_update(
                        threat_id, new_threat_level / 100.0
                    )
                    
                    if result["processed"]:
                        st.success("✅ 업데이트 완료")
                        st.session_state["data_changed"] = True
                        st.session_state["last_update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 영향받는 추천 표시
                        if result.get("affected_recommendations"):
                            st.warning(f"⚠️ {len(result['affected_recommendations'])}개 추천이 영향받음")
                            st.info("💡 추천을 다시 실행하세요.")
                    else:
                        st.error(f"❌ 업데이트 실패: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"업데이트 오류: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    with col2:
        st.markdown("#### 자동 시뮬레이션")
        auto_simulate = st.checkbox("자동 시뮬레이션", value=False, key="auto_simulate")
        
        if auto_simulate:
            interval = st.slider("업데이트 간격 (초)", 5, 60, 10, key="sim_interval")
            
            if st.button("시작", key="start_auto_sim"):
                st.session_state["auto_simulation_running"] = True
                st.session_state["simulation_interval"] = interval
                st.info(f"자동 시뮬레이션 시작 (간격: {interval}초)")
                st.warning("⚠️ Streamlit의 제한으로 실제 자동 실행은 지원되지 않습니다. 수동으로 버튼을 클릭하세요.")
            
            if st.session_state.get("auto_simulation_running"):
                if st.button("중지", key="stop_auto_sim"):
                    st.session_state["auto_simulation_running"] = False
                    st.info("자동 시뮬레이션 중지")
        
        # 이벤트 히스토리
        if orchestrator.core.event_stream.event_history:
            with st.expander("📋 이벤트 히스토리 (최근 10개)"):
                for i, event in enumerate(reversed(orchestrator.core.event_stream.event_history[-10:]), 1):
                    event_time = event.get('timestamp', 'N/A')
                    event_type = event.get('type', 'unknown')
                    entity_id = event.get('entity_id', 'N/A')
                    new_value = event.get('new_value', 'N/A')
                    st.write(f"{i}. [{event_time}] {event_type}: {entity_id} = {new_value}")


