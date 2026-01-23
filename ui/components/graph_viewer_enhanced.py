# ui/components/graph_viewer_enhanced.py
# -*- coding: utf-8 -*-
"""
Enhanced Graph Viewer Component
현재 시스템의 D3.js 기반 지식그래프 시각화 통합
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import hashlib
import colorsys
from pathlib import Path
from typing import Dict, List, Optional, Callable


def render_enhanced_graph(core, use_reasoned_graph: bool = True, 
                         graph_data_path: Optional[str] = None,
                         on_node_click: Optional[Callable] = None,
                         show_analysis: bool = False,
                         graph_data: Optional[Dict] = None):
    """
    강화된 지식그래프 시각화 (현재 시스템 D3.js 기반)
    
    Args:
        core: CorePipeline 인스턴스
        use_reasoned_graph: 추론된 그래프 사용 여부
        graph_data_path: 그래프 데이터 파일 경로 (없으면 자동 생성)
        on_node_click: 노드 클릭 시 호출할 콜백 함수 (node_id, node_label, node_data)
        show_analysis: 그래프 분석 패널 표시 여부 (기본: False)
        graph_data: 외부에서 제공하는 그래프 데이터 (선택 사항, 가장 높은 우선순위)
    """
    st.markdown("### 🕸 지식그래프 시각화 (D3.js 기반)")
    
    # 디버깅 모드 토글
    debug_mode = st.checkbox("🔍 디버깅 모드 (그래프 데이터 생성 과정 확인)", key="debug_graph")
    
    # 그래프 데이터 로드 또는 생성
    if graph_data is not None:
        # 외부에서 전달된 데이터 사용 (필터링된 데이터 등)
        if debug_mode:
            st.info("외부에서 전달된 그래프 데이터를 사용합니다.")
    elif graph_data_path and os.path.exists(graph_data_path):
        # 기존 그래프 데이터 파일 사용
        try:
            with open(graph_data_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # JavaScript 변수에서 데이터 추출
                if 'window.__GRAPH_INSTANCES__' in content:
                    # graph_data.js 형식 파싱
                    instances_str = content.split('window.__GRAPH_INSTANCES__ = ')[1].split(';')[0]
                    schema_str = content.split('window.__GRAPH_SCHEMA__ = ')[1].split(';')[0]
                    instances = json.loads(instances_str)
                    schema = json.loads(schema_str)
                    graph_data = {"instances": instances, "schema": schema}
                else:
                    # JSON 형식
                    graph_data = json.loads(content)
        except Exception as e:
            st.warning(f"그래프 데이터 파일 로드 실패: {e}")
            graph_data = _generate_graph_data_from_ontology(core, use_reasoned_graph, debug_mode)
    else:
        # 온톨로지에서 그래프 데이터 생성
        graph_data = _generate_graph_data_from_ontology(core, use_reasoned_graph, debug_mode)
    
    if not graph_data or not graph_data.get("instances", {}).get("nodes"):
        st.info("그래프 데이터가 없습니다. 온톨로지를 생성하세요.")
        return
    
    # 그래프 모드 선택
    graph_mode = st.radio(
        "그래프 타입",
        ["인스턴스 그래프 (ABox)", "스키마 그래프 (TBox)"],
        horizontal=True
    )
    
    use_instances = graph_mode == "인스턴스 그래프 (ABox)"
    data = graph_data["instances"] if use_instances else graph_data["schema"]
    
    # 그래프 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("노드 수", len(data.get("nodes", [])))
    with col2:
        st.metric("관계 수", len(data.get("links", [])))
    with col3:
        groups = set(n.get("group", "") for n in data.get("nodes", []))
        st.metric("그룹 수", len(groups))
    
    # 범례 표시
    if data.get("nodes"):
        _render_legend(data["nodes"])
    
    # Streamlit UI의 그룹 선택 및 노드 선택 필터 제거됨
    # 모든 필터링은 HTML 내부 컨트롤에서 처리
    
    # D3.js 기반 그래프 시각화 (전체 graph_data 전달)
    html_content = _generate_d3_graph_html(graph_data, on_node_click)
    
    # 그래프 표시 영역과 버튼 영역
    col_graph, col_button = st.columns([4, 1])
    
    with col_graph:
        components.html(html_content, height=710, scrolling=False)
    
    with col_button:
        st.markdown("<br>", unsafe_allow_html=True)  # 여백
        
        # 로컬 브라우저로 열기 버튼
        if st.button("🪟 로컬 브라우저로 열기\n(권장)", width='stretch', 
                    help="그래프를 별도 브라우저 창에서 엽니다. 노드 클릭 시 정보를 확인할 수 있습니다."):
            graph_html_path = _save_graph_html(html_content, graph_mode)
            if graph_html_path:
                try:
                    import webbrowser
                    # 시스템 기본 브라우저로 열기
                    abs_path = os.path.abspath(graph_html_path)
                    file_url = f"file:///{abs_path.replace(os.sep, '/')}"
                    webbrowser.open(file_url)
                    st.success(f"✅ 브라우저에서 열었습니다!")
                    st.info(f"파일: {os.path.basename(graph_html_path)}")
                except Exception as e:
                    st.error(f"브라우저 열기 실패: {e}")
                    # 폴백: 파일 경로 표시
                    st.info(f"파일 경로: {graph_html_path}")
        
        # HTML 다운로드 버튼 (선택적)
        graph_html_path = _save_graph_html(html_content, graph_mode)
        if graph_html_path and os.path.exists(graph_html_path):
            with open(graph_html_path, 'rb') as f:
                st.download_button(
                    label="📥 HTML 다운로드",
                    data=f.read(),
                    file_name=os.path.basename(graph_html_path),
                    mime="text/html",
                    width='stretch'
                )
    
    # 그래프 분석 패널 표시 (show_analysis가 True인 경우만)
    if show_analysis:
        try:
            from ui.components.graph_analysis_panel import render_graph_analysis
            render_graph_analysis(core, graph_data, graph_mode)
        except Exception as e:
            st.warning(f"그래프 분석 패널 로드 실패: {e}")


def _generate_graph_data_from_ontology(core, use_reasoned_graph: bool, debug_mode: bool = False) -> Dict:
    """온톨로지에서 그래프 데이터 생성"""
    # TTL 파일에서 직접 로드 시도 (knowledge/ontology 경로 사용)
    ontology_path = core.config.get("ontology_path", "./knowledge/ontology")
    
    # 추론된 인스턴스 파일 우선 사용
    if use_reasoned_graph:
        inst_file = os.path.join(ontology_path, "instances_reasoned.ttl")
        if not os.path.exists(inst_file):
            inst_file = os.path.join(ontology_path, "instances.ttl")
    else:
        inst_file = os.path.join(ontology_path, "instances.ttl")
    
    onto_file = os.path.join(ontology_path, "schema.owl")
    
    # TTL 파일이 있으면 로드 (우선순위 1)
    if os.path.exists(inst_file) and os.path.exists(onto_file):
        try:
            import sys
            scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts")
            if scripts_path not in sys.path:
                sys.path.insert(0, scripts_path)
            from graph_loader import load_graph
            instances, schema, _ = load_graph(
                inst_path=inst_file,
                onto_path=onto_file,
                load_all_files=True  # 모든 파일 로드
            )
            # 디버깅 정보
            if debug_mode:
                st.info(f"📊 graph_loader 결과: 인스턴스 노드 {len(instances.get('nodes', []))}개, 링크 {len(instances.get('links', []))}개 / 스키마 노드 {len(schema.get('nodes', []))}개, 링크 {len(schema.get('links', []))}개")
            return {"instances": instances, "schema": schema}
        except ImportError as e:
            st.warning(f"graph_loader import 실패: {e}")
        except Exception as e:
            st.warning(f"TTL 파일 로드 실패: {e}")
            import traceback
            if debug_mode:
                st.code(traceback.format_exc())
    
    # 온톨로지 매니저에서 그래프 데이터 생성
    if core.ontology_manager.graph is None:
        return {}
    
    # Enhanced Ontology Manager가 있으면 사용 (2단계와 3단계에서 동일한 그래프 보장)
    if hasattr(core, 'enhanced_ontology_manager') and core.enhanced_ontology_manager:
        try:
            enhanced_om = core.enhanced_ontology_manager
            
            # 그래프 동기화: Enhanced Manager와 기본 Manager의 그래프를 동기화
            if enhanced_om.graph is not None:
                # Enhanced 그래프를 core.ontology_manager.graph에 할당
                core.ontology_manager.graph = enhanced_om.graph
            
            # Enhanced Manager의 to_json() 사용
            graph_data = core.enhanced_ontology_manager.to_json()
            if debug_mode:
                schema_nodes = len(graph_data.get("schema", {}).get("nodes", []))
                schema_links = len(graph_data.get("schema", {}).get("links", []))
                inst_nodes = len(graph_data.get("instances", {}).get("nodes", []))
                inst_links = len(graph_data.get("instances", {}).get("links", []))
                st.info(f"[DEBUG] Enhanced Ontology Manager.to_json() 결과: 스키마 노드 {schema_nodes}개, 링크 {schema_links}개 / 인스턴스 노드 {inst_nodes}개, 링크 {inst_links}개")
            return graph_data
        except Exception as e:
            st.warning(f"Enhanced Ontology Manager 사용 실패: {e}")
            if debug_mode:
                import traceback
                st.code(traceback.format_exc())
    
    # 기본 OntologyManager 사용
    try:
        graph_data = core.ontology_manager.to_json()
        # 디버깅 정보
        if debug_mode:
            inst_nodes = len(graph_data.get("instances", {}).get("nodes", []))
            inst_links = len(graph_data.get("instances", {}).get("links", []))
            schema_nodes = len(graph_data.get("schema", {}).get("nodes", []))
            schema_links = len(graph_data.get("schema", {}).get("links", []))
            st.info(f"📊 ontology_manager.to_json() 결과: 인스턴스 노드 {inst_nodes}개, 링크 {inst_links}개 / 스키마 노드 {schema_nodes}개, 링크 {schema_links}개")
        return graph_data
    except Exception as e:
        st.warning(f"그래프 데이터 생성 실패: {e}")
        import traceback
        if debug_mode:
            st.code(traceback.format_exc())
        return {}


# 스키마 그룹 색상 (고정 - OWL 표준)
_SCHEMA_GROUP_COLORS = {
    "Class": "#9b59b6",
    "Property": "#e67e22",
    "Table": "#3498db",
    "Column": "#e74c3c",
}

# 레거시 그룹 색상 (하위 호환성 유지, 선택적 사용)
_LEGACY_GROUP_COLORS = {
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
    
    # ✨ COA 타입별 고정 색상 (Week 1 개선)
    "DefenseCOA": "#3498db",       # 방어: 파랑
    "방어방책": "#3498db",
    "OffensiveCOA": "#e74c3c",     # 공격: 빨강
    "공격방책": "#e74c3c",
    "CounterAttackCOA": "#e67e22", # 반격: 주황
    "반격방책": "#e67e22",
    "PreemptiveCOA": "#9b59b6",    # 선제: 보라
    "선제방책": "#9b59b6",
    "DeterrenceCOA": "#2ecc71",    # 억제: 녹색
    "억제방책": "#2ecc71",
    "ManeuverCOA": "#1abc9c",      # 기동: 청록
    "기동방책": "#1abc9c",
    "InformationOpsCOA": "#f1c40f", # 정보: 노랑
    "정보방책": "#f1c40f",
}


def _generate_color_for_group(group: str, existing_colors: Dict[str, str] = None) -> str:
    """
    그룹명을 기반으로 일관된 색상을 생성 (해시 기반)
    데이터 변경 시에도 동일한 그룹은 동일한 색상 유지
    
    Args:
        group: 그룹명
        existing_colors: 기존 색상 매핑 (중복 방지)
    
    Returns:
        HEX 색상 코드
    """
    if existing_colors and group in existing_colors:
        return existing_colors[group]
    
    # 스키마 그룹은 고정 색상 사용
    if group in _SCHEMA_GROUP_COLORS:
        return _SCHEMA_GROUP_COLORS[group]
    
    # 레거시 그룹은 기존 색상 사용 (하위 호환성)
    if group in _LEGACY_GROUP_COLORS:
        return _LEGACY_GROUP_COLORS[group]
    
    # 새로운 그룹은 해시 기반 색상 생성
    # 해시를 사용하여 그룹명에 따라 일관된 색상 생성
    hash_obj = hashlib.md5(group.encode('utf-8'))
    hash_int = int(hash_obj.hexdigest()[:8], 16)
    
    # HSL 색상 공간 사용 (밝고 채도 높은 색상)
    hue = hash_int % 360
    saturation = 60 + (hash_int % 20)  # 60-80%
    lightness = 50 + (hash_int % 15)   # 50-65%
    
    # HSL to RGB 변환
    rgb = colorsys.hls_to_rgb(hue/360, lightness/100, saturation/100)
    color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
    
    return color


def _get_group_colors_from_data(nodes: List[Dict]) -> Dict[str, str]:
    """
    실제 데이터에서 그룹을 추출하고 색상 할당 (동적)
    
    Args:
        nodes: 노드 리스트
    
    Returns:
        그룹별 색상 매핑 딕셔너리
    """
    groups = set(node.get("group", "기타") for node in nodes)
    group_colors = {}
    
    # 모든 그룹에 대해 색상 할당
    for group in sorted(groups):
        group_colors[group] = _generate_color_for_group(group, group_colors)
    
    return group_colors


def _render_legend(nodes: List[Dict]):
    """범례 렌더링 - 색상 박스 + 모양 아이콘 + 텍스트"""
    # 그룹별 색상 매핑 (데이터에서 동적으로 생성)
    group_colors = _get_group_colors_from_data(nodes)
    
    groups = {}
    for node in nodes:
        group = node.get("group", "기타")
        if group not in groups:
            # 그룹별 색상 가져오기 (노드에 color가 있으면 사용, 없으면 매핑에서 찾기)
            node_color = node.get("color")
            if not node_color:
                node_color = group_colors.get(group, "#99ccff")
            groups[group] = {"count": 0, "color": node_color}
        groups[group]["count"] += 1
    
    if groups:
        st.markdown("#### 📊 범례")
        # 그룹을 4열로 배치 (더 컴팩트하게)
        cols = st.columns(min(len(groups), 4))
        for i, (group, info) in enumerate(sorted(groups.items())):
            with cols[i % len(cols)]:
                color = info["color"]
                count = info["count"]
                # 색상 원형 + 텍스트를 표시 (컴팩트 버전, D3.js는 circle 모양 사용)
                # 컬럼을 사용해서 색상 원형과 텍스트를 분리
                legend_col1, legend_col2 = st.columns([1, 5])
                with legend_col1:
                    # 색상 원형 표시 (HTML 사용, 크기 축소)
                    st.markdown(
                        f'<div style="width: 10px; height: 10px; background-color: {color}; border: 1px solid #fff; border-radius: 50%; margin-top: 4px;"></div>',
                        unsafe_allow_html=True
                    )
                with legend_col2:
                    # 텍스트 표시 (작은 폰트)
                    st.markdown(f'<span style="font-size: 0.85em;">**{group}**: {count}개</span>', unsafe_allow_html=True)


def _generate_d3_graph_html(graph_data: Dict, on_node_click: Optional[Callable] = None) -> str:
    """D3.js 기반 그래프 HTML 생성 (인스턴스와 스키마 그래프 모두 포함)"""
    # 로컬 D3.js 사용 (오프라인 지원)
    from pathlib import Path
    import base64
    
    # 프로젝트 루트 경로 찾기
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    d3_local_path = project_root / "lib" / "d3" / "d3.v7.min.js"
    
    # 로컬 파일이 있으면 읽어서 인라인으로 포함, 없으면 CDN (하위 호환성)
    if d3_local_path.exists():
        try:
            # 로컬 파일을 읽어서 base64로 인코딩하여 인라인으로 포함
            with open(d3_local_path, 'rb') as f:
                d3_content = f.read()
            d3_base64 = base64.b64encode(d3_content).decode('utf-8')
            d3_script = f'<script src="data:text/javascript;base64,{d3_base64}"></script>'
        except Exception as e:
            # 파일 읽기 실패 시 CDN 폴백
            d3_script = '<script src="https://d3js.org/d3.v7.min.js"></script>'
    else:
        # CDN 폴백 (인터넷 연결 시)
        d3_script = '<script src="https://d3js.org/d3.v7.min.js"></script>'
    
    # 인스턴스와 스키마 그래프 데이터 준비
    instances_data = graph_data.get("instances", {"nodes": [], "links": []})
    schema_data = graph_data.get("schema", {"nodes": [], "links": []})
    
    # 기본값: 인스턴스 그래프 사용
    initial_data = instances_data
    
    # 그룹별 색상 매핑 (인스턴스 데이터에서 동적으로 생성)
    all_nodes = instances_data.get("nodes", []) + schema_data.get("nodes", [])
    group_colors = _get_group_colors_from_data(all_nodes)
    
    # JavaScript 변수로 변환
    instances_json = json.dumps(instances_data, ensure_ascii=False)
    schema_json = json.dumps(schema_data, ensure_ascii=False)
    group_colors_json = json.dumps(group_colors, ensure_ascii=False)
    
    # 노드 정보 패널 HTML
    node_info_panel = f"""
        <!-- 노드 정보 패널 -->
        <div id="node-info-panel" style="
            position: fixed;
            top: 10px;
            right: 10px;
            width: 350px;
            max-height: 80vh;
            background: rgba(14, 17, 23, 0.98);
            border: 2px solid #1f77b4;
            border-radius: 8px;
            padding: 15px;
            color: white;
            font-family: Arial, sans-serif;
            font-size: 14px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px;">
                <h3 style="margin: 0; color: #1f77b4; font-size: 18px;">📊 노드 정보</h3>
                <button onclick="closeNodeInfo()" style="
                    background: #ff4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 12px;
                    cursor: pointer;
                    font-size: 12px;
                    font-weight: bold;
                ">✕ 닫기</button>
            </div>
            <div id="node-info-content">
                <p style="color: #aaa; text-align: center; margin: 20px 0;">노드를 클릭하여 정보를 확인하세요.</p>
            </div>
        </div>
        
        <script>
            // 노드 정보 패널 함수 (전역)
            function showNodeInfo(nodeId) {{
                // 현재 데이터에서 노드 찾기
                const node = (window.nodesData && window.nodesData[nodeId]) || 
                            (data && data.nodes && data.nodes.find(n => n.id === nodeId));
                const linksData = window.linksData || (data && data.links) || [];
                if (!node) {{
                    console.warn('Node not found:', nodeId);
                    return;
                }}
                
                const panel = document.getElementById('node-info-panel');
                const content = document.getElementById('node-info-content');
                
                // 노드 기본 정보
                let html = `
                    <div style="margin-bottom: 15px;">
                        <h4 style="color: #1f77b4; margin: 0 0 10px 0; font-size: 16px;">${{node.label || node.id || 'Unknown'}}</h4>
                        <div style="background: rgba(31, 119, 180, 0.1); padding: 10px; border-radius: 4px; margin-top: 10px;">
                            <p style="margin: 5px 0; font-size: 12px; color: #aaa;">
                                <strong style="color: #fff;">ID:</strong> <span style="word-break: break-all;">${{node.id || 'N/A'}}</span>
                            </p>
                            <p style="margin: 5px 0; font-size: 12px; color: #aaa;">
                                <strong style="color: #fff;">그룹:</strong> <span style="color: #1f77b4;">${{node.group || '기타'}}</span>
                            </p>
                        </div>
                    </div>
                `;
                
                // 관련 관계 찾기
                const relatedLinks = linksData.filter(link => {{
                    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                    return sourceId === nodeId || targetId === nodeId;
                }});
                
                if (relatedLinks.length > 0) {{
                    // 나가는 관계와 들어오는 관계 분리
                    const outgoingLinks = relatedLinks.filter(link => {{
                        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                        return sourceId === nodeId;
                    }});
                    
                    const incomingLinks = relatedLinks.filter(link => {{
                        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                        return targetId === nodeId;
                    }});
                    
                    html += `
                        <div style="margin-top: 15px; border-top: 1px solid #333; padding-top: 15px;">
                            <h5 style="color: #1f77b4; margin: 0 0 10px 0; font-size: 14px;">🔗 관련 관계 (${{relatedLinks.length}}개)</h5>
                            <div style="max-height: 300px; overflow-y: auto;">
                    `;
                    
                    // 나가는 관계
                    if (outgoingLinks.length > 0) {{
                        html += `
                            <div style="margin-bottom: 15px;">
                                <p style="color: #1f77b4; font-size: 12px; font-weight: bold; margin: 0 0 8px 0;">나가는 관계 (${{outgoingLinks.length}}개)</p>
                        `;
                        outgoingLinks.slice(0, 10).forEach(link => {{
                            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                            const otherNode = (window.nodesData && window.nodesData[targetId]) || 
                                            (data && data.nodes && data.nodes.find(n => n.id === targetId)) ||
                                            {{id: targetId, label: targetId}};
                            const relation = link.relation || 'relatedTo';
                            
                            html += `
                                <div style="
                                    margin: 5px 0;
                                    padding: 8px;
                                    background: rgba(31, 119, 180, 0.15);
                                    border-left: 3px solid #1f77b4;
                                    border-radius: 4px;
                                    font-size: 12px;
                                ">
                                    <span style="color: #1f77b4; font-weight: bold;">→</span>
                                    <strong style="color: #fff;">${{otherNode.label || otherNode.id}}</strong>
                                    <span style="color: #aaa; margin-left: 5px;">(${{relation}})</span>
                                </div>
                            `;
                        }});
                        if (outgoingLinks.length > 10) {{
                            html += `<p style="color: #aaa; font-size: 11px; margin-top: 5px;">... 외 ${{outgoingLinks.length - 10}}개</p>`;
                        }}
                        html += `</div>`;
                    }}
                    
                    // 들어오는 관계
                    if (incomingLinks.length > 0) {{
                        html += `
                            <div>
                                <p style="color: #ffa500; font-size: 12px; font-weight: bold; margin: 15px 0 8px 0;">들어오는 관계 (${{incomingLinks.length}}개)</p>
                        `;
                        incomingLinks.slice(0, 10).forEach(link => {{
                            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                            const otherNode = (window.nodesData && window.nodesData[sourceId]) || 
                                            (data && data.nodes && data.nodes.find(n => n.id === sourceId)) ||
                                            {{id: sourceId, label: sourceId}};
                            const relation = link.relation || 'relatedTo';
                            
                            html += `
                                <div style="
                                    margin: 5px 0;
                                    padding: 8px;
                                    background: rgba(255, 165, 0, 0.15);
                                    border-left: 3px solid #ffa500;
                                    border-radius: 4px;
                                    font-size: 12px;
                                ">
                                    <span style="color: #ffa500; font-weight: bold;">←</span>
                                    <strong style="color: #fff;">${{otherNode.label || otherNode.id}}</strong>
                                    <span style="color: #aaa; margin-left: 5px;">(${{relation}})</span>
                                </div>
                            `;
                        }});
                        if (incomingLinks.length > 10) {{
                            html += `<p style="color: #aaa; font-size: 11px; margin-top: 5px;">... 외 ${{incomingLinks.length - 10}}개</p>`;
                        }}
                        html += `</div>`;
                    }}
                    
                    html += `
                            </div>
                        </div>
                    `;
                }} else {{
                    html += `
                        <div style="margin-top: 15px; border-top: 1px solid #333; padding-top: 15px;">
                            <p style="color: #aaa; font-size: 12px; text-align: center;">관련 관계가 없습니다.</p>
                        </div>
                    `;
                }}
                
                content.innerHTML = html;
                panel.style.display = 'block';
            }}
            
            function closeNodeInfo() {{
                document.getElementById('node-info-panel').style.display = 'none';
            }}
        </script>
    """
    
    # 간소화된 컨트롤 패널 HTML (제목 제거, 필수 기능만)
    header_controls = f"""
    <div class="controls">
        <div class="control-group">
            <label>그래프 타입</label>
            <select id="graphMode">
                <option value="instances">인스턴스 그래프 (ABox)</option>
                <option value="schema">스키마 그래프 (TBox)</option>
            </select>
        </div>
        
        <div class="control-group">
            <label>노드 선택</label>
            <select id="nodeSelector">
                <option value="">선택 안함</option>
            </select>
        </div>
        
        <div class="control-group">
            <label>그룹 선택</label>
            <div class="custom-dropdown">
                <button id="groupSelectorButton" class="dropdown-button">
                    <span id="groupSelectorText">전체 그룹</span>
                    <span class="dropdown-arrow">▼</span>
                </button>
                <div id="groupSelectorDropdown" class="dropdown-content">
                    <label class="dropdown-item">
                        <input type="checkbox" value="" id="groupAll" checked>
                        <span>전체 그룹</span>
                    </label>
                    <div id="groupCheckboxes"></div>
                </div>
            </div>
        </div>
    </div>
    """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <title>지식그래프 뷰어</title>
        {d3_script}
        <style>
            body {{
                margin: 0;
                background: #0e1117;
                color: white;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            .controls {{
                background: #1e1e1e;
                padding: 8px 15px;
                display: flex;
                gap: 15px;
                align-items: center;
                flex-wrap: wrap;
                border-bottom: 1px solid #333;
            }}
            
            .control-group {{
                display: flex;
                flex-direction: row;
                gap: 8px;
                align-items: center;
            }}
            
            label {{
                font-size: 12px;
                color: #ccc;
                font-weight: 500;
                margin: 0;
                white-space: nowrap;
            }}
            
            select {{
                padding: 6px 12px;
                background: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 12px;
                min-height: 28px;
                min-width: 180px;
                cursor: pointer;
            }}
            
            select[multiple] {{
                min-height: 60px;
                overflow-y: auto;
            }}
            
            select[multiple] option {{
                padding: 4px 8px;
            }}
            
            select[multiple] option:checked {{
                background: #1f77b4;
                color: white;
            }}
            
            .custom-dropdown {{
                position: relative;
                min-width: 200px;
            }}
            
            .dropdown-button {{
                width: 100%;
                padding: 6px 12px;
                background: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 12px;
                min-height: 28px;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .dropdown-button:hover {{
                background: #3a3a3a;
            }}
            
            .dropdown-arrow {{
                font-size: 10px;
                color: #aaa;
                margin-left: 8px;
            }}
            
            .dropdown-content {{
                display: none;
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 4px;
                max-height: 300px;
                overflow-y: auto;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            }}
            
            .dropdown-content.show {{
                display: block;
            }}
            
            .dropdown-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 12px;
                font-size: 12px;
                color: #ccc;
                cursor: pointer;
                user-select: none;
            }}
            
            .dropdown-item:hover {{
                background: #333;
            }}
            
            .dropdown-item input[type="checkbox"] {{
                margin: 0;
                margin-right: 8px;
                cursor: pointer;
                width: 16px;
                height: 16px;
                flex-shrink: 0;
                position: relative;
                z-index: 1;
            }}
            
            .dropdown-item input[type="checkbox"]:checked {{
                accent-color: #4CAF50;
            }}
            
            .dropdown-item span {{
                color: #ccc;
            }}
            
            .dropdown-item:hover span {{
                color: white;
            }}
            
            .dropdown-item input[type="checkbox"]:checked + span {{
                color: #4CAF50;
                font-weight: 500;
            }}
            
            .dropdown-content::-webkit-scrollbar {{
                width: 6px;
            }}
            
            .dropdown-content::-webkit-scrollbar-track {{
                background: #222;
            }}
            
            .dropdown-content::-webkit-scrollbar-thumb {{
                background: #555;
                border-radius: 3px;
            }}
            
            .dropdown-content::-webkit-scrollbar-thumb:hover {{
                background: #666;
            }}
            
            #graph-container {{
                position: relative;
                width: 100%;
                height: calc(100vh - 60px);
                min-height: 600px;
            }}
            
            svg {{
                width: 100%;
                height: 100%;
            }}
            
            .node {{
                cursor: pointer;
            }}
            
            .node:hover {{
                stroke: white;
                stroke-width: 3px;
            }}
            
            .link {{
                stroke: #999;
                stroke-opacity: 0.8;
            }}
            
            .link.inferred {{
                stroke: #ffa500;
                stroke-opacity: 0.8;
                stroke-dasharray: 5,5;
            }}
            
            .link:hover {{
                stroke-opacity: 1;
                stroke-width: 3px;
            }}
            
            .label {{
                fill: white;
                font-size: 12px;
                pointer-events: none;
            }}
        </style>
    </head>
    <body>
        {header_controls}
        {node_info_panel}
        <div id="graph-container">
            <svg id="graph-svg"></svg>
        </div>
        <script>
            // 그래프 데이터 로드
            const DATA_INSTANCES = {instances_json};
            const DATA_SCHEMA = {schema_json};
            const groupColors = {group_colors_json};
            
            // 데이터 유효성 검사
            console.log("데이터 로드:", {{
                instances: (DATA_INSTANCES && DATA_INSTANCES.nodes && Array.isArray(DATA_INSTANCES.nodes)) ? DATA_INSTANCES.nodes.length : 0,
                schema: (DATA_SCHEMA && DATA_SCHEMA.nodes && Array.isArray(DATA_SCHEMA.nodes)) ? DATA_SCHEMA.nodes.length : 0
            }});
            
            let data = DATA_INSTANCES; // 기본값: 인스턴스 그래프
            let selectedNodeId = null;
            let simulation = null;
            let svg, container, width, height, zoom;
            let node, link, label;
            
            // 그래프 초기화
            function initGraph() {{
                svg = d3.select("#graph-svg");
                const containerEl = document.getElementById("graph-container");
                width = containerEl.clientWidth;
                height = containerEl.clientHeight;
                
                svg.attr("width", width).attr("height", height);
                
                // 기존 요소 제거
                svg.selectAll("*").remove();
                
                // 컨테이너 그룹 생성
                container = svg.append("g").attr("class", "container");
                
                // 줌 기능 - 확장된 범위로 더 많이 축소 가능
                zoom = d3.zoom()
                    .scaleExtent([0.01, 10])  // 최소 0.01배, 최대 10배로 확장
                    .on("zoom", (event) => {{
                        container.attr("transform", event.transform);
                    }});
                svg.call(zoom);
                
                // 휠 이벤트 처리 - D3.js 줌이 작동하도록 개선
                // D3.js zoom은 기본적으로 마우스 휠로 줌인/아웃을 지원하므로
                // SVG 영역 내에서만 스크롤 방지
                try {{
                    svg.node().addEventListener('wheel', function(e) {{
                        // SVG 영역 내에서만 스크롤 방지 (D3.js 줌 작동 허용)
                        if (e.target === svg.node() || svg.node().contains(e.target)) {{
                            e.preventDefault();
                        }}
                    }}, {{ passive: false }});
                }} catch(e) {{
                    console.log("Wheel event handler failed:", e);
                }}
                
                createGraph();
            }}
            
            // 그래프 생성
            function createGraph() {{
                if (!data || !data.nodes || data.nodes.length === 0) {{
                    console.warn("그래프 데이터가 없습니다:", data);
                    // 빈 메시지 표시
                    container.append("text")
                        .attr("x", width / 2)
                        .attr("y", height / 2)
                        .attr("text-anchor", "middle")
                        .attr("fill", "white")
                        .attr("font-size", "16px")
                        .text("그래프 데이터가 없습니다.");
                    return;
                }}
                
                const linksCount = (data && data.links && Array.isArray(data.links)) ? data.links.length : 0;
                console.log("그래프 생성 시작:", data.nodes.length, "노드,", linksCount, "링크");
                
                // 기존 시뮬레이션 정지
                if (simulation) {{
                    simulation.stop();
                }}
                
                // 기존 요소 제거
                container.selectAll("*").remove();
                
                // 링크 데이터 전처리
                const nodeMap = new Map();
                data.nodes.forEach(n => {{
                    nodeMap.set(n.id, n);
                }});
                
                const processedLinks = data.links.map(l => {{
                    if (typeof l.source === 'string') {{
                        l.source = nodeMap.get(l.source) || l.source;
                    }}
                    if (typeof l.target === 'string') {{
                        l.target = nodeMap.get(l.target) || l.target;
                    }}
                    return l;
                }}).filter(l => l.source && l.target);
                
                // Force simulation
                simulation = d3.forceSimulation(data.nodes)
                    .force("link", d3.forceLink(processedLinks)
                        .id(d => d.id)
                        .distance(200)) // 기본값 사용
                    .force("charge", d3.forceManyBody()
                        .strength(-500)) // 기본값 사용
                    .force("center", d3.forceCenter(width / 2, height / 2))
                    .force("collision", d3.forceCollide().radius(30));
            
                // 링크 그리기
                link = container.append("g")
                    .attr("class", "links")
                    .selectAll("line")
                    .data(processedLinks)
                    .enter().append("line")
                    .attr("class", d => d.inferred ? "link inferred" : "link")
                    .attr("stroke-width", 2)
                    .attr("stroke", d => d.inferred ? "#ffa500" : "#999")
                    .attr("stroke-opacity", 0.8)
                    .on("mouseover", function(event, d) {{
                        d3.select(this)
                            .attr("stroke-width", 3)
                            .attr("stroke-opacity", 1);
                    }})
                    .on("mouseout", function(event, d) {{
                        d3.select(this)
                            .attr("stroke-width", 2)
                            .attr("stroke-opacity", 0.8);
                    }});
                
                // 노드 그리기
                const nodeSize = 20; // 기본값 사용
                node = container.append("g")
                    .attr("class", "nodes")
                    .selectAll("circle")
                    .data(data.nodes)
                    .enter().append("circle")
                    .attr("class", "node")
                    .attr("r", nodeSize)
                    .attr("fill", d => {{
                        const group = d.group || "기타";
                        return groupColors[group] || "#99ccff";
                    }})
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 2)
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended))
                    .on("mouseover", function(event, d) {{
                        d3.select(this).attr("r", nodeSize + 5);
                    }})
                    .on("mouseout", function(event, d) {{
                        d3.select(this).attr("r", nodeSize);
                    }})
                    .on("click", function(event, d) {{
                        event.stopPropagation();
                        
                        // 이전 선택 해제
                        if (selectedNodeId) {{
                            node.style("opacity", 1);
                            node.style("stroke-width", 2);
                        }}
                        
                        // 새 노드 선택
                        selectedNodeId = d.id;
                        
                        // 노드 선택 드롭다운 업데이트
                        const nodeSelector = document.getElementById("nodeSelector");
                        if (nodeSelector) {{
                            nodeSelector.value = d.id;
                        }}
                        
                        // 클릭된 노드 하이라이트
                        node.style("opacity", n => {{
                            if (n.id === d.id) return 1;
                            const isConnected = processedLinks.some(link => {{
                                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                                return (sourceId === d.id && targetId === n.id) ||
                                       (targetId === d.id && sourceId === n.id);
                            }});
                            return isConnected ? 0.7 : 0.3;
                        }});
                        node.style("stroke-width", n => n.id === d.id ? 4 : 2);
                        node.style("stroke", n => n.id === d.id ? "#ffeb3b" : "#fff");
                        
                        // 노드 정보 패널 표시
                        if (typeof showNodeInfo === 'function') {{
                            showNodeInfo(d.id);
                        }}
                    }});
                
                // 라벨 그리기
                label = container.append("g")
                    .attr("class", "labels")
                    .selectAll("text")
                    .data(data.nodes)
                    .enter().append("text")
                    .attr("class", "label")
                    .text(d => d.label || d.id || "Unknown")
                    .attr("dy", -(nodeSize + 5))
                    .attr("text-anchor", "middle");
                
                // 노드 선택 드롭다운 업데이트
                updateNodeSelector();
                
                // 그룹 선택 드롭다운 업데이트
                updateGroupSelector();
                
                // 시뮬레이션 업데이트
                simulation.on("tick", () => {{
                    if (link && link.size() > 0) {{
                        link
                            .attr("x1", d => d.source.x || 0)
                            .attr("y1", d => d.source.y || 0)
                            .attr("x2", d => d.target.x || 0)
                            .attr("y2", d => d.target.y || 0);
                    }}
                    
                    if (node && node.size() > 0) {{
                        node
                            .attr("cx", d => d.x || width / 2)
                            .attr("cy", d => d.y || height / 2);
                    }}
                    
                    if (label && label.size() > 0) {{
                        label
                            .attr("x", d => d.x || width / 2)
                            .attr("y", d => d.y || height / 2);
                    }}
                }});
                
                // 레이아웃 수렴 후 자동 맞춤
                setTimeout(fitToView, 1200);
            }}
            
            // 노드 선택 드롭다운 업데이트
            function updateNodeSelector() {{
                const selector = document.getElementById("nodeSelector");
                if (!selector || !data || !data.nodes) return;
                
                // 기존 옵션 제거 (첫 번째 옵션 제외)
                while (selector.children.length > 1) {{
                    selector.removeChild(selector.lastChild);
                }}
                
                // 노드 추가
                const sortedNodes = [...data.nodes].sort((a, b) => {{
                    const labelA = (a.label || a.id || "").toLowerCase();
                    const labelB = (b.label || b.id || "").toLowerCase();
                    return labelA.localeCompare(labelB);
                }});
                
                sortedNodes.forEach(n => {{
                    const option = document.createElement("option");
                    option.value = n.id;
                    option.textContent = n.label || n.id || "Unknown";
                    selector.appendChild(option);
                }});
            }}
            
            // 드롭다운 열기/닫기
            function toggleGroupDropdown() {{
                const dropdown = document.getElementById("groupSelectorDropdown");
                if (!dropdown) return;
                dropdown.classList.toggle("show");
            }}
            
            // 드롭다운 외부 클릭 시 닫기 (한 번만 등록)
            if (!window.groupDropdownClickHandlerAttached) {{
                window.groupDropdownClickHandlerAttached = true;
                document.addEventListener("click", function(event) {{
                    const dropdown = document.getElementById("groupSelectorDropdown");
                    const button = document.getElementById("groupSelectorButton");
                    
                    if (!dropdown || !button) return;
                    
                    const target = event.target;
                    
                    // 체크박스나 label을 클릭한 경우는 드롭다운을 닫지 않음
                    if (target && (
                        target.type === "checkbox" || 
                        target.tagName === "LABEL" || 
                        target.closest("label") ||
                        target.closest(".dropdown-content")
                    )) {{
                        return;
                    }}
                    
                    // 드롭다운이나 버튼 외부를 클릭한 경우에만 닫기
                    if (!dropdown.contains(target) && !button.contains(target)) {{
                        dropdown.classList.remove("show");
                    }}
                }}, true); // 캡처링 단계에서 처리
            }}
            
            // 그룹 선택 버튼 텍스트 업데이트
            function updateGroupSelectorText() {{
                const textElement = document.getElementById("groupSelectorText");
                const allCheckbox = document.getElementById("groupAll");
                const container = document.getElementById("groupCheckboxes");
                
                if (!textElement) return;
                
                if (allCheckbox && allCheckbox.checked) {{
                    textElement.textContent = "전체 그룹";
                }} else if (container) {{
                    const checkedBoxes = container.querySelectorAll('input[type="checkbox"]:checked');
                    if (checkedBoxes.length === 0) {{
                        textElement.textContent = "그룹 선택";
                    }} else if (checkedBoxes.length === 1) {{
                        textElement.textContent = checkedBoxes[0].value;
                    }} else {{
                        textElement.textContent = checkedBoxes.length + "개 그룹 선택됨";
                    }}
                }}
            }}
            
            // 그룹 선택 드롭다운 업데이트
            function updateGroupSelector() {{
                const container = document.getElementById("groupCheckboxes");
                if (!container) return;
                
                // 원본 데이터에서 그룹 추출 (필터링 전)
                const originalData = document.getElementById("graphMode").value === "schema" ? DATA_SCHEMA : DATA_INSTANCES;
                const groups = new Set();
                if (originalData && originalData.nodes) {{
                    originalData.nodes.forEach(n => {{
                        const group = n.group || "기타";
                        if (group) groups.add(group);
                    }});
                }}
                
                // 기존 체크박스의 선택 상태 저장
                const existingCheckboxes = container.querySelectorAll('input[type="checkbox"]');
                const checkedGroups = new Set();
                existingCheckboxes.forEach(cb => {{
                    if (cb.checked) {{
                        checkedGroups.add(cb.value);
                    }}
                }});
                
                // 기존 체크박스 제거
                container.innerHTML = "";
                
                // 그룹 체크박스 추가 (정렬)
                const sortedGroups = Array.from(groups).sort();
                sortedGroups.forEach(group => {{
                    const label = document.createElement("label");
                    label.className = "dropdown-item";
                    
                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.value = group;
                    checkbox.id = "groupCheckbox_" + group.replace(/\s+/g, "_");
                    
                    // 기존 선택 상태 복원
                    if (checkedGroups.has(group)) {{
                        checkbox.checked = true;
                    }}
                    
                    // 체크박스 클릭 이벤트 - 드롭다운이 닫히지 않도록
                    checkbox.addEventListener("click", function(e) {{
                        e.stopPropagation(); // 드롭다운 외부 클릭 이벤트로 전파 방지
                        // preventDefault()를 호출하지 않아서 체크박스의 기본 토글 동작 유지
                        console.log("Checkbox clicked:", group, "will be:", !this.checked);
                    }});
                    
                    // 체크박스 변경 이벤트
                    checkbox.addEventListener("change", function(e) {{
                        e.stopPropagation(); // 드롭다운 외부 클릭 이벤트로 전파 방지
                        console.log("Checkbox change event:", group, "checked:", this.checked);
                        
                        // 개별 그룹 선택 시 "전체 그룹" 해제
                        const allCheckbox = document.getElementById("groupAll");
                        if (allCheckbox && this.checked) {{
                            allCheckbox.checked = false;
                        }}
                        updateGroupSelectorText();
                        updateGroupFilter();
                    }});
                    
                    // label 클릭 이벤트 - label 클릭 시 체크박스 토글
                    label.addEventListener("click", function(e) {{
                        // 체크박스 자체를 클릭한 경우는 기본 동작 사용
                        if (e.target === checkbox || e.target === checkbox.parentNode) {{
                            return;
                        }}
                        // label의 다른 부분을 클릭한 경우 체크박스 토글
                        e.preventDefault();
                        e.stopPropagation();
                        // 체크박스 상태를 명시적으로 토글
                        checkbox.checked = !checkbox.checked;
                        console.log("Label clicked, toggling checkbox:", group, "to", checkbox.checked);
                        // change 이벤트 수동 발생
                        const changeEvent = new Event("change", {{ bubbles: true, cancelable: true }});
                        checkbox.dispatchEvent(changeEvent);
                    }});
                    
                    const span = document.createElement("span");
                    span.textContent = group;
                    
                    label.appendChild(checkbox);
                    label.appendChild(span);
                    container.appendChild(label);
                }});
                
                updateGroupSelectorText();
            }}
            
            // "전체 그룹" 체크박스 이벤트 처리
            function setupGroupAllCheckbox() {{
                const allCheckbox = document.getElementById("groupAll");
                const button = document.getElementById("groupSelectorButton");
                
                if (!allCheckbox || !button) return;
                
                // 기존 이벤트 리스너가 있는지 확인하고 제거
                // cloneNode를 사용하지 않고 직접 이벤트 리스너 추가
                // 중복 방지를 위해 먼저 이벤트 리스너 제거 (없어도 안전)
                const newAllCheckbox = allCheckbox.cloneNode(false); // 이벤트 리스너는 복제하지 않음
                const parent = allCheckbox.parentNode;
                const nextSibling = allCheckbox.nextSibling;
                parent.removeChild(allCheckbox);
                parent.insertBefore(newAllCheckbox, nextSibling);
                
                // 속성 복원
                newAllCheckbox.type = "checkbox";
                newAllCheckbox.value = "";
                newAllCheckbox.id = "groupAll";
                newAllCheckbox.checked = true;
                
                // label과 span 복원 (이미 있으면 재사용)
                const label = parent;
                let span = label.querySelector("span");
                if (!span) {{
                    span = document.createElement("span");
                    span.textContent = "전체 그룹";
                    label.appendChild(span);
                }} else {{
                    span.textContent = "전체 그룹";
                }}
                
                newAllCheckbox.addEventListener("change", function(e) {{
                    e.stopPropagation(); // 드롭다운 외부 클릭 이벤트로 전파 방지
                    
                    if (this.checked) {{
                        // "전체 그룹" 선택 시 다른 모든 체크박스 해제
                        const container = document.getElementById("groupCheckboxes");
                        if (container) {{
                            const checkboxes = container.querySelectorAll('input[type="checkbox"]');
                            checkboxes.forEach(cb => cb.checked = false);
                        }}
                    }}
                    updateGroupSelectorText();
                    updateGroupFilter();
                }});
                
                // "전체 그룹" 체크박스 클릭 이벤트 - 드롭다운이 닫히지 않도록 (기본 동작은 유지)
                newAllCheckbox.addEventListener("click", function(e) {{
                    e.stopPropagation(); // 드롭다운 외부 클릭 이벤트로 전파 방지
                    // preventDefault()를 호출하지 않아서 체크박스의 기본 토글 동작 유지
                }}, false);
                
                // "전체 그룹" label 클릭 이벤트
                const allLabel = newAllCheckbox.parentNode;
                if (allLabel && allLabel.tagName === "LABEL") {{
                    allLabel.addEventListener("click", function(e) {{
                        if (e.target !== newAllCheckbox) {{
                            e.preventDefault();
                            e.stopPropagation();
                            newAllCheckbox.checked = !newAllCheckbox.checked;
                            const changeEvent = new Event("change", {{ bubbles: true, cancelable: true }});
                            newAllCheckbox.dispatchEvent(changeEvent);
                        }}
                    }}, false);
                }}
                
                // 드롭다운 버튼 클릭 이벤트
                if (!button.hasAttribute("data-listener-attached")) {{
                    button.setAttribute("data-listener-attached", "true");
                    button.addEventListener("click", toggleGroupDropdown);
                }}
            }}
            
            // 그룹 필터링 함수
            function filterByGroups(selectedGroups) {{
                // "전체 그룹"이 선택되었거나 선택된 그룹이 없으면 모든 그룹 표시
                const allCheckbox = document.getElementById("groupAll");
                if (allCheckbox && allCheckbox.checked) {{
                    const mode = document.getElementById("graphMode").value;
                    return mode === "schema" ? DATA_SCHEMA : DATA_INSTANCES;
                }}
                
                if (!selectedGroups || selectedGroups.length === 0) {{
                    const mode = document.getElementById("graphMode").value;
                    return mode === "schema" ? DATA_SCHEMA : DATA_INSTANCES;
                }}
                
                const originalData = document.getElementById("graphMode").value === "schema" ? DATA_SCHEMA : DATA_INSTANCES;
                if (!originalData || !originalData.nodes) return originalData;
                
                // 선택된 그룹의 노드만 필터링
                const filteredNodes = originalData.nodes.filter(n => {{
                    const group = n.group || "기타";
                    return selectedGroups.includes(group);
                }});
                
                // 필터링된 노드 ID 집합
                const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
                
                // 필터링된 노드와 연결된 링크만 포함
                const filteredLinks = (originalData.links || []).filter(link => {{
                    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                    return filteredNodeIds.has(sourceId) && filteredNodeIds.has(targetId);
                }});
                
                return {{nodes: filteredNodes, links: filteredLinks}};
            }}
            
            // 그룹 선택 변경
            function updateGroupFilter() {{
                const container = document.getElementById("groupCheckboxes");
                const allCheckbox = document.getElementById("groupAll");
                
                if (!container) return;
                
                // "전체 그룹" 체크박스 확인
                if (allCheckbox && allCheckbox.checked) {{
                    data = filterByGroups([]);
                }} else {{
                    // 선택된 그룹 가져오기
                    const selectedGroups = Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
                        .map(cb => cb.value);
                    
                    // 선택된 그룹이 없으면 "전체 그룹" 자동 선택
                    if (selectedGroups.length === 0 && allCheckbox) {{
                        allCheckbox.checked = true;
                        data = filterByGroups([]);
                    }} else {{
                        data = filterByGroups(selectedGroups);
                    }}
                }}
                
                updateGroupSelectorText();
                
                // 노드 정보 패널의 데이터도 업데이트
                updateNodeInfoData();
                
                // 그래프 재생성
                if (simulation) {{
                    simulation.stop();
                }}
                createGraph();
            }}
            
            // 그래프 타입 변경
            function updateGraphMode() {{
                const mode = document.getElementById("graphMode").value;
                const originalData = mode === "schema" ? DATA_SCHEMA : DATA_INSTANCES;
                
                // 그룹 선택 상태 확인
                const container = document.getElementById("groupCheckboxes");
                let selectedGroups = [];
                const allCheckbox = document.getElementById("groupAll");
                
                if (container && !(allCheckbox && allCheckbox.checked)) {{
                    selectedGroups = Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
                        .map(cb => cb.value);
                }}
                
                // 그룹 필터 적용
                data = filterByGroups(selectedGroups);
                
                // 그룹 선택 드롭다운 업데이트
                updateGroupSelector();
                
                // "전체 그룹" 체크박스 설정
                setupGroupAllCheckbox();
                
                // 노드 정보 패널의 데이터도 업데이트
                updateNodeInfoData();
                
                // 그래프 재생성
                if (simulation) {{
                    simulation.stop();
                }}
                createGraph();
            }}
            
            // 노드 정보 패널 데이터 업데이트
            function updateNodeInfoData() {{
                // 현재 데이터의 모든 노드를 맵으로 변환
                const nodesMap = {{}};
                const linksList = [];
                
                if (data && data.nodes) {{
                    data.nodes.forEach(n => {{
                        nodesMap[n.id] = n;
                    }});
                }}
                
                if (data && data.links) {{
                    linksList.push(...data.links);
                }}
                
                // 전역 변수 업데이트 (showNodeInfo 함수에서 사용)
                window.nodesData = nodesMap;
                window.linksData = linksList;
            }}
            
            // 드래그 함수
            function dragstarted(event, d) {{
                if (!event.active && simulation) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }}
            
            function dragged(event, d) {{
                d.fx = event.x;
                d.fy = event.y;
            }}
            
            function dragended(event, d) {{
                if (!event.active && simulation) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }}
            
            // 자동 맞춤
            function fitToView() {{
                if (!data || !data.nodes || data.nodes.length === 0) return;
                
                const nodes = data.nodes;
                const minX = d3.min(nodes, d => d.x);
                const maxX = d3.max(nodes, d => d.x);
                const minY = d3.min(nodes, d => d.y);
                const maxY = d3.max(nodes, d => d.y);
                
                if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) return;
                
                const padding = 80;
                const dx = (maxX - minX) + padding;
                const dy = (maxY - minY) + padding;
                // 스케일 제한 완화 - 더 작게 축소 가능하도록 최대 스케일 제한 제거
                const scale = Math.min(width / dx, height / dy);
                const tx = (width - scale * (minX + maxX)) / 2;
                const ty = (height - scale * (minY + maxY)) / 2;
                
                if (svg && zoom) {{
                    svg.transition()
                        .duration(600)
                        .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
                }}
            }}
            
            // 그래프 초기화
            function resetGraph() {{
                if (simulation) {{
                    simulation.alpha(1).restart();
                }}
                setTimeout(fitToView, 800);
            }}
            
            // 노드로 포커싱하는 함수
            function focusNode(nodeId) {{
                if (!nodeId || !data || !data.nodes) return;
                
                const targetNode = data.nodes.find(n => n.id === nodeId);
                if (!targetNode) return;
                
                // 노드가 시뮬레이션에서 위치를 가지고 있는지 확인
                if (targetNode.x === undefined || targetNode.y === undefined) {{
                    // 위치가 없으면 시뮬레이션이 완료될 때까지 대기
                    if (simulation) {{
                        simulation.on("end", function() {{
                            focusNodeToPosition(targetNode);
                        }});
                        simulation.alpha(1).restart();
                    }}
                }} else {{
                    focusNodeToPosition(targetNode);
                }}
            }}
            
            // 노드 위치로 포커싱
            function focusNodeToPosition(targetNode) {{
                if (!targetNode || targetNode.x === undefined || targetNode.y === undefined) return;
                if (!svg || !zoom || !width || !height) return;
                
                // 노드 위치를 화면 중심으로 이동하고 약간 확대
                const scale = 2; // 2배 확대
                const tx = width / 2 - targetNode.x * scale;
                const ty = height / 2 - targetNode.y * scale;
                
                // 부드러운 애니메이션으로 이동
                svg.transition()
                    .duration(800)
                    .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
                
                // 노드 하이라이트
                if (node && node.size() > 0) {{
                    // 이전 선택 해제
                    node.style("opacity", 1);
                    node.style("stroke-width", 2);
                    node.style("stroke", "#fff");
                    
                    // 선택된 노드 하이라이트
                    const selectedNode = node.filter(d => d.id === targetNode.id);
                    selectedNode.style("opacity", 1);
                    selectedNode.style("stroke-width", 4);
                    selectedNode.style("stroke", "#ffeb3b");
                    
                    // 관련 노드도 하이라이트
                    if (data && data.links) {{
                        const relatedNodeIds = new Set();
                        data.links.forEach(link => {{
                            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                            if (sourceId === targetNode.id) {{
                                relatedNodeIds.add(targetId);
                            }} else if (targetId === targetNode.id) {{
                                relatedNodeIds.add(sourceId);
                            }}
                        }});
                        
                        node.style("opacity", n => {{
                            if (n.id === targetNode.id) return 1;
                            if (relatedNodeIds.has(n.id)) return 0.7;
                            return 0.3;
                        }});
                    }}
                }}
                
                // 노드 정보 패널 표시
                if (typeof showNodeInfo === 'function') {{
                    showNodeInfo(targetNode.id);
                }}
            }}
            
            // 이벤트 리스너 설정
            document.getElementById("graphMode").addEventListener("change", updateGraphMode);
            document.getElementById("nodeSelector").addEventListener("change", function() {{
                const nodeId = this.value;
                if (nodeId) {{
                    focusNode(nodeId);
                }} else {{
                    // 선택 해제 시 모든 노드 표시
                    if (node && node.size() > 0) {{
                        node.style("opacity", 1);
                        node.style("stroke-width", 2);
                        node.style("stroke", "#fff");
                    }}
                    // 노드 정보 패널 닫기
                    if (typeof closeNodeInfo === 'function') {{
                        closeNodeInfo();
                    }}
                }}
            }});
            // groupSelector 이벤트 리스너는 제거 (드롭다운 버튼에 직접 이벤트 추가됨)
            
            // 노드 크기, 링크 거리, 중력 강도는 기본값 사용 (컨트롤 제거됨)
            
            // 윈도우 리사이즈 처리
            window.addEventListener("resize", function() {{
                initGraph();
            }});
            
            // 초기 노드 정보 데이터 설정
            updateNodeInfoData();
            
            // "전체 그룹" 체크박스 설정 (먼저 설정)
            setupGroupAllCheckbox();
            
            // 초기 그룹 선택 드롭다운 업데이트
            updateGroupSelector();
            
            // 초기화
            initGraph();
        </script>
    </body>
    </html>
    """

    return html_template


def _save_graph_html(html_content: str, graph_mode: str) -> Optional[str]:
    """그래프 HTML 파일 저장"""
    from pathlib import Path
    import os
    from datetime import datetime
    
    try:
        # 출력 디렉토리 생성
        output_dir = Path("outputs/graph_html")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # [NEW] 파일 정리: 유지할 최대 파일 수 제한 (예: 5개)
        MAX_FILES = 5
        html_files = sorted(output_dir.glob("*.html"), key=os.path.getmtime)
        
        if len(html_files) >= MAX_FILES:
            # 삭제할 수 계산 (새 파일이 추가되므로 1개 더 삭제해야 할 수도 있음)
            # 가장 오래된 파일들 삭제
            files_to_delete = html_files[:len(html_files) - MAX_FILES + 1]
            for old_file in files_to_delete:
                try:
                    old_file.unlink()
                except Exception:
                    pass
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = "instances" if graph_mode and "인스턴스" in graph_mode else "schema"
        filename = f"graph_{mode_suffix}_{timestamp}.html"
        filepath = output_dir / filename
        
        # HTML 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return str(filepath)
    except Exception as e:
        import streamlit as st
        st.warning(f"HTML 파일 저장 실패: {e}")
        return None

