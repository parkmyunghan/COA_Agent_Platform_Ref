# ui/components/ontology_studio/quality_assurance.py
# -*- coding: utf-8 -*-
"""
품질 보증 컴포넌트
온톨로지 품질 검증 및 개선
"""
import streamlit as st
import pandas as pd
from core_pipeline.batch_validator import BatchValidator

def render_quality_assurance(orchestrator):
    """품질 보증 렌더링"""
    st.markdown("### ✅ 품질 보증 (Quality Assurance)")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if not ontology_manager or not ontology_manager.graph:
        st.warning("⚠️ 온톨로지 그래프가 없습니다.")
        return
    
    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "스키마 검증",
        "관계 품질 검증",
        "배치 검증",
        "품질 리포트"
    ])
    
    with sub_tab1:
        _render_schema_validation(orchestrator)
    
    with sub_tab2:
        _render_relationship_quality_validation(orchestrator)
    
    with sub_tab3:
        _render_batch_validation(orchestrator)
    
    with sub_tab4:
        _render_quality_report(orchestrator)

def _render_schema_validation(orchestrator):
    """스키마 검증"""
    st.markdown("#### ✅ 스키마 검증")
    
    if st.button("🚀 검증 실행", key="run_schema_valid"):
        with st.spinner("데이터 스키마 및 정합성 검사 중..."):
            from core_pipeline.ontology_validator import OntologyValidator
            validator = OntologyValidator(orchestrator.core.enhanced_ontology_manager)
            report = validator.validate_schema_compliance()
        
        # Scorecard
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("종합 점수", f"{report['overall_score']}%")
        
        # Detail Checks
        st.divider()
        
        # Axis Check
        axis_res = report.get('axis_compliance', {})
        with st.expander("1. 전장축선(Axis) 객체화 검증", expanded=True):
            for check in axis_res.get('checks', []):
                status_icon = "🟢" if check.get('status') == 'PASS' else "🔴"
                st.markdown(f"**{status_icon} {check.get('name', '')}**: {check.get('message', '')}")
        
        # Connectivity Check
        conn_res = report.get('connectivity_health', {})
        with st.expander("2. 데이터 연결성 검증", expanded=True):
            for check in conn_res.get('checks', []):
                status_icon = "🟢" if check.get('status') == 'PASS' else "🟡"
                st.markdown(f"**{status_icon} {check.get('name', '')}**: {check.get('message', '')}")
        
        # Reasoning Check
        reason_res = report.get('reasoning_status', {})
        with st.expander("3. 추론 엔진 상태", expanded=True):
            for check in reason_res.get('checks', []):
                status_icon = "🟢" if check.get('status') == 'PASS' else "⚪"
                st.markdown(f"**{status_icon} {check.get('name', '')}**: {check.get('message', '')}")
        
        # 검증 결과 표시
        if report['overall_score'] >= 80:
            st.success("✅ 검증 통과!")
        else:
            st.warning(f"⚠️ 검증 점수: {report['overall_score']}% (80% 이상 권장)")

def _render_relationship_quality_validation(orchestrator):
    """관계 품질 검증"""
    st.markdown("#### 🔍 관계 품질 검증")
    
    # 기존 relationship_quality_validator 재사용
    from ui.components.relationship_quality_validator import render_relationship_quality_validator
    render_relationship_quality_validator(orchestrator, show_title=False)

def _render_batch_validation(orchestrator):
    """배치 검증"""
    st.markdown("### 🔄 배치 검증 (Batch Validation)")
    st.info("💡 대량의 관계를 일괄적으로 검증하고 승인/거부할 수 있습니다.")
    
    # 검증 범위 선택
    validation_scope = st.radio(
        "검증 범위",
        ["전체 관계", "특정 관계 유형", "특정 테이블", "사용자 지정 필터"],
        key="batch_validation_scope"
    )
    
    # 검증 규칙 선택
    validation_rules = st.multiselect(
        "검증 규칙",
        [
            "관계 유효성 (노드 존재 확인)",
            "순환 참조 탐지",
            "중복 관계 탐지",
            "품질 점수 (Z-score 기반)",
            "관계 밀도 검증",
            "스키마 준수"
        ],
        default=["관계 유효성 (노드 존재 확인)", "순환 참조 탐지"],
        key="batch_validation_rules"
    )
    
    # 검증 실행
    if st.button("🚀 배치 검증 실행", type="primary", key="batch_validate_run"):
        with st.spinner("검증 중... (시간이 걸릴 수 있습니다)"):
            batch_validator = BatchValidator(orchestrator.core.enhanced_ontology_manager)
            results = batch_validator.validate(scope=validation_scope, rules=validation_rules)
            
            st.session_state.batch_validation_results = results
    
    # 검증 결과 표시
    if "batch_validation_results" in st.session_state:
        results = st.session_state.batch_validation_results
        
        st.markdown("#### 📊 검증 결과")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("전체", f"{results['total']:,}")
        with col2:
            passed_pct = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
            st.metric("통과", f"{results['passed']:,}", delta=f"{passed_pct:.1f}%")
        with col3:
            failed_pct = (results['failed'] / results['total'] * 100) if results['total'] > 0 else 0
            st.metric("실패", f"{results['failed']:,}", delta=f"-{failed_pct:.1f}%")
        with col4:
            st.metric("주의", f"{results['warning']:,}")
        
        # 결과 상세 표시
        st.divider()
        st.markdown("#### 📋 상세 결과")
        
        if results['details']:
            df_results = pd.DataFrame(results['details'])
            st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        # 배치 승인/거부
        st.divider()
        st.markdown("#### ✅ 배치 승인/거부")
        
        if results['failed'] == 0:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✅ 통과한 관계 일괄 승인", type="primary"):
                    st.success(f"✅ {results['passed']}개 관계가 승인되었습니다!")
        else:
            st.warning("⚠️ 실패한 관계가 있어 일괄 승인할 수 없습니다. 먼저 실패한 관계를 수정하세요.")

def _render_quality_report(orchestrator):
    """품질 리포트"""
    st.markdown("#### 📊 품질 리포트")
    st.info("💡 종합 품질 리포트를 생성하고 내보낼 수 있습니다.")
    
    if st.button("품질 리포트 생성", type="primary"):
        st.info("품질 리포트 생성 기능은 구현 예정입니다.")

