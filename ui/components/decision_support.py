# ui/components/decision_support.py
# -*- coding: utf-8 -*-
"""
Decision Support
대화형 의사결정 지원 컴포넌트
"""
import streamlit as st
import json
from datetime import datetime


def render_decision_support(orchestrator, agent_result):
    """의사결정 지원 패널"""
    if not agent_result:
        return
    
    st.subheader("🎯 의사결정 지원")
    
    # 1. 추천 변경 이력
    if agent_result.get("change_detected"):
        st.warning("⚠️ 상황 변화 감지됨")
        with st.expander("변경 사항 상세", expanded=True):
            change_summary = agent_result.get("change_summary", {})
            change_info = agent_result.get("change_info", {})
            
            col1, col2 = st.columns(2)
            with col1:
                threat_change = change_info.get('threat_change', 0)
                threat_change_pct = change_info.get('threat_change_pct', 0)
                st.metric(
                    "위협 수준 변화",
                    f"{threat_change:+.2f}",
                    delta=f"{threat_change_pct:.1f}%"
                )
            with col2:
                if change_summary.get("coa_changed"):
                    st.warning("⚠️ 최고 추천 방책 변경됨")
                else:
                    st.success("✅ 최고 추천 방책 유지")
            
            if change_summary:
                st.json(change_summary)
    
    # 2. 이전 추천과 비교
    if agent_result.get("previous_recommendation"):
        if st.button("📊 이전 추천과 비교", key="compare_recommendations"):
            previous = agent_result.get("previous_recommendation")
            render_comparison_view(previous, agent_result)
    
    # 3. "What if" 시나리오
    with st.expander("🔮 시나리오 분석", expanded=False):
        current_threat = agent_result.get("situation_info", {}).get("심각도", agent_result.get("situation_info", {}).get("위협수준", 0.7))
        if isinstance(current_threat, str):
            try:
                current_threat = float(str(current_threat).replace(',', ''))
            except (ValueError, TypeError):
                current_threat = 0.7
        
        scenario_threat = st.slider(
            "위협 수준 변경", 0, 100, 
            value=int(current_threat * 100),
            key="scenario_threat"
        )
        
        if st.button("시나리오 분석 실행", key="run_scenario"):
            with st.spinner("시나리오 분석 중..."):
                # 시나리오 기반 재추천
                scenario_result = run_scenario_analysis(
                    orchestrator, scenario_threat / 100.0, agent_result
                )
                if scenario_result:
                    render_scenario_comparison(agent_result, scenario_result)
    
    # 4. 추천 근거 시각화
    if agent_result.get("recommendations"):
        with st.expander("📊 추천 근거 상세", expanded=False):
            render_recommendation_breakdown(agent_result["recommendations"][0])


def render_comparison_view(previous, current):
    """추천 비교 뷰"""
    st.subheader("📊 추천 비교")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 이전 추천")
        if previous.get("recommendations"):
            prev_rec = previous["recommendations"][0]
            st.write(f"**방책**: {prev_rec.get('방책명', prev_rec.get('coa_name', 'N/A'))}")
            st.write(f"**점수**: {prev_rec.get('최종점수', prev_rec.get('score', 0)):.2f}")
            prev_threat = previous.get('situation_info', {}).get('심각도', previous.get('situation_info', {}).get('위협수준', 0))
            st.write(f"**위협 수준**: {prev_threat:.2f}")
    
    with col2:
        st.markdown("#### 현재 추천")
        if current.get("recommendations"):
            curr_rec = current["recommendations"][0]
            st.write(f"**방책**: {curr_rec.get('방책명', curr_rec.get('coa_name', 'N/A'))}")
            st.write(f"**점수**: {curr_rec.get('최종점수', curr_rec.get('score', 0)):.2f}")
            curr_threat = current.get('situation_info', {}).get('심각도', current.get('situation_info', {}).get('위협수준', 0))
            st.write(f"**위협 수준**: {curr_threat:.2f}")


def run_scenario_analysis(orchestrator, scenario_threat, base_result):
    """시나리오 분석 실행"""
    try:
        # 시나리오 기반 재추천
        situation_info = base_result.get("situation_info", {}).copy()
        situation_info["심각도"] = scenario_threat
        
        # Agent 재실행
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        
        scenario_result = agent.execute_reasoning(
            situation_id=base_result.get("situation_id"),
            use_palantir_mode=True,
            enable_rag_search=True
        )
        
        return scenario_result
    except Exception as e:
        st.error(f"시나리오 분석 실패: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_scenario_comparison(base_result, scenario_result):
    """시나리오 비교"""
    if not scenario_result:
        st.warning("시나리오 분석 실패")
        return
    
    st.subheader("시나리오 분석 결과")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 현재 상황")
        if base_result.get("recommendations"):
            base_rec = base_result["recommendations"][0]
            st.write(f"**방책**: {base_rec.get('방책명', base_rec.get('coa_name', 'N/A'))}")
            st.write(f"**점수**: {base_rec.get('최종점수', base_rec.get('score', 0)):.2f}")
    
    with col2:
        st.markdown("#### 시나리오 상황")
        if scenario_result.get("recommendations"):
            scenario_rec = scenario_result["recommendations"][0]
            st.write(f"**방책**: {scenario_rec.get('방책명', scenario_rec.get('coa_name', 'N/A'))}")
            st.write(f"**점수**: {scenario_rec.get('최종점수', scenario_rec.get('score', 0)):.2f}")
            
            # 점수 변화
            base_score = base_rec.get('최종점수', base_rec.get('score', 0)) if base_result.get("recommendations") else 0
            scenario_score = scenario_rec.get('최종점수', scenario_rec.get('score', 0))
            score_diff = scenario_score - base_score
            
            if score_diff > 0:
                st.success(f"점수 증가: +{score_diff:.2f}")
            elif score_diff < 0:
                st.error(f"점수 감소: {score_diff:.2f}")
            else:
                st.info("점수 변화 없음")


def render_recommendation_breakdown(recommendation):
    """추천 근거 breakdown"""
    score_breakdown = recommendation.get("score_breakdown", {})
    
    if not score_breakdown:
        st.info("점수 breakdown 정보가 없습니다.")
        return
    
    st.markdown("#### 6개 요소 점수 breakdown")
    
    # 테이블 형식
    import pandas as pd
    breakdown_data = {
        "요소": ["위협 수준", "자원 가용성", "방어 자산 능력", "환경 적합성", "과거 성공률", "체인 점수"],
        "점수": [
            score_breakdown.get("threat", 0),
            score_breakdown.get("resources", 0),
            score_breakdown.get("assets", 0),
            score_breakdown.get("environment", 0),
            score_breakdown.get("historical", 0),
            score_breakdown.get("chain", 0)
        ],
        "가중치": [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]
    }
    
    df = pd.DataFrame(breakdown_data)
    df["가중 점수"] = df["점수"] * df["가중치"]
    
    # 테이블
    st.dataframe(df, width='stretch')
    
    # METT-C 점수 (있는 경우)
    mett_c_scores = score_breakdown.get("mett_c") or recommendation.get("mett_c")
    if mett_c_scores:
        st.divider()
        st.markdown("#### METT-C 종합 평가")
        
        mett_c_data = {
            "요소": ["🎯 임무", "⚠️ 적군", "🌍 지형", "👥 부대", "🏘️ 민간인", "⏰ 시간"],
            "점수": [
                mett_c_scores.get("mission", 0),
                mett_c_scores.get("enemy", 0),
                mett_c_scores.get("terrain", 0),
                mett_c_scores.get("troops", 0),
                mett_c_scores.get("civilian", 0),
                mett_c_scores.get("time", 0)
            ],
            "가중치": [0.20, 0.20, 0.15, 0.15, 0.15, 0.15]
        }
        
        mett_c_df = pd.DataFrame(mett_c_data)
        mett_c_df["가중 점수"] = mett_c_df["점수"] * mett_c_df["가중치"]
        
        # 경고 표시
        civilian_score = mett_c_scores.get("civilian", 1.0)
        time_score = mett_c_scores.get("time", 1.0)
        
        if civilian_score < 0.3 or time_score == 0.0:
            st.warning("⚠️ 민간인 보호 또는 시간 제약에 문제가 있습니다. 상세 정보를 확인하세요.")
        
        st.dataframe(mett_c_df, width='stretch')
        
        # METT-C 종합 점수
        mett_c_total = mett_c_scores.get("total", 0)
        st.metric("METT-C 종합 점수", f"{mett_c_total:.3f}")
    
    # 차트 (Plotly 사용 가능한 경우)
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        # Bar chart
        fig = px.bar(
            df, 
            x="요소", 
            y="점수",
            title="6개 요소 점수 breakdown",
            color="점수",
            color_continuous_scale="RdYlGn",
            text="점수"
        )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        st.plotly_chart(fig, width='stretch')
        
        # 가중 점수 비교
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df["요소"],
            y=df["가중 점수"],
            name="가중 점수",
            marker_color='lightblue',
            text=df["가중 점수"],
            texttemplate='%{text:.3f}',
            textposition='outside'
        ))
        fig2.update_layout(
            title="가중 점수 비교",
            xaxis_title="요소",
            yaxis_title="가중 점수"
        )
        st.plotly_chart(fig2, width='stretch')
        
    except ImportError:
        st.info("Plotly가 설치되지 않아 차트를 표시할 수 없습니다. `pip install plotly` 실행")


