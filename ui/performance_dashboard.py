# ui/performance_dashboard.py
# -*- coding: utf-8 -*-
"""
Execution Timeline & Performance Dashboard
단계별 처리시간, 토큰수, GPU 메모리 사용률 시각화
"""
import streamlit as st
import pandas as pd
from core_pipeline.logger import get_performance_logger


def render_performance_dashboard():
    """성능 대시보드 렌더링"""
    st.header("📊 Performance Dashboard")
    
    logger = get_performance_logger()
    
    # 로그 레벨 필터
    log_level = st.selectbox(
        "로그 레벨",
        ["ALL", "INFO", "PERF", "ERROR"],
        key="perf_log_level"
    )
    
    # 최근 로그 가져오기
    recent_logs = logger.get_recent_logs(n=20)
    
    if not recent_logs:
        st.info("성능 로그가 없습니다. Agent를 실행하면 로그가 기록됩니다.")
        return
    
    # 데이터프레임 생성
    df_data = []
    for log in recent_logs:
        df_data.append({
            "단계": log.get("step", "Unknown"),
            "시간(ms)": f"{log.get('time_ms', 0):.2f}",
            "토큰수": log.get("tokens", "-") or "-",
            "GPU메모리(MB)": f"{log.get('gpu_memory_mb', 0):.2f}" if log.get("gpu_memory_mb") else "-",
            "타임스탬프": log.get("timestamp", "")[:19] if log.get("timestamp") else ""
        })
    
    df = pd.DataFrame(df_data)
    
    # 테이블 표시
    st.subheader("📋 실행 로그")
    st.dataframe(df, width='stretch', hide_index=True)
    
    # 차트 시각화
    if len(recent_logs) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⏱️ 단계별 실행 시간")
            time_data = {
                "단계": [log.get("step", "Unknown") for log in recent_logs],
                "시간(ms)": [log.get("time_ms", 0) for log in recent_logs]
            }
            time_df = pd.DataFrame(time_data)
            st.bar_chart(time_df.set_index("단계"))
        
        with col2:
            st.subheader("💾 GPU 메모리 사용량")
            gpu_logs = [log for log in recent_logs if log.get("gpu_memory_mb")]
            if gpu_logs:
                gpu_data = {
                    "단계": [log.get("step", "Unknown") for log in gpu_logs],
                    "GPU메모리(MB)": [log.get("gpu_memory_mb", 0) for log in gpu_logs]
                }
                gpu_df = pd.DataFrame(gpu_data)
                st.line_chart(gpu_df.set_index("단계"))
            else:
                st.info("GPU 메모리 데이터가 없습니다.")
        
        # 요약 통계
        st.subheader("📈 성능 요약")
        summary = logger.get_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 실행 시간", f"{summary.get('total_time_ms', 0):.2f} ms")
        with col2:
            st.metric("총 토큰 수", summary.get("total_tokens", 0))
        with col3:
            avg_gpu = summary.get("avg_gpu_memory_mb")
            st.metric("평균 GPU 메모리", f"{avg_gpu:.2f} MB" if avg_gpu else "N/A")
        with col4:
            st.metric("실행 단계 수", summary.get("step_count", 0))
    
    # 로그 초기화 버튼
    if st.button("🗑️ 로그 초기화"):
        logger.clear()
        st.rerun()









