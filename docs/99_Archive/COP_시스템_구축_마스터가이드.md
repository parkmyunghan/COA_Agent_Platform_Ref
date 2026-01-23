# COP 시스템 구축 마스터 가이드

## 1. 시스템 철학 및 목표 (Project Philosophy)

본 시스템은 단순한 전술 지도 시각화 도구가 아닙니다. 
**Palantir AIP**와 경쟁할 수 있는, **온톨로지 추론 기반의 설명 가능한 작전 지휘 통제 플랫폼(Explainable Command & Control)**을 지향합니다.

### 1.1 핵심 가치: Object-Centric Operation
- **지도(Map)는 배경일 뿐:** 지도는 객체들이 활동하는 무대이며, 주인공은 **객체(Object)**입니다.
- **Live Objects:** 지도 위의 모든 마커는 백엔드 온톨로지(RDF Graph)의 인스턴스와 실시간으로 동기화된 "살아있는 객체"입니다.
- **Context over Content:** "무엇이 있는가"를 넘어 **"왜(Why) 거기에 있으며, 어떤 관계(Relationship)를 맺고 있는가"**를 보여줍니다.

---

## 2. 아키텍처 및 환경 (Architecture & Environment)

### 2.1 Hybrid Map Architecture
폐쇄망(Offline)과 인터넷망(Online) 환경을 모두 지원하는 하이브리드 구조를 채택합니다.

*   **Online Mode:** OpenStreetMap(OSM), CartoDB, ESRI Satellite 등 외부 타일 사용.
*   **Offline Mode:** 로컬 Tile Server에서 호스팅하는 **MBTiles (Vector Tiles)** 사용.
    *   **권장 기술:** `MapLibre GL JS` (Offline Vector Tile 표준 지원)
    *   **레거시 삭제:** 단순 이미지 폴더 로딩 방식은 폐기하고 MBTiles로 단일화.

### 2.2 Map Server (Local Tile Server)
*   **실행 파일:** `tools/map_server_osm.py`
*   **포트:** `8080`
*   **기능:**
    *   `/tiles/{z}/{x}/{y}`: MBTiles 벡터 타일 서빙
    *   `/maps/{filename}`: 공통 GeoJSON 데이터 서빙
    *   `/static/lib/`: 외부망 차단 시 필요한 JS/CSS 라이브러리 서빙
*   **자동 실행:** `run_streamlit.py` 실행 시 백그라운드 데몬으로 자동 구동되므로 별도 실행 불필요.

---

## 3. 데이터 전략: 온톨로지-좌표 매핑 (Data Strategy)

### 3.1 문제 정의
온톨로지(RDF)는 논리적 관계를 저장하지만, 시각화를 위한 물리적 좌표(위도/경도)가 없는 경우가 많습니다.

### 3.2 해결책: 의미 기반 좌표 매핑 (Semantic Coordinate Mapping)
`ui/components/scenario_mapper.py`의 `ScenarioMapper`를 통해 논리 객체를 물리 좌표로 변환합니다.

**매핑 우선순위:**
1.  **명시적 좌표:** 데이터에 `location` 필드가 있으면 최우선 사용.
2.  **지명(Gazetteer) 매핑:** 객체 이름/설명에 포함된 키워드(예: "평양", "개성")를 `LOCATION_DB`에서 조회.
3.  **랜덤 분산(Jitter):** 위치 불명확 시 기본 좌표(평양 등) 주변에 랜덤 산개 배치.

### 3.3 온톨로지 명명 규칙 가이드
데이터 입력 시 인스턴스 이름에 표준 지명을 포함할 것을 권장합니다.
*   **Good:** `제1군단_개성_전방지휘소` (->"개성" 좌표 매핑)
*   **Bad:** `제1군단_지휘소` (-> 위치 불명)

### 3.4 지형셀(Terrain Cell) 좌표 통합
정밀한 위치 표현을 위해 **지형셀 기반 좌표**를 지원합니다.
*   **방법:** `data_lake/지형셀.xlsx` 파일에 **`좌표정보`** 컬럼을 추가하고, `"경도, 위도"` (예: `127.5, 36.5`) 형식으로 입력합니다.
*   **효과:** 해당 지형셀에 위치한 위협/부대 정보는 온톨로지 로딩 시 자동으로 `hasLongitude`, `hasLatitude` 속성을 갖게 되며, 지도상에 정확한 위치로 표시됩니다. (`ScenarioMapper` 최우선 순위 적용)

---

## 4. 레이어 구현 가이드 (Implementation Guide)

### 4.1 기본 레이어 구조 (Web Stack)
*   **Frontend:** Streamlit + `components.html` (React + MapLibre GL JS)
*   **Backend:** Python (`ontology_aware_cop.py` -> `ScenarioMapper`)

### 4.2 주요 레이어 명세 (Palantir Style)

#### 1) Unit & Threat (Context Layer)
*   **표현:** Milsymbol (MIL-STD-2525D)
*   **인터랙션:** 클릭 시 **Object 360 View** 팝업 (정적 제원, 동적 상태, 상위 부대 연결).
*   **Contextual Highlight:** 특정 위협 선택 시 대응 가능한 아군 자산만 하이라이트.

#### 2) Reasoning Layer (Explainability)
"AI가 왜 이 방책을 추천했는가?"에 대한 시각적 답변입니다.
*   **형태:** 화살표, 점선 연결 (LineString)
*   **GeoJSON 속성:** `type="REASONING_LINK"`, `relation="threatens|defends"`
*   **스타일:**
    *   위협 관계: 빨간색 점선
    *   방어/지원 관계: 파란색/초록색 실선

#### 3) Risk Layer (Simulation)
방책 수행 시 예상되는 위험도를 시각화합니다.
*   **형태:** 히트맵 (Heatmap) 또는 등고선 (Polygon)
*   **GeoJSON 속성:** `properties.risk_level` (0.0 ~ 1.0)
*   **구현:** `heatmap-weight` 속성을 사용하여 동적으로 렌더링.

### 4.3 지도 초기화 및 옵션 코드 (HybridTacticalMap.jsx)
```javascript
// 오프라인 모드 감지 및 소스 설정
const tileStyle = offlineMode ? {
    version: 8,
    sources: {
        'offline-tiles': {
            type: 'vector',
            tiles: ['http://localhost:8080/tiles/{z}/{x}/{y}'], // Local Server
            minzoom: 0, maxzoom: 14
        }
    },
    layers: [
        // ... MBTiles 스타일 레이어 정의 ...
    ]
} : 'https://demotiles.maplibre.org/style.json'; // Online Style

const map = new maplibregl.Map({
    container: 'map',
    style: tileStyle,
    center: [127.5, 36.5],
    zoom: 7
});
```

---

## 5. 테스트 및 검증 (Verification)

### 5.1 필수 점검 항목
1.  **서버 구동:** `http://localhost:8080` 접속하여 "running" 메시지 확인.
2.  **타일 로딩:** 오프라인 모드에서 지도가 깨지지 않고 로드되는지 확인.
3.  **마커 표시:** 평양, 서울 등 주요 거점에 Unit/Threat 마커가 뜨는지 확인.
4.  **추론 시각화:** 방책 선택 시 화살표(Reasoning Link)가 논리적으로 타당하게 연결되는지 확인.

### 5.2 디버깅 팁
*   마커가 안 보일 때: `ScenarioMapper`의 `LOCATION_DB`에 해당 지명이 있는지 확인.
*   타일이 안 보일 때: `tools/map_server_osm.py` 콘솔 로그에서 404 에러 확인.

---

## 6. 결론
이 문서는 **"보여주기식 지도"에서 "생각하는 지도"로의 전환**을 선언합니다.
모든 개발 및 기획은 이 마스터 가이드의 철학(Object-Centric, Explainable)을 따라야 합니다.
