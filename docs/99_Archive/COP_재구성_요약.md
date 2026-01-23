# COP 재구성 요약

## ✅ 완료된 작업

### 1. 핵심 원칙 구현
- ✅ COP를 "온톨로지 추론 결과를 공간적으로 검증하는 지휘 인터페이스"로 재정의
- ✅ 지도는 배경으로 사용, 핵심은 COA 판단과 설명
- ✅ 모든 전술 객체에 온톨로지 URI 포함

### 2. 컴포넌트 생성
- ✅ `ontology_aware_cop_leaflet.py`: 온톨로지 인식 COP 컴포넌트
- ✅ `ontology_cop_mapper.py`: 온톨로지 COP 매퍼

### 3. 데이터 구조 개선
- ✅ `scenario_mapper.py`: 온톨로지 URI 및 3계층 정보 추가
  - Unit: 정적 정보, 동적 상태, 추론 연계 정보
  - Threat: threat_type, confidence, affected_coa
  - COA: participating_units, exposed_threats, success_probability

### 4. UI 구조
- ✅ 좌측 패널: 상황 요약
- ✅ 우측 패널: 추론 근거 (COA 선택 시)
- ✅ 하단 패널: COA 비교 모드

### 5. 통합
- ✅ `agent_execution.py`: 새로운 COP 컴포넌트 통합
- ✅ COA 추천 결과가 있을 때 자동으로 온톨로지 인식 COP 표시

## 📁 생성/수정된 파일

### 새로 생성
1. `ui/components/ontology_aware_cop_leaflet.py`
2. `ui/components/ontology_cop_mapper.py`
3. `docs/COP_재구성_완료.md`

### 수정
1. `ui/components/scenario_mapper.py`
2. `ui/views/agent_execution.py`
3. `scripts/download_offline_assets.py` (MapLibre GL JS 추가)

## 🎯 주요 기능

### Unit 표현
- MIL-STD-2525D 부호 사용
- 클릭 시 3계층 정보 표시
- 온톨로지 URI 표시

### Threat 표현
- 개념 객체로 표현 (단순 반경 금지)
- 위협 유형에 따라 다른 스타일
- affected_coa 배열 포함

### COA 가시화
- 집합으로 표현 (경로, 부대, 위협, 점수)
- 복수 COA 비교 모드
- 추론 근거 표시

## 💡 사용 방법

1. Agent 실행 페이지에서 방책 추천 실행
2. COA 추천 결과가 있으면 자동으로 온톨로지 인식 COP 표시
3. 하단 패널에서 COA 선택
4. 우측 패널에서 추론 근거 확인
5. 지도에서 Unit/Threat 클릭하여 상세 정보 확인

## 🔄 향후 개선 사항

1. MapLibre GL JS 전환 (MBTiles 벡터 타일 직접 지원)
2. COA 선택 시 위협 강조 기능
3. 시간 흐름/단계 전환 슬라이더
4. 온톨로지 추론 경로 그래프 시각화

