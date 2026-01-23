# ui/components/notifications_panel.py
# -*- coding: utf-8 -*-
"""
알림 패널 UI
"""
import streamlit as st
import time
from pathlib import Path
import sys

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_pipeline.realtime_collaboration import RealtimeCollaboration


def render_notifications(auto_refresh: bool = True, refresh_interval: int = 5):
    """알림 패널 (자동 새로고침 지원)"""
    
    user = st.session_state.get("user")
    if not user:
        return
    
    user_id = user.get("user_id")
    
    # RealtimeCollaboration 초기화
    if "realtime_collaboration" not in st.session_state:
        st.session_state.realtime_collaboration = RealtimeCollaboration()
        # 활성 세션 등록
        session_id = st.session_state.get("session_id", f"session_{user_id}")
        st.session_state.realtime_collaboration.register_active_session(session_id, user)
    
    collaboration = st.session_state.realtime_collaboration
    collaboration.update_user_activity(user_id)
    
    st.subheader("알림")
    
    # 자동 새로고침 (선택적)
    if auto_refresh:
        if st.button("새로고침", width='stretch'):
            st.rerun()
    
    # 읽지 않은 알림 조회
    notifications = collaboration.get_unread_notifications(user_id)
    
    if notifications:
        st.info(f"읽지 않은 알림: {len(notifications)}개")
        
        for notif in sorted(notifications, key=lambda x: x.get("created_at", ""), reverse=True):
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # 알림 타입별 아이콘
                    labels = {
                        "approval_request": "[REQ]",
                        "review_comment": "[REVIEW]",
                        "approval_result": "[OK]",
                        "modification_request": "[MODIFY]",
                        "new_recommendation": "[NEW]"
                    }
                    label = labels.get(notif.get("type"), "[INFO]")
                    
                    st.markdown(f"{label} **{notif.get('message')}**")
                    st.caption(notif.get("created_at", ""))
                    
                    # 알림 데이터 표시
                    notif_data = notif.get("data", {})
                    if notif_data.get("request_id"):
                        st.caption(f"요청 ID: {notif_data.get('request_id')}")
                
                with col2:
                    if st.button("읽음", key=f"read_{notif.get('notification_id')}", width='stretch'):
                        collaboration.mark_notification_read(notif.get("notification_id"))
                        st.success("읽음 처리되었습니다.")
                        time.sleep(0.5)
                        st.rerun()
                
                st.divider()
    else:
        st.info("새로운 알림이 없습니다.")
    
    # 모든 알림 보기
    with st.expander("전체 알림 보기", expanded=False):
        render_all_notifications(user_id, collaboration)


def render_all_notifications(user_id: str, collaboration: RealtimeCollaboration):
    """모든 알림 보기"""
    all_notifications = [
        n for n in collaboration.notifications
        if n.get("user_id") == user_id
    ]
    
    if not all_notifications:
        st.info("알림이 없습니다.")
        return
    
    # 읽음/안 읽음 필터
    filter_option = st.radio(
        "필터",
        options=["전체", "읽지 않음", "읽음"],
        horizontal=True
    )
    
    filtered = all_notifications
    if filter_option == "읽지 않음":
        filtered = [n for n in all_notifications if not n.get("read", False)]
    elif filter_option == "읽음":
        filtered = [n for n in all_notifications if n.get("read", False)]
    
    # 정렬 (최신순)
    filtered = sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)
    
    for notif in filtered:
        read_status = "[READ]" if notif.get("read") else "[NEW]"
        st.markdown(f"{read_status} **{notif.get('message')}**")
        st.caption(f"{notif.get('created_at', '')} | 타입: {notif.get('type', '')}")
        st.divider()


def render_active_users():
    """활성 사용자 표시"""
    if "realtime_collaboration" not in st.session_state:
        return
    
    collaboration = st.session_state.realtime_collaboration
    active_users = collaboration.get_active_users()
    
    st.subheader("활성 사용자")
    
    if active_users:
        for user in active_users:
            role_icons = {
                "commander": "[CMD]",
                "planner": "[PLAN]",
                "analyst": "[ANAL]",
                "admin": "[ADMIN]",
                "pilot_tester": "[TEST]"
            }
            icon = role_icons.get(user.get("role"), "👤")
            st.markdown(f"{icon} {user.get('username')} ({user.get('role')})")
    else:
        st.info("활성 사용자가 없습니다.")


