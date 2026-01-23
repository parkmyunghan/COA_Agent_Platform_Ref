# core_pipeline/workflow_manager.py
# -*- coding: utf-8 -*-
"""
워크플로우 관리 시스템
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List


class WorkflowManager:
    """워크플로우 관리 클래스"""
    
    def __init__(self, requests_file: str = "data/collaboration/approval_requests.json", realtime_collaboration=None):
        self.requests_file = Path(requests_file)
        self.requests_file.parent.mkdir(parents=True, exist_ok=True)
        self.realtime_collaboration = realtime_collaboration
        self.requests = self._load_requests()
    
    def _load_requests(self) -> List[Dict]:
        """승인 요청 목록 로드"""
        if self.requests_file.exists():
            try:
                with open(self.requests_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 승인 요청 파일 로드 실패: {e}")
                return []
        return []
    
    def _save_requests(self):
        """승인 요청 목록 저장"""
        try:
            with open(self.requests_file, 'w', encoding='utf-8') as f:
                json.dump(self.requests, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 승인 요청 파일 저장 실패: {e}")
    
    def create_approval_request(
        self,
        recommendation: Dict,
        requester_id: str,
        approver_id: str = None
    ) -> str:
        """승인 요청 생성 (자동 알림 전송)"""
        request_id = f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # approver_id가 없으면 지휘관 역할의 사용자 찾기
        if not approver_id and self.realtime_collaboration:
            from core_pipeline.user_manager import UserManager
            user_manager = UserManager()
            commanders = user_manager.get_users_by_role("commander")
            if commanders:
                approver_id = commanders[0].get("user_id")
        
        request = {
            "request_id": request_id,
            "recommendation_id": recommendation.get("recommendation_id") or f"REC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "requester_id": requester_id,
            "approver_id": approver_id,
            "status": "pending_approval",
            "created_at": datetime.now().isoformat(),
            "recommendation_data": recommendation,
            "comments": [],
            "review_comments": []
        }
        
        self.requests.append(request)
        self._save_requests()
        
        # 자동 알림 전송: 지휘관 역할의 사용자에게
        if self.realtime_collaboration:
            self.realtime_collaboration.send_workflow_notification(
                workflow_event="approval_requested",
                workflow_data={
                    "request_id": request_id,
                    "recommendation_id": request["recommendation_id"],
                    "requester_id": requester_id,
                    "approver_id": approver_id
                }
            )
        
        return request_id
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """승인 요청 조회"""
        for request in self.requests:
            if request.get("request_id") == request_id:
                return request
        return None
    
    def get_request_by_recommendation(self, recommendation_id: str) -> Optional[Dict]:
        """추천 ID로 승인 요청 조회"""
        for request in self.requests:
            if request.get("recommendation_id") == recommendation_id:
                return request
        return None
    
    def add_review_comment(
        self,
        request_id: str,
        reviewer_id: str,
        comment: str,
        rating: int = 3  # 1-5
    ):
        """검토 의견 추가 (자동 알림 전송)"""
        request = self.get_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        # 의견 추가
        review_comment = {
            "reviewer_id": reviewer_id,
            "comment": comment,
            "rating": rating,
            "created_at": datetime.now().isoformat()
        }
        
        if "review_comments" not in request:
            request["review_comments"] = []
        request["review_comments"].append(review_comment)
        
        if request["status"] == "pending_review":
            request["status"] = "under_review"
        
        self._save_requests()
        
        # 자동 알림 전송: 요청자에게
        if self.realtime_collaboration:
            self.realtime_collaboration.send_workflow_notification(
                workflow_event="review_comment_added",
                workflow_data={
                    "request_id": request_id,
                    "reviewer_id": reviewer_id,
                    "requester_id": request.get("requester_id"),
                    "comment": comment
                }
            )
    
    def approve_recommendation(
        self,
        request_id: str,
        approver_id: str,
        comments: str = None
    ):
        """방책 승인 (자동 알림 전송)"""
        request = self.get_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        request["status"] = "approved"
        request["approved_at"] = datetime.now().isoformat()
        request["approver_id"] = approver_id
        if comments:
            request["approver_comments"] = comments
        
        self._save_requests()
        
        # 자동 알림 전송: 요청자에게
        if self.realtime_collaboration:
            self.realtime_collaboration.send_workflow_notification(
                workflow_event="approved",
                workflow_data={
                    "request_id": request_id,
                    "recommendation_id": request.get("recommendation_id"),
                    "requester_id": request.get("requester_id"),
                    "approver_id": approver_id,
                    "comments": comments
                }
            )
    
    def reject_recommendation(
        self,
        request_id: str,
        approver_id: str,
        reason: str
    ):
        """방책 반려 (자동 알림 전송)"""
        request = self.get_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        request["status"] = "rejected"
        request["rejected_at"] = datetime.now().isoformat()
        request["approver_id"] = approver_id
        request["rejection_reason"] = reason
        
        self._save_requests()
        
        # 자동 알림 전송: 요청자에게
        if self.realtime_collaboration:
            self.realtime_collaboration.send_workflow_notification(
                workflow_event="rejected",
                workflow_data={
                    "request_id": request_id,
                    "recommendation_id": request.get("recommendation_id"),
                    "requester_id": request.get("requester_id"),
                    "approver_id": approver_id,
                    "reason": reason
                }
            )
    
    def request_modification(
        self,
        request_id: str,
        approver_id: str,
        modification_request: str
    ):
        """수정 요청"""
        request = self.get_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        request["status"] = "pending_modification"
        request["modification_request"] = modification_request
        request["modification_requested_at"] = datetime.now().isoformat()
        request["modification_requester_id"] = approver_id
        
        self._save_requests()
        
        # 자동 알림 전송
        if self.realtime_collaboration:
            self.realtime_collaboration.send_workflow_notification(
                workflow_event="modification_requested",
                workflow_data={
                    "request_id": request_id,
                    "requester_id": request.get("requester_id"),
                    "modification_request": modification_request
                }
            )
    
    def get_requests_by_user(self, user_id: str, role: str = None) -> List[Dict]:
        """사용자별 승인 요청 조회"""
        result = []
        for request in self.requests:
            if role == "commander" and request.get("approver_id") == user_id:
                result.append(request)
            elif role == "planner" and request.get("requester_id") == user_id:
                result.append(request)
            elif not role:
                if request.get("requester_id") == user_id or request.get("approver_id") == user_id:
                    result.append(request)
        return sorted(result, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def create_approval_request_as_role(
        self,
        recommendation_id: str,
        role: str,
        user_id: str
    ) -> str:
        """특정 역할로 승인 요청 생성 (파일럿 모드)"""
        # 파일럿 테스터는 어떤 역할로든 요청 생성 가능
        recommendation = {
            "recommendation_id": recommendation_id,
            "created_by": user_id,
            "role": role
        }
        return self.create_approval_request(recommendation, user_id)


