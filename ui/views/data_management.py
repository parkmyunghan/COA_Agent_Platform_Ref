# ui/views/data_management.py
# -*- coding: utf-8 -*-
"""
데이터 관리 페이지
데이터 로드, 편집, 컬럼 추가
"""
import streamlit as st
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

from ui.components.data_panel import render_data_panel
# from ui.components.pipeline_status import render_pipeline_status  # 학습 페이지로 이동
from ui.components.data_quality_checker import render_data_quality_checker
from ui.components.user_friendly_errors import render_user_friendly_error
from core_pipeline.orchestrator import Orchestrator
import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


st.set_page_config(
    page_title="데이터 관리",
    layout="wide"
)

# 제목 (Compact Style Upgrade)
# 상단 여백 최소화 및 컴팩트 헤더 스타일 적용
st.markdown("""
<style>
    /* 상단 여백 최소화 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0rem !important;
    }
    /* Plan B: 헤더 전체를 숨기지 않고 투명화하여 버튼 기능 복구 */
    header[data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: none !important;  /* Streamlit 기본 구분선 제거 */
    }
    
    /* 데코레이션(줄무늬) 숨김 */
    [data-testid="stDecoration"] {
        display: none;
    }

    /* 사이드바 토글 버튼 강제 노출 */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        color: #e6edf3 !important;
    }
    
    /* 컴팩트 헤더 스타일 */
    .compact-header {
        background-color: #0e1117 !important;
        border-bottom: 1px solid #30363d !important;
        padding-bottom: 5px !important;
        margin-bottom: 8px !important;  /* 본문과의 간격 축소 */
        display: flex !important;
        flex-wrap: wrap;  /* 작은 화면에서 줄바꿈 허용 */
        width: 100%;  /* 브라우저 너비에 맞춤 */
        justify-content: space-between !important;
        align-items: center !important;
    }
    .header-title {
        display: block !important;
        visibility: visible !important;
        font-family: 'Roboto Mono', monospace !important; 
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        color: #2E9AFE !important; /* Distinct Blue Color */
        text-transform: uppercase !important;
    }
    .header-subtitle {
        display: block !important;
        visibility: visible !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.85rem !important;
        color: #8b949e !important;
    }
</style>

<div class="compact-header">
    <div class="header-title">
        데이터 관리
    </div>
    <div class="header-subtitle">
        원천 데이터 로드, 편집, 컬럼 추가
    </div>
</div>
""", unsafe_allow_html=True)


# CSS 로드
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    pass  # load_css("ui/style.css") - 주석 처리: 커스텀 헤더와 충돌 방지
except FileNotFoundError:
    pass  # st.warning("ui/style.css 파일을 찾을 수 없습니다.")



# 설정 파일 로드
try:
    config = load_yaml("./config/global.yaml")
except Exception as e:
    render_user_friendly_error(e, "설정 파일 로드")
    st.stop()

# Orchestrator 초기화 (Enhanced Ontology Manager 사용)
# 이미 초기화 완료 플래그가 있으면 초기화 로직 건너뛰기
if st.session_state.get("main_orchestrator_initialized", False):
    # 이미 초기화 완료 - 아무 작업도 하지 않음
    pass
elif "main_orchestrator" not in st.session_state:
    # Orchestrator가 없으면 새로 생성 및 초기화
    with st.spinner("시스템 초기화 중..."):
        try:
            st.session_state.main_orchestrator = Orchestrator(config, use_enhanced_ontology=True)
            st.session_state.main_orchestrator.initialize()
            st.session_state.main_orchestrator_initialized = True
            st.success("[OK] 시스템 초기화 완료 (Enhanced Ontology Manager 활성화)")
        except Exception as e:
            render_user_friendly_error(e, "시스템 초기화")
            st.stop()
else:
    # Orchestrator는 있지만 초기화 플래그가 없는 경우
    # 실제 초기화 상태 확인 (중복 초기화 방지)
    if hasattr(st.session_state.main_orchestrator, 'core') and \
       hasattr(st.session_state.main_orchestrator.core, '_initialized') and \
       st.session_state.main_orchestrator.core._initialized:
        # 이미 초기화되었으면 플래그만 업데이트 (spinner 없이)
        st.session_state.main_orchestrator_initialized = True
    else:
        # 실제로 초기화가 필요한 경우에만 spinner 표시
        with st.spinner("시스템 초기화 중..."):
            try:
                st.session_state.main_orchestrator.initialize()
                st.session_state.main_orchestrator_initialized = True
            except Exception as e:
                render_user_friendly_error(e, "시스템 초기화")
                st.stop()

orchestrator = st.session_state.main_orchestrator

# 시스템 아키텍처 다이어그램 제거됨 - 학습 페이지로 이동
# st.header("시스템 아키텍처")
# render_pipeline_status(config, show_diagram=True)

# st.divider()  # 제거: 헤더 아래 불필요한 구분선

# 데이터 품질 검증
st.header("데이터 품질 검증")
render_data_quality_checker(orchestrator.core.data_manager, config)

st.divider()

# 데이터 관리 패널
st.header("데이터 테이블 관리")
render_data_panel(config, orchestrator.core)

st.divider()
