# ui/components/ontology_dashboard_panel.py
# -*- coding: utf-8 -*-
"""
Ontology Dashboard Component
Reusable UI component for displaying ontology structure, health, and reasoning insights.
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
from core_pipeline.ontology_validator import OntologyValidator

def render_ontology_dashboard_panel(orchestrator):
    """
    온톨로지 대시보드 패널 렌더링
    
    Args:
        orchestrator: Orchestrator 인스턴스 (core.enhanced_ontology_manager 필요)
    """
    # Validator 초기화
    validator = OntologyValidator(orchestrator.core.enhanced_ontology_manager)

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["🏗️ 구조 시각화 (Structure)", "✅ 건전성 검증 (Health)", "🧠 추론 능력 (Reasoning)"])

    with tab1:
        st.markdown("### 🗺️ 핵심 스키마 구조 (T-Box)")
        
        # Live Metrics
        with st.container():
            counts = validator.get_instance_counts()
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("위협 (Threat)", counts.get("Threat", 0), border=True)
            m2.metric("방책 (COA)", counts.get("COA", 0), border=True)
            m3.metric("축선 (Axis)", counts.get("Axis", 0), border=True)
            m4.metric("부대 (Unit)", counts.get("Unit", 0), border=True)
            m5.metric("지형 (Terrain)", counts.get("Terrain", 0), border=True)

        st.divider()
        
        view_mode = st.radio(
            "시각화 모드 선택", 
            [
                "핵심 클래스 관계도 (Core Schema)", 
                "데이터-결심 연계 계보 (Data-to-Decision Lineage)",
                "테이블 관계 매핑 (Table Relationship Mapping)"
            ], 
            horizontal=True, 
            label_visibility="collapsed",
            key="dashboard_view_mode_selector"
        )

        # Streamlit의 위젯 재사용 문제를 해결하기 위해 각 그래프를 완전히 다른 레이아웃 구조에 배치
        if view_mode == "핵심 클래스 관계도 (Core Schema)":
            st.info("💡 전체 온톨로지가 아닌, **방책 결심 지원을 위한 핵심 클래스** 관계도입니다.")
            
            # 핵심 클래스 관계도 그래프 생성 및 표시
            # 고유한 레이아웃 구조 사용 (컬럼 레이아웃)
            col_graph, col_info = st.columns([2, 1])
            with col_graph:
                core_schema_dot = _get_core_schema_graph()
                st.graphviz_chart(core_schema_dot, use_container_width=True)
            with col_info:
                st.markdown("#### 📝 주요 스키마 변경 사항")
                st.markdown("\n".join([
                    "- **Axis Objectification**: 기존 문자열 속성이었던 '축선'이 `Axis` 객체로 승격되어, 지형/부대와 복합적인 관계를 맺을 수 있게 되었습니다.",
                    "- **Threat-COA Link**: 위협 상황에 따라 방책이 동적으로 매핑되는 `respondsTo` 관계가 정의되었습니다."
                ]))

        elif view_mode == "데이터-결심 연계 계보 (Data-to-Decision Lineage)":
            st.info("💡 **실제 데이터 필드**가 어떻게 **온톨로지**로 매핑되고, 최종 **의사결정**에 기여하는지 보여주는 상세 흐름도입니다.")
            
            # 실제 사용된 테이블 수 및 속성 수 표시
            ontology_manager = orchestrator.core.enhanced_ontology_manager
            info_text = []
            if ontology_manager and hasattr(ontology_manager, 'schema_registry'):
                actual_table_count = len(ontology_manager.schema_registry)
                info_text.append(f"📊 테이블: **{actual_table_count}개** (Layer 1에는 최대 10개만 표시)")
            
            if ontology_manager and ontology_manager.graph:
                try:
                    props_set = set()
                    ns_str = str(ontology_manager.ns) if ontology_manager.ns else "http://coa-agent-platform.org/ontology#"
                    for s, p, o in ontology_manager.graph.triples((None, None, None)):
                        p_str = str(p)
                        if p_str.startswith(ns_str):
                            prop_name = p_str.replace(ns_str, ":")
                            if prop_name and prop_name not in ["rdf:type", "rdfs:label", "rdfs:comment"]:
                                props_set.add(prop_name)
                    actual_prop_count = len(props_set)
                    info_text.append(f"🔗 속성: **{actual_prop_count}개** (Layer 2에는 최대 15개만 표시)")
                except:
                    pass
            
            if info_text:
                st.caption(" | ".join(info_text))
            
            # 데이터-결심 연계 계보 그래프 생성 및 표시
            # 실제 schema_registry 데이터 기반으로 동적 생성
            lineage_dot = None
            try:
                lineage_dot = _get_lineage_graph(orchestrator.core.enhanced_ontology_manager)
                st.graphviz_chart(lineage_dot, use_container_width=True)
            except Exception as e:
                st.error(f"다이어그램 렌더링 오류: {str(e)}")
                import traceback
                with st.expander("상세 오류 정보"):
                    st.code(traceback.format_exc())
                # 디버깅: DOT 코드 표시
                if lineage_dot:
                    with st.expander("생성된 DOT 코드 확인"):
                        st.code(lineage_dot, language="text")
            
            st.markdown("#### 🔍 분석: 데이터가 결심에 미치는 영향")
            col1, col2 = st.columns(2)
            with col1:
                 st.markdown("\n".join([
                     "**🔴 패널티 사례 (Penalty Case)**",
                     "- **데이터**: `지형유형=\"Mountain\"`, `병종=\"Armor\"`",
                     "- **규칙**: 기갑부대는 산악 지형에서 기동력이 급격히 저하됨",
                     "- **결과**: 기동 방책 점수 **-0.3점 감점**"
                 ]))
            with col2:
                 st.markdown("\n".join([
                     "**🟢 보너스 사례 (Bonus Case)**",
                     "- **데이터**: `지형유형=\"Mountain\"`, `병종=\"Infantry\"`",
                     "- **규칙**: 보병은 산악 지형을 방어 거점으로 활용 가능",
                     "- **결과**: 방어 방책 점수 **+0.2점 가산**"
                 ]))
        
        else:  # "테이블 관계 매핑 (Table Relationship Mapping)"
            st.info("💡 **모든 테이블의 컬럼들이 다른 테이블들과 맺는 관계**를 인터랙티브 네트워크 그래프로 시각화합니다.")
            
            # 인터랙티브 네트워크 그래프 뷰어 사용
            from ui.components.table_column_relationship_viewer import render_table_column_relationship_viewer
            render_table_column_relationship_viewer(orchestrator)

    with tab2:
        st.markdown("### ✅ 데이터 건전성 검 점수표")
        
        # 탭 내부에 서브탭 추가
        sub_tab1, sub_tab2 = st.tabs(["스키마 검증", "관계 품질 검증"])
        
        with sub_tab1:
            if st.button("🚀 검증 실행", key="run_valid_comp"):
                with st.spinner("데이터 스키마 및 정합성 검사 중..."):
                    report = validator.validate_schema_compliance()
                
                # Scorecard
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("종합 점수", f"{report['overall_score']}%")
                
                # Detail Checks
                st.divider()
                
                # Axis Check
                axis_res = report['axis_compliance']
                with st.expander("1. 전장축선(Axis) 객체화 검증", expanded=True):
                    for check in axis_res['checks']:
                        status_icon = "🟢" if check['status'] == 'PASS' else "🔴"
                        st.markdown(f"**{status_icon} {check['name']}**: {check['message']}")
                
                # Connectivity Check
                conn_res = report['connectivity_health']
                with st.expander("2. 데이터 연결성 검증", expanded=True):
                     for check in conn_res['checks']:
                        status_icon = "🟢" if check['status'] == 'PASS' else "🟡"
                        st.markdown(f"**{status_icon} {check['name']}**: {check['message']}")
                
                # Reasoning Check
                reason_res = report['reasoning_status']
                with st.expander("3. 추론 엔진 상태", expanded=True):
                     for check in reason_res['checks']:
                        status_icon = "🟢" if check['status'] == 'PASS' else "⚪"
                        st.markdown(f"**{status_icon} {check['name']}**: {check['message']}")
        
        with sub_tab2:
            # 관계 품질 검증
            from ui.components.relationship_quality_validator import render_relationship_quality_validator
            render_relationship_quality_validator(orchestrator)

    with tab3:
        st.markdown("### 🧠 추론 전/후 비교 (Inference Inspector)")
        st.markdown("온톨로지 추론 엔진이 도출한 **새로운 지식(Implicit Knowledge)**을 확인합니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("Input Graph (사람이 입력한 데이터)")
            st.code("\n".join([
                "# A unit is on high ground",
                ":Unit_A :locatedIn :HighGround .",
                ":HighGround :type :Mountain ."
            ]), language="turtle")
            
        with col2:
            st.success("Reasoned Graph (AI가 추론한 사실)")
            st.code("\n".join([
                "# AI infers advantage",
                ':Unit_A :hasAdvantage "True" .',
                ':Unit_A :movementSpeed "Slow" .'
            ]), language="turtle")
        
        st.divider()
        st.caption("실제 데이터 추론 결과 (Sample)")
        
        # 실제 추론된 트리플 샘플 조회
        query_inferred_sample = "\n".join([
            "SELECT ?s ?p ?o WHERE {",
            "    ?s <http://coa-agent-platform.org/ontology#hasAdvantage> ?o .",
            "} LIMIT 5"
        ])
        try:
            res = orchestrator.enhanced_ontology_manager.graph.query(query_inferred_sample)
            data = []
            for row in res:
                data.append({"Subject": row.s, "Predicate": "hasAdvantage", "Object": row.o})
            
            if data:
                st.dataframe(pd.DataFrame(data), width="stretch")
            else:
                st.warning("현재 추론된 '전술적 이점(hasAdvantage)' 데이터가 없습니다.")
        except Exception as e:
            st.error(f"추론 데이터 조회 실패: {e}")

def _get_core_schema_graph():
    lines = [
        "digraph Schema {",
        "    # CORE_SCHEMA_GRAPH_UNIQUE_ID",
        "    rankdir=LR;",
        '    node [shape=box, style="filled,rounded", fontname="Malgun Gothic", fillcolor="#2d333b", fontcolor="#c9d1d9", color="#7d8590"];',
        '    edge [fontname="Malgun Gothic", fontsize=10, color="#7d8590", fontcolor="#8b949e"];',
        '    bgcolor="transparent";',
        "",
        "    # Classes",
        '    Threat [label="위협 (Threat)", fillcolor="#7f1d1d", color="#f85149"];',
        '    COA [label="방책 (COA)", fillcolor="#1f2937", color="#388bfd"];',
        '    Axis [label="전장축선 (Axis)", fillcolor="#1e3a8a", color="#58a6ff"];',
        '    Terrain [label="지형 (Terrain)", fillcolor="#112211", color="#3fb950"];',
        '    Unit [label="부대 (Unit)"];',
        "    ",
        "    # Relations",
        '    Threat -> COA [label="respondsTo", style=dashed];',
        '    Threat -> Axis [label="usesAxis\\n(공격로)"];',
        '    COA -> Axis [label="hasMainAxis\\n(주공)"];',
        '    COA -> Axis [label="hasSubAxis\\n(조공)"];',
        '    Axis -> Terrain [label="locatedIn"];',
        '    Unit -> Terrain [label="locatedIn"];',
        '    Unit -> Threat [label="isHostileTo"];',
        "}"
    ]
    return "\n".join(lines)

def _get_lineage_graph(ontology_manager=None):
    """
    데이터-결심 연계 계보 그래프 생성
    
    Args:
        ontology_manager: EnhancedOntologyManager 인스턴스 (실제 테이블 목록 가져오기용)
    """
    # 실제 테이블 목록 가져오기
    source_tables = []
    if ontology_manager and hasattr(ontology_manager, 'schema_registry'):
        source_tables = list(ontology_manager.schema_registry.keys())
    
    # 테이블이 없으면 예시 데이터 사용
    if not source_tables:
        source_tables = ["지형셀", "아군부대현황", "적군부대현황", "기상상황", "위협상황", "임무정보", "전장축선"]
    
    lines = [
        "digraph Lineage {",
        "    # LINEAGE_GRAPH_UNIQUE_ID",
        "    rankdir=TB;",
        '    node [shape=box, style="filled,rounded", fontname="Malgun Gothic", margin="0.2,0.1"];',
        '    edge [fontname="Malgun Gothic", fontsize=9, color="#7d8590", fontcolor="#8b949e"];',
        '    bgcolor="transparent";',
        "    splines=spline;",
        "",
        "    # Layer 1: Excel Source Data",
        "    subgraph cluster_source {",
        f'        label="Layer 1: 원천 데이터 (Source Data) - {len(source_tables)}개 테이블";',
        '        style=dashed; color="#30363d"; fontcolor="#8b949e";',
        '        node [fillcolor="#161b22", color="#30363d", fontcolor="#c9d1d9"];',
        "        ",
    ]
    
    # 실제 테이블 목록을 노드로 추가
    for i, table_name in enumerate(source_tables[:10]):  # 최대 10개만 표시 (너무 많으면 복잡해짐)
        node_id = f"xls_{i}"
        # 파일명 형식으로 표시
        file_name = f"{table_name}.xlsx"
        lines.append(f'        {node_id} [label="[{file_name}]\\n{table_name}"];')
    
    # 10개 이상이면 생략 표시
    if len(source_tables) > 10:
        lines.append(f'        xls_more [label="... 외 {len(source_tables) - 10}개 테이블", style=dashed, fillcolor="#161b22", color="#30363d", fontcolor="#8b949e"];')
    
    lines.append("    }")
    lines.append("")
    lines.append("    # Layer 2: Ontology Properties")
    lines.append("    subgraph cluster_ontology {")
    
    # 실제 온톨로지 속성 가져오기
    ontology_props = []
    if ontology_manager and ontology_manager.graph:
        try:
            # 그래프에서 모든 속성(predicate) 추출
            props_set = set()
            ns_str = str(ontology_manager.ns) if ontology_manager.ns else "http://coa-agent-platform.org/ontology#"
            
            for s, p, o in ontology_manager.graph.triples((None, None, None)):
                p_str = str(p)
                # 온톨로지 네임스페이스의 속성만 추출
                if p_str.startswith(ns_str):
                    prop_name = p_str.replace(ns_str, ":")
                    if prop_name and prop_name not in ["rdf:type", "rdfs:label", "rdfs:comment"]:
                        props_set.add(prop_name)
            
            ontology_props = sorted(list(props_set))
        except Exception as e:
            # 오류 발생 시 기본 속성 사용
            ontology_props = [":terrainType", ":unitType", ":weatherCondition", ":threatType", ":coaType"]
    else:
        # 그래프가 없으면 기본 속성 사용
        ontology_props = [":terrainType", ":unitType", ":weatherCondition", ":threatType", ":coaType"]
    
    # 속성 개수 표시
    prop_count = len(ontology_props)
    lines.append(f'        label="Layer 2: 온톨로지 속성 (Ontology Model) - {prop_count}개 속성";')
    lines.append('        style=dashed; color="#30363d"; fontcolor="#8b949e";')
    lines.append('        node [fillcolor="#1f2937", color="#388bfd", fontcolor="#58a6ff"];')
    lines.append("        ")
    
    # 온톨로지 속성 노드 추가 (최대 15개만 표시, 너무 많으면 복잡해짐)
    display_props = ontology_props[:15]
    for i, prop in enumerate(display_props):
        prop_id = f"onto_{i}"
        lines.append(f'        {prop_id} [label="{prop}"];')
    
    # 15개 이상이면 생략 표시
    if len(ontology_props) > 15:
        lines.append(f'        onto_more [label="... 외 {len(ontology_props) - 15}개 속성", style=dashed, fillcolor="#1f2937", color="#388bfd", fontcolor="#58a6ff"];')
    
    lines.append("    }")
    lines.append("")
    lines.append("    # Layer 3: Decision Logic (Rules)")
    lines.append("    subgraph cluster_logic {")
    lines.append('        label="Layer 3: 의사결정 로직 (Decision Logic)";')
    lines.append('        style=dashed; color="#30363d"; fontcolor="#8b949e";')
    lines.append("        ")
    lines.append('        rule_mobility [label="기동성 판단 규칙\\n(Mobility Rule)", shape=diamond, fillcolor="#3e1f1b", color="#f85149", fontcolor="#ff7b72"];')
    lines.append('        rule_air [label="항공작전 판단 규칙\\n(Air Ops Rule)", shape=diamond, fillcolor="#3e1f1b", color="#f85149", fontcolor="#ff7b72"];')
    lines.append('        score_penalty [label="기동 점수 감점\\n(-0.3)", shape=ellipse, fillcolor="#7f1d1d", color="#f85149", fontcolor="#ff7b72"];')
    lines.append('        score_bonus [label="방어 유리\\n(+0.2)", shape=ellipse, fillcolor="#112211", color="#3fb950", fontcolor="#c9d1d9"];')
    lines.append("    }")
    lines.append("")
    lines.append("    # Mapping Links (Source -> Ontology) - 예시 연결")
    lines.append("    # 실제 매핑은 복잡하므로 대표적인 연결만 표시")
    if len(source_tables) > 0:
        lines.append(f'    xls_0 -> onto_0 [label="매핑", color="#8b949e", style=dashed];')
    if len(source_tables) > 1:
        lines.append(f'    xls_1 -> onto_1 [label="매핑", color="#8b949e", style=dashed];')
    lines.append("")
    lines.append("    # Logic Links (Ontology -> Rules)")
    lines.append('    onto_0 -> rule_mobility [label="입력", color="#8b949e"];')
    lines.append('    onto_1 -> rule_mobility [label="입력", color="#8b949e"];')
    lines.append('    onto_2 -> rule_air [label="입력", color="#8b949e"];')
    lines.append("")
    lines.append("    # Result Links (Rules -> Outcome)")
    lines.append('    rule_mobility -> score_penalty [label="조건: 산악+기갑", color="#da3633", penwidth=2];')
    lines.append('    rule_mobility -> score_bonus [label="조건: 산악+보병", color="#238636", penwidth=2];')
    lines.append("}")
    
    return "\n".join(lines)

def _render_table_relationship_mapping(orchestrator):
    """테이블 관계 매핑 시각화"""
    try:
        # 1. relation_mappings.json 로드
        base_dir = Path(__file__).parent.parent.parent
        relation_mapping_path = base_dir / "metadata" / "relation_mappings.json"
        
        if not relation_mapping_path.exists():
            st.error(f"관계 매핑 파일을 찾을 수 없습니다: {relation_mapping_path}")
            return
        
        with open(relation_mapping_path, 'r', encoding='utf-8') as f:
            relation_mappings = json.load(f)
        
        # 2. schema_registry에서 테이블 목록 가져오기
        ontology_manager = orchestrator.core.enhanced_ontology_manager
        available_tables = list(ontology_manager.schema_registry.keys())
        
        if not available_tables:
            st.warning("등록된 테이블이 없습니다.")
            return
        
        # 3. 테이블 선택
        selected_table = st.selectbox(
            "분석할 테이블 선택",
            options=available_tables,
            key="table_relationship_selector",
            help="테이블을 선택하면 해당 테이블의 컬럼들이 다른 테이블들과 맺는 관계를 시각화합니다."
        )
        
        if not selected_table:
            return
        
        # 4. 선택된 테이블의 관계 추출
        table_relations = relation_mappings.get(selected_table, {})
        
        if not table_relations:
            st.info(f"'{selected_table}' 테이블에는 정의된 관계가 없습니다.")
            return
        
        # 5. 관계 정보 표시
        st.markdown(f"#### 📊 '{selected_table}' 테이블의 관계 매핑")
        
        # 관계 유형별로 분류
        simple_fk_relations = []  # 단순 FK 관계
        dynamic_fk_relations = []  # 동적 FK 관계
        inference_relations = []  # 추론 관계
        
        for col_name, relation_info in table_relations.items():
            if isinstance(relation_info, dict):
                if relation_info.get('dynamic'):
                    dynamic_fk_relations.append((col_name, relation_info))
                elif relation_info.get('target') == '동적':
                    dynamic_fk_relations.append((col_name, relation_info))
                elif col_name.startswith('추론:'):
                    inference_relations.append((col_name, relation_info))
                elif 'target' in relation_info:
                    simple_fk_relations.append((col_name, relation_info))
            elif isinstance(relation_info, str):
                # 단순 문자열인 경우 타겟 테이블명으로 간주
                simple_fk_relations.append((col_name, {'target': relation_info}))
        
        # 6. Graphviz 다이어그램 생성
        dot_lines = [
            "digraph TableRelations {",
            "    # TABLE_RELATIONSHIP_MAPPING",
            "    rankdir=LR;",
            '    node [shape=box, style="filled,rounded", fontname="Malgun Gothic"];',
            '    edge [fontname="Malgun Gothic", fontsize=9];',
            '    bgcolor="transparent";',
            "",
            f'    # 중심 테이블',
            f'    center_table [label="{selected_table}\\n(중심 테이블)", fillcolor="#1f2937", color="#388bfd", fontcolor="#58a6ff", penwidth=3];',
            "",
        ]
        
        # 관계별 노드 및 엣지 추가
        node_counter = 0
        target_tables = set()
        
        # 단순 FK 관계
        for col_name, rel_info in simple_fk_relations:
            target_table = rel_info.get('target', '')
            if target_table and target_table != '동적':
                relation_name = rel_info.get('relation', f'has{target_table}')
                target_tables.add(target_table)
                node_id = f"target_{node_counter}"
                dot_lines.append(f'    {node_id} [label="{target_table}", fillcolor="#112211", color="#3fb950", fontcolor="#c9d1d9"];')
                dot_lines.append(f'    center_table -> {node_id} [label="{col_name}\\n({relation_name})", color="#3fb950", penwidth=2];')
                node_counter += 1
        
        # 동적 FK 관계
        for col_name, rel_info in dynamic_fk_relations:
            type_mapping = rel_info.get('type_mapping', {})
            relation_name = rel_info.get('relation', 'appliesTo')
            for type_val, target_table in type_mapping.items():
                if target_table and target_table != '동적':
                    target_tables.add(f"{target_table}({type_val})")
                    node_id = f"dynamic_{node_counter}"
                    dot_lines.append(f'    {node_id} [label="{target_table}\\n({type_val})", fillcolor="#7f1d1d", color="#f85149", fontcolor="#ff7b72"];')
                    dot_lines.append(f'    center_table -> {node_id} [label="{col_name}\\n({relation_name})", color="#f85149", style=dashed, penwidth=1.5];')
                    node_counter += 1
        
        # 추론 관계
        for col_name, rel_info in inference_relations:
            target_table = rel_info.get('target', '')
            confidence = rel_info.get('confidence', 0.8)
            if target_table:
                target_tables.add(f"{target_table}(추론)")
                node_id = f"inference_{node_counter}"
                dot_lines.append(f'    {node_id} [label="{target_table}\\n(추론, {confidence:.0%})", fillcolor="#1e3a8a", color="#58a6ff", fontcolor="#c9d1d9", style=dashed];')
                relation_name = col_name.replace('추론:', '')
                dot_lines.append(f'    center_table -> {node_id} [label="{col_name}\\n({relation_name})", color="#58a6ff", style=dotted, penwidth=1];')
                node_counter += 1
        
        dot_lines.append("}")
        
        # 7. 그래프 표시
        dot_code = "\n".join(dot_lines)
        st.graphviz_chart(dot_code, use_container_width=True)
        
        # 8. 관계 상세 정보 표시
        st.markdown("#### 📋 관계 상세 정보")
        
        if simple_fk_relations:
            with st.expander("🔗 단순 외래키 관계 (Simple FK)", expanded=True):
                for col_name, rel_info in simple_fk_relations:
                    target_table = rel_info.get('target', '')
                    relation_name = rel_info.get('relation', f'has{target_table}')
                    st.markdown(f"- **컬럼**: `{col_name}` → **타겟 테이블**: `{target_table}` (관계: `{relation_name}`)")
        
        if dynamic_fk_relations:
            with st.expander("🔄 동적 외래키 관계 (Dynamic FK)", expanded=True):
                for col_name, rel_info in dynamic_fk_relations:
                    relation_name = rel_info.get('relation', 'appliesTo')
                    type_column = rel_info.get('type_column', '')
                    type_mapping = rel_info.get('type_mapping', {})
                    st.markdown(f"- **컬럼**: `{col_name}` (타입 컬럼: `{type_column}`)")
                    st.markdown(f"  - **관계명**: `{relation_name}`")
                    st.markdown("  - **타입별 타겟 테이블**:")
                    for type_val, target_table in type_mapping.items():
                        st.markdown(f"    - `{type_val}` → `{target_table}`")
        
        if inference_relations:
            with st.expander("🧠 추론 관계 (Inferred Relationship)", expanded=True):
                for col_name, rel_info in inference_relations:
                    target_table = rel_info.get('target', '')
                    confidence = rel_info.get('confidence', 0.8)
                    column = rel_info.get('column', '')
                    relation_name = col_name.replace('추론:', '')
                    st.markdown(f"- **컬럼**: `{column}` → **타겟 테이블**: `{target_table}`")
                    st.markdown(f"  - **관계명**: `{relation_name}` (신뢰도: {confidence:.0%})")
        
        # 9. 통계 정보
        st.markdown("#### 📊 관계 통계")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("단순 FK 관계", len(simple_fk_relations))
        with col2:
            st.metric("동적 FK 관계", len(dynamic_fk_relations))
        with col3:
            st.metric("추론 관계", len(inference_relations))
        
    except Exception as e:
        st.error(f"테이블 관계 매핑 시각화 중 오류 발생: {str(e)}")
        import traceback
        with st.expander("상세 오류 정보"):
            st.code(traceback.format_exc())
