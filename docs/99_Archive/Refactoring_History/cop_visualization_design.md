# COP(Common Operational Picture) 시각화 설계안

## 1. 개요

### 1.1 목적
본 설계안은 MIL-STD-2525D 표준과 팔란티어(Palantir)의 COP 시각화 방식을 참고하여, 방책 추천 시스템의 전술상황도(COP)에 위협상황별 적 정보와 아군 방책 관련 정보를 효과적으로 시각화하는 방안을 제시합니다.

### 1.2 참고 표준 및 시스템
- **MIL-STD-2525D**: 군사 심볼 표준 (NATO APP-6A 호환)
- **Palantir Gotham**: 객체 중심 시각화, 타임라인 기반 동적 표시
- **실제 방책 추천 시스템 요구사항**: 위협-방책 매핑, 축선 정보, 시간 정보

## 2. 시각화 레이어 구조

### 2.1 레이어 계층 구조 (Z-Index 우선순위)

```
┌─────────────────────────────────────────┐
│  최상위 레이어 (z-index: 10000+)        │
│  - 선택된 요소 강조 (하이라이트)        │
│  - 사용자 인터랙션 요소 (팝업, 툴팁)    │
├─────────────────────────────────────────┤
│  상위 레이어 (z-index: 5000-9999)       │
│  - 선택된 방책의 작전 경로              │
│  - 선택된 방책의 아군 부대              │
│  - 선택된 위협의 영향 범위              │
├─────────────────────────────────────────┤
│  중위 레이어 (z-index: 2000-4999)       │
│  - 방책 작전 경로 (Polyline)            │
│  - 방책 작전 영역 (Polygon)             │
│  - 위협 영향 범위 (Circle)              │
├─────────────────────────────────────────┤
│  하위 레이어 (z-index: 1000-1999)       │
│  - 아군 부대 마커 (MIL-STD-2525D)        │
│  - 적군 부대 마커 (MIL-STD-2525D)       │
│  - 위협 마커                            │
├─────────────────────────────────────────┤
│  기본 레이어 (z-index: 0-999)           │
│  - 축선 (Axis) 라인                     │
│  - 지형 셀 (Terrain Cells)              │
│  - 배경 지도                            │
└─────────────────────────────────────────┘
```

## 3. 위협상황별 적 정보 시각화

### 3.1 적군 마커 (Hostile Units)

#### 3.1.1 기본 적군 마커
- **심볼**: MIL-STD-2525D Red Force 심볼
- **위치**: 위협 식별 위치 (location_cell_id 기반)
- **표시 정보**:
  - 위협 유형 (threat_type_code)
  - 위협 수준 (threat_level)
  - 식별 시간 (occurrence_time)
  - 신뢰도 (confidence)

#### 3.1.2 위협 영향 범위 (Threat Influence Area)
```typescript
interface ThreatInfluenceArea {
    threat_id: string;
    center: LatLngExpression;
    radius: number; // km 단위
    threat_level: number; // 0.0 ~ 1.0
    threat_type: string;
    visualization: {
        color: string; // 위협 수준에 따라 색상 변화
        opacity: number; // 0.1 ~ 0.3 (반투명)
        stroke: boolean;
        strokeColor: string;
        strokeWidth: number;
    };
}
```

**색상 매핑**:
- 위협 수준 0.0-0.3: 초록색 (#22c55e, opacity: 0.1)
- 위협 수준 0.3-0.6: 노란색 (#eab308, opacity: 0.15)
- 위협 수준 0.6-0.8: 주황색 (#f97316, opacity: 0.2)
- 위협 수준 0.8-1.0: 빨간색 (#ef4444, opacity: 0.3)

**반경 계산**:
- 기본 반경: 5km
- 위협 수준에 따른 가중치: `radius = baseRadius * (1 + threat_level)`
- 위협 유형별 추가 반경:
  - 미사일: +10km
  - 포병: +8km
  - 기갑: +5km
  - 보병: +3km

#### 3.1.3 위협 타임라인 표시
- **팔란티어 스타일**: 시간 슬라이더를 통한 동적 표시
- **표시 방식**:
  - 위협 발생 시간 기준으로 마커 표시/숨김
  - 시간대별 위협 수준 변화를 색상으로 표현
  - 애니메이션 효과 (펄스, 확장/축소)

### 3.2 배경 적군 정보 (Background Enemy Forces)

#### 3.2.1 배경 적군 마커
- **표시 방식**: 반투명 마커 (opacity: 0.5)
- **심볼 크기**: 기본 마커보다 작게 (size: 20px)
- **정보 표시**:
  - 부대명
  - 예상 위치
  - 위협 가능성

#### 3.2.2 적군 작전 영역 (Enemy Operational Area)
- **Polygon 레이어**: 적군의 예상 작전 영역 표시
- **스타일**: 빨간색 반투명 영역 (opacity: 0.1)

## 4. 아군 방책 관련 정보 시각화

### 4.1 방책별 아군 부대 배치

#### 4.1.1 아군 부대 마커 (Friendly Units)
```typescript
interface FriendlyUnitMarker {
    unit_id: string;
    unit_name: string;
    coa_id: string; // 소속 방책
    position: LatLngExpression;
    sidc: string; // MIL-STD-2525D 심볼 코드
    unit_type: 'INFANTRY' | 'ARMOR' | 'ARTILLERY' | 'AIR' | 'MISSILE' | 'ENGINEER';
    status: 'DEPLOYED' | 'MOVING' | 'ENGAGED' | 'RESERVE';
    visualization: {
        size: number; // 선택된 방책의 부대는 더 크게
        color: string; // 방책별 색상 구분
        pulse: boolean; // 선택된 방책의 부대는 펄스 효과
    };
}
```

**심볼 코드 매핑**:
- 보병: `SFGPUCI----K---` (Friendly Ground Unit, Combat Infantry)
- 기갑: `SFGPUCA----K---` (Friendly Ground Unit, Combat Armor)
- 포병: `SFGPUCF----K---` (Friendly Ground Unit, Combat Field Artillery)
- 공군: `SFAPUCI----K---` (Friendly Air Unit, Combat Infantry)
- 미사일: `SFGPUCM----K---` (Friendly Ground Unit, Combat Missile)

#### 4.1.2 방책별 색상 구분
- **방책 1 (Rank 1)**: 파란색 (#3b82f6)
- **방책 2 (Rank 2)**: 초록색 (#10b981)
- **방책 3 (Rank 3)**: 보라색 (#8b5cf6)
- **선택된 방책**: 강조 색상 (빨간색 테두리, 펄스 효과)

### 4.2 방책 작전 경로 (COA Operational Path)

#### 4.2.1 작전 경로 표시
```typescript
interface COAOperationalPath {
    coa_id: string;
    path_type: 'MOVEMENT' | 'ATTACK' | 'DEFENSE' | 'SUPPORT';
    waypoints: LatLngExpression[];
    visualization: {
        color: string; // 방책별 색상
        weight: number; // 선 두께 (선택된 방책: 4px, 기타: 2px)
        opacity: number; // 0.7
        dashArray?: string; // 점선 패턴
        arrow: boolean; // 화살표 표시
    };
}
```

**경로 타입별 스타일**:
- **MOVEMENT (기동)**: 실선, 파란색
- **ATTACK (공격)**: 실선, 빨간색, 화살표
- **DEFENSE (방어)**: 점선, 파란색, 두꺼운 선
- **SUPPORT (지원)**: 점선, 초록색

#### 4.2.2 작전 단계별 표시
- **Phase 1 (초기 전개)**: 점선
- **Phase 2 (주공격)**: 실선, 두꺼운 선
- **Phase 3 (지원/후속)**: 점선, 얇은 선

### 4.3 방책 작전 영역 (COA Operational Area)

#### 4.3.1 작전 영역 Polygon
```typescript
interface COAOperationalArea {
    coa_id: string;
    area_type: 'DEPLOYMENT' | 'ENGAGEMENT' | 'SUPPORT';
    polygon: LatLngExpression[];
    visualization: {
        fillColor: string;
        fillOpacity: number; // 0.1 ~ 0.2
        stroke: boolean;
        strokeColor: string;
        strokeWidth: number;
    };
}
```

### 4.4 축선 정보 시각화

#### 4.4.1 축선 라인 (Axis Lines)
```typescript
interface AxisLine {
    axis_id: string;
    axis_name: string;
    start_point: LatLngExpression;
    end_point: LatLngExpression;
    axis_type: 'PRIMARY' | 'SECONDARY' | 'SUPPORT';
    visualization: {
        color: string; // 축선 타입별 색상
        weight: number; // 주요 축선: 3px, 보조: 2px
        opacity: number; // 0.6
        dashArray?: string; // 보조 축선은 점선
    };
}
```

**축선 타입별 색상**:
- **PRIMARY (주요 축선)**: 진한 파란색 (#1e40af), 실선, 3px
- **SECONDARY (보조 축선)**: 파란색 (#3b82f6), 점선, 2px
- **SUPPORT (지원 축선)**: 연한 파란색 (#93c5fd), 점선, 1px

#### 4.4.2 축선 라벨
- 축선 중간 지점에 축선명 표시
- 배경색과 테두리로 가독성 향상

### 4.5 추론 경로 (Reasoning Trace) 시각화

#### 4.5.1 온톨로지 기반 추론 경로
- **마커**: 추론 단계별 번호가 표시된 원형 마커
- **연결선**: 점선으로 추론 단계 연결
- **색상**: 보라색 (#8b5cf6)

## 5. 상호작용 및 필터링

### 5.1 레이어 토글 (Layer Toggle)
```typescript
interface LayerToggle {
    threats: boolean; // 위협 마커 표시/숨김
    threatInfluence: boolean; // 위협 영향 범위 표시/숨김
    friendlyUnits: boolean; // 아군 부대 표시/숨김
    coaPaths: boolean; // 방책 경로 표시/숨김
    coaAreas: boolean; // 방책 영역 표시/숨김
    axes: boolean; // 축선 표시/숨김
    terrain: boolean; // 지형 셀 표시/숨김
}
```

### 5.2 방책 필터링
- **전체 표시**: 모든 방책의 정보 표시 (반투명)
- **단일 선택**: 선택된 방책만 강조 표시
- **비교 모드**: 2개 방책 동시 비교 (색상 구분)

### 5.3 시간 필터링 (팔란티어 스타일)
- **타임라인 슬라이더**: 시간대별 상황 표시
- **애니메이션 재생**: 시간 경과에 따른 동적 표시
- **특정 시점 고정**: 특정 시간대의 상황만 표시

## 6. 팝업 및 상세 정보

### 6.1 마커 팝업 (Popup)

#### 6.1.1 위협 마커 팝업
```typescript
interface ThreatPopup {
    threat_id: string;
    threat_type: string;
    threat_level: number;
    location: string;
    occurrence_time: string;
    confidence: number;
    related_axis_id: string;
    enemy_unit: string;
    actions: {
        viewDetails: () => void;
        selectCOA: (coa_id: string) => void;
    };
}
```

#### 6.1.2 아군 부대 마커 팝업
```typescript
interface FriendlyUnitPopup {
    unit_id: string;
    unit_name: string;
    unit_type: string;
    coa_id: string;
    coa_name: string;
    status: string;
    position: LatLngExpression;
    actions: {
        viewCOADetails: () => void;
        viewUnitDetails: () => void;
    };
}
```

### 6.2 지도 범례 (Legend)
- 심볼 설명
- 색상 의미
- 레이어 토글 버튼

## 7. 데이터 구조

### 7.1 백엔드 데이터 형식

#### 7.1.1 COA 시각화 데이터 확장
```typescript
interface COAVisualizationData {
    // 기존 필드
    coa_geojson?: GeoJSON;
    unit_positions?: GeoJSON;
    
    // 추가 필드
    operational_path?: {
        waypoints: LatLngExpression[];
        path_type: string;
        phases: Array<{
            phase_name: string;
            waypoints: LatLngExpression[];
        }>;
    };
    operational_area?: {
        polygon: LatLngExpression[];
        area_type: string;
    };
    axis_info?: {
        axis_id: string;
        axis_name: string;
        axis_type: string;
        coordinates: LatLngExpression[];
    };
    threat_mapping?: Array<{
        threat_id: string;
        engagement_type: 'DIRECT' | 'INDIRECT' | 'SUPPORT';
        engagement_area?: LatLngExpression[];
    }>;
}
```

#### 7.1.2 위협 시각화 데이터
```typescript
interface ThreatVisualizationData {
    threat_id: string;
    position: LatLngExpression;
    influence_area: {
        center: LatLngExpression;
        radius: number; // km
    };
    threat_timeline?: Array<{
        timestamp: string;
        threat_level: number;
        position?: LatLngExpression;
    }>;
    background_enemies?: Array<{
        unit_id: string;
        unit_name: string;
        position: LatLngExpression;
        threat_probability: number;
    }>;
}
```

## 8. 구현 우선순위

### Phase 1: 기본 시각화 (필수)
1. ✅ 위협 마커 표시 (MIL-STD-2525D)
2. ✅ 아군 부대 마커 표시 (MIL-STD-2525D)
3. ✅ 방책별 색상 구분
4. ✅ 선택된 방책 강조
5. ✅ 위협 영향 범위 (Circle)

### Phase 2: 경로 및 영역 (중요)
1. 방책 작전 경로 (Polyline)
2. 방책 작전 영역 (Polygon)
3. 축선 라인 표시
4. 추론 경로 시각화

### Phase 3: 고급 기능 (선택)
1. 타임라인 기반 동적 표시
2. 레이어 토글 기능
3. 방책 비교 모드
4. 애니메이션 효과

## 9. 기술 구현 사항

### 9.1 라이브러리
- **Leaflet**: 지도 렌더링
- **react-leaflet**: React 통합
- **milsymbol**: MIL-STD-2525D 심볼 생성
- **GeoJSON**: 지리 데이터 표현

### 9.2 성능 최적화
- **마커 클러스터링**: 많은 마커가 있을 때 클러스터로 그룹화
- **가상화 (Virtualization)**: 보이는 영역의 마커만 렌더링
- **레이어 LOD (Level of Detail)**: 줌 레벨에 따른 상세도 조절

### 9.3 반응형 디자인
- 모바일/태블릿/데스크톱 대응
- 터치 제스처 지원 (핀치 줌, 팬)

## 10. 참고 자료

### 10.1 MIL-STD-2525D
- [MIL-STD-2525D 공식 문서](https://www.milsymbol.net/)
- SIDC (Symbol Identification Code) 구조
- 심볼 카테고리 및 변형

### 10.2 Palantir Gotham
- 객체 중심 시각화 패러다임
- 타임라인 기반 동적 표시
- 관계 그래프 시각화

### 10.3 군사 작전 시각화 모범 사례
- NATO APP-6A 표준
- 실전 COP 시스템 사례
- 지휘통제 시스템 UI/UX

## 11. 데이터 소스 분석 및 시각화 정보 식별

### 11.1 엑셀 테이블 필드 분석

#### 11.1.1 위협상황 테이블 (위협상황.xlsx)
**시각화에 필요한 필드**:
- `위협ID` (PK): 위협 식별자
- `발생시각`: 위협 발생 시간 (타임라인 시각화용)
- `위협유형코드`: 위협 유형 (MIL-STD-2525D 심볼 결정)
- `관련축선ID` (FK → 전장축선): 위협이 발생한 축선
- `발생위치셀ID` (FK → 지형셀): 위협 발생 위치
- `관련_적부대ID` (FK → 적군부대현황): 관련 적군 부대
- `위협수준`: 위협 수준 (0.0-1.0, 영향 범위 반경 계산용)
- `좌표정보`: 직접 좌표 (문자열 형식: "경도,위도")
- `이동방향`, `이동속도`, `전투력`: 적군 동적 정보

**추가 확인 필요**:
- ⚠️ `좌표정보` 필드 형식 표준화 필요 (현재 문자열, 파싱 로직 필요)
- ⚠️ `위협수준` 필드 타입 확인 (문자열 vs 숫자)

#### 11.1.2 아군부대현황 테이블 (아군부대현황.xlsx)
**시각화에 필요한 필드**:
- `아군부대ID` (PK): 부대 식별자
- `부대명`: 부대명 (마커 라벨)
- `제대`, `병종`: 부대 유형 (MIL-STD-2525D 심볼 결정)
- `배치축선ID` (FK → 전장축선): 부대 배치 축선
- `배치지형셀ID` (FK → 지형셀): 부대 배치 위치
- `전투력지수`: 전투력 (마커 크기/색상 조절용)
- `가용상태`: 부대 상태 (배치 가능 여부)
- `임무역할`: 임무 역할 (팝업 정보)
- `좌표정보`: 직접 좌표
- `이동방향`, `이동속도`: 부대 동적 정보

**추가 확인 필요**:
- ⚠️ `전투력지수` vs `전투력` 필드 중복 (Data_Validation_Plan.md 참조)
- ⚠️ `가용상태` vs `상태` 필드 중복

#### 11.1.3 적군부대현황 테이블 (적군부대현황.xlsx)
**시각화에 필요한 필드**:
- `적군부대ID` (PK): 적군 부대 식별자
- `부대명`: 부대명
- `제대`, `병종`: 부대 유형 (MIL-STD-2525D Red Force 심볼)
- `배치축선ID` (FK → 전장축선): 적군 배치 축선
- `배치지형셀ID` (FK → 지형셀): 적군 배치 위치
- `전투력지수`: 전투력
- `위협수준`: 위협 수준
- `좌표정보`: 직접 좌표
- `SIDC`: MIL-STD-2525D 심볼 코드 (직접 제공 시 우선 사용)
- `이동속도_kmh`: 이동 속도 (단위 명시)
- `감지범위_km`: 감지 범위 (위협 영향 범위 계산용)

**추가 확인 필요**:
- ⚠️ `이동속도_kmh` vs 다른 테이블의 `이동속도` 단위 불일치

#### 11.1.4 전장축선 테이블 (전장축선.xlsx)
**시각화에 필요한 필드**:
- `축선ID` (PK): 축선 식별자
- `축선명`: 축선명 (라벨 표시)
- `축선유형`: 축선 유형 (PRIMARY/SECONDARY/SUPPORT 구분)
- `시작지형셀ID` (FK → 지형셀): 축선 시작점
- `종단지형셀ID` (FK → 지형셀): 축선 종단점
- `주요지형셀목록`: 축선 경로상의 지형셀 목록 (콤마 구분 문자열)
- `축선설명`: 축선 설명

**추가 확인 필요**:
- ⚠️ `주요지형셀목록` vs `구성지형셀목록` 컬럼명 불일치 (Data_Validation_Plan.md 참조)
- ⚠️ 축선 좌표 계산 로직: 시작/종단 지형셀 → 좌표 변환 필요

#### 11.1.5 지형셀 테이블 (지형셀.xlsx)
**시각화에 필요한 필드**:
- `지형셀ID` (PK): 지형셀 식별자
- `지형명`: 지형명 (라벨)
- `지형유형`: 지형 유형 (지형 셀 색상/패턴 결정)
- `X좌표`, `Y좌표`: 지형셀 중심 좌표
- `기동성등급`: 기동성 등급 (지형 셀 시각화용)
- `방어유리도`, `관측유리도`: 지형 특성
- `요충지여부`: 요충지 여부 (강조 표시용)

**추가 확인 필요**:
- ⚠️ `X좌표`, `Y좌표` vs `좌표정보` 필드 형식 불일치
- ⚠️ 실제 파일에는 `좌표정보` 필드도 존재할 수 있음 (Data_Validation_Plan.md 참조)

#### 11.1.6 임무정보 테이블 (임무정보.xlsx)
**시각화에 필요한 필드**:
- `임무ID` (PK): 임무 식별자
- `임무명`: 임무명
- `임무종류`: 임무 종류
- `작전지역`: 작전 지역 (Polygon 영역 표시용)
- `주공축선ID`, `조공축선ID`, `예비축선ID` (FK → 전장축선): 임무 관련 축선
- `작전개시시각`, `작전종료예상`: 시간 정보 (타임라인 시각화용)

#### 11.1.7 COA_Library 테이블 (COA_Library.xlsx)
**시각화에 필요한 필드**:
- `COA_ID` (PK): 방책 식별자
- `명칭`: 방책명
- `방책유형`: 방책 유형 (Defense/Offensive/CounterAttack 등)
- `설명`: 방책 설명
- `필요자원`: 필요 자원 (아군 부대 배치 결정용)
- `전장환경_제약`: 환경 제약 (작전 영역 결정용)
- `키워드`: 키워드 (위협 매칭용)

**추가 확인 필요**:
- ⚠️ `적용조건` vs `전장환경_제약` 의미 중복 가능성
- ⚠️ `환경호환성` vs `전장환경_최적조건` 의미 중복 가능성

### 11.2 온톨로지 구조 분석

#### 11.2.1 온톨로지 클래스 및 관계
**핵심 클래스**:
- `위협상황`: 위협 정보
- `아군부대현황`: 아군 부대
- `적군부대현황`: 적군 부대
- `전장축선`: 축선 정보
- `지형셀`: 지형 정보
- `COA_Library`: 방책 라이브러리
- `임무정보`: 임무 정보

**핵심 관계 (Object Properties)**:
- `has지형셀`: 위협상황, 전장축선 → 지형셀
- `has전장축선`: 위협상황, 아군부대현황, 적군부대현황, 임무정보 → 전장축선
- `locatedIn`: 아군부대현황, 적군부대현황, 기상상황, 민간인지역 → 지형셀
- `has적군부대현황`: 위협상황 → 적군부대현황
- `has임무정보`: 위협상황, 시나리오모음 → 임무정보
- `countersThreat`: COA → Threat (방책이 대응하는 위협)

**추론 관계 (Inferred Relations)**:
- `relatedTo`: 적군부대현황 → 위협상황 (부대유형 기반, confidence: 0.8)
- `affectsCivilianArea`: 위협상황 → 민간인지역 (동일 지형셀 기반, confidence: 0.7)

### 11.3 방책 추천 정보 분석

#### 11.3.1 COA 추천 결과 구조
**현재 제공되는 정보**:
- `coa_id`, `coa_name`: 방책 식별자 및 명칭
- `participating_units`: 참여 부대 목록
- `reasoning_trace`: 추론 경로 (온톨로지 기반)
- `chain_info`: 체인 정보 (위협-방책 연계)
- `score_breakdown`: 점수 세부 분석
- `visualization_data`: 시각화 데이터 (선택적)

**시각화에 활용 가능한 정보**:
- `participating_units`: 아군 부대 배치 결정
- `reasoning_trace`: 추론 경로 시각화
- `chain_info`: 위협-방책 연계 시각화
- `visualization_data.main_axis_id`: 주요 축선 정보

### 11.4 시각화에 필요한 정보 식별

#### 11.4.1 현재 사용 가능한 정보 ✅
1. **위협 정보**:
   - 위치: `발생위치셀ID` → 지형셀 → 좌표
   - 위치 (대체): `좌표정보` 직접 파싱
   - 축선: `관련축선ID` → 전장축선 → 좌표
   - 위협 수준: `위협수준` → 영향 범위 반경
   - 위협 유형: `위협유형코드` → MIL-STD-2525D 심볼

2. **아군 부대 정보**:
   - 위치: `배치지형셀ID` → 지형셀 → 좌표
   - 위치 (대체): `좌표정보` 직접 파싱
   - 축선: `배치축선ID` → 전장축선
   - 부대 유형: `제대`, `병종` → MIL-STD-2525D 심볼
   - 상태: `가용상태`, `전투력지수`

3. **적군 부대 정보**:
   - 위치: `배치지형셀ID` → 지형셀 → 좌표
   - 위치 (대체): `좌표정보` 직접 파싱
   - 축선: `배치축선ID` → 전장축선
   - 부대 유형: `제대`, `병종` → MIL-STD-2525D Red Force 심볼
   - 감지 범위: `감지범위_km` → 위협 영향 범위

4. **축선 정보**:
   - 경로: `시작지형셀ID`, `종단지형셀ID`, `주요지형셀목록` → 지형셀 → 좌표
   - 축선 유형: `축선유형` → PRIMARY/SECONDARY/SUPPORT 구분

5. **지형 정보**:
   - 좌표: `X좌표`, `Y좌표`
   - 지형 특성: `기동성등급`, `방어유리도`, `관측유리도`, `요충지여부`

#### 11.4.2 추가/확인이 필요한 정보 ⚠️

**1. 위협 영향 범위 계산**
- ✅ 현재: `위협수준` 필드 존재
- ⚠️ 확인 필요: `위협수준` 필드 타입 (문자열 vs 숫자)
- ⚠️ 추가 필요: 위협 유형별 기본 반경 매핑 테이블
  - 예: 미사일: 10km, 포병: 8km, 기갑: 5km, 보병: 3km

**2. 방책 작전 경로**
- ✅ 현재: `participating_units`에서 부대 위치 추출 가능
- ⚠️ 추가 필요: 방책별 작전 경로 waypoints
  - 출발지: 아군 부대 배치 위치
  - 목표지: 위협 위치 또는 작전 목표 지점
  - 경유지: 축선상의 지형셀 또는 임의 waypoint

**3. 방책 작전 영역**
- ✅ 현재: `전장환경_제약` 필드 존재
- ⚠️ 추가 필요: 방책별 작전 영역 Polygon 좌표
  - 배치 영역: 아군 부대 배치 영역
  - 교전 영역: 예상 교전 영역
  - 지원 영역: 지원 부대 작전 영역

**4. 시간 정보**
- ✅ 현재: `발생시각` (위협), `작전개시시각`, `작전종료예상` (임무)
- ⚠️ 추가 필요: 방책별 시간 정보
  - 전개 시간: 부대 전개 예상 시간
  - 교전 시간: 예상 교전 시각
  - 완료 시간: 작전 완료 예상 시간

**5. 배경 적군 정보**
- ✅ 현재: `적군부대현황` 테이블 존재
- ⚠️ 추가 필요: 위협과 직접 관련 없는 배경 적군 필터링 로직
  - `관련_적부대ID`가 없는 적군 부대는 배경 적군으로 표시

**6. 민간인 지역 정보**
- ✅ 현재: `민간인지역` 테이블 존재, `locatedIn` 관계로 지형셀 연결
- ⚠️ 추가 필요: 민간인 지역 Polygon 좌표
  - 현재는 지형셀 기반 추론만 가능 (confidence: 0.7)

**7. 기상 정보**
- ✅ 현재: `기상상황` 테이블 존재, `locatedIn` 관계로 지형셀 연결
- ⚠️ 추가 필요: 기상 영향 영역 시각화
  - 기상 조건에 따른 작전 제약 표시

### 11.5 데이터 매핑 및 변환 로직

#### 11.5.1 좌표 해결 우선순위
```
1순위: 직접 좌표 (좌표정보 필드 파싱)
2순위: StatusManager 실시간 좌표
3순위: 지형셀 좌표 (배치지형셀ID → 지형셀 → X좌표, Y좌표)
4순위: 축선 좌표 (배치축선ID → 전장축선 → 시작/종단 지형셀 → 좌표)
5순위: 기본 위치 (LOCATION_DB 또는 하드코딩)
```

#### 11.5.2 MIL-STD-2525D 심볼 결정 로직
```
1순위: 직접 SIDC 필드 (적군부대현황.SIDC)
2순위: 부대 유형 기반 매핑
   - 제대 + 병종 → UNIT_TEMPLATES 매핑
   - 예: "사단" + "기계화" → BLUE_MECHANIZED
3순위: 방책 유형 기반 기본 심볼
   - 공중 작전 → BLUE_AIR
   - 미사일 작전 → BLUE_MISSILE
   - 기타 → BLUE_INFANTRY
```

### 11.6 추가 데이터 구조 제안

#### 11.6.1 백엔드 시각화 데이터 확장
```typescript
interface EnhancedCOAVisualizationData {
    // 기존 필드
    coa_geojson?: GeoJSON;
    unit_positions?: GeoJSON;
    
    // 좌표 정보 (우선순위별)
    coordinates?: {
        primary?: LatLngExpression; // 직접 좌표
        from_status_manager?: LatLngExpression; // StatusManager 좌표
        from_terrain_cell?: {
            cell_id: string;
            coordinates: LatLngExpression;
        };
        from_axis?: {
            axis_id: string;
            coordinates: LatLngExpression[];
        };
    };
    
    // 작전 경로
    operational_path?: {
        waypoints: LatLngExpression[];
        path_type: 'MOVEMENT' | 'ATTACK' | 'DEFENSE' | 'SUPPORT';
        phases: Array<{
            phase_name: string;
            phase_type: 'DEPLOYMENT' | 'ENGAGEMENT' | 'SUPPORT';
            waypoints: LatLngExpression[];
            estimated_time?: string; // ISO 8601
        }>;
    };
    
    // 작전 영역
    operational_area?: {
        deployment_area?: {
            polygon: LatLngExpression[];
            description: string;
        };
        engagement_area?: {
            polygon: LatLngExpression[];
            description: string;
        };
        support_area?: {
            polygon: LatLngExpression[];
            description: string;
        };
    };
    
    // 축선 정보
    axis_info?: {
        primary_axis?: {
            axis_id: string;
            axis_name: string;
            axis_type: 'PRIMARY' | 'SECONDARY' | 'SUPPORT';
            coordinates: LatLngExpression[];
            terrain_cells: string[]; // 지형셀ID 목록
        };
        related_axes?: Array<{
            axis_id: string;
            axis_name: string;
            axis_type: string;
            coordinates: LatLngExpression[];
        }>;
    };
    
    // 위협 매핑
    threat_mapping?: Array<{
        threat_id: string;
        threat_name: string;
        engagement_type: 'DIRECT' | 'INDIRECT' | 'SUPPORT';
        engagement_area?: LatLngExpression[];
        engagement_time?: string;
    }>;
    
    // 참여 부대 상세 정보
    participating_units_detail?: Array<{
        unit_id: string;
        unit_name: string;
        unit_type: string;
        position: LatLngExpression;
        sidc: string;
        status: string;
        deployment_time?: string;
        movement_path?: LatLngExpression[];
    }>;
}
```

#### 11.6.2 위협 시각화 데이터 확장
```typescript
interface EnhancedThreatVisualizationData {
    threat_id: string;
    threat_name: string;
    threat_type: string;
    threat_type_code: string;
    
    // 위치 정보 (우선순위별)
    position: {
        primary?: LatLngExpression; // 직접 좌표
        from_terrain_cell?: {
            cell_id: string;
            coordinates: LatLngExpression;
        };
        from_axis?: {
            axis_id: string;
            coordinates: LatLngExpression;
        };
    };
    
    // 영향 범위
    influence_area: {
        center: LatLngExpression;
        radius: number; // km
        threat_level: number; // 0.0 ~ 1.0
        threat_type_multiplier: number; // 위협 유형별 가중치
        calculated_radius: number; // 최종 계산된 반경
    };
    
    // 관련 적군 부대
    related_enemy_units?: Array<{
        unit_id: string;
        unit_name: string;
        position: LatLngExpression;
        threat_probability: number;
    }>;
    
    // 배경 적군 (관련 없는 적군)
    background_enemies?: Array<{
        unit_id: string;
        unit_name: string;
        position: LatLngExpression;
        threat_probability: number;
    }>;
    
    // 타임라인
    timeline?: Array<{
        timestamp: string; // ISO 8601
        threat_level: number;
        position?: LatLngExpression;
        status: 'DETECTED' | 'CONFIRMED' | 'ENGAGED' | 'NEUTRALIZED';
    }>;
    
    // 관련 축선
    related_axes?: Array<{
        axis_id: string;
        axis_name: string;
        coordinates: LatLngExpression[];
    }>;
}
```

### 11.7 데이터 검증 및 보완 계획

#### 11.7.1 즉시 확인 필요 사항
1. **좌표 정보 일관성**:
   - [ ] `좌표정보` 필드 형식 표준화 (예: "경도,위도" 또는 "위도,경도")
   - [ ] `X좌표`, `Y좌표` vs `좌표정보` 우선순위 결정
   - [ ] 좌표 파싱 로직 통일

2. **필드명 통일**:
   - [ ] `전투력지수` vs `전투력` 통일
   - [ ] `이동속도` vs `이동속도_kmh` 통일
   - [ ] `주요지형셀목록` vs `구성지형셀목록` 통일

3. **데이터 무결성**:
   - [ ] 모든 FK 참조 무결성 확인 (이미 검증 완료 ✅)
   - [ ] 좌표 데이터 존재 여부 확인
   - [ ] 필수 필드 NULL 값 확인

#### 11.7.2 추가 데이터 생성 필요
1. **방책 작전 경로 생성 로직**:
   - 출발지: `participating_units`의 부대 위치
   - 목표지: 위협 위치 또는 작전 목표
   - 경유지: 축선상의 지형셀 또는 A* 알고리즘 기반 경로 생성

2. **방책 작전 영역 생성 로직**:
   - 배치 영역: 부대 배치 위치 중심 반경 계산
   - 교전 영역: 위협 위치와 부대 위치 사이 영역
   - 지원 영역: 지원 부대 작전 반경

3. **위협 영향 범위 계산 로직**:
   - 기본 반경: 5km
   - 위협 수준 가중치: `radius = baseRadius * (1 + threat_level)`
   - 위협 유형별 가중치: 위협유형_마스터 테이블에 반경 정보 추가

4. **타임라인 데이터 생성**:
   - 위협 발생 시간: `발생시각`
   - 부대 전개 시간: `작전개시시각` 또는 계산된 전개 시간
   - 예상 교전 시간: 위협 위치와 부대 위치 기반 계산

## 12. 데이터 매핑 상세 설계

### 12.1 위협 정보 시각화 데이터 매핑

#### 12.1.1 위협 마커 생성 로직
```python
def create_threat_marker(threat: Dict) -> ThreatMarker:
    """
    위협상황 데이터로부터 마커 생성
    """
    # 1. 위치 결정 (우선순위별)
    position = None
    
    # 1순위: 좌표정보 직접 파싱
    coord_str = threat.get("좌표정보")
    if coord_str:
        position = parse_coordinates(coord_str)  # "경도,위도" 또는 "위도,경도"
    
    # 2순위: 발생위치셀ID → 지형셀 → 좌표
    if not position:
        cell_id = threat.get("발생위치셀ID")
        if cell_id:
            terrain_cell = get_terrain_cell(cell_id)
            if terrain_cell:
                position = [terrain_cell.get("Y좌표"), terrain_cell.get("X좌표")]  # [lat, lng]
    
    # 3순위: 관련축선ID → 축선 → 좌표
    if not position:
        axis_id = threat.get("관련축선ID")
        if axis_id:
            axis = get_axis(axis_id)
            if axis:
                # 축선 시작점 또는 중간점 사용
                position = get_axis_center_coordinates(axis)
    
    # 4순위: 기본 위치
    if not position:
        position = DEFAULT_THREAT_POSITION
    
    # 2. MIL-STD-2525D 심볼 결정
    sidc = None
    
    # 1순위: 적군부대현황.SIDC (관련_적부대ID가 있는 경우)
    enemy_unit_id = threat.get("관련_적부대ID")
    if enemy_unit_id:
        enemy_unit = get_enemy_unit(enemy_unit_id)
        if enemy_unit and enemy_unit.get("SIDC"):
            sidc = enemy_unit.get("SIDC")
    
    # 2순위: 위협유형코드 → 심볼 매핑
    if not sidc:
        threat_type_code = threat.get("위협유형코드")
        sidc = get_sidc_from_threat_type(threat_type_code)
    
    # 3순위: 기본 적군 심볼
    if not sidc:
        sidc = "SHGPUCA----K---"  # 기본 적군 기갑
    
    # 3. 위협 수준 파싱
    threat_level = parse_threat_level(threat.get("위협수준"))  # 문자열 → 숫자 변환
    
    # 4. 영향 범위 계산
    influence_radius = calculate_threat_influence_radius(
        threat_level=threat_level,
        threat_type_code=threat.get("위협유형코드"),
        detection_range=threat.get("감지범위_km")  # 관련 적군 부대의 감지범위
    )
    
    return ThreatMarker(
        threat_id=threat.get("위협ID"),
        position=position,
        sidc=sidc,
        threat_level=threat_level,
        influence_radius=influence_radius,
        occurrence_time=threat.get("발생시각"),
        related_axis_id=threat.get("관련축선ID")
    )
```

#### 12.1.2 위협 영향 범위 계산 로직
```python
def calculate_threat_influence_radius(
    threat_level: float,
    threat_type_code: str,
    detection_range: Optional[float] = None
) -> float:
    """
    위협 영향 범위 반경 계산 (km)
    """
    # 기본 반경
    base_radius = 5.0  # km
    
    # 위협 수준 가중치
    level_multiplier = 1.0 + threat_level  # 1.0 ~ 2.0
    
    # 위협 유형별 추가 반경
    threat_type_radius = {
        "미사일": 10.0,
        "포병": 8.0,
        "기갑": 5.0,
        "보병": 3.0,
        "공중": 15.0,
        "해상": 12.0
    }
    type_bonus = threat_type_radius.get(threat_type_code, 0.0)
    
    # 감지 범위 반영 (있는 경우)
    if detection_range:
        type_bonus = max(type_bonus, detection_range)
    
    # 최종 반경
    radius = base_radius * level_multiplier + type_bonus
    
    return min(radius, 50.0)  # 최대 50km로 제한
```

### 12.2 아군 부대 정보 시각화 데이터 매핑

#### 12.2.1 아군 부대 마커 생성 로직
```python
def create_friendly_unit_marker(
    unit: Dict,
    coa_id: str,
    coa_rank: int,
    is_selected: bool = False
) -> FriendlyUnitMarker:
    """
    아군부대현황 데이터로부터 마커 생성
    """
    # 1. 위치 결정 (우선순위별)
    position = None
    
    # 1순위: StatusManager 실시간 좌표
    if orchestrator:
        unit_id = unit.get("아군부대ID")
        status_coords = orchestrator.core.status_manager.get_coordinates(unit_id)
        if status_coords:
            position = [status_coords[1], status_coords[0]]  # [lat, lng]
    
    # 2순위: 좌표정보 직접 파싱
    if not position:
        coord_str = unit.get("좌표정보")
        if coord_str:
            position = parse_coordinates(coord_str)
    
    # 3순위: 배치지형셀ID → 지형셀 → 좌표
    if not position:
        cell_id = unit.get("배치지형셀ID")
        if cell_id:
            terrain_cell = get_terrain_cell(cell_id)
            if terrain_cell:
                position = [terrain_cell.get("Y좌표"), terrain_cell.get("X좌표")]
    
    # 4순위: 배치축선ID → 축선 → 좌표
    if not position:
        axis_id = unit.get("배치축선ID")
        if axis_id:
            axis = get_axis(axis_id)
            if axis:
                position = get_axis_center_coordinates(axis)
    
    # 5순위: 기본 위치
    if not position:
        position = DEFAULT_FRIENDLY_POSITION
    
    # 2. MIL-STD-2525D 심볼 결정
    sidc = determine_friendly_sidc(
        제대=unit.get("제대"),
        병종=unit.get("병종")
    )
    
    # 3. 방책별 색상 결정
    color = get_coa_color(coa_rank)  # Rank 1: 파란색, Rank 2: 초록색, Rank 3: 보라색
    
    # 4. 선택된 방책 강조
    size = 35 if is_selected else 25
    pulse = is_selected
    
    return FriendlyUnitMarker(
        unit_id=unit.get("아군부대ID"),
        unit_name=unit.get("부대명"),
        coa_id=coa_id,
        position=position,
        sidc=sidc,
        color=color,
        size=size,
        pulse=pulse,
        status=unit.get("가용상태"),
        combat_power=unit.get("전투력지수")
    )
```

#### 12.2.2 MIL-STD-2525D 심볼 매핑 테이블
```python
UNIT_SIDC_MAPPING = {
    # 보병
    ("사단", "보병"): "SFGPUCI----K---",  # Friendly Ground Unit, Combat Infantry
    ("여단", "보병"): "SFGPUCI----K---",
    ("대대", "보병"): "SFGPUCI----K---",
    
    # 기갑
    ("사단", "기갑"): "SFGPUCA----K---",  # Friendly Ground Unit, Combat Armor
    ("여단", "기갑"): "SFGPUCA----K---",
    ("대대", "기갑"): "SFGPUCA----K---",
    ("기계화"): "SFGPUCA----K---",
    
    # 포병
    ("여단", "포병"): "SFGPUCF----K---",  # Friendly Ground Unit, Combat Field Artillery
    ("대대", "포병"): "SFGPUCF----K---",
    
    # 공군
    ("비행단", "공군"): "SFAPUCI----K---",  # Friendly Air Unit, Combat Infantry
    ("전투비행단"): "SFAPUCI----K---",
    
    # 미사일
    ("사령부", "유도탄"): "SFGPUCM----K---",  # Friendly Ground Unit, Combat Missile
    ("미사일"): "SFGPUCM----K---",
    
    # 기본값
    "default": "SFGPUCI----K---"
}

def determine_friendly_sidc(제대: str, 병종: str) -> str:
    key = (제대, 병종) if 제대 and 병종 else None
    if key and key in UNIT_SIDC_MAPPING:
        return UNIT_SIDC_MAPPING[key]
    
    # 부분 매칭
    for (dae, jong), sidc in UNIT_SIDC_MAPPING.items():
        if isinstance(dae, str) and dae in (제대 or ""):
            return sidc
        if isinstance(jong, str) and jong in (병종 or ""):
            return sidc
    
    return UNIT_SIDC_MAPPING["default"]
```

### 12.3 축선 정보 시각화 데이터 매핑

#### 12.3.1 축선 좌표 해결 로직
```python
def resolve_axis_coordinates(axis_id: str) -> List[LatLngExpression]:
    """
    축선 좌표 해결 (3단계 조회)
    """
    # 1단계: 축선 정의 조회
    axis = get_axis(axis_id)  # 전장축선.xlsx에서 조회
    if not axis:
        return []
    
    # 2단계: 지형셀 경로 파싱
    terrain_path = axis.get("주요지형셀목록") or axis.get("구성지형셀목록")
    if not terrain_path:
        # 시작/종단 지형셀만 사용
        start_cell = get_terrain_cell(axis.get("시작지형셀ID"))
        end_cell = get_terrain_cell(axis.get("종단지형셀ID"))
        if start_cell and end_cell:
            return [
                [start_cell.get("Y좌표"), start_cell.get("X좌표")],
                [end_cell.get("Y좌표"), end_cell.get("X좌표")]
            ]
        return []
    
    # 3단계: 지형셀 목록 → 좌표 변환
    terrain_ids = [t.strip() for t in str(terrain_path).split(',')]
    coordinates = []
    
    for cell_id in terrain_ids:
        terrain_cell = get_terrain_cell(cell_id)
        if terrain_cell:
            coordinates.append([
                terrain_cell.get("Y좌표"),
                terrain_cell.get("X좌표")
            ])
    
    return coordinates
```

#### 12.3.2 축선 타입 결정 로직
```python
def determine_axis_type(axis_id: str, mission_id: Optional[str] = None) -> str:
    """
    축선 타입 결정 (PRIMARY/SECONDARY/SUPPORT)
    """
    axis = get_axis(axis_id)
    axis_type = axis.get("축선유형", "").upper()
    
    # 축선유형 필드가 있으면 우선 사용
    if axis_type in ["PRIMARY", "SECONDARY", "SUPPORT"]:
        return axis_type
    
    # 임무 정보에서 주공/조공/예비 축선 확인
    if mission_id:
        mission = get_mission(mission_id)
        if mission:
            if axis_id == mission.get("주공축선ID"):
                return "PRIMARY"
            elif axis_id == mission.get("조공축선ID"):
                return "SECONDARY"
            elif axis_id == mission.get("예비축선ID"):
                return "SUPPORT"
    
    # 기본값
    return "SECONDARY"
```

### 12.4 방책 작전 경로 생성 로직

#### 12.4.1 경로 생성 알고리즘
```python
def generate_operational_path(
    coa: Dict,
    threat_position: LatLngExpression,
    friendly_units: List[Dict]
) -> OperationalPath:
    """
    방책 작전 경로 생성
    """
    waypoints = []
    
    # 1. 출발지: 아군 부대 배치 위치
    start_positions = [get_unit_position(u) for u in friendly_units]
    if start_positions:
        # 여러 부대가 있으면 중심점 계산
        start_point = calculate_center_point(start_positions)
        waypoints.append(start_point)
    
    # 2. 경유지: 축선상의 지형셀
    main_axis_id = coa.get("visualization_data", {}).get("main_axis_id")
    if main_axis_id:
        axis_coordinates = resolve_axis_coordinates(main_axis_id)
        # 축선 좌표를 경유지로 추가 (간소화: 시작/중간/종단점만)
        if len(axis_coordinates) >= 2):
            waypoints.append(axis_coordinates[len(axis_coordinates) // 2])  # 중간점
    
    # 3. 목표지: 위협 위치 또는 작전 목표
    waypoints.append(threat_position)
    
    # 4. 경로 타입 결정
    path_type = determine_path_type(coa)
    
    return OperationalPath(
        waypoints=waypoints,
        path_type=path_type,
        phases=generate_phases(coa, waypoints)
    )

def determine_path_type(coa: Dict) -> str:
    """
    방책 유형에 따른 경로 타입 결정
    """
    coa_type = coa.get("coa_type", "").lower()
    coa_name = coa.get("coa_name", "").lower()
    
    if "공격" in coa_name or "offensive" in coa_type:
        return "ATTACK"
    elif "방어" in coa_name or "defense" in coa_type:
        return "DEFENSE"
    elif "지원" in coa_name or "support" in coa_type:
        return "SUPPORT"
    else:
        return "MOVEMENT"
```

### 12.5 방책 작전 영역 생성 로직

#### 12.5.1 영역 생성 알고리즘
```python
def generate_operational_area(
    coa: Dict,
    friendly_units: List[Dict],
    threat_position: LatLngExpression
) -> OperationalArea:
    """
    방책 작전 영역 생성
    """
    # 1. 배치 영역: 부대 배치 위치 중심 반경
    deployment_polygon = None
    if friendly_units:
        unit_positions = [get_unit_position(u) for u in friendly_units]
        if unit_positions:
            center = calculate_center_point(unit_positions)
            # 반경: 부대 수에 비례 (기본 5km + 부대당 2km)
            radius = 5.0 + len(friendly_units) * 2.0
            deployment_polygon = create_circle_polygon(center, radius)
    
    # 2. 교전 영역: 위협 위치와 부대 위치 사이 영역
    engagement_polygon = None
    if friendly_units and threat_position:
        unit_positions = [get_unit_position(u) for u in friendly_units]
        if unit_positions:
            # 위협과 부대 사이의 버퍼 영역 생성
            engagement_polygon = create_buffer_between_points(
                unit_positions,
                threat_position,
                buffer_distance=3.0  # km
            )
    
    return OperationalArea(
        deployment_area=deployment_polygon,
        engagement_area=engagement_polygon,
        support_area=None  # 향후 확장
    )
```

## 13. 구현 계획 및 우선순위

### 13.1 Phase 1: 기본 시각화 (필수) - 1주차

#### 13.1.1 위협 정보 시각화
- [ ] 위협 마커 표시 (MIL-STD-2525D)
  - 위치: 좌표정보 → 지형셀 → 축선 우선순위로 해결
  - 심볼: 위협유형코드 → SIDC 매핑
- [ ] 위협 영향 범위 (Circle)
  - 반경 계산 로직 구현
  - 색상 매핑 (위협 수준별)

#### 13.1.2 아군 부대 정보 시각화
- [ ] 아군 부대 마커 표시 (MIL-STD-2525D)
  - 위치: StatusManager → 좌표정보 → 지형셀 → 축선 우선순위
  - 심볼: 제대 + 병종 → SIDC 매핑
- [ ] 방책별 색상 구분
- [ ] 선택된 방책 강조

### 13.2 Phase 2: 경로 및 영역 (중요) - 2주차

#### 13.2.1 축선 정보 시각화
- [ ] 축선 라인 표시
  - 좌표 해결: 주요지형셀목록 → 지형셀 → 좌표
  - 타입별 스타일 (PRIMARY/SECONDARY/SUPPORT)
- [ ] 축선 라벨 표시

#### 13.2.2 방책 작전 경로
- [ ] 경로 생성 로직 구현
  - 출발지: 아군 부대 위치
  - 경유지: 축선상의 지형셀
  - 목표지: 위협 위치
- [ ] 경로 타입별 스타일 (MOVEMENT/ATTACK/DEFENSE/SUPPORT)

#### 13.2.3 방책 작전 영역
- [ ] 배치 영역 (Polygon)
- [ ] 교전 영역 (Polygon)

#### 13.2.4 추론 경로 시각화
- [ ] 온톨로지 기반 추론 경로 표시
- [ ] 추론 단계별 마커 및 연결선

### 13.3 Phase 3: 고급 기능 (선택) - 3주차

#### 13.3.1 타임라인 기반 동적 표시
- [ ] 타임라인 슬라이더 구현
- [ ] 시간대별 마커 표시/숨김
- [ ] 애니메이션 효과

#### 13.3.2 레이어 토글 기능
- [ ] 레이어 토글 UI 구현
- [ ] 레이어별 표시/숨김 로직

#### 13.3.3 방책 비교 모드
- [ ] 2개 방책 동시 비교
- [ ] 색상 구분 및 강조

## 14. 데이터 검증 및 보완 계획

### 14.1 즉시 확인 필요 사항 (우선순위 1)

#### 14.1.1 좌표 정보 일관성
- [ ] `좌표정보` 필드 형식 표준화
  - 현재: 문자열 형식 (예: "127.0,37.5" 또는 "37.5,127.0")
  - 제안: "경도,위도" 형식으로 통일 (GeoJSON 표준)
  - 파싱 로직: `parse_coordinates()` 함수 구현
- [ ] `X좌표`, `Y좌표` vs `좌표정보` 우선순위 결정
  - 제안: `좌표정보` 우선 (더 정확), `X좌표`, `Y좌표`는 fallback

#### 14.1.2 필드명 통일
- [ ] `전투력지수` vs `전투력
  - 제안: `전투력지수`로 통일 (더 명확)
- [ ] `이동속도` vs `이동속도_kmh`
  - 제안: `이동속도_kmh`로 통일 (단위 명시)
- [ ] `주요지형셀목록` vs `구성지형셀목록`
  - 제안: 실제 파일 확인 후 통일 (excel_columns.json에는 "주요지형셀목록")

#### 14.1.3 데이터 타입 확인
- [ ] `위협수준` 필드 타입 확인
  - 현재: schema_registry.yaml에는 "string"
  - 확인: 실제 데이터가 숫자인지 문자열인지
  - 제안: 숫자로 변환 가능한 경우 숫자 타입으로 통일

### 14.2 추가 데이터 생성 필요 (우선순위 2)

#### 14.2.1 위협유형별 반경 매핑 테이블
**제안**: `위협유형_마스터.xlsx`에 `기본반경_km` 컬럼 추가
```
위협유형코드 | 위협유형명 | 기본반경_km
MISSILE     | 미사일    | 10.0
ARTILLERY   | 포병      | 8.0
ARMOR       | 기갑      | 5.0
INFANTRY    | 보병      | 3.0
AIR         | 공중      | 15.0
NAVAL       | 해상      | 12.0
```

#### 14.2.2 방책 작전 경로 waypoints 생성
**제안**: 백엔드에서 방책 추천 시 `visualization_data.operational_path` 생성
- 출발지: `participating_units`의 부대 위치
- 경유지: `main_axis_id` 기반 축선 좌표
- 목표지: 위협 위치

#### 14.2.3 방책 작전 영역 polygon 생성
**제안**: 백엔드에서 방책 추천 시 `visualization_data.operational_area` 생성
- 배치 영역: 부대 배치 위치 중심 반경 계산
- 교전 영역: 위협 위치와 부대 위치 사이 버퍼 영역

### 14.3 데이터 보완 계획 (우선순위 3)

#### 14.3.1 민간인 지역 Polygon 좌표
- 현재: 지형셀 기반 추론만 가능 (confidence: 0.7)
- 제안: `민간인지역.xlsx`에 `Polygon좌표` 컬럼 추가 또는 별도 GeoJSON 파일

#### 14.3.2 기상 영향 영역
- 현재: `기상상황` 테이블에 지형셀 연결만 존재
- 제안: 기상 영향 영역 Polygon 좌표 추가

#### 14.3.3 배경 적군 필터링
- 현재: `적군부대현황` 테이블에 모든 적군 포함
- 제안: `관련_적부대ID`가 없는 적군은 배경 적군으로 표시 (opacity: 0.5)

## 15. 다음 단계

1. **데이터 검증 및 보완** (1주차):
   - 좌표 정보 일관성 확인 및 표준화
   - 필드명 통일 작업
   - 위협유형별 반경 매핑 테이블 추가

2. **백엔드 데이터 구조 확장** (2주차):
   - `EnhancedCOAVisualizationData` 필드 추가
   - `EnhancedThreatVisualizationData` 필드 추가
   - 방책 작전 경로/영역 생성 로직 구현

3. **프론트엔드 컴포넌트 구현** (3주차):
   - `TacticalMap` 확장
   - 각 레이어별 렌더링 로직 구현
   - 레이어 토글 UI 구현

4. **통합 테스트** (4주차):
   - 전체 시각화 파이프라인 테스트
   - 성능 최적화
   - 사용자 피드백 수집
