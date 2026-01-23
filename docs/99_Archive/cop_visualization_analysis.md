# COP 시각화 로직 근본 분석 보고서

## 📋 개요

COP(Common Operational Picture) 전술상황도의 위협상황 및 방책 시각화 로직에 대한 전반적인 분석을 수행하여, 설계대로 동작하지 않는 근본 원인을 파악하고 개선 방향을 제시합니다.

## 🔍 현재 시각화 아키텍처

### 1. 데이터 흐름 (Data Flow)

```
[상황 선택] → [Agent 실행] → [COA 추천 생성] → [GeoJSON 변환] → [Map 렌더링]
     ↓              ↓                ↓                  ↓                 ↓
session_state  orchestrator   coa_recommendations  ScenarioMapper   tactical_map.py
```

### 2. 핵심 컴포넌트

#### 2.1 데이터 생성 계층
- **agent_execution.py** (lines 527-916)
  - 역할: UI 상태 관리, 데이터 취합
  - 위협 데이터: `threat_geojson` (line 529)
  - 방책 데이터: `coa_geojson` (line 530)
  - 추천 목록: `coa_recommendations` (line 531)

#### 2.2 데이터 변환 계층
- **scenario_mapper.py** (전체 971 lines)
  - `map_threats_to_geojson()` (lines 153-318): 위협 → GeoJSON
  - `map_coa_to_geojson()` (lines 320-637): 방책 → GeoJSON
  - `map_reasoning_to_geojson()` (lines 668-760): 추론 → GeoJSON

#### 2.3 시각화 계층
- **tactical_map.py** (720 lines)
  - `render_tactical_map()`: Leaflet 기반 지도 렌더링

#### 2.4 보조 컴포넌트
- **ontology_cop_mapper.py** (233 lines)
  - 온톨로지 기반 데이터 보강
  - 현재 **사용되지 않음**

## ❌ 발견된 문제점

### 문제 #1: 데이터 파이프라인 단절

#### 현상
- `agent_execution.py`에서 GeoJSON 생성은 정상 동작
- **ontology_cop_mapper.py는 전혀 호출되지 않음**
- 로그에 GeoJSON 관련 디버그 출력 없음

#### 원인 분석

**agent_execution.py의 데이터 생성 로직 (lines 545-667):**

```python
# 1. 위협 GeoJSON 생성 (✓ 정상)
all_threats = []  # 전체 위협 로드
threat_geojson = ScenarioMapper.map_threats_to_geojson(all_threats, orchestrator, selected_id=selected_id)

# 2. 방책 GeoJSON 생성 (⚠️ 문제 발생)
if coa_recommendations:
    all_coa_features = []
    for idx, coa in enumerate(coa_recommendations):
        coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson)
        # features 병합
```

**핵심 문제:**
1. `ScenarioMapper.map_coa_to_geojson()`에 **orchestrator가 전달되지 않음**
2. 이로 인해 **StatusManager 기반 좌표 조회 실패**
3. **축선(Axis) 정보 해결 실패**

#### 코드 증거

**scenario_mapper.py line 321:**
```python
def map_coa_to_geojson(coa: Dict, threat_features: Dict, orchestrator: Any = None) -> Dict:
    # orchestrator 파라미터 존재하나, agent_execution.py에서 전달 안 함!
```

**agent_execution.py line 653:**
```python
coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson)
# orchestrator 누락! ← 근본 원인
```

### 문제 #2: 좌표 없는 시각화 요소

#### 현상
- 방책(COA)의 축선(Axis), 이동 경로 등이 표시되지 않음
- 부대 위치가 기본값으로만 표시

#### 원인

**scenario_mapper.py의 좌표 결정 우선순위 (lines 377-423):**

```python
# 1순위: StatusManager (실시간 좌표) ← orchestrator 필요!
if orchestrator:
    status_coords = orchestrator.core.status_manager.get_coordinates(unit_id)
    if status_coords:
        pos = [status_coords[1], status_coords[0]]
    else:
        # 2순위: COA별 고정 오프셋 (Fallback)
        
# orchestrator가 없으면 → 항상 Fallback 사용
```

**축선 해결 로직 (lines 457-492):**

```python
main_axis_id = vis_data.get("main_axis_id")
if main_axis_id:
    coordinates, axis_meta = ScenarioMapper._resolve_axis_coordinates(main_axis_id)
    # 엑셀 데이터 기반 축선 좌표 해결
    # ✓ 이 부분은 정상 동작 (orchestrator 불필요)
```

### 문제 #3: 온톨로지 데이터 활용 부재

#### 현상
- `ontology_cop_mapper.py`가 임포트는 되지만 사용되지 않음

#### 발견 사항

**agent_execution.py에서:**
```python
# ✗ OntologyCOPMapper 임포트 없음
# ✗ enhance_threat_data_with_ontology() 호출 없음
# ✗ map_coa_recommendations_to_cop_data() 호출 없음
```

**ontology_cop_mapper.py 용도:**
- 온톨로지에서 위협/COA 메타데이터 추출
- 추론 경로(`reasoning_path`) 생성
- **현재 완전히 미사용 상태**

### 문제 #4: 실시간 데이터 동기화

#### 현상
- StatusManager에 저장된 실시간 좌표가 반영되지 않음

#### 원인
- **orchestrator 미전달로 StatusManager 접근 불가**
- 결과: 모든 시각화가 정적 Fallback 데이터 사용

## 🔧 개선 방안

### 즉시 조치 (Critical Fix)

#### Fix #1: orchestrator 전달

**agent_execution.py line 653 수정:**
```python
# 기존 (❌)
coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson)

# 수정 (✅)
coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson, orchestrator)
```

**적용 위치:** `agent_execution.py` lines 649-667

**예상 효과:**
- ✅ StatusManager 기반 실시간 좌표 적용
- ✅ 축선(Axis) 정상 해결
- ✅ 부대 위치 정확도 향상

#### Fix #2: 디버그 로깅 추가

**scenario_mapper.py에 디버그 출력 추가:**
```python
def map_coa_to_geojson(coa: Dict, threat_features: Dict, orchestrator: Any = None) -> Dict:
    print(f"[DEBUG] map_coa_to_geojson called: coa_id={coa.get('coa_id')}, orchestrator={'✓' if orchestrator else '✗'}")
    
    # ... 기존 로직
    
    if main_axis_id:
        coordinates, axis_meta = ScenarioMapper._resolve_axis_coordinates(main_axis_id)
        print(f"[DEBUG] Axis resolved: {main_axis_id} → {len(coordinates)} points")
```

### 단기 개선 (Enhancement)

#### Enhancement #1: ontology_cop_mapper 통합

**agent_execution.py에 추가:**
```python
from ui.components.ontology_cop_mapper import OntologyCOPMapper

# 위협 데이터 보강
threat_geojson = OntologyCOPMapper.enhance_threat_data_with_ontology(
    threat_geojson, 
    orchestrator.core.ontology_manager
)
```

#### Enhancement #2: 좌표 검증 로직

**scenario_mapper.py에 검증 추가:**
```python
def _validate_coordinates(coordinates: List, entity_id: str):
    """좌표 유효성 검증"""
    if not coordinates or len(coordinates) == 0:
        print(f"[WARN] No coordinates for {entity_id}")
        return False
    
    for coord in coordinates:
        if not (isinstance(coord, (list, tuple)) and len(coord) == 2):
            print(f"[ERROR] Invalid coordinate format: {coord}")
            return False
            
        lat, lng = coord
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            print(f"[ERROR] Out of range: lat={lat}, lng={lng}")
            return False
    
    return True
```

### 장기 개선 (Refactoring)

#### Refactor #1: 시각화 파이프라인 단순화

**현재 구조:**
```
agent_execution → ScenarioMapper (직접 호출) → tactical_map
```

**개선 구조:**
```
agent_execution → OntologyCOPMapper → ScenarioMapper → tactical_map
                        ↓
                  (데이터 보강, 검증, 변환 통합)
```

#### Refactor #2: 데이터 모델 표준화

**COA 데이터 모델 정의:**
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class COAVisualizationData:
    coa_id: str
    coa_name: str
    coa_type: str
    
    # 필수 좌표 정보
    main_axis_coords: List[List[float]]  # [[lat, lng], ...]
    unit_positions: List[Dict]  # [{"unit_id": "...", "pos": [lng, lat]}]
    
    # 메타데이터
    visualization_data: Dict
    reasoning_trace: List[str]
    
    # 검증 메서드
    def validate(self) -> bool:
        return (self.main_axis_coords is not None 
                and len(self.main_axis_coords) > 0)
```

## 📊 테스트 계획

### 테스트 시나리오

#### 시나리오 #1: 기본 시각화
1. 위협 THR001 선택
2. COA 추천 실행
3. 검증:
   - [ ] 위협 아이콘 표시
   - [ ] 방책 축선 표시
   - [ ] 부대 마커 표시

#### 시나리오 #2: 다중 위협
1. 여러 위협 동시 표시
2. 검증:
   - [ ] 모든 위협 표시
   - [ ] 선택된 위협 강조
   - [ ] 충돌 없음

#### 시나리오 #3: 실시간 업데이트
1. 상황 변경
2. 검증:
   - [ ] 지도 즉시 갱신
   - [ ] 기존 마커 삭제
   - [ ] 새 데이터 표시

## 🎯 우선순위 액션 아이템

### P0 (즉시 수정 필요)
1. ✅ [Fix #1] `orchestrator` 파라미터 전달
   - 파일: `agent_execution.py`
   - 라인: 653
   - 예상 소요: 5분

### P1 (금주 내 수정)
2. ✅ [Fix #2] 디버그 로깅 추가
   - 파일: `scenario_mapper.py`
   - 다수 함수
   - 예상 소요: 30분

3. ✅ [Enhancement #1] ontology_cop_mapper 통합
   - 파일: `agent_execution.py`
   - 새 임포트 + 함수 호출
   - 예상 소요: 1시간

### P2 (차주 내 수정)
4. [Enhancement #2] 좌표 검증 로직
   - 파일: `scenario_mapper.py`
   - 새 함수 추가
   - 예상 소요: 2시간

5. [Refactor #1,#2] 아키텍처 개선
   - 다수 파일
   - 예상 소요: 1일

## 📝 결론

### 핵심 문제
**`orchestrator`가 시각화 파이프라인에 전달되지 않아, 실시간 좌표 정보를 활용할 수 없는 상태**

### 근본 원인
1. `agent_execution.py` line 653에서 `orchestrator` 미전달
2. `ontology_cop_mapper.py` 완전 미사용
3. 디버깅 로그 부재로 문제 파악 어려움

### 해결 방향
1. **즉시 조치**: orchestrator 전달 (1줄 수정)
2. **단기 개선**: 디버그 로깅 + 데이터 검증
3. **장기 리팩토링**: 파이프라인 재설계 + 모델 표준화

### 예상 효과
- ✅ 설계대로 시각화 동작
- ✅ 실시간 좌표 반영
- ✅ 축선/부대 정확 표시
- ✅ 디버깅 용이성 향상

---

**작성일**: 2026-01-08  
**작성자**: AI Assistant  
**버전**: 1.0
