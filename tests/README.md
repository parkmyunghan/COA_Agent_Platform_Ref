# 테스트 가이드

## 개요

이 디렉토리에는 Defense Intelligent Agent Platform의 모든 테스트 코드와 결과 문서가 포함되어 있습니다.

## 테스트 파일 구조

```
tests/
├── test_situation_input.py                    # 상황정보 입력 테스트 (51개)
├── test_coa_recommendation_integration.py     # 방책 추천 통합 테스트 (9개)
├── test_situation_input_to_coa_recommendation.py  # 상황정보 입력 → 방책 추천 통합 테스트 (9개)
├── test_coa_recommendation_validation.py      # 방책 추천 결과 검증 테스트 (7개)
├── run_all_tests.py                          # 전체 테스트 실행 스크립트
│
├── TEST_SUMMARY.md                           # 테스트 종합 요약
├── TEST_RESULTS_situation_input.md            # 상황정보 입력 테스트 결과
├── TEST_RESULTS_COA_RECOMMENDATION.md        # 방책 추천 통합 테스트 결과
├── TEST_RESULTS_SITUATION_INPUT_TO_COA.md    # 상황정보 입력 → 방책 추천 통합 테스트 결과
├── TEST_RESULTS_COA_VALIDATION.md            # 방책 추천 결과 검증 테스트 결과
└── TEST_COA_RECOMMENDATION_GAP_ANALYSIS.md   # 테스트 커버리지 분석
```

## 빠른 시작

### 전체 테스트 실행

```bash
# 전체 테스트 한 번에 실행
python tests/run_all_tests.py
```

### 개별 테스트 실행

```bash
# 상황정보 입력 테스트
python tests/test_situation_input.py

# 방책 추천 통합 테스트
python tests/test_coa_recommendation_integration.py

# 상황정보 입력 → 방책 추천 통합 테스트
python tests/test_situation_input_to_coa_recommendation.py

# 방책 추천 결과 검증 테스트
python tests/test_coa_recommendation_validation.py
```

### 특정 테스트만 실행

```bash
# unittest 사용
python -m unittest tests.test_situation_input.TestSituationInput.test_render_manual_input

# pytest 사용
pytest tests/test_situation_input.py::TestSituationInput::test_render_manual_input -v
```

## 테스트 커버리지

### 현재 커버리지

- **총 테스트 수**: 76개
- **통과율**: 100%
- **커버리지**: 주요 기능 100%

### 테스트된 기능

1. ✅ 상황정보 입력 UI
   - 수동 입력
   - 실제 데이터 선택
   - SITREP 파싱
   - 데모 시나리오
   - 접근 방식 선택

2. ✅ 방책 추천 기능
   - 위협 수준별 추천
   - 위협 유형별 추천
   - 방책 타입 필터링
   - 점수 계산
   - 추천 이유 생성

3. ✅ 통합 워크플로우
   - 상황정보 입력 → 방책 추천
   - 접근 방식 전달
   - 데이터 보존

4. ✅ 결과 검증
   - 점수 다양성
   - 상황별 차이
   - 품질 검증

## 테스트 결과 문서

각 테스트의 상세 결과는 다음 문서에서 확인할 수 있습니다:

1. **TEST_SUMMARY.md**: 전체 테스트 종합 요약
2. **TEST_RESULTS_situation_input.md**: 상황정보 입력 테스트 상세 결과
3. **TEST_RESULTS_COA_RECOMMENDATION.md**: 방책 추천 통합 테스트 상세 결과
4. **TEST_RESULTS_SITUATION_INPUT_TO_COA.md**: 상황정보 입력 → 방책 추천 통합 테스트 상세 결과
5. **TEST_RESULTS_COA_VALIDATION.md**: 방책 추천 결과 검증 테스트 상세 결과

## 문제 해결

### 테스트 실행 오류

1. **모듈을 찾을 수 없음**
   ```bash
   # 프로젝트 루트에서 실행
   cd C:\POC\(NEW)Defense_Intelligent_Agent_Platform
   python tests/run_all_tests.py
   ```

2. **설정 파일 오류**
   - `config/global.yaml` 파일이 존재하는지 확인
   - `data_lake/` 폴더에 필요한 Excel 파일이 있는지 확인

3. **타임아웃 오류**
   - 일부 테스트는 실행 시간이 오래 걸릴 수 있음 (최대 10분)
   - 개별 테스트를 실행하여 문제가 있는 테스트 확인

### 테스트 실패 시

1. 테스트 출력에서 오류 메시지 확인
2. 해당 테스트 파일의 상세 결과 문서 확인
3. 로그 파일 확인 (있는 경우)

## 추가 정보

자세한 내용은 각 테스트 결과 문서를 참조하세요.
