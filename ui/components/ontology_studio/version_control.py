# ui/components/ontology_studio/version_control.py
# -*- coding: utf-8 -*-
"""
버전 관리 컴포넌트
변경 이력 추적 및 롤백
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from core_pipeline.ontology_history import OntologyHistory

def render_version_control(orchestrator):
    """버전 관리 렌더링"""
    st.markdown("### 📜 버전 관리 (Version Control)")
    st.info("💡 온톨로지 변경 이력을 추적하고 필요시 롤백할 수 있습니다.")
    
    # 히스토리 관리자 초기화
    if "history_manager" not in st.session_state:
        st.session_state.history_manager = OntologyHistory()
    history_manager = st.session_state.history_manager
    
    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "변경 이력",
        "버전 비교",
        "롤백",
        "감사 로그"
    ])
    
    with sub_tab1:
        _render_change_history(orchestrator, history_manager)
    
    with sub_tab2:
        _render_version_comparison(orchestrator, history_manager)
    
    with sub_tab3:
        _render_rollback(orchestrator, history_manager)
    
    with sub_tab4:
        _render_audit_log(orchestrator, history_manager)

def _render_change_history(orchestrator, history_manager: OntologyHistory):
    """변경 이력"""
    st.markdown("#### 📜 변경 이력")
    
    # 필터 옵션
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_source = st.text_input("소스 노드 필터", key="history_filter_source")
    with col2:
        filter_target = st.text_input("타겟 노드 필터", key="history_filter_target")
    with col3:
        filter_relation = st.text_input("관계명 필터", key="history_filter_relation")
    
    # 날짜 범위 선택
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("시작 날짜", key="history_date_from")
    with col2:
        date_to = st.date_input("종료 날짜", key="history_date_to")
    
    # 히스토리 조회
    if st.button("🔍 히스토리 조회", type="primary"):
        history_entries = history_manager.get_history(
            source=filter_source if filter_source else None,
            target=filter_target if filter_target else None,
            relation=filter_relation if filter_relation else None,
            date_from=date_from.isoformat() if date_from else None,
            date_to=date_to.isoformat() if date_to else None,
            limit=1000
        )
        
        if history_entries:
            # 히스토리 표시
            df_history = pd.DataFrame(history_entries)
            # 필요한 컬럼만 선택
            display_cols = ['timestamp', 'change_type', 'source', 'relation', 'target', 'user']
            available_cols = [col for col in display_cols if col in df_history.columns]
            st.dataframe(df_history[available_cols], use_container_width=True, hide_index=True)
            
            st.session_state.history_entries = history_entries
        else:
            st.info("조회된 히스토리가 없습니다.")

def _render_version_comparison(orchestrator, history_manager: OntologyHistory):
    """버전 비교"""
    st.markdown("#### 🔄 버전 비교")
    st.info("💡 버전 간 차이점을 비교할 수 있습니다.")
    
    st.info("버전 비교 기능은 구현 예정입니다.")

def _render_rollback(orchestrator, history_manager: OntologyHistory):
    """롤백"""
    st.markdown("#### 🔄 롤백")
    st.warning("⚠️ 롤백은 이전 상태로 되돌립니다. 신중하게 선택하세요.")
    
    if "history_entries" in st.session_state and st.session_state.history_entries:
        history_entries = st.session_state.history_entries
        
        selected_entry_id = st.selectbox(
            "롤백할 변경 선택",
            options=[(i, entry) for i, entry in enumerate(history_entries)],
            format_func=lambda x: f"{x[1].get('timestamp', '')} - {x[1].get('change_type', '')} - {x[1].get('source', '')} → {x[1].get('target', '')}",
            key="history_rollback_select"
        )
        
        if selected_entry_id is not None:
            if st.button("🔄 롤백 실행", type="primary"):
                with st.spinner("롤백 중..."):
                    entry = history_entries[selected_entry_id[0]]
                    success = history_manager.rollback(entry.get('entry_id'), orchestrator.core.enhanced_ontology_manager)
                    if success:
                        st.success("✅ 롤백 완료!")
                        st.rerun()
                    else:
                        st.error("롤백 실패")
    else:
        st.info("먼저 변경 이력을 조회하세요.")

def _render_audit_log(orchestrator, history_manager: OntologyHistory):
    """감사 로그"""
    st.markdown("#### 📋 감사 로그")
    st.info("💡 전체 활동 로그를 확인할 수 있습니다.")
    
    # 전체 히스토리 조회
    all_history = history_manager.get_history(limit=1000)
    
    if all_history:
        df_audit = pd.DataFrame(all_history)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)
    else:
        st.info("감사 로그가 없습니다.")

