# ui/components/situation_input.py
# -*- coding: utf-8 -*-
"""
상황 입력 UI 컴포넌트
COA 방책 추천을 위한 상황 정보 입력
실전 데이터 연동 지원
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from pandas import Timestamp


def _convert_to_string(value):
    """값을 문자열로 변환 (Timestamp 객체 처리)"""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (Timestamp, datetime)):
        return str(value)
    return str(value)


def enrich_situation_info_with_ontology(situation_info: Dict, orchestrator) -> Dict:
    """온톨로지 데이터를 사용하여 상황 정보 보강 (지형명, 지역, 축선명 등)"""
    if not situation_info or not orchestrator:
        return situation_info

    # 1. 축선명 보강
    axis_id = situation_info.get("관련축선ID") or situation_info.get("axis_id") or situation_info.get("주요축선ID")
    if axis_id and (not situation_info.get("관련축선명") or situation_info.get("관련축선명") in ["N/A", ""]):
        try:
            axis_df = orchestrator.core.data_manager.load_table('전장축선')
            if axis_df is not None and not axis_df.empty:
                # 대소문자 및 한글 컬럼명 강인한 매칭
                cols_upper = [str(c).upper() for c in axis_df.columns]
                id_idx = next((i for i, c in enumerate(cols_upper) if c in ['축선ID', 'AXIS_ID', 'AXISID', 'ID']), None)
                name_idx = next((i for i, c in enumerate(cols_upper) if c in ['축선명', 'AXIS_NAME', 'AXISNAME', 'NAME']), None)
                
                if id_idx is not None and name_idx is not None:
                    id_col = axis_df.columns[id_idx]
                    name_col = axis_df.columns[name_idx]
                    # ID 매칭 (공백 제거 및 대문자 변환 후 비교)
                    axis_id_clean = str(axis_id).strip().upper()
                    matched = axis_df[axis_df[id_col].astype(str).str.strip().str.upper() == axis_id_clean]
                    if not matched.empty:
                        name_val = str(matched.iloc[0][name_col])
                        situation_info["관련축선명"] = name_val
                        situation_info["axis_name"] = name_val
                        if "주요축선명" in situation_info: situation_info["주요축선명"] = name_val
        except Exception as e:
            pass

    # 2. 지형 상세 정보 보강 (지역, 지형명)
    loc_id = (situation_info.get("발생장소") or situation_info.get("location") or 
              situation_info.get("location_cell_id") or situation_info.get("location_id"))
              
    # ✅ 엑셀 직접 좌표정보(좌표정보 컬럼) 우선 확인 및 보강
    coord_info = situation_info.get("좌표정보") or situation_info.get("coord_info")
    if coord_info and "," in str(coord_info):
        try:
            parts = [p.strip() for p in str(coord_info).split(",")]
            if len(parts) >= 2:
                # 엑셀 형식: "경도, 위도" (127.x, 37.x)
                lng, lat = float(parts[0]), float(parts[1])
                situation_info.update({
                    "latitude": lat, "longitude": lng,
                    "lat": lat, "lng": lng,
                    "hasLatitude": lat, "hasLongitude": lng
                })
                print(f"[INFO] 엑셀 직접 좌표 보강 성공: {coord_info}")
        except Exception as e:
            print(f"[WARN] 엑셀 좌표 파싱 실패: {e}")

    if loc_id and (not situation_info.get("발생지형명") or situation_info.get("발생지형명") in ["N/A", ""]):
        try:
            terrain_df = orchestrator.core.data_manager.load_table('지형셀')
            if terrain_df is not None and not terrain_df.empty:
                cols_upper = [str(c).upper() for c in terrain_df.columns]
                tid_idx = next((i for i, c in enumerate(cols_upper) if c in ['지형셀ID', 'TERRAIN_CELL_ID', 'TERRAINID', 'ID', '지형셀_ID']), None)
                tname_idx = next((i for i, c in enumerate(cols_upper) if c in ['지형명', 'TERRAIN_NAME', 'TERRAINNAME', 'NAME']), None)
                ttype_idx = next((i for i, c in enumerate(cols_upper) if c in ['지형유형', 'TERRAIN_TYPE', 'TYPE']), None)
                treg_idx = next((i for i, c in enumerate(cols_upper) if c in ['지역', 'REGION', 'DISTRICT']), None)
                
                if tid_idx is not None:
                    tid_col = terrain_df.columns[tid_idx]
                    loc_id_clean = str(loc_id).strip().upper()
                    matched_t = terrain_df[terrain_df[tid_col].astype(str).str.strip().str.upper() == loc_id_clean]
                    
                    if not matched_t.empty:
                        # 실제 매칭된 ID로 loc_id 업데이트 (온톨로지 조회 정확도 향상)
                        loc_id = str(matched_t.iloc[0][tid_col])
                        loc_name = str(matched_t.iloc[0][terrain_df.columns[tname_idx]]) if tname_idx is not None else ""
                        loc_type = str(matched_t.iloc[0][terrain_df.columns[ttype_idx]]) if ttype_idx is not None else ""
                        loc_region = str(matched_t.iloc[0][terrain_df.columns[treg_idx]]) if treg_idx is not None else ""
                        
                        situation_info["발생지형명"] = loc_name
                        situation_info["발생지형유형"] = loc_type
                        situation_info["발생지역"] = loc_region
                        situation_info["location_name"] = loc_name if loc_name else (f"{loc_id}({loc_type})" if loc_type else loc_id)
                        situation_info["location_region"] = loc_region
                        situation_info["location_id"] = loc_id

                # [MOD] 좌표 정보 보강 (StatusManager 우선 -> OntologyManager 차선)
                if not situation_info.get("latitude"):
                    try:
                        # 1. StatusManager에서 실시간 좌표 우선 조회 (발생장소 ID 또는 상황 ID 기준)
                        # 상황 ID(THR001 등)로 검색 시도
                        search_id = situation_info.get("situation_id") or situation_info.get("위협ID") or loc_id
                        coords = orchestrator.core.status_manager.get_coordinates(search_id)
                        
                        # 지형셀 ID로 직접 검색 (StatusManager가 지형 데이터도 가지고 있을 경우 대비)
                        if not coords and loc_id != search_id:
                            coords = orchestrator.core.status_manager.get_coordinates(loc_id)

                        if coords:
                            lat, lng = coords
                            situation_info.update({
                                "latitude": lat, "longitude": lng,
                                "lat": lat, "lng": lng,
                                "hasLatitude": lat, "hasLongitude": lng
                            })
                            print(f"[INFO] StatusManager 좌표 보강 성공: {search_id} -> ({lat}, {lng})")
                        else:
                            # 2. 온톨로지에서 정적 좌표 조회 (Fallback)
                            coords = orchestrator.core.ontology_manager.get_coordinates(loc_id)
                            if coords:
                                lat, lng = coords
                                situation_info.update({
                                    "latitude": lat, "longitude": lng,
                                    "lat": lat, "lng": lng,
                                    "hasLatitude": lat, "hasLongitude": lng
                                })
                                print(f"[INFO] 온톨로지 좌표 보강 성공: {loc_id} -> ({lat}, {lng})")
                    except Exception as e:
                        print(f"[WARN] 좌표 조회 실패 ({loc_id}): {e}")
        except Exception as e:
            pass
    
    return situation_info


def _find_threat_table(orchestrator) -> Optional[str]:
    """
    위협 관련 테이블을 동적으로 찾기
    
    Args:
        orchestrator: Orchestrator 인스턴스
    
    Returns:
        위협 관련 테이블명 또는 None
    """
    if not orchestrator or not orchestrator.config:
        return None
    
    # 설정 파일에서 위협 관련 테이블 찾기
    data_paths = orchestrator.config.get("data_paths", {})
    
    # 위협 관련 키워드로 테이블 찾기
    threat_keywords = ["위협", "threat", "Threat", "THREAT"]
    for table_name in data_paths.keys():
        if any(keyword in table_name for keyword in threat_keywords):
            return table_name
    
    # 기본값: 첫 번째 테이블 또는 None
    return list(data_paths.keys())[0] if data_paths else None


def render_situation_input(orchestrator=None, use_real_data: bool = True):
    """
    상황 입력 UI 렌더링 (임무 중심/위협 중심 통합)
    
    Args:
        orchestrator: Orchestrator 인스턴스 (실제 데이터 로드용)
        use_real_data: 실제 데이터 테이블 사용 여부
    
    Returns:
        상황 정보 딕셔너리 (situation_id, threat_level, defense_assets, approach_mode 등)
    """
    st.subheader("상황 정보 입력")
    
    # 1단계: 접근 방식 선택 (임무 중심 vs 위협 중심)
    approach_mode = st.radio(
        "접근 방식 선택",
        options=["위협 중심", "임무 중심"],
        horizontal=True,
        key="situation_approach_mode",
        help="위협 중심: 방어 작전 (위협상황이 먼저 보고된 경우)\n임무 중심: 공격 작전 (상급 부대에서 임무가 부여된 경우)"
    )
    
    st.divider()
    
    # 2단계: 입력 방식 선택 (접근 방식에 따라 옵션 변경)
    if approach_mode == "위협 중심":
        input_mode = st.radio(
            "입력 방식 선택",
            options=["실제 데이터에서 선택", "SITREP 텍스트 입력", "수동 입력", "데모 시나리오"],
            horizontal=True,
            key="situation_input_mode_threat"
        )
        
        if input_mode == "실제 데이터에서 선택":
            if orchestrator and use_real_data:
                situation_info = render_real_data_selection_ui(orchestrator)
                if situation_info:
                    situation_info = enrich_situation_info_with_ontology(situation_info, orchestrator)
                    st.session_state.selected_situation_info = situation_info
            else:
                st.warning("실제 데이터를 사용할 수 없습니다. 수동 입력 또는 데모 시나리오를 선택하세요.")
                situation_info = None
        elif input_mode == "SITREP 텍스트 입력":
            situation_info = render_sitrep_input_ui(orchestrator)
        elif input_mode == "수동 입력":
            situation_info = render_manual_input(orchestrator=orchestrator, approach_mode="threat_centered")
        else:  # 데모 시나리오
            from ui.components.demo_scenario import render_demo_scenario_selection_ui
            situation_info = render_demo_scenario_selection_ui(approach_mode="threat_centered")
            if situation_info:
                situation_info = enrich_situation_info_with_ontology(situation_info, orchestrator)
                st.session_state.selected_situation_info = situation_info
    
    else:  # 임무 중심
        input_mode = st.radio(
            "입력 방식 선택",
            options=["실제 데이터에서 선택", "수동 입력", "데모 시나리오"],
            horizontal=True,
            key="situation_input_mode_mission"
        )
        
        if input_mode == "실제 데이터에서 선택":
            if orchestrator and use_real_data:
                situation_info = render_mission_selection_ui(orchestrator)
            else:
                st.warning("실제 데이터를 사용할 수 없습니다. 수동 입력 또는 데모 시나리오를 선택하세요.")
                situation_info = None
        elif input_mode == "수동 입력":
            situation_info = render_manual_input(orchestrator=orchestrator, approach_mode="mission_centered")
        else:  # 데모 시나리오
            from ui.components.demo_scenario import render_demo_scenario_selection_ui
            situation_info = render_demo_scenario_selection_ui(approach_mode="mission_centered")
    
    # approach_mode를 situation_info에 추가
    if situation_info:
        situation_info["approach_mode"] = "threat_centered" if approach_mode == "위협 중심" else "mission_centered"
        
        # 🔥 모든 경로 공통: 온톨로지 상세 정보 최종 보강
        situation_info = enrich_situation_info_with_ontology(situation_info, orchestrator)
        
        # 반환값이 있으면 session_state에 저장 (통일된 저장 로직)
        saved_info = st.session_state.get("selected_situation_info")
        # situation_id가 다르거나 저장된 정보가 없으면 저장 (또는 보강된 경우 업데이트)
        if not saved_info or saved_info.get("situation_id") != situation_info.get("situation_id") or "location_name" not in saved_info:
            st.session_state.selected_situation_info = situation_info
    
    return situation_info


def render_manual_input(orchestrator=None, approach_mode: str = "threat_centered") -> Dict:
    """수동 입력 UI 렌더링 (접근 방식별)"""
    # 상황 ID
    situation_id = st.text_input(
        "상황 ID",
        value=f"SIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        key=f"situation_id_manual_{approach_mode}",
        help="고유한 상황 식별자"
    )
    
    situation_info = {
        "situation_id": situation_id,
        "approach_mode": approach_mode,
        "timestamp": datetime.now().isoformat(),
        "is_manual": True
    }
    
    if approach_mode == "threat_centered":
        # 위협 중심 수동 입력
        threat_level = st.slider(
            "위협 수준",
            min_value=0,
            max_value=100,
            value=70,
            step=1,
            key=f"threat_level_manual_{approach_mode}",
            help="0-100 범위의 위협 수준 (높을수록 위험)"
        )
        
        # 위협 수준 시각화
        if threat_level >= 80:
            st.error(f"🔴 높은 위협 수준: {threat_level}%")
        elif threat_level >= 50:
            st.warning(f"🟡 중간 위협 수준: {threat_level}%")
        else:
            st.info(f"🟢 낮은 위협 수준: {threat_level}%")
        
        situation_info.update({
            "threat_level": threat_level / 100.0,  # 정규화된 값 (0-1)
            "위협수준": str(threat_level),  # ✅ 추가: 원본 값 저장
            "심각도": threat_level,
            "위협ID": situation_id
        })
        
        # [NEW] 위협 유형 및 임무 유형 선택 (Threat Centered 모드 확장)
        col1, col2 = st.columns(2)
        with col1:
            threat_type = st.selectbox(
                "위협 유형",
                options=[
                    "공중위협", "포격", "침투", "국지도발", "전면전",
                    "사이버", "기습공격", "정면공격", "측면공격", 
                    "포위공격", "지속공격", "정밀타격", "화생방공격", "집결징후"
                ],
                key=f"threat_type_manual_{approach_mode}",
                help="예상되는 위협의 유형"
            )
            situation_info['위협유형'] = threat_type
            situation_info['threat_type'] = threat_type
            
        with col2:
            mission_type_opt = st.selectbox(
                "현재 임무 유형 (선택)",
                options=["선택 안 함", "방어", "공격", "반격", "정찰", "기동", "억제"],
                index=0,
                key=f"mission_type_manual_opt_{approach_mode}",
                help="현재 수행 중인 임무 (점수 계산 시 가중치 반영)"
            )
            if mission_type_opt != "선택 안 함":
                situation_info['임무유형'] = mission_type_opt
                situation_info['mission_type'] = mission_type_opt
    
    else:  # mission_centered
        # 임무 중심 수동 입력
        mission_id = st.text_input(
            "임무 ID",
            value="MSN001",
            key=f"mission_id_manual_{approach_mode}",
            help="임무 식별자"
        )
        
        mission_name = st.text_input(
            "임무명",
            value="방어 작전",
            key=f"mission_name_manual_{approach_mode}",
            help="임무 이름"
        )

        mission_type = st.selectbox(
            "임무 종류",
            options=["방어", "공격", "반격", "정찰", "매복", "기동", "전술 철수"],
            index=0,
            key=f"mission_type_manual_{approach_mode}",
            help="수행할 임무의 종류"
        )

        primary_axis_id = st.text_input(
            "주요 작전 축선 ID",
            value="AXIS_001",
            key=f"mission_axis_manual_{approach_mode}",
            help="임무가 수행되는 주요 축선 식별자"
        )

        mission_objective = st.text_area(
            "임무 목표 (Objective)",
            value="적 제5전차대대의 남하를 저지하고 주요 보급로를 확보함.",
            key=f"mission_objective_manual_{approach_mode}",
            help="임무의 구체적인 목표와 달성 상태"
        )
        
        situation_info.update({
            "mission_id": mission_id,
            "임무ID": mission_id,
            "임무명": mission_name,
            "임무종류": mission_type,
            "주요축선ID": primary_axis_id,
            "관련축선ID": primary_axis_id,
            "임무목표": mission_objective,
            "threat_level": 0.5  # 기본값
        })
    
    st.divider()
    
    # [NEW] 자원 및 환경 정보 (공통)
    st.markdown("#### 작전 환경 및 자원")
    
    # 1. 자원 가용성
    col_res, col_env = st.columns([1, 2])
    with col_res:
        resource_availability = st.slider(
            "자원 가용성 (%)",
            0, 100, 70, 5,
            key=f"resource_avail_manual_{approach_mode}",
            help="현재 사용 가능한 자원의 비율"
        )
        situation_info['resource_availability'] = resource_availability / 100.0
        
    with col_env:
        c1, c2, c3 = st.columns(3)
        with c1:
            weather = st.selectbox("기상", ["맑음", "흐림", "비", "눈", "안개"], key=f"weather_{approach_mode}")
        with c2:
            terrain = st.selectbox("지형", ["평지", "산악", "시가지", "하천", "혼합"], key=f"terrain_{approach_mode}")
        with c3:
            time_of_day = st.selectbox("시간", ["주간", "야간", "새벽", "황혼"], key=f"time_{approach_mode}")
            
    situation_info['environment'] = {
        'weather': weather,
        'terrain': terrain,
        'time_of_day': time_of_day
    }
    
    st.divider()
    
    # 방어 자산 정보 (확장)
    st.markdown("#### 방어 자산 정보")
    
    col1, col2 = st.columns(2)
    
    with col1:
        defense_assets_count = st.number_input(
            "방어 자산 수",
            min_value=0,
            max_value=100,
            value=5,
            step=1,
            key=f"defense_assets_count_manual_{approach_mode}",
            help="사용 가능한 방어 자산의 개수"
        )
    
    with col2:
        defense_firepower = st.number_input(
            "평균 화력 지수",
            min_value=0,
            max_value=100,
            value=75,
            step=1,
            key=f"defense_firepower_manual_{approach_mode}",
            help="방어 자산의 평균 화력 지수"
        )
        
    # [NEW] 자산 세부 능력
    col3, col4 = st.columns(2)
    with col3:
        mobility = st.slider("기동력", 0, 100, 60, 5, key=f"mobility_{approach_mode}")
    with col4:
        defense_cap = st.slider("방어력", 0, 100, 70, 5, key=f"defense_cap_{approach_mode}")
    
    situation_info["defense_assets"] = {
        "count": defense_assets_count,
        "firepower": defense_firepower,
        "mobility": mobility,
        "defense_capability": defense_cap
    }
    
    st.divider()
    
    # 추가 상황 정보
    with st.expander("📝 추가 상황 정보 (선택)", expanded=False):
        location = st.text_input(
            "위치",
            value="Grid 1234",
            key=f"situation_location_manual_{approach_mode}",
            help="작전 위치 또는 그리드 좌표"
        )
        
        enemy_units = st.text_area(
            "적군 정보",
            value="적 5전차 대대 (ThreatLevel: 92)" if approach_mode == "threat_centered" else "",
            key=f"situation_enemy_manual_{approach_mode}",
            help="적군 부대 및 위협 정보"
        )
        
        friendly_units = st.text_area(
            "아군 정보",
            value="1기갑여단 (Firepower: 90)",
            key=f"situation_friendly_manual_{approach_mode}",
            help="아군 부대 및 능력 정보"
        )
        
        additional_context = st.text_area(
            "추가 컨텍스트",
            value="",
            key=f"situation_context_manual_{approach_mode}",
            help="기타 상황 정보"
        )
        
        situation_info.update({
            "location": location,
            "enemy_units": enemy_units,
            "friendly_units": friendly_units,
            "additional_context": additional_context
        })
    
    # 저장 버튼
    if st.button("✅ 상황 정보 저장", type="primary", key=f"save_manual_input_{approach_mode}"):
        # ✅ NEW: 통합 변환기 사용
        from common.situation_converter import SituationInfoConverter
        
        standardized_info = SituationInfoConverter.convert(
            situation_info,
            source_type="manual"
        )
        
        # ✅ NEW: 검증
        is_valid, errors = SituationInfoConverter.validate(standardized_info)
        if not is_valid:
            for err in errors:
                st.error(f"❌ {err}")
        else:
            # ✅ 온톨로지 상세 정보 보강 (좌표, 지형명 등)
            if orchestrator:
                standardized_info = enrich_situation_info_with_ontology(standardized_info, orchestrator)
                
            st.session_state.selected_situation_info = standardized_info
            st.success("✅ 상황 정보가 저장되었습니다!")
            st.info("💡 이제 Agent 실행 페이지에서 질문을 입력하세요.")
            st.rerun()
    
    # 저장된 정보가 있으면 표시
    saved_info = st.session_state.get("selected_situation_info")
    if saved_info and saved_info.get("is_manual") and saved_info.get("approach_mode") == approach_mode:
        st.info(f"✅ 저장된 상황: {saved_info.get('situation_id', 'N/A')}")
    
    return situation_info


def render_real_data_selection_ui(orchestrator) -> Optional[Dict]:
    """
    실제 데이터 테이블에서 위협 상황 선택 UI (대시보드와 동일한 방식)
    
    Args:
        orchestrator: Orchestrator 인스턴스
        
    Returns:
        situation_info 딕셔너리 또는 None
    """
    try:
        # 위협 관련 테이블을 동적으로 찾기
        threat_table_name = _find_threat_table(orchestrator)
        if not threat_table_name:
            st.warning("위협 관련 테이블을 찾을 수 없습니다.")
            return None
        
        # 위협상황 테이블 로드 (동적으로 찾은 테이블명 사용)
        threats_df = orchestrator.core.data_manager.load_table(threat_table_name)
        
        if threats_df is None or threats_df.empty:
            st.warning(f"{threat_table_name} 테이블이 비어있거나 로드할 수 없습니다.")
            return None
        
        # 컬럼명 동적 찾기 (대시보드와 동일한 방식)
        id_col = None
        threat_type_col = None
        threat_level_col = None
        axis_id_col = None
        location_col = None
        
        for col in threats_df.columns:
            col_upper = col.upper()
            # ID 컬럼 찾기
            if id_col is None and col_upper in ['ID', '위협ID', 'THREAT_ID', 'THREATID']:
                id_col = col
            # 위협유형 컬럼 찾기 (위협유형코드 우선, 위협유형 차선)
            if threat_type_col is None:
                if col_upper in ['위협유형코드', 'THREAT_TYPE_CODE', 'THREATTYPECODE']:
                    threat_type_col = col
                elif col_upper in ['위협유형', 'THREAT_TYPE', 'THREATTYPE']:
                    threat_type_col = col
            # 위협수준 컬럼 찾기 (위협수준 우선, 심각도 차선)
            if threat_level_col is None:
                if col_upper in ['위협수준', 'THREAT_LEVEL', 'THREATLEVEL']:
                    threat_level_col = col
                elif col_upper in ['심각도', 'SEVERITY']:
                    threat_level_col = col
            # 관련축선ID 컬럼 찾기
            if axis_id_col is None and col_upper in ['관련축선ID', 'RELATED_AXIS_ID', 'RELATEDAXISID', '축선ID', 'AXIS_ID']:
                axis_id_col = col
            # 발생장소/위치 컬럼 찾기
            if location_col is None:
                if col_upper in ['발생장소', 'LOCATION', '발생위치', 'OCCURRENCE_LOCATION']:
                    location_col = col
                elif col_upper in ['발생위치셀ID', 'LOCATION_CELL_ID']:
                    location_col = col
        
        if not id_col:
            st.warning("위협상황 테이블에 ID 컬럼을 찾을 수 없습니다.")
            # 디버깅 정보 표시
            with st.expander("🔍 사용 가능한 컬럼 목록", expanded=False):
                st.write("**컬럼명:**")
                for col in threats_df.columns:
                    st.write(f"- {col}")
            return None
        
        # 위협 상황 선택
        threat_options = []
        for idx, row in threats_df.iterrows():
            threat_id_val = str(row.get(id_col, f'THREAT_{idx}'))
            
            # 위협유형
            if threat_type_col:
                threat_type = str(row.get(threat_type_col, 'N/A'))
            else:
                threat_type = 'N/A'
            
            # 위협수준/심각도
            if threat_level_col:
                threat_level = row.get(threat_level_col, 'N/A')
            else:
                threat_level = 'N/A'
            
            # 관련축선ID
            if axis_id_col:
                axis_id = str(row.get(axis_id_col, 'N/A'))
            else:
                axis_id = 'N/A'
            
            # 발생장소
            if location_col:
                location = str(row.get(location_col, 'N/A'))
            else:
                location = 'N/A'
            
            # 표시 텍스트 구성 (대시보드와 동일한 형식)
            if axis_id != 'N/A':
                display_text = f"{threat_id_val} - {threat_type} ({threat_level}) - 축선: {axis_id}"
            else:
                display_text = f"{threat_id_val} - {threat_type} ({threat_level})"
            
            threat_options.append({
                "display": display_text,
                "data": row.to_dict(),
                "threat_id": threat_id_val,
                "id_col": id_col,
                "threat_type_col": threat_type_col,
                "threat_level_col": threat_level_col,
                "axis_id_col": axis_id_col,
                "location_col": location_col
            })
        
        if threat_options:
            # session_state에 저장된 선택값 사용 (상태 유지)
            selected_key = "real_data_threat_selection"
            default_idx = 0
            
            # 이전 선택값이 있으면 유지
            if selected_key in st.session_state:
                try:
                    prev_selection = st.session_state[selected_key]
                    if prev_selection in [opt["display"] for opt in threat_options]:
                        default_idx = [opt["display"] for opt in threat_options].index(prev_selection)
                except (ValueError, KeyError):
                    default_idx = 0
            
            selected_display = st.selectbox(
                "위협 상황 선택",
                options=[opt["display"] for opt in threat_options],
                index=default_idx,
                key=selected_key,
                help="실제 데이터 테이블에서 위협 상황을 선택하세요."
            )
            
            selected_idx = [opt["display"] for opt in threat_options].index(selected_display)
            selected_threat = threat_options[selected_idx]
            selected_threat_data = selected_threat["data"]
            
            # 선택된 위협 정보 간단히 표시
            threat_id = selected_threat["threat_id"]
            threat_type = str(selected_threat_data.get(selected_threat["threat_type_col"], 'N/A')) if selected_threat["threat_type_col"] else 'N/A'
            threat_level = selected_threat_data.get(selected_threat["threat_level_col"], 'N/A') if selected_threat["threat_level_col"] else 'N/A'
            axis_id = str(selected_threat_data.get(selected_threat["axis_id_col"], 'N/A')) if selected_threat["axis_id_col"] else 'N/A'
            location = str(selected_threat_data.get(selected_threat["location_col"], 'N/A')) if selected_threat["location_col"] else 'N/A'
            
            # 표시 정보 구성
            info_parts = [f"**위협ID**: {threat_id}"]
            if threat_type != 'N/A':
                info_parts.append(f"**위협유형**: {threat_type}")
            if threat_level != 'N/A':
                info_parts.append(f"**위협수준**: {threat_level}")
            if axis_id != 'N/A':
                info_parts.append(f"**관련축선**: {axis_id}")
            if location != 'N/A':
                info_parts.append(f"**발생장소**: {location}")
            
            st.info(f"✅ **선택된 위협**: {' | '.join(info_parts)}")
            
            # 선택된 위협 상세 정보 (expander로 접을 수 있게)
            with st.expander("📋 선택된 위협 상세 정보", expanded=False):
                # Timestamp 객체를 문자열로 변환하여 DataFrame 생성
                threat_display_data = {k: _convert_to_string(v) for k, v in selected_threat_data.items()}
                threat_display_df = pd.DataFrame([threat_display_data]).T
                threat_display_df.columns = ["값"]
                st.dataframe(threat_display_df, width='stretch')
            
            # ✅ NEW: 선택된 위협상황에 맞는 SITREP 텍스트 자동 생성 (콤보박스 선택 시마다)
            # 선택된 위협 데이터를 기반으로 매번 새로 생성
            from common.situation_converter import SituationInfoConverter
            temp_situation_info = SituationInfoConverter.convert(
                selected_threat_data,
                source_type="real_data",
                approach_mode="threat_centered"
            )
            
            from ui.components.sitrep_generator import generate_sitrep_from_real_data
            # 현재 선택된 위협 데이터를 기반으로 SITREP 생성
            generated_sitrep = generate_sitrep_from_real_data(selected_threat_data, temp_situation_info)
            
            # 선택된 위협상황에 맞는 SITREP을 session_state에 저장 (SITREP 입력 UI에서 사용)
            # 콤보박스 선택이 변경될 때마다 업데이트되도록 항상 새로 저장
            st.session_state.generated_sitrep_example = generated_sitrep
            st.session_state.current_threat_id_for_sitrep = threat_id  # 현재 위협ID 저장
            
            with st.expander("📝 생성된 SITREP 텍스트 (텍스트를 선택하여 복사하세요)", expanded=False):
                # 위협ID를 포함한 고유 키로 매번 새로 렌더링되도록 보장
                sitrep_key = f"generated_sitrep_real_data_{threat_id}_{selected_display}"
                st.text_area(
                    "생성된 SITREP 텍스트",
                    value=generated_sitrep,
                    height=100,
                    key=sitrep_key,
                    label_visibility="collapsed",
                    disabled=False  # 텍스트 선택 가능하도록
                )
                st.caption(f"💡 위 텍스트는 선택한 위협상황 (**{threat_id}**: {threat_type}, 위협수준: {threat_level})에 맞게 생성되었습니다. 텍스트를 선택하여 복사한 후, SITREP 텍스트 입력란에서 사용하세요.")
            
            # [UX 개선] "이 위협으로 상황 설정" 버튼 제거 (One-Click 실행으로 통합)
            # 선택된 상황 정보는 반환값으로 전달되어 agent_execution.py에서 처리됨
            
            # 온톨로지 상세 정보 보강 (좌표, 지형명 등)
            temp_situation_info = enrich_situation_info_with_ontology(temp_situation_info, orchestrator)
            return temp_situation_info
            
            # ✅ 버튼을 누르지 않았어도, 선택된 상황 정보를 반환하여 미리보기(Map/Banner) 갱신
            # 단, 저장은 안 된 상태임 (is_preview=True 같은 플래그 추가 가능하나 현재 로직상 반환만 해도 됨)
            # 온톨로지 상세 정보 보강 (좌표, 지형명 등) - 미리보기용
            temp_situation_info = enrich_situation_info_with_ontology(temp_situation_info, orchestrator)
            return temp_situation_info
        else:
            st.warning("선택 가능한 위협 상황이 없습니다.")
            return None
            
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        import traceback
        with st.expander("상세 오류 정보"):
            st.code(traceback.format_exc())
        return None


def convert_threat_data_to_situation_info(threat_data: Dict, 
                                         id_col: str = None,
                                         threat_type_col: str = None,
                                         threat_level_col: str = None,
                                         axis_id_col: str = None,
                                         location_col: str = None) -> Dict:
    """
    위협 데이터를 situation_info 형식으로 변환 (동적 컬럼명 지원)
    
    Args:
        threat_data: 위협 데이터 딕셔너리 (DataFrame row)
        id_col: ID 컬럼명
        threat_type_col: 위협유형 컬럼명
        threat_level_col: 위협수준 컬럼명
        axis_id_col: 관련축선ID 컬럼명
        location_col: 발생장소 컬럼명
        
    Returns:
        situation_info 딕셔너리
    """
    # ID 컬럼 동적 찾기
    threat_id = None
    if id_col and id_col in threat_data:
        threat_id = str(threat_data.get(id_col, 'UNKNOWN'))
    else:
        for col in ['ID', '위협ID', 'threat_id', 'THREAT_ID']:
            if col in threat_data:
                threat_id = str(threat_data.get(col, 'UNKNOWN'))
                break
    
    if not threat_id:
        threat_id = 'UNKNOWN'
    
    # 위협유형 컬럼 동적 찾기
    threat_type = 'N/A'
    if threat_type_col and threat_type_col in threat_data:
        threat_type = str(threat_data.get(threat_type_col, 'N/A'))
    else:
        for col in ['위협유형코드', '위협유형', 'threat_type_code', 'threat_type']:
            if col in threat_data:
                threat_type = str(threat_data.get(col, 'N/A'))
                break
    
    # 위협수준/심각도 컬럼 동적 찾기
    severity = 0
    threat_level_raw = None  # 원본 값 저장
    
    if threat_level_col and threat_level_col in threat_data:
        threat_level_raw = threat_data.get(threat_level_col)
        # 숫자로 변환 시도
        if isinstance(threat_level_raw, str):
            # 문자열 위협수준 처리 ("High", "Medium", "Low")
            threat_level_upper = threat_level_raw.upper()
            if threat_level_upper in ['HIGH', '높음', 'H']:
                severity = 90
            elif threat_level_upper in ['MEDIUM', '중간', 'M']:
                severity = 50
            elif threat_level_upper in ['LOW', '낮음', 'L']:
                severity = 20
            else:
                try:
                    severity = float(str(threat_level_raw).replace(',', ''))
                except:
                    severity = 0
        else:
            severity = threat_level_raw if threat_level_raw is not None else 0
    else:
        # 폴백: 여러 컬럼명 시도
        for col in ['위협수준', '심각도', 'threat_level', 'severity']:
            if col in threat_data:
                threat_level_raw = threat_data.get(col)
                # 위와 동일한 변환 로직
                if isinstance(threat_level_raw, str):
                    threat_level_upper = threat_level_raw.upper()
                    if threat_level_upper in ['HIGH', '높음', 'H']:
                        severity = 90
                    elif threat_level_upper in ['MEDIUM', '중간', 'M']:
                        severity = 50
                    elif threat_level_upper in ['LOW', '낮음', 'L']:
                        severity = 20
                    else:
                        try:
                            severity = float(str(threat_level_raw).replace(',', ''))
                        except:
                            severity = 0
                else:
                    severity = threat_level_raw if threat_level_raw is not None else 0
                break
    
    # 발생장소 컬럼 동적 찾기
    location = 'N/A'
    location_cell_id = None  # [FIX] 발생위치셀ID 별도 추출
    
    if location_col and location_col in threat_data:
        location = str(threat_data.get(location_col, 'N/A'))
    else:
        for col in ['발생장소', 'location', '발생위치', 'occurrence_location', '발생위치셀ID', 'location_cell_id']:
            if col in threat_data:
                location = str(threat_data.get(col, 'N/A'))
                break
    
    # [FIX] 발생위치셀ID 별도 추출 (지형셀 좌표 조회용)
    for col in ['발생위치셀ID', 'location_cell_id', 'LOCATION_CELL_ID', '배치지형셀ID']:
        if col in threat_data and pd.notna(threat_data[col]):
            cell_id_val = str(threat_data[col]).strip()
            if cell_id_val and cell_id_val != 'N/A':
                location_cell_id = cell_id_val
                break
    
    # 탐지시각 컬럼 동적 찾기
    detection_time = ''
    for col in ['탐지시각', 'occurrence_time', '발생시각', 'detection_time']:
        if col in threat_data:
            detection_time = str(threat_data.get(col, ''))
            break
    
    # 근거 컬럼 동적 찾기
    evidence = ''
    for col in ['근거', 'raw_report_text', '원시보고텍스트', 'evidence']:
        if col in threat_data:
            evidence = str(threat_data.get(col, ''))
            break
    
    # 관련축선ID 컬럼 동적 찾기
    axis_id = 'N/A'
    if axis_id_col and axis_id_col in threat_data:
        axis_id = str(threat_data.get(axis_id_col, 'N/A'))
    else:
        for col in ['관련축선ID', 'related_axis_id', '축선ID', 'axis_id']:
            if col in threat_data:
                axis_id = str(threat_data.get(col, 'N/A'))
                break
    
    # 심각도를 0-1 범위로 정규화
    threat_level = severity / 100.0 if severity > 1 else severity
    
    # 위협수준 원본 값 저장 (문자열 또는 숫자)
    threat_level_display = threat_level_raw if threat_level_raw is not None else str(severity)
    
    # [NEW] 좌표 정보 파싱 (좌표정보, 위도/경도 컬럼 지원)
    latitude = None
    longitude = None
    
    # 1. 분리된 컬럼 확인
    for lat_col in ['위도', 'latitude', 'LATITUDE', 'lat', 'LAT']:
        if lat_col in threat_data and pd.notna(threat_data[lat_col]):
            try:
                latitude = float(threat_data[lat_col])
                break
            except: pass
            
    for lng_col in ['경도', 'longitude', 'LONGITUDE', 'lng', 'LNG', 'lon', 'LON']:
        if lng_col in threat_data and pd.notna(threat_data[lng_col]):
            try:
                longitude = float(threat_data[lng_col])
                break
            except: pass
            
    # 2. 통합 컬럼 확인 (좌표정보="127.5, 36.5")
    if latitude is None or longitude is None:
        for coord_col in ['좌표정보', 'coordinates', 'COORDINATES', '좌표']:
            if coord_col in threat_data and pd.notna(threat_data[coord_col]):
                try:
                    val_str = str(threat_data[coord_col])
                    if ',' in val_str:
                        parts = val_str.split(',')
                        if len(parts) >= 2:
                            # GeoJSON 순서: 경도, 위도 (x, y)
                            lng_tmp = float(parts[0].strip())
                            lat_tmp = float(parts[1].strip())
                            longitude = lng_tmp
                            latitude = lat_tmp
                            break
                except:
                    pass

    # 좌표정보 문자열도 포함 (scenario_mapper에서 사용)
    coord_info_str = None
    if latitude is not None and longitude is not None:
        coord_info_str = f"{longitude}, {latitude}"
    else:
        # 원본 좌표정보가 있으면 그대로 사용
        for coord_col in ['좌표정보', 'coordinates', 'COORDINATES', '좌표']:
            if coord_col in threat_data and pd.notna(threat_data[coord_col]):
                coord_info_str = str(threat_data[coord_col])
                break
    
    return {
        "situation_id": threat_id,
        "threat_level": threat_level,  # 정규화된 값 (0-1)
        # 좌표 정보 추가
        "latitude": latitude,
        "longitude": longitude,
        "좌표정보": coord_info_str,  # [FIX] 좌표정보 문자열도 포함
        "coordinates": coord_info_str,  # 영어 키도 포함
        "위협ID": threat_id,
        "위협유형": threat_type,
        "위협수준": threat_level_display,  # ✅ 추가: 원본 값 (문자열 또는 숫자)
        "심각도": severity,
        "발생장소": location,
        "발생위치셀ID": location_cell_id,  # [FIX] 발생위치셀ID 별도 포함
        "location_cell_id": location_cell_id,  # 영어 키도 포함
        "관련축선ID": axis_id,
        "탐지시각": detection_time,
        "근거": evidence,
        "additional_context": f"실제 데이터에서 선택된 위협: {threat_id}",
        "approach_mode": "threat_centered",
        "timestamp": datetime.now().isoformat(),
        "is_real_data": True
    }


def _find_mission_table(orchestrator) -> Optional[str]:
    """
    임무 관련 테이블을 동적으로 찾기
    
    Args:
        orchestrator: Orchestrator 인스턴스
    
    Returns:
        임무 관련 테이블명 또는 None
    """
    if not orchestrator or not orchestrator.config:
        return None
    
    # 설정 파일에서 임무 관련 테이블 찾기
    data_paths = orchestrator.config.get("data_paths", {})
    
    # 임무 관련 키워드로 테이블 찾기
    mission_keywords = ["임무", "mission", "Mission", "MISSION"]
    for table_name in data_paths.keys():
        if any(keyword in table_name for keyword in mission_keywords):
            return table_name
    
    # 기본값: None
    return None


def render_mission_selection_ui(orchestrator) -> Optional[Dict]:
    """임무 선택 UI (동적 테이블명 지원)"""
    try:
        # 임무 관련 테이블을 동적으로 찾기
        mission_table_name = _find_mission_table(orchestrator)
        if not mission_table_name:
            # 폴백: '임무정보' 시도
            mission_table_name = '임무정보'
        
        missions_df = orchestrator.core.data_manager.load_table(mission_table_name)
        if missions_df is None or missions_df.empty:
            st.warning(f"{mission_table_name} 테이블이 비어있거나 로드할 수 없습니다.")
            # 디버깅 정보 표시
            with st.expander("🔍 사용 가능한 테이블 목록", expanded=False):
                if orchestrator and orchestrator.config:
                    data_paths = orchestrator.config.get("data_paths", {})
                    st.write("**테이블명:**")
                    for table_name in data_paths.keys():
                        st.write(f"- {table_name}")
            return None
        
        # 임무 선택
        mission_options = []
        id_col = None
        name_col = None
        type_col = None
        
        for col in missions_df.columns:
            col_upper = col.upper()
            if id_col is None and col_upper in ['임무ID', 'MISSION_ID', 'MISSIONID', 'ID']:
                id_col = col
            if name_col is None and col_upper in ['임무명', 'MISSION_NAME', 'MISSIONNAME', 'NAME']:
                name_col = col
            if type_col is None and col_upper in ['임무종류', 'MISSION_TYPE', 'MISSIONTYPE', 'TYPE']:
                type_col = col
        
        if not id_col:
            st.warning("임무정보 테이블에 ID 컬럼을 찾을 수 없습니다.")
            return None
        
        for idx, row in missions_df.iterrows():
            mission_id = str(row.get(id_col, f'MISSION_{idx}'))
            mission_name = str(row.get(name_col, 'N/A')) if name_col else 'N/A'
            mission_type = str(row.get(type_col, 'N/A')) if type_col else 'N/A'
            
            display_text = f"{mission_id}: {mission_name} ({mission_type})"
            mission_options.append({
                "display": display_text,
                "data": row.to_dict(),
                "mission_id": mission_id
            })
        
        if mission_options:
            selected_key = "real_data_mission_selection"
            default_idx = 0
            
            # 이전 선택값이 있으면 유지
            if selected_key in st.session_state:
                try:
                    prev_selection = st.session_state[selected_key]
                    if prev_selection in [opt["display"] for opt in mission_options]:
                        default_idx = [opt["display"] for opt in mission_options].index(prev_selection)
                except (ValueError, KeyError):
                    default_idx = 0
            
            selected_display = st.selectbox(
                "임무 선택",
                options=[opt["display"] for opt in mission_options],
                index=default_idx,
                key=selected_key,
                help="실제 데이터 테이블에서 임무를 선택하세요."
            )
            
            selected_mission = next(
                opt for opt in mission_options
                if opt["display"] == selected_display
            )
            
            mission_id = selected_mission["mission_id"]
            mission_data = selected_mission["data"]
            
            # 컬럼 정보 저장
            mission_info = {
                "id_col": id_col,
                "name_col": name_col,
                "type_col": type_col
            }
            
            st.info(f"✅ **선택된 임무**: {mission_id} - {mission_data.get(name_col, 'N/A') if name_col else 'N/A'}")
            
            # 임무 상세 정보 표시
            with st.expander("📋 선택된 임무 상세 정보", expanded=False):
                # Timestamp 객체를 문자열로 변환하여 DataFrame 생성
                mission_display_data = {k: _convert_to_string(v) for k, v in mission_data.items()}
                mission_display_df = pd.DataFrame([mission_display_data]).T
                mission_display_df.columns = ["값"]
                st.dataframe(mission_display_df, width='stretch')
            
            # 상황 정보로 변환 및 저장
            if st.button("✅ 이 임무로 상황 설정", type="primary", key="set_real_data_mission"):
                situation_info = convert_mission_data_to_situation_info(
                    mission_data, 
                    mission_id,
                    id_col=mission_info["id_col"],
                    name_col=mission_info["name_col"],
                    type_col=mission_info["type_col"]
                )
                st.session_state.selected_situation_info = situation_info
                st.success(f"✅ 임무 상황이 설정되었습니다: {mission_id}")
                st.info("💡 이제 Agent 실행 페이지에서 질문을 입력하세요.")
                st.rerun()
                return situation_info
            
            # ✅ 버튼을 누르지 않았어도, 선택된 임무 정보를 반환하여 미리보기 갱신
            temp_mission_info = convert_mission_data_to_situation_info(
                mission_data, 
                mission_id,
                id_col=mission_info["id_col"],
                name_col=mission_info["name_col"],
                type_col=mission_info["type_col"]
            )
            return temp_mission_info

        else:
            st.warning("선택 가능한 임무가 없습니다.")
            return None
            
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        import traceback
        with st.expander("상세 오류 정보"):
            st.code(traceback.format_exc())
        return None


def convert_mission_data_to_situation_info(mission_data: Dict, mission_id: str,
                                          id_col: str = None,
                                          name_col: str = None,
                                          type_col: str = None) -> Dict:
    """임무 데이터를 situation_info 형식으로 변환 (동적 컬럼명 지원)"""
    # 임무명 동적 찾기
    mission_name = 'N/A'
    if name_col and name_col in mission_data:
        mission_name = str(mission_data.get(name_col, 'N/A'))
    else:
        for col in ['임무명', '임무이름', 'mission_name', 'name']:
            if col in mission_data:
                mission_name = str(mission_data.get(col, 'N/A'))
                break
    
    # 임무종류 동적 찾기
    mission_type = 'N/A'
    if type_col and type_col in mission_data:
        mission_type = str(mission_data.get(type_col, 'N/A'))
    else:
        for col in ['임무종류', 'mission_type', 'type']:
            if col in mission_data:
                mission_type = str(mission_data.get(col, 'N/A'))
                break
    
    # 주요축선ID 동적 찾기
    primary_axis_id = 'N/A'
    for col in ['주요축선ID', '주축선ID', 'primary_axis_id', 'axis_id']:
        if col in mission_data:
            primary_axis_id = str(mission_data.get(col, 'N/A'))
            break
    
    # 주요축선명 조회
    primary_axis_name = 'N/A'
    if primary_axis_id != 'N/A':
        try:
            # DataManager는 coa_service 등을 통해 접근해야 함 (상위 context에서 처리 권장하지만 여기서는 직접 로직 추가 가능성 확인)
            # 여기서는 일단 mission_data에 축선명이 있을 경우를 대비
            for col in ['주요축선명', '축선명', 'axis_name']:
                if col in mission_data:
                    primary_axis_name = str(mission_data.get(col, 'N/A'))
                    break
        except: pass

    # [FIX] 임무 중심 모드: 주공축선ID를 통해 좌표 결정
    # 주공축선의 중심점을 임무 위치로 사용
    latitude = None
    longitude = None
    coord_info_str = None
    
    if primary_axis_id and primary_axis_id != 'N/A':
        try:
            from ui.components.scenario_mapper import ScenarioMapper
            axis_coords, axis_meta = ScenarioMapper._resolve_axis_coordinates(str(primary_axis_id).strip())
            if axis_coords and len(axis_coords) > 0:
                # 축선의 중간 지점 계산
                mid_idx = len(axis_coords) // 2
                mid_pt = axis_coords[mid_idx]  # [lng, lat]
                longitude = mid_pt[0]
                latitude = mid_pt[1]
                coord_info_str = f"{longitude}, {latitude}"
                print(f"[INFO] 임무 중심 좌표 결정 (축선 기반): {mission_id} -> {primary_axis_id} -> ({longitude}, {latitude})")
        except Exception as e:
            print(f"[WARN] 임무 축선 좌표 조회 실패 ({mission_id}, {primary_axis_id}): {e}")
    
    # 작전지역을 통한 좌표 결정 (축선 실패 시)
    if (latitude is None or longitude is None) and mission_data:
        operation_area = mission_data.get("작전지역") or mission_data.get("operation_area")
        if operation_area and str(operation_area).strip() and str(operation_area).strip() != "N/A":
            # 작전지역명을 LOCATION_DB에서 검색
            from ui.components.scenario_mapper import LOCATION_DB
            area_str = str(operation_area).strip().lower()
            for key, loc in LOCATION_DB.items():
                loc_name = loc.get("name", "").lower()
                if loc_name and loc_name in area_str:
                    latitude = loc["lat"]
                    longitude = loc["lng"]
                    coord_info_str = f"{longitude}, {latitude}"
                    print(f"[INFO] 임무 중심 좌표 결정 (작전지역 기반): {mission_id} -> {operation_area} -> ({longitude}, {latitude})")
                    break
    
    return {
        "situation_id": mission_id,
        "mission_id": mission_id,
        "임무ID": mission_id,
        "임무명": mission_name,
        "임무종류": mission_type,
        "주요축선ID": primary_axis_id,
        "주요축선명": primary_axis_name,
        "관련축선ID": primary_axis_id,
        "관련축선명": primary_axis_name,
        "threat_level": 0.5,  # 임무 중심은 기본 위협 수준
        "approach_mode": "mission_centered",
        # [FIX] 좌표 정보 추가
        "latitude": latitude,
        "longitude": longitude,
        "좌표정보": coord_info_str,
        "coordinates": coord_info_str,
        "timestamp": datetime.now().isoformat(),
        "is_real_data": True
    }


def render_sitrep_input_ui(orchestrator) -> Optional[Dict]:
    """SITREP 텍스트 입력 UI"""
    # [NEW] SITREP 작성 가이드
    with st.expander("📝 SITREP 작성 가이드 (템플릿)", expanded=False):
        st.markdown("""
        **SITREP(상황보고) 작성 표준 양식:**
        
        1. **누가 (Who)**: 적 부대 식별 (예: *적 제3전차대대*)
        2. **언제 (When)**: 발생/관측 시각 (예: *금일 06:00경*)
        3. **어디서 (Where)**: 위치/좌표 (예: *동부전선 GP-3 일대*, *좌표 35.12, 127.34*)
        4. **무엇을 (What)**: 활동 내용 (예: *전차 30여 대를 동원하여 남하 중*)
        5. **어떻게 (How)**: 공격 형태/규모 (예: *전면 공격 대형으로*, *포병 지원 하에*)
        
        **예시:**
        > "금일 06:30경, 적 제5기계화보병여단이 파주 북방 5km 지점(Grid 123456)에서 전술 도로를 따라 남하 중임. 대규모 포병 사격 지원이 관측됨. 위협 수준 매우 높음."
        """)

    # ✅ NEW: 생성된 SITREP 예시 자료 표시
    generated_sitrep_example = st.session_state.get("generated_sitrep_example")
    if generated_sitrep_example:
        st.info("💡 **예시 SITREP 텍스트가 생성되었습니다!** 아래 텍스트를 선택하여 복사하세요.")
        with st.expander("📋 예시 SITREP 텍스트 (텍스트를 선택하여 복사하세요)", expanded=True):
            st.text_area(
                "예시 SITREP 텍스트",
                value=generated_sitrep_example,
                height=100,
                key="example_sitrep_text",
                label_visibility="collapsed",
                disabled=False  # 텍스트 선택 가능하도록
            )
            if st.button("🗑️ 예시 제거", key="clear_example_sitrep"):
                st.session_state.generated_sitrep_example = None
                st.rerun()
        st.divider()
    
    sitrep_text = st.text_area(
        "상황보고(SITREP) 텍스트를 입력하세요",
        height=150,
        placeholder="예: 적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음.",
        key="sitrep_input_text",
        value=st.session_state.get("sitrep_input_text", "")
    )
    
    if sitrep_text:
        if st.button("SITREP 파싱", type="primary", key="parse_sitrep_button"):
            with st.spinner("SITREP 파싱 중..."):
                try:
                    # LLM을 사용하여 SITREP 파싱
                    from core_pipeline.coa_service import COAService
                    coa_service = COAService(orchestrator.config)
                    threat_event = coa_service.parse_sitrep_to_threat(
                        sitrep_text=sitrep_text,
                        mission_id=None,
                        use_llm=True
                    )
                    
                    if threat_event:
                        st.success("✅ 위협상황 생성 완료")
                        
                        # ThreatEvent를 situation_info로 변환
                        # 위협수준 원본 값 저장
                        threat_level_raw = threat_event.threat_level if threat_event.threat_level else "N/A"
                        
                        # 정규화된 threat_level 계산 (문자열 위협수준 처리)
                        threat_level_normalized = 0.5  # 기본값
                        if isinstance(threat_level_raw, str):
                            threat_level_upper = threat_level_raw.upper()
                            if threat_level_upper in ['HIGH', '높음', 'H']:
                                threat_level_normalized = 0.9
                            elif threat_level_upper in ['MEDIUM', '중간', 'M']:
                                threat_level_normalized = 0.5
                            elif threat_level_upper in ['LOW', '낮음', 'L']:
                                threat_level_normalized = 0.2
                            else:
                                try:
                                    threat_level_normalized = float(str(threat_level_raw).replace(',', '')) / 100.0
                                except:
                                    threat_level_normalized = 0.5
                        else:
                            threat_level_normalized = float(threat_level_raw) / 100.0 if threat_level_raw and threat_level_raw > 1 else (threat_level_raw if threat_level_raw else 0.5)

                        situation_info = {
                            "situation_id": threat_event.threat_id,
                            "threat_level": threat_level_normalized,
                            "위협ID": threat_event.threat_id,
                            "위협유형": threat_event.threat_type_code,
                            "위협수준": threat_level_raw,
                            "관련축선ID": threat_event.related_axis_id,
                            "발생장소": threat_event.location_cell_id,
                            "location": threat_event.location_cell_id,
                            "enemy_units": threat_event.related_enemy_unit_id,
                            "적부대": threat_event.related_enemy_unit_id,
                            "occurrence_time": threat_event.occurrence_time.isoformat() if hasattr(threat_event.occurrence_time, 'isoformat') else str(threat_event.occurrence_time),
                            "발생시각": threat_event.occurrence_time.isoformat() if hasattr(threat_event.occurrence_time, 'isoformat') else str(threat_event.occurrence_time),
                            "time_str": str(threat_event.occurrence_time) if threat_event.occurrence_time else None,
                            "threat_type_original": threat_event.threat_type_original,
                            "enemy_unit_original": threat_event.enemy_unit_original,
                            "remarks": threat_event.remarks,
                            "description": threat_event.remarks if threat_event.remarks else sitrep_text,
                            "상황설명": threat_event.remarks if threat_event.remarks else sitrep_text,
                            "approach_mode": "threat_centered",
                            "is_sitrep_parsed": True,
                            "sitrep_text": sitrep_text,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # 온톨로지 상세 정보 보강 (축선명, 지형명, 지역 등)
                        situation_info = enrich_situation_info_with_ontology(situation_info, orchestrator)
                        
                        # ✅ 파싱 결과를 세션 상태에 저장 (상태 유지용)
                        st.session_state["temp_parsed_sitrep_info"] = situation_info
                        
                except Exception as e:
                    st.error(f"SITREP 파싱 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # ✅ 파싱된 결과가 있으면 표시 및 저장 버튼 렌더링 (파싱 버튼 루프 밖에서 처리)
    if "temp_parsed_sitrep_info" in st.session_state:
        situation_info = st.session_state["temp_parsed_sitrep_info"]
        
        # [MOD] 파싱 결과 확인 및 수정 (Editing UI)
        st.markdown("##### 📝 파싱 결과 확인 및 수정")
        
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                # 위협 유형 수정
                current_type = situation_info.get('위협유형', '미상')
                if not current_type: current_type = '미상'
                new_type = st.text_input("위협 유형", value=str(current_type), key="edit_sitrep_type")
                situation_info['위협유형'] = new_type
                situation_info['threat_type'] = new_type # 호환성 유지
                
            with col2:
                # 위협 수준 수정
                try:
                    current_val = int(float(situation_info.get('threat_level', 0.5)) * 100)
                except: current_val = 50
                new_level = st.slider("위협 수준 (%)", 0, 100, current_val, key="edit_sitrep_level")
                situation_info['threat_level'] = new_level / 100.0
                situation_info['위협수준'] = str(new_level)
                situation_info['심각도'] = new_level
                
            # 관련 축선 및 발생 장소
            col3, col4 = st.columns(2)
            with col3:
                current_axis = situation_info.get('관련축선ID', 'N/A')
                new_axis = st.text_input("관련 축선 ID", value=str(current_axis), key="edit_sitrep_axis")
                situation_info['관련축선ID'] = new_axis
            with col4:
                current_loc = situation_info.get('발생장소', 'N/A')
                new_loc = st.text_input("발생 장소 (Cell ID)", value=str(current_loc), key="edit_sitrep_loc")
                situation_info['발생장소'] = new_loc
                situation_info['location'] = new_loc

            # 상황 설명 (비고)
            current_desc = situation_info.get('상황설명', situation_info.get('description', ''))
            new_desc = st.text_area("상황 설명", value=str(current_desc), height=100, key="edit_sitrep_desc")
            situation_info['상황설명'] = new_desc
            situation_info['description'] = new_desc
            
            # 세션 상태 업데이트 (편집 결과 반영)
            st.session_state["temp_parsed_sitrep_info"] = situation_info
        
        if st.button("✅ 이 위협으로 상황 설정", type="primary", key="set_sitrep_threat_final"):
            st.session_state.selected_situation_info = situation_info
            # 임시 데이터 정리
            if "temp_parsed_sitrep_info" in st.session_state:
                del st.session_state["temp_parsed_sitrep_info"]
                
            st.success("✅ 위협 상황이 설정되었습니다!")
            st.info("💡 이제 Agent 실행 페이지에서 질문을 입력하세요.")
            st.rerun()
            return situation_info
            
        # ✅ 버튼을 누르지 않았어도, 파싱된 정보를 반환하여 미리보기 갱신
        return situation_info
    
    return None


def render_situation_summary(situation_info):
    """
    상황 정보 요약 표시 (접근 방식별)
    
    Args:
        situation_info: 상황 정보 딕셔너리
    """
    approach_mode = situation_info.get("approach_mode", "unknown")
    
    st.markdown("### 📊 입력된 상황 요약")
    
    if approach_mode == "threat_centered":
        # 위협 중심: 위협유형, 위협수준(원본), 관련축선 표시 (대시보드와 동일)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            threat_type = situation_info.get("위협유형", situation_info.get("threat_type", "N/A"))
            st.metric("위협유형", threat_type)
        
        with col2:
            # 위협수준 원본 값 사용 (문자열 또는 숫자)
            threat_level_raw = situation_info.get("위협수준", None)
            if threat_level_raw is None or threat_level_raw == "N/A":
                # 폴백: 정규화된 threat_level 사용
                threat_pct = int(situation_info.get("threat_level", 0) * 100)
                threat_level_display = f"{threat_pct}%"
            else:
                threat_level_display = str(threat_level_raw)
            st.metric("위협수준", threat_level_display)
        
        with col3:
            axis_id = situation_info.get("관련축선ID", "N/A")
            st.metric("관련축선", axis_id)
        
        # [MOD] 추가 정보 표시 (발생장소, 상황설명)
        location = situation_info.get("location", situation_info.get("발생장소", "미상"))
        description = situation_info.get("description", situation_info.get("상황설명", ""))
        
        st.markdown(f"📍 **발생장소**: {location}")
        if description:
            with st.expander("📝 상세 상황 설명", expanded=True):
                st.write(description)

        # 위협 수준에 따른 권장 사항 (정규화된 값 사용)
        threat_level = situation_info.get("threat_level", 0)
        if threat_level >= 0.8:
            st.warning("⚠️ **높은 위협 수준**: 강력한 방어 방책이 필요합니다.")
        elif threat_level >= 0.5:
            st.info("ℹ️ **중간 위협 수준**: 적절한 방어 방책을 권장합니다.")
        else:
            st.success("✅ **낮은 위협 수준**: 기본 방어 방책으로 충분합니다.")
    
    elif approach_mode == "mission_centered":
        # 임무 중심: 임무ID, 임무명, 임무종류, 주요축선ID 표시
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            mission_id = situation_info.get("mission_id", situation_info.get("임무ID", "N/A"))
            st.metric("임무 ID", mission_id)
        
        with col2:
            mission_name = situation_info.get("임무명", "N/A")
            st.metric("임무명", mission_name)
        
        with col3:
            mission_type = situation_info.get("임무종류", "N/A")
            st.metric("임무종류", mission_type)
        
        with col4:
            primary_axis = situation_info.get("주요축선ID", "N/A")
            st.metric("주요축선", primary_axis)
    
    else:
        # 알 수 없는 접근 방식: 기본 정보만 표시
        col1, col2 = st.columns(2)
        with col1:
            st.metric("상황 ID", situation_info.get("situation_id", "N/A"))
        with col2:
            threat_pct = int(situation_info.get("threat_level", 0) * 100)
            st.metric("위협 수준", f"{threat_pct}%")

