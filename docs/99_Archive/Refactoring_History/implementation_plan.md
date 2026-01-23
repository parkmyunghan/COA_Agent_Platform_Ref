# 누락 기능 구현 설계 및 개발 계획서

## 문서 정보

**작성일**: 2025-01-XX  
**기반 문서**: `feature_comparison_analysis.md`  
**목적**: Streamlit vs React 기능 비교 분석 결과를 바탕으로 누락된 기능들의 구현 설계 및 개발 계획 수립

---

## 1. 개요

### 1.1 현재 상태
- **전체 평균 완성도**: 약 53%
- **가장 완성도 높은 페이지**: 학습 가이드 (80%)
- **가장 완성도 낮은 페이지**: 온톨로지 생성 (30%)

### 1.2 목표
- **단기 목표 (3개월)**: 높은 우선순위 기능 구현으로 완성도 70% 달성
- **중기 목표 (6개월)**: 중간 우선순위 기능 구현으로 완성도 85% 달성
- **장기 목표 (12개월)**: 모든 기능 구현으로 완성도 95% 이상 달성

---

## 2. 우선순위별 구현 계획

## 2.1 높은 우선순위 (Phase 1: 즉시 구현)

### 2.1.1 지휘통제 페이지 - 진행 상황 표시

#### 설계
```typescript
// components/ProgressStatus.tsx
interface ProgressStatusProps {
  label: string;
  progress: number; // 0-100
  logs: string[];
  state: 'running' | 'complete' | 'error';
  onCancel?: () => void;
}
```

**구현 내용**:
- `st.status`와 유사한 UI 컴포넌트 구현
- 진행률 바 (Progress Bar) 표시
- 로그 메시지 스트리밍 표시
- 완료/에러 상태 처리
- 취소 버튼 (선택적)

**기술 스택**:
- React Hooks (`useState`, `useEffect`)
- Tailwind CSS (애니메이션)
- Shadcn UI Progress 컴포넌트

**예상 소요 시간**: 2일

---

### 2.1.2 지휘통제 페이지 - 실행 중 UI 비활성화

#### 설계
```typescript
// hooks/useExecutionState.ts
interface ExecutionState {
  isRunning: boolean;
  progress: number;
  message: string;
}

// components/ExecutionOverlay.tsx
// 전체 화면을 덮는 오버레이로 UI 비활성화
```

**구현 내용**:
- 전역 실행 상태 관리 (Context API)
- 실행 중일 때 전체 UI opacity 조절
- 포인터 이벤트 차단
- 진행 상황 표시는 항상 활성화

**기술 스택**:
- React Context API
- CSS transitions
- Portal (오버레이)

**예상 소요 시간**: 1일

---

### 2.1.3 지휘통제 페이지 - 방책 상세 분석 탭 구조

#### 설계
```typescript
// components/COADetailTabs.tsx
interface COADetailTabsProps {
  coa: COARecommendation;
  tabs: {
    evaluation: COAEvaluationDetails;
    effects: ExpectedEffects;
    references: DoctrineReferences;
    rawData: any;
  };
}
```

**구현 내용**:
- 4개 탭 구조 (평가 세부사항, 기대 효과, 참고 자료, 원본 데이터)
- 각 탭별 전용 컴포넌트
- 데이터 포맷팅 및 시각화
- Shadcn UI Tabs 컴포넌트 활용

**기술 스택**:
- Shadcn UI Tabs
- React Table (데이터 표시)
- Chart.js / Recharts (시각화)

**예상 소요 시간**: 3일

---

### 2.1.4 지식 그래프 페이지 - 그래프 필터 및 검색

#### 설계
```typescript
// components/knowledge/GraphFilterPanel.tsx
interface GraphFilterPanelProps {
  onFilterChange: (filters: GraphFilters) => void;
  availableGroups: string[];
  availableRelations: string[];
}

interface GraphFilters {
  searchTerm: string;
  selectedGroups: string[];
  selectedRelations: string[];
}
```

**구현 내용**:
- 노드 검색 (ID/Label 기반)
- 그룹 필터 (멀티셀렉트)
- 관계 타입 필터 (멀티셀렉트)
- 실시간 필터링 적용
- 필터 상태 URL 파라미터로 저장 (선택적)

**기술 스택**:
- React Hooks (필터 상태 관리)
- Debounce (검색 최적화)
- Cytoscape.js / D3.js (그래프 필터링)

**예상 소요 시간**: 4일

---

### 2.1.5 데이터 관리 페이지 - Excel 파일 업로드

#### 설계
```typescript
// components/data/FileUploader.tsx
interface FileUploaderProps {
  onUpload: (file: File) => Promise<void>;
  acceptedTypes: string[];
  maxSize: number;
}

// API: POST /api/v1/data/upload
```

**구현 내용**:
- 드래그 앤 드롭 업로드
- 파일 선택 다이얼로그
- 파일 유효성 검사 (확장자, 크기)
- 업로드 진행 상황 표시
- 에러 처리

**기술 스택**:
- react-dropzone
- axios (파일 업로드)
- FormData API

**예상 소요 시간**: 2일

---

### 2.1.6 데이터 관리 페이지 - 데이터 편집 기능 강화

#### 설계
```typescript
// components/data/EditableDataGrid.tsx
interface EditableDataGridProps {
  data: any[];
  columns: ColumnDef[];
  onSave: (updatedData: any[]) => Promise<void>;
  editable: boolean;
}
```

**구현 내용**:
- AgGrid 편집 모드 활성화
- 셀 편집 (텍스트, 숫자, 날짜)
- 행 추가/삭제
- 변경사항 임시 저장
- 일괄 저장 기능

**기술 스택**:
- ag-grid-react (편집 기능)
- React Hook Form (폼 검증)

**예상 소요 시간**: 3일

---

### 2.1.7 RAG 관리 페이지 - 문서 업로드

#### 설계
```typescript
// components/rag/DocumentUploader.tsx
interface DocumentUploaderProps {
  onUpload: (files: File[]) => Promise<void>;
  acceptedTypes: string[];
}

// API: POST /api/v1/rag/documents/upload
```

**구현 내용**:
- 다중 파일 업로드
- 파일 목록 미리보기
- 업로드 진행 상황
- 자동 인덱스 재구축 옵션

**기술 스택**:
- react-dropzone
- axios (멀티파트 업로드)

**예상 소요 시간**: 2일

---

### 2.1.8 RAG 관리 페이지 - 인덱스 재구축

#### 설계
```typescript
// components/rag/IndexRebuilder.tsx
interface IndexRebuilderProps {
  onRebuild: () => Promise<void>;
  status: 'idle' | 'building' | 'complete' | 'error';
}

// API: POST /api/v1/rag/index/rebuild
```

**구현 내용**:
- 재구축 버튼
- 진행 상황 표시
- 완료 알림
- 에러 처리

**기술 스택**:
- React Hooks
- WebSocket (실시간 진행 상황, 선택적)

**예상 소요 시간**: 1일

---

## 2.2 중간 우선순위 (Phase 2: 단기 구현)

### 2.2.1 지휘통제 페이지 - Reasoning Trace GeoJSON 시각화

#### 설계
```typescript
// components/TacticalMap.tsx 확장
interface ReasoningTraceLayer {
  type: 'geojson';
  data: GeoJSON.FeatureCollection;
  style: {
    color: string;
    opacity: number;
    weight: number;
  };
}
```

**구현 내용**:
- 지도에 추론 경로 레이어 추가
- 경로 애니메이션 (선택적)
- 클릭 시 상세 정보 표시
- 레이어 토글 기능

**기술 스택**:
- react-leaflet
- Leaflet GeoJSON 플러그인

**예상 소요 시간**: 3일

---

### 2.2.2 지휘통제 페이지 - 배경 적군 부대 표시

#### 설계
```typescript
// components/TacticalMap.tsx 확장
interface EnemyUnitLayer {
  units: EnemyUnit[];
  highlightId?: string; // 현재 선택된 위협
}
```

**구현 내용**:
- 모든 적군 부대를 지도에 표시
- 현재 선택된 위협 하이라이트
- 적군 부대 정보 팝업
- 필터링 옵션 (선택적)

**기술 스택**:
- react-leaflet
- Leaflet Marker 클러스터링

**예상 소요 시간**: 2일

---

### 2.2.3 지휘통제 페이지 - 방책 선정 사유 박스

#### 설계
```typescript
// components/COARationaleBox.tsx
interface COARationaleBoxProps {
  rationale: string;
  searchPath?: string;
  unitRationale?: string;
}
```

**구현 내용**:
- 방책 선정 사유 표시 박스
- 시스템 탐색 과정 표시
- 스타일링 (배경색, 테두리)
- 확장/축소 기능

**기술 스택**:
- Tailwind CSS
- Shadcn UI Card

**예상 소요 시간**: 1일

---

### 2.2.4 지식 그래프 페이지 - 그래프 뷰어 모드 선택

#### 설계
```typescript
// components/knowledge/GraphViewerModeSelector.tsx
type ViewerMode = 'pyvis' | 'd3' | 'cytoscape';

interface GraphViewerModeSelectorProps {
  mode: ViewerMode;
  onModeChange: (mode: ViewerMode) => void;
}
```

**구현 내용**:
- 라디오 버튼으로 모드 선택
- 모드별 그래프 렌더러 전환
- 모드 설정 저장 (localStorage)

**기술 스택**:
- React Hooks
- 각 그래프 라이브러리 (Pyvis, D3.js, Cytoscape.js)

**예상 소요 시간**: 2일

---

### 2.2.5 온톨로지 스튜디오 - 시각화 탭

#### 설계
```typescript
// components/studio/OntologyVisualizer.tsx
interface OntologyVisualizerProps {
  graphData: GraphData;
  onNodeClick?: (node: Node) => void;
}
```

**구현 내용**:
- 온톨로지 그래프 시각화
- 노드/엣지 인터랙션
- 줌/팬 기능
- 레이아웃 알고리즘 선택

**기술 스택**:
- Cytoscape.js 또는 D3.js
- react-cytoscapejs

**예상 소요 시간**: 4일

---

### 2.2.6 온톨로지 스튜디오 - 검증 권장사항 알림

#### 설계
```typescript
// components/studio/ValidationAlert.tsx
interface ValidationAlertProps {
  recommendations: ValidationRecommendation[];
  onNavigate: (tab: string, subtab?: string) => void;
}

interface ValidationRecommendation {
  id: string;
  type: 'warning' | 'error' | 'info';
  message: string;
  relatedTab: string;
  relatedSubtab?: string;
  resolved: boolean;
}
```

**구현 내용**:
- 상단 경고 배너
- 권장사항 목록 표시
- 탭으로 이동 버튼
- 해결 표시 기능

**기술 스택**:
- Shadcn UI Alert
- React Router (탭 네비게이션)

**예상 소요 시간**: 2일

---

### 2.2.7 온톨로지 생성 - 그래프 시각화

#### 설계
```typescript
// components/studio/OntologyGraphViewer.tsx
interface OntologyGraphViewerProps {
  graphData: GraphData;
  onNodeClick?: (node: Node) => void;
  showAnalysis?: boolean;
}
```

**구현 내용**:
- 생성된 그래프 시각화
- 노드 클릭 상호작용
- 그래프 분석 패널 (선택적)
- 그래프 통계 표시

**기술 스택**:
- Pyvis 또는 Cytoscape.js
- react-force-graph (선택적)

**예상 소요 시간**: 3일

---

### 2.2.8 온톨로지 생성 - 그래프 재로드 기능

#### 설계
```typescript
// components/studio/GraphReloadButton.tsx
interface GraphReloadButtonProps {
  onReload: () => Promise<void>;
  loading: boolean;
}

// API: GET /api/v1/ontology/graph/reload
```

**구현 내용**:
- 재로드 버튼
- 로딩 상태 표시
- 성공/실패 알림

**기술 스택**:
- React Hooks
- Shadcn UI Button

**예상 소요 시간**: 0.5일

---

## 2.3 낮은 우선순위 (Phase 3: 장기 구현)

### 2.3.1 온톨로지 스튜디오 - 버전 관리

#### 설계
```typescript
// components/studio/VersionControl.tsx
interface VersionControlProps {
  versions: OntologyVersion[];
  currentVersion: string;
  onVersionChange: (version: string) => void;
  onCreateVersion: (name: string) => Promise<void>;
}
```

**구현 내용**:
- 버전 목록 표시
- 버전 비교
- 버전 생성
- 버전 롤백

**예상 소요 시간**: 5일

---

### 2.3.2 온톨로지 스튜디오 - 피드백 및 개선

#### 설계
```typescript
// components/studio/FeedbackPanel.tsx
interface FeedbackPanelProps {
  onSubmit: (feedback: Feedback) => Promise<void>;
}
```

**구현 내용**:
- 피드백 입력 폼
- 피드백 제출
- 피드백 히스토리

**예상 소요 시간**: 3일

---

### 2.3.3 학습 가이드 - 문서 검색 기능

#### 설계
```typescript
// components/learning/DocumentSearch.tsx
interface DocumentSearchProps {
  documents: Document[];
  onSearch: (query: string) => Document[];
}
```

**구현 내용**:
- 검색 입력창
- 실시간 검색
- 검색 결과 하이라이트

**예상 소요 시간**: 2일

---

## 3. 기술 아키텍처 설계

### 3.1 상태 관리 전략

#### 전역 상태 (Context API)
```typescript
// contexts/ExecutionContext.tsx
interface ExecutionContextValue {
  isRunning: boolean;
  progress: number;
  message: string;
  startExecution: () => void;
  updateProgress: (progress: number, message: string) => void;
  completeExecution: () => void;
  errorExecution: (error: string) => void;
}
```

#### 로컬 상태 (useState)
- 컴포넌트별 독립적인 상태는 `useState` 사용
- 복잡한 상태는 `useReducer` 고려

#### 서버 상태 (React Query)
```typescript
// hooks/useSystemData.ts (기존)
// React Query 사용 고려
```

---

### 3.2 API 설계

#### 새로운 엔드포인트

**데이터 관리**:
```
POST /api/v1/data/upload
  - 파일 업로드
  - Content-Type: multipart/form-data

PUT /api/v1/data/tables/{tableName}
  - 데이터 테이블 업데이트
  - Body: { data: any[] }
```

**RAG 관리**:
```
POST /api/v1/rag/documents/upload
  - 문서 업로드
  - Content-Type: multipart/form-data

POST /api/v1/rag/index/rebuild
  - 인덱스 재구축
  - Response: { status: 'building' | 'complete', progress: number }

GET /api/v1/rag/documents
  - 문서 목록 조회

DELETE /api/v1/rag/documents/{docId}
  - 문서 삭제
```

**온톨로지**:
```
GET /api/v1/ontology/graph/reload
  - 그래프 재로드

GET /api/v1/ontology/validation/recommendations
  - 검증 권장사항 조회
```

---

### 3.3 컴포넌트 구조

```
frontend/src/
├── components/
│   ├── common/
│   │   ├── ProgressStatus.tsx          # 진행 상황 표시
│   │   ├── ExecutionOverlay.tsx        # 실행 중 오버레이
│   │   └── ...
│   ├── command/
│   │   ├── COADetailTabs.tsx           # 방책 상세 탭
│   │   ├── COARationaleBox.tsx         # 방책 선정 사유
│   │   ├── ReasoningTraceLayer.tsx     # 추론 경로 레이어
│   │   └── ...
│   ├── knowledge/
│   │   ├── GraphFilterPanel.tsx        # 그래프 필터
│   │   ├── GraphViewerModeSelector.tsx # 뷰어 모드 선택
│   │   └── ...
│   ├── data/
│   │   ├── FileUploader.tsx            # 파일 업로드
│   │   ├── EditableDataGrid.tsx        # 편집 가능한 그리드
│   │   └── ...
│   ├── rag/
│   │   ├── DocumentUploader.tsx         # 문서 업로드
│   │   ├── IndexRebuilder.tsx          # 인덱스 재구축
│   │   └── ...
│   └── studio/
│       ├── OntologyVisualizer.tsx      # 온톨로지 시각화
│       ├── ValidationAlert.tsx         # 검증 알림
│       └── ...
├── hooks/
│   ├── useExecutionState.ts            # 실행 상태 관리
│   ├── useFileUpload.ts                # 파일 업로드
│   └── ...
└── contexts/
    └── ExecutionContext.tsx            # 실행 컨텍스트
```

---

## 4. 개발 일정

### Phase 1: 높은 우선순위 (3주)

| 주차 | 작업 | 담당 | 소요 시간 |
|------|------|------|----------|
| 1주 | 진행 상황 표시, 실행 중 UI 비활성화 | Frontend | 3일 |
| 1주 | 방책 상세 분석 탭 구조 | Frontend | 3일 |
| 2주 | 그래프 필터 및 검색 | Frontend | 4일 |
| 2주 | Excel 파일 업로드, 데이터 편집 강화 | Frontend | 5일 |
| 3주 | 문서 업로드, 인덱스 재구축 | Frontend | 3일 |
| 3주 | 백엔드 API 개발 | Backend | 5일 |

**총 소요 시간**: 약 15일 (3주)

---

### Phase 2: 중간 우선순위 (4주)

| 주차 | 작업 | 담당 | 소요 시간 |
|------|------|------|----------|
| 4주 | Reasoning Trace 시각화, 배경 적군 표시 | Frontend | 5일 |
| 5주 | 방책 선정 사유 박스, 그래프 뷰어 모드 | Frontend | 3일 |
| 6주 | 온톨로지 시각화 탭, 검증 알림 | Frontend | 6일 |
| 7주 | 그래프 시각화, 재로드 기능 | Frontend | 3.5일 |

**총 소요 시간**: 약 17.5일 (4주)

---

### Phase 3: 낮은 우선순위 (2주)

| 주차 | 작업 | 담당 | 소요 시간 |
|------|------|------|----------|
| 8주 | 버전 관리, 피드백 및 개선 | Frontend | 8일 |
| 9주 | 문서 검색 기능 | Frontend | 2일 |

**총 소요 시간**: 약 10일 (2주)

---

**전체 개발 기간**: 약 9주 (2.25개월)

---

## 5. 테스트 계획

### 5.1 단위 테스트

**대상 컴포넌트**:
- `ProgressStatus`
- `ExecutionOverlay`
- `COADetailTabs`
- `GraphFilterPanel`
- `FileUploader`

**테스트 도구**:
- Vitest
- React Testing Library

**테스트 커버리지 목표**: 70% 이상

---

### 5.2 통합 테스트

**테스트 시나리오**:
1. 파일 업로드 → 데이터 표시 → 편집 → 저장
2. 문서 업로드 → 인덱스 재구축 → 검색
3. COA 생성 → 진행 상황 표시 → 결과 표시

**테스트 도구**:
- Playwright 또는 Cypress

---

### 5.3 E2E 테스트

**주요 시나리오**:
- 전체 워크플로우 테스트
- 사용자 시나리오 기반 테스트

---

## 6. 리스크 관리

### 6.1 기술적 리스크

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| 그래프 라이브러리 성능 이슈 | 높음 | 라이브러리 벤치마크 테스트, 대안 검토 |
| 대용량 파일 업로드 실패 | 중간 | 청크 업로드, 재시도 로직 |
| 실시간 진행 상황 동기화 | 중간 | WebSocket 또는 Polling 구현 |

---

### 6.2 일정 리스크

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| 개발 지연 | 중간 | 우선순위 재조정, 기능 축소 |
| 백엔드 API 지연 | 높음 | Mock API 사용, 병렬 개발 |

---

## 7. 성공 지표

### 7.1 기능 완성도
- Phase 1 완료 시: 70% 이상
- Phase 2 완료 시: 85% 이상
- Phase 3 완료 시: 95% 이상

### 7.2 품질 지표
- 테스트 커버리지: 70% 이상
- 버그 수: 주당 5개 이하
- 사용자 만족도: 4.0/5.0 이상

---

## 8. 다음 단계

### 즉시 시작 가능한 작업
1. ✅ Phase 1 작업 환경 설정
2. ✅ 컴포넌트 구조 설계 확정
3. ✅ API 스펙 정의
4. ✅ 개발 일정 확정

### 준비 작업
1. 백엔드 API 개발자와 협의
2. 디자인 시스템 확정
3. 테스트 환경 구축

---

## 부록

### A. 참고 자료
- [기능 비교 분석 문서](./feature_comparison_analysis.md)
- [리팩토링 마스터 플랜](./refactoring_analysis_design.md)

### B. 관련 문서
- API 명세서 (작성 예정)
- 컴포넌트 스펙 (작성 예정)
- 테스트 계획서 (작성 예정)

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX  
**다음 리뷰 예정일**: Phase 1 완료 시
