# LLM 기반 "상황판단" 정보 UI 사용 현황 분석

## 현재 상황

### 백엔드에서 생성 및 전달

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`

1. **생성**: `_generate_situation_assessment()` 메서드 (1183줄)
   - LLM 기반으로 상황 판단 텍스트 생성
   - 온톨로지 정보와 상황 정보를 기반으로 전문적인 판단 작성
   - Fallback으로 템플릿 기반 생성도 지원

2. **전달**: `execute_reasoning()` 메서드 (664줄)
   ```python
   "reasoning": {
       "situation_assessment": s.get("adapted_assessment") or situation_assessment_text,
       "justification": recommendation_reason,
       "pros": s.get("adapted_strengths") or self._generate_expected_effects(s, situation_info),
       "unit_rationale": s.get("unit_rationale") or s.get("llm_reason"),
       "system_search_path": s.get("system_search_path")
   }
   ```

### 프론트엔드에서의 사용 현황

**타입 정의**: `frontend/src/types/schema.ts` (67줄)
```typescript
reasoning?: {
    justification?: string;
    situation_assessment?: string;  // ✅ 정의되어 있음
    pros?: string[];
    cons?: string[];
    unit_rationale?: string;
    system_search_path?: string;
};
```

**실제 사용**: ❌ **사용되지 않음**

현재 프론트엔드에서 `reasoning` 객체의 다른 필드들은 사용되지만, `situation_assessment`는 사용되지 않습니다:

1. **`justification`** (선정 사유): ✅ 사용됨
   - `COADetailModal.tsx` (287줄)
   - `COADetailPanel.tsx` (172줄)

2. **`unit_rationale`** (부대 운용 근거): ✅ 사용됨
   - `COADetailModal.tsx` (302줄)
   - `COAExecutionPlanPanel.tsx` (44줄)

3. **`system_search_path`** (시스템 탐색 과정): ✅ 사용됨
   - `COADetailModal.tsx` (317줄)

4. **`situation_assessment`** (상황판단): ❌ **사용되지 않음**
   - 프론트엔드 코드에서 참조 없음

## 문제점

1. **데이터 낭비**: LLM으로 생성한 상황판단 정보가 백엔드에서 전달되지만 프론트엔드에서 표시되지 않음
2. **정보 손실**: 사용자가 상황판단 정보를 확인할 수 없음
3. **일관성 부족**: 다른 `reasoning` 필드들은 표시되지만 `situation_assessment`만 누락

## 개선 방안

### 옵션 1: COADetailModal에 "상황판단" 섹션 추가 (권장)

**위치**: `COADetailModal.tsx`의 `justification` 섹션 다음**

**구현**:
```typescript
{/* 상황판단 */}
{coa.reasoning?.situation_assessment && (
    <section>
        <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">상황판단</h3>
        </div>
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
            <p className="text-sm text-gray-700 dark:text-gray-300">
                {coa.reasoning.situation_assessment}
            </p>
        </div>
    </section>
)}
```

**장점**:
- LLM 기반 생성 정보 활용
- 사용자가 상황판단 확인 가능
- 다른 reasoning 필드와 일관성 유지

### 옵션 2: ReasoningExplanationPanel에 탭 추가

**위치**: `ReasoningExplanationPanel.tsx`의 탭 목록에 "상황판단" 탭 추가

**장점**:
- 추론 근거 관련 정보를 한 곳에 모음
- 탭 구조로 정보 정리

**단점**:
- 탭이 많아질 수 있음

### 옵션 3: SituationSummaryPanel에 통합

**위치**: `SituationSummaryPanel.tsx`에 상황판단 정보 표시

**장점**:
- 상황 정보와 함께 표시되어 맥락 이해 용이

**단점**:
- COA별 상황판단이 다를 수 있어 적합하지 않을 수 있음

## 권장 사항

**옵션 1 (COADetailModal에 섹션 추가)**을 권장합니다:
1. `justification` (선정 사유) 다음에 배치하여 논리적 흐름 유지
2. LLM 기반 생성 정보를 명확히 표시
3. 다른 reasoning 필드들과 일관된 스타일 유지

## 참고

- 백엔드에서 `situation_assessment`는 각 COA별로 생성되므로, COA 상세 모달에 표시하는 것이 적절합니다.
- Streamlit 버전에서는 COP 우측 패널 "추론 근거" → "상황 판단"에 표시되었습니다.
