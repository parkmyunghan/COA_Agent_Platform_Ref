# ui/dashboard.py
# -*- coding: utf-8 -*-
"""
Defense Intelligent Agent Platform - Main Entry Point
네비게이션 구조 정의 및 페이지 라우팅
"""
# Streamlit Dashboard Entry Point (Reload Triggered v18)
import streamlit as st
import sys
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

# 로거 초기화 (애플리케이션 시작 시)
from common.logger import get_logger
logger = get_logger("DefenseAI")
logger.info("애플리케이션 시작")

# 페이지 설정 (가장 먼저 호출)
st.set_page_config(
    page_title="Defense AI Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 로드
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    load_css("ui/style.css")
except FileNotFoundError:
    st.warning("ui/style.css 파일을 찾을 수 없습니다.")

# 페이지 정의
# 순환형 워크플로우 기반 페이지 구성

# Phase 1: 준비 및 설계 (Preparation & Design)
preparation_pages = [
    st.Page("views/data_management.py", title="데이터 관리", icon="💾"),
    st.Page("views/ontology_studio.py", title="온톨로지 스튜디오", icon="📊"),
]

# Phase 2: 구축 (Construction)
construction_pages = [
    st.Page("views/ontology_generation.py", title="온톨로지 생성", icon="🕸️"),
    st.Page("views/rag_indexing.py", title="RAG 인덱스 구성", icon="📚"),
]

# Phase 3: 검증 및 배포 (Validation & Deployment)
# 승인 및 배포는 온톨로지 스튜디오 내부에 통합

# Phase 4: 사용 (Usage)
usage_pages = [
    st.Page("views/knowledge_graph.py", title="지식 탐색", icon="🔍"),
    st.Page("views/agent_execution.py", title="지휘통제/분석", icon="🤖", default=True),
]

# Phase 5: 모니터링 및 개선 (Monitoring & Improvement)
# 성능 모니터링은 온톨로지 스튜디오 내부에 통합

# 학습 및 가이드 (Learning)
learning_pages = [
    st.Page("views/learning_guide.py", title="시스템 소개", icon="📖"),
]

# 네비게이션 구성 (워크플로우 순서대로)
pg = st.navigation({
    "Phase 1: 준비 및 설계": preparation_pages,
    "Phase 2: 구축": construction_pages,
    "Phase 4: 사용": usage_pages,
    "학습 및 가이드": learning_pages
})

# 페이지 실행
pg.run()
