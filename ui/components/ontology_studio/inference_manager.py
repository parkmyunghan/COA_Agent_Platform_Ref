# ui/components/ontology_studio/inference_manager.py
# -*- coding: utf-8 -*-
"""
추론 관리 컴포넌트
추론 엔진 관리 및 분석
"""
import streamlit as st
import pandas as pd
from ui.components.ontology_dashboard_panel import render_ontology_dashboard_panel

def render_inference_manager(orchestrator):
    """추론 관리 렌더링"""
    st.markdown("### 🧠 추론 및 분석 (Inference & Analysis)")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if not ontology_manager or not ontology_manager.graph:
        st.warning("⚠️ 온톨로지 그래프가 없습니다.")
        return
    
    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "추론 전/후 비교",
        "추론 규칙 관리",
        "추론 결과 분석"
    ])
    
    with sub_tab1:
        _render_inference_comparison(orchestrator)
    
    with sub_tab2:
        _render_inference_rules(orchestrator)
    
    with sub_tab3:
        _render_inference_results(orchestrator)

def _render_inference_comparison(orchestrator):
    """추론 전/후 비교"""
    st.markdown("#### 🔄 추론 전/후 비교")
    st.markdown("온톨로지 추론 엔진이 도출한 **새로운 지식(Implicit Knowledge)**을 확인합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("Input Graph (사람이 입력한 데이터)")
        st.code("\n".join([
            "# A unit is on high ground",
            ":Unit_A :locatedIn :HighGround .",
            ":HighGround :type :Mountain ."
        ]), language="turtle")
    
    with col2:
        st.success("Reasoned Graph (AI가 추론한 사실)")
        st.code("\n".join([
            "# AI infers advantage",
            ':Unit_A :hasAdvantage "True" .',
            ':Unit_A :movementSpeed "Slow" .'
        ]), language="turtle")
    
    st.divider()
    st.caption("실제 데이터 추론 결과 (Sample)")
    
    # 실제 추론된 트리플 샘플 조회
    query_inferred_sample = "\n".join([
        "SELECT ?s ?p ?o WHERE {",
        "    ?s <http://coa-agent-platform.org/ontology#hasAdvantage> ?o .",
        "} LIMIT 5"
    ])
    
    try:
        ontology_manager = orchestrator.core.enhanced_ontology_manager
        res = ontology_manager.graph.query(query_inferred_sample)
        data = []
        for row in res:
            data.append({"Subject": row.s, "Predicate": "hasAdvantage", "Object": row.o})
        
        if data:
            st.dataframe(pd.DataFrame(data), width="stretch")
        else:
            st.warning("현재 추론된 '전술적 이점(hasAdvantage)' 데이터가 없습니다.")
    except Exception as e:
        st.error(f"추론 데이터 조회 실패: {e}")

def _render_inference_rules(orchestrator):
    """추론 규칙 관리"""
    st.markdown("#### 📋 추론 규칙 관리")
    st.info("💡 추론 규칙을 관리하고 활성화/비활성화할 수 있습니다.")
    
    st.info("추론 규칙 관리 기능은 구현 예정입니다.")

def _render_inference_results(orchestrator):
    """추론 결과 분석"""
    st.markdown("#### 📊 추론 결과 분석")
    st.info("💡 추론된 관계의 통계 및 패턴을 분석합니다.")
    
    st.info("추론 결과 분석 기능은 구현 예정입니다.")

