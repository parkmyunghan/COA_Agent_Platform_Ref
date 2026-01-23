# 방책(COA) 생성 기능 설계 문서

## 문서 정보

**작성일**: 2025-01-XX  
**목적**: 지휘통제 페이지의 방책 생성 버튼 작동 문제 해결 및 전체 플로우 설계  
**대상 시스템**: React 프론트엔드 + FastAPI 백엔드

---

## 1. 문제 분석

### 1.1 현재 상태

**프론트엔드 (`COAGenerator.tsx`)**:
- 버튼 비활성화 조건: `disabled={loading || (!selectedThreat && !situationInfo)}`
- API 호출: `POST /api/v1/coa/generate`
- 응답 처리: `COAResponse` 타입으로 받아서 카드 목록 표시
- **문제점**: 
  - 버튼이 비활성화되어 클릭 불가능한 경우 존재
  - 응답이 와도 지도에 COA가 시각화되지 않음
  - 진행 상황 표시 없음
  - **방책 선택 UI 없음** (Streamlit에서는 상위 3개 방책 선택 가능)
  - **선정 사유 및 추론 근거 표시 없음** (Streamlit에서는 `reasoning_explanation` 컴포넌트로 표시)
  - **RAG 문서 참조 표시 없음** (Streamlit에서는 `doctrine_reference_display` 컴포넌트로 표시)
  - **전략 연계 시각화 없음** (Streamlit에서는 `chain_visualizer` 컴포넌트로 표시)
  - **방책 실행 계획 표시 없음** (Streamlit에서는 `coa_execution_plan` 컴포넌트로 표시)
  - **보고서 생성 기능 없음** (Streamlit에서는 `report_download_button` 컴포넌트로 표시)
  - **채팅 인터페이스 연동 없음** (Streamlit에서는 `chat_interface_v2`로 LLM 상호작용)
  - **방책 카드에 추가 정보 부족** (참여 부대, 방책 유형, 선정 카테고리, 시스템 탐색 과정 등)

**백엔드 (`api/routers/coa.py`)**:
- 엔드포인트: `POST /coa/generate`
- `COAService.generate_coas_unified()` 호출
- 응답: `COAResponse` (coas, axis_states, original_request)

**지도 컴포넌트 (`TacticalMap.tsx`)**:
- 현재: missions와 threats만 표시
- **문제점**: COA 추천 결과를 지도에 표시하지 않음

---

## 2. 전체 플로우 설계

### 2.1 방책 생성 워크플로우

```
[사용자 입력]
    ↓
[입력 검증]
    ↓
[API 요청 생성]
    ↓
[백엔드 처리]
    ├─ 위협/임무 정보 로드
    ├─ Axis State 계산
    ├─ COA 생성
    ├─ COA 평가
    └─ 결과 반환
    ↓
[프론트엔드 응답 처리]
    ├─ COA 목록 표시
    ├─ Axis States 표시
    └─ 지도 시각화
        ├─ 위협 마커
        ├─ COA 마커/라인
        └─ 추론 경로 (선택적)
```

---

## 3. 입력 정보 수집 및 검증

### 3.1 입력 방식 (4가지)

Streamlit 구현에서는 4가지 입력 방식을 지원했습니다. React 구현에서도 동일하게 지원해야 합니다:

#### 1. 엑셀 위협정보 읽기 (`실제 데이터에서 선택`)

**Streamlit 구현**:
- `ui/components/situation_input.py`의 `render_real_data_selection_ui()` 함수
- `data_lake/위협상황.xlsx` 파일에서 위협 정보 로드
- 드롭다운으로 위협 선택
- 선택 시 자동으로 상황 정보 채움

**React 구현 필요사항**:
```typescript
// components/SituationInputPanel.tsx
// 현재: 'real_data' 모드로 구현되어 있음
// 개선 필요:
// 1. 엑셀 파일 직접 업로드 기능 추가 (선택)
// 2. 또는 백엔드 API로 위협 목록 조회 후 선택
```

**백엔드 API**:
- `GET /data/threats` - 위협 목록 조회 (이미 구현됨)
- 엑셀 파일에서 직접 읽는 경우: `DataManager.load_table('위협상황')`

#### 2. SITREP 텍스트 입력 (`SITREP 텍스트 입력`)

**Streamlit 구현**:
- `ui/components/situation_input.py`의 `render_sitrep_input_ui()` 함수
- 텍스트 입력 후 `SITREPParser`로 파싱
- 백엔드 `/threat/analyze` API 호출

**React 구현 상태**:
- ✅ 이미 구현됨 (`SituationInputPanel.tsx`의 `sitrep` 모드)
- `POST /threat/analyze` API 호출
- 파싱된 위협 정보를 상황 정보로 변환

#### 3. 시나리오 선택 (`데모 시나리오`)

**Streamlit 구현**:
- `ui/components/demo_scenario.py`의 `render_demo_scenario_selection_ui()` 함수
- 미리 정의된 데모 시나리오 목록 (`DEMO_SCENARIOS`)
- 시나리오 선택 시 자동으로 상황 정보 로드
- 시나리오별 위협/임무 정보 자동 채움

**React 구현 필요사항**:
```typescript
// components/SituationInputPanel.tsx
// 추가 필요: 'scenario' 입력 모드
const DEMO_SCENARIOS = [
    {
        id: "scenario_1",
        name: "시나리오 1: 적군 정찰기 침입",
        description: "적 정찰기가 경계 지역 침입 시 방책 추천",
        threat_type: "정찰",
        severity: 75,
        location: "경계지역",
        // ... 기타 필드
    },
    // ... 더 많은 시나리오
];

// 시나리오 선택 UI 추가
{inputMode === 'scenario' && (
    <select
        value={situation.selected_scenario_id || ''}
        onChange={(e) => {
            const scenario = DEMO_SCENARIOS.find(s => s.id === e.target.value);
            if (scenario) {
                updateSituation({
                    selected_scenario_id: scenario.id,
                    threat_type: scenario.threat_type,
                    threat_level: scenario.severity / 100.0,
                    location: scenario.location,
                    // ... 기타 필드 매핑
                });
            }
        }}
    >
        <option value="">시나리오 선택...</option>
        {DEMO_SCENARIOS.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
        ))}
    </select>
)}
```

**백엔드 API (선택적)**:
- `GET /scenarios` - 시나리오 목록 조회 (구현 필요)
- 또는 프론트엔드에 하드코딩

#### 4. 수동 입력 (`수동 입력`)

**Streamlit 구현**:
- `ui/components/situation_input.py`의 `render_manual_input()` 함수
- 사용자가 직접 모든 필드 입력
- 위협 중심/임무 중심 모드별 다른 입력 폼

**React 구현 상태**:
- ✅ 이미 구현됨 (`SituationInputPanel.tsx`의 `manual` 모드)
- 위협 중심/임무 중심 모드별 다른 입력 폼 제공

### 3.2 입력 방식별 데이터 흐름

```
[입력 방식 선택]
    ↓
┌─────────────────────────────────────────┐
│ 1. 엑셀 위협정보 읽기                    │
│    - GET /data/threats                  │
│    - 드롭다운에서 위협 선택              │
│    - 선택된 위협 데이터를 situation에 반영│
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. SITREP 텍스트 입력                    │
│    - 텍스트 입력                         │
│    - POST /threat/analyze               │
│    - 파싱된 위협 정보를 situation에 반영 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 3. 시나리오 선택                         │
│    - 시나리오 목록에서 선택              │
│    - 시나리오 데이터를 situation에 반영 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 4. 수동 입력                            │
│    - 사용자가 직접 모든 필드 입력        │
│    - 입력값을 situation에 저장          │
└─────────────────────────────────────────┘
    ↓
[situation 정보 완성]
    ↓
[방책 생성 버튼 활성화]
```

### 3.3 필수 입력 정보

#### 위협 중심 모드 (Threat-Centered)
```typescript
interface ThreatCenteredInput {
    // 필수
    threat_id?: string;              // 기존 위협 ID
    threat_data?: ThreatEventBase;    // 새로 입력한 위협 데이터
    
    // 위협 데이터 필드
    threat_type: string;              // 위협 유형
    threat_level: number;             // 위협 수준 (0-1)
    location: string;                 // 발생 장소
    axis_id?: string;                 // 관련 축선 ID
    
    // 선택
    latitude?: number;                // 위도
    longitude?: number;               // 경도
    environment?: string;             // 환경 정보
    defense_assets?: string[];        // 방어 자산
    resource_availability?: any;     // 자원 가용성
    
    // 임무 정보 (선택)
    mission_id?: string;              // 관련 임무 ID
}
```

#### 임무 중심 모드 (Mission-Centered)
```typescript
interface MissionCenteredInput {
    // 필수
    mission_id: string;               // 임무 ID
    
    // 임무 데이터 필드
    mission_type?: string;            // 임무 유형
    mission_objective?: string;       // 임무 목표
    commander_intent?: string;        // 지휘관 의도
    
    // 선택
    approach_mode: 'mission_centered';
    situation_info?: {
        environment?: string;
        defense_assets?: string[];
        resource_availability?: any;
    };
}
```

### 3.2 입력 검증 로직

```typescript
// components/COAGenerator.tsx
const validateInput = (): ValidationResult => {
    const errors: string[] = [];
    
    // 위협 중심 모드 검증
    if (approachMode === 'threat_centered') {
        if (!threatToUse && !selectedThreat) {
            errors.push('위협 정보가 필요합니다.');
        }
        
        if (threatToUse) {
            if (!threatToUse.threat_type) {
                errors.push('위협 유형을 입력해주세요.');
            }
            if (threatToUse.threat_level === undefined || threatToUse.threat_level < 0 || threatToUse.threat_level > 1) {
                errors.push('위협 수준은 0-1 사이의 값이어야 합니다.');
            }
            if (!threatToUse.location) {
                errors.push('발생 장소를 입력해주세요.');
            }
        }
    }
    
    // 임무 중심 모드 검증
    if (approachMode === 'mission_centered') {
        if (!selectedMission?.mission_id && !situationInfo?.mission_id) {
            errors.push('임무 정보가 필요합니다.');
        }
    }
    
    return {
        isValid: errors.length === 0,
        errors
    };
};
```

---

## 4. API 요청 구조

### 4.1 요청 페이로드

```typescript
interface COAGenerationRequest {
    threat_id?: string;
    mission_id?: string;
    threat_data?: ThreatEventBase;
    user_params: {
        max_coas: number;                    // 기본값: 3
        approach_mode: 'threat_centered' | 'mission_centered';
        use_palantir_mode: boolean;          // 기본값: true
        coa_type_filter?: string[];          // ['Defense', 'Offensive', ...]
        situation_info?: {
            situation_id: string;
            environment?: string;
            defense_assets?: string[];
            resource_availability?: any;
        };
    };
}
```

### 4.2 요청 생성 로직

```typescript
// components/COAGenerator.tsx
const buildRequest = (): COAGenerationRequest => {
    const approachMode = situationInfo?.approach_mode || 'threat_centered';
    const threatToUse = situationInfo 
        ? buildThreatFromSituation(situationInfo) 
        : selectedThreat;
    
    return {
        threat_id: threatToUse?.threat_id || selectedThreat?.threat_id,
        threat_data: threatToUse || selectedThreat,
        mission_id: selectedMission?.mission_id || situationInfo?.mission_id,
        user_params: {
            max_coas: 3,
            approach_mode: approachMode,
            use_palantir_mode: usePalantirMode,
            coa_type_filter: coaTypeFilter.length > 0 ? coaTypeFilter : undefined,
            ...(situationInfo && {
                situation_info: {
                    situation_id: situationInfo.situation_id,
                    environment: situationInfo.environment,
                    defense_assets: situationInfo.defense_assets,
                    resource_availability: situationInfo.resource_availability
                }
            })
        }
    };
};
```

---

## 5. 백엔드 처리 로직

### 5.1 COAService.generate_coas_unified() 플로우

```python
# core_pipeline/coa_service.py
def generate_coas_unified(
    self,
    mission_id: Optional[str] = None,
    threat_id: Optional[str] = None,
    threat_event: Optional[ThreatEvent] = None,
    user_params: Optional[Dict] = None
) -> Dict:
    """
    1. 위협/임무 정보 로드
    2. Axis State 계산
    3. COA 생성
    4. COA 평가
    5. 결과 반환
    """
    
    # 1. 위협/임무 정보 로드
    if threat_event:
        # 동적으로 생성된 위협 사용
        threat = threat_event
    elif threat_id:
        # 파일에서 로드
        threat = self.data_manager.load_threat(threat_id)
    
    if mission_id:
        mission = self.data_manager.load_mission(mission_id)
    
    # 2. Axis State 계산
    axis_states = self.axis_state_builder.build_axis_states(
        threat=threat,
        mission=mission
    )
    
    # 3. COA 생성
    coas = self.coa_generator.generate_coas(
        mission_id=mission_id,
        axis_states=axis_states,
        user_params=user_params
    )
    
    # 4. COA 평가
    evaluations = []
    for coa in coas:
        eval_result = self.coa_evaluator.evaluate_coa(
            coa=coa,
            axis_states=axis_states,
            threat=threat,
            mission=mission,
            user_params=user_params
        )
        evaluations.append(eval_result)
    
    # 5. 정렬 및 상위 선택
    top_coas = sorted(
        evaluations,
        key=lambda e: e.total_score,
        reverse=True
    )[:user_params.get('max_coas', 3)]
    
    return {
        "coas": coas,
        "evaluations": evaluations,
        "top_coas": top_coas,
        "axis_states": axis_states
    }
```

### 5.2 응답 매핑

```python
# api/routers/coa.py
@router.post("/generate", response_model=COAResponse)
def generate_coas(request: COAGenerationRequest, ...):
    result = service.generate_coas_unified(...)
    
    # COAEvaluation → COASummary 변환
    coas_summary = []
    for idx, coa_eval in enumerate(result["top_coas"]):
        summary = service.get_coa_summary(coa_eval)
        coas_summary.append(COASummary(
            coa_id=coa_eval.coa_id,
            coa_name=summary.get('coa_name'),
            total_score=summary.get('total_score', 0.0),
            rank=idx + 1,
            description=summary.get('description', ''),
            combat_power_score=summary.get('combat_power_score', 0.0),
            mobility_score=summary.get('mobility_score', 0.0),
            constraint_score=summary.get('constraint_compliance_score', 0.0),
            threat_response_score=summary.get('threat_response_score', 0.0),
            risk_score=summary.get('risk_score', 0.0),
            # 추가 필드
            reasoning_trace=coa_eval.reasoning_trace,
            execution_plan=coa_eval.execution_plan,
            required_resources=coa_eval.required_resources,
            # 지도 시각화용
            participating_units=coa_eval.participating_units,
            unit_positions=coa_eval.unit_positions,  # GeoJSON 형식
            coa_geojson=coa_eval.coa_geojson  # COA 경로/영역 GeoJSON
        ))
    
    return COAResponse(
        coas=coas_summary,
        axis_states=[axis.to_dict() for axis in result["axis_states"]],
        original_request=request
    )
```

---

## 6. 프론트엔드 응답 처리

### 6.0 전체 응답 처리 플로우

```
[API 응답 수신]
    ↓
[응답 데이터 검증]
    ├─ coas 배열 확인 (최대 3개)
    ├─ axis_states 확인
    └─ 메타데이터 확인
    ↓
[상위 3개 방책 추출]
    ├─ 점수 기준 정렬
    └─ max_coas 제한 적용
    ↓
[방책 선택 UI 표시]
    ├─ 드롭다운으로 방책 선택
    └─ 선택된 방책 하이라이트
    ↓
[선택된 방책 상세 정보 표시]
    ├─ 선정 사유
    ├─ 추론 근거
    ├─ 전략 연계
    ├─ 실행 계획
    ├─ RAG 문서 참조
    └─ 온톨로지 추론 경로
    ↓
[지도 시각화]
    ├─ COA 마커/라인
    ├─ 부대 배치
    └─ 추론 경로
    ↓
[보고서 생성 옵션]
    └─ 다운로드 버튼
```

### 6.1 방책 선택 및 상세 정보 표시 (누락된 기능)

**Streamlit 구현**:
- 상위 3개 방책 추천 (`recommendations[:3]`)
- `st.selectbox`로 방책 선택 UI
- 선택된 방책의 상세 정보 표시:
  - **선정 사유** (`justification`)
  - **추론 근거** (`reasoning_explanation.py`)
  - **RAG 문서** (`doctrine_references`)
  - **점수 세부 분석** (`score_breakdown`)
  - **온톨로지 추론 경로** (`reasoning_trace`)

**React 구현 필요사항**:
```typescript
// components/COAGenerator.tsx 또는 새로운 COASelectionPanel.tsx
interface COASelectionPanelProps {
    coas: COASummary[]; // 최대 3개
    selectedCOA: COASummary | null;
    onCOASelect: (coa: COASummary) => void;
}

// 1. 방책 선택 UI
const COASelectionPanel: React.FC<COASelectionPanelProps> = ({ coas, selectedCOA, onCOASelect }) => {
    return (
        <div className="space-y-4">
            <h3 className="font-bold text-lg">추천 방책 선택 (상위 3개)</h3>
            <select
                value={selectedCOA?.coa_id || ''}
                onChange={(e) => {
                    const coa = coas.find(c => c.coa_id === e.target.value);
                    if (coa) onCOASelect(coa);
                }}
                className="w-full p-2 border rounded"
            >
                <option value="">방책 선택...</option>
                {coas.map((coa, idx) => (
                    <option key={coa.coa_id} value={coa.coa_id}>
                        {idx + 1}. {coa.coa_name} (점수: {(coa.total_score * 100).toFixed(1)}%)
                    </option>
                ))}
            </select>
        </div>
    );
};
```

### 6.2 선정 사유 및 추천 근거 표시

**필요한 데이터 구조**:
```typescript
interface COASummary {
    coa_id: string;
    coa_name: string;
    total_score: number;
    rank: number;
    description?: string;
    
    // 선정 사유 및 추론 근거
    reasoning?: {
        justification?: string;        // 방책 선정 사유
        situation_assessment?: string; // 상황 판단
        pros?: string[];               // 기대 효과
        cons?: string[];               // 위험 요소
        unit_rationale?: string;       // 부대 운용 근거
        system_search_path?: string;   // 시스템 탐색 과정
    };
    
    // 점수 세부 분석
    score_breakdown?: {
        combat_power_score?: number;
        mobility_score?: number;
        constraint_score?: number;
        threat_response_score?: number;
        reasoning?: Array<{
            factor: string;
            score: number;
            weight: number;
            weighted_score: number;
            reason: string;
        }>;
    };
    
    // 온톨로지 추론 경로
    reasoning_trace?: string[];
    
    // RAG 문서 참조
    doctrine_references?: Array<{
        reference_type: 'doctrine' | 'general';
        doctrine_id?: string;
        statement_id?: string;
        source: string;
        excerpt: string;
        relevance_score: number;
        mett_c_elements?: string[];
    }>;
}
```

**컴포넌트 설계**:
```typescript
// components/COADetailPanel.tsx
interface COADetailPanelProps {
    coa: COASummary;
}

export const COADetailPanel: React.FC<COADetailPanelProps> = ({ coa }) => {
    return (
        <div className="space-y-6">
            {/* 1. 방책 선정 사유 */}
            {coa.reasoning?.justification && (
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                    <h4 className="font-bold text-sm mb-2">🛡️ 방책 선정 사유</h4>
                    <p className="text-sm">{coa.reasoning.justification}</p>
                </div>
            )}
            
            {/* 2. 점수 세부 분석 */}
            {coa.score_breakdown && (
                <ReasoningExplanationPanel coa={coa} />
            )}
            
            {/* 3. RAG 문서 참조 */}
            {coa.doctrine_references && coa.doctrine_references.length > 0 && (
                <DoctrineReferencePanel references={coa.doctrine_references} />
            )}
            
            {/* 4. 온톨로지 추론 경로 */}
            {coa.reasoning_trace && coa.reasoning_trace.length > 0 && (
                <ReasoningTracePanel trace={coa.reasoning_trace} />
            )}
        </div>
    );
};
```

### 6.3 RAG 문서 표시 (교리 참조)

**Streamlit 구현**:
- `doctrine_reference_display.py`에서 교리 문서와 일반 문서 구분 표시
- 각 문서의 관련도 점수, METT-C 요소 표시
- 교리 문장 본문 하이라이트

**React 구현 필요사항**:
```typescript
// components/DoctrineReferencePanel.tsx
interface DoctrineReference {
    reference_type: 'doctrine' | 'general';
    doctrine_id?: string;
    statement_id?: string;
    source: string;
    excerpt: string;
    relevance_score: number;
    mett_c_elements?: string[];
}

interface DoctrineReferencePanelProps {
    references: DoctrineReference[];
}

export const DoctrineReferencePanel: React.FC<DoctrineReferencePanelProps> = ({ references }) => {
    // 교리 문서와 일반 문서 구분
    const doctrineRefs = references.filter(r => r.reference_type === 'doctrine');
    const generalRefs = references.filter(r => r.reference_type === 'general');
    
    return (
        <div className="space-y-4">
            <h4 className="font-bold text-lg">📚 적용된 참고 자료</h4>
            
            {/* 교리 문서 */}
            {doctrineRefs.length > 0 && (
                <div>
                    <h5 className="font-semibold mb-2">📖 교리 문서</h5>
                    {doctrineRefs.map((ref, idx) => (
                        <div key={idx} className="p-4 mb-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                            <div className="flex justify-between items-start mb-2">
                                <span className="font-bold text-sm">
                                    [{ref.statement_id || ref.doctrine_id}]
                                </span>
                                <span className="text-xs text-gray-500">
                                    관련도: {(ref.relevance_score * 100).toFixed(1)}%
                                </span>
                            </div>
                            <p className="text-sm italic text-gray-700 dark:text-gray-300 mb-2">
                                "{ref.excerpt}"
                            </p>
                            {ref.mett_c_elements && ref.mett_c_elements.length > 0 && (
                                <div className="text-xs text-gray-500">
                                    관련 METT-C: {ref.mett_c_elements.join(', ')}
                                </div>
                            )}
                            <div className="mt-2">
                                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1">
                                    <div
                                        className="bg-blue-500 h-1 rounded-full"
                                        style={{ width: `${ref.relevance_score * 100}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
            
            {/* 일반 문서 */}
            {generalRefs.length > 0 && (
                <div>
                    <h5 className="font-semibold mb-2">📄 일반 참고 문서</h5>
                    {generalRefs.map((ref, idx) => (
                        <div key={idx} className="p-4 mb-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border-l-4 border-yellow-500">
                            {/* 동일한 구조 */}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
```

### 6.4 전략 연계 시각화 (Chain Visualizer)

**Streamlit 구현**:
- `ui/components/chain_visualizer.py`의 `ChainVisualizer` 클래스
- 선택된 방책의 전략 연계 체인 표시
- `chain_info_details` 또는 `chain_info` 데이터 사용

**React 구현 필요사항**:
```typescript
// components/ChainVisualizer.tsx (이미 존재하는지 확인 필요)
// 선택된 방책의 chain_info 표시
{selectedCOA?.chain_info && (
    <ChainVisualizer chainInfo={selectedCOA.chain_info} />
)}
```

**필요한 데이터 구조**:
```typescript
interface ChainInfo {
    chains?: Array<{
        from: string;
        to: string;
        relationship: string;
        description?: string;
    }>;
    summary?: string;
}
```

### 6.5 방책 실행 계획 (Execution Plan)

**Streamlit 구현**:
- `ui/components/coa_execution_plan.py`의 `render_coa_execution_plan()` 함수
- 최우수 방책(rank 1)의 실행 계획 표시
- 단계별 실행 계획, 필요 자원, 위험 요소, 예상 소요 시간

**React 구현 상태**:
- ✅ `COAExecutionPlanPanel.tsx` 컴포넌트 존재
- 확인 필요: CommandControlPage에서 사용되는지

**필요한 데이터 구조**:
```typescript
interface ExecutionPlan {
    phases: Array<{
        name: string;
        description: string;
        tasks: string[];
        duration?: string;
        responsible?: string;
        priority?: 'high' | 'medium' | 'low';
    }>;
    required_resources?: Array<{
        resource_id: string;
        name: string;
        type: string;
        quantity?: number;
    }>;
    risks?: Array<{
        element: string;
        level: 'high' | 'medium' | 'low';
        description: string;
        response: string;
    }>;
    estimated_time?: string;
}
```

### 6.6 보고서 생성 기능

**Streamlit 구현**:
- `ui/components/report_generator.py`의 `render_report_download_button()` 함수
- 방책 추천 결과를 보고서로 다운로드
- 인용 정보(citations) 포함

**React 구현 상태**:
- ✅ `ReportGenerator.tsx` 컴포넌트 존재
- 확인 필요: CommandControlPage에서 사용되는지

**필요한 기능**:
```typescript
// components/ReportGenerator.tsx
interface ReportGeneratorProps {
    agentName: string;
    summary: string;
    coaRecommendations: COASummary[];
    citations?: Array<{
        source: string;
        excerpt: string;
        relevance_score: number;
    }>;
}

// 보고서 다운로드 기능
const handleDownloadReport = async () => {
    // POST /report/generate API 호출
    // PDF/Word 형식으로 다운로드
};
```

### 6.7 채팅 인터페이스 연동

**Streamlit 구현**:
- `ui/components/chat_interface_v2.py`의 `render_chat_interface()` 함수
- LLM 실시간 상호작용
- 인용 모드 (RAG 검색 결과 근거 표시)
- 메시지 히스토리 관리

**React 구현 상태**:
- ✅ `ChatInterface.tsx` 컴포넌트 존재
- 확인 필요: CommandControlPage에서 제대로 연동되는지
- 확인 필요: COA 생성 결과를 채팅으로 질문할 수 있는지

**필요한 기능**:
```typescript
// pages/CommandControlPage.tsx
// 채팅 인터페이스에 COA 결과 전달
<ChatInterface 
    coaRecommendations={lastResponse?.coas || []}
    selectedCOA={selectedCOA}
    onQuestion={(question) => {
        // LLM에 질문 전달
        // 예: "이 방책의 위험 요소는 무엇인가요?"
    }}
/>
```

### 6.8 방책 카드 추가 정보 표시

**Streamlit 구현**:
- 방책 카드에 다음 정보 표시:
  - 참여 부대 (participating_units)
  - 방책 유형 (coa_type) - 한글 변환
  - 선정 카테고리 (selection_category) - 한글 변환
  - 시스템 탐색 과정 (system_search_path)
  - 교리 참조 인라인 표시
  - 온톨로지 추론 흔적

**React 구현 필요사항**:
```typescript
// components/COACard.tsx 개선
const COACard: React.FC<{ coa: COASummary; onClick: () => void }> = ({ coa, onClick }) => {
    // 방책 유형 한글 변환
    const coaTypeMap = {
        "Defense": "방어",
        "Offensive": "공세",
        "Counter_Attack": "반격",
        "Preemptive": "선제",
        "Deterrence": "억제",
        "Maneuver": "기동",
        "Information_Ops": "정보작전"
    };
    
    // 선정 카테고리 한글 변환
    const categoryMap = {
        "Operational Optimum": "작전 최적",
        "Maneuver & Speed": "기동/속도",
        "Firepower Focus": "화력 집중",
        "Sustainable Defense": "지속 방어"
    };
    
    return (
        <div onClick={onClick} className="...">
            {/* 기존 내용 */}
            
            {/* 추가 정보 */}
            <div className="flex items-center gap-2 mb-2">
                <span className="badge">{coaTypeMap[coa.coa_type] || coa.coa_type}</span>
                <span className="badge">{categoryMap[coa.selection_category] || coa.selection_category}</span>
            </div>
            
            {/* 참여 부대 */}
            {coa.participating_units && (
                <div className="text-xs text-gray-500">
                    ⚓ {Array.isArray(coa.participating_units) 
                        ? coa.participating_units.join(', ')
                        : coa.participating_units}
                </div>
            )}
            
            {/* 시스템 탐색 과정 */}
            {coa.reasoning?.system_search_path && (
                <div className="text-xs text-gray-400 italic mt-2">
                    🔍 {coa.reasoning.system_search_path}
                </div>
            )}
        </div>
    );
};
```

### 6.9 응답 데이터 구조

```typescript
interface COAResponse {
    coas: COASummary[];
    axis_states: AxisState[];
    original_request: COAGenerationRequest;
    analysis_time?: string;
}

interface COASummary {
    coa_id: string;
    coa_name: string;
    total_score: number;
    rank: number;
    description?: string;
    combat_power_score?: number;
    mobility_score?: number;
    constraint_score?: number;
    threat_response_score?: number;
    risk_score?: number;
    // 지도 시각화용
    participating_units?: string[];
    unit_positions?: GeoJSON.FeatureCollection;
    coa_geojson?: GeoJSON.FeatureCollection;
    reasoning_trace?: any[];
}
```

### 6.2 응답 처리 로직

```typescript
// components/COAGenerator.tsx
const handleGenerate = async () => {
    // 1. 입력 검증
    const validation = validateInput();
    if (!validation.isValid) {
        setError(validation.errors.join(', '));
        return;
    }
    
    // 2. 로딩 상태 시작
    setLoading(true);
    setError(null);
    setResponse(null);
    
    try {
        // 3. 요청 생성
        const payload = buildRequest();
        
        // 4. API 호출
        const res = await api.post<COAResponse>('/coa/generate', payload);
        
        // 5. 응답 처리
        setResponse(res.data);
        
        // 6. 부모 컴포넌트에 전달 (지도 시각화용)
        if (onResponse) {
            onResponse(res.data);
        }
        
        // 7. 성공 알림
        // (토스트 또는 상태 업데이트)
        
    } catch (err: any) {
        console.error('COA 생성 오류:', err);
        setError(
            err.response?.data?.detail || 
            err.message || 
            '방책 생성 중 오류가 발생했습니다.'
        );
    } finally {
        setLoading(false);
    }
};
```

---

## 7. COP 시각화 설계

### 7.1 지도에 표시할 요소

1. **위협 마커** (기존)
   - 위치: 위협 발생 지점
   - 스타일: 적군 마커 (빨간색)
   - 선택된 위협은 하이라이트

2. **COA 마커/라인** (신규)
   - **부대 배치 마커**: 각 COA의 참여 부대 위치
   - **작전 경로 라인**: COA별 작전 경로
   - **작전 영역 폴리곤**: COA별 작전 영역
   - **추론 경로**: Reasoning Trace 시각화 (선택적)

3. **임무 마커** (기존)
   - 위치: 임무 수행 지점
   - 스타일: 아군 마커 (파란색)

### 7.2 TacticalMap 컴포넌트 확장

```typescript
// components/TacticalMap.tsx
interface TacticalMapProps {
    missions?: MissionBase[];
    threats?: ThreatEventBase[];
    selectedThreat?: ThreatEventBase | null;
    // 신규 추가
    coaRecommendations?: COASummary[];
    selectedCOA?: COASummary | null;
    onCOAClick?: (coa: COASummary) => void;
}

export const TacticalMap: React.FC<TacticalMapProps> = ({
    missions = [],
    threats = [],
    selectedThreat,
    coaRecommendations = [],
    selectedCOA,
    onCOAClick
}) => {
    // COA GeoJSON 레이어 추가
    const coaLayers = useMemo(() => {
        if (!coaRecommendations.length) return [];
        
        return coaRecommendations.map(coa => ({
            coa_id: coa.coa_id,
            coa_name: coa.coa_name,
            geojson: coa.coa_geojson,
            unit_positions: coa.unit_positions,
            isSelected: selectedCOA?.coa_id === coa.coa_id
        }));
    }, [coaRecommendations, selectedCOA]);
    
    return (
        <MapContainer ...>
            {/* 기존 마커들 */}
            {markers.map(...)}
            
            {/* COA 레이어 추가 */}
            {coaLayers.map(layer => (
                <GeoJSON
                    key={layer.coa_id}
                    data={layer.geojson}
                    style={{
                        color: layer.isSelected ? '#ff6b6b' : '#4ecdc4',
                        weight: layer.isSelected ? 4 : 2,
                        opacity: 0.7
                    }}
                    onEachFeature={(feature, layer) => {
                        layer.on('click', () => {
                            if (onCOAClick) {
                                const coa = coaRecommendations.find(c => c.coa_id === layer.coa_id);
                                if (coa) onCOAClick(coa);
                            }
                        });
                    }}
                />
            ))}
            
            {/* 부대 배치 마커 */}
            {coaRecommendations.flatMap(coa => 
                (coa.unit_positions?.features || []).map((feature, idx) => (
                    <Marker
                        key={`${coa.coa_id}-unit-${idx}`}
                        position={[feature.geometry.coordinates[1], feature.geometry.coordinates[0]]}
                        icon={createMilSymbolIcon({
                            sidc: feature.properties.sidc || 'SFGPUCI----K---',
                            size: selectedCOA?.coa_id === coa.coa_id ? 35 : 25
                        })}
                    >
                        <Popup>
                            <div>
                                <h4>{coa.coa_name}</h4>
                                <p>{feature.properties.unit_name}</p>
                            </div>
                        </Popup>
                    </Marker>
                ))
            )}
        </MapContainer>
    );
};
```

### 7.3 CommandControlPage에서 COA 전달

```typescript
// pages/CommandControlPage.tsx
const [coaResponse, setCOAResponse] = useState<COAResponse | null>(null);
const [selectedCOA, setSelectedCOA] = useState<COASummary | null>(null);

const handleCOAResponse = (res: COAResponse) => {
    setCOAResponse(res);
    setLastResponse(res);
};

// TacticalMap에 COA 전달
<TacticalMap
    missions={missions}
    threats={threats}
    selectedThreat={selectedThreat}
    coaRecommendations={coaResponse?.coas || []}
    selectedCOA={selectedCOA}
    onCOAClick={setSelectedCOA}
/>
```

---

## 8. 진행 상황 표시

### 8.1 ProgressStatus 컴포넌트

```typescript
// components/common/ProgressStatus.tsx
interface ProgressStatusProps {
    label: string;
    progress: number; // 0-100
    logs: string[];
    state: 'running' | 'complete' | 'error';
    onCancel?: () => void;
}

export const ProgressStatus: React.FC<ProgressStatusProps> = ({
    label,
    progress,
    logs,
    state,
    onCancel
}) => {
    return (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 
                        bg-white dark:bg-zinc-900 rounded-lg shadow-xl border 
                        border-gray-200 dark:border-zinc-700 p-4 min-w-[400px]">
            <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-sm">{label}</h3>
                {onCancel && state === 'running' && (
                    <button onClick={onCancel} className="text-xs text-gray-500">취소</button>
                )}
            </div>
            
            {/* Progress Bar */}
            <div className="w-full h-2 bg-gray-200 dark:bg-zinc-800 rounded-full mb-2">
                <div 
                    className="h-full bg-blue-600 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                />
            </div>
            
            <div className="text-xs text-gray-500 mb-2">{progress}%</div>
            
            {/* Logs */}
            {logs.length > 0 && (
                <div className="max-h-32 overflow-y-auto text-xs text-gray-600 dark:text-gray-400">
                    {logs.map((log, idx) => (
                        <div key={idx} className="py-0.5">{log}</div>
                    ))}
                </div>
            )}
        </div>
    );
};
```

### 8.2 ExecutionContext (전역 상태)

```typescript
// contexts/ExecutionContext.tsx
interface ExecutionContextValue {
    isRunning: boolean;
    progress: number;
    message: string;
    logs: string[];
    startExecution: () => void;
    updateProgress: (progress: number, message: string) => void;
    addLog: (log: string) => void;
    completeExecution: () => void;
    errorExecution: (error: string) => void;
}

export const ExecutionContext = createContext<ExecutionContextValue | null>(null);

export const ExecutionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isRunning, setIsRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState('');
    const [logs, setLogs] = useState<string[]>([]);
    
    const startExecution = () => {
        setIsRunning(true);
        setProgress(0);
        setMessage('방책 생성 시작...');
        setLogs([]);
    };
    
    const updateProgress = (newProgress: number, newMessage: string) => {
        setProgress(newProgress);
        setMessage(newMessage);
    };
    
    const addLog = (log: string) => {
        setLogs(prev => [...prev, log]);
    };
    
    const completeExecution = () => {
        setIsRunning(false);
        setProgress(100);
        setMessage('방책 생성 완료');
    };
    
    const errorExecution = (error: string) => {
        setIsRunning(false);
        setMessage(`오류: ${error}`);
        addLog(`[ERROR] ${error}`);
    };
    
    return (
        <ExecutionContext.Provider value={{
            isRunning,
            progress,
            message,
            logs,
            startExecution,
            updateProgress,
            addLog,
            completeExecution,
            errorExecution
        }}>
            {children}
        </ExecutionContext.Provider>
    );
};
```

### 8.3 COAGenerator에서 진행 상황 표시

```typescript
// components/COAGenerator.tsx
const { startExecution, updateProgress, addLog, completeExecution, errorExecution } = useContext(ExecutionContext);

const handleGenerate = async () => {
    // 검증...
    
    startExecution();
    addLog('방책 생성 요청 전송...');
    
    try {
        const payload = buildRequest();
        addLog('백엔드 처리 중...');
        updateProgress(30, 'COA 생성 중...');
        
        const res = await api.post<COAResponse>('/coa/generate', payload);
        
        updateProgress(70, 'COA 평가 중...');
        addLog('COA 평가 완료');
        
        updateProgress(90, '결과 처리 중...');
        setResponse(res.data);
        
        if (onResponse) onResponse(res.data);
        
        updateProgress(100, '완료');
        addLog('방책 생성 완료');
        completeExecution();
        
    } catch (err: any) {
        errorExecution(err.response?.data?.detail || err.message);
        setError(...);
    }
};
```

---

## 9. 버튼 활성화 조건 개선

### 9.1 현재 문제

```typescript
// 현재: 버튼이 비활성화되는 조건이 너무 엄격함
disabled={loading || (!selectedThreat && !situationInfo)}
```

**문제점**:
- `situationInfo`가 있어도 `selectedThreat`가 없으면 비활성화될 수 있음
- 임무 중심 모드에서는 `selectedThreat`가 필요 없음

### 9.2 개선된 조건

```typescript
// components/COAGenerator.tsx
const isButtonDisabled = (): boolean => {
    if (loading) return true;
    
    const approachMode = situationInfo?.approach_mode || 'threat_centered';
    
    // 위협 중심 모드: 위협 정보 필요
    if (approachMode === 'threat_centered') {
        return !selectedThreat && !situationInfo;
    }
    
    // 임무 중심 모드: 임무 정보 필요
    if (approachMode === 'mission_centered') {
        return !selectedMission && !situationInfo?.mission_id;
    }
    
    return false;
};

<button
    onClick={handleGenerate}
    disabled={isButtonDisabled()}
    className={...}
>
    방책 추천 실행
</button>
```

---

## 10. 에러 처리 및 사용자 피드백

### 10.1 에러 타입별 처리

```typescript
// components/COAGenerator.tsx
const handleError = (err: any) => {
    if (err.response) {
        // HTTP 에러
        const status = err.response.status;
        const detail = err.response.data?.detail || '알 수 없는 오류';
        
        switch (status) {
            case 400:
                setError(`입력 오류: ${detail}`);
                break;
            case 404:
                setError(`리소스를 찾을 수 없습니다: ${detail}`);
                break;
            case 500:
                setError(`서버 오류: ${detail}`);
                break;
            default:
                setError(`오류 발생 (${status}): ${detail}`);
        }
    } else if (err.request) {
        // 네트워크 에러
        setError('서버에 연결할 수 없습니다. 네트워크를 확인해주세요.');
    } else {
        // 기타 에러
        setError(`오류 발생: ${err.message}`);
    }
};
```

### 10.2 사용자 피드백

- **로딩 중**: ProgressStatus 표시
- **성공**: 토스트 알림 + 결과 표시
- **실패**: 에러 메시지 표시 + 재시도 옵션

---

## 11. 구현 체크리스트

### 11.1 프론트엔드

#### 전체 기능 체크리스트

**기본 기능**
- [x] Agent 선택 (AgentSelector)
- [x] 상황 정보 입력 (SituationInputPanel) - 3가지 방식 구현됨
- [x] 시스템 설정 (SettingsPanel)
- [x] 방책 생성 버튼 (COAGenerator)
- [x] 채팅 인터페이스 (ChatInterface) - 존재하나 연동 확인 필요

**입력 방식 구현**
- [x] 수동 입력 (manual) - 구현 완료
- [x] 실제 데이터에서 선택 (real_data) - 구현 완료
- [x] SITREP 텍스트 입력 (sitrep) - 구현 완료
- [ ] **시나리오 선택 (scenario) - 구현 필요**
  - [ ] DEMO_SCENARIOS 데이터 정의
  - [ ] 시나리오 선택 UI 추가
  - [ ] 시나리오 데이터를 situation 정보로 변환
  - [ ] 시나리오 상세 정보 표시

#### 방책 생성 기능
- [ ] 입력 검증 로직 구현
- [ ] 버튼 활성화 조건 개선
- [ ] ProgressStatus 컴포넌트 구현
- [ ] ExecutionContext 구현
- [ ] COAGenerator에 진행 상황 통합
- [ ] TacticalMap에 COA 레이어 추가
- [ ] COA GeoJSON 파싱 및 표시
- [ ] 부대 배치 마커 표시
- [ ] COA 클릭 이벤트 처리
- [ ] 에러 처리 개선
- [ ] CommandControlPage에서 COA 상태 관리

#### 방책 선택 및 상세 정보 표시 (누락된 기능)
- [ ] **상위 3개 방책 추천 표시**
  - [ ] COASelectionPanel 컴포넌트 구현
  - [ ] 방책 선택 드롭다운 UI
  - [ ] 선택된 방책 하이라이트
  - [ ] 방책 카드에 추가 정보 표시
    - [ ] 참여 부대 (participating_units)
    - [ ] 방책 유형 (coa_type) 한글 변환
    - [ ] 선정 카테고리 (selection_category) 한글 변환
- [ ] **선정 사유 표시**
  - [ ] `justification` 필드 표시
  - [ ] `situation_assessment` 표시
  - [ ] `unit_rationale` 표시
  - [ ] `system_search_path` (시스템 탐색 과정) 표시
- [ ] **추론 근거 상세 분석**
  - [ ] ReasoningExplanationPanel 개선
  - [ ] 점수 세부 분석 차트
  - [ ] 점수 요인별 설명
- [ ] **전략 연계 시각화** (누락됨)
  - [ ] ChainVisualizer 컴포넌트 확인/개선
  - [ ] `chain_info_details` 또는 `chain_info` 표시
  - [ ] 전략 체인 그래프 시각화
- [ ] **방책 실행 계획** (누락됨)
  - [ ] COAExecutionPlanPanel 확인/개선
  - [ ] 최우수 방책 실행 계획 표시
  - [ ] 단계별 실행 계획
  - [ ] 필요 자원 목록
  - [ ] 위험 요소 및 대응 방안
  - [ ] 예상 소요 시간
- [ ] **RAG 문서 참조 표시**
  - [ ] DoctrineReferencePanel 구현/개선
  - [ ] 교리 문서와 일반 문서 구분
  - [ ] 관련도 점수 표시
  - [ ] METT-C 요소 표시
  - [ ] 문서 본문 하이라이트
  - [ ] 인라인 표시 옵션 (방책 카드 내)
- [ ] **온톨로지 추론 경로 표시**
  - [ ] ReasoningTracePanel 구현
  - [ ] 추론 단계별 시각화
  - [ ] 온톨로지 추론 흔적 (reasoning_trace) 표시
- [ ] **보고서 생성 기능** (누락됨)
  - [ ] ReportGenerator 컴포넌트 확인/개선
  - [ ] 방책 추천 결과 보고서 다운로드
  - [ ] 인용 정보 포함
  - [ ] PDF/Word 형식 지원
- [ ] **백엔드 응답에 필요한 필드 확인**
  - [ ] `reasoning` 객체 포함 확인
  - [ ] `doctrine_references` 포함 확인
  - [ ] `reasoning_trace` 포함 확인
  - [ ] `score_breakdown` 포함 확인
  - [ ] `chain_info_details` 또는 `chain_info` 포함 확인
  - [ ] `participating_units` 포함 확인
  - [ ] `coa_type` 포함 확인
  - [ ] `selection_category` 포함 확인
  - [ ] `execution_plan` 포함 확인 (또는 별도 API 필요)

#### 기타 기능
- [ ] **상황 요약 표시**
  - [x] SituationSummaryPanel 구현됨
  - [x] SituationBanner 구현됨
  - [ ] 상황 브리핑 배너와 연동 확인
- [ ] **진행 상황 표시**
  - [ ] ProgressStatus 컴포넌트 구현
  - [ ] ExecutionContext 구현
  - [ ] 진행률 바 및 로그 표시
  - [ ] 상태 업데이트 콜백
- [ ] **채팅 인터페이스 연동**
  - [x] ChatInterface 컴포넌트 존재
  - [ ] COA 결과와 연동 확인
  - [ ] LLM 질문 기능 확인
  - [ ] 인용 모드 확인

### 11.2 백엔드

- [ ] `generate_coas_unified` 메서드 검증
- [ ] COA GeoJSON 생성 로직 확인
- [ ] 부대 위치 정보 포함 확인
- [ ] 응답에 `coa_geojson` 필드 추가
- [ ] 응답에 `unit_positions` 필드 추가
- [ ] **응답에 `reasoning` 객체 포함 확인**
  - [ ] `justification` (선정 사유)
  - [ ] `situation_assessment` (상황 판단)
  - [ ] `unit_rationale` (부대 운용 근거)
  - [ ] `system_search_path` (시스템 탐색 과정)
- [ ] **응답에 `doctrine_references` 포함 확인**
  - [ ] 교리 문서 참조
  - [ ] 일반 문서 참조
  - [ ] 관련도 점수
  - [ ] METT-C 요소
- [ ] **응답에 `reasoning_trace` 포함 확인**
  - [ ] 온톨로지 추론 경로
- [ ] **응답에 `score_breakdown` 포함 확인**
  - [ ] 점수 요인별 세부 분석
  - [ ] `reasoning` 배열 (요인별 점수 및 근거)
- [ ] **응답에 `execution_plan` 포함 확인**
  - [ ] 단계별 실행 계획
  - [ ] 필요 자원 목록
  - [ ] 위험 요소 및 대응 방안
  - [ ] 예상 소요 시간
- [ ] **응답에 `participating_units` 포함 확인**
  - [ ] 참여 부대 목록
  - [ ] 부대별 역할
- [ ] **응답에 `coa_type` 및 `selection_category` 포함 확인**
- [ ] 에러 메시지 개선

---

## 12. 테스트 시나리오

### 12.1 위협 중심 모드

1. **시나리오 1: 기존 위협 선택**
   - 위협 목록에서 위협 선택
   - 임무 선택 (선택)
   - 방책 추천 실행
   - 결과 확인

2. **시나리오 2: 수동 입력**
   - SituationInputPanel에서 수동 입력
   - 위협 유형, 수준, 장소 입력
   - 방책 추천 실행
   - 결과 확인

3. **시나리오 3: SITREP 분석**
   - SITREP 텍스트 입력
   - 분석 실행
   - 방책 추천 실행
   - 결과 확인

### 12.2 임무 중심 모드

1. **시나리오 1: 임무 선택**
   - 임무 목록에서 임무 선택
   - 방책 추천 실행
   - 결과 확인

### 12.3 지도 시각화

1. **COA 마커 표시**
   - 방책 생성 후 지도에 COA 마커 표시 확인
   - COA 클릭 시 상세 정보 표시 확인

2. **부대 배치 표시**
   - 각 COA의 참여 부대 위치 표시 확인

3. **작전 경로 표시**
   - COA별 작전 경로 라인 표시 확인

---

## 13. 예상 문제 및 해결 방안

### 13.1 문제: COA GeoJSON이 응답에 없음

**원인**: 백엔드에서 GeoJSON 생성 로직이 없거나 응답에 포함되지 않음

**해결**:
1. 백엔드 `COAService`에서 GeoJSON 생성 로직 확인
2. `scenario_mapper.py`의 `map_coa_to_geojson` 함수 활용
3. 응답 스키마에 `coa_geojson` 필드 추가

### 13.2 문제: 부대 위치 정보 없음

**원인**: COA에 참여 부대 정보는 있지만 위치 정보가 없음

**해결**:
1. 백엔드에서 부대 위치 조회 로직 추가
2. StatusManager 또는 데이터베이스에서 위치 정보 조회
3. 응답에 `unit_positions` GeoJSON 포함

### 13.3 문제: API 응답 형식 불일치

**원인**: 프론트엔드와 백엔드의 응답 형식이 다름

**해결**:
1. API 스키마 확인 (`api/schemas.py`)
2. 프론트엔드 타입 정의 확인 (`frontend/src/types/schema.ts`)
3. 불일치 시 스키마 수정 또는 어댑터 구현

---

## 14. 구현 우선순위

### Phase 1: 기본 기능 복구 (즉시)
1. **시나리오 선택 기능 추가** (누락된 입력 방식)
   - DEMO_SCENARIOS 데이터 정의
   - 시나리오 선택 UI 구현
   - 시나리오 데이터 매핑 로직
2. **방책 선택 및 상세 정보 표시** (누락된 핵심 기능)
   - 상위 3개 방책 추천 표시 (max_coas: 3)
   - 방책 선택 드롭다운 UI 구현
   - 선택된 방책 하이라이트
   - 방책 카드에 추가 정보 표시
     - 참여 부대 (participating_units)
     - 방책 유형 (coa_type) 한글 변환
     - 선정 카테고리 (selection_category) 한글 변환
     - 시스템 탐색 과정 (system_search_path)
   - 선정 사유 표시 (justification, unit_rationale)
   - 추론 근거 상세 분석 (ReasoningExplanationPanel)
   - RAG 문서 참조 표시 (DoctrineReferencePanel)
   - 온톨로지 추론 경로 표시 (reasoning_trace)
3. **전략 연계 시각화** (누락됨)
   - ChainVisualizer 컴포넌트 확인/개선
   - chain_info 표시
4. **방책 실행 계획** (누락됨)
   - COAExecutionPlanPanel 확인/개선
   - 최우수 방책 실행 계획 표시
5. **보고서 생성 기능** (누락됨)
   - ReportGenerator 컴포넌트 확인/개선
   - 보고서 다운로드 기능
6. 버튼 활성화 조건 수정
7. 입력 검증 로직 추가
8. 에러 처리 개선
9. 기본 API 호출 및 응답 처리

### Phase 2: 진행 상황 표시 (단기)
1. ProgressStatus 컴포넌트 구현
2. ExecutionContext 구현
3. COAGenerator에 통합

### Phase 3: 지도 시각화 (단기)
1. TacticalMap에 COA 레이어 추가
2. COA GeoJSON 파싱 및 표시
3. 부대 배치 마커 표시
4. COA 클릭 이벤트 처리

### Phase 4: 고급 기능 (중기)
1. 추론 경로 시각화 (지도상)
2. 배경 적군 부대 표시
3. COA 비교 기능
4. 채팅 인터페이스 고급 기능
   - COA 결과 기반 질문 자동 생성
   - 컨텍스트 인식 대화
5. 실시간 업데이트 (WebSocket)
   - 방책 생성 진행 상황 실시간 업데이트
   - 지도 마커 실시간 업데이트

---

## 15. 참고 자료

- [기능 비교 분석 문서](./feature_comparison_analysis.md)
- [구현 계획서](./implementation_plan.md)
- Streamlit 구현: `ui/views/agent_execution.py`
- 백엔드 API: `api/routers/coa.py`
- COA 서비스: `core_pipeline/coa_service.py`
- 시나리오 매퍼: `ui/components/scenario_mapper.py`

---

---

## 16. 추가 누락 기능 요약

### 16.1 확인된 누락 기능

1. **시나리오 선택 기능** (입력 방식 4가지 중 1개 누락)
2. **방책 선택 UI** (상위 3개 방책 선택)
3. **전략 연계 시각화** (ChainVisualizer)
4. **방책 실행 계획** (COAExecutionPlanPanel)
5. **보고서 생성 기능** (ReportGenerator)
6. **방책 카드 추가 정보** (참여 부대, 유형, 카테고리 등)
7. **채팅 인터페이스 연동** (COA 결과와 연동)
8. **진행 상황 표시** (ProgressStatus, ExecutionContext)
9. **지도 시각화** (COA 마커/라인, 부대 배치)

### 16.2 구현 우선순위 재정의

**즉시 구현 필요 (Phase 1)**:
1. 시나리오 선택 기능
2. 방책 선택 UI (상위 3개)
3. 선정 사유 및 추론 근거 표시
4. RAG 문서 참조 표시
5. 전략 연계 시각화
6. 방책 실행 계획
7. 보고서 생성 기능

**단기 구현 (Phase 2)**:
1. 진행 상황 표시
2. 지도 시각화
3. 방책 카드 추가 정보

**중기 구현 (Phase 3)**:
1. 채팅 인터페이스 고급 기능
2. 실시간 업데이트

---

**문서 버전**: 1.1  
**최종 업데이트**: 2025-01-XX  
**변경 이력**:
- v1.1: 누락 기능 점검 및 추가 반영 (전략 연계, 실행 계획, 보고서 생성, 채팅 연동 등)
- v1.0: 초기 설계 문서 작성
