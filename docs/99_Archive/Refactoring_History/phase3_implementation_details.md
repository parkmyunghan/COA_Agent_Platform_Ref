# Phase 3 구현 세부사항 (지식 및 데이터 관리)

## 작업 일시
- 시작일: 2026-01-10
- 현재 상태: 시작 (0% 완료)

## 개요

Phase 3에서는 `knowledge_graph.py` 및 `data_management.py`를 React로 마이그레이션합니다.
이를 통해 온톨로지 지식 그래프 시각화 및 데이터 관리 기능을 제공합니다.

## 구현 범위

### 1. 지식 그래프 (Knowledge Graph)
**목적**: 온톨로지 데이터를 시각적으로 탐색하고 SPARQL 쿼리를 실행

**주요 기능**:
- **SPARQL 쿼리 패널**: 사용자 정의 쿼리 실행 및 결과 표시
- **그래프 탐색**: 노드/엣지 필터링 및 인터랙티브 시각화
- **스키마 검증**: 온톨로지 일관성 및 품질 검사

**기술 스택**:
- `react-force-graph-2d` 또는 `cytoscape.js`: 그래프 시각화
- `ag-grid-react`: SPARQL 쿼리 결과 테이블
- `monaco-editor` 또는 `codemirror`: SPARQL 코드 편집기

### 2. 데이터 관리 (Data Management)
**목적**: Excel 원천 데이터 조회 및 품질 검증

**주요 기능**:
- **데이터 그리드**: Ag-Grid를 활용한 고성능 데이터 조회
- **데이터 품질 검증**: 누락 필드, 타입 오류, 중복 데이터 검사
- **데이터 업로드/다운로드**: Excel 파일 업로드 및 편집 결과 내보내기

**기술 스택**:
- `ag-grid-react`: 데이터 그리드
- `react-dropzone`: 파일 업로드
- `xlsx` 라이브러리: Excel 파일 읽기/쓰기

## 작업 계획

### Step 1: 지식 그래프 컴포넌트 개발 (예정)

#### 1.1 SPARQL 쿼리 패널 (`SPARQLQueryPanel.tsx`)
**우선순위**: 높음

**기능**:
- SPARQL 쿼리 입력을 위한 코드 편집기
- 쿼리 실행 버튼 및 로딩 상태 표시
- 쿼리 결과를 테이블 형태로 표시 (Ag-Grid)
- 샘플 쿼리 템플릿 제공 (드롭다운)

**API 엔드포인트**:
```typescript
POST /api/v1/ontology/sparql
{
  "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 100"
}

Response:
{
  "results": [
    {"s": "...", "p": "...", "o": "..."},
    ...
  ],
  "count": 100
}
```

#### 1.2 그래프 탐색 패널 (`GraphExplorerPanel.tsx`)
**우선순위**: 높음

**기능**:
- 노드/엣지 필터링 (그룹, 관계 타입)
- 검색 기능 (노드 레이블)
- 인터랙티브 그래프 시각화 (줌, 드래그, 클릭)
- 노드 클릭 시 상세 정보 표시 (사이드 패널)

**API 엔드포인트**:
```typescript
GET /api/v1/ontology/graph?mode=instances&groups=...&relations=...

Response:
{
  "nodes": [
    {"id": "...", "label": "...", "group": "..."},
    ...
  ],
  "links": [
    {"source": "...", "target": "...", "relation": "..."},
    ...
  ]
}
```

**시각화 라이브러리 선택**:
- **Option 1**: `react-force-graph-2d` (Force-directed layout, 성능 우수)
- **Option 2**: `cytoscape.js` (더 많은 커스터마이징 옵션, 복잡한 레이아웃)

👉 **추천**: `react-force-graph-2d` (빠른 구현, 좋은 성능)

#### 1.3 스키마 검증 패널 (`SchemaValidationPanel.tsx`)
**우선순위**: 중간

**기능**:
- 온톨로지 스키마 일관성 검증 결과 표시
- 경고 및 오류 목록 (누락된 관계, 고아 노드 등)
- 검증 통계 (총 노드 수, 엣지 수, 클래스 수 등)

**API 엔드포인트**:
```typescript
GET /api/v1/ontology/validate

Response:
{
  "status": "valid" | "warning" | "error",
  "statistics": {
    "total_nodes": 1234,
    "total_edges": 5678,
    "classes": 50,
    "individuals": 1184
  },
  "issues": [
    {
      "severity": "warning",
      "message": "Orphaned node: Node123 has no incoming edges",
      "node_id": "Node123"
    }
  ]
}
```

### Step 2: 데이터 관리 컴포넌트 개발 (예정)

#### 2.1 데이터 그리드 (`DataGrid.tsx`)
**우선순위**: 높음

**기능**:
- Ag-Grid를 활용한 고성능 데이터 표시
- 컬럼 필터링, 정렬, 검색
- 셀 편집 (인라인 편집)
- 페이지네이션

**API 엔드포인트**:
```typescript
GET /api/v1/data/tables?table_name=아군부대현황

Response:
{
  "columns": ["부대명", "제대", "병종", ...],
  "rows": [
    {"부대명": "...", "제대": "...", ...},
    ...
  ],
  "total_count": 500
}
```

#### 2.2 데이터 품질 검증 (`DataQualityPanel.tsx`)
**우선순위**: 중간

**기능**:
- 데이터 품질 검증 결과 시각화
- 누락 필드, 타입 오류, 중복 데이터 표시
- 각 테이블별 품질 점수

**API 엔드포인트**:
```typescript
GET /api/v1/data/quality-check

Response:
{
  "tables": [
    {
      "name": "아군부대현황",
      "quality_score": 85,
      "issues": [
        {
          "severity": "error",
          "type": "missing_field",
          "field": "제대",
          "row_index": 10
        }
      ]
    }
  ]
}
```

#### 2.3 파일 업로드 (`FileUpload.tsx`)
**우선순위**: 낮음 (Phase 4로 이연 가능)

**기능**:
- 드래그 앤 드롭 파일 업로드
- Excel 파일 파싱 및 미리보기
- 업로드 진행 상태 표시

**API 엔드포인트**:
```typescript
POST /api/v1/data/upload
FormData: { file: File }

Response:
{
  "success": true,
  "file_name": "...",
  "rows_imported": 123
}
```

### Step 3: 백엔드 API 구현 (예정)

#### 3.1 온톨로지 관련 API
**파일**: `api/routers/ontology.py`

**엔드포인트**:
- `POST /api/v1/ontology/sparql`: SPARQL 쿼리 실행
- `GET /api/v1/ontology/graph`: 그래프 데이터 조회 (필터링 지원)
- `GET /api/v1/ontology/validate`: 스키마 검증

#### 3.2 데이터 관리 관련 API
**파일**: `api/routers/data.py`

**엔드포인트**:
- `GET /api/v1/data/tables`: 데이터 테이블 목록 조회
- `GET /api/v1/data/tables/{table_name}`: 특정 테이블 데이터 조회
- `GET /api/v1/data/quality-check`: 데이터 품질 검증
- `POST /api/v1/data/upload`: 파일 업로드

### Step 4: 라우팅 및 네비게이션 통합 (예정)

**파일**: `frontend/src/App.tsx`

**라우팅 추가**:
```typescript
<Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
<Route path="/data-management" element={<DataManagementPage />} />
```

**네비게이션 메뉴 업데이트**:
- 사이드바에 "지식 그래프", "데이터 관리" 메뉴 추가

## 기술 요구사항

### Frontend 패키지 설치
```bash
npm install --save ag-grid-react ag-grid-community
npm install --save react-force-graph
npm install --save @monaco-editor/react  # SPARQL 편집기
npm install --save react-dropzone xlsx   # 파일 업로드 (Phase 4)
```

### Backend 패키지 설치
이미 설치되어 있음 (`rdflib`, `pandas`, `openpyxl` 등)

## 다음 작업

1. ✅ Phase 3 구현 세부사항 문서 작성
2. ⏳ SPARQL 쿼리 패널 컴포넌트 개발
3. ⏳ 그래프 탐색 패널 컴포넌트 개발
4. ⏳ 백엔드 API 구현 (ontology router)
5. ⏳ 데이터 그리드 컴포넌트 개발
6. ⏳ 백엔드 API 구현 (data router)

## 참고 자료

- [Ag-Grid React Documentation](https://www.ag-grid.com/react-data-grid/)
- [React Force Graph](https://github.com/vasturiano/react-force-graph)
- [Cytoscape.js](https://js.cytoscape.org/)
- [Monaco Editor for React](https://www.npmjs.com/package/@monaco-editor/react)
