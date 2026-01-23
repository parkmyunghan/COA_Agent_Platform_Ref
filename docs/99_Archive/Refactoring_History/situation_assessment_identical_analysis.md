# "상황판단" 정보 방책별 동일성 분석

## 분석 결과

### ✅ **방책별로 동일한 내용**

**이유**:
1. **한 번만 생성**: `situation_assessment_text`는 한 번만 생성되어 모든 방책에 재사용됩니다.
   - 코드 위치: `agents/defense_coa_agent/logic_defense_enhanced.py` (615-623줄)
   - 주석: "상황판단은 한 번만 생성 (모든 방책에 대해 동일하므로 중복 호출 방지)"

2. **할당 로직**: 각 방책에 할당할 때 (664줄)
   ```python
   "situation_assessment": s.get("adapted_assessment") or situation_assessment_text,
   ```
   - `adapted_assessment`가 있으면 그것을 사용
   - 없으면 공통 `situation_assessment_text` 사용

3. **`adapted_assessment` 미생성**: 
   - `_adapt_coas_with_llm()` 메서드는 `unit_rationale`와 `system_search_path`만 생성
   - `adapted_assessment`는 생성하지 않음
   - 따라서 항상 `situation_assessment_text` 사용

## 코드 흐름

```
1. execute_reasoning() 시작
   ↓
2. 여러 방책 추천 (recommendations 리스트 생성)
   ↓
3. 상황판단 한 번만 생성 (615-623줄)
   situation_assessment_text = _generate_situation_assessment(situation_info)
   ↓
4. 각 방책별로 선정사유 생성 (631-678줄)
   for idx, s in enumerate(recommendations):
       recommendation_reason = _generate_recommendation_reason(s, situation_info)  # 방책별로 다름
       ...
       "reasoning": {
           "situation_assessment": s.get("adapted_assessment") or situation_assessment_text,  # 항상 동일
           "justification": recommendation_reason,  # 방책별로 다름
           ...
       }
```

## 의미

**상황판단 (`situation_assessment`)**:
- **목적**: 현재 전술 상황에 대한 전체적인 판단
- **범위**: 특정 방책이 아닌 전체 상황에 대한 평가
- **내용**: 위협 유형, 수준, 발생 위치, 관련 축선 등 상황 정보 기반
- **결과**: 모든 방책에 동일 (상황 자체에 대한 판단이므로)

**선정 사유 (`justification`)**:
- **목적**: 특정 방책이 왜 추천되었는지 설명
- **범위**: 각 방책별로 다름
- **내용**: 해당 방책의 특성, 장점, 적합성 등
- **결과**: 방책별로 다름

## UI 표시 권장 사항

### 옵션 1: COA 상세 모달에 표시 (권장)
- **위치**: `justification` (선정 사유) **이전**에 배치
- **이유**: 
  - 상황판단 → 선정 사유 순서가 논리적 흐름
  - 상황판단은 전체 상황에 대한 것이므로 선정 사유보다 먼저 이해해야 함

### 옵션 2: 지도 상단 정황보고에 통합
- **위치**: `SituationSummaryPanel` 또는 지도 내 정황보고 박스
- **이유**: 
  - 상황판단은 특정 방책이 아닌 전체 상황에 대한 것이므로
  - 모든 방책에 동일하므로 공통 영역에 표시하는 것이 적절

### 옵션 3: 두 곳 모두 표시
- **위치**: 
  1. 지도 상단 정황보고 (공통 정보)
  2. COA 상세 모달 (상황판단 섹션)
- **이유**: 
  - 사용자가 어디서든 확인 가능
  - 맥락에 따라 다른 위치에서 확인 가능

## 권장 사항

**옵션 3 (두 곳 모두 표시)**을 권장합니다:
1. 지도 상단 정황보고에 표시: 전체 상황 파악
2. COA 상세 모달에도 표시: 방책 선택 시 상황 재확인

이렇게 하면:
- 사용자가 상황판단을 쉽게 확인 가능
- 방책별로 동일하므로 중복 표시해도 혼란 없음
- 맥락에 따라 적절한 위치에서 확인 가능
