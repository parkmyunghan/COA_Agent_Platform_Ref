# ui/components/node_info_panel.py
# -*- coding: utf-8 -*-
"""
노드 정보 패널 컴포넌트
지식그래프 노드 클릭 시 상세 정보 표시
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


def render_node_info_panel(core, node_id: str, node_label: str):
    """
    노드 정보 패널 표시
    
    Args:
        core: CorePipeline 인스턴스
        node_id: 노드 URI 또는 ID
        node_label: 노드 레이블
    """
    if not node_id or not node_label:
        st.info("노드를 선택하세요.")
        return
    
    st.subheader(f"노드 정보: {node_label}")
    
    graph = core.ontology_manager.graph
    if graph is None:
        st.warning("그래프가 생성되지 않았습니다.")
        return
    
    # 노드 URI 정규화
    node_uri = _normalize_node_uri(node_id, core.ontology_manager.ns)
    
    # 탭으로 정보 구분
    tab1, tab2, tab3, tab4 = st.tabs(["📊 기본 정보", "🔗 관계", "📄 관련 문서", "🔍 SPARQL 쿼리"])
    
    with tab1:
        _render_basic_info(core, node_uri, node_label)
    
    with tab2:
        _render_relationships(core, node_uri, node_label)
    
    with tab3:
        _render_related_documents(core, node_label)
    
    with tab4:
        _render_sparql_info(core, node_uri, node_label)


def _normalize_node_uri(node_id: str, ns) -> str:
    """노드 URI 정규화"""
    if node_id.startswith('http://'):
        return node_id
    elif '#' in node_id:
        return node_id
    else:
        # 로컬 이름만 있는 경우 네임스페이스 추가
        return f"{ns}{node_id}"


def _render_basic_info(core, node_uri: str, node_label: str):
    """기본 정보 표시"""
    graph = core.ontology_manager.graph
    
    # 노드의 모든 속성 조회
    query = f"""
    PREFIX def: <http://defense-ai.kr/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?predicate ?object ?object_label WHERE {{
        <{node_uri}> ?predicate ?object .
        OPTIONAL {{
            ?object rdfs:label ?object_label .
        }}
    }}
    ORDER BY ?predicate
    """
    
    try:
        from rdflib import URIRef, RDFS
        node_node = URIRef(node_uri)
        results = []
        for p, o in graph.predicate_objects(node_node):
            obj_label = ""
            if isinstance(o, URIRef):
                labels = list(graph.objects(o, RDFS.label))
                if labels: obj_label = str(labels[0])
            results.append({
                'predicate': str(p),
                'object': str(o),
                'object_label': obj_label
            })
        
        if results:
            # 결과를 DataFrame으로 변환
            df = pd.DataFrame(results)
            
            # predicate와 object를 읽기 쉽게 변환
            df['속성'] = df['predicate'].apply(lambda x: _extract_local_name(str(x)))
            df['값'] = df['object'].apply(lambda x: _format_object_value(str(x)))
            
            # 필요한 컬럼만 선택
            display_df = df[['속성', '값']].copy()
            
            # 값 컬럼을 문자열로 변환하여 Arrow 호환성 확보
            display_df['값'] = display_df['값'].astype(str)
            
            st.dataframe(display_df, width='stretch', hide_index=True)
            
            # 통계 정보
            col1, col2 = st.columns(2)
            with col1:
                st.metric("속성 수", len(display_df))
            with col2:
                st.metric("노드 URI", node_uri[:50] + "..." if len(node_uri) > 50 else node_uri)
        else:
            st.info("노드 속성 정보가 없습니다.")
            
    except Exception as e:
        st.error(f"노드 정보 조회 실패: {e}")


def _render_relationships(core, node_uri: str, node_label: str):
    """관계 정보 표시 및 관리"""
    graph = core.ontology_manager.graph
    
    # Incoming 관계 (다른 노드에서 이 노드로)
    incoming_query = f"""
    PREFIX def: <http://defense-ai.kr/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?source ?predicate ?source_label WHERE {{
        ?source ?predicate <{node_uri}> .
        OPTIONAL {{
            ?source rdfs:label ?source_label .
        }}
    }}
    LIMIT 50
    """
    
    # Outgoing 관계 (이 노드에서 다른 노드로)
    outgoing_query = f"""
    PREFIX def: <http://defense-ai.kr/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?predicate ?target ?target_label WHERE {{
        <{node_uri}> ?predicate ?target .
        FILTER (isIRI(?target))
        OPTIONAL {{
            ?target rdfs:label ?target_label .
        }}
    }}
    LIMIT 50
    """
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔽 Incoming (들어오는 관계)")
        try:
            from rdflib import URIRef, RDFS
            node_node = URIRef(node_uri)
            incoming_results = []
            for s, p, o in graph.triples((None, None, node_node)):
                if isinstance(s, URIRef):
                    labels = list(graph.objects(s, RDFS.label))
                    s_label = str(labels[0]) if labels else ""
                    incoming_results.append({
                        'source': str(s),
                        'predicate': str(p),
                        'source_label': s_label
                    })
            
            if incoming_results:
                df_in = pd.DataFrame(incoming_results)
                df_in['소스'] = df_in['source'].apply(lambda x: _extract_local_name(str(x)))
                df_in['관계'] = df_in['predicate'].apply(lambda x: _extract_local_name(str(x)))
                display_df_in = df_in[['소스', '관계']].copy()
                st.dataframe(display_df_in, width='stretch', hide_index=True)
                st.caption(f"총 {len(display_df_in)}개 관계")
            else:
                st.info("들어오는 관계가 없습니다.")
        except Exception as e:
            st.error(f"관계 조회 실패: {e}")
    
    with col2:
        st.markdown("#### 🔼 Outgoing (나가는 관계)")
        try:
            from rdflib import URIRef, RDFS
            node_node = URIRef(node_uri)
            outgoing_results = []
            for p, o in graph.predicate_objects(node_node):
                if isinstance(o, URIRef):
                    labels = list(graph.objects(o, RDFS.label))
                    o_label = str(labels[0]) if labels else ""
                    outgoing_results.append({
                        'predicate': str(p),
                        'target': str(o),
                        'target_label': o_label
                    })
            
            if outgoing_results:
                df_out = pd.DataFrame(outgoing_results)
                df_out['관계'] = df_out['predicate'].apply(lambda x: _extract_local_name(str(x)))
                df_out['타겟'] = df_out['target'].apply(lambda x: _extract_local_name(str(x)))
                display_df_out = df_out[['관계', '타겟']].copy()
                st.dataframe(display_df_out, width='stretch', hide_index=True)
                st.caption(f"총 {len(display_df_out)}개 관계")
            else:
                st.info("나가는 관계가 없습니다.")
        except Exception as e:
            st.error(f"관계 조회 실패: {e}")
    
    # 관계 관리 기능
    st.divider()
    st.markdown("#### 🔧 관계 관리")
    
    # 노드 ID 추출
    node_id = _extract_local_name(node_uri)
    
    # 관계 추가
    with st.expander("➕ 새 관계 추가", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            target_search = st.text_input("타겟 노드 검색", placeholder="노드 ID 또는 라벨로 검색", key="target_search")
        with col2:
            relation_name = st.text_input("관계명", value="relatedTo", key="relation_name")
        
        # 타겟 노드 검색 결과
        if target_search:
            graph_data = core.ontology_manager.to_json()
            nodes = graph_data.get("instances", {}).get("nodes", [])
            matched = [n for n in nodes if target_search.lower() in n.get("id", "").lower() or 
                      target_search.lower() in n.get("label", "").lower()]
            
            if matched:
                st.markdown("**검색 결과:**")
                for node in matched[:10]:
                    target_node_id = node.get("id", "")
                    target_node_label = node.get("label", "")
                    if st.button(f"추가: {target_node_label}", key=f"add_rel_{target_node_id}"):
                        with st.spinner("관계 추가 중..."):
                            success = core.ontology_manager.add_relationship(node_id, target_node_id, relation_name)
                            if success:
                                core.ontology_manager.save_graph()
                                st.success(f"✅ 관계가 추가되었습니다!")
                                st.rerun()
                            else:
                                st.error("관계 추가 실패")
            else:
                st.info("검색 결과가 없습니다.")
    
    # 관계 삭제
    with st.expander("🗑️ 관계 삭제", expanded=False):
        st.warning("⚠️ 삭제된 관계는 복구할 수 없습니다.")
        
        # Outgoing 관계 삭제
        try:
            from rdflib import URIRef, RDFS
            node_node = URIRef(node_uri)
            outgoing_results = []
            for p, o in graph.predicate_objects(node_node):
                if isinstance(o, URIRef):
                    labels = list(graph.objects(o, RDFS.label))
                    o_label = str(labels[0]) if labels else ""
                    outgoing_results.append({
                        'predicate': p,
                        'target': o,
                        'target_label': o_label
                    })
            
            if outgoing_results:
                st.markdown("**나가는 관계 삭제:**")
                for idx, row in enumerate(outgoing_results):
                    target_id = _extract_local_name(str(row['target']))
                    relation = _extract_local_name(str(row['predicate']))
                    target_label = row['target_label'] or target_id
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.text(f"{relation} → {target_label}")
                    with col2:
                        if st.button("삭제", key=f"del_outgoing_{idx}", type="secondary"):
                            with st.spinner("관계 삭제 중..."):
                                success = core.ontology_manager.remove_relationship(node_id, target_id, relation)
                                if success:
                                    core.ontology_manager.save_graph()
                                    st.success("✅ 관계가 삭제되었습니다!")
                                    st.rerun()
                                else:
                                    st.error("관계 삭제 실패")
        except Exception as e:
            st.error(f"관계 조회 실패: {e}")


def _render_related_documents(core, node_label: str):
    """관련 문서 표시 (RAG 검색)"""
    if not core.rag_manager.is_available():
        st.info("RAG 인덱스가 구성되지 않았습니다.")
        return
    
    if st.button(f"'{node_label}' 관련 문서 검색"):
        try:
            with st.spinner("문서 검색 중..."):
                retrieved = core.rag_manager.retrieve_with_context(node_label, top_k=5)
                
                if retrieved:
                    from ui.components.citation_panel import render_citation_panel
                    render_citation_panel(retrieved, highlight_query=node_label)
                else:
                    st.info("관련 문서를 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"문서 검색 실패: {e}")
    else:
        st.info("위 버튼을 클릭하여 관련 문서를 검색하세요.")


def _render_sparql_info(core, node_uri: str, node_label: str):
    """SPARQL 쿼리 정보 표시"""
    st.markdown("#### 노드 정보 조회용 SPARQL 쿼리")
    
    # 자동 생성된 쿼리 표시
    query_template = f"""PREFIX def: <http://defense-ai.kr/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# 노드의 모든 속성 조회
SELECT ?predicate ?object WHERE {{
    <{node_uri}> ?predicate ?object .
}}
ORDER BY ?predicate"""
    
    st.code(query_template, language="sparql")
    
    if st.button("▶ 이 쿼리 실행"):
        try:
            results = core.ontology_manager.query(query_template)
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, width='stretch', hide_index=True)
            else:
                st.info("쿼리 결과가 없습니다.")
        except Exception as e:
            st.error(f"쿼리 실행 실패: {e}")


def _extract_local_name(uri: str) -> str:
    """URI에서 로컬 이름 추출"""
    if '#' in uri:
        return uri.split('#')[-1]
    elif '/' in uri:
        return uri.split('/')[-1]
    else:
        return uri


def _format_object_value(obj_str: str) -> str:
    """객체 값을 읽기 쉽게 포맷"""
    # 리터럴 값 처리
    if obj_str.startswith('"') and obj_str.endswith('"'):
        return obj_str[1:-1]
    # URI 처리
    return _extract_local_name(obj_str)

