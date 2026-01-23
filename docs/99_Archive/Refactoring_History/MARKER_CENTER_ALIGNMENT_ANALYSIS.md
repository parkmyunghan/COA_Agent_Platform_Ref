# 마커-원형 위험영역 중앙 정렬 문제 근본 원인 분석

## 문제 현상

- ✅ **실제 데이터에서 위협 선택**: 마커와 원형 위험영역 중앙 정렬 정상
- ❌ **데모 시나리오 선택**: 마커와 원형 위험영역 중앙 정렬 불일치
- ❌ **수동 입력**: 동일한 문제 발생 가능
- ❌ **SITREP 텍스트 입력**: 동일한 문제 발생 가능

## 근본 원인 분석

### 1. 데이터 소스 차이

#### 실제 데이터 선택 시
```typescript
// TacticalMap.tsx line 214-215
if ((t as any).latitude !== undefined && (t as any).longitude !== undefined) {
    position = [(t as any).latitude, (t as any).longitude];  // ✅ 새 배열 생성
}
```
- `ThreatEventBase` 객체에서 직접 좌표 추출
- **매번 새 배열 생성** → 참조 독립성 보장
- Circle과 Marker가 동일한 값이지만 다른 참조 사용

#### 데모 시나리오/수동 입력/SITREP 시
```typescript
// TacticalMap.tsx line 169-176
const resolvedPos = resolveLocation(demoLocation) || ...;
const demoPosition: LatLngExpression = Array.isArray(resolvedPos)
    ? [resolvedPos[0] as number, resolvedPos[1] as number]  // ⚠️ 복사하지만...
    : resolvedPos;
```
- `resolveLocation()` 함수를 통해 좌표 변환
- `LOCATION_COORDINATES`에서 직접 배열 참조 반환 가능
- 복사를 하지만 **타이밍 이슈** 발생 가능

### 2. `resolveLocation()` 함수의 문제점

```typescript
// cop-visualization-utils.ts
const LOCATION_COORDINATES: Record<string, LatLngExpression> = {
    '경계지역': [37.95, 126.67],  // ⚠️ 직접 배열 참조
    ...
};

export function resolveLocation(location: string): LatLngExpression | null {
    if (LOCATION_COORDINATES[locationName]) {
        return LOCATION_COORDINATES[locationName];  // ⚠️ 원본 배열 참조 반환
    }
    return parseCoordinates(locationName);
}
```

**문제점**:
1. `LOCATION_COORDINATES`의 배열이 직접 반환됨
2. 여러 곳에서 같은 배열 참조를 사용할 수 있음
3. React의 렌더링 최적화로 인해 참조가 변경될 수 있음

### 3. 마커 생성 로직의 불일치

#### 실제 데이터 (line 214-215)
```typescript
position = [(t as any).latitude, (t as any).longitude];  // 항상 새 배열
```

#### 데모 시나리오 (line 174-176)
```typescript
const demoPosition: LatLngExpression = Array.isArray(resolvedPos)
    ? [resolvedPos[0] as number, resolvedPos[1] as number]  // 복사하지만...
    : resolvedPos;
```

**차이점**:
- 실제 데이터: 항상 새 배열 생성 (명시적)
- 데모 시나리오: 조건부 복사 (암묵적)
- 수동 입력/SITREP: 처리 로직 없음

### 4. Circle과 Marker의 position 동기화 문제

```typescript
// Circle 생성 (line 599-601)
const circleCenter: LatLngExpression = Array.isArray(marker.position) 
    ? [marker.position[0] as number, marker.position[1] as number] 
    : marker.position;

// Marker 생성 (line 668)
<Marker position={marker.position} ... />
```

**문제점**:
- Circle과 Marker가 **다른 시점**에 렌더링됨
- `marker.position`이 참조 타입이면 변경 가능
- React의 렌더링 최적화로 인해 참조가 달라질 수 있음

## 근본 원인 요약

1. **데이터 소스 차이**: 실제 데이터는 항상 새 배열 생성, 데모/수동/SITREP은 함수 반환값 사용
2. **참조 공유 문제**: `LOCATION_COORDINATES`의 배열이 직접 참조로 반환됨
3. **타이밍 이슈**: Circle과 Marker가 다른 렌더링 사이클에서 참조 사용
4. **일관성 부족**: 입력 방식별로 다른 좌표 처리 로직

## 해결 방안

### 방안 1: 통합 좌표 해결 함수 생성 (권장)

모든 입력 방식에서 동일한 좌표 해결 로직 사용:

```typescript
function resolveMarkerPosition(
    situationInfo: any,
    threatData?: ThreatEventBase
): LatLngExpression {
    // 1. 위도/경도 직접 제공 (최우선)
    if (situationInfo?.latitude && situationInfo?.longitude) {
        return [situationInfo.latitude, situationInfo.longitude];  // 새 배열
    }
    
    // 2. threatData에서 좌표 추출
    if (threatData?.latitude && threatData?.longitude) {
        return [threatData.latitude, threatData.longitude];  // 새 배열
    }
    
    // 3. 좌표정보 문자열 파싱
    const coordStr = situationInfo?.좌표정보 || threatData?.좌표정보;
    if (coordStr) {
        const parsed = parseCoordinates(coordStr);
        if (parsed) {
            return [parsed[0], parsed[1]];  // 새 배열로 복사
        }
    }
    
    // 4. 위치 이름 변환 (항상 새 배열 반환)
    const location = situationInfo?.location || situationInfo?.발생장소;
    if (location) {
        const resolved = resolveLocation(location);
        if (resolved) {
            return Array.isArray(resolved) 
                ? [resolved[0] as number, resolved[1] as number]  // 항상 새 배열
                : resolved;
        }
    }
    
    // 5. 기본 위치
    return [38.0, 127.0];  // DMZ 중앙
}
```

### 방안 2: `resolveLocation()` 함수 수정

항상 새 배열 반환하도록 수정:

```typescript
export function resolveLocation(location: string | undefined | null): LatLngExpression | null {
    if (!location) return null;
    
    const locationName = String(location).trim();
    if (LOCATION_COORDINATES[locationName]) {
        const coords = LOCATION_COORDINATES[locationName];
        // 항상 새 배열 반환 (참조 독립성 보장)
        return Array.isArray(coords) 
            ? [coords[0] as number, coords[1] as number]
            : coords;
    }
    
    const parsed = parseCoordinates(locationName);
    if (parsed) {
        // 파싱된 값도 새 배열로 반환
        return [parsed[0] as number, parsed[1] as number];
    }
    
    return null;
}
```

### 방안 3: 마커 생성 시 position 고정

마커 생성 시 position을 명시적으로 고정:

```typescript
// 마커 생성 시
const fixedPosition: LatLngExpression = Array.isArray(marker.position)
    ? [marker.position[0] as number, marker.position[1] as number]  // 항상 새 배열
    : marker.position;

newMarkers.push({
    ...marker,
    position: fixedPosition,  // 고정된 position 사용
});
```

## 권장 해결책

**방안 1 + 방안 2 조합**:
1. `resolveLocation()` 함수를 항상 새 배열 반환하도록 수정
2. 통합 좌표 해결 함수 생성하여 모든 입력 방식에서 일관된 처리
3. 마커 생성 시 position을 명시적으로 고정

이렇게 하면:
- 모든 입력 방식에서 동일한 로직 사용
- 참조 독립성 보장
- Circle과 Marker의 position 동기화 보장
