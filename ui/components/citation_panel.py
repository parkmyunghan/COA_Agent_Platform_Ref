# ui/components/citation_panel.py
# -*- coding: utf-8 -*-
"""
문서 인용 패널 컴포넌트
RAG 검색 결과를 표시하고 하이라이트 기능 제공
"""
import streamlit as st
import re


def render_citation_panel(retrieved_results, highlight_query: str = None):
    """
    RAG 검색 근거 목록 표시
    
    Args:
        retrieved_results: RAG 검색 결과 리스트
        highlight_query: 하이라이트할 검색어
    """
    if not retrieved_results:
        st.info("검색 결과가 없습니다.")
        return
    
    st.markdown("### 📚 참고 문서 근거")
    
    for i, result in enumerate(retrieved_results, 1):
        text = result.get("text", "")
        score = result.get("score", 0.0)
        doc_id = result.get("doc_id", i - 1)
        metadata = result.get("metadata", {})
        
        # 근거 카드
        with st.expander(f"📑 근거 [{i}] (점수: {score:.4f})", expanded=(i == 1)):
            # 메타데이터 표시
            if metadata:
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"문서 ID: {doc_id}")
                with col2:
                    if "chunk_index_in_doc" in metadata:
                        st.caption(f"청크: {metadata['chunk_index_in_doc'] + 1}")
            
            # 텍스트 표시 (하이라이트 포함)
            if highlight_query and highlight_query in text:
                # 검색어 하이라이트
                highlighted_text = text.replace(
                    highlight_query,
                    f"<mark style='background-color: yellow;'>{highlight_query}</mark>"
                )
                st.markdown(highlighted_text, unsafe_allow_html=True)
            else:
                # st.text 대신 st.markdown 사용 (다크 테마 호환성 및 줄바꿈 개선)
                st.markdown(text)
            
            # 점수 바
            st.progress(min(score, 1.0))
            st.caption(f"관련도 점수: {score:.4f}")


def highlight_citations_in_text(text: str, citation_pattern: str = r'\(\d+\)') -> str:
    """
    텍스트에서 인용 번호를 하이라이트
    
    Args:
        text: 원본 텍스트
        citation_pattern: 인용 패턴 (기본: (1), (2) 등)
        
    Returns:
        하이라이트된 HTML 텍스트
    """
    # 인용 번호 찾기
    pattern = re.compile(citation_pattern)
    highlighted = pattern.sub(
        lambda m: f"<span style='background-color: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;'>{m.group()}</span>",
        text
    )
    return highlighted


def render_citation_summary(retrieved_results):
    """
    인용 요약 표시 (간단한 리스트 형태)
    
    Args:
        retrieved_results: RAG 검색 결과 리스트
    """
    if not retrieved_results:
        return
    
    st.markdown("#### 📋 근거 요약")
    
    summary_data = []
    for i, result in enumerate(retrieved_results, 1):
        text = result.get("text", "")
        score = result.get("score", 0.0)
        # 첫 100자만 표시
        preview = text[:100] + "..." if len(text) > 100 else text
        summary_data.append({
            "번호": i,
            "점수": f"{score:.4f}",
            "내용 미리보기": preview
        })
    
    import pandas as pd
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, width='stretch', hide_index=True)



