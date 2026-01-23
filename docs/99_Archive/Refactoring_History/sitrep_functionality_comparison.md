# SITREP 입력 기능 중복 분석

## 개요
현재 시스템에 두 가지 SITREP 입력 기능이 존재합니다. 이 문서는 두 기능의 중복 여부와 차이점을 분석합니다.

## 기능 비교

### 1. 위협 식별 및 분석 (Threat Analysis) 패널
- **위치**: 좌측 사이드바, `ThreatAnalysisPanel` 컴포넌트
- **입력창**: SITREP 텍스트 입력 (textarea, min-h-[100px])
- **버튼**: "유사도 분석 및 식별 실행"
- **API**: `POST /api/v1/threat/analyze`
- **결과 처리**:
  - `ThreatEventBase` 객체 반환
  - `onThreatIdentified` 콜백 호출 → `setSelectedThreat(t)`
  - `refetch()` 호출하여 시스템 데이터 새로고침
  - 패널 내부에 분석 결과 표시 (위협 ID, 유형, 신뢰도, 위치, 발생시간)
- **용도**: 위협 중심 접근 방식
  - 위협을 식별하고 `selectedThreat` 상태에 설정
  - 이후 방책 추천 시 이 위협 정보 사용

### 2. 상황정보 설정 - SITREP 텍스트 입력 모드
- **위치**: 좌측 사이드바, `SituationInputPanel` 컴포넌트 내부
- **입력창**: SITREP 텍스트 입력 (Textarea, rows={5})
- **버튼**: "SITREP 분석 실행"
- **API**: `POST /api/v1/threat/analyze` (동일)
- **결과 처리**:
  - `threatData` 받아서 `updateSituation()`으로 상황 정보에 반영
  - `onSituationChange` 콜백 호출 → `setSituationInfo`
  - `alert()`로 성공 메시지 표시
  - 상황 정보 객체에 위협 정보 포함하여 저장
- **용도**: 상황 정보 전체 설정
  - 위협 정보를 포함한 전체 상황 정보(`situationInfo`) 설정
  - 방책 추천 시 `situationInfo` 사용

## 중복 분석

### 공통점
1. **동일한 API 사용**: 둘 다 `/api/v1/threat/analyze` 엔드포인트 사용
2. **동일한 파싱 로직**: 백엔드에서 같은 `parse_sitrep_to_threat` 메서드 사용
3. **동일한 입력 형식**: SITREP 텍스트 입력
4. **동일한 추출 정보**: 위협 유형, 수준, 위치, 축선 등 동일한 정보 추출

### 차이점

| 항목 | ThreatAnalysisPanel | SituationInputPanel (SITREP 모드) |
|------|---------------------|-----------------------------------|
| **상태 관리** | `selectedThreat` (위협만) | `situationInfo` (전체 상황 정보) |
| **결과 표시** | 패널 내부 상세 표시 | Alert 메시지 + 상황 정보에 반영 |
| **데이터 새로고침** | `refetch()` 호출 | 없음 |
| **컨텍스트** | 위협 중심 | 상황 정보 전체 |
| **입력창 크기** | min-h-[100px] | rows={5} (더 큼) |

## 중복 여부 판단

### 결론: **부분적 중복**

두 기능은 **기술적으로는 동일한 API와 파싱 로직을 사용**하지만, **사용 목적과 결과 처리 방식이 다릅니다**:

1. **ThreatAnalysisPanel**: 
   - 위협을 **독립적으로 식별**하는 용도
   - 위협 정보만 별도로 관리 (`selectedThreat`)
   - 위협 중심 접근 방식에 적합

2. **SituationInputPanel (SITREP 모드)**:
   - **전체 상황 정보**를 설정하는 용도
   - 위협 정보를 포함한 종합 상황 정보 관리 (`situationInfo`)
   - 상황 정보 입력의 한 방법으로 제공

### 문제점

1. **사용자 혼란 가능성**:
   - 같은 기능이 두 곳에 있어 어떤 것을 사용해야 할지 혼란스러울 수 있음
   - 버튼 이름이 다름 ("유사도 분석 및 식별 실행" vs "SITREP 분석 실행")

2. **데이터 동기화 이슈**:
   - `ThreatAnalysisPanel`에서 분석한 위협이 `selectedThreat`에만 설정됨
   - `SituationInputPanel`에서 분석한 위협이 `situationInfo`에만 반영됨
   - 두 상태가 서로 동기화되지 않을 수 있음

3. **UI 복잡도 증가**:
   - 같은 기능이 두 곳에 있으면 UI가 복잡해짐
   - 사용자가 어느 것을 사용해야 할지 판단해야 함

## 개선 방안 제안

### 옵션 1: ThreatAnalysisPanel 제거 (권장)
- **이유**: `SituationInputPanel`의 SITREP 모드가 더 포괄적이고 통합적
- **장점**: 
  - UI 단순화
  - 데이터 일관성 향상
  - 사용자 혼란 감소
- **단점**: 
  - 위협만 빠르게 식별하고 싶을 때 불편할 수 있음

### 옵션 2: SituationInputPanel의 SITREP 모드 제거
- **이유**: `ThreatAnalysisPanel`이 더 명확한 목적을 가짐
- **장점**: 
  - 위협 식별에 특화
  - 결과 표시가 더 상세함
- **단점**: 
  - 상황 정보 입력의 다른 방법(수동 입력, 시나리오 등)과의 일관성 저하

### 옵션 3: 통합 (권장)
- **방법**: `ThreatAnalysisPanel`에서 분석한 결과를 `situationInfo`에도 자동 반영
- **장점**: 
  - 두 기능 모두 유지하면서 데이터 동기화
  - 사용자가 원하는 방식으로 사용 가능
- **구현**:
  ```typescript
  <ThreatAnalysisPanel 
    onThreatIdentified={(t) => { 
      setSelectedThreat(t); 
      // situationInfo에도 자동 반영
      setSituationInfo(prev => ({
        ...prev,
        threat_type: t.threat_type_code,
        threat_level: t.threat_level,
        location: t.location_cell_id,
        axis_id: t.related_axis_id,
        ...t
      }));
      refetch(); 
    }} 
  />
  ```

### 옵션 4: 기능 차별화
- **ThreatAnalysisPanel**: 위협 빠른 식별 및 검증용 (결과 상세 표시)
- **SituationInputPanel**: 전체 상황 정보 설정용 (다양한 입력 방법 제공)
- **장점**: 각각의 명확한 역할
- **단점**: 여전히 중복 기능 존재

## 권장 사항

**옵션 3 (통합)**을 권장합니다:
1. 두 기능 모두 유지 (사용자 선택권 제공)
2. `ThreatAnalysisPanel`에서 분석한 결과를 `situationInfo`에도 자동 반영
3. 데이터 일관성 확보
4. 사용자 혼란 최소화

또는 **옵션 1 (ThreatAnalysisPanel 제거)**도 고려 가능:
- `SituationInputPanel`의 SITREP 모드가 더 포괄적
- UI 단순화
- 데이터 일관성 향상
