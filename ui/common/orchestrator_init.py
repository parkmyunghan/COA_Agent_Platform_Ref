# ui/common/orchestrator_init.py
# -*- coding: utf-8 -*-
"""
Orchestrator 초기화 공통 함수
모든 페이지에서 동일한 방식으로 Orchestrator를 초기화하기 위한 유틸리티
"""
import streamlit as st
from core_pipeline.orchestrator import Orchestrator
from typing import Optional


def get_or_initialize_orchestrator(config: dict, key: str = "main_orchestrator") -> Optional[Orchestrator]:
    """
    Orchestrator를 가져오거나 초기화합니다.
    
    Args:
        config: 설정 딕셔너리
        key: session_state에 저장할 키 (기본: "main_orchestrator")
        
    Returns:
        Orchestrator 인스턴스
    """
    # 이미 초기화된 경우 바로 반환
    if key in st.session_state:
        orchestrator = st.session_state[key]
        # 초기화 플래그 확인 (이미 initialize()가 호출되었는지)
        if hasattr(orchestrator, 'core') and hasattr(orchestrator.core, '_initialized') and orchestrator.core._initialized:
            return orchestrator
        # 초기화되지 않은 경우에만 초기화
        if not hasattr(orchestrator, 'core') or not hasattr(orchestrator.core, '_initialized'):
            orchestrator.initialize()
        return orchestrator
    
    # 새로 생성
    with st.spinner("시스템 초기화 중..."):
        try:
            orchestrator = Orchestrator(config, use_enhanced_ontology=True)
            orchestrator.initialize()
            st.session_state[key] = orchestrator
            st.success("[OK] 시스템 초기화 완료 (Enhanced Ontology Manager 활성화)")
            return orchestrator
        except Exception as e:
            st.error(f"시스템 초기화 실패: {e}")
            st.stop()
            return None




