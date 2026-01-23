# ui/components/ontology_studio/overview.py
# -*- coding: utf-8 -*-
"""
온톨로지 개요 대시보드
"""
import streamlit as st
import pandas as pd
from typing import Dict
from pathlib import Path
from datetime import datetime

def render_overview(orchestrator):
    """개요 대시보드 렌더링"""
    st.markdown("### 🏠 온톨로지 개요")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if not ontology_manager or not ontology_manager.graph:
        st.warning("⚠️ 온톨로지 그래프가 없습니다.")
        return
    
    graph = ontology_manager.graph
    ns = ontology_manager.ns
    
    # 1. 주요 지표 (KPI Cards)
    st.markdown("#### 📊 주요 지표")
    
    # 통계 계산
    total_triples = len(list(graph.triples((None, None, None))))
    
    # 관계 유형 수
    relation_types = set()
    for s, p, o in graph.triples((None, None, None)):
        if str(p).startswith(str(ns)) and str(p) != str(ns.type):
            relation_types.add(str(p).replace(str(ns), ""))
    
    # 품질 분석
    try:
        from ui.components.relationship_quality_validator import _analyze_relationship_quality
        quality_report = _analyze_relationship_quality(graph, ns, ontology_manager)
        avg_density = quality_report.get('avg_relationship_density', 0)
        anomaly_score = quality_report.get('anomaly_score', 0)
    except:
        avg_density = 0
        anomaly_score = 0
    
    # 최근 변경 건수
    try:
        from core_pipeline.ontology_history import OntologyHistory
        history_manager = OntologyHistory()
        recent_changes = len(history_manager.get_history(limit=7))
    except:
        recent_changes = 0
    
    # 온톨로지 파일 상태
    ontology_path = orchestrator.config.get("ontology_path", "./knowledge/ontology")
    instances_file = Path(ontology_path) / "instances.ttl"
    instances_reasoned_file = Path(ontology_path) / "instances_reasoned.ttl"
    schema_file = Path(ontology_path) / "schema.ttl"
    
    file_status = "활성"
    if instances_reasoned_file.exists():
        file_status = "활성 (추론 포함)"
    elif instances_file.exists():
        file_status = "활성"
    elif schema_file.exists():
        file_status = "스키마만"
    else:
        file_status = "없음"
    
    # KPI Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("총 Triples", f"{total_triples:,}", help="전체 RDF 트리플 수")
    with col2:
        st.metric("관계 유형", len(relation_types), help="고유한 관계 유형 수")
    with col3:
        st.metric("평균 관계 밀도", f"{avg_density:.2f}", help="관계 유형당 평균 관계 수")
    with col4:
        delta_color = "normal" if anomaly_score < 30 else "inverse"
        st.metric("이상 패턴 점수", f"{anomaly_score:.1f}%", 
                 delta="정상" if anomaly_score < 30 else "주의" if anomaly_score < 60 else "위험",
                 delta_color=delta_color,
                 help="Z-score 기반 이상 패턴 비율")
    with col5:
        st.metric("최근 변경", f"{recent_changes}건", help="최근 7일간 변경 건수")
    
    st.divider()
    
    # 2. 온톨로지 상태 요약
    st.markdown("#### 📊 온톨로지 상태")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("그래프 상태", "활성" if ontology_manager.graph else "비활성")
    with col2:
        st.metric("파일 상태", file_status)
    with col3:
        if instances_file.exists() or instances_reasoned_file.exists():
            file_path = instances_reasoned_file if instances_reasoned_file.exists() else instances_file
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            st.metric("마지막 업데이트", mtime.strftime("%Y-%m-%d %H:%M"))
        else:
            st.metric("마지막 업데이트", "없음")
    
    st.divider()
    
    # 3. 빠른 액션
    st.markdown("#### ⚡ 빠른 액션")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔄 배치 검증 실행", use_container_width=True):
            st.session_state.quick_action = "batch_validation"
            st.rerun()
    
    # 배치 검증 결과 표시
    if st.session_state.get('quick_action') == "batch_validation":
        st.divider()
        st.markdown("#### 🔄 배치 검증 결과")
        with st.spinner("배치 검증 실행 중..."):
            try:
                from core_pipeline.batch_validator import BatchValidator
                batch_validator = BatchValidator(ontology_manager)
                results = batch_validator.validate(
                    scope="전체 관계",
                    rules=["관계 유효성 (노드 존재 확인)", "순환 참조 탐지"]
                )
                
                st.session_state.batch_validation_results = results
                st.session_state.quick_action = None  # 초기화
                
                # 결과 요약 표시
                st.success(f"✅ 배치 검증 완료!")
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("전체", f"{results['total']:,}")
                with col_r2:
                    passed_pct = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
                    st.metric("통과", f"{results['passed']:,}", delta=f"{passed_pct:.1f}%")
                with col_r3:
                    failed_pct = (results['failed'] / results['total'] * 100) if results['total'] > 0 else 0
                    st.metric("실패", f"{results['failed']:,}", delta=f"-{failed_pct:.1f}%")
                with col_r4:
                    st.metric("주의", f"{results['warning']:,}")
                
                st.info("💡 상세 결과는 **품질 보증** 탭의 **배치 검증**에서 확인하세요.")
            except Exception as e:
                st.error(f"배치 검증 실행 실패: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state.quick_action = None
    
    with col2:
        if st.button("✅ 전체 재검증", use_container_width=True):
            st.session_state.quick_action = "full_validation"
            st.rerun()
    
    # 전체 재검증 결과 표시
    if st.session_state.get('quick_action') == "full_validation":
        st.divider()
        st.markdown("#### ✅ 전체 재검증 결과")
        with st.spinner("전체 검증 실행 중..."):
            try:
                # 스키마 검증
                from core_pipeline.ontology_validator import OntologyValidator
                validator = OntologyValidator(ontology_manager)
                schema_report = validator.validate_schema_compliance()
                
                # 관계 품질 검증
                from ui.components.relationship_quality_validator import _analyze_relationship_quality
                quality_report = _analyze_relationship_quality(graph, ns, ontology_manager)
                
                st.session_state.full_validation_results = {
                    "schema": schema_report,
                    "quality": quality_report
                }
                st.session_state.quick_action = None  # 초기화
                
                # 결과 요약 표시
                schema_score = schema_report.get('overall_score', 0)
                anomaly_score = quality_report.get('anomaly_score', 0)
                
                st.success("✅ 전체 검증 완료!")
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    delta_color = "normal" if schema_score >= 80 else "inverse"
                    st.metric("스키마 검증", f"{schema_score}%", 
                             delta="통과" if schema_score >= 80 else "미통과",
                             delta_color=delta_color)
                with col_r2:
                    delta_color = "normal" if anomaly_score < 30 else "inverse"
                    st.metric("이상 패턴", f"{anomaly_score:.1f}%",
                             delta="정상" if anomaly_score < 30 else "주의",
                             delta_color=delta_color)
                
                st.info("💡 상세 결과는 **품질 보증** 탭에서 확인하세요.")
            except Exception as e:
                st.error(f"전체 검증 실행 실패: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state.quick_action = None
    
    with col3:
        if st.button("📜 히스토리 보기", use_container_width=True):
            st.session_state.quick_action = "view_history"
            st.rerun()
    
    # 히스토리 결과 표시
    if st.session_state.get('quick_action') == "view_history":
        st.divider()
        st.markdown("#### 📜 최근 변경 이력")
        try:
            from core_pipeline.ontology_history import OntologyHistory
            history_manager = OntologyHistory()
            recent_history = history_manager.get_history(limit=10)
            
            st.session_state.quick_action = None  # 초기화
            
            if recent_history:
                st.success(f"✅ 최근 변경 이력 {len(recent_history)}건 조회 완료")
                
                # 최근 변경 이력 요약 표시
                history_summary = []
                for entry in recent_history[:10]:
                    timestamp = entry.get('timestamp', '')
                    if timestamp:
                        try:
                            timestamp_dt = datetime.fromisoformat(timestamp)
                            timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            timestamp_str = timestamp[:16] if len(timestamp) > 16 else timestamp
                    else:
                        timestamp_str = ''
                    
                    source = entry.get('source', '')
                    target = entry.get('target', '')
                    
                    history_summary.append({
                        "일시": timestamp_str,
                        "유형": entry.get('change_type', ''),
                        "소스": source[:30] + "..." if len(source) > 30 else source,
                        "관계": entry.get('relation', ''),
                        "타겟": target[:30] + "..." if len(target) > 30 else target
                    })
                
                if history_summary:
                    df_history = pd.DataFrame(history_summary)
                    st.dataframe(df_history, use_container_width=True, hide_index=True)
                
                st.info("💡 전체 이력은 **버전 관리** 탭에서 확인하세요.")
            else:
                st.info("등록된 변경 이력이 없습니다.")
        except Exception as e:
            st.error(f"히스토리 조회 실패: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.session_state.quick_action = None
    
    with col4:
        if st.button("📊 리포트 생성", use_container_width=True):
            st.session_state.quick_action = "generate_report"
            st.rerun()
    
    # 리포트 생성 결과 표시
    if st.session_state.get('quick_action') == "generate_report":
        st.divider()
        st.markdown("#### 📊 품질 리포트")
        with st.spinner("품질 리포트 생성 중..."):
            try:
                # 종합 품질 리포트 생성
                from core_pipeline.ontology_validator import OntologyValidator
                from ui.components.relationship_quality_validator import _analyze_relationship_quality
                
                validator = OntologyValidator(ontology_manager)
                schema_report = validator.validate_schema_compliance()
                quality_report = _analyze_relationship_quality(graph, ns, ontology_manager)
                
                # 리포트 데이터 구성
                report_data = {
                    "생성 일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "온톨로지 통계": {
                        "총 Triples": total_triples,
                        "관계 유형 수": len(relation_types),
                        "평균 관계 밀도": avg_density
                    },
                    "스키마 검증": {
                        "종합 점수": schema_report.get('overall_score', 0),
                        "Axis 객체화": schema_report.get('axis_compliance', {}).get('status', 'N/A'),
                        "연결성": schema_report.get('connectivity_health', {}).get('status', 'N/A')
                    },
                    "관계 품질": {
                        "이상 패턴 점수": anomaly_score,
                        "관계 유형 수": quality_report.get('relation_type_count', 0),
                        "평균 관계 밀도": avg_density
                    },
                    "파일 상태": file_status
                }
                
                st.session_state.quality_report_data = report_data
                st.session_state.quick_action = None  # 초기화
                
                st.success("✅ 품질 리포트 생성 완료!")
                
                # 리포트 요약 표시
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    st.metric("스키마 점수", f"{report_data['스키마 검증']['종합 점수']}%")
                with col_r2:
                    st.metric("이상 패턴", f"{report_data['관계 품질']['이상 패턴 점수']:.1f}%")
                with col_r3:
                    st.metric("관계 유형", f"{report_data['관계 품질']['관계 유형 수']}개")
                
                # 리포트 다운로드 (JSON)
                import json
                report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 리포트 다운로드 (JSON)",
                    data=report_json,
                    file_name=f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                
                st.info("💡 상세 리포트는 **품질 보증** 탭의 **품질 리포트**에서 확인하세요.")
            except Exception as e:
                st.error(f"리포트 생성 실패: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state.quick_action = None

