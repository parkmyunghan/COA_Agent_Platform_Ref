# api/routers/ontology.py
"""
온톨로지 관련 API 엔드포인트
- SPARQL 쿼리 실행
- 그래프 데이터 조회
- 스키마 검증
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from core_pipeline.orchestrator import Orchestrator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ontology", tags=["ontology"])

# Global orchestrator instance (injected from main.py)
_orchestrator: Optional[Orchestrator] = None

# [OPTIMIZATION] Inferred Graph Cache
_inferred_graph_cache = {
    "graph": None,
    "source_hash": None
}


def set_orchestrator(orchestrator: Orchestrator):
    """Set the global orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return _orchestrator


# Request/Response Models
class SPARQLQueryRequest(BaseModel):
    query: str


class SPARQLQueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int


class GraphNode(BaseModel):
    id: str
    label: str
    group: str


class GraphLink(BaseModel):
    source: str
    target: str
    relation: str


class GraphDataResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


class ValidationIssue(BaseModel):
    severity: str  # "error", "warning", "info"
    message: str
    node_id: Optional[str] = None


class ValidationStatistics(BaseModel):
    total_nodes: int
    total_edges: int
    classes: int
    individuals: int


class ValidationResponse(BaseModel):
    status: str  # "valid", "warning", "error"
    statistics: ValidationStatistics
    issues: List[ValidationIssue]


class NodeDetailResponse(BaseModel):
    id: str
    label: str
    group: str
    properties: List[Dict[str, Any]]


class NLToSPARQLRequest(BaseModel):
    question: str  # 자연어 질문


class NLToSPARQLResponse(BaseModel):
    sparql: str           # 생성된 SPARQL 쿼리
    question: str         # 원래 질문
    success: bool         # 변환 성공 여부
    error: Optional[str] = None  # 에러 메시지


# API Endpoints
@router.post("/sparql", response_model=SPARQLQueryResponse)
async def execute_sparql_query(request: SPARQLQueryRequest):
    """
    SPARQL 쿼리를 실행하고 결과를 반환합니다.
    """
    try:
        orchestrator = get_orchestrator()
        ontology_manager = orchestrator.core.ontology_manager
        
        # Execute SPARQL query
        logger.info(f"Executing SPARQL query: {request.query[:100]}...")
        results = ontology_manager.graph.query(request.query)
        
        # Convert results to list of dictionaries
        result_list = []
        for row in results:
            result_dict = {}
            for var_name in results.vars:
                value = row[var_name]
                # Convert RDF terms to strings
                result_dict[str(var_name)] = str(value) if value else None
            result_list.append(result_dict)
        
        logger.info(f"SPARQL query returned {len(result_list)} results")
        
        return SPARQLQueryResponse(
            results=result_list,
            count=len(result_list)
        )
    
    except Exception as e:
        logger.error(f"Error executing SPARQL query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SPARQL query failed: {str(e)}")


@router.get("/graph", response_model=GraphDataResponse)
async def get_graph_data(
    mode: str = Query("instances", description="Graph mode: 'instances' or 'schema'"),
    groups: Optional[str] = Query(None, description="Comma-separated list of groups to filter"),
    relations: Optional[str] = Query(None, description="Comma-separated list of relations to filter"),
    search: Optional[str] = Query(None, description="Search term for node labels"),
    include_inferred: bool = Query(False, description="Include OWL-RL inferred relations in graph")
):
    """
    온톨로지 그래프 데이터를 조회합니다.
    분석 모드 및 필터링 지원.
    
    Args:
        include_inferred: OWL-RL 추론 결과를 그래프에 포함할지 여부
    """
    try:
        logger.info(f"======== GRAPH DATA REQUEST START (mode={mode}, include_inferred={include_inferred}) ========")
        orchestrator = get_orchestrator()
        ontology_manager = orchestrator.core.ontology_manager
        
        # 추론 포함 옵션이 활성화된 경우 추론된 그래프 사용
        graph_to_use = ontology_manager.graph
        if include_inferred:
            # [OPTIMIZATION] 캐시된 추론 그래프 사용
            from core_pipeline.owl_reasoner import OWLRL_AVAILABLE
            if OWLRL_AVAILABLE:
                try:
                    # 원본 그래프 해시 (변경 감지용 - 간단히 길이로 체크)
                    current_source_hash = len(ontology_manager.graph)
                    
                    if _inferred_graph_cache["source_hash"] == current_source_hash and _inferred_graph_cache["graph"] is not None:
                        graph_to_use = _inferred_graph_cache["graph"]
                        logger.info(f"Using cached inferred graph ({len(graph_to_use)} triples)")
                    else:
                        from core_pipeline.owl_reasoner import OWLReasoner
                        namespace = str(ontology_manager.ns) if hasattr(ontology_manager, 'ns') and ontology_manager.ns else None
                        reasoner = OWLReasoner(ontology_manager.graph, namespace)
                        
                        inferred_graph = reasoner.run_inference()
                        
                        if inferred_graph is not None:
                            graph_to_use = inferred_graph
                            _inferred_graph_cache["graph"] = inferred_graph
                            _inferred_graph_cache["source_hash"] = current_source_hash
                            logger.info(f"Created and cached inferred graph ({len(inferred_graph)} triples)")
                        else:
                            logger.warning("Inferred graph is None, using original graph")
                except Exception as e:
                    logger.warning(f"Inference cache logic failed: {e}")
            else:
                logger.warning("OWLRL not available, using original graph")
        
        # Get full graph data (추론된 그래프 사용)
        logger.info(f"Fetching graph data (mode={mode})")
        
        # 임시로 그래프를 교체하여 to_json 호출
        original_graph = ontology_manager.graph
        try:
            ontology_manager.graph = graph_to_use
            full_data = ontology_manager.to_json()
        finally:
            ontology_manager.graph = original_graph
        
        if not full_data or mode not in full_data:
            logger.warning(f"No graph data available for mode={mode}")
            return GraphDataResponse(nodes=[], links=[])
        
        # Parse filters
        group_filter = set(groups.split(",")) if groups else None
        relation_filter = set(relations.split(",")) if relations else None
        
        # Filter nodes
        nodes = []
        valid_node_ids = set()
        for node_data in full_data[mode].get("nodes", []):
            node_id = node_data.get("id")
            node_label = node_data.get("label", "")
            node_group = node_data.get("group", "Unknown")
            
            # Apply filters
            if group_filter and node_group not in group_filter:
                continue
            if search and search.lower() not in node_label.lower():
                continue
            
            nodes.append(GraphNode(
                id=node_id,
                label=node_label,
                group=node_group
            ))
            valid_node_ids.add(node_id)
        
        # Filter links (only include links between valid nodes)
        links = []
        for link_data in full_data[mode].get("links", []):
            source = link_data.get("source")
            target = link_data.get("target")
            relation = link_data.get("relation", "Unknown")
            
            if source not in valid_node_ids or target not in valid_node_ids:
                continue
            if relation_filter and relation not in relation_filter:
                continue
            
            links.append(GraphLink(
                source=source,
                target=target,
                relation=relation
            ))
        
        logger.info(f"Returning {len(nodes)} nodes and {len(links)} links")
        
        return GraphDataResponse(nodes=nodes, links=links)
    
    except Exception as e:
        logger.error(f"Error fetching graph data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph data: {str(e)}")


from core_pipeline.ontology_validator import OntologyValidator


@router.post("/nl-to-sparql", response_model=NLToSPARQLResponse)
async def convert_nl_to_sparql(request: NLToSPARQLRequest):
    """
    자연어 질문을 SPARQL 쿼리로 변환합니다.
    LLM을 사용하여 자연어를 분석하고 적절한 SPARQL 쿼리를 생성합니다.
    """
    try:
        orchestrator = get_orchestrator()
        ontology_manager = orchestrator.core.ontology_manager
        llm_manager = orchestrator.core.llm_manager
        
        logger.info(f"Converting NL to SPARQL: {request.question[:100]}...")
        
        # 스키마 정보 로드
        schema_summary = ontology_manager.get_schema_summary()
        
        # LLM 프롬프트 구성 (상세 스키마 정보 포함)
        prompt = f"""당신은 군사 온톨로지 전문가이자 SPARQL 마스터입니다.
사용자의 자연어 질문을 온톨로지 지식그래프를 조회하기 위한 SPARQL 쿼리로 변환하세요.

[필수 요구사항]
생성된 SPARQL 쿼리는 사용자의 학습을 돕기 위해 **각 라인마다 상세한 한글 주석(#)**을 반드시 포함해야 합니다.
어떤 데이터를 조회하는지, 어떤 필터를 거는지 상세히 설명해주세요.

[Prefixes - 반드시 포함]
# 온톨로지 기본 네임스페이스
PREFIX def: <http://coa-agent-platform.org/ontology#>
# 라벨 및 설명 스키마
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

[클래스 및 속성 - 반드시 이 이름만 사용하세요!]

1. 아군 부대 (def:아군부대현황)
   - rdfs:label: 부대명 (예: "기계화여단", "포병여단")
   - def:병종: 부대 종류 (값: "기갑", "포병", "보병", "기계화", "수색", "공병", "통신", "의무", "보급", "항공", "특수작전")
   - def:좌표정보: 위치 (예: "37.75, 126.90")
   - def:locatedIn: 지형셀 URI (예: def:지형셀_TERR024)
   - def:가용상태: "가용" 또는 "비가용"
   - def:임무역할: "주공", "조공", "화력지원", "예비" 등
   - def:상급부대: 상위 부대명 (예: "제1군단")
   - def:제대: "여단", "대대", "중대" 등
   - def:has전장축선: 축선 URI

2. 적군 부대 (def:적군부대현황)
   - rdfs:label: 부대명 (예: "적 기계화보병여단1", "적 전차대대1", "적 포병여단")
   - def:병종: 부대 종류 (값: "기계화", "기갑", "포병", "보병" 등) ← 아군과 동일!
   - def:위협수준: 위협 수준 (값: "High", "Medium", "Low")
   - def:제대: 부대 규모 (예: "여단", "대대")
   - def:좌표정보: 위치
   - def:has전장축선: 축선 URI
   - def:locatedIn: 지형셀 URI

3. 방책/COA (def:COA_Library)
   - rdfs:label: 방책명 (예: "정면 공격", "포위 공격", "주방어 진지 고수", "충격 반격")
   - ID 패턴: COA_OFF_xxx(공격), COA_DEF_xxx(방어), COA_CNT_xxx(반격), COA_DET_xxx(억제), COA_MAN_xxx(기동), COA_INF_xxx(정보), COA_PRE_xxx(선제)

4. 위협상황 (def:위협상황)
   - rdfs:label: 위협명 (예: "능선503 침투", "고지245 공중위협")
   - def:위협유형: 위협 유형 (값: "정면공격", "전면전", "공중위협", "공중강습", "침투" 등)
   - def:위협수준: 위협 수준 (값: "High", "Medium", "Low")
   - def:발생장소: 발생 위치

5. 축선 (def:전장축선) - ⚠️ 좌표정보 속성 없음!
   - rdfs:label: 축선명 (예: "동부 주공축선")
   - def:has지형셀: 연결된 지형셀 URI (예: def:지형셀_TERR001)
   - def:주요지형셀목록: 지형셀 목록 문자열 (예: "TERR001,TERR003,TERR005")
   - def:축선유형: "주공", "조공" 등
   - def:거리_km: 축선 거리
   - ID: AXIS01~AXIS10

6. 지형 (def:지형셀)
   - rdfs:label: 지형명 (예: "321고지", "계곡지대", "철원평야")
   - def:지형유형: 지형 종류 (값: "산악", "도시", "해안", "평야", "계곡", "고지")
   - def:좌표정보: 좌표 (예: "127.3133, 38.3000")
   - def:기동성등급: 기동 용이도 (1~5)
   - def:방어유리도: 방어 유리도 (1~5)
   - def:관측유리도: 관측 유리도 (1~5)
   - def:요충지여부: "Y" 또는 "N"
   - def:설명: 지형 설명 (예: "전략적 요충지/산악")
   - ID: TERR001~TERR031

7. 임무 (def:임무정보)
   - rdfs:label: 임무명 (예: "포병 제압", "서부 기계화차단", "강안방어")
   - def:임무종류: 임무 유형 (값: "공격", "방어", "지원")
   - def:작전지역: 작전 지역 (예: "동부전선", "북부", "중앙후방")
   - def:지휘관의도: 지휘관 의도 (예: "적 포병 제압", "적 기갑 돌파 차단")
   - def:has전장축선: 관련 축선 URI
   - ID: MSN001~MSN010

8. 자산 (def:아군가용자산)
   - rdfs:label: 자산명 (예: "K-9 자주포", "K-2 전차", "공병대대")
   - def:자산종류: 자산 유형
   - def:가용상태: "가용" 또는 "비가용"

[검색 패턴 예시]

Q: "포병 부대 목록과 위치"
→ 병종이 "포병"인 부대 검색
```
SELECT ?unit ?name ?location WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?name .
  ?unit def:병종 "포병" .
  OPTIONAL {{ ?unit def:좌표정보 ?location }}
}}
```

Q: "공격용 방책 목록"
→ ID에 "OFF"가 포함된 방책
```
SELECT ?coa ?name WHERE {{
  ?coa a def:COA_Library .
  ?coa rdfs:label ?name .
  FILTER(CONTAINS(STR(?coa), "COA_OFF"))
}}
```

Q: "모든 축선 목록"
```
SELECT ?axis ?name WHERE {{
  ?axis a def:전장축선 .
  ?axis rdfs:label ?name .
}}
```

Q: "기갑 부대가 배치된 축선"
```
SELECT ?unit ?unitName ?axis ?axisName WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?unitName .
  ?unit def:병종 "기갑" .
  ?unit def:has전장축선 ?axis .
  ?axis rdfs:label ?axisName .
}}
```

Q: "동부 주공축선의 좌표 정보" 또는 "축선의 위치"
→ 축선 자체에는 좌표가 없으므로, 관계를 따라 지형셀의 좌표를 조회
```
SELECT ?axis ?axisName ?terrain ?terrainName ?coords WHERE {{
  ?axis a def:전장축선 .
  ?axis rdfs:label ?axisName .
  FILTER(CONTAINS(?axisName, "동부 주공"))
  ?axis def:has지형셀 ?terrain .
  ?terrain rdfs:label ?terrainName .
  ?terrain def:좌표정보 ?coords .
}}
```

Q: "가용 상태인 부대"
```
SELECT ?unit ?name WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?name .
  ?unit def:가용상태 "가용" .
}}
```

Q: "산악 지형에 해당하는 지역" 또는 "산악 지형 목록"
→ 지형유형이 "산악"인 지형셀 검색
```
SELECT ?terrain ?name ?coords ?defense WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?name .
  ?terrain def:지형유형 "산악" .
  OPTIONAL {{ ?terrain def:좌표정보 ?coords }}
  OPTIONAL {{ ?terrain def:방어유리도 ?defense }}
}}
```

Q: "도시 지형 중 요충지인 곳"
```
SELECT ?terrain ?name ?coords WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?name .
  ?terrain def:지형유형 "도시" .
  ?terrain def:요충지여부 "Y" .
  OPTIONAL {{ ?terrain def:좌표정보 ?coords }}
}}
```

Q: "기동성이 좋은 지형" 또는 "기동에 유리한 지형"
→ 기동성등급이 높은(4 이상) 지형
```
SELECT ?terrain ?name ?mobility ?type WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?name .
  ?terrain def:기동성등급 ?mobility .
  OPTIONAL {{ ?terrain def:지형유형 ?type }}
  FILTER(xsd:float(?mobility) >= 4)
}}
```

Q: "방어에 유리한 산악 지형"
```
SELECT ?terrain ?name ?defense ?coords WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?name .
  ?terrain def:지형유형 "산악" .
  ?terrain def:방어유리도 ?defense .
  OPTIONAL {{ ?terrain def:좌표정보 ?coords }}
  FILTER(xsd:float(?defense) >= 4)
}}
```

Q: "적 기갑 부대 정보" 또는 "적 포병 부대"
→ 적군부대현황에서 병종으로 검색
```
SELECT ?enemy ?name ?coords ?threatLevel WHERE {{
  ?enemy a def:적군부대현황 .
  ?enemy rdfs:label ?name .
  ?enemy def:병종 "기갑" .
  OPTIONAL {{ ?enemy def:좌표정보 ?coords }}
  OPTIONAL {{ ?enemy def:위협수준 ?threatLevel }}
}}
```

Q: "위협 수준이 높은 적 부대" 또는 "고위협 적 부대"
```
SELECT ?enemy ?name ?type ?coords WHERE {{
  ?enemy a def:적군부대현황 .
  ?enemy rdfs:label ?name .
  ?enemy def:위협수준 "High" .
  OPTIONAL {{ ?enemy def:병종 ?type }}
  OPTIONAL {{ ?enemy def:좌표정보 ?coords }}
}}
```

Q: "동부 축선에 배치된 적 부대"
→ 관계를 통해 축선과 연결된 적 부대 검색
```
SELECT ?enemy ?enemyName ?axis ?axisName WHERE {{
  ?enemy a def:적군부대현황 .
  ?enemy rdfs:label ?enemyName .
  ?enemy def:has전장축선 ?axis .
  ?axis rdfs:label ?axisName .
  FILTER(CONTAINS(?axisName, "동부"))
}}
```

Q: "위협 수준이 높은 상황" 또는 "고위협 상황"
```
SELECT ?threat ?name ?type ?location WHERE {{
  ?threat a def:위협상황 .
  ?threat rdfs:label ?name .
  ?threat def:위협수준 "High" .
  OPTIONAL {{ ?threat def:위협유형 ?type }}
  OPTIONAL {{ ?threat def:발생장소 ?location }}
}}
```

Q: "공중 위협 상황" 또는 "공중위협 목록"
```
SELECT ?threat ?name ?level ?location WHERE {{
  ?threat a def:위협상황 .
  ?threat rdfs:label ?name .
  ?threat def:위협유형 "공중위협" .
  OPTIONAL {{ ?threat def:위협수준 ?level }}
  OPTIONAL {{ ?threat def:발생장소 ?location }}
}}
```

Q: "방어 임무 목록" 또는 "공격 임무 목록"
```
SELECT ?mission ?name ?region ?intent WHERE {{
  ?mission a def:임무정보 .
  ?mission rdfs:label ?name .
  ?mission def:임무종류 "방어" .
  OPTIONAL {{ ?mission def:작전지역 ?region }}
  OPTIONAL {{ ?mission def:지휘관의도 ?intent }}
}}
```

Q: "임무와 관련된 축선" 또는 "임무에 할당된 축선"
```
SELECT ?mission ?missionName ?axis ?axisName WHERE {{
  ?mission a def:임무정보 .
  ?mission rdfs:label ?missionName .
  ?mission def:has전장축선 ?axis .
  ?axis rdfs:label ?axisName .
}}
```

Q: "요충지인 지형 목록"
```
SELECT ?terrain ?name ?type ?coords WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?name .
  ?terrain def:요충지여부 "Y" .
  OPTIONAL {{ ?terrain def:지형유형 ?type }}
  OPTIONAL {{ ?terrain def:좌표정보 ?coords }}
}}
```

Q: "하천 지형 목록"
```
SELECT ?terrain ?name ?coords WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?name .
  ?terrain def:지형유형 "하천" .
  OPTIONAL {{ ?terrain def:좌표정보 ?coords }}
}}
```

Q: "반격 방책 목록"
→ ID에 CNT가 포함된 방책
```
SELECT ?coa ?name WHERE {{
  ?coa a def:COA_Library .
  ?coa rdfs:label ?name .
  FILTER(CONTAINS(STR(?coa), "COA_CNT"))
}}
```

[온톨로지 관계 다이어그램 - 반드시 참조]
```
                    ┌─────────────┐
                    │  임무정보    │
                    └──────┬──────┘
                           │ has전장축선
                           ▼
┌─────────────┐  has전장축선  ┌─────────────┐  has지형셀  ┌─────────────┐
│ 아군부대현황 │ ───────────→ │  전장축선    │ ─────────→ │   지형셀    │
└──────┬──────┘               └──────┬──────┘             └──────┬──────┘
       │                             │                           │
       │ locatedIn                   │                           │ ← 좌표정보 있음!
       └─────────────────────────────┼───────────────────────────┘
                                     │
                           ┌─────────┴─────────┐
                           │                   │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  위협상황   │     │ 적군부대현황 │
                    └─────────────┘     └─────────────┘
```

[관계 탐색 패턴 - ★ 중요 ★]

1. 축선의 좌표가 필요할 때:
   축선 → has지형셀 → 지형셀.좌표정보
   
2. 부대가 위치한 지형 정보가 필요할 때:
   부대 → locatedIn → 지형셀 (지형명, 지형유형, 좌표정보)

3. 축선에 배치된 부대가 필요할 때:
   부대 → has전장축선 → 축선 (역방향 탐색)

4. 임무와 관련된 축선/지형이 필요할 때:
   임무 → has전장축선 → 축선 → has지형셀 → 지형셀

5. 위협이 발생한 위치 정보가 필요할 때:
   위협상황 → has지형셀 → 지형셀.좌표정보

[추가 관계 탐색 예시]

Q: "동부 전선에 배치된 부대와 그 위치 지형"
```
SELECT ?unit ?unitName ?terrain ?terrainName ?coords WHERE {{
  ?unit a def:아군부대현황 .
  ?unit rdfs:label ?unitName .
  ?unit def:has전장축선 ?axis .
  ?axis rdfs:label ?axisName .
  FILTER(CONTAINS(?axisName, "동부"))
  ?unit def:locatedIn ?terrain .
  ?terrain rdfs:label ?terrainName .
  OPTIONAL {{ ?terrain def:좌표정보 ?coords }}
}}
```

Q: "특정 위협과 관련된 적군 부대 정보"
```
SELECT ?threat ?threatName ?enemy ?enemyName ?coords WHERE {{
  ?threat a def:위협상황 .
  ?threat rdfs:label ?threatName .
  ?threat def:has적군부대현황 ?enemy .
  ?enemy rdfs:label ?enemyName .
  OPTIONAL {{ ?enemy def:좌표정보 ?coords }}
}}
```

Q: "특정 임무에 할당된 축선과 지형 정보"
```
SELECT ?mission ?missionName ?axis ?axisName ?terrain ?terrainName WHERE {{
  ?mission a def:임무정보 .
  ?mission rdfs:label ?missionName .
  ?mission def:has전장축선 ?axis .
  ?axis rdfs:label ?axisName .
  OPTIONAL {{ ?axis def:has지형셀 ?terrain . ?terrain rdfs:label ?terrainName }}
}}
```

Q: "지형셀에 위치한 모든 부대와 자산"
```
SELECT ?terrain ?terrainName ?entity ?entityName ?entityType WHERE {{
  ?terrain a def:지형셀 .
  ?terrain rdfs:label ?terrainName .
  {{
    ?entity a def:아군부대현황 .
    ?entity def:locatedIn ?terrain .
    ?entity rdfs:label ?entityName .
    BIND("아군부대" AS ?entityType)
  }} UNION {{
    ?entity a def:아군가용자산 .
    ?entity def:locatedIn ?terrain .
    ?entity rdfs:label ?entityName .
    BIND("자산" AS ?entityType)
  }}
}}
```

[중요 규칙]
1. 클래스명은 반드시 한글로: def:아군부대현황, def:적군부대현황, def:전장축선, def:지형셀, def:임무정보, def:위협상황, def:COA_Library, def:아군가용자산
2. 영문 클래스명 사용 금지: FriendlyUnit, EnemyUnit, Axis, Terrain 등 사용하지 마세요
3. 부대 유형 검색 시 def:병종 속성 사용 (rdfs:label에서 검색하지 마세요)
4. OPTIONAL로 없을 수 있는 속성 처리 (특히 좌표정보)
5. 마크다운 코드 블록 사용 금지
6. **관계 탐색 필수**: 직접 속성이 없으면 관계를 따라 탐색 (예: 축선 좌표 → has지형셀 → 지형셀.좌표정보)
7. 여러 엔티티를 연결할 때 JOIN 패턴 사용: ?부대 def:has전장축선 ?축선 . ?축선 def:has지형셀 ?지형 .
8. 역방향 탐색 가능: "이 축선에 배치된 부대" → ?부대 def:has전장축선 ?축선 패턴 사용
9. **주석 필수**: 초보자도 이해할 수 있도록 라인별로 친절한 한글 주석을 달아주세요.

[Question]
"{request.question}"

[SPARQL Query]
"""
        
        # LLM 호출
        response = llm_manager.generate(prompt, max_tokens=500)
        
        # 응답 정제 (마크다운 코드 블록 및 불필요한 텍스트 제거)
        sparql = response.strip()
        sparql = sparql.replace("```sparql", "").replace("```", "")
        
        # 라인 단위 정제 (구분선 등 제거)
        clean_lines = []
        for line in sparql.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('---'): # 구분선 제거
                continue
            clean_lines.append(line)
        
        sparql = '\n'.join(clean_lines)
        if not sparql.upper().startswith("PREFIX"):
            prefixes = """# [네임스페이스 설정]
# 기본 온톨로지 스키마 (클래스, 속성 등)
PREFIX def: <http://coa-agent-platform.org/ontology#>
# RDF 구문 및 타입 정의
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
# RDFS 스키마 (라벨, 레이블 등)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
# OWL 웹 온톨로지 언어
PREFIX owl: <http://www.w3.org/2002/07/owl#>

"""
            sparql = prefixes + sparql
        
        logger.info(f"Generated SPARQL query: {sparql[:200]}...")
        
        return NLToSPARQLResponse(
            sparql=sparql,
            question=request.question,
            success=True
        )
    
    except Exception as e:
        logger.error(f"Error converting NL to SPARQL: {str(e)}")
        return NLToSPARQLResponse(
            sparql="",
            question=request.question,
            success=False,
            error=str(e)
        )


@router.get("/validate", response_model=ValidationResponse)
async def validate_ontology():
    """
    온톨로지 스키마를 검증하고 일관성 이슈를 반환합니다.
    core_pipeline.ontology_validator.OntologyValidator를 사용하여 정교한 검증을 수행합니다.
    """
    try:
        orchestrator = get_orchestrator()
        ontology_manager = orchestrator.core.ontology_manager
        
        logger.info("Validating ontology schema using OntologyValidator...")
        
        # 1. Initialize Validator
        validator = OntologyValidator(ontology_manager)
        
        # 2. Run Validation
        results = validator.validate_schema_compliance()
        
        # 3. Transform results to Response Model
        issues = []
        overall_score = results.get("overall_score", 0)
        
        # Map checks to ValidationIssues
        categories = ["axis_compliance", "connectivity_health", "reasoning_status"]
        for cat in categories:
            cat_result = results.get(cat, {})
            for check in cat_result.get("checks", []):
                # Map Check Status to Issue Severity
                status = check.get("status", "INFO")
                severity = "info"
                if status == "FAIL":
                    severity = "error"
                elif status == "WARNING":
                    severity = "warning"
                
                # Create detailed message
                count = check.get("count", 0)
                msg = f"[{cat}] {check.get('name')}: {check.get('message')} (Count: {count})"
                
                # Add to issues list (even passing checks can be shown as info if desired, 
                # but let's focus on non-PASS or significant items)
                if status != "PASS":
                     issues.append(ValidationIssue(
                        severity=severity,
                        message=msg,
                        node_id=None # OntologyValidator aggregates counts, doesn't give single node_id here
                    ))
                elif check.get('name') == "전술적 유불리 추론" and count > 0:
                     # Positive confirmation for reasoning
                     issues.append(ValidationIssue(
                        severity="info",
                        message=msg,
                        node_id="ReasoningEngine"
                    ))

        # 4. Get Statistics (Graph Stats) using existing logic or helper
        # Reuse simple counting for statistics display
        full_data = ontology_manager.to_json()
        total_nodes = 0
        total_edges = 0
        classes = set()
        individuals = set()
        
        for mode in ["instances", "schema"]:
            if mode in full_data:
                nodes = full_data[mode].get("nodes", [])
                links = full_data[mode].get("links", [])
                total_nodes += len(nodes)
                total_edges += len(links)
                for node in nodes:
                    if "Class" in node.get("group", "") or mode == "schema":
                        classes.add(node.get("id"))
                    else:
                        individuals.add(node.get("id"))

        # Determine overall status based on issues
        error_count = len([i for i in issues if i.severity == "error"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        
        status = "valid"
        if error_count > 0:
            status = "error"
        elif warning_count > 0:
            status = "warning"
        
        logger.info(f"Validation complete: {status} (Score: {overall_score})")
        
        return ValidationResponse(
            status=status,
            statistics=ValidationStatistics(
                total_nodes=total_nodes,
                total_edges=total_edges,
                classes=len(classes),
                individuals=len(individuals)
            ),
            issues=issues
        )
    
    except Exception as e:
        logger.error(f"Error validating ontology: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
@router.get("/node/{node_id}", response_model=NodeDetailResponse)
async def get_node_details(node_id: str):
    """
    특정 노드의 상세 정보 및 속성을 조회합니다.
    """
    try:
        orchestrator = get_orchestrator()
        om = orchestrator.core.ontology_manager
        
        from rdflib import URIRef, Literal
        
        # URI 생성 (ID 기반)
        node_uri = URIRef(om.ns[node_id])
        
        # 라벨 및 그룹 정보 가져오기
        label = ""
        for _, _, lbl in om.graph.triples((node_uri, om.ns.label, None)):
            label = str(lbl)
            break
        if not label:
            for _, _, lbl in om.graph.triples((node_uri, om.RDFS.label, None)):
                label = str(lbl)
                break
        if not label:
            label = node_id
            
        group = "Unknown"
        for _, _, typ in om.graph.triples((node_uri, om.RDF.type, None)):
            # ns 네임스페이스에 있는 경우만 그룹으로 인정
            if str(typ).startswith(str(om.ns)):
                group = str(typ).split("#")[-1] if "#" in str(typ) else str(typ).split("/")[-1]
                break
        
        # 모든 속성 수집 (Subject가 node_id인 모든 트리플)
        properties = []
        for s, p, o in om.graph.triples((node_uri, None, None)):
            pred_label = str(p).split("#")[-1] if "#" in str(p) else str(p).split("/")[-1]
            
            # 값 처리 (URI면 로컬명, 리터럴이면 문자열)
            if isinstance(o, URIRef):
                val_str = str(o).split("#")[-1] if "#" in str(o) else str(o).split("/")[-1]
            else:
                val_str = str(o)
                
            properties.append({
                "predicate": str(p),
                "predicate_label": pred_label,
                "value": val_str,
                "is_uri": isinstance(o, URIRef)
            })
            
        return NodeDetailResponse(
            id=node_id,
            label=label,
            group=group,
            properties=properties
        )
        
    except Exception as e:
        logger.error(f"Error fetching node details ({node_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch node details: {str(e)}")
