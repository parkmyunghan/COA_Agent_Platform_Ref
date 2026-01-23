# 디버깅 모드 가이드

## 개요

시스템은 실제 운영 단계에서 성능 최적화를 위해 디버깅 모드를 제공합니다. 디버깅 모드가 비활성화된 경우 상세한 디버깅 로그가 기록되지 않아 성능이 향상됩니다.

## 설정 방법

### 1. 실행 시 대화형 선택 (권장)

서버 실행 시 대화형 프롬프트가 표시되어 디버깅 모드를 선택할 수 있습니다:

```bash
python -m api.main
```

또는

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

실행 시 다음과 같은 프롬프트가 표시됩니다:

```
============================================================
디버깅 모드 선택
============================================================
현재 설정 파일 기본값: 운영 모드

디버깅 모드를 활성화하시겠습니까?
  - 디버깅 모드: 상세한 로그 기록 (성능에 영향 있음)
  - 운영 모드: 기본 로그만 기록 (성능 최적화)

디버깅 모드 활성화? [Y/N] (기본값: N):
```

**입력 방법:**
- `Y` 또는 `YES`: 디버깅 모드 활성화
- `N` 또는 `NO`: 운영 모드 (기본값)
- 엔터만 입력: 설정 파일의 기본값 사용

### 2. 설정 파일 수정 (기본값 설정)

`config/global.yaml` 파일에서 `debug_mode` 옵션을 설정하면 대화형 프롬프트의 기본값이 됩니다:

```yaml
# 로그 설정
log_level: "INFO"
log_path: "./logs"
debug_mode: false  # true로 설정 시 대화형 프롬프트 기본값이 디버깅 모드로 설정됨
```

### 3. 환경 변수로 강제 설정

환경 변수를 통해 디버깅 모드를 강제로 설정할 수 있습니다 (대화형 프롬프트 스킵):

```bash
# Windows
set DEBUG_MODE=Y
python -m api.main

# Linux/Mac
export DEBUG_MODE=Y
python -m api.main
```

**환경 변수 값:**
- `DEBUG_MODE=Y` 또는 `DEBUG_MODE=TRUE` 또는 `DEBUG_MODE=1`: 디버깅 모드 강제 활성화
- `DEBUG_MODE=N` 또는 `DEBUG_MODE=FALSE` 또는 `DEBUG_MODE=0`: 운영 모드 강제 활성화

### 2. 운영 모드 (기본값)

```yaml
debug_mode: false
```

**기록되는 로그:**
- 기본 정보: API 요청 수신, 완료 상태, 에러/경고
- 중요한 정보: COA 생성 완료, 추론 완료, 그래프 적용 완료
- 에러 및 경고: 모든 에러와 경고 메시지

**기록되지 않는 로그:**
- 상세 파라미터 정보
- 단계별 상세 진행 상황
- 샘플 데이터 출력
- 필터링 상세 정보
- 신뢰도 계산 상세 과정

### 3. 디버깅 모드

```yaml
debug_mode: true
```

**추가로 기록되는 로그:**
- 모든 상세 디버깅 정보
- 단계별 진행 상황
- 샘플 데이터 및 통계
- 필터링 및 처리 과정 상세 정보

## 로그 레벨과의 관계

- **로그 레벨 (`log_level`)**: 로그의 중요도 기준 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **디버깅 모드 (`debug_mode`)**: 상세 디버깅 정보 기록 여부

두 설정은 독립적으로 작동합니다:
- `log_level: "INFO"`, `debug_mode: false` → 기본 정보만 기록 (운영 모드)
- `log_level: "DEBUG"`, `debug_mode: false` → DEBUG 레벨 로그는 기록되지만 상세 디버깅 정보는 기록되지 않음
- `log_level: "INFO"`, `debug_mode: true` → INFO 레벨 이상 + 상세 디버깅 정보 기록

## 성능 영향

### 운영 모드 (`debug_mode: false`)
- 로그 파일 크기: 약 70-80% 감소
- 로그 기록 오버헤드: 최소화
- 디스크 I/O: 감소

### 디버깅 모드 (`debug_mode: true`)
- 로그 파일 크기: 증가 (상세 정보 포함)
- 로그 기록 오버헤드: 증가
- 디스크 I/O: 증가

## 사용 시나리오

### 운영 환경
```yaml
debug_mode: false
log_level: "INFO"
```
- 실제 운영 시 권장 설정
- 성능 최적화
- 필수 정보만 기록

### 개발/테스트 환경
```yaml
debug_mode: true
log_level: "DEBUG"
```
- 개발 및 디버깅 시 권장 설정
- 상세 정보 기록으로 문제 진단 용이

### 문제 해결 시
```yaml
debug_mode: true
log_level: "INFO"
```
- 문제 발생 시 일시적으로 활성화
- 상세 로그로 원인 분석

## 주의사항

1. **디버깅 모드 활성화 시**: 로그 파일이 빠르게 증가할 수 있으므로 주기적인 로그 파일 관리가 필요합니다.

2. **비대화형 환경**: Docker, systemd 서비스 등 비대화형 환경에서는 설정 파일의 기본값이 자동으로 사용됩니다.

3. **중요 로그**: 에러 및 경고 로그는 디버깅 모드와 관계없이 항상 기록됩니다.

4. **환경 변수 우선순위**: 환경 변수로 설정된 경우 대화형 프롬프트가 표시되지 않고 환경 변수 값이 사용됩니다.

## 예시

### 운영 모드 로그 예시
```
2026-01-23 10:00:00 - api.routers.coa - INFO - [방책추천 API] 요청 수신 - mission_id: MSN001, threat_id: THR001
2026-01-23 10:00:05 - core_pipeline.coa_service - INFO - [COA Service] 통합 COA 생성 완료 (5.23초) - 생성된 COA: 3개, 상위 COA: 3개
2026-01-23 10:00:05 - api.routers.coa - INFO - [방책추천 API] 응답 생성 완료 (5.25초) - COA 수: 3개
```

### 디버깅 모드 로그 예시
```
2026-01-23 10:00:00 - api.routers.coa - INFO - [방책추천 API] 요청 수신 - mission_id: MSN001, threat_id: THR001
2026-01-23 10:00:00 - api.routers.coa - INFO - [방책추천 API] 상세 파라미터 - approach_mode: threat_centered, user_params: {...}
2026-01-23 10:00:01 - core_pipeline.coa_service - INFO - [COA Service] 통합 COA 생성 시작 - mission_id: MSN001, threat_id: THR001, approach_mode: threat_centered
2026-01-23 10:00:01 - core_pipeline.coa_service - INFO - [COA Service] 상세 파라미터 - user_params: {...}
2026-01-23 10:00:02 - core_pipeline.coa_service - INFO - [COA Service] COA 생성 시작 - mission_id: MSN001, preferred_strategy: defensive
2026-01-23 10:00:04 - core_pipeline.coa_service - INFO - [COA Service] COA 생성 완료 (2.15초) - 생성된 COA 수: 3개
2026-01-23 10:00:04 - core_pipeline.coa_service - INFO - [COA Service] COA 평가 시작 - 평가 대상: 3개
2026-01-23 10:00:05 - core_pipeline.coa_service - INFO - [COA Service] COA 평가 완료 (1.08초) - 평가 완료: 3개
2026-01-23 10:00:05 - core_pipeline.coa_service - INFO - [COA Service] 통합 COA 생성 완료 (5.23초) - 생성된 COA: 3개, 상위 COA: 3개
2026-01-23 10:00:05 - core_pipeline.coa_service - INFO - [COA Service] 상세 결과 - 평가 완료: 3개
2026-01-23 10:00:05 - core_pipeline.coa_service - INFO - [COA Service] 최상위 COA: 방어작전_COA_001 (점수: 0.85)
2026-01-23 10:00:05 - api.routers.coa - INFO - [방책추천 API] 응답 생성 완료 (5.25초) - COA 수: 3개
```
