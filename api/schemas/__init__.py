"""
API Schemas Package
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Common Models ---

class MissionBase(BaseModel):
    mission_id: str
    mission_type: Optional[str] = None
    commander_intent: Optional[str] = None
    superior_guidance: Optional[str] = None
    primary_axis_id: Optional[str] = None
    time_limit: Optional[datetime] = None
    priority: Optional[int] = None
    remarks: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ThreatEventBase(BaseModel):
    threat_id: str
    occurrence_time: Optional[datetime] = None
    threat_type_code: Optional[str] = None
    related_axis_id: Optional[str] = None
    location_cell_id: Optional[str] = None
    related_enemy_unit_id: Optional[str] = None
    threat_level: Optional[str] = None
    related_mission_id: Optional[str] = None
    raw_report_text: Optional[str] = None
    confidence: Optional[int] = None
    status: Optional[int] = None
    threat_type_original: Optional[str] = None
    enemy_unit_original: Optional[str] = None
    remarks: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class FriendlyUnit(BaseModel):
    unit_id: str
    unit_name: str
    unit_type: Optional[str] = None # 병종
    echelon: Optional[str] = None # 제대
    symbol_id: Optional[str] = None # SIDC
    location_cell_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    combat_power: Optional[float] = None
    max_speed_kmh: Optional[float] = None # NEW: 이동속도
    description: Optional[str] = None

class AxisItem(BaseModel):
    axis_id: str
    axis_name: str
    axis_type: Optional[str] = None
    start_cell_id: Optional[str] = None
    end_cell_id: Optional[str] = None
    coordinates: Optional[List[List[float]]] = None # [[lat, lon], ...]
    description: Optional[str] = None

class TerrainCellItem(BaseModel):
    cell_id: str
    coordinates: Optional[List[float]] = None # [lon, lat]
    name: Optional[str] = None
    description: Optional[str] = None

# --- Request Models ---

class ThreatAnalyzeRequest(BaseModel):
    sitrep_text: str = Field(..., description="The situation report text to analyze")
    mission_id: Optional[str] = Field(None, description="Optional mission ID context")

class COAGenerationRequest(BaseModel):
    threat_id: Optional[str] = None
    mission_id: Optional[str] = None
    threat_data: Optional[ThreatEventBase] = None
    user_params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_coas": 3,
            "preferred_strategy": "balanced",
            "approach_mode": "threat_centered"
        }
    )

# --- Response Models ---

class COASummary(BaseModel):
    coa_id: str
    coa_name: str
    total_score: float
    description: Optional[str] = None
    reasoning: Optional[str] = None # NEW: 추론 근거/설명
    rank: int
    combat_power_score: Optional[float] = 0.0
    mobility_score: Optional[float] = 0.0
    constraint_score: Optional[float] = 0.0
    threat_response_score: Optional[float] = 0.0
    risk_score: Optional[float] = 0.0
    visualization_data: Optional[Dict[str, Any]] = None # NEW: 시각화 데이터 (경로, 영역 등)
    unit_positions: Optional[Dict[str, Any]] = None # NEW: 부대 위치 GeoJSON

class COAResponse(BaseModel):
    coas: List[COASummary]
    axis_states: List[Dict[str, Any]]  # Simplified for now, or define AxisState model
    original_request: COAGenerationRequest
    analysis_time: datetime = Field(default_factory=datetime.now)
    situation_summary: Optional[str] = None  # LLM 기반 정황보고
    situation_summary_source: Optional[str] = None  # "llm", "template", "cache" - 정황보고 생성 방식

class MissionListResponse(BaseModel):
    missions: List[MissionBase]

class ThreatListResponse(BaseModel):
    threats: List[ThreatEventBase]

class FriendlyUnitListResponse(BaseModel):
    units: List[FriendlyUnit]

class AxisListResponse(BaseModel):
    axes: List[AxisItem]

class TerrainCellListResponse(BaseModel):
    cells: List[TerrainCellItem]

class COADetailResponse(BaseModel):
    coa_id: str
    explanation: str

class SystemHealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"

# --- Chat Models ---

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    agent_id: Optional[str] = None
    situation_id: Optional[str] = None
    use_rag: bool = True
    llm_model: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    citations: List[Dict[str, Any]] = []
    agent_result: Optional[Dict[str, Any]] = None

# Export all models
__all__ = [
    'MissionBase',
    'ThreatEventBase',
    'ThreatAnalyzeRequest',
    'COAGenerationRequest',
    'COASummary',
    'COAResponse',
    'MissionListResponse',
    'ThreatListResponse',
    'COADetailResponse',
    'SystemHealthResponse',
    'ChatMessage',
    'ChatRequest',
    'ChatResponse',
    'FriendlyUnit',
    'AxisItem',
    'FriendlyUnitListResponse',
    'AxisListResponse',
    'TerrainCellItem',
    'TerrainCellListResponse',
]
