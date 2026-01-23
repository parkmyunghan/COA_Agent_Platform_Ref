# ui/components/table_column_relationship_viewer.py
# -*- coding: utf-8 -*-
"""
테이블-컬럼 관계 네트워크 시각화 컴포넌트
모든 테이블의 컬럼들 간의 관계를 인터랙티브 지식그래프로 표시
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
import pandas as pd


def render_table_column_relationship_viewer(orchestrator):
    """
    테이블-컬럼 관계 네트워크 시각화
    
    Args:
        orchestrator: Orchestrator 인스턴스
    """
    st.markdown("### 🔗 테이블-컬럼 관계 네트워크")
    st.info("💡 **모든 테이블의 컬럼들이 다른 테이블과 맺는 관계**를 인터랙티브 네트워크 그래프로 시각화합니다.")
    
    try:
        # 1. 관계 데이터 수집
        graph_data = _build_table_column_relationship_graph(orchestrator)
        
        if not graph_data or not graph_data.get("nodes"):
            st.warning("관계 데이터가 없습니다. relation_mappings.json 파일을 확인하세요.")
            return
        
        # 2. 통계 정보 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("테이블 수", len([n for n in graph_data["nodes"] if n.get("type") == "table"]))
        with col2:
            st.metric("컬럼 수", len([n for n in graph_data["nodes"] if n.get("type") == "column"]))
        with col3:
            st.metric("관계 수", len(graph_data.get("links", [])))
        with col4:
            relation_types = set(l.get("relation_type", "") for l in graph_data.get("links", []))
            st.metric("관계 유형", len(relation_types))
        
        # 3. 필터 옵션
        st.divider()
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # 테이블 필터
            all_tables = sorted([n["label"] for n in graph_data["nodes"] if n.get("type") == "table"])
            selected_tables = st.multiselect(
                "테이블 필터",
                options=all_tables,
                default=[],
                help="선택한 테이블과 관련된 관계만 표시합니다."
            )
        
        with filter_col2:
            # 관계 유형 필터
            all_relation_types = sorted(list(relation_types))
            selected_relation_types = st.multiselect(
                "관계 유형 필터",
                options=all_relation_types,
                default=all_relation_types,
                help="선택한 관계 유형만 표시합니다."
            )
        
        with filter_col3:
            # 레이아웃 선택
            layout_mode = st.selectbox(
                "레이아웃 모드",
                options=["force", "hierarchical", "circular"],
                index=0,
                help="그래프 레이아웃 방식을 선택합니다."
            )
        
        # 4. 필터링된 데이터 생성
        filtered_data = _filter_graph_data(
            graph_data, 
            selected_tables, 
            selected_relation_types
        )
        
        # 필터링된 데이터 검증
        if not filtered_data.get("nodes") or not filtered_data.get("links"):
            st.warning("선택한 필터 조건에 해당하는 관계가 없습니다. 필터를 조정해주세요.")
            # 필터링 전 데이터로 표시
            filtered_data = graph_data
        
        # 5. D3.js 기반 네트워크 그래프 생성
        html_content = _generate_network_graph_html(filtered_data, layout_mode)
        
        # 6. 그래프 표시
        components.html(html_content, height=800, scrolling=True)
        
        # 7. 관계 상세 정보 테이블
        st.divider()
        st.markdown("#### 📋 관계 상세 정보")
        
        with st.expander("전체 관계 목록", expanded=False):
            relations_df = _build_relations_dataframe(graph_data)
            if not relations_df.empty:
                st.dataframe(relations_df, use_container_width=True, hide_index=True)
            else:
                st.info("관계 데이터가 없습니다.")
        
    except Exception as e:
        st.error(f"테이블-컬럼 관계 시각화 중 오류 발생: {str(e)}")
        import traceback
        with st.expander("상세 오류 정보"):
            st.code(traceback.format_exc())


def _build_table_column_relationship_graph(orchestrator) -> Dict:
    """
    테이블-컬럼 관계 그래프 데이터 생성
    
    Returns:
        {
            "nodes": [{"id": str, "label": str, "type": str, "group": str, ...}],
            "links": [{"source": str, "target": str, "relation": str, "relation_type": str, ...}]
        }
    """
    nodes = []
    links = []
    node_id_set = set()
    
    # 1. relation_mappings.json 로드
    base_dir = Path(__file__).parent.parent.parent
    relation_mapping_path = base_dir / "metadata" / "relation_mappings.json"
    
    if not relation_mapping_path.exists():
        return {"nodes": [], "links": []}
    
    with open(relation_mapping_path, 'r', encoding='utf-8') as f:
        relation_mappings = json.load(f)
    
    # 2. schema_registry에서 테이블 정보 가져오기
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    schema_registry = ontology_manager.schema_registry if ontology_manager else {}
    
    # 3. 노드 생성: 테이블 노드
    for table_name in schema_registry.keys():
        table_id = f"table:{table_name}"
        if table_id not in node_id_set:
            nodes.append({
                "id": table_id,
                "label": table_name,
                "type": "table",
                "group": "table",
                "size": 20,
                "color": "#388bfd"
            })
            node_id_set.add(table_id)
    
    # 4. 노드 및 링크 생성: 컬럼과 관계
    for src_table, table_relations in relation_mappings.items():
        # 소스 테이블 노드 확인
        src_table_id = f"table:{src_table}"
        if src_table_id not in node_id_set:
            nodes.append({
                "id": src_table_id,
                "label": src_table,
                "type": "table",
                "group": "table",
                "size": 20,
                "color": "#388bfd"
            })
            node_id_set.add(src_table_id)
        
        # 컬럼별 관계 처리
        for col_name, relation_info in table_relations.items():
            # 컬럼 노드 생성
            col_id = f"column:{src_table}:{col_name}"
            if col_id not in node_id_set:
                nodes.append({
                    "id": col_id,
                    "label": f"{src_table}.{col_name}",
                    "type": "column",
                    "group": "column",
                    "size": 10,
                    "color": "#58a6ff",
                    "table": src_table
                })
                node_id_set.add(col_id)
            
            # 컬럼 → 테이블 링크
            links.append({
                "source": col_id,
                "target": src_table_id,
                "relation": "belongsTo",
                "relation_type": "belongsTo",
                "value": 1,
                "color": "#8b949e"
            })
            
            # 관계 정보 처리
            if isinstance(relation_info, dict):
                # 동적 FK 관계
                if relation_info.get('dynamic') or relation_info.get('target') == '동적':
                    type_mapping = relation_info.get('type_mapping', {})
                    relation_name = relation_info.get('relation', 'appliesTo')
                    for type_val, target_table in type_mapping.items():
                        target_table_id = f"table:{target_table}"
                        if target_table_id not in node_id_set:
                            nodes.append({
                                "id": target_table_id,
                                "label": target_table,
                                "type": "table",
                                "group": "table",
                                "size": 20,
                                "color": "#388bfd"
                            })
                            node_id_set.add(target_table_id)
                        
                        links.append({
                            "source": col_id,
                            "target": target_table_id,
                            "relation": relation_name,
                            "relation_type": "dynamic_fk",
                            "value": 2,
                            "color": "#f85149",
                            "label": f"{relation_name} ({type_val})",
                            "type_value": type_val
                        })
                
                # 추론 관계
                elif col_name.startswith('추론:'):
                    target_table = relation_info.get('target', '')
                    confidence = relation_info.get('confidence', 0.8)
                    if target_table:
                        target_table_id = f"table:{target_table}"
                        if target_table_id not in node_id_set:
                            nodes.append({
                                "id": target_table_id,
                                "label": target_table,
                                "type": "table",
                                "group": "table",
                                "size": 20,
                                "color": "#388bfd"
                            })
                            node_id_set.add(target_table_id)
                        
                        relation_name = col_name.replace('추론:', '')
                        links.append({
                            "source": col_id,
                            "target": target_table_id,
                            "relation": relation_name,
                            "relation_type": "inference",
                            "value": 1.5,
                            "color": "#58a6ff",
                            "label": f"{relation_name} ({confidence:.0%})",
                            "confidence": confidence
                        })
                
                # 단순 FK 관계
                elif 'target' in relation_info:
                    target_table = relation_info.get('target', '')
                    relation_name = relation_info.get('relation', f'has{target_table}')
                    if target_table and target_table != '동적':
                        target_table_id = f"table:{target_table}"
                        if target_table_id not in node_id_set:
                            nodes.append({
                                "id": target_table_id,
                                "label": target_table,
                                "type": "table",
                                "group": "table",
                                "size": 20,
                                "color": "#388bfd"
                            })
                            node_id_set.add(target_table_id)
                        
                        links.append({
                            "source": col_id,
                            "target": target_table_id,
                            "relation": relation_name,
                            "relation_type": "simple_fk",
                            "value": 2,
                            "color": "#3fb950",
                            "label": relation_name
                        })
            
            # 단순 문자열인 경우 (하위 호환성)
            elif isinstance(relation_info, str):
                target_table = relation_info
                target_table_id = f"table:{target_table}"
                if target_table_id not in node_id_set:
                    nodes.append({
                        "id": target_table_id,
                        "label": target_table,
                        "type": "table",
                        "group": "table",
                        "size": 20,
                        "color": "#388bfd"
                    })
                    node_id_set.add(target_table_id)
                
                links.append({
                    "source": col_id,
                    "target": target_table_id,
                    "relation": f"has{target_table}",
                    "relation_type": "simple_fk",
                    "value": 2,
                    "color": "#3fb950",
                    "label": f"has{target_table}"
                })
    
    return {"nodes": nodes, "links": links}


def _filter_graph_data(graph_data: Dict, selected_tables: List[str], selected_relation_types: List[str]) -> Dict:
    """그래프 데이터 필터링"""
    all_relation_types = set(l.get("relation_type") for l in graph_data.get("links", []))
    
    # 필터가 없으면 전체 데이터 반환
    if not selected_tables and set(selected_relation_types) == all_relation_types:
        return graph_data
    
    # 선택된 테이블과 관련된 노드 찾기 (반복적으로 확장)
    relevant_nodes = set()
    if selected_tables:
        # 초기 노드 추가: 선택된 테이블과 그 컬럼들
        for table in selected_tables:
            table_id = f"table:{table}"
            relevant_nodes.add(table_id)
            # 해당 테이블의 컬럼들 추가
            for node in graph_data["nodes"]:
                if node.get("type") == "column" and node.get("table") == table:
                    relevant_nodes.add(node["id"])
        
        # 연결된 모든 노드를 찾기 위해 반복적으로 확장
        changed = True
        while changed:
            changed = False
            for link in graph_data.get("links", []):
                source = link.get("source", "")
                target = link.get("target", "")
                
                # relevant_nodes에 포함된 노드와 연결된 노드 추가
                if source in relevant_nodes and target not in relevant_nodes:
                    relevant_nodes.add(target)
                    changed = True
                if target in relevant_nodes and source not in relevant_nodes:
                    relevant_nodes.add(source)
                    changed = True
    
    # 필터링된 링크
    filtered_links = []
    for link in graph_data.get("links", []):
        # 관계 유형 필터
        if link.get("relation_type") not in selected_relation_types:
            continue
        
        # 테이블 필터
        if selected_tables:
            source = link.get("source", "")
            target = link.get("target", "")
            if source not in relevant_nodes or target not in relevant_nodes:
                continue
        
        filtered_links.append(link)
    
    # 필터링된 노드 (필터링된 링크에 포함된 노드만)
    if selected_tables:
        # 필터링된 링크에 사용된 노드만 포함
        nodes_in_links = set()
        for link in filtered_links:
            nodes_in_links.add(link.get("source"))
            nodes_in_links.add(link.get("target"))
        
        filtered_nodes = [n for n in graph_data["nodes"] if n["id"] in nodes_in_links]
    else:
        filtered_nodes = graph_data["nodes"]
    
    return {"nodes": filtered_nodes, "links": filtered_links}


def _build_relations_dataframe(graph_data: Dict) -> pd.DataFrame:
    """관계 정보를 DataFrame으로 변환"""
    relations = []
    for link in graph_data.get("links", []):
        if link.get("relation_type") == "belongsTo":
            continue  # 컬럼-테이블 소속 관계는 제외
        
        source = link.get("source", "").replace("column:", "").replace("table:", "")
        target = link.get("target", "").replace("table:", "")
        relation = link.get("relation", "")
        relation_type = link.get("relation_type", "")
        
        relations.append({
            "소스": source,
            "관계": relation,
            "타겟": target,
            "관계 유형": relation_type,
            "라벨": link.get("label", relation)
        })
    
    return pd.DataFrame(relations)


def _generate_network_graph_html(graph_data: Dict, layout_mode: str = "force") -> str:
    """D3.js 기반 네트워크 그래프 HTML 생성"""
    nodes_json = json.dumps(graph_data.get("nodes", []), ensure_ascii=False)
    links_json = json.dumps(graph_data.get("links", []), ensure_ascii=False)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 20px;
                font-family: 'Malgun Gothic', sans-serif;
                background: #0e1117;
                color: #c9d1d9;
            }}
            .node {{
                cursor: pointer;
            }}
            .node circle {{
                stroke: #30363d;
                stroke-width: 2px;
            }}
            .link {{
                fill: none;
                stroke-opacity: 0.6;
            }}
            .link-label {{
                font-size: 10px;
                fill: #8b949e;
                pointer-events: none;
            }}
            .node-label {{
                font-size: 11px;
                fill: #c9d1d9;
                pointer-events: none;
                text-anchor: middle;
            }}
        </style>
    </head>
    <body>
        <div id="graph-container"></div>
        <script>
            const nodes = {nodes_json};
            const links = {links_json};
            const layoutMode = "{layout_mode}";
            
            const width = window.innerWidth - 40;
            const height = 750;
            
            const svg = d3.select("#graph-container")
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            const simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(links).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            if (layoutMode === "hierarchical") {{
                simulation.force("y", d3.forceY().y(d => {{
                    if (d.type === "table") return height * 0.2;
                    return height * 0.6;
                }}));
            }}
            
            const link = svg.append("g")
                .selectAll("line")
                .data(links)
                .enter().append("line")
                .attr("class", "link")
                .attr("stroke", d => d.color || "#8b949e")
                .attr("stroke-width", d => Math.sqrt(d.value || 1))
                .attr("stroke-dasharray", d => d.relation_type === "inference" ? "5,5" : "none");
            
            const linkLabels = svg.append("g")
                .selectAll("text")
                .data(links.filter(d => d.label))
                .enter().append("text")
                .attr("class", "link-label")
                .text(d => d.label);
            
            const node = svg.append("g")
                .selectAll("g")
                .data(nodes)
                .enter().append("g")
                .attr("class", "node")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            node.append("circle")
                .attr("r", d => d.size || 10)
                .attr("fill", d => d.color || "#388bfd");
            
            node.append("text")
                .attr("class", "node-label")
                .attr("dy", d => (d.size || 10) + 15)
                .text(d => d.label);
            
            node.append("title")
                .text(d => `${{d.label}} (${{d.type}})`);
            
            simulation.on("tick", () => {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                linkLabels
                    .attr("x", d => (d.source.x + d.target.x) / 2)
                    .attr("y", d => (d.source.y + d.target.y) / 2);
                
                node
                    .attr("transform", d => `translate(${{d.x}},${{d.y}})`);
            }});
            
            function dragstarted(event, d) {{
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }}
            
            function dragged(event, d) {{
                d.fx = event.x;
                d.fy = event.y;
            }}
            
            function dragended(event, d) {{
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }}
        </script>
    </body>
    </html>
    """
    return html

