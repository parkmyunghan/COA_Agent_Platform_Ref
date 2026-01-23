# "상황판단" LLM vs 템플릿 기반 비교 분석

## 개요

"상황판단" (Situation Assessment) 기능에 LLM을 도입하는 방안과 기존 템플릿 기반 방법을 비교 분석한 문서입니다.

---

## 1. 현재 구현 (템플릿 기반)

### 1.1 코드 구조

```python
def _generate_situation_assessment(self, situation_info: Dict) -> str:
    approach_mode = situation_info.get("approach_mode", "threat_centered")
    location = situation_info.get('발생장소') or situation_info.get('location') or '작전 구역'
    threat_type = situation_info.get('위협유형') or situation_info.get('threat_type') or '미상'
    threat_level = self._extract_threat_level(situation_info)
    
    if approach_mode == "mission_centered":
        m_name = situation_info.get('임무명') or situation_info.get('mission_name') or '기본 임무'
        success_prob = 1.0 - threat_level
        
        assessment = f"'{location}' 일대에서 하달된 '{m_name}' 임무에 대한 분석 결과입니다. "
        assessment += f"현재 임무 성공 가능성은 {int(success_prob * 100)}%로 평가되며, "
        
        if success_prob >= 0.7:
            assessment += "임무 완수를 위한 제반 여건이 매우 양호한 것으로 판단됩니다."
        elif success_prob >= 0.4:
            assessment += "효과적인 자원 분배와 치밀한 계획 수립이 필요한 상황입니다."
        else:
            assessment += "임무 수행을 위한 추가 자원 확보 및 작전 계획 재검토가 필요할 수 있습니다."
    else:
        assessment = f"'{location}' 일대에서 감지된 '{threat_type}' 위협에 대한 분석 결과입니다. "
        assessment += f"현재 위협 지수는 {int(threat_level * 100)}%로 평가되며, "
        
        if threat_level >= 0.8:
            assessment += "즉각적이고 단호한 대응이 필요한 심각한 위협 상황으로 판단됩니다."
        elif threat_level >= 0.5:
            assessment += "지속적인 정찰과 유연한 대응 태세 유지가 필요한 상황입니다."
        else:
            assessment += "정상 수준의 감시 체계를 유지하며 상황 변화를 예의주시해야 합니다."
    
    return assessment
```

### 1.2 템플릿 기반의 장점

| 항목 | 설명 |
|------|------|
| **일관성** | 동일한 입력에 대해 항상 동일한 출력 보장 |
| **예측 가능성** | 출력 형식이 명확하고 예측 가능 |
| **성능** | LLM 호출 없이 즉시 생성 (0ms 지연) |
| **비용** | LLM API 비용 없음 |
| **안정성** | LLM 서비스 장애와 무관하게 작동 |
| **디버깅 용이** | 규칙 기반이라 문제 추적이 쉬움 |
| **오프라인 작동** | 인터넷 연결 불필요 |

### 1.3 템플릿 기반의 단점

| 항목 | 설명 |
|------|------|
| **다양성 부족** | 항상 같은 패턴의 문장 반복 |
| **맥락 이해 부족** | 복잡한 상황의 뉘앙스를 반영하지 못함 |
| **확장성 제한** | 새로운 상황 유형 추가 시 코드 수정 필요 |
| **자연스러움 부족** | 기계적인 문장 느낌 |
| **상세 분석 부족** | 단순 조건부 분기로는 깊이 있는 분석 어려움 |

---

## 2. LLM 기반 구현 방안

### 2.1 제안 코드 구조

```python
def _generate_situation_assessment(self, situation_info: Dict) -> str:
    """
    상황 판단 텍스트 생성 (LLM 우선, 템플릿 Fallback)
    """
    approach_mode = situation_info.get("approach_mode", "threat_centered")
    location = situation_info.get('발생장소') or situation_info.get('location') or '작전 구역'
    threat_type = situation_info.get('위협유형') or situation_info.get('threat_type') or '미상'
    threat_level = self._extract_threat_level(situation_info)
    threat_pct = int(threat_level * 100)
    
    # 1. LLM 기반 생성 시도
    if self.core.llm_manager and self.core.llm_manager.is_available():
        try:
            # 추가 컨텍스트 수집
            axis_id = situation_info.get('관련축선ID') or situation_info.get('axis_id', 'N/A')
            axis_name = situation_info.get('관련축선명') or situation_info.get('axis_name', 'N/A')
            enemy = situation_info.get('적부대') or situation_info.get('enemy_units', 'N/A')
            detection_time = situation_info.get('탐지시각', '최근')
            description = situation_info.get('상황설명') or situation_info.get('description', '')
            
            if approach_mode == "mission_centered":
                m_id = situation_info.get('mission_id') or situation_info.get('임무ID', 'N/A')
                m_name = situation_info.get('임무명') or situation_info.get('mission_name', 'N/A')
                m_type = situation_info.get('임무종류') or situation_info.get('mission_type', 'N/A')
                m_objective = situation_info.get('임무목표') or situation_info.get('mission_objective', 'N/A')
                success_prob = 1.0 - threat_level
                success_pct = int(success_prob * 100)
                
                prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 임무 상황에 대한 전문적인 판단을 작성하세요.

## 임무 정보
- 임무명: {m_name} (ID: {m_id})
- 임무유형: {m_type}
- 임무목표: {m_objective}
- 하달시각: {detection_time}

## 작전 환경
- 작전구역: {location}
- 주요축선: {axis_name} ({axis_id})
- 성공 가능성: {success_pct}%

## 상세 상황
{description if description else "상세 상황 설명 없음"}

## 작성 요구사항
1. **정확성**: 위의 수치(성공 가능성 {success_pct}%)를 정확히 반영하세요.
2. **전문성**: 군사 작전 보고 스타일로 작성하세요.
3. **구조**: 
   - 첫 문장: 임무 개요 및 작전구역
   - 중간 문장: 성공 가능성 평가 및 주요 고려사항
   - 마지막 문장: 권장 조치사항
4. **길이**: 2-3문장으로 간결하게 작성 (최대 150자)
5. **톤**: 객관적이고 전문적인 판단 톤

상황 판단:"""
            else:
                prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 위협 상황에 대한 전문적인 판단을 작성하세요.

## 위협 정보
- 위협 유형: {threat_type}
- 위협 수준: {threat_pct}%
- 위협원: {enemy}
- 발생시각: {detection_time}

## 발생 위치
- 발생장소: {location}
- 관련축선: {axis_name} ({axis_id})

## 상세 상황
{description if description else "상세 상황 설명 없음"}

## 작성 요구사항
1. **정확성**: 위의 수치(위협 수준 {threat_pct}%)를 정확히 반영하세요.
2. **전문성**: 군사 작전 보고 스타일로 작성하세요.
3. **구조**: 
   - 첫 문장: 위협 개요 및 발생 위치
   - 중간 문장: 위협 수준 평가 및 심각도 판단
   - 마지막 문장: 권장 대응 조치
4. **길이**: 2-3문장으로 간결하게 작성 (최대 150자)
5. **톤**: 객관적이고 전문적인 판단 톤

상황 판단:"""
            
            response = self.core.llm_manager.generate(prompt, temperature=0.2, max_tokens=200)
            if response:
                assessment_text = response.strip()
                # 기본 검증: 너무 짧거나 의미없는 경우 fallback
                if len(assessment_text) > 30 and not assessment_text.startswith("죄송"):
                    safe_print(f"[INFO] LLM 기반 상황판단 생성 성공: {assessment_text[:50]}...")
                    return assessment_text
                else:
                    safe_print(f"[WARN] LLM 응답이 부적절하여 fallback 사용: {assessment_text[:30]}")
        except Exception as e:
            safe_print(f"[WARN] LLM 상황판단 생성 실패: {e}, fallback 사용")
    
    # 2. Fallback: 기존 템플릿 방식
    # ... (기존 템플릿 코드 유지)
```

### 2.2 LLM 기반의 장점

| 항목 | 설명 |
|------|------|
| **자연스러움** | 상황에 맞게 다양한 표현으로 생성 |
| **맥락 이해** | 복잡한 상황의 뉘앙스를 반영 |
| **확장성** | 새로운 상황 유형에 자동 적응 |
| **상세 분석** | 여러 요소를 종합하여 깊이 있는 판단 가능 |
| **사용자 경험** | 더 읽기 쉽고 이해하기 쉬운 문장 |

### 2.3 LLM 기반의 단점

| 항목 | 설명 |
|------|------|
| **일관성 부족** | 동일 입력이라도 약간씩 다른 출력 가능 |
| **성능** | LLM 호출로 인한 지연 (0.5-2초) |
| **비용** | LLM API 호출 비용 발생 |
| **안정성** | LLM 서비스 장애 시 작동 불가 |
| **디버깅 어려움** | 출력이 예측 불가능하여 문제 추적 어려움 |
| **오프라인 불가** | 인터넷 연결 필요 |
| **정확성 검증 필요** | 수치나 사실이 정확히 반영되는지 검증 필요 |

---

## 3. 상세 비교 분석

### 3.1 기능적 측면

| 측면 | 템플릿 기반 | LLM 기반 | 승자 |
|------|------------|----------|------|
| **정확성** | ✅ 항상 정확 (규칙 기반) | ⚠️ 프롬프트에 따라 달라짐 | 템플릿 |
| **자연스러움** | ❌ 기계적 | ✅ 자연스러움 | LLM |
| **다양성** | ❌ 제한적 | ✅ 높음 | LLM |
| **맥락 이해** | ❌ 단순 조건부 | ✅ 복잡한 맥락 반영 | LLM |
| **확장성** | ❌ 코드 수정 필요 | ✅ 자동 적응 | LLM |

### 3.2 기술적 측면

| 측면 | 템플릿 기반 | LLM 기반 | 승자 |
|------|------------|----------|------|
| **성능** | ✅ 즉시 (0ms) | ⚠️ 0.5-2초 지연 | 템플릿 |
| **비용** | ✅ 무료 | ⚠️ API 비용 | 템플릿 |
| **안정성** | ✅ 높음 | ⚠️ 서비스 의존 | 템플릿 |
| **오프라인** | ✅ 가능 | ❌ 불가능 | 템플릿 |
| **디버깅** | ✅ 쉬움 | ⚠️ 어려움 | 템플릿 |

### 3.3 사용자 경험 측면

| 측면 | 템플릿 기반 | LLM 기반 | 승자 |
|------|------------|----------|------|
| **가독성** | ⚠️ 보통 | ✅ 높음 | LLM |
| **신뢰성** | ✅ 높음 (일관성) | ⚠️ 변동 가능 | 템플릿 |
| **전문성** | ⚠️ 보통 | ✅ 높음 | LLM |
| **만족도** | ⚠️ 보통 | ✅ 높음 | LLM |

---

## 4. 하이브리드 접근법 (권장)

### 4.1 제안: LLM 우선 + 템플릿 Fallback

**장점:**
- ✅ LLM의 자연스러움과 다양성 활용
- ✅ LLM 실패 시 템플릿으로 안정성 보장
- ✅ 사용자 경험과 안정성의 균형

**구현 전략:**
1. **LLM 우선 시도**: 자연스러운 문장 생성
2. **검증 단계**: 생성된 문장의 품질 및 정확성 검증
3. **Fallback**: 검증 실패 또는 LLM 불가 시 템플릿 사용

### 4.2 검증 로직 예시

```python
def _validate_llm_assessment(self, assessment: str, situation_info: Dict) -> bool:
    """LLM 생성 문장의 품질 검증"""
    # 1. 최소 길이 검증
    if len(assessment) < 30:
        return False
    
    # 2. 핵심 정보 포함 여부 확인
    threat_level = self._extract_threat_level(situation_info)
    threat_pct = int(threat_level * 100)
    
    # 위협 수준이 언급되었는지 확인 (선택적)
    # 너무 엄격하면 안됨 - LLM이 다양한 표현 사용 가능
    
    # 3. 의미없는 응답 필터링
    invalid_responses = ["죄송", "알 수 없", "생성할 수 없", "오류"]
    if any(invalid in assessment for invalid in invalid_responses):
        return False
    
    return True
```

### 4.3 완전한 구현 예시

```python
def _generate_situation_assessment(self, situation_info: Dict) -> str:
    """
    상황 판단 텍스트 생성 (하이브리드: LLM 우선 + 템플릿 Fallback)
    """
    approach_mode = situation_info.get("approach_mode", "threat_centered")
    location = situation_info.get('발생장소') or situation_info.get('location') or situation_info.get('상황위치') or '작전 구역'
    threat_type = situation_info.get('위협유형') or situation_info.get('threat_type') or situation_info.get('상황명') or '미상'
    threat_level = self._extract_threat_level(situation_info)
    threat_pct = int(threat_level * 100)
    
    # 데이터 부족 검증
    if not situation_info or (location == '작전 구역' and threat_type == '미상' and threat_level == 0.7):
        if not situation_info:
            return "분석 가능한 상황 데이터가 부족합니다. 추가 작전 정보를 수정하여 상세 분석을 수행해야 합니다." if approach_mode == "mission_centered" else "분석 가능한 상황 데이터가 부족합니다. 정찰 자산을 투입하여 상세 정보를 수집해야 합니다."
    
    # 1. LLM 기반 생성 시도 (우선순위 1)
    if self.core.llm_manager and self.core.llm_manager.is_available():
        try:
            # 추가 컨텍스트 수집
            axis_id = situation_info.get('관련축선ID') or situation_info.get('axis_id', 'N/A')
            axis_name = situation_info.get('관련축선명') or situation_info.get('axis_name', 'N/A')
            enemy = situation_info.get('적부대') or situation_info.get('enemy_units', 'N/A')
            detection_time = situation_info.get('탐지시각', '최근')
            description = situation_info.get('상황설명') or situation_info.get('description', '')
            
            if approach_mode == "mission_centered":
                m_id = situation_info.get('mission_id') or situation_info.get('임무ID', 'N/A')
                m_name = situation_info.get('임무명') or situation_info.get('mission_name', 'N/A')
                m_type = situation_info.get('임무종류') or situation_info.get('mission_type', 'N/A')
                m_objective = situation_info.get('임무목표') or situation_info.get('mission_objective', 'N/A')
                success_prob = 1.0 - threat_level
                success_pct = int(success_prob * 100)
                
                prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 임무 상황에 대한 전문적인 판단을 작성하세요.

## 임무 정보
- 임무명: {m_name} (ID: {m_id})
- 임무유형: {m_type}
- 임무목표: {m_objective}
- 하달시각: {detection_time}

## 작전 환경
- 작전구역: {location}
- 주요축선: {axis_name} ({axis_id})
- 성공 가능성: {success_pct}%

## 상세 상황
{description if description else "상세 상황 설명 없음"}

## 작성 요구사항
1. **정확성**: 위의 수치(성공 가능성 {success_pct}%)를 정확히 반영하세요.
2. **전문성**: 군사 작전 보고 스타일로 작성하세요.
3. **구조**: 
   - 첫 문장: 임무 개요 및 작전구역
   - 중간 문장: 성공 가능성 평가 및 주요 고려사항
   - 마지막 문장: 권장 조치사항
4. **길이**: 2-3문장으로 간결하게 작성 (최대 150자)
5. **톤**: 객관적이고 전문적인 판단 톤

상황 판단:"""
            else:
                prompt = f"""당신은 작전 참모입니다. 다음 정보를 바탕으로 위협 상황에 대한 전문적인 판단을 작성하세요.

## 위협 정보
- 위협 유형: {threat_type}
- 위협 수준: {threat_pct}%
- 위협원: {enemy}
- 발생시각: {detection_time}

## 발생 위치
- 발생장소: {location}
- 관련축선: {axis_name} ({axis_id})

## 상세 상황
{description if description else "상세 상황 설명 없음"}

## 작성 요구사항
1. **정확성**: 위의 수치(위협 수준 {threat_pct}%)를 정확히 반영하세요.
2. **전문성**: 군사 작전 보고 스타일로 작성하세요.
3. **구조**: 
   - 첫 문장: 위협 개요 및 발생 위치
   - 중간 문장: 위협 수준 평가 및 심각도 판단
   - 마지막 문장: 권장 대응 조치
4. **길이**: 2-3문장으로 간결하게 작성 (최대 150자)
5. **톤**: 객관적이고 전문적인 판단 톤

상황 판단:"""
            
            response = self.core.llm_manager.generate(prompt, temperature=0.2, max_tokens=200)
            if response:
                assessment_text = response.strip()
                # 검증: 품질 확인
                if self._validate_llm_assessment(assessment_text, situation_info):
                    safe_print(f"[INFO] LLM 기반 상황판단 생성 성공: {assessment_text[:50]}...")
                    return assessment_text
                else:
                    safe_print(f"[WARN] LLM 응답이 부적절하여 fallback 사용: {assessment_text[:30]}")
        except Exception as e:
            safe_print(f"[WARN] LLM 상황판단 생성 실패: {e}, fallback 사용")
    
    # 2. Fallback: 기존 템플릿 방식
    if approach_mode == "mission_centered":
        m_name = situation_info.get('임무명') or situation_info.get('mission_name') or '기본 임무'
        success_prob = 1.0 - threat_level
        
        assessment = f"'{location}' 일대에서 하달된 '{m_name}' 임무에 대한 분석 결과입니다. "
        assessment += f"현재 임무 성공 가능성은 {int(success_prob * 100)}%로 평가되며, "
        
        if success_prob >= 0.7:
            assessment += "임무 완수를 위한 제반 여건이 매우 양호한 것으로 판단됩니다."
        elif success_prob >= 0.4:
            assessment += "효과적인 자원 분배와 치밀한 계획 수립이 필요한 상황입니다."
        else:
            assessment += "임무 수행을 위한 추가 자원 확보 및 작전 계획 재검토가 필요할 수 있습니다."
    else:
        assessment = f"'{location}' 일대에서 감지된 '{threat_type}' 위협에 대한 분석 결과입니다. "
        assessment += f"현재 위협 지수는 {int(threat_level * 100)}%로 평가되며, "
        
        if threat_level >= 0.8:
            assessment += "즉각적이고 단호한 대응이 필요한 심각한 위협 상황으로 판단됩니다."
        elif threat_level >= 0.5:
            assessment += "지속적인 정찰과 유연한 대응 태세 유지가 필요한 상황입니다."
        else:
            assessment += "정상 수준의 감시 체계를 유지하며 상황 변화를 예의주시해야 합니다."
    
    return assessment

def _validate_llm_assessment(self, assessment: str, situation_info: Dict) -> bool:
    """LLM 생성 문장의 품질 검증"""
    # 1. 최소 길이 검증
    if len(assessment) < 30:
        return False
    
    # 2. 의미없는 응답 필터링
    invalid_responses = ["죄송", "알 수 없", "생성할 수 없", "오류", "죄송합니다"]
    if any(invalid in assessment for invalid in invalid_responses):
        return False
    
    # 3. 기본적인 문장 구조 확인 (선택적)
    # 너무 엄격하면 안됨 - LLM이 다양한 표현 사용 가능
    
    return True
```

---

## 5. 최종 권장사항

### 5.1 추천: **하이브리드 접근법 (LLM 우선 + 템플릿 Fallback)**

**이유:**

1. **사용자 경험 개선**
   - 템플릿의 반복적인 문장 패턴 문제 해결
   - 더 자연스럽고 읽기 쉬운 문장 제공
   - 상황에 맞는 다양한 표현 가능

2. **안정성 보장**
   - LLM 실패 시 템플릿으로 즉시 대체
   - 오프라인 환경에서도 작동 가능
   - 예측 가능한 최소 품질 보장

3. **비용 효율성**
   - LLM이 사용 가능할 때만 비용 발생
   - Fallback으로 불필요한 비용 방지

4. **점진적 개선**
   - 현재 템플릿을 유지하면서 LLM 추가
   - 사용자 피드백에 따라 LLM 비중 조절 가능

### 5.2 구현 우선순위

| 단계 | 작업 | 우선순위 |
|------|------|----------|
| 1 | 하이브리드 구조 구현 (LLM 우선 + Fallback) | 높음 |
| 2 | 검증 로직 추가 | 높음 |
| 3 | 사용자 피드백 수집 | 중간 |
| 4 | 프롬프트 최적화 (필요 시) | 중간 |
| 5 | 캐싱 전략 도입 (선택적) | 낮음 |

### 5.3 주의사항

1. **정확성 보장**
   - 프롬프트에 정확한 수치 명시
   - "수치를 정확히 반영하라"는 지시사항 포함

2. **성능 최적화**
   - LLM 호출을 비동기로 처리 (선택적)
   - 캐싱 전략 고려 (동일 입력에 대해)

3. **모니터링**
   - LLM 성공률 추적
   - Fallback 사용 빈도 모니터링
   - 사용자 만족도 조사

---

## 6. 예상 효과

### 6.1 개선 전 (템플릿 기반)

```
예시: "'작전 구역' 일대에서 감지된 '침투' 위협에 대한 분석 결과입니다. 
현재 위협 지수는 85%로 평가되며, 즉각적이고 단호한 대응이 필요한 
심각한 위협 상황으로 판단됩니다."
```

**문제점:**
- 항상 같은 패턴 반복
- 기계적인 느낌
- 맥락이 부족함

### 6.2 개선 후 (LLM 기반)

```
예시: "'작전 구역' 일대에서 '침투' 유형의 위협이 감지되었습니다. 
위협 수준 85%로 평가되며, 이는 적의 침투 작전이 진행 중임을 시사합니다. 
즉각적인 차단 작전과 추가 정찰이 필요합니다."
```

**개선점:**
- 더 자연스러운 문장 흐름
- 상황에 맞는 구체적 판단
- 읽기 쉽고 이해하기 쉬움

---

## 7. 결론

### 7.1 최종 권장: **하이브리드 접근법 (LLM 우선 + 템플릿 Fallback)**

**이유:**
- ✅ **사용자 경험 개선**: 템플릿의 반복적인 패턴 문제 해결, 자연스러운 문장 제공
- ✅ **안정성 보장**: LLM 실패 시 템플릿으로 즉시 대체, 오프라인 환경 지원
- ✅ **비용 효율성**: LLM 사용 가능할 때만 비용 발생
- ✅ **점진적 개선**: 피드백 기반 최적화 가능

### 7.2 구현 시 고려사항

1. **정확성 보장**
   - 프롬프트에 정확한 수치 명시
   - "수치를 정확히 반영하라"는 지시사항 포함
   - 검증 로직으로 핵심 정보 포함 여부 확인

2. **성능 최적화**
   - LLM 호출을 비동기로 처리 (선택적)
   - 캐싱 전략 고려 (동일 입력에 대해)

3. **모니터링**
   - LLM 성공률 추적
   - Fallback 사용 빈도 모니터링
   - 사용자 만족도 조사

### 7.3 예상 개선 효과

| 측면 | 개선 전 (템플릿) | 개선 후 (LLM) | 개선율 |
|------|----------------|--------------|--------|
| **문장 다양성** | 낮음 (3-5개 패턴) | 높음 (무한 변형) | ⬆️ 90%+ |
| **자연스러움** | 보통 | 높음 | ⬆️ 70%+ |
| **사용자 만족도** | 보통 | 높음 | ⬆️ 60%+ |
| **안정성** | 높음 | 높음 (Fallback) | 유지 |
| **성능** | 즉시 | 0.5-2초 | ⬇️ 약간 |

### 7.4 구현 우선순위

**즉시 구현 권장:**
- 하이브리드 구조 (LLM 우선 + Fallback)
- 기본 검증 로직

**단기 개선 (1-2주):**
- 프롬프트 최적화
- 모니터링 체계 구축

**장기 개선 (선택적):**
- 캐싱 전략
- 비동기 처리
- A/B 테스트
