# ui/views/learning_guide.py
# -*- coding: utf-8 -*-
"""
학습 및 가이드 페이지
시스템 소개 문서 및 학습 자료 제공
"""
import streamlit as st
import streamlit.components.v1 as components
import sys
from pathlib import Path
import re
import webbrowser
import os

# 경로 설정
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# 페이지 설정
st.set_page_config(
    page_title="시스템 소개",
    page_icon="📖",
    layout="wide"
)

def get_docs_directory():
    """docs 디렉토리 경로 반환"""
    return BASE_DIR / "docs"

def categorize_document(file_path):
    """문서를 디렉토리 구조 기반으로 분류"""
    file_path_str = str(file_path)
    docs_dir = get_docs_directory()
    
    # 상대 경로 계산
    try:
        relative_path = file_path.relative_to(docs_dir)
        parts = relative_path.parts
        
        # 루트 레벨 파일
        if len(parts) == 1:
            # HTML 파일 및 특정 MD 파일은 주요 업무 Flow로 분류
            if file_path.suffix.lower() == '.html' or file_path.name == 'coa_recommendation_process.md':
                return "⚡ 주요 업무 Flow"
            return "📄 주요 문서"
        
        # 첫 번째 디렉토리로 분류
        first_dir = parts[0]
        
        # 디렉토리별 카테고리 매핑
        if first_dir == "00_Management":
            return "📋 Management"
        elif first_dir == "10_Architecture":
            return "🏗️ Architecture"
        elif first_dir == "20_Components":
            # 컴포넌트는 서브레이어까지 표시
            if len(parts) > 1:
                sub_layer = parts[1]
                layer_map = {
                    "agent_layer": "🤖 Agent Layer",
                    "command_layer": "👤 Command Layer",
                    "data_layer": "🏗️ Data Layer",
                    "orchestration_layer": "⚙️ Orchestration Layer"
                }
                layer_name = layer_map.get(sub_layer, sub_layer)
                return f"🔧 Components > {layer_name}"
            return "🔧 Components"
        elif first_dir == "30_Guides":
            return "📚 Guides"
        elif first_dir == "99_Archive":
            return "📦 Archive"
        else:
            return "📋 기타"
            
    except ValueError:
        # docs 디렉토리 외부 파일
        return "📋 기타"

def get_document_files():
    """docs 폴더의 모든 MD 및 HTML 파일 목록을 유형별로 분류하여 반환"""
    docs_dir = get_docs_directory()
    if not docs_dir.exists():
        return {}
    
    # MD 파일과 HTML 파일만 필터링 (재귀적으로 components 폴더 포함)
    files = []
    for file_path in docs_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.md', '.html']:
            # README.md는 제외 (인덱스용)
            if file_path.name.lower() != 'readme.md':
                files.append(file_path)
    
    # 파일명으로 정렬
    files.sort(key=lambda x: x.name)
    
    # 유형별로 분류
    categorized = {}
    for file_path in files:
        category = categorize_document(file_path)
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(file_path)
    
    return categorized

def get_document_title(file_name):
    """파일명을 읽기 쉬운 제목으로 변환"""
    # 확장자 제거
    title = file_name.replace('.md', '').replace('.html', '')
    # 언더스코어를 공백으로
    title = title.replace('_', ' ')
    # 한글과 영문 사이 공백 추가 (간단한 버전)
    title = re.sub(r'([가-힣])([A-Za-z])', r'\1 \2', title)
    title = re.sub(r'([A-Za-z])([가-힣])', r'\1 \2', title)
    return title

def render_document_item(file_path, category):
    """문서 항목 렌더링"""
    file_name = file_path.name
    file_type = file_path.suffix.lower()
    title = get_document_title(file_name)
    
    # 세션 상태에 선택된 문서 저장
    doc_key = f"selected_doc_{file_name}"
    
    col1, col2, col3 = st.columns([4, 1, 1])
    
    with col1:
        if file_type == '.html':
            icon = "🌐"
        else:
            icon = "📄"
        st.markdown(f"**{icon} {title}**")
    
    with col2:
        if file_type == '.html':
            # ✅ 개선: iframe으로 HTML 임베드 (네트워크 접근 가능)
            if st.button("📖 여기서 보기", key=f"embed_{file_name}", width="stretch"):
                st.session_state[doc_key] = True
                st.rerun()
        else:
            if st.button("📖 열기", key=f"open_{file_name}", width="stretch"):
                st.session_state[doc_key] = True
                st.rerun()
    
    with col3:
        st.caption(f"`{file_name}`")
    
    # HTML 파일 내용 임베드 표시 (선택된 경우)
    if file_type == '.html' and st.session_state.get(doc_key, False):
        st.markdown("---")
        
        # 상단: 제목과 닫기 버튼
        col_title, col_close_top = st.columns([4, 1])
        with col_title:
            st.markdown(f"### 🌐 {title}")
        with col_close_top:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("❌ 닫기", key=f"close_top_html_{file_name}", width="stretch"):
                st.session_state[doc_key] = False
                st.rerun()
        
        st.markdown("---")
        
        # HTML 파일 읽기 및 임베드
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Streamlit components로 HTML 렌더링
            # 높이를 크게 설정하여 최대한 많은 내용을 한 번에 볼 수 있도록 함
            # 다이어그램 확대/축소, 드래그 이동 등 모든 기능 정상 작동
            components.html(html_content, height=1400, scrolling=True)
            
            st.info("💡 **사용 방법**: 다이어그램 내부의 +/- 버튼으로 확대/축소, 드래그하여 이동할 수 있습니다.")
            
        except Exception as e:
            st.error(f"HTML 파일을 읽는 중 오류 발생: {e}")
            st.session_state[doc_key] = False
        
        st.markdown("---")
        
        # 하단: 닫기 버튼
        col_spacer, col_close_bottom = st.columns([4, 1])
        with col_spacer:
            st.empty()
        with col_close_bottom:
            if st.button("❌ 닫기", key=f"close_bottom_html_{file_name}", width="stretch"):
                st.session_state[doc_key] = False
                st.rerun()
        
        st.markdown("---")
    
    # MD 파일 내용 표시 (선택된 경우)
    if file_type == '.md' and st.session_state.get(doc_key, False):
        st.markdown("---")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 상단: 제목과 닫기 버튼
            col_title, col_close_top = st.columns([4, 1])
            with col_title:
                st.markdown(f"### 📄 {title}")
            with col_close_top:
                st.markdown("<br>", unsafe_allow_html=True)  # 수직 정렬을 위한 공백
                if st.button("❌ 닫기", key=f"close_top_{file_name}", width="stretch"):
                    st.session_state[doc_key] = False
                    st.rerun()
            
            st.markdown("---")
            
            # 내용 표시
            st.markdown(content)
            
            st.markdown("---")
            
            # 하단: 닫기 버튼
            col_spacer, col_close_bottom = st.columns([4, 1])
            with col_spacer:
                st.empty()
            with col_close_bottom:
                if st.button("❌ 닫기", key=f"close_bottom_{file_name}", width="stretch"):
                    st.session_state[doc_key] = False
                    st.rerun()
            
        except Exception as e:
            st.error(f"파일을 읽는 중 오류 발생: {e}")
            st.session_state[doc_key] = False
        st.markdown("---")

def render_directory_section(category, files, description=None, expanded=True):
    """디렉토리 기반 섹션 렌더링"""
    if not files:
        return
    
    # 컴포넌트 섹션인 경우 서브레이어별로 그룹화
    if category == "🔧 Components":
        st.markdown(f"### {category}")
        if description:
            st.markdown(description)
        st.markdown("---")
        
        # 서브레이어별로 그룹화
        layer_groups = {}
        for file_path in files:
            file_category = categorize_document(file_path)
            if file_category not in layer_groups:
                layer_groups[file_category] = []
            layer_groups[file_category].append(file_path)
        
        # 서브레이어별로 표시
        for layer_category in sorted(layer_groups.keys()):
            layer_files = layer_groups[layer_category]
            layer_name = layer_category.split(" > ")[-1] if " > " in layer_category else layer_category
            with st.expander(f"{layer_name} ({len(layer_files)}개)", expanded=False):
                for file_path in sorted(layer_files, key=lambda x: x.name):
                    render_document_item(file_path, layer_category)
                    st.markdown("---")
    else:
        # 일반 섹션
        st.markdown(f"### {category}")
        if description:
            st.markdown(description)
        st.markdown("---")
        
        with st.expander(f"문서 목록 ({len(files)}개)", expanded=expanded):
            for file_path in sorted(files, key=lambda x: x.name):
                render_document_item(file_path, category)
                st.markdown("---")

def main():
    """메인 함수"""
    # 제목 (Compact Style Upgrade)
    # 상단 여백 최소화 및 컴팩트 헤더 스타일 적용
    st.markdown("""
    <style>
        /* 상단 여백 최소화 */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            margin-top: 0rem !important;
        }
        /* Plan B: 헤더 전체를 숨기지 않고 투명화하여 버튼 기능 복구 */
        header[data-testid="stHeader"] {
            background: transparent !important;
            border-bottom: none !important;  /* Streamlit 기본 구분선 제거 */
        }
        
        /* 데코레이션(줄무늬) 숨김 */
        [data-testid="stDecoration"] {
            display: none;
        }

        /* 사이드바 토글 버튼 강제 노출 */
        [data-testid="stSidebarCollapsedControl"] {
            display: block !important;
            color: #e6edf3 !important;
        }
        
        /* 컴팩트 헤더 스타일 */
        .compact-header {
            background-color: #0e1117;
            border-bottom: 1px solid #30363d;
            padding-bottom: 5px;
            margin-bottom: 15px;
            display: flex;
            flex-wrap: wrap;  /* 작은 화면에서 줄바꿈 허용 */
            width: 100%;  /* 브라우저 너비에 맞춤 */
            justify-content: space-between;
            align-items: center;
        }
        .header-title {
            font-family: 'Roboto Mono', monospace; 
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            color: #2E9AFE; /* Distinct Blue Color */
            text-transform: uppercase;
        }
        .header-subtitle {
            font-family: 'Roboto', sans-serif;
            font-size: 0.85rem;
            color: #8b949e;
        }
    </style>

    <div class="compact-header">
        <div class="header-title">
            📖 시스템 소개
        </div>
        <div class="header-subtitle">
            시스템 소개 문서 및 학습 자료 제공
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    이 페이지에서는 Intelligent Operation Agent Platform에 대한 다양한 문서를 제공합니다.
    각 문서를 클릭하여 내용을 확인하세요.
    """)
    
    # 문서 파일 목록 가져오기 (유형별로 분류)
    categorized_docs = get_document_files()
    
    if not categorized_docs:
        st.warning("⚠️ docs 폴더에 문서 파일을 찾을 수 없습니다.")
        return
    
    # 카테고리 표시 순서 정의 (디렉토리 번호 순서)
    category_order = [
        "⚡ 주요 업무 Flow",
        "📋 Management",
        "🏗️ Architecture", 
        "🔧 Components",
        "📚 Guides",
        "📄 주요 문서",
        "📦 Archive"
    ]
    
    # 카테고리별 설명
    category_descriptions = {
        "⚡ 주요 업무 Flow": "시스템의 주요 업무 흐름도 및 프로세스 정의",
        "📋 Management": "시스템 로드맵 및 운영 매뉴얼",
        "🏗️ Architecture": "시스템 아키텍처, 온톨로지 설계, 점수 산정 시스템",
        "🔧 Components": "시스템 컴포넌트 상세 설명 (레이어별)",
        "📚 Guides": "사용자 가이드 및 설치 가이드",
        "📄 주요 문서": "주요 프로세스 및 시스템 문서",
        "📦 Archive": "아카이브된 문서"
    }
    
    # 전체 문서 개수 계산
    total_count = sum(len(files) for files in categorized_docs.values())
    st.markdown(f"### 📚 전체 문서 ({total_count}개)")
    st.markdown("---")
    
    # 순서대로 섹션 표시
    for category in category_order:
        if category in categorized_docs:
            files = categorized_docs[category]
            # Components와 Archive는 기본적으로 접힌 상태, 나머지는 펼쳐진 상태
            expanded = category not in ["🔧 Components", "📦 Archive"]
            render_directory_section(
                category, 
                files, 
                description=category_descriptions.get(category),
                expanded=expanded
            )
    
    # 정의되지 않은 카테고리가 있다면 마지막에 표시
    for category, files in sorted(categorized_docs.items()):
        if category not in category_order:
            render_directory_section(category, files, expanded=False)
    
    # 하단 안내
    st.info("""
    💡 **안내**: 
    - **HTML 파일**: "📖 여기서 보기" 버튼을 클릭하면 페이지 내에서 HTML 문서를 확인할 수 있습니다 (네트워크 접근 지원).
    - **Markdown 파일**: "📖 열기" 버튼을 클릭하면 페이지 내에서 내용을 확인할 수 있습니다.
    - 문서를 닫으려면 각 문서 하단의 "❌ 닫기" 버튼을 클릭하세요.
    - **문서 구조**: docs 폴더의 디렉토리 구조에 따라 자동으로 분류됩니다.
    - **HTML 다이어그램**: 임베드된 HTML 내부의 +/- 버튼으로 확대/축소, 드래그하여 이동할 수 있습니다.
    """)

if __name__ == "__main__":
    main()
