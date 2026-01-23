# ui/components/ontology_studio/relationship_manager.py
# -*- coding: utf-8 -*-
"""
관계 관리 컴포넌트
관계(인스턴스) 생성, 편집, 관리
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from core_pipeline.ontology_history import OntologyHistory

def render_relationship_manager(orchestrator):
    """관계 관리 메인 렌더링"""
    st.markdown("### 🔗 관계 관리 (Relationship Management)")
    
    # 검증 권장사항 배너 표시
    if 'validation_recommendations' in st.session_state and st.session_state.validation_recommendations:
        _render_validation_recommendations_banner()
    
    # 히스토리 관리자 초기화
    if "history_manager" not in st.session_state:
        st.session_state.history_manager = OntologyHistory()
    history_manager = st.session_state.history_manager
    
    # 권장사항에 따라 관련 서브탭으로 자동 이동 안내
    if 'navigate_to_subtab' in st.session_state:
        target_subtab = st.session_state.navigate_to_subtab
        if target_subtab:
            st.info(f"💡 **검증 권장사항**: '{target_subtab}' 서브탭에서 권장사항을 확인하세요.")
        # navigate_to_subtab 초기화 (한 번만 표시)
        del st.session_state.navigate_to_subtab
    
    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "📋 관계 조회",
        "🔍 관계 생성 규칙",
        "✏️ 관계 편집",
        "🔄 배치 작업"
    ])
    
    with sub_tab1:
        _render_relationship_browser(orchestrator)
    
    with sub_tab2:
        _render_relationship_rules(orchestrator)
    
    with sub_tab3:
        _render_relationship_editor(orchestrator, history_manager)
    
    with sub_tab4:
        _render_batch_operations(orchestrator, history_manager)

def _render_relationship_browser(orchestrator):
    """관계 조회"""
    st.markdown("#### 📋 관계 조회 및 검색")
    
    # 검증 권장사항이 있고 관계 조회 관련이면 하이라이트
    if 'validation_recommendations' in st.session_state:
        browser_recs = [r for r in st.session_state.validation_recommendations 
                       if r.get('관련_서브탭') == '관계 조회']
        if browser_recs:
            rec = browser_recs[0]
            st.warning(f"⚠️ **검증 권장사항**: {rec.get('항목', '')} - {rec.get('조치', '')}")
            st.markdown(f"**문제**: {rec.get('문제', '')}")
            st.markdown("**권장 조치:**")
            for step in rec.get('상세_조치', []):
                st.markdown(f"- {step}")
            st.divider()
    
    # 기존 ontology_manager_panel의 관계 조회 기능 재사용
    from ui.components.ontology_manager_panel import _render_relationship_browser
    _render_relationship_browser(orchestrator.core, show_title=False)

def _render_relationship_rules(orchestrator):
    """관계 생성 규칙 검토"""
    st.markdown("#### 🔍 관계 생성 규칙 검토")
    st.info("💡 AI가 관계를 생성할 때 사용한 규칙을 확인하고 수정할 수 있습니다.")
    
    # 검증 권장사항이 있고 전장축선 관련이면 하이라이트
    if 'validation_recommendations' in st.session_state:
        axis_recs = [r for r in st.session_state.validation_recommendations 
                     if r.get('대상') in ['전장축선', '전체'] and r.get('관련_서브탭') == '관계 생성 규칙']
        if axis_recs:
            rec = axis_recs[0]
            st.warning(f"⚠️ **검증 권장사항**: {rec.get('항목', '')} - {rec.get('조치', '')}")
            st.markdown(f"**문제**: {rec.get('문제', '')}")
            st.markdown("**권장 조치:**")
            for step in rec.get('상세_조치', []):
                st.markdown(f"- {step}")
            if rec.get('관련_테이블'):
                st.markdown(f"**관련 테이블**: {', '.join(rec['관련_테이블'])}")
            st.divider()
    
    # relation_mappings.json 로드
    base_dir = Path(__file__).parent.parent.parent.parent
    relation_mapping_path = base_dir / "metadata" / "relation_mappings.json"
    
    if not relation_mapping_path.exists():
        st.error("관계 매핑 파일을 찾을 수 없습니다.")
        return
    
    with open(relation_mapping_path, 'r', encoding='utf-8') as f:
        relation_mappings = json.load(f)
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    graph = ontology_manager.graph
    ns = ontology_manager.ns
    
    # 규칙별 통계 계산
    rule_stats = []
    for table_name, rules in relation_mappings.items():
        for col_name, rule_config in rules.items():
            rule_type = _get_rule_type(rule_config)
            created_count = _count_relationships_by_rule(
                graph, ns, table_name, col_name, rule_config
            )
            
            rule_stats.append({
                "테이블": table_name,
                "컬럼": col_name,
                "규칙 타입": rule_type,
                "생성된 관계 수": created_count,
                "규칙 설정": json.dumps(rule_config, ensure_ascii=False) if isinstance(rule_config, dict) else rule_config
            })
    
    # 통계 표시
    if rule_stats:
        df_stats = pd.DataFrame(rule_stats)
        df_stats = df_stats.sort_values('생성된 관계 수', ascending=False)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
        
        # 규칙 상세 정보
        st.divider()
        st.markdown("#### 📝 규칙 상세 정보")
        
        selected_table = st.selectbox(
            "테이블 선택",
            options=sorted(relation_mappings.keys()),
            key="rule_reviewer_table_select"
        )
        
        # 권장사항과 관련된 테이블이면 하이라이트
        if 'validation_recommendations' in st.session_state:
            for rec in st.session_state.validation_recommendations:
                if rec.get('대상') == selected_table or (rec.get('대상') == '전체' and selected_table in rec.get('관련_테이블', [])):
                    st.info(f"💡 **권장사항**: 이 테이블에 대한 관계 규칙을 확인하세요. {rec.get('조치', '')}")
                    if rec.get('상세_조치'):
                        with st.expander("📋 상세 조치 방법", expanded=False):
                            for step in rec.get('상세_조치', []):
                                st.markdown(f"- {step}")
                    break
        
        if selected_table:
            table_rules = relation_mappings[selected_table]
            for col_name, rule_config in table_rules.items():
                with st.expander(f"📋 {col_name} 컬럼 규칙", expanded=False):
                    _render_rule_details(col_name, rule_config, graph, ns, selected_table)
                    _render_rule_actions(relation_mapping_path, selected_table, col_name, rule_config)
    else:
        st.info("등록된 규칙이 없습니다.")

def _get_rule_type(rule_config) -> str:
    """규칙 타입 판단"""
    if isinstance(rule_config, dict):
        if rule_config.get('dynamic'):
            return "동적 FK"
        elif '추론:' in str(rule_config) or rule_config.get('confidence'):
            return "추론 관계"
        elif rule_config.get('type_mapping'):
            return "동적 FK (타입 매핑)"
        else:
            return "일반 FK"
    elif isinstance(rule_config, str):
        return "단순 FK"
    return "알 수 없음"

def _count_relationships_by_rule(graph, ns, table_name: str, col_name: str, rule_config) -> int:
    """규칙으로 생성된 관계 수 계산 (간단한 버전)"""
    if not graph or not ns:
        return 0
    # 실제 구현: 그래프에서 해당 규칙으로 생성된 관계 수 계산
    # 현재는 간단히 0 반환
    # TODO: 실제 관계 매칭 로직 구현
    return 0

def _render_rule_details(col_name: str, rule_config, graph, ns, table_name: str):
    """규칙 상세 정보 표시"""
    st.markdown(f"**규칙 타입**: {_get_rule_type(rule_config)}")
    
    if isinstance(rule_config, dict):
        if rule_config.get('target'):
            st.markdown(f"**타겟 테이블**: `{rule_config['target']}`")
        if rule_config.get('confidence'):
            st.markdown(f"**신뢰도**: {rule_config['confidence']:.0%}")
        if rule_config.get('type_mapping'):
            st.markdown("**타입 매핑**:")
            for type_val, target in rule_config['type_mapping'].items():
                st.markdown(f"- `{type_val}` → `{target}`")
    elif isinstance(rule_config, str):
        st.markdown(f"**타겟 테이블**: `{rule_config}`")
    
    # 생성된 관계 수
    if graph and ns:
        created_count = _count_relationships_by_rule(graph, ns, table_name, col_name, rule_config)
        st.metric("생성된 관계 수", f"{created_count:,}개")
    else:
        st.metric("생성된 관계 수", "N/A")

def _render_rule_actions(relation_mapping_path: Path, table_name: str, col_name: str, rule_config):
    """규칙 액션 버튼"""
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("✏️ 규칙 편집", key=f"edit_rule_{table_name}_{col_name}"):
            st.session_state[f"editing_rule_{table_name}_{col_name}"] = True
    with col2:
        if st.button("🚫 규칙 비활성화", key=f"disable_rule_{table_name}_{col_name}"):
            st.info("규칙 비활성화 기능은 구현 예정입니다.")
    with col3:
        if st.button("🗑️ 규칙 삭제", key=f"delete_rule_{table_name}_{col_name}"):
            st.warning("규칙 삭제 기능은 구현 예정입니다.")

def _render_relationship_editor(orchestrator, history_manager: OntologyHistory):
    """관계 편집"""
    st.markdown("#### ✏️ 관계 편집")
    
    # 기존 ontology_manager_panel의 관계 편집 기능 재사용
    from ui.components.ontology_manager_panel import _render_relationship_editor, _render_relationship_deleter
    
    # 관계 수정
    _render_relationship_editor(orchestrator.core, show_title=False)
    
    st.divider()
    
    # 관계 삭제
    _render_relationship_deleter(orchestrator.core)

def _render_batch_operations(orchestrator, history_manager: OntologyHistory):
    """배치 작업"""
    st.markdown("#### 🔄 배치 작업 (Batch Operations)")
    st.info("💡 여러 관계를 한 번에 수정하거나 삭제할 수 있습니다.")
    
    # 관계 선택 방법
    selection_method = st.radio(
        "관계 선택 방법",
        ["필터 기반 선택", "검증 결과 기반 선택", "수동 선택"],
        key="batch_edit_selection_method"
    )
    
    st.info("배치 작업 기능은 구현 예정입니다.")

def _render_validation_recommendations_banner():
    """검증 권장사항 배너 표시"""
    recommendations = st.session_state.validation_recommendations
    timestamp = st.session_state.get('validation_recommendations_timestamp', None)
    
    # 해결되지 않은 권장사항만 표시
    unresolved = [r for r in recommendations if not r.get('resolved', False)]
    
    if not unresolved:
        return
    
    with st.container():
        st.markdown("""
        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h4 style="margin-top: 0; color: #856404;">⚠️ 스키마 검증 권장사항</h4>
        </div>
        """, unsafe_allow_html=True)
        
        if timestamp:
            st.caption(f"검증 일시: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 권장사항별로 표시
        for idx, rec in enumerate(unresolved):
            priority_color = {
                "높음": "🔴",
                "중간": "🟡",
                "낮음": "🟢"
            }.get(rec.get('우선순위', ''), "⚪")
            
            with st.expander(f"{priority_color} {rec.get('항목', '')} - 우선순위: {rec.get('우선순위', '')}", expanded=(idx == 0)):
                st.markdown(f"**문제**: {rec.get('문제', '')}")
                st.markdown(f"**조치**: {rec.get('조치', '')}")
                st.markdown(f"**대상**: {rec.get('대상', '')}")
                
                st.markdown("**상세 조치 방법:**")
                for step in rec.get('상세_조치', []):
                    st.markdown(f"- {step}")
                
                # 관련 테이블/관계 정보
                if rec.get('관련_테이블'):
                    st.markdown(f"**관련 테이블**: {', '.join(rec['관련_테이블'])}")
                if rec.get('관련_관계'):
                    st.markdown(f"**관련 관계**: {', '.join(rec['관련_관계'])}")
                
                # 조치 완료 버튼
                if st.button(f"✅ 조치 완료", key=f"resolve_rec_{rec.get('id', idx)}"):
                    # 권장사항 제거 (또는 완료 표시)
                    rec['resolved'] = True
                    st.success("조치 완료로 표시되었습니다. 다음 검증에서 확인하세요.")
                    st.rerun()
        
        # 모든 권장사항 닫기 버튼
        if st.button("❌ 권장사항 닫기", key="close_recommendations"):
            del st.session_state.validation_recommendations
            if 'validation_recommendations_timestamp' in st.session_state:
                del st.session_state.validation_recommendations_timestamp
            st.rerun()

