# COP 시각화 데이터 매핑 및 레이어 가이드

## 1. 개요 및 문제 해결 (좌표 매핑 전략)

현재 온톨로지(데이터베이스)에는 시각화를 위한 **물리적 좌표(위도/경도)**가 포함되어 있지 않습니다. 그러나 COP(전술상황도)는 반드시 공간 정보를 필요로 합니다.
이를 해결하기 위해 **`ScenarioMapper`** 를 통한 **"의미 기반 좌표 매핑(Semantic Coordinate Mapping)"** 전략을 사용합니다.

### 1-1. 매핑 전략 (ScenarioMapper 역할)

시스템은 온톨로지에서 넘어온 논리적 객체(Threat, Unit 등)를 다음 우선순위에 따라 물리적 좌표로 변환합니다.

1.  **1순위: 명시적 좌표 (Explicit Coordinates)**
    *   입력 데이터에 `location: { lat: ..., lng: ... }` 또는 `MGRS` 좌표가 있는 경우 최우선 사용.
2.  **2순위: 지정된 위치명 매핑 (Gazetteer Lookup)**
    *   데이터의 `name`, `description`, `발생장소` 필드에 포함된 **지명 키워드**를 `LOCATION_DB`에서 검색하여 매핑.
    *   예: "평양 미사일 기지" -> "평양" 키워드 감지 -> `LOCATION_DB["PYONGYANG"]` 좌표 할당.
3.  **3순위: 기본값 및 랜덤 분산 (Fallback with Jitter)**
    *   위치를 특정할 수 없는 경우, 기본 위치(예: 평양)를 중심으로 **랜덤 오프셋(Jitter)**을 적용하여 객체 겹침 방지.

### 1-2. 개발자 및 온톨로지 설계자 가이드

지도가 정확하게 표시되게 하려면 다음 두 가지 방법 중 하나를 따르십시오.

#### A. 온톨로지 인스턴스 명명 규칙 준수 (권장)
온톨로지 인스턴스의 `label` 또는 `description`에 `LOCATION_DB`에 등록된 **표준 지명**을 포함시키십시오.
*   **Good:** "제1군단_**개성**_전방지휘소" (-> 개성 좌표로 매핑됨)
*   **Bad:** "제1군단_지휘소" (-> 위치 불명, 기본값인 평양으로 매핑될 위험)

#### B. `ui/components/scenario_mapper.py`의 `LOCATION_DB` 확장
새로운 작전 지역이 필요할 경우, `ScenarioMapper` 클래스 내의 `LOCATION_DB` 딕셔너리에 좌표를 추가하십시오.

```python
LOCATION_DB = {
    # ... 기존 데이터 ...
    "KUMGANG": {"lat": 38.65, "lng": 128.05, "name": "금강산"},
    "NAMPO": {"lat": 38.72, "lng": 125.42, "name": "남포"},
}
```

---

## 2. 축선/지형셀 레이어 삽입 가이드 (기존)
- 기존 축선/지형셀 내용은 유지하되, 아래의 고급 레이어를 추가로 구현해야 합니다.

## 3. [고도화] Reasoning & Risk Layer 삽입 가이드 (NEW)

Palantir 스타일의 "설명 가능한 지도"를 구현하기 위해 **인과관계(Reasoning)**와 **위협수준(Risk)**을 시각화하는 전용 레이어를 추가합니다.

### 3-1. Reasoning Layer (Logical Links)
방책이 선택된 논리적 근거를 화살표로 연결하여 표시합니다. 단순한 부대 이동 경로와는 다릅니다.

*   **데이터 구조 (GeoJSON LineString):**
    *   `properties.type`: "REASONING_LINK"
    *   `properties.relation`: "threatens", "defends", "supports"
    *   `properties.link_style`: "curved", "dotted"

*   **구현 위치:** `renderTacticalLayers` 함수 내 축선 레이어 추가 직후

```javascript
// Reasoning Layer (논리적 연결선) 추가
if (copData.reasoningData && copData.reasoningData.features) {
    if (!map.getSource('reasoning-source')) {
        map.addSource('reasoning-source', { type: 'geojson', data: copData.reasoningData });
        
        map.addLayer({
            id: 'reasoning-links',
            type: 'line',
            source: 'reasoning-source',
            paint: {
                'line-color': '#ffffff',
                'line-width': 2,
                'line-dasharray': [2, 2], // 점선으로 표현 (논리적 연결임)
                'line-opacity': 0.6
            }
        });
        
        // 화살표 머리 (Symbol Layer) 추가 가능
    } else {
        map.getSource('reasoning-source').setData(copData.reasoningData);
    }
}
```

### 3-2. Risk Layer (Dynamic Heatmap)
특정 방책 수행 시 예상되는 위험 지역을 히트맵 또는 등고선 형태로 시각화합니다.

*   **데이터 구조 (GeoJSON Polygon/Heatmap):**
    *   `properties.risk_level`: 0.0 ~ 1.0 (높을수록 위험)
    *   `geometry`: 위협 반경 또는 영향권

*   **구현 위치:** `renderTacticalLayers` 함수 최상단 (다른 객체보다 아래에 그려져야 함)

```javascript
// Risk Layer (히트맵) 추가
if (copData.riskData) {
    if (!map.getSource('risk-source')) {
        map.addSource('risk-source', { type: 'geojson', data: copData.riskData });
        
        // Heatmap Layer 예시
        map.addLayer({
            id: 'risk-heatmap',
            type: 'heatmap',
            source: 'risk-source',
            paint: {
                'heatmap-weight': ['get', 'risk_level'],
                'heatmap-intensity': 1,
                'heatmap-color': [
                    'interpolate', ['linear'], ['heatmap-density'],
                    0, 'rgba(0,0,0,0)',
                    0.2, 'rgba(255,255,0,0.3)', // 노란색 (주의)
                    0.5, 'rgba(255,165,0,0.5)', // 주황색 (경고)
                    1.0, 'rgba(255,0,0,0.7)'    // 빨간색 (위험)
                ],
                'heatmap-radius': 30,
                'heatmap-opacity': 0.6
            }
        }, 'waterway-label'); // 지명 라벨 아래에 위치
    }
}
```

---


`ontology_aware_cop.py` 파일의 `renderTacticalLayers` 함수에 축선 레이어와 지형셀 레이어를 추가해야 합니다.

## 삽입 위치

`ui/components/ontology_aware_cop.py` 파일에서 다음 위치를 찾습니다:

```javascript
console.log("✅ 위협 마커 " + copData.threatData.features.length + "개 추가됨");
}
```

이 코드 바로 다음에 아래 코드를 삽입합니다.

## 삽입할 코드

`ui/components/cop_layer_additions.js` 파일의 내용을 Python f-string 형식으로 변환하여 삽입합니다.

### Python f-string 형식 변환 규칙

- JavaScript의 `{{` → Python f-string의 `{{{{`
- JavaScript의 `}}` → Python f-string의 `}}}}`
- JavaScript의 `'` → Python f-string에서 그대로 사용 (또는 `"` 사용)

## 삽입 방법

1. `ui/components/ontology_aware_cop.py` 파일을 엽니다.
2. `renderTacticalLayers` 함수 내부를 찾습니다 (약 2158번째 줄).
3. 위협 마커 추가 완료 후 (약 2217번째 줄) 다음 코드를 삽입합니다:

```python
                    // 축선 레이어 추가 (LineString)
                    if (copData.axesData && copData.axesData.features && copData.axesData.features.length > 0) {{
                        try {{
                            // 축선 GeoJSON 소스 추가
                            if (!map.getSource('axes-source')) {{
                                map.addSource('axes-source', {{
                                    type: 'geojson',
                                    data: copData.axesData
                                }});
                            }} else {{
                                map.getSource('axes-source').setData(copData.axesData);
                            }}
                            
                            // 축선 유형별 색상 매핑
                            const axisTypeColors = {{
                                '주공': '#ef4444',      // 빨간색 실선
                                '조공': '#f97316',      // 주황색 실선
                                '차단': '#eab308',      // 노란색 점선
                                '방어': '#3b82f6',      // 파란색 실선
                                '예비': '#6b7280'       // 회색 점선
                            }};
                            
                            // 각 축선별로 레이어 추가
                            copData.axesData.features.forEach(function(feature, index) {{
                                const axisType = feature.properties.axis_type || '주공';
                                const axisName = feature.properties.axis_name || '축선 ' + (index + 1);
                                const layerId = 'axis-layer-' + index;
                                const color = axisTypeColors[axisType] || '#ef4444';
                                const isDashed = (axisType === '차단' || axisType === '예비');
                                
                                if (!map.getLayer(layerId)) {{
                                    map.addLayer({{
                                        id: layerId,
                                        type: 'line',
                                        source: 'axes-source',
                                        filter: ['==', ['get', 'axis_uri'], feature.properties.axis_uri],
                                        paint: {{
                                            'line-color': color,
                                            'line-width': 3,
                                            'line-opacity': 0.8,
                                            'line-dasharray': isDashed ? [4, 4] : [1, 0]
                                        }}
                                    }});
                                    
                                    // 축선 라벨 추가
                                    if (!map.getLayer(layerId + '-label')) {{
                                        map.addLayer({{
                                            id: layerId + '-label',
                                            type: 'symbol',
                                            source: 'axes-source',
                                            filter: ['==', ['get', 'axis_uri'], feature.properties.axis_uri],
                                            layout: {{
                                                'text-field': axisName,
                                                'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                                                'text-size': 12,
                                                'text-offset': [0, 1.5],
                                                'text-anchor': 'top'
                                            }},
                                            paint: {{
                                                'text-color': color,
                                                'text-halo-color': '#000000',
                                                'text-halo-width': 2
                                            }}
                                        }});
                                    }}
                                }}
                            }});
                            
                            console.log("✅ 축선 레이어 " + copData.axesData.features.length + "개 추가됨");
                        }} catch (e) {{
                            console.warn("⚠️ 축선 레이어 추가 실패:", e.message);
                        }}
                    }}
                    
                    // 지형셀 레이어 추가 (Polygon)
                    if (copData.terrainCellsData && copData.terrainCellsData.features && copData.terrainCellsData.features.length > 0) {{
                        try {{
                            // 지형셀 GeoJSON 소스 추가
                            if (!map.getSource('terrain-cells-source')) {{
                                map.addSource('terrain-cells-source', {{
                                    type: 'geojson',
                                    data: copData.terrainCellsData
                                }});
                            }} else {{
                                map.getSource('terrain-cells-source').setData(copData.terrainCellsData);
                            }}
                            
                            // 기동성등급별 색상 매핑 (1=좋음, 5=나쁨)
                            const mobilityColors = {{
                                1: '#22c55e',  // 매우 좋음 - 밝은 녹색
                                2: '#84cc16',  // 좋음 - 연두색
                                3: '#eab308',  // 보통 - 노란색
                                4: '#f97316',  // 나쁨 - 주황색
                                5: '#ef4444'   // 매우 나쁨 - 빨간색
                            }};
                            
                            // 지형셀 Polygon 레이어 추가
                            if (!map.getLayer('terrain-cells-fill')) {{
                                map.addLayer({{
                                    id: 'terrain-cells-fill',
                                    type: 'fill',
                                    source: 'terrain-cells-source',
                                    filter: ['==', ['geometry-type'], 'Polygon'],
                                    paint: {{
                                        'fill-color': [
                                            'case',
                                            ['has', '기동성등급'],
                                            [
                                                'match',
                                                ['get', '기동성등급'],
                                                1, mobilityColors[1],
                                                2, mobilityColors[2],
                                                3, mobilityColors[3],
                                                4, mobilityColors[4],
                                                5, mobilityColors[5],
                                                '#6b7280'  // 기본값 - 회색
                                            ],
                                            '#6b7280'  // 기동성등급이 없으면 회색
                                        ],
                                        'fill-opacity': 0.3
                                    }}
                                }});
                            }}
                            
                            // 요충지 강조 테두리
                            if (!map.getLayer('terrain-cells-border')) {{
                                map.addLayer({{
                                    id: 'terrain-cells-border',
                                    type: 'line',
                                    source: 'terrain-cells-source',
                                    filter: ['==', ['geometry-type'], 'Polygon'],
                                    paint: {{
                                        'line-color': [
                                            'case',
                                            ['==', ['get', '요충지여부'], 'Y'],
                                            '#fbbf24',  // 요충지 - 노란색 강조
                                            '#6b7280'   // 일반 - 회색
                                        ],
                                        'line-width': [
                                            'case',
                                            ['==', ['get', '요충지여부'], 'Y'],
                                            3,  // 요충지 - 두꺼운 테두리
                                            1   // 일반 - 얇은 테두리
                                        ],
                                        'line-opacity': 0.8
                                    }}
                                }});
                            }}
                            
                            // 지형셀 라벨 추가
                            if (!map.getLayer('terrain-cells-label')) {{
                                map.addLayer({{
                                    id: 'terrain-cells-label',
                                    type: 'symbol',
                                    source: 'terrain-cells-source',
                                    layout: {{
                                        'text-field': ['get', 'terrain_name'],
                                        'text-font': ['Open Sans Regular', 'Arial Unicode MS'],
                                        'text-size': 10
                                    }},
                                    paint: {{
                                        'text-color': '#ffffff',
                                        'text-halo-color': '#000000',
                                        'text-halo-width': 1
                                    }}
                                }});
                            }}
                            
                            console.log("✅ 지형셀 레이어 " + copData.terrainCellsData.features.length + "개 추가됨");
                        }} catch (e) {{
                            console.warn("⚠️ 지형셀 레이어 추가 실패:", e.message);
                        }}
                    }}
```

## 참고

- `cop_layer_additions.js` 파일에 전체 코드가 있습니다.
- Python f-string 형식으로 변환할 때 중괄호를 이중으로 사용해야 합니다 (`{{` → `{{{{`).

