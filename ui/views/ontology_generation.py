# ui/views/ontology_generation.py
# -*- coding: utf-8 -*-
"""
온톨로지 생성 페이지
데이터로부터 RDF 그래프 생성
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "common"))

from ui.components.graph_viewer import render_graph
from ui.components.pipeline_status import render_pipeline_status
from ui.components.node_info_panel import render_node_info_panel
from ui.components.ontology_manager_panel import render_ontology_manager_panel
from core_pipeline.orchestrator import Orchestrator
import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


st.set_page_config(
    page_title="온톨로지 생성",
    layout="wide"
)

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
        background-color: #0e1117 !important;
        border-bottom: 1px solid #30363d !important;
        padding-bottom: 5px !important;
        margin-bottom: 8px !important;  /* 본문과의 간격 축소 */
        display: flex !important;
        flex-wrap: wrap;  /* 작은 화면에서 줄바꿈 허용 */
        width: 100%;  /* 브라우저 너비에 맞춤 */
        justify-content: space-between !important;
        align-items: center !important;
    }
    .header-title {
        display: block !important;
        visibility: visible !important;
        font-family: 'Roboto Mono', monospace !important; 
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        color: #2E9AFE !important; /* Distinct Blue Color */
        text-transform: uppercase !important;
    }
    .header-subtitle {
        display: block !important;
        visibility: visible !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.85rem !important;
        color: #8b949e !important;
    }
</style>

<div class="compact-header">
    <div class="header-title">
        온톨로지 생성
    </div>
    <div class="header-subtitle">
        데이터로부터 RDF 그래프 생성 및 시각화
    </div>
</div>
""", unsafe_allow_html=True)


# CSS 로드
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    pass  # load_css("ui/style.css") - 주석 처리: 커스텀 헤더와 충돌 방지
except FileNotFoundError:
    pass  # st.warning("ui/style.css 파일을 찾을 수 없습니다.")



# 설정 파일 로드
try:
    config = load_yaml("./config/global.yaml")
except Exception as e:
    st.error(f"설정 파일 로드 실패: {e}")
    st.stop()

# Orchestrator 초기화 (Enhanced Ontology Manager 사용)
# 이미 초기화 완료 플래그가 있으면 초기화 로직 건너뛰기
if st.session_state.get("main_orchestrator_initialized", False):
    # 이미 초기화 완료 - 아무 작업도 하지 않음
    pass
elif "main_orchestrator" not in st.session_state:
    # Orchestrator가 없으면 새로 생성 및 초기화
    with st.spinner("시스템 초기화 중..."):
        try:
            st.session_state.main_orchestrator = Orchestrator(config, use_enhanced_ontology=True)
            st.session_state.main_orchestrator.initialize()
            st.session_state.main_orchestrator_initialized = True
            st.success("[OK] 시스템 초기화 완료 (Enhanced Ontology Manager 활성화)")
        except Exception as e:
            st.error(f"시스템 초기화 실패: {e}")
            st.stop()
else:
    # Orchestrator는 있지만 초기화 플래그가 없는 경우
    # 실제 초기화 상태 확인 (중복 초기화 방지)
    if hasattr(st.session_state.main_orchestrator, 'core') and \
       hasattr(st.session_state.main_orchestrator.core, '_initialized') and \
       st.session_state.main_orchestrator.core._initialized:
        # 이미 초기화되었으면 플래그만 업데이트 (spinner 없이)
        st.session_state.main_orchestrator_initialized = True
    else:
        # 실제로 초기화가 필요한 경우에만 spinner 표시
        with st.spinner("시스템 초기화 중..."):
            try:
                st.session_state.main_orchestrator.initialize()
                st.session_state.main_orchestrator_initialized = True
            except Exception as e:
                st.error(f"시스템 초기화 실패: {e}")
                st.stop()

orchestrator = st.session_state.main_orchestrator

# [auto-load] 온톨로지 자동 로드 확인
# Orchestrator가 초기화되었더라도, 페이지 진입 시 그래프가 비어있고 디스크에 파일이 있다면 로드 시도
# (사용자가 그래프를 갱신했지만 세션이 유지되는 경우 대응)
if hasattr(orchestrator.core, 'enhanced_ontology_manager'):
    eom = orchestrator.core.enhanced_ontology_manager
    
    # 그래프가 비어있는 경우에만 로드 시도
    if eom.graph is None or len(eom.graph) == 0:
        # 이미 로드 시도했는지 세션 플래그 확인
        if not st.session_state.get('auto_load_attempted', False):
            with st.spinner("기존 온톨로지 자동 로드 중..."):
                eom.try_load_existing_graph()
                # core.ontology_manager와 동기화
                if eom.graph and len(eom.graph) > 0:
                    orchestrator.core.ontology_manager.graph = eom.graph
                    # [UI] 레이아웃 시프트를 방지하기 위해 success 대신 toast 사용
                    st.toast(f"✅ 기존 온톨로지 자동 로드 완료 ({len(eom.graph)} triples)", icon="✅")
                    
                st.session_state.auto_load_attempted = True

# 파이프라인 상태 (다이어그램 제외)
# render_pipeline_status(config, show_diagram=False)  # 다이어그램은 데이터관리 페이지에만 표시

# st.divider()  # 제거: 헤더 아래 불필요한 구분선

# 온톨로지 생성 및 시각화
st.header("온톨로지 그래프 생성")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("그래프 생성")
    
    # EnhancedOntologyManager는 이제 기본으로 사용되므로 체크박스 제거
    # 가상 엔티티 활성화 옵션만 제공
    enable_virtual_entities = st.checkbox("가상 엔티티 생성 활성화", value=True, 
                                          help="추론된 관계를 위한 가상 엔티티를 생성합니다 (예: 전략유형 기반 임무정보 추론)")
    
    enable_reasoned_graph = st.checkbox("추론 그래프 생성 (instances_reasoned.ttl)", value=False,
                                        help="의미 기반 추론을 수행하여 instances_reasoned.ttl 파일을 생성합니다. 시간이 오래 걸릴 수 있습니다.")
    
    if st.button("그래프 생성", type="primary"):
        with st.spinner("그래프 생성 중..."):
            try:
                data = orchestrator.core.data_manager.load_all()
                
                # EnhancedOntologyManager 사용 (항상 활성화)
                enhanced_om = orchestrator.core.enhanced_ontology_manager
                if not enhanced_om:
                    enhanced_om = orchestrator.core.ontology_manager
                
                # 디버깅: 실제 객체 타입 확인
                print(f"[DEBUG] enhanced_om type: {type(enhanced_om)}")
                print(f"[DEBUG] enhanced_om has save_graph: {hasattr(enhanced_om, 'save_graph')}")
                if hasattr(enhanced_om, 'save_graph'):
                    import inspect
                    sig = inspect.signature(enhanced_om.save_graph)
                    print(f"[DEBUG] save_graph signature: {sig}")
                
                # 기존 그래프 초기화 (새로 생성하기 위해)
                from rdflib import Graph
                if enhanced_om.graph is not None:
                    enhanced_om.graph = Graph()
                if orchestrator.core.ontology_manager.graph is not None:
                    orchestrator.core.ontology_manager.graph = Graph()
                print("[INFO] 그래프 초기화 완료")
                
                # OWL 온톨로지 생성 (스키마)
                graph = enhanced_om.generate_owl_ontology(data)
                if graph:
                    # 인스턴스 생성 (가상 엔티티 옵션 적용)
                    graph = enhanced_om.generate_instances(data, enable_virtual_entities=enable_virtual_entities)
                    
                    # core.ontology_manager.graph 동기화
                    if graph is not None:
                        orchestrator.core.ontology_manager.graph = enhanced_om.graph
                        
                        # TTL 파일로 저장 (2단계 또는 3단계 구조)
                        # save_graph 메서드가 새 파라미터를 지원하는지 확인
                        try:
                            save_success = enhanced_om.save_graph(
                                save_schema_separately=True,
                                save_instances_separately=True,
                                save_reasoned_separately=enable_reasoned_graph,
                                enable_semantic_inference=True,
                                cleanup_old_files=True,
                                backup_old_files=True
                            )
                        except TypeError as e:
                            # 이전 버전 호환성: 파라미터 없이 호출
                            print(f"[WARN] 새 파라미터를 지원하지 않습니다. 기본 파라미터로 호출: {e}")
                            save_success = enhanced_om.save_graph()
                        
                        # [FIX] 추론 활성화 시 save_graph 내부에서 그래프 객체가 변경될 수 있으므로 다시 동기화
                        if enable_reasoned_graph:
                            orchestrator.core.ontology_manager.graph = enhanced_om.graph
                            print(f"[DEBUG] 그래프 재동기화 완료: {len(enhanced_om.graph)} triples")
                        
                        # [FIX] 메시지에 표시할 트리플 수를 최신 그래프(enhanced_om.graph) 기준으로 계산
                        # graph 변수는 generate_instances의 반환값(추론 전)일 수 있음
                        current_graph = enhanced_om.graph
                        triples_count = len(list(current_graph.triples((None, None, None))))
                        
                        if save_success:
                            st.success(f"[OK] OWL 온톨로지 생성 및 저장 완료: {triples_count} triples")
                        else:
                            st.warning(f"[WARN] 그래프 생성 완료 ({triples_count} triples)하지만 파일 저장 실패")
                    else:
                        st.error("그래프 생성 실패: generate_instances가 None을 반환했습니다.")
                    st.rerun()
                else:
                    st.error("그래프 생성 실패: generate_owl_ontology가 None을 반환했습니다.")
            except Exception as e:
                st.error(f"그래프 생성 실패: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # 그래프 재로드 버튼 (정리 후 업데이트된 그래프를 보기 위해)
    if st.button("🔄 그래프 재로드", help="정리된 그래프를 메모리에 다시 로드합니다"):
        try:
            # 그래프 초기화 후 재로드
            from rdflib import Graph
            orchestrator.core.ontology_manager.graph = None
            orchestrator.core.enhanced_ontology_manager.graph = None
            loaded_graph = orchestrator.core.ontology_manager.load_graph()
            if loaded_graph:
                if orchestrator.core.enhanced_ontology_manager:
                    orchestrator.core.enhanced_ontology_manager.graph = loaded_graph
                st.success("✅ 그래프 재로드 완료")
                st.rerun()
            else:
                st.warning("그래프 로드 실패")
        except Exception as e:
            st.error(f"그래프 재로드 실패: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # 그래프 상태 및 상세 통계
    if orchestrator.core.ontology_manager.graph is not None:
        try:
            graph_data = orchestrator.core.ontology_manager.to_json()
            stats = graph_data.get("stats", {})
            
            # 기본 통계는 항상 표시 (총 Triples만 표시, 나머지는 그래프 시각화 영역에서 표시)
            if stats and stats.get("total_triples"):
                st.metric("총 Triples", stats.get("total_triples", 0))
            else:
                triples_count = len(list(orchestrator.core.ontology_manager.graph.triples((None, None, None))))
                st.metric("총 Triples", triples_count)
            
            # 상세 통계 (접을 수 있는 섹션, 기본 접힘) - 항상 표시
            with st.expander("📊 상세 통계 보기", expanded=False):
                if stats and stats.get("triples_by_category"):
                    triples_by_cat = stats.get("triples_by_category", {})
                    node_breakdown = stats.get("node_breakdown", {})
                    viz = stats.get("visualization", {})
                    
                    # 핵심 통계 요약 표
                    summary_data = []
                    summary_data.append({
                        "항목": "총 Triples",
                        "값": f"{stats.get('total_triples', 0):,}개"
                    })
                    summary_data.append({
                        "항목": "인스턴스 타입 (rdf:type)",
                        "값": f"{triples_by_cat.get('instance_type', 0):,}개"
                    })
                    summary_data.append({
                        "항목": "관계 (엣지)",
                        "값": f"{triples_by_cat.get('relationships', 0):,}개"
                    })
                    summary_data.append({
                        "항목": "라벨 (rdfs:label)",
                        "값": f"{triples_by_cat.get('labels', 0):,}개"
                    })
                    summary_data.append({
                        "항목": "Literal 값",
                        "값": f"{triples_by_cat.get('literals', 0):,}개"
                    })
                    summary_data.append({
                        "항목": "스키마 정보 (OWL)",
                        "값": f"{triples_by_cat.get('schema', 0):,}개"
                    })
                    
                    if node_breakdown:
                        summary_data.append({
                            "항목": "실제 데이터 노드",
                            "값": f"{node_breakdown.get('actual_data_nodes', 0):,}개"
                        })
                        if node_breakdown.get('virtual_entities', 0) > 0:
                            summary_data.append({
                                "항목": "가상 엔티티",
                                "값": f"{node_breakdown.get('virtual_entities', 0):,}개 ({node_breakdown.get('virtual_to_actual_ratio', 0):.2f}%)"
                            })
                    
                    if summary_data:
                        st.dataframe(pd.DataFrame(summary_data), width="stretch", hide_index=True)
                    
                    # 추가 상세 정보 (접을 수 있는 서브 섹션)
                    with st.expander("📈 변환 비율 및 기타 정보", expanded=False):
                        node_ratio = viz.get("node_to_triple_ratio", 0)
                        edge_ratio = viz.get("edge_to_triple_ratio", 0)
                        st.write(f"- **노드 변환율**: {node_ratio:.1f}% ({viz.get('nodes', 0)}개 / {stats.get('total_triples', 0)}개)")
                        st.write(f"- **엣지 변환율**: {edge_ratio:.1f}% ({viz.get('edges', 0)}개 / {stats.get('total_triples', 0)}개)")
                        
                        excluded = stats.get("excluded", {})
                        if excluded:
                            st.markdown("**제외된 항목 (시각화에 표시 안 됨):**")
                            st.write(f"- rdf:type: {excluded.get('rdf_type_triples', 0)}개")
                            st.write(f"- rdfs:label: {excluded.get('rdfs_label_triples', 0)}개")
                            st.write(f"- Literal 값: {excluded.get('literal_triples', 0)}개")
                    
                    # 그룹별 상세 정보
                    group_details = stats.get("group_details", {})
                    if group_details:
                        with st.expander("📋 그룹별 상세 정보", expanded=False):
                            group_data = []
                            for group, info in sorted(group_details.items()):
                                group_data.append({
                                    "그룹": group,
                                    "노드 수": info.get("count", 0),
                                    "평균 연결도": f"{info.get('avg_degree', 0):.1f}"
                                })
                            if group_data:
                                st.dataframe(pd.DataFrame(group_data), width="stretch", hide_index=True)
                    
                    st.info("💡 **참고**: RDF/온톨로지에서 각 데이터 행은 하나의 노드(리소스)로 표현됩니다.")
                else:
                    st.info("상세 통계 정보를 가져올 수 없습니다. 그래프를 다시 생성해보세요.")
                    st.caption("💡 그래프 생성 후 상세 통계가 자동으로 계산됩니다.")
        except Exception as e:
            # 오류 발생 시 기본 정보만 표시
            triples_count = len(list(orchestrator.core.ontology_manager.graph.triples((None, None, None))))
            st.metric("총 Triples", triples_count)
            st.warning(f"상세 통계 로드 실패: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.warning("[WARN] 그래프가 생성되지 않았습니다.")

with col2:
    st.subheader("그래프 시각화")
    
    # 노드 클릭 콜백 함수
    def on_node_click_callback(node_id: str, node_label: str, node_data: dict):
        """노드 클릭 시 호출되는 콜백"""
        st.session_state.selected_node_info = {
            "id": node_id,
            "label": node_label,
            "data": node_data
        }
    
    # 그래프 시각화 (분석 패널 활성화, 노드 클릭 콜백 추가)
    render_graph(orchestrator.core, 
                 on_node_click=on_node_click_callback,
                 show_analysis=True)
    
    # 선택된 노드 정보 표시 (접을 수 있게)
    if "selected_node_info" in st.session_state and st.session_state.selected_node_info:
        st.divider()
        node_info = st.session_state.selected_node_info
        with st.expander("📋 선택된 노드 정보", expanded=False):
            render_node_info_panel(
                orchestrator.core,
                node_info.get("id", ""),
                node_info.get("label", "")
            )

st.divider()

# 온톨로지 관계 관리
if orchestrator.core.ontology_manager.graph is not None:
    # 모듈 강제 리로드 로직 제거 (개발용 코드)
    render_ontology_manager_panel(orchestrator.core)
else:
    st.info("그래프를 먼저 생성해주세요.")

st.divider()
