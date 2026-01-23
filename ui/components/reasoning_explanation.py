# ui/components/reasoning_explanation.py
# -*- coding: utf-8 -*-
"""
Reasoning Explanation Component
방책 추천 근거를 시각적으로 설명하는 컴포넌트
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Optional

def render_reasoning_explanation(strategy: Dict, core=None, approach_mode: str = "threat_centered"):
    """
    추천 방책의 상세 근거를 시각화하여 표시
    
    Args:
        strategy: 방책 정보 딕셔너리 (score_breakdown, reasoning 포함)
        core: CorePipeline 인스턴스 (옵션)
        approach_mode: "threat_centered" 또는 "mission_centered"
    """
    header_text = "🎯 임무수행 상세 분석" if approach_mode == "mission_centered" else "🔍 추천 근거 상세 분석"
    st.markdown(f"#### {header_text}")
    
    # 1. 데이터 추출
    # agent_result 구조인 경우 recommendations[0]에서 score_breakdown 확인
    score_breakdown = strategy.get("score_breakdown", {})
    reasoning = score_breakdown.get("reasoning", [])
    
    # agent_result 구조인 경우 recommendations[0]에서 score_breakdown 찾기
    if not score_breakdown or not reasoning:
        recommendations = strategy.get('recommendations', [])
        if recommendations and len(recommendations) > 0:
            first_rec = recommendations[0]
            rec_score_breakdown = first_rec.get("score_breakdown", {})
            if rec_score_breakdown:
                score_breakdown = rec_score_breakdown
                reasoning = rec_score_breakdown.get("reasoning", [])
    
    # reasoning 로그가 없으면 score_breakdown에서 추정 시도
    if not reasoning and score_breakdown:
        # 기본 breakdown만 있는 경우
        reasoning = []
        for key, val in score_breakdown.items():
            if key not in ['reasoning', 'agent_score', 'llm_score', 'hybrid_score']:
                reasoning.append({
                    "factor": key,
                    "score": val,
                    "weight": 0.0, # 알 수 없음
                    "weighted_score": 0.0, # 알 수 없음
                    "reason": "상세 로그 없음"
                })
    
    # reasoning이 없어도 참고 자료 탭은 표시할 수 있도록 계속 진행
    has_reasoning_data = bool(reasoning)

    # 2. 탭 구성 (시각화 / 상세 설명 / 참고 자료 / 온톨로지 추론)
    # reasoning 데이터가 있으면 기본 탭 추가, 없으면 참고 자료 탭만 표시
    tabs = []
    if has_reasoning_data:
        tabs = ["📊 점수 요인 분석", "📝 상세 설명"]
    
    # 🔥 개선: 참고 자료(교리+일반) 탭 추가
    # strategy가 개별 recommendation 객체인 경우 직접 확인
    doctrine_refs = strategy.get('doctrine_references')
    
    # strategy가 agent_result(전체 결과)인 경우에만 recommendations에서 찾기
    if doctrine_refs is None or (isinstance(doctrine_refs, list) and len(doctrine_refs) == 0):
        # agent_result 구조인 경우에만 recommendations 확인
        if 'recommendations' in strategy:
            recommendations = strategy.get('recommendations', [])
            if recommendations and len(recommendations) > 0:
                # 첫 번째 recommendation부터 순차적으로 확인
                for rec in recommendations:
                    if rec:
                        rec_doctrine_refs = rec.get('doctrine_references')
                        # None이 아니고 빈 리스트가 아닌 경우에만 할당
                        if rec_doctrine_refs is not None:
                            if isinstance(rec_doctrine_refs, list):
                                if len(rec_doctrine_refs) > 0:
                                    doctrine_refs = rec_doctrine_refs
                                    break  # 유효한 참조를 찾으면 중단
                            else:
                                # 리스트가 아닌 경우도 할당 (다른 타입일 수 있음)
                                doctrine_refs = rec_doctrine_refs
                                break
    
    # doctrine_refs가 리스트인 경우 길이 확인, 그 외에는 bool 확인
    has_data = False # 데이터 존재 여부
    if doctrine_refs is not None:
        if isinstance(doctrine_refs, list):
            has_data = len(doctrine_refs) > 0
        else:
            has_data = bool(doctrine_refs)
    
    # 탭 추가 (항상 추가)
    tabs.append("📚 참고 자료")
    
    reasoning_trace = strategy.get("reasoning_trace", [])
    if reasoning_trace:
        tabs.append("🌱 온톨로지 추론")
        
    # 탭이 없으면 참고 자료만 표시하거나 메시지 표시
    if not tabs:
        # 이 분기점은 이제 도달하기 어려움 (참고 자료 탭이 항상 추가되므로)
        st.info("상세 추천 근거 데이터가 없습니다.")
        return
    
    render_tabs = st.tabs(tabs)
    
    # reasoning 데이터가 있으면 기본 탭 렌더링
    if has_reasoning_data:
        with render_tabs[0]:
            _render_score_chart(reasoning, approach_mode=approach_mode)
            
        with render_tabs[1]:
            _render_detailed_explanation(reasoning, approach_mode=approach_mode)
    
    # 🔥 개선: 참고 자료 탭 (항상 렌더링)
    # 탭 인덱스 계산: reasoning 데이터가 있으면 2, 없으면 0
    reference_tab_idx = 2 if has_reasoning_data else 0
    
    with render_tabs[reference_tab_idx]:
        if has_data:
            from ui.components.doctrine_reference_display import render_doctrine_references, render_doctrine_based_explanation
            
            # strategy가 agent_result인 경우 개별 COA 추천 결과 사용
            # doctrine_refs가 strategy에 있으면 strategy 사용, 없으면 recommendations[0] 사용
            target_strategy = strategy
            strategy_doctrine_refs = strategy.get('doctrine_references')
            if strategy_doctrine_refs is None or (isinstance(strategy_doctrine_refs, list) and len(strategy_doctrine_refs) == 0):
                # agent_result 구조인 경우 recommendations[0] 사용
                recommendations = strategy.get('recommendations', [])
                if recommendations and len(recommendations) > 0:
                    target_strategy = recommendations[0]
            
            render_doctrine_references(target_strategy)
        else:
            st.warning("⚠️ 참고 자료를 불러올 수 없습니다. 데이터 연결 상태를 확인해주세요.")
        
    if reasoning_trace:
        # 온톨로지 추론 탭 인덱스 계산
        # 참고 자료 탭이 항상 존재하므로 인덱스 계산 단순화
        if has_reasoning_data:
            # [0]점수 -> [1]상세 -> [2]참고 -> [3]추론
            reasoning_tab_idx = 3
        else:
            # [0]참고 -> [1]추론
            reasoning_tab_idx = 1
        
        with render_tabs[reasoning_tab_idx]:
            _render_ontology_reasoning(reasoning_trace)

def _render_ontology_reasoning(trace: List[str]):
    """온톨로지 추론 흔적 렌더링"""
    st.markdown("### 🌱 온톨로지 추론 과정")
    st.info("이 방책은 지식그래프(Ontology) 상의 관계와 개체 속성을 기반으로 자동 도출되었습니다.")
    
    for i, step in enumerate(trace, 1):
        st.markdown(f"**Step {i}**")
        st.success(step)
        if i < len(trace):
            st.markdown("   ↓")

def _render_score_chart(reasoning: List[Dict], approach_mode: str = "threat_centered"):
    """점수 요인 분석 차트 렌더링"""
    if not reasoning:
        return
        
    # 데이터 준비
    factors = []
    scores = []
    weighted_scores = []
    weights = []
    
    # 한글 라벨 매핑 (접근 방식에 따라 변경)
    if approach_mode == "mission_centered":
        label_map = {
            'threat': '임무 수행',
            'resources': '자원 효율',
            'assets': '자산 능력',
            'environment': '환경 적합',
            'historical': '과거 사례',
            'chain': '연계 작전'
        }
        chart_title = "평가 요소별 획득 점수 (임무 중심)"
    else:
        label_map = {
            'threat': '위협 대응',
            'resources': '자원 효율',
            'assets': '자산 능력',
            'environment': '환경 적합',
            'historical': '과거 사례',
            'chain': '연계 작전'
        }
        chart_title = "평가 요소별 획득 점수 (위협 중심)"
    
    for item in reasoning:
        factor_key = item.get("factor", "Unknown")
        label = label_map.get(factor_key, factor_key)
        
        factors.append(label)
        scores.append(item.get("score", 0.0))
        weighted_scores.append(item.get("weighted_score", 0.0))
        weights.append(item.get("weight", 0.0))
    
    # Plotly 차트 생성 (가로 막대 그래프)
    fig = go.Figure()
    
    # 원점수 (배경)
    fig.add_trace(go.Bar(
        y=factors,
        x=[1.0] * len(factors), # 전체 1.0 기준
        orientation='h',
        name='최대 점수',
        marker=dict(color='rgba(200, 200, 200, 0.1)'),
        hoverinfo='none',
        showlegend=False
    ))
    
    # 획득 점수
    fig.add_trace(go.Bar(
        y=factors,
        x=scores,
        orientation='h',
        name='획득 점수',
        marker=dict(
            color=scores,
            colorscale='Blues',
            cmin=0,
            cmax=1.0
        ),
        text=[f"{s:.2f}" for s in scores],
        textposition='auto',
        hovertemplate='%{y}: %{x:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f"{chart_title} (1.0 만점)",
        xaxis=dict(title="점수", range=[0, 1.05], showgrid=True),
        yaxis=dict(autorange="reversed"), # 위에서부터 표시
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, width="content")
    
    # 기여도 차트 (가중 점수)
    total_weighted = sum(weighted_scores)
    if total_weighted > 0:
        fig2 = go.Figure(data=[go.Pie(
            labels=factors, 
            values=weighted_scores,
            hole=.4,
            textinfo='label+percent',
            marker=dict(colors=['#3498db', '#e74c3c', '#f1c40f', '#2ecc71', '#9b59b6', '#95a5a6'])
        )])
        
        fig2.update_layout(
            title="총점 기여도 분석",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            showlegend=False
        )
        
        st.plotly_chart(fig2, width="content")

def _render_detailed_explanation(reasoning: List[Dict], approach_mode: str = "threat_centered"):
    """상세 설명 렌더링"""
    if not reasoning:
        return
        
    st.markdown("### 📝 요소별 상세 평가")
    
    # 중요도 순 정렬 (가중 점수 기준)
    sorted_reasoning = sorted(reasoning, key=lambda x: x.get("weighted_score", 0), reverse=True)
    
    for item in sorted_reasoning:
        factor = item.get("factor", "Unknown")
        score = item.get("score", 0.0)
        weight = item.get("weight", 0.0)
        reason = item.get("reason", "설명 없음")
        
        # 임무 중심인 경우 용어 변환
        if approach_mode == "mission_centered":
            mapping = {
                "위협": "임무 상황",
                "적군": "대항군",
                "식별된 적 부대": "대항군",
                "대응": "수행",
                "수준": "가능성"
            }
            for old, new in mapping.items():
                reason = reason.replace(old, new)
        
        # 아이콘 및 레이블 매핑
        if approach_mode == "mission_centered":
            icon_map = {
                'threat': '🎯',
                'resources': '💰',
                'assets': '🔫',
                'environment': '🏔️',
                'historical': '📚',
                'chain': '🔗'
            }
            label_map = {
                'threat': '임무(MISSION)',
                'resources': '자원(RESOURCES)',
                'assets': '자산(ASSETS)',
                'environment': '환경(ENVIRONMENT)',
                'historical': '과거사례(HISTORY)',
                'chain': '연계성(CHAIN)'
            }
        else:
            icon_map = {
                'threat': '🛡️',
                'resources': '💰',
                'assets': '🔫',
                'environment': '🏔️',
                'historical': '📚',
                'chain': '🔗'
            }
            label_map = {
                'threat': '위협(THREAT)',
                'resources': '자원(RESOURCES)',
                'assets': '자산(ASSETS)',
                'environment': '환경(ENVIRONMENT)',
                'historical': '과거사례(HISTORY)',
                'chain': '연계성(CHAIN)'
            }
            
        icon = icon_map.get(factor, '🔹')
        display_label = label_map.get(factor, factor).upper()
        
        # 점수에 따른 색상
        color = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
        
        with st.expander(f"{icon} **{display_label}**: {score:.2f} (가중치: {weight:.2f})", expanded=(score >= 0.7)):
            st.markdown(f"""
            - **평가 점수**: :{color}[{score:.2f}] / 1.0
            - **반영 가중치**: {weight:.2f}
            - **최종 기여점수**: {item.get('weighted_score', 0):.3f}
            
            **💡 평가 근거**:
            > {reason}
            """)
