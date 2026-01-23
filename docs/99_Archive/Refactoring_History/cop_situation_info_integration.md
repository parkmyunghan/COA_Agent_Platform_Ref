# COP 시각화 - situationInfo 통합 개선

## 문제점 분석

### 현재 상태
1. ✅ 정황보고 내용은 `situationInfo` 변경 시 즉시 반영됨
2. ❌ COP 시각화는 `situationInfo` 변경 시 제대로 반영되지 않음

### 원인
- `TacticalMap` 컴포넌트가 `threats` 배열만 사용하여 위협 표시
- `situationInfo`에 위협 정보가 있어도 `threats` 배열에 없으면 표시되지 않음
- `situationInfo`의 좌표 정보가 지도에 반영되지 않음
- `situationInfo` 변경 시 지도 중심 이동이 안됨

## 수정 내용

### 1. TacticalMap에 situationInfo prop 추가

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `TacticalMapProps`에 `situationInfo?: any` 추가
- `situationInfo`에서 위협 정보 직접 추출하여 표시

```typescript
interface TacticalMapProps {
    // ... 기존 props
    situationInfo?: any; // 상황 정보 (위협 정보 포함)
}
```

### 2. situationInfo에서 위협 정보 추출 및 표시

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `situationInfo`에 위협 정보가 있으면 `threats` 배열과 독립적으로 표시
- `situationInfo`의 좌표 정보를 우선적으로 사용

```typescript
// situationInfo에서 위협 정보 추출 (threats 배열에 없어도 표시)
const situationThreat: any = situationInfo && (situationInfo.selected_threat_id || situationInfo.threat_id || situationInfo.위협ID) ? {
    threat_id: situationInfo.selected_threat_id || situationInfo.threat_id || situationInfo.위협ID || `situation-${Date.now()}`,
    threat_type_code: situationInfo.threat_type || situationInfo.위협유형 || situationInfo.threat_type_code || 'UNKNOWN',
    threat_level: situationInfo.threat_level || (situationInfo.위협수준 ? parseFloat(String(situationInfo.위협수준)) / 100 : undefined) || 0.7,
    location_cell_id: situationInfo.location_cell_id || situationInfo.발생위치셀ID,
    좌표정보: situationInfo.좌표정보 || (situationInfo.longitude && situationInfo.latitude ? `${situationInfo.longitude},${situationInfo.latitude}` : undefined),
    raw_report_text: situationInfo.description || situationInfo.raw_report_text || situationInfo.발생장소 || situationInfo.location,
    ...situationInfo
} : null;

// 위협 목록 구성: situationInfo의 위협이 있으면 우선, 없으면 threats 배열 사용
const threatsToDisplay = situationThreat 
    ? [situationThreat] 
    : (selectedThreat ? threats.filter(t => t.threat_id === selectedThreat.threat_id) : threats);
```

### 3. 좌표 해결 우선순위 개선

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- 좌표 해결 우선순위: `좌표정보` → `latitude/longitude` → `location_cell_id` → 기본 위치

```typescript
// 위치 해결 (우선순위: 좌표정보 → latitude/longitude → location_cell_id → 기본 위치)
let position: LatLngExpression | null = null;

// 1. 좌표정보 직접 파싱
const coordStr = (t as any).좌표정보;
if (coordStr) {
    const parsed = parseCoordinates(coordStr);
    if (parsed) {
        position = parsed;
    }
}

// 2. latitude/longitude 직접 사용
if (!position && (t as any).latitude && (t as any).longitude) {
    position = [(t as any).latitude, (t as any).longitude];
}

// 3. location_cell_id 기반 조회 (TODO: 실제 지형셀 조회)
if (!position && t.location_cell_id) {
    // TODO: 지형셀에서 좌표 조회
    position = [37.8 + idx * 0.1, 127.2 + idx * 0.1];
}

// 4. 기본 위치 (Mock)
if (!position) {
    position = [37.8 + idx * 0.1, 127.2 + idx * 0.1];
}
```

### 4. 지도 중심 자동 이동

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `situationInfo`에 좌표가 있으면 지도 중심을 해당 위치로 자동 이동

```typescript
// Calculate center based on selected threat or situationInfo
const selectedMarker = markers.find(m => m.selected);
let mapCenter = selectedMarker ? selectedMarker.position : DEFAULT_CENTER;

// situationInfo에 좌표가 있으면 지도 중심을 해당 위치로 이동
if (situationInfo && !selectedMarker) {
    if (situationInfo.latitude && situationInfo.longitude) {
        mapCenter = [situationInfo.latitude, situationInfo.longitude];
    } else if (situationInfo.좌표정보) {
        const parsed = parseCoordinates(situationInfo.좌표정보);
        if (parsed) {
            mapCenter = parsed;
        }
    }
}
```

### 5. CommandControlPage에서 situationInfo 전달

**파일**: `frontend/src/pages/CommandControlPage.tsx`

**변경 사항**:
- `TacticalMap`에 `situationInfo` prop 전달

```typescript
<TacticalMap
    // ... 기존 props
    situationInfo={situationInfo}
/>
```

## 지원하는 situationInfo 필드

### 위협 정보 필드
- `selected_threat_id` / `threat_id` / `위협ID`: 위협 ID
- `threat_type` / `위협유형` / `threat_type_code`: 위협 유형 코드
- `threat_level` / `위협수준`: 위협 수준 (0.0~1.0 또는 0~100)
- `location_cell_id` / `발생위치셀ID`: 발생 위치 셀 ID
- `좌표정보`: 좌표 문자열 ("경도,위도")
- `latitude` / `longitude`: 위도/경도
- `description` / `raw_report_text` / `발생장소` / `location`: 위협 설명

### 위치 정보 필드
- `latitude` / `longitude`: 위도/경도
- `좌표정보`: 좌표 문자열 ("경도,위도")
- `location` / `발생장소`: 위치 이름

## 테스트 방법

### 1. 상황정보 입력 테스트
1. SituationInputPanel에서 위협 선택 또는 수동 입력
2. 지도에 선택된 위협이 즉시 표시되는지 확인
3. 위협 마커에 펄스 효과 확인
4. 위협 영향 범위 표시 확인
5. 지도 중심이 위협 위치로 이동하는지 확인

### 2. 좌표 정보 테스트
1. `situationInfo`에 `latitude`/`longitude` 설정
2. 지도에 위협이 해당 좌표에 표시되는지 확인
3. `situationInfo`에 `좌표정보` 문자열 설정
4. 지도에 위협이 해당 좌표에 표시되는지 확인

### 3. 위협 수준 테스트
1. `situationInfo`에 `위협수준` 설정 (0~100)
2. 위협 영향 범위 색상이 수준에 맞게 표시되는지 확인
3. `situationInfo`에 `threat_level` 설정 (0.0~1.0)
4. 위협 영향 범위 색상이 수준에 맞게 표시되는지 확인

## 예상 결과

- ✅ `situationInfo` 변경 시 위협 정보가 즉시 지도에 표시
- ✅ `situationInfo`의 좌표 정보가 지도에 반영
- ✅ `situationInfo` 변경 시 지도 중심이 위협 위치로 자동 이동
- ✅ `threats` 배열에 없어도 `situationInfo`의 위협 정보 표시
- ✅ 정황보고와 COP 시각화가 동기화됨

## 참고 사항

- `situationInfo`의 위협 정보는 `threats` 배열보다 우선적으로 표시됩니다.
- `situationInfo`에 위협 정보가 없으면 기존처럼 `threats 배열을 사용합니다.
- `selectedThreat`가 있으면 선택된 위협만 표시됩니다.
