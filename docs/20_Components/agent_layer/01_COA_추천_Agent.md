# COA 추천 Agent (EnhancedDefenseCOAAgent)

## 1. 개요

- **역할**: 상황 분석 및 COA 추천 (통합 Agent)
- **위치**: Agent Layer
- **클래스**: `agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent`
- **다이어그램 표시**: "COA 추천 Agent (EnhancedDefenseCOAAgent)"

COA 추천 Agent는 시스템의 핵심 지능형 에이전트로, 상황 분석과 방책 추천을 통합적으로 수행합니다. 이전에는 "상황 분석 Agent"와 "COA 추천 Agent"로 분리되어 있었으나, 현재는 단일 클래스 내부에서 두 기능을 모두 수행합니다.

---

## 2. 주요 기능

### 2.1 상황 분석
- **`_analyze_situation()`**: 다차원 상황 분석
  - 위협 심각도, 긴급도, 복잡도 분석
  - 관련 엔티티 탐색 (온톨로지 그래프)
  - RAG 검색 (유사 상황 검색)
  - LLM 협력 (상황 의미 분석)

### 2.2 COA 추천
- **`_recommend_by_type()`**: 타입별 방책 추천
  - 7가지 방책 타입 지원 (방어, 공격, 반격, 선제, 억제, 기동, 정보작전)
  - 온톨로지 기반 검색
  - 임베딩 기반 유사도 검색
  - 하이브리드 검색

### 2.3 점수 계산
- **`_score_with_palantir_mode()`**: 팔란티어 모드 점수 계산
  - **7가지 요소** 종합 평가 (위협대응, 자원가용성, 전력능력, 환경적합성, 효과성, 연계성, 임무부합성)
  - 각 방책별 독립적인 컨텍스트(Context) 생성 및 시뮬레이션

---

## 3. 구현 상세

### 3.1 클래스 위치
```python
# agents/defense_coa_agent/logic_defense_enhanced.py
class EnhancedDefenseCOAAgent(BaseAgent):
    """강화된 방책추천 에이전트 (현재 시스템 로직 통합)"""
```

### 3.2 주요 메서드

#### `execute_reasoning(situation_id, **kwargs)`
전체 추론 프로세스를 실행합니다.

```python
# 사용 예시
result = agent.execute_reasoning(
    situation_id="THR001",
    selected_situation_info=situation_info,
    coa_type_filter=["defense", "offensive"],
    use_embedding=True,
    top_k=5
)
```

#### `_analyze_situation(situation_info, **kwargs)`
상황을 분석합니다.

```python
situation_analysis = agent._analyze_situation(
    situation_info,
    enable_rag_search=True,
    enable_llm_analysis=True
)
```

---

## 4. 데이터 흐름

```
사용자 입력 (상황 정보)
    ↓
execute_reasoning()
    ↓
_analyze_situation()
    ├─→ DataManager: 상황 정보 로드
    ├─→ OntologyManager: 관련 엔티티 탐색
    ├─→ RAGManager: 유사 상황 검색
    └─→ LLMManager: 상황 의미 분석
    ↓
_recommend_by_type()
    ├─→ OntologyManager: SPARQL 쿼리
    └─→ 임베딩 검색 (선택적)
    ↓
_score_with_palantir_mode()
    └─→ COAScorer: 점수 계산
    ↓
LLM 적응화
    └─→ LLMManager: 설명 생성
    ↓
추천 결과 반환
```

---

## 5. 설정 및 파라미터

### 5.1 Agent 등록
- **위치**: `config/agent_registry.yaml`
- **설정**:
  ```yaml
  - name: coa_recommendation_agent
    class: agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent
    enabled: true
  ```

### 5.2 지원하는 방책 타입
```python
supported_coa_types = [
    "defense", "offensive", "counter_attack", 
    "preemptive", "deterrence", "maneuver", "information_ops"
]
```

---

## 6. 사용 예시

### 6.1 기본 사용
```python
from core_pipeline.orchestrator import Orchestrator

# Orchestrator에서 Agent 가져오기
orchestrator = Orchestrator(config)
orchestrator.initialize()
agent = orchestrator.get_agent("coa_recommendation_agent")

# 추천 실행
result = agent.execute_reasoning(
    situation_id="THR001",
    selected_situation_info={
        "위협유형": "침투",
        "심각도": 85,
        "threat_level": 0.85
    },
    coa_type_filter=["defense"],
    top_k=5
)
```

### 6.2 모든 타입 추천
```python
result = agent.execute_reasoning(
    situation_id="THR001",
    selected_situation_info=situation_info,
    coa_type_filter=["all"],  # 모든 타입
    top_k=10
)
```

---

## 7. 관련 컴포넌트

### 7.1 입력
- **DataManager**: 상황 정보 및 방책 라이브러리
- **OntologyManager**: 관련 엔티티 및 SPARQL 쿼리
- **RAGManager**: 유사 상황 검색 결과

### 7.2 출력
- **COAScorer**: 점수 계산 요청
- **LLMManager**: 상황 분석 및 설명 생성 요청
- **사용자 인터페이스**: 추천 결과 반환

---

## 8. 참고 자료

- **코드 위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`
- **관련 문서**: 
  - `docs/방책추천_시스템.md`
  - `docs/점수_산정_시스템.md`
  - `docs/시스템_아키텍처.md`
- **설정 파일**: `config/agent_registry.yaml`

---

## 9. 중요 사항

### 9.1 통합 구조
이전에는 "상황 분석 Agent"와 "COA 추천 Agent"를 별도로 표시했으나, 실제로는 **단일 클래스 내부에서 두 기능을 모두 수행**합니다:
- `_analyze_situation()`: 상황 분석 (내부 메서드)
- `_recommend_by_type()`: COA 추천 (내부 메서드)

### 9.2 7가지 방책 타입 지원
기본값은 `["defense"]`이지만, `coa_type_filter` 파라미터로 모든 타입을 선택할 수 있습니다.

---

**작성일**: 2025년 12월  
**버전**: 1.0

