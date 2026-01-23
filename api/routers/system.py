from fastapi import APIRouter, Depends, BackgroundTasks
from api.schemas import SystemHealthResponse
from api.dependencies import get_global_state, GlobalStateManager
import os
from pathlib import Path
from typing import List, Dict, Any
import yaml

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health", response_model=SystemHealthResponse)
def health_check():
    return SystemHealthResponse(status="ok")

@router.post("/init")
def initialize_system(
    background_tasks: BackgroundTasks,
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Triggers system initialization (loading LLMs, etc.) in the background.
    """
    background_tasks.add_task(state.initialize)
    return {"message": "시스템 초기화가 백그라운드에서 시작되었습니다."}

@router.get("/docs")
def list_documents():
    """docs 디렉토리의 문서 목록을 카테고리별로 반환합니다."""
    base_dir = Path(__file__).parent.parent.parent
    docs_dir = base_dir / "docs"
    
    if not docs_dir.exists():
        return {"categories": {}}

    docs = {}
    for path in docs_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in [".md", ".html"]:
            if "readme.md" in path.name.lower(): continue
            
            # 카테고리 결정 (디렉토리 구조 기반)
            rel_path = path.relative_to(docs_dir)
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "주요 문서"
            
            if category not in docs:
                docs[category] = []
            
            docs[category].append({
                "name": path.name,
                "path": str(rel_path).replace("\\", "/"),
                "type": path.suffix[1:]
            })
    
    return {"categories": docs}

@router.get("/docs/content")
def get_doc_content(path: str):
    """특정 문서의 내용을 반환합니다."""
    base_dir = Path(__file__).parent.parent.parent
    docs_dir = base_dir / "docs"
    full_path = docs_dir / path
    
    if not full_path.exists() or not str(full_path).startswith(str(docs_dir)):
        return {"error": "문서를 찾을 수 없습니다."}
        
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"content": content}

@router.get("/stats/kpi")
def get_kpi_stats(state: GlobalStateManager = Depends(get_global_state)):
    """대시보드용 시스템 전체 지표를 반환합니다."""
    orchestrator = state.get_orchestrator()
    if not orchestrator:
        return {"error": "오케스트레이터가 초기화되지 않았습니다."}
        
    om = orchestrator.core.ontology_manager
    rm = orchestrator.core.rag_manager
    dm = orchestrator.core.data_manager
    
    # 온톨로지 지표
    triple_count = len(om.graph) if hasattr(om, 'graph') else 0
    
    # RAG 지표
    chunk_count = len(rm.chunks) if hasattr(rm, 'chunks') else 0
    
    # 위협 지표
    threats = dm.load_all().get("threats", [])
    
    return {
        "ontology": {
            "triples": triple_count,
            "status": "active"
        },
        "rag": {
            "chunks": chunk_count,
            "status": "ready" if rm.is_available() else "loading"
        },
        "threats": {
            "total": len(threats),
            "active": len([t for t in threats if t.get('status') != 'resolved'])
        }
    }

@router.get("/agents")
def get_agents():
    """
    사용 가능한 Agent 목록을 반환합니다.
    
    Returns:
        Agent 목록 (name, description, enabled 필드 포함)
    """
    # Agent 레지스트리 파일 경로
    base_dir = Path(__file__).parent.parent.parent
    registry_path = base_dir / "config" / "agent_registry.yaml"
    
    if not registry_path.exists():
        return {"agents": []}
    
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f)
        
        agents = registry.get("agents", [])
        
        # 프론트엔드가 기대하는 형식으로 변환
        return {
            "agents": [
                {
                    "name": agent.get("name"),
                    "description": agent.get("description", ""),
                    "enabled": agent.get("enabled", True)
                }
                for agent in agents
            ]
        }
    except Exception as e:
        # 에러 발생 시 빈 목록 반환 (프론트엔드가 기본값 사용)
        return {"agents": []}

@router.get("/code-mappings")
def get_code_mappings():
    """
    코드-한글 라벨 매핑 정보를 반환합니다.
    
    Returns:
        {
            "threat_types": {"THR_TYPE_001": "침투", ...},
            "axes": {"AXIS01": "동부 주공축선", ...},
            "threat_ids": {"THR001": "침투", ...}
        }
    """
    try:
        from api.utils.code_label_mapper import get_mapper
        mapper = get_mapper()
        return mapper.get_all_mappings()
    except Exception as e:
        print(f"[System API] 코드 매핑 로드 실패: {e}")
        return {
            "threat_types": {},
            "axes": {},
            "threat_ids": {}
        }

