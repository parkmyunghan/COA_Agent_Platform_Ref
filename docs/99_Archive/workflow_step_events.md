# 워크플로우 Step 이벤트 정의

## 개요

각 Step의 마지막 수행 일시를 기록하기 위한 이벤트 트리거 정의입니다.

## Step별 이벤트 정의

### 1. data_management (데이터 관리)
- **파일**: `ui/views/data_management.py` 또는 `ui/components/data_panel.py`
- **이벤트**: 데이터 파일 로드/업로드 성공 시
- **기록 시점**: 데이터 로드 완료 후
- **상태**: `COMPLETED`
- **메타데이터**: `data_files_count`

### 2. schema_design (스키마 설계)
- **파일**: `ui/components/ontology_studio/schema_manager.py`
- **이벤트**: 스키마 검증 통과 시
- **기록 시점**: 스키마 검증 완료 후 (점수 >= 80)
- **상태**: `COMPLETED`
- **메타데이터**: `validation_score`

### 3. ontology_generation (온톨로지 생성)
- **파일**: `ui/views/ontology_generation.py`
- **이벤트**: "그래프 생성" 버튼 클릭 후 성공 시
- **기록 시점**: 그래프 생성 및 저장 완료 후
- **상태**: `COMPLETED`
- **메타데이터**: `triples_count`, `enable_virtual_entities`, `enable_reasoned_graph`

### 4. rag_indexing (RAG 인덱스 구성)
- **파일**: `ui/views/rag_indexing.py` 또는 `ui/components/doc_manager.py`
- **이벤트**: RAG 인덱스 생성 버튼 클릭 후 성공 시
- **기록 시점**: 인덱스 생성 및 저장 완료 후
- **상태**: `COMPLETED`
- **메타데이터**: `index_size`, `document_count`

### 5. quality_validation (품질 검증)
- **파일**: `ui/components/ontology_studio/quality_assurance.py`
- **이벤트**: "검증 실행" 버튼 클릭 후 검증 완료 시
- **기록 시점**: 검증 완료 후 (통과/실패 무관)
- **상태**: `VALIDATED` (점수 >= 80) 또는 `FAILED` (점수 < 80)
- **메타데이터**: `validation_results`, `overall_score`

### 6. approval_deployment (승인 및 배포)
- **파일**: `ui/components/ontology_studio/approval_deployment.py`
- **이벤트**: 
  - 승인: "✅ 승인" 버튼 클릭 시
  - 배포: "프로덕션 배포" 버튼 클릭 시
- **기록 시점**: 각 액션 완료 후
- **상태**: `APPROVED` (승인) 또는 `DEPLOYED` (배포)
- **메타데이터**: `approved_at`, `deployed_at`

### 7. knowledge_exploration (지식 탐색)
- **파일**: `ui/views/knowledge_graph.py`
- **이벤트**: SPARQL 쿼리 실행 또는 그래프 탐색 시작 시
- **기록 시점**: 쿼리 실행 또는 탐색 시작 시
- **상태**: `COMPLETED` (또는 `IN_PROGRESS`)
- **메타데이터**: `usage_count`

### 8. agent_execution (Agent 실행)
- **파일**: `ui/views/agent_execution.py`
- **이벤트**: Agent 실행 버튼 클릭 후 실행 완료 시
- **기록 시점**: 실행 완료 후
- **상태**: `COMPLETED`
- **메타데이터**: `usage_count`

### 9. performance_monitoring (성능 모니터링)
- **파일**: `ui/components/ontology_studio/feedback_improvement.py` (향후 별도 페이지)
- **이벤트**: 모니터링 실행 버튼 클릭 후 모니터링 완료 시
- **기록 시점**: 모니터링 완료 후
- **상태**: `COMPLETED`
- **메타데이터**: `last_monitored_at`, `issues_found`

### 10. feedback_improvement (피드백 및 개선)
- **파일**: `ui/components/ontology_studio/feedback_improvement.py`
- **이벤트**: "개선 완료 및 워크플로우 재시작" 버튼 클릭 시
- **기록 시점**: 개선 계획 수립 완료 후
- **상태**: `COMPLETED`
- **메타데이터**: `improvement_plans`

## 구현 상태

✅ **구현 완료**:
- schema_design
- ontology_generation
- quality_validation
- approval_deployment
- feedback_improvement

⏳ **구현 예정**:
- data_management
- rag_indexing
- knowledge_exploration
- agent_execution
- performance_monitoring

## 사용 예시

```python
from core_pipeline.ontology_workflow_manager import StepStatus
from datetime import datetime

# Step 상태 업데이트
workflow_manager.update_step_status(
    "ontology_generation",
    StepStatus.COMPLETED,
    {
        "last_executed_at": datetime.now().isoformat(),
        "triples_count": 12345,
        "enable_virtual_entities": True
    }
)
```

