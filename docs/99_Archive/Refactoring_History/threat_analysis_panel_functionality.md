# 위협 식별 및 분석 (Threat Analysis) 패널 기능 설명

## 개요
좌측 사이드바의 "위협 식별 및 분석 (Threat Analysis)" 영역은 SITREP(상황보고) 텍스트를 입력받아 자동으로 구조화된 위협상황 정보로 변환하는 기능을 제공합니다.

## 위치
- **컴포넌트**: `frontend/src/components/ThreatAnalysisPanel.tsx`
- **페이지**: `frontend/src/pages/CommandControlPage.tsx` (좌측 사이드바)
- **API 엔드포인트**: `POST /api/v1/threat/analyze`

## 주요 기능

### 1. SITREP 입력창
- **용도**: 상황보고(SITREP) 텍스트를 입력받는 텍스트 영역
- **예시 입력**:
  ```
  적 전차대대가 00지역에서 남하하는 징후 식별...
  적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음
  ```
- **특징**:
  - 최소 높이 100px의 텍스트 영역
  - 자유 형식의 자연어 텍스트 입력 가능

### 2. "유사도 분석 및 식별 실행" 버튼
- **기능**: 입력된 SITREP 텍스트를 분석하여 구조화된 위협상황 정보로 변환
- **동작 과정**:
  1. 사용자가 SITREP 텍스트 입력
  2. 버튼 클릭 시 `/api/v1/threat/analyze` API 호출
  3. 백엔드에서 LLM을 사용하여 텍스트 분석
  4. 구조화된 `ThreatEvent` 객체로 변환
  5. 분석 결과를 화면에 표시
  6. `onThreatIdentified` 콜백을 통해 상위 컴포넌트에 전달

## 백엔드 처리 로직

### API 엔드포인트
- **경로**: `POST /api/v1/threat/analyze`
- **요청 형식**:
  ```json
  {
    "sitrep_text": "적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음",
    "mission_id": "MSN001" // 선택적
  }
  ```

### 파싱 프로세스
1. **LLM 기반 파싱** (기본):
   - `SITREPParser._parse_with_llm()` 메서드 사용
   - LLM을 통해 자연어 텍스트를 구조화된 JSON으로 변환
   - 최대 3회 재시도 로직 포함

2. **규칙 기반 파싱** (LLM 사용 불가 시):
   - `SITREPParser._parse_with_rules()` 메서드 사용
   - 키워드 매칭을 통한 기본 파싱

### 추출되는 정보
LLM 파싱을 통해 다음 정보를 추출합니다:

1. **위협 유형 (threat_type_code)**
   - ARMOR (전차/기갑)
   - ARTILLERY (포병)
   - INFANTRY (보병)
   - AIR (항공)
   - MISSILE (미사일)
   - INFILTRATION (침투)
   - CBRN (화생방)
   - CYBER (사이버)
   - UNKNOWN (미상)

2. **위협 수준 (threat_level)**
   - High (높음)
   - Medium (보통)
   - Low (낮음)

3. **위치 정보 (location_cell_id)**
   - TERR001, GRID_1234 등의 지형셀 ID
   - 텍스트에서 지명이나 ID 추출

4. **관련 축선 (related_axis_id)**
   - 키워드 매핑:
     - "동부 주공축선" / "동부" / "주공축선" / "주공" → "AXIS01"
     - "서부 조공축선" / "서부" / "조공축선" / "조공" → "AXIS02"
     - "북부" / "북쪽" → "AXIS03"
     - "남부" / "남쪽" → "AXIS04"
   - 키워드가 없으면 `null`

5. **적 부대 정보 (related_enemy_unit_id)**
   - "적 전차부대", "적군 기갑부대" 등 언급 시 "ENU_ESTIMATED"
   - 구체적인 부대ID가 있으면 그대로 사용

6. **발생 시각 (occurrence_time)**
   - HH:MM 또는 YYYY-MM-DD HH:MM:SS 형식

7. **신뢰도 (confidence)**
   - 0-100 숫자

8. **원문 텍스트 (raw_report_text)**
   - 입력된 SITREP 텍스트 그대로 저장

## 반환 결과

### 성공 시
- 분석 결과가 패널 하단에 표시됨:
  - 위협 ID
  - 위협 유형
  - 신뢰도
  - 위치
  - 발생시간
- `onThreatIdentified` 콜백을 통해 `CommandControlPage`의 `selectedThreat` 상태가 업데이트됨
- 시스템 데이터가 자동으로 새로고침됨 (`refetch()`)

### 실패 시
- 에러 메시지가 빨간색 박스로 표시됨
- 콘솔에 에러 로그 출력

## 사용 시나리오

1. **사용자가 SITREP 텍스트 입력**
   ```
   적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음
   ```

2. **"유사도 분석 및 식별 실행" 버튼 클릭**

3. **분석 결과 표시**
   - 위협 ID: THREAT_20260111_131500
   - 유형: ARMOR (전차)
   - 신뢰도: 80%
   - 위치: (추출된 경우)
   - 발생시간: (추출된 경우)

4. **자동 연동**
   - 분석된 위협이 `selectedThreat`로 설정됨
   - 이후 방책 추천 시 이 위협 정보가 사용됨

## 관련 컴포넌트 및 파일

- **프론트엔드**:
  - `frontend/src/components/ThreatAnalysisPanel.tsx`
  - `frontend/src/pages/CommandControlPage.tsx`
  - `frontend/src/types/schema.ts` (ThreatAnalyzeRequest, ThreatEventBase)

- **백엔드**:
  - `api/routers/threat.py` (API 엔드포인트)
  - `core_pipeline/coa_service.py` (parse_sitrep_to_threat 메서드)
  - `core_pipeline/coa_engine/llm_services.py` (SITREPParser 클래스)

## 참고사항

- 이 기능은 `SituationInputPanel`의 "SITREP 텍스트 입력" 모드와 유사한 기능을 제공하지만, 별도의 독립적인 패널로 구현되어 있습니다.
- LLM이 사용 불가능한 경우 규칙 기반 파싱으로 자동 전환됩니다.
- 분석 결과는 위협상황 테이블에 자동으로 저장되지 않으며, 현재 세션에서만 사용됩니다.
