# COP 시각화 - 방책 중심 시각화 개선

## 문제점 분석

### 현재 상태
1. ❌ 추천 방책 선정 시 모든 임무 마커가 COP에 표시됨
2. ❌ 선택된 방책의 아군 부대 및 대응 방향이 제대로 시각화되지 않음
3. ❌ 모든 방책의 부대가 동시에 표시되어 혼란스러움

### 원인
- `missions` 배열의 마커가 방책과 무관하게 항상 표시됨
- `selectedCOA`가 선택되어도 모든 방책의 부대가 표시됨
- 방책 작전 경로 및 영역도 모든 방책이 동시에 표시됨

## 수정 내용

### 1. missions 배열 마커 제거

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `missions` 배열에서 아군 부대 마커를 생성하는 로직 제거
- 대신 `coaRecommendations`의 `unit_positions`만 사용

```typescript
// missions 배열의 마커는 제거 (방책의 부대만 표시)
// 대신 coaRecommendations의 unit_positions를 사용
```

### 2. 선택된 방책의 부대만 표시

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedCOA`가 있으면 선택된 방책의 부대만 표시
- `selectedCOA`가 없으면 모든 방책의 부대 표시 (방책별 색상 구분)

```typescript
{layerToggle.friendlyUnits && coaRecommendations
    .filter((coa) => {
        // selectedCOA가 있으면 선택된 방책만 표시
        if (selectedCOA) {
            return coa.coa_id === selectedCOA.coa_id;
        }
        // selectedCOA가 없으면 모든 방책 표시
        return true;
    })
    .flatMap((coa) => {
        // 부대 마커 생성
    })}
```

### 3. 선택된 방책의 작전 경로만 표시

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedCOA`가 있으면 선택된 방책의 작전 경로만 표시

```typescript
{layerToggle.coaPaths && coaRecommendations
    .filter(coa => {
        // selectedCOA가 있으면 선택된 방책만 표시
        if (selectedCOA) {
            if (coa.coa_id !== selectedCOA.coa_id) {
                return false;
            }
        }
        // 작전 경로 데이터 확인
        const operationalPath = (coa as any).visualization_data?.operational_path || (coa as any).operational_path;
        return operationalPath && operationalPath.waypoints && Array.isArray(operationalPath.waypoints) && operationalPath.waypoints.length >= 2;
    })
```

### 4. 선택된 방책의 작전 영역만 표시

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedCOA`가 있으면 선택된 방책의 작전 영역만 표시

```typescript
{layerToggle.coaAreas && coaRecommendations
    .filter(coa => {
        // selectedCOA가 있으면 선택된 방책만 표시
        if (selectedCOA) {
            if (coa.coa_id !== selectedCOA.coa_id) {
                return false;
            }
        }
        // 작전 영역 데이터 확인
        const operationalArea = (coa as any).visualization_data?.operational_area || (coa as any).operational_area;
        return operationalArea && (
            (operationalArea.deployment_area?.polygon) ||
            (operationalArea.engagement_area?.polygon) ||
            (operationalArea.polygon)
        );
    })
```

### 5. 선택된 방책 중심으로 지도 이동

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedCOA`가 있으면 선택된 방책의 부대 위치 중심으로 지도 이동

```typescript
// selectedCOA가 있으면 선택된 방책의 부대 위치 중심으로 이동
if (selectedCOA && !selectedMarker) {
    const selectedCOAUnits = coaRecommendations
        .filter(coa => coa.coa_id === selectedCOA.coa_id)
        .flatMap(coa => {
            const unitPositions = (coa as any).unit_positions;
            if (!unitPositions || !unitPositions.features || unitPositions.features.length === 0) {
                return [];
            }
            return unitPositions.features
                .map((feature: any) => {
                    if (!feature.geometry || !feature.geometry.coordinates) {
                        return null;
                    }
                    const [lng, lat] = feature.geometry.coordinates;
                    return [lat, lng] as LatLngExpression;
                })
                .filter(Boolean);
        });
    
    if (selectedCOAUnits.length > 0) {
        // 부대 위치들의 중심점 계산
        const avgLat = selectedCOAUnits.reduce((sum, pos) => sum + pos[0], 0) / selectedCOAUnits.length;
        const avgLng = selectedCOAUnits.reduce((sum, pos) => sum + pos[1], 0) / selectedCOAUnits.length;
        mapCenter = [avgLat, avgLng];
    }
}
```

### 6. 부대 마커 정보 개선

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- 부대 마커 팝업에 제대, 병종, 전투력 정보 추가
- 선택된 방책의 부대는 더 크게 표시

```typescript
<Popup>
    <div className="p-2 min-w-[200px]">
        <h4 className="font-bold text-sm mb-1">{coa.coa_name || coa.coa_id}</h4>
        <p className="text-xs text-gray-600 dark:text-gray-400 font-semibold">{unitName}</p>
        {feature.properties?.제대 && (
            <p className="text-[10px] text-gray-500 mt-1">제대: {feature.properties.제대}</p>
        )}
        {feature.properties?.병종 && (
            <p className="text-[10px] text-gray-500">병종: {feature.properties.병종}</p>
        )}
        {feature.properties?.전투력지수 && (
            <p className="text-[10px] text-blue-600 dark:text-blue-400 mt-1">
                전투력: {feature.properties.전투력지수}
            </p>
        )}
        <p className="text-[10px] text-gray-500 mt-1">Rank {coa.rank}</p>
        {isSelected && (
            <p className="text-[10px] text-red-600 dark:text-red-400 mt-1 font-bold border-t pt-1">
                ⭐ 선택된 방책
            </p>
        )}
    </div>
</Popup>
```

## 시각화 우선순위

1. **selectedCOA가 있는 경우**:
   - 선택된 방책의 부대만 표시
   - 선택된 방책의 작전 경로만 표시
   - 선택된 방책의 작전 영역만 표시
   - 선택된 방책의 부대 위치 중심으로 지도 이동

2. **selectedCOA가 없는 경우**:
   - 모든 방책의 부대 표시 (방책별 색상 구분)
   - 모든 방책의 작전 경로 표시
   - 모든 방책의 작전 영역 표시

## 테스트 방법

### 1. 방책 선택 테스트
1. COA 생성 후 방책 선택
2. 선택된 방책의 부대만 표시되는지 확인
3. 선택된 방책의 작전 경로만 표시되는지 확인
4. 선택된 방책의 작전 영역만 표시되는지 확인
5. 지도 중심이 선택된 방책의 부대 위치로 이동하는지 확인

### 2. 방책 해제 테스트
1. 방책 선택 해제
2. 모든 방책의 부대가 표시되는지 확인
3. 모든 방책의 작전 경로가 표시되는지 확인
4. 모든 방책의 작전 영역이 표시되는지 확인

### 3. 부대 정보 테스트
1. 부대 마커 클릭
2. 팝업에 제대, 병종, 전투력 정보가 표시되는지 확인
3. 선택된 방책의 부대는 "선택된 방책" 표시가 있는지 확인

## 예상 결과

- ✅ 선택된 방책의 아군 부대만 표시
- ✅ 선택된 방책의 작전 경로만 표시
- ✅ 선택된 방책의 작전 영역만 표시
- ✅ 선택된 방책의 부대 위치 중심으로 지도 이동
- ✅ 부대 마커에 상세 정보 표시
- ✅ 모든 임무 마커 제거 (방책 중심 시각화)

## 참고 사항

- `missions` 배열의 마커는 더 이상 표시되지 않습니다.
- 방책의 부대 정보는 `coaRecommendations`의 `unit_positions` GeoJSON에서 가져옵니다.
- `selectedCOA`가 없으면 모든 방책의 정보가 표시되지만, 방책별로 색상이 구분됩니다.
