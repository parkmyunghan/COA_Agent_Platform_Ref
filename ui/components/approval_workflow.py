# ui/components/approval_workflow.py
# -*- coding: utf-8 -*-
"""
승인 워크플로우 UI
"""
import streamlit as st
from pathlib import Path
from typing import Dict
import sys

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_pipeline.workflow_manager import WorkflowManager
from core_pipeline.permission_manager import PermissionManager


def render_approval_workflow(recommendation_id: str):
    """승인 워크플로우 UI"""
    
    user = st.session_state.get("user")
    if not user:
        st.warning("로그인이 필요합니다.")
        return
    
    user_id = user.get("user_id")
    is_pilot_tester = user.get('role') == 'pilot_tester'
    active_role = st.session_state.get('active_role', user.get('role'))
    
    # WorkflowManager 초기화
    if "workflow_manager" not in st.session_state:
        from core_pipeline.realtime_collaboration import RealtimeCollaboration
        if "realtime_collaboration" not in st.session_state:
            st.session_state.realtime_collaboration = RealtimeCollaboration()
        st.session_state.workflow_manager = WorkflowManager(
            realtime_collaboration=st.session_state.get("realtime_collaboration")
        )
    
    workflow_manager = st.session_state.workflow_manager
    
    request = workflow_manager.get_request_by_recommendation(recommendation_id)
    
    # 파일럿 모드 알림
    if is_pilot_tester:
        st.info("🎭 파일럿 모드: 모든 워크플로우 단계를 수행할 수 있습니다.")
        if active_role != 'pilot_tester':
            st.warning(f"현재 역할 시뮬레이션: {active_role}")
    
    # 워크플로우 상태 표시
    if request:
        render_workflow_status(request)
    else:
        st.info("승인 요청이 생성되지 않았습니다.")
    
    st.divider()
    
    # 파일럿 모드: 워크플로우 단계별 수동 진행 옵션
    if is_pilot_tester and not request:
        st.subheader("파일럿 모드: 워크플로우 시뮬레이션")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("1) 작전 계획 담당으로 요청 생성", width='stretch', key=f"create_request_{recommendation_id}"):
                # 작전 계획 담당 역할로 전환하여 요청 생성
                st.session_state.active_role = 'planner'
                request_id = workflow_manager.create_approval_request_as_role(
                    recommendation_id, 'planner', user_id
                )
                st.success(f"승인 요청이 생성되었습니다! (ID: {request_id})")
                st.rerun()
        
        with col2:
            if st.button("2) 분석가로 검토 의견 추가", width='stretch', disabled=not request, key=f"add_review_{recommendation_id}"):
                st.session_state.active_role = 'analyst'
                with st.form(f"review_comment_form_{recommendation_id}"):
                    comment = st.text_area("검토 의견")
                    rating = st.slider("평가 (1-5점)", 1, 5, 3)
                    if st.form_submit_button("의견 등록"):
                        if request:
                            workflow_manager.add_review_comment(
                                request['request_id'], user_id, comment, rating
                            )
                            st.success("검토 의견이 추가되었습니다!")
                            st.rerun()
        
        with col3:
            if st.button("3) 지휘관으로 승인/반려", width='stretch', disabled=not request, key=f"approve_reject_{recommendation_id}"):
                st.session_state.active_role = 'commander'
                st.rerun()
    
    # 현재 단계에 따른 액션 버튼
    if request and request['status'] == 'pending_approval':
        # 파일럿 테스터는 항상 승인 가능
        can_approve = PermissionManager.is_approver(user) or is_pilot_tester
        
        if can_approve:
            st.subheader("승인/반려 결정")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("[OK] 승인", type="primary", width='stretch', key=f"approve_{recommendation_id}"):
                    if is_pilot_tester and active_role != 'commander':
                        st.session_state.active_role = 'commander'
                    
                    comments = st.text_input("승인 의견 (선택)", key=f"approve_comments_{recommendation_id}")
                    workflow_manager.approve_recommendation(
                        request['request_id'],
                        user_id,
                        comments
                    )
                    st.success("방책이 승인되었습니다!")
                    st.rerun()
            
            with col2:
                if st.button("[REJECT] 반려", width='stretch', key=f"reject_{recommendation_id}"):
                    with st.form(f"reject_form_{recommendation_id}"):
                        reason = st.text_area("반려 사유 (필수)", key=f"reject_reason_{recommendation_id}")
                        if st.form_submit_button("반려 확인"):
                            if reason:
                                if is_pilot_tester and active_role != 'commander':
                                    st.session_state.active_role = 'commander'
                                workflow_manager.reject_recommendation(
                                    request['request_id'],
                                    user_id,
                                    reason
                                )
                                st.success("방책이 반려되었습니다.")
                                st.rerun()
            
            with col3:
                if st.button("수정 요청", width='stretch', key=f"modify_{recommendation_id}"):
                    with st.form(f"modification_form_{recommendation_id}"):
                        modification = st.text_area("수정 요청 사항", key=f"modification_request_{recommendation_id}")
                        if st.form_submit_button("수정 요청 전송"):
                            if modification:
                                workflow_manager.request_modification(
                                    request['request_id'],
                                    user_id,
                                    modification
                                )
                                st.success("수정 요청이 전송되었습니다.")
                                st.rerun()
    
    # 검토 의견 추가 (분석가 또는 파일럿 테스터)
    if request and (user.get('role') == 'analyst' or is_pilot_tester):
        st.divider()
        st.subheader("검토 의견 추가")
        with st.form(f"add_review_comment_{recommendation_id}"):
            comment = st.text_area("검토 의견")
            rating = st.slider("평가 (1-5점)", 1, 5, 3)
            if st.form_submit_button("의견 등록"):
                if comment:
                    workflow_manager.add_review_comment(
                        request['request_id'], user_id, comment, rating
                    )
                    st.success("검토 의견이 추가되었습니다!")
                    st.rerun()
    
    # 검토 의견 목록
    if request and request.get("review_comments"):
        st.divider()
        st.subheader("검토 의견 목록")
        for review in request.get("review_comments", []):
            with st.container():
                st.markdown(f"**평가:** {review.get('rating')}/5")
                st.write(review.get('comment', ''))
                st.caption(f"작성일: {review.get('created_at', '')}")
                st.divider()


def render_workflow_status(request: Dict):
    """워크플로우 상태 표시"""
    status_labels = {
        "draft": "[DRAFT]",
        "pending_review": "[PENDING]",
        "under_review": "[REVIEW]",
        "pending_approval": "[APPROVAL]",
        "pending_modification": "[MODIFY]",
        "approved": "[OK]",
        "rejected": "[REJECT]",
        "executed": "[EXEC]"
    }
    
    status = request.get("status", "draft")
    label = status_labels.get(status, "[UNKNOWN]")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("상태", f"{label} {status}")
    with col2:
        st.caption(f"생성일: {request.get('created_at', '')}")
        if request.get("approved_at"):
            st.caption(f"승인일: {request.get('approved_at')}")
        if request.get("rejected_at"):
            st.caption(f"반려일: {request.get('rejected_at')}")
    
    # 워크플로우 타임라인
    st.markdown("**워크플로우 타임라인:**")
    timeline_items = []
    if request.get("created_at"):
        timeline_items.append(f"[CREATE] 요청 생성: {request.get('created_at')}")
    if request.get("review_comments"):
        timeline_items.append(f"[REVIEW] 검토 의견 추가: {len(request.get('review_comments', []))}개")
    if request.get("approved_at"):
        timeline_items.append(f"[OK] 승인: {request.get('approved_at')}")
    if request.get("rejected_at"):
        timeline_items.append(f"[REJECT] 반려: {request.get('rejected_at')}")
    
    for item in timeline_items:
        st.write(f"  - {item}")

