# ui/components/ontology_studio/schema_manager.py
# -*- coding: utf-8 -*-
"""
스키마 관리 컴포넌트
온톨로지 스키마(T-Box) 정의 및 관리
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List
from rdflib import RDF, RDFS, OWL

def render_schema_manager(orchestrator):
    """스키마 관리 렌더링"""
    st.markdown("### 📐 스키마 관리 (Schema Management)")
    st.info("💡 온톨로지 스키마(T-Box)를 정의하고 관리합니다.")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if not ontology_manager or not ontology_manager.graph:
        st.warning("⚠️ 온톨로지 그래프가 없습니다.")
        return
    
    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "클래스 정의",
        "속성 정의",
        "관계 정의",
        "스키마 검증"
    ])
    
    with sub_tab1:
        _render_class_definition(orchestrator)
    
    with sub_tab2:
        _render_property_definition(orchestrator)
    
    with sub_tab3:
        _render_relation_definition(orchestrator)
    
    with sub_tab4:
        _render_schema_validation(orchestrator)

def _render_class_definition(orchestrator):
    """클래스 정의 - 개선된 버전"""
    st.markdown("#### 📋 클래스 정의")
    st.info("💡 온톨로지의 클래스(Class)를 정의하고 관리합니다.")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    graph = ontology_manager.graph
    ns = ontology_manager.ns
    
    # 클래스 추출 (OWL.Class 포함)
    classes = []
    class_details = {}
    
    # OWL.Class 추출
    for s, p, o in graph.triples((None, RDF.type, OWL.Class)):
        class_name = str(s).replace(str(ns), "")
        if class_name and class_name not in class_details:
            # 인스턴스 개수 확인
            instance_count = len(list(graph.triples((None, RDF.type, s))))
            classes.append(class_name)
            class_details[class_name] = {
                "name": class_name,
                "uri": str(s),
                "instance_count": instance_count,
                "type": "OWL.Class"
            }
    
    # RDFS.Class도 확인 (하위 호환성)
    for s, p, o in graph.triples((None, RDF.type, RDFS.Class)):
        class_name = str(s).replace(str(ns), "")
        if class_name and class_name not in class_details:
            instance_count = len(list(graph.triples((None, RDF.type, s))))
            classes.append(class_name)
            class_details[class_name] = {
                "name": class_name,
                "uri": str(s),
                "instance_count": instance_count,
                "type": "RDFS.Class"
            }
    
    # Table, Column 등 레거시 클래스도 확인
    if hasattr(ns, 'Table'):
        for s, p, o in graph.triples((None, RDF.type, ns.Table)):
            class_name = str(s).replace(str(ns), "")
            if class_name and class_name not in class_details:
                instance_count = len(list(graph.triples((None, RDF.type, s))))
                classes.append(class_name)
                class_details[class_name] = {
                    "name": class_name,
                    "uri": str(s),
                    "instance_count": instance_count,
                    "type": "Legacy.Table"
                }
    
    if classes:
        st.success(f"✅ 등록된 클래스: **{len(classes)}개**")
        
        # 검색 및 필터링
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 클래스 검색", placeholder="클래스명으로 검색...", key="class_search")
        with col2:
            min_instances = st.number_input("최소 인스턴스 수", min_value=0, value=0, step=1, key="min_instances")
        
        # 필터링
        filtered_classes = []
        for cls_name in sorted(classes):
            if search_term and search_term.lower() not in cls_name.lower():
                continue
            if class_details[cls_name]["instance_count"] < min_instances:
                continue
            filtered_classes.append(cls_name)
        
        if filtered_classes:
            # 테이블 형식으로 표시
            class_data = []
            for cls_name in filtered_classes:
                details = class_details[cls_name]
                class_data.append({
                    "클래스명": cls_name,
                    "인스턴스 수": details["instance_count"],
                    "타입": details["type"]
                })
            
            df = pd.DataFrame(class_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 통계 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 클래스 수", len(classes))
            with col2:
                total_instances = sum(d["instance_count"] for d in class_details.values())
                st.metric("총 인스턴스 수", f"{total_instances:,}")
            with col3:
                avg_instances = total_instances / len(classes) if classes else 0
                st.metric("평균 인스턴스 수", f"{avg_instances:.1f}")
        else:
            st.info("검색 조건에 맞는 클래스가 없습니다.")
    else:
        st.warning("⚠️ 등록된 클래스가 없습니다.")
        st.info("💡 클래스는 온톨로지 생성 과정에서 자동으로 생성됩니다. 온톨로지 생성 페이지에서 온톨로지를 생성해주세요.")

def _render_property_definition(orchestrator):
    """속성 정의 - 개선된 버전"""
    st.markdown("#### 🔧 속성 정의")
    st.info("💡 온톨로지의 속성(Property)을 정의하고 관리합니다.")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    graph = ontology_manager.graph
    ns = ontology_manager.ns
    
    # 속성 추출 및 통계 수집
    properties = set()
    property_stats = defaultdict(int)
    property_details = {}
    
    for s, p, o in graph.triples((None, None, None)):
        if str(p).startswith(str(ns)) and str(p) != str(ns.type):
            prop_name = str(p).replace(str(ns), "")
            properties.add(prop_name)
            property_stats[prop_name] += 1
            
            if prop_name not in property_details:
                property_details[prop_name] = {
                    "name": prop_name,
                    "uri": str(p),
                    "usage_count": 0,
                    "domain_classes": set(),
                    "range_types": set()
                }
            property_details[prop_name]["usage_count"] = property_stats[prop_name]
    
    if properties:
        st.success(f"✅ 등록된 속성: **{len(properties)}개**")
        
        # 검색 및 필터링
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input("🔍 속성 검색", placeholder="속성명으로 검색...", key="prop_search")
        with col2:
            min_usage = st.number_input("최소 사용 횟수", min_value=0, value=0, step=1, key="min_usage")
        with col3:
            sort_by = st.selectbox("정렬 기준", ["이름", "사용 횟수"], index=0, key="prop_sort")
        
        # 필터링 및 정렬
        filtered_props = []
        for prop_name in properties:
            if search_term and search_term.lower() not in prop_name.lower():
                continue
            if property_details[prop_name]["usage_count"] < min_usage:
                continue
            filtered_props.append(prop_name)
        
        # 정렬
        if sort_by == "사용 횟수":
            filtered_props.sort(key=lambda x: property_details[x]["usage_count"], reverse=True)
        else:
            filtered_props.sort()
        
        if filtered_props:
            # 페이지네이션
            items_per_page = 20
            total_pages = (len(filtered_props) + items_per_page - 1) // items_per_page
            page = st.selectbox("페이지", range(1, total_pages + 1), index=0, key="prop_page") if total_pages > 1 else 1
            
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_props = filtered_props[start_idx:end_idx]
            
            # 테이블 형식으로 표시
            prop_data = []
            for prop_name in page_props:
                details = property_details[prop_name]
                prop_data.append({
                    "속성명": prop_name,
                    "사용 횟수": details["usage_count"],
                    "URI": details["uri"][:50] + "..." if len(details["uri"]) > 50 else details["uri"]
                })
            
            df = pd.DataFrame(prop_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if total_pages > 1:
                st.caption(f"페이지 {page}/{total_pages} (총 {len(filtered_props)}개 속성)")
            
            # 통계 정보
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 속성 수", len(properties))
            with col2:
                total_usage = sum(d["usage_count"] for d in property_details.values())
                st.metric("총 사용 횟수", f"{total_usage:,}")
            with col3:
                avg_usage = total_usage / len(properties) if properties else 0
                st.metric("평균 사용 횟수", f"{avg_usage:.1f}")
            with col4:
                max_usage_prop = max(property_details.items(), key=lambda x: x[1]["usage_count"])
                st.metric("가장 많이 사용", max_usage_prop[0][:20])
        else:
            st.info("검색 조건에 맞는 속성이 없습니다.")
    else:
        st.warning("⚠️ 등록된 속성이 없습니다.")

def _render_relation_definition(orchestrator):
    """관계 정의 - 개선된 버전 (누락된 테이블 경고 추가)"""
    st.markdown("#### 🔗 관계 정의")
    st.info("💡 온톨로지의 관계(Relation) 규칙을 정의하고 관리합니다.")
    
    # relation_mappings.json 로드
    base_dir = Path(__file__).parent.parent.parent.parent
    relation_mapping_path = base_dir / "metadata" / "relation_mappings.json"
    
    if not relation_mapping_path.exists():
        st.error("관계 매핑 파일을 찾을 수 없습니다.")
        return
    
    with open(relation_mapping_path, 'r', encoding='utf-8') as f:
        relation_mappings = json.load(f)
    
    # schema_registry.yaml과 비교하여 누락된 테이블 확인
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    schema_registry = ontology_manager.schema_registry if hasattr(ontology_manager, 'schema_registry') else {}
    
    # data_lake의 실제 파일 확인
    data_lake_path = base_dir / "data_lake"
    actual_tables = set()
    if data_lake_path.exists():
        for file in data_lake_path.glob("*.xlsx"):
            table_name = file.stem
            actual_tables.add(table_name)
    
    # relation_mappings.json에 있는 테이블 (중복 제거)
    mapped_tables = set(relation_mappings.keys())
    
    # schema_registry에 있는 테이블
    registry_tables = set(schema_registry.keys()) if schema_registry else set()
    
    # 누락된 테이블 확인
    missing_from_mapping = registry_tables - mapped_tables
    missing_from_registry = mapped_tables - registry_tables
    
    # 통계 계산
    total_tables = len(relation_mappings)
    total_rules = sum(len(rules) for rules in relation_mappings.values())
    
    # 관계 유형별 분류
    rule_types = {
        "일반 관계": 0,
        "동적 FK": 0,
        "추론 관계": 0
    }
    
    relation_data = []
    for table_name, rules in relation_mappings.items():
        if not rules:  # 빈 규칙은 스킵
            continue
        for col_name, rule_config in rules.items():
            rule_type = "일반 관계"
            if isinstance(rule_config, dict):
                if rule_config.get("dynamic"):
                    rule_type = "동적 FK"
                elif col_name.startswith("추론:"):
                    rule_type = "추론 관계"
            
            rule_types[rule_type] += 1
            
            target = rule_config.get("target", "") if isinstance(rule_config, dict) else str(rule_config)
            relation = rule_config.get("relation", "") if isinstance(rule_config, dict) else ""
            
            relation_data.append({
                "소스 테이블": table_name,
                "소스 컬럼": col_name.replace("추론:", "").replace("동적FK:", ""),
                "관계 유형": rule_type,
                "타겟": target,
                "관계명": relation,
                "설정": json.dumps(rule_config, ensure_ascii=False) if isinstance(rule_config, dict) else str(rule_config)
            })
    
    # 경고 표시
    if missing_from_mapping:
        st.warning(f"⚠️ **{len(missing_from_mapping)}개 테이블이 관계 매핑에 누락되었습니다:** {', '.join(sorted(missing_from_mapping))}")
        st.info("💡 `schema_registry.yaml`에는 정의되어 있지만 `relation_mappings.json`에 관계 규칙이 없습니다. 온톨로지 생성 시 해당 테이블의 관계가 생성되지 않을 수 있습니다.")
    
    if missing_from_registry:
        st.info(f"ℹ️ **{len(missing_from_registry)}개 테이블이 schema_registry에 없습니다:** {', '.join(sorted(missing_from_registry))}")
    
    st.success(f"✅ 등록된 관계 규칙: **{len(mapped_tables)}개 테이블**, **{total_rules}개 규칙**")
    
    # 동기화 상태 표시
    if schema_registry:
        sync_status = len(mapped_tables) / len(registry_tables) * 100 if registry_tables else 0
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("테이블 수", len(mapped_tables))
        with col2:
            st.metric("총 규칙 수", total_rules)
        with col3:
            st.metric("일반 관계", rule_types["일반 관계"])
        with col4:
            st.metric("동적/추론", rule_types["동적 FK"] + rule_types["추론 관계"])
        with col5:
            delta_color = "normal" if sync_status >= 90 else "inverse"
            st.metric("동기화율", f"{sync_status:.1f}%", 
                     delta="완전" if sync_status >= 90 else "부족",
                     delta_color=delta_color)
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("테이블 수", len(mapped_tables))
        with col2:
            st.metric("총 규칙 수", total_rules)
        with col3:
            st.metric("일반 관계", rule_types["일반 관계"])
        with col4:
            st.metric("동적/추론", rule_types["동적 FK"] + rule_types["추론 관계"])
    
    st.divider()
    
    # 필터링 옵션
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 검색", placeholder="테이블명, 컬럼명, 관계명으로 검색...", key="rel_search")
    with col2:
        filter_type = st.selectbox("관계 유형 필터", ["전체", "일반 관계", "동적 FK", "추론 관계"], index=0, key="rel_filter")
    
    # 필터링
    filtered_data = relation_data
    if search_term:
        filtered_data = [
            r for r in filtered_data
            if search_term.lower() in r["소스 테이블"].lower() or
               search_term.lower() in r["소스 컬럼"].lower() or
               search_term.lower() in r["관계명"].lower()
        ]
    if filter_type != "전체":
        filtered_data = [r for r in filtered_data if r["관계 유형"] == filter_type]
    
    if filtered_data:
        # 테이블 형식으로 표시 (설정 컬럼 제외)
        display_data = [
            {
                "소스 테이블": r["소스 테이블"],
                "소스 컬럼": r["소스 컬럼"],
                "관계 유형": r["관계 유형"],
                "타겟": r["타겟"],
                "관계명": r["관계명"]
            }
            for r in filtered_data
        ]
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 상세 정보는 expander로 표시
        with st.expander("📋 상세 설정 보기 (JSON)", expanded=False):
            if len(filtered_data) > 0:
                selected_idx = st.selectbox("규칙 선택", range(len(filtered_data)), 
                                           format_func=lambda x: f"{filtered_data[x]['소스 테이블']}.{filtered_data[x]['소스 컬럼']}",
                                           key="rel_detail_select")
                try:
                    st.json(json.loads(filtered_data[selected_idx]["설정"]))
                except:
                    st.code(filtered_data[selected_idx]["설정"])
    else:
        st.info("검색 조건에 맞는 관계 규칙이 없습니다.")
    
    # 누락된 테이블 상세 정보
    if missing_from_mapping:
        st.divider()
        st.markdown("#### ⚠️ 누락된 테이블 상세 정보")
        missing_data = []
        for table_name in sorted(missing_from_mapping):
            table_info = schema_registry.get(table_name, {})
            relations = table_info.get('relations', [])
            missing_data.append({
                "테이블명": table_name,
                "설명": table_info.get('description', ''),
                "정의된 관계 수": len(relations),
                "파일명": table_info.get('file_name', '')
            })
        
        if missing_data:
            df_missing = pd.DataFrame(missing_data)
            st.dataframe(df_missing, use_container_width=True, hide_index=True)
            st.info("💡 이 테이블들은 `schema_registry.yaml`에 관계가 정의되어 있지만 `relation_mappings.json`에 반영되지 않았습니다.")

def _render_schema_validation(orchestrator):
    """스키마 검증 - 개선된 버전 (개선방안 제시 추가)"""
    st.markdown("#### ✅ 스키마 검증")
    st.info("💡 온톨로지 스키마의 일관성 및 유효성을 검증합니다.")
    
    # 검증 실행 버튼
    if st.button("🚀 스키마 검증 실행", type="primary", key="schema_validate_btn"):
        st.session_state.schema_validation_running = True
        st.rerun()
    
    # 검증 실행 및 결과 저장
    if st.session_state.get('schema_validation_running', False):
        st.session_state.schema_validation_running = False  # 플래그 초기화
        
        with st.spinner("검증 중..."):
            from core_pipeline.ontology_validator import OntologyValidator
            validator = OntologyValidator(orchestrator.core.enhanced_ontology_manager)
            report = validator.validate_schema_compliance()
            
            st.session_state.schema_validation_report = report
            
            # 권장사항 추출 및 저장
            recommendations = _extract_recommendations(report)
            if recommendations:
                st.session_state.validation_recommendations = recommendations
                st.session_state.validation_recommendations_timestamp = datetime.now()
                # navigate_to_tab은 제거 (자동 탭 이동 방지)
            else:
                # 권장사항이 없으면 기존 권장사항 제거
                if 'validation_recommendations' in st.session_state:
                    del st.session_state.validation_recommendations
                if 'validation_recommendations_timestamp' in st.session_state:
                    del st.session_state.validation_recommendations_timestamp
        
        st.rerun()  # 결과 표시를 위한 재렌더링
    
    # 검증 결과 표시
    if 'schema_validation_report' in st.session_state:
        report = st.session_state.schema_validation_report
        
        # 검증 결과 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            score = report['overall_score']
            delta_color = "normal" if score >= 80 else "inverse"
            st.metric("종합 점수", f"{score}%", 
                     delta="통과" if score >= 80 else "미통과",
                     delta_color=delta_color)
        
        # 상세 검증 결과
        st.divider()
        
        # Axis 검증
        axis_res = report.get('axis_compliance', {})
        with st.expander("1. 전장축선(Axis) 객체화 검증", expanded=True):
            for check in axis_res.get('checks', []):
                status_icon = "🟢" if check.get('status') == 'PASS' else "🔴"
                st.markdown(f"**{status_icon} {check.get('name', '')}**: {check.get('message', '')}")
            
            # 개선방안 제시
            if axis_res.get('score', 0) < 100:
                st.warning("⚠️ 개선 필요")
                st.markdown("**개선 방안:**")
                st.markdown("""
                - 전장축선이 객체로 존재하지 않는 경우:
                  1. 온톨로지 생성 페이지에서 전장축선 데이터를 확인하세요
                  2. `schema_registry.yaml`에서 전장축선 테이블의 관계 설정을 확인하세요
                  3. 온톨로지를 재생성하여 전장축선이 객체로 변환되도록 하세요
                - 축선-지형 연결이 없는 경우:
                  1. `relation_mappings.json`에서 `전장축선` 테이블의 관계 규칙을 확인하세요
                  2. 지형셀과의 연결 관계(`locatedIn` 등)가 정의되어 있는지 확인하세요
                """)
        
        # 연결성 검증
        conn_res = report.get('connectivity_health', {})
        with st.expander("2. 데이터 연결성 검증", expanded=True):
            for check in conn_res.get('checks', []):
                status_icon = "🟢" if check.get('status') == 'PASS' else "🟡"
                st.markdown(f"**{status_icon} {check.get('name', '')}**: {check.get('message', '')}")
            
            # 개선방안 제시
            failed_checks = [c for c in conn_res.get('checks', []) if c.get('status') != 'PASS']
            if failed_checks:
                st.warning("⚠️ 개선 필요")
                st.markdown("**개선 방안:**")
                for check in failed_checks:
                    check_name = check.get('name', '')
                    if "고립된 노드" in check_name:
                        st.markdown(f"""
                        - **{check_name}**:
                          1. 관계 관리 탭에서 고립된 노드를 확인하세요
                          2. 해당 노드에 대한 관계 규칙이 `relation_mappings.json`에 정의되어 있는지 확인하세요
                          3. 필요시 관계를 수동으로 추가하세요
                        """)
                    elif "순환 참조" in check_name:
                        st.markdown(f"""
                        - **{check_name}**:
                          1. 관계 관리 탭에서 순환 참조 관계를 확인하세요
                          2. 순환 참조가 의도된 것인지 검토하세요
                          3. 의도되지 않은 경우 관계 규칙을 수정하세요
                        """)
        
        # 추론 엔진 상태 (있는 경우)
        if 'reasoning_status' in report:
            reason_res = report.get('reasoning_status', {})
            with st.expander("3. 추론 엔진 상태", expanded=False):
                for check in reason_res.get('checks', []):
                    status_icon = "🟢" if check.get('status') == 'PASS' else "⚪"
                    st.markdown(f"**{status_icon} {check.get('name', '')}**: {check.get('message', '')}")
        
        # 종합 개선방안
        st.divider()
        if report['overall_score'] >= 80:
            st.success("✅ 스키마 검증 통과!")
            # 통과 시 권장사항 제거
            if 'validation_recommendations' in st.session_state:
                del st.session_state.validation_recommendations
        else:
            st.warning(f"⚠️ 스키마 검증 점수: {report['overall_score']}% (80% 이상 권장)")
            
            st.markdown("#### 💡 종합 개선 권장사항")
            
            # 권장사항이 이미 추출되어 있으면 표시
            if 'validation_recommendations' in st.session_state:
                recommendations = st.session_state.validation_recommendations
                
                # 간단한 요약 테이블
                summary_data = []
                for rec in recommendations:
                    summary_data.append({
                        "우선순위": rec.get('우선순위', ''),
                        "항목": rec.get('항목', ''),
                        "조치": rec.get('조치', ''),
                        "대상": rec.get('대상', '')
                    })
                
                if summary_data:
                    df_rec = pd.DataFrame(summary_data)
                    st.dataframe(df_rec, use_container_width=True, hide_index=True)
                    
                    # 관계 관리 탭으로 이동 안내
                    st.info("💡 **개선 권장사항을 조치하려면:** 위의 권장사항을 확인하고, 필요시 **관계 관리** 탭으로 이동하여 관계를 추가/수정하세요.")
                    
                    # 관계 관리 탭으로 이동 버튼 (안내용)
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("🔗 관계 관리 탭으로 이동", type="primary", use_container_width=True, key="nav_to_rel_mgmt_from_validation"):
                            st.session_state.navigate_to_tab = "관계 관리"
                            if recommendations:
                                st.session_state.navigate_to_subtab = recommendations[0].get('관련_서브탭', '관계 조회')
                            st.info("👉 상단의 **관계 관리** 탭을 클릭하세요. 권장사항이 자동으로 표시됩니다.")
                    with col2:
                        st.caption("💡 권장사항은 관계 관리 탭 상단에 배너로 표시됩니다.")
            else:
                st.info("💡 상세한 관계 관리는 **관계 관리** 탭에서 수행할 수 있습니다.")

def _extract_recommendations(report: Dict) -> List[Dict]:
    """검증 결과에서 권장사항 추출"""
    recommendations = []
    
    # Axis 검증 권장사항
    axis_res = report.get('axis_compliance', {})
    if axis_res.get('score', 0) < 100:
        failed_checks = [c for c in axis_res.get('checks', []) if c.get('status') != 'PASS']
        for check in failed_checks:
            check_name = check.get('name', '')
            check_message = check.get('message', '')
            
            if "축선-지형 연결성" in check_name:
                recommendations.append({
                    "id": "axis_terrain_connectivity",
                    "우선순위": "높음",
                    "항목": "축선-지형 연결성",
                    "문제": check_message,
                    "조치": "관계 규칙 확인 및 추가",
                    "대상": "전장축선",
                    "관련_탭": "관계 관리",
                    "관련_서브탭": "관계 생성 규칙",
                    "상세_조치": [
                        "1. 관계 관리 탭의 '관계 생성 규칙' 서브탭으로 이동",
                        "2. '전장축선' 테이블 선택",
                        "3. 시작지형셀ID, 종단지형셀ID 관계 규칙 확인",
                        "4. 관계 규칙이 없으면 추가 (지형셀 타겟, has지형셀 관계)",
                        "5. 온톨로지 재생성하여 관계 적용"
                    ],
                    "관련_테이블": ["전장축선", "지형셀"],
                    "관련_관계": ["has지형셀"]
                })
            elif "전장축선 객체화" in check_name:
                recommendations.append({
                    "id": "axis_objectification",
                    "우선순위": "높음",
                    "항목": "전장축선 객체화",
                    "문제": check_message,
                    "조치": "온톨로지 재생성",
                    "대상": "전장축선",
                    "관련_탭": "온톨로지 생성",
                    "관련_서브탭": None,
                    "상세_조치": [
                        "1. 온톨로지 생성 페이지로 이동",
                        "2. 전장축선 데이터 확인",
                        "3. 온톨로지 재생성 실행"
                    ]
                })
    
    # 연결성 검증 권장사항
    conn_res = report.get('connectivity_health', {})
    failed_conn = [c for c in conn_res.get('checks', []) if c.get('status') != 'PASS']
    for check in failed_conn:
        check_name = check.get('name', '')
        check_message = check.get('message', '')
        
        if "고립된 노드" in check_name:
            recommendations.append({
                "id": "orphan_nodes",
                "우선순위": "중간",
                "항목": "고립된 노드",
                "문제": check_message,
                "조치": "고립된 노드 확인 및 관계 추가",
                "대상": "전체",
                "관련_탭": "관계 관리",
                "관련_서브탭": "관계 조회",
                "상세_조치": [
                    "1. 관계 관리 탭의 '관계 조회' 서브탭으로 이동",
                    "2. 고립된 노드 검색 및 확인",
                    "3. 필요한 관계를 '관계 편집' 서브탭에서 추가",
                    "4. 또는 '관계 생성 규칙' 서브탭에서 관계 규칙 추가"
                ]
            })
        elif "순환 참조" in check_name:
            recommendations.append({
                "id": "circular_reference",
                "우선순위": "중간",
                "항목": "순환 참조",
                "문제": check_message,
                "조치": "순환 참조 관계 확인 및 수정",
                "대상": "전체",
                "관련_탭": "관계 관리",
                "관련_서브탭": "관계 조회",
                "상세_조치": [
                    "1. 관계 관리 탭의 '관계 조회' 서브탭으로 이동",
                    "2. 순환 참조 관계 검색 및 확인",
                    "3. 의도된 순환 참조인지 검토",
                    "4. 의도되지 않은 경우 '관계 편집' 서브탭에서 수정"
                ]
            })
    
    return recommendations
