# Defense Intelligent Agent Platform - 설치 및 실행 가이드

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 요구사항](#시스템-요구사항)
3. [설치 단계](#설치-단계)
4. [설정 파일 구성](#설정-파일-구성)
5. [실행 방법](#실행-방법)
6. [문제 해결](#문제-해결)
7. [주요 기능](#주요-기능)

---

## 프로젝트 개요

**Defense Intelligent Agent Platform**은 방어 작전을 위한 방책 추천 시스템입니다.

### 주요 기능
- 🤖 AI 기반 방책 추천 (EnhancedDefenseCOAAgent)
- 📊 온톨로지 기반 지식 그래프 구축 및 조회
- 🔍 RAG (Retrieval-Augmented Generation) 기반 문서 검색
- 📈 실시간 협업 및 승인 워크플로우
- 📄 다양한 형식의 보고서 생성 (PDF, Word, HTML, Excel)

---

## 시스템 요구사항

### 필수 요구사항
- **Python**: 3.9 이상 (3.12 이상 권장)
- **운영체제**: Windows 10/11, Linux, macOS
- **메모리**: 최소 8GB RAM (16GB 권장)
- **디스크 공간**: 최소 10GB (모델 포함 시 20GB 이상)

### 선택적 요구사항
- **GPU**: NVIDIA GPU (CUDA 지원) - 로컬 LLM 모델 사용 시 권장
- **인터넷 연결**: OpenAI API 사용 또는 모델 다운로드 시 필요

---

## 설치 단계

### 1단계: Python 설치 확인

```bash
python --version
# Python 3.8 이상이어야 합니다.
```

Python이 설치되어 있지 않다면 [Python 공식 사이트](https://www.python.org/downloads/)에서 다운로드하세요.

### 2단계: 프로젝트 복사

프로젝트 폴더를 원하는 위치에 복사합니다.

```bash
# 예시: C:\POC\COA_Agent_Platform
```

### 3단계: 가상 환경 생성 (권장)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 4단계: 필수 패키지 설치

프로젝트 루트 디렉토리에서 다음 명령을 실행합니다:

```bash
pip install -r requirements.txt
```

**중요: Graphviz 실행 파일 설치**
이 프로젝트는 그래프 시각화를 위해 Graphviz 실행 파일이 필요합니다.
1. [Graphviz 공식 사이트](https://graphviz.org/download/)에서 설치 파일을 다운로드합니다.
2. 설치 시 "Add Graphviz to the system PATH for all users" 옵션을 선택합니다.
3. 설치 후 터미널을 재시작합니다.

또는 개별 설치:

```bash
# 필수 패키지
pip install streamlit pandas pyyaml jinja2 openpyxl

# 시각화 및 그래프
pip install graphviz plotly pyvis networkx

# 온톨로지 관련
pip install rdflib

# RAG 및 임베딩
pip install faiss-cpu  # 또는 faiss-gpu (GPU 사용 시)
pip install sentence-transformers

# LLM 관련 (로컬 모델 사용 시)
pip install transformers torch accelerate

# 보고서 생성
pip install reportlab python-docx

# OpenAI API (선택적)
pip install openai

# HuggingFace Hub (모델 다운로드 시)
pip install huggingface_hub
```

### 5단계: 디렉토리 구조 확인

다음 디렉토리들이 존재하는지 확인하세요:

```
COA_Agent_Platform/
├── config/              # 설정 파일
├── data_lake/           # Excel 데이터 파일
├── knowledge/           # 온톨로지 및 RAG 문서
│   ├── ontology/
│   ├── rag_docs/
│   └── embeddings/
├── models/              # LLM 및 임베딩 모델 (선택적)
│   ├── llm/
│   └── embedding/
├── ui/                  # Streamlit UI
└── core_pipeline/       # 핵심 파이프라인
```

필요한 디렉토리가 없으면 자동으로 생성됩니다.

---

## 설정 파일 구성

### 1. `config/global.yaml`

데이터 경로 및 기본 설정을 확인/수정합니다:

```yaml
# 데이터 경로 확인
data_paths:
  위협상황: "./data_lake/위협상황.xlsx"
  # ... 기타 테이블 경로

# 출력 경로
output_path: "./outputs"
ontology_path: "./knowledge/ontology"
```

### 2. `config/model_config.yaml`

모델 설정을 확인/수정합니다:

```yaml
llm:
  use_openai: true  # OpenAI API 사용 여부
  model_path: "./models/llm/beomi-gemma-ko-2b"  # 로컬 모델 경로

openai:
  api_key: "your-api-key-here"  # OpenAI API 키 설정
  model: "gpt-4o"
```

**중요**: 
- OpenAI API를 사용하려면 `api_key`를 설정하세요.
- 로컬 모델만 사용하려면 `use_openai: false`로 설정하세요.

### 3. 데이터 파일 확인

`data_lake/` 폴더에 다음 Excel 파일들이 있는지 확인하세요:
- 위협상황.xlsx
- 적군부대.xlsx
- 아군부대.xlsx
- 아군가용자산.xlsx
- COA_라이브러리.xlsx
- 평가기준_가중치.xlsx
- 기타 테이블 파일들

---

## 실행 방법

### 방법 1: Streamlit 실행 스크립트 사용 (권장)

```bash
python run_streamlit.py
```

### 방법 2: Streamlit 직접 실행

```bash
streamlit run ui/dashboard.py --server.port=8501 --server.address=0.0.0.0
```

### 접속

브라우저에서 다음 주소로 접속:
- **로컬**: `http://localhost:8501`
- **네트워크**: `http://[서버IP]:8501`

### 기본 로그인 정보

- **사용자명**: `pilot`
- **비밀번호**: `pilot123`
- **역할**: 파일럿 테스터 (모든 권한)

---

## 문제 해결

### 1. 패키지 설치 오류

**문제**: `pip install` 실패

**해결**:
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 개별 패키지 설치
pip install [패키지명] --upgrade
```

### 2. FAISS 설치 오류

**문제**: `faiss-cpu` 설치 실패

**해결**:
```bash
# Windows
pip install faiss-cpu --no-cache-dir

# Linux/Mac
pip install faiss-cpu
```

GPU를 사용하는 경우:
```bash
pip install faiss-gpu
```

### 3. 모델 로드 오류

**문제**: LLM 모델을 찾을 수 없음

**해결**:
- OpenAI API를 사용하도록 설정 (`config/model_config.yaml`에서 `use_openai: true`)
- 또는 로컬 모델 다운로드:
  ```bash
  huggingface-cli download beomi/gemma-ko-2b --local-dir ./models/llm/gemma-ko-2b
  ```

### 4. 데이터 파일 오류

**문제**: Excel 파일을 찾을 수 없음

**해결**:
- `data_lake/` 폴더에 필요한 Excel 파일이 있는지 확인
- `config/global.yaml`의 경로가 올바른지 확인

### 5. 포트 충돌

**문제**: 포트 8501이 이미 사용 중

**해결**:
```bash
# 다른 포트 사용
streamlit run ui/dashboard.py --server.port=8502
```

### 6. 인코딩 오류 (Windows)

**문제**: 한글 깨짐

**해결**:
- Windows 콘솔 인코딩을 UTF-8로 설정
- 또는 PowerShell 대신 Command Prompt 사용

### 7. 모듈 Import 오류

**문제**: `ModuleNotFoundError`

**해결**:
```bash
# 프로젝트 루트에서 실행 확인
cd COA_Agent_Platform
python run_streamlit.py
```

### 8. 권한 오류 (Windows)

**문제**: 파일 접근 권한 오류

**해결**:
- 관리자 권한으로 실행
- 또는 프로젝트 폴더의 권한 확인

---

## 주요 기능

### 1. 데이터 관리
- Excel 파일 업로드 및 편집
- 데이터 품질 검증
- 실시간 데이터 변경 감시

### 2. 온톨로지 생성
- Excel 데이터를 RDF 그래프로 변환
- SPARQL 쿼리 실행
- 관계 시각화

### 3. RAG 인덱스 구성
- 문서 업로드 및 관리
- FAISS 벡터 인덱스 생성
- 의미 기반 검색

### 4. Agent 실행
- 방책 추천 에이전트 실행
- 상황 입력 및 추천 결과 확인
- 추론 과정 시각화

### 5. 성능 모니터링
- 파이프라인 상태 확인
- 성능 벤치마크
- 로그 확인

---

## 추가 정보

### 모델 다운로드

로컬 LLM 모델을 사용하려면:

```bash
huggingface-cli download beomi/gemma-ko-2b --local-dir ./models/llm/gemma-ko-2b
```

또는 수동으로 HuggingFace에서 다운로드:
- LLM: `beomi/gemma-ko-2b`
- Embedding: `BAAI/bge-small-en-v1.5` (또는 한국어 모델)

### 🗺️ 오프라인 지도 설정 (필수)
폐쇄망 환경에서 지도를 사용하기 위해 다음 단계를 수행해야 합니다.

1. **지도 라이브러리 다운로드 (최초 1회)**
    ```bash
    python scripts/download_offline_assets.py
    ```

2. **지도 데이터(MBTiles) 준비 (선택사항)**
    *고해상도 지도가 필요한 경우 수행하세요. 이 단계를 생략하면 **기본 지도(GeoJSON)**가 자동으로 적용됩니다.*
    - [MapTiler Korea](https://data.maptiler.com/downloads/asia/south-korea/) 사이트 접속
    - **OpenStreetMap (Vector)** 항목 선택 및 다운로드 (**무료 계정 로그인 필요**)
    - 다운로드한 파일을 `data/maps/korea.mbtiles` 위치에 저장합니다.

3. **지도 서버 실행**
    앱 실행 전, 백그라운드에서 지도 서버를 실행해야 합니다. (기본 지도 사용 시에도 필수)
    ```bash
    python scripts/serve_offline_map.py
    ```
    - 정상 실행 시 `http://localhost:8080` 포트를 사용합니다.

### 테스트 실행

```bash
# 통합 테스트
python tests/test_integration.py

# 단위 테스트
python -m pytest tests/
```

### 로그 확인

로그 파일은 `logs/` 디렉토리에 저장됩니다.

### 첫 실행 시 체크리스트

1. ✅ Python 3.8+ 설치 확인
2. ✅ `requirements.txt` 패키지 설치
3. ✅ `data_lake/` 폴더에 Excel 파일 확인
4. ✅ `config/model_config.yaml`에서 OpenAI API 키 설정 (또는 로컬 모델 경로 확인)
5. ✅ `config/global.yaml` 경로 확인
6. ✅ `python run_streamlit.py` 실행
7. ✅ 브라우저에서 `http://localhost:8501` 접속
8. ✅ 로그인 (pilot/pilot123)

---

## 지원 및 문의

문제가 발생하면:
1. 로그 파일 확인 (`logs/` 디렉토리)
2. 에러 메시지 확인
3. 이 가이드의 "문제 해결" 섹션 참조

---

**문서 버전**: 1.1  
**최종 업데이트**: 2025-12-18


