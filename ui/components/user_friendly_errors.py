# ui/components/user_friendly_errors.py
# -*- coding: utf-8 -*-
"""
사용자 친화적 에러 메시지 컴포넌트
기술적 에러를 사용자 친화적인 메시지로 변환
"""
import streamlit as st
import traceback
from typing import Optional, Dict


# 에러 타입별 사용자 친화적 메시지
ERROR_MESSAGES = {
    "FileNotFoundError": {
        "message": "필요한 데이터 파일을 찾을 수 없습니다.",
        "solution": "1단계: 데이터 관리 페이지에서 데이터 파일을 확인하세요.",
        "action_text": "데이터 관리 페이지로 이동",
        "action_page": "1_📊_데이터_관리"
    },
    "GraphNotBuilt": {
        "message": "온톨로지 그래프가 생성되지 않았습니다.",
        "solution": "2단계: 온톨로지 생성 페이지에서 그래프를 생성하세요.",
        "action_text": "온톨로지 생성 페이지로 이동",
        "action_page": "2_🕸_온톨로지_생성"
    },
    "RAGIndexNotFound": {
        "message": "RAG 인덱스가 구성되지 않았습니다.",
        "solution": "4단계: RAG 인덱스 구성 페이지에서 문서를 업로드하고 인덱스를 구축하세요.",
        "action_text": "RAG 인덱스 구성 페이지로 이동",
        "action_page": "4_📂_RAG_인덱스_구성"
    },
    "DataLoadError": {
        "message": "데이터를 로드할 수 없습니다.",
        "solution": "데이터 파일이 올바른 형식인지 확인하고, 1단계: 데이터 관리 페이지에서 데이터를 확인하세요.",
        "action_text": "데이터 관리 페이지로 이동",
        "action_page": "1_📊_데이터_관리"
    },
    "ModelNotLoaded": {
        "message": "AI 모델이 로드되지 않았습니다.",
        "solution": "시스템 초기화를 다시 시도하거나, 설정에서 모델 경로를 확인하세요.",
        "action_text": "시스템 재시작",
        "action_page": None
    },
    "SPARQLQueryError": {
        "message": "온톨로지 쿼리 실행에 실패했습니다.",
        "solution": "온톨로지 그래프가 올바르게 생성되었는지 확인하고, 2단계: 온톨로지 생성 페이지에서 그래프를 다시 생성하세요.",
        "action_text": "온톨로지 생성 페이지로 이동",
        "action_page": "2_🕸_온톨로지_생성"
    }
}


def render_user_friendly_error(error: Exception, context: Optional[str] = None):
    """
    사용자 친화적 에러 메시지 렌더링
    
    Args:
        error: 발생한 에러
        context: 에러 컨텍스트 설명
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    # 에러 타입 매핑
    mapped_error_type = map_error_type(error_type, error_message)
    
    if mapped_error_type in ERROR_MESSAGES:
        error_info = ERROR_MESSAGES[mapped_error_type]
        
        # 에러 메시지 표시
        st.error(f"❌ **{error_info['message']}**")
        
        if context:
            st.caption(f"컨텍스트: {context}")
        
        # 해결 방법 표시
        st.info(f"💡 **해결 방법:** {error_info['solution']}")
        
        # 액션 버튼
        if error_info.get("action_text"):
            if error_info.get("action_page"):
                st.button(
                    f"🔗 {error_info['action_text']}",
                    key=f"error_action_{mapped_error_type}",
                    help=f"좌측 사이드바에서 '{error_info['action_page']}' 페이지를 선택하세요."
                )
            else:
                st.button(
                    error_info['action_text'],
                    key=f"error_action_{mapped_error_type}"
                )
        
        # 기술적 상세 정보 (접을 수 있게)
        with st.expander("🔧 기술적 상세 정보 (개발자용)", expanded=False):
            st.code(f"에러 타입: {error_type}\n에러 메시지: {error_message}")
            st.code(traceback.format_exc())
    else:
        # 일반 에러 처리
        st.error(f"❌ **오류 발생:** {error_message}")
        
        if context:
            st.caption(f"컨텍스트: {context}")
        
        st.info("💡 문제가 지속되면 시스템을 재시작하거나 관리자에게 문의하세요.")
        
        # 기술적 상세 정보
        with st.expander("🔧 기술적 상세 정보", expanded=False):
            st.code(f"에러 타입: {error_type}\n에러 메시지: {error_message}")
            st.code(traceback.format_exc())


def map_error_type(error_type: str, error_message: str) -> str:
    """
    에러 타입을 매핑된 타입으로 변환
    
    Args:
        error_type: 원본 에러 타입
        error_message: 에러 메시지
        
    Returns:
        매핑된 에러 타입
    """
    # FileNotFoundError 관련
    if error_type == "FileNotFoundError" or "파일을 찾을 수 없습니다" in error_message:
        if "graph" in error_message.lower() or "ontology" in error_message.lower():
            return "GraphNotBuilt"
        elif "index" in error_message.lower() or "rag" in error_message.lower():
            return "RAGIndexNotFound"
        else:
            return "FileNotFoundError"
    
    # 데이터 로드 관련
    if "데이터" in error_message or "data" in error_message.lower():
        if "로드" in error_message or "load" in error_message.lower():
            return "DataLoadError"
    
    # 모델 관련
    if "모델" in error_message or "model" in error_message.lower():
        if "로드" in error_message or "load" in error_message.lower():
            return "ModelNotLoaded"
    
    # SPARQL 관련
    if "sparql" in error_message.lower() or "쿼리" in error_message:
        return "SPARQLQueryError"
    
    # 그래프 관련
    if "그래프" in error_message or "graph" in error_message.lower():
        if "없" in error_message or "not" in error_message.lower():
            return "GraphNotBuilt"
    
    # 기본값
    return error_type


def render_error_summary(errors: list):
    """
    에러 요약 표시
    
    Args:
        errors: 에러 리스트
    """
    if not errors:
        return
    
    st.warning(f"⚠️ {len(errors)}개의 오류가 발생했습니다.")
    
    for i, error in enumerate(errors[:5], 1):  # 최대 5개만 표시
        with st.expander(f"오류 {i}: {type(error).__name__}", expanded=False):
            render_user_friendly_error(error)


def safe_execute(func, default_return=None, error_context: Optional[str] = None):
    """
    안전한 함수 실행 (에러 처리 포함)
    
    Args:
        func: 실행할 함수
        default_return: 에러 발생 시 반환할 기본값
        error_context: 에러 컨텍스트
        
    Returns:
        함수 결과 또는 default_return
    """
    try:
        return func()
    except Exception as e:
        render_user_friendly_error(e, error_context)
        return default_return


