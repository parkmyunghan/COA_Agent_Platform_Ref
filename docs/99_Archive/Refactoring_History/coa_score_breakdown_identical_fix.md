# 방책 비교 분석 점수 동일 문제 해결 방안

## 문제 상황

방책 비교 분석에서:
- **각 항목 점수 (전투력, 기동성, 제약조건, 위협대응, 위험도)**: 모두 동일 (0.0%)
- **총점**: 다름

## 원인 분석

### 1. COAScorer breakdown의 특성

COAScorer의 각 점수 계산 메서드 분석:

1. **`_calculate_threat_score`**: 상황 정보 기반 → **모든 COA 동일**
   - `threat_level` 또는 `threat_score` 사용
   - 상황 정보이므로 모든 COA에 대해 동일

2. **`_calculate_resource_score`**: 상황 정보 기반 → **모든 COA 동일**
   - `resource_availability` 사용
   - 상황 정보이므로 모든 COA에 대해 동일

3. **`_calculate_asset_score`**: 상황 정보 기반 → **모든 COA 동일 가능**
   - `defense_assets` (가용 방어 자산) 사용
   - 상황 정보이므로 모든 COA에 대해 동일할 수 있음
   - **개선 필요**: COA별 필요 자원과 가용 자원 비교

4. **`_calculate_environment_score`**: 상황 정보 기반 → **모든 COA 동일**
   - `environment_fit` 사용
   - 상황 정보이므로 모든 COA에 대해 동일

5. **`_calculate_historical_score`**: COA별로 다를 수 있음
   - `expected_success_rate` (COA별 예상 성공률) 사용
   - RAG 결과 기반 계산

6. **`_calculate_chain_score`**: COA별로 다름 ✅
   - `coa_uri`를 사용하여 COA별 체인 관계 분석
   - 각 COA별로 다른 점수 계산

7. **`_calculate_mission_alignment_score`**: COA별로 다름 ✅
   - `coa_id`, `coa_type`을 사용하여 COA-임무 부합성 분석
   - 각 COA별로 다른 점수 계산

### 2. 프론트엔드 점수 추출 문제

**위치**: `api/routers/agent.py` (167-171줄)

```python
threat_response_score = extract_score("threat_response_score", "threat", 0.0)
combat_power_score = extract_score("combat_power_score", "assets", 0.0)
mobility_score = extract_score("mobility_score", "resources", 0.0)
constraint_score = extract_constraint_score()
risk_score = extract_risk_score()
```

**문제**:
- `rec`에 직접 필드가 없으면 `score_breakdown`에서 추출
- `score_breakdown`에 COAScorer breakdown이 없으면 기본값 0.0 반환
- 기본 모드(`_score_strategies`)에서는 breakdown이 포함되지 않음

## 해결 방안

### 옵션 1: 기본 모드에서도 COAScorer breakdown 포함 (권장)

**위치**: `agents/defense_coa_agent/logic_defense_enhanced.py`의 `_score_strategies` 메서드

**방법**: 기본 모드에서도 각 COA별로 COAScorer breakdown 계산

```python
def _score_strategies(self, strategies: List[Dict], 
                     situation_info: Dict,
                     situation_analysis: Dict = None) -> List[Dict]:
    # ... 기존 agent_score, llm_score 계산 ...
    
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
        if coa_id and self.core.ontology_manager:
            coa_id_safe = str(coa_id).split('#')[-1] if '#' in str(coa_id) else str(coa_id)
            if hasattr(self.core.ontology_manager, '_make_uri_safe'):
                coa_id_safe = self.core.ontology_manager._make_uri_safe(coa_id_safe)
            if not coa_id_safe.startswith("COA_Library_"):
                coa_uri = f"http://coa-agent-platform.org/ontology#COA_Library_{coa_id_safe}"
            else:
                coa_uri = f"http://coa-agent-platform.org/ontology#{coa_id_safe}"
        else:
            coa_uri = coa_id if coa_id else None
        
        context = {
            "threat_level": self._extract_threat_level(situation_info),
            "coa_uri": coa_uri,
            "coa_id": coa_id,
            "situation_id": situation_info.get('위협ID'),
            "ontology_manager": self.core.ontology_manager,
            "graph": self.core.ontology_manager.graph if self.core.ontology_manager else None,
            "resource_availability": situation_info.get('resource_availability', 0.7),
            "defense_assets": situation_info.get('defense_assets', []),
            "environment_fit": 0.7,  # 기본값
            "coa_type": strategy.get('coa_type', 'defense'),
            "threat_type": situation_info.get('위협유형'),
            "mission_type": situation_info.get('임무유형'),
            "coa_suitability": self._safe_float(strategy.get('적합도점수', 1.0)),
            "expected_success_rate": strategy.get('expected_success_rate', 0.5),
            "required_resources": strategy.get('required_resources', []),
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

### 옵션 2: COAScorer의 `_calculate_asset_score` 개선

**위치**: `core_pipeline/coa_scorer.py`의 `_calculate_asset_score` 메서드

**방법**: COA별 필요 자원과 가용 자원을 비교하여 점수 계산

```python
def _calculate_asset_score(self, context: Dict) -> float:
    """자산 점수 계산 (COA별 필요 자원 고려)"""
    # COA별 필요 자원 확인
    coa_uri = context.get('coa_uri')
    required_resources = context.get('required_resources', [])
    
    # COA별 필요 자원이 있으면 가용 자원과 비교
    if coa_uri and required_resources:
        # 온톨로지에서 COA의 필요 자원 조회
        # 가용 자원과 비교하여 점수 계산
        # ...
    
    # 기존 로직 (상황 정보 기반)
    # ...
```

### 옵션 3: 프론트엔드에서 breakdown이 없을 때 대체 로직

**위치**: `api/routers/agent.py`의 `extract_score` 함수

**방법**: breakdown이 없을 때 다른 소스에서 점수 추출 시도

## 권장 사항

**옵션 1 (기본 모드에서도 COAScorer breakdown 포함)**을 권장합니다:
1. 기본 모드와 팔란티어 모드 모두에서 일관된 breakdown 제공
2. 각 COA별로 다른 점수 계산 보장
3. 프론트엔드에서 정확한 점수 표시 가능

**추가 개선**:
- `_calculate_asset_score`에서 COA별 필요 자원 고려
- `_calculate_resource_score`에서 COA별 필요 자원과 가용 자원 비교

## 참고

- `threat`, `resources`, `environment`는 상황 정보 기반이므로 모든 COA에 대해 동일한 것이 정상입니다.
- `assets`, `chain`, `mission_alignment`, `historical`는 COA별로 다를 수 있으므로, 이들이 제대로 계산되어야 합니다.
- 현재는 `chain`과 `mission_alignment`만 COA별로 다르게 계산되고, 나머지는 동일하거나 기본값을 사용하는 것으로 보입니다.
