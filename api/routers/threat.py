from fastapi import APIRouter, Depends, HTTPException
from api.schemas import ThreatAnalyzeRequest, ThreatEventBase
from api.dependencies import get_coa_service
from core_pipeline.coa_service import COAService
from core_pipeline.data_models import ThreatEvent

router = APIRouter(prefix="/threat", tags=["Threat"])

@router.post("/analyze", response_model=ThreatEventBase)
def analyze_threat(
    request: ThreatAnalyzeRequest,
    service: COAService = Depends(get_coa_service)
):
    """
    Analyze SITREP text and parse it into a ThreatEvent.
    """
    try:
        threat_event = service.parse_sitrep_to_threat(
            sitrep_text=request.sitrep_text,
            mission_id=request.mission_id,
            use_llm=True
        )
        
        if not threat_event:
            raise HTTPException(status_code=400, detail="Failed to parse SITREP")
            
        # Enrich with coordinates
        from core_pipeline.visualization_generator import VisualizationDataGenerator
        viz_gen = VisualizationDataGenerator()
        lat, lon = None, None
        
        if threat_event.location_cell_id:
            coords = viz_gen._get_terrain_cell_coordinates(threat_event.location_cell_id)
            if coords:
                lon, lat = coords # [lng, lat]
        
        # Convert dataclass to Pydantic
        return ThreatEventBase(
            threat_id=threat_event.threat_id,
            threat_type_code=threat_event.threat_type_code,
            threat_level=threat_event.threat_level,
            related_axis_id=threat_event.related_axis_id,
            location_cell_id=threat_event.location_cell_id,
            occurrence_time=threat_event.occurrence_time,
            confidence=threat_event.confidence,
            raw_report_text=threat_event.raw_report_text,
            latitude=lat,
            longitude=lon
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
