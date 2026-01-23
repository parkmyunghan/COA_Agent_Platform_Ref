# core_pipeline/realtime_collaboration.py
# -*- coding: utf-8 -*-
"""
실시간 협업 및 알림 시스템
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class RealtimeCollaboration:
    """실시간 협업 및 알림 시스템"""
    
    def __init__(
        self,
        active_sessions_file: str = "data/collaboration/active_sessions.json",
        notifications_file: str = "data/collaboration/notifications.json"
    ):
        self.active_sessions_file = Path(active_sessions_file)
        self.notifications_file = Path(notifications_file)
        
        # 디렉토리 생성
        self.active_sessions_file.parent.mkdir(parents=True, exist_ok=True)
        self.notifications_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.active_sessions = self._load_active_sessions()
        self.notifications = self._load_notifications()
    
    def _load_active_sessions(self) -> Dict:
        """활성 세션 로드"""
        if self.active_sessions_file.exists():
            try:
                with open(self.active_sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 활성 세션 파일 로드 실패: {e}")
                return {}
        return {}
    
    def _save_active_sessions(self):
        """활성 세션 저장"""
        try:
            with open(self.active_sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 활성 세션 파일 저장 실패: {e}")
    
    def _load_notifications(self) -> List[Dict]:
        """알림 목록 로드"""
        if self.notifications_file.exists():
            try:
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 알림 파일 로드 실패: {e}")
                return []
        return []
    
    def _save_notifications(self):
        """알림 목록 저장"""
        try:
            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump(self.notifications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 알림 파일 저장 실패: {e}")
    
    def register_active_session(self, session_id: str, user_info: Dict):
        """활성 세션 등록 (사용자 로그인 시)"""
        self.active_sessions[session_id] = {
            **user_info,
            "last_activity": datetime.now().isoformat(),
            "session_id": session_id
        }
        self._save_active_sessions()
    
    def update_user_activity(self, user_id: str):
        """사용자 활동 업데이트"""
        # session_id로 찾기
        for session_id, session_data in self.active_sessions.items():
            if session_data.get("user_id") == user_id:
                session_data["last_activity"] = datetime.now().isoformat()
                self._save_active_sessions()
                return
    
    def get_active_users(self) -> List[Dict]:
        """현재 활성 사용자 목록 (같은 네트워크의 모든 사용자)"""
        # 5분 이내 활동한 사용자만
        cutoff = datetime.now() - timedelta(minutes=5)
        active = []
        
        for session_id, session_data in self.active_sessions.items():
            last_activity_str = session_data.get("last_activity", "2000-01-01T00:00:00")
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                if last_activity > cutoff:
                    active.append({
                        "user_id": session_data.get("user_id"),
                        "username": session_data.get("username"),
                        "role": session_data.get("role"),
                        "last_activity": last_activity_str
                    })
            except Exception:
                continue
        
        return active
    
    def send_notification(
        self,
        user_id: str,
        notification_type: str,
        message: str,
        data: Dict = None
    ) -> str:
        """알림 전송 (특정 사용자에게)"""
        notification_id = f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        notification = {
            "notification_id": notification_id,
            "user_id": user_id,
            "type": notification_type,
            "message": message,
            "data": data or {},
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        
        self.notifications.append(notification)
        self._save_notifications()
        
        return notification_id
    
    def send_notification_by_role(
        self,
        target_role: str,
        notification_type: str,
        message: str,
        data: Dict = None
    ) -> List[str]:
        """역할 기반 알림 전송 (특정 역할의 모든 사용자에게)"""
        # 해당 역할의 모든 활성 사용자 찾기
        target_users = [
            user for user in self.get_active_users()
            if user.get("role") == target_role
        ]
        
        # 활성 사용자가 없으면 모든 사용자 중에서 찾기
        if not target_users:
            from core_pipeline.user_manager import UserManager
            user_manager = UserManager()
            all_users = user_manager.get_users_by_role(target_role)
            target_users = [{"user_id": u.get("user_id")} for u in all_users]
        
        notification_ids = []
        for user in target_users:
            notification_id = self.send_notification(
                user_id=user["user_id"],
                notification_type=notification_type,
                message=message,
                data=data
            )
            notification_ids.append(notification_id)
        
        return notification_ids
    
    def send_workflow_notification(
        self,
        workflow_event: str,  # "approval_requested", "approved", "rejected", etc.
        workflow_data: Dict
    ):
        """워크플로우 이벤트 기반 자동 알림"""
        request_id = workflow_data.get("request_id")
        recommendation_id = workflow_data.get("recommendation_id")
        
        if workflow_event == "approval_requested":
            # 승인 요청 생성 → 지휘관에게 알림
            approver_id = workflow_data.get("approver_id")
            requester_id = workflow_data.get("requester_id")
            
            # 지휘관 역할의 사용자에게 알림
            self.send_notification_by_role(
                target_role="commander",
                notification_type="approval_request",
                message=f"새로운 승인 요청이 생성되었습니다. (요청 ID: {request_id})",
                data={
                    "request_id": request_id,
                    "recommendation_id": recommendation_id,
                    "requester_id": requester_id,
                    "action_url": f"/approval/{request_id}"
                }
            )
        
        elif workflow_event == "review_comment_added":
            # 검토 의견 추가 → 요청자에게 알림
            reviewer_id = workflow_data.get("reviewer_id")
            requester_id = workflow_data.get("requester_id")
            
            if requester_id:
                self.send_notification(
                    user_id=requester_id,
                    notification_type="review_comment",
                    message=f"분석가가 검토 의견을 추가했습니다.",
                    data=workflow_data
                )
        
        elif workflow_event == "approved":
            # 승인됨 → 요청자에게 알림
            requester_id = workflow_data.get("requester_id")
            if requester_id:
                self.send_notification(
                    user_id=requester_id,
                    notification_type="approval_result",
                    message=f"방책이 승인되었습니다!",
                    data=workflow_data
                )
        
        elif workflow_event == "rejected":
            # 반려됨 → 요청자에게 알림
            requester_id = workflow_data.get("requester_id")
            reason = workflow_data.get("reason", "")
            if requester_id:
                self.send_notification(
                    user_id=requester_id,
                    notification_type="approval_result",
                    message=f"방책이 반려되었습니다. 사유: {reason}",
                    data=workflow_data
                )
        
        elif workflow_event == "modification_requested":
            # 수정 요청 → 요청자에게 알림
            requester_id = workflow_data.get("requester_id")
            if requester_id:
                self.send_notification(
                    user_id=requester_id,
                    notification_type="modification_request",
                    message=f"수정 요청이 전송되었습니다.",
                    data=workflow_data
                )
    
    def get_unread_notifications(self, user_id: str) -> List[Dict]:
        """읽지 않은 알림 조회"""
        return [
            n for n in self.notifications
            if n.get("user_id") == user_id and not n.get("read", False)
        ]
    
    def mark_notification_read(self, notification_id: str):
        """알림 읽음 처리"""
        for n in self.notifications:
            if n.get("notification_id") == notification_id:
                n["read"] = True
                n["read_at"] = datetime.now().isoformat()
                self._save_notifications()
                break
    
    def lock_resource(
        self,
        resource_id: str,
        user_id: str
    ) -> bool:
        """리소스 잠금 (동시 편집 방지)"""
        lock_file = Path(f"data/collaboration/locks/{resource_id}.lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 이미 잠금이 있는지 확인
        if lock_file.exists():
            try:
                lock_data = json.loads(lock_file.read_text())
                lock_owner = lock_data.get("user_id")
                lock_time_str = lock_data.get("locked_at", "2000-01-01T00:00:00")
                lock_time = datetime.fromisoformat(lock_time_str)
                
                # 10분 이상 잠금이면 자동 해제
                if datetime.now() - lock_time > timedelta(minutes=10):
                    lock_file.unlink()
                elif lock_owner != user_id:
                    return False  # 다른 사용자가 잠금 중
            except Exception:
                # 파일이 손상된 경우 삭제
                lock_file.unlink()
        
        # 잠금 설정
        lock_data = {
            "user_id": user_id,
            "resource_id": resource_id,
            "locked_at": datetime.now().isoformat()
        }
        lock_file.write_text(json.dumps(lock_data))
        return True
    
    def unlock_resource(self, resource_id: str, user_id: str):
        """리소스 잠금 해제"""
        lock_file = Path(f"data/collaboration/locks/{resource_id}.lock")
        if lock_file.exists():
            try:
                lock_data = json.loads(lock_file.read_text())
                if lock_data.get("user_id") == user_id:
                    lock_file.unlink()
            except Exception:
                pass


