# Defense Intelligent Agent Platform - 종합 가이드

## 📋 문서 개요
- **최종 수정**: 2025-12-18
- **버전**: 1.1
- **목적**: 프로토타입 시스템의 핵심 정보 통합 제공

---

## 📚 목차

1. [시스템 소개](#1-시스템-소개)
2. [주요 기능](#2-주요-기능)
3. [설치 및 실행](#3-설치-및-실행)
4. [프로토타입 개선 계획](#4-프로토타입-개선-계획)
5. [참고 문서](#5-참고-문서)

---

## 1. 시스템 소개

### 1.1 시스템 목적

**Defense Intelligent Agent Platform**은 온톨로지 기반 군사 의사결정 지원 시스템의 프로토타입입니다.

**핵심 목표**:
- 온톨로지 기반 지식 표현 학습
- AI 에이전트 방책 추천 로직 검증
- 본격 시스템 개발 전 개념 검증 (PoC)
- 관련 인력의 이해도 향상

### 1.2 시스템 특징

| 특징 | 설명 |
|------|------|
| **데이터 관리** | Excel/Access 기반 PC 환경 |
| **온톨로지** | RDF 기반 자동 생성 및 시각화 |
| **RAG** | 의미 기반 문서 검색 |
| **AI 에이전트** | 7가지 COA 타입 지원 |
| **LLM 통합** | OpenAI API, 로컬 모델 지원 |
| **UI** | Streamlit 기반 대화형 인터페이스 |

### 1.3 팔란티어 벤치마킹

본 시스템은 Palantir의 핵심 개념을 참고했습니다:
- **Foundry**: 데이터 온톨로지 기반 통합
- **AIP**: AI 에이전트 협력 및 컨텍스트 엔진
- **Gotham**: 국방 특화 기능

**차별점**: PC 단독 실행, 교육/학습 중심, 단순화된 구조

---

## 2. 주요 기능

### 2.1 데이터 관리
- Excel 파일 자동 로드 (`data_lake/`)
- 8개 주요 테이블: COA_Library, 위협상황, 방책템플릿, 평가기준_가중치 등
- 데이터 검증 및 품질 체크

### 2.2 온톨로지 생성
- Excel → RDF 그래프 자동 변환
- 관계 매핑 기반 자동 연결
- PyVis 인터랙티브 시각화
- SPARQL 쿼리 지원

### 2.3 방책 추천 (COA Recommendation)

#### 지원 방책 타입 (7가지)
1. **Defense** (방어): 적 공격 대응
2. **Offensive** (공격): 적 약점 공격
3. **Counter_Attack** (반격): 공격 후 즉시 반격
4. **Preemptive** (선제공격): 적의 공격 전 선제 타격
5. **Deterrence** (억제): 적의 공격 의도 억제
6. **Maneuver** (기동): 전술적 재배치
7. **Information_Ops** (정보작전): 정보 우위 확보

#### 추천 방식
- **기본 모드**: 규칙 기반 + LLM 평가 (하이브리드)
- **팔란티어 모드**: 다중 요소 종합 점수 계산
  - 위협 점수
  - 자원 가용성
  - 자산 능력
  - 환경 적합성
  - 과거 성공률
  - 관계 체인

### 2.4 RAG (검색 증강 생성)
- FAISS 벡터 인덱스
- Sentence Transformers 임베딩
- 의미 기반 문서 검색
- LLM 응답 생성 시 인용 제공

### 2.5 UI 기능
- 6단계 파이프라인 페이지
  1. 데이터 관리
  2. 온톨로지 생성
  3. 지식 그래프 조회
  4. RAG 인덱스 구성
  5. Agent 실행
  6. 성능 모니터링
- 방책 유형 필터 (멀티셀렉트)
- 추론 과정 시각화
- 인용 모드 채팅

---

## 3. 설치 및 실행

### 3.1 사전 요구사항
- Python 3.9 이상 (3.12 이상 권장)
- 16GB RAM 이상 권장
- Windows 10/11, Linux, macOS

### 3.2 설치

```powershell
# 1. 가상환경 활성화 (가상환경 경로는 실제 환경에 맞게 조정)
& "c:/POC/COA_Agent_Platform/venv/Scripts/Activate.ps1"

# 2. 의존성 설치 (이미 설치된 경우 skip)
pip install -r requirements.txt
```

### 3.3 실행

```powershell
# Streamlit 앱 실행
python run_streamlit.py

# 또는 직접 실행
streamlit run ui/dashboard.py
```

접속: `http://localhost:8501`

### 3.4 주요 파일 경로

```
c:/POC/COA_Agent_Platform/
├── data_lake/                    # 데이터 파일
│   ├── COA_Library.xlsx          # 방책 라이브러리
│   ├── 위협상황.xlsx
│   ├── 방책템플릿.xlsx
│   └── 평가기준_가중치.xlsx
├── config/
│   ├── global.yaml               # 전역 설정
│   └── model_config.yaml         # LLM 모델 설정
├── ui/
│   └── dashboard.py              # 통합 대시보드
└── run_streamlit.py              # 실행 스크립트
```

---

## 4. 프로토타입 개선 계획

### 4.1 최우선 과제 (P0 - 1-2주)

#### 4.1.1 온톨로지 생성 기능 완성
- ✅ 구현 완료: 기본 온톨로지 생성
- ⏳ 개선 필요: COA 타입별 클래스/속성 추가

**액션**:
```python
# 타입별 클래스 분리
ns.방어방책  # DefenseCOA
ns.공격방책  # OffensiveCOA
ns.반격방책  # CounterAttackCOA
# ... 등
```

#### 4.1.2 추천 로직 투명성 강화
- ⏳ 점수 계산 과정 상세 로그
- ⏳ 추천 이유 자동 생성
- ⏳ UI에 추론 과정 시각화 (막대 차트, 플로우차트)

#### 4.1.3 교육용 문서 작성
- ⏳ 사용자 가이드 (초보자용)
- ⏳ 온톨로지 설계 문서
- ⏳ 방책 추천 알고리즘 설명
- ⏳ FAQ 및 트러블슈팅

### 4.2 중요 과제 (P1 - 2-4주)

#### 4.2.1 데이터 품질 개선
- 목표: 각 COA 타입별 10개 이상 방책 (총 70개)
- 10개 대표 시나리오 작성
- 데이터 검증 규칙 강화

#### 4.2.2 시각화 개선
- 온톨로지 그래프 시각화 강화
- 방책 비교 레이더 차트
- 추론 플로우 다이어그램 (Mermaid)

### 4.3 성공 지표

| 지표 | 현재 | 목표 (1개월) |
|------|------|-------------|
| COA 샘플 데이터 | 9개 | 70개 |
| 문서 | README | 4개 가이드 |
| 시나리오 | 0개 | 10개 |
| 사용자 만족도 | - | 4.0/5.0 |

---

## 5. 참고 문서

### 5.1 프로젝트 문서
- `INSTALLATION_GUIDE.md`: 상세 설치 가이드
- `TEST_GUIDE.md`: 테스트 방법

### 5.2 데이터 관련
- `docs/테이블정의서_작성_예시.md`: 데이터 구조 이해
- `docs/테이블정의서_구조_가이드.md`: 데이터 작성 방법
- `metadata/RELATION_MAPPINGS_GUIDE.md`: 관계 매핑 정의

### 5.3 작성 예정 문서
- `docs/사용자_가이드.md`: 초보자 실습 가이드
- `docs/온톨로지_설계.md`: 온톨로지 상세 설명
- `docs/방책추천_알고리즘.md`: 알고리즘 수식 및 예제

### 5.4 테스트 관련
- `tests/TEST_SUMMARY.md`: 테스트 종합 요약
- `tests/TEST_RESULTS_situation_input.md`: 상황정보 입력 테스트 결과
- `tests/TEST_RESULTS_COA_RECOMMENDATION.md`: 방책 추천 통합 테스트 결과
- `tests/TEST_RESULTS_SITUATION_INPUT_TO_COA.md`: 상황정보 입력 → 방책 추천 통합 테스트 결과
- `tests/TEST_RESULTS_COA_VALIDATION.md`: 방책 추천 결과 검증 테스트 결과
- `tests/TEST_COA_RECOMMENDATION_GAP_ANALYSIS.md`: 테스트 커버리지 분석

---

## 6. 자주 묻는 질문

### Q1: 첫 실행 시 오류가 발생해요
**A**: 다음을 확인하세요:
1. Python 3.9 이상 설치 확인
2. 가상환경 활성화 확인
3. `pip install -r requirements.txt` 실행
4. `data_lake/` 폴더에 Excel 파일 존재 확인

### Q2: LLM 모델을 어떻게 선택하나요?
**A**: 
- Sidebar에서 "LLM 모델 선택" 드롭다운 사용
- OpenAI API 키가 설정되어 있으면 GPT-4 사용 가능
- 로컬 모델은 `config/model_config.yaml`에서 경로 설정

### Q3: 온톨로지가 생성되지 않아요
**A**:
1. "2단계: 온톨로지 생성" 페이지에서 "온톨로지 재생성" 버튼 클릭
2. 데이터 파일 확인 (Excel 포맷 오류 체크)
3. 로그에서 오류 메시지 확인

### Q4: 방책 추천이 이상해요
**A**:
- 위협 수준(threat_level)이 정확히 입력되었는지 확인
- 팔란티어 모드 활성화 여부 확인
- `평가기준_가중치.xlsx`의 가중치 값 검토

### Q5: 테스트는 어떻게 실행하나요?
**A**:
```powershell
# 전체 테스트 실행
python tests/run_all_tests.py

# 개별 테스트 실행
python tests/test_situation_input.py
python tests/test_coa_recommendation_integration.py
python tests/test_situation_input_to_coa_recommendation.py
python tests/test_coa_recommendation_validation.py
```
자세한 내용은 `tests/TEST_SUMMARY.md` 참조

---

## 7. 문의 및 지원

**프로젝트 디렉토리**: `c:/POC/COA_Agent_Platform/`

**로그 파일**: `logs/system.log` (향후 추가 예정)

**Streamlit 접속**: `http://localhost:8501`

---

## 8. 라이선스 및 주의사항

- 본 시스템은 **교육/학습용 프로토타입**입니다.
- 실전 운영 전 충분한 검증 필요
- 팔란티어는 Palantir Technologies Inc.의 등록 상표입니다.
