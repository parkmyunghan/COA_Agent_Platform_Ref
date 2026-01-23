# COP 시각화 통합 테스트 가이드

## 개요

이 문서는 COP 시각화 기능의 통합 테스트를 수행하는 방법을 안내합니다.

## 테스트 환경 설정

### 1. 백엔드 서버 실행

```bash
# 가상환경 활성화
venv\Scripts\activate  # Windows
# 또는
source venv/bin/activate  # Linux/Mac

# 백엔드 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 프론트엔드 개발 서버 실행

```bash
cd frontend
npm install  # 최초 1회만
npm run dev
```

## 테스트 시나리오

### 시나리오 1: 위협 기반 COA 생성 및 시각화

#### 1단계: 위협 선택

1. 프론트엔드에서 "지휘통제 및 방책분석" 페이지 접속
2. "위협 중심" 모드 선택
3. 실제 데이터에서 위협 선택 (예: THR001)

#### 2단계: COA 생성 요청

1. "방책 생성" 버튼 클릭
2. API 응답 확인 (브라우저 개발자 도구 Network 탭)

**확인 사항**:
- `POST /api/v1/coa/generate` 요청 성공
- 응답에 `visualization_data` 필드 포함 여부
- `axis_states`에 `coordinates` 필드 포함 여부

#### 3단계: 시각화 확인

**지도에서 확인할 항목**:

1. **위협 마커**
   - [ ] 위협 위치에 MIL-STD-2525D 심볼 표시
   - [ ] 마커 클릭 시 팝업에 위협 정보 표시

2. **위협 영향 범위**
   - [ ] 위협 위치 주변에 원형 영역 표시
   - [ ] 위협 수준에 따른 색상 확인 (초록→노랑→주황→빨강)
   - [ ] 반경이 위협 유형에 맞게 계산되었는지 확인

3. **아군 부대 마커**
   - [ ] 방책별 색상 구분 확인 (Rank 1: 파란색, Rank 2: 초록색, Rank 3: 보라색)
   - [ ] 선택된 방책의 부대는 빨간색 테두리 및 펄스 효과
   - [ ] MIL-STD-2525D 심볼이 부대 유형에 맞게 표시

4. **축선 라인**
   - [ ] PRIMARY/SECONDARY/SUPPORT 타입별 스타일 확인
   - [ ] 축선 라벨 표시 확인

5. **방책 작전 경로**
   - [ ] 출발지 → 경유지 → 목표지 경로 표시
   - [ ] 경로 타입별 색상 확인 (MOVEMENT: 파란색, ATTACK: 빨간색 등)

6. **방책 작전 영역**
   - [ ] 배치 영역 Polygon 표시
   - [ ] 교전 영역 Polygon 표시 (위협이 있는 경우)

7. **레이어 토글**
   - [ ] 우측 상단 레이어 토글 패널 표시
   - [ ] 각 레이어 켜기/끄기 동작 확인

### 시나리오 2: 임무 기반 COA 생성 및 시각화

1. "임무 중심" 모드 선택
2. 실제 데이터에서 임무 선택
3. COA 생성 및 시각화 확인 (시나리오 1과 동일)

## API 응답 검증

### COA 응답 구조 확인

브라우저 개발자 도구에서 다음 구조 확인:

```json
{
  "coas": [
    {
      "coa_id": "...",
      "coa_name": "...",
      "rank": 1,
      "visualization_data": {
        "operational_path": {
          "waypoints": [[lng, lat], ...],
          "path_type": "ATTACK" | "DEFENSE" | "MOVEMENT" | "SUPPORT"
        },
        "operational_area": {
          "deployment_area": {
            "polygon": [[lng, lat], ...],
            "description": "..."
          },
          "engagement_area": {
            "polygon": [[lng, lat], ...],
            "description": "..."
          }
        }
      }
    }
  ],
  "axis_states": [
    {
      "axis_id": "...",
      "axis_name": "...",
      "axis_type": "PRIMARY" | "SECONDARY" | "SUPPORT",
      "coordinates": [[lat, lng], ...],
      "geojson": {
        "type": "LineString",
        "coordinates": [[lng, lat], ...]
      }
    }
  ]
}
```

## 문제 해결

### 위협 영향 범위가 표시되지 않는 경우

**원인**:
- 위협 수준 필드가 문자열일 수 있음
- 위협 위치를 찾을 수 없음

**해결**:
1. 브라우저 콘솔에서 오류 메시지 확인
2. 위협 데이터의 `위협수준` 필드 타입 확인
3. `발생위치셀ID` 또는 `좌표정보` 필드 존재 여부 확인

### 축선이 표시되지 않는 경우

**원인**:
- `axis_states`에 좌표 정보가 없음
- `주요지형셀목록` 필드가 비어있음

**해결**:
1. API 응답에서 `axis_states[].coordinates` 확인
2. 백엔드 로그에서 축선 좌표 해결 로그 확인
3. `전장축선.xlsx`의 `주요지형셀목록` 필드 확인

### 작전 경로가 표시되지 않는 경우

**원인**:
- 참여 부대 위치 정보 부족
- 위협 위치 정보 부족

**해결**:
1. API 응답에서 `visualization_data.operational_path` 확인
2. 참여 부대의 `좌표정보` 또는 `배치지형셀ID` 확인
3. 위협의 `발생위치셀ID` 확인

### 작전 영역이 표시되지 않는 경우

**원인**:
- 참여 부대 위치 정보 부족
- 위협 위치 정보 부족

**해결**:
1. API 응답에서 `visualization_data.operational_area` 확인
2. 참여 부대 위치 정보 확인
3. 위협 위치 정보 확인

## 수동 테스트 체크리스트

### 기본 기능
- [ ] 위협 마커 표시
- [ ] 위협 영향 범위 Circle 표시
- [ ] 아군 부대 마커 표시
- [ ] 축선 라인 표시
- [ ] 방책 작전 경로 표시
- [ ] 방책 작전 영역 표시
- [ ] 레이어 토글 동작

### 상호작용
- [ ] 마커 클릭 시 팝업 표시
- [ ] 방책 선택 시 강조 표시
- [ ] 레이어 토글 시 즉시 반영

### 데이터 검증
- [ ] 위협 수준에 따른 영향 범위 색상 변경
- [ ] 방책 Rank에 따른 색상 구분
- [ ] 축선 타입에 따른 스타일 구분
- [ ] 경로 타입에 따른 스타일 구분

## 자동화 테스트 스크립트

### 백엔드 테스트

```bash
# 프로젝트 루트에서 실행
python scripts/test_cop_visualization.py
python scripts/test_cop_integration_simple.py
```

### 프론트엔드 테스트

```bash
cd frontend
npm test  # 테스트가 설정되어 있는 경우
```

## 성능 테스트

### 많은 마커가 있을 때

1. 많은 위협/부대가 있는 시나리오 선택
2. 지도 줌 인/아웃 시 성능 확인
3. 레이어 토글 시 렌더링 속도 확인

### 권장 사항

- 마커가 50개 이상일 때 클러스터링 고려
- 보이는 영역만 렌더링하는 가상화 고려

## 참고 자료

- 설계 문서: `docs/40_Refactoring/cop_visualization_design.md`
- 구현 요약: `docs/40_Refactoring/cop_visualization_implementation_summary.md`
- 테스트 보고서: `docs/40_Refactoring/cop_visualization_test_report.md`
- 데이터 검증 계획: `docs/30_Guides/Data_Validation_Plan.md` (10장)
