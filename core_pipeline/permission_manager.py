# core_pipeline/permission_manager.py
# -*- coding: utf-8 -*-
"""
권한 관리 시스템
"""
import streamlit as st
from typing import Dict, List


class PermissionManager:
    """권한 관리 클래스"""
    
    PERMISSIONS = {
        "commander": [
            "view_recommendations",
            "approve_recommendations",
            "view_reports",
            "view_analysis"
        ],
        "planner": [
            "view_recommendations",
            "create_recommendations",
            "edit_recommendations",
            "create_reports",
            "add_comments",
            "view_analysis"
        ],
        "analyst": [
            "view_recommendations",
            "view_analysis",
            "create_reports",
            "add_comments"
        ],
        "admin": [
            "*"  # 모든 권한
        ],
        "pilot_tester": [
            "*"  # 모든 권한 (파일럿 테스트용)
        ]
    }
    
    @classmethod
    def has_permission(cls, user_role: str, permission: str) -> bool:
        """권한 확인"""
        # 파일럿 테스터는 항상 모든 권한 보유
        if user_role == "pilot_tester":
            return True
        
        # 활성 역할이 설정된 경우 (역할 전환 모드)
        if hasattr(st, 'session_state'):
            active_role = st.session_state.get('active_role')
            if active_role and active_role != user_role and active_role in cls.PERMISSIONS:
                user_role = active_role
        
        permissions = cls.PERMISSIONS.get(user_role, [])
        
        # "*"는 모든 권한을 의미
        if "*" in permissions:
            return True
        
        return permission in permissions
    
    @classmethod
    def can_act_as_role(cls, user_role: str, target_role: str) -> bool:
        """특정 역할로 행동할 수 있는지 확인 (파일럿 테스터 전용)"""
        if user_role == "pilot_tester":
            return True
        return user_role == target_role
    
    @classmethod
    def get_user_permissions(cls, user_role: str) -> List[str]:
        """사용자 역할의 모든 권한 조회"""
        permissions = cls.PERMISSIONS.get(user_role, [])
        if "*" in permissions:
            # 모든 권한 목록 반환
            all_permissions = set()
            for role_perms in cls.PERMISSIONS.values():
                all_permissions.update(role_perms)
            all_permissions.discard("*")
            return list(all_permissions)
        return permissions
    
    @classmethod
    def is_approver(cls, user: Dict) -> bool:
        """승인 권한이 있는지 확인"""
        role = user.get("role")
        return cls.has_permission(role, "approve_recommendations")
    
    @classmethod
    def can_create_recommendation(cls, user: Dict) -> bool:
        """방책 추천 생성 권한이 있는지 확인"""
        role = user.get("role")
        return cls.has_permission(role, "create_recommendations")
    
    @classmethod
    def can_edit_recommendation(cls, user: Dict) -> bool:
        """방책 추천 편집 권한이 있는지 확인"""
        role = user.get("role")
        return cls.has_permission(role, "edit_recommendations")


