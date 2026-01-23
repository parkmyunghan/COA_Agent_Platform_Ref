# ui/components/graph_viewer.py
# -*- coding: utf-8 -*-
"""
RDF 그래프 시각화 컴포넌트 (노드 클릭 이벤트 포함)
"""
import streamlit as st
import streamlit.components.v1 as components
from rdflib import Graph
import json
import os
import hashlib
import colorsys
import hashlib
import colorsys


def render_graph(core, on_node_click=None, show_analysis=False, graph_data=None):
    """
    온톨로지 그래프 시각화 (ABox/TBox 구분 지원)
    
    Args:
        core: CorePipeline 인스턴스
        on_node_click: 노드 클릭 시 호출할 콜백 함수 (node_label, core)
        show_analysis: 그래프 분석 패널 표시 여부 (기본: False)
        graph_data: 외부에서 제공하는 그래프 데이터 (선택 사항)
    """
    st.markdown("### 🕸 온톨로지 기반 지식그래프")
    
    # Enhanced Ontology Manager가 있으면 그래프 동기화 확인 (2단계와 3단계에서 동일한 그래프 보장)
    if hasattr(core, 'enhanced_ontology_manager') and core.enhanced_ontology_manager:
        enhanced_om = core.enhanced_ontology_manager
        if enhanced_om.graph is not None:
            # Enhanced 그래프를 core.ontology_manager.graph에 동기화
            core.ontology_manager.graph = enhanced_om.graph
    
    graph = core.ontology_manager.graph
    
    if graph is None or len(list(graph.triples((None, None, None)))) == 0:
        st.info("그래프가 생성되지 않았습니다. 데이터를 로드하고 Agent를 실행하세요.")
        
        # 그래프 생성 버튼
        if st.button("🔄 그래프 생성"):
            try:
                data = core.data_manager.load_all()
                graph = core.ontology_manager.build_from_data(data)
                if graph:
                    st.success(f"✅ 그래프 생성 완료: {len(list(graph.triples((None, None, None))))} triples")
                    st.rerun()
            except Exception as e:
                st.error(f"그래프 생성 실패: {e}")
        return
    
    # ABox/TBox 구분 기능 추가
    try:
        # 구조화된 그래프 데이터 가져오기 (외부 데이터가 없으면 생성)
        if graph_data is None:
            graph_data = core.ontology_manager.to_json()
        
        if graph_data and (graph_data.get("instances", {}).get("nodes") or graph_data.get("schema", {}).get("nodes")):
            # 그래프 타입 선택
            graph_mode = st.radio(
                "그래프 타입",
                ["인스턴스 그래프 (ABox)", "스키마 그래프 (TBox)"],
                horizontal=True,
                key="basic_graph_mode"
            )
            
            use_instances = graph_mode == "인스턴스 그래프 (ABox)"
            data = graph_data["instances"] if use_instances else graph_data["schema"]
            
            # 구조화된 데이터에서 노드와 엣지 추출
            nodes_list = []
            edges = []
            
            # 노드 변환
            for node in data.get("nodes", []):
                node_id = node.get("id", "")
                node_label = node.get("label", node_id)
                group = node.get("group", "기타")
                
                nodes_list.append({
                    "id": node_id,
                    "label": node_label,
                    "group": group,
                    "color": _get_node_color_by_group(group)
                })
            
            # 엣지 변환
            for link in data.get("links", []):
                source = link.get("source", "")
                target = link.get("target", "")
                relation = link.get("relation", "")
                
                edges.append({
                    "from": source,
                    "to": target,
                    "label": relation,
                    "color": _get_edge_color_by_relation(relation)
                })
            
        else:
            # 구조화된 데이터가 없으면 기존 방식 사용
            st.info("⚠️ 구조화된 그래프 데이터를 사용할 수 없어 기본 모드로 표시합니다.")
            graph_mode = None
            nodes_list, edges = _extract_graph_from_triples(graph)
            
    except Exception as e:
        # 오류 발생 시 기존 방식으로 폴백
        st.warning(f"구조화된 그래프 데이터 로드 실패: {e}. 기본 모드로 표시합니다.")
        graph_mode = None
        nodes_list, edges = _extract_graph_from_triples(graph)
    
    # 노드 선택 UI는 제거 (RAG 검색은 노드 정보 패널에서 수행)
    
    # 최대 표시 노드 수 설정 (사용자 조정 가능)
    MAX_NODES_DEFAULT = 100
    total_nodes = len(nodes_list)
    
    # 슬라이더 표시 (노드가 50개 이상일 때만)
    if total_nodes >= 50:
        # 슬라이더 범위 계산
        min_val = 50
        max_val = min(1000, total_nodes)  # 최대 1000개 또는 전체 노드 수 중 작은 값
        
        # step 크기 동적 조정 (노드 수에 따라)
        if total_nodes <= 200:
            step_size = 10  # 노드가 적을 때는 10 단위
        elif total_nodes <= 500:
            step_size = 25  # 중간일 때는 25 단위
        else:
            step_size = 50  # 많을 때는 50 단위
        
        # 세션 상태에서 값 가져오기 또는 초기화
        if "max_graph_nodes" not in st.session_state:
            st.session_state.max_graph_nodes = min(MAX_NODES_DEFAULT, max_val)
        
        # 현재 값이 범위를 벗어나면 조정
        current_val = st.session_state.max_graph_nodes
        if current_val < min_val:
            current_val = min_val
        elif current_val > max_val:
            current_val = max_val
        else:
            # step 단위로 반올림
            current_val = ((current_val + step_size // 2) // step_size) * step_size
            if current_val < min_val:
                current_val = min_val
            elif current_val > max_val:
                current_val = max_val
        
        # 세션 상태 업데이트 (범위 조정된 값)
        st.session_state.max_graph_nodes = current_val
        
        # key를 사용할 때는 value 파라미터를 사용하지 않음 (세션 상태에서 자동으로 가져옴)
        max_nodes = st.slider(
            "최대 표시 노드 수",
            min_value=min_val,
            max_value=max_val,
            step=step_size,  # 동적 step 사용
            key="max_graph_nodes",
            help=f"그래프에 {total_nodes}개 노드가 있습니다. 표시할 노드 수를 조정하세요."
        )
        
        if total_nodes > max_nodes:
            st.warning(f"그래프가 너무 큽니다 ({total_nodes}개 노드). 처음 {max_nodes}개만 표시합니다.")
            nodes_list = nodes_list[:max_nodes]
            node_ids = {n["id"] for n in nodes_list}
            edges = [e for e in edges if e["from"] in node_ids and e["to"] in node_ids]
    else:
        # 노드가 50개 미만이면 모든 노드 표시
        max_nodes = total_nodes
    
    # 그래프 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("노드 수", len(nodes_list))
    with col2:
        st.metric("엣지 수", len(edges))
    with col3:
        if graph_mode:
            groups = set(n.get("group", "") for n in nodes_list)
            st.metric("그룹 수", len(groups))
        else:
            st.metric("Triples", len(list(graph.triples((None, None, None)))))
    
    # 범례 표시 (그룹 정보가 있는 경우) - 색상 박스 + 모양 아이콘 + 텍스트
    if nodes_list and len(nodes_list) > 0 and "group" in nodes_list[0]:
        groups = {}
        for node in nodes_list:
            group = node.get("group", "기타")
            if group not in groups:
                groups[group] = {"count": 0, "color": node.get("color", "#99ccff")}
            groups[group]["count"] += 1
        
        if groups:
            st.markdown("#### 📊 범례")
            # 그룹을 4열로 배치 (더 컴팩트하게)
            cols = st.columns(min(len(groups), 4))
            for i, (group, info) in enumerate(sorted(groups.items())):
                with cols[i % len(cols)]:
                    color = info["color"]
                    count = info["count"]
                    # 색상 박스 + 모양 아이콘 + 텍스트를 표시 (컴팩트 버전)
                    # Pyvis는 box 모양 사용 (■)
                    # 컬럼을 사용해서 색상 박스와 텍스트를 분리
                    legend_col1, legend_col2 = st.columns([1, 5])
                    with legend_col1:
                        # 색상 박스 표시 (HTML 사용, 크기 축소)
                        st.markdown(
                            f'<div style="width: 12px; height: 12px; background-color: {color}; border: 1px solid #fff; border-radius: 2px; margin-top: 4px;"></div>',
                            unsafe_allow_html=True
                        )
                    with legend_col2:
                        # 텍스트 표시 (작은 폰트)
                        st.markdown(f'<span style="font-size: 0.85em;">**{group}**: {count}개</span>', unsafe_allow_html=True)
    
    # 그래프 시각화 옵션
    use_pyvis = st.checkbox("고급 그래프 뷰어 사용 (Pyvis)", value=True)
    
    if use_pyvis:
        try:
            from pyvis.network import Network
            import base64
            from pathlib import Path
            import re
            
            # [PERF] HTML 생성 로직을 캐싱하여 렌더링 속도 개선
            # 노드와 엣지 리스트는 딕셔너리 리스트이므로 해시 가능하지 않을 수 있음 -> 튜플로 변환 필요할 수도 있으나
            # st.cache_data는 기본적인 파이썬 타입에 대해 해싱을 지원함
            @st.cache_data(show_spinner=False, ttl=3600)
            def _generate_graph_html_cached(nodes_data, edges_data, height="500px"):
                net = Network(height=height, width="100%", directed=True, bgcolor="#0e1117")
                net.set_options("""
                {
                  "physics": {
                    "enabled": true,
                    "barnesHut": {
                      "gravitationalConstant": -2000,
                      "centralGravity": 0.1,
                      "springLength": 200,
                      "springConstant": 0.04
                    }
                  },
                  "interaction": {
                    "hover": true,
                    "tooltipDelay": 200
                  }
                }
                """)
                
                # 노드 추가
                for node in nodes_data:
                    net.add_node(
                        node.get("id", ""),
                        label=node.get("label", node.get("id", "")),
                        color=node.get("color", "#99ccff"),
                        shape="box"
                    )
                
                # 엣지 추가
                for edge in edges_data:
                    net.add_edge(
                        edge["from"],
                        edge["to"],
                        label=edge.get("label", ""),
                        color=edge.get("color", "#999999"),
                        arrows="to"
                    )
                
                # HTML 생성
                # save_graph 대신 직접 template 렌더링 혹은 generate_html 사용 권장되나
                # pyvis 0.3.x 에서는 save_graph나 html property 사용
                try:
                    # 임시 파일 경로
                    graph_html = "ui_graph_temp.html"
                    net.save_graph(graph_html)
                    
                    with open(graph_html, "r", encoding="utf-8") as f:
                        html_content = f.read()
                except:
                    # fallback
                    html_content = net.html
                
                return html_content

            # 캐시된 함수 호출
            html_content = _generate_graph_html_cached(nodes_list, edges, "500px")
            
            # CDN 링크를 로컬 파일로 교체 (캐싱하지 않는 부분 - 파일 시스템 의존)
            try:
                # 프로젝트 루트 경로 찾기
                current_dir = Path(__file__).parent
                # ui/components -> ui -> root
                project_root = current_dir.parent.parent
                
                vis_css_path = project_root / "lib" / "vis-9.1.2" / "vis-network.css"
                vis_js_path = project_root / "lib" / "vis-9.1.2" / "vis-network.min.js"
                
                if vis_css_path.exists() and vis_js_path.exists():
                     # CSS 파일 읽기
                    with open(vis_css_path, 'r', encoding='utf-8') as f:
                        vis_css_content = f.read()
                    
                    # JS 파일 읽기
                    with open(vis_js_path, 'rb') as f:
                        vis_js_content = f.read()
                    vis_js_base64 = base64.b64encode(vis_js_content).decode('utf-8')
                    
                    # CDN 링크를 인라인으로 교체
                    html_content = re.sub(
                        r'<link[^>]*href="https://cdnjs\.cloudflare\.com[^"]*vis-network[^"]*"[^>]*>',
                        f'<style>{vis_css_content}</style>',
                        html_content
                    )
                    html_content = re.sub(
                        r'<script[^>]*src="https://cdnjs\.cloudflare\.com[^"]*vis-network[^"]*"[^>]*></script>',
                        f'<script src="data:text/javascript;base64,{vis_js_base64}"></script>',
                        html_content
                    )
            except Exception as e:
                # 파일 처리 실패 시 원본 유지
                pass
            
            # Bootstrap CDN 제거 (필수 아님)
            html_content = re.sub(
                r'<link[^>]*href="https://cdn\.jsdelivr\.net[^"]*bootstrap[^"]*"[^>]*>',
                '',  # Bootstrap은 선택적이므로 제거 가능
                html_content
            )
            html_content = re.sub(
                r'<script[^>]*src="https://cdn\.jsdelivr\.net[^"]*bootstrap[^"]*"[^>]*></script>',
                '',  # Bootstrap JS도 제거
                html_content
            )
            
            components.html(html_content, height=510, scrolling=False)
            
        except ImportError:
            st.warning("pyvis가 설치되지 않았습니다. pip install pyvis")
            _render_simple_graph(nodes_list, edges)
    else:
        _render_simple_graph(nodes_list, edges)
    
    # 그래프 분석 패널 표시 (show_analysis가 True인 경우만)
    if show_analysis:
        try:
            st.divider()
            # [FIX] 분석 패널이 리렌더링될 때 화면 스크롤이 튀는 현상을 방지하기 위해 
            # Expander 대신 Checkbox를 사용하여 사용자가 명시적으로 요청할 때만 렌더링하도록 변경
            show_analysis_panel = st.checkbox("📊 그래프 분석 및 품질 평가 보기", value=False)
            
            if show_analysis_panel:
                with st.spinner("분석 중..."):
                    from ui.components.graph_analysis_panel import render_graph_analysis
                    
                    # graph_data 형식으로 변환
                    graph_data = {
                        "instances": {
                            "nodes": nodes_list,
                            "links": [{"source": e["from"], "target": e["to"], "relation": e.get("label", "")} for e in edges]
                        },
                        "schema": {
                            "nodes": [],
                            "links": []
                        }
                    }
                    
                    # graph_mode가 있으면 스키마 데이터도 포함
                    if graph_mode:
                        graph_data_from_json = core.ontology_manager.to_json()
                        if graph_data_from_json:
                            graph_data["schema"] = graph_data_from_json.get("schema", {"nodes": [], "links": []})
                    
                    current_mode = graph_mode if graph_mode else "인스턴스 그래프 (ABox)"
                    render_graph_analysis(core, graph_data, current_mode)
        except Exception as e:
            # 분석 패널 오류는 무시 (선택적 기능)
            pass


def _extract_graph_from_triples(graph):
    """기존 방식: RDF triples에서 직접 그래프 데이터 추출"""
    nodes = {}
    edges = []
    
    for s, p, o in graph:
        s_str = str(s)
        o_str = str(o)
        p_str = str(p)
        
        # 노드 추가
        if s_str not in nodes:
            label = s_str.split("#")[-1].split("/")[-1]
            nodes[s_str] = {
                "id": s_str,
                "label": label,
                "color": _get_node_color(s_str, graph)
            }
        
        if o_str not in nodes and not _is_literal(o_str):
            label = o_str.split("#")[-1].split("/")[-1]
            nodes[o_str] = {
                "id": o_str,
                "label": label,
                "color": _get_node_color(o_str, graph)
            }
        
        # 엣지 추가 (리터럴 제외)
        if not _is_literal(o_str):
            edges.append({
                "from": s_str,
                "to": o_str,
                "label": p_str.split("#")[-1].split("/")[-1],
                "color": _get_edge_color(p_str)
            })
    
    return list(nodes.values()), edges


def _extract_node_labels(graph):
    """그래프에서 노드 레이블 추출"""
    labels = set()
    for s, p, o in graph:
        s_str = str(s)
        o_str = str(o)
        
        if not _is_literal(s_str):
            label = s_str.split("#")[-1].split("/")[-1]
            labels.add(label)
        
        if not _is_literal(o_str):
            label = o_str.split("#")[-1].split("/")[-1]
            labels.add(label)
    
    return sorted(list(labels))


def _generate_color_for_group(group: str) -> str:
    """
    그룹명을 기반으로 일관된 색상을 생성 (해시 기반)
    강화뷰어와 동일한 로직 사용
    """
    # 스키마 그룹 색상 (고정)
    schema_colors = {
        "Class": "#9b59b6",
        "Property": "#e67e22",
        "Table": "#3498db",
        "Column": "#e74c3c",
    }
    if group in schema_colors:
        return schema_colors[group]
    
    # 레거시 그룹 색상 (하위 호환성)
    legacy_colors = {
        "위협상황": "#ff6b6b",
        "적군부대": "#ff4757",
        "아군부대": "#4ecdc4",
        "아군가용자산": "#45b7d1",
        "정보보고서": "#ffe66d",
        "보급상태": "#95e1d3",
        "기상상황": "#a8e6cf",
        "전력준비태세": "#ffd93d",
        "COA_라이브러리": "#6c5ce7",
        "부대": "#1f77b4",
        "작전": "#ff7f0e",
        "자산": "#2ca02c",
    }
    if group in legacy_colors:
        return legacy_colors[group]
    
    # 새로운 그룹은 해시 기반 색상 생성
    hash_obj = hashlib.md5(group.encode('utf-8'))
    hash_int = int(hash_obj.hexdigest()[:8], 16)
    
    hue = hash_int % 360
    saturation = 60 + (hash_int % 20)  # 60-80%
    lightness = 50 + (hash_int % 15)   # 50-65%
    
    rgb = colorsys.hls_to_rgb(hue/360, lightness/100, saturation/100)
    color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
    
    return color


def _get_node_color_by_group(group: str) -> str:
    """그룹별 노드 색상 결정 (동적 생성)"""
    return _generate_color_for_group(group)


def _get_edge_color_by_relation(relation: str) -> str:
    """관계별 엣지 색상 결정"""
    relation_colors = {
        "subClassOf": "#9b59b6",
        "hasColumn": "#3498db",
        "hasSuitableCOA": "#6c5ce7",
        "has위협상황": "#ff6b6b",
        "relatedTo": "#ff4757",
    }
    
    relation_lower = relation.lower()
    if "threat" in relation_lower or "위협" in relation_lower:
        return "#ff6b6b"
    elif "location" in relation_lower or "위치" in relation_lower:
        return "#95e1d3"
    elif "reliability" in relation_lower or "신뢰" in relation_lower:
        return "#ffe66d"
    elif "subclass" in relation_lower:
        return "#9b59b6"
    else:
        return relation_colors.get(relation, "#999999")


def _get_node_color(node_id, graph):
    """노드 색상 결정 (ThreatLevel 등에 따라) - 기존 호환성 유지"""
    node_str = str(node_id).lower()
    
    # 위협 관련 노드는 빨간색
    if "threat" in node_str or "enemy" in node_str:
        return "#ff6b6b"
    
    # 아군 관련 노드는 파란색
    if "friendly" in node_str or "unit" in node_str:
        return "#4ecdc4"
    
    # 첩보 관련 노드는 노란색
    if "intel" in node_str or "report" in node_str:
        return "#ffe66d"
    
    # 기본 색상
    return "#99ccff"


def _get_edge_color(predicate):
    """엣지 색상 결정"""
    pred_str = str(predicate).lower()
    
    if "threat" in pred_str:
        return "#ff6b6b"
    elif "location" in pred_str:
        return "#95e1d3"
    elif "reliability" in pred_str:
        return "#ffe66d"
    else:
        return "#999999"


def _is_literal(value):
    """리터럴 값인지 확인"""
    return isinstance(value, str) and (
        value.startswith('"') or 
        value.replace('.', '').replace('-', '').isdigit()
    )


def _render_simple_graph(nodes_list, edges):
    """간단한 그래프 표시 (pyvis 없을 때)"""
    st.markdown("#### 노드 목록")
    for node in nodes_list[:20]:  # 최대 20개만 표시
        st.text(f"• {node['label']}")
    
    if len(nodes_list) > 20:
        st.caption(f"... 및 {len(nodes_list) - 20}개 추가 노드")
    
    st.markdown("#### 관계 목록")
    for edge in edges[:20]:  # 최대 20개만 표시
        st.text(f"• {edge['label']}")
    
    if len(edges) > 20:
        st.caption(f"... 및 {len(edges) - 20}개 추가 관계")
