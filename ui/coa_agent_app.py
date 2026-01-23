# ui/coa_agent_app.py
# -*- coding: utf-8 -*-
"""
COA Agent 데모 앱
POC 데모용 단순화된 UI - COA Agent 관점에서 한눈에 흐름을 볼 수 있도록 구성
"""
import streamlit as st
import sys
from pathlib import Path
import yaml

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

# 로거 초기화 (애플리케이션 시작 시)
from common.logger import get_logger
logger = get_logger("COAAgent")
logger.info("COA Agent 애플리케이션 시작")

from core_pipeline.coa_service import COAService
from core_pipeline.orchestrator import Orchestrator
from core_pipeline.data_models import ThreatEvent


def load_config():
    """설정 파일 로드"""
    config_path = BASE_DIR / "config" / "global.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def initialize_service():
    """COA 서비스 초기화"""
    # 성능 최적화를 위해 불필요한 재로드 제거
    if "coa_service" not in st.session_state:
        config = load_config()
        st.session_state.coa_service = COAService(config)
        
        # Orchestrator가 있으면 LLM/RAG 서비스 연결
        if "orchestrator" in st.session_state:
            orchestrator = st.session_state.orchestrator
            st.session_state.coa_service.initialize_llm_services(
                llm_manager=orchestrator.core.llm_manager,
                rag_manager=orchestrator.core.rag_manager,
                ontology_manager=orchestrator.core.ontology_manager,
                use_enhanced=True
            )
    else:
        # 기존 서비스 재사용 (LLM 연결만 확인)
        # Orchestrator가 새로 초기화되었을 수 있으므로 연결 갱신
        if "orchestrator" in st.session_state:
            orchestrator = st.session_state.orchestrator
            # 이미 연결되어 있어도 안전하게 재연결
            st.session_state.coa_service.initialize_llm_services(
                llm_manager=orchestrator.core.llm_manager,
                rag_manager=orchestrator.core.rag_manager,
                ontology_manager=orchestrator.core.ontology_manager,
                use_enhanced=True
            )
    
    return st.session_state.coa_service


def initialize_orchestrator(progress_callback=None):
    """
    Orchestrator 초기화 (LLM/RAG 서비스용)
    Args:
        progress_callback: 진행 상황 콜백 함수
    """
    if "orchestrator" not in st.session_state:
        config = load_config()
        st.session_state.orchestrator = Orchestrator(config, use_enhanced_ontology=True)
        # 진행 콜백 전달
        st.session_state.orchestrator.initialize(progress_callback=progress_callback)
        st.session_state.orchestrator_initialized = True  # 초기화 완료 플래그
    elif not st.session_state.get("orchestrator_initialized", False):
        # Orchestrator는 있지만 아직 초기화되지 않은 경우
        st.session_state.orchestrator.initialize(progress_callback=progress_callback)
        st.session_state.orchestrator_initialized = True
    
    return st.session_state.orchestrator


def render_threat_centered_ui(coa_service):
    """위협상황 중심 UI"""
    st.subheader("🎯 위협상황 중심 COA 생성")
    st.info("💡 **방어 작전**: 위협상황이 먼저 보고된 경우 사용")
    
    # 위협상황 선택 방법
    threat_input_method = st.radio(
        "위협상황 입력 방법",
        options=["위협상황 테이블에서 선택", "SITREP 텍스트 입력"],
        horizontal=True,
        key="threat_input_method"
    )
    
    threat_event = None
    threat_id = None
    
    if threat_input_method == "위협상황 테이블에서 선택":
        # 위협상황 테이블에서 선택
        try:
            threats_df = coa_service.data_manager.load_table('위협상황')
            if threats_df is not None and not threats_df.empty:
                threat_options = []
                # ID 컬럼 찾기
                id_col = None
                for col in threats_df.columns:
                    if col.upper() in ['ID', '위협ID', 'THREAT_ID', 'THREATID']:
                        id_col = col
                        break
                
                if id_col:
                    for idx, row in threats_df.iterrows():
                        threat_id_val = str(row.get(id_col, f'THREAT_{idx}'))
                        threat_type = str(row.get('위협유형코드', row.get('위협유형', 'N/A')))
                        threat_level = str(row.get('위협수준', 'N/A'))
                        axis_id = str(row.get('관련축선ID', 'N/A'))
                        
                        display_text = f"{threat_id_val} - {threat_type} ({threat_level}) - 축선: {axis_id}"
                        threat_options.append({
                            "display": display_text,
                            "threat_id": threat_id_val,
                            "row": row
                        })
                    
                    selected_threat_display = st.selectbox(
                        "위협상황 선택",
                        options=[opt["display"] for opt in threat_options],
                        key="selected_threat_display"
                    )
                    
                    selected_threat = next(
                        opt for opt in threat_options
                        if opt["display"] == selected_threat_display
                    )
                    threat_id = selected_threat["threat_id"]
                    threat_event = ThreatEvent.from_row(selected_threat["row"].to_dict())
                    
                    # 선택된 위협상황 정보 표시
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("위협유형", threat_event.threat_type_code or "N/A")
                    with col2:
                        st.metric("위협수준", threat_event.threat_level or "N/A")
                    with col3:
                        st.metric("관련축선", threat_event.related_axis_id or "N/A")
                else:
                    st.warning("위협상황 테이블에 ID 컬럼을 찾을 수 없습니다.")
            else:
                st.warning("위협상황 테이블을 불러올 수 없습니다.")
        except Exception as e:
            st.error(f"위협상황 테이블 로드 실패: {e}")
    
    else:  # SITREP 텍스트 입력
        sitrep_text = st.text_area(
            "상황보고(SITREP) 텍스트를 입력하세요",
            height=150,
            placeholder="예: 적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음.",
            key="sitrep_input_threat"
        )
        
        if sitrep_text:
            if st.button("SITREP 파싱", key="parse_sitrep_threat"):
                with st.spinner("SITREP 파싱 중..."):
                    try:
                        # 위협상황 중심이므로 임무는 나중에 자동 찾기
                        threat_event = coa_service.parse_sitrep_to_threat(
                            sitrep_text=sitrep_text,
                            mission_id=None,
                            use_llm=True
                        )
                        if threat_event:
                            st.success("✅ 위협상황 생성 완료")
                            threat_id = threat_event.threat_id
                            
                            # 생성된 위협상황 정보 표시
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("위협유형", threat_event.threat_type_code or "N/A")
                            with col2:
                                st.metric("위협수준", threat_event.threat_level or "N/A")
                            with col3:
                                st.metric("관련축선", threat_event.related_axis_id or "N/A")
                            
                            st.session_state["generated_threat_event"] = threat_event
                    except Exception as e:
                        st.error(f"오류: {e}")
        
        # 세션에 저장된 위협상황이 있으면 사용
        if "generated_threat_event" in st.session_state:
            threat_event = st.session_state["generated_threat_event"]
            threat_id = threat_event.threat_id
    
    # 전략 선택 (방어 전략으로 고정, 선택 가능하게)
    preferred_strategy = st.selectbox(
        "선호 전략",
        options=["defensive", "balanced"],
        index=0,
        key="threat_strategy",
        help="위협상황 중심은 방어 전략을 권장합니다"
    )
    
    # COA 생성 버튼
    if threat_event or threat_id:
        if st.button("🚀 COA 생성 및 평가 실행", type="primary", width='stretch', key="generate_coa_threat"):
            with st.spinner("COA 생성 및 평가 중..."):
                try:
                    result = coa_service.generate_coas_unified(
                        threat_id=threat_id,
                        threat_event=threat_event,
                        user_params={
                            "max_coas": 5,
                            "preferred_strategy": preferred_strategy,
                            "approach_mode": "threat_centered"
                        }
                    )
                    
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.session_state["coa_result"] = result
                        st.success("✅ COA 생성 및 평가 완료")
                        st.rerun()
                except Exception as e:
                    st.error(f"오류 발생: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        st.info("👆 위의 방법으로 위협상황을 입력하세요.")


def render_mission_centered_ui(coa_service):
    """임무 중심 UI (기존 방식)"""
    st.subheader("🎯 임무 중심 COA 생성")
    st.info("💡 **공격 작전**: 상급 부대에서 임무가 부여된 경우 사용")
    
    # 임무 선택
    missions = coa_service.get_available_missions()
    if not missions:
        st.error("임무 정보를 불러올 수 없습니다. 데이터 파일을 확인해주세요.")
        return
    
    mission_options = {
        f"{m['mission_id']} - {m['mission_name']}": m['mission_id']
        for m in missions
    }
    
    selected_mission_label = st.selectbox(
        "임무 선택",
        options=list(mission_options.keys()),
        key="selected_mission_mission_centered"
    )
    selected_mission_id = mission_options[selected_mission_label]
    
    # 임무 정보 표시
    try:
        missions_df = coa_service.data_manager.load_table('임무정보')
        if missions_df is not None and not missions_df.empty:
            mission_id_col = None
            mission_type_col = None
            primary_axis_col = None
            
            for col in missions_df.columns:
                if col.upper() in ['임무ID', 'MISSION_ID', 'MISSIONID']:
                    mission_id_col = col
                elif col.upper() in ['임무종류', 'MISSION_TYPE', 'MISSIONTYPE']:
                    mission_type_col = col
                elif col.upper() in ['주요축선ID', 'PRIMARY_AXIS_ID', 'PRIMARYAXISID']:
                    primary_axis_col = col
            
            if mission_id_col:
                mission_row = missions_df[missions_df[mission_id_col] == selected_mission_id]
                if not mission_row.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        if mission_type_col:
                            mission_type = mission_row.iloc[0].get(mission_type_col, 'N/A')
                            st.metric("임무 종류", mission_type)
                    with col2:
                        if primary_axis_col:
                            primary_axis = mission_row.iloc[0].get(primary_axis_col, 'N/A')
                            st.metric("주요 축선", primary_axis)
    except Exception as e:
        st.warning(f"임무 정보 표시 실패: {e}")
    
    # 전략 선택
    preferred_strategy = st.selectbox(
        "선호 전략",
        options=["defensive", "offensive", "balanced"],
        index=2,
        key="mission_strategy",
        help="임무 종류에 따라 적합한 전략을 선택하세요"
    )
    
    # COA 생성 버튼
    if st.button("🚀 COA 생성 및 평가 실행", type="primary", width='stretch', key="generate_coa_mission"):
        with st.spinner("COA 생성 및 평가 중..."):
            try:
                result = coa_service.generate_coas_unified(
                    mission_id=selected_mission_id,
                    user_params={
                        "max_coas": 5,
                        "preferred_strategy": preferred_strategy,
                        "approach_mode": "mission_centered"
                    }
                )
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.session_state["coa_result"] = result
                    st.success("✅ COA 생성 및 평가 완료")
                    st.rerun()
            except Exception as e:
                st.error(f"오류 발생: {e}")
                import traceback
                st.code(traceback.format_exc())


# 페이지 설정
st.set_page_config(
    page_title="COA Agent 데모",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 로드
try:
    css_path = BASE_DIR / "ui" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except Exception as e:
    st.warning(f"CSS 로드 실패: {e}")

# 제목
st.title("🎯 COA Agent 데모")
st.markdown("**작전 방안(COA) 생성 및 평가 시스템**")

# 초기화 (st.status 사용으로 개선)
if "orchestrator_initialized" not in st.session_state or not st.session_state.orchestrator_initialized:
    # 처음 로드 시에만 확장된 상태 상자 표시
    with st.status("시스템 초기화 중...", expanded=True) as status:
        st.write("초기화 프로세스를 시작합니다...")
        
        # 콜백 함수: 상태 상자에 메시지 출력
        def update_status(msg):
            st.write(f"👉 {msg}")
        
        orchestrator = initialize_orchestrator(progress_callback=update_status)
        coa_service = initialize_service()
        
        status.update(label="✅ 시스템 초기화 완료", state="complete", expanded=False)
else:
    # 이미 초기화된 경우 조용히 처리
    orchestrator = initialize_orchestrator()
    coa_service = initialize_service()

st.divider()

# ==================== 접근 방식 선택 ====================
st.header("📋 COA 생성")

# 접근 방식 선택
approach_mode = st.radio(
    "접근 방식 선택",
    options=["위협상황 중심 (방어 작전)", "임무 중심 (공격 작전)"],
    horizontal=True,
    key="coa_approach_mode",
    help="작전 유형에 따라 적합한 접근 방식을 선택하세요"
)

st.divider()

# 선택한 접근 방식에 따라 다른 UI 표시
if approach_mode == "위협상황 중심 (방어 작전)":
    render_threat_centered_ui(coa_service)
else:
    render_mission_centered_ui(coa_service)

st.divider()

st.divider()

# ==================== 출력 섹션 ====================
if "coa_result" not in st.session_state:
    st.info("👆 위의 'COA 생성 및 평가 실행' 버튼을 클릭하세요.")
    st.stop()

result = st.session_state["coa_result"]

# 접근 방식 표시
approach_mode = result.get("approach_mode", "unknown")
if approach_mode == "threat_centered":
    st.success("🎯 **위협상황 중심 접근** - 방어 작전")
    if "threat_id" in result:
        st.info(f"**위협상황 ID**: {result['threat_id']}")
    if "mission_id" in result:
        st.info(f"**자동 선택된 임무 ID**: {result['mission_id']}")
elif approach_mode == "mission_centered":
    st.success("🎯 **임무 중심 접근** - 공격 작전")
    if "mission_id" in result:
        st.info(f"**임무 ID**: {result['mission_id']}")

st.divider()

# 축선별 전장상태 요약
st.header("📊 축선별 전장상태 요약")

axis_states = result.get("axis_states", [])
if axis_states:
    cols = st.columns(min(len(axis_states), 3))
    for idx, axis_state in enumerate(axis_states[:3]):
        with cols[idx % len(cols)]:
            summary = coa_service.get_axis_state_summary(axis_state)
            st.subheader(f"축선: {summary['axis_name']}")
            st.metric("위협레벨", summary['threat_level'])
            st.metric("아군 전투력", f"{summary['friendly_combat_power']:.1f}")
            st.metric("적군 전투력", f"{summary['enemy_combat_power']:.1f}")
            st.metric("전투력 비율", f"{summary['combat_power_ratio']:.2f}")
            # 기동성등급은 None일 수 있음
            mobility = summary['mobility_grade']
            st.metric("기동성등급", f"{mobility:.1f}" if mobility is not None else "N/A")
            st.caption(f"제약조건: {summary['constraint_count']}개")
else:
    st.warning("축선별 전장상태 정보가 없습니다.")

st.divider()

# COA 후보 카드
st.header("🎯 COA 후보 (상위 3개)")

top_coas = result.get("top_coas", [])
if not top_coas:
    st.warning("COA 후보가 없습니다.")
else:
    # 상위 3개 COA를 카드 형태로 표시
    coa_cols = st.columns(3)
    
    for idx, coa_eval in enumerate(top_coas[:3]):
        with coa_cols[idx]:
            summary = coa_service.get_coa_summary(coa_eval)
            
            # 점수에 따른 색상 결정
            score = summary['total_score']
            if score >= 0.7:
                border_color = "#4CAF50"  # 녹색
                bg_color = "#E8F5E9"
            elif score >= 0.5:
                border_color = "#FF9800"  # 주황색
                bg_color = "#FFF3E0"
            else:
                border_color = "#F44336"  # 빨간색
                bg_color = "#FFEBEE"
            
            # 카드 스타일
            st.markdown(f"""
            <div style="
                border: 3px solid {border_color};
                border-radius: 10px;
                padding: 20px;
                margin: 10px 0;
                background-color: {bg_color};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <h3 style="color: {border_color}; margin-top: 0;">{summary['coa_name']}</h3>
                <h2 style="color: {border_color}; margin-bottom: 10px;">종합 점수: {summary['total_score']:.4f}</h2>
                <p style="color: #666; font-size: 0.9em;">순위: {idx + 1}위</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 점수 바 차트
            st.progress(summary['total_score'], text=f"종합 점수: {summary['total_score']:.2%}")
            
            # 세부 점수 (컴팩트하게)
            with st.expander("📊 세부 점수", expanded=False):
                st.metric("전투력 우세도", f"{summary['combat_power_score']:.2%}")
                st.metric("기동 가능성", f"{summary['mobility_score']:.2%}")
                st.metric("제약조건 준수도", f"{summary['constraint_compliance_score']:.2%}")
                st.metric("위협 대응도", f"{summary['threat_response_score']:.2%}")
                st.metric("위험도", f"{summary['risk_score']:.2%}")
            
            # 상세 설명 버튼
            button_key = f"show_detail_{idx}"
            if st.button(f"📖 상세 설명 보기", key=button_key, width='stretch'):
                st.session_state[f"show_coa_detail_{idx}"] = True
    
    # 선택한 COA의 상세 설명 표시
    for idx in range(len(top_coas[:3])):
        if st.session_state.get(f"show_coa_detail_{idx}", False):
            st.divider()
            
            # COA 정보 헤더
            coa_eval = top_coas[idx]
            summary = coa_service.get_coa_summary(coa_eval)
            
            col_header1, col_header2 = st.columns([3, 1])
            with col_header1:
                st.subheader(f"📖 {coa_eval.coa_name or coa_eval.coa_id} 상세 설명")
            with col_header2:
                st.metric("종합 점수", f"{summary['total_score']:.4f}")
            
            # 상세 설명 생성
            with st.spinner("상세 설명 생성 중..."):
                try:
                    explanation = coa_service.generate_coa_explanation(
                        coa_evaluation=coa_eval,
                        axis_states=axis_states,
                        language='ko',
                        use_llm=st.session_state.get("use_llm", True)
                    )
                    st.markdown(explanation)
                    
                    # 평가 세부 정보
                    with st.expander("📊 평가 세부 정보", expanded=False):
                        eval_dict = coa_eval.to_dict()
                        st.json(eval_dict)
                        
                except Exception as e:
                    st.error(f"설명 생성 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            
            if st.button(f"닫기", key=f"close_detail_{idx}"):
                st.session_state[f"show_coa_detail_{idx}"] = False
                st.rerun()

st.divider()

# 사이드바: 추가 정보
with st.sidebar:
    st.header("ℹ️ 정보")
    st.markdown(f"**생성된 COA 수**: {len(result.get('coas', []))}")
    st.markdown(f"**평가된 COA 수**: {len(result.get('evaluations', []))}")
    st.markdown(f"**축선 수**: {len(axis_states)}")
    
    st.divider()
    
    st.header("⚙️ 설정")
    use_llm = st.checkbox("LLM 사용", value=True, key="use_llm")
    preferred_strategy = st.selectbox(
        "선호 전략",
        options=["balanced", "defensive", "offensive"],
        index=0,
        key="preferred_strategy"
    )
    
    if st.button("설정 적용", width='stretch'):
        # 설정 재적용을 위해 결과 초기화
        if "coa_result" in st.session_state:
            del st.session_state["coa_result"]
        st.rerun()

