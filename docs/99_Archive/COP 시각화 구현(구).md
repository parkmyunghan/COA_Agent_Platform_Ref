# Role: Defense Geospatial UI & Offline Systems Expert

# Objective: 
온톨로지 기반 방책 추천 에이전트의 결과를 시각화하기 위한 '한반도 전술 지도 대시보드'를 구축한다. 팔란티어 AIP와 유사한 다크 모드 기반의 고성능 UI를 지향하며, **인터넷이 차단된 폐쇄망 환경**에서도 로컬 데이터를 통해 완벽히 동작해야 한다.

# 고려사항
- 아래 내용들은 절대적인 기준이 아니며, 현재 구현 중인 시스템의 구조를 분석하여 적용에 무리가 있거나 더 나은 방향이 있다면 먼저 추천하여 동의 여부 확인 후 그 방향으로 구현하며 md 파일도 업데이트한다.
- 폐쇄망 환경을 최우선으로 고려하여 외부 CDN이나 외부 타일 서버(Google, OSM 등) 호출 코드는 모두 로컬 참조로 대체한다.

# Technical Stack:
- **Frontend**: React.js
- **Map Library**: MapLibre GL JS (벡터 타일 지원 및 오프라인 스타일링 최적화) 또는 Leaflet.js
- **Map Data (Local)**: 
    - Base Map: 로컬 서버(`http://localhost:8080`)에서 서빙되는 한반도 `.mbtiles` 또는 `GeoJSON`
    - Terrain: 로컬 SRTM(고도 데이터) 기반의 지형 정보
- **Symbols**: `milsymbol.js` (MIL-STD-2525D 표준 부호 라이브러리 로컬 연동)
- **Data Format**: GeoJSON (적/아군 위치, 위협 반경, 방책 기동 경로)

# Task Instructions:

## 1. 오프라인 베이스 맵 설정
- [x] 외부 네트워크 연결 없이 로컬 디렉토리의 지도 데이터를 로드한다. (`scripts/serve_offline_map.py`)
    - *Note: `korea.mbtiles` 부재 시 `korea_provinces.geojson` 자동 폴백 구현 완료*
- [x] 한반도 전역(33~39°N, 124~131°E)을 초기 뷰로 설정한다.
- [x] 로컬 스타일 JSON 파일을 사용하여 팔란티어 AIP 특유의 다크 모드(Dark Tactical) 테마를 적용한다.


## 2. 군대 부호 및 자산 표시 (milsymbol)
- `milsymbol` 라이브러리를 사용하여 아군(Blue, 사각형)과 적군(Red, 다이아몬드)의 위치를 지도에 마커로 표시한다.
- 각 유닛 클릭 시 온톨로지 속성(부대명, 상태, 현재 임무, 추론 근거)을 우측 사이드 패널(Side Panel)에 출력한다.

## 3. 위협 상황(Threat Zone) 시각화
- 적의 미사일 사거리나 감시 범위를 반투명한 빨간색 원(Circle) 또는 부채꼴로 렌더링한다.
- 위협 강도(Lethality)에 따라 그라데이션 효과를 적용하며, 필요시 애니메이션(Pulse 효과)을 추가한다.

## 4. 방책(COA) 가시화 및 시뮬레이션
- 에이전트가 추천한 '최적 기동 경로'를 전술 화살표(Tactical Polyline)로 지도 위에 그린다.
- 공격 방향(Axis of Advance)을 보여주는 화살표 머리를 포함한다.
- '방책 실행' 버튼 클릭 시, 하단 타임라인 슬라이더와 연동하여 부대 아이콘이 경로를 따라 이동하는 애니메이션을 구현한다.

## 5. UI Layout (Palantir AIP Style)
- **좌측 상단**: 실시간 상황 요약 및 주요 경보(Critical Alerts).
- **하단**: 시점별 상황 변화를 제어하고 확인할 수 있는 타임라인 슬라이더.
- **우측 상단**: 에이전트의 방책 추천 근거(Reasoning Log) 및 온톨로지 추론 경로 시각화창.

# Output:
- 위 기능을 포함하는 `OfflineTacticalMap.jsx` 컴포넌트와 필요한 CSS 코드를 작성한다.
- 샘플 데이터(JSON)를 포함하여 오프라인 환경에서 즉시 시뮬레이션이 가능한 형태로 작성한다.
- 로컬 지도 데이터를 웹 UI에 서빙하기 위한 간단한 백엔드(Python/FastAPI 등) 가이드를 포함한다.

# 참고사항
- 팔란티어 AIP의 UI 및 인터랙션 참고: https://youtu.be/XEM5qz__HOU
