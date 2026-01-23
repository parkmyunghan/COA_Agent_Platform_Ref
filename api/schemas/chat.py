from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict]] = []
    agent_id: Optional[str] = None
    situation_id: Optional[str] = None
    situation_info: Optional[Dict[str, Any]] = None
    coa_context: Optional[Dict] = None
    use_rag: bool = True
    llm_model: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    citations: List[Dict[str, Any]] = []
    agent_result: Optional[Dict[str, Any]] = None
