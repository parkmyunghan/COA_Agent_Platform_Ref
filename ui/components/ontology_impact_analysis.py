# ui/components/ontology_impact_analysis.py
# -*- coding: utf-8 -*-
"""
온톨로지 영향력 분석 컴포넌트
온톨로지에서 추출한 정보가 점수 계산에 미친 영향을 분석하고 표시
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


def render_ontology_impact_analysis(agent_result: Dict, core=None):
    """
    온톨로지 정보의 영향력 분석 렌더링
    
    Args:
        agent_result: Agent 실행 결과 딕셔너리
        core: CorePipeline 인스턴스 (선택적)
    """
    if not agent_result:
        st.info("분석할 결과가 없습니다.")
        return
    
    st.subheader("🔍 온톨로지 영향력 분석")
    st.markdown("온톨로지에서 추출한 정보가 방책 추천 점수에 미친 영향을 분석합니다.")
    
    recommendations = agent_result.get("recommendations", [])
    if not recommendations:
        st.warning("추천 결과가 없습니다.")
        return
    
    top_recommendation = recommendations[0]
    situation_analysis = agent_result.get("situation_analysis", {})
    score_breakdown = top_recommendation.get("score_breakdown", {})
    
    # 디버깅 정보 표시
    with st.expander("🔧 시스템 상태 및 디버깅 정보", expanded=False):
        render_debug_info(agent_result, core, situation_analysis, score_breakdown)
    
    # 1. 온톨로지 정보 요약
    with st.expander("📊 온톨로지 정보 요약", expanded=True):
        render_ontology_info_summary(situation_analysis, agent_result, core)
    
    # 2. 점수별 온톨로지 기여도 분석
    with st.expander("📈 점수별 온톨로지 기여도", expanded=True):
        if not score_breakdown:
            st.warning("점수 breakdown 정보가 없습니다.")
            st.info("""
            **가능한 원인:**
            1. 팔란티어 모드가 사용되지 않았습니다. (기본 모드 사용)
            2. 점수 계산이 완료되지 않았습니다.
            
            **해결 방법:**
            - 팔란티어 모드를 활성화하여 Agent를 다시 실행하세요.
            - "상황 입력 및 추천" 탭에서 "팔란티어 모드" 체크박스를 선택하세요.
            """)
        else:
            render_score_ontology_contribution(score_breakdown, situation_analysis, top_recommendation)
    
    # 3. 체인 정보 상세 분석
    chain_info = situation_analysis.get("chain_info", {})
    if chain_info:
        with st.expander("🔗 관계 체인 분석", expanded=False):
            render_chain_analysis(chain_info, top_recommendation)
    
    # 4. RAG 검색 결과 상세
    rag_results = situation_analysis.get("rag_results", [])
    if rag_results:
        with st.expander("📚 RAG 검색 결과 상세", expanded=False):
            render_rag_results_detail(rag_results, score_breakdown)
    
    # 5. 관련 엔티티 상세
    related_entities = situation_analysis.get("related_entities", [])
    if related_entities:
        with st.expander("🏷️ 관련 엔티티 상세", expanded=False):
            render_related_entities_detail(related_entities, core)


def render_ontology_info_summary(situation_analysis: Dict, agent_result: Dict, core=None):
    """온톨로지 정보 요약 표시"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        rag_results = situation_analysis.get("rag_results", [])
        st.metric("RAG 검색 결과", f"{len(rag_results)}개")
        if len(rag_results) == 0:
            if core and not core.rag_manager.is_available():
                st.caption("⚠️ RAG 매니저 미사용")
            else:
                st.caption("ℹ️ RAG 검색 미수행")
    
    with col2:
        related_entities = situation_analysis.get("related_entities", [])
        st.metric("관련 엔티티", f"{len(related_entities)}개")
        if len(related_entities) == 0:
            if core and core.ontology_manager.graph is None:
                st.caption("⚠️ 온톨로지 그래프 없음")
            else:
                st.caption("ℹ️ 관련 엔티티 미탐색")
    
    with col3:
        chain_info = situation_analysis.get("chain_info", {})
        chains = chain_info.get("chains", []) if chain_info else []
        st.metric("관계 체인", f"{len(chains)}개")
        if len(chains) == 0:
            palantir_mode = agent_result.get("palantir_mode", False)
            if not palantir_mode:
                st.caption("⚠️ 팔란티어 모드 필요")
            else:
                st.caption("ℹ️ 체인 미발견")
    
    with col4:
        if hasattr(situation_analysis, 'graph') or 'graph_triples' in situation_analysis:
            triples = situation_analysis.get('graph_triples', 0)
            st.metric("온톨로지 Triples", f"{triples}개")
        else:
            if core and core.ontology_manager.graph:
                triples_count = len(list(core.ontology_manager.graph.triples((None, None, None))))
                st.metric("온톨로지 Triples", f"{triples_count}개")
            else:
                st.metric("온톨로지 사용", "활성")
    
    # 정보가 없을 때 안내
    if len(situation_analysis) == 0:
        st.warning("⚠️ 상황 분석 정보가 없습니다.")
        st.info("""
        **가능한 원인:**
        1. Agent 실행 시 상황 분석이 수행되지 않았습니다.
        2. RAG 매니저가 사용 불가능합니다.
        3. 온톨로지 그래프가 구축되지 않았습니다.
        
        **확인 사항:**
        - RAG 인덱스가 구축되었는지 확인하세요.
        - 온톨로지 그래프가 생성되었는지 확인하세요.
        """)
    
    # 온톨로지 정보 활용 여부
    st.markdown("---")
    st.markdown("#### 온톨로지 정보 활용 현황")
    
    # score_breakdown에서 정보 가져오기
    top_recommendation = agent_result.get("recommendations", [{}])[0] if agent_result.get("recommendations") else {}
    score_breakdown = top_recommendation.get("score_breakdown", {})
    
    # 자원 매칭 확인 (resource_info 또는 score_breakdown에서)
    resource_used = False
    if situation_analysis.get("resource_info"):
        resource_used = True
    elif score_breakdown and score_breakdown.get("resources", 0) > 0:
        resource_used = True
    else:
        resource_used = _check_resource_matching(situation_analysis)
    
    # 환경 호환성 확인 (environment_info 또는 score_breakdown에서)
    environment_used = False
    if situation_analysis.get("environment_info"):
        environment_used = True
    elif score_breakdown and score_breakdown.get("environment", 0) > 0:
        environment_used = True
    else:
        environment_used = _check_environment_compatibility(situation_analysis)
    
    ontology_usage = {
        "RAG 검색": len(situation_analysis.get("rag_results", [])) > 0,
        "관계 체인": len(situation_analysis.get("chain_info", {}).get("chains", [])) > 0,
        "관련 엔티티": len(situation_analysis.get("related_entities", [])) > 0,
        "자원 매칭": resource_used,
        "환경 호환성": environment_used,
    }
    
    usage_data = []
    for key, value in ontology_usage.items():
        status = "✅ 사용됨" if value else "❌ 미사용"
        reason = _get_usage_reason(key, value, situation_analysis, agent_result, core)
        usage_data.append({
            "항목": key,
            "활용 여부": status,
            "원인/상태": reason
        })
    
    usage_df = pd.DataFrame(usage_data)
    st.dataframe(usage_df, width='stretch', hide_index=True)
    
    # 미사용 항목에 대한 해결 방법 제시
    unused_items = [key for key, value in ontology_usage.items() if not value]
    if unused_items:
        st.markdown("---")
        st.markdown("#### 💡 해결 방법")
        for item in unused_items:
            solution = _get_solution_for_item(item, core, agent_result)
            if solution:
                with st.expander(f"❌ {item} 활성화 방법", expanded=False):
                    st.markdown(solution)


def render_score_ontology_contribution(score_breakdown: Dict, situation_analysis: Dict, recommendation: Dict):
    """점수별 온톨로지 기여도 분석"""
    if not score_breakdown:
        st.info("점수 breakdown 정보가 없습니다.")
        return
    
    # 각 점수 요소별 온톨로지 기여도 분석
    factors = {
        "threat": ("위협 수준", "위협 정보는 주로 입력 데이터에서 추출"),
        "resources": ("자원 가용성", "온톨로지에서 COA-자원 관계 조회"),
        "assets": ("전력 능력", "온톨로지에서 아군 자산 정보 조회"),
        "environment": ("환경 적합성", "온톨로지에서 기상-위협 관계 조회"),
        "historical": ("과거 효과성", "RAG 검색 결과 기반"),
        "chain": ("연계성", "온톨로지 관계 체인 탐색 기반"),
    }
    
    contribution_data = []
    
    for key, (name, description) in factors.items():
        score = score_breakdown.get(key, 0)
        
        # 온톨로지 기여도 판단
        ontology_contribution = _analyze_ontology_contribution(
            key, score, situation_analysis, recommendation
        )
        
        contribution_data.append({
            "요소": name,
            "점수": f"{score:.3f}",
            "온톨로지 기여도": ontology_contribution["level"],
            "기여 내용": ontology_contribution["description"],
            "데이터 출처": ontology_contribution["source"]
        })
    
    df = pd.DataFrame(contribution_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    # 기여도 시각화
    try:
        import plotly.express as px
        
        # 기여도 레벨을 숫자로 변환
        level_map = {"높음": 3, "보통": 2, "낮음": 1, "없음": 0}
        df_viz = df.copy()
        df_viz["기여도 점수"] = df_viz["온톨로지 기여도"].map(level_map)
        
        fig = px.bar(
            df_viz,
            x="요소",
            y="기여도 점수",
            color="온톨로지 기여도",
            title="온톨로지 기여도 분석",
            color_discrete_map={"높음": "#2ecc71", "보통": "#f39c12", "낮음": "#e74c3c", "없음": "#95a5a6"}
        )
        fig.update_layout(yaxis_title="기여도 (높음=3, 보통=2, 낮음=1, 없음=0)")
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        st.info("Plotly가 설치되지 않아 차트를 표시할 수 없습니다.")


def render_chain_analysis(chain_info: Dict, recommendation: Dict):
    """체인 정보 상세 분석"""
    chains = chain_info.get("chains", [])
    if not chains:
        st.info("체인 정보가 없습니다.")
        return
    
    st.write(f"**발견된 관계 체인: {len(chains)}개**")
    
    # 체인 요약 정보
    summary = chain_info.get("summary", {})
    if summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("평균 체인 길이", f"{summary.get('avg_depth', 0):.1f}")
        with col2:
            st.metric("평균 체인 점수", f"{summary.get('avg_score', 0):.3f}")
        with col3:
            st.metric("최고 체인 점수", f"{summary.get('max_score', 0):.3f}")
    
    # 상위 체인 표시
    st.markdown("#### 상위 관계 체인")
    
    for i, chain in enumerate(chains[:5], 1):  # 상위 5개만
        with st.container():
            path = chain.get("path", [])
            predicates = chain.get("predicates", [])
            score = chain.get("score", 0)
            
            # 체인 경로 표시
            chain_text = " → ".join([
                f"{_extract_entity_name(path[j])} ({_extract_predicate_name(predicates[j]) if j < len(predicates) else ''})"
                for j in range(len(path))
            ])
            
            st.markdown(f"**{i}. 체인 점수: {score:.3f}**")
            st.write(chain_text)
            
            if i < min(5, len(chains)):
                st.divider()
    
    # 체인 점수가 종합 점수에 미친 영향
    chain_score = recommendation.get("score_breakdown", {}).get("chain", 0)
    chain_weight = 0.10  # 체인 가중치 (기본값)
    
    st.markdown("#### 체인 점수의 종합 점수 기여도")
    st.write(f"- 체인 점수: {chain_score:.3f}")
    st.write(f"- 체인 가중치: {chain_weight:.2f}")
    st.write(f"- 기여도: {chain_score * chain_weight:.4f} (종합 점수에 기여)")


def render_rag_results_detail(rag_results: List[Dict], score_breakdown: Dict):
    """RAG 검색 결과 상세 표시"""
    historical_score = score_breakdown.get("historical", 0)
    
    st.write(f"**과거 효과성 점수: {historical_score:.3f}**")
    st.write(f"**검색된 문서: {len(rag_results)}개**")
    
    # 성공 키워드 분석
    success_keywords = ['성공', '효과적', '승리', '완료', '달성']
    success_count = 0
    
    for result in rag_results:
        text = result.get("text", "")
        if any(keyword in text for keyword in success_keywords):
            success_count += 1
    
    st.write(f"**성공 사례 포함 문서: {success_count}개**")
    st.write(f"**성공률: {success_count / len(rag_results) * 100:.1f}%** (과거 효과성 점수 계산에 사용)")
    
    st.markdown("---")
    st.markdown("#### 검색 결과 상세")
    
    for i, result in enumerate(rag_results[:5], 1):  # 상위 5개만
        with st.container():
            text = result.get("text", "")
            score = result.get("score", 0)
            metadata = result.get("metadata", {})
            
            st.markdown(f"**{i}. 관련도: {score:.3f}**")
            
            # 성공 키워드 하이라이트
            highlighted_text = text
            for keyword in success_keywords:
                if keyword in highlighted_text:
                    highlighted_text = highlighted_text.replace(
                        keyword, f"**{keyword}**"
                    )
            
            st.write(highlighted_text[:500] + ("..." if len(text) > 500 else ""))
            
            if metadata:
                st.caption(f"출처: {metadata.get('source', 'N/A')}")
            
            if i < min(5, len(rag_results)):
                st.divider()


def render_related_entities_detail(related_entities: List[Dict], core=None):
    """관련 엔티티 상세 표시"""
    st.write(f"**발견된 관련 엔티티: {len(related_entities)}개**")
    
    # 엔티티 타입별 그룹화
    entity_types = {}
    for entity in related_entities:
        entity_type = entity.get("type", "기타")
        if entity_type not in entity_types:
            entity_types[entity_type] = []
        entity_types[entity_type].append(entity)
    
    # 타입별 표시
    for entity_type, entities in entity_types.items():
        with st.expander(f"📌 {entity_type} ({len(entities)}개)", expanded=False):
            for entity in entities[:10]:  # 타입별 최대 10개
                entity_id = entity.get("id", entity.get("label", "Unknown"))
                entity_label = entity.get("label", entity_id)
                relations = entity.get("relations", [])
                
                st.write(f"**{entity_label}** ({entity_id})")
                if relations:
                    st.caption(f"관계: {', '.join(relations[:3])}")
                st.divider()


def _analyze_ontology_contribution(factor_key: str, score: float, situation_analysis: Dict, recommendation: Dict) -> Dict:
    """온톨로지 기여도 분석"""
    rag_results = situation_analysis.get("rag_results", [])
    chain_info = situation_analysis.get("chain_info", {})
    related_entities = situation_analysis.get("related_entities", [])
    
    if factor_key == "chain":
        chains = chain_info.get("chains", []) if chain_info else []
        if chains:
            return {
                "level": "높음",
                "description": f"온톨로지에서 {len(chains)}개의 관계 체인을 발견하여 연계성 점수 계산에 직접 사용",
                "source": "온톨로지 관계 체인 탐색"
            }
        else:
            return {
                "level": "없음",
                "description": "관계 체인을 찾지 못하여 기본값(0.5) 사용",
                "source": "기본값"
            }
    
    elif factor_key == "historical":
        if rag_results:
            success_count = sum(1 for r in rag_results if any(kw in r.get("text", "") for kw in ['성공', '효과적', '승리']))
            return {
                "level": "높음",
                "description": f"RAG 검색 결과 {len(rag_results)}개 중 {success_count}개가 성공 사례 포함",
                "source": "RAG 검색 (과거 문서)"
            }
        else:
            return {
                "level": "없음",
                "description": "RAG 검색 결과가 없어 기본값(0.5) 사용",
                "source": "기본값"
            }
    
    elif factor_key == "resources":
        # 자원 정보는 온톨로지에서 조회했는지 확인
        return {
            "level": "보통",
            "description": "온톨로지에서 COA-자원 관계를 조회하여 자원 가용성 계산",
            "source": "온톨로지 COA-자원 관계"
        }
    
    elif factor_key == "environment":
        # 환경 정보는 온톨로지에서 조회했는지 확인
        return {
            "level": "보통",
            "description": "온톨로지에서 기상-위협 관계를 조회하여 환경 적합성 계산",
            "source": "온톨로지 기상-위협 관계"
        }
    
    elif factor_key == "assets":
        if related_entities:
            asset_entities = [e for e in related_entities if "자산" in str(e.get("type", "")) or "asset" in str(e.get("type", "")).lower()]
            if asset_entities:
                return {
                    "level": "보통",
                    "description": f"온톨로지에서 {len(asset_entities)}개의 자산 엔티티 발견",
                    "source": "온톨로지 자산 엔티티"
                }
        
        return {
            "level": "낮음",
            "description": "주로 입력 데이터에서 자산 정보 추출",
            "source": "입력 데이터"
        }
    
    elif factor_key == "threat":
        return {
            "level": "낮음",
            "description": "주로 입력 데이터에서 위협 수준 추출",
            "source": "입력 데이터"
        }
    
    return {
        "level": "없음",
        "description": "온톨로지 정보 미사용",
        "source": "기본값"
    }


def _check_resource_matching(situation_analysis: Dict) -> bool:
    """자원 매칭 정보 확인"""
    # 자원 관련 정보가 있는지 확인
    related_entities = situation_analysis.get("related_entities", [])
    for entity in related_entities:
        if "자원" in str(entity.get("type", "")) or "resource" in str(entity.get("type", "")).lower():
            return True
    return False


def _check_environment_compatibility(situation_analysis: Dict) -> bool:
    """환경 호환성 정보 확인"""
    # 기상/환경 관련 정보가 있는지 확인
    related_entities = situation_analysis.get("related_entities", [])
    for entity in related_entities:
        entity_type = str(entity.get("type", "")).lower()
        if "기상" in entity_type or "weather" in entity_type or "환경" in entity_type or "environment" in entity_type:
            return True
    return False


def _extract_entity_name(uri: str) -> str:
    """URI에서 엔티티 이름 추출"""
    if not uri:
        return "Unknown"
    if "#" in uri:
        return uri.split("#")[-1]
    if "/" in uri:
        return uri.split("/")[-1]
    return uri


def _extract_predicate_name(uri: str) -> str:
    """URI에서 프레디케이트 이름 추출"""
    return _extract_entity_name(uri)


def render_debug_info(agent_result: Dict, core, situation_analysis: Dict, score_breakdown: Dict):
    """디버깅 정보 표시"""
    st.write("**Agent 실행 결과 구조:**")
    
    debug_data = {
        "situation_analysis 존재": situation_analysis is not None and len(situation_analysis) > 0,
        "situation_analysis 키": list(situation_analysis.keys()) if situation_analysis else [],
        "score_breakdown 존재": score_breakdown is not None and len(score_breakdown) > 0,
        "score_breakdown 키": list(score_breakdown.keys()) if score_breakdown else [],
        "palantir_mode": agent_result.get("palantir_mode", False),
    }
    
    if core:
        debug_data.update({
            "RAG 매니저 사용 가능": core.rag_manager.is_available() if hasattr(core, 'rag_manager') else "N/A",
            "임베딩 모델 로드": core.rag_manager.embedding_model is not None if hasattr(core, 'rag_manager') else "N/A",
            "온톨로지 그래프 존재": core.ontology_manager.graph is not None if hasattr(core, 'ontology_manager') else "N/A",
        })
        if hasattr(core, 'ontology_manager') and core.ontology_manager.graph:
            triples_count = len(list(core.ontology_manager.graph.triples((None, None, None))))
            debug_data["온톨로지 Triples 수"] = triples_count
    
    st.json(debug_data)
    
    # 상세 정보
    st.markdown("---")
    st.write("**상황 분석 상세:**")
    if situation_analysis:
        st.json({
            "rag_results 개수": len(situation_analysis.get("rag_results", [])),
            "related_entities 개수": len(situation_analysis.get("related_entities", [])),
            "chain_info 존재": situation_analysis.get("chain_info") is not None,
            "chain_info chains 개수": len(situation_analysis.get("chain_info", {}).get("chains", [])) if situation_analysis.get("chain_info") else 0,
        })
    else:
        st.warning("situation_analysis가 비어있습니다.")


def _get_usage_reason(item: str, is_used: bool, situation_analysis: Dict, agent_result: Dict, core) -> str:
    """항목별 사용 여부 원인 반환"""
    if is_used:
        return "정상 사용 중"
    
    if item == "RAG 검색":
        if not core:
            return "Core 정보 없음"
        if not hasattr(core, 'rag_manager'):
            return "RAG 매니저 없음"
        if not core.rag_manager.is_available():
            return "RAG 매니저 미사용"
        if not core.rag_manager.embedding_model:
            return "임베딩 모델 미로드"
        return "RAG 검색 미수행"
    
    elif item == "관계 체인":
        palantir_mode = agent_result.get("palantir_mode", False)
        if not palantir_mode:
            return "팔란티어 모드 미활성화"
        chain_info = situation_analysis.get("chain_info", {})
        if not chain_info:
            return "체인 정보 미생성"
        return "체인 미발견"
    
    elif item == "관련 엔티티":
        if not core:
            return "Core 정보 없음"
        if not hasattr(core, 'ontology_manager'):
            return "온톨로지 매니저 없음"
        if not core.ontology_manager.graph:
            return "온톨로지 그래프 없음"
        return "관련 엔티티 미탐색"
    
    elif item == "자원 매칭":
        palantir_mode = agent_result.get("palantir_mode", False)
        if not palantir_mode:
            return "팔란티어 모드 필요"
        resource_info = situation_analysis.get("resource_info", {})
        if resource_info:
            return f"자원 정보 조회됨 (점수: {resource_info.get('score', 0):.3f})"
        return "자원 정보 미조회"
    
    elif item == "환경 호환성":
        palantir_mode = agent_result.get("palantir_mode", False)
        if not palantir_mode:
            return "팔란티어 모드 필요"
        environment_info = situation_analysis.get("environment_info", {})
        if environment_info:
            return f"환경 정보 조회됨 (점수: {environment_info.get('score', 0):.3f})"
        return "환경 정보 미조회"
    
    return "알 수 없음"


def _get_solution_for_item(item: str, core, agent_result: Dict) -> str:
    """항목별 해결 방법 반환"""
    if item == "RAG 검색":
        if not core or not hasattr(core, 'rag_manager'):
            return "시스템 초기화 문제입니다. 시스템을 재시작하세요."
        if not core.rag_manager.is_available():
            return """
            **RAG 매니저가 사용 불가능합니다.**
            
            1. RAG 인덱스 구축 확인:
               - "4단계: RAG 인덱스 구성" 페이지로 이동
               - 문서를 업로드하고 인덱스를 구축하세요
            
            2. 임베딩 모델 확인:
               - 임베딩 모델이 로드되었는지 확인
               - 모델 로드 오류가 있는지 확인
            """
        return """
        **RAG 검색이 수행되지 않았습니다.**
        
        - Agent 실행 시 `enable_rag_search=True` 또는 `use_embedding=True`로 설정되어 있는지 확인
        - RAG 인덱스가 구축되어 있는지 확인
        """
    
    elif item == "관계 체인":
        return """
        **관계 체인을 사용하려면:**
        
        1. 팔란티어 모드 활성화:
           - "상황 입력 및 추천" 탭 또는 "Agent 실행" 페이지에서
           - "팔란티어 모드" 체크박스를 선택하세요
        
        2. Agent 재실행:
           - 팔란티어 모드가 활성화된 상태에서 Agent를 다시 실행하세요
        
        3. 온톨로지 그래프 확인:
           - 온톨로지 그래프가 구축되어 있어야 합니다
           - 관계 정보가 온톨로지에 포함되어 있어야 합니다
        """
    
    elif item == "관련 엔티티":
        if not core or not hasattr(core, 'ontology_manager'):
            return "시스템 초기화 문제입니다. 시스템을 재시작하세요."
        if not core.ontology_manager.graph:
            return """
            **온톨로지 그래프가 없습니다.**
            
            1. 데이터 로드:
               - Excel 데이터 파일이 `data_lake/` 폴더에 있는지 확인
            
            2. 온톨로지 구축:
               - Agent를 실행하면 자동으로 온톨로지 그래프가 구축됩니다
               - 또는 "3단계: 지식그래프 조회" 페이지에서 그래프 생성 버튼 클릭
            """
        return """
        **관련 엔티티 탐색이 수행되지 않았습니다.**
        
        - Agent 실행 시 `use_reasoned_graph=True`로 설정되어 있는지 확인
        - 온톨로지 그래프에 관련 엔티티 정보가 있는지 확인
        """
    
    elif item == "자원 매칭":
        return """
        **자원 매칭을 사용하려면:**
        
        1. 팔란티어 모드 활성화:
           - 팔란티어 모드에서만 자원 매칭 점수가 계산됩니다
        
        2. 온톨로지 관계 확인:
           - COA-자원 관계가 온톨로지에 포함되어 있어야 합니다
           - FK 기반 관계가 테이블정의서에 정의되어 있어야 합니다
        """
    
    elif item == "환경 호환성":
        return """
        **환경 호환성을 사용하려면:**
        
        1. 팔란티어 모드 활성화:
           - 팔란티어 모드에서만 환경 적합성 점수가 계산됩니다
        
        2. 온톨로지 관계 확인:
           - 기상-위협 관계가 온톨로지에 포함되어 있어야 합니다
           - FK 기반 관계가 테이블정의서에 정의되어 있어야 합니다
        """
    
    return "해결 방법을 확인할 수 없습니다."

