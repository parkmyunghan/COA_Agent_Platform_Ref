# 위협수준 데이터 흐름 전체 분석

## 기존 통합 변환기 확인

### 1. `SituationInfoConverter` (common/situation_converter.py)

**이미 존재하는 통합 변환기:**
- `normalize_threat_level()`: 문자열("HIGH", "MEDIUM", "LOW") 및 숫자를 정규화
- `convert()`: 모든 입력 방식을 표준 `situation_info`로 변환
- `_convert_real_data()`: 실제 데이터 테이블 변환 시 사용

**매핑 테이블:**
```python
THREAT_LEVEL_MAPPING = {
    "high": 0.85, "medium": 0.60, "low": 0.30,
    "높음": 0.85, "중간": 0.60, "낮음": 0.30,
    "h": 0.85, "m": 0.60, "l": 0.30
}
```

**반환 형식:**
```python
(normalized: float, raw: int, label: str)
# 예: (0.85, 85, "HIGH")
```

## 현재 데이터 흐름 분석

### 1. Excel → 백엔드

```
위협상황.XLSX
  ↓
ThreatEvent.from_row() (core_pipeline/data_models.py)
  - threat_level: Optional[str] = None
  - 변환 없이 원본 값 그대로 저장 (문자열 "HIGH" 또는 숫자)
  ↓
/api/v1/data/threats (api/routers/data.py)
  - SituationInfoConverter.normalize_threat_level() 사용
  - normalized, raw_val, label = normalize_threat_level(threat_level_raw)
  - threat_level_normalized = str(raw_val)  # 0-100 범위의 정수 문자열
  ↓
ThreatEventBase (api/schemas/__init__.py)
  - threat_level: Optional[str] = None
  - API 스키마가 문자열을 기대하므로 문자열로 반환
```

### 2. 백엔드 → 프론트엔드

```
API 응답 (ThreatEventBase)
  - threat_level: "85" (0-100 범위의 정수 문자열)
  - 또는 원본 값이 그대로 전달될 수 있음 (변환 실패 시)
  ↓
프론트엔드 (frontend/src/lib/threat-level-parser.ts)
  - parseThreatLevel() 사용
  - 문자열 "HIGH", "MEDIUM", "LOW" 및 숫자 처리
```

### 3. 프론트엔드 내부 처리

```
위협 선택 (SituationInputPanel.tsx)
  - parseThreatLevel(selectedThreat.threat_level)
  - threat_level: 0.85 (0-1 범위)
  - 위협수준: "85" (0-100 범위 문자열)
  ↓
situationInfo 업데이트
  - threat_level: 0.85
  - 위협수준: "85"
  ↓
각 컴포넌트에서 사용
  - 정황보고: parseThreatLevel() 사용
  - 위협마커: parseThreatLevel() 사용
  - 상황요약: parseThreatLevel() 사용
```

## 문제점 분석

### 1. 백엔드 변환 시점

**현재:**
- `/api/v1/data/threats`에서만 변환
- `ThreatEvent.from_row()`에서는 변환하지 않음
- 다른 경로(예: Agent 실행)에서는 변환되지 않을 수 있음

**영향:**
- API 응답의 `threat_level`이 일관되지 않을 수 있음
- 문자열 "HIGH"가 그대로 전달될 수 있음

### 2. 프론트엔드 파서 중복

**현재:**
- 백엔드에서 이미 변환하지만, API 스키마가 문자열을 기대
- 프론트엔드에서 별도 파서 생성 (중복 가능성)

**영향:**
- 백엔드 변환 결과와 프론트엔드 파서가 불일치할 수 있음
- 매핑 테이블이 중복됨

### 3. 데이터 형식 불일치

**현재:**
- 백엔드: `normalize_threat_level()` → (0.85, 85, "HIGH")
- API 응답: `threat_level: "85"` (0-100 범위 문자열)
- 프론트엔드: `parseThreatLevel()` → {normalized: 0.85, percent: 85, label: "HIGH"}

**문제:**
- 백엔드 변환이 제대로 적용되지 않으면 원본 문자열이 전달될 수 있음
- 프론트엔드 파서가 백엔드 변환 결과를 처리할 수 있어야 함

## 재검토 및 개선 방안

### 옵션 1: 백엔드 변환 강화 (권장)

**변경 사항:**
1. `ThreatEvent.from_row()`에서 변환하지 않고 원본 유지 (현재 상태 유지)
2. `/api/v1/data/threats`에서 변환 (현재 구현)
3. **추가**: 다른 경로에서도 변환 보장

**장점:**
- 백엔드에서 일관된 변환
- 프론트엔드는 변환된 값만 처리

**단점:**
- API 스키마가 문자열을 기대하므로 변환된 값도 문자열로 전달

### 옵션 2: 프론트엔드 파서 유지 (현재 구현)

**변경 사항:**
1. 백엔드 변환 결과(0-100 범위 문자열) 처리
2. 원본 문자열("HIGH", "MEDIUM", "LOW") 처리
3. 숫자 처리

**장점:**
- 백엔드 변환 실패 시에도 처리 가능
- 다양한 형식 지원

**단점:**
- 백엔드와 프론트엔드 로직 중복

### 옵션 3: 통합 (최적)

**변경 사항:**
1. 백엔드: `SituationInfoConverter.normalize_threat_level()` 사용 (현재 구현)
2. 프론트엔드: 백엔드 변환 결과를 우선 처리, 원본 문자열은 fallback

**구현:**
```typescript
// 백엔드 변환 결과 우선 처리
if (백엔드에서 변환된 숫자 문자열인 경우) {
    // 0-100 범위의 정수 문자열 처리
    return { normalized: parseInt(value) / 100, ... }
} else {
    // 원본 문자열 처리 (fallback)
    return parseThreatLevel(value)
}
```

## 권장 사항 및 개선 사항

### 1. 백엔드 변환 강화
- ✅ `/api/v1/data/threats`에서 `SituationInfoConverter.normalize_threat_level()` 사용
- ✅ 변환 실패 시 예외 처리 및 로깅 추가
- ✅ 변환된 값을 0-100 범위의 정수 문자열로 반환

### 2. 프론트엔드 파서 개선
- ✅ 백엔드 변환 결과(0-100 범위의 정수 문자열) 우선 처리
- ✅ 원본 문자열("HIGH", "MEDIUM", "LOW") fallback 처리
- ✅ 백엔드 매핑 테이블과 일치하도록 매핑 테이블 동기화

### 3. 일관성 보장
- ✅ 백엔드와 프론트엔드 모두 `SituationInfoConverter`의 매핑 테이블 사용
- ✅ 프론트엔드 파서는 백엔드 변환 결과를 우선 처리

## 최종 구현 상태

### 백엔드
- ✅ `api/routers/data.py`: `SituationInfoConverter.normalize_threat_level()` 사용
- ✅ 변환된 값을 0-100 범위의 정수 문자열로 반환
- ✅ 변환 실패 시 예외 처리 및 원본 값 유지

### 프론트엔드
- ✅ `frontend/src/lib/threat-level-parser.ts`: 통합 파서
- ✅ 백엔드 변환 결과(0-100 범위 정수 문자열) 우선 처리
- ✅ 원본 문자열("HIGH", "MEDIUM", "LOW") fallback 처리
- ✅ 백엔드 매핑 테이블과 일치

### 데이터 흐름
1. Excel → `ThreatEvent.from_row()` → 원본 값 유지
2. `/api/v1/data/threats` → `SituationInfoConverter.normalize_threat_level()` → "85" (0-100 범위 문자열)
3. 프론트엔드 → `parseThreatLevel("85")` → {normalized: 0.85, percent: 85, label: "HIGH"}
4. 각 컴포넌트에서 일관된 값 사용
