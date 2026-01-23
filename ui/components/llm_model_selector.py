# ui/components/llm_model_selector.py
# -*- coding: utf-8 -*-
"""
LLM 모델 선택 컴포넌트
"""
import streamlit as st
from typing import Optional

def render_llm_model_selector(llm_manager, key_prefix: str = "") -> Optional[str]:
    """
    LLM 모델 선택 UI 렌더링
    
    Args:
        llm_manager: LLMManager 인스턴스
        key_prefix: 세션 상태 키 접두사
        
    Returns:
        선택된 모델 키 (예: 'openai', 'local', 'internal_Qwen3-235B-A22B-GPTQ-Int4')
    """
    # 사용 가능한 모델 목록 가져오기
    available_models = llm_manager.get_available_models()
    
    # 모델별 표시 이름 생성
    model_options = []
    model_labels = []
    
    for model_key, model_info in available_models.items():
        available = model_info.get('available', False)
        name = model_info.get('name', model_key)
        description = model_info.get('description', '')
        
        # 사용 가능 여부 표시
        status_icon = "✅" if available else "❌"
        status_text = " (사용 가능)" if available else " (사용 불가)"
        
        label = f"{status_icon} {name}{status_text}"
        if description:
            label += f" - {description}"
        
        model_options.append(model_key)
        model_labels.append(label)
    
    # 세션 상태에서 이전 선택 가져오기
    session_key = f"{key_prefix}selected_llm_model"
    global_session_key = "selected_llm_manager"  # 전역 세션 키 (대시보드와 공유)
    
    # 전역 세션에서 먼저 확인 (다른 페이지에서 선택한 모델이 있으면 사용)
    if global_session_key in st.session_state:
        st.session_state[session_key] = st.session_state[global_session_key]
        llm_manager.set_selected_model(st.session_state[global_session_key])
    elif session_key not in st.session_state:
        # 기본값 선택 순서: gpt-4o → 사내망 첫 번째 → 로컬 모델
        if available_models.get('openai', {}).get('available', False):
            default_model = 'openai'
        else:
            # 사용 가능한 첫 번째 사내망 모델 찾기
            internal_models = [
                model_key for model_key, model_info in available_models.items()
                if model_key.startswith('internal_') and model_info.get('available', False)
            ]
            if internal_models:
                default_model = internal_models[0]
            elif available_models.get('local', {}).get('available', False):
                default_model = 'local'
            else:
                # 사용 가능한 첫 번째 모델
                default_model = None
                for model_key, model_info in available_models.items():
                    if model_info.get('available', False):
                        default_model = model_key
                        break
        
        if default_model:
            st.session_state[session_key] = default_model
            st.session_state[global_session_key] = default_model
            llm_manager.set_selected_model(default_model)
    
    # 모델 선택 드롭다운
    selected_index = model_options.index(st.session_state[session_key]) if st.session_state[session_key] in model_options else 0
    selected_model = st.selectbox(
        "🤖 사용할 LLM 모델",
        options=model_options,
        format_func=lambda x: model_labels[model_options.index(x)],
        index=selected_index,
        key=f"{key_prefix}llm_model_selectbox",
        help="사용할 LLM 모델을 선택하세요. 사용 가능한 모델만 선택할 수 있습니다."
    )
    
    # 선택된 모델 정보 표시
    if selected_model in available_models:
        model_info = available_models[selected_model]
        available = model_info.get('available', False)
        
        if available:
            st.success(f"✅ {model_info['name']} 모델이 선택되었습니다.")
        else:
            st.error(f"❌ {model_info['name']} 모델을 사용할 수 없습니다.")
            st.info("다른 모델을 선택하거나 네트워크 연결을 확인하세요.")
    
    # 세션 상태 업데이트 및 LLMManager에 설정
    st.session_state[session_key] = selected_model
    st.session_state[global_session_key] = selected_model  # 전역 세션에도 저장
    llm_manager.set_selected_model(selected_model)
    
    return selected_model

