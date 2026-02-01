# 온톨로지 스튜디오 단계별 진행 상황 데이터 소스

## 현재 구조

### 데이터 소스

단계별 진행 상황은 다음 소스에서 데이터를 가져옵니다:

1. **워크플로우 상태 파일**: `metadata/ontology_workflow.json`
   - 각 단계의 상태(status) 저장
   - 완료 일시(completed_at) 저장
   - 검증 결과 등 메타데이터 저장

2. **데이터 흐름**:
   ```
   workflow_status_dashboard.py
       ↓
   workflow_manager.get_step_status(step_name)
       ↓
   ontology_workflow.json 파일 읽기
       ↓
   StepStatus 반환
   ```

### 현재 문제점

1. **수동 상태 업데이트 필요**
   - 각 단계 완료 시 `update_step_status()`를 수동으로 호출해야 함
   - 실제 시스템 상태(파일 존재, 그래프 존재 등)를 자동으로 확인하지 않음

2. **실제 완료 여부와 상태 불일치 가능**
   - 예: 온톨로지 파일이 존재하지만 상태가 `NOT_STARTED`일 수 있음
   - 예: RAG 인덱스가 생성되었지만 상태가 업데이트되지 않을 수 있음

## 개선 방안

### 1. 실제 시스템 상태 확인 메서드 추가

`OntologyWorkflowManager`에 실제 시스템 상태를 확인하는 메서드를 추가합니다:

```python
def check_actual_step_status(self, step_name: str, config: Dict = None) -> StepStatus:
    """
    실제 시스템 상태를 확인하여 단계 상태 반환
    
    Args:
        step_name: 단계 이름
        config: 설정 딕셔너리 (경로 정보 포함)
    
    Returns:
        실제 상태에 맞는 StepStatus
    """
    if step_name == "data_management":
        # 데이터 파일 존재 확인
        data_paths = config.get("data_paths", {})
        data_files = [p for p in data_paths.values() if Path(p).exists()]
        return StepStatus.COMPLETED if len(data_files) > 0 else StepStatus.NOT_STARTED
    
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
        rag_index_file = Path("knowledge/embeddings/faiss_index.bin")
        return StepStatus.COMPLETED if rag_index_file.exists() else StepStatus.NOT_STARTED
    
    # 기타 단계는 기존 상태 반환
    return self.get_step_status(step_name)
```

### 2. 자동 동기화 기능

대시보드에서 실제 상태를 확인하고 워크플로우 상태와 동기화:

```python
def sync_with_actual_status(self, config: Dict):
    """
    실제 시스템 상태와 워크플로우 상태 동기화
    
    Args:
        config: 설정 딕셔너리
    """
    steps_to_check = [
        "data_management",
        "ontology_generation", 
        "rag_indexing"
    ]
    
    for step_name in steps_to_check:
        actual_status = self.check_actual_step_status(step_name, config)
        current_status = self.get_step_status(step_name)
        
        # 실제 상태가 완료인데 현재 상태가 미완료면 업데이트
        if actual_status == StepStatus.COMPLETED and \
           current_status in [StepStatus.NOT_STARTED, StepStatus.IN_PROGRESS]:
            self.update_step_status(step_name, StepStatus.COMPLETED)
```

### 3. 통합 상태 확인

`workflow_status_dashboard.py`에서 실제 상태와 워크플로우 상태를 모두 표시:

```python
def render_workflow_status_dashboard(workflow_manager, orchestrator):
    """워크플로우 상태 대시보드 렌더링 (실제 상태 확인 포함)"""
    
    # 실제 시스템 상태 동기화
    config = orchestrator.config if hasattr(orchestrator, 'config') else {}
    workflow_manager.sync_with_actual_status(config)
    
    # 기존 렌더링 로직...
```

## 구현 예시

### 단계별 실제 상태 확인 기준

| 단계 | 확인 항목 | 완료 기준 |
|------|----------|----------|
| **data_management** | 데이터 파일 존재 | `data_paths`에 정의된 파일 중 1개 이상 존재 |
| **schema_design** | 스키마 파일 존재 | `schema_registry.yaml` 존재 또는 `schema.ttl` 존재 |
| **ontology_generation** | 온톨로지 파일 존재 | `instances.ttl` 또는 `instances_reasoned.ttl` 존재 |
| **rag_indexing** | RAG 인덱스 파일 존재 | `faiss_index.bin` 존재 |
| **quality_validation** | 검증 결과 존재 | `validation_results` 메타데이터 존재 |
| **approval_deployment** | 배포 정보 존재 | `deployed_at` 메타데이터 존재 |
| **knowledge_exploration** | 사용 기록 | `usage_count` > 0 |
| **agent_execution** | 사용 기록 | `usage_count` > 0 |
| **performance_monitoring** | 모니터링 기록 | `last_monitored_at` 메타데이터 존재 |
| **feedback_improvement** | 개선 계획 존재 | `improvement_plans` 메타데이터 존재 |

## 권장 사항

1. **자동 동기화 활성화**
   - 대시보드 로드 시 자동으로 실제 상태 확인
   - 사용자가 "상태 새로고침" 버튼 클릭 시 동기화

2. **상태 불일치 경고**
   - 실제 상태와 워크플로우 상태가 불일치할 때 경고 표시
   - 사용자에게 동기화 옵션 제공

3. **실시간 모니터링**
   - 파일 시스템 변경 감지 (선택적)
   - 주기적인 상태 확인 (선택적)

