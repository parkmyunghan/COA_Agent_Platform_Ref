# ui/components/ontology_studio/approval_deployment.py
# -*- coding: utf-8 -*-
"""
승인 및 배포 컴포넌트
검증 완료 후 승인 및 프로덕션 배포 프로세스
"""
import streamlit as st
from datetime import datetime
from typing import Dict
from core_pipeline.ontology_workflow_manager import (
    OntologyWorkflowManager, StepStatus, WorkflowPhase
)

def render_approval_deployment(orchestrator, workflow_manager: OntologyWorkflowManager):
    """승인 및 배포 렌더링"""
    st.markdown("### 📜 승인 및 배포")
    st.info("💡 검증을 통과한 온톨로지를 승인하고 프로덕션 환경에 배포합니다.")
    
    # 검증 상태 확인
    validation_status = workflow_manager.get_step_status("quality_validation")
    
    if validation_status != StepStatus.VALIDATED:
        st.warning("⚠️ 품질 검증을 먼저 완료해야 합니다.")
        st.info("💡 **품질 보증** 탭에서 검증을 실행하세요.")
        return
    
    # 검증 결과 표시
    validation_results = _get_validation_results(workflow_manager)
    
    st.markdown("#### ✅ 검증 결과 요약")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체", validation_results.get('total', 0))
    with col2:
        pass_rate = validation_results.get('pass_rate', 0)
        st.metric("통과", validation_results.get('passed', 0), 
                 delta=f"{pass_rate:.1f}%")
    with col3:
        st.metric("실패", validation_results.get('failed', 0))
    with col4:
        st.metric("주의", validation_results.get('warning', 0))
    
    st.divider()
    
    # 승인 워크플로우
    approval_status = workflow_manager.get_step_status("approval_deployment")
    
    if approval_status == StepStatus.NOT_STARTED:
        st.markdown("#### 📝 승인 요청")
        
        # 승인 정보 입력
        approver_name = st.text_input("승인자 이름", key="approver_name")
        approval_comments = st.text_area("승인 의견 (선택)", key="approval_comments")
        
        if st.button("승인 요청 생성", type="primary"):
            workflow_manager.update_step_status(
                "approval_deployment",
                StepStatus.IN_PROGRESS,
                {"approver_name": approver_name, "approval_comments": approval_comments}
            )
            st.success("✅ 승인 요청이 생성되었습니다.")
            st.rerun()
    
    elif approval_status == StepStatus.IN_PROGRESS:
        st.markdown("#### ⏳ 승인 대기 중")
        st.info("승인 요청이 제출되었습니다. 승인을 진행하세요.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 승인", type="primary"):
                workflow_manager.update_step_status(
                    "approval_deployment",
                    StepStatus.APPROVED,
                    {
                        "last_executed_at": datetime.now().isoformat(),
                        "approved_at": datetime.now().isoformat()
                    }
                )
                st.success("✅ 승인 완료!")
                st.rerun()
        
        with col2:
            if st.button("❌ 거부", type="secondary"):
                rejection_reason = st.text_area("거부 사유", key="rejection_reason")
                if st.button("거부 확인", key="confirm_reject"):
                    workflow_manager.update_step_status(
                        "approval_deployment",
                        StepStatus.NEEDS_REVISION,
                        {"rejected_at": datetime.now().isoformat(), "rejection_reason": rejection_reason}
                    )
                    # 검증 단계로 되돌림
                    workflow_manager.transition_to_phase(WorkflowPhase.VALIDATION)
                    st.warning("❌ 승인이 거부되었습니다. 검증 단계로 돌아갑니다.")
                    st.rerun()
    
    elif approval_status == StepStatus.APPROVED:
        st.markdown("#### 🚀 배포")
        st.success("✅ 승인 완료. 프로덕션 환경에 배포할 수 있습니다.")
        
        if st.button("프로덕션 배포", type="primary"):
            # 배포 프로세스
            _deploy_to_production(orchestrator, workflow_manager)
            
            workflow_manager.update_step_status(
                "approval_deployment",
                StepStatus.DEPLOYED,
                {
                    "last_executed_at": datetime.now().isoformat(),
                    "deployed_at": datetime.now().isoformat()
                }
            )
            
            # 사용 단계로 전환
            workflow_manager.transition_to_phase(WorkflowPhase.USAGE)
            
            st.success("🚀 프로덕션 배포 완료!")
            st.info("💡 이제 **지식 탐색** 및 **지휘통제/분석** 페이지에서 온톨로지를 사용할 수 있습니다.")
            st.rerun()
    
    elif approval_status == StepStatus.DEPLOYED:
        st.markdown("#### ✅ 배포 완료")
        st.success("✅ 온톨로지가 프로덕션 환경에 배포되었습니다.")
        
        deployment_info = workflow_manager.workflow_state["steps"]["approval_deployment"]
        if deployment_info.get("deployed_at"):
            st.caption(f"배포 일시: {deployment_info['deployed_at']}")
        
        # 롤백 옵션
        with st.expander("🔄 롤백 옵션", expanded=False):
            st.warning("⚠️ 롤백은 이전 버전으로 되돌립니다.")
            if st.button("이전 버전으로 롤백", type="secondary"):
                st.info("롤백 기능은 구현 예정입니다.")

def _get_validation_results(workflow_manager: OntologyWorkflowManager) -> Dict:
    """검증 결과 가져오기"""
    step = workflow_manager.workflow_state["steps"].get("quality_validation", {})
    results = step.get("validation_results", {})
    
    total = results.get("total", 0)
    passed = results.get("passed", 0)
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "passed": passed,
        "failed": results.get("failed", 0),
        "warning": results.get("warning", 0),
        "pass_rate": pass_rate
    }

def _deploy_to_production(orchestrator, workflow_manager: OntologyWorkflowManager):
    """프로덕션 배포"""
    # 실제 배포 로직 (예: 그래프 파일 복사, 버전 태깅 등)
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if ontology_manager:
        # 그래프 저장 (프로덕션 경로)
        ontology_manager.save_graph()
        # 버전 태깅
        # ...

