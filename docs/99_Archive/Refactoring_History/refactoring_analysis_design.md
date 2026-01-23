# Streamlit -> React 리팩토링 마스터 플랜

## 1. 개요 (Overview)
본 문서는 `COA_Agent_Platform` 시스템 전체를 기존 Streamlit 기반에서 React + FastAPI 아키텍처로 전환하기 위한 포괄적인 전략을 기술합니다.
기존 `ui/` 디렉토리 분석을 바탕으로, 마이그레이션이 필요한 모듈과 기능을 정의합니다.

## 2. 레거시 시스템 범위 (Streamlit)
기존 시스템은 크게 7개의 주요 화면으로 구성되어 있습니다:
1.  **지휘통제/분석 (`agent_execution.py`)** [부분 완료]
    -   *완료*: 위협 분석, COA 생성, 전술 지도.
    -   *예정*: 채팅 인터페이스 (LLM 상호작용), COA 실행 계획 상세, 보고서 생성, 팔란티어 모드 토글.
2.  **지식 그래프 (`knowledge_graph.py`)**
    -   PyVis/NetworkX를 활용한 온톨로지 시각화 및 탐색.
3.  **데이터 관리 (`data_management.py`)**
    -   Excel 파일 업로드 및 조회 (AgGrid).
4.  **온톨로지 스튜디오 (`ontology_studio.py`)**
    -   온톨로지 구조 및 관계 시각적 편집 도구.
5.  **온톨로지 생성 (`ontology_generation.py`)**
    -   텍스트 기반 LLM 활용 온톨로지 자동 생성.
6.  **RAG 인덱싱 (`rag_indexing.py`)**
    -   문서 업로드 및 벡터 저장소 인덱싱.
7.  **시스템 가이드 (`learning_guide.py`)**
    -   시스템 사용법 및 튜토리얼 문서.

## 3. 리팩토링 로드맵 (Refactoring Roadmap)

### 1단계: 기반 구축 및 검증 (Phase 1: Foundation & Validation) [완료]
-   FastAPI 백엔드 및 React 프론트엔드 기본 구조 설정.
-   기본 위협 분석 및 COA 생성 기능 구현.
-   기본 전술 지도(`react-leaflet`) 구현.
-   **검증**: 프론트엔드-백엔드 연동 및 데이터 흐름 확인 완료.

### 2단계: 지휘통제 핵심 기능 완성 (Phase 2: Complete Command & Control) [진행 중]
`agent_execution.py`의 남은 기능 완전 대체.
-   **채팅 인터페이스**: LLM 상호작용을 위한 지속적인 채팅 패널/Drawer 구현 (`ChatInterface.tsx`) [✅ 완료]
-   **상세 보기**: COA 카드 클릭 시 "추론 근거(Reasoning Explanation)" 및 "실행 계획(Execution Plan)" 표시 [✅ 완료]
    -   `COADetailModal.tsx` 컴포넌트로 구현
    -   추론 근거, 실행 계획, 점수 세부사항, 필요 자원 시각화
-   **보고서 생성**: 백엔드 엔드포인트를 활용한 "PDF/Word 내보내기" 기능 추가 [예정]
-   **통합 테스트**: 프론트엔드-백엔드 E2E 테스트 [예정]
-   **단위 테스트 (Unit Tests)**:
    -   Frontend: 채팅, COA 카드 등 주요 컴포넌트 테스트. [예정]
    -   Backend: `generate_report`, `chat_response` 등 API 테스트. [예정]

### 3단계: 지식 및 데이터 관리 (Phase 3: Knowledge & Data Management)
`knowledge_graph.py` 및 `data_management.py` 대체.
-   **지식 그래프**: `react-force-graph` 또는 `Cytoscape.js`를 활용한 인터랙티브 시각화.
-   **데이터 그리드**: `ag-grid-react`를 활용한 고성능 데이터 조회 및 편집.
-   **단위 테스트**:
    -   Backend: 파일 업로드/다운로드, 그래프 쿼리 테스트.

### 4단계: 고급 온톨로지 도구 (Phase 4: Advanced Ontology Tools)
`ontology_studio.py`, `ontology_generation.py`, `rag_indexing.py` 대체.
-   **온톨로지 스튜디오**: 노드/엣지 편집을 위한 복합 UI 구현.
-   **RAG 대시보드**: 파일 처리 상태 및 인덱싱 현황 시각화.

### 5단계: 시스템 고도화 및 문서화 (Phase 5: System Polish & Documentation)
`learning_guide.py` 및 대시보드 홈 화면 대체.
-   **대시보드 홈**: KPI 위젯 및 임무 현황판 구현.
-   **가이드**: 인터랙티브 튜토리얼 또는 마크다운 뷰어 내장.

## 4. 단위 테스트 전략 (Unit Testing Strategy)

### 4.1 백엔드 (FastAPI + Pytest)
-   **위치**: `tests/api/`
-   **전략**:
    -   모든 `router` 엔드포인트에 대한 테스트 케이스 작성.
    -   `COAService` 및 `Orchestrator`를 Mocking하여 무거움 LLM 호출 배제.
    -   `fastapi.testclient`의 `TestClient` 활용.

### 4.2 프론트엔드 (React + Vitest/Jest)
-   **위치**: `frontend/src/__tests__/`
-   **전략**:
    -   **컴포넌트 테스트**: 주요 UI 컴포넌트(`ThreatAnalysisPanel` 등) 렌더링 및 요소 존재 여부 검증.
    -   **훅(Hook) 테스트**: `useSystemData` 등 커스텀 훅 로직 검증.
    -   **Mocking**: `msw` 또는 `vi.fn()`을 사용하여 API 호출 모의 처리.

## 5. 기술 스택 (To-Be)
-   **Frontend**: React, TypeScript, Vite, Zustand, React Query, TailwindCSS, ShadcnUI.
-   **Map**: React-Leaflet + Milsymbol.
-   **Graph**: React-Force-Graph / Cytoscape.js.
-   **Grid**: Ag-Grid-React.
-   **Backend**: FastAPI, Pydantic, Uvicorn.
