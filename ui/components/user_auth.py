# ui/components/user_auth.py
# -*- coding: utf-8 -*-
"""
사용자 인증 UI 컴포넌트
"""
import streamlit as st
from pathlib import Path
import sys

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_pipeline.user_manager import UserManager


def render_login():
    """로그인 UI"""
    st.subheader("🔐 로그인")
    
    # UserManager 초기화
    if "user_manager" not in st.session_state:
        st.session_state.user_manager = UserManager()
        # 기본 사용자 초기화 (처음 실행 시)
        st.session_state.user_manager.initialize_default_users()
    
    user_manager = st.session_state.user_manager
    
    username = st.text_input("사용자명", key="login_username")
    password = st.text_input("비밀번호", type="password", key="login_password")
    
    # 파일럿 모드 체크박스 (개발/테스트용)
    pilot_mode = st.checkbox(
        "파일럿 모드 (모든 권한)",
        value=False,
        key="pilot_mode",
        help="파일럿 테스트를 위해 모든 역할의 권한을 가진 슈퍼 유저로 로그인"
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("로그인", type="primary", width='stretch'):
            if not username or not password:
                st.error("사용자명과 비밀번호를 입력해주세요.")
            else:
                user = user_manager.authenticate(username, password)
                if user:
                    # 파일럿 모드인 경우 슈퍼 유저 권한 부여
                    if pilot_mode:
                        user['role'] = 'pilot_tester'
                        user['is_super_user'] = True
                        # 위젯 키와 다른 키를 사용하여 파일럿 모드 상태 저장
                        st.session_state.is_pilot_mode = True
                    else:
                        st.session_state.is_pilot_mode = False
                    
                    st.session_state.user = user
                    st.session_state.user_id = user.get('user_id')
                    st.success(f"환영합니다, {user['username']}님! (역할: {user['role']})")
                    st.rerun()
                else:
                    st.error("로그인 실패: 사용자명 또는 비밀번호가 올바르지 않습니다.")
    
    with col2:
        if st.button("회원가입", width='stretch'):
            st.session_state.show_register = True
            st.rerun()
    
    # 기본 사용자 정보 표시 (파일럿 테스트용)
    with st.expander("📋 기본 사용자 계정 (파일럿 테스트용)", expanded=False):
        st.markdown("""
        | 사용자명 | 비밀번호 | 역할 |
        |---------|---------|------|
        | commander1 | commander123 | 지휘관 |
        | planner1 | planner123 | 작전 계획 담당 |
        | analyst1 | analyst123 | 분석가 |
        | admin | admin123 | 시스템 관리자 |
        | pilot | pilot123 | 파일럿 테스터 |
        """)


def render_register():
    """회원가입 UI"""
    st.subheader("📝 회원가입")
    
    if "user_manager" not in st.session_state:
        st.session_state.user_manager = UserManager()
    
    user_manager = st.session_state.user_manager
    
    username = st.text_input("사용자명", key="register_username")
    password = st.text_input("비밀번호", type="password", key="register_password")
    password_confirm = st.text_input("비밀번호 확인", type="password", key="register_password_confirm")
    
    role = st.selectbox(
        "역할",
        options=["commander", "planner", "analyst", "admin"],
        key="register_role"
    )
    
    department = st.text_input("부서", key="register_department")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("가입", type="primary", width='stretch'):
            if not username or not password:
                st.error("사용자명과 비밀번호를 입력해주세요.")
            elif password != password_confirm:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                try:
                    new_user = user_manager.create_user(
                        username=username,
                        password=password,
                        role=role,
                        department=department
                    )
                    st.success(f"회원가입이 완료되었습니다! 사용자 ID: {new_user.get('user_id')}")
                    st.session_state.show_register = False
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
    
    with col2:
        if st.button("취소", width='stretch'):
            st.session_state.show_register = False
            st.rerun()


def render_logout():
    """로그아웃 UI"""
    if st.sidebar.button("로그아웃", width='stretch'):
        # 세션 상태 초기화
        for key in list(st.session_state.keys()):
            if key not in ["main_orchestrator"]:  # orchestrator는 유지
                del st.session_state[key]
        st.rerun()


def render_role_switcher():
    """역할 전환 UI (파일럿 테스터 전용)"""
    user = st.session_state.get("user")
    if not user or user.get('role') != 'pilot_tester':
        return
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎭 역할 전환 모드")
    
    current_role = st.session_state.get('active_role', user.get('role'))
    
    selected_role = st.sidebar.selectbox(
        "현재 역할 (시뮬레이션)",
        options=["pilot_tester", "commander", "planner", "analyst", "admin"],
        index=0 if current_role == "pilot_tester" else 
              ["commander", "planner", "analyst", "admin"].index(current_role) + 1,
        help="파일럿 테스트를 위해 다른 역할로 전환하여 워크플로우를 시뮬레이션할 수 있습니다.",
        key="role_switcher"
    )
    
    if selected_role != current_role:
        st.session_state.active_role = selected_role
        st.sidebar.info(f"역할 전환: {selected_role}")
        st.rerun()
    
    st.sidebar.caption("💡 이 모드에서는 모든 워크플로우 단계를 한 명이 수행할 수 있습니다.")


def check_authentication():
    """인증 확인 (페이지 보호)"""
    if "user" not in st.session_state:
        render_login()
        if "show_register" in st.session_state and st.session_state.show_register:
            render_register()
        st.stop()
    return st.session_state.user

