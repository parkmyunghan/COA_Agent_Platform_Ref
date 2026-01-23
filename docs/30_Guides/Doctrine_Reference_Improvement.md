# 교리 참조 기능 개선 보고서

## 문서 정보
- **작성일**: 2026-01-06
- **목적**: 교리 참조 기능의 문제점 분석 및 개선 사항 정리

---

## 1. 문제점 분석

### 1.1 발견된 문제점

1. **교리 문장 본문 추출 실패**
   - 문제: "# Doctrine_ID: DOCTRINE-DEF-001", "1. 선행 방책 (Preceding COA)" 등 의미없는 헤더나 리스트 항목만 추출됨
   - 원인: `_extract_doctrine_excerpt`가 마크다운 헤더를 제대로 필터링하지 못함

2. **교리 ID 추출 실패**
   - 문제: 교리 ID가 "UNKNOWN"으로 표시됨
   - 원인: RAG 청크가 교리 문서 헤더를 포함하지 않아 메타데이터가 없음

3. **METT-C 요소 부정확**
   - 문제: 내용과 무관한 METT-C 요소가 제시됨 (예: 모든 요소가 표시됨)
   - 원인: 단순 키워드 매칭만 사용하여 부정확함

4. **RAG 청킹 문제**
   - 문제: 교리 문서가 임의로 청킹되어 교리 문장 단위가 깨짐
   - 원인: 일반 문서 청킹 방식을 사용하여 교리 문서 구조를 고려하지 않음

5. **의미없는 결과 포함**
   - 문제: 관련도가 낮거나 의미없는 결과가 포함됨
   - 원인: 필터링 로직 부재

---

## 2. 개선 사항

### 2.1 교리 문서 전용 청킹 함수 추가

**파일**: `core_pipeline/rag_manager.py`

**추가된 함수**: `chunk_doctrine_documents()`

**기능**:
- 교리 문서를 교리 문장 단위로 청킹
- 각 청크에 메타데이터 포함:
  - `doctrine_id`: 교리 문서 ID
  - `statement_id`: 교리 문장 ID
  - `statement_text`: 실제 교리 문장 본문
  - `mett_c_elements`: 관련 METT-C 요소 리스트
  - `interpretation`: 작전적 해석

**예시**:
```python
chunks = rag_manager.chunk_doctrine_documents(doctrine_docs, doc_names=doctrine_names)
# 결과: 각 청크에 교리 문장 본문과 메타데이터가 포함됨
```

### 2.2 교리 참조 파싱 로직 개선

**파일**: `core_pipeline/coa_engine/doctrine_reference_service.py`

**개선 사항**:

1. **메타데이터 우선 사용**
   - RAG 결과의 메타데이터에서 `statement_text` 우선 사용
   - 없으면 텍스트에서 추출

2. **텍스트 정리 함수 추가**
   - `_clean_doctrine_text()`: 마크다운, 헤더, 주석 제거
   - 실제 교리 문장 본문만 추출

3. **교리 문장 본문 추출 개선**
   - `_extract_doctrine_excerpt()` 개선
   - 헤더, 주석, 메타데이터 제거
   - 첫 번째 의미있는 문장 추출

**예시**:
```python
# 개선 전
excerpt = "# Doctrine_ID: DOCTRINE-DEF-001\n1. 선행 방책..."

# 개선 후
excerpt = "적 주공축이 제한된 지형을 통해 예상될 경우, 방어 COA는 지형 차단선을 중심으로 구성되는 것이 권장된다."
```

### 2.3 METT-C 요소 추출 개선

**파일**: `core_pipeline/coa_engine/doctrine_reference_service.py`

**개선 사항**:

1. **헤더에서 METT-C 요소 추출**
   - 교리 문서 헤더의 "## 관련 METT-C 요소: Mission, Terrain, Troops" 패턴 인식
   - 쉼표로 구분된 요소 추출

2. **표준 METT-C 요소명 매핑**
   - 소문자/대문자 변형 자동 처리
   - 표준 요소명으로 정규화

3. **키워드 기반 추출 개선**
   - 헤더에서 추출 실패 시에만 키워드 매칭 사용
   - 기본값 제거 (빈 리스트 반환 가능)

**예시**:
```python
# 개선 전
mett_c_elements = ["Mission", "Enemy", "Troops", "Time"]  # 모든 요소

# 개선 후
mett_c_elements = ["Mission", "Terrain", "Troops"]  # 교리 문서 헤더에서 정확히 추출
```

### 2.4 RAG 검색 쿼리 개선

**파일**: `core_pipeline/coa_engine/doctrine_reference_service.py`

**개선 사항**:

1. **COA 설명 활용**
   - COA 설명에서 핵심 키워드 추출
   - "방어", "기동", "차단" 등 작전 관련 키워드 포함

2. **METT-C 핵심 정보만 추출**
   - 긴 요약이 아닌 핵심 키워드만 사용
   - 50자 이하의 간결한 정보만 포함

3. **축선 정보 간소화**
   - 위협 수준을 "고위협", "중위협", "저위협"으로 변환
   - 상위 2개 축선만 사용

**예시**:
```python
# 개선 전
query = "COA: 지형 차단선 중심 방어 임무: 방어선 유지 및 적의 진격 저지 지형: 협소한 접근로..."

# 개선 후
query = "방어 차단 지형 차단선 중심 방어 방어선 유지 협소한 접근로 고위협"
```

### 2.5 의미없는 결과 필터링

**파일**: `core_pipeline/coa_engine/doctrine_reference_service.py`

**개선 사항**:

1. **교리 문장 본문 길이 검증**
   - 15자 미만의 짧은 텍스트 제외

2. **교리 ID 검증**
   - 교리 ID가 없거나 "UNKNOWN"이면 제외 (단, 텍스트에서 추출 가능한 경우는 포함)

3. **관련도 점수 필터링**
   - 0.3 미만의 낮은 관련도 결과 제외

**예시**:
```python
# 필터링 전
results = [
    {"excerpt": "# Doctrine_ID...", "relevance_score": 0.15},  # 제외됨
    {"excerpt": "방어 작전 시...", "relevance_score": 0.85}  # 포함됨
]

# 필터링 후
results = [
    {"excerpt": "방어 작전 시...", "relevance_score": 0.85}  # 의미있는 결과만
]
```

### 2.6 RAG Manager 메타데이터 처리 개선

**파일**: `core_pipeline/rag_manager.py`

**개선 사항**:

1. **retrieve_with_context 메타데이터 포함**
   - 교리 문서 메타데이터를 결과에 포함
   - `doctrine_id`, `statement_id`, `statement_text`, `mett_c_elements` 등

2. **최상위 레벨 메타데이터 포함**
   - 하위 호환성을 위해 메타데이터를 최상위 레벨에도 포함
   - `DoctrineReferenceService`에서 직접 접근 가능

**예시**:
```python
# 개선 전
result = {
    "text": "...",
    "score": 0.85,
    "metadata": {"chunk_index": 0}
}

# 개선 후
result = {
    "text": "...",
    "score": 0.85,
    "doctrine_id": "DOCTRINE-DEF-001",
    "statement_id": "D-DEF-001",
    "statement_text": "방어 작전 시...",
    "mett_c_elements": ["Mission", "Terrain"],
    "metadata": {
        "chunk_index": 0,
        "doctrine_id": "DOCTRINE-DEF-001",
        ...
    }
}
```

### 2.7 RAG 인덱스 재구축 스크립트 개선

**파일**: `scripts/rebuild_rag_index.py`

**개선 사항**:

1. **교리 문서 전용 청킹 사용**
   - `DOCTRINE-*.md` 파일은 `chunk_doctrine_documents()` 사용
   - 일반 문서는 기존 `chunk_documents()` 사용

2. **청크 통합**
   - 교리 문서 청크와 일반 문서 청크를 통합하여 인덱스 구축

**예시**:
```python
# 교리 문서와 일반 문서 분리
doctrine_docs = [doc for doc, name in zip(docs, doc_names) if name.startswith("DOCTRINE-")]
normal_docs = [doc for doc, name in zip(docs, doc_names) if not name.startswith("DOCTRINE-")]

# 각각 전용 청킹 함수 사용
doctrine_chunks = rag_manager.chunk_doctrine_documents(doctrine_docs, ...)
normal_chunks = rag_manager.chunk_documents(normal_docs, ...)
```

---

## 3. 사용 방법

### 3.1 RAG 인덱스 재구축

기존 교리 문서를 새로운 청킹 방식으로 재인덱싱:

```bash
python scripts/rebuild_rag_index.py
```

### 3.2 교리 문서 생성

새 교리 문서 생성 시 자동으로 전용 청킹 사용:

```python
from core_pipeline.doctrine_generator import DoctrineGenerator

generator = DoctrineGenerator(llm_manager, rag_manager)
doctrine_doc = generator.generate_doctrine_document(...)
generator.save_to_rag(doctrine_doc)  # 자동으로 전용 청킹 사용
```

### 3.3 교리 참조 검색

개선된 파싱 로직이 자동으로 적용됨:

```python
from core_pipeline.coa_engine.doctrine_reference_service import DoctrineReferenceService

service = DoctrineReferenceService(rag_manager)
doctrine_refs = service.find_doctrine_references(coa, mett_c_analysis, axis_states)
# 결과: 개선된 파싱 로직으로 정확한 교리 참조 반환
```

---

## 4. 개선 효과

### 4.1 교리 문장 본문 추출 정확도 향상

- **개선 전**: 헤더나 리스트 항목만 추출
- **개선 후**: 실제 교리 문장 본문만 추출

### 4.2 교리 ID 추출 정확도 향상

- **개선 전**: "UNKNOWN"으로 표시
- **개선 후**: 정확한 교리 ID 추출 (예: "DOCTRINE-DEF-001")

### 4.3 METT-C 요소 정확도 향상

- **개선 전**: 내용과 무관한 모든 요소 표시
- **개선 후**: 교리 문서 헤더에서 정확한 요소만 추출

### 4.4 관련도 점수 개선

- **개선 전**: 의미없는 결과 포함
- **개선 후**: 관련도 0.3 이상의 의미있는 결과만 포함

---

## 5. 주의 사항

### 5.1 기존 인덱스 재구축 필요

기존 RAG 인덱스는 일반 청킹 방식으로 구축되었으므로, 개선된 기능을 사용하려면 **반드시 인덱스를 재구축**해야 합니다:

```bash
python scripts/rebuild_rag_index.py
```

### 5.2 교리 문서 형식 준수

교리 문서는 다음 형식을 따라야 전용 청킹이 정상 작동합니다:

```markdown
# Doctrine_ID: DOCTRINE-XXX
## 교리명: ...
## 적용 작전유형: ...
## 관련 METT-C 요소: Mission, Terrain, Troops

### Doctrine_Statement_ID: D-XXX-001
- [교리 문장 본문]
- **작전적 해석**: ...
```

---

## 6. 체크리스트

### 구현 완료
- [x] 교리 문서 전용 청킹 함수 추가
- [x] 교리 참조 파싱 로직 개선
- [x] METT-C 요소 추출 개선
- [x] RAG 검색 쿼리 개선
- [x] 의미없는 결과 필터링
- [x] RAG Manager 메타데이터 처리 개선
- [x] RAG 인덱스 재구축 스크립트 개선

### 테스트 필요
- [ ] RAG 인덱스 재구축 후 교리 참조 정확도 확인
- [ ] 교리 문장 본문 추출 정확도 확인
- [ ] METT-C 요소 추출 정확도 확인
- [ ] 관련도 점수 개선 확인

---

**문서 버전**: 1.0  
**최종 수정일**: 2026-01-06


