# 작전분석결과 영역의 LLM 활용 방식 분석

## 개요

작전분석결과 영역에서 생성되는 텍스트 콘텐츠들이 LLM을 어떤 방식으로 활용하는지 상세 분석한 문서입니다.

---

## 1. 위협상황 "정황보고" (Situation Summary)

### 위치
- **UI**: 작전분석결과 영역 상단 배너
- **코드**: `logic_defense_enhanced.py::_generate_overall_situation_summary()`

### LLM 활용 방식

#### ✅ **LLM 우선 사용 (Primary)**
```python
# Line 1108-1163
if self.core.llm_manager and self.core.llm_manager.is_available():
    try:
        # 위협 중심 모드 프롬프트
        prompt = f"""다음의 온톨로지 팩트를 기반으로 지휘관에게 보고하는 자연스러운 군사 상황 요약 문장을 한 문장으로 생성하세요.
        
## 온톨로지 팩트:
- 발생시각: {situation_info.get('탐지시각', '최근')}
- 발생위치: {loc_full} (ID: {loc_id})
- 위협원: {enemy_ko}
- 위협유형: {t_type_ko}
- 관련축선: {axis_full}
- 위협수준: {t_level_ko}

## 요구사항:
- 전문적인 군사 보고 톤앤매너 사용
- 핵심 명사는 굵게(**) 표시
- 지명과 축선명 뒤에 ID를 괄호로 병기
- 한 문장으로 생성
"""
        summary = self.core.llm_manager.generate(prompt, max_tokens=256).strip()
```

**특징:**
- **입력**: 온톨로지 팩트 기반 구조화된 데이터
- **출력**: 자연스러운 군사 보고 문장 (한 문장)
- **톤앤매너**: 전문적인 군사 보고 스타일
- **포맷팅**: Markdown 굵게 표시, ID 병기

#### ⚠️ **Fallback: 템플릿 기반 (Template-based)**
LLM이 실패하거나 사용 불가능한 경우:
```python
# Line 1165-1204
# 템플릿 기반 자동 생성
summary = f"{loc_disp} 일대에서 {enemy_part}{type_part}"
if axis_id and axis_id != "N/A":
    summary += f"{ax_disp} 방향의 위협 수준은 **{t_level_ko}** 상태로 분석됩니다."
```

---

## 2. 전술상황도(COP) 내 추론근거 박스

### 2.1 "상황판단" (Situation Assessment)

#### 위치
- **UI**: COP 우측 패널 "추론 근거" → "상황 판단"
- **코드**: `logic_defense_enhanced.py::_generate_situation_assessment()`

#### LLM 활용 방식

**✅ LLM 우선 사용 (Primary) - 하이브리드 접근법**

```python
# Line 1129-1169 (개선됨)
def _generate_situation_assessment(self, situation_info: Dict) -> str:
    # 1. LLM 기반 생성 시도 (우선순위 1)
    if self.core.llm_manager and self.core.llm_manager.is_available():
        try:
            # 정확한 정보 수집
            threat_pct = int(threat_level * 100)
            axis_id = situation_info.get('관련축선ID', 'N/A')
            axis_name = situation_info.get('관련축선명', 'N/A')
            description = situation_info.get('상황설명', '')
            
            prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 위협 상황에 대한 전문적인 판단을 작성하세요.

## 위협 정보
- 위협 유형: {threat_type}
- 위협 수준: {threat_pct}%
- 발생장소: {location}
- 관련축선: {axis_name} ({axis_id})

## 작성 요구사항
1. **정확성**: 위의 수치(위협 수준 {threat_pct}%)를 정확히 반영하세요.
2. **전문성**: 군사 작전 보고 스타일로 작성하세요.
3. **자연스러움**: 템플릿처럼 보이지 않도록 자연스러운 문장으로 작성하세요.
4. **길이**: 2-3문장으로 간결하게 작성 (최대 150자)
"""
            response = self.core.llm_manager.generate(prompt, temperature=0.2, max_tokens=200)
            # 검증 후 반환
            if self._validate_llm_assessment(response, situation_info):
                return response
        except Exception as e:
            safe_print(f"[WARN] LLM 상황판단 생성 실패: {e}, fallback 사용")
    
    # 2. Fallback: 기존 템플릿 방식
    # ... (기존 템플릿 코드 유지)
```

**특징:**
- **입력**: `situation_info` 딕셔너리 (위협 수준, 위치, 유형 등)
- **출력**: 자연스러운 한국어 상황 판단 (2-3문장)
- **방식**: **LLM 우선 사용** → 정확한 정보를 프롬프트에 포함하여 자연스러운 문장 생성
- **Fallback**: LLM 실패 시 기존 템플릿 방식 사용
- **정확성 보장**: 프롬프트에 정확한 수치를 명시하여 LLM이 임의로 변경하지 않도록 지시

---

### 2.2 "선정사유" (Justification)

#### 위치
- **UI**: COP 우측 패널 "추론 근거" → "선정 사유"
- **코드**: `logic_defense_enhanced.py::_generate_recommendation_reason()`

#### LLM 활용 방식

**✅ LLM 우선 사용 (Primary) - 정확한 정보 기반 자연어 생성**

```python
# Line 887-1028 (개선됨)
def _generate_recommendation_reason(self, strategy: Dict, situation_info: Dict) -> str:
    # 1. LLM을 활용한 자연스러운 선정사유 생성 (우선순위 1)
    if self.core.llm_manager and self.core.llm_manager.is_available():
        # 구조화된 데이터 수집
        trace = strategy.get('reasoning_trace', [])
        score_breakdown = strategy.get('score_breakdown', {})
        reasoning = score_breakdown.get('reasoning', [])
        
        # LLM 프롬프트 구성 (정확한 정보 포함)
        prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 방책 선정 사유를 자연스럽고 전문적인 한국어로 작성하세요.

## 현재 상황
- 위협 유형: {threat_type}
- 위협 수준: {threat_pct}%
- 발생 위치: {location}

## 추천 방책 정보
- 방책명: {coa_name}
- 방책 ID: {coa_id}
- 종합 점수: {coa_score:.3f}

## 온톨로지 탐색 경로 (전술적 연관성)
{trace_summary}

## 평가 요소별 점수
{breakdown_summary}

## 주요 선정 요인 (상위 3개)
{top_reasons}

## 작성 요구사항
1. **정확성**: 위의 수치와 정보를 정확히 반영하세요.
2. **자연스러움**: 템플릿처럼 보이지 않도록 자연스러운 문장으로 작성하세요.
3. **구조**: 3-5문장으로 간결하게 작성
"""
        response = self.core.llm_manager.generate(prompt, temperature=0.3, max_tokens=300)
    
    # 2. Fallback: 기존 템플릿 방식 (LLM 실패 시)
    # ... 온톨로지 기반 규칙 변환
```

**특징:**
- **입력**: 
  - `reasoning_trace`: 온톨로지 탐색 경로
  - `score_breakdown`: 점수 평가 근거 (정확한 수치 포함)
  - `strategy`: 방책 정보
  - `situation_info`: 상황 정보
- **출력**: 자연스러운 한국어 선정 사유 (3-5문장)
- **방식**: **LLM 우선 사용** → 정확한 정보를 프롬프트에 포함하여 자연스러운 문장 생성
- **Fallback**: LLM 실패 시 기존 템플릿 방식 사용
- **정확성 보장**: 프롬프트에 정확한 수치와 정보를 명시하여 LLM이 임의로 변경하지 않도록 지시

---

### 2.3 "기대효과" (Expected Effects)

#### 위치
- **UI**: COP 우측 패널 "추론 근거" → "기대 효과"
- **코드**: `logic_defense_enhanced.py::_generate_expected_effects()`

#### LLM 활용 방식

**✅ LLM 우선 사용 (Conditional)**

```python
# Line 1206-1251
def _generate_expected_effects(self, strategy: Dict, situation_info: Dict) -> List[str]:
    # 1. LLM 구체화 데이터가 있으면 우선 사용 (가장 고품질)
    if strategy.get("adapted_strengths"):
        return strategy["adapted_strengths"]
    
    # 2. Scorer에서 생성한 strengths 사용
    strengths = strategy.get("strengths") or strategy.get("score_breakdown", {}).get("strengths")
    # ... 검증 및 필터링
    
    # 3. Fallback: 방책 명칭 기반 규칙 생성
    coa_name = strategy.get("coa_name") or ...
    if any(kw in coa_name for kw in ["선제", "공격", "타격"]):
        effects = [f"적 '{coa_name}' 위협 능력 근원적 무력화", ...]
    # ... 기타 키워드 기반 생성
```

**특징:**
- **우선순위 1**: `adapted_strengths` (LLM 생성 데이터) - **LLM 사용**
- **우선순위 2**: Scorer의 `strengths` (규칙 기반)
- **우선순위 3**: 방책 명칭 키워드 기반 템플릿

**`adapted_strengths` 생성 위치:**
- `_adapt_coas_with_llm()` 함수에서 생성될 수 있으나, 현재 코드에서는 `unit_rationale`만 생성
- 실제로는 Scorer나 다른 모듈에서 생성될 가능성 있음

---

## 3. 추천방책목록 영역 내 "방책선정사유"

#### 위치
- **UI**: 추천방책목록 각 방책 카드 내부
- **코드**: `logic_defense_enhanced.py::_generate_recommendation_reason()`

#### LLM 활용 방식

**✅ LLM 우선 사용 - "선정사유"와 동일한 함수 사용**

"선정사유"와 동일한 함수 사용:
```python
# Line 887-1028
"justification": self._generate_recommendation_reason(s, situation_info)
```

**특징:**
- **입력**: 온톨로지 `reasoning_trace`, 점수 `breakdown`, 방책 정보
- **출력**: 자연스러운 한국어 선정 사유 (LLM 생성)
- **방식**: **LLM 우선 사용** → 정확한 정보 기반 자연어 생성
- **개선 사항**: 템플릿 기반의 반복적인 수치 나열 문제 해결

---

## 4. 추가 LLM 활용 영역

### 4.1 부대 운용 근거 (Unit Rationale)

#### 위치
- 방책별 상세 정보 내부
- **코드**: `logic_defense_enhanced.py::_adapt_coas_with_llm()`

#### LLM 활용 방식

**✅ LLM 직접 사용**

```python
# Line 742-812
def _adapt_coas_with_llm(self, recommendations: List[Dict], ...):
    def adapt_coa(coa_item):
        prompt = (
            f"당신은 작전 참모이자 시스템 설계자입니다. "
            f"다음 방책(COA)에 할당된 부대(Resource)의 선정 근거와 시스템적 탐색 과정을 지휘관에게 설명하세요.\n\n"
            f"[상황 정보]\n{situation_str}\n\n"
            f"[선택된 방책]\n명칭: {coa_name}\n\n"
            f"[할당된 아군 부대/자산]\n{participating_units}\n\n"
            f"다음 두 가지 항목을 군사적 전문성과 시스템적 투명성을 담아 한글로 작성하세요:\n"
            f"1. 부대 운용 근거 (Unit Rationale): ...\n"
            f"2. 시스템 탐색 과정 (Search Path): ...\n\n"
            f"응답 형식:\n[운용근거]\n...\n[탐색과정]\n..."
        )
        
        response = self.core.llm_manager.generate(prompt, temperature=0.1, max_tokens=512)
        # 파싱하여 unit_rationale, system_search_path 추출
```

**특징:**
- **입력**: 상황 정보, 방책 정보, 할당된 부대 목록
- **출력**: 구조화된 텍스트 (`[운용근거]`, `[탐색과정]` 섹션)
- **용도**: 부대 할당 근거 설명 (Process Transparency)

---

## 5. 종합 비교표

| 항목 | 위치 | LLM 사용 | 우선순위 | Fallback |
|------|------|----------|----------|----------|
| **정황보고** | 작전분석결과 상단 | ✅ **사용** | 1순위 | 템플릿 기반 |
| **상황판단** | COP 추론근거 | ✅ **사용** | 1순위 | 템플릿 기반 |
| **선정사유** | COP 추론근거 | ✅ **사용** | 1순위 | 온톨로지 기반 |
| **기대효과** | COP 추론근거 | ✅ **조건부** | 1순위 (adapted_strengths) | 템플릿 기반 |
| **방책선정사유** | 방책 목록 카드 | ✅ **사용** | 1순위 | 온톨로지 기반 |
| **부대운용근거** | 방책 상세 정보 | ✅ **사용** | 1순위 | 템플릿 기반 |

---

## 6. LLM 활용 패턴 분석

### 6.1 LLM을 사용하는 경우

1. **자연스러운 문장 생성이 중요한 경우**
   - 정황보고: 지휘관 보고용 자연스러운 문장
   - 부대운용근거: 전문적 설명이 필요한 경우

2. **구조화된 데이터 → 자연어 변환이 복잡한 경우**
   - 온톨로지 팩트를 자연스러운 문장으로 변환

### 6.2 LLM을 사용하지 않는 경우 (Fallback)

1. **LLM 실패 또는 사용 불가능한 경우**
   - 네트워크 오류, API 장애 등
   - 오프라인 환경
   - LLM 서비스 비활성화

2. **일관성과 예측 가능성이 중요한 경우 (선택적)**
   - 특정 상황에서 템플릿이 더 적합할 수 있음
   - 하지만 현재는 LLM 우선 사용으로 통일

3. **비용 최적화가 필요한 경우**
   - 캐싱 전략으로 동일 입력에 대한 중복 호출 방지
   - Fallback으로 불필요한 비용 방지

---

## 7. 개선 제안

### 7.1 현재 문제점

1. **기대효과의 `adapted_strengths` 생성 경로 불명확**
   - 현재 코드에서 `adapted_strengths`가 어디서 생성되는지 명확하지 않음
   - 대부분 템플릿 기반 fallback 사용 가능성

2. ~~**선정사유의 다양성 부족**~~ ✅ **해결됨**
   - ~~온톨로지 기반 규칙 변환만으로는 문장 다양성이 제한적~~
   - ✅ **LLM을 활용하여 자연스러운 문장 생성으로 개선 완료**

### 7.2 개선 방안

1. ~~**선정사유에 LLM 활용 추가 (선택적)**~~ ✅ **완료**
   - ✅ **LLM 우선 사용으로 변경**
   - ✅ **정확한 정보(온톨로지 trace, 점수 breakdown 등)를 프롬프트에 포함**
   - ✅ **템플릿 기반의 반복적인 수치 나열 문제 해결**

2. **기대효과의 LLM 생성 보장**
   - `_adapt_coas_with_llm()`에서 `adapted_strengths`도 함께 생성
   - 또는 별도 함수로 분리하여 명시적 생성

3. ~~**상황판단의 LLM 활용 (선택적)**~~ ✅ **완료**
   - ✅ **하이브리드 접근법 구현 완료 (LLM 우선 + 템플릿 Fallback)**
   - ✅ **정확한 정보 기반 자연스러운 문장 생성**
   - ✅ **템플릿의 반복적인 패턴 문제 해결**

---

## 8. 참고 코드 위치

- `agents/defense_coa_agent/logic_defense_enhanced.py`:
  - `_generate_overall_situation_summary()`: Line 1072-1204
  - `_generate_situation_assessment()`: Line 1030-1070
  - `_generate_recommendation_reason()`: Line 887-1028
  - `_generate_expected_effects()`: Line 1206-1251
  - `_adapt_coas_with_llm()`: Line 742-812

- `ui/components/tactical_map.py`:
  - 추론근거 박스 렌더링: Line 508-536

- `ui/views/agent_execution.py`:
  - 정황보고 표시: Line 734-920
