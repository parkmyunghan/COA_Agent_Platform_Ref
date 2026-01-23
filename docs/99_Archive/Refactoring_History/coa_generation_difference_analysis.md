# 방책 추천 로직 차이점 분석 및 해결 방안

## 문제 요약

현재 React 구현의 방책 추천 로직이 기존 Streamlit 시스템과 다르게 동작하고 있습니다. Streamlit에서는 Agent 기반의 통합 파이프라인을 사용하지만, React에서는 COAService의 규칙 기반 로직만 사용하고 있습니다.

## 차이점 분석

### 1. Streamlit 방식 (기존 시스템)

**호출 경로:**
```
UI → EnhancedDefenseCOAAgent.execute_reasoning()
```

**주요 특징:**
1. **Agent 기반 통합 파이프라인**
   - `EnhancedDefenseCOAAgent.execute_reasoning()` 직접 호출
   - 온톨로지, RAG, LLM을 모두 활용한 복합적인 방책 생성

2. **4단계 프로세스**
   - **Phase 1: 상황 분석**
     - 다차원 상황 분석 (`_analyze_situation_dimensions`)
     - 온톨로지 관련 엔티티 탐색 (`_find_related_entities_enhanced`)
     - RAG 검색 (`retrieve_with_context`)
     - LLM 협력 (`analyze_situation`)
   
   - **Phase 2: 방책 검색 (타입별)**
     - SPARQL 쿼리로 타입별 방책 후보 필터링
     - 온톨로지 기반 검색 (`_search_coas_from_ontology`)
     - 임베딩 기반 유사도 검색
     - 하이브리드 검색
   
   - **Phase 3: 점수 계산**
     - 팔란티어 모드: 6가지 요소 종합 평가
     - 각 방책별 독립적인 컨텍스트 생성
     - RAG 기반 역사적 성공률 조회
   
   - **Phase 4: LLM 적응화**
     - LLM이 방책을 현재 상황에 맞게 구체화
     - 추천 이유 생성 (`_generate_overall_situation_summary`)
     - 교범 참조 문서 검색

3. **출력 형식**
   ```python
   {
       "agent": "EnhancedDefenseCOAAgent",
       "status": "completed",
       "situation_id": "...",
       "situation_analysis": {...},
       "recommendations": [...],  # COA 리스트
       "situation_summary": "...",  # 자연어 요약
       "llm_collaboration": {...},
       "palantir_mode": True
   }
   ```

### 2. React/FastAPI 방식 (현재 구현)

**호출 경로:**
```
Frontend → API /coa/generate → COAService.generate_coas_unified() 
→ EnhancedCOAGenerator.generate_coas()
```

**주요 특징:**
1. **COAService 기반 규칙 로직**
   - `COAService.generate_coas_unified()` 사용
   - `EnhancedCOAGenerator.generate_coas()` 호출
   - Agent의 `execute_reasoning()`을 사용하지 않음

2. **제한된 프로세스**
   - 규칙 기반 COA 생성 (기본 로직)
   - 온톨로지 보강 (선택적)
   - **RAG 검색 없음**
   - **LLM 협력 없음**
   - **상황 분석 단계 없음**

3. **출력 형식**
   ```python
   {
       "coas": [...],
       "evaluations": [...],
       "top_coas": [...],
       "axis_states": [...]
       # situation_summary 없음
       # reasoning_trace 없음
       # doctrine_references 없음
   }
   ```

## 핵심 차이점

| 항목 | Streamlit (Agent) | React (COAService) |
|------|------------------|-------------------|
| **상황 분석** | ✅ 다차원 분석 + 온톨로지 + RAG + LLM | ❌ 없음 |
| **방책 검색** | ✅ SPARQL + 임베딩 + 하이브리드 | ⚠️ 온톨로지 보강만 |
| **점수 계산** | ✅ 팔란티어 모드 (6요소) | ⚠️ 기본 점수 계산 |
| **LLM 적응화** | ✅ 상황 맞춤 구체화 | ❌ 없음 |
| **추론 근거** | ✅ reasoning_trace 생성 | ❌ 없음 |
| **교범 참조** | ✅ RAG 검색 기반 | ❌ 없음 |
| **상황 요약** | ✅ 자연어 요약 생성 | ❌ 없음 |

## 원인 분석

### 1. API 엔드포인트 부재
- `/coa/generate` 엔드포인트가 `COAService.generate_coas_unified()`만 호출
- Agent 실행을 위한 별도 엔드포인트가 없음

### 2. COAService의 제한적 구현
- `COAService`는 규칙 기반 로직 중심
- Agent의 통합 파이프라인을 활용하지 않음
- 온톨로지 보강만 제공하고 RAG/LLM 협력 없음

### 3. 프론트엔드 요청 형식
- Agent 실행에 필요한 파라미터 전달 불가
- `selected_situation_info`, `coa_type_filter`, `use_palantir_mode` 등 Agent 전용 파라미터 미지원

## 해결 방안

### 방안 1: Agent 실행 API 엔드포인트 추가 (권장)

**장점:**
- Streamlit과 동일한 로직 사용
- 최소한의 변경으로 기존 기능 활용
- 향후 확장성 우수

**구현:**
1. `/api/v1/agent/execute` 엔드포인트 추가
2. Agent 클래스 로드 및 실행
3. 결과를 COAResponse 형식으로 변환

**코드 예시:**
```python
# api/routers/agent.py
@router.post("/execute", response_model=COAResponse)
def execute_agent(
    request: AgentExecutionRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    # Agent 클래스 로드
    agent_class = orchestrator.load_agent_class(request.agent_class_path)
    agent = agent_class(core=orchestrator.core)
    
    # Agent 실행
    result = agent.execute_reasoning(
        situation_id=request.situation_id,
        selected_situation_info=request.situation_info,
        use_palantir_mode=request.use_palantir_mode,
        enable_rag_search=True,
        coa_type_filter=request.coa_type_filter,
        status_callback=on_status_update
    )
    
    # 결과 변환
    return convert_agent_result_to_coa_response(result)
```

### 방안 2: COAService에 Agent 통합

**장점:**
- 기존 API 구조 유지
- 점진적 마이그레이션 가능

**단점:**
- COAService가 Agent 의존성 추가
- 코드 복잡도 증가

**구현:**
```python
# core_pipeline/coa_service.py
def generate_coas_unified(self, ..., use_agent: bool = True):
    if use_agent:
        # Agent 기반 생성
        agent = EnhancedDefenseCOAAgent(core=self.orchestrator.core)
        result = agent.execute_reasoning(...)
        return convert_to_unified_format(result)
    else:
        # 기존 규칙 기반 생성
        ...
```

### 방안 3: 하이브리드 방식

**장점:**
- 두 방식 모두 지원
- 사용자 선택 가능

**구현:**
- `user_params`에 `use_agent_mode` 플래그 추가
- 플래그에 따라 Agent 또는 COAService 사용

## 권장 해결 방안

**방안 1 (Agent 실행 API 추가)을 권장합니다.**

### 이유:
1. **기존 로직 재사용**: Streamlit의 검증된 로직 그대로 사용
2. **최소 변경**: 기존 코드 수정 최소화
3. **확장성**: 향후 다른 Agent 추가 용이
4. **일관성**: Streamlit과 동일한 결과 보장

### 구현 계획

1. **API 엔드포인트 추가**
   - `api/routers/agent.py` 생성
   - `/api/v1/agent/execute` 엔드포인트 구현

2. **스키마 정의**
   - `AgentExecutionRequest` 스키마 추가
   - Agent 결과를 `COAResponse`로 변환하는 함수 구현

3. **프론트엔드 수정**
   - `COAGenerator.tsx`에서 Agent API 호출로 변경
   - Agent 실행에 필요한 파라미터 전달

4. **결과 변환**
   - Agent 결과 형식을 COAResponse로 변환
   - `situation_summary`, `reasoning_trace`, `doctrine_references` 포함

## 예상 효과

### 개선 사항
1. ✅ 온톨로지 + RAG + LLM 통합 활용
2. ✅ 상황 분석 단계 포함
3. ✅ 추론 근거 및 교범 참조 제공
4. ✅ 자연어 상황 요약 생성
5. ✅ 팔란티어 모드 정확한 점수 계산

### 성능 고려사항
- Agent 실행 시간이 더 길 수 있음 (LLM 호출 포함)
- 진행 상황 업데이트를 위한 WebSocket 또는 폴링 필요
- 결과 캐싱 고려
