# api/routers/rag.py
"""
RAG 관련 API 엔드포인트
- 문서 관리 및 업로드
- 인덱스 상태 조회 및 재구축
- 시맨틱 검색 테스트
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from core_pipeline.orchestrator import Orchestrator
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

# Global orchestrator instance
_orchestrator: Optional[Orchestrator] = None

def set_orchestrator(orchestrator: Orchestrator):
    global _orchestrator
    _orchestrator = orchestrator

def get_orchestrator() -> Orchestrator:
    if _orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return _orchestrator

def get_rag_docs_path(orchestrator: Orchestrator) -> Path:
    """RAG 문서 디렉토리 경로 가져오기"""
    # config에서 경로를 가져오거나 기본값 사용
    doc_dir = orchestrator.config.get('rag', {}).get('document_dir', './knowledge/rag_docs')
    path = Path(doc_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path

# Models
class RAGStatusResponse(BaseModel):
    is_available: bool
    embedding_model_loaded: bool
    index_count: int
    sources: List[str]
    config: Dict[str, Any]

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    doc_id: Optional[int]
    text: str
    score: float
    metadata: Dict[str, Any]

class DocumentInfo(BaseModel):
    filename: str
    size_kb: float
    modified_at: str
    is_indexed: bool

# API Endpoints
@router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status():
    """
    RAG 시스템의 현재 상태를 조회합니다.
    """
    try:
        orchestrator = get_orchestrator()
        rag_manager = orchestrator.core.rag_manager
        
        return RAGStatusResponse(
            is_available=rag_manager.is_available(),
            embedding_model_loaded=rag_manager.embedding_model is not None,
            index_count=len(rag_manager.chunks) if hasattr(rag_manager, 'chunks') else 0,
            sources=rag_manager.get_indexed_sources(),
            config=orchestrator.config.get('rag', {})
        )
    except Exception as e:
        logger.error(f"Error fetching RAG status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch status: {str(e)}")

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    문서를 업로드하고 RAG 데이터 디렉토리에 저장합니다.
    """
    try:
        orchestrator = get_orchestrator()
        upload_dir = get_rag_docs_path(orchestrator)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"filename": file.filename, "status": "uploaded", "path": str(file_path)}
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """
    업로드된 문서 목록과 인덱싱 상태를 조회합니다.
    """
    try:
        orchestrator = get_orchestrator()
        docs_path = get_rag_docs_path(orchestrator)
        rag_manager = orchestrator.core.rag_manager
        
        indexed_sources = set(rag_manager.get_indexed_sources())
        
        docs = []
        for file_path in docs_path.glob("*.*"):
            if file_path.suffix.lower() in ['.txt', '.pd', '.md', '.docx']:
                stat = file_path.stat()
                from datetime import datetime
                docs.append(DocumentInfo(
                    filename=file_path.name,
                    size_kb=stat.st_size / 1024,
                    modified_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    is_indexed=file_path.name in indexed_sources
                ))
        return docs
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reindex")
async def rebuild_index():
    """
    업로드된 문서들을 기반으로 RAG 인덱스를 재구축합니다.
    """
    try:
        orchestrator = get_orchestrator()
        rag_manager = orchestrator.core.rag_manager
        docs_path = get_rag_docs_path(orchestrator)
        
        doc_files = list(docs_path.glob("*.*"))
        doc_files = [f for f in doc_files if f.suffix.lower() in ['.txt', '.pdf', '.md', '.docx']]
        
        if not doc_files:
            return {"status": "no_documents", "message": "No documents found to index"}

        # 문서 로드 및 분류 (Streamlit 로직 마이그레이션)
        doctrine_docs = []
        doctrine_doc_names = []
        general_docs = []
        general_doc_names = []
        
        for doc_file in doc_files:
            if doc_file.suffix.lower() in ['.txt', '.md']:
                try:
                    with open(doc_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            is_doctrine = (
                                doc_file.name.upper().startswith("DOCTRINE") or 
                                "# Doctrine_ID:" in content
                            )
                            if is_doctrine:
                                doctrine_docs.append(content)
                                doctrine_doc_names.append(doc_file.name)
                            else:
                                general_docs.append(content)
                                general_doc_names.append(doc_file.name)
                except Exception as e:
                    logger.warning(f"Failed to read {doc_file.name}: {e}")
            else:
                logger.warning(f"Unsupported format: {doc_file.suffix}")

        all_chunks = []
        
        # 1. 교리 문서 청킹 (특수 로직)
        if doctrine_docs:
            doctrine_chunks = rag_manager.chunk_doctrine_documents(
                doctrine_docs, 
                doc_names=doctrine_doc_names
            )
            all_chunks.extend(doctrine_chunks)
        
        # 2. 일반 문서 청킹
        if general_docs:
            general_chunks = rag_manager.chunk_documents(
                general_docs, 
                doc_names=general_doc_names
            )
            all_chunks.extend(general_chunks)

        if all_chunks:
            # 인덱스 재구축 및 저장
            rag_manager.build_index(all_chunks, use_faiss=True)
            rag_manager.save_index()
            return {
                "status": "success", 
                "total_chunks": len(all_chunks),
                "doctrine_docs": len(doctrine_docs),
                "general_docs": len(general_docs)
            }
        else:
            return {"status": "no_chunks", "message": "No valid chunks generated from documents"}
            
    except Exception as e:
        logger.error(f"Error rebuilding index: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")

@router.post("/search", response_model=List[SearchResult])
async def search_rag(request: SearchRequest):
    """
    시맨틱 검색을 수행합니다.
    """
    try:
        orchestrator = get_orchestrator()
        rag_manager = orchestrator.core.rag_manager
        
        if not rag_manager.is_available():
            raise HTTPException(status_code=400, detail="RAG index not available")
            
        results = rag_manager.retrieve_with_context(request.query, top_k=request.top_k)
        
        return [
            SearchResult(
                doc_id=r.get('doc_id'),
                text=r.get('text', ''),
                score=float(r.get('score', 0.0)),
                metadata=r.get('metadata', {})
            ) for r in results
        ]
    except Exception as e:
        logger.error(f"Error during RAG search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
