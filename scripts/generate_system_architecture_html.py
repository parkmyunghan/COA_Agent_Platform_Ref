# scripts/generate_system_architecture_html.py
# -*- coding: utf-8 -*-
"""
시스템 아키텍처 다이어그램을 HTML로 변환하는 스크립트
Mermaid 다이어그램을 HTML 파일로 생성
"""
import os
import sys
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

def generate_mermaid_diagram(config):
    """Mermaid 다이어그램 코드 생성"""
    mermaid = """
graph LR
    subgraph Data["🏗️ 원천 데이터 관리자 (Data Layer)"]
        direction TB
        SourceDB[("원천 데이터<br/>(10개 파일 Excel)")]
        DocDB[("전문 문서<br/>(PDF/Text)")]
        DataMgr[데이터관리자<br/>Data Manager]
        OntoEngine[온톨로지 변환기]
        RAGEngine[임베딩 엔진<br/>rogel-embedding-v2]
        KG[("지식그래프<br/>(RDF/TTL)<br/>schema.ttl<br/>instances.ttl<br/>instances_reasoned.ttl")]
        VectorDB[("벡터 DB<br/>(FAISS)<br/>346개 문서")]
        
        SourceDB -->|로드| DataMgr
        DataMgr -->|데이터| OntoEngine
        OntoEngine -->|스키마| KG
        OntoEngine -->|인스턴스| KG
        OntoEngine -->|추론 결과| KG
        DocDB -->|임베딩| RAGEngine
        RAGEngine -->|스토어| VectorDB
    end
    
    subgraph Orchestration["⚙️ 파이프라인 조율 (Orchestration)"]
        Orchestrator{Orchestrator<br/>Core Pipeline}
    end
    
    subgraph Agents["🤖 지능형 에이전트 (Agent Layer)"]
        direction TB
        COAAgent[COA 추천 Agent<br/>EnhancedDefenseCOAAgent]
        LLMMgr[LLM Manager]
        Scorer[점수 계산기<br/>COA Scorer<br/>7가지 요소]
        Reasoner[온톨로지 추론기<br/>SPARQL]
        
        COAAgent -->|정보 전달| Scorer
        Scorer -->|점수 반환| COAAgent
        COAAgent -->|상황 분석| LLMMgr
        COAAgent -->|COA 적응화| LLMMgr
        LLMMgr -.->|연결 설명| COAAgent
        COAAgent <-->|SPARQL| Reasoner
    end
    
    subgraph User["👤 지휘통제 (Command Layer)"]
        direction TB
        UserInput[상황 입력<br/>Dashboard]
        ResultView[방책 결과 시각화<br/>Top 3]
        ChainViz[전략 체인 시각화<br/>Graphviz]
        Feedback[사용자 피드백]
        
        UserInput --> ResultView
        ResultView --> ChainViz
    end
    
    %% Cross-Layer Connections
    KG -.->|스키마/인스턴스| Orchestrator
    Orchestrator -->|요청| COAAgent
    KG -.->|SPARQL 쿼리| Reasoner
    KG -.->|자원/제약| Scorer
    VectorDB -.->|문맥| Scorer
    UserInput ==>|요청| Orchestrator
    COAAgent ==>|추천| ResultView
    Reasoner -.->|경로 탐색| ChainViz
    ResultView -->|체인 정보| ChainViz
    ResultView --> Feedback
    Feedback -.->|조정| Orchestrator
    
    %% 스타일 정의
    classDef dataLayer fill:#E3F2FD,stroke:#1976D2,stroke-width:3px,color:#0D47A1,font-size:16px
    classDef agentLayer fill:#F3E5F5,stroke:#7B1FA2,stroke-width:3px,color:#4A148C,font-size:16px
    classDef userLayer fill:#E8F5E9,stroke:#388E3C,stroke-width:3px,color:#1B5E20,font-size:16px
    classDef orchestration fill:#ECEFF1,stroke:#546E7A,stroke-width:3px,color:#263238,font-size:16px
    classDef mainFlow stroke:#388E3C,stroke-width:5px
    classDef aiService fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#880E4F,font-size:16px
    
    %% 스타일 적용
    class SourceDB,DocDB,DataMgr,OntoEngine,KG,VectorDB dataLayer
    class COAAgent,Scorer,Reasoner agentLayer
    class UserInput,ResultView,ChainViz,Feedback userLayer
    class Orchestrator orchestration
    class RAGEngine,LLMMgr aiService
    class UserInput,Orchestrator,COAAgent,ResultView mainFlow
"""
    return mermaid.strip()

def get_component_docs_mapping():
    """컴포넌트 ID와 문서 경로 매핑 (절대 경로 포함)"""
    # Mermaid 노드 ID -> 문서 경로 매핑
    # 노드 ID는 Mermaid 다이어그램에서 정의한 ID와 일치해야 함
    docs_dir = BASE_DIR / "docs"
    
    mapping = {
        # Data Layer
        "DataMgr": str((docs_dir / "components" / "data_layer" / "01_데이터관리자.md").absolute()),
        "OntoEngine": str((docs_dir / "components" / "data_layer" / "02_온톨로지변환기.md").absolute()),
        "RAGEngine": str((docs_dir / "components" / "data_layer" / "03_임베딩엔진.md").absolute()),
        "KG": str((docs_dir / "components" / "data_layer" / "04_지식그래프.md").absolute()),
        "VectorDB": str((docs_dir / "components" / "data_layer" / "05_벡터DB.md").absolute()),
        # Orchestration Layer
        "Orchestrator": str((docs_dir / "components" / "orchestration_layer" / "01_Orchestrator.md").absolute()),
        # Agent Layer
        "COAAgent": str((docs_dir / "components" / "agent_layer" / "01_COA_추천_Agent.md").absolute()),
        "LLMMgr": str((docs_dir / "components" / "agent_layer" / "02_LLM_Manager.md").absolute()),
        "Scorer": str((docs_dir / "components" / "agent_layer" / "03_점수계산기.md").absolute()),
        "Reasoner": str((docs_dir / "components" / "agent_layer" / "04_온톨로지추론기.md").absolute()),
        # Command Layer
        "UserInput": str((docs_dir / "components" / "command_layer" / "01_상황입력.md").absolute()),
        "ResultView": str((docs_dir / "components" / "command_layer" / "02_방책결과시각화.md").absolute()),
        "ChainViz": str((docs_dir / "components" / "command_layer" / "03_전략체인시각화.md").absolute()),
        "Feedback": str((docs_dir / "components" / "command_layer" / "04_사용자피드백.md").absolute()),
    }
    return mapping

def generate_component_links_html():
    """컴포넌트 링크 섹션 HTML 생성"""
    import urllib.parse
    import re
    mapping = get_component_docs_mapping()
    
    # 레이어별로 그룹화
    layers = {
        "🏗️ Data Layer": ["DataMgr", "OntoEngine", "RAGEngine", "KG", "VectorDB"],
        "⚙️ Orchestration Layer": ["Orchestrator"],
        "🤖 Agent Layer": ["COAAgent", "LLMMgr", "Scorer", "Reasoner"],
        "👤 Command Layer": ["UserInput", "ResultView", "ChainViz", "Feedback"]
    }
    
    # 컴포넌트 이름 매핑
    component_names = {
        "DataMgr": "데이터관리자 (Data Manager)",
        "OntoEngine": "온톨로지 변환기",
        "RAGEngine": "임베딩 엔진 (rogel-embedding-v2)",
        "KG": "지식그래프 (RDF/TTL)",
        "VectorDB": "벡터 DB (FAISS)",
        "Orchestrator": "Orchestrator (CorePipeline)",
        "COAAgent": "COA 추천 Agent",
        "LLMMgr": "LLM Manager",
        "Scorer": "점수 계산기 (COA Scorer)",
        "Reasoner": "온톨로지 추론기 (SPARQL)",
        "UserInput": "상황 입력 (Dashboard)",
        "ResultView": "방책 결과 시각화 (Top 3)",
        "ChainViz": "전략 체인 시각화 (Graphviz)",
        "Feedback": "사용자 피드백"
    }
    
    html = """
        <div class="component-links">
            <h2>📚 컴포넌트 상세 문서</h2>
            <p style="font-size: 16px; line-height: 1.8; margin-bottom: 20px;">
                다이어그램의 각 컴포넌트를 클릭하거나 아래 링크를 통해 상세 문서를 확인할 수 있습니다.
            </p>
    """
    
    for layer_name, component_ids in layers.items():
        html += f"""
            <div class="layer-section">
                <h3>{layer_name}</h3>
                <ul class="component-list">
        """
        for comp_id in component_ids:
            if comp_id in mapping:
                doc_path = mapping[comp_id]
                comp_name = component_names.get(comp_id, comp_id)
                # Windows 경로를 file:// URL로 변환
                # 백슬래시를 슬래시로 변환
                file_url = doc_path.replace('\\', '/')
                # 드라이브 문자 처리 (C:/ -> /C:/)
                if re.match(r'^[A-Z]:/', file_url):
                    file_url = '/' + file_url
                # 경로 부분만 인코딩 (file:// 프로토콜은 인코딩하지 않음)
                path_parts = file_url.split('/')
                encoded_parts = [urllib.parse.quote(part, safe='') for part in path_parts]
                file_url = 'file://' + '/'.join(encoded_parts)
                
                html += f"""
                    <li>
                        <a href="{file_url}" 
                           target="_blank" 
                           class="component-link"
                           data-component-id="{comp_id}"
                           onclick="console.log('링크 클릭:', '{{comp_id}}', '{{file_url}}'); return true;">
                            {comp_name}
                        </a>
                    </li>
                """
        html += """
                </ul>
            </div>
        """
    
    html += """
        </div>
    """
    return html

def generate_html(mermaid_code, output_path):
    """Mermaid 다이어그램을 HTML로 변환"""
    component_links_html = generate_component_links_html()
    component_mapping = get_component_docs_mapping()
    
    # JavaScript에서 사용할 수 있도록 매핑을 JSON으로 변환
    mapping_json = str(component_mapping).replace("'", '"')
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>시스템 아키텍처 및 데이터 흐름도</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: "Malgun Gothic", "맑은 고딕", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        @media (max-width: 1200px) {{
            .container {{
                padding: 20px;
            }}
        }}
        
        h1 {{
            color: #1976D2;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 4px solid #1976D2;
            font-size: 32px;
        }}
        
        .diagram-container {{
            width: 100%;
            margin: 30px 0;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            position: relative;
            overflow: hidden;
        }}
        
        .mermaid-wrapper {{
            width: 100%;
            height: 70vh;
            min-height: 600px;
            overflow: auto;
            cursor: grab;
            position: relative;
            background-color: #f5f5f5;
            border-radius: 8px;
            -webkit-overflow-scrolling: touch;
        }}
        
        .mermaid-wrapper.dragging {{
            cursor: grabbing !important;
            user-select: none;
        }}
        
        .mermaid-wrapper:not(.dragging) {{
            cursor: grab;
        }}
        
        .mermaid {{
            text-align: left;
            font-size: 20px;
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            display: inline-block;
            position: relative;
            min-width: fit-content;
        }}
        
        .mermaid svg {{
            display: block;
            width: auto;
            height: auto;
        }}
        
        .zoom-controls {{
            position: absolute;
            top: 30px;
            right: 30px;
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        
        .zoom-btn {{
            background: #1976D2;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 18px;
            font-weight: bold;
            min-width: 50px;
            transition: background 0.2s;
        }}
        
        .zoom-btn:hover {{
            background: #1565C0;
        }}
        
        .zoom-btn:active {{
            background: #0D47A1;
        }}
        
        .zoom-info {{
            text-align: center;
            padding: 5px;
            font-size: 14px;
            color: #424242;
        }}
        
        .description {{
            margin-top: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #f9f9f9 0%, #e8f4f8 100%);
            border-left: 5px solid #1976D2;
            border-radius: 8px;
        }}
        
        .description h2 {{
            color: #1976D2;
            margin-bottom: 15px;
            font-size: 24px;
        }}
        
        .description h3 {{
            color: #424242;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 20px;
        }}
        
        .description ul {{
            line-height: 2;
            margin-left: 20px;
        }}
        
        .description li {{
            margin-bottom: 8px;
        }}
        
        .description strong {{
            color: #1976D2;
        }}
        
        .tip-box {{
            margin-top: 20px;
            padding: 15px;
            background-color: #E3F2FD;
            border-left: 4px solid #1976D2;
            border-radius: 4px;
        }}
        
        .tip-box strong {{
            color: #0D47A1;
        }}
        
        /* 컴포넌트 링크 섹션 */
        .component-links {{
            margin-top: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #fff9e6 0%, #ffe8cc 100%);
            border-left: 5px solid #FF9800;
            border-radius: 8px;
        }}
        
        .component-links h2 {{
            color: #FF9800;
            margin-bottom: 15px;
            font-size: 24px;
        }}
        
        .component-links h3 {{
            color: #E65100;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 20px;
            padding-bottom: 8px;
            border-bottom: 2px solid #FFB74D;
        }}
        
        .layer-section {{
            margin-bottom: 20px;
        }}
        
        .component-list {{
            list-style: none;
            padding-left: 0;
            margin: 0;
        }}
        
        .component-list li {{
            margin-bottom: 10px;
            padding: 8px 0;
        }}
        
        .component-link {{
            display: inline-block;
            padding: 10px 15px;
            background-color: #FFF3E0;
            color: #E65100;
            text-decoration: none;
            border-radius: 5px;
            border: 2px solid #FFB74D;
            transition: all 0.3s ease;
            font-weight: 500;
        }}
        
        .component-link:hover {{
            background-color: #FFE0B2;
            border-color: #FF9800;
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
        }}
        
        .component-link:active {{
            transform: translateX(3px);
        }}
        
        /* Mermaid 노드 클릭 가능 스타일 */
        .mermaid svg .node {{
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        
        .mermaid svg .node:hover {{
            opacity: 0.8;
        }}
        
        /* 스크롤바 스타일링 */
        .diagram-container::-webkit-scrollbar {{
            height: 12px;
        }}
        
        .diagram-container::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 6px;
        }}
        
        .diagram-container::-webkit-scrollbar-thumb {{
            background: #1976D2;
            border-radius: 6px;
        }}
        
        .diagram-container::-webkit-scrollbar-thumb:hover {{
            background: #1565C0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>시스템 아키텍처 및 데이터 흐름도</h1>
        
        <div class="diagram-container">
            <div class="zoom-controls">
                <button class="zoom-btn" onclick="zoomIn()" title="확대">+</button>
                <div class="zoom-info">
                    <span id="zoom-level">100%</span>
                </div>
                <button class="zoom-btn" onclick="zoomOut()" title="축소">-</button>
                <button class="zoom-btn" onclick="resetZoom()" title="초기화" style="font-size: 14px; padding: 8px;">⟲</button>
            </div>
            <div class="mermaid-wrapper" id="mermaid-wrapper">
                <div class="mermaid" id="mermaid-diagram">
{mermaid_code}
                </div>
            </div>
        </div>
        
        <div class="description">
            <h2>시스템 개요</h2>
            <p style="font-size: 16px; line-height: 1.8; margin-bottom: 20px;">
                이 다이어그램은 Defense Intelligent Agent Platform의 전체 아키텍처와 데이터 흐름을 보여줍니다.
                시스템은 4개의 주요 레이어로 구성되어 있으며, 각 레이어는 명확한 역할과 책임을 가지고 있습니다.
            </p>
            
            <h3>주요 구성 요소</h3>
            <ul>
                <li><strong>🏗️ Data Layer (원천 데이터 관리자)</strong>: Excel 파일과 전문 문서를 로드하여 지식그래프와 벡터 DB로 변환</li>
                <li><strong>⚙️ Orchestration Layer (파이프라인 조율)</strong>: 전체 시스템의 워크플로우를 조율하고 제어</li>
                <li><strong>🤖 Agent Layer (지능형 에이전트)</strong>: 상황 분석, COA 추천, 점수 계산 등 지능형 처리 수행</li>
                <li><strong>👤 Command Layer (지휘통제)</strong>: 사용자 인터페이스 및 결과 시각화</li>
            </ul>
            
            <h3>데이터 흐름</h3>
            <ul>
                <li><strong>실선 (→)</strong>: 직접적인 데이터 흐름</li>
                <li><strong>점선 (-.->)</strong>: 간접/참조 연결 또는 추론 연결</li>
                <li><strong>굵은 실선 (==>)</strong>: 메인 흐름 (요청 → 처리 → 추천)</li>
            </ul>
            
            <div class="tip-box">
                <strong>💡 사용 방법:</strong>
                <ul style="margin-top: 10px; margin-left: 20px;">
                    <li><strong>드래그 이동:</strong> 마우스로 다이어그램을 클릭하고 드래그하여 이동</li>
                    <li><strong>확대/축소:</strong> 우측 상단 버튼 또는 Ctrl + 마우스 휠</li>
                    <li><strong>키보드 단축키:</strong> Ctrl + = (확대), Ctrl + - (축소), Ctrl + 0 (초기화)</li>
                    <li><strong>스크롤:</strong> 마우스 휠로 스크롤 가능</li>
                    <li><strong>컴포넌트 클릭:</strong> 다이어그램의 컴포넌트를 클릭하면 상세 문서로 이동</li>
                </ul>
            </div>
        </div>
        
        {component_links_html}
    </div>
    
    <script>
        // 컴포넌트 문서 매핑
        const componentDocs = {mapping_json};
        
        // 컴포넌트 ID를 노드 ID로 변환하는 함수
        function getNodeIdFromComponentId(componentId) {{
            // Mermaid 노드 ID는 보통 소문자로 시작하지만, 실제로는 다이어그램에서 정의한 대로 사용
            return componentId;
        }}
        
        // 문서 경로를 열기
        function openComponentDoc(componentId) {{
            console.log('openComponentDoc 호출:', componentId);
            console.log('componentDocs:', componentDocs);
            
            if (componentDocs[componentId]) {{
                const docPath = componentDocs[componentId];
                console.log('문서 경로:', docPath);
                
                // Windows 절대 경로를 file:// URL로 변환
                let fileUrl = docPath.replace(/\\\\/g, '/');
                // 드라이브 문자 처리 (C:/ -> /C:/)
                if (fileUrl.match(/^[A-Z]:/)) {{
                    fileUrl = '/' + fileUrl;
                }}
                // file:// 프로토콜 추가
                if (!fileUrl.startsWith('file://')) {{
                    fileUrl = 'file://' + fileUrl;
                }}
                // 공백과 특수문자 인코딩
                fileUrl = encodeURI(fileUrl);
                
                console.log('최종 URL:', fileUrl);
                
                try {{
                    window.open(fileUrl, '_blank');
                }} catch (e) {{
                    console.error('파일 열기 실패:', e);
                    alert('파일을 열 수 없습니다. 경로를 확인하세요:\\n' + fileUrl);
                }}
            }} else {{
                console.log('문서를 찾을 수 없습니다:', componentId);
                console.log('사용 가능한 컴포넌트:', Object.keys(componentDocs));
            }}
        }}
        
        let currentZoom = 1.0;
        const minZoom = 0.5;
        const maxZoom = 3.0;
        const zoomStep = 0.2;
        
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            themeVariables: {{
                fontSize: '20px',
                fontFamily: 'Malgun Gothic, 맑은 고딕, Arial, sans-serif',
                primaryColor: '#E3F2FD',
                primaryTextColor: '#0D47A1',
                primaryBorderColor: '#1976D2',
                lineColor: '#757575',
                secondaryColor: '#F3E5F5',
                tertiaryColor: '#E8F5E9'
            }},
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true,
                curve: 'basis',
                padding: 20,
                nodeSpacing: 60,
                rankSpacing: 100
            }},
            securityLevel: 'loose'
        }});
        
        let baseSvgWidth = null;
        let baseSvgHeight = null;
        
        function updateZoom() {{
            const diagram = document.getElementById('mermaid-diagram');
            const svg = diagram.querySelector('svg');
            if (svg) {{
                // 기본 크기 저장 (첫 번째 호출 시)
                if (!baseSvgWidth || !baseSvgHeight) {{
                    baseSvgWidth = parseFloat(svg.getAttribute('width')) || svg.viewBox.baseVal.width;
                    baseSvgHeight = parseFloat(svg.getAttribute('height')) || svg.viewBox.baseVal.height;
                }}
                
                // SVG 크기를 확대/축소
                const newWidth = baseSvgWidth * currentZoom;
                const newHeight = baseSvgHeight * currentZoom;
                svg.setAttribute('width', newWidth);
                svg.setAttribute('height', newHeight);
                svg.style.width = newWidth + 'px';
                svg.style.height = newHeight + 'px';
            }}
            document.getElementById('zoom-level').textContent = Math.round(currentZoom * 100) + '%';
        }}
        
        // Mermaid 렌더링 완료 후 초기 크기 저장 및 노드 클릭 이벤트 추가
        function setupDiagram() {{
            const diagram = document.getElementById('mermaid-diagram');
            const svg = diagram.querySelector('svg');
            if (svg) {{
                // 기본 크기 저장
                baseSvgWidth = parseFloat(svg.getAttribute('width')) || svg.viewBox.baseVal.width;
                baseSvgHeight = parseFloat(svg.getAttribute('height')) || svg.viewBox.baseVal.height;
                
                // SVG가 원래 크기로 표시되도록
                svg.setAttribute('preserveAspectRatio', 'none');
                svg.style.width = baseSvgWidth + 'px';
                svg.style.height = baseSvgHeight + 'px';
                
                // 노드에 클릭 이벤트 추가
                setupNodeClickEvents(svg);
            }}
        }}
        
        // 텍스트 기반 컴포넌트 매핑 (노드 ID를 찾을 수 없을 때 사용)
        const textToComponentMap = {{
            '데이터관리자': 'DataMgr',
            'Data Manager': 'DataMgr',
            '온톨로지 변환기': 'OntoEngine',
            '임베딩 엔진': 'RAGEngine',
            'rogel-embedding-v2': 'RAGEngine',
            '지식그래프': 'KG',
            'RDF/TTL': 'KG',
            '벡터 DB': 'VectorDB',
            'FAISS': 'VectorDB',
            'Orchestrator': 'Orchestrator',
            'Core Pipeline': 'Orchestrator',
            'COA 추천 Agent': 'COAAgent',
            'EnhancedDefenseCOAAgent': 'COAAgent',
            'LLM Manager': 'LLMMgr',
            '점수 계산기': 'Scorer',
            'COA Scorer': 'Scorer',
            '온톨로지 추론기': 'Reasoner',
            'SPARQL': 'Reasoner',
            '상황 입력': 'UserInput',
            'Dashboard': 'UserInput',
            '방책 결과 시각화': 'ResultView',
            'Top 3': 'ResultView',
            '전략 체인 시각화': 'ChainViz',
            'Graphviz': 'ChainViz',
            '사용자 피드백': 'Feedback'
        }};
        
        // 텍스트에서 컴포넌트 ID 찾기
        function findComponentIdFromText(text) {{
            if (!text) return null;
            const normalizedText = text.trim();
            for (const [key, compId] of Object.entries(textToComponentMap)) {{
                if (normalizedText.includes(key)) {{
                    return compId;
                }}
            }}
            return null;
        }}
        
        // Mermaid 노드에 클릭 이벤트 추가 (완전히 새로운 접근)
        function setupNodeClickEvents(svg) {{
            console.log('setupNodeClickEvents 시작');
            
            // 모든 가능한 노드 선택
            const allNodes = svg.querySelectorAll('g');
            console.log('전체 g 요소 수:', allNodes.length);
            
            // 노드 ID와 컴포넌트 매핑 저장
            const nodeComponentMap = new Map();
            
            // 1단계: 모든 노드를 순회하며 ID와 텍스트 수집
            allNodes.forEach((node, index) => {{
                let nodeId = null;
                let nodeText = '';
                
                // title에서 ID 추출
                const title = node.querySelector('title');
                if (title) {{
                    nodeId = title.textContent.trim();
                }}
                
                // id 속성에서 추출
                if (!nodeId && node.id) {{
                    nodeId = node.id.replace(/^flowchart-/, '').replace(/-node$/, '');
                }}
                
                // 텍스트 수집
                const textElements = node.querySelectorAll('text');
                textElements.forEach(text => {{
                    nodeText += (text.textContent || '') + ' ';
                }});
                nodeText = nodeText.trim();
                
                // 텍스트에서 컴포넌트 ID 찾기
                if (nodeText) {{
                    const foundId = findComponentIdFromText(nodeText);
                    if (foundId && componentDocs[foundId]) {{
                        nodeId = foundId;
                    }}
                }}
                
                // 노드 ID가 있으면 매핑에 저장
                if (nodeId && componentDocs[nodeId]) {{
                    nodeComponentMap.set(node, nodeId);
                    console.log('노드 매핑:', nodeId, '텍스트:', nodeText.substring(0, 50));
                }}
            }});
            
            console.log('매핑된 노드 수:', nodeComponentMap.size);
            
            // 2단계: SVG 전체에 클릭 이벤트 추가 (이벤트 위임)
            svg.addEventListener('click', function(e) {{
                // 클릭된 요소에서 가장 가까운 노드 찾기
                let target = e.target;
                let clickedNode = null;
                
                // 위로 올라가며 노드 찾기
                while (target && target !== svg) {{
                    if (nodeComponentMap.has(target)) {{
                        clickedNode = target;
                        break;
                    }}
                    // 부모 노드도 확인
                    if (target.parentElement && nodeComponentMap.has(target.parentElement)) {{
                        clickedNode = target.parentElement;
                        break;
                    }}
                    target = target.parentElement;
                }}
                
                if (clickedNode) {{
                    const componentId = nodeComponentMap.get(clickedNode);
                    console.log('노드 클릭 감지:', componentId);
                    e.stopPropagation();
                    e.preventDefault();
                    openComponentDoc(componentId);
                    return false;
                }}
            }}, true); // capture phase
            
            // 3단계: 각 노드에 호버 효과 추가
            nodeComponentMap.forEach((componentId, node) => {{
                node.style.cursor = 'pointer';
                
                node.addEventListener('mouseenter', function() {{
                    node.style.opacity = '0.85';
                    node.style.filter = 'brightness(1.1)';
                }});
                
                node.addEventListener('mouseleave', function() {{
                    node.style.opacity = '1';
                    node.style.filter = 'none';
                }});
            }});
            
            console.log('setupNodeClickEvents 완료');
        }}
        
        // Mermaid 렌더링 완료 대기
        const checkMermaidReady = setInterval(function() {{
            const svg = document.querySelector('#mermaid-diagram svg');
            if (svg && svg.getAttribute('width')) {{
                clearInterval(checkMermaidReady);
                setupDiagram();
                // 추가로 노드 클릭 이벤트 재설정 (렌더링 완료 후)
                setTimeout(function() {{
                    const svg = document.querySelector('#mermaid-diagram svg');
                    if (svg) {{
                        setupNodeClickEvents(svg);
                    }}
                }}, 500);
            }}
        }}, 100);
        
        // 최대 5초 후에도 렌더링이 안 되면 강제 설정
        setTimeout(function() {{
            if (!baseSvgWidth || !baseSvgHeight) {{
                setupDiagram();
            }}
        }}, 5000);
        
        function zoomIn() {{
            if (currentZoom < maxZoom) {{
                currentZoom = Math.min(currentZoom + zoomStep, maxZoom);
                updateZoom();
            }}
        }}
        
        function zoomOut() {{
            if (currentZoom > minZoom) {{
                currentZoom = Math.max(currentZoom - zoomStep, minZoom);
                updateZoom();
            }}
        }}
        
        function resetZoom() {{
            currentZoom = 1.0;
            updateZoom();
            // 스크롤 위치도 초기화
            const wrapper = document.getElementById('mermaid-wrapper');
            wrapper.scrollTop = 0;
            wrapper.scrollLeft = 0;
        }}
        
        // 드래그로 이동 (Pan) 기능
        let isDragging = false;
        let startX, startY;
        let scrollLeft, scrollTop;
        const wrapper = document.getElementById('mermaid-wrapper');
        const diagram = document.getElementById('mermaid-diagram');
        
        // 마우스 이벤트 (드래그)
        wrapper.addEventListener('mousedown', function(e) {{
            // 확대/축소 버튼이나 다른 요소 클릭 시 드래그 방지
            if (e.target.classList.contains('zoom-btn') || 
                e.target.closest('.zoom-controls') ||
                e.target.tagName === 'BUTTON') {{
                return;
            }}
            
            // SVG 내부의 텍스트나 요소 클릭도 허용
            const svgElement = e.target.closest('svg');
            if (svgElement) {{
                // 노드 클릭인지 확인 (노드의 text나 rect, path 등을 클릭한 경우)
                const isNodeClick = e.target.closest('g.node, g[class*="node"]') || 
                                   e.target.tagName === 'text' ||
                                   e.target.closest('g') !== null;
                
                // 노드 클릭이면 드래그 시작하지 않음
                if (isNodeClick) {{
                    // 잠시 대기하여 클릭 이벤트가 처리될 시간을 줌
                    setTimeout(function() {{
                        // 클릭 이벤트가 처리되지 않았다면 드래그 시작
                        if (!e.defaultPrevented) {{
                            isDragging = true;
                            wrapper.classList.add('dragging');
                            startX = e.pageX;
                            startY = e.pageY;
                            scrollLeft = wrapper.scrollLeft;
                            scrollTop = wrapper.scrollTop;
                        }}
                    }}, 100);
                    return;
                }}
                
                isDragging = true;
                wrapper.classList.add('dragging');
                startX = e.pageX;
                startY = e.pageY;
                scrollLeft = wrapper.scrollLeft;
                scrollTop = wrapper.scrollTop;
                e.preventDefault();
                e.stopPropagation();
            }}
        }});
        
        document.addEventListener('mousemove', function(e) {{
            if (!isDragging) return;
            e.preventDefault();
            e.stopPropagation();
            const x = e.pageX;
            const y = e.pageY;
            const walkX = (startX - x); // 반대 방향으로 이동
            const walkY = (startY - y);
            wrapper.scrollLeft = scrollLeft + walkX;
            wrapper.scrollTop = scrollTop + walkY;
        }});
        
        document.addEventListener('mouseup', function(e) {{
            if (isDragging) {{
                isDragging = false;
                wrapper.classList.remove('dragging');
            }}
        }});
        
        // 터치 이벤트 지원 (모바일)
        let touchStartX, touchStartY;
        let touchScrollLeft, touchScrollTop;
        
        wrapper.addEventListener('touchstart', function(e) {{
            if (e.target.classList.contains('zoom-btn') || 
                e.target.closest('.zoom-controls') ||
                e.target.tagName === 'BUTTON') {{
                return;
            }}
            
            if (e.target.closest('svg') || e.target.closest('.mermaid')) {{
                const touch = e.touches[0];
                touchStartX = touch.pageX;
                touchStartY = touch.pageY;
                touchScrollLeft = wrapper.scrollLeft;
                touchScrollTop = wrapper.scrollTop;
                wrapper.classList.add('dragging');
            }}
        }}, {{ passive: false }});
        
        wrapper.addEventListener('touchmove', function(e) {{
            if (!touchStartX || !touchStartY) return;
            const touch = e.touches[0];
            const walkX = touchStartX - touch.pageX;
            const walkY = touchStartY - touch.pageY;
            wrapper.scrollLeft = touchScrollLeft + walkX;
            wrapper.scrollTop = touchScrollTop + walkY;
            e.preventDefault();
        }}, {{ passive: false }});
        
        wrapper.addEventListener('touchend', function() {{
            touchStartX = null;
            touchStartY = null;
            wrapper.classList.remove('dragging');
        }}, {{ passive: true }});
        
        // 마우스 휠로 확대/축소 (Ctrl 키와 함께) 또는 스크롤
        wrapper.addEventListener('wheel', function(e) {{
            if (e.ctrlKey || e.metaKey) {{
                e.preventDefault();
                if (e.deltaY < 0) {{
                    zoomIn();
                }} else {{
                    zoomOut();
                }}
            }}
            // Ctrl 없이 휠을 돌리면 스크롤 (기본 동작)
        }}, {{ passive: false }});
        
        // 키보드 단축키
        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === '=') {{
                e.preventDefault();
                zoomIn();
            }} else if ((e.ctrlKey || e.metaKey) && e.key === '-') {{
                e.preventDefault();
                zoomOut();
            }} else if ((e.ctrlKey || e.metaKey) && e.key === '0') {{
                e.preventDefault();
                resetZoom();
            }}
        }});
    </script>
</body>
</html>
"""
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML 파일이 생성되었습니다: {output_path}")
        return True
    except Exception as e:
        print(f"❌ HTML 파일 생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    # 출력 경로 설정
    output_dir = BASE_DIR / "docs"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "system_architecture.html"
    
    # 기본 설정
    config = {}
    
    # Mermaid 다이어그램 코드 생성
    print("📝 Mermaid 다이어그램 코드 생성 중...")
    mermaid_code = generate_mermaid_diagram(config)
    
    # HTML 생성
    print("🔄 HTML 파일 생성 중...")
    if generate_html(mermaid_code, output_path):
        print(f"\n✨ 완료! 파일 위치: {output_path}")
        print(f"   브라우저에서 열기: file://{output_path.absolute()}")
    else:
        print("\n❌ HTML 생성 실패")

if __name__ == "__main__":
    main()
