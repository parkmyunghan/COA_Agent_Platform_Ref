# Streamlit vs React 기능 비교 분석 자료

## 개요

본 문서는 Streamlit으로 구현된 파일럿 시스템과 React로 리팩토링된 시스템 간의 기능 비교 분석 자료입니다. 각 페이지별로 구현된 기능과 누락된 기능을 상세히 비교합니다.

**작성일**: 2025-01-XX  
**비교 대상**: 
- Streamlit 시스템: `ui/views/` 디렉토리
- React 시스템: `frontend/src/pages/` 디렉토리

---

## 1. 지휘통제/분석 페이지 (Command & Control)

### Streamlit: `ui/views/agent_execution.py`
### React: `frontend/src/pages/CommandControlPage.tsx`

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| Agent 선택 | `render_agent_selector` | `AgentSelector` | ✅ 완료 |
| 상황 정보 입력 | `render_situation_input` | `SituationInputPanel` | ✅ 완료 |
| 상황 요약 표시 | `render_situation_summary` | `SituationSummaryPanel` | ✅ 완료 |
| 상황 브리핑 배너 | 커스텀 HTML/CSS | `SituationBanner` | ✅ 완료 |
| 팔란티어 모드 토글 | 사이드바 체크박스 | `SettingsPanel` | ✅ 완료 |
| 방책 유형 필터 | 멀티셀렉트 | `SettingsPanel` | ✅ 완료 |
| 전술 지도 (COP) | `render_tactical_map` | `TacticalMap` | ✅ 완료 |
| 위협 분석 패널 | `ThreatAnalysisPanel` | `ThreatAnalysisPanel` | ✅ 완료 |
| COA 생성 및 표시 | Agent 실행 결과 | `COAGenerator` | ✅ 완료 |
| 채팅 인터페이스 | `render_chat_interface_v2` | `ChatInterface` | ✅ 완료 |
| COA 상세 모달 | Expander 기반 | `COADetailModal` | ✅ 완료 |
| 추론 근거 설명 | `render_reasoning_explanation` | `ReasoningExplanationPanel` | ✅ 완료 |
| 실행 계획 | `render_coa_execution_plan` | `COAExecutionPlanPanel` | ✅ 완료 |
| 전략 체인 시각화 | `ChainVisualizer` | `ChainVisualizer` | ✅ 완료 |
| 교리 참조 표시 | `render_doctrine_references` | `DoctrineReferencePanel` | ✅ 완료 |
| 보고서 생성 | `render_report_download_button` | `ReportGenerator` | ✅ 완료 |
| 축선별 전장분석 | `AxisSummaryPanel` | `AxisSummaryPanel` | ✅ 완료 |
| 시스템 상태 카드 | 커스텀 위젯 | `StatusCard` | ✅ 완료 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| 진행 상황 표시 (Status) | `st.status` with progress bar | ❌ 미구현 | 높음 |
| 실행 중 UI 비활성화 | CSS 기반 opacity 조절 | ❌ 미구현 | 중간 |
| 방책 선택 드롭다운 | `st.selectbox`로 상세 분석 대상 선택 | ❌ 미구현 | 중간 |
| 방책 카드 상세 탭 | 4개 탭 (평가 세부사항, 기대 효과, 참고 자료, 원본 데이터) | ⚠️ 부분 구현 | 중간 |
| 교리 기반 설명 | `render_doctrine_based_explanation` | ❌ 미구현 | 낮음 |
| 온톨로지 추론 흔적 표시 | 인라인 표시 | ⚠️ 부분 구현 | 낮음 |
| 방책 선정 사유 박스 | 커스텀 HTML 박스 | ❌ 미구현 | 중간 |
| 시스템 탐색 과정 표시 | 커스텀 HTML 박스 | ❌ 미구현 | 낮음 |
| 파이프라인 상태 표시 | 사이드바 상태 표시 | ❌ 미구현 | 낮음 |
| LLM 협력 모드 토글 | 체크박스 | ❌ 미구현 | 낮음 |
| Reasoning Trace GeoJSON | 지도에 추론 경로 표시 | ❌ 미구현 | 중간 |
| 배경 적군 부대 표시 | 지도에 모든 적군 표시 | ❌ 미구현 | 중간 |
| 온톨로지 보강 (enrich) | `enrich_situation_info_with_ontology` | ⚠️ 부분 구현 | 중간 |
| 상황 정보 자동 저장 | `st.session_state` | ⚠️ 부분 구현 | 낮음 |
| 스크롤 자동 이동 | JavaScript 기반 | ❌ 미구현 | 낮음 |

#### 📊 구현 완성도: 약 70%

**주요 누락 사항**:
- 진행 상황 표시 및 실행 중 UI 상태 관리
- 방책 상세 분석 UI (탭 구조)
- 지도 상의 Reasoning Trace 시각화
- 배경 적군 부대 표시

---

## 2. 지식 그래프 탐색 페이지 (Knowledge Graph)

### Streamlit: `ui/views/knowledge_graph.py`
### React: `frontend/src/pages/KnowledgeGraphPage.tsx`

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| SPARQL 쿼리 실행 | `render_sparql_query_panel` | `SPARQLQueryPanel` | ✅ 완료 |
| 그래프 탐색 | `render_graph` / `render_enhanced_graph` | `GraphExplorerPanel` | ✅ 완료 |
| 스키마 검증 | `render_ontology_dashboard_panel` | `SchemaValidationPanel` | ✅ 완료 |
| 노드 정보 패널 | `render_node_info_panel` | 노드 클릭 시 표시 | ⚠️ 부분 구현 |
| 온톨로지 설명 | `render_ontology_explainer` | ❌ 미구현 | ❌ 미구현 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| 그래프 필터 및 검색 | 노드 검색, 그룹 필터, 관계 필터 | ❌ 미구현 | 높음 |
| 그래프 뷰어 모드 선택 | 라디오 버튼 (Pyvis vs D3.js) | ❌ 미구현 | 중간 |
| 추론된 그래프 사용 옵션 | 체크박스 | ❌ 미구현 | 중간 |
| 노드 클릭 콜백 | 세션 상태에 저장 | ⚠️ 부분 구현 | 중간 |
| 그래프 데이터 필터링 | 실시간 필터링 로직 | ❌ 미구현 | 높음 |
| 그래프 분석 패널 | `show_analysis=True` 옵션 | ❌ 미구현 | 낮음 |
| 온톨로지 관계 설명 | `render_ontology_explainer` | ❌ 미구현 | 낮음 |

#### 📊 구현 완성도: 약 50%

**주요 누락 사항**:
- 그래프 필터링 및 검색 기능
- 그래프 뷰어 모드 선택
- 노드 클릭 상호작용 개선
- 온톨로지 설명 패널

---

## 3. 데이터 관리 페이지 (Data Management)

### Streamlit: `ui/views/data_management.py`
### React: `frontend/src/pages/DataManagementPage.tsx`

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| 데이터 그리드 | `render_data_panel` | `DataGridPanel` | ✅ 완료 |
| 데이터 품질 검증 | `render_data_quality_checker` | `DataQualityPanel` | ✅ 완료 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| Excel 파일 업로드 | `st.file_uploader` | ⚠️ 부분 구현 | 높음 |
| 데이터 테이블 편집 | AgGrid 편집 기능 | ⚠️ 부분 구현 | 높음 |
| 컬럼 추가/삭제 | 동적 컬럼 관리 | ❌ 미구현 | 중간 |
| 데이터 저장 | 파일 시스템 저장 | ⚠️ 부분 구현 | 높음 |
| 데이터 테이블 선택 | 드롭다운으로 테이블 선택 | ⚠️ 부분 구현 | 중간 |
| 데이터 미리보기 | 상세 미리보기 | ⚠️ 부분 구현 | 낮음 |
| 데이터 통계 | 기본 통계 정보 | ❌ 미구현 | 낮음 |

#### 📊 구현 완성도: 약 40%

**주요 누락 사항**:
- 파일 업로드 기능 완전 구현
- 데이터 편집 기능 강화
- 컬럼 관리 기능
- 데이터 저장 기능

---

## 4. 온톨로지 스튜디오 페이지 (Ontology Studio)

### Streamlit: `ui/views/ontology_studio.py`
### React: `frontend/src/pages/OntologyStudioPage.tsx`

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| 개요 탭 | `render_overview` | 개요 통계 | ✅ 완료 |
| 관계 관리 | `render_relationship_manager` | `RelationshipManagerPanel` | ✅ 완료 |
| 품질 보증 | `render_quality_assurance` | `QualityAssurancePanel` | ✅ 완료 |
| 그래프 생성 | 온톨로지 생성 통합 | 그래프 생성 탭 | ✅ 완료 |
| 추론 테스트 | `render_inference_manager` | `InferenceTestPanel` | ✅ 완료 |
| 스키마 상세 | `render_schema_manager` | `SchemaDetailsPanel` | ✅ 완료 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| 스키마 관리 탭 | `render_schema_manager` | ⚠️ 부분 구현 | 높음 |
| 시각화 탭 | `render_visualizer` | ❌ 미구현 | 중간 |
| 버전 관리 탭 | `render_version_control` | ❌ 미구현 | 낮음 |
| 피드백 및 개선 탭 | `render_feedback_improvement` | ❌ 미구현 | 낮음 |
| 검증 권장사항 알림 | 상단 경고 배너 | ❌ 미구현 | 중간 |
| 탭 간 네비게이션 | 세션 상태 기반 | ❌ 미구현 | 낮음 |
| 스키마 요약 표시 | 상세 통계 | ⚠️ 부분 구현 | 중간 |
| 가상 엔티티 옵션 | 체크박스 | ✅ 완료 | - |
| 추론 그래프 옵션 | 체크박스 | ✅ 완료 | - |

#### 📊 구현 완성도: 약 60%

**주요 누락 사항**:
- 시각화 탭
- 버전 관리 기능
- 피드백 및 개선 기능
- 검증 권장사항 알림

---

## 5. 온톨로지 생성 페이지 (Ontology Generation)

### Streamlit: `ui/views/ontology_generation.py`
### React: `frontend/src/pages/OntologyStudioPage.tsx` (통합됨)

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| 그래프 생성 버튼 | `st.button` | 그래프 생성 탭 | ✅ 완료 |
| 가상 엔티티 옵션 | 체크박스 | 체크박스 | ✅ 완료 |
| 추론 그래프 옵션 | 체크박스 | 체크박스 | ✅ 완료 |
| 그래프 통계 표시 | `st.metric`, 상세 통계 | 통계 카드 | ⚠️ 부분 구현 |
| 그래프 시각화 | `render_graph` | ❌ 미구현 | ❌ 미구현 |
| 노드 정보 패널 | `render_node_info_panel` | ❌ 미구현 | ❌ 미구현 |
| 그래프 재로드 | 재로드 버튼 | ❌ 미구현 | 중간 |
| 온톨로지 관계 관리 | `render_ontology_manager_panel` | ❌ 미구현 | 중간 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| 그래프 생성 진행 상황 | `st.spinner` | ❌ 미구현 | 높음 |
| 상세 통계 표시 | Expander 내 상세 통계 | ❌ 미구현 | 중간 |
| 그래프 시각화 | Pyvis 기반 시각화 | ❌ 미구현 | 높음 |
| 노드 클릭 상호작용 | 콜백 함수 | ❌ 미구현 | 중간 |
| 그래프 재로드 기능 | 재로드 버튼 | ❌ 미구현 | 중간 |
| 온톨로지 자동 로드 | 페이지 진입 시 자동 로드 | ❌ 미구현 | 낮음 |
| 그룹별 상세 정보 | 데이터프레임 표시 | ❌ 미구현 | 낮음 |
| 변환 비율 표시 | 상세 통계 | ❌ 미구현 | 낮음 |

#### 📊 구현 완성도: 약 30%

**주요 누락 사항**:
- 그래프 시각화 기능
- 상세 통계 표시
- 그래프 재로드 기능
- 온톨로지 관계 관리 패널

**참고**: 이 페이지는 React에서 `OntologyStudioPage`에 통합되었습니다.

---

## 6. RAG 인덱싱 페이지 (RAG Management)

### Streamlit: `ui/views/rag_indexing.py`
### React: `frontend/src/pages/RAGManagementPage.tsx`

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| 문서 관리 탭 | `render_doc_manager` | 문서 관리 탭 | ⚠️ 부분 구현 |
| 인덱스 상태 탭 | `render_index_status` | 상태 대시보드 | ⚠️ 부분 구현 |
| 검색 테스트 탭 | 검색 인터페이스 | 검색 테스트 탭 | ✅ 완료 |
| 모델 상태 표시 | 성공/경고 메시지 | 상태 카드 | ✅ 완료 |
| 인덱스 현황 표시 | `get_rag_index_status` | 상태 카드 | ✅ 완료 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| 문서 업로드 | `render_doc_manager` 내 파일 업로더 | ❌ 미구현 | 높음 |
| 문서 목록 표시 | 업로드된 문서 목록 | ⚠️ 부분 구현 | 높음 |
| 문서 삭제 | 삭제 버튼 | ❌ 미구현 | 중간 |
| 인덱스 재구축 | 재구축 버튼 | ❌ 미구현 | 높음 |
| 인덱스 수정 옵션 | `show_fix_option=True` | ❌ 미구현 | 중간 |
| 검색 결과 인용 표시 | `render_citation_panel` | ❌ 미구현 | 중간 |
| 검색어 하이라이트 | 검색어 강조 표시 | ❌ 미구현 | 낮음 |
| Top-K 설정 | 숫자 입력 | ⚠️ 부분 구현 | 낮음 |
| 검색 진행 상황 | `st.spinner` | ❌ 미구현 | 낮음 |

#### 📊 구현 완성도: 약 40%

**주요 누락 사항**:
- 문서 업로드 기능
- 인덱스 재구축 기능
- 문서 관리 기능 (삭제, 목록 관리)
- 검색 결과 인용 표시

---

## 7. 학습 가이드 페이지 (Learning Guide)

### Streamlit: `ui/views/learning_guide.py`
### React: `frontend/src/pages/LearningGuidePage.tsx`

#### ✅ 구현 완료된 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| 문서 카테고리 분류 | 디렉토리 기반 분류 | API 기반 분류 | ✅ 완료 |
| 문서 목록 표시 | Expander 기반 | 사이드바 목록 | ✅ 완료 |
| 문서 내용 표시 | 마크다운/HTML | `ReactMarkdown`/iframe | ✅ 완료 |
| HTML 문서 임베드 | `components.html` | iframe | ✅ 완료 |
| 문서 열기/닫기 | 세션 상태 관리 | 상태 관리 | ✅ 완료 |

#### ❌ 누락된 기능

| 기능 | Streamlit 구현 | React 상태 | 우선순위 |
|------|---------------|-----------|---------|
| 문서 제목 변환 | 파일명 기반 변환 | ⚠️ 부분 구현 | 낮음 |
| 컴포넌트 서브레이어 그룹화 | 서브레이어별 Expander | ❌ 미구현 | 낮음 |
| 문서 검색 기능 | 텍스트 검색 | ❌ 미구현 | 중간 |
| 문서 즐겨찾기 | 즐겨찾기 기능 | ❌ 미구현 | 낮음 |
| 최근 본 문서 | 세션 기반 기록 | ❌ 미구현 | 낮음 |

#### 📊 구현 완성도: 약 80%

**주요 누락 사항**:
- 문서 검색 기능
- 서브레이어별 그룹화 (Components)

---

## 8. 전체 시스템 기능 비교

### 공통 기능

| 기능 | Streamlit | React | 상태 |
|------|-----------|-------|------|
| 시스템 초기화 | Orchestrator 초기화 | API 기반 | ✅ 완료 |
| 에러 처리 | `render_user_friendly_error` | 기본 에러 처리 | ⚠️ 부분 구현 |
| 다크 모드 | CSS 기반 | Tailwind 다크 모드 | ✅ 완료 |
| 반응형 레이아웃 | Streamlit 기본 | Tailwind 반응형 | ✅ 완료 |

### 누락된 공통 기능

| 기능 | 설명 | 우선순위 |
|------|------|---------|
| 사용자 인증 | `user_auth.py` | 낮음 |
| 알림 패널 | `notifications_panel.py` | 낮음 |
| 워크플로우 상태 | `workflow_status_dashboard.py` | 낮음 |
| 실시간 시뮬레이터 | `realtime_simulator.py` | 낮음 |
| 벤치마크 패널 | `benchmark_panel.py` | 낮음 |

---

## 9. 우선순위별 구현 권장사항

### 높은 우선순위 (즉시 구현 필요)

1. **지휘통제 페이지**
   - 진행 상황 표시 (Status with Progress Bar)
   - 실행 중 UI 비활성화
   - 방책 상세 분석 탭 구조 완성

2. **지식 그래프 페이지**
   - 그래프 필터 및 검색 기능
   - 그래프 뷰어 모드 선택

3. **데이터 관리 페이지**
   - Excel 파일 업로드 기능
   - 데이터 편집 기능 강화

4. **RAG 관리 페이지**
   - 문서 업로드 기능
   - 인덱스 재구축 기능

### 중간 우선순위 (단기 구현)

1. **지휘통제 페이지**
   - Reasoning Trace GeoJSON 시각화
   - 배경 적군 부대 표시
   - 방책 선정 사유 박스

2. **온톨로지 스튜디오**
   - 시각화 탭
   - 검증 권장사항 알림

3. **온톨로지 생성**
   - 그래프 시각화
   - 그래프 재로드 기능

### 낮은 우선순위 (장기 구현)

1. 버전 관리 기능
2. 피드백 및 개선 기능
3. 사용자 인증
4. 알림 시스템
5. 벤치마크 패널

---

## 10. 기술적 차이점

### Streamlit의 장점
- 빠른 프로토타이핑
- Python 기반으로 백엔드 로직과 통합 용이
- 세션 상태 관리 자동화
- 내장 컴포넌트 풍부

### React의 장점
- 더 나은 사용자 경험 (빠른 반응성)
- 컴포넌트 재사용성
- 타입 안정성 (TypeScript)
- 현대적인 UI/UX

### 마이그레이션 시 고려사항
- Streamlit의 `st.session_state` → React의 `useState`/Context API
- Streamlit의 `st.rerun()` → React의 상태 업데이트
- Python 기반 컴포넌트 → TypeScript/React 컴포넌트
- Streamlit 위젯 → Shadcn UI / 커스텀 컴포넌트

---

## 11. 구현 완성도 요약

| 페이지 | Streamlit 기능 수 | React 구현 수 | 완성도 |
|--------|------------------|--------------|--------|
| 지휘통제/분석 | ~25개 | ~18개 | 70% |
| 지식 그래프 | ~8개 | ~4개 | 50% |
| 데이터 관리 | ~7개 | ~2개 | 40% |
| 온톨로지 스튜디오 | ~8개 | ~6개 | 60% |
| 온톨로지 생성 | ~10개 | ~3개 | 30% |
| RAG 인덱싱 | ~9개 | ~4개 | 40% |
| 학습 가이드 | ~6개 | ~5개 | 80% |

**전체 평균 완성도: 약 53%**

---

## 12. 다음 단계 권장사항

1. **1단계 (즉시)**: 높은 우선순위 기능 구현
2. **2단계 (단기)**: 중간 우선순위 기능 구현
3. **3단계 (장기)**: 낮은 우선순위 기능 및 개선사항

각 기능 구현 시 Streamlit 컴포넌트의 로직을 참고하여 React 컴포넌트로 변환하되, React의 장점을 활용한 개선을 권장합니다.

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX
