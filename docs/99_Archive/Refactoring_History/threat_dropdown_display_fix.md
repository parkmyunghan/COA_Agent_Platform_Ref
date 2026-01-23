# 위협 선택 콤보박스 표시 문제 수정

## 문제점 분석

### 현재 상태
- 콤보박스에 "THR001-미지정(NaN%)" 형식으로 표시됨
- 위협 유형이 "미지정"으로 표시됨
- 위협 수준이 "NaN%"로 표시됨

### 원인
1. **필드명 불일치**:
   - 프론트엔드: `threat.threat_type` 사용
   - 백엔드: `threat_type_code` 반환
   - 결과: `threat.threat_type`이 `undefined`이므로 '미지정' 표시

2. **위협 수준 파싱 문제**:
   - 백엔드에서 `threat_level`이 문자열로 반환될 수 있음 (예: "0.7", "70", "70%")
   - 프론트엔드에서 숫자 변환 없이 `Math.round()` 사용
   - 결과: `Math.round("0.7" * 100)` = `NaN`

3. **백엔드 응답 필드 누락**:
   - `threat_type_original`, `raw_report_text` 등 추가 정보가 응답에 포함되지 않음

## 수정 내용

### 1. 프론트엔드: 위협 유형 표시 로직 개선

**파일**: `frontend/src/components/SituationInputPanel.tsx`

**변경 사항**:
- `threat.threat_type` 대신 `threat.threat_type_code || threat.threat_type_original || threat.threat_type` 사용
- 우선순위: `threat_type_code` → `threat_type_original` → `threat_type` → '미지정'

```typescript
// 위협 유형 결정 (우선순위: threat_type_code → threat_type_original → threat_type → '미지정')
const threatType = threat.threat_type_code || threat.threat_type_original || (threat as any).threat_type || '미지정';
```

### 2. 프론트엔드: 위협 수준 파싱 로직 개선

**파일**: `frontend/src/components/SituationInputPanel.tsx`

**변경 사항**:
- 문자열 형식의 `threat_level` 파싱 로직 추가
- 백분율 형식 (100보다 큰 값) 처리
- NaN 방지

```typescript
// 위협 수준 파싱 (문자열일 수 있음)
let threatLevel: number = 0.7;
if (threat.threat_level !== undefined && threat.threat_level !== null) {
    if (typeof threat.threat_level === 'string') {
        // 문자열인 경우 파싱 (예: "0.7", "70", "70%")
        const cleaned = threat.threat_level.replace('%', '').trim();
        const parsed = parseFloat(cleaned);
        if (!isNaN(parsed)) {
            // 100보다 크면 백분율로 간주 (예: 70 -> 0.7)
            threatLevel = parsed > 1 ? parsed / 100 : parsed;
        }
    } else {
        threatLevel = typeof threat.threat_level === 'number' ? threat.threat_level : 0.7;
    }
}

const threatLevelPercent = Math.round(threatLevel * 100);
```

### 3. 프론트엔드: 위협 선택 시 데이터 매핑 개선

**파일**: `frontend/src/components/SituationInputPanel.tsx`

**변경 사항**:
- 위협 선택 시 올바른 필드명 사용
- 위협 수준 파싱 로직 적용
- 모든 관련 필드 매핑

```typescript
// 위협 유형 결정
const threatType = selectedThreat.threat_type_code || selectedThreat.threat_type_original || (selectedThreat as any).threat_type || '';

// 위협 수준 파싱
let threatLevel: number = 0.7;
if (selectedThreat.threat_level !== undefined && selectedThreat.threat_level !== null) {
    if (typeof selectedThreat.threat_level === 'string') {
        const cleaned = String(selectedThreat.threat_level).replace('%', '').trim();
        const parsed = parseFloat(cleaned);
        if (!isNaN(parsed)) {
            threatLevel = parsed > 1 ? parsed / 100 : parsed;
        }
    } else {
        threatLevel = typeof selectedThreat.threat_level === 'number' ? selectedThreat.threat_level : 0.7;
    }
}

updateSituation({
    selected_threat_id: threatId,
    threat_type: threatType,
    threat_type_code: selectedThreat.threat_type_code,
    threat_level: threatLevel,
    // ... 기타 필드
});
```

### 4. 백엔드: 추가 필드 반환

**파일**: `api/routers/data.py`

**변경 사항**:
- `ThreatEventBase` 응답에 추가 필드 포함
- `threat_type_original`, `raw_report_text` 등 포함

```python
threat_objs.append(ThreatEventBase(
    threat_id=threat_event.threat_id,
    threat_type_code=threat_event.threat_type_code,
    threat_level=threat_event.threat_level,
    related_axis_id=threat_event.related_axis_id,
    location_cell_id=threat_event.location_cell_id,
    occurrence_time=threat_event.occurrence_time,
    latitude=lat,
    longitude=lon,
    threat_type_original=threat_event.threat_type_original,
    raw_report_text=threat_event.raw_report_text,
    confidence=threat_event.confidence,
    status=threat_event.status,
    enemy_unit_original=threat_event.enemy_unit_original,
    remarks=threat_event.remarks
))
```

## 데이터 필드 매핑

### 백엔드 → 프론트엔드

| 백엔드 필드 | 프론트엔드 필드 | 우선순위 |
|------------|---------------|---------|
| `threat_type_code` | `threat_type_code` | 1 |
| `threat_type_original` | `threat_type_original` | 2 |
| `threat_type` (레거시) | `threat_type` | 3 |
| - | '미지정' | 4 (fallback) |

### 위협 수준 파싱 규칙

| 입력 형식 | 파싱 결과 | 예시 |
|----------|----------|------|
| `"0.7"` | `0.7` | 정상 |
| `"70"` | `0.7` (100으로 나눔) | 정상 |
| `"70%"` | `0.7` (%, 100으로 나눔) | 정상 |
| `0.7` (숫자) | `0.7` | 정상 |
| `null` / `undefined` | `0.7` (기본값) | 정상 |
| `"invalid"` | `0.7` (기본값) | 정상 |

## 테스트 방법

### 1. 콤보박스 표시 테스트
1. 상황정보 설정에서 "실제 데이터" 입력 방식 선택
2. "실제 데이터에서 위협 선택" 콤보박스 확인
3. 위협 목록이 올바른 형식으로 표시되는지 확인:
   - `THR001 - 미사일 (70%)` ✅
   - `THR001 - 미지정 (NaN%)` ❌ (수정 전)

### 2. 위협 선택 테스트
1. 콤보박스에서 위협 선택
2. 상황 정보가 올바르게 채워지는지 확인
3. 위협 유형과 위협 수준이 올바르게 표시되는지 확인

### 3. 데이터 검증
1. 브라우저 개발자 도구에서 API 응답 확인
2. `/api/v1/data/threats` 응답에서 필드 확인
3. `threat_type_code`, `threat_level` 값 확인

## 예상 결과

- ✅ 콤보박스에 올바른 위협 유형 표시 (예: "THR001 - 미사일 (70%)")
- ✅ 위협 수준이 올바르게 표시 (NaN% 없음)
- ✅ 위협 선택 시 상황 정보가 올바르게 채워짐
- ✅ 다양한 위협 수준 형식 지원 (문자열, 숫자, 백분율)

## 참고 사항

- `threat_level`은 백엔드에서 문자열로 반환될 수 있으므로 항상 파싱 필요
- `threat_type_code`가 없으면 `threat_type_original`을 사용
- 둘 다 없으면 '미지정' 표시 (데이터 품질 문제)
