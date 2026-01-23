# 위협상황 마커 위치 문제 분석 및 수정

## 문제 현상

위협상황 마커가 항상 지도상에 동일 위치에 나타나는 문제

## 원인 분석

### 1. 데이터 확인 결과

✅ **좌표정보는 정상적으로 존재함**
- 모든 위협상황(THR001~THR010)에 서로 다른 좌표정보가 채워져 있음
- 예: THR001: 127.002824, 37.997618, THR002: 126.983969, 37.991562 등

### 2. 코드 분석 결과

**문제점 발견:**

1. **발생위치셀ID를 통한 지형셀 좌표 조회 로직 부재**
   - `scenario_mapper.py`의 `map_threats_to_geojson()` 함수에서
   - 발생위치셀ID가 있어도 지형셀 Excel 파일에서 좌표를 조회하지 않음
   - 관련축선ID를 통한 축선 좌표 조회는 있지만, 발생위치셀ID는 없음

2. **좌표정보 전달 누락 가능성**
   - `situation_input.py`의 `convert_threat_data_to_situation_info()`에서
   - 좌표정보를 파싱하지만, 원본 "좌표정보" 필드가 `situation_info`에 포함되지 않을 수 있음

3. **StatusManager 우선순위 문제**
   - StatusManager가 우선순위 1이므로, StatusManager에 좌표가 있으면 Excel 좌표정보를 무시
   - StatusManager에 모든 위협이 같은 좌표로 저장되어 있을 가능성

## 수정 사항

### 1. 발생위치셀ID를 통한 지형셀 좌표 조회 추가

**파일**: `ui/components/scenario_mapper.py`

**추가된 로직** (PRIORITY 3):
```python
# [PRIORITY 3] 발생위치셀ID를 통한 지형셀 좌표 조회
if not base_loc and not use_exact_coords:
    cell_id = threat.get("발생위치셀ID") or threat.get("location_cell_id")
    if cell_id:
        # 지형셀 Excel 파일에서 좌표 조회
        terrain_df = pd.read_excel("data_lake/지형셀.xlsx")
        terr_row = terrain_df[terrain_df["지형셀ID"] == cell_id]
        if not terr_row.empty:
            coord_str = terr_row.iloc[0]["좌표정보"]
            # 좌표 파싱 및 base_loc 설정
```

### 2. 좌표정보 필드 명시적 포함

**파일**: `ui/components/situation_input.py`

**수정 사항**:
- `convert_threat_data_to_situation_info()` 함수에서
- `좌표정보` 필드를 명시적으로 `situation_info`에 포함
- `발생위치셀ID` 필드도 명시적으로 포함

### 3. 디버깅 로그 추가

**추가된 로그**:
- StatusManager 좌표 적용 시 로그
- 좌표정보 파싱 성공/실패 로그
- 지형셀 좌표 조회 성공/실패 로그
- 최종 좌표 로깅

## 좌표 결정 우선순위 (수정 후)

1. **StatusManager 실시간 좌표** (최우선)
   - `orchestrator.core.status_manager.get_coordinates(entity_id)`

2. **Excel 좌표정보 컬럼** (PRIORITY 1)
   - `threat.get("좌표정보")` 파싱

3. **개별 위도/경도 컬럼** (PRIORITY 2)
   - `latitude`, `longitude` 등 개별 컬럼

4. **발생위치셀ID → 지형셀 좌표** (PRIORITY 3) ✅ **신규 추가**
   - `발생위치셀ID`를 통해 지형셀 Excel에서 좌표 조회

5. **관련축선ID → 축선 중심점** (PRIORITY 4)
   - 축선의 중간 지점 계산

6. **LOCATION_DB 매핑** (PRIORITY 5)
   - 위협ID나 위치명 기반 매핑

7. **기본값(평양)** (Fallback)
   - 모든 방법 실패 시

## 테스트 방법

1. **위협상황 선택 후 방책 추천 실행**
2. **콘솔 로그 확인**:
   - `[INFO] 좌표정보 컬럼 파싱 성공: THR002 -> 126.983969, 37.991562`
   - `[INFO] 지형셀 기반 위협 위치 조회: THR002 -> TERR006 -> (126.983969, 37.991562)`
   - `[DEBUG] 위협 THR002 최종 좌표: (126.983969, 37.991562)`
3. **지도에서 마커 위치 확인**:
   - 각 위협상황마다 다른 위치에 마커가 표시되어야 함
   - THR001과 THR002가 같은 위치에 있으면 안됨

## 예상 결과

- ✅ 각 위협상황마다 고유한 위치에 마커 표시
- ✅ Excel의 좌표정보가 정확히 반영
- ✅ 발생위치셀ID를 통한 지형셀 좌표 조회 작동
- ✅ 디버깅 로그로 좌표 결정 과정 추적 가능

---

## 추가 수정 사항 (2025-01-08)

### 문제: 위협중심/임무중심 모드별 좌표 오류

1. **위협중심 모드**: 모든 위협이 서울 지역으로 표시됨
2. **임무중심 모드**: 모든 임무가 평양으로 표시됨

### 원인 분석

1. **위협중심 모드**:
   - LOCATION_DB 텍스트 검색이 너무 관대하여 "SEOUL"이 잘못 매칭됨
   - 위협명이나 설명에 "서울"이 포함되면 SEOUL로 매칭되는 문제

2. **임무중심 모드**:
   - `convert_mission_data_to_situation_info()`에서 좌표 정보가 전혀 포함되지 않음
   - 임무 데이터에는 "작전지역"과 "주공축선ID"가 있으나 좌표로 변환되지 않음
   - `map_threats_to_geojson()`에서 임무ID를 인식하지 못함

### 수정 사항

#### 1. LOCATION_DB 텍스트 검색 개선

**파일**: `ui/components/scenario_mapper.py`

- 텍스트 검색을 더 엄격하게 수정
- "SEOUL" 같은 일반적인 단어가 우연히 매칭되는 것을 방지
- 디버깅 로그 추가

#### 2. 임무 중심 모드 좌표 결정 추가

**파일**: `ui/components/situation_input.py`

- `convert_mission_data_to_situation_info()`에서 주공축선ID를 통해 좌표 결정
- 축선의 중간 지점을 임무 위치로 사용
- 축선 실패 시 작전지역을 통해 LOCATION_DB에서 좌표 조회
- `좌표정보`, `latitude`, `longitude` 필드 추가

#### 3. 임무 중심 모드 지원 추가

**파일**: `ui/components/scenario_mapper.py`

- `map_threats_to_geojson()`에서 임무ID도 인식하도록 수정
- `entity_id`, `tid`, `curr_id` 추출 시 `임무ID`, `mission_id`도 포함

### 좌표 결정 우선순위 (임무 중심 모드)

1. **StatusManager 실시간 좌표** (최우선)
2. **Excel 좌표정보 컬럼** (PRIORITY 1)
3. **개별 위도/경도 컬럼** (PRIORITY 2)
4. **주공축선ID → 축선 중심점** (PRIORITY 3) ✅ **임무 중심 모드 신규 추가**
5. **작전지역 → LOCATION_DB** (PRIORITY 4) ✅ **임무 중심 모드 신규 추가**
6. **발생위치셀ID → 지형셀 좌표** (PRIORITY 5)
7. **관련축선ID → 축선 중심점** (PRIORITY 6)
8. **LOCATION_DB 매핑** (PRIORITY 7)
9. **기본값(평양)** (Fallback)

### 테스트 방법

1. **위협중심 모드**:
   - 여러 위협상황 선택 후 방책 추천 실행
   - 각 위협이 서로 다른 위치에 표시되는지 확인
   - 콘솔 로그에서 LOCATION_DB 매칭 과정 확인

2. **임무중심 모드**:
   - 임무 선택 후 방책 추천 실행
   - 임무 위치가 주공축선의 중심점에 표시되는지 확인
   - 콘솔 로그에서 "임무 중심 좌표 결정 (축선 기반)" 메시지 확인
