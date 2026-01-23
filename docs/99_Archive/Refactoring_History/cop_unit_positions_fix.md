# COP 시각화 - unit_positions 생성 및 표시 수정

## 문제점

추천 방책을 선택했을 때 시각화되는 것이 없음

### 원인 분석
1. 백엔드에서 `unit_positions` GeoJSON을 생성하는 로직이 없음
2. COA 응답에 `unit_positions` 필드가 포함되지 않음
3. 프론트엔드에서 `unit_positions`가 없을 때 대체 로직 부재

## 수정 내용

### 1. 백엔드: unit_positions GeoJSON 생성 함수 추가

**파일**: `core_pipeline/visualization_generator.py`

**변경 사항**:
- `generate_unit_positions_geojson()` 함수 추가
- `friendly_units` 배열을 GeoJSON FeatureCollection 형식으로 변환

```python
def generate_unit_positions_geojson(
    self,
    friendly_units: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    아군 부대 위치 GeoJSON 생성
    
    Args:
        friendly_units: 참여 아군 부대 목록
        
    Returns:
        GeoJSON FeatureCollection 또는 None
    """
    try:
        features = []
        
        for unit in friendly_units:
            # 부대 위치 조회
            position = self._get_unit_position(unit)
            if not position:
                continue
            
            # GeoJSON Feature 생성
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": position  # [lng, lat]
                },
                "properties": {
                    "unit_id": unit.get("unit_id", ""),
                    "unit_name": unit.get("부대명", unit.get("unit_name", "")),
                    "제대": unit.get("제대", unit.get("unit_level", "")),
                    "병종": unit.get("병종", unit.get("unit_type", "")),
                    "전투력지수": unit.get("전투력지수", unit.get("combat_power", 0)),
                    "배치지형셀ID": unit.get("배치지형셀ID", ""),
                    "배치축선ID": unit.get("배치축선ID", ""),
                }
            }
            features.append(feature)
        
        if not features:
            return None
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    except Exception as e:
        logger.warning(f"Failed to generate unit positions GeoJSON: {e}")
        return None
```

### 2. 백엔드: COA 응답에 unit_positions 추가

**파일**: `api/routers/coa.py`

**변경 사항**:
- `generate_unit_positions_geojson()` 호출
- COA 응답에 `unit_positions` 필드 추가

```python
# 아군 부대 위치 GeoJSON 생성
unit_positions_geojson = viz_generator.generate_unit_positions_geojson(friendly_units)

# COASummary 생성 (시각화 데이터 포함)
coa_summary_dict = {
    # ... 기존 필드들
}

# unit_positions GeoJSON 추가
if unit_positions_geojson:
    coa_summary_dict["unit_positions"] = unit_positions_geojson

coas_summary.append(COASummary(**coa_summary_dict))
```

### 3. 프론트엔드: 디버깅 로그 추가

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `unit_positions`가 없을 때 콘솔 경고 로그 추가
- `operational_path`가 없을 때 콘솔 경고 로그 추가
- `operational_area`가 없을 때 콘솔 경고 로그 추가

```typescript
// unit_positions가 없는 경우 디버깅 로그
if (selectedCOA && coa.coa_id === selectedCOA.coa_id) {
    console.warn(`[TacticalMap] unit_positions가 없습니다. COA: ${coa.coa_id}`, {
        coa_id: coa.coa_id,
        coa_name: coa.coa_name,
        has_unit_positions: !!unitPositions,
        unit_positions_type: typeof unitPositions,
        unit_positions_keys: unitPositions ? Object.keys(unitPositions) : []
    });
}
```

## 데이터 구조

### unit_positions GeoJSON 형식

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [127.0, 37.5]  // [lng, lat]
      },
      "properties": {
        "unit_id": "UNIT001",
        "unit_name": "1사단",
        "제대": "사단",
        "병종": "기계화보병",
        "전투력지수": 85,
        "배치지형셀ID": "CELL001",
        "배치축선ID": "AXIS01"
      }
    }
  ]
}
```

## 테스트 방법

### 1. 백엔드 테스트
1. COA 생성 API 호출
2. 응답에서 `unit_positions` 필드 확인
3. `unit_positions.features` 배열 확인
4. 각 feature의 `geometry.coordinates` 확인

### 2. 프론트엔드 테스트
1. COA 생성 후 방책 선택
2. 브라우저 콘솔에서 경고 로그 확인
3. 지도에 부대 마커가 표시되는지 확인
4. 부대 마커 클릭 시 팝업 정보 확인

### 3. 데이터 검증
1. `friendly_units` 배열에 부대 정보가 있는지 확인
2. 각 부대의 `좌표정보` 또는 `배치지형셀ID` 확인
3. 좌표가 제대로 파싱되는지 확인

## 예상 결과

- ✅ 백엔드에서 `unit_positions` GeoJSON 생성
- ✅ COA 응답에 `unit_positions` 필드 포함
- ✅ 프론트엔드에서 `unit_positions`를 사용하여 부대 마커 표시
- ✅ 선택된 방책의 부대만 표시
- ✅ 부대 마커에 제대, 병종, 전투력 정보 표시

## 문제 해결 체크리스트

### 백엔드
- [ ] `generate_unit_positions_geojson()` 함수가 제대로 작동하는지 확인
- [ ] `friendly_units` 배열에 부대 정보가 포함되어 있는지 확인
- [ ] 각 부대의 좌표가 제대로 조회되는지 확인
- [ ] COA 응답에 `unit_positions` 필드가 포함되는지 확인

### 프론트엔드
- [ ] API 응답에서 `unit_positions` 필드를 받는지 확인
- [ ] `unit_positions.features` 배열을 제대로 파싱하는지 확인
- [ ] 부대 마커가 지도에 표시되는지 확인
- [ ] 선택된 방책의 부대만 표시되는지 확인

## 참고 사항

- `unit_positions`는 GeoJSON FeatureCollection 형식입니다.
- 각 feature의 `geometry.coordinates`는 `[lng, lat]` 형식입니다.
- 프론트엔드에서 Leaflet에 표시할 때는 `[lat, lng]`로 변환해야 합니다.
- 좌표가 없는 부대는 `unit_positions`에 포함되지 않습니다.
