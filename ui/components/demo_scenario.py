# ui/components/demo_scenario.py
# -*- coding: utf-8 -*-
"""
데모 시나리오 컴포넌트
파일럿 프로그램 데모용 시나리오 제공
"""
import streamlit as st
import pandas as pd
from typing import Dict, Optional
from datetime import datetime


# 미리 정의된 데모 시나리오
DEMO_SCENARIOS = [
    {
        "id": "scenario_1",
        "name": "시나리오 1: 적군 정찰기 침입",
        "description": "적 정찰기가 경계 지역 침입 시 방책 추천",
        "threat_type": "정찰",
        "severity": 75,
        "location": "경계지역",
        "enemy_info": "적 정찰기 2대가 경계 지역 상공에서 정찰 활동 중",
        "friendly_info": "1기갑여단이 경계 지역 근처에 배치되어 있음",
        "expected_coa": "Moderate_Defense 또는 Main_Defense",
        "key_points": [
            "정찰 활동은 공격 전 단계일 수 있음",
            "경계 지역은 중요 방어 지점",
            "기갑 부대의 기동력 활용 가능"
        ]
    },
    {
        "id": "scenario_2",
        "name": "시나리오 2: 적군 전차 부대 이동",
        "description": "적 전차 부대가 전방기지로 이동 시 방책 추천",
        "threat_type": "공격",
        "severity": 90,
        "location": "전방기지",
        "enemy_info": "적 5전차 대대가 전방기지 방향으로 이동 중 (ThreatLevel: 92)",
        "friendly_info": "2기갑여단이 전방기지에 배치되어 있음 (Firepower: 85)",
        "expected_coa": "Main_Defense",
        "key_points": [
            "높은 위협 수준 (90%)",
            "전차 부대는 공격력이 높음",
            "전방기지는 전략적 중요 지점"
        ]
    },
    {
        "id": "scenario_3",
        "name": "시나리오 3: 적군 정보수집 활동",
        "description": "적군의 정보수집 활동 감지 시 방책 추천",
        "threat_type": "정보수집",
        "severity": 40,
        "location": "후방기지",
        "enemy_info": "적 정보수집 부대가 후방기지 근처에서 활동 중",
        "friendly_info": "경계 부대가 후방기지 경계 임무 수행 중",
        "expected_coa": "Minimal_Defense 또는 Moderate_Defense",
        "key_points": [
            "낮은 위협 수준 (40%)",
            "정보수집은 직접 공격보다 위협도 낮음",
            "경계 강화로 대응 가능"
        ]
    },
    {
        "id": "scenario_4",
        "name": "시나리오 4: 적군 보급선 이동",
        "description": "적 보급선 이동 감지 시 방책 추천",
        "threat_type": "보급",
        "severity": 60,
        "location": "본부",
        "enemy_info": "적 보급선이 본부 방향으로 이동 중",
        "friendly_info": "본부 방어 부대가 배치되어 있음",
        "expected_coa": "Moderate_Defense",
        "key_points": [
            "보급선 이동은 공격 준비 신호일 수 있음",
            "본부는 중요 시설",
            "적절한 방어 조치 필요"
        ]
    }
]


def render_demo_scenario_selection_ui(approach_mode: str = "threat_centered") -> Optional[Dict]:
    """
    데모 시나리오 선택 UI (situation_input에서 호출)
    
    Args:
        approach_mode: 접근 방식 ("threat_centered" 또는 "mission_centered")
    
    Returns:
        situation_info 딕셔너리 또는 None
    """
    # 시나리오 선택
    scenario_options = {s["name"]: s for s in DEMO_SCENARIOS}
    
    # 이전 선택값 유지
    selected_key = "demo_scenario_selection"
    default_idx = 0
    if selected_key in st.session_state:
        try:
            prev_selection = st.session_state[selected_key]
            if prev_selection in list(scenario_options.keys()):
                default_idx = list(scenario_options.keys()).index(prev_selection)
        except (ValueError, KeyError):
            default_idx = 0
    
    selected_scenario_name = st.selectbox(
        "데모 시나리오 선택",
        options=list(scenario_options.keys()),
        index=default_idx,
        key=selected_key,
        help="시나리오를 선택하면 상황 정보가 자동으로 입력됩니다."
    )
    
    selected_scenario = scenario_options[selected_scenario_name]
    
    # 시나리오 상세 정보 표시
    with st.expander("📋 시나리오 상세 정보", expanded=True):
        st.write(f"**설명:** {selected_scenario['description']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("위협 유형", selected_scenario['threat_type'])
        with col2:
            st.metric("심각도", f"{selected_scenario['severity']}%")
        with col3:
            st.metric("발생 장소", selected_scenario['location'])
        
        st.write("**적군 정보:**")
        st.info(selected_scenario['enemy_info'])
        
        st.write("**아군 정보:**")
        st.success(selected_scenario['friendly_info'])
        
        st.write("**예상 방책:**")
        st.warning(selected_scenario['expected_coa'])
        
        st.write("**주요 포인트:**")
        for point in selected_scenario['key_points']:
            st.write(f"- {point}")
    
    # ✅ NEW: 선택된 시나리오에 맞는 SITREP 텍스트 자동 생성 (콤보박스 선택 시마다)
    # 선택된 시나리오를 기반으로 매번 새로 생성
    from ui.components.sitrep_generator import generate_sitrep_from_demo
    # 현재 선택된 시나리오를 기반으로 SITREP 생성
    generated_sitrep = generate_sitrep_from_demo(selected_scenario)
    
    # 선택된 시나리오에 맞는 SITREP을 session_state에 저장 (SITREP 입력 UI에서 사용)
    # 콤보박스 선택이 변경될 때마다 업데이트되도록 항상 새로 저장
    st.session_state.generated_sitrep_example = generated_sitrep
    st.session_state.current_scenario_id_for_sitrep = selected_scenario['id']  # 현재 시나리오ID 저장
    
    with st.expander("📝 생성된 SITREP 텍스트 (텍스트를 선택하여 복사하세요)", expanded=False):
        # 시나리오ID와 선택값을 포함한 고유 키로 매번 새로 렌더링되도록 보장
        sitrep_key = f"generated_sitrep_demo_{selected_scenario['id']}_{selected_scenario_name}"
        st.text_area(
            "생성된 SITREP 텍스트",
            value=generated_sitrep,
            height=100,
            key=sitrep_key,
            label_visibility="collapsed",
            disabled=False  # 텍스트 선택 가능하도록
        )
        st.caption(f"💡 위 텍스트는 선택한 시나리오 (**{selected_scenario['name']}**: {selected_scenario['threat_type']}, 심각도: {selected_scenario['severity']}%)에 맞게 생성되었습니다. 텍스트를 선택하여 복사한 후, SITREP 텍스트 입력란에서 사용하세요.")
    
    # 시나리오 적용 버튼
    if st.button("✅ 이 시나리오로 상황 설정", type="primary", key="set_demo_scenario"):
        situation_info = convert_scenario_to_situation_info(selected_scenario, approach_mode)
        
        # 생성된 SITREP을 session_state에 저장 (예시 자료용)
        st.session_state.generated_sitrep_example = generated_sitrep
        
        st.session_state.selected_situation_info = situation_info
        st.success(f"✅ '{selected_scenario['name']}' 시나리오가 로드되었습니다!")
        st.info("💡 이제 Agent 실행 페이지에서 질문을 입력하거나 '방책 추천해줘'라고 질문하세요.")
        # st.rerun() 제거: 페이지 새로고침 없이 입력 UI 유지
        return situation_info
    
    # ✅ 버튼을 누르지 않았어도, 선택된 시나리오 정보를 반환하여 미리보기 갱신
    temp_demo_info = convert_scenario_to_situation_info(selected_scenario, approach_mode)
    return temp_demo_info


def render_demo_scenario(orchestrator, on_scenario_select=None, approach_mode: str = "threat_centered"):
    """
    데모 시나리오 선택 및 실행 패널 렌더링 (레거시 호환용)
    
    Args:
        orchestrator: Orchestrator 인스턴스 (사용되지 않음, 호환성 유지)
        on_scenario_select: 시나리오 선택 시 호출할 콜백 함수
        approach_mode: 접근 방식 ("threat_centered" 또는 "mission_centered")
    """
    st.subheader("파일럿 데모 시나리오")
    
    st.info("""
    **데모 시나리오를 선택하면 상황 정보가 자동으로 입력됩니다.**
    """)
    
    result = render_demo_scenario_selection_ui(approach_mode=approach_mode)
    
    if result and on_scenario_select:
        on_scenario_select(result)


def convert_scenario_to_situation_info(scenario: Dict, approach_mode: str = "threat_centered") -> Dict:
    """
    시나리오를 situation_info 형식으로 변환
    
    Args:
        scenario: 시나리오 딕셔너리
        approach_mode: 접근 방식 ("threat_centered" 또는 "mission_centered")
        
    Returns:
        situation_info 딕셔너리
    """
    situation_info = {
        "situation_id": f"DEMO_{scenario['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "threat_level": scenario['severity'] / 100.0,  # 0-1 범위로 정규화
        "위협수준": str(scenario['severity']),  # ✅ 추가: 원본 값 저장
        "심각도": scenario['severity'],
        "발생장소": scenario['location'],
        "enemy_units": scenario['enemy_info'],
        "friendly_units": scenario['friendly_info'],
        "additional_context": f"데모 시나리오: {scenario['name']}",
        "approach_mode": approach_mode,
        "timestamp": datetime.now().isoformat(),
        "is_demo": True,
        "demo_scenario_id": scenario['id']
    }
    
    if approach_mode == "threat_centered":
        situation_info["위협유형"] = scenario['threat_type']
    else:  # mission_centered
        situation_info["임무명"] = scenario.get('name', '데모 임무')
        situation_info["mission_id"] = f"DEMO_MISSION_{scenario['id']}"
        situation_info["임무ID"] = situation_info["mission_id"]
    
    return situation_info


def convert_threat_data_to_situation_info(threat_data: Dict) -> Dict:
    """
    위협 데이터를 situation_info 형식으로 변환
    
    Args:
        threat_data: 위협 데이터 딕셔너리 (DataFrame row)
        
    Returns:
        situation_info 딕셔너리
    """
    threat_id = str(threat_data.get('위협ID', threat_data.get('ID', 'UNKNOWN')))
    threat_type = str(threat_data.get('위협유형코드', threat_data.get('위협유형', 'N/A')))
    severity = threat_data.get('심각도', threat_data.get('위협수준', 0))
    
    # 심각도를 숫자로 변환
    if isinstance(severity, str):
        # 'High', 'Medium', 'Low' 문자열 처리
        severity_upper = severity.upper()
        if severity_upper in ['HIGH', 'H', '높음']:
            severity = 85
        elif severity_upper in ['MEDIUM', 'M', '보통', '중간']:
            severity = 60
        elif severity_upper in ['LOW', 'L', '낮음']:
            severity = 30
        else:
            try:
                severity = float(str(severity).replace(',', ''))
            except:
                severity = 0
    
    location = str(threat_data.get('발생장소', 'N/A'))
    detection_time = threat_data.get('탐지시각', '')
    evidence = threat_data.get('근거', '')
    
    return {
        "situation_id": threat_id,
        "threat_level": severity / 100.0 if severity > 1 else severity,  # 0-1 범위로 정규화
        "위협ID": threat_id,
        "위협유형": threat_type,
        "심각도": severity,
        "발생장소": location,
        "탐지시각": detection_time,
        "근거": evidence,
        "additional_context": f"실제 데이터에서 선택된 위협: {threat_id}",
        "timestamp": datetime.now().isoformat(),
        "is_demo": False
    }


def get_scenario_situation_info() -> Optional[Dict]:
    """
    현재 설정된 시나리오 상황 정보 가져오기 (레거시 호환용)
    
    Returns:
        situation_info 딕셔너리 또는 None
    """
    # 레거시 호환: demo_scenario_data도 확인
    return st.session_state.get("selected_situation_info") or st.session_state.get("demo_scenario_data")

