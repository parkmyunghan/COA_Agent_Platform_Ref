# ui/components/recommendation_visualization.py
# -*- coding: utf-8 -*-
"""
Recommendation Visualization
추천 근거 시각화 컴포넌트
"""
import streamlit as st
import pandas as pd


def render_recommendation_breakdown(recommendation, agent_result=None):
    """추천 근거 breakdown 시각화 (사용자 친화적 버전)"""
    # agent_result가 딕셔너리이고 recommendations 키가 있으면 첫 번째 추천 사용
    if isinstance(recommendation, dict) and "recommendations" in recommendation:
        agent_result = recommendation
        recommendations = recommendation.get("recommendations", [])
        if recommendations:
            recommendation = recommendations[0]
        else:
            st.info("추천 결과가 없습니다.")
            return
    
    score_breakdown = recommendation.get("score_breakdown", {})
    
    if not score_breakdown:
        st.info("점수 breakdown 정보가 없습니다.")
        return
    
    st.subheader("📊 추천 근거 분석")
    
    # 사용자 친화적 요소 이름 및 설명
    factors = {
        "threat": {
            "name": "위협 수준",
            "description": "적의 위협 정도를 평가합니다. 위협이 높을수록 강력한 방어가 필요합니다.",
            "icon": "⚠️"
        },
        "resources": {
            "name": "자원 가용성",
            "description": "필요한 자원 대비 가용 자원의 비율입니다. 자원이 충분할수록 방책 실행이 용이합니다.",
            "icon": "📦"
        },
        "assets": {
            "name": "전력 능력",
            "description": "아군 전력의 준비도 및 능력을 평가합니다. 전력이 강할수록 방어 효과가 높습니다.",
            "icon": "🛡️"
        },
        "environment": {
            "name": "환경 적합성",
            "description": "기상, 지형 등 환경 조건의 적합도를 평가합니다. 환경이 유리할수록 방책 성공 가능성이 높습니다.",
            "icon": "🌍"
        },
        "historical": {
            "name": "과거 효과성",
            "description": "유사한 상황에서의 과거 성공 사례를 기반으로 평가합니다. 검증된 방책일수록 신뢰도가 높습니다.",
            "icon": "📚"
        },
        "chain": {
            "name": "연계성",
            "description": "다른 방책과의 연계 가능성을 평가합니다. 연계가 잘 될수록 종합 작전 효과가 높습니다.",
            "icon": "🔗"
        }
    }
    
    # 가중치 정보
    weights = {
        "threat": 0.25,
        "resources": 0.20,
        "assets": 0.20,
        "environment": 0.15,
        "historical": 0.10,
        "chain": 0.10
    }
    
    # 점수 데이터 구성
    breakdown_data = []
    total_weighted_score = 0
    
    for key, factor_info in factors.items():
        score = score_breakdown.get(key, 0)
        weight = weights.get(key, 0)
        weighted_score = score * weight
        total_weighted_score += weighted_score
        
        # 점수 해석
        if score >= 0.8:
            interpretation = "매우 우수"
            color = "green"
            icon = "🟢"
        elif score >= 0.6:
            interpretation = "양호"
            color = "yellow"
            icon = "🟡"
        elif score >= 0.4:
            interpretation = "보통"
            color = "orange"
            icon = "🟠"
        else:
            interpretation = "부족"
            color = "red"
            icon = "🔴"
        
        # 온톨로지 기여도 정보 추가 (agent_result가 있는 경우)
        ontology_info = ""
        if agent_result:
            from ui.components.ontology_impact_analysis import _analyze_ontology_contribution
            situation_analysis = agent_result.get("situation_analysis", {})
            contribution = _analyze_ontology_contribution(key, score, situation_analysis, recommendation)
            ontology_info = f"{contribution['level']} ({contribution['source']})"
        
        breakdown_data.append({
            "요소": f"{factor_info['icon']} {factor_info['name']}",
            "점수": f"{score:.3f}",
            "해석": interpretation,
            "가중치": f"{weight:.2f}",
            "가중 점수": f"{weighted_score:.3f}",
            "온톨로지 기여": ontology_info if ontology_info else "N/A",
            "설명": factor_info['description']
        })
    
    df = pd.DataFrame(breakdown_data)
    
    # 사용자 친화적 테이블 표시
    st.dataframe(df, width='stretch', hide_index=True)
    
    # 각 요소별 상세 카드 표시
    st.markdown("#### 📋 요소별 상세 평가")
    cols = st.columns(3)
    
    for idx, (key, factor_info) in enumerate(factors.items()):
        with cols[idx % 3]:
            score = score_breakdown.get(key, 0)
            weight = weights.get(key, 0)
            weighted_score = score * weight
            
            # 점수에 따른 색상 및 아이콘
            if score >= 0.8:
                icon = "🟢"
                interpretation = "매우 우수"
            elif score >= 0.6:
                icon = "🟡"
                interpretation = "양호"
            elif score >= 0.4:
                icon = "🟠"
                interpretation = "보통"
            else:
                icon = "🔴"
                interpretation = "부족"
            
            st.markdown(f"""
            **{icon} {factor_info['name']}**
            
            점수: **{score:.3f}** ({interpretation})
            
            가중 점수: **{weighted_score:.3f}**
            
            *{factor_info['description']}*
            """)
            
            # 진행 바
            st.progress(score)
    
    # 총점 표시
    total_score = recommendation.get("score", 0)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("**종합 점수**", f"{total_score:.3f}")
    with col2:
        st.metric("**가중 합계**", f"{total_weighted_score:.3f}")
    
    # METT-C 종합 평가 섹션 (확장 가능)
    st.divider()
    _render_mett_c_evaluation(recommendation, agent_result)
    
    # 🔥 NEW: 교리 참조 표시
    doctrine_refs = recommendation.get('doctrine_references', [])
    if doctrine_refs:
        st.divider()
        from ui.components.doctrine_reference_display import render_doctrine_references
        render_doctrine_references(recommendation)
    
    # 시각화 차트
    st.markdown("#### 📈 시각화")
    
    # 1. 추천 로직 그래프 (Graphviz)
    render_recommendation_logic(recommendation)
    
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        # 차트용 데이터 준비
        chart_data = []
        for key, factor_info in factors.items():
            score = score_breakdown.get(key, 0)
            weight = weights.get(key, 0)
            chart_data.append({
                "요소": factor_info['name'],
                "점수": score,
                "가중 점수": score * weight,
                "가중치": weight
            })
        
        chart_df = pd.DataFrame(chart_data)
        
        # Bar chart (점수)
        fig = px.bar(
            chart_df, 
            x="요소", 
            y="점수",
            title="6개 요소별 점수",
            color="점수",
            color_continuous_scale="RdYlGn",
            text="점수"
        )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, width='stretch')
        
        # 가중 점수 비교
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=chart_df["요소"],
            y=chart_df["가중 점수"],
            name="가중 점수",
            marker_color='lightblue',
            text=chart_df["가중 점수"],
            texttemplate='%{text:.3f}',
            textposition='outside'
        ))
        fig2.update_layout(
            title="가중 점수 비교 (종합 점수에 기여하는 정도)",
            xaxis_title="요소",
            yaxis_title="가중 점수",
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig2, width='stretch')
        
    except ImportError:
        st.info("Plotly가 설치되지 않아 차트를 표시할 수 없습니다. `pip install plotly` 실행")


def render_recommendation_logic(recommendation):
    """추천 로직 시각화 (Graphviz)"""
    st.markdown("##### 🧠 추천 논리 구조")
    
    coa_name = recommendation.get("coa_name", "Unknown COA")
    score = recommendation.get("score", 0)
    score_breakdown = recommendation.get("score_breakdown", {})
    
    # 요소별 색상 결정
    def get_color_config(score):
        if score >= 0.8: return "#00b894", "white"  # Green
        if score >= 0.6: return "#fdcb6e", "black"  # Yellow (Black text for contrast)
        if score >= 0.4: return "#e17055", "white"  # Orange
        return "#d63031", "white"  # Red
    
    # Graphviz DOT
    dot = f"""
    digraph Logic {{
        rankdir=LR;
        splines=curved;
        nodesep=0.3;
        ranksep=0.5;
        fontname="Malgun Gothic";
        fontsize=11;
        bgcolor="transparent";
        
        node [shape=box, style="filled,rounded", fontname="Malgun Gothic", fontsize=10, margin=0.1];
        edge [fontname="Malgun Gothic", fontsize=9, color="#aaaaaa", arrowsize=0.6];
        
        # Central COA Node
        coa [label="{coa_name}\\n(점수: {score:.3f})", shape=doubleoctagon, fillcolor="#0984e3", fontcolor="white", fontsize=12, width=1.5];
        
        # Factor Nodes
    """
    
    # Add nodes with dynamic colors
    for key, name in [("threat", "위협 수준"), ("resources", "자원 가용성"), ("assets", "전력 능력"), 
                      ("environment", "환경 적합성"), ("historical", "과거 효과성"), ("chain", "연계성")]:
        val = score_breakdown.get(key, 0)
        bg_color, font_color = get_color_config(val)
        dot += f'    {key} [label="{name}\\n({val:.2f})", fillcolor="{bg_color}", fontcolor="{font_color}"];\n'

    dot += """
        # Inputs (Simulation)
        subgraph cluster_inputs {{
            label="입력 데이터";
            style=dashed;
            color="#555555";
            fontcolor="#aaaaaa";
            
            input_threat [label="적군 배치", shape=plaintext, fontcolor="#cccccc"];
            input_res [label="보급 현황", shape=plaintext, fontcolor="#cccccc"];
            input_env [label="기상/지형", shape=plaintext, fontcolor="#cccccc"];
        }}
        
        # Connections
        input_threat -> threat [style=dotted];
        input_res -> resources [style=dotted];
        input_env -> env [style=dotted];
        
        threat -> coa [label="0.25", penwidth=2];
        resources -> coa [label="0.20", penwidth=1.5];
        assets -> coa [label="0.20", penwidth=1.5];
        env -> coa [label="0.15", penwidth=1.2];
        history -> coa [label="0.10", penwidth=1];
        chain -> coa [label="0.10", penwidth=1];
    }}
    """
    
    st.graphviz_chart(dot, width='stretch')


def render_chain_visualization(chain_info):
    """체인 시각화"""
    if not chain_info:
        return
    
    st.subheader("🔗 관계 체인 시각화")
    
    chains = chain_info.get("chains", [])
    if chains:
        st.write(f"**발견된 체인**: {len(chains)}개")
        
        # 최고 체인 표시
        best_chain = chains[0] if chains else None
        if best_chain:
            st.markdown("#### 최고 체인")
            path = best_chain.get("path", [])
            predicates = best_chain.get("predicates", [])
            
            chain_text = " → ".join([
                f"{path[i].split('#')[-1] if '#' in path[i] else path[i]} ({predicates[i].split('#')[-1] if i < len(predicates) and '#' in predicates[i] else ''})"
                for i in range(len(path))
            ])
            st.write(chain_text)
            st.write(f"**점수**: {best_chain.get('score', 0):.2f}")
            
            # 체인 요약
            summary = chain_info.get("summary", {})
            if summary:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 체인 수", summary.get("total_chains", 0))
                with col2:
                    st.metric("평균 깊이", f"{summary.get('avg_depth', 0):.1f}")
                with col3:
                    st.metric("평균 점수", f"{summary.get('avg_score', 0):.2f}")


def _render_mett_c_evaluation(recommendation, agent_result=None):
    """METT-C 종합 평가 섹션 렌더링"""
    # METT-C 점수 확인
    score_breakdown = recommendation.get("score_breakdown", {})
    mett_c_scores = score_breakdown.get("mett_c") or recommendation.get("mett_c")
    
    if not mett_c_scores:
        # METT-C 점수가 없으면 표시하지 않음
        return
    
    # 확장 가능한 섹션
    with st.expander("🎯 METT-C 종합 평가 (Mission, Enemy, Terrain, Troops, Civilian, Time)", expanded=False):
        st.markdown("""
        **METT-C 프레임워크**는 작전 계획 시 고려해야 할 6가지 핵심 요소를 평가합니다.
        """)
        
        # METT-C 요소 정의
        mett_c_factors = {
            "mission": {
                "name": "임무 부합성",
                "description": "방책이 주어진 임무 목표와 얼마나 부합하는지 평가합니다.",
                "icon": "🎯",
                "weight": 0.20
            },
            "enemy": {
                "name": "적군 대응",
                "description": "적군의 위협에 효과적으로 대응할 수 있는 능력을 평가합니다.",
                "icon": "⚠️",
                "weight": 0.20
            },
            "terrain": {
                "name": "지형 적합성",
                "description": "작전 지역의 지형 조건이 방책 실행에 얼마나 유리한지 평가합니다.",
                "icon": "🌍",
                "weight": 0.15
            },
            "troops": {
                "name": "부대 능력",
                "description": "아군 부대의 전투력과 준비도를 평가합니다.",
                "icon": "👥",
                "weight": 0.15
            },
            "civilian": {
                "name": "민간인 보호",
                "description": "방책이 민간인 지역에 미치는 영향을 평가합니다. 점수가 낮을수록 민간인 보호가 부족합니다.",
                "icon": "🏘️",
                "weight": 0.15,
                "is_critical": True  # 민간인 보호는 중요 요소
            },
            "time": {
                "name": "시간 제약",
                "description": "임무 시간 제한 및 제약조건을 준수하는지 평가합니다. 0점이면 실행 불가입니다.",
                "icon": "⏰",
                "weight": 0.15,
                "is_critical": True  # 시간 제약도 중요 요소
            }
        }
        
        # METT-C 종합 점수
        mett_c_total = mett_c_scores.get("total", 0)
        
        # 종합 점수 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            delta_color = "normal" if mett_c_total >= 0.7 else "inverse"
            st.metric("METT-C 종합 점수", f"{mett_c_total:.3f}",
                     delta="우수" if mett_c_total >= 0.7 else "보통",
                     delta_color=delta_color)
        with col2:
            civilian_score = mett_c_scores.get("civilian", 1.0)
            if civilian_score < 0.3:
                st.error(f"⚠️ 민간인 보호: {civilian_score:.3f}")
            elif civilian_score < 0.5:
                st.warning(f"민간인 보호: {civilian_score:.3f}")
            else:
                st.success(f"✅ 민간인 보호: {civilian_score:.3f}")
        with col3:
            time_score = mett_c_scores.get("time", 1.0)
            if time_score == 0.0:
                st.error("❌ 시간 제약 위반")
            elif time_score < 0.5:
                st.warning(f"시간 제약: {time_score:.3f}")
            else:
                st.success(f"✅ 시간 제약: {time_score:.3f}")
        
        st.divider()
        
        # METT-C 요소별 breakdown 테이블
        mett_c_breakdown_data = []
        for key, factor_info in mett_c_factors.items():
            score = mett_c_scores.get(key, 0)
            weight = factor_info.get("weight", 0)
            weighted_score = score * weight
            
            # 점수 해석
            if score >= 0.8:
                interpretation = "매우 우수"
                status_icon = "🟢"
            elif score >= 0.6:
                interpretation = "양호"
                status_icon = "🟡"
            elif score >= 0.4:
                interpretation = "보통"
                status_icon = "🟠"
            else:
                interpretation = "부족"
                status_icon = "🔴"
            
            # 중요 요소 강조
            if factor_info.get("is_critical") and score < 0.5:
                interpretation = f"⚠️ {interpretation}"
            
            mett_c_breakdown_data.append({
                "요소": f"{factor_info['icon']} {factor_info['name']}",
                "점수": f"{score:.3f}",
                "해석": interpretation,
                "가중치": f"{weight:.2f}",
                "가중 점수": f"{weighted_score:.3f}",
                "설명": factor_info['description']
            })
        
        mett_c_df = pd.DataFrame(mett_c_breakdown_data)
        st.dataframe(mett_c_df, use_container_width=True, hide_index=True)
        
        # METT-C 요소별 상세 카드
        st.markdown("#### 📋 METT-C 요소별 상세 평가")
        mett_c_cols = st.columns(3)
        
        for idx, (key, factor_info) in enumerate(mett_c_factors.items()):
            with mett_c_cols[idx % 3]:
                score = mett_c_scores.get(key, 0)
                weight = factor_info.get("weight", 0)
                weighted_score = score * weight
                
                # 점수에 따른 색상 및 아이콘
                if score >= 0.8:
                    status_icon = "🟢"
                    interpretation = "매우 우수"
                elif score >= 0.6:
                    status_icon = "🟡"
                    interpretation = "양호"
                elif score >= 0.4:
                    status_icon = "🟠"
                    interpretation = "보통"
                else:
                    status_icon = "🔴"
                    interpretation = "부족"
                
                # 중요 요소 경고
                warning_msg = ""
                if factor_info.get("is_critical"):
                    if key == "civilian" and score < 0.3:
                        warning_msg = "⚠️ **민간인 지역에 큰 영향** - 방책 재검토 필요"
                    elif key == "time" and score == 0.0:
                        warning_msg = "❌ **시간 제약 위반** - 실행 불가"
                    elif key == "time" and score < 0.5:
                        warning_msg = "⚠️ **시간 제약 준수도 낮음**"
                
                st.markdown(f"""
                **{status_icon} {factor_info['icon']} {factor_info['name']}**
                
                점수: **{score:.3f}** ({interpretation})
                
                가중 점수: **{weighted_score:.3f}**
                
                *{factor_info['description']}*
                
                {warning_msg}
                """)
                
                # 진행 바
                st.progress(score)
        
        # 민간인 보호 상세 정보 (점수가 낮을 때)
        civilian_score = mett_c_scores.get("civilian", 1.0)
        if civilian_score < 0.5:
            st.divider()
            st.markdown("#### 🏘️ 민간인 보호 상세 분석")
            st.warning(f"""
            **민간인 보호 점수: {civilian_score:.3f}**
            
            이 방책은 민간인 지역에 영향을 줄 수 있습니다. 다음 사항을 검토하세요:
            
            1. **영향받는 민간인 지역 확인**: 방책 실행 지역 주변의 민간인 밀집 지역을 확인하세요.
            2. **대피 계획 수립**: 필요시 민간인 대피 경로를 확보하세요.
            3. **대안 검토**: 민간인 지역에 영향을 주지 않는 대안 방책을 검토하세요.
            
            민간인 보호 점수가 0.3 미만인 경우, 해당 방책은 자동으로 제외됩니다.
            """)
        
        # 시간 제약 상세 정보 (점수가 낮을 때)
        time_score = mett_c_scores.get("time", 1.0)
        if time_score < 0.5:
            st.divider()
            st.markdown("#### ⏰ 시간 제약 상세 분석")
            if time_score == 0.0:
                st.error(f"""
                **시간 제약 위반: 실행 불가**
                
                이 방책은 임무 시간 제한을 초과하거나 시간 제약조건을 위반합니다.
                
                - 예상 소요 시간이 임무 시간 제한을 초과함
                - 또는 시간 제약조건을 위반함
                
                **권장사항**: 시간 제약을 만족하는 대안 방책을 검토하세요.
                """)
            else:
                st.warning(f"""
                **시간 제약 준수도: {time_score:.3f}**
                
                이 방책은 시간 제약을 준수하지만 여유가 적습니다.
                
                - 예상 소요 시간이 임무 시간 제한에 근접함
                - 시간 제약조건을 간신히 만족함
                
                **권장사항**: 시간 여유를 확보할 수 있는 방안을 검토하세요.
                """)
        
        # METT-C 차트 시각화
        try:
            import plotly.express as px
            import plotly.graph_objects as go
            
            mett_c_chart_data = []
            for key, factor_info in mett_c_factors.items():
                score = mett_c_scores.get(key, 0)
                weight = factor_info.get("weight", 0)
                mett_c_chart_data.append({
                    "요소": factor_info['name'],
                    "점수": score,
                    "가중 점수": score * weight,
                    "가중치": weight
                })
            
            mett_c_chart_df = pd.DataFrame(mett_c_chart_data)
            
            # Bar chart
            fig = px.bar(
                mett_c_chart_df,
                x="요소",
                y="점수",
                title="METT-C 요소별 점수",
                color="점수",
                color_continuous_scale="RdYlGn",
                text="점수"
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
        except ImportError:
            st.info("Plotly가 설치되지 않아 차트를 표시할 수 없습니다.")


def render_resource_comparison(recommendation):
    """자원 가용성 비교"""
    # 자원 정보가 있는 경우 표시
    # 구현 필요: 추천 결과에서 자원 정보 추출 및 비교

