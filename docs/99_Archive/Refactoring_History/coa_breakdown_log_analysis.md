# 백엔드 로그 breakdown 값 분석 결과

## 로그 분석 결과

### COAScorer breakdown 값 (로그에서 확인)

로그 파일 `logs/system_20260109.log`에서 "COA 점수 계산 완료" 메시지를 통해 breakdown 값을 확인했습니다.

#### 예시 1: COA_DET_001 (Pass 1)
```
COA=COA_Library_COA_DET_001, 최종총점=0.6160 
(위협:0.850, 자원:0.000, 환경:0.900, 과거:0.900, 체인:0.300, Mission:0.420)
```

#### 예시 2: COA_CNT_002 (Pass 1)
```
COA=COA_Library_COA_CNT_002, 최종총점=0.6323 
(위협:0.850, 자원:0.152, 환경:0.900, 과거:0.680, 체인:0.300, Mission:0.580)
```

#### 예시 3: COA_DEF_001 (Pass 2)
```
COA=COA_Library_COA_DEF_001, 최종총점=0.6486 
(위협:0.850, 자원:0.303, 환경:0.700, 과거:0.620, 체인:0.680, Mission:0.820)
```

### 분석 결과

1. **위협 (threat)**: 모든 COA에서 **0.850으로 동일** ✅ (정상 - 상황 정보 기반)
2. **자원 (resources)**: COA별로 **다름** ✅
   - COA_DET_001: 0.000
   - COA_CNT_002: 0.152
   - COA_DEF_001: 0.303
3. **환경 (environment)**: 대부분 **0.900 또는 0.700** (대부분 동일, 일부 다름)
4. **과거 (historical)**: COA별로 **다름** ✅
   - COA_DET_001: 0.900
   - COA_CNT_002: 0.680
   - COA_DEF_001: 0.620
5. **체인 (chain)**: Pass 1에서는 **0.300**, Pass 2에서는 **0.680** 등으로 다름 ✅
6. **Mission (mission_alignment)**: COA별로 **다름** ✅
   - COA_DET_001: 0.420
   - COA_CNT_002: 0.580
   - COA_DEF_001: 0.820

### 프론트엔드 점수 추출 로그 부재

**문제**: `api/routers/agent.py`에서 추가한 디버깅 로그가 로그 파일에 나타나지 않음.

**가능한 원인**:
1. 최근 방책 추천 실행이 없어서 새로운 로그가 생성되지 않음
2. API 라우터의 로그가 별도 파일에 저장되거나 콘솔에만 출력됨
3. 로그 레벨 설정으로 인해 INFO 레벨 로그가 출력되지 않음

### 프론트엔드 매핑 규칙

프론트엔드에서 breakdown을 다음과 같이 매핑:
- `threat` → `threat_response_score` (위협 대응)
- `assets` → `combat_power_score` (전투력)
- `resources` → `mobility_score` (기동성)
- `environment` → `constraint_score` (제약조건)
- `risk_score`는 breakdown에 없으므로 `1.0 - threat_score` 계산

**주의**: 로그에는 `assets` 값이 직접 출력되지 않음. COAScorer의 `_calculate_asset_score` 메서드가 계산하지만 breakdown 로그에 포함되지 않을 수 있음.

## 결론

1. **COAScorer breakdown은 COA별로 다르게 계산되고 있음** ✅
2. **프론트엔드에서 breakdown 추출 로그가 없음** → 최근 방책 추천 실행 필요
3. **`assets` 값이 로그에 나타나지 않음** → 별도 확인 필요

## 다음 단계

1. **최근 방책 추천 실행**: 프론트엔드에서 방책 추천을 실행하여 새로운 로그 생성
2. **API 라우터 로그 확인**: `api/routers/agent.py`의 로그가 어디에 출력되는지 확인
3. **`assets` 값 확인**: COAScorer의 `_calculate_asset_score` 메서드가 breakdown에 포함되는지 확인
