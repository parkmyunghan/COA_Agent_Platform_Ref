# 위협수준 데이터 흐름 분석 및 재정의

## 문제점

위협상황.XLSX 테이블에서 위협수준이 문자열("HIGH", "MEDIUM", "LOW")로 저장되어 있으나, 다른 테이블들에도 비슷한 위협수준 컬럼들이 있어 데이터 흐름에 일관성이 없었습니다.

## 데이터 흐름

### 1. 백엔드 데이터 로드

```
Excel 파일 (위협상황.XLSX)
  ↓
ThreatEvent.from_row() (core_pipeline/data_models.py)
  ↓
threat_level: Optional[str] = None  (문자열 그대로 저장)
  ↓
/api/v1/data/threats (api/routers/data.py)
  ↓
SituationInfoConverter.normalize_threat_level() (문자열 → 숫자 변환)
  ↓
ThreatEventBase.threat_level (0-100 범위의 정수 문자열)
```

### 2. 프론트엔드 데이터 처리

```
API 응답 (ThreatEventBase)
  ↓
parseThreatLevel() (frontend/src/lib/threat-level-parser.ts)
  ↓
{
  normalized: 0.85,  // 0-1 범위
  percent: 85,        // 0-100 범위
  label: "HIGH",      // "HIGH" | "MEDIUM" | "LOW"
  raw: "HIGH"         // 원본 값
}
  ↓
각 컴포넌트에서 사용
  - 정황보고 생성
  - 위협마커 팝업
  - 상황요약 패널
```

## 구현 내용

### 1. 통합 위협수준 파서 (`frontend/src/lib/threat-level-parser.ts`)

문자열("HIGH", "MEDIUM", "LOW") 및 숫자를 0-1 범위의 숫자로 정규화하는 통합 유틸리티:

```typescript
export function parseThreatLevel(rawValue: any): ThreatLevelParseResult | null {
    // 1. 문자열 매핑 (HIGH → 0.85, MEDIUM → 0.60, LOW → 0.30)
    // 2. 숫자 변환 및 정규화 (0-1 또는 0-100 → 0-1)
    // 3. 레이블 결정 ("HIGH" | "MEDIUM" | "LOW")
}
```

**매핑 테이블:**
- `HIGH`, `높음`, `H` → 0.85 (85%)
- `MEDIUM`, `중간`, `M` → 0.60 (60%)
- `LOW`, `낮음`, `L` → 0.30 (30%)
- `CRITICAL`, `위급` → 0.95 (95%)
- `VERY HIGH`, `매우높음` → 0.90 (90%)

### 2. 백엔드 변환 (`api/routers/data.py`)

Excel 로드 시 문자열을 숫자로 변환:

```python
from common.situation_converter import SituationInfoConverter

# 위협수준 정규화 (문자열 "HIGH", "MEDIUM", "LOW" 등을 숫자로 변환)
normalized, raw_val, label = SituationInfoConverter.normalize_threat_level(threat_level_raw)
threat_level_normalized = str(raw_val)  # 0-100 범위의 정수 문자열
```

### 3. 프론트엔드 컴포넌트 적용

모든 컴포넌트에서 통합 파서 사용:

#### `SituationInputPanel.tsx`
- 위협 선택 시 `parseThreatLevel()` 사용하여 정규화된 값 저장

#### `CommandControlPage.tsx`
- 정황보고 생성 시 `parseThreatLevel()` 사용

#### `TacticalMap.tsx`
- 위협마커 생성 시 `parseThreatLevel()` 사용

#### `SituationSummaryPanel.tsx`
- 상황요약 표시 시 `parseThreatLevel()` 사용

## 데이터 형식

### 입력 형식 (다양한 형식 지원)

1. **문자열 레이블:**
   - `"HIGH"`, `"MEDIUM"`, `"LOW"`
   - `"높음"`, `"중간"`, `"낮음"`
   - `"H"`, `"M"`, `"L"`

2. **숫자 (0-1 범위):**
   - `0.85`, `0.60`, `0.30`

3. **숫자 (0-100 범위):**
   - `85`, `60`, `30`
   - `"85"`, `"60"`, `"30"`

4. **백분율 문자열:**
   - `"85%"`, `"60%"`, `"30%"`

### 출력 형식 (통일)

```typescript
{
    normalized: 0.85,  // 0-1 범위 (계산용)
    percent: 85,        // 0-100 범위 (표시용)
    label: "HIGH",      // 레이블 (표시용)
    raw: "HIGH"         // 원본 값 (디버깅용)
}
```

## 적용 위치

### 백엔드
- ✅ `api/routers/data.py`: Excel 로드 시 변환
- ✅ `common/situation_converter.py`: 기존 변환 로직 활용

### 프론트엔드
- ✅ `frontend/src/lib/threat-level-parser.ts`: 통합 파서 (신규)
- ✅ `frontend/src/components/SituationInputPanel.tsx`: 위협 선택 시
- ✅ `frontend/src/pages/CommandControlPage.tsx`: 정황보고 생성 시
- ✅ `frontend/src/components/TacticalMap.tsx`: 위협마커 표시 시
- ✅ `frontend/src/components/SituationSummaryPanel.tsx`: 상황요약 표시 시

## 결과

이제 모든 컴포넌트가 동일한 파서를 사용하여:
1. **문자열 "HIGH", "MEDIUM", "LOW"** 처리 가능
2. **숫자 (0-1 또는 0-100)** 처리 가능
3. **일관된 정규화** (항상 0-1 범위로 변환)
4. **일관된 표시** (모든 컴포넌트에서 동일한 값 표시)

## 향후 개선 사항

1. **백엔드 스키마 정리:**
   - `ThreatEventBase.threat_level`의 타입을 명확히 정의
   - 문자열과 숫자 중 하나로 통일 고려

2. **데이터베이스 정규화:**
   - Excel 파일의 위협수준 컬럼을 숫자로 변환하여 저장
   - 또는 별도의 매핑 테이블 생성

3. **검증 로직 추가:**
   - API 응답 시 위협수준 형식 검증
   - 프론트엔드에서도 입력 검증 강화
