# ui/components/ontology_manager_panel.py
# -*- coding: utf-8 -*-
"""
온톨로지 관리 패널
관계의 CRUD 기능을 제공하는 통합 관리 인터페이스
"""
import streamlit as st
from typing import Dict, List, Optional
import pandas as pd

try:
    from rdflib import URIRef
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False


def render_ontology_manager_panel(core):
    """
    온톨로지 관리 패널 렌더링
    
    Args:
        core: CorePipeline 인스턴스
    """
    if not RDFLIB_AVAILABLE or not core.ontology_manager or not core.ontology_manager.graph:
        st.warning("온톨로지 그래프가 생성되지 않았습니다.")
        return
    
    # 메서드 존재 여부 확인 및 디버깅 정보
    required_methods = ['get_all_relationships', 'add_relationship', 'remove_relationship', 'update_relationship', 'search_relationships']
    missing_methods = [m for m in required_methods if not hasattr(core.ontology_manager, m)]
    
    if missing_methods:
        st.error(f"⚠️ 온톨로지 관리자에 필요한 메서드가 없습니다: {', '.join(missing_methods)}")
        st.info("💡 **해결 방법:**\n1. Streamlit 서버를 완전히 중지하세요 (Ctrl+C)\n2. Python 캐시를 삭제하세요: `find . -type d -name __pycache__ -exec rm -r {} +`\n3. Streamlit을 다시 시작하세요")
        
        with st.expander("🔍 디버깅 정보", expanded=False):
            # 모듈 강제 리로드 시도
            try:
                import importlib
                import core_pipeline.ontology_manager_enhanced
                importlib.reload(core_pipeline.ontology_manager_enhanced)
                st.success("✅ 모듈 리로드 완료. 페이지를 새로고침해주세요.")
            except Exception as e:
                st.warning(f"모듈 리로드 실패: {e}")
            
            st.code(f"""
Ontology Manager Type: {type(core.ontology_manager).__name__}
Ontology Manager Module: {type(core.ontology_manager).__module__}
Available Methods: {[m for m in dir(core.ontology_manager) if not m.startswith('_') and 'relationship' in m.lower()]}
Missing Methods: {missing_methods}
All Methods (first 20): {[m for m in dir(core.ontology_manager) if not m.startswith('_')][:20]}
            """)
            
            # 직접 메서드 존재 여부 확인
            st.markdown("**직접 확인:**")
            for method in required_methods:
                has_method = hasattr(core.ontology_manager, method)
                st.write(f"- {method}: {'✅' if has_method else '❌'}")
                if has_method:
                    try:
                        method_obj = getattr(core.ontology_manager, method)
                        st.write(f"  - Type: {type(method_obj)}")
                        st.write(f"  - Callable: {callable(method_obj)}")
                    except Exception as e:
                        st.write(f"  - Error: {e}")
        return
    
    st.markdown("### 🔧 온톨로지 관계 관리")
    st.markdown("그래프의 관계를 조회, 추가, 수정, 삭제할 수 있습니다.")
    
    # 탭으로 기능 분리
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 관계 조회",
        "➕ 관계 추가",
        "✏️ 관계 수정",
        "🗑️ 관계 삭제"
    ])
    
    with tab1:
        _render_relationship_browser(core)
    
    with tab2:
        _render_relationship_creator(core)
    
    with tab3:
        _render_relationship_editor(core)
    
    with tab4:
        _render_relationship_deleter(core)


def _render_relationship_browser(core, show_title=True):
    """관계 조회"""
    if show_title:
        st.markdown("#### 📋 관계 조회 및 검색")
    
    # 검색 옵션
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input("검색어 입력", placeholder="노드 ID, 라벨, 관계명으로 검색", key="browser_search_query")
    with col2:
        search_in_labels = st.checkbox("라벨에서도 검색", value=True, key="browser_search_labels")
    with col3:
        if st.button("🔍 검색", type="primary", key="browser_search_button"):
            st.session_state.relationship_search_query = search_query
            st.session_state.relationship_search_labels = search_in_labels
    
    # 필터 옵션
    with st.expander("🔽 고급 필터", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_source = st.text_input("소스 노드 ID", placeholder="예: 임무정보_MSN001", key="browser_filter_source")
        with col2:
            filter_target = st.text_input("타겟 노드 ID", placeholder="예: 전장축선_AXIS001", key="browser_filter_target")
        with col3:
            filter_relation = st.text_input("관계명", placeholder="예: relatedTo", key="browser_filter_relation")
        
        if st.button("필터 적용", key="browser_filter_apply"):
            st.session_state.relationship_filter_source = filter_source if filter_source else None
            st.session_state.relationship_filter_target = filter_target if filter_target else None
            st.session_state.relationship_filter_relation = filter_relation if filter_relation else None
    
    # 관계 목록 조회
    # 메서드 존재 여부 확인
    if not hasattr(core.ontology_manager, 'get_all_relationships'):
        st.error("온톨로지 관리자에 관계 조회 메서드가 없습니다. Streamlit을 재시작해주세요.")
        return
    
    if hasattr(st.session_state, 'relationship_search_query') and st.session_state.relationship_search_query:
        # 검색 모드
        if hasattr(core.ontology_manager, 'search_relationships'):
            relationships = core.ontology_manager.search_relationships(
                st.session_state.relationship_search_query,
                search_in_labels=st.session_state.get('relationship_search_labels', True)
            )
            st.info(f"검색 결과: {len(relationships)}개 관계 발견")
        else:
            st.error("온톨로지 관리자에 관계 검색 메서드가 없습니다.")
            relationships = []
    else:
        # 필터 모드
        filter_source = st.session_state.get('relationship_filter_source')
        filter_target = st.session_state.get('relationship_filter_target')
        filter_relation = st.session_state.get('relationship_filter_relation')
        
        relationships = core.ontology_manager.get_all_relationships(
            source_node_id=filter_source,
            target_node_id=filter_target,
            relation_name=filter_relation
        )
        
        if filter_source or filter_target or filter_relation:
            st.info(f"필터 결과: {len(relationships)}개 관계 발견")
    
    # 관계 목록 표시
    if relationships:
        # 데이터프레임 생성
        df_data = []
        for rel in relationships:
            df_data.append({
                "소스 노드": rel.get("source_label", rel.get("source", "")),
                "관계": rel.get("relation", ""),
                "타겟 노드": rel.get("target_label", rel.get("target", "")),
                "소스 ID": rel.get("source", ""),
                "타겟 ID": rel.get("target", "")
            })
        
        df = pd.DataFrame(df_data)
        
        # 표시할 컬럼 선택
        display_cols = ["소스 노드", "관계", "타겟 노드"]
        st.dataframe(
            df[display_cols],
            width="stretch",
            hide_index=True
        )
        
        # 상세 정보 (접을 수 있는 섹션)
        with st.expander("📊 상세 정보", expanded=False):
            st.dataframe(df, width="stretch", hide_index=True)
            st.caption(f"총 {len(relationships)}개 관계")
    else:
        st.info("관계가 없거나 검색 결과가 없습니다.")


def _render_relationship_creator(core):
    """관계 추가"""
    st.markdown("#### ➕ 새 관계 추가")
    
    # 방법 선택
    creation_method = st.radio(
        "관계 추가 방법",
        ["직접 입력", "노드 선택"],
        horizontal=True,
        key="creator_method_radio"
    )
    
    if creation_method == "직접 입력":
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            source_id = st.text_input("소스 노드 ID", placeholder="예: 임무정보_MSN001", key="creator_source_id")
        with col2:
            target_id = st.text_input("타겟 노드 ID", placeholder="예: 전장축선_AXIS001", key="creator_target_id")
        with col3:
            relation_name = st.text_input("관계명", placeholder="예: relatedTo", value="relatedTo", key="creator_relation_name")
        
        # 노드 검색 도우미
        with st.expander("🔍 노드 검색 도우미", expanded=False):
            node_search = st.text_input("노드 검색", placeholder="노드 ID 또는 라벨로 검색", key="creator_node_search")
            if node_search:
                graph_data = core.ontology_manager.to_json()
                nodes = graph_data.get("instances", {}).get("nodes", [])
                matched = [n for n in nodes if node_search.lower() in n.get("id", "").lower() or 
                          node_search.lower() in n.get("label", "").lower()]
                
                if matched:
                    st.markdown("**검색 결과:**")
                    for node in matched[:10]:
                        node_id = node.get("id", "")
                        node_label = node.get("label", "")
                        if st.button(f"소스로 선택: {node_label}", key=f"select_source_{node_id}"):
                            st.session_state.creator_source_id = node_id
                            st.rerun()
                        if st.button(f"타겟으로 선택: {node_label}", key=f"select_target_{node_id}"):
                            st.session_state.creator_target_id = node_id
                            st.rerun()
                else:
                    st.info("검색 결과가 없습니다.")
        
        # 세션 상태에서 선택된 값 사용
        if hasattr(st.session_state, 'creator_source_id'):
            source_id = st.session_state.creator_source_id
            del st.session_state.creator_source_id
        
        if hasattr(st.session_state, 'creator_target_id'):
            target_id = st.session_state.creator_target_id
            del st.session_state.creator_target_id
        
        # 관계명 제안
        st.markdown("**관계명 제안:**")
        relation_suggestions = ["relatedTo", "hasMission", "locatedIn", "hasAxis", 
                               "hasFriendlyUnit", "hasEnemyUnit", "hasThreat", "appliesTo"]
        selected_relation = st.selectbox("관계명 선택", [""] + relation_suggestions, key="creator_relation_selector")
        if selected_relation:
            relation_name = selected_relation
        
        if st.button("➕ 관계 추가", type="primary", key="creator_add_button"):
            if source_id and target_id and relation_name:
                with st.spinner("관계 추가 중..."):
                    success = core.ontology_manager.add_relationship(source_id, target_id, relation_name)
                    if success:
                        # 그래프 저장
                        core.ontology_manager.save_graph()
                        st.success(f"✅ 관계가 추가되었습니다: {source_id} -[{relation_name}]-> {target_id}")
                        st.rerun()
                    else:
                        st.error("관계 추가 실패. 노드 ID를 확인해주세요.")
            else:
                st.warning("모든 필드를 입력해주세요.")
    
    else:  # 노드 선택
        st.info("노드 선택 기능은 그래프 시각화에서 노드를 클릭하여 사용할 수 있습니다.")


def _render_relationship_editor(core, show_title=True):
    """관계 수정"""
    if show_title:
        st.markdown("#### ✏️ 관계 수정")
    
    # 수정할 관계 선택
    st.markdown("**수정할 관계 선택:**")
    
    # 관계 목록 가져오기
    if not hasattr(core.ontology_manager, 'get_all_relationships'):
        st.error("온톨로지 관리자에 관계 조회 메서드가 없습니다. Streamlit을 재시작해주세요.")
        return
    
    all_relationships = core.ontology_manager.get_all_relationships()
    
    if not all_relationships:
        st.info("수정할 관계가 없습니다.")
        return
    
    # 관계 선택 드롭다운
    relationship_options = []
    for idx, rel in enumerate(all_relationships[:100]):  # 최대 100개
        source_label = rel.get("source_label", rel.get("source", ""))
        target_label = rel.get("target_label", rel.get("target", ""))
        relation = rel.get("relation", "")
        option_text = f"{source_label} -[{relation}]-> {target_label}"
        relationship_options.append((option_text, idx))
    
    selected_option = st.selectbox(
        "관계 선택",
        options=[opt[1] for opt in relationship_options],
        format_func=lambda x: relationship_options[x][0] if x < len(relationship_options) else "",
        key="editor_relationship_select"
    )
    
    if selected_option is not None and selected_option < len(all_relationships):
        selected_rel = all_relationships[selected_option]
        
        st.divider()
        st.markdown("**현재 관계 정보:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("소스 노드", value=selected_rel.get("source_label", selected_rel.get("source", "")), disabled=True, key="editor_source_display")
        with col2:
            st.text_input("관계명", value=selected_rel.get("relation", ""), disabled=True, key="editor_relation_display")
        with col3:
            st.text_input("타겟 노드", value=selected_rel.get("target_label", selected_rel.get("target", "")), disabled=True, key="editor_target_display")
        
        st.divider()
        st.markdown("**수정할 내용:**")
        
        col1, col2 = st.columns(2)
        with col1:
            new_relation = st.text_input("새로운 관계명", value=selected_rel.get("relation", ""), key="editor_new_relation")
        with col2:
            new_target_id = st.text_input("새로운 타겟 노드 ID (선택적)", placeholder="변경하지 않으려면 비워두세요", key="editor_new_target")
        
        if st.button("✏️ 관계 수정", type="primary", key="editor_update_button"):
            if new_relation:
                with st.spinner("관계 수정 중..."):
                    success = core.ontology_manager.update_relationship(
                        source_node_id=selected_rel.get("source"),
                        target_node_id=selected_rel.get("target"),
                        old_relation_name=selected_rel.get("relation"),
                        new_relation_name=new_relation,
                        new_target_node_id=new_target_id if new_target_id else None
                    )
                    
                    if success:
                        # 그래프 저장
                        core.ontology_manager.save_graph()
                        st.success("✅ 관계가 수정되었습니다.")
                        st.rerun()
                    else:
                        st.error("관계 수정 실패.")
            else:
                st.warning("새로운 관계명을 입력해주세요.")


def _render_relationship_deleter(core):
    """관계 삭제"""
    st.markdown("#### 🗑️ 관계 삭제")
    st.warning("⚠️ 삭제된 관계는 복구할 수 없습니다. 신중하게 선택해주세요.")
    
    # 메서드 존재 여부 확인
    if not hasattr(core.ontology_manager, 'get_all_relationships'):
        st.error("온톨로지 관리자에 관계 조회 메서드가 없습니다. Streamlit을 재시작해주세요.")
        return
    
    # 삭제할 관계 선택
    all_relationships = core.ontology_manager.get_all_relationships()
    
    if not all_relationships:
        st.info("삭제할 관계가 없습니다.")
        return
    
    # 관계 선택 (체크박스)
    st.markdown("**삭제할 관계 선택:**")
    
    if "relationships_to_delete" not in st.session_state:
        st.session_state.relationships_to_delete = set()
    
    # 관계 목록 표시
    delete_data = []
    for idx, rel in enumerate(all_relationships[:100]):  # 최대 100개
        is_selected = idx in st.session_state.relationships_to_delete
        
        source_label = rel.get("source_label", rel.get("source", ""))
        target_label = rel.get("target_label", rel.get("target", ""))
        relation = rel.get("relation", "")
        
        delete_data.append({
            "선택": "✓" if is_selected else "",
            "소스 노드": source_label,
            "관계": relation,
            "타겟 노드": target_label
        })
    
    if delete_data:
        df = pd.DataFrame(delete_data)
        st.dataframe(df[["소스 노드", "관계", "타겟 노드"]], width="stretch", hide_index=True)
        
        # 체크박스로 선택
        st.markdown("**관계 선택:**")
        num_cols = 3
        num_rows = (len(all_relationships[:100]) + num_cols - 1) // num_cols
        
        for row_idx in range(num_rows):
            cols = st.columns(num_cols)
            for col_idx in range(num_cols):
                idx = row_idx * num_cols + col_idx
                if idx < len(all_relationships[:100]):
                    rel = all_relationships[idx]
                    source_label = rel.get("source_label", rel.get("source", ""))[:20]
                    target_label = rel.get("target_label", rel.get("target", ""))[:20]
                    relation = rel.get("relation", "")
                    
                    with cols[col_idx]:
                        checkbox_label = f"#{idx+1}: {source_label} -[{relation}]-> {target_label}"
                        is_selected = st.checkbox(
                            checkbox_label,
                            value=idx in st.session_state.relationships_to_delete,
                            key=f"delete_select_{idx}"
                        )
                        
                        if is_selected:
                            st.session_state.relationships_to_delete.add(idx)
                        else:
                            st.session_state.relationships_to_delete.discard(idx)
        
        # 삭제 버튼
        if st.session_state.relationships_to_delete:
            st.divider()
            st.warning(f"⚠️ {len(st.session_state.relationships_to_delete)}개 관계가 선택되었습니다.")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🗑️ 선택된 관계 삭제", type="primary"):
                    with st.spinner("관계 삭제 중..."):
                        deleted_count = 0
                        failed_count = 0
                        
                        for idx in list(st.session_state.relationships_to_delete):
                            if idx < len(all_relationships):
                                rel = all_relationships[idx]
                                success = core.ontology_manager.remove_relationship(
                                    source_node_id=rel.get("source"),
                                    target_node_id=rel.get("target"),
                                    relation_name=rel.get("relation")
                                )
                                
                                if success:
                                    deleted_count += 1
                                else:
                                    failed_count += 1
                        
                        if deleted_count > 0:
                            # 그래프 저장
                            core.ontology_manager.save_graph()
                            st.success(f"✅ {deleted_count}개 관계가 삭제되었습니다.")
                            if failed_count > 0:
                                st.warning(f"⚠️ {failed_count}개 관계 삭제 실패")
                            
                            # 선택 초기화
                            st.session_state.relationships_to_delete = set()
                            st.rerun()
                        else:
                            st.error("관계 삭제 실패")
            
            with col2:
                if st.button("🔄 선택 초기화"):
                    st.session_state.relationships_to_delete = set()
                    st.rerun()

