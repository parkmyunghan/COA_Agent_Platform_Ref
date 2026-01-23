# COP 시각화 긴급 수정 완료 보고서

## 📅 수정 일시
2026-01-08 09:28 KST

## ✅ 적용된 수정 사항

### 1. Critical Fix: orchestrator 파라미터 전달

**파일**: `ui/views/agent_execution.py`  
**라인**: 653 → 655

#### Before (문제)
```python
coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson)
```

#### After (수정)
```python
# ✅ orchestrator 전달 - StatusManager 좌표, 축선 해결 활성화
coa_geo = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson, orchestrator)
```

#### 효과
- ✅ StatusManager를 통한 실시간 좌표 조회 가능
- ✅ 축선(Axis) 데이터 정상 해결
- ✅ 부대 위치 정확도 대폭 향상
- ✅ visualization_data 정상 처리

---

### 2. 디버그 로깅 추가

#### 2.1 agent_execution.py
**위치**: COA GeoJSON 생성 루프

```python
# COA별 feature 생성 추적
coa_id = coa.get("coa_id") or coa.get("id") or f"COA_{idx+1}"
feature_count = len(coa_geo.get("features", [])) if coa_geo else 0
print(f"[COP-VIZ] COA {coa_id}: Generated {feature_count} features")

# 전체 feature 카운트
print(f"[COP-VIZ] Total COA features generated: {len(all_coa_features)}")
```

#### 2.2 scenario_mapper.py - 함수 진입점
**위치**: `map_coa_to_geojson()` 시작 부분

```python
coa_id = coa.get("coa_id") or coa.get("id") or "Unknown"
has_orchestrator = orchestrator is not None
print(f"[ScenarioMapper] map_coa_to_geojson: coa_id={coa_id}, orchestrator={'✓' if has_orchestrator else '✗'}")
```

#### 2.3 scenario_mapper.py - visualization_data 처리
**위치**: 축선 해결 로직

```python
# visualization_data 존재 확인
print(f"[ScenarioMapper] COA {coa_id} visualization_data: {bool(vis_data)}, keys: {list(vis_data.keys()) if vis_data else []}")

# 축선 해결 추적
if main_axis_id:
    print(f"[ScenarioMapper] COA {coa_id} references axis: {main_axis_id}")
    # ... 해결 시도
    print(f"[ScenarioMapper] ✅ Rendered axis {main_axis_id} ({axis_name}) with {len(coordinates)} waypoints")
else:
    print(f"[ScenarioMapper] No main_axis_id found for COA {coa_id}")
```

---

## 🎯 기대 효과

### 즉시 효과
1. **실시간 좌표 반영**: StatusManager에 등록된 위협/부대 좌표가 COP에 즉시 반영
2. **축선 시각화 복원**: 방책의 주공/조공 축선이 지도에 정상 표시
3. **부대 배치 정확도**: Fallback 기본값 대신 실제 배치 위치 사용

### 디버깅 효과
4. **문제 추적 용이**: 로그를 통해 각 단계의 데이터 흐름 확인 가능
5. **빠른 이슈 해결**: 향후 시각화 문제 발생 시 로그만으로 원인 파악

---

## 📊 테스트 방법

### 1. 즉시 확인
Streamlit 앱이 실행 중이므로, 브라우저를 새로고침하고:

1. **위협 상황 선택** (예: THR002)
2. **방책 추천 실행**
3. **COP 맵 확인**:
   - [ ] 위협 마커 표시
   - [ ] 방책 축선 표시 (파란색 점선)
   - [ ] 부대 위치 표시
   - [ ] 이동 경로 표시

### 2. 로그 확인
터미널 또는 로그 파일에서 다음 메시지 확인:

```
[COP-VIZ] COA COA_Library_COA_DET_001: Generated X features
[ScenarioMapper] map_coa_to_geojson: coa_id=COA_Library_COA_DET_001, orchestrator=✓
[ScenarioMapper] COA COA_Library_COA_DET_001 visualization_data: True, keys: ['main_axis_id', ...]
[ScenarioMapper] ✅ Rendered axis AXIS01 (서부축선) with 5 waypoints
```

### 3. 비교 테스트
- **이전**: 축선 없음, 부대가 항상 고정 위치
- **현재**: 축선 표시, 부대가 실제 위치 또는 COA별 차별화된 위치

---

## 🔄 다음 단계

### P1 (이번 주 내)
- [ ] **Enhancement #1**: ontology_cop_mapper 통합
  - 위협 데이터에 온톨로지 메타데이터 추가
  - reasoning_path 시각화

### P2 (다음 주)
- [ ] **Enhancement #2**: 좌표 검증 로직
  - 유효하지 않은 좌표 필터링
  - 범위 체크 (위도/경도)

### P3 (장기)
- [ ] **Refactoring**: 시각화 파이프라인 재설계
  - 데이터 모델 표준화
  - 테스트 커버리지 확대

---

## 📝 변경 파일 목록

1. ✅ `ui/views/agent_execution.py` (중요도: 최상)
   - orchestrator 전달 추가
   - 디버그 로깅 추가

2. ✅ `ui/components/scenario_mapper.py` (중요도: 상)
   - 함수 진입점 로깅
   - 축선 해결 로깅
   - visualization_data 추적

3. ✅ `docs/cop_visualization_analysis.md` (참조)
   - 전체 분석 보고서

4. ✅ `docs/cop_visualization_hotfix.md` (본 문서)
   - 수정 내역 요약

---

## ⚠️ 주의사항

### 알려진 제약사항
1. **데이터 의존성**: visualization_data가 COA 객체에 없으면 여전히 Fallback 사용
2. **축선 데이터**: `전장축선.xlsx`와 `지형셀.xlsx`가 정확해야 축선 해결 성공
3. **StatusManager**: 위협/부대 좌표가 StatusManager에 등록되어 있어야 우선 적용

### 롤백 방법
문제 발생 시 Git을 통해 이전 버전으로 복구:
```bash
git checkout HEAD~1 ui/views/agent_execution.py
git checkout HEAD~1 ui/components/scenario_mapper.py
```

---

**작성자**: AI Assistant  
**검토자**: (승인 필요)  
**상태**: ✅ 적용 완료, 테스트 대기
