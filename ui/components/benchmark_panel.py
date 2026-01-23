# ui/components/benchmark_panel.py
# -*- coding: utf-8 -*-
"""
성능 벤치마크 패널
시스템 성능 측정 및 목표 성능과 비교
"""
import streamlit as st
import pandas as pd
import time
from typing import Dict, Callable, Optional
from functools import wraps


# 목표 성능 (밀리초)
TARGET_PERFORMANCE = {
    "데이터 로드": 1000,  # 1초
    "온톨로지 구축": 5000,  # 5초
    "RAG 검색": 500,  # 0.5초
    "방책 추천": 3000,  # 3초
    "LLM 응답 생성": 2000,  # 2초
    "전체 파이프라인": 12000  # 12초
}


def measure_time(func: Callable, *args, **kwargs) -> Dict:
    """
    함수 실행 시간 측정
    
    Args:
        func: 측정할 함수
        *args, **kwargs: 함수 인자
        
    Returns:
        {"time_ms": 실행 시간(ms), "result": 함수 결과}
    """
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed_time = (time.time() - start_time) * 1000  # 밀리초로 변환
        return {
            "time_ms": elapsed_time,
            "result": result,
            "success": True
        }
    except Exception as e:
        elapsed_time = (time.time() - start_time) * 1000
        return {
            "time_ms": elapsed_time,
            "result": None,
            "success": False,
            "error": str(e)
        }


def render_benchmark_panel(orchestrator):
    """
    성능 벤치마크 패널 렌더링
    
    Args:
        orchestrator: Orchestrator 인스턴스
    """
    st.subheader("⚡ 성능 벤치마크")
    
    st.info("""
    💡 **성능 벤치마크:** 각 단계별 처리 시간을 측정하고 목표 성능과 비교합니다.
    """)
    
    # 벤치마크 실행 버튼
    if st.button("🚀 벤치마크 실행", type="primary"):
        with st.spinner("벤치마크 실행 중..."):
            benchmark_results = run_benchmarks(orchestrator)
            render_benchmark_results(benchmark_results)
    
    # 저장된 벤치마크 결과 표시
    if "benchmark_results" in st.session_state:
        render_benchmark_results(st.session_state.benchmark_results)


def run_benchmarks(orchestrator) -> Dict:
    """
    벤치마크 실행
    
    Args:
        orchestrator: Orchestrator 인스턴스
        
    Returns:
        벤치마크 결과 딕셔너리
    """
    results = {}
    
    # 1. 데이터 로드 벤치마크
    st.write("📊 데이터 로드 측정 중...")
    data_result = measure_time(orchestrator.core.data_manager.load_all)
    results["데이터 로드"] = data_result
    
    # 2. 온톨로지 구축 벤치마크
    if data_result["success"] and data_result["result"]:
        st.write("🕸 온톨로지 구축 측정 중...")
        data = data_result["result"]
        ontology_result = measure_time(
            orchestrator.core.ontology_manager.build_from_data,
            data
        )
        results["온톨로지 구축"] = ontology_result
    
    # 3. RAG 검색 벤치마크
    if orchestrator.core.rag_manager.is_available():
        st.write("🔍 RAG 검색 측정 중...")
        test_query = "적군 위협 상황"
        rag_result = measure_time(
            orchestrator.core.rag_manager.retrieve_with_context,
            test_query,
            5
        )
        results["RAG 검색"] = rag_result
    
    # 4. 방책 추천 벤치마크 (간단한 시나리오)
    st.write("🤖 방책 추천 측정 중...")
    try:
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        agent = EnhancedDefenseCOAAgent(orchestrator.core)
        
        test_context = {
            "threat_level": 0.7,
            "situation_id": "BENCHMARK_TEST"
        }
        
        coa_result = measure_time(
            agent.execute_reasoning,
            situation_id="BENCHMARK_TEST",
            use_palantir_mode=True
        )
        results["방책 추천"] = coa_result
    except Exception as e:
        results["방책 추천"] = {
            "time_ms": 0,
            "success": False,
            "error": str(e)
        }
    
    # 5. LLM 응답 생성 벤치마크
    if orchestrator.core.llm_manager.is_available():
        st.write("💬 LLM 응답 생성 측정 중...")
        test_prompt = "적군 침입에 대한 방책을 추천해주세요."
        llm_result = measure_time(
            orchestrator.core.llm_manager.generate,
            test_prompt,
            max_tokens=100
        )
        results["LLM 응답 생성"] = llm_result
    
    # 전체 파이프라인 시간 계산
    total_time = sum(r.get("time_ms", 0) for r in results.values() if r.get("success"))
    results["전체 파이프라인"] = {
        "time_ms": total_time,
        "success": True
    }
    
    # 결과 저장
    st.session_state.benchmark_results = results
    
    return results


def render_benchmark_results(results: Dict):
    """벤치마크 결과 렌더링"""
    if not results:
        st.warning("벤치마크 결과가 없습니다.")
        return
    
    # 결과 테이블 생성
    benchmark_data = []
    for step_name, result in results.items():
        if step_name == "전체 파이프라인":
            continue
        
        time_ms = result.get("time_ms", 0)
        success = result.get("success", False)
        target_time = TARGET_PERFORMANCE.get(step_name, 0)
        
        status = "✅" if success else "❌"
        performance_status = "✅ 목표 달성" if time_ms <= target_time else "⚠️ 목표 미달성"
        
        benchmark_data.append({
            "단계": step_name,
            "실행 시간 (ms)": f"{time_ms:.2f}",
            "목표 시간 (ms)": f"{target_time:.2f}",
            "상태": status,
            "성능": performance_status,
            "차이": f"{time_ms - target_time:+.2f} ms"
        })
    
    # 전체 파이프라인 추가
    if "전체 파이프라인" in results:
        total_result = results["전체 파이프라인"]
        total_time = total_result.get("time_ms", 0)
        target_total = TARGET_PERFORMANCE.get("전체 파이프라인", 0)
        
        benchmark_data.append({
            "단계": "**전체 파이프라인**",
            "실행 시간 (ms)": f"**{total_time:.2f}**",
            "목표 시간 (ms)": f"**{target_total:.2f}**",
            "상태": "✅" if total_result.get("success") else "❌",
            "성능": "✅ 목표 달성" if total_time <= target_total else "⚠️ 목표 미달성",
            "차이": f"**{total_time - target_total:+.2f} ms**"
        })
    
    df = pd.DataFrame(benchmark_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    # 시각화
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        # 실제 시간 vs 목표 시간 비교 차트
        chart_data = []
        for step_name, result in results.items():
            if step_name == "전체 파이프라인":
                continue
            time_ms = result.get("time_ms", 0)
            target_time = TARGET_PERFORMANCE.get(step_name, 0)
            
            chart_data.append({
                "단계": step_name,
                "실행 시간": time_ms,
                "목표 시간": target_time
            })
        
        if chart_data:
            chart_df = pd.DataFrame(chart_data)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=chart_df["단계"],
                y=chart_df["실행 시간"],
                name="실행 시간",
                marker_color='lightblue'
            ))
            fig.add_trace(go.Bar(
                x=chart_df["단계"],
                y=chart_df["목표 시간"],
                name="목표 시간",
                marker_color='lightgreen'
            ))
            
            fig.update_layout(
                title="실행 시간 vs 목표 시간 비교",
                xaxis_title="단계",
                yaxis_title="시간 (ms)",
                barmode='group',
                xaxis_tickangle=-45
            )
            
            st.plotly_chart(fig, width='stretch')
    except ImportError:
        st.info("Plotly가 설치되지 않아 차트를 표시할 수 없습니다.")
    
    # 개선 제안
    suggest_improvements(results)


def suggest_improvements(results: Dict):
    """성능 개선 제안"""
    improvements = []
    
    for step_name, result in results.items():
        if step_name == "전체 파이프라인":
            continue
        
        time_ms = result.get("time_ms", 0)
        target_time = TARGET_PERFORMANCE.get(step_name, 0)
        
        if time_ms > target_time:
            ratio = time_ms / target_time if target_time > 0 else 0
            
            if step_name == "데이터 로드":
                improvements.append({
                    "단계": step_name,
                    "문제": f"목표 시간({target_time}ms) 대비 {ratio:.1f}배 느림",
                    "제안": "데이터 캐싱 적용, 필요한 테이블만 선택적 로드"
                })
            elif step_name == "온톨로지 구축":
                improvements.append({
                    "단계": step_name,
                    "문제": f"목표 시간({target_time}ms) 대비 {ratio:.1f}배 느림",
                    "제안": "온톨로지 그래프 캐싱, 증분 업데이트 활용"
                })
            elif step_name == "RAG 검색":
                improvements.append({
                    "단계": step_name,
                    "문제": f"목표 시간({target_time}ms) 대비 {ratio:.1f}배 느림",
                    "제안": "FAISS 인덱스 최적화, 검색 결과 캐싱"
                })
            elif step_name == "방책 추천":
                improvements.append({
                    "단계": step_name,
                    "문제": f"목표 시간({target_time}ms) 대비 {ratio:.1f}배 느림",
                    "제안": "SPARQL 쿼리 최적화, 불필요한 계산 제거"
                })
            elif step_name == "LLM 응답 생성":
                improvements.append({
                    "단계": step_name,
                    "문제": f"목표 시간({target_time}ms) 대비 {ratio:.1f}배 느림",
                    "제안": "토큰 수 제한, 응답 스트리밍 적용"
                })
    
    if improvements:
        st.divider()
        st.subheader("💡 성능 개선 제안")
        
        for improvement in improvements:
            with st.expander(f"⚠️ {improvement['단계']} 개선 필요", expanded=False):
                st.write(f"**문제:** {improvement['문제']}")
                st.write(f"**제안:** {improvement['제안']}")
    else:
        st.success("✅ 모든 단계가 목표 성능을 달성했습니다!")


