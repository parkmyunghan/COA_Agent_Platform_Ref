# ui/components/dashboard_tab_settings.py
# -*- coding: utf-8 -*-
"""
탭 4: 설정 및 관리
"""
import streamlit as st
from ui.components.palantir_mode_toggle import render_palantir_mode_toggle
from ui.components.data_panel import render_data_panel
from ui.components.doc_manager import render_doc_manager


def render_settings_tab(orchestrator, config):
    """탭 4: 설정 및 관리"""
    
    st.header("설정 및 관리")
    st.markdown("시스템 설정 및 데이터 관리")
    
    # 시스템 설정
    st.subheader("시스템 설정")
    
    # 현재 LLM 모델 표시 (선택된 모델에 따라 동적 업데이트)
    llm_manager = orchestrator.core.llm_manager
    st.markdown("#### 현재 LLM 모델")
    selected_model_key = llm_manager.selected_model_key
    
    # 선택된 모델이 없으면 기본값 사용
    if not selected_model_key:
        if llm_manager.openai_available and llm_manager.use_openai:
            selected_model_key = 'openai'
        elif llm_manager.model is not None:
            selected_model_key = 'local'
        else:
            # 사용 가능한 첫 번째 모델 찾기
            available_models = llm_manager.get_available_models()
            for model_key, model_info in available_models.items():
                if model_info.get('available', False):
                    selected_model_key = model_key
                    break
    
    # 선택된 모델에 따라 모델명 표시
    if selected_model_key == 'openai':
        model_name = llm_manager.openai_model if llm_manager.openai_available else "OpenAI (사용 불가)"
        st.info(f"**OpenAI API**: {model_name}")
        st.caption("참고: OpenAI API를 사용합니다. API 호출 실패 시 로컬 모델로 자동 전환됩니다.")
    elif selected_model_key == 'local':
        if llm_manager.model is not None:
            model_path = llm_manager.model_path or "로컬 모델"
            if model_path:
                import os
                model_name = os.path.basename(model_path) if model_path else "로컬 모델"
                st.info(f"**로컬 모델**: {model_name}")
                st.caption(f"경로: {model_path}")
            else:
                st.info("**로컬 모델**: 경로 정보 없음")
        else:
            st.warning("**로컬 모델**: 미로드")
            st.caption("참고: 로컬 모델이 아직 로드되지 않았습니다. Agent 실행 시 자동으로 로드됩니다.")
    elif selected_model_key and selected_model_key.startswith('internal_'):
        # 사내망 모델
        model_key = selected_model_key.replace('internal_', '')
        if model_key in llm_manager.internal_models:
            model_info = llm_manager.internal_models[model_key]
            model_name = model_info.get('name', model_key)
            model_url = model_info.get('url', '')
            st.info(f"**사내망 모델**: {model_name}")
            st.caption(f"URL: {model_url}")
        else:
            st.warning(f"**사내망 모델**: {model_key} (설정 없음)")
    else:
        st.warning("[WARN] 모델이 선택되지 않았습니다.")
        st.caption("참고: 채팅 인터페이스에서 모델을 선택하세요.")
    
    st.divider()
    
    # 팔란티어 모드 토글
    render_palantir_mode_toggle(key_prefix="settings_")
    
    st.divider()
    
    # 단계별 페이지로 이동
    st.subheader("단계별 페이지")
    st.markdown("""
    세부 워크플로우는 다음 단계별 페이지에서 수행하세요:
    
    - **1단계: 데이터 관리** - 데이터 로드, 편집, 검증
    - **2단계: 온톨로지 생성** - 그래프 생성 및 관계 관리
    - **3단계: 지식그래프 조회** - SPARQL 쿼리 및 그래프 탐색
    - **4단계: RAG 인덱스 구성** - 문서 업로드 및 인덱스 관리
    - **5단계: Agent 실행** - LLM 질문 및 상세 상호작용
    - **6단계: 성능 모니터링** - 성능 분석 및 벤치마크
    
    💡 좌측 사이드바에서 각 페이지로 이동할 수 있습니다.
    """)

