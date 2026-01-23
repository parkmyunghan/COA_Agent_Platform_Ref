from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from api.schemas import ChatRequest, ChatResponse
from api.dependencies import get_orchestrator
from core_pipeline.orchestrator import Orchestrator
import logging
import yaml
from pathlib import Path

# Setup Router
router = APIRouter(tags=["chat"])
logger = logging.getLogger("api.routers.chat")

# Load Agent Registry once
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = BASE_DIR / "config" / "agent_registry.yaml"

def get_agent_registry():
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"agents": []}

@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, orchestrator: Orchestrator = Depends(get_orchestrator)):
    """
    Chat completion endpoint supporting RAG and Agent execution.
    """
    try:
        user_prompt = request.message
        
        # [DEBUG] 요청 데이터 로깅
        logger.info(f"[Chat] Request received - situation_id: {request.situation_id}, has_situation_info: {request.situation_info is not None}")
        if request.situation_info:
            logger.info(f"[Chat] situation_info keys: {list(request.situation_info.keys())}")
        
        # 1. Palantir Search (RAG + Ontology + Reasoning)
        retrieved_docs = []
        if request.use_rag:
            try:
                # PalantirSearch 사용 (질의 확장 및 가설 기반 검색 포함)
                if hasattr(orchestrator.core, 'palantir_search'):
                    retrieved_docs = orchestrator.core.palantir_search.search(
                        user_prompt, top_k=3, use_graph=True
                    )
                # Fallback: PalantirSearch가 없으면 기존 RAG 사용
                elif orchestrator.core.rag_manager.embedding_model is not None:
                    logger.warning("PalantirSearch not found, falling back to basic RAG")
                    retrieved_docs = orchestrator.core.rag_manager.retrieve_with_context(
                        user_prompt, top_k=3
                    )
            except Exception as e:
                logger.error(f"Search failed: {e}")
                # 검색 실패해도 계속 진행 (LLM 단독 사용)
        
        # 2. Agent Execution
        agent_result = None
        if request.agent_id:
            try:
                registry = get_agent_registry()
                agents_list = registry.get("agents", [])
                agent_info = next((a for a in agents_list if a.get("name") == request.agent_id), None)
                
                if agent_info and agent_info.get("class"):
                    cls_path = agent_info.get("class")
                    AgentClass = orchestrator.load_agent_class(cls_path)
                    # Initialize Agent
                    agent = AgentClass(core=orchestrator.core)
                    
                    # Prepare arguments
                    # This maps to execute_reasoning logic in chat_interface_v2.py
                    
                    # TODO: Retrieve actual situation_info if situation_id is provided
                    # For now passing situation_id directly
                    
                    # Log progress callback
                    def status_callback(msg, progress=None):
                        # Since we are not streaming, we just log debug for now
                        logger.debug(f"Agent Progress [{progress}%]: {msg}")

                    agent_result = agent.execute_reasoning(
                        situation_id=request.situation_id,
                        user_query=user_prompt,
                        # selected_situation_info=None, # Fetch from DB if needed
                        use_palantir_mode=True, # Default to True
                        enable_rag_search=True,
                        coa_type_filter=["Defense", "Offensive", "Counter_Attack", "Preemptive", "Deterrence", "Maneuver", "Information_Ops"], # All types
                        status_callback=status_callback
                    )
                    
                    # Inject Agent result into RAG context
                    if agent_result:
                         agent_result_text = f"Agent Execution Result:\n{str(agent_result)}"
                         retrieved_docs.append({
                            "doc_id": -1,
                            "text": agent_result_text,
                            "score": 1.0,
                            "index": -1,
                            "metadata": {"source": "agent", "agent_result": agent_result}
                        })
                else:
                    logger.warning(f"Agent {request.agent_id} not found in registry")
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
                
        # 3. LLM Generation
        response_text = ""
        if orchestrator.core.llm_manager.is_available():
            try:
                # [NEW] 실시간 상황 정보 주입 (Situation Info)
                threat_info_text = ""
                
                # 1. 프론트엔드에서 전달된 situation_info 최우선 활용
                if request.situation_info:
                    info = request.situation_info
                    t_id = info.get('threat_id') or info.get('위협ID') or request.situation_id
                    t_type = info.get('threat_type') or info.get('위협유형')
                    t_level = info.get('threat_level') or info.get('위협수준')
                    loc = info.get('location') or info.get('발생장소') or info.get('location_name') or info.get('발생지형명')
                    axis = info.get('axis_id') or info.get('관련축선ID') or info.get('axis_name') or info.get('관련축선명')
                    desc = info.get('raw_report_text') or info.get('description') or info.get('상황설명')
                    
                    threat_info_text = f"현재 작전 상황 정보 (실시간):\n"
                    threat_info_text += f"- 위협ID: {t_id}\n"
                    if t_type: threat_info_text += f"- 위협유형: {t_type}\n"
                    if t_level: threat_info_text += f"- 위협수준: {t_level}\n"
                    if loc: threat_info_text += f"- 위치: {loc}\n"
                    if axis: threat_info_text += f"- 관련축선: {axis}\n"
                    if desc: threat_info_text += f"- 상황설명: {desc}\n"
                    
                    logger.info(f"[Chat] Injected situation_info from request: {t_id}")
                    logger.debug(f"[Chat] threat_info_text preview: {threat_info_text[:200] if len(threat_info_text) > 200 else threat_info_text}")

                # 2. situation_id를 기반으로 DB(위협상황.xlsx) 보완 조회 (프론트엔드 정보가 부족할 때)
                elif request.situation_id:
                     try:
                        threat_df = orchestrator.core.data_manager.load_table("위협상황")
                        if threat_df is not None and not threat_df.empty:
                            threat_row = threat_df[threat_df['위협ID'] == request.situation_id]
                            if not threat_row.empty:
                                row = threat_row.iloc[0]
                                location_id = str(row.get('발생지형셀ID', row.get('location_cell_id', '미상')))
                                axis_id = str(row.get('관련축선ID', row.get('related_axis_id', '미상')))
                                
                                threat_info_text = f"현재 작전 상황 정보 (시스템 DB):\n"
                                threat_info_text += f"- 위협ID: {row.get('위협ID')}\n"
                                threat_info_text += f"- 유형: {row.get('위협유형코드')} ({row.get('위협유형원문', '미상')})\n"
                                threat_info_text += f"- 수준: {row.get('위협수준', 0.5)}\n"
                                threat_info_text += f"- 위치: {location_id}\n"
                                threat_info_text += f"- 축선: {axis_id}\n"
                                threat_info_text += f"- 탐지시각: {row.get('탐지시각')}\n"
                                threat_info_text += f"- 상황보고: {row.get('상황보고원문')}\n"
                                logger.info(f"[Chat] Injected situation_info from DB: {request.situation_id}")
                                logger.debug(f"[Chat] threat_info_text preview: {threat_info_text[:200] if len(threat_info_text) > 200 else threat_info_text}")
                     except Exception as e:
                        logger.warning(f"Failed to fetch threat from DB: {e}")

                if threat_info_text:
                     retrieved_docs.append({
                        "text": threat_info_text.strip(),
                        "metadata": {
                            "type": "situation_info",
                            "source": "system",
                            "title": "현재 상황 정보"
                        }
                    })

                # 3. 추천 방책 조회 (CoA Recommendations)
                sit_id_for_coa = request.situation_id
                if not sit_id_for_coa and request.situation_info:
                    sit_id_for_coa = request.situation_info.get('threat_id') or request.situation_info.get('위협ID') or request.situation_info.get('situation_id')

                if sit_id_for_coa:
                    try:
                        logger.debug(f"[Chat] Attempting to fetch COA recommendations for situation_id: {sit_id_for_coa}")
                        rec_history = orchestrator.core.recommendation_history.get_latest_recommendation(sit_id_for_coa)
                        coa_info_text = ""
                        
                        if rec_history:
                            recommendations = rec_history.get("recommendation", {}).get("recommendations", [])
                            if recommendations:
                                coa_lines = [f"관련 추천 방책 (ID: {sit_id_for_coa}):"]
                                for idx, coa in enumerate(recommendations[:3]):
                                    rank = idx + 1
                                    name = coa.get("방책명", coa.get("coa_name", "Unknown"))
                                    score = coa.get("최종점수", coa.get("score", 0))
                                    desc = coa.get("설명", coa.get("description", ""))
                                    if len(desc) > 100: desc = desc[:100] + "..."
                                    coa_lines.append(f"{rank}순위: {name} (점수: {score:.2f})\n   설명: {desc}")
                                
                                coa_info_text = "\n".join(coa_lines)
                        
                        if coa_info_text:
                             retrieved_docs.append({
                                "text": coa_info_text.strip(),
                                "metadata": {
                                    "type": "coa_recommendation",
                                    "source": "system",
                                    "title": "방책 추천 결과"
                                }
                            })
                    except Exception as e:
                        logger.warning(f"Failed to inject CoA context: {e}")

                # [DEBUG] 컨텍스트 카운트 로깅
                context_counts = {}
                for doc in retrieved_docs:
                    ctx_type = doc.get('metadata', {}).get('type', 'unknown')
                    context_counts[ctx_type] = context_counts.get(ctx_type, 0) + 1
                logger.info(f"[Chat] Total contexts for LLM: {len(retrieved_docs)} - {context_counts}")
                
                if retrieved_docs:
                    response_text = orchestrator.core.llm_manager.generate_with_citations(
                        user_prompt, retrieved_docs, max_tokens=1024
                    )
                else:
                    response_text = orchestrator.core.llm_manager.generate(
                        user_prompt, max_tokens=1024
                    )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                response_text = "Sorry, I encountered an error generating the response."
        else:
            response_text = "LLM service is not available."
            if agent_result:
                response_text += "\n\nHowever, the agent executed successfully. See details."

        return ChatResponse(
            response=response_text,
            citations=retrieved_docs,
            agent_result=agent_result
        )

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
