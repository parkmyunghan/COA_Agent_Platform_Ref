// Backend Pydantic Model Replicas

export interface MissionBase {
    mission_id: string;
    mission_name?: string; // 임무명
    mission_type?: string; // 임무 유형 (방어, 공격, 정찰 등)
    mission_objective?: string; // 전술 목표
    commander_intent?: string;
    superior_guidance?: string;
    primary_axis_id?: string;
    location_cell_id?: string; // 작전 지역
    // time_limit?: string; // Datetime as string
    priority?: number;
    remarks?: string;
    latitude?: number;
    longitude?: number;
}

export interface ThreatEventBase {
    threat_id: string;
    threat_type_code?: string;
    threat_level?: string;
    related_axis_id?: string;
    location_cell_id?: string;
    occurrence_time?: string; // ISO String
    confidence?: number;
    raw_report_text?: string;
    status?: number;
    threat_type_original?: string;
    enemy_unit_original?: string;
    remarks?: string;
}

export interface FriendlyUnit {
    unit_id: string;
    unit_name: string;
    unit_type?: string;
    echelon?: string;
    symbol_id?: string;
    location_cell_id?: string;
    latitude?: number;
    longitude?: number;
    status?: string;
    combat_power?: number;
    description?: string;
}

export interface AxisItem {
    axis_id: string;
    axis_name: string;
    axis_type?: string;
    start_cell_id?: string;
    end_cell_id?: string;
    coordinates?: number[][]; // [[lat, lon], ...]
    description?: string;
}

export interface ThreatAnalyzeRequest {
    sitrep_text: string;
    mission_id?: string;
}

export interface COAGenerationRequest {
    threat_id?: string;
    mission_id?: string;
    threat_data?: ThreatEventBase;
    user_params?: Record<string, any>;
}

export interface COASummary {
    coa_id: string;
    coa_name: string;
    total_score: number;
    suitability_score?: number;
    feasibility_score?: number;
    acceptability_score?: number;
    description?: string;
    rank: number;
    reasoning_trace?: string[] | any[];
    execution_plan?: {
        phases: {
            name: string;
            description: string;
            tasks: string[];
        }[];
    };
    required_resources?: {
        resource_id: string;
        name: string;
        type: string;
        quantity?: number;
    }[];
    // 선정 사유 및 추론 근거
    reasoning?: {
        justification?: string;
        situation_assessment?: string;
        pros?: string[];
        cons?: string[];
        unit_rationale?: string;
        system_search_path?: string;
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
    // RAG 문서 참조
    doctrine_references?: Array<{
        reference_type?: 'doctrine' | 'general';
        doctrine_id?: string;
        statement_id?: string;
        source: string;
        excerpt: string;
        relevance_score: number;
        mett_c_elements?: string[];
    }>;
    // 전략 연계
    chain_info?: any;
    chain_info_details?: any;
    // 추가 정보
    participating_units?: string[];
    coa_type?: string;
    type?: string;
    selection_category?: string;
    // 지도 시각화용
    coa_geojson?: any;
    unit_positions?: any;
    // 점수 세부 항목 (COACard에서 사용)
    combat_power_score?: number;
    mobility_score?: number;
    constraint_score?: number;
    threat_response_score?: number;
    risk_score?: number;
    // METT-C 점수 (별도 평가 체계)
    mett_c_scores?: {
        mission_score?: number;
        enemy_score?: number;
        terrain_score?: number;
        troops_score?: number;
        civilian_score?: number;
        time_score?: number;
        total_score?: number;
    };
}

export interface ProgressLog {
    message: string;
    progress: number | null;
    timestamp: string;
}

export interface COAResponse {
    coas: COASummary[];
    axis_states: unknown[]; // Use proper type if needed
    original_request: COAGenerationRequest;
    analysis_time: string;
    progress_logs?: ProgressLog[]; // 백엔드에서 수집한 진행 상황 로그
}

export interface MissionListResponse {
    missions: MissionBase[];
}

export interface ThreatListResponse {
    threats: ThreatEventBase[];
}

export interface FriendlyUnitListResponse {
    units: FriendlyUnit[];
}

export interface AxisListResponse {
    axes: AxisItem[];
}

export interface SystemHealthResponse {
    status: string;
    version: string;
}
