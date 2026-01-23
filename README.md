# COA Agent Platform
### 국방 지능형 의사결정 지원 플랫폼 - 지능형 방책(COA) 추천 및 전술 분석 체계

본 플랫폼은 현대전의 복잡한 전장 상황에서 지휘관 및 참모의 신속하고 정확한 의사결정을 돕기 위해 구축된 **지능형 방책(COA) 추천 시스템**입니다. 기존 Streamlit 기반 프로토타입을 현대적인 **React + FastAPI** 아키텍처로 완전히 리팩토링하고, METT-C 전술 요소와 온톨로지 지식 체계를 결합하여 고도의 추론 성능을 제공합니다.

---

## 📚 주요 성과 및 문서 (Documentation)

### [문서 전체 인덱스 및 가이드 보러가기](docs/INDEX.md)
최근 진행된 시스템 고도화 및 데이터 분석 성과는 아래 문서에서 상세히 확인하실 수 있습니다.
- **문서 통합 인덱스**: [INDEX.md](docs/INDEX.md) - 전체 문서 분류 및 가이드
- **종합 성과 보고서**: [final_project_summary_report.md](docs/reports/final_project_summary_report.md)
- **온톨로지 특화 전략**: [ontology_strategy_report.md](docs/reports/ontology_strategy_report.md)
- **통합 검증 결과**: [walkthrough.md](docs/reports/walkthrough.md)
- **상세 분석 보고서**: 16개 핵심 데이터 테이블(`임무`, `위협`, `지형`, `날씨` 등)에 대한 정밀 분석 보고서 완비.

---

## �️ 기술 스택 (Tech Stack)

본 프로젝트는 확장성과 유지보수성을 고려하여 최신 웹 기술과 데이터 분석 라이브러리를 기반으로 구축되었습니다.

### Frontend
- **Framework**: React 18, Vite (초고속 빌드 및 HMR 지원)
- **UI Component**: Ant Design (엔터프라이즈급 UI 시스템)
- **State Management**: React Hooks (Custom Hooks)
- **Visualization**: OpenLayers, React-Force-Graph (지리정보 및 지식그래프 시각화)

### Backend
- **Framework**: FastAPI (비동기 처리 및 자동 문서화 지원)
- **Server**: Uvicorn (ASGI 서버)
- **API Documentation**: Swagger UI / ReDoc 내장

### Data & AI
- **Ontology**: RDFLib (RDF/OWL/Turtle 처리 및 SPARQL 쿼리 엔진)
- **Data Processing**: Pandas (전술 데이터 분석 및 변환)
- **LLM Integration**: OpenAI API (자연어 처리 및 추론 보조)

---

## 🧩 주요 모듈 상세 (Key Modules)

### 1. 지휘통제 (Command & Control)
실시간 전술 상황을 시각화하고 방책을 수립하는 핵심 모듈입니다.
- **기능**: 위협 식별, COA 생성 요청, 실시간 상황도(COP) 표출, 방책 세부 평가(점수, 성공 확률)
- **특징**: METT-C 요소를 종합적으로 고려하여 최적의 대응 방책을 제안합니다.

### 2. 온톨로지 스튜디오 (Ontology Studio)
전술 지식 체계(Ontology)를 시각적으로 관리하고 검증하는 도구입니다.
- **기능**: 클래스/속성 탐색, SPARQL 쿼리 실행, 관계 시각화, 무결성 검증
- **특징**: 복잡한 RDF 데이터를 그래프 형태로 직관적으로 표현하여 지식베이스 구축 효율을 높입니다.

### 3. 지식 그래프 (Knowledge Graph)
구축된 온톨로지 데이터를 기반으로 심층적인 관계를 탐색합니다.
- **기능**: 노드 중심 탐색, 연관 개체 추적, 추론 경로 확인
- **특징**: 단순 데이터 조회를 넘어 '왜'라는 질문에 답할 수 있는 인과적 정보를 제공합니다.

### 4. 데이터 관리 (Data Management)
16종의 전술 마스터 데이터를 관리하고 품질을 모니터링합니다.
- **기능**: 데이터 CRUD, 품질 지표(정확성, 완전성 등) 대시보드, 이상치 탐지
- **특징**: 데이터의 신뢰성을 보장하여 AI 추론의 정확도를 뒷받침합니다.

---

## �🚀 빠른 시작 (Quick Start)

### 1. 사전 요구사항 (Prerequisites)
- **Python**: 3.12 권장 (3.9 이상 필요)
- **Node.js**: 18.0 이상
- **npm**: 최신 버전

### 2. 프로젝트 설정 및 실행

#### [백엔드 실행]
```bash
# 가상환경 활성화 (Windows 기준)
.venv\Scripts\activate

# 의존성 설치 (일반)
python -m pip install -r requirements.txt

# GPU(CUDA) 지원이 필요한 경우 (추천)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 서버 실행 (권장 방식: venv 경로 이슈 회피)
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
> [!TIP]
> 직접 `uvicorn` 실행 시 경로 오류가 발생한다면 반드시 `python -m uvicorn` 명령어를 사용해 주세요.

#### [프론트엔드 실행]
```bash
cd frontend
npm install # 최초 실행 시 또는 의존성 변경 시에만 실행
npm run dev # http://localhost:5173 접속
```

---

## 🌐 외부 접근 및 네트워크 설정

본 플랫폼은 동일 네트워크 대역의 다른 기기에서도 IP 주소를 통해 접근할 수 있도록 설계되었습니다.

### 1. 서버 IP 주소 확인 (Windows)
명령 프롬프트(cmd) 또는 PowerShell에서 아래 명령어를 실행하여 현재 서버의 IP 주소를 확인합니다.
```bash
ipconfig
# 'IPv4 주소' 항목 확인 (예: 192.168.0.10)
```

### 2. 접속 방법
- **백엔드 API**: `http://[서버IP]:8000/docs` (Swagger UI 접속 가능)
- **프론트엔드 UI**: `npm run dev` 실행 시 출력되는 네트워크 주소 또는 `http://[서버IP]:5173`으로 접속

> [!IMPORTANT]
> - 서버 실행 시 반드시 `--host 0.0.0.0` 옵션을 포함해야 외부 접근이 가능합니다.
> - 방화벽 설정에서 8000번(API) 및 5173번(Vite) 포트가 허용되어 있는지 확인해 주세요.

---

## � 프로젝트 구조 (Directory Structure)
```
COA_Agent_Platform/
├── api/                    # FastAPI 백엔드 (Business Logic & API Routers)
│   ├── routers/            # 모듈별 API 엔드포인트 (Agent, Ontology, Data 등)
│   └── web/                # 웹 소켓 및 공통 유틸리티
├── frontend/               # React 프론트엔드 (Modern UI/UX)
│   ├── src/
│   │   ├── components/     # 재사용 가능한 UI 컴포넌트
│   │   ├── pages/          # 주요 기능 페이지 (C2, Ontology, Data 등)
│   │   └── hooks/          # 커스텀 훅 (API 통신, 상태 관리)
├── core_pipeline/          # 핵심 추천 엔진
│   ├── Generator.py        # 방책 생성 로직
│   ├── Scorer.py           # 정량적 평가 엔진
│   └── Evaluator.py        # 종합 검증 및 순위 선정
├── knowledge/              # 온톨로지 및 시맨틱 지식 베이스 (.ttl, .owl)
├── data_lake/              # 16개 핵심 전술 데이터 마스터 (.csv, .xlsx)
├── docs/                   # 프로젝트 문서 및 보고서
└── scripts/                # 데이터 분석, 검증, 유틸리티 스크립트
```

---

## 🛠️ 문제 해결 (Troubleshooting)

### 백엔드 실행 오류 (Fatal error in launcher)
Windows 환경에서 가상환경 경로에 공백이나 한글이 포함된 경우 `uvicorn` 실행 파일이 오류를 일으킬 수 있습니다.
- **해결책**: `python -m uvicorn api.main:app ...` 명령어를 사용하여 Python 인터프리터를 통해 직접 실행하세요.

### 데이터 로드 문제
`평가기준_가중치.xlsx` 등 필수 파일이 `data_lake` 폴더에 있는지 확인하세요. 라이브러리 누락 시 `pip install -r requirements.txt`를 다시 수행하세요.

---
**문의**: 시스템 관련 질문은 프로젝트 관리자 또는 지능형 에이전트 개발팀에 문의해 주시기 바랍니다.
