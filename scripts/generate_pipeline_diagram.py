import graphviz
import os

def generate_diagram(output_format="png", view=True):
    """
    데이터 처리 및 지휘통제 파이프라인 다이어그램 생성
    """
    # 상태에 따른 색상 설정 (기본값: 녹색)
    # 실제 구현시에는 파일 존재 여부 등을 체크하여 결정
    color_db = "green"
    color_onto = "green"
    color_inst = "green"
    color_graph = "green"
    color_rag = "green"

    # Graphviz DOT 언어로 흐름도 정의
    dot_source = f"""
    digraph G {{
        rankdir=LR;
        splines=ortho;
        nodesep=0.4;
        ranksep=0.6;
        fontname="Malgun Gothic";
        fontsize=10;
        
        node [shape=box, style="filled,rounded", fontname="Malgun Gothic", fontsize=9, margin=0.2];
        edge [fontname="Malgun Gothic", fontsize=8, color="#aaaaaa"];
        
        # 범례
        subgraph cluster_legend {{
            label="범례";
            style=dashed;
            color="#555555";
            fontcolor="#aaaaaa";
            node [shape=plaintext, style=""];
            key [label=<<table border="0" cellpadding="2" cellspacing="5" cellborder="0">
                <tr>
                    <td bgcolor="#dfe6e9" width="15" height="15" border="1"></td>
                    <td bgcolor="white" width="15" height="15" border="1"></td>
                    <td bgcolor="green" width="15" height="15" border="1"></td>
                    <td align="left"> System/Data</td>
                </tr>
                <tr>
                    <td bgcolor="#a29bfe" width="15" height="15" border="1"></td>
                    <td bgcolor="#74b9ff" width="15" height="15" border="1"></td>
                    <td></td>
                    <td align="left"> AI Agent</td>
                </tr>
                <tr>
                    <td bgcolor="#00b894" width="15" height="15" border="1"></td>
                    <td bgcolor="#fab1a0" width="15" height="15" border="1"></td>
                    <td></td>
                    <td align="left"> User Action</td>
                </tr>
                </table>>];
        }}

        # 1. 데이터 관리 레이어 (Data Layer)
        subgraph cluster_data {{
            label="데이터 관리 (Data Layer)";
            style=filled;
            color="#2d3436";
            fillcolor="#2d3436";
            fontcolor="white";
            
            # Nodes
            source_db [label="원천 데이터\\n(CSV/Excel)", shape=cylinder, fillcolor="{color_db}", fontcolor="white"];
            doc_db [label="작전 교범\\n(PDF/Text)", shape=cylinder, fillcolor="#dfe6e9", fontcolor="black"];
            
            onto_engine [label="온톨로지 변환기", shape=component, fillcolor="white", fontcolor="black"];
            rag_engine [label="임베딩 엔진", shape=component, fillcolor="white", fontcolor="black"];
            
            knowledge_graph [label="지식 그래프\\n(RDF/TTL)", shape=cylinder, fillcolor="{color_onto}", fontcolor="white"];
            vector_db [label="벡터 DB\\n(FAISS)", shape=cylinder, fillcolor="{color_rag}", fontcolor="white"];
            
            # Edges
            source_db -> onto_engine;
            onto_engine -> knowledge_graph;
            
            doc_db -> rag_engine;
            rag_engine -> vector_db;
        }}
        
        # 2. 지능형 에이전트 레이어 (Agent Layer)
        subgraph cluster_agents {{
            label="지능형 에이전트 (Agent Layer)";
            style=filled;
            color="#34495e";
            fillcolor="#34495e";
            fontcolor="white";
            
            # Nodes
            agent_situation [label="상황 분석 에이전트\\n(Situation Agent)", shape=hexagon, fillcolor="#a29bfe", fontcolor="black"];
            agent_coa [label="방책 추천 에이전트\\n(COA Agent)", shape=hexagon, fillcolor="#a29bfe", fontcolor="black"];
            reasoner [label="온톨로지 추론기\\n(Reasoner)", shape=component, fillcolor="#74b9ff", fontcolor="black"];
            
            # Edges
            agent_situation -> agent_coa;
            agent_coa -> reasoner [dir=both, style=dotted];
        }}
        
        # 3. 지휘통제 레이어 (User Layer)
        subgraph cluster_user {{
            label="지휘통제 (Command Layer)";
            style=filled;
            color="#576574";
            fillcolor="#576574";
            fontcolor="white";
            
            # Nodes
            user_input [label="상황 입력\\n(Dashboard)", shape=rect, fillcolor="#00b894", fontcolor="white"];
            result_view [label="방책 결과 시각화\\n(Visualization)", shape=rect, fillcolor="#00b894", fontcolor="white"];
            feedback [label="사용자 피드백", shape=parallelogram, fillcolor="#fab1a0", fontcolor="black"];
            
            # Edges
            user_input -> result_view [style=invis]; # Layout hint
        }}
        
        # Cross-Layer Connections
        knowledge_graph -> agent_situation [style=dashed, color="#fab1a0"];
        knowledge_graph -> agent_coa [style=dashed, color="#fab1a0"];
        vector_db -> agent_situation [style=dashed, color="#fab1a0"];
        
        user_input -> agent_situation [label="분석 요청"];
        agent_coa -> result_view [label="추천 결과"];
        result_view -> feedback;
        feedback -> agent_coa [label="재조정", style=dotted];
    }}
    """

    # Create Graphviz Source object
    try:
        src = graphviz.Source(dot_source)
        
        # Render
        output_path = "pipeline_diagram"
        src.render(output_path, format=output_format, view=view)
        print(f"Diagram generated: {output_path}.{output_format}")
    except Exception as e:
        print(f"Error generating diagram: {e}")
        print("Make sure Graphviz is installed on your system (not just the python package).")

if __name__ == "__main__":
    generate_diagram()
