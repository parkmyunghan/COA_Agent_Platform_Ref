# 팔란티어 모드에서 방책 비교 분석 점수 동일 문제 해결 방안

## 문제 상황

**팔란티어 모드를 사용하고 있음에도 불구하고**:
- 방책 비교 분석에서 각 항목 점수 (전투력, 기동성, 제약조건, 위협대응, 위험도)가 모두 동일 (0.0%)
- 총점은 다름

## 원인 분석

### 1. Pass 1 vs Pass 2 breakdown 업데이트 문제

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`의 `_score_with_palantir_mode`

**Pass 1 (모든 후보 대상)**:
```python
pass1_score_result = scorer.calculate_score(pass1_context)
strategy['score_breakdown'] = pass1_score_result.get('breakdown', {})
```

**Pass 2 (상위 5개만 정밀 계산)**:
```python
score_result = scorer.calculate_score(context)
strategy['score_breakdown'] = score_result['breakdown']
```

**문제**:
- Pass 2에서 breakdown을 업데이트하지만, **상위 5개만** 업데이트됨
- 나머지 COA는 Pass 1의 breakdown을 그대로 사용
- Pass 1에서는 `chain_info: {"score": 0.5}`로 고정되어 있어 breakdown이 제한적

### 2. COAScorer breakdown의 특성

COAScorer의 각 점수 계산 메서드 분석:

1. **`threat`**: 상황 정보 기반 → **모든 COA 동일** (정상)
2. **`resources`**: 상황 정보 기반 → **모든 COA 동일** (정상)
3. **`environment`**: 상황 정보 기반 → **모든 COA 동일** (정상)
4. **`assets`**: 상황 정보 기반 → **모든 COA 동일 가능** (개선 필요)
5. **`historical`**: COA별로 다를 수 있음 (`expected_success_rate` 사용)
6. **`chain`**: COA별로 다름 ✅ (Pass 1에서는 0.5로 고정, Pass 2에서만 계산)
7. **`mission_alignment`**: COA별로 다름 ✅

### 3. 프론트엔드 점수 추출 문제

**위치**: `api/routers/agent.py` (167-171줄)

```python
threat_response_score = extract_score("threat_response_score", "threat", 0.0)
combat_power_score = extract_score("combat_power_score", "assets", 0.0)
mobility_score = extract_score("mobility_score", "resources", 0.0)
constraint_score = extract_constraint_score()
risk_score = extract_risk_score()
```

**매핑 규칙**:
- `threat` → `threat_response_score` (위협 대응)
- `assets` → `combat_power_score` (전투력)
- `resources` → `mobility_score` (기동성)
- `environment` → `constraint_score` (제약조건)
- `risk_score`는 breakdown에 없으므로 `1.0 - threat_score` 계산

**문제**:
- `score_breakdown`에 값이 있어도 모두 0.0으로 표시되는 경우
- `score_breakdown`이 비어있거나 키가 없는 경우
- Pass 1의 breakdown이 Pass 2로 업데이트되지 않은 경우

## 해결 방안

### 옵션 1: Pass 2 breakdown을 모든 COA에 적용 (권장)

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`의 `_score_with_palantir_mode`

**방법**: Pass 2에서 계산된 breakdown을 상위 5개뿐만 아니라 모든 COA에 적용

```python
# Pass 2: 정밀 점수 계산 (상위 5개 대상)
# ... Pass 2 계산 ...

# Pass 2 breakdown을 상위 5개에 적용
for idx, strategy in enumerate(top_k_for_pass2):
    # Pass 2 결과에서 breakdown 가져오기
    # (이미 strategy['score_breakdown']에 업데이트됨)

# 나머지 COA에도 Pass 1 breakdown이 제대로 있는지 확인
for strategy in sorted_strategies[5:]:
    if not strategy.get('score_breakdown') or len(strategy.get('score_breakdown', {})) < 3:
        # Pass 1 breakdown이 없거나 불완전하면 재계산
        # (또는 최소한 기본 breakdown 제공)
        pass
```

### 옵션 2: Pass 1에서도 정확한 breakdown 계산

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`의 `_score_with_palantir_mode` Pass 1 부분

**방법**: Pass 1에서도 `chain_info`를 실제로 계산하도록 개선

```python
# Pass 1에서 chain_info를 실제로 계산
# (현재는 {"score": 0.5}로 고정)
# 체인 정보가 있으면 실제 점수 계산, 없으면 0.5 사용
chain_info = situation_analysis.get("chain_info", {})
if not chain_info or chain_info.get("score") == 0.5:
    # 체인 정보가 없으면 기본값 사용
    pass1_context["chain_info"] = {"score": 0.5}
else:
    # 체인 정보가 있으면 사용
    pass1_context["chain_info"] = chain_info
```

### 옵션 3: 프론트엔드 점수 추출 로직 개선

**위치**: `api/routers/agent.py`의 `extract_score` 함수

**방법**: breakdown이 없거나 불완전할 때 대체 로직 추가

```python
def extract_score(field_name, breakdown_key, default=0.0):
    """점수 필드 추출 (None 체크 명시)"""
    # 먼저 rec에서 직접 필드 확인
    direct_value = rec.get(field_name)
    if direct_value is not None:
        try:
            return float(direct_value)
        except (TypeError, ValueError):
            pass
    
    # rec에 없으면 score_breakdown에서 추출
    if breakdown_key is not None:
        score = safe_get_score(breakdown_key, default)
        # breakdown에서 추출한 값이 0.0이고 breakdown이 비어있지 않으면
        # 실제로 0.0인지 확인 (디버깅 로그 추가)
        if score == 0.0 and score_breakdown:
            logger.warning(f"COA {rec.get('coa_id')}: breakdown['{breakdown_key}'] = 0.0 (기본값일 수 있음)")
        return score
    return default
```

### 옵션 4: 디버깅 로그 추가로 실제 breakdown 값 확인

**위치**: `api/routers/agent.py`의 점수 추출 부분

**방법**: 각 COA별 breakdown 값을 로그로 출력하여 실제 값 확인

```python
# 디버깅: 각 COA별 breakdown 값 확인
logger.info(f"COA {idx+1} ({rec.get('coa_id', 'Unknown')}) breakdown 값:")
logger.info(f"  - threat={safe_get_score('threat'):.4f}")
logger.info(f"  - assets={safe_get_score('assets'):.4f}")
logger.info(f"  - resources={safe_get_score('resources'):.4f}")
logger.info(f"  - environment={safe_get_score('environment'):.4f}")
logger.info(f"  - chain={safe_get_score('chain'):.4f}")
logger.info(f"  - mission_alignment={safe_get_score('mission_alignment'):.4f}")

# 최종 추출된 점수도 로그
logger.info(f"  - threat_response_score={threat_response_score:.4f}")
logger.info(f"  - combat_power_score={combat_power_score:.4f}")
logger.info(f"  - mobility_score={mobility_score:.4f}")
logger.info(f"  - constraint_score={constraint_score:.4f}")
logger.info(f"  - risk_score={risk_score:.4f}")
```

## 권장 사항

**옵션 4 (디버깅 로그 추가)를 먼저 실행**하여 실제 breakdown 값 확인:
1. 각 COA별 breakdown이 실제로 동일한지 확인
2. breakdown이 제대로 전달되는지 확인
3. 프론트엔드에서 추출이 제대로 되는지 확인

**그 다음 옵션 1 또는 옵션 2 적용**:
- breakdown이 실제로 동일하다면: 옵션 2 (Pass 1에서도 정확한 breakdown 계산)
- breakdown이 다르지만 프론트엔드에서 추출이 안 된다면: 옵션 3 (프론트엔드 로직 개선)
- Pass 2 breakdown이 업데이트되지 않는다면: 옵션 1 (Pass 2 breakdown 적용)

## 추가 확인 사항

1. **실제 breakdown 값 확인**
   - 백엔드 로그에서 각 COA별 breakdown 값 확인
   - 프론트엔드에서 받은 breakdown 값 확인

2. **Pass 1 vs Pass 2 breakdown 차이 확인**
   - Pass 1 breakdown과 Pass 2 breakdown 비교
   - 상위 5개와 나머지 COA의 breakdown 비교

3. **프론트엔드 점수 추출 확인**
   - `extract_score` 함수가 제대로 작동하는지 확인
   - breakdown 키가 매핑 규칙과 일치하는지 확인
