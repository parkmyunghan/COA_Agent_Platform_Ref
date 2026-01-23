# core_pipeline/user_manager.py
# -*- coding: utf-8 -*-
"""
사용자 관리 시스템
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import hashlib


class UserManager:
    """사용자 관리 클래스"""
    
    def __init__(self, users_file: str = "data/collaboration/users.json"):
        self.users_file = Path(users_file)
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        self.users = self._load_users()
    
    def _load_users(self) -> List[Dict]:
        """사용자 목록 로드"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 사용자 파일 로드 실패: {e}")
                return []
        return []
    
    def _save_users(self):
        """사용자 목록 저장"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 사용자 파일 저장 실패: {e}")
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱 (간단한 해싱, 파일럿 단계)"""
        # 파일럿 단계에서는 간단한 해싱 사용
        # 실전에서는 bcrypt 사용 권장
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """사용자 인증"""
        password_hash = self._hash_password(password)
        
        for user in self.users:
            if user.get("username") == username and user.get("password_hash") == password_hash:
                # 마지막 로그인 시간 업데이트
                user["last_login"] = datetime.now().isoformat()
                self._save_users()
                
                # 비밀번호 해시는 반환하지 않음
                user_copy = user.copy()
                user_copy.pop("password_hash", None)
                return user_copy
        
        return None
    
    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        department: str = "",
        is_super_user: bool = False
    ) -> Dict:
        """사용자 생성"""
        # 중복 확인
        for user in self.users:
            if user.get("username") == username:
                raise ValueError(f"사용자명 '{username}'이 이미 존재합니다.")
        
        user_id = f"USER{len(self.users) + 1:03d}"
        new_user = {
            "user_id": user_id,
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,
            "department": department,
            "is_super_user": is_super_user,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        self.users.append(new_user)
        self._save_users()
        
        # 비밀번호 해시는 반환하지 않음
        user_copy = new_user.copy()
        user_copy.pop("password_hash", None)
        return user_copy
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """사용자 조회"""
        for user in self.users:
            if user.get("user_id") == user_id:
                user_copy = user.copy()
                user_copy.pop("password_hash", None)
                return user_copy
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """사용자명으로 사용자 조회"""
        for user in self.users:
            if user.get("username") == username:
                user_copy = user.copy()
                user_copy.pop("password_hash", None)
                return user_copy
        return None
    
    def get_users_by_role(self, role: str) -> List[Dict]:
        """역할별 사용자 조회"""
        users = []
        for user in self.users:
            if user.get("role") == role:
                user_copy = user.copy()
                user_copy.pop("password_hash", None)
                users.append(user_copy)
        return users
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """사용자 정보 업데이트"""
        for user in self.users:
            if user.get("user_id") == user_id:
                # 비밀번호는 별도 처리
                if "password" in kwargs:
                    user["password_hash"] = self._hash_password(kwargs.pop("password"))
                
                # 나머지 필드 업데이트
                for key, value in kwargs.items():
                    if key != "password_hash":  # 해시는 직접 수정 불가
                        user[key] = value
                
                self._save_users()
                return True
        return False
    
    def delete_user(self, user_id: str) -> bool:
        """사용자 삭제"""
        for i, user in enumerate(self.users):
            if user.get("user_id") == user_id:
                self.users.pop(i)
                self._save_users()
                return True
        return False
    
    def initialize_default_users(self):
        """기본 사용자 초기화 (파일럿 테스트용)"""
        if len(self.users) > 0:
            return  # 이미 사용자가 있으면 초기화하지 않음
        
        default_users = [
            {
                "username": "commander1",
                "password": "commander123",
                "role": "commander",
                "department": "작전부"
            },
            {
                "username": "planner1",
                "password": "planner123",
                "role": "planner",
                "department": "작전계획부"
            },
            {
                "username": "analyst1",
                "password": "analyst123",
                "role": "analyst",
                "department": "정보분석부"
            },
            {
                "username": "admin",
                "password": "admin123",
                "role": "admin",
                "department": "시스템관리부"
            },
            {
                "username": "pilot",
                "password": "pilot123",
                "role": "pilot_tester",
                "department": "파일럿테스트",
                "is_super_user": True
            }
        ]
        
        for user_data in default_users:
            try:
                self.create_user(
                    username=user_data["username"],
                    password=user_data["password"],
                    role=user_data["role"],
                    department=user_data.get("department", ""),
                    is_super_user=user_data.get("is_super_user", False)
                )
            except ValueError:
                pass  # 이미 존재하는 경우 무시
        
        print("[INFO] 기본 사용자 초기화 완료")


