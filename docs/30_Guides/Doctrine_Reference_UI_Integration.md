# 교리 참조 UI 통합 가이드

## 문서 정보
- **작성일**: 2026-01-06
- **목적**: COA 추천 결과에서 교리 참조 정보가 UI에 표시되는 위치 및 방법 설명

---

## 1. 교리 참조 표시 위치

교리 참조 정보는 다음 UI 위치에서 표시됩니다:

### 1.1 Agent 실행 페이지 (`ui/views/agent_execution.py`)

#### 위치 1: COA 카드 내부 (인라인 표시)
- **위치**: 각 COA 추천 카드 내부
- **표시 방식**: 간단한 인라인 박스
- **내용**: 교리 참조 개수 및 교리 문장 ID 목록

```python
# 교리 참조가 있으면 카드 내부에 표시
if doctrine_refs:
    render_doctrine_references_inline(rec)
```

#### 위치 2: 상세 분석 탭
- **위치**: COA 카드의 "상세 분석 결과" Expander 내부
- **탭**: "📚 교리 참조" 탭 (교리 참조가 있을 때만 표시)
- **내용**: 
  - 교리 문장 상세 정보
  - 교리 기반 추천 근거 설명

```python
# 교리 참조가 있으면 탭 추가
if has_doctrine:
    tab1, tab2, tab3, tab4 = st.tabs(["평가 세부사항", "기대 효과", "📚 교리 참조", "Raw Data"])
```

### 1.2 대시보드 분석 탭 (`ui/components/dashboard_tab_analysis.py`)

#### 위치: 추천 근거 분석 섹션
- **위치**: 점수 Breakdown 다음
- **표시 방식**: 독립 섹션
- **내용**: 
  - 교리 참조 상세 정보
  - 교리 기반 추천 근거 설명

```python
# 교리 참조 표시 (상위 추천에만)
if first_rec.get('doctrine_references'):
    st.subheader("📚 교리 참조")
    render_doctrine_references(first_rec)
    render_doctrine_based_explanation(...)
```

### 1.3 추론 근거 설명 (`ui/components/reasoning_explanation.py`)

#### 위치: 추론 과정 상세 탭
- **위치**: "📚 교리 참조" 탭 (교리 참조가 있을 때만 표시)
- **표시 방식**: 독립 탭
- **내용**: 교리 참조 상세 정보 및 교리 기반 설명

```python
# 교리 참조 탭 추가
if has_doctrine:
    tabs.append("📚 교리 참조")
```

### 1.4 추천 근거 분석 (`ui/components/recommendation_visualization.py`)

#### 위치: 점수 Breakdown 섹션
- **위치**: METT-C 평가 다음
- **표시 방식**: 독립 섹션
- **내용**: 교리 참조 상세 정보

```python
# 교리 참조 표시
if doctrine_refs:
    st.divider()
    render_doctrine_references(recommendation)
```

---

## 2. 교리 참조 표시 컴포넌트

### 2.1 `doctrine_reference_display.py`

새로 생성된 UI 컴포넌트로, 다음 함수들을 제공합니다:

#### `render_doctrine_references(coa_recommendation)`
- **용도**: 교리 참조 상세 정보 표시
- **표시 내용**:
  - 교리 문장 ID 및 본문
  - 관련도 점수
  - 관련 METT-C 요소
  - 교리 ID

#### `render_doctrine_based_explanation(...)`
- **용도**: 교리 기반 COA 추천 근거 설명 생성 및 표시
- **표시 내용**:
  - 작전 상황 요약
  - METT-C 핵심 제약 요소
  - 적용된 교리 문장
  - 교리 → COA 연결 논리
  - 안전장치 문장

#### `render_doctrine_references_inline(coa_recommendation)`
- **용도**: COA 카드 내부에 간단히 표시
- **표시 내용**: 교리 참조 개수 및 교리 문장 ID 목록

---

## 3. UI 표시 예시

### 3.1 COA 카드 내부 (인라인)

```
┌─────────────────────────────────────┐
│ 1. 지형 차단선 중심 방어            │
│    [Defense] [작전 최적안]          │
│    ⚓ 공병대대, 통신대대             │
│                                     │
│    📚 교리 참조: 3개                │
│    D-DEF-001, D-DEF-002, D-DEF-003 │
└─────────────────────────────────────┘
```

### 3.2 상세 분석 탭

```
📊 지형 차단선 중심 방어 상세 분석 결과
├─ 평가 세부사항
├─ 기대 효과
├─ 📚 교리 참조  ← [NEW]
│   ├─ [D-DEF-001] (관련도: 0.92)
│   │   "적 주공축이 제한된 지형을 통해 예상될 경우..."
│   │   관련 METT-C: Terrain, Mission
│   │
│   └─ [D-DEF-002] (관련도: 0.85)
│       "아군 전력이 제한된 상황에서는..."
│
└─ Raw Data
```

### 3.3 교리 기반 설명

```
📖 교리 기반 추천 근거 설명

### COA-02 (지형 차단선 중심 방어) 추천 근거 설명

#### 1. 작전 상황 요약
현재 작전 상황을 분석한 결과, 제시된 COA가 적합한 것으로 판단됩니다.

#### 2. METT-C 핵심 제약 요소
- **Mission**: 방어선 유지
- **Terrain**: 협소한 접근로
- **Troops**: 기동부대 제한

#### 3. 적용된 교리 문장
[D-DEF-001] (관련도: 0.92)
"적 주공축이 제한된 지형을 통해 예상될 경우..."

#### 4. 교리 → COA 연결 논리
교리 문장 D-DEF-001에 따르면, 적 주공축이 제한된 지형을 통해 예상될 경우...
이에 따라 본 COA는 Terrain, Mission을 고려하여 설계되었습니다.

---

**안전장치 문장**:
본 설명은 교리 문장을 근거로 한 추천 논리를 제시하는 것이며,
최종 작전 결정은 지휘관 판단에 따른다.
```

---

## 4. 교리 참조 데이터 구조

COA 추천 결과에 포함되는 교리 참조 데이터:

```json
{
  "coa_id": "COA-02",
  "coa_name": "지형 차단선 중심 방어",
  "doctrine_references": [
    {
      "doctrine_id": "DOCTRINE-DEF-001",
      "statement_id": "D-DEF-001",
      "excerpt": "적 주공축이 제한된 지형을 통해 예상될 경우, 방어 COA는 지형 차단선을 중심으로 구성되는 것이 권장된다.",
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

## 5. UI 표시 조건

### 5.1 교리 참조 표시 조건

교리 참조는 다음 조건을 만족할 때만 표시됩니다:

1. **COA 추천 결과에 `doctrine_references` 필드가 있음**
2. **`doctrine_references` 리스트가 비어있지 않음**

```python
doctrine_refs = coa_recommendation.get('doctrine_references', [])
if doctrine_refs:
    # 교리 참조 표시
```

### 5.2 교리 참조가 없는 경우

교리 참조가 없으면:
- 교리 참조 관련 UI 섹션이 표시되지 않음
- 기존 UI는 정상적으로 작동
- 오류 없이 처리됨

---

## 6. 사용자 가이드

### 6.1 교리 참조 확인 방법

1. **Agent 실행 페이지**에서 COA 추천 실행
2. 추천된 COA 카드 확인
   - 교리 참조가 있으면 카드 내부에 "📚 교리 참조: N개" 표시
3. "📊 상세 분석 결과" Expander 클릭
4. "📚 교리 참조" 탭 선택
5. 교리 문장 상세 정보 및 교리 기반 설명 확인

### 6.2 대시보드에서 확인

1. **탭 2: 추천 근거 분석** 선택
2. "📚 교리 참조" 섹션 확인
3. 교리 문장 및 교리 기반 설명 확인

---

## 7. 구현된 파일

### 7.1 새로 생성된 파일
- `ui/components/doctrine_reference_display.py` - 교리 참조 표시 컴포넌트

### 7.2 수정된 파일
- `ui/views/agent_execution.py` - Agent 실행 페이지에 교리 참조 탭 추가
- `ui/components/dashboard_tab_analysis.py` - 분석 탭에 교리 참조 섹션 추가
- `ui/components/reasoning_explanation.py` - 추론 근거 설명에 교리 참조 탭 추가
- `ui/components/recommendation_visualization.py` - 추천 근거 분석에 교리 참조 추가

---

## 8. 체크리스트

### 구현 완료
- [x] 교리 참조 표시 컴포넌트 생성
- [x] Agent 실행 페이지에 교리 참조 탭 추가
- [x] 대시보드 분석 탭에 교리 참조 섹션 추가
- [x] 추론 근거 설명에 교리 참조 탭 추가
- [x] 추천 근거 분석에 교리 참조 추가
- [x] COA 카드 내부 인라인 표시 추가

### 테스트 필요
- [ ] UI에서 교리 참조가 정상적으로 표시되는지 확인
- [ ] 교리 참조가 없는 경우 UI가 정상 작동하는지 확인
- [ ] 교리 기반 설명이 올바르게 생성되는지 확인

---

## 9. 참고 사항

### 9.1 교리 참조 표시 우선순위

1. **상위 3개 COA에만 교리 참조 추가** (Agent 로직)
2. **교리 참조가 있는 COA만 UI에 표시**
3. **교리 참조가 없으면 관련 UI 섹션 숨김**

### 9.2 성능 고려사항

- 교리 참조 검색은 COA 추천 후 상위 3개에만 수행
- UI 렌더링은 교리 참조가 있을 때만 추가 처리
- 교리 기반 설명 생성은 사용자가 탭을 클릭할 때만 수행 (선택적)

---

**문서 버전**: 1.0  
**최종 수정일**: 2026-01-06


