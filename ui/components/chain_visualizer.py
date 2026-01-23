import streamlit as st
import graphviz
from typing import Dict, List, Any

class ChainVisualizer:
    """
    Dynamic Chain of Strategy Visualizer
    Renders relationship chains from Threat to COA using Graphviz
    """
    
    def render_chains(self, chain_info: Dict[str, Any], expanded: bool = False):
        """
        Render chains using Streamlit Graphviz chart
        
        Args:
            chain_info: Dictionary containing 'chains' list and 'summary'
            expanded: Whether the expander is open by default
        """
        if not chain_info:
            return

        chains = chain_info.get("chains", [])
        summary = chain_info.get("summary", {})
        
        if not chains:
            # 체인이 없는 경우, 사유를 표시
            with st.expander("🔗 전략 연결 체인 (연결 정보 없음)", expanded=expanded):
                reason = chain_info.get("info", "해당 위협과 방책 간의 직접적인 온톨로지 연결(Graph Path)을 찾을 수 없습니다.")
                st.info(
                    f"**⚠️ 전략 체인 미발견**\n\n"
                    f"**사유**: {reason}\n\n"
                    f"**해설**: 이 방책은 온톨로지 그래프상의 직접적인 인과관계(Chain)보다는, "
                    f"LLM의 추론이나 과거 통계적 패턴(전투 성공률 등)에 기반하여 추천되었습니다."
                )
            return
            
        chains = chain_info.get("chains", [])
        summary = chain_info.get("summary", {})
        
        total_chains = summary.get("total_chains", len(chains))
        
        with st.expander(f"🔗 전략 연결 체인 (Dynamic Chain of Strategy) - {total_chains} paths found", expanded=expanded):
            # Summary Metrics
            cols = st.columns(3)
            with cols[0]:
                st.metric("Total Chains", total_chains)
            with cols[1]:
                st.metric("Avg Depth", summary.get("avg_depth", 0))
            with cols[2]:
                st.metric("Avg Score", summary.get("avg_score", 0))
            
            # Graph Visualization
            # Create a directed graph
            dot = graphviz.Digraph(comment='Strategy Chains')
            dot.attr(rankdir='LR')  # Left to Right
            dot.attr('node', shape='box', style='rounded,filled', fontname="Malgun Gothic")
            
            # Track added nodes/edges to avoid duplicates in the graph
            added_edges = set()
            added_nodes = set()
            
            for i, chain in enumerate(chains):
                path = chain.get('path', [])
                if not path:
                    continue
                
                # Path is a list of URIs or names
                # e.g. [ThreatURI, ..., COAURI]
                
                for j in range(len(path) - 1):
                    src = self._get_label(path[j])
                    dst = self._get_label(path[j+1])
                    
                    # Add nodes with specific styles
                    if j == 0 and src not in added_nodes: # Start Node (Threat)
                        dot.node(src, src, color='red', fillcolor='#ffebee', shape='doublecircle')
                        added_nodes.add(src)
                    
                    if j == len(path) - 2 and dst not in added_nodes: # End Node (COA)
                        dot.node(dst, dst, color='blue', fillcolor='#e3f2fd', shape='box')
                        added_nodes.add(dst)
                        
                    if src not in added_nodes:
                        dot.node(src, src, color='grey', fillcolor='#f5f5f5')
                        added_nodes.add(src)
                    if dst not in added_nodes:
                        dot.node(dst, dst, color='grey', fillcolor='#f5f5f5')
                        added_nodes.add(dst)
                    
                    # Add Edge
                    edge_key = (src, dst)
                    if edge_key not in added_edges:
                        # Try to get predicate label if available
                        label = ""
                        predicates = chain.get('predicates', [])
                        if j < len(predicates):
                            label = self._get_label(predicates[j])
                        
                        dot.edge(src, dst, label=label, fontsize='10', color='#666666')
                        added_edges.add(edge_key)
            
            st.graphviz_chart(dot)
            
            # Detailed Paths (Text)
            if st.checkbox("Show Raw Paths", key="show_raw_paths"):
                for i, chain in enumerate(chains):
                    path_labels = [self._get_label(p) for p in chain.get('path', [])]
                    # Use info box for better contrast and visibility
                    st.info(f"Path {i+1}: {' -> '.join(path_labels)} (Score: {chain.get('score', 0):.2f})")

    def _get_label(self, uri_or_str: str) -> str:
        """Extract a readable label from URI"""
        if not uri_or_str:
            return "Unknown"
        # Remove namespace
        if "#" in uri_or_str:
            return uri_or_str.split("#")[-1]
        if "/" in uri_or_str:
            return uri_or_str.split("/")[-1]
        return uri_or_str
