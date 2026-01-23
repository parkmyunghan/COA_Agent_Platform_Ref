# ui/components/workflow_status_dashboard.py
# -*- coding: utf-8 -*-
"""
워크플로우 상태 대시보드
순환형 워크플로우의 현재 상태를 시각화
"""
import streamlit as st
from core_pipeline.ontology_workflow_manager import (
    OntologyWorkflowManager, WorkflowPhase, StepStatus
)

def render_workflow_status_dashboard(workflow_manager: OntologyWorkflowManager, orchestrator=None):
    """워크플로우 상태 대시보드 렌더링"""
    st.markdown("### 🔄 온톨로지 생명주기 상태")
    
    # 실제 시스템 상태 동기화 (orchestrator가 제공된 경우)
    if orchestrator and hasattr(orchestrator, 'config'):
        config = orchestrator.config
        # 자동 동기화 버튼
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 상태 새로고침", key="sync_workflow_status"):
                # 메서드 존재 여부 확인
                if hasattr(workflow_manager, 'sync_with_actual_status'):
                    workflow_manager.sync_with_actual_status(config)
                    st.success("상태 동기화 완료!")
                else:
                    st.warning("동기화 기능을 사용할 수 없습니다. Streamlit 서버를 재시작해주세요.")
                st.rerun()
        # 자동 동기화 실행 (메서드가 있는 경우에만)
        if hasattr(workflow_manager, 'sync_with_actual_status'):
            try:
                workflow_manager.sync_with_actual_status(config)
            except Exception as e:
                # 동기화 실패해도 계속 진행
                pass
    
    summary = workflow_manager.get_workflow_summary()
    current_phase = WorkflowPhase(summary["current_phase"])
    
    # 현재 단계 표시
    phase_info = {
        WorkflowPhase.PREPARATION: {"name": "준비 및 설계", "icon": "📋", "color": "#4CAF50"},
        WorkflowPhase.CONSTRUCTION: {"name": "구축", "icon": "🔨", "color": "#2196F3"},
        WorkflowPhase.VALIDATION: {"name": "검증", "icon": "✅", "color": "#FF9800"},
        WorkflowPhase.DEPLOYMENT: {"name": "배포", "icon": "🚀", "color": "#9C27B0"},
        WorkflowPhase.USAGE: {"name": "사용", "icon": "👥", "color": "#00BCD4"},
        WorkflowPhase.MONITORING: {"name": "모니터링", "icon": "📊", "color": "#607D8B"},
        WorkflowPhase.IMPROVEMENT: {"name": "개선", "icon": "🔄", "color": "#E91E63"}
    }
    
    info = phase_info.get(current_phase, {"name": "알 수 없음", "icon": "❓", "color": "#9E9E9E"})
    
    # 현재 단계 카드
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div style="background-color: {info['color']}20; padding: 15px; border-radius: 8px; border-left: 4px solid {info['color']};">
            <h3 style="margin: 0; color: {info['color']};">
                {info['icon']} 현재 단계: {info['name']}
            </h3>
            <p style="margin: 5px 0 0 0; color: #8b949e; font-size: 0.9rem;">
                Phase: {current_phase.value}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("피드백 루프", f"{summary.get('feedback_loop_count', 0)}회")
    
    with col3:
        if summary.get('last_transition'):
            st.caption(f"마지막 전환: {summary['last_transition']['to']}")
    
    st.divider()
    
    # 단계별 진행 상황
    st.markdown("#### 📊 단계별 진행 상황")
    
    # Step 이름 한글 매핑
    step_names_kr = {
        "data_management": "데이터 관리",
        "schema_design": "스키마 설계",
        "ontology_generation": "온톨로지 생성",
        "rag_indexing": "RAG 인덱스 구성",
        "quality_validation": "품질 검증",
        "approval_deployment": "승인 및 배포",
        "knowledge_exploration": "지식 탐색",
        "agent_execution": "Agent 실행",
        "performance_monitoring": "성능 모니터링",
        "feedback_improvement": "피드백 및 개선"
    }
    
    phases_steps = {
        WorkflowPhase.PREPARATION: ["data_management", "schema_design"],
        WorkflowPhase.CONSTRUCTION: ["ontology_generation", "rag_indexing"],
        WorkflowPhase.VALIDATION: ["quality_validation"],
        WorkflowPhase.DEPLOYMENT: ["approval_deployment"],
        WorkflowPhase.USAGE: ["knowledge_exploration", "agent_execution"],
        WorkflowPhase.MONITORING: ["performance_monitoring"],
        WorkflowPhase.IMPROVEMENT: ["feedback_improvement"]
    }
    
    # 단계별 진행률 계산 및 표시
    for phase, step_names in phases_steps.items():
        phase_info_item = phase_info.get(phase, {})
        completed = sum(
            1 for step_name in step_names
            if workflow_manager.get_step_status(step_name) in [
                StepStatus.COMPLETED, StepStatus.VALIDATED, 
                StepStatus.APPROVED, StepStatus.DEPLOYED
            ]
        )
        total = len(step_names)
        progress = (completed / total * 100) if total > 0 else 0
        
        # Phase 헤더
        with st.expander(
            f"{phase_info_item.get('icon', '')} **{phase_info_item.get('name', phase.value)}** ({completed}/{total} 완료)",
            expanded=(phase == current_phase)
        ):
            # 각 Step 상세 표시
            for step_name in step_names:
                step_status = workflow_manager.get_step_status(step_name)
                step_data = workflow_manager.workflow_state["steps"].get(step_name, {})
                last_executed = step_data.get("last_executed_at")
                
                # 상태 아이콘
                if step_status in [StepStatus.COMPLETED, StepStatus.VALIDATED, StepStatus.APPROVED, StepStatus.DEPLOYED]:
                    status_icon = "✅"
                    status_text = "완료"
                elif step_status == StepStatus.IN_PROGRESS:
                    status_icon = "🔄"
                    status_text = "진행 중"
                elif step_status == StepStatus.FAILED:
                    status_icon = "❌"
                    status_text = "실패"
                elif step_status == StepStatus.NEEDS_REVISION:
                    status_icon = "⚠️"
                    status_text = "수정 필요"
                else:
                    status_icon = "⏸️"
                    status_text = "미수행"
                
                # 마지막 수행 일시 표시
                if last_executed:
                    try:
                        from datetime import datetime
                        last_executed_dt = datetime.fromisoformat(last_executed)
                        last_executed_str = last_executed_dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        last_executed_str = last_executed
                    time_text = f"마지막 수행: {last_executed_str}"
                else:
                    time_text = "미수행"
                
                # Step 정보 표시
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.markdown(f"{status_icon} **{step_names_kr.get(step_name, step_name)}**")
                with col2:
                    st.caption(f"{status_text} | {time_text}")
            
            # 다음 단계로 진행 버튼 (현재 Phase이고 모든 Step 완료 시)
            if phase == current_phase and completed == total:
                next_phase = _get_next_phase(phase)
                if next_phase:
                    can_proceed, message = workflow_manager.can_proceed_to_phase(next_phase)
                    if can_proceed:
                        if st.button(
                            f"→ {phase_info.get(next_phase, {}).get('name', next_phase.value)} 단계로 진행", 
                            key=f"transition_{phase.value}",
                            type="primary"
                        ):
                            success, msg = workflow_manager.transition_to_phase(next_phase)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.warning(f"⚠️ {message}")
        
        # Phase 진행률 바 (간단히 표시)
        st.progress(progress / 100)
        st.caption(f"{phase_info_item.get('name', phase.value)} 진행률: {progress:.0f}%")
        
        st.divider()

def _get_next_phase(current_phase: WorkflowPhase) -> WorkflowPhase:
    """다음 단계 반환"""
    phase_order = [
        WorkflowPhase.PREPARATION,
        WorkflowPhase.CONSTRUCTION,
        WorkflowPhase.VALIDATION,
        WorkflowPhase.DEPLOYMENT,
        WorkflowPhase.USAGE,
        WorkflowPhase.MONITORING,
        WorkflowPhase.IMPROVEMENT
    ]
    
    try:
        current_index = phase_order.index(current_phase)
        if current_index < len(phase_order) - 1:
            return phase_order[current_index + 1]
        # 마지막 단계에서 첫 단계로 (순환)
        return WorkflowPhase.PREPARATION
    except ValueError:
        return WorkflowPhase.PREPARATION

