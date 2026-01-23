# COP 시각화 구현 요약

## 구현 완료 사항

### Phase 1: 기본 시각화 (완료 ✅)

#### 1. 위협 영향 범위 (Circle) 시각화
- **파일**: `frontend/src/components/TacticalMap.tsx`
- **기능**:
  - 위협 수준에 따른 색상 매핑 (초록→노랑→주황→빨강)
  - 위협 유형별 반경 계산 (미사일: 10km, 포병: 8km, 기갑: 5km, 보병: 3km)
  - 위협 수준 가중치 적용
  - 반투명 원형 영역 표시
- **유틸리티**: `frontend/src/lib/cop-visualization-utils.ts`의 `createThreatInfluenceArea()`, `calculateThreatInfluenceRadius()`

#### 2. 아군 부대 마커 개선
- **기능**:
  - 방책별 색상 구분 (Rank 1: 파란색, Rank 2: 초록색, Rank 3: 보라색)
  - 선택된 방책의 부대는 빨간색 테두리 및 펄스 효과
  - MIL-STD-2525D 심볼 매핑 (제대 + 병종 기반)
- **유틸리티**: `determineFriendlySIDC()`, `getCOAColor()`

#### 3. 위협 마커 개선
- **기능**:
  - MIL-STD-2525D 심볼 매핑 (위협 유형 코드 기반)
  - 위협 수준 표시
  - 위치 해결 로직 (좌표정보 → 지형셀 → 축선 우선순위)
- **유틸리티**: `determineThreatSIDC()`, `parseCoordinates()`

### Phase 2: 경로 및 영역 (완료 ✅)

#### 1. 축선 라인 표시
- **기능**:
  - PRIMARY/SECONDARY/SUPPORT 타입별 스타일
  - PRIMARY: 진한 파란색, 실선, 3px
  - SECONDARY: 파란색, 점선, 2px
  - SUPPORT: 연한 파란색, 점선, 1px
  - 축선 라벨 표시 (중간 지점)
- **데이터 소스**: `axisStates` prop (COA 응답의 `axis_states`)
- **유틸리티**: `getAxisLineStyle()`

#### 2. 방책 작전 경로 (Polyline)
- **기능**:
  - 경로 타입별 스타일 (MOVEMENT/ATTACK/DEFENSE/SUPPORT)
  - 선택된 방책 강조 (두꺼운 선)
  - 방책별 색상 구분
- **데이터 소스**: `visualization_data.operational_path` 또는 `operational_path`
- **유틸리티**: `getPathStyle()`

#### 3. 방책 작전 영역 (Polygon)
- **기능**:
  - 배치 영역, 교전 영역 표시
  - 방책별 색상 구분
  - 선택된 방책 강조
- **데이터 소스**: `visualization_data.operational_area` 또는 `operational_area`

#### 4. 추론 경로 시각화
- **기능**: 기존 구현 유지 (온톨로지 기반 추론 경로 표시)

### Phase 3: 고급 기능 (부분 완료 ✅)

#### 1. 레이어 토글 기능
- **파일**: `frontend/src/components/LayerToggleControl.tsx`
- **기능**:
  - 위협 마커 표시/숨김
  - 위협 영향 범위 표시/숨김
  - 아군 부대 표시/숨김
  - 방책 작전 경로 표시/숨김
  - 방책 작전 영역 표시/숨김
  - 축선 표시/숨김
  - 추론 경로 표시/숨김
- **UI**: 지도 우측 상단에 토글 패널

#### 2. 타임라인 기반 동적 표시
- **상태**: 미구현 (향후 구현 예정)

## 구현된 파일 목록

### 새로 생성된 파일
1. `frontend/src/lib/cop-visualization-utils.ts`
   - COP 시각화 관련 유틸리티 함수
   - 위협 영향 범위 계산
   - MIL-STD-2525D 심볼 매핑
   - 색상 및 스타일 결정 함수

2. `frontend/src/components/LayerToggleControl.tsx`
   - 레이어 토글 UI 컴포넌트

### 수정된 파일
1. `frontend/src/components/TacticalMap.tsx`
   - 위협 영향 범위 Circle 추가
   - 방책별 색상 구분 적용
   - 축선 라인 표시 추가
   - 방책 작전 경로 표시 추가
   - 방책 작전 영역 표시 추가
   - 레이어 토글 기능 통합
   - 선택된 위협만 표시하도록 필터링 추가
   - 좌표 형식 자동 변환 로직 추가

2. `frontend/src/pages/CommandControlPage.tsx`
   - `axisStates` prop 추가
   - situationInfo 변경 시 selectedThreat 자동 설정 로직 추가

3. `frontend/src/lib/milsymbol-wrapper.ts`
   - 선택된 마커 강조 효과 추가 (펄스 애니메이션, 외곽 원)

4. `frontend/src/index.css`
   - 선택된 위협 마커 펄스 애니메이션 CSS 추가

3. `api/routers/coa.py`
   - 시각화 데이터 생성 로직 통합
   - `VisualizationDataGenerator` 사용

4. `api/schemas.py`
   - `COASummary`에 `visualization_data` 필드 추가

5. `core_pipeline/visualization_generator.py` (새로 생성)
   - 축선 좌표 해결 로직
   - 방책 작전 경로 생성
   - 방책 작전 영역 생성
   - axis_states 좌표 정보 추가

## 데이터 구조 요구사항

### 백엔드에서 제공해야 하는 데이터

#### 1. 위협 시각화 데이터
```typescript
{
    threat_id: string;
    threat_level: number; // 0.0 ~ 1.0
    threat_type_code: string;
    location_cell_id?: string;
    좌표정보?: string; // "경도,위도" 형식
}
```

#### 2. 방책 시각화 데이터
```typescript
{
    coa_id: string;
    rank: number;
    visualization_data?: {
        operational_path?: {
            waypoints: LatLngExpression[];
            path_type: 'MOVEMENT' | 'ATTACK' | 'DEFENSE' | 'SUPPORT';
        };
        operational_area?: {
            deployment_area?: { polygon: LatLngExpression[] };
            engagement_area?: { polygon: LatLngExpression[] };
        };
    };
    unit_positions?: GeoJSON; // 아군 부대 배치 위치
}
```

#### 3. 축선 시각화 데이터
```typescript
{
    axis_states: Array<{
        axis_id: string;
        axis_name?: string;
        axis_type?: 'PRIMARY' | 'SECONDARY' | 'SUPPORT';
        coordinates?: LatLngExpression[]; // 또는
        geojson?: GeoJSON; // LineString
    }>;
}
```

## 사용 방법

### 기본 사용
```tsx
<TacticalMap
    threats={threats}
    coaRecommendations={coas}
    selectedCOA={selectedCOA}
    axisStates={axisStates}
    // ... 기타 props
/>
```

### 레이어 토글
- 지도 우측 상단의 레이어 토글 패널에서 각 레이어를 켜고 끌 수 있습니다.

## 백엔드 구현 완료 사항

### 시각화 데이터 생성 모듈
- **파일**: `core_pipeline/visualization_generator.py`
- **기능**:
  - 축선 좌표 해결 (`resolve_axis_coordinates`)
  - 방책 작전 경로 생성 (`generate_operational_path`)
  - 방책 작전 영역 생성 (`generate_operational_area`)
  - axis_states 좌표 정보 추가 (`enrich_axis_states_with_coordinates`)

### COA API 통합
- **파일**: `api/routers/coa.py`
- **변경사항**:
  - COA 생성 시 자동으로 시각화 데이터 생성
  - `visualization_data` 필드에 `operational_path`, `operational_area` 포함
  - `axis_states`에 좌표 정보 자동 추가

## 향후 개선 사항

### 1. 타임라인 기반 동적 표시
- 시간 슬라이더 구현
- 시간대별 마커 표시/숨김
- 애니메이션 효과

### 2. 성능 최적화
- 마커 클러스터링 (많은 마커가 있을 때)
- 가상화 (보이는 영역의 마커만 렌더링)
- 레이어 LOD (줌 레벨에 따른 상세도 조절)

### 3. 추가 기능
- 방책 비교 모드 (2개 방책 동시 비교)
- 지형 셀 표시
- 민간인 지역 표시
- 기상 영향 영역 표시

### 4. 백엔드 개선
- 참여 부대 상세 정보 조회 (현재는 unit_id만 사용)
- 더 정교한 작전 경로 생성 알고리즘
- 지형 정보를 고려한 경로 최적화

## 테스트 결과

### 테스트 스크립트 실행 결과

**테스트 스크립트**: `scripts/test_cop_visualization.py`

**테스트 결과**:
1. ✅ **축선 좌표 해결**: 성공
   - AXIS01: 3개 좌표 해결 성공
   - AXIS02: 3개 좌표 해결 성공
   - AXIS03: 3개 좌표 해결 성공

2. ✅ **방책 작전 경로 생성**: 성공
   - 경로 타입 자동 결정 (DEFENSE)
   - Waypoints 생성 성공 (출발지 → 경유지 → 목표지)

3. ✅ **방책 작전 영역 생성**: 성공
   - 배치 영역: 33개 좌표 생성
   - 교전 영역: 5개 좌표 생성

4. ⚠️ **지형셀 좌표 조회**: 부분 성공
   - DataManager 초기화 이슈 (config 필요)
   - 직접 파일 읽기로 대체 가능

### 발견된 이슈

1. **참여 부대 정보 조회 개선**
   - ✅ 수정 완료: `unit_assignments`에서 부대 정보 추출
   - ✅ 수정 완료: `data_manager`에서 부대 상세 정보 조회

2. **좌표 정보 우선순위**
   - ✅ 구현 완료: 좌표정보 → 지형셀 → 축선 우선순위 적용

3. **데이터 검증 필요 사항**
   - ⚠️ `위협수준` 필드 타입 확인 필요 (문자열 vs 숫자)
     - **해결**: 프론트엔드에서 파싱 로직 적용 (이미 구현됨)
   - ⚠️ `좌표정보` 필드 형식 표준화 필요
     - **해결**: 좌표 형식 자동 변환 로직 추가 (이미 구현됨)

4. **좌표 형식 변환**
   - ✅ 구현 완료: [lng, lat] ↔ [lat, lng] 자동 변환
   - ✅ waypoints 및 polygon 좌표 형식 자동 감지 및 변환

5. **선택된 위협 강조 표시**
   - ✅ 구현 완료: selectedThreat가 있을 때 선택된 위협만 표시
   - ✅ 선택된 위협 마커 펄스 효과 및 강조 스타일 추가
   - ✅ 선택된 위협의 영향 범위만 표시
   - ✅ 배경 적군은 selectedThreat가 있을 때 숨김
   - ✅ situationInfo 변경 시 selectedThreat 자동 설정

6. **situationInfo 통합 개선**
   - ✅ 구현 완료: TacticalMap에 situationInfo prop 추가
   - ✅ situationInfo에서 위협 정보 직접 추출 및 표시
   - ✅ situationInfo의 좌표 정보를 우선적으로 사용
   - ✅ situationInfo 변경 시 지도 중심 자동 이동
   - ✅ threats 배열에 없어도 situationInfo의 위협 정보 표시

7. **방책 중심 시각화 개선**
   - ✅ 구현 완료: missions 배열 마커 제거 (방책 중심 시각화)
   - ✅ selectedCOA가 있으면 선택된 방책의 부대만 표시
   - ✅ selectedCOA가 있으면 선택된 방책의 작전 경로만 표시
   - ✅ selectedCOA가 있으면 선택된 방책의 작전 영역만 표시
   - ✅ 선택된 방책의 부대 위치 중심으로 지도 자동 이동
   - ✅ 부대 마커 팝업에 제대, 병종, 전투력 정보 추가

## 참고 자료

- 설계 문서: `docs/40_Refactoring/cop_visualization_design.md`
- 데이터 검증 계획: `docs/30_Guides/Data_Validation_Plan.md` (10장: COP 시각화 데이터 요구사항)
- MIL-STD-2525D: https://www.milsymbol.net/
- Leaflet 문서: https://leafletjs.com/
- react-leaflet 문서: https://react-leaflet.js.org/
