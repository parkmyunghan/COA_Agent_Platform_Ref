# RAG 기반 교리-COA 연계 설계 문서

## 문서 정보
- **작성일**: 2026-01-06
- **참조 문서**: `docs/99_MD/20260106_02.md`
- **목적**: RAG 기반 교리 문서 생성 및 COA 추천 시 교리 인용 구조 설계

---

## 1. 전체 설계 개요

### 1.1 핵심 원칙
문서 `20260106_02.md`에서 제시한 3가지 요소는 **분리 불가**:
1. **교리/교범 가상 생성** → RAG 문서화 + 메타데이터 부여
2. **COA 추천 시 RAG 인용** → 교리 문장 단위 인용
3. **"왜 이 COA인가?" 설명 생성** → 교리 문장 기반 근거 설명

**중요**: ①의 출력 품질이 ②·③의 품질을 결정합니다.

### 1.2 현재 시스템 상태 분석

#### ✅ 이미 구현된 기능
- `core_pipeline/rag_manager.py`: RAG 검색 기능 (FAISS 기반)
- `core_pipeline/coa_engine/llm_services.py::DoctrineSearchService`: 교범 검색 서비스
- `knowledge/rag_docs/`: 8개 RAG 문서 보유
- COA 추천 시스템: `agents/defense_coa_agent/`
- METT-C 평가 시스템: `core_pipeline/mett_c_evaluator.py`

#### ⚠️ 개선이 필요한 부분
1. **교리 문서 자동 생성 파이프라인 없음**
   - 현재는 수동으로 문서 작성
   - 가상 교리 생성 프롬프트 및 파이프라인 필요

2. **COA 추천 결과에 교리 인용 정보 미포함**
   - `DoctrineSearchService`는 있으나 COA 추천 결과에 통합되지 않음
   - 교리 문장 ID 및 인용 구조 없음

3. **COA 추천 근거 설명 구조 미표준화**
   - `COAExplanationGenerator`는 있으나 교리 기반 설명 구조 없음
   - METT-C → 교리 → COA 연결 논리 명확하지 않음

---

## 2. 설계 1: RAG용 교리 문서 자동 생성 프롬프트 세트

### 2.1 설계 목표
- 실제 교범을 요약하거나 모방하지 않고, **교리 '형식'과 '논리 구조'만 재현**
- RAG 검색·인용을 전제로 **문장 단위로 쪼개기**
- METT-C / COA 판단에 직접 쓰일 수 있는 문장만 생성

### 2.2 구현 위치
```
core_pipeline/
  └── doctrine_generator.py  (신규 생성)
      ├── DoctrineGenerator 클래스
      ├── 교리 생성 프롬프트 템플릿
      └── 교리 문서 메타데이터 관리
```

### 2.3 교리 문서 구조 표준 (MD 형식)

```markdown
# Doctrine_ID: DOCTRINE-XXX
## 교리명: [교리명]
## 적용 작전유형: [방어작전/공격작전/기동작전 등]
## 관련 METT-C 요소: [Mission, Terrain, Troops 등]

### Doctrine_Statement_ID: D-DEF-001
- 적 주공축이 제한된 지형을 통해 예상될 경우,
  방어 COA는 지형 차단선을 중심으로 구성되는 것이 권장된다.
- **작전적 해석**: 협소한 접근로에서는 지형을 활용한 방어선 설정이 효과적
- **COA 판단 시 활용 포인트**: 
  - 지형 제약이 큰 축선 → 차단선 중심 방어
  - 우회 기동 제한 → 예비전력 후방 배치
```

### 2.4 교리 생성 프롬프트 템플릿

```python
DOCTRINE_GENERATION_PROMPT = """
너는 군사 교리 집필 보조 AI이다.

목표:
- 실제 교범을 인용하거나 요약하지 말고,
- "군 교리 문장 형식"을 따르는 가상 교리 문서를 생성하라.
- 생성된 문서는 RAG 시스템에 저장되어
  COA 추천 시 근거 문장으로 사용된다.

생성 규칙:
1. 각 교리 문장은 단문·명시적 판단 기준 형태로 작성
2. 하나의 문장은 하나의 작전 판단 논리만 포함
3. METT-C 요소 중 최소 1개 이상을 명시적으로 언급
4. "권장된다 / 고려한다 / 제한된다" 와 같은 규범적 표현 사용
5. 역사적 사례, 실제 교범 명칭, 실존 문서 언급 금지

출력 형식:
- MD 형식
- 각 교리 문장은 고유 ID 부여 (예: D-DEF-001)
- 교리명, 적용 작전유형, 관련 METT-C 요소 명시

생성 대상:
- 작전유형: {operation_type}
- METT-C 중점: {mett_c_focus}
- COA 활용 목적: {coa_purpose}

이제 교리 문서를 생성하라.
"""
```

### 2.5 DoctrineGenerator 클래스 설계

```python
class DoctrineGenerator:
    """교리 문서 자동 생성기"""
    
    def __init__(self, llm_manager, rag_manager):
        self.llm_manager = llm_manager
        self.rag_manager = rag_manager
        self.doctrine_id_counter = {}  # 작전유형별 카운터
    
    def generate_doctrine_document(
        self,
        operation_type: str,
        mett_c_focus: List[str],
        coa_purpose: List[str],
        num_statements: int = 5
    ) -> Dict:
        """
        교리 문서 생성
        
        Returns:
            {
                "doctrine_id": "DOCTRINE-DEF-001",
                "content": "마크다운 형식 교리 문서",
                "statements": [
                    {
                        "statement_id": "D-DEF-001",
                        "text": "교리 문장",
                        "mett_c_elements": ["Terrain", "Mission"],
                        "operation_type": "defense"
                    }
                ]
            }
        """
        pass
    
    def save_to_rag(self, doctrine_doc: Dict) -> bool:
        """생성된 교리 문서를 RAG 인덱스에 추가"""
        pass
```

---

## 3. 설계 2: COA 추천 시 RAG 문서 인용 / 근거 표시 포맷

### 3.1 설계 목표
- "AI 판단"이 아니라 **"교리 근거 기반 판단"**으로 보이게
- RAG는 **판단 주체가 아닌 근거 제공자**
- METT-C → COA → 교리 문장 연결이 명확해야 함

### 3.2 COA 추천 결과 표준 포맷 (JSON)

```json
{
  "coa_id": "COA-02",
  "coa_name": "지형 차단선 중심 방어",
  "recommendation_level": "HIGH",
  "score": 0.85,
  "mett_c_alignment": {
    "mission": "방어선 유지",
    "terrain": "협소한 접근로",
    "troops": "기동부대 제한"
  },
  "doctrine_references": [
    {
      "doctrine_id": "DOCTRINE-DEF",
      "statement_id": "D-DEF-001",
      "excerpt": "적 주공축이 제한된 지형을 통해 예상될 경우, 방어 COA는 지형 차단선을 중심으로 구성되는 것이 권장된다.",
      "relevance_score": 0.92,
      "mett_c_elements": ["Terrain", "Mission"]
    }
  ],
  "reasoning": {
    "situation_assessment": "...",
    "selection_reason": "...",
    "expected_effect": "..."
  }
}
```

### 3.3 구현 위치

#### 3.3.1 DoctrineReferenceService (신규)
```
core_pipeline/
  └── coa_engine/
      └── doctrine_reference_service.py  (신규)
          ├── DoctrineReferenceService 클래스
          ├── COA 추천 시 교리 검색
          └── 교리 인용 정보 생성
```

#### 3.3.2 COA 추천 Agent 수정
```
agents/
  └── defense_coa_agent/
      └── logic_defense_enhanced.py
          └── execute_reasoning() 메서드 수정
              └── 교리 인용 정보 추가
```

### 3.4 DoctrineReferenceService 클래스 설계

```python
class DoctrineReferenceService:
    """COA 추천 시 교리 인용 서비스"""
    
    def __init__(self, rag_manager, doctrine_search_service):
        self.rag_manager = rag_manager
        self.doctrine_search_service = doctrine_search_service
    
    def find_doctrine_references(
        self,
        coa: COA,
        mett_c_analysis: Dict,
        axis_states: List[AxisState],
        top_k: int = 3
    ) -> List[Dict]:
        """
        COA에 대한 교리 참조 검색
        
        Args:
            coa: COA 객체
            mett_c_analysis: METT-C 분석 결과
            axis_states: 축선별 전장상태
            top_k: 반환할 교리 문장 수
        
        Returns:
            [
                {
                    "doctrine_id": "DOCTRINE-DEF",
                    "statement_id": "D-DEF-001",
                    "excerpt": "...",
                    "relevance_score": 0.92,
                    "mett_c_elements": ["Terrain", "Mission"]
                }
            ]
        """
        # 1. METT-C 분석 결과 기반 쿼리 생성
        query = self._build_doctrine_query(coa, mett_c_analysis, axis_states)
        
        # 2. RAG 검색
        rag_results = self.doctrine_search_service.search_doctrine_references(
            query, top_k=top_k, coa_context=coa
        )
        
        # 3. 교리 문장 파싱 및 메타데이터 추출
        doctrine_refs = []
        for result in rag_results:
            parsed = self._parse_doctrine_statement(result)
            if parsed:
                doctrine_refs.append(parsed)
        
        return doctrine_refs
    
    def _build_doctrine_query(
        self,
        coa: COA,
        mett_c_analysis: Dict,
        axis_states: List[AxisState]
    ) -> str:
        """교리 검색 쿼리 생성"""
        # METT-C 요소 추출
        mission = mett_c_analysis.get('mission', {}).get('summary', '')
        terrain = mett_c_analysis.get('terrain', {}).get('summary', '')
        troops = mett_c_analysis.get('troops', {}).get('summary', '')
        
        query_parts = []
        if mission:
            query_parts.append(f"임무: {mission}")
        if terrain:
            query_parts.append(f"지형: {terrain}")
        if troops:
            query_parts.append(f"부대: {troops}")
        
        query = f"{coa.coa_name or coa.coa_id} {', '.join(query_parts)}"
        return query
    
    def _parse_doctrine_statement(self, rag_result: Dict) -> Optional[Dict]:
        """RAG 결과에서 교리 문장 파싱"""
        text = rag_result.get('text', '')
        # 교리 문장 ID 추출 (예: D-DEF-001)
        # 메타데이터에서 추출 또는 텍스트 파싱
        pass
```

### 3.5 COA 추천 Agent 통합

```python
# agents/defense_coa_agent/logic_defense_enhanced.py

class EnhancedDefenseCOAAgent(BaseAgent):
    def __init__(self, core, **kwargs):
        super().__init__(core, **kwargs)
        # NEW: 교리 인용 서비스 추가
        from core_pipeline.coa_engine.doctrine_reference_service import DoctrineReferenceService
        self.doctrine_ref_service = DoctrineReferenceService(
            rag_manager=core.rag_manager,
            doctrine_search_service=core.doctrine_search_service
        )
    
    def execute_reasoning(self, situation_id: Optional[str] = None, **kwargs) -> Dict:
        # ... 기존 로직 ...
        
        # COA 추천 결과 생성
        recommendations = []
        for coa_score in scored_coas:
            # NEW: 교리 인용 정보 추가
            doctrine_refs = self.doctrine_ref_service.find_doctrine_references(
                coa=coa_score['coa'],
                mett_c_analysis=situation_analysis.get('mett_c', {}),
                axis_states=axis_states,
                top_k=3
            )
            
            recommendation = {
                "coa_id": coa_score['coa_id'],
                "coa_name": coa_score['coa_name'],
                "score": coa_score['score'],
                "mett_c_alignment": situation_analysis.get('mett_c', {}),
                "doctrine_references": doctrine_refs,  # NEW
                # ... 기존 필드 ...
            }
            recommendations.append(recommendation)
        
        return {
            "recommendations": recommendations,
            # ... 기존 필드 ...
        }
```

---

## 4. 설계 3: "이 COA는 어떤 교리 문장을 근거로 추천되었는가?" 설명 구조

### 4.1 설계 목표
- 교리 문장 기반 근거 설명 생성
- METT-C → 교리 → COA 연결 논리 명확화
- 보고서·UI 공용 형식

### 4.2 설명 구조 표준

```markdown
### COA-02 추천 근거 설명

#### 1. 작전 상황 요약
[현재 작전 상황 간단 요약]

#### 2. METT-C 핵심 제약 요소
- **Mission**: 방어선 유지
- **Terrain**: 협소한 접근로, 우회 기동 제한
- **Troops**: 기동부대 제한

#### 3. 적용된 교리 문장
[D-DEF-001]
"적 주공축이 제한된 지형을 통해 예상될 경우,
방어 COA는 지형 차단선을 중심으로 구성되는 것이 권장된다."

#### 4. 교리 → COA 연결 논리
본 COA는 해당 교리에 따라 차단선 중심 방어선을 설정하고,
예비 전력은 후방에 배치하는 구조로 구성되었다.

#### 5. 교리 미적용 영역 (있을 경우)
[교리로 설명되지 않는 부분은 "추론"으로 표기]

---

**안전장치 문장**:
본 설명은 교리 문장을 근거로 한 추천 논리를 제시하는 것이며,
최종 작전 결정은 지휘관 판단에 따른다.
```

### 4.3 구현 위치

#### 4.3.1 DoctrineBasedExplanationGenerator (신규)
```
core_pipeline/
  └── coa_engine/
      └── doctrine_explanation_generator.py  (신규)
          ├── DoctrineBasedExplanationGenerator 클래스
          └── 교리 기반 COA 근거 설명 생성
```

### 4.4 DoctrineBasedExplanationGenerator 클래스 설계

```python
class DoctrineBasedExplanationGenerator:
    """교리 기반 COA 근거 설명 생성기"""
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
    
    def generate_explanation(
        self,
        coa_recommendation: Dict,
        situation_info: Dict,
        mett_c_analysis: Dict,
        axis_states: List[AxisState]
    ) -> str:
        """
        교리 기반 COA 추천 근거 설명 생성
        
        Args:
            coa_recommendation: COA 추천 결과 (doctrine_references 포함)
            situation_info: 상황 정보
            mett_c_analysis: METT-C 분석 결과
            axis_states: 축선별 전장상태
        
        Returns:
            마크다운 형식 설명문
        """
        doctrine_refs = coa_recommendation.get('doctrine_references', [])
        
        if not doctrine_refs:
            # 교리 참조가 없으면 기존 방식으로 폴백
            return self._generate_fallback_explanation(coa_recommendation, situation_info)
        
        # 교리 기반 설명 생성
        explanation = self._build_doctrine_based_explanation(
            coa_recommendation,
            situation_info,
            mett_c_analysis,
            axis_states,
            doctrine_refs
        )
        
        return explanation
    
    def _build_doctrine_based_explanation(
        self,
        coa_recommendation: Dict,
        situation_info: Dict,
        mett_c_analysis: Dict,
        axis_states: List[AxisState],
        doctrine_refs: List[Dict]
    ) -> str:
        """교리 기반 설명 구성"""
        coa_id = coa_recommendation.get('coa_id', 'Unknown')
        coa_name = coa_recommendation.get('coa_name', 'Unknown')
        
        # 1. 작전 상황 요약
        situation_summary = self._summarize_situation(situation_info, axis_states)
        
        # 2. METT-C 핵심 제약 요소
        mett_c_summary = self._summarize_mett_c(mett_c_analysis)
        
        # 3. 적용된 교리 문장
        doctrine_section = self._format_doctrine_references(doctrine_refs)
        
        # 4. 교리 → COA 연결 논리
        connection_logic = self._explain_doctrine_coa_connection(
            coa_recommendation, doctrine_refs, mett_c_analysis
        )
        
        # 5. 교리 미적용 영역
        non_doctrine_areas = self._identify_non_doctrine_areas(
            coa_recommendation, doctrine_refs
        )
        
        # 최종 설명 조합
        explanation = f"""### {coa_id} ({coa_name}) 추천 근거 설명

#### 1. 작전 상황 요약
{situation_summary}

#### 2. METT-C 핵심 제약 요소
{mett_c_summary}

#### 3. 적용된 교리 문장
{doctrine_section}

#### 4. 교리 → COA 연결 논리
{connection_logic}
"""
        
        if non_doctrine_areas:
            explanation += f"""
#### 5. 교리 미적용 영역 (추론)
{non_doctrine_areas}
"""
        
        explanation += """
---

**안전장치 문장**:
본 설명은 교리 문장을 근거로 한 추천 논리를 제시하는 것이며,
최종 작전 결정은 지휘관 판단에 따른다.
"""
        
        return explanation
    
    def _format_doctrine_references(self, doctrine_refs: List[Dict]) -> str:
        """교리 참조 포맷팅"""
        sections = []
        for ref in doctrine_refs:
            statement_id = ref.get('statement_id', 'Unknown')
            excerpt = ref.get('excerpt', '')
            sections.append(f"[{statement_id}]\n\"{excerpt}\"")
        return "\n\n".join(sections)
```

### 4.5 COAExplanationGenerator 통합

```python
# core_pipeline/coa_engine/llm_services.py

class COAExplanationGenerator:
    def __init__(self, llm_manager, doctrine_explanation_generator=None):
        self.llm_manager = llm_manager
        # NEW: 교리 기반 설명 생성기 추가
        self.doctrine_explanation_generator = doctrine_explanation_generator
    
    def generate_explanation(
        self,
        coa_result: 'COAEvaluationResult',
        axis_states: List,
        language: str = "ko",
        coa_recommendation: Optional[Dict] = None  # NEW: 교리 참조 포함 추천 결과
    ) -> str:
        """COA 설명 생성"""
        # NEW: 교리 참조가 있으면 교리 기반 설명 사용
        if (self.doctrine_explanation_generator and 
            coa_recommendation and 
            coa_recommendation.get('doctrine_references')):
            
            return self.doctrine_explanation_generator.generate_explanation(
                coa_recommendation=coa_recommendation,
                situation_info={},  # 상황 정보 전달 필요
                mett_c_analysis={},  # METT-C 분석 결과 전달 필요
                axis_states=axis_states
            )
        
        # 기존 방식 (LLM 또는 템플릿 기반)
        return self._generate_with_llm(coa_result, axis_states, language)
```

---

## 5. 구현 우선순위 및 단계

### 5.1 Phase 1: 교리 문서 생성 파이프라인 (우선순위: 높음)
**기간**: 1주
**작업**:
1. `core_pipeline/doctrine_generator.py` 생성
2. 교리 생성 프롬프트 템플릿 구현
3. 교리 문서 메타데이터 구조 정의
4. RAG 인덱스 자동 추가 기능

**결과물**:
- 교리 문서 자동 생성 기능
- 최소 10개 교리 문장 생성 (테스트용)

### 5.2 Phase 2: COA 추천 시 교리 인용 (우선순위: 높음)
**기간**: 1주
**작업**:
1. `core_pipeline/coa_engine/doctrine_reference_service.py` 생성
2. `DoctrineReferenceService` 클래스 구현
3. `EnhancedDefenseCOAAgent`에 통합
4. COA 추천 결과 포맷 확장

**결과물**:
- COA 추천 결과에 `doctrine_references` 필드 추가
- 교리 문장 ID 및 인용 정보 포함

### 5.3 Phase 3: 교리 기반 근거 설명 (우선순위: 중간)
**기간**: 1주
**작업**:
1. `core_pipeline/coa_engine/doctrine_explanation_generator.py` 생성
2. `DoctrineBasedExplanationGenerator` 클래스 구현
3. `COAExplanationGenerator`에 통합
4. UI에서 설명 표시 확인

**결과물**:
- 교리 기반 COA 추천 근거 설명 생성
- 표준화된 설명 포맷

### 5.4 Phase 4: 통합 테스트 및 개선 (우선순위: 중간)
**기간**: 1주
**작업**:
1. 전체 파이프라인 통합 테스트
2. 교리 문장 품질 검증
3. RAG 검색 정확도 개선
4. UI/UX 개선

**결과물**:
- 통합 테스트 결과
- 개선 사항 문서화

---

## 6. 데이터 구조 및 메타데이터

### 6.1 교리 문서 메타데이터 구조

```python
{
    "doctrine_id": "DOCTRINE-DEF-001",
    "doctrine_name": "지형 제약 기반 방어 교리",
    "operation_type": "defense",
    "mett_c_elements": ["Terrain", "Mission", "Troops"],
    "created_at": "2026-01-06T10:00:00Z",
    "statements": [
        {
            "statement_id": "D-DEF-001",
            "text": "적 주공축이 제한된 지형을 통해 예상될 경우...",
            "mett_c_elements": ["Terrain", "Mission"],
            "coa_purpose": ["기동 제한", "방어선 설정"]
        }
    ]
}
```

### 6.2 RAG 청크 메타데이터 확장

```python
{
    "text": "적 주공축이 제한된 지형을 통해 예상될 경우...",
    "doctrine_id": "DOCTRINE-DEF-001",
    "statement_id": "D-DEF-001",
    "operation_type": "defense",
    "mett_c_elements": ["Terrain", "Mission"],
    "source": "doctrine_generated",
    "chunk_index": 0,
    "doc_index": 0
}
```

---

## 7. 프롬프트 개선 가이드

### 7.1 COA 추천 프롬프트 (수정 필요)

```text
COA를 추천할 때는 반드시 다음을 수행하라.

1. METT-C 분석 결과를 먼저 제시
2. COA 추천 판단은 교리 문장에 의해 뒷받침되어야 한다
3. 모든 추천 COA에는 최소 1개 이상의 교리 문장 ID를 포함하라
4. 교리 문장이 없는 판단은 '추론'으로 분리 표기하라
5. 교리 문장을 임의로 생성하거나 수정하지 말고 RAG 결과만 인용하라
```

**적용 위치**:
- `core_pipeline/coa_engine/llm_services.py::COARecommendationService`
- `agents/defense_coa_agent/logic_defense_enhanced.py`

---

## 8. 테스트 시나리오

### 8.1 교리 문서 생성 테스트
```python
def test_doctrine_generation():
    generator = DoctrineGenerator(llm_manager, rag_manager)
    doc = generator.generate_doctrine_document(
        operation_type="defense",
        mett_c_focus=["Terrain", "Mission"],
        coa_purpose=["기동 제한", "방어선 설정"],
        num_statements=5
    )
    assert doc["doctrine_id"].startswith("DOCTRINE-")
    assert len(doc["statements"]) == 5
    assert all("statement_id" in stmt for stmt in doc["statements"])
```

### 8.2 교리 인용 테스트
```python
def test_doctrine_reference():
    service = DoctrineReferenceService(rag_manager, doctrine_search_service)
    refs = service.find_doctrine_references(
        coa=test_coa,
        mett_c_analysis=test_mett_c,
        axis_states=test_axis_states,
        top_k=3
    )
    assert len(refs) > 0
    assert all("statement_id" in ref for ref in refs)
    assert all("excerpt" in ref for ref in refs)
```

### 8.3 근거 설명 생성 테스트
```python
def test_doctrine_explanation():
    generator = DoctrineBasedExplanationGenerator(llm_manager)
    explanation = generator.generate_explanation(
        coa_recommendation=test_recommendation,
        situation_info=test_situation,
        mett_c_analysis=test_mett_c,
        axis_states=test_axis_states
    )
    assert "교리 문장" in explanation
    assert "METT-C" in explanation
    assert "안전장치 문장" in explanation
```

---

## 9. 향후 개선 방향

### 9.1 교리 문장 품질 개선
- 교리 문장 생성 프롬프트 반복 개선
- 생성된 교리 문장 검증 파이프라인
- 사용자 피드백 기반 교리 문장 업데이트

### 9.2 RAG 검색 정확도 개선
- 교리 문장별 임베딩 최적화
- 메타데이터 기반 필터링 강화
- 하이브리드 검색 가중치 조정

### 9.3 설명 생성 개선
- 교리 문장과 COA 연결 논리 자동화
- 다중 교리 문장 조합 설명
- 시각화 지원 (교리 → COA 연결 그래프)

---

## 10. 체크리스트

### 10.1 Phase 1 체크리스트
- [ ] `doctrine_generator.py` 생성
- [ ] 교리 생성 프롬프트 템플릿 구현
- [ ] 교리 문서 메타데이터 구조 정의
- [ ] RAG 인덱스 자동 추가 기능
- [ ] 테스트용 교리 문서 10개 생성

### 10.2 Phase 2 체크리스트
- [ ] `doctrine_reference_service.py` 생성
- [ ] `DoctrineReferenceService` 클래스 구현
- [ ] `EnhancedDefenseCOAAgent` 통합
- [ ] COA 추천 결과 포맷 확장
- [ ] 교리 인용 정보 UI 표시

### 10.3 Phase 3 체크리스트
- [ ] `doctrine_explanation_generator.py` 생성
- [ ] `DoctrineBasedExplanationGenerator` 클래스 구현
- [ ] `COAExplanationGenerator` 통합
- [ ] 설명 포맷 표준화
- [ ] UI에서 설명 표시 확인

### 10.4 Phase 4 체크리스트
- [ ] 전체 파이프라인 통합 테스트
- [ ] 교리 문장 품질 검증
- [ ] RAG 검색 정확도 측정
- [ ] 성능 최적화
- [ ] 문서화 완료

---

## 11. 참고 사항

### 11.1 기존 시스템과의 호환성
- 기존 COA 추천 시스템과 호환되도록 설계
- 교리 참조가 없어도 기존 방식으로 동작
- 점진적 마이그레이션 가능

### 11.2 보안 및 안전장치
- 교리 문장은 "가상 교리"임을 명시
- 모든 설명에 안전장치 문장 포함
- 최종 결정은 지휘관 판단에 따름을 강조

### 11.3 확장성
- 교리 문서 라이브러리 확장 용이
- 다양한 작전유형 지원 가능
- 메타데이터 기반 필터링 및 검색 확장 가능

---

**문서 버전**: 1.0  
**최종 수정일**: 2026-01-06


