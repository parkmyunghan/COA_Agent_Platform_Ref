# RAG 문서 활용 현황 분석

## 문서 정보
- **작성일**: 2026-01-06
- **목적**: RAG 문서 중 교리 문서와 일반 문서의 활용 현황 분석

---

## 1. 현재 상태

### 1.1 RAG 문서 종류

#### 교리 문서 (DOCTRINE-*.md)
- `DOCTRINE-DEF-001.md`: 방어 작전 교리
- `DOCTRINE-DEF-002.md`: 방어작전 교리
- `DOCTRINE-OFF-001.md`: 공격 작전 교리
- `DOCTRINE-CA-001.md`: 반격 작전 교리

**특징**:
- 구조화된 형식 (Doctrine_ID, Statement_ID 등)
- 교리 문장 단위로 청킹 가능
- 메타데이터 포함 (doctrine_id, statement_id, mett_c_elements)

#### 일반 문서 (*.txt)
- `방책_연계_원칙.txt`: 방책 연계 원칙 및 기준
- `ROE_및_제약조건.txt`: 작전 규칙 및 제약조건
- `작전_방책선정_지침.txt`: 방책 선정 지침
- `적_대응전술_분석_가이드.txt`: 적 대응 전술 분석 가이드
- `지휘관_의도_해석_가이드.txt`: 지휘관 의도 해석 가이드
- `COA_적용조건_해석_가이드.txt`: COA 적용조건 해석 가이드
- `환경_조건_해석_가이드.txt`: 환경 조건 해석 가이드
- `통신_보급_체크리스트.txt`: 통신 및 보급 체크리스트

**특징**:
- 비구조화된 텍스트 형식
- 일반 청킹 방식 사용
- 메타데이터 없음

---

## 2. 현재 활용 현황

### 2.1 검색 과정

1. **DoctrineSearchService.search_doctrine_references()**
   - `rag_manager.retrieve_with_context()` 호출
   - **모든 RAG 문서**를 검색 (교리 문서 + 일반 문서)
   - 관련도 점수로 정렬

2. **DoctrineReferenceService._parse_doctrine_statement()**
   - 검색 결과를 교리 문서 형식으로 파싱 시도
   - 교리 문서: 정상 파싱 ✅
   - 일반 문서: 파싱 실패 또는 부정확한 결과 ❌

### 2.2 문제점

#### 문제 1: 일반 문서 파싱 실패
```python
# 일반 문서 검색 결과 예시
{
    "text": "1. 선행 방책 (Preceding COA)\n   - 주 방책 실행 전에 선행하여 실행되는 방책",
    "score": 0.75
}

# 파싱 시도 결과
{
    "doctrine_id": "UNKNOWN",  # ❌ 교리 ID 추출 실패
    "statement_id": "STMT-0",   # ❌ 문장 ID 없음
    "excerpt": "1. 선행 방책...",  # ❌ 리스트 항목만 추출
    "mett_c_elements": ["Mission"]  # ❌ 부정확한 METT-C 요소
}
```

#### 문제 2: 일반 문서 필터링
- `_parse_doctrine_statement()`에서 교리 ID가 없으면 제외될 수 있음
- 관련도가 높은 일반 문서도 제외될 수 있음

#### 문제 3: 일반 문서의 가치 미활용
- 일반 문서는 COA 추천에 유용한 정보를 포함하지만
- 교리 문서 형식으로만 파싱하려고 하여 제대로 활용되지 않음

---

## 3. 개선 방안

### 3.1 일반 문서도 근거로 활용

**방안 1: 일반 문서 파싱 로직 추가**

일반 문서도 COA 추천 근거로 활용할 수 있도록 파싱 로직 개선:

```python
def _parse_reference(self, rag_result: Dict) -> Optional[Dict]:
    """RAG 결과 파싱 (교리 문서 + 일반 문서 지원)"""
    # 교리 문서인 경우
    if rag_result.get('doctrine_id') or self._is_doctrine_format(rag_result):
        return self._parse_doctrine_statement(rag_result)
    
    # 일반 문서인 경우
    else:
        return self._parse_general_document(rag_result)

def _parse_general_document(self, rag_result: Dict) -> Optional[Dict]:
    """일반 문서 파싱"""
    text = rag_result.get('text', '')
    score = rag_result.get('score', 0.0)
    metadata = rag_result.get('metadata', {})
    
    # 문서 소스 추출
    source = metadata.get('source', '') or rag_result.get('source', '')
    
    # 의미있는 문장 추출
    excerpt = self._extract_meaningful_sentence(text)
    
    # METT-C 요소 추출 (키워드 기반)
    mett_c_elements = self._extract_mett_c_elements(text)
    
    return {
        "doctrine_id": None,  # 일반 문서는 교리 ID 없음
        "statement_id": None,  # 일반 문서는 문장 ID 없음
        "document_type": "general",  # 일반 문서 표시
        "source": source,  # 문서 소스 (예: "방책_연계_원칙.txt")
        "excerpt": excerpt,
        "relevance_score": float(score),
        "mett_c_elements": mett_c_elements
    }
```

**방안 2: 참조 타입 구분**

교리 참조와 일반 문서 참조를 구분하여 표시:

```python
{
    "reference_type": "doctrine",  # 또는 "general"
    "doctrine_id": "DOCTRINE-DEF-001",  # 교리 문서인 경우
    "statement_id": "D-DEF-001",  # 교리 문서인 경우
    "source": "방책_연계_원칙.txt",  # 일반 문서인 경우
    "excerpt": "...",
    "relevance_score": 0.85
}
```

### 3.2 UI 표시 개선

일반 문서 참조도 UI에 표시:

```markdown
📚 적용된 참고 자료

### 교리 문서
- [D-DEF-001] (관련도: 0.92)
  "적 주공축이 제한된 지형을 통해..."

### 일반 문서
- 방책_연계_원칙.txt (관련도: 0.75)
  "선행 방책은 주 방책 실행 전에 선행하여 실행되는 방책"
```

---

## 4. 권장 사항

### 4.1 단기 개선 (즉시 적용 가능)

1. **일반 문서 파싱 로직 추가**
   - `DoctrineReferenceService`에 일반 문서 파싱 함수 추가
   - 교리 문서와 일반 문서를 구분하여 파싱

2. **필터링 로직 개선**
   - 교리 ID가 없어도 일반 문서는 포함
   - 관련도 점수만으로 필터링

3. **UI 표시 개선**
   - 교리 문서와 일반 문서를 구분하여 표시
   - 일반 문서는 소스 파일명 표시

### 4.2 중기 개선 (향후 계획)

1. **일반 문서 메타데이터 추가**
   - 일반 문서도 청킹 시 메타데이터 포함
   - 문서 타입, 섹션 정보 등

2. **일반 문서 구조화**
   - 일반 문서도 일정 형식으로 구조화
   - 예: "## 섹션명", "### 항목명" 등

3. **참조 타입별 가중치**
   - 교리 문서와 일반 문서의 가중치 구분
   - 교리 문서는 더 높은 가중치

---

## 5. 체크리스트

### 현재 상태
- [x] 교리 문서는 정상적으로 파싱됨
- [x] 일반 문서도 검색됨
- [ ] 일반 문서는 제대로 파싱되지 않음
- [ ] 일반 문서 참조가 UI에 표시되지 않음

### 개선 필요
- [ ] 일반 문서 파싱 로직 추가
- [ ] 참조 타입 구분 (교리/일반)
- [ ] UI에 일반 문서 참조 표시
- [ ] 일반 문서 메타데이터 추가

---

**문서 버전**: 1.0  
**최종 수정일**: 2026-01-06


