# ui/components/pipeline_status.py

# -*- coding: utf-8 -*-

"""
파이프라인 상태 대시보드 컴포넌트
5단계 파이프라인 시각화 및 상태 체크
"""

import streamlit as st
import os
import glob
from pathlib import Path
from datetime import datetime

def check_pipeline_status(config):

    """
    파이프라인 상태 체크
 
    Args:
        config: 설정 딕셔너리              

    Returns:
        파이프라인 상태 딕셔너리
    """

    data_paths = config.get("data_paths", {})

    # 데이터 파일 경로 확인
    data_files = []
    for name, path in data_paths.items():
        if not os.path.isabs(path):
            base_dir = Path(__file__).parent.parent.parent
            path = base_dir / path
        if os.path.exists(str(path)):
            data_files.append(str(path))

    status = {

        "원천 DB": {
            "files": data_files,
            "required": True,
            "exists": len(data_files) > 0
        },
        "RDF 온톨로지": {
            "files": ["knowledge/ontology/schema.ttl", "knowledge/ontology/instances.ttl"],
            "required": False,
            "exists": any(os.path.exists(f) for f in ["knowledge/ontology/schema.ttl", "knowledge/ontology/instances.ttl"])
        },
        "인스턴스": {
            "files": ["knowledge/ontology/instances.ttl"],
            "required": True,
            "exists": os.path.exists("knowledge/ontology/instances.ttl")
        },
        "RAG 인덱스": {
            "files": ["knowledge/embeddings/faiss_index.bin"],
            "required": False,
            "exists": os.path.exists("knowledge/embeddings/faiss_index.bin")
        },

        "그래프 파일": {
            "files": ["knowledge/ontology/instances.ttl", "knowledge/ontology/schema.ttl"],
            "required": False,
            "exists": any(os.path.exists(f) for f in ["knowledge/ontology/instances.ttl", "knowledge/ontology/schema.ttl"])
        }
    }

     # 각 단계별 ready 상태 계산
    for name, info in status.items():
        info["ready"] = info["exists"] or not info["required"]
 
    return status




#############################################################################
def check_component_status(config, pipeline_status):

    """
    컴포넌트 상태 체크 (시스템 건강 상태)
 

    Args:

        config: 설정 딕셔너리

        pipeline_status: 파이프라인 상태 딕셔너리

        

    Returns:

        컴포넌트 상태 딕셔너리

    """

    status = {}


    # 1. Data Manager 상태 (Excel 파일 개수)
    excel_count = len(pipeline_status["원천 DB"]["files"])

    status["data_manager"] = "normal" if excel_count >= 8 else "warning" if excel_count >= 5 else "error"




    openai_key = None

    try:

        import yaml

        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'model_config.yaml')

        if os.path.exists(config_path):

            with open(config_path, 'r', encoding='utf-8') as f:

                model_config = yaml.safe_load(f)

                openai_config = model_config.get('openai', {})

                openai_key = openai_config.get('api_key') or os.environ.get('OPENAI_API_KEY')

    except:

        # Fallback: 환경변수만 확인

        openai_key = os.environ.get('OPENAI_API_KEY')

    

    status["llm_manager"] = "normal" if openai_key and len(openai_key) > 20 else "error"

    

    # 3. Knowledge Graph 상태

    graph_exists = pipeline_status["그래프 파일"]["exists"]

    status["knowledge_graph"] = "normal" if graph_exists else "warning"

    

    # 4. Vector DB 상태

    rag_exists = pipeline_status["RAG 인덱스"]["exists"]

    status["vector_db"] = "normal" if rag_exists else "warning"

    

    return status





def get_status_border(status):

    """

    상태에 따른 테두리 스타일 반환

    

    Args:

        status: "normal", "warning", "error"

        

    Returns:

        (color, penwidth) 튜플

    """

    if status == "normal":

        return "green", "3"

    elif status == "warning":

        return "orange", "3"

    else:  # error

        return "red", "3"

#############################################################################



def get_step_status(step_name, status):

    """
    단계별 상태 반환
   
    Args:
        step_name: 단계 이름
        status: 파이프라인 상태 딕셔너리
      
    Returns:
        (상태 텍스트, 상태 타입)
    """
    if step_name not in status:
        return None, None
   
    info = status[step_name]
  
    if info["exists"]:

        # 모든 파일 중 최신 수정 시간 찾기
        latest_time = None
        file_count = 0
      
        for file_path in info["files"]:
            if os.path.exists(file_path):
                file_count += 1
                file_time = os.path.getmtime(file_path)
                if latest_time is None or file_time > latest_time:
                    latest_time = file_time
      
        if latest_time:
            file_time_str = datetime.fromtimestamp(latest_time).strftime("%Y-%m-%d %H:%M")
           
            # 원천 DB의 경우 파일 개수도 표시
            if step_name == "원천 DB":
                return f"{file_count}개 파일 (최신: {file_time_str})", "success"
            else:
                return f"마지막 업데이트: {file_time_str}", "success"
        else:
            return "파일 존재", "success"
    else:

        if info["required"]:
            return "파일 없음 (필수)", "error"
        else:
            return "파일 없음 (선택)", "info"

def render_pipeline_status(config, show_diagram=True):
    """
    파이프라인 상태 대시보드 랜더링 (Graphviz 기반 상세 흐름도)
   
    Args:
        config: 설정 딕셔너리
    """

    if show_diagram:
        st.header("시스템 아키텍처 및 데이터 흐름도")
  
        # 파이프라인 상태 체크 (기존 로직 활용)
        pipeline_status = check_pipeline_status(config)
  
        # 컴포넌트 상태 체크 
        component_status = check_component_status(config, pipeline_status)

  

        # 계산
        dm_border, dm_pen = get_status_border(component_status["data_manager"])
        llm_border, llm_pen = get_status_border(component_status["llm_manager"])
        graph_border, graph_pen = get_status_border(component_status["knowledge_graph"])
        vector_border, vector_pen = get_status_border(component_status["vector_db"])
   
        # Graphviz DOT 언어로 흐름도 정의 (UX 개선 버전)
        dot = f"""
        digraph G {{
        rankdir=LR;
        splines=ortho;
        newrank=true;
        newrank=true;
        nodesep=0.7;
        ranksep=1.0;
        fontname="Malgun Gothic";
        fontsize=15;
        bgcolor="white";
        dpi=150;
        
        node [shape=box, style="filled,rounded", fontname="Malgun Gothic", fontsize=15, margin=0.35, height=0.7];
        edge [fontname="Malgun Gothic", fontsize=12, color="#757575", penwidth=1.5];

   
        # 2단계 구조 범례(영역 + 상태) - 가독성 개선
        subgraph cluster_legend {{
            label="범례";
            style=filled;
            fillcolor="#f5f5f5";
            color="#424242";
            fontcolor="#212121";
            fontsize=12;
            node [shape=plaintext, style=""];
            key [label=<
                <table border="0" cellpadding="6" cellspacing="6" cellborder="0">
                <!--  구역 구분 (배경) -->
                <tr><td colspan="4" align="left"><b><font point-size="11">구역(배경)</font></b></td></tr>
                <tr>
                    <td bgcolor="#E3F2FD" width="24" height="18" border="1" color="#1976D2"></td>
                    <td align="left"><font point-size="10">Data</font></td>
                    <td bgcolor="#F3E5F5" width="24" height="18" border="1" color="#7B1FA2"></td>
                    <td align="left"><font point-size="10">Agent</font></td>
                </tr>
                <tr>
                    <td bgcolor="#FCE4EC" width="24" height="18" border="1" color="#C2185B"></td>
                    <td align="left"><font point-size="10">AI Service</font></td>
                    <td bgcolor="#E8F5E9" width="24" height="18" border="1" color="#388E3C"></td>
                    <td align="left"><font point-size="10">User</font></td>
                </tr>
                <tr>
                    <td bgcolor="#ECEFF1" width="24" height="18" border="1" color="#546E7A"></td>
                    <td align="left"><font point-size="10">Others</font></td>
                    <td></td>
                    <td></td>
                </tr>
               
                <!-- 상태 시각화 -->
                <tr><td colspan="4" align="left"><b><font point-size="11"> 상태 (모두 정상인 경우)</font></b></td></tr>
                <tr>
                    <td bgcolor="white" width="24" height="18" border="4" color="#4CAF50"></td>
                    <td align="left"><font point-size="10">정상</font></td>
                    <td bgcolor="white" width="24" height="18" border="4" color="#FF9800"></td>
                    <td align="left"><font point-size="10">경고</font></td>
                </tr>
                <tr>
                    <td bgcolor="white" width="24" height="18" border="4" color="#F44336"></td>
                    <td align="left"><font point-size="10">오류</font></td>
                    <td></td>
                    <td></td>
                </tr>
               

                <!-- 연결 유형 (화살표) -->
                <tr><td colspan="4" align="left"><b><font point-size="11">연결 유형 (화살표)</font></b></td></tr>
                <tr>
                    <td align="center"><font point-size="10" color="#757575">━━━</font></td>
                    <td align="left"><font point-size="10">실선: 직접 데이터 흐름</font></td>
                    <td align="center"><font point-size="10" color="#1976D2">╌╌╌</font></td>
                    <td align="left"><font point-size="10">점선: 간접/참조 연결</font></td>
                </tr>
                <tr>
                    <td align="center"><font point-size="10" color="#757575">┄┄┄</font></td>
                    <td align="left"><font point-size="10">점선: 추론/설명 연결</font></td>
                    <td align="center"><font point-size="10" color="#388E3C"><b>━━━</b></font></td>
                    <td align="left"><font point-size="10">굵은선: 메인 흐름</font></td>
                </tr>
                </table>
            >];
        }}

        # 1. 원천 데이터 관리자 (Data Layer)
        subgraph cluster_data {{

            label="원천 데이터 관리자(Data Layer)";
            style=filled;
            color="#1976D2";
            fillcolor="#E3F2FD";
            fontcolor="#0D47A1";
            fontsize=12;
            penwidth=2;
           

            # Nodes - 원천 데이터 관리자
            source_db [label="원천 데이터\n(10개 파일 Excel)", shape=cylinder, fillcolor="#90CAF9", fontcolor="#0D47A1", color="#1976D2", penwidth=2, fontsize=15];
            doc_db [label="전문 문서\\n(PDF/Text)", shape=cylinder, fillcolor="#90CAF9", fontcolor="#0D47A1", color="#1976D2", penwidth=2, fontsize=15];
         
            # Nodes - 처리 진행 (진한 블루)
            data_manager [label=" 데이터관리자\\n(Data Manager)", shape=component, fillcolor="#BBDEFB", fontcolor="#0D47A1", color="{dm_border}", penwidth={dm_pen}, fontsize=15];
            onto_engine [label="온톨로지 변환기", shape=component, fillcolor="#BBDEFB", fontcolor="#0D47A1", color="#64B5F6", penwidth=2, fontsize=15];
        
            # Nodes - AI 비즈니스 로직 (Data Layer)
            rag_engine [label="임베딩 엔진\\n(rogel-embedding-v2)", shape=component, fillcolor="#F8BBD0", fontcolor="#880E4F", color="#EC407A", penwidth=2.5, fontsize=15];        


            # Nodes - 소스 데이터 (진한 블루)
            knowledge_graph [label="지식그래프\n(RDF/TTL)", shape=cylinder, fillcolor="#64B5F6", fontcolor="#0D47A1", color="{graph_border}", penwidth={graph_pen}, fontsize=15];
            vector_db [label="벡터 DB\\n(FAISS)\\n346개 문서", shape=cylinder, fillcolor="#64B5F6", fontcolor="#0D47A1", color="{vector_border}", penwidth={vector_pen}, fontsize=15];
         
            # Edges - 굵게
            source_db -> data_manager [label="로드", fontsize=12, penwidth=2];
            data_manager -> onto_engine [label="데이터", fontsize=12, penwidth=2];

            onto_engine -> knowledge_graph [label="스토어 ", fontsize=12, penwidth=2];
           

            doc_db -> rag_engine [label="임베딩", fontsize=12, penwidth=2];
            rag_engine -> vector_db [label="스토어", fontsize=12, penwidth=2];

        }}
        

        # 2. 파이프라인 조율(Orchestration Layer)

        subgraph cluster_orchestration {{
            label="파이프라인 조율 (Orchestration)";
            style=filled;
            color="#546E7A";
            fillcolor="#ECEFF1";
            fontcolor="#263238";
            fontsize=12;
            penwidth=2;
         
            # Nodes (Others 영역 - 회색)
            orchestrator [label="Orchestrator\\n(Core Pipeline)", shape=diamond, fillcolor="#B0BEC5", fontcolor="#263238", color="#607D8B", penwidth=2.5, fontsize=15];
        }}
      
        # 3. 지능형 에이전트 레이어(Agent Layer)
        subgraph cluster_agents {{

            label="지능형 에이전트 (Agent Layer)";
            style=filled;
            color="#7B1FA2";
            fillcolor="#F3E5F5";
            fontcolor="#4A148C";
            fontsize=12;
            penwidth=2;
           

            # Nodes - 에이전트 (COA 추천 Agent - 상황 분석 + COA 추천 통합)
            agent_coa [label="COA 추천 Agent\\n(EnhancedDefenseCOAAgent)\\n상황 분석 + COA 추천", shape=hexagon, fillcolor="#CE93D8", fontcolor="#4A148C", color="#8E24AA", penwidth=2.5, fontsize=15];
           

            # Nodes - AI 비즈니스로직(llm manager)
            llm_manager [label="LLM Manager", shape=hexagon, fillcolor="#F48FB1", fontcolor="#880E4F", color="{llm_border}", penwidth={llm_pen}, fontsize=15];
           

            # Nodes - Others (회색)
            coa_scorer [label="점수 계산기\n(COA Scorer)\\n7가지 요소", shape=hexagon, fillcolor="#B0BEC5", fontcolor="#263238", color="#607D8B", penwidth=2.5, fontsize=15];
            reasoner [label="온톨로지 추론기\n(SPARQL)", shape=component, fillcolor="#B0BEC5", fontcolor="#263238", color="{graph_border}", penwidth={graph_pen}, fontsize=15];
 
            # 에이전트 처리 흐름
            agent_coa -> coa_scorer [label="정보 전달", fontsize=12, penwidth=2];
            coa_scorer -> agent_coa [label="점수 반환", fontsize=12, penwidth=2];
           

            # LLM 결과 전달
            agent_coa -> llm_manager [label="상황 분석 / COA 적응화", fontsize=12, penwidth=2];
            llm_manager -> agent_coa [style=dotted, label="연결 설명", fontsize=12, penwidth=2];
           

            # 추론결과 전달
            agent_coa -> reasoner [dir=both, style=dotted, label="SPARQL", fontsize=12, penwidth=2];
        }}
       

        # 4. 지휘통제(User Layer)
        subgraph cluster_user {{
            label="지휘통제 (Command Layer)";
            style=filled;
            color="#388E3C";
            fillcolor="#E8F5E9";
            fontcolor="#1B5E20";
            fontsize=12;
            penwidth=2;
           
            # Nodes - UI (사용자)
            user_input [label="상황 입력\\n(Dashboard)", shape=rect, fillcolor="#81C784", fontcolor="#1B5E20", color="#43A047", penwidth=2.5, fontsize=15];
            result_view [label="방책 결과 시각화\n(Top 3)", shape=rect, fillcolor="#81C784", fontcolor="#1B5E20", color="#43A047", penwidth=2.5, fontsize=15];
            chain_viz [label="전략 체인 시각화\n(Graphviz)", shape=rect, fillcolor="#81C784", fontcolor="#1B5E20", color="#43A047", penwidth=2.5, fontsize=15];
            feedback [label="사용자 피드백", shape=parallelogram, fillcolor="#A5D6A7", fontcolor="#1B5E20", color="#43A047", penwidth=2.5, fontsize=15];
         
            # Layout hint
            user_input -> result_view [style=invis];
            result_view -> chain_viz [style=invis];
        }}
       

        # Cross-Layer Connections (굵고 명확하게)
        
        # Data -> Orchestrator
        knowledge_graph -> orchestrator [style=dashed, color="#1976D2", penwidth=2];
    

        # Orchestrator -> Agents

        orchestrator -> agent_coa [label="요청", fontsize=12, penwidth=2.5, color="#546E7A"];
       

        # Data -> Agents (직접 연결)
        knowledge_graph -> reasoner [style=dashed, color="#1976D2", label="그래프 파일", fontsize=12, penwidth=2];
       

        # Data -> Scorer
        knowledge_graph -> coa_scorer [style=dashed, color="#1976D2", label="자원/제약", fontsize=12, penwidth=2];
        vector_db -> coa_scorer [style=dashed, color="#1976D2", label="문맥", fontsize=12, penwidth=2];
      
        # User -> Orchestrator -> User (메인 흐름 강조)
        user_input -> orchestrator [label="요청", color="#388E3C", penwidth=3.5, fontsize=13, fontcolor="#388E3C", decorate=true, labeldistance=1.5];
        agent_coa -> result_view [label="추천", color="#388E3C", penwidth=3.5, fontsize=12, fontcolor="#1B5E20"];

        

        # Reasoner -> Visualizer
        reasoner -> chain_viz [style=dotted, label="경로 탐색", fontsize=12, penwidth=2];
        result_view -> chain_viz [label="체인 정보", fontsize=12, penwidth=2];
      

        # Feedback loop
        result_view -> feedback [penwidth=2];
        feedback -> orchestrator [label="조정", style=dotted, color="#757575", penwidth=2, fontsize=12];
        }}
        """

        # 간단하고 확실한 DOT 코드로 교체
        try:
            # 간단한 데이터 흐름 다이어그램 생성 (원래 변수명 사용)
            simple_dot = f"""
            digraph Pipeline {{
                rankdir=LR;
                splines=ortho;
                fontname="Malgun Gothic";
                fontsize=12;
                bgcolor="white";
                
                node [shape=box, style="filled,rounded", fontname="Malgun Gothic"];
                edge [fontname="Malgun Gothic", fontsize=10];
                
                // Data Layer
                subgraph cluster_data {{
                    label="데이터 관리 (Data Layer)";
                    style=filled;
                    fillcolor="#E3F2FD";
                    color="#1976D2";
                    
                    source_db [label="원천 데이터\\n(Excel)", shape=cylinder, fillcolor="#90CAF9"];
                    data_manager [label="데이터 관리자", fillcolor="#BBDEFB", color="{dm_border}", penwidth={dm_pen}];
                    onto_engine [label="온톨로지 변환기", fillcolor="#BBDEFB"];
                    knowledge_graph [label="지식 그래프\\n(RDF/TTL)", shape=cylinder, fillcolor="#64B5F6", color="{graph_border}", penwidth={graph_pen}];
                    rag_engine [label="임베딩 엔진", fillcolor="#F8BBD0"];
                    vector_db [label="벡터 DB\\n(FAISS)", shape=cylinder, fillcolor="#64B5F6", color="{vector_border}", penwidth={vector_pen}];
                    
                    source_db -> data_manager [label="로드"];
                    data_manager -> onto_engine [label="데이터"];
                    onto_engine -> knowledge_graph [label="스토어"];
                    rag_engine -> vector_db [label="임베딩"];
                }}
                
                // Orchestration Layer
                subgraph cluster_orch {{
                    label="파이프라인 조율 (Orchestration)";
                    style=filled;
                    fillcolor="#ECEFF1";
                    color="#546E7A";
                    
                    orchestrator [label="Orchestrator\\n(Core Pipeline)", shape=diamond, fillcolor="#B0BEC5"];
                }}
                
                // Agent Layer
                subgraph cluster_agents {{
                    label="지능형 에이전트 (Agent Layer)";
                    style=filled;
                    fillcolor="#F3E5F5";
                    color="#7B1FA2";
                    
                    agent_situation [label="상황 분석\\nAgent", shape=hexagon, fillcolor="#CE93D8"];
                    agent_coa [label="COA 추천\\nAgent", shape=hexagon, fillcolor="#CE93D8"];
                    llm_manager [label="LLM Manager\\n(OpenAI)", shape=hexagon, fillcolor="#F48FB1", color="{llm_border}", penwidth={llm_pen}];
                    coa_scorer [label="점수 계산기\\n(COA Scorer)", shape=hexagon, fillcolor="#B0BEC5"];
                    reasoner [label="온톨로지 추론기\\n(SPARQL)", fillcolor="#B0BEC5", color="{graph_border}", penwidth={graph_pen}];
                    
                    agent_situation -> agent_coa [label="분석 결과"];
                    agent_coa -> coa_scorer [label="정보 전달"];
                    coa_scorer -> agent_coa [label="점수 반환"];
                    agent_situation -> llm_manager [label="상황 분석"];
                    agent_coa -> llm_manager [label="COA 적응화"];
                    llm_manager -> agent_coa [style=dotted, label="연결 설명"];
                    agent_coa -> reasoner [dir=both, style=dotted, label="SPARQL"];
                }}
                
                // User Layer
                subgraph cluster_user {{
                    label="지휘통제 (Command Layer)";
                    style=filled;
                    fillcolor="#E8F5E9";
                    color="#388E3C";
                    
                    user_input [label="상황 입력\\n(Dashboard)", fillcolor="#81C784"];
                    result_view [label="방책 결과 시각화\\n(Top 3)", fillcolor="#81C784"];
                    chain_viz [label="전략 체인 시각화", fillcolor="#81C784"];
                    feedback [label="사용자 피드백", shape=parallelogram, fillcolor="#A5D6A7"];
                    
                    user_input -> result_view [style=invis];
                    result_view -> chain_viz [style=invis];
                }}
                
                // Cross-Layer Connections
                knowledge_graph -> orchestrator [style=dashed, color="#1976D2"];
                orchestrator -> agent_situation [label="분석 요청", color="#546E7A"];
                orchestrator -> agent_coa [color="#546E7A"];
                knowledge_graph -> reasoner [style=dashed, color="#1976D2", label="그래프 파일"];
                knowledge_graph -> coa_scorer [style=dashed, color="#1976D2", label="자원/제약"];
                vector_db -> coa_scorer [style=dashed, color="#1976D2", label="문맥"];
                user_input -> orchestrator [label="요청", color="#388E3C", penwidth=3];
                agent_coa -> result_view [label="추천", color="#388E3C", penwidth=3];
                reasoner -> chain_viz [style=dotted, label="경로 탐색"];
                result_view -> chain_viz [label="체인 정보"];
                result_view -> feedback;
                feedback -> orchestrator [label="조정", style=dotted, color="#757575"];
            }}
            """
            
            # Graphviz 렌더링
            st.graphviz_chart(dot, width='stretch')
            
        except Exception as e:
            import traceback
            st.error(f"❌ 다이어그램 렌더링 오류: {str(e)}")
            with st.expander("🔍 상세 오류 정보"):
                st.code(traceback.format_exc(), language='python')
            
            # 최소한의 테스트 다이어그램
            try:
                test_dot = 'digraph Test { A [label="테스트"]; B [label="성공"]; A -> B; }'
                st.graphviz_chart(test_dot)
                st.info("💡 기본 Graphviz는 작동하지만 복잡한 다이어그램에 문제가 있습니다.")
            except:
                st.error("❌ Graphviz가 설치되지 않았거나 작동하지 않습니다.")

    












