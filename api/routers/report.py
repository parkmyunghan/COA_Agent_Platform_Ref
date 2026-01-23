# api/routers/report.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import os
from datetime import datetime
from core_pipeline.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/report", tags=["report"])

# Global orchestrator instance
_orchestrator: Optional[Orchestrator] = None

def set_orchestrator(orchestrator: Orchestrator):
    global _orchestrator
    _orchestrator = orchestrator

class ReportRequest(BaseModel):
    threat_info: Dict[str, Any]
    selected_coa: Dict[str, Any]
    format: str = "txt" # "pdf" or "txt"

@router.post("/generate")
async def generate_report(request: ReportRequest):
    """
    분석 결과 보고서를 생성합니다.
    """
    try:
        # Create reports directory if not exists
        report_dir = "reports"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"COA_Report_{timestamp}.{request.format}"
        file_path = os.path.join(report_dir, filename)
        
        # Simple text report generation for now
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"=== 작전 분석 결과 보고서 ===\n")
            f.write(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"1. 위협 상황 상세\n")
            f.write(f"- 위협 ID: {request.threat_info.get('threat_id', 'Unknown')}\n")
            f.write(f"- 위협 유형: {request.threat_info.get('threat_type_original', 'Unknown')}\n")
            f.write(f"- 상황 설명: {request.threat_info.get('raw_report_text', '정보 없음')}\n\n")
            
            f.write(f"2. 선정 방책 (Recommended COA)\n")
            f.write(f"- 방책명: {request.selected_coa.get('coa_name', 'Unknown')}\n")
            f.write(f"- 종합 점수: {request.selected_coa.get('total_score', 0)}\n")
            f.write(f"- 설명: {request.selected_coa.get('description', '정보 없음')}\n\n")
            
            f.write(f"3. 추론 근거\n")
            traces = request.selected_coa.get('reasoning_trace', [])
            for i, trace in enumerate(traces):
                f.write(f"  Step {i+1}: {trace}\n")
            f.write("\n")
            
            f.write(f"4. 실행 계획\n")
            plan = request.selected_coa.get('execution_plan', {})
            phases = plan.get('phases', [])
            for i, phase in enumerate(phases):
                f.write(f"  Phase {i+1}: {phase.get('name')}\n")
                f.write(f"    - {phase.get('description')}\n")
                for task in phase.get('tasks', []):
                    f.write(f"      * {task}\n")
            
        logger.info(f"Report generated: {file_path}")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"보고서 생성 실패: {str(e)}")
