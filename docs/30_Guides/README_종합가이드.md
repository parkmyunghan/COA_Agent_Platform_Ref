# Defense Intelligent Agent Platform - 종합 가이드

## 📋 문서 개요
- **최종 수정**: 2026-01-26
- **버전**: 2.0 (React Re-platforming)
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
| **UI** | React 기반 웹 대시보드 (C2 Dashboard) |

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
- **Command & Control**: 통합 지휘통제 및 방책 추천 메인 화면
- **Ontology Studio**: 지식 그래프 탐색 및 고급 쿼리
- **Data Management**: 데이터 테이블 조회 및 관리
- **System Guide**: 시스템 도움말 및 기술 문서

---

## 3. 설치 및 실행

### 3.1 사전 요구사항
- Python 3.9 이상
- Node.js 18.0 이상
- 16GB RAM 이상 권장
- Windows 10/11, Linux, macOS

### 3.2 설치

```bash
# 1. 가상환경 활성화
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# 2. Backend 의존성 설치
pip install -r requirements.txt

# 3. Frontend 의존성 설치
cd frontend
npm install
```

### 3.3 실행

**Backend (Terminal 1)**
```bash
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Terminal 2)**
```bash
cd frontend
npm run dev
```

접속: `http://localhost:5173`

### 3.4 주요 파일 경로

```
c:/POC/COA_Agent_Platform/
├── data_lake/                    # 데이터 파일 (Excel)
├── config/                       # 설정 파일
├── api/                          # Backend (FastAPI)
│   └── main.py                   # 진입점
└── frontend/                     # Frontend (React)
    └── src/                      # 소스 코드
```

---

## 4. 프로토타입 개선 계획

### 4.1 최우선 과제 (P0)

#### 4.1.1 React 전환 및 아키텍처 고도화 (완료)
- ✅ Streamlit → React + FastAPI 전환 완료
- ✅ 컴포넌트 기반 UI 설계 적용

#### 4.1.2 추천 로직 투명성 강화 (진행중)
- ⏳ 점수 계산 과정 상세 로그 UI 표출
- ⏳ 추천 근거 시각화 컴포넌트 개발

---

## 5. 핵심 가이드 문서 (Quick Links)

시스템 사용 및 관리를 위해 다음 3가지 핵심 문서를 참고하세요.

### 📘 [사용자 매뉴얼 (User Manual)](USER_MANUAL.md)
- **대상**: 작전 장교, 분석가, 일반 사용자
- **내용**: 시스템 접속, 상황 입력, 방책 추천 결과 해석, 전술상황도(COP) 시각화 방법 등 시스템 활용을 위한 통합 가이드입니다.

### 💾 [데이터 관리 가이드 (Data Guide)](DATA_MANAGEMENT_GUIDE.md)
- **대상**: 데이터 관리자, 시나리오 작성자
- **내용**: 엑셀 데이터 작성 표준, **테이블정의서** 구조, FK 관계 설정 및 데이터 품질 검증 방법에 대한 상세 가이드입니다.

### ⚙️ [시스템 운영 가이드 (Admin Guide)](ADMIN_GUIDE.md)
- **대상**: 시스템 엔지니어, 관리자
- **내용**: React+FastAPI 환경 설치, 서버 실행, 디버깅 모드 설정 및 트러블슈팅을 위한 기술 문서입니다.

---

## 6. 라이선스 및 주의사항

- 본 시스템은 **교육/학습용 프로토타입**입니다.
- 실전 운영 전 충분한 검증 필요
- 팔란티어는 Palantir Technologies Inc.의 등록 상표입니다.
