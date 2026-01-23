# core_pipeline/ontology_workflow_manager.py
# -*- coding: utf-8 -*-
"""
온톨로지 생명주기 워크플로우 관리
순환형 워크플로우 상태 관리 및 전환 제어
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

class WorkflowPhase(Enum):
    """워크플로우 단계"""
    PREPARATION = "preparation"  # 준비 단계
    CONSTRUCTION = "construction"  # 구축 단계
    VALIDATION = "validation"  # 검증 단계
    DEPLOYMENT = "deployment"  # 배포 단계
    USAGE = "usage"  # 사용 단계
    MONITORING = "monitoring"  # 모니터링 단계
    IMPROVEMENT = "improvement"  # 개선 단계

class StepStatus(Enum):
    """단계별 상태"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VALIDATED = "validated"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"

class OntologyWorkflowManager:
    """온톨로지 워크플로우 관리자"""
    
    def __init__(self, workflow_file: str = "metadata/ontology_workflow.json"):
        self.workflow_file = Path(workflow_file)
        self.workflow_file.parent.mkdir(parents=True, exist_ok=True)
        self.workflow_state = self._load_workflow_state()
    
    def _load_workflow_state(self) -> Dict:
        """워크플로우 상태 로드"""
        if self.workflow_file.exists():
            try:
                with open(self.workflow_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 워크플로우 상태 로드 실패: {e}")
        
        # 초기 상태
        return {
            "current_phase": WorkflowPhase.PREPARATION.value,
            "steps": {
                "data_management": {
                    "status": StepStatus.NOT_STARTED.value,
                    "completed_at": None,
                    "validation_passed": False
                },
                "schema_design": {
                    "status": StepStatus.NOT_STARTED.value,
                    "completed_at": None,
                    "validation_passed": False
                },
                "ontology_generation": {
                    "status": StepStatus.NOT_STARTED.value,
                    "completed_at": None,
                    "validation_passed": False
                },
                "rag_indexing": {
                    "status": StepStatus.NOT_STARTED.value,
                    "completed_at": None,
                    "validation_passed": False
                },
                "quality_validation": {
                    "status": StepStatus.NOT_STARTED.value,
                    "completed_at": None,
                    "validation_results": None
                },
                "approval_deployment": {
                    "status": StepStatus.NOT_STARTED.value,
                    "completed_at": None,
                    "approved_by": None,
                    "deployed_at": None
                },
                "knowledge_exploration": {
                    "status": StepStatus.NOT_STARTED.value,
                    "usage_count": 0
                },
                "agent_execution": {
                    "status": StepStatus.NOT_STARTED.value,
                    "usage_count": 0
                },
                "performance_monitoring": {
                    "status": StepStatus.NOT_STARTED.value,
                    "last_monitored_at": None,
                    "issues_found": []
                },
                "feedback_improvement": {
                    "status": StepStatus.NOT_STARTED.value,
                    "improvement_plans": []
                }
            },
            "history": [],
            "feedback_loop_count": 0
        }
    
    def _save_workflow_state(self):
        """워크플로우 상태 저장"""
        try:
            with open(self.workflow_file, 'w', encoding='utf-8') as f:
                json.dump(self.workflow_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 워크플로우 상태 저장 실패: {e}")
    
    def get_current_phase(self) -> WorkflowPhase:
        """현재 단계 반환"""
        return WorkflowPhase(self.workflow_state["current_phase"])
    
    def get_step_status(self, step_name: str) -> StepStatus:
        """단계별 상태 반환"""
        step = self.workflow_state["steps"].get(step_name, {})
        status_str = step.get("status", StepStatus.NOT_STARTED.value)
        try:
            return StepStatus(status_str)
        except ValueError:
            return StepStatus.NOT_STARTED
    
    def update_step_status(self, step_name: str, status: StepStatus, 
                          metadata: Optional[Dict] = None):
        """단계 상태 업데이트"""
        if step_name not in self.workflow_state["steps"]:
            self.workflow_state["steps"][step_name] = {}
        
        step = self.workflow_state["steps"][step_name]
        step["status"] = status.value
        step["updated_at"] = datetime.now().isoformat()
        
        if status == StepStatus.COMPLETED:
            step["completed_at"] = datetime.now().isoformat()
        
        if metadata:
            step.update(metadata)
        
        # 히스토리 기록
        self.workflow_state["history"].append({
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "status": status.value,
            "metadata": metadata or {}
        })
        
        self._save_workflow_state()
    
    def can_proceed_to_phase(self, target_phase: WorkflowPhase) -> Tuple[bool, str]:
        """다음 단계로 진행 가능 여부 확인"""
        current_phase = self.get_current_phase()
        
        # 단계별 전제 조건 확인
        if target_phase == WorkflowPhase.CONSTRUCTION:
            # 준비 단계 완료 확인
            data_status = self.get_step_status("data_management")
            schema_status = self.get_step_status("schema_design")
            
            if data_status != StepStatus.COMPLETED:
                return False, "데이터 관리 단계를 완료해야 합니다."
            if schema_status != StepStatus.COMPLETED:
                return False, "스키마 설계 단계를 완료해야 합니다."
        
        elif target_phase == WorkflowPhase.VALIDATION:
            # 구축 단계 완료 확인
            onto_status = self.get_step_status("ontology_generation")
            
            if onto_status != StepStatus.COMPLETED:
                return False, "온톨로지 생성 단계를 완료해야 합니다."
            # RAG는 선택적
        
        elif target_phase == WorkflowPhase.DEPLOYMENT:
            # 검증 단계 완료 및 승인 확인
            validation_status = self.get_step_status("quality_validation")
            if validation_status != StepStatus.VALIDATED:
                return False, "품질 검증을 통과해야 합니다."
        
        elif target_phase == WorkflowPhase.USAGE:
            # 배포 단계 완료 확인
            deployment_status = self.get_step_status("approval_deployment")
            if deployment_status != StepStatus.DEPLOYED:
                return False, "승인 및 배포를 완료해야 합니다."
        
        elif target_phase == WorkflowPhase.MONITORING:
            # 사용 단계에서 모니터링 시작 가능
            pass
        
        elif target_phase == WorkflowPhase.IMPROVEMENT:
            # 모니터링에서 문제 발견 시 개선 단계로
            monitoring_status = self.get_step_status("performance_monitoring")
            if monitoring_status == StepStatus.NOT_STARTED:
                return False, "성능 모니터링을 먼저 수행해야 합니다."
        
        elif target_phase == WorkflowPhase.PREPARATION:
            # 개선 후 다시 준비 단계로 (피드백 루프)
            improvement_status = self.get_step_status("feedback_improvement")
            if improvement_status != StepStatus.COMPLETED:
                return False, "개선 계획을 완료해야 합니다."
        
        return True, ""
    
    def transition_to_phase(self, target_phase: WorkflowPhase) -> Tuple[bool, str]:
        """단계 전환"""
        can_proceed, message = self.can_proceed_to_phase(target_phase)
        
        if not can_proceed:
            return False, message
        
        previous_phase = self.get_current_phase()
        self.workflow_state["current_phase"] = target_phase.value
        self.workflow_state["last_transition"] = {
            "from": previous_phase.value,
            "to": target_phase.value,
            "timestamp": datetime.now().isoformat()
        }
        
        # 피드백 루프 카운트
        if target_phase == WorkflowPhase.PREPARATION and previous_phase == WorkflowPhase.IMPROVEMENT:
            self.workflow_state["feedback_loop_count"] = self.workflow_state.get("feedback_loop_count", 0) + 1
        
        self._save_workflow_state()
        return True, f"{previous_phase.value} → {target_phase.value} 전환 완료"
    
    def get_workflow_summary(self) -> Dict:
        """워크플로우 요약 정보"""
        return {
            "current_phase": self.get_current_phase().value,
            "steps_status": {
                name: step.get("status", StepStatus.NOT_STARTED.value)
                for name, step in self.workflow_state["steps"].items()
            },
            "feedback_loop_count": self.workflow_state.get("feedback_loop_count", 0),
            "last_transition": self.workflow_state.get("last_transition")
        }
    
    def check_actual_step_status(self, step_name: str, config: Optional[Dict] = None) -> StepStatus:
        """
        실제 시스템 상태를 확인하여 단계 상태 반환
        
        Args:
            step_name: 단계 이름
            config: 설정 딕셔너리 (경로 정보 포함)
        
        Returns:
            실제 상태에 맞는 StepStatus
        """
        if not config:
            # config가 없으면 기존 상태 반환
            return self.get_step_status(step_name)
        
        if step_name == "data_management":
            # 데이터 파일 존재 확인
            data_paths = config.get("data_paths", {})
            if not data_paths:
                return self.get_step_status(step_name)
            
            base_dir = Path(__file__).parent.parent.parent
            data_files = []
            for name, path in data_paths.items():
                if not os.path.isabs(path):
                    path = base_dir / path
                else:
                    path = Path(path)
                if path.exists():
                    data_files.append(str(path))
            
            return StepStatus.COMPLETED if len(data_files) > 0 else StepStatus.NOT_STARTED
        
        elif step_name == "schema_design":
            # 스키마 파일 존재 확인
            metadata_path = config.get("metadata_path", "./metadata")
            schema_registry = Path(metadata_path) / "schema_registry.yaml"
            ontology_path = config.get("ontology_path", "./knowledge/ontology")
            schema_file = Path(ontology_path) / "schema.ttl"
            
            if schema_registry.exists() or schema_file.exists():
                return StepStatus.COMPLETED
            return StepStatus.NOT_STARTED
        
        elif step_name == "ontology_generation":
            # 온톨로지 파일 존재 확인
            ontology_path = config.get("ontology_path", "./knowledge/ontology")
            instances_file = Path(ontology_path) / "instances.ttl"
            instances_reasoned_file = Path(ontology_path) / "instances_reasoned.ttl"
            
            if instances_reasoned_file.exists() or instances_file.exists():
                return StepStatus.COMPLETED
            return StepStatus.NOT_STARTED
        
        elif step_name == "rag_indexing":
            # RAG 인덱스 파일 존재 확인
            base_dir = Path(__file__).parent.parent.parent
            rag_index_file = base_dir / "knowledge" / "embeddings" / "faiss_index.bin"
            return StepStatus.COMPLETED if rag_index_file.exists() else StepStatus.NOT_STARTED
        
        elif step_name == "quality_validation":
            # 검증 결과 메타데이터 확인
            step = self.workflow_state["steps"].get(step_name, {})
            if step.get("validation_results"):
                return StepStatus.VALIDATED
            return self.get_step_status(step_name)
        
        elif step_name == "approval_deployment":
            # 배포 정보 확인
            step = self.workflow_state["steps"].get(step_name, {})
            if step.get("deployed_at"):
                return StepStatus.DEPLOYED
            elif step.get("approved_at"):
                return StepStatus.APPROVED
            return self.get_step_status(step_name)
        
        # 기타 단계는 기존 상태 반환
        return self.get_step_status(step_name)
    
    def sync_with_actual_status(self, config: Optional[Dict] = None):
        """
        실제 시스템 상태와 워크플로우 상태 동기화
        
        Args:
            config: 설정 딕셔너리
        """
        if not config:
            return
        
        # 실제 상태를 확인할 수 있는 단계들
        steps_to_check = [
            "data_management",
            "schema_design",
            "ontology_generation", 
            "rag_indexing"
        ]
        
        for step_name in steps_to_check:
            actual_status = self.check_actual_step_status(step_name, config)
            current_status = self.get_step_status(step_name)
            
            # 실제 상태가 완료인데 현재 상태가 미완료면 업데이트
            if actual_status == StepStatus.COMPLETED and \
               current_status in [StepStatus.NOT_STARTED, StepStatus.IN_PROGRESS]:
                self.update_step_status(
                    step_name, 
                    StepStatus.COMPLETED,
                    {"auto_synced": True, "synced_at": datetime.now().isoformat()}
                )

