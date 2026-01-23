# 방책 비교 분석 점수 동일 문제 해결 구현

## 수정 사항

### 1. `extract_score` 함수: breakdown 우선 사용

**위치**: `api/routers/agent.py` (114-140줄)

**변경 내용**:
- 기존: `rec`의 직접 필드를 먼저 확인 → breakdown 무시 가능
- 수정: breakdown을 우선 사용, `rec`의 직접 필드는 fallback으로만 사용

**코드**:
```python
def extract_score(field_name, breakdown_key, default=0.0):
    """점수 필드 추출 (breakdown 우선, rec 직접 필드는 fallback)"""
    # 🔥 FIX: breakdown을 우선 사용 (COA별로 다를 수 있음)
    if breakdown_key is not None and score_breakdown:
        breakdown_value = safe_get_score(breakdown_key, None)
        if breakdown_value is not None:
            logger.info(f"    [DEBUG] {field_name}: breakdown['{breakdown_key}']에서 추출 = {breakdown_value:.4f}")
            return breakdown_value
    
    # breakdown에 없으면 rec에서 직접 필드 확인 (fallback)
    direct_value = rec.get(field_name)
    if direct_value is not None:
        try:
            direct_score = float(direct_value)
            logger.info(f"    [DEBUG] {field_name}: rec에서 직접 추출 = {direct_score:.4f} (breakdown 없음)")
            return direct_score
        except (TypeError, ValueError):
            pass
    
    # 둘 다 없으면 기본값
    logger.warning(f"    [WARNING] {field_name}: breakdown['{breakdown_key}']와 rec['{field_name}'] 모두 없음, 기본값 {default} 사용")
    return default
```

### 2. `_calculate_asset_score` 개선: COA별 필요 자원 고려

**위치**: `core_pipeline/coa_scorer.py` (920-958줄)

**변경 내용**:
- COA별 필요 자원과 가용 자원을 비교하여 점수 계산
- 기본값 0.5 대신 실제 매칭률 사용

**코드**:
```python
def _calculate_asset_score(self, context: Dict) -> float:
    """방어 자산 능력 점수 계산 (COA별 필요 자원 고려)"""
    coa_uri = context.get('coa_uri')
    required_resources = context.get('required_resources', [])
    available_resources = context.get('available_resources', [])
    
    # COA별 필요 자원이 있으면 가용 자원과 비교
    if coa_uri and required_resources:
        if isinstance(required_resources, list) and len(required_resources) > 0:
            if isinstance(available_resources, list) and len(available_resources) > 0:
                matched = set(required_resources) & set(available_resources)
                match_ratio = len(matched) / len(required_resources)
                asset_capability = match_ratio
            else:
                asset_capability = 0.2  # 가용 자원 없으면 낮은 점수
        else:
            asset_capability = context.get('asset_capability', 0.5)
    else:
        asset_capability = context.get('asset_capability', 0.5)
    
    # 기존 로직 유지 (defense_assets 기반 계산)
    # ...
    
    return min(1.0, max(0.0, asset_capability))
```

### 3. 디버깅 로그 강화

**위치**: `api/routers/agent.py`

**추가된 로그**:
- breakdown 키 존재 여부 확인
- rec에 직접 필드가 있는지 확인 (하드코딩된 값 경고)
- 모든 COA가 동일한 점수인 경우 경고
- 각 점수가 어디서 추출되었는지 상세 로그

### 4. Pass 1/Pass 2 breakdown 저장 개선

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`

**변경 내용**:
- Pass 1 breakdown 저장 시 copy() 사용 (참조 문제 방지)
- Pass 2 breakdown 업데이트 시 로그 추가

## 예상 효과

1. **breakdown 우선 사용**: COA별로 다른 breakdown 값이 우선 사용됨
2. **`assets` 점수 개선**: COA별 필요 자원과 가용 자원 비교로 다른 점수 계산
3. **디버깅 강화**: 문제 발생 시 원인 파악 용이

## 다음 단계

1. **방책 추천 재실행**: 프론트엔드에서 방책 추천을 다시 실행
2. **로그 확인**: 백엔드 로그에서 breakdown 추출 경로 확인
3. **프론트엔드 확인**: COA별로 다른 점수가 표시되는지 확인

## 추가 확인 사항

만약 여전히 동일한 점수가 표시된다면:
1. **breakdown이 실제로 동일한지 확인**: 로그에서 각 COA별 breakdown 값 비교
2. **`rec`에 직접 필드가 있는지 확인**: 로그에서 "rec에 직접 필드가 있습니다" 경고 확인
3. **Pass 1 vs Pass 2 breakdown 차이 확인**: 로그에서 Pass 1/Pass 2 breakdown 비교
