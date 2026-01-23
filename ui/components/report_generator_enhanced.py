# ui/components/report_generator_enhanced.py
# -*- coding: utf-8 -*-
"""
강화된 보고서 생성 UI
"""
import streamlit as st
from pathlib import Path
import os
from ui.components.report_engine import ReportEngine


def render_report_generator(agent_result=None, situation_info=None):
    """강화된 보고서 생성 UI"""
    
    st.subheader("보고서 생성")
    
    # 보고서 타입 선택
    report_type = st.selectbox(
        "보고서 타입",
        options=[
            "상황 분석 보고서",
            "방책 추천 보고서",
            "의사결정 근거 보고서",
            "실행 계획서"
        ],
        key="report_type_select"
    )
    
    # 출력 형식 선택
    output_format = st.radio(
        "출력 형식",
        options=["PDF", "Word (DOCX)", "HTML", "Excel (XLSX)"],
        horizontal=True,
        key="report_format_select"
    )
    
    # 커스터마이징 옵션
    with st.expander("보고서 커스터마이징", expanded=False):
        include_charts = st.checkbox("차트 포함", value=True, key="include_charts")
        include_details = st.checkbox("상세 정보 포함", value=True, key="include_details")
        include_appendix = st.checkbox("부록 포함", value=False, key="include_appendix")
    
    # 생성 버튼
    if st.button("보고서 생성", type="primary", width='stretch'):
        with st.spinner("보고서 생성 중..."):
            report_engine = ReportEngine()
            
            # 보고서 타입 매핑
            type_mapping = {
                "상황 분석 보고서": "situation",
                "방책 추천 보고서": "coa",
                "의사결정 근거 보고서": "rationale",
                "실행 계획서": "execution"
            }
            
            report_type_key = type_mapping.get(report_type, "coa")
            format_key = output_format.lower().replace("word (docx)", "docx").replace("html", "html").replace("excel (xlsx)", "xlsx")
            
            try:
                if report_type == "상황 분석 보고서":
                    if not situation_info:
                        st.warning("상황 정보가 없습니다. 먼저 상황을 입력해주세요.")
                        return
                    report_path = report_engine.generate_situation_report(
                        situation_info, format=format_key
                    )
                elif report_type == "방책 추천 보고서":
                    if not agent_result:
                        st.warning("Agent 실행 결과가 없습니다. 먼저 Agent를 실행해주세요.")
                        return
                    report_path = report_engine.generate_coa_report(
                        agent_result, format=format_key
                    )
                elif report_type == "의사결정 근거 보고서":
                    if not agent_result:
                        st.warning("Agent 실행 결과가 없습니다. 먼저 Agent를 실행해주세요.")
                        return
                    report_path = report_engine.generate_rationale_report(
                        agent_result, format=format_key
                    )
                elif report_type == "실행 계획서":
                    if not agent_result:
                        st.warning("Agent 실행 결과가 없습니다. 먼저 Agent를 실행해주세요.")
                        return
                    recommendations = agent_result.get("recommendations", [])
                    if not recommendations:
                        st.warning("추천된 방책이 없습니다.")
                        return
                    report_path = report_engine.generate_execution_plan(
                        recommendations[0],
                        agent_result.get("situation_info"),
                        format=format_key
                    )
                else:
                    st.error("알 수 없는 보고서 타입입니다.")
                    return
                
                if report_path and os.path.exists(report_path):
                    st.success("[OK] 보고서 생성 완료!")
                    
                    # 다운로드 버튼
                    with open(report_path, "rb") as report_file:
                        file_extension = Path(report_path).suffix
                        mime_types = {
                            ".pdf": "application/pdf",
                            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            ".html": "text/html"
                        }
                        mime_type = mime_types.get(file_extension, "application/octet-stream")
                        
                        st.download_button(
                            label=f"📥 {output_format} 다운로드",
                            data=report_file.read(),
                            file_name=os.path.basename(report_path),
                            mime=mime_type,
                            width='stretch'
                        )
                    
                    # 미리보기 (HTML인 경우)
                    if output_format == "HTML" and report_path.endswith(".html"):
                        st.divider()
                        st.subheader("미리보기")
                        with open(report_path, 'r', encoding='utf-8') as f:
                            st.components.v1.html(f.read(), height=600, scrolling=True)
                else:
                    st.error("보고서 생성에 실패했습니다.")
                    
            except Exception as e:
                st.error(f"보고서 생성 중 오류 발생: {e}")
                import traceback
                st.code(traceback.format_exc())


def render_report_generator_in_tab(agent_result=None, situation_info=None):
    """탭 내에서 사용할 보고서 생성 UI (간소화 버전)"""
    
    # Agent 결과가 있는 경우에만 표시
    if not agent_result:
        return
    
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**보고서 생성**")
    with col2:
        if st.button("보고서 생성", width='stretch'):
            st.session_state.show_report_generator = True
    
    if st.session_state.get("show_report_generator", False):
        render_report_generator(agent_result, situation_info)

