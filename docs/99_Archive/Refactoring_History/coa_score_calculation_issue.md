# 방책 비교 분석 점수 산출 로직 문제 분석

## 문제 상황

방책 비교 분석(3개 방책)에서:
- **각 항목 점수 (전투력, 기동성, 제약조건, 위협대응, 위험도)**: 모두 동일
- **총점**: 다름

## 원인 분석

### 1. 백엔드 점수 계산 방식

#### 팔란티어 모드 (`_score_with_palantir_mode`)
- **Pass 1**: 모든 후보에 대해 대략적인 점수 계산
  - 각 COA별로 다른 `coa_uri`와 `coa_id`를 사용하여 `context` 구성
  - `scorer.calculate_score(context)` 호출
  - `score_result['breakdown']`을 `strategy['score_breakdown']`에 할당
- **Pass 2**: 상위 5개만 정밀 계산
  - 더 정확한 점수 계산 (체인 점수 등 포함)

#### 기본 모드 (`_score_strategies`)
- **문제**: `score_breakdown`에 COAScorer breakdown이 없음
  ```python
  strategy['score_breakdown'] = {
      'agent_score': agent_score,
      'llm_score': llm_score,
      'hybrid_score': hybrid_score
  }
  ```
  - COAScorer의 breakdown (threat, resources, assets, environment 등)이 포함되지 않음
  - 따라서 프론트엔드에서 `extract_score`가 모두 기본값 0.0을 반환

### 2. 프론트엔드 점수 추출 로직

**위치**: `api/routers/agent.py` (113-126줄)

```python
def extract_score(field_name, breakdown_key, default=0.0):
    """점수 필드 추출 (None 체크 명시)"""
    # 먼저 rec에서 직접 필드 확인 (None이 아닌 경우만)
    direct_value = rec.get(field_name)
    if direct_value is not None:
        try:
            return float(direct_value)
        except (TypeError, ValueError):
            pass
    
    # rec에 없으면 score_breakdown에서 추출 (breakdown_key가 None이 아니면)
    if breakdown_key is not None:
        return safe_get_score(breakdown_key, default)
    return default
```

**문제**:
1. `rec`에 직접 필드가 없으면 `score_breakdown`에서 추출
2. `score_breakdown`에 COAScorer breakdown이 없으면 기본값 0.0 반환
3. 모든 COA가 동일한 기본값을 사용

### 3. COAScorer의 breakdown 계산

**위치**: `core_pipeline/coa_scorer.py` (648-656줄)

```python
scores = {
    'threat': self._calculate_threat_score(context),
    'resources': self._calculate_resource_score(context),
    'assets': self._calculate_asset_score(context),
    'environment': self._calculate_environment_score(context),
    'historical': self._calculate_historical_score(context),
    'chain': self._calculate_chain_score(context),
    'mission_alignment': self._calculate_mission_alignment_score(context)
}
```

**각 메서드가 `coa_uri`나 `coa_id`를 사용하는지 확인 필요**:
- `_calculate_threat_score`: 상황 정보 기반 (모든 COA 동일 가능)
- `_calculate_resource_score`: 상황 정보 기반 (모든 COA 동일 가능)
- `_calculate_asset_score`: COA별로 다를 수 있음 (COA의 필요 자원 등)
- `_calculate_environment_score`: 상황 정보 기반 (모든 COA 동일 가능)
- `_calculate_chain_score`: COA별로 다를 수 있음 (COA의 체인 관계)
- `_calculate_mission_alignment_score`: COA별로 다를 수 있음 (COA-임무 부합성)

## 해결 방안

### 옵션 1: 기본 모드에서도 COAScorer breakdown 포함 (권장)

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`의 `_score_strategies` 메서드

**방법**: 기본 모드에서도 COAScorer를 사용하여 breakdown 계산

```python
def _score_strategies(self, strategies: List[Dict], 
                     situation_info: Dict,
                     situation_analysis: Dict = None) -> List[Dict]:
    # ... 기존 로직 ...
    
    # COAScorer를 사용하여 각 COA별 breakdown 계산
    from core_pipeline.coa_scorer import COAScorer
    scorer = COAScorer(
        data_manager=self.core.data_manager, 
        config=self.core.config, 
        context=situation_info
    )
    
    for strategy in strategies:
        # ... 기존 agent_score, llm_score 계산 ...
        
        # COAScorer breakdown 계산
        coa_id = strategy.get('COA_ID') or strategy.get('방책ID') or strategy.get('ID')
        coa_uri = f"http://coa-agent-platform.org/ontology#COA_Library_{coa_id}" if coa_id else None
        
        context = {
            "threat_level": self._extract_threat_level(situation_info),
            "coa_uri": coa_uri,
            "coa_id": coa_id,
            "situation_id": situation_info.get('위협ID'),
            "ontology_manager": self.core.ontology_manager,
            # ... 기타 컨텍스트 ...
        }
        
        score_result = scorer.calculate_score(context)
        
        # 기존 breakdown에 COAScorer breakdown 추가
        strategy['score_breakdown'] = {
            'agent_score': agent_score,
            'llm_score': llm_score,
            'hybrid_score': hybrid_score,
            # COAScorer breakdown 추가
            **score_result.get('breakdown', {})
        }
```

### 옵션 2: COAScorer의 각 점수 계산 메서드가 COA별로 다른 점수 반환하도록 개선

**위치**: `core_pipeline/coa_scorer.py`의 각 `_calculate_*_score` 메서드

**방법**: `coa_uri`나 `coa_id`를 활용하여 COA별로 다른 점수 계산

예를 들어:
- `_calculate_asset_score`: COA의 필요 자원과 가용 자원 비교
- `_calculate_chain_score`: COA별 체인 관계 분석
- `_calculate_mission_alignment_score`: COA-임무 부합성 분석

### 옵션 3: 프론트엔드에서 breakdown이 없을 때 대체 로직 추가

**위치**: `api/routers/agent.py`의 `extract_score` 함수

**방법**: breakdown이 없을 때 다른 소스에서 점수 추출 시도

## 권장 사항

**옵션 1 (기본 모드에서도 COAScorer breakdown 포함)**을 권장합니다:
1. 기본 모드와 팔란티어 모드 모두에서 일관된 breakdown 제공
2. 각 COA별로 다른 점수 계산 보장
3. 프론트엔드에서 정확한 점수 표시 가능

## 추가 확인 사항

1. **COAScorer의 각 점수 계산 메서드가 COA별로 다른 점수를 반환하는지 확인**
   - `_calculate_asset_score`: COA별 필요 자원 고려 여부
   - `_calculate_chain_score`: COA별 체인 관계 고려 여부
   - `_calculate_mission_alignment_score`: COA-임무 부합성 고려 여부

2. **Pass 1에서 모든 COA가 동일한 context를 사용하는지 확인**
   - `coa_uri`와 `coa_id`가 제대로 전달되는지
   - 각 COA별로 다른 점수가 계산되는지

3. **기본 모드 사용 여부 확인**
   - `use_palantir_mode`가 `False`인 경우 기본 모드 사용
   - 기본 모드에서는 breakdown이 제대로 포함되지 않음
