# ui/components/ontology_explainer.py
# -*- coding: utf-8 -*-
"""
온톨로지 관계 설명 컴포넌트
온톨로지 그래프의 관계를 설명하고 시각화
"""
import streamlit as st
from typing import Dict, List, Optional
from rdflib import Graph, URIRef, Namespace, RDF


# 관계 타입별 의미 설명
RELATION_MEANINGS = {
    "hasAvailableResource": "가용 자원 보유",
    "requiresResource": "필요한 자원",
    "occursInEnvironment": "발생 환경",
    "compatibleWith": "호환 가능",
    "hasSuitableCOA": "적합한 방책",
    "has장소": "위치 관계",
    "relatedTo": "관련 관계",
    "hasRelation": "일반 관계"
}


def render_ontology_explainer(ontology_manager, entity_id: Optional[str] = None):
    """
    온톨로지 관계 설명 패널 렌더링
    
    Args:
        ontology_manager: OntologyManager 인스턴스
        entity_id: 설명할 엔티티 ID (선택적)
    """
    st.subheader("🔗 온톨로지 관계 설명")
    
    if ontology_manager is None or ontology_manager.graph is None:
        st.warning("온톨로지 그래프가 생성되지 않았습니다.")
        return
    
    # 엔티티 선택 (하이브리드 방식)
    if entity_id is None:
        selection_method = st.radio(
            "엔티티 선택 방식",
            ["📋 목록에서 선택", "🔍 검색", "⌨️ 직접 입력"],
            horizontal=True,
            key="entity_selection_method"
        )
        
        graph = ontology_manager.graph
        # ns_legacy를 우선 사용 (실제 그래프에서 사용하는 네임스페이스)
        ns = getattr(ontology_manager, 'ns_legacy', None) or ontology_manager.ns
        
        if selection_method == "📋 목록에서 선택":
            # to_json()을 사용하여 실제 노드 목록 가져오기 (더 정확함)
            try:
                graph_data = ontology_manager.to_json()
                instance_nodes = graph_data.get("instances", {}).get("nodes", [])
                
                if instance_nodes:
                    # 노드 ID와 라벨 추출
                    entities = []
                    for node in instance_nodes:
                        node_id = node.get("id", "")
                        node_label = node.get("label", node_id)
                        node_group = node.get("group", "")
                        if node_id:
                            entities.append({
                                "id": node_id,
                                "label": node_label,
                                "group": node_group
                            })
                    
                    if entities:
                        # 그룹별로 정렬
                        entity_groups = {}
                        for entity in entities:
                            group = entity.get("group", "기타")
                            if group not in entity_groups:
                                entity_groups[group] = []
                            entity_groups[group].append(entity)
                        
                        # 그룹별로 표시
                        entity_options = []
                        for group_name, entity_list in sorted(entity_groups.items()):
                            entity_options.append(f"--- {group_name} ({len(entity_list)}개) ---")
                            for entity in sorted(entity_list, key=lambda x: x.get("label", x.get("id", ""))):
                                label = entity.get("label", entity.get("id", ""))
                                entity_options.append(f"{entity.get('id')} ({label})")
                        
                        selected = st.selectbox(
                            "엔티티 선택",
                            ["선택하세요..."] + entity_options,
                            key="entity_selectbox"
                        )
                        
                        if selected and selected != "선택하세요...":
                            # 선택된 엔티티 ID 추출 (괄호 앞 부분)
                            entity_id = selected.split(" (")[0]
                    else:
                        st.info("그래프에서 엔티티를 찾을 수 없습니다.")
                        entity_id = None
                else:
                    # 폴백: 그래프에서 직접 추출
                    entities = get_all_entities(graph, ns)
                    if entities:
                        # 엔티티를 타입별로 그룹화
                        entity_groups = group_entities_by_type(graph, ns, entities)
                        
                        # 그룹별로 표시
                        entity_options = []
                        for entity_type, entity_list in entity_groups.items():
                            entity_options.append(f"--- {entity_type} ({len(entity_list)}개) ---")
                            entity_options.extend([f"{e} ({get_entity_type_label(graph, ns, e)})" for e in entity_list])
                        
                        selected = st.selectbox(
                            "엔티티 선택",
                            ["선택하세요..."] + entity_options,
                            key="entity_selectbox"
                        )
                        
                        if selected and selected != "선택하세요...":
                            # 선택된 엔티티 ID 추출 (괄호 앞 부분)
                            entity_id = selected.split(" (")[0]
                    else:
                        st.info("그래프에서 엔티티를 찾을 수 없습니다.")
                        entity_id = None
            except Exception as e:
                st.warning(f"엔티티 목록을 가져오는 중 오류 발생: {e}")
                # 폴백: 그래프에서 직접 추출
                entities = get_all_entities(graph, ns)
                if entities:
                    entity_groups = group_entities_by_type(graph, ns, entities)
                    entity_options = []
                    for entity_type, entity_list in entity_groups.items():
                        entity_options.append(f"--- {entity_type} ({len(entity_list)}개) ---")
                        entity_options.extend([f"{e} ({get_entity_type_label(graph, ns, e)})" for e in entity_list])
                    
                    selected = st.selectbox(
                        "엔티티 선택",
                        ["선택하세요..."] + entity_options,
                        key="entity_selectbox"
                    )
                    
                    if selected and selected != "선택하세요...":
                        entity_id = selected.split(" (")[0]
                else:
                    st.info("그래프에서 엔티티를 찾을 수 없습니다.")
                    entity_id = None
                
        elif selection_method == "🔍 검색":
            search_term = st.text_input(
                "엔티티 검색",
                placeholder="THREAT, COA, ASSET, RES...",
                key="entity_search"
            )
            
            if search_term:
                matching_entities = search_entities(graph, ns, search_term)
                if matching_entities:
                    # 검색 결과를 타입별로 표시
                    entity_options = []
                    for entity_id_option, entity_type in matching_entities:
                        entity_options.append(f"{entity_id_option} ({entity_type})")
                    
                    selected = st.selectbox(
                        f"검색 결과 ({len(matching_entities)}개)",
                        ["선택하세요..."] + entity_options,
                        key="entity_search_result"
                    )
                    
                    if selected and selected != "선택하세요...":
                        entity_id = selected.split(" (")[0]
                else:
                    st.info(f"'{search_term}'와 일치하는 엔티티를 찾을 수 없습니다.")
                    entity_id = None
            else:
                entity_id = None
        else:  # 직접 입력
            # 실제 그래프에서 첫 번째 엔티티를 가져와서 디폴트값으로 사용
            default_entity_id = ""
            try:
                graph_data = ontology_manager.to_json()
                instance_nodes = graph_data.get("instances", {}).get("nodes", [])
                if instance_nodes:
                    # 첫 번째 노드의 ID를 디폴트값으로 사용
                    default_entity_id = instance_nodes[0].get("id", "")
                else:
                    # 폴백: 그래프에서 직접 추출
                    entities = get_all_entities(graph, ns)
                    if entities:
                        default_entity_id = entities[0]
            except Exception:
                # 오류 발생 시 빈 값 사용
                default_entity_id = ""
            
            # 예시 텍스트 생성
            example_text = "지형셀_TERR001, 임무정보_MSN001 등"
            if default_entity_id:
                example_text = f"{default_entity_id} (또는 다른 엔티티 ID)"
            
            entity_id = st.text_input(
                "엔티티 ID 직접 입력",
                value=default_entity_id,
                help=f"관계를 확인할 엔티티 ID를 입력하세요 (예: {example_text})",
                key="entity_direct_input"
            )
    
    if entity_id:
        render_entity_relations(ontology_manager, entity_id)


def render_entity_relations(ontology_manager, entity_id: str):
    """엔티티의 관계 표시"""
    graph = ontology_manager.graph
    # ns_legacy를 우선 사용 (실제 그래프에서 사용하는 네임스페이스)
    ns = getattr(ontology_manager, 'ns_legacy', None) or ontology_manager.ns
    
    # 엔티티 URI 생성 (ns_legacy 우선, 없으면 ns 사용)
    try:
        entity_uri = URIRef(ns[entity_id])
    except Exception:
        # ns_legacy가 없으면 ns 사용
        ns = ontology_manager.ns
        entity_uri = URIRef(ns[entity_id])
    
    # 엔티티가 그래프에 존재하는지 확인
    entity_exists = (entity_uri, None, None) in graph or (None, None, entity_uri) in graph
    
    if not entity_exists:
        # ns_legacy로 다시 시도
        if hasattr(ontology_manager, 'ns_legacy') and ontology_manager.ns_legacy:
            try:
                entity_uri_legacy = URIRef(ontology_manager.ns_legacy[entity_id])
                entity_exists = (entity_uri_legacy, None, None) in graph or (None, None, entity_uri_legacy) in graph
                if entity_exists:
                    ns = ontology_manager.ns_legacy
                    entity_uri = entity_uri_legacy
            except Exception:
                pass
    
    if not entity_exists:
        st.warning(f"엔티티 '{entity_id}'를 그래프에서 찾을 수 없습니다.")
        st.info("💡 사용 가능한 엔티티 예시: 지형셀_TERR009, 임무정보_MSN001 등")
        return
    
    st.success(f"✅ 엔티티 '{entity_id}' 발견")
    
    # 1. 시각화 (Graphviz)
    render_ontology_graph(graph, ns, entity_id)
    
    # 2. 직접 관계
    direct_relations = get_direct_relations(graph, ns, entity_uri)
    render_direct_relations(direct_relations, entity_id)
    
    # 3. 간접 관계 (체인)
    chains = find_relation_chains(graph, ns, entity_uri, max_depth=2)
    if chains:
        render_relation_chains(chains, entity_id)


def render_ontology_graph(graph, ns, center_id):
    """온톨로지 그래프 시각화 (Graphviz)"""
    st.markdown("#### 🕸️ 온톨로지 그래프 시각화")
    
    # 중심 노드와 직접 연결된 노드들만 추출
    center_uri = URIRef(ns[center_id])
    
    dot = f"""
    digraph Ontology {{
        rankdir=LR;
        splines=curved;
        nodesep=0.5;
        ranksep=1.0;
        fontname="Malgun Gothic";
        fontsize=10;
        bgcolor="white";
        
        node [shape=ellipse, style="filled", fontname="Malgun Gothic", fontsize=10, fontcolor="black"];
        edge [fontname="Malgun Gothic", fontsize=8, color="#333333", fontcolor="black"];
        
        # Center Node
        "{center_id}" [fillcolor="#ff7675", fontcolor="white", penwidth=2];
    """
    
    # 관계 추가
    # Outgoing
    for s, p, o in graph.triples((center_uri, None, None)):
        pred = str(p).split('#')[-1]
        obj = str(o).split('#')[-1]
        dot += f'    "{center_id}" -> "{obj}" [label="{pred}", color="#333333", fontcolor="black"];\n'
        dot += f'    "{obj}" [fillcolor="#74b9ff", fontcolor="black"];\n'
        
    # Incoming
    for s, p, o in graph.triples((None, None, center_uri)):
        pred = str(p).split('#')[-1]
        subj = str(s).split('#')[-1]
        dot += f'    "{subj}" -> "{center_id}" [label="{pred}", color="#333333", fontcolor="black"];\n'
        dot += f'    "{subj}" [fillcolor="#55efc4", fontcolor="black"];\n'
        
    dot += "}"
    
    st.graphviz_chart(dot, width='stretch')


def get_direct_relations(graph: Graph, ns: Namespace, entity_uri: URIRef) -> Dict:
    """직접 관계 조회"""
    relations = {}
    
    # 나가는 관계 (entity가 주체인 경우)
    for s, p, o in graph.triples((entity_uri, None, None)):
        predicate = str(p).split('#')[-1] if '#' in str(p) else str(p)
        object_uri = str(o).split('#')[-1] if '#' in str(o) else str(o)
        
        if predicate not in relations:
            relations[predicate] = []
        relations[predicate].append(object_uri)
    
    # 들어오는 관계 (entity가 객체인 경우)
    for s, p, o in graph.triples((None, None, entity_uri)):
        predicate = str(p).split('#')[-1] if '#' in str(p) else str(p)
        subject_uri = str(s).split('#')[-1] if '#' in str(s) else str(s)
        
        inverse_predicate = f"역_{predicate}"
        if inverse_predicate not in relations:
            relations[inverse_predicate] = []
        relations[inverse_predicate].append(subject_uri)
    
    return relations


def render_direct_relations(relations: Dict, entity_id: str):
    """직접 관계 표시"""
    st.markdown("#### 📊 직접 연결된 관계")
    
    if not relations:
        st.info("직접 연결된 관계가 없습니다.")
        return
    
    for predicate, target_entities in relations.items():
        # 관계 의미 설명
        relation_meaning = get_relation_meaning(predicate)
        
        with st.expander(f"🔗 {predicate} ({len(target_entities)}개)", expanded=True):
            st.write(f"**의미:** {relation_meaning}")
            
            # 연결된 엔티티 목록
            st.write(f"**연결된 엔티티:**")
            for i, entity in enumerate(target_entities[:10], 1):  # 최대 10개만 표시
                st.write(f"{i}. {entity}")
            
            if len(target_entities) > 10:
                st.caption(f"... 외 {len(target_entities) - 10}개")


def find_relation_chains(graph: Graph, ns: Namespace, entity_uri: URIRef, max_depth: int = 2) -> List[Dict]:
    """관계 체인 탐색"""
    chains = []
    
    def dfs(current_uri: URIRef, path: List[str], predicates: List[str], depth: int):
        if depth > max_depth:
            return
        
        # 나가는 관계 탐색
        for s, p, o in graph.triples((current_uri, None, None)):
            if o not in path:  # 순환 방지
                predicate = str(p).split('#')[-1] if '#' in str(p) else str(p)
                object_uri = str(o).split('#')[-1] if '#' in str(o) else str(o)
                
                new_path = path + [object_uri]
                new_predicates = predicates + [predicate]
                
                chains.append({
                    "path": new_path,
                    "predicates": new_predicates,
                    "depth": depth + 1,
                    "score": calculate_chain_score(new_path, new_predicates)
                })
                
                # 재귀 탐색
                dfs(o, new_path, new_predicates, depth + 1)
    
    initial_entity = str(entity_uri).split('#')[-1] if '#' in str(entity_uri) else str(entity_uri)
    dfs(entity_uri, [initial_entity], [], 0)
    
    # 점수 순으로 정렬
    chains.sort(key=lambda x: x["score"], reverse=True)
    
    return chains[:10]  # 상위 10개만 반환


def calculate_chain_score(path: List[str], predicates: List[str]) -> float:
    """체인 점수 계산"""
    # 간단한 점수 계산: 체인 길이와 관계 타입에 따라
    base_score = 1.0 / len(path) if path else 0
    
    # 중요한 관계 타입에 가중치 부여
    important_predicates = ["hasSuitableCOA", "requiresResource", "hasAvailableResource"]
    for pred in predicates:
        if pred in important_predicates:
            base_score *= 1.5
    
    return base_score


def render_relation_chains(chains: List[Dict], entity_id: str):
    """관계 체인 표시"""
    st.markdown("#### 🔗 간접 관계 체인")
    
    if not chains:
        st.info("간접 관계 체인이 없습니다.")
        return
    
    st.write(f"**발견된 체인:** {len(chains)}개")
    
    # 최고 체인 표시
    best_chain = chains[0] if chains else None
    if best_chain:
        st.markdown("##### 최고 점수 체인")
        path = best_chain.get("path", [])
        predicates = best_chain.get("predicates", [])
        
        # 체인 시각화
        chain_text = " → ".join([
            f"{path[i]} ({predicates[i] if i < len(predicates) else 'N/A'})"
            for i in range(len(path))
        ])
        st.write(chain_text)
        st.write(f"**점수:** {best_chain.get('score', 0):.3f}")
        st.write(f"**깊이:** {best_chain.get('depth', 0)}")
    
    # 체인 요약
    if len(chains) > 1:
        with st.expander("전체 체인 목록", expanded=False):
            for i, chain in enumerate(chains[:5], 1):  # 상위 5개만 표시
                path = chain.get("path", [])
                predicates = chain.get("predicates", [])
                
                chain_text = " → ".join([
                    f"{path[j]} ({predicates[j] if j < len(predicates) else 'N/A'})"
                    for j in range(len(path))
                ])
                st.write(f"{i}. {chain_text} (점수: {chain.get('score', 0):.3f})")


def get_relation_meaning(predicate: str) -> str:
    """관계 타입의 의미 반환"""
    # 역_ 접두사 제거
    clean_predicate = predicate.replace("역_", "")
    
    meaning = RELATION_MEANINGS.get(clean_predicate, "일반 관계")
    
    if predicate.startswith("역_"):
        return f"역 관계: {meaning}"
    
    return meaning


def get_all_entities(graph: Graph, ns: Namespace) -> List[str]:
    """그래프에서 모든 엔티티 목록 가져오기"""
    entities = set()
    
    # ns_legacy와 ns 모두 확인
    ns_str = str(ns)
    ns_legacy_str = "http://coa-agent-platform.org/ontology#"
    ns_new_str = "http://defense-ai.kr/ontology#"
    
    # 모든 트리플에서 주체와 객체 추출
    for s, p, o in graph.triples((None, None, None)):
        # 주체 추출
        if isinstance(s, URIRef):
            s_str = str(s)
            # ns_legacy 또는 ns로 시작하는 경우만 추출
            if s_str.startswith(ns_legacy_str) or s_str.startswith(ns_new_str) or s_str.startswith(ns_str):
                entity_id = _extract_entity_id(s_str, ns)
                if entity_id:
                    entities.add(entity_id)
        
        # 객체 추출 (리터럴 제외)
        if isinstance(o, URIRef):
            o_str = str(o)
            # ns_legacy 또는 ns로 시작하는 경우만 추출
            if o_str.startswith(ns_legacy_str) or o_str.startswith(ns_new_str) or o_str.startswith(ns_str):
                entity_id = _extract_entity_id(o_str, ns)
                if entity_id:
                    entities.add(entity_id)
    
    return sorted(list(entities))


def _extract_entity_id(uri: str, ns: Namespace) -> Optional[str]:
    """URI에서 엔티티 ID 추출"""
    try:
        # ns_legacy와 ns 모두 확인
        ns_legacy_str = "http://coa-agent-platform.org/ontology#"
        ns_new_str = "http://defense-ai.kr/ontology#"
        ns_str = str(ns) if ns else ""
        
        # ns_legacy로 시작하는 경우
        if uri.startswith(ns_legacy_str):
            return uri.replace(ns_legacy_str, "")
        # ns_new로 시작하는 경우
        if uri.startswith(ns_new_str):
            return uri.replace(ns_new_str, "")
        # ns로 시작하는 경우
        if ns_str and uri.startswith(ns_str):
            return uri.replace(ns_str, "")
        # # 기호로 분리된 경우
        if '#' in uri:
            return uri.split('#')[-1]
        # / 기호로 분리된 경우
        if '/' in uri:
            return uri.split('/')[-1]
        return None
    except:
        return None


def _get_namespace(ontology_manager) -> Namespace:
    """온톨로지 매니저에서 올바른 네임스페이스 가져오기 (ns_legacy 우선)"""
    if hasattr(ontology_manager, 'ns_legacy') and ontology_manager.ns_legacy:
        return ontology_manager.ns_legacy
    return ontology_manager.ns


def get_entity_type(graph: Graph, ns: Namespace, entity_id: str) -> Optional[str]:
    """엔티티의 타입 가져오기"""
    try:
        # ns_legacy와 ns 모두 시도
        entity_uri = None
        try:
            entity_uri = URIRef(ns[entity_id])
        except Exception:
            # ns_legacy 시도
            ns_legacy = Namespace("http://coa-agent-platform.org/ontology#")
            try:
                entity_uri = URIRef(ns_legacy[entity_id])
            except Exception:
                pass
        
        if entity_uri:
            # rdf:type 관계 찾기
            for s, p, o in graph.triples((entity_uri, RDF.type, None)):
                type_str = str(o)
                # 타입에서 로컬 이름 추출
                if '#' in type_str:
                    return type_str.split('#')[-1]
                if '/' in type_str:
                    return type_str.split('/')[-1]
                return type_str
        
        # 타입을 찾지 못한 경우, 엔티티 ID에서 추정
        if entity_id.startswith("THREAT") or entity_id.startswith("위협"):
            return "위협상황"
        elif entity_id.startswith("COA") or entity_id.startswith("방책"):
            return "방책"
        elif entity_id.startswith("ASSET") or entity_id.startswith("자산"):
            return "자산"
        elif entity_id.startswith("RES") or entity_id.startswith("자원"):
            return "자원"
        elif entity_id.startswith("WX") or entity_id.startswith("기상"):
            return "기상상황"
        elif entity_id.startswith("지형셀") or "지형" in entity_id:
            return "지형셀"
        elif entity_id.startswith("임무정보") or "임무" in entity_id:
            return "임무정보"
        elif entity_id.startswith("전장축선") or "축선" in entity_id:
            return "전장축선"
        elif entity_id.startswith("아군부대") or "아군" in entity_id:
            return "아군부대현황"
        elif entity_id.startswith("적군부대") or "적군" in entity_id:
            return "적군부대현황"
        elif entity_id.startswith("제약조건") or "제약" in entity_id:
            return "제약조건"
        
        return "알 수 없음"
    except:
        return "알 수 없음"


def get_entity_type_label(graph: Graph, ns: Namespace, entity_id: str) -> str:
    """엔티티 타입 라벨 가져오기 (간단한 버전)"""
    entity_type = get_entity_type(graph, ns, entity_id)
    if entity_type:
        # 한글 타입명을 간단하게 표시
        if "위협" in entity_type:
            return "위협"
        elif "방책" in entity_type or "COA" in entity_type:
            return "방책"
        elif "자산" in entity_type or "ASSET" in entity_type:
            return "자산"
        elif "자원" in entity_type or "RES" in entity_type:
            return "자원"
        elif "기상" in entity_type or "WX" in entity_type:
            return "기상"
        return entity_type[:10]  # 최대 10자
    return "알 수 없음"


def group_entities_by_type(graph: Graph, ns: Namespace, entities: List[str]) -> Dict[str, List[str]]:
    """엔티티를 타입별로 그룹화"""
    groups = {}
    
    for entity_id in entities:
        entity_type = get_entity_type(graph, ns, entity_id)
        if entity_type not in groups:
            groups[entity_type] = []
        groups[entity_type].append(entity_id)
    
    # 타입별로 정렬
    for entity_type in groups:
        groups[entity_type].sort()
    
    # 타입명으로 정렬
    return dict(sorted(groups.items()))


def search_entities(graph: Graph, ns: Namespace, search_term: str) -> List[tuple]:
    """엔티티 검색"""
    search_term_lower = search_term.lower()
    all_entities = get_all_entities(graph, ns)
    matching = []
    
    for entity_id in all_entities:
        # ID로 검색
        if search_term_lower in entity_id.lower():
            entity_type = get_entity_type_label(graph, ns, entity_id)
            matching.append((entity_id, entity_type))
        else:
            # 타입으로도 검색
            entity_type = get_entity_type(graph, ns, entity_id)
            if entity_type and search_term_lower in entity_type.lower():
                entity_type_label = get_entity_type_label(graph, ns, entity_id)
                matching.append((entity_id, entity_type_label))
    
    return matching


def render_relation_summary(ontology_manager):
    """온톨로지 관계 요약 표시"""
    if ontology_manager is None or ontology_manager.graph is None:
        return
    
    graph = ontology_manager.graph
    
    # 전체 관계 통계
    total_triples = len(list(graph.triples((None, None, None))))
    
    # 관계 타입별 통계
    relation_types = {}
    for s, p, o in graph.triples((None, None, None)):
        predicate = str(p).split('#')[-1] if '#' in str(p) else str(p)
        relation_types[predicate] = relation_types.get(predicate, 0) + 1
    
    st.markdown("#### 📊 온톨로지 관계 통계")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("전체 트리플 수", total_triples)
    with col2:
        st.metric("관계 타입 수", len(relation_types))
    
    # 관계 타입별 상세
    if relation_types:
        st.markdown("**관계 타입별 통계:**")
        for rel_type, count in sorted(relation_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            st.write(f"- {rel_type}: {count}개")


