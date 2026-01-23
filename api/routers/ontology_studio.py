# api/routers/ontology_studio.py
"""
온톨로지 스튜디오 관련 API 엔드포인트
- 온톨로지 생성 (OWL/Instances)
- 상세 통계 조회
- 관계 관리 (CRUD)
- 의미 기반 추론
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from core_pipeline.orchestrator import Orchestrator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ontology/studio", tags=["ontology-studio"])

# Global orchestrator instance (injected from main.py)
_orchestrator: Optional[Orchestrator] = None

def set_orchestrator(orchestrator: Orchestrator):
    """Set the global orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator

def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return _orchestrator

# Models
class GenerationRequest(BaseModel):
    enable_virtual_entities: bool = True
    enable_reasoned_graph: bool = False

class GenerationResponse(BaseModel):
    success: bool
    message: str
    triple_count: int

class InferenceRequest(BaseModel):
    entity_id: str
    max_depth: int = 2

class InferenceResponse(BaseModel):
    entity_id: str
    direct_relations: List[Dict[str, Any]]
    indirect_relations: List[Dict[str, Any]]
    confidence: float

class OWLInferenceRequest(BaseModel):
    entity_id: str
    include_rdfs: bool = True
    max_results: int = 50
    apply_to_graph: bool = False  # 추론 결과를 원본 그래프에 추가할지 여부

class OWLInferenceResponse(BaseModel):
    entity: str
    entity_uri: str
    direct_relations: List[Dict[str, Any]]
    inferred_relations: List[Dict[str, Any]]
    total_direct: int
    total_inferred: int
    confidence: float
    stats: Dict[str, Any]
    reasoning_enabled: bool = True

class TripleModel(BaseModel):
    subject: str
    predicate: str
    object_val: str

class QualityIssue(BaseModel):
    severity: str  # "error", "warning", "info"
    message: str
    node_id: Optional[str] = None

class QualityCheckResponse(BaseModel):
    status: str
    issues: List[QualityIssue]

# API Endpoints
@router.get("/stats")
async def get_studio_stats():
    """
    온톨로지 스튜디오 상세 통계를 조회합니다.
    """
    try:
        orchestrator = get_orchestrator()
        # Use EnhancedOntologyManager if available
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        
        full_data = om.to_json()
        stats = full_data.get("stats", {})
        
        return {
            "stats": stats,
            "schema_summary": om.get_schema_summary() if hasattr(om, 'get_schema_summary') else ""
        }
    except Exception as e:
        logger.error(f"Error fetching studio stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@router.post("/generate", response_model=GenerationResponse)
async def generate_ontology(request: GenerationRequest):
    """
    온톨로지 그래프를 생성하고 저장합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        dm = orchestrator.core.data_manager
        
        data = dm.load_all()
        
        # 1. Reset graph
        from rdflib import Graph
        om.graph = Graph()
        
        # 2. Generate OWL
        om.generate_owl_ontology(data)
        
        # 3. Generate Instances
        om.generate_instances(data, enable_virtual_entities=request.enable_virtual_entities)
        
        # 4. Save
        try:
            save_success = om.save_graph(
                save_schema_separately=True,
                save_instances_separately=True,
                save_reasoned_separately=request.enable_reasoned_graph,
                enable_semantic_inference=True,
                cleanup_old_files=True
            )
        except TypeError:
            # Fallback for older save_graph signature
            save_success = om.save_graph()
            
        # 정확한 트리플 수 측정 (중복 제거)
        triple_count = len(set(om.graph))
        
        return GenerationResponse(
            success=save_success,
            message="Ontology generated successfully" if save_success else "Generation completed but saving failed",
            triple_count=triple_count
        )
    except Exception as e:
        logger.error(f"Error generating ontology: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.post("/inference", response_model=InferenceResponse)
async def run_semantic_inference(request: InferenceRequest):
    """
    특정 엔티티에 대한 의미 기반 관계 추론을 수행합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = orchestrator.core.ontology_manager
        
        # We might need to initialize SemanticInference if not already in orchestrator
        from core_pipeline.semantic_inference import SemanticInference
        
        # ontology_manager의 namespace를 config에 추가
        inference_config = dict(orchestrator.config) if orchestrator.config else {}
        if hasattr(om, 'ns') and om.ns is not None:
            inference_config["namespace"] = str(om.ns)
        
        inference_engine = SemanticInference(inference_config)
        
        results = inference_engine.infer_relations(om.graph, request.entity_id, max_depth=request.max_depth)
        
        # semantic_inference.py는 'entity'와 'predicate' 키를 사용하므로 변환
        def transform_relation(rel):
            return {
                "relation": rel.get("predicate", "").split("#")[-1] if rel.get("predicate") else "",
                "target": rel.get("entity", "").split("#")[-1] if rel.get("entity") else "",
                "type": rel.get("type", "direct")
            }
        
        return InferenceResponse(
            entity_id=request.entity_id,
            direct_relations=[transform_relation(rel) for rel in results.get('direct', [])],
            indirect_relations=[transform_relation(rel) for rel in results.get('indirect', [])],
            confidence=results.get('confidence', 0.0)
        )
    except Exception as e:
        logger.error(f"Error during semantic inference: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@router.post("/owl-inference", response_model=OWLInferenceResponse)
async def run_owl_inference(request: OWLInferenceRequest):
    """
    OWL-RL 기반 추론을 수행합니다.
    
    기존 키워드 기반 추론과 달리, OWL 표준 규칙을 적용하여:
    - TransitiveProperty: 전이적 관계 추론
    - InverseOf: 역관계 자동 생성
    - PropertyChainAxiom: 관계 체인 추론
    - SymmetricProperty: 대칭 관계 추론
    """
    from api.logger import debug_log
    # 기본 정보는 항상 기록
    logger.info(f"[OWL Inference API] 요청 수신 - entity_id: {request.entity_id}, max_results: {request.max_results}")
    # 상세 정보는 디버깅 모드에서만 기록
    debug_log(logger, f"[OWL Inference API] 상세 파라미터 - include_rdfs: {request.include_rdfs}, apply_to_graph: {request.apply_to_graph}")
    try:
        orchestrator = get_orchestrator()
        om = orchestrator.core.ontology_manager
        
        # OWL Reasoner 초기화
        from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
        
        if not OWLRL_AVAILABLE:
            # owlrl이 없으면 기존 방식으로 폴백
            logger.warning("owlrl 라이브러리가 없어 기존 추론 방식을 사용합니다.")
            from core_pipeline.semantic_inference import SemanticInference
            
            inference_config = dict(orchestrator.config) if orchestrator.config else {}
            if hasattr(om, 'ns') and om.ns is not None:
                inference_config["namespace"] = str(om.ns)
            
            inference_engine = SemanticInference(inference_config)
            results = inference_engine.infer_relations(om.graph, request.entity_id, max_depth=2)
            
            def transform_relation(rel):
                return {
                    "relation": rel.get("predicate", "").split("#")[-1] if rel.get("predicate") else "",
                    "target": rel.get("entity", "").split("#")[-1] if rel.get("entity") else "",
                    "type": rel.get("type", "direct"),
                    "reasoning": "키워드 유사도 기반 추론 (owlrl 미설치)"
                }
            
            return OWLInferenceResponse(
                entity=request.entity_id,
                entity_uri=f"http://coa-agent-platform.org/ontology#{request.entity_id}",
                direct_relations=[transform_relation(rel) for rel in results.get('direct', [])],
                inferred_relations=[transform_relation(rel) for rel in results.get('indirect', [])],
                total_direct=len(results.get('direct', [])),
                total_inferred=len(results.get('indirect', [])),
                confidence=results.get('confidence', 0.0),
                stats={"fallback": True, "reason": "owlrl not installed"},
                reasoning_enabled=False
            )
        
        # OWL-RL 추론 실행
        namespace = str(om.ns) if hasattr(om, 'ns') and om.ns else None
        
        from rdflib import Graph
        from pathlib import Path
        
        ontology_dir = Path(om.ontology_path) if hasattr(om, 'ontology_path') else Path("knowledge/ontology")
        
        # 현재 om.graph는 이미 추론된 그래프(instances_reasoned.ttl)일 수 있음
        # 원본 그래프(instances.ttl)를 별도로 로드하여 추론 실행
        original_graph = Graph()
        
        # 네임스페이스 바인딩 복사
        if hasattr(om, 'graph') and om.graph:
            for prefix, namespace_obj in om.graph.namespaces():
                original_graph.bind(prefix, namespace_obj)
        
        # 스키마 로드
        schema_path = ontology_dir / "schema.ttl"
        if schema_path.exists():
            original_graph.parse(str(schema_path), format="turtle")
            debug_log(logger, f"[DEBUG] Loaded schema: {schema_path}")
        
        # 원본 인스턴스 로드 (instances.ttl, 추론 전)
        instances_path = ontology_dir / "instances.ttl"
        if instances_path.exists():
            original_graph.parse(str(instances_path), format="turtle")
            debug_log(logger, f"[DEBUG] Loaded original instances: {instances_path}")
        else:
            # instances.ttl이 없으면 현재 그래프를 원본으로 사용
            logger.warning(f"[DEBUG] instances.ttl not found, using current graph as original")
            original_graph = Graph()
            for prefix, namespace_obj in om.graph.namespaces():
                original_graph.bind(prefix, namespace_obj)
            for triple in om.graph:
                original_graph.add(triple)
        
        original_graph_size = len(set(original_graph))
        current_graph_size = len(set(om.graph))
        debug_log(logger, f"[DEBUG] Original graph size (instances.ttl): {original_graph_size} triples")
        debug_log(logger, f"[DEBUG] Current om.graph size (instances_reasoned.ttl): {current_graph_size} triples")
        
        # 원본 그래프에서 OWL-RL 추론 실행
        reasoner = OWLReasoner(original_graph, namespace)
        inferred_graph = reasoner.run_inference(include_rdfs=request.include_rdfs)
        
        if inferred_graph is not None:
            inferred_graph_size = len(set(inferred_graph))
            debug_log(logger, f"[DEBUG] Newly inferred graph size: {inferred_graph_size} triples")
            debug_log(logger, f"[DEBUG] New triples from inference: {inferred_graph_size - original_graph_size}")
            
            # 현재 om.graph(instances_reasoned.ttl)와 새로 추론한 그래프 비교
            current_graph_set = set(om.graph)
            inferred_graph_set = set(inferred_graph)
            new_triples_in_reasoned = inferred_graph_set - current_graph_set
            debug_log(logger, f"[DEBUG] Triples in newly inferred graph but not in instances_reasoned.ttl: {len(new_triples_in_reasoned)}")
        
        # 추론 결과를 원본 그래프에 적용할지 여부
        applied_count = 0
        if request.apply_to_graph and inferred_graph is not None:
            # 추론된 그래프의 새로운 트리플만 원본 그래프에 추가
            original_triples = set(om.graph)
            for triple in inferred_graph:
                if triple not in original_triples:
                    om.graph.add(triple)
                    applied_count += 1
            logger.info(f"Applied {applied_count} inferred triples to original graph")
        
        # 엔티티 ID 정규화
        import re
        entity_id = request.entity_id
        original_entity_id = entity_id
        
        debug_log(logger, f"[OWL Inference API] 엔티티 ID 정규화 시작 - 원본: '{entity_id}'")
        
        # 괄호와 설명 제거 (예: 임무정보_MSN004(기만작전 실시) -> 임무정보_MSN004)
        entity_id = re.sub(r'\([^)]*\)', '', entity_id).strip()
        if entity_id != original_entity_id:
            debug_log(logger, f"[OWL Inference API] 괄호 제거 후: '{entity_id}'")
        
        # 연속된 언더스코어를 하나로 변환 (예: 임무정보__MSN004 -> 임무정보_MSN004)
        entity_id = re.sub(r'_+', '_', entity_id)
        if entity_id.startswith('_'):
            entity_id = entity_id[1:]
        if entity_id.endswith('_'):
            entity_id = entity_id[:-1]
        
        # 대소문자 정규화 (예: 임무정보_msn004 -> 임무정보_MSN004)
        if "_" in entity_id:
            parts = entity_id.split("_", 1)
            if len(parts) == 2:
                prefix, suffix = parts
                # 접미사가 소문자로 시작하는 경우 대문자로 변환 시도
                if suffix and suffix[0].islower():
                    # MSN, THR, TERR 등의 패턴 확인
                    if suffix.upper().startswith(("MSN", "THR", "TERR", "AXIS", "FRU", "ENU")):
                        entity_id = f"{prefix}_{suffix.upper()}"
                        debug_log(logger, f"[OWL Inference API] 대소문자 정규화: '{parts[1]}' -> '{suffix.upper()}'")
        
        if entity_id != original_entity_id:
            debug_log(logger, f"[OWL Inference API] 엔티티 ID 정규화 완료: '{original_entity_id}' -> '{entity_id}'")
        else:
            debug_log(logger, f"[OWL Inference API] 엔티티 ID 정규화 불필요 (변경 없음): '{entity_id}'")
        
        # 원본 그래프(instances.ttl)와 새로 추론한 그래프를 비교
        # 이렇게 하면 원본에는 없지만 추론으로 생성된 관계를 찾을 수 있습니다
        # 직접 관계는 instances_reasoned.ttl에서 가져오고,
        # 추론 관계는 원본 그래프와 비교하여 찾습니다
        results = reasoner.get_inferred_relations(
            entity_id, 
            max_results=request.max_results,
            compare_with_graph=original_graph  # 원본 그래프(instances.ttl)와 비교
        )
        
        # 직접 관계는 instances_reasoned.ttl에서 가져오기
        # (원본 그래프에는 없을 수 있는 관계들도 포함)
        from rdflib import URIRef, RDF, RDFS
        
        # 엔티티 URI 생성 (여러 후보 시도)
        entity_uri_for_direct = None
        if namespace:
            entity_uri_for_direct = URIRef(f"{namespace}{entity_id}")
        else:
            entity_uri_for_direct = URIRef(f"http://coa-agent-platform.org/ontology#{entity_id}")
        
        # instances_reasoned.ttl에서 직접 관계 가져오기
        direct_relations_from_reasoned = []
        original_graph_set = set(original_graph)
        
        # 엔티티가 subject인 경우
        for s, p, o in om.graph.triples((entity_uri_for_direct, None, None)):
            if p not in [RDF.type, RDFS.label]:
                # 원본 그래프에 있는지 확인
                in_original = (s, p, o) in original_graph_set
                relation_name = str(p).split("#")[-1] if "#" in str(p) else str(p)
                target_name = str(o).split("#")[-1] if "#" in str(o) else str(o)
                
                direct_relations_from_reasoned.append({
                    "relation": relation_name,
                    "target": target_name,
                    "type": "direct",
                    "full_predicate": str(p),
                    "full_object": str(o)
                })
        
        # 엔티티가 object인 경우
        for s, p, o in om.graph.triples((None, None, entity_uri_for_direct)):
            if p not in [RDF.type, RDFS.label]:
                in_original = (s, p, o) in original_graph_set
                relation_name = str(p).split("#")[-1] if "#" in str(p) else str(p)
                source_name = str(s).split("#")[-1] if "#" in str(s) else str(s)
                
                direct_relations_from_reasoned.append({
                    "relation": relation_name,
                    "source": source_name,
                    "type": "direct_reverse",
                    "full_predicate": str(p),
                    "full_subject": str(s)
                })
        
        debug_log(logger, f"[OWL Inference API] 직접 관계 조회 완료 - instances_reasoned.ttl에서 {len(direct_relations_from_reasoned)}개 발견")
        
        # 직접 관계는 instances_reasoned.ttl에서 가져온 것으로 업데이트
        results["direct_relations"] = direct_relations_from_reasoned
        results["total_direct"] = len(direct_relations_from_reasoned)
        
        # 적용된 트리플 수를 stats에 추가
        stats = results.get("stats", {})
        if request.apply_to_graph:
            stats["applied_to_graph"] = True
            stats["applied_count"] = applied_count
        
        # 결과 요약 로깅
        total_direct = results.get("total_direct", 0)
        total_inferred = results.get("total_inferred", 0)
        confidence = results.get("confidence", 0.0)
        entity_uri = results.get("entity_uri", "")
        
        # 기본 정보는 항상 기록
        logger.info(f"[OWL Inference API] 추론 완료 - 엔티티: {entity_id}, 직접 관계: {total_direct}개, 추론 관계: {total_inferred}개, 신뢰도: {confidence:.1%}")
        
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[OWL Inference API] ===== 추론 API 결과 요약 =====")
        debug_log(logger, f"[OWL Inference API] 엔티티 URI: {entity_uri}")
        
        if total_inferred > 0:
            inferred_relations = results.get("inferred_relations", [])
            sample_count = min(5, len(inferred_relations))
            debug_log(logger, f"[OWL Inference API] 추론 관계 샘플 (상위 {sample_count}개):")
            for i, rel in enumerate(inferred_relations[:sample_count]):
                rel_type = rel.get("type", "unknown")
                relation = rel.get("relation", "unknown")
                target = rel.get("target") or rel.get("source", "unknown")
                reasoning = rel.get("reasoning", "")
                debug_log(logger, f"[OWL Inference API]   [{i+1}] {rel_type}: {relation} -> {target}")
                if reasoning:
                    debug_log(logger, f"[OWL Inference API]       추론 근거: {reasoning}")
        elif total_direct == 0:
            logger.warning(f"[OWL Inference API] 경고: 엔티티 '{entity_id}'에 대한 직접 관계도 추론 관계도 없습니다.")
            debug_log(logger, f"[OWL Inference API] 가능한 원인:")
            debug_log(logger, f"[OWL Inference API]   1. 엔티티 URI가 그래프에 존재하지 않음")
            debug_log(logger, f"[OWL Inference API]   2. 엔티티 ID 정규화 문제")
            debug_log(logger, f"[OWL Inference API]   3. 네임스페이스 불일치")
        
        if request.apply_to_graph and applied_count > 0:
            logger.info(f"[OWL Inference API] 그래프에 적용 완료: {applied_count}개 트리플 추가됨")
        
        debug_log(logger, f"[OWL Inference API] ==============================")
        
        return OWLInferenceResponse(
            entity=results["entity"],
            entity_uri=results.get("entity_uri", ""),
            direct_relations=results.get("direct_relations", []),
            inferred_relations=results.get("inferred_relations", []),
            total_direct=results.get("total_direct", 0),
            total_inferred=results.get("total_inferred", 0),
            confidence=results.get("confidence", 0.0),
            stats=stats,
            reasoning_enabled=True
        )
        
    except Exception as e:
        import traceback
        logger.error(f"[OWL Inference API] 추론 실행 중 오류 발생: {str(e)}")
        logger.error(f"[OWL Inference API] 상세 오류 정보:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"OWL Inference failed: {str(e)}")


@router.get("/owl-inference/stats")
async def get_owl_inference_stats():
    """
    OWL-RL 추론 엔진 상태 및 통계를 조회합니다.
    """
    try:
        from core_pipeline.owl_reasoner import OWLRL_AVAILABLE
        
        orchestrator = get_orchestrator()
        om = orchestrator.core.ontology_manager
        
        graph_size = len(om.graph) if om.graph else 0
        
        return {
            "owlrl_available": OWLRL_AVAILABLE,
            "graph_size": graph_size,
            "supported_rules": [
                "TransitiveProperty",
                "InverseOf", 
                "SymmetricProperty",
                "PropertyChainAxiom",
                "FunctionalProperty"
            ] if OWLRL_AVAILABLE else [],
            "status": "ready" if OWLRL_AVAILABLE else "fallback_mode"
        }
    except Exception as e:
        logger.error(f"Error getting OWL inference stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# SWRL 스타일 규칙 엔진 API
# ═══════════════════════════════════════════════════════════════════════════

class RulesExecutionRequest(BaseModel):
    categories: Optional[List[str]] = None
    priority_filter: Optional[str] = None
    apply_to_graph: bool = False

class RulesExecutionResponse(BaseModel):
    total_rules_executed: int
    total_inferred: int
    rules_by_category: Dict[str, int]
    inferred_by_category: Dict[str, int]
    rule_results: Dict[str, Any]
    applied_to_graph: bool = False
    applied_count: int = 0


@router.get("/rules")
async def get_inference_rules(category: Optional[str] = None):
    """
    도메인 추론 규칙 목록을 조회합니다.
    """
    try:
        from core_pipeline.inference_rules import TACTICAL_RULES, RULE_CATEGORIES
        
        rules = TACTICAL_RULES
        if category:
            rules = [r for r in rules if r.category == category]
        
        return {
            "total": len(rules),
            "categories": RULE_CATEGORIES,
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "category": r.category,
                    "priority": r.priority,
                    "enabled": r.enabled
                }
                for r in rules
            ]
        }
    except Exception as e:
        logger.error(f"Error getting rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/execute", response_model=RulesExecutionResponse)
async def execute_inference_rules(request: RulesExecutionRequest):
    """
    도메인 추론 규칙을 실행합니다.
    
    SWRL 스타일의 전술 도메인 규칙을 적용하여:
    - 교전 대상 추론
    - 위협 노출 분석
    - 화력 지원 가능 범위
    - 협력 관계 추론
    - 기동 제한 분석
    """
    try:
        orchestrator = get_orchestrator()
        om = orchestrator.core.ontology_manager
        
        from core_pipeline.inference_rules import InferenceRulesEngine
        
        namespace = str(om.ns) if hasattr(om, 'ns') and om.ns else None
        engine = InferenceRulesEngine(om.graph, namespace)
        
        # 규칙 실행
        result = engine.execute_all_rules(
            categories=request.categories,
            priority_filter=request.priority_filter
        )
        
        applied_count = 0
        if request.apply_to_graph and result.get("all_inferred"):
            applied_count = engine.apply_inferences_to_graph(result["all_inferred"])
        
        stats = result.get("stats", {})
        
        return RulesExecutionResponse(
            total_rules_executed=stats.get("total_rules_executed", 0),
            total_inferred=stats.get("total_inferred", 0),
            rules_by_category=stats.get("rules_by_category", {}),
            inferred_by_category=stats.get("inferred_by_category", {}),
            rule_results=result.get("rule_results", {}),
            applied_to_graph=request.apply_to_graph,
            applied_count=applied_count
        )
        
    except Exception as e:
        logger.error(f"Error executing rules: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Rules execution failed: {str(e)}")


@router.get("/rules/{rule_id}")
async def get_rule_details(rule_id: str):
    """
    특정 규칙의 상세 정보를 조회합니다.
    """
    try:
        from core_pipeline.inference_rules import TACTICAL_RULES
        
        for rule in TACTICAL_RULES:
            if rule.id == rule_id:
                return {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "category": rule.category,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "condition_sparql": rule.condition_sparql.strip(),
                    "conclusion_template": rule.conclusion_template
                }
        
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_schema_details():
    """
    온톨로지 스키마(클래스, 속성) 상세 정보를 조회합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        
        # Load relation mappings
        raw_mappings = om.load_relation_mappings()
        
        # 프론트엔드 콤보박스에서 사용하기 편하도록 중복 제거된 딕셔너리 형태로 변환
        # (relation 명칭을 키로 사용)
        predicate_mappings = {}
        for m in raw_mappings:
            rel_name = m.get('relation')
            if rel_name and rel_name not in predicate_mappings:
                predicate_mappings[rel_name] = {
                    "label": rel_name,
                    "target_table": m.get('tgt_table'),
                    "source": m.get('source')
                }
        
        return {
            "mappings": predicate_mappings,
            "registry": getattr(om, 'schema_registry', {})
        }
    except Exception as e:
        logger.error(f"Error fetching schema details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {str(e)}")

def _resolve_uri(val: str, om: Any) -> Any:
    """ID 또는 접두사 형태의 문자열을 URIRef로 변환"""
    from rdflib import URIRef
    if not val:
        return None
    if val.startswith("http"):
        return URIRef(val)
    if ":" in val and not val.startswith("http"):
        prefix, local = val.split(":", 1)
        if prefix == "coa":
            return URIRef(str(om.ns) + local)
    # 기본은 ns 네임스페이스 사용
    return URIRef(str(om.ns) + val)

@router.get("/relations")
async def get_relations(subject: Optional[str] = None, predicate: Optional[str] = None):
    """
    온톨로지 관계(Triple) 목록을 조회하거나 검색합니다.
    기술적 메타데이터(Axiom, Restriction, Schema definition 등)는 제외합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        
        s = _resolve_uri(subject, om) if subject else None
        p = _resolve_uri(predicate, om) if predicate else None
        
        from rdflib import RDF, RDFS, OWL
        
        # 제외할 기술적 속성 및 타입 정의
        EXCLUDED_PREDICATES = {
            RDF.type, RDFS.subClassOf, RDFS.domain, RDFS.range,
            OWL.equivalentClass, OWL.intersectionOf, OWL.unionOf,
            OWL.onProperty, OWL.someValuesFrom, OWL.allValuesFrom,
            OWL.hasValue, OWL.minCardinality, OWL.maxCardinality, OWL.cardinality,
            OWL.inverseOf, OWL.disjointWith
        }
        
        EXCLUDED_TYPES = {
            OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, 
            OWL.AnnotationProperty, OWL.Ontology, OWL.Restriction, OWL.Axiom
        }
        
        results = []
        for s_res, p_res, o_res in om.graph.triples((s, p, None)):
            # 0. 블랭크 노드(BNode) 필터링 - 주로 기술적 소유/제약 조건 등을 나타냄
            from rdflib import BNode
            if isinstance(s_res, BNode) or isinstance(o_res, BNode):
                continue

            # 1. 기술적 속성 필터링
            if p_res in EXCLUDED_PREDICATES:
                continue
                
            # 2. 로컬 네임 기반 기술적 엔티티 필터링 (Axiom, Restriction 등)
            s_str = str(s_res)
            o_str = str(o_res)
            s_name = s_str.split('#')[-1].split('/')[-1]
            o_name = o_str.split('#')[-1].split('/')[-1]
            
            if "Axiom" in s_name or "Restriction" in s_name or s_str.startswith("n"):
                continue
            if "Axiom" in o_name or "Restriction" in o_name or o_str.startswith("n"):
                continue
                
            # 3. 기술적 타입 선언 필터링
            if o_res in EXCLUDED_TYPES:
                continue
                
            results.append({
                "subject": str(s_res),
                "predicate": str(p_res),
                "object_val": str(o_res)
            })
            if len(results) >= 2000: # Limit increased 
                break
                
        # 리스트로 직접 반환하여 프론트엔드 연동 단순화 (기존 {"triples": ...} 에서 변경)
        return results
    except Exception as e:
        logger.error(f"Error fetching relations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch relations: {str(e)}")

@router.post("/relations")
async def add_relation(triple: TripleModel):
    """
    새로운 온톨로지 관계(Triple)를 추가합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        
        from rdflib import URIRef, Literal
        
        s = _resolve_uri(triple.subject, om)
        p = _resolve_uri(triple.predicate, om)
        
        print(f"[DEBUG] Adding relation: S={s}, P={p}")
        
        if triple.object_val.startswith("http") or (":" in triple.object_val and not triple.object_val.startswith("http") and not any(char in triple.object_val for char in " \n\r\t")):
             o = _resolve_uri(triple.object_val, om)
             print(f"[DEBUG] Object resolved as URI: {o}")
        else:
            # Check if it exists as an individual, else treat as literal
            potential_o = _resolve_uri(triple.object_val, om)
            # 공백이 포함된 경우 개체(Individual)일 가능성이 낮으므로 리터럴로 우선 처리
            if " " not in triple.object_val and (potential_o, None, None) in om.graph:
                o = potential_o
                print(f"[DEBUG] Object resolved as existing Individual: {o}")
            else:
                o = Literal(triple.object_val)
                print(f"[DEBUG] Object resolved as Literal: {o}")
            
        om.graph.add((s, p, o))
        print(f"[DEBUG] Triple added to graph in memory. Total triples for this subject: {len(list(om.graph.triples((s, None, None))))}")
        
        om.save_graph()
        print(f"[DEBUG] Graph saved to file.")
        
        return {"status": "success", "message": "Relation added successfully"}
    except Exception as e:
        logger.error(f"Error adding relation: {str(e)}")
        print(f"[ERROR] Failed to add relation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add relation: {str(e)}")

@router.delete("/relations")
async def delete_relation(subject: str, predicate: str, object_val: str):
    """
    관계를 삭제합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        
        from rdflib import URIRef, Literal
        
        s = _resolve_uri(subject, om)
        p = _resolve_uri(predicate, om)
        # Handle object potentially being a URI or Literal
        o = _resolve_uri(object_val, om)
        if (s, p, o) not in om.graph:
            # Try literal if URI removal failed
            o = Literal(object_val)
        
        om.graph.remove((s, p, o))
        om.save_graph()
        
        return {"success": True, "message": "Relation deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting relation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete relation: {str(e)}")

@router.get("/quality-check")
async def quality_check():
    """
    온톨로지 품질을 검사합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = getattr(orchestrator.core, 'enhanced_ontology_manager', orchestrator.core.ontology_manager)
        
        # Use ontology validator
        from core_pipeline.ontology_validator import OntologyValidator
        validator = OntologyValidator(om)
        
        results = validator.validate_schema_compliance()
        
        issues = []
        # Category: axis_compliance
        axis_comp = results.get("axis_compliance", {})
        for check in axis_comp.get("checks", []):
            if check["status"] != "PASS":
                issues.append(QualityIssue(
                    severity="error" if check["status"] == "FAIL" else "warning",
                    message=f"{check['name']}: {check['message']}",
                    node_id=None
                ))

        # Category: connectivity_health
        conn_health = results.get("connectivity_health", {})
        for check in conn_health.get("checks", []):
            if check["status"] != "PASS":
                issues.append(QualityIssue(
                    severity="error" if check["status"] == "FAIL" else "warning",
                    message=f"{check['name']}: {check['message']}",
                    node_id=None
                ))
                
        # Category: reasoning_status
        reasoning_stat = results.get("reasoning_status", {})
        for check in reasoning_stat.get("checks", []):
            if check["status"] != "PASS":
                issues.append(QualityIssue(
                    severity="info",
                    message=f"{check['name']}: {check['message']}",
                    node_id=None
                ))
            
        status = "valid"
        if any(i.severity == "error" for i in issues):
            status = "error"
        elif any(i.severity == "warning" for i in issues):
            status = "warning"
            
        return QualityCheckResponse(status=status, issues=issues)
    except Exception as e:
        logger.error(f"Error during quality check: {str(e)}")
        # If validator fails, return a simple check
        return QualityCheckResponse(status="unknown", issues=[
            QualityIssue(severity="info", message=f"Quality check fallback: {str(e)}")
        ])
