# ui/components/relationship_quality_validator.py
# -*- coding: utf-8 -*-
"""
관계 품질 검증 컴포넌트
AI가 자동 생성한 관계의 적정성을 검증하는 도구
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json
from pathlib import Path


def render_relationship_quality_validator(orchestrator, show_title=True):
    """
    관계 품질 검증 대시보드
    
    Args:
        orchestrator: Orchestrator 인스턴스
        show_title: 제목 표시 여부 (기본값: True)
    """
    if show_title:
        st.markdown("### 🔍 관계 품질 검증 (Relationship Quality Validation)")
    st.info("💡 **AI가 자동 생성한 관계의 적정성을 검증**하고, 이상 패턴을 탐지합니다.")
    
    ontology_manager = orchestrator.core.enhanced_ontology_manager
    if not ontology_manager or not ontology_manager.graph:
        st.warning("온톨로지 그래프가 없습니다. 먼저 온톨로지를 생성하세요.")
        return
    
    graph = ontology_manager.graph
    ns = ontology_manager.ns
    
    # 1. 전체 통계
    st.markdown("#### 📊 전체 관계 통계")
    quality_report = _analyze_relationship_quality(graph, ns, ontology_manager)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 튜플 수", f"{quality_report['total_triples']:,}")
    with col2:
        st.metric("관계 유형 수", quality_report['relation_type_count'])
    with col3:
        st.metric("평균 관계 밀도", f"{quality_report['avg_relationship_density']:.2f}")
    with col4:
        anomaly_score = quality_report.get('anomaly_score', 0)
        st.metric("이상 패턴 점수", f"{anomaly_score:.1f}%", 
                 delta=f"{'정상' if anomaly_score < 30 else '주의' if anomaly_score < 60 else '위험'}")
    
    # 2. 관계 유형별 분석
    st.divider()
    st.markdown("#### 📈 관계 유형별 분석")
    
    relation_stats = quality_report.get('relation_type_stats', [])
    if relation_stats:
        # 테이블로 표시
        df_stats = pd.DataFrame(relation_stats)
        df_stats = df_stats.sort_values('count', ascending=False)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(
                df_stats[['relation_type', 'count', 'percentage', 'status']],
                use_container_width=True,
                hide_index=True
            )
        with col2:
            # 이상 패턴 하이라이트
            anomalies = [r for r in relation_stats if r.get('is_anomaly', False)]
            if anomalies:
                st.warning(f"⚠️ **{len(anomalies)}개 이상 패턴 발견**")
                for anomaly in anomalies[:5]:
                    st.markdown(f"- `{anomaly['relation_type']}`: {anomaly['count']:,}개")
            else:
                st.success("✅ 이상 패턴 없음")
    
    # 3. 테이블별 관계 밀도 분석
    st.divider()
    st.markdown("#### 🗂️ 테이블별 관계 밀도 분석")
    
    table_density = quality_report.get('table_density', {})
    if table_density:
        df_density = pd.DataFrame([
            {
                "테이블": table,
                "관계 수": stats['relation_count'],
                "평균 밀도": f"{stats['avg_density']:.2f}",
                "상태": stats['status']
            }
            for table, stats in table_density.items()
        ])
        df_density = df_density.sort_values('관계 수', ascending=False)
        
        st.dataframe(df_density, use_container_width=True, hide_index=True)
        
        # 이상 밀도 테이블 하이라이트
        high_density_tables = [
            (table, stats) 
            for table, stats in table_density.items() 
            if stats.get('is_anomaly', False)
        ]
        if high_density_tables:
            st.warning("⚠️ **이상적으로 높은 관계 밀도를 가진 테이블:**")
            for table, stats in high_density_tables[:5]:
                st.markdown(f"- `{table}`: {stats['relation_count']:,}개 관계 (평균 대비 {stats['density_ratio']:.1f}배)")
    
    # 4. 관계 패턴 시각화
    st.divider()
    st.markdown("#### 📊 관계 패턴 시각화")
    
    viz_mode = st.radio(
        "시각화 모드",
        ["관계 유형별 분포", "테이블별 관계 밀도", "이상 패턴 하이라이트"],
        horizontal=True
    )
    
    if viz_mode == "관계 유형별 분포":
        _render_relation_type_distribution(relation_stats)
    elif viz_mode == "테이블별 관계 밀도":
        _render_table_density_chart(table_density)
    else:
        _render_anomaly_highlight(quality_report)
    
    # 5. 검증 권장사항
    st.divider()
    st.markdown("#### 💡 검증 권장사항")
    
    recommendations = _generate_recommendations(quality_report)
    for i, rec in enumerate(recommendations, 1):
        with st.expander(f"{i}. {rec['title']}", expanded=(i == 1)):
            st.markdown(rec['description'])
            if rec.get('actions'):
                st.markdown("**권장 조치:**")
                for action in rec['actions']:
                    st.markdown(f"- {action}")


def _analyze_relationship_quality(graph, ns, ontology_manager) -> Dict:
    """관계 품질 분석"""
    # 전체 튜플 수
    all_triples = list(graph.triples((None, None, None)))
    total_triples = len(all_triples)
    
    # 관계 유형별 통계
    relation_type_counts = defaultdict(int)
    relation_type_details = defaultdict(list)
    
    for s, p, o in all_triples:
        # 온톨로지 네임스페이스의 관계만 카운트 (rdf:type 제외)
        if str(p).startswith(str(ns)) and str(p) != str(ns.type):
            relation_name = str(p).replace(str(ns), "")
            relation_type_counts[relation_name] += 1
            relation_type_details[relation_name].append((str(s), str(o)))
    
    # 평균 관계 밀도 계산
    avg_count = sum(relation_type_counts.values()) / len(relation_type_counts) if relation_type_counts else 0
    std_count = _calculate_std([v for v in relation_type_counts.values()]) if relation_type_counts else 0
    
    # 이상 패턴 탐지 (Z-score 기반)
    relation_type_stats = []
    for rel_type, count in relation_type_counts.items():
        z_score = (count - avg_count) / std_count if std_count > 0 else 0
        is_anomaly = abs(z_score) > 2.0  # 2 표준편차 이상
        
        relation_type_stats.append({
            "relation_type": rel_type,
            "count": count,
            "percentage": (count / total_triples * 100) if total_triples > 0 else 0,
            "z_score": z_score,
            "is_anomaly": is_anomaly,
            "status": "⚠️ 이상" if is_anomaly else "✅ 정상"
        })
    
    # 테이블별 관계 밀도 분석
    table_density = _analyze_table_density(graph, ns, ontology_manager)
    
    # 이상 점수 계산 (0-100, 높을수록 이상)
    anomaly_count = sum(1 for r in relation_type_stats if r['is_anomaly'])
    anomaly_score = (anomaly_count / len(relation_type_stats) * 100) if relation_type_stats else 0
    
    return {
        "total_triples": total_triples,
        "relation_type_count": len(relation_type_counts),
        "avg_relationship_density": avg_count,
        "relation_type_stats": relation_type_stats,
        "table_density": table_density,
        "anomaly_score": anomaly_score,
        "anomaly_count": anomaly_count
    }


def _analyze_table_density(graph, ns, ontology_manager) -> Dict:
    """테이블별 관계 밀도 분석"""
    schema_registry = ontology_manager.schema_registry if ontology_manager else {}
    
    # 테이블별 관계 수 집계
    table_relations = defaultdict(int)
    
    for s, p, o in graph.triples((None, None, None)):
        if str(p).startswith(str(ns)) and str(p) != str(ns.type):
            # 주체가 어느 테이블에 속하는지 추정
            s_str = str(s)
            for table_name in schema_registry.keys():
                if table_name in s_str or any(col in s_str for col in schema_registry.get(table_name, {}).get('columns', {}).keys()):
                    table_relations[table_name] += 1
                    break
    
    # 평균 밀도 계산
    avg_density = sum(table_relations.values()) / len(table_relations) if table_relations else 0
    std_density = _calculate_std([v for v in table_relations.values()]) if table_relations else 0
    
    # 테이블별 밀도 분석
    result = {}
    for table, count in table_relations.items():
        z_score = (count - avg_density) / std_density if std_density > 0 else 0
        is_anomaly = abs(z_score) > 2.0
        
        result[table] = {
            "relation_count": count,
            "avg_density": avg_density,
            "z_score": z_score,
            "is_anomaly": is_anomaly,
            "density_ratio": count / avg_density if avg_density > 0 else 0,
            "status": "⚠️ 이상" if is_anomaly else "✅ 정상"
        }
    
    return result


def _calculate_std(values: List[float]) -> float:
    """표준편차 계산"""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


def _render_relation_type_distribution(relation_stats: List[Dict]):
    """관계 유형별 분포 차트"""
    if not relation_stats:
        st.info("데이터가 없습니다.")
        return
    
    df = pd.DataFrame(relation_stats)
    df = df.sort_values('count', ascending=False).head(20)
    
    st.bar_chart(df.set_index('relation_type')['count'])


def _render_table_density_chart(table_density: Dict):
    """테이블별 관계 밀도 차트"""
    if not table_density:
        st.info("데이터가 없습니다.")
        return
    
    df = pd.DataFrame([
        {"테이블": table, "관계 수": stats['relation_count']}
        for table, stats in table_density.items()
    ])
    df = df.sort_values('관계 수', ascending=False)
    
    st.bar_chart(df.set_index('테이블')['관계 수'])


def _render_anomaly_highlight(quality_report: Dict):
    """이상 패턴 하이라이트"""
    anomalies = [
        r for r in quality_report.get('relation_type_stats', [])
        if r.get('is_anomaly', False)
    ]
    
    if not anomalies:
        st.success("✅ 이상 패턴이 발견되지 않았습니다.")
        return
    
    st.warning(f"⚠️ **{len(anomalies)}개 이상 패턴 발견**")
    
    for anomaly in anomalies[:10]:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{anomaly['relation_type']}**")
        with col2:
            st.metric("개수", f"{anomaly['count']:,}")
        with col3:
            st.metric("Z-score", f"{anomaly['z_score']:.2f}")


def _generate_recommendations(quality_report: Dict) -> List[Dict]:
    """검증 권장사항 생성"""
    recommendations = []
    
    anomaly_score = quality_report.get('anomaly_score', 0)
    anomaly_count = quality_report.get('anomaly_count', 0)
    
    if anomaly_score > 60:
        recommendations.append({
            "title": "높은 이상 패턴 비율",
            "description": f"전체 관계 유형의 {anomaly_score:.1f}%에서 이상 패턴이 발견되었습니다. 관계 생성 규칙을 재검토해야 합니다.",
            "actions": [
                "이상 패턴이 많은 관계 유형의 생성 규칙 확인",
                "관계 생성 임계값 조정 검토",
                "수동 검증 대상 관계 목록 작성"
            ]
        })
    
    if anomaly_count > 0:
        recommendations.append({
            "title": "이상 관계 유형 검토",
            "description": f"{anomaly_count}개 관계 유형에서 이상 패턴이 발견되었습니다. 각 유형별로 관계 수가 적정한지 확인하세요.",
            "actions": [
                "이상 패턴 목록에서 각 관계 유형 클릭하여 상세 확인",
                "관계 생성 로그 확인",
                "관계 매핑 규칙 검토"
            ]
        })
    
    total_triples = quality_report.get('total_triples', 0)
    if total_triples > 100000:
        recommendations.append({
            "title": "대량의 튜플 생성",
            "description": f"총 {total_triples:,}개의 튜플이 생성되었습니다. 관계 생성 규칙이 너무 관대할 수 있습니다.",
            "actions": [
                "관계 생성 규칙의 필터링 조건 강화 검토",
                "불필요한 관계 제거 규칙 추가",
                "관계 품질 임계값 설정"
            ]
        })
    
    if not recommendations:
        recommendations.append({
            "title": "관계 품질 양호",
            "description": "현재 관계 품질이 양호한 것으로 보입니다. 정기적인 모니터링을 계속하세요.",
            "actions": [
                "주기적인 관계 품질 검증 실행",
                "새로운 데이터 추가 시 관계 품질 확인"
            ]
        })
    
    return recommendations

