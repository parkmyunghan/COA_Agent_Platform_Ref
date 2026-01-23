# RuleEngine 규칙 파일 설명

## 문서 정보
- **작성일**: 2026-01-06
- **목적**: 시스템 초기화 시 나타나는 "규칙 파일 로드 완료" 메시지 설명

---

## 1. 메시지 의미

시스템 초기화 단계에서 나타나는 메시지:
```
[INFO] 규칙 파일 로드 완료: 3개 규칙, 3개 가중치
```

이 메시지는 **RuleEngine**이 YAML 규칙 파일을 성공적으로 로드했다는 의미입니다.

### 의미
- **3개 규칙**: 위협 수준에 따른 방어 COA 추천 규칙 3개
- **3개 가중치**: COA 평가 시 사용할 가중치 3개

---

## 2. 규칙 파일 위치 및 구조

### 파일 위치
```
agents/defense_coa_agent/rules_defense.yaml
```

### 파일 구조
```yaml
rules:
  - name: "규칙명"
    condition:
      # 조건 정의
    action:
      # 액션 정의

weights:
  # 가중치 정의
```

---

## 3. 현재 정의된 규칙 (3개)

### 규칙 1: High Threat Defense (고위협 방어)
```yaml
- name: "High Threat Defense"
  condition:
    threat_level: "> 0.7"  # 위협 수준이 0.7 초과
  action:
    coa: "Main_Defense"     # 주 방어 COA 추천
    priority: 1             # 최우선 순위
```

**의미**: 위협 수준이 높을 때(0.7 초과) 주 방어 COA를 최우선으로 추천

### 규칙 2: Moderate Threat Defense (중위협 방어)
```yaml
- name: "Moderate Threat Defense"
  condition:
    threat_level: "> 0.4 and <= 0.7"  # 위협 수준이 0.4~0.7 사이
  action:
    coa: "Moderate_Defense"            # 중간 방어 COA 추천
    priority: 2                         # 두 번째 우선순위
```

**의미**: 위협 수준이 중간일 때(0.4~0.7) 중간 방어 COA를 추천

### 규칙 3: Low Threat Defense (저위협 방어)
```yaml
- name: "Low Threat Defense"
  condition:
    threat_level: "<= 0.4"  # 위협 수준이 0.4 이하
  action:
    coa: "Minimal_Defense"  # 최소 방어 COA 추천
    priority: 3             # 세 번째 우선순위
```

**의미**: 위협 수준이 낮을 때(0.4 이하) 최소 방어 COA를 추천

---

## 4. 가중치 (3개)

```yaml
weights:
  threat_level: 1.0          # 위협 수준 가중치 (최우선)
  defense_assets: 0.8        # 방어 자산 가중치
  situation_urgency: 0.6     # 상황 긴급도 가중치
```

### 의미
- **threat_level (1.0)**: 위협 수준이 가장 중요한 평가 요소
- **defense_assets (0.8)**: 방어 자산 가용성이 두 번째로 중요
- **situation_urgency (0.6)**: 상황 긴급도는 상대적으로 낮은 가중치

---

## 5. RuleEngine 동작 방식

### 5.1 초기화
```python
# agents/defense_coa_agent/logic_defense_enhanced.py
self.rule_engine = RuleEngine()
```

RuleEngine이 초기화되면 자동으로 `rules_defense.yaml` 파일을 로드합니다.

### 5.2 규칙 평가 프로세스

1. **상황 정보 수집**
   ```python
   rule_context = {
       "threat_level": 0.85  # 예: 위협 수준 0.85
   }
   ```

2. **규칙 매칭**
   - 각 규칙의 조건을 평가
   - 위협 수준 0.85 → "High Threat Defense" 규칙 매칭 (0.7 초과)

3. **COA 추천**
   ```python
   recommended_coa = rule_engine.get_recommended_coa(rule_context)
   # 결과: {"coa": "Main_Defense", "priority": 1, "rule_name": "High Threat Defense"}
   ```

4. **점수 조정**
   ```python
   strategies = rule_engine.apply_rule_based_scoring(strategies, rule_context)
   ```
   - 규칙에서 추천된 COA와 일치하는 방책에 가산점 부여
   - 일치하지 않는 방책에 소폭 감점

---

## 6. 사용 위치

### 6.1 Defense COA Agent
```python
# agents/defense_coa_agent/logic_defense_enhanced.py
class EnhancedDefenseCOAAgent:
    def __init__(self, core, **kwargs):
        # 규칙 엔진 초기화
        self.rule_engine = RuleEngine()
```

### 6.2 COA 추천 프로세스
```python
# 규칙 기반 점수 조정 적용
strategies = self.rule_engine.apply_rule_based_scoring(strategies, rule_context)
```

---

## 7. 규칙 파일 수정 방법

### 7.1 규칙 추가
```yaml
rules:
  - name: "New Rule Name"
    condition:
      threat_level: "> 0.9"  # 조건
      defense_assets: "> 5"   # 복합 조건 가능
    action:
      coa: "Emergency_Defense"
      priority: 0  # 더 높은 우선순위 (낮은 숫자)
```

### 7.2 가중치 수정
```yaml
weights:
  threat_level: 1.2      # 가중치 증가
  defense_assets: 0.9    # 가중치 증가
  situation_urgency: 0.5 # 가중치 감소
```

### 7.3 조건 연산자
- `> 0.7`: 0.7 초과
- `>= 0.7`: 0.7 이상
- `< 0.4`: 0.4 미만
- `<= 0.4`: 0.4 이하
- `> 0.4 and <= 0.7`: 0.4 초과이고 0.7 이하
- `> 0.7 or < 0.2`: 0.7 초과 또는 0.2 미만

---

## 8. 규칙 엔진의 역할

### 8.1 COA 추천 보조
- 위협 수준에 따라 적절한 방어 COA를 빠르게 추천
- 규칙 기반 점수 조정으로 COA 평가 점수에 반영

### 8.2 하이브리드 방식
현재 시스템은 **하이브리드 방식**을 사용합니다:

1. **규칙 기반** (RuleEngine): 빠른 초기 추천
2. **온톨로지 기반**: 구조화된 지식 활용
3. **RAG 기반**: 교리/교범 문서 참조
4. **LLM 기반**: 상황별 맞춤 설명

RuleEngine은 이 중 **규칙 기반 추천**을 담당합니다.

---

## 9. 규칙 파일과 교리 문서의 차이

| 구분 | 규칙 파일 (RuleEngine) | 교리 문서 (RAG) |
|------|----------------------|----------------|
| **형식** | YAML (구조화) | Markdown (서술형) |
| **용도** | 빠른 규칙 기반 추천 | 교리 문장 기반 근거 설명 |
| **처리 방식** | 조건 평가 → 액션 실행 | RAG 검색 → 인용 |
| **변경 용이성** | 쉬움 (YAML 수정) | 어려움 (문서 재생성) |
| **적용 시점** | COA 추천 초기 단계 | COA 추천 후 근거 설명 |

---

## 10. 체크리스트

### 규칙 파일 확인
- [x] 파일 위치: `agents/defense_coa_agent/rules_defense.yaml`
- [x] 규칙 수: 3개
- [x] 가중치 수: 3개
- [x] 로드 확인: 시스템 초기화 시 자동 로드

### 규칙 내용
- [x] High Threat Defense: 위협 > 0.7 → Main_Defense
- [x] Moderate Threat Defense: 위협 0.4~0.7 → Moderate_Defense
- [x] Low Threat Defense: 위협 <= 0.4 → Minimal_Defense

### 가중치
- [x] threat_level: 1.0
- [x] defense_assets: 0.8
- [x] situation_urgency: 0.6

---

## 11. 참고 사항

### 11.1 규칙 파일이 없을 때
규칙 파일이 없거나 로드에 실패하면:
- 경고 메시지 출력
- 기본 규칙 로직 사용 (하드코딩된 규칙)
- COA 추천은 계속 작동 (규칙 없이)

### 11.2 규칙 재로드
```python
rule_engine.reload_rules()  # 규칙 파일 재로드
```

### 11.3 다른 Agent의 규칙 파일
- CCIR Agent: `agents/ccir_recommendation_agent/rules_ccir.yaml`
- Defense COA Agent: `agents/defense_coa_agent/rules_defense.yaml`

---

**문서 버전**: 1.0  
**최종 수정일**: 2026-01-06


