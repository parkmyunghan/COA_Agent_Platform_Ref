# RAG 기반 교리-COA 연계 구현 완료 보고서

## 문서 정보
- **작성일**: 2026-01-06
- **구현 상태**: ✅ 완료
- **참조 설계 문서**: `docs/30_Guides/RAG_Doctrine_COA_Integration_Design.md`

---

## 구현 완료 항목

### ✅ Phase 1: 교리 문서 자동 생성 파이프라인

**파일**: `core_pipeline/doctrine_generator.py`

**주요 기능**:
- `DoctrineGenerator` 클래스 구현
- LLM 기반 교리 문서 자동 생성
- 교리 문장 단위 청킹 및 RAG 인덱스 자동 추가
- 교리 문서 메타데이터 관리 (doctrine_id, statement_id, mett_c_elements 등)

**사용 예시**:
```python
from core_pipeline.doctrine_generator import DoctrineGenerator

generator = DoctrineGenerator(llm_manager, rag_manager)
doctrine_doc = generator.generate_doctrine_document(
    operation_type="defense",
    mett_c_focus=["Mission", "Terrain", "Troops"],
    coa_purpose=["기동 제한", "방어선 설정"],
    num_statements=5
)

# RAG 인덱스에 자동 추가
generator.save_to_rag(doctrine_doc)
```

---

### ✅ Phase 2: COA 추천 시 교리 인용

**파일**: `core_pipeline/coa_engine/doctrine_reference_service.py`

**주요 기능**:
- `DoctrineReferenceService` 클래스 구현
- COA 추천 시 교리 문장 자동 검색
- METT-C 분석 결과 기반 쿼리 생성
- 교리 문장 파싱 및 메타데이터 추출

**통합 위치**:
- `agents/defense_coa_agent/logic_defense_enhanced.py`
  - `__init__`에서 `DoctrineReferenceService` 초기화
  - `execute_reasoning`에서 상위 3개 COA에 교리 참조 추가

**결과 포맷**:
```json
{
  "coa_id": "COA-02",
  "doctrine_references": [
    {
      "doctrine_id": "DOCTRINE-DEF-001",
      "statement_id": "D-DEF-001",
      "excerpt": "적 주공축이 제한된 지형을 통해 예상될 경우...",
      "relevance_score": 0.92,
      "mett_c_elements": ["Terrain", "Mission"]
    }
  ],
  "mett_c_alignment": {
    "mission": "방어선 유지",
    "terrain": "협소한 접근로"
  }
}
```

---

### ✅ Phase 3: 교리 기반 근거 설명

**파일**: `core_pipeline/coa_engine/doctrine_explanation_generator.py`

**주요 기능**:
- `DoctrineBasedExplanationGenerator` 클래스 구현
- 교리 문장 기반 COA 추천 근거 설명 생성
- 표준화된 설명 포맷 (5단계 구조)
- 안전장치 문장 자동 포함

**통합 위치**:
- `core_pipeline/coa_engine/llm_services.py::COAExplanationGenerator`
  - `generate_coa_explanation` 메서드에 교리 기반 설명 로직 추가
  - 교리 참조가 있으면 자동으로 교리 기반 설명 사용

**설명 구조**:
```markdown
### COA-02 추천 근거 설명

#### 1. 작전 상황 요약
...

#### 2. METT-C 핵심 제약 요소
...

#### 3. 적용된 교리 문장
[D-DEF-001] (관련도: 0.92)
"적 주공축이 제한된 지형을 통해 예상될 경우..."

#### 4. 교리 → COA 연결 논리
...

#### 5. 교리 미적용 영역 (추론)
...

---

**안전장치 문장**:
본 설명은 교리 문장을 근거로 한 추천 논리를 제시하는 것이며,
최종 작전 결정은 지휘관 판단에 따른다.
```

---

## 파일 구조

```
core_pipeline/
├── doctrine_generator.py                    # [NEW] 교리 문서 생성기
└── coa_engine/
    ├── doctrine_reference_service.py        # [NEW] 교리 인용 서비스
    ├── doctrine_explanation_generator.py    # [NEW] 교리 기반 설명 생성기
    └── llm_services.py                      # [MODIFIED] COAExplanationGenerator 확장

agents/
└── defense_coa_agent/
    └── logic_defense_enhanced.py            # [MODIFIED] 교리 인용 통합

core_pipeline/coa_engine/
└── __init__.py                              # [MODIFIED] 새 모듈 export 추가
```

---

## 사용 방법

### 1. 교리 문서 생성

```python
from core_pipeline.doctrine_generator import DoctrineGenerator
from core_pipeline.llm_manager import LLMManager
from core_pipeline.rag_manager import RAGManager

# 초기화
llm_manager = LLMManager()
rag_manager = RAGManager(config)
rag_manager.load_embeddings()

generator = DoctrineGenerator(llm_manager, rag_manager)

# 교리 문서 생성
doctrine_doc = generator.generate_doctrine_document(
    operation_type="defense",
    mett_c_focus=["Mission", "Terrain"],
    coa_purpose=["기동 제한", "방어선 설정"],
    num_statements=5
)

# RAG 인덱스에 추가
generator.save_to_rag(doctrine_doc)
```

### 2. COA 추천 시 교리 인용 (자동)

`EnhancedDefenseCOAAgent`를 사용하면 자동으로 교리 참조가 추가됩니다:

```python
agent = EnhancedDefenseCOAAgent(core)
result = agent.execute_reasoning(situation_id="THREAT_001")

# result["recommendations"][0]["doctrine_references"]에 교리 참조 포함
```

### 3. 교리 기반 설명 생성

```python
from core_pipeline.coa_engine.doctrine_explanation_generator import DoctrineBasedExplanationGenerator

generator = DoctrineBasedExplanationGenerator(llm_manager)

explanation = generator.generate_explanation(
    coa_recommendation=coa_recommendation,  # doctrine_references 포함
    situation_info=situation_info,
    mett_c_analysis=mett_c_analysis,
    axis_states=axis_states
)
```

---

## 테스트 방법

### 1. 교리 문서 생성 테스트

```python
# scripts/test_doctrine_generator.py (생성 필요)
from core_pipeline.doctrine_generator import DoctrineGenerator
from core_pipeline.llm_manager import get_llm_manager
from core_pipeline.rag_manager import RAGManager
import yaml

# 설정 로드
with open("config/global.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 초기화
llm_manager = get_llm_manager()
rag_manager = RAGManager(config)
rag_manager.load_embeddings()

generator = DoctrineGenerator(llm_manager, rag_manager)

# 테스트
doctrine_doc = generator.generate_doctrine_document(
    operation_type="defense",
    mett_c_focus=["Mission", "Terrain"],
    coa_purpose=["기동 제한"],
    num_statements=3
)

print(f"생성된 교리 ID: {doctrine_doc['doctrine_id']}")
print(f"교리 문장 수: {len(doctrine_doc['statements'])}")

# RAG 인덱스에 추가
generator.save_to_rag(doctrine_doc)
```

### 2. 교리 인용 테스트

COA 추천을 실행하면 자동으로 교리 참조가 추가됩니다:

```python
# UI에서 COA 추천 실행 후
# result["recommendations"][0]["doctrine_references"] 확인
```

### 3. 설명 생성 테스트

```python
from core_pipeline.coa_engine.doctrine_explanation_generator import DoctrineBasedExplanationGenerator

# COA 추천 결과 (doctrine_references 포함)
coa_recommendation = {
    "coa_id": "COA-02",
    "coa_name": "지형 차단선 중심 방어",
    "doctrine_references": [
        {
            "statement_id": "D-DEF-001",
            "excerpt": "적 주공축이 제한된 지형을 통해 예상될 경우...",
            "relevance_score": 0.92
        }
    ]
}

generator = DoctrineBasedExplanationGenerator()
explanation = generator.generate_explanation(
    coa_recommendation=coa_recommendation,
    situation_info={},
    mett_c_analysis={},
    axis_states=[]
)

print(explanation)
```

---

## 향후 개선 사항

### 1. 교리 문장 품질 개선
- 교리 생성 프롬프트 반복 개선
- 생성된 교리 문장 검증 파이프라인
- 사용자 피드백 기반 교리 문장 업데이트

### 2. RAG 검색 정확도 개선
- 교리 문장별 임베딩 최적화
- 메타데이터 기반 필터링 강화
- 하이브리드 검색 가중치 조정

### 3. 설명 생성 개선
- 교리 문장과 COA 연결 논리 자동화 (LLM 활용)
- 다중 교리 문장 조합 설명
- 시각화 지원 (교리 → COA 연결 그래프)

### 4. UI 통합
- COA 추천 결과에 교리 참조 표시
- 교리 기반 설명 UI 컴포넌트 추가
- 교리 문서 관리 UI 추가

---

## 주의사항

1. **교리 문서는 "가상 교리"임을 명시**
   - 실제 교범을 인용하거나 요약하지 않음
   - 교리 '형식'과 '논리 구조'만 재현

2. **안전장치 문장 필수 포함**
   - 모든 설명에 "최종 작전 결정은 지휘관 판단에 따른다" 문장 포함

3. **점진적 활성화**
   - 교리 참조가 없어도 기존 방식으로 동작
   - RAG 인덱스가 없어도 오류 없이 동작

---

## 체크리스트

### 구현 완료
- [x] `DoctrineGenerator` 클래스 구현
- [x] `DoctrineReferenceService` 클래스 구현
- [x] `DoctrineBasedExplanationGenerator` 클래스 구현
- [x] `EnhancedDefenseCOAAgent`에 교리 인용 통합
- [x] `COAExplanationGenerator`에 교리 기반 설명 통합
- [x] 모듈 export 추가 (`__init__.py`)

### 테스트 필요
- [ ] 교리 문서 생성 테스트
- [ ] 교리 인용 검색 테스트
- [ ] 교리 기반 설명 생성 테스트
- [ ] 전체 파이프라인 통합 테스트

### 문서화 필요
- [ ] 사용자 가이드 작성
- [ ] API 문서 작성
- [ ] 예제 코드 추가

---

**구현 완료일**: 2026-01-06  
**구현자**: AI Assistant  
**검토 상태**: 대기 중


