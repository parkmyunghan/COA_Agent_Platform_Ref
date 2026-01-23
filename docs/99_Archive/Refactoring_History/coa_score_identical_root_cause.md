# 방책 비교 분석 점수 동일 문제 근본 원인 분석

## 문제 상황

프론트엔드에서 모든 방책이 동일한 점수를 표시:
- 전투력: 50% (0.5)
- 기동성: 20% (0.2)
- 제약조건: 90% (0.9)
- 위협대응: 75% (0.75)
- 위험도: 25% (0.25)

## 근본 원인 분석

### 1. `extract_score` 함수의 우선순위 문제

**위치**: `api/routers/agent.py` (115-128줄)

```python
def extract_score(field_name, breakdown_key, default=0.0):
    """점수 필드 추출"""
    # 먼저 rec에서 직접 필드 확인 (None이 아닌 경우만)
    direct_value = rec.get(field_name)
    if direct_value is not None:
        return float(direct_value)  # ← 여기서 반환하면 breakdown 무시!
    
    # rec에 없으면 score_breakdown에서 추출
    if breakdown_key is not None:
        return safe_get_score(breakdown_key, default)
    return default
```

**문제**:
- `rec`에 `combat_power_score`, `mobility_score` 등의 필드가 있으면 breakdown을 무시하고 그것을 사용
- 모든 COA에 대해 동일한 값이 하드코딩되어 있을 수 있음

### 2. `_calculate_asset_score`의 기본값 문제

**위치**: `core_pipeline/coa_scorer.py` (920-958줄)

```python
def _calculate_asset_score(self, context: Dict) -> float:
    """방어 자산 능력 점수 계산"""
    # 직접 제공된 자산 능력 사용
    asset_capability = context.get('asset_capability', 0.5)  # ← 기본값 0.5!
    
    # 자산 정보가 있으면 계산
    if asset_capability == 0.5:  # ← 기본값인 경우에만 계산
        defense_assets = context.get('defense_assets', [])
        # ...
    
    return min(1.0, max(0.0, asset_capability))
```

**문제**:
- `asset_capability`가 context에 없으면 기본값 0.5 사용
- 모든 COA에 대해 동일한 값(0.5 = 50%) 반환
- COA별 필요 자원과 가용 자원을 비교하지 않음

### 3. 백엔드 로그 vs 프론트엔드 점수 불일치

**백엔드 로그 (COAScorer breakdown)**:
- 위협: 0.850 (85%) → 프론트엔드: 75% ❌
- 자원: 0.000, 0.152, 0.303 (다름) → 프론트엔드: 20% (모두 동일) ❌
- 환경: 0.900, 0.700 (다름) → 프론트엔드: 90% (모두 동일) ❌
- 자산: breakdown에 포함되지만 로그에 출력 안 됨 → 프론트엔드: 50% (모두 동일) ❌

**분석**:
- 백엔드에서는 breakdown이 COA별로 다르게 계산됨
- 프론트엔드에서는 모든 COA가 동일한 점수 표시
- `rec`에 직접 필드가 있거나 breakdown이 제대로 전달되지 않았을 가능성

## 해결 방안

### 옵션 1: breakdown 우선 사용 (권장)

**위치**: `api/routers/agent.py`의 `extract_score` 함수

**방법**: breakdown을 우선 사용하고, 없을 때만 `rec`의 직접 필드 사용

```python
def extract_score(field_name, breakdown_key, default=0.0):
    """점수 필드 추출 (breakdown 우선)"""
    # 1순위: score_breakdown에서 추출 (COA별로 다를 수 있음)
    if breakdown_key is not None and score_breakdown:
        breakdown_value = safe_get_score(breakdown_key, None)
        if breakdown_value is not None:
            return breakdown_value
    
    # 2순위: rec에서 직접 필드 확인
    direct_value = rec.get(field_name)
    if direct_value is not None:
        try:
            return float(direct_value)
        except (TypeError, ValueError):
            pass
    
    # 3순위: 기본값
    return default
```

### 옵션 2: `_calculate_asset_score` 개선

**위치**: `core_pipeline/coa_scorer.py`의 `_calculate_asset_score` 메서드

**방법**: COA별 필요 자원과 가용 자원을 비교하여 점수 계산

```python
def _calculate_asset_score(self, context: Dict) -> float:
    """방어 자산 능력 점수 계산 (COA별 필요 자원 고려)"""
    # COA별 필요 자원 확인
    coa_uri = context.get('coa_uri')
    required_resources = context.get('required_resources', [])
    available_resources = context.get('available_resources', [])
    defense_assets = context.get('defense_assets', [])
    
    # COA별 필요 자원이 있으면 가용 자원과 비교
    if coa_uri and required_resources:
        # 자원 매칭률 계산
        # ...
        asset_capability = match_ratio
    else:
        # 기존 로직 (상황 정보 기반)
        asset_capability = context.get('asset_capability', 0.5)
        # ...
    
    return min(1.0, max(0.0, asset_capability))
```

### 옵션 3: 디버깅 로그 강화 (이미 적용됨)

**위치**: `api/routers/agent.py`

**방법**: 각 점수가 어디서 추출되었는지 로그로 확인

## 권장 사항

**옵션 1 (breakdown 우선 사용)**을 권장합니다:
1. COAScorer breakdown이 COA별로 다르게 계산되므로 이를 우선 사용
2. `rec`의 직접 필드는 하드코딩된 값일 수 있으므로 fallback으로만 사용
3. 프론트엔드에서 COA별로 다른 점수 표시 가능

**추가 개선**:
- `_calculate_asset_score`에서 COA별 필요 자원 고려
- 디버깅 로그를 통해 실제 추출 경로 확인

## 다음 단계

1. **옵션 1 적용**: breakdown 우선 사용하도록 `extract_score` 함수 수정
2. **방책 추천 재실행**: 새로운 로그 확인하여 점수 추출 경로 확인
3. **프론트엔드 확인**: COA별로 다른 점수 표시되는지 확인
