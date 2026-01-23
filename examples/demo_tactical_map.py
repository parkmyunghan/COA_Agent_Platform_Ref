# examples/demo_tactical_map.py
# -*- coding: utf-8 -*-
"""
Tactical Map Demo
ui/components/tactical_map.py 컴포넌트의 기능을 검증하기 위한 데모 스크립트
"""
import streamlit as st
import sys
import os

# 프로젝트 루트 경로 추가 (모듈 임포트용)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from ui.components.tactical_map_osm import render_tactical_map
from ui.components.scenario_mapper import ScenarioMapper

st.set_page_config(layout="wide", page_title="COP Tactical Map Demo")

st.title("🛡️ COP Tactical Map Verification (OpenStreetMap)")
st.markdown("OpenStreetMap GeoJSON 기반의 전술 지도 컴포넌트 테스트")

# 1. 시나리오 데이터 생성 (Mock)
st.sidebar.header("Scenario Settings")
threat_level = st.sidebar.slider("Threat Level", 1, 5, 3)
coa_choice = st.sidebar.selectbox("Select COA", ["Preemptive Strike", "Defense", "Counter Attack"])

# 데이터 매퍼를 통해 GeoJSON 생성
# 실제로는 에이전트 결과에서 데이터를 받아와야 함
mock_threats = [
    {"name": "평양 미사일 기지", "type": "Missile", "radius_km": 15 * threat_level},
    {"name": "개성 기계화 부대", "type": "Tank", "radius_km": 10},
    {"name": "원산 해군 기지", "type": "Navy", "radius_km": 20}
]

mock_coa = {
    "coa_type": "preemptive" if "Strike" in coa_choice else "defense",
    "name": coa_choice,
    "description": "Selected Course of Action Demo"
}

# 매핑 실행
threat_geojson = ScenarioMapper.map_threats_to_geojson(mock_threats)
coa_geojson = ScenarioMapper.map_coa_to_geojson(mock_coa, threat_geojson)

# JSON 데이터 확인 (디버깅용)
with st.expander("View GeoJSON Data"):
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Threat Data")
        st.json(threat_geojson)
    with col2:
        st.caption("COA Data")
        st.json(coa_geojson)

# 2. 지도 렌더링
st.subheader("Operational Map")

# 2단 레이아웃 (Palantir Style - 좌측 텍스트, 우측 지도)
col_left, col_right = st.columns([3, 7])

with col_left:
    st.info(f"**Current Threat**: Level {threat_level}")
    st.markdown("""
    ### 📋 Mission Brief
    **Target**: Neutralize Enemy Missile Assets
    **Status**: PLANNING
    
    ### 🎯 Selected COA
    """)
    st.success(f"**{coa_choice}**")
    st.markdown("Air assets will be deployed from the southern airbase to strike identified targets in the northern sector.")
    
    st.divider()
    st.caption("AIP Assistant Log")
    st.code("""
    [14:00] Threat detected
    [14:01] Analyzing assets...
    [14:02] COA Generated
    """, language="text")

with col_right:
    # 여기서 컴포넌트 호출
    render_tactical_map(threat_geojson, coa_geojson, height=600)

