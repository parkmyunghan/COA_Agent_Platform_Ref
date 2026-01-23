# ui/components/graph_analysis_panel.py
# -*- coding: utf-8 -*-
"""
그래프 분석 및 해석 패널
지식그래프의 구조, 품질, 개선점을 분석하고 제안
"""
import streamlit as st
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter, deque
import pandas as pd
import math

try:
    from rdflib import Graph, URIRef, RDF, RDFS, OWL, Namespace
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False


def render_graph_analysis(core, graph_data: Dict, graph_mode: str):
    """
    그래프 분석 및 해석 패널 렌더링
    
    Args:
        core: CorePipeline 인스턴스
        graph_data: 그래프 데이터 {"instances": {...}, "schema": {...}}
        graph_mode: "인스턴스 그래프 (ABox)" 또는 "스키마 그래프 (TBox)"
    """
    st.markdown("---")
    st.markdown("### 📊 그래프 분석 및 해석")
    
    use_instances = graph_mode == "인스턴스 그래프 (ABox)"
    data = graph_data["instances"] if use_instances else graph_data["schema"]
    
    # 탭으로 분석 기능 분리
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 구조 분석",
        "🔍 누락 관계 탐지",
        "✅ 품질 평가",
        "💡 개선 제안"
    ])
    
    with tab1:
        _render_structure_analysis(data, use_instances)
    
    with tab2:
        if use_instances:
            _render_missing_relations_analysis(core, graph_data)
        else:
            st.info("스키마 그래프에서는 누락 관계 탐지가 지원되지 않습니다.")
    
    with tab3:
        _render_quality_assessment(core, graph_data, use_instances)
    
    with tab4:
        _render_improvement_suggestions(core, graph_data, use_instances)


def _render_structure_analysis(data: Dict, is_instance: bool):
    """그래프 구조 분석"""
    st.markdown("#### 📈 그래프 구조 분석")
    
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    
    if not nodes:
        st.warning("분석할 노드가 없습니다.")
        return
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 노드 수", len(nodes))
    with col2:
        st.metric("총 관계 수", len(links))
    with col3:
        # 평균 연결도 계산
        node_degree = defaultdict(int)
        for link in links:
            node_degree[link.get("source")] += 1
            node_degree[link.get("target")] += 1
        avg_degree = sum(node_degree.values()) / len(nodes) if nodes else 0
        st.metric("평균 연결도", f"{avg_degree:.2f}")
    with col4:
        # 그룹 수
        groups = set(n.get("group", "") for n in nodes)
        st.metric("그룹 수", len(groups))
    
    st.divider()
    
    # 노드별 연결도 분석
    st.markdown("##### 🔗 노드 연결도 분석")
    node_degree = defaultdict(int)
    for link in links:
        node_degree[link.get("source")] += 1
        node_degree[link.get("target")] += 1
    
    # 연결도가 높은 노드 (허브 노드)
    if node_degree:
        sorted_nodes = sorted(node_degree.items(), key=lambda x: x[1], reverse=True)
        st.markdown("**연결도가 높은 노드 (Top 10)**")
        hub_data = []
        for node_id, degree in sorted_nodes[:10]:
            node = next((n for n in nodes if n.get("id") == node_id), None)
            if node:
                hub_data.append({
                    "노드": node.get("label", node_id),
                    "그룹": node.get("group", ""),
                    "연결도": degree
                })
        
        if hub_data:
            st.dataframe(pd.DataFrame(hub_data), width='stretch')
    
    # 고립된 노드 (연결도가 0인 노드)
    isolated_nodes = [n for n in nodes if node_degree.get(n.get("id"), 0) == 0]
    if isolated_nodes:
        st.warning(f"⚠️ 고립된 노드 {len(isolated_nodes)}개 발견")
        with st.expander("고립된 노드 목록 보기"):
            isolated_data = []
            for node in isolated_nodes[:20]:  # 최대 20개만 표시
                isolated_data.append({
                    "노드": node.get("label", node.get("id")),
                    "그룹": node.get("group", "")
                })
            if isolated_data:
                st.dataframe(pd.DataFrame(isolated_data), width='stretch')
            if len(isolated_nodes) > 20:
                st.caption(f"... 외 {len(isolated_nodes) - 20}개")
    
    # 관계 유형 분석
    st.divider()
    st.markdown("##### 🔗 관계 유형 분석")
    relation_types = Counter(link.get("relation", "Unknown") for link in links)
    if relation_types:
        st.markdown("**가장 많이 사용되는 관계 유형 (Top 10)**")
        rel_data = []
        for rel_type, count in relation_types.most_common(10):
            rel_data.append({
                "관계 유형": rel_type,
                "사용 횟수": count,
                "비율": f"{count / len(links) * 100:.1f}%"
            })
        st.dataframe(pd.DataFrame(rel_data), width='stretch')
    
    # 그룹별 분포
    st.divider()
    st.markdown("##### 📊 그룹별 노드 분포")
    group_counts = Counter(n.get("group", "Unknown") for n in nodes)
    if group_counts:
        group_data = []
        for group, count in group_counts.most_common():
            group_data.append({
                "그룹": group,
                "노드 수": count,
                "비율": f"{count / len(nodes) * 100:.1f}%"
            })
        st.dataframe(pd.DataFrame(group_data), width='stretch')


def _render_missing_relations_analysis(core, graph_data: Dict):
    """누락된 관계 탐지"""
    st.markdown("#### 🔍 누락된 관계 탐지")
    
    if not RDFLIB_AVAILABLE or not core.ontology_manager or not core.ontology_manager.graph:
        st.warning("온톨로지 그래프가 없어 분석할 수 없습니다.")
        return
    
    graph = core.ontology_manager.graph
    instances = graph_data.get("instances", {})
    nodes = instances.get("nodes", [])
    links = instances.get("links", [])
    
    if not nodes:
        st.warning("분석할 노드가 없습니다.")
        return
    
    # 기존 관계 맵 생성
    existing_relations = defaultdict(set)
    for link in links:
        source = link.get("source")
        target = link.get("target")
        relation = link.get("relation", "")
        if source and target:
            existing_relations[source].add((target, relation))
    
    # 누락된 관계 탐지
    st.markdown("##### 🔗 잠재적 관계 분석")
    
    # 1. 외래키 기반 누락 관계 탐지
    missing_fk_relations = _detect_missing_fk_relations(core, graph, nodes, existing_relations)
    
    if missing_fk_relations:
        st.markdown("**외래키 기반 누락 관계**")
        st.info(f"외래키 컬럼이 있지만 관계가 설정되지 않은 경우 {len(missing_fk_relations)}건 발견")
        with st.expander("누락된 관계 목록 보기"):
            fk_data = []
            for item in missing_fk_relations[:20]:  # 최대 20개
                fk_data.append({
                    "소스 노드": item.get("source_label", item.get("source")),
                    "타겟 노드": item.get("target_label", item.get("target")),
                    "제안 관계": item.get("relation", ""),
                    "신뢰도": f"{item.get('confidence', 0):.2f}"
                })
            if fk_data:
                st.dataframe(pd.DataFrame(fk_data), width='stretch')
            if len(missing_fk_relations) > 20:
                st.caption(f"... 외 {len(missing_fk_relations) - 20}건")
    else:
        st.success("✅ 외래키 기반 누락 관계가 없습니다.")
    
    # 2. 유사성 기반 관계 제안
    st.divider()
    
    # 방법 선택
    similarity_method = st.radio(
        "유사성 분석 방법",
        ["기본 (그룹 기반)", "구조적 유사성 (권장)", "하이브리드 (LLM 검증)"],
        horizontal=True,
        help="기본: 같은 그룹 내 노드 쌍 제안\n구조적 유사성: 그래프 구조 기반 유사도 계산\n하이브리드: 구조적 유사성 + LLM 검증"
    )
    
    with st.spinner("유사성 분석 중..."):
        if similarity_method == "기본 (그룹 기반)":
            similarity_relations = _suggest_similarity_based_relations(nodes, links, existing_relations)
        elif similarity_method == "구조적 유사성 (권장)":
            similarity_relations = _suggest_similarity_based_relations_structural(
                nodes, links, existing_relations, max_suggestions=20
            )
        else:  # 하이브리드
            similarity_relations = _suggest_similarity_based_relations_hybrid(
                core, nodes, links, existing_relations, use_llm=True, max_suggestions=20
            )
    
    if similarity_relations:
        st.markdown("**유사성 기반 관계 제안**")
        st.info(f"유사한 속성을 가진 노드 간 잠재적 관계 {len(similarity_relations)}건 제안")
        
        with st.expander("제안된 관계 목록 보기", expanded=True):
            # 선택된 관계를 저장할 세션 상태 초기화
            if "selected_relations" not in st.session_state:
                st.session_state.selected_relations = set()
            
            # 표 데이터 준비
            sim_data = []
            selected_indices = []
            
            for idx, item in enumerate(similarity_relations[:20]):  # 최대 20개
                # 세션 상태에서 선택 여부 확인
                is_selected = idx in st.session_state.selected_relations
                
                row = {
                    "선택": "✓" if is_selected else "",
                    "노드 1": item.get("node1_label", item.get("node1")),
                    "노드 2": item.get("node2_label", item.get("node2")),
                    "제안 관계": item.get("relation", "relatedTo"),
                    "유사도": f"{item.get('similarity', 0):.2f}"
                }
                
                # 구조적 유사성 방법인 경우 추가 정보 표시
                if similarity_method == "구조적 유사성 (권장)":
                    if item.get('common_neighbors') is not None:
                        row["공통 이웃"] = item.get('common_neighbors', 0)
                    if item.get('path_length') is not None:
                        row["경로 길이"] = item.get('path_length', 'N/A')
                
                # 하이브리드 방법인 경우 LLM 검증 여부 표시
                if similarity_method == "하이브리드 (LLM 검증)":
                    row["LLM 검증"] = "✓" if item.get('llm_validated', False) else "-"
                
                sim_data.append(row)
                if is_selected:
                    selected_indices.append(idx)
            
            # 표 표시
            if sim_data:
                df = pd.DataFrame(sim_data)
                st.dataframe(df, width="stretch", hide_index=True)
            
            st.divider()
            
            # 각 행에 대한 체크박스 (표 아래에 그리드 형태로 배치)
            st.markdown("**관계 선택 (표의 행 번호와 일치):**")
            num_cols = 5
            num_items = len(similarity_relations[:20])
            num_rows = (num_items + num_cols - 1) // num_cols
            
            for row_idx in range(num_rows):
                cols = st.columns(num_cols)
                for col_idx in range(num_cols):
                    idx = row_idx * num_cols + col_idx
                    if idx < num_items:
                        with cols[col_idx]:
                            item = similarity_relations[idx]
                            # 짧은 라벨 생성
                            node1_label = item.get('node1_label', item.get('node1', ''))[:12]
                            checkbox_label = f"#{idx+1}: {node1_label}..."
                            
                            is_selected = st.checkbox(
                                checkbox_label,
                                value=idx in st.session_state.selected_relations,
                                key=f"relation_select_{idx}"
                            )
                            
                            if is_selected:
                                st.session_state.selected_relations.add(idx)
                                if idx not in selected_indices:
                                    selected_indices.append(idx)
                            else:
                                st.session_state.selected_relations.discard(idx)
                                if idx in selected_indices:
                                    selected_indices.remove(idx)
            
            if len(similarity_relations) > 20:
                st.caption(f"... 외 {len(similarity_relations) - 20}건")
            
            st.divider()
            
            # 선택된 관계 추가 버튼
            # 세션 상태에서 선택된 항목 다시 읽기
            current_selected = list(st.session_state.selected_relations)
            
            if current_selected:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("✅ 선택된 관계 추가", type="primary"):
                        with st.spinner("관계 추가 중..."):
                            try:
                                relationships_to_add = []
                                for idx in current_selected:
                                    if idx < len(similarity_relations):
                                        item = similarity_relations[idx]
                                        relationships_to_add.append({
                                            "source": item.get("node1"),
                                            "target": item.get("node2"),
                                            "relation": item.get("relation", "relatedTo")
                                        })
                                
                                # 그래프에 관계 추가
                                if hasattr(core, 'ontology_manager') and core.ontology_manager:
                                    result = core.ontology_manager.add_relationships_batch(relationships_to_add)
                                    
                                    if result["success"] > 0:
                                        # 그래프 저장
                                        core.ontology_manager.save_graph()
                                        
                                        st.success(f"✅ {result['success']}개 관계가 추가되었습니다.")
                                        if result["failed"] > 0:
                                            st.warning(f"⚠️ {result['failed']}개 관계 추가 실패")
                                        
                                        # 선택 초기화
                                        st.session_state.selected_relations = set()
                                        
                                        # 그래프 새로고침
                                        st.rerun()
                                    else:
                                        st.error("관계 추가 실패")
                                else:
                                    st.error("Ontology Manager를 사용할 수 없습니다.")
                            except Exception as e:
                                st.error(f"관계 추가 중 오류: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                
                with col2:
                    if st.button("🔄 선택 초기화"):
                        st.session_state.selected_relations = set()
                        st.rerun()
    else:
        st.info("유사성 기반 관계 제안이 없습니다.")


def _detect_missing_fk_relations(core, graph: Graph, nodes: List[Dict], 
                                 existing_relations: Dict) -> List[Dict]:
    """외래키 기반 누락 관계 탐지"""
    missing_relations = []
    
    if not hasattr(core, 'data_manager') or not core.data_manager:
        return missing_relations
    
    try:
        # 데이터 로드
        data = core.data_manager.load_all()
        
        # 관계 매핑 로드 (Enhanced Ontology Manager가 있으면)
        relation_mappings = []
        if hasattr(core, 'enhanced_ontology_manager') and core.enhanced_ontology_manager:
            relation_mappings = core.enhanced_ontology_manager.load_relation_mappings()
        
        # 각 노드에 대해 외래키 확인
        for node in nodes[:50]:  # 성능을 위해 최대 50개만 확인
            node_id = node.get("id", "")
            node_label = node.get("label", node_id)
            node_group = node.get("group", "")
            
            # 노드 ID에서 테이블명과 행 ID 추출
            if "_" in node_id:
                parts = node_id.split("_", 1)
                if len(parts) == 2:
                    table_name = parts[0]
                    row_id = parts[1]
                    
                    # 해당 테이블의 데이터 확인
                    if table_name in data:
                        df = data[table_name]
                        # ID 컬럼 찾기
                        id_col = None
                        for col in df.columns:
                            if col.upper() == 'ID' or col.endswith('ID') or col.endswith('_id'):
                                id_col = col
                                break
                        
                        if id_col:
                            # 해당 행 찾기
                            matching_rows = df[df[id_col].astype(str).str.strip() == row_id]
                            if not matching_rows.empty:
                                row = matching_rows.iloc[0]
                                
                                # 관계 매핑 확인
                                for rel_map in relation_mappings:
                                    if rel_map.get('src_table') == table_name:
                                        src_col = rel_map.get('src_col')
                                        if src_col and src_col in row:
                                            fk_val = str(row[src_col]).strip()
                                            if fk_val and fk_val != 'nan':
                                                tgt_table = rel_map.get('tgt_table')
                                                relation_name = rel_map.get('relation', f"has{tgt_table}")
                                                
                                                # 타겟 노드 찾기
                                                target_node_id = f"{tgt_table}_{fk_val}"
                                                
                                                # 이미 관계가 있는지 확인
                                                if target_node_id not in [r[0] for r in existing_relations.get(node_id, set())]:
                                                    missing_relations.append({
                                                        "source": node_id,
                                                        "source_label": node_label,
                                                        "target": target_node_id,
                                                        "target_label": f"{tgt_table}_{fk_val}",
                                                        "relation": relation_name,
                                                        "confidence": 0.9  # 외래키 기반이므로 높은 신뢰도
                                                    })
    except Exception as e:
        st.warning(f"누락 관계 탐지 중 오류: {e}")
    
    return missing_relations


def _find_shortest_path(neighbors_map: Dict, start: str, end: str, max_depth: int = 3) -> Optional[List[str]]:
    """BFS로 최단 경로 찾기"""
    if start == end:
        return [start]
    
    queue = deque([(start, [start])])
    visited = {start}
    
    while queue and len(queue[0][1]) <= max_depth:
        current, path = queue.popleft()
        
        for neighbor in neighbors_map.get(current, set()):
            if neighbor == end:
                return path + [neighbor]
            
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    
    return None


def _suggest_similarity_based_relations_structural(
    nodes: List[Dict], 
    links: List[Dict],
    existing_relations: Dict,
    max_suggestions: int = 20
) -> List[Dict]:
    """
    구조적 유사성 기반 관계 제안 (Palantir 스타일)
    
    방법:
    1. 공통 이웃 (Common Neighbors): 두 노드가 공유하는 이웃 노드 수
    2. Jaccard 유사도: 공통 이웃 / 전체 이웃
    3. Adamic-Adar 점수: 공통 이웃의 연결도 역가중
    4. 경로 기반 유사도: 최단 경로 거리
    """
    suggestions = []
    
    # 노드별 이웃 맵 구성
    neighbors_map = defaultdict(set)
    for link in links:
        source = link.get("source", "")
        target = link.get("target", "")
        if source and target:
            neighbors_map[source].add(target)
            neighbors_map[target].add(source)
    
    # 노드 쌍별 유사도 계산
    node_pairs = []
    for i, node1 in enumerate(nodes):
        for node2 in nodes[i+1:]:
            node1_id = node1.get("id")
            node2_id = node2.get("id")
            
            # 이미 관계가 있는지 확인
            has_relation = False
            if node1_id in existing_relations:
                if any(target == node2_id for target, _ in existing_relations[node1_id]):
                    has_relation = True
            
            if has_relation:
                continue
            
            # 공통 이웃 계산
            neighbors1 = neighbors_map.get(node1_id, set())
            neighbors2 = neighbors_map.get(node2_id, set())
            common_neighbors = neighbors1 & neighbors2
            
            # 유사도 점수 계산
            similarity_scores = {}
            
            # 1. 공통 이웃 수
            similarity_scores['common_neighbors'] = len(common_neighbors)
            
            # 2. Jaccard 유사도
            union_neighbors = neighbors1 | neighbors2
            if union_neighbors:
                similarity_scores['jaccard'] = len(common_neighbors) / len(union_neighbors)
            else:
                similarity_scores['jaccard'] = 0.0
            
            # 3. Adamic-Adar 점수 (공통 이웃의 연결도 역가중)
            adamic_adar = 0.0
            for neighbor in common_neighbors:
                neighbor_degree = len(neighbors_map.get(neighbor, set()))
                if neighbor_degree > 1:
                    adamic_adar += 1.0 / math.log(neighbor_degree)
            similarity_scores['adamic_adar'] = adamic_adar
            
            # 4. 최단 경로 거리 (BFS)
            shortest_path = _find_shortest_path(neighbors_map, node1_id, node2_id, max_depth=3)
            if shortest_path:
                similarity_scores['path_similarity'] = 1.0 / (len(shortest_path) + 1)
            else:
                similarity_scores['path_similarity'] = 0.0
            
            # 종합 점수 (가중 평균)
            final_score = (
                similarity_scores['jaccard'] * 0.4 +
                min(similarity_scores['adamic_adar'] / 10.0, 1.0) * 0.3 +
                similarity_scores['path_similarity'] * 0.3
            )
            
            if final_score > 0.1:  # 임계값 이상인 경우만 제안
                node_pairs.append({
                    "node1": node1_id,
                    "node1_label": node1.get("label", node1_id),
                    "node2": node2_id,
                    "node2_label": node2.get("label", node2_id),
                    "similarity": final_score,
                    "common_neighbors": len(common_neighbors),
                    "jaccard": similarity_scores['jaccard'],
                    "adamic_adar": similarity_scores['adamic_adar'],
                    "path_length": len(shortest_path) if shortest_path else None,
                    "relation": "relatedTo"  # 기본 관계명
                })
    
    # 유사도 순으로 정렬
    node_pairs.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return node_pairs[:max_suggestions]


def _suggest_similarity_based_relations_hybrid(
    core,
    nodes: List[Dict], 
    links: List[Dict],
    existing_relations: Dict,
    use_llm: bool = True,
    max_suggestions: int = 20
) -> List[Dict]:
    """
    하이브리드 접근: 구조적 유사성 + LLM 검증 (Palantir 스타일)
    
    방법:
    1. 구조적 유사성으로 후보 선정
    2. LLM으로 상위 제안 검증 및 관계명 제안
    """
    # 1. 구조적 유사성 기반 제안
    structural_suggestions = _suggest_similarity_based_relations_structural(
        nodes, links, existing_relations, max_suggestions * 2
    )
    
    if not structural_suggestions:
        return []
    
    # 2. LLM으로 상위 제안 검증 및 관계명 제안 (선택적)
    if use_llm and core and hasattr(core, 'llm_manager') and core.llm_manager and core.llm_manager.is_available():
        # 상위 10개만 LLM으로 검증 (성능 최적화)
        top_suggestions = structural_suggestions[:10]
        
        for suggestion in top_suggestions:
            # LLM으로 관계명 제안
            prompt = f"""다음 두 노드 간의 관계를 분석하세요.

노드 1: {suggestion['node1_label']} (ID: {suggestion['node1']})
노드 2: {suggestion['node2_label']} (ID: {suggestion['node2']})
구조적 유사도: {suggestion.get('similarity', 0):.2f}
공통 이웃: {suggestion.get('common_neighbors', 0)}개

이 두 노드 간에 의미 있는 관계가 있다면 관계명을 제안하세요. 없으면 "없음"이라고 답하세요.
관계명만 간단히 답하세요 (예: relatedTo, partOf, locatedIn, hasMission 등)"""
            
            try:
                response = core.llm_manager.generate(prompt, max_tokens=20)
                relation_name = response.strip()
                if relation_name and relation_name != "없음" and len(relation_name) < 50:
                    suggestion['relation'] = relation_name
                    suggestion['llm_validated'] = True
                else:
                    suggestion['llm_validated'] = False
            except Exception as e:
                suggestion['llm_validated'] = False
                st.warning(f"LLM 검증 실패: {e}")
    else:
        # LLM 없으면 모두 검증되지 않음으로 표시
        for suggestion in structural_suggestions:
            suggestion['llm_validated'] = False
    
    # LLM 검증된 것 우선, 그 다음 유사도 순
    validated = [s for s in structural_suggestions if s.get('llm_validated', False)]
    not_validated = [s for s in structural_suggestions if not s.get('llm_validated', False)]
    
    final_suggestions = validated + not_validated
    return final_suggestions[:max_suggestions]


def _suggest_similarity_based_relations(nodes: List[Dict], links: List[Dict],
                                       existing_relations: Dict) -> List[Dict]:
    """유사성 기반 관계 제안 (기본 방법: 그룹 기반)"""
    suggestions = []
    
    # 간단한 유사성 기반 제안 (그룹이 같고 연결이 없는 경우)
    node_by_group = defaultdict(list)
    for node in nodes:
        group = node.get("group", "")
        if group:
            node_by_group[group].append(node)
    
    # 같은 그룹 내에서 연결이 없는 노드 쌍 찾기
    for group, group_nodes in node_by_group.items():
        if len(group_nodes) >= 2:
            # 이미 연결된 노드 쌍 제외
            for i, node1 in enumerate(group_nodes[:10]):  # 성능 제한
                for node2 in group_nodes[i+1:11]:
                    node1_id = node1.get("id")
                    node2_id = node2.get("id")
                    
                    # 이미 관계가 있는지 확인
                    has_relation = False
                    if node1_id in existing_relations:
                        if any(target == node2_id for target, _ in existing_relations[node1_id]):
                            has_relation = True
                    
                    if not has_relation:
                        suggestions.append({
                            "node1": node1_id,
                            "node1_label": node1.get("label", node1_id),
                            "node2": node2_id,
                            "node2_label": node2.get("label", node2_id),
                            "relation": "relatedTo",
                            "similarity": 0.5  # 기본 유사도
                        })
    
    return suggestions[:50]  # 최대 50개만 반환


def _render_quality_assessment(core, graph_data: Dict, is_instance: bool):
    """품질 평가"""
    st.markdown("#### ✅ 그래프 품질 평가")
    
    if is_instance:
        _assess_instance_quality(core, graph_data)
    else:
        _assess_schema_quality(core, graph_data)


def _assess_instance_quality(core, graph_data: Dict):
    """인스턴스 그래프 품질 평가"""
    instances = graph_data.get("instances", {})
    nodes = instances.get("nodes", [])
    links = instances.get("links", [])
    
    quality_scores = {}
    issues = []
    
    # 1. 연결성 평가
    node_degree = defaultdict(int)
    for link in links:
        node_degree[link.get("source")] += 1
        node_degree[link.get("target")] += 1
    
    isolated_count = sum(1 for n in nodes if node_degree.get(n.get("id"), 0) == 0)
    connectivity_score = 1.0 - (isolated_count / len(nodes)) if nodes else 0.0
    quality_scores["연결성"] = connectivity_score
    
    if isolated_count > 0:
        issues.append({
            "항목": "연결성",
            "문제": f"고립된 노드 {isolated_count}개 발견",
            "심각도": "중간" if isolated_count < len(nodes) * 0.1 else "높음",
            "권장 조치": "외래키 관계를 확인하고 누락된 관계를 추가하세요"
        })
    
    # 2. 관계 밀도 평가
    if nodes:
        max_possible_links = len(nodes) * (len(nodes) - 1) / 2
        actual_density = len(links) / max_possible_links if max_possible_links > 0 else 0
        quality_scores["관계 밀도"] = min(actual_density * 10, 1.0)  # 정규화
    
    # 3. 그룹 분포 평가
    groups = set(n.get("group", "") for n in nodes)
    if groups:
        group_distribution = Counter(n.get("group", "") for n in nodes)
        max_group_count = max(group_distribution.values())
        min_group_count = min(group_distribution.values())
        balance_score = min_group_count / max_group_count if max_group_count > 0 else 0
        quality_scores["그룹 균형"] = balance_score
        
        if balance_score < 0.1:
            issues.append({
                "항목": "그룹 균형",
                "문제": "그룹 간 노드 수의 불균형이 큽니다",
                "심각도": "낮음",
                "권장 조치": "데이터 수집 시 그룹별 균형을 고려하세요"
            })
    
    # 품질 점수 표시
    st.markdown("##### 📊 품질 점수")
    cols = st.columns(len(quality_scores))
    for idx, (metric, score) in enumerate(quality_scores.items()):
        with cols[idx]:
            st.metric(metric, f"{score:.2f}")
    
    # 문제점 표시
    if issues:
        st.divider()
        st.markdown("##### ⚠️ 발견된 문제점")
        issues_df = pd.DataFrame(issues)
        st.dataframe(issues_df, width='stretch')
    else:
        st.success("✅ 심각한 품질 문제가 발견되지 않았습니다.")


def _assess_schema_quality(core, graph_data: Dict):
    """스키마 그래프 품질 평가"""
    schema = graph_data.get("schema", {})
    nodes = schema.get("nodes", [])
    links = schema.get("links", [])
    
    if not RDFLIB_AVAILABLE or not core.ontology_manager or not core.ontology_manager.graph:
        st.warning("온톨로지 그래프가 없어 스키마 품질을 평가할 수 없습니다.")
        return
    
    graph = core.ontology_manager.graph
    quality_scores = {}
    issues = []
    
    # 1. 클래스 정의 완성도
    classes = [n for n in nodes if n.get("group") == "Class"]
    properties = [n for n in nodes if n.get("group") == "Property"]
    
    quality_scores["클래스 수"] = len(classes)
    quality_scores["속성 수"] = len(properties)
    
    # 2. Domain/Range 정의 확인
    domain_links = [l for l in links if l.get("relation") == "domain"]
    range_links = [l for l in links if l.get("relation") == "range"]
    
    if properties:
        domain_completeness = len(domain_links) / len(properties)
        range_completeness = len(range_links) / len(properties)
        quality_scores["Domain 정의율"] = domain_completeness
        quality_scores["Range 정의율"] = range_completeness
        
        if domain_completeness < 0.8:
            issues.append({
                "항목": "Domain 정의",
                "문제": f"속성의 {int((1-domain_completeness)*100)}%가 domain이 정의되지 않았습니다",
                "심각도": "중간",
                "권장 조치": "속성에 domain을 명시하여 스키마를 완성하세요"
            })
        
        if range_completeness < 0.8:
            issues.append({
                "항목": "Range 정의",
                "문제": f"속성의 {int((1-range_completeness)*100)}%가 range가 정의되지 않았습니다",
                "심각도": "중간",
                "권장 조치": "속성에 range를 명시하여 스키마를 완성하세요"
            })
    
    # 3. 계층 구조 확인
    subclass_links = [l for l in links if l.get("relation") == "subClassOf"]
    if classes:
        hierarchy_score = len(subclass_links) / len(classes) if classes else 0
        quality_scores["계층 구조 완성도"] = min(hierarchy_score, 1.0)
    
    # 품질 점수 표시
    st.markdown("##### 📊 스키마 품질 점수")
    cols = st.columns(len(quality_scores))
    for idx, (metric, score) in enumerate(quality_scores.items()):
        with cols[idx]:
            if isinstance(score, float):
                st.metric(metric, f"{score:.2f}")
            else:
                st.metric(metric, score)
    
    # 문제점 표시
    if issues:
        st.divider()
        st.markdown("##### ⚠️ 발견된 문제점")
        issues_df = pd.DataFrame(issues)
        st.dataframe(issues_df, width='stretch')
    else:
        st.success("✅ 스키마 품질이 양호합니다.")


def _render_improvement_suggestions(core, graph_data: Dict, is_instance: bool):
    """개선 제안"""
    st.markdown("#### 💡 개선 제안")
    
    suggestions = []
    
    if is_instance:
        # 인스턴스 그래프 개선 제안
        instances = graph_data.get("instances", {})
        nodes = instances.get("nodes", [])
        links = instances.get("links", [])
        
        # 고립된 노드가 많으면
        node_degree = defaultdict(int)
        for link in links:
            node_degree[link.get("source")] += 1
            node_degree[link.get("target")] += 1
        
        isolated_count = sum(1 for n in nodes if node_degree.get(n.get("id"), 0) == 0)
        if isolated_count > len(nodes) * 0.1:
            suggestions.append({
                "우선순위": "높음",
                "제안": "고립된 노드 연결",
                "설명": f"전체 노드의 {isolated_count/len(nodes)*100:.1f}%가 고립되어 있습니다. 외래키 관계를 확인하고 누락된 관계를 추가하세요.",
                "실행 방법": "관계 매핑 파일(metadata/relation_mappings.json)을 확인하고 필요한 관계를 추가하세요. 편집 가이드는 metadata/RELATION_MAPPINGS_GUIDE.md를 참조하세요."
            })
        
        # 관계 밀도가 낮으면
        if nodes:
            max_possible = len(nodes) * (len(nodes) - 1) / 2
            actual_density = len(links) / max_possible if max_possible > 0 else 0
            if actual_density < 0.01:
                suggestions.append({
                    "우선순위": "중간",
                    "제안": "관계 밀도 향상",
                    "설명": f"현재 관계 밀도가 {actual_density*100:.2f}%로 매우 낮습니다. 더 많은 관계를 추가하면 그래프의 유용성이 향상됩니다.",
                    "실행 방법": "테이블정의서에서 FK 관계를 정의하면 자동으로 온톨로지 관계가 생성됩니다."
                })
    else:
        # 스키마 그래프 개선 제안
        schema = graph_data.get("schema", {})
        nodes = schema.get("nodes", [])
        links = schema.get("links", [])
        
        properties = [n for n in nodes if n.get("group") == "Property"]
        domain_links = [l for l in links if l.get("relation") == "domain"]
        range_links = [l for l in links if l.get("relation") == "range"]
        
        if properties:
            domain_completeness = len(domain_links) / len(properties)
            if domain_completeness < 0.8:
                suggestions.append({
                    "우선순위": "중간",
                    "제안": "Domain 정의 보완",
                    "설명": f"속성의 {int((1-domain_completeness)*100)}%가 domain이 정의되지 않았습니다.",
                    "실행 방법": "Enhanced Ontology Manager를 사용하면 자동으로 domain/range가 설정됩니다."
                })
            
            range_completeness = len(range_links) / len(properties)
            if range_completeness < 0.8:
                suggestions.append({
                    "우선순위": "중간",
                    "제안": "Range 정의 보완",
                    "설명": f"속성의 {int((1-range_completeness)*100)}%가 range가 정의되지 않았습니다.",
                    "실행 방법": "Enhanced Ontology Manager를 사용하면 자동으로 domain/range가 설정됩니다."
                })
    
    # 제안 표시
    if suggestions:
        for idx, suggestion in enumerate(suggestions, 1):
            priority_color = {
                "높음": "🔴",
                "중간": "🟡",
                "낮음": "🟢"
            }.get(suggestion.get("우선순위", ""), "⚪")
            
            with st.expander(f"{priority_color} [{suggestion.get('우선순위', '')}] {suggestion.get('제안', '')}"):
                st.markdown(f"**설명:** {suggestion.get('설명', '')}")
                st.markdown(f"**실행 방법:** {suggestion.get('실행 방법', '')}")
    else:
        st.success("✅ 현재 그래프 상태가 양호합니다. 특별한 개선 제안이 없습니다.")

