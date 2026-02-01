# Orchestrator (CorePipeline)

## 1. 개요

- **역할**: 전체 파이프라인 조율 및 Agent 관리
- **위치**: Orchestration Layer
- **클래스**: `core_pipeline.orchestrator.Orchestrator`, `core_pipeline.orchestrator.CorePipeline`
- **다이어그램 표시**: "Orchestrator (Core Pipeline)"

Orchestrator는 시스템의 전체 워크플로우를 조율하고 제어하는 핵심 컴포넌트입니다. Agent를 등록하고 관리하며, CorePipeline을 통해 모든 하위 컴포넌트를 초기화하고 연결합니다.

---

## 2. 주요 기능

### 2.1 Agent 관리
- **`register_agent()`**: Agent 등록
- **`get_agent()`**: 등록된 Agent 조회
- **`load_agent_class()`**: Agent 클래스 동적 로드

### 2.2 CorePipeline 초기화
- DataManager, OntologyManager, RAGManager, LLMManager 초기화
- 온톨로지 그래프 자동 구축
- GPU 메모리 관리 및 최적화

### 2.3 워크플로우 제어
- 전체 파이프라인 초기화 순서 관리
- 컴포넌트 간 의존성 해결

---

## 3. 구현 상세

### 3.1 클래스 위치
```python
# core_pipeline/orchestrator.py
class Orchestrator:
    """오케스트레이터 클래스"""
    
class CorePipeline:
    """코어 파이프라인 클래스"""
```

### 3.2 주요 메서드

#### `register_agent(name: str, agent_class: Type, **kwargs)`
Agent를 등록합니다.

```python
# 사용 예시
orchestrator = Orchestrator(config)
orchestrator.register_agent(
    "coa_agent",
    EnhancedDefenseCOAAgent
)
```

#### `initialize()`
시스템을 초기화합니다.

```python
# 사용 예시
orchestrator.initialize()
```

---

## 4. 데이터 흐름

```
설정 파일 (config.yaml)
    ↓
Orchestrator 초기화
    ↓
CorePipeline 생성
    ├─→ DataManager 초기화
    ├─→ OntologyManager 초기화
    ├─→ RAGManager 초기화
    ├─→ LLMManager 초기화
    └─→ ReasoningEngine 초기화
    ↓
Agent 등록
    ↓
시스템 준비 완료
```

---

## 5. 설정 및 파라미터

### 5.1 설정 파일
- **위치**: `config/config.yaml`
- **주요 설정**:
  ```yaml
  data_paths:
    data_lake_path: "./data_lake"
    ontology_path: "./knowledge/ontology"
    embedding_path: "./knowledge/embeddings"
  ```

### 5.2 Agent 등록
- **위치**: `config/agent_registry.yaml`
- **형식**:
  ```yaml
  agents:
    - name: coa_recommendation_agent
      class: agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent
      enabled: true
  ```

---

## 6. 사용 예시

### 6.1 기본 사용
```python
from core_pipeline.orchestrator import Orchestrator

# 초기화
config = load_config()
orchestrator = Orchestrator(config, use_enhanced_ontology=True)
orchestrator.initialize()

# Agent 가져오기
agent = orchestrator.get_agent("coa_recommendation_agent")
```

### 6.2 FastAPI에서 사용
```python
# api/routers/system.py
from api.dependencies import get_global_state

state = get_global_state()
orchestrator = state.get_orchestrator()
```

---

## 7. 관련 컴포넌트

### 7.1 관리하는 컴포넌트
- **DataManager**: 데이터 로드 및 관리
- **OntologyManager**: 온톨로지 그래프 구축
- **RAGManager**: 벡터 검색
- **LLMManager**: LLM 모델 관리
- **ReasoningEngine**: 추론 엔진

### 7.2 관리하는 Agent
- **EnhancedDefenseCOAAgent**: COA 추천 Agent

---

## 8. 참고 자료

- **코드 위치**: `core_pipeline/orchestrator.py`
- **관련 문서**: 
  - `docs/시스템_아키텍처.md`
- **설정 파일**: 
  - `config/config.yaml`
  - `config/agent_registry.yaml`

---

**작성일**: 2026년 1월
**최종 업데이트**: 2026-01-26
**버전**: 2.0 (React Re-platforming)

