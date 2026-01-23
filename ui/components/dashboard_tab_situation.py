# ui/components/dashboard_tab_situation.py
# -*- coding: utf-8 -*-
"""
탭 1: 상황 입력 및 추천 (Quick COA Recommendation)
빠른 방책 추천을 위한 자동 추론 방식
"""
import streamlit as st
from ui.components.situation_input import render_situation_input, render_situation_summary
from ui.components.agent_selector import render_agent_selector
from ui.components.recommendation_visualization import render_recommendation_breakdown
from ui.components.reasoning_explanation import render_reasoning_explanation
from ui.components.coa_execution_plan import render_coa_execution_plan
from ui.components.user_friendly_errors import render_user_friendly_error


def render_situation_tab(orchestrator, agents_list):
    """탭 1: 상황 입력 및 추천 (Quick COA)"""
    
    st.header("📋 상황 입력 및 추천")
    st.markdown("**빠른 방책 추천**: 상황 입력 후 자동으로 방책을 추천합니다.")
    st.info("💡 **LLM 질문 및 상세 상호작용**이 필요하시면 **5단계: Agent 실행** 페이지를 이용하세요.")
    
    # 상황 입력 (항상 표시)
    situation_info = render_situation_input(orchestrator, use_real_data=True)
    
    if situation_info:
        render_situation_summary(situation_info)
        
        st.divider()
        
        # Agent 선택
        selected_agent = render_agent_selector(agents_list)
        
        # 자동 Agent 실행 (상황 정보가 있고 Agent가 선택된 경우)
        if selected_agent and ("coa" in selected_agent.lower() and "recommendation" in selected_agent.lower()):
            st.divider()
            
            # 자동 실행 버튼
            auto_execute_key = "auto_execute_agent_dashboard"
            if auto_execute_key not in st.session_state:
                st.session_state[auto_execute_key] = False
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### 🤖 Agent 실행")
                st.caption("선택한 상황 정보로 방책을 자동 추천합니다.")
            with col2:
                if st.button("🚀 방책 추천 실행", type="primary", key="execute_auto_recommendation"):
                    st.session_state[auto_execute_key] = True
                    st.rerun()
            
            # 자동 실행 수행
            if st.session_state.get(auto_execute_key, False):
                with st.spinner("방책 추천 중... (온톨로지 분석 + RAG 검색 + 추론)"):
                    try:
                        # Agent 로드 및 실행
                        agent_info = next(
                            (a for a in agents_list if a.get("name") == selected_agent),
                            None
                        )
                        
                        if agent_info:
                            cls_path = agent_info.get("class")
                            if cls_path:
                                AgentClass = orchestrator.load_agent_class(cls_path)
                                agent = AgentClass(core=orchestrator.core)
                                
                                # 팔란티어 모드 설정
                                use_palantir_mode = st.session_state.get("use_palantir_mode", True)
                                enable_rag_search = True
                                
                                # 상황 정보에서 ID 추출
                                situation_id = situation_info.get("situation_id") or situation_info.get("위협ID") or situation_info.get("임무ID")
                                
                                # Agent 실행 (자동 추론, LLM 질문 없음)
                                agent_result = agent.execute_reasoning(
                                    situation_id=situation_id,
                                    user_query="방책을 추천해주세요",  # 기본 질문
                                    selected_situation_info=situation_info,
                                    use_palantir_mode=use_palantir_mode,
                                    enable_rag_search=enable_rag_search
                                )
                                
                                if agent_result:
                                    # 결과를 session_state에 저장
                                    st.session_state["dashboard_agent_result"] = agent_result
                                    st.session_state["dashboard_situation_info"] = situation_info
                                    st.session_state[auto_execute_key] = False  # 실행 완료
                                    st.success("✅ 방책 추천 완료!")
                                    st.rerun()
                            else:
                                st.error("Agent 클래스 경로가 설정되지 않았습니다.")
                        else:
                            st.error(f"Agent '{selected_agent}'를 찾을 수 없습니다.")
                    except Exception as e:
                        render_user_friendly_error(e, "Agent 실행")
                        st.session_state[auto_execute_key] = False
            
            # 추천 결과 표시
            agent_result = st.session_state.get("dashboard_agent_result")
            if agent_result:
                recommendations = agent_result.get("recommendations", [])
                
                if recommendations:
                    st.divider()
                    st.subheader("✅ 추천 결과 요약")
                    
                    # LLM-Agent 협력 정보 표시 (새로 추가)
                    llm_collab = agent_result.get("llm_collaboration", {})
                    if llm_collab:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "협력 모드",
                                "활성화" if llm_collab.get("situation_analysis_used") or llm_collab.get("strategy_evaluation_used") else "비활성화"
                            )
                        with col2:
                            st.metric(
                                "LLM 참여",
                                f"{sum([llm_collab.get('situation_analysis_used', False), llm_collab.get('strategy_evaluation_used', False)])}/2 단계"
                            )
                        with col3:
                            insights_count = len(llm_collab.get("llm_insights", {}).get("key_factors", []))
                            st.metric("LLM 인사이트", f"{insights_count}개")
                        st.divider()
                    
                    # 상위 3개 방책 표시
                    for i, rec in enumerate(recommendations[:3], 1):
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                coa_name = rec.get('coa_name') or rec.get('명칭') or rec.get('방책명') or f'방책 {i}'
                                st.markdown(f"**{i}. {coa_name}**")
                                description = rec.get('description') or rec.get('설명') or rec.get('방책설명') or ''
                                if description:
                                    st.caption(description[:100] + '...' if len(description) > 100 else description)
                                
                                # 점수 구성 표시 (LLM 협력 시)
                                score_breakdown = rec.get("score_breakdown", {})
                                if score_breakdown and (score_breakdown.get('agent_score') is not None or score_breakdown.get('llm_score') is not None):
                                    with st.expander("점수 구성", expanded=False):
                                        agent_score = score_breakdown.get('agent_score', 0)
                                        llm_score = score_breakdown.get('llm_score', 0)
                                        st.write(f"- Agent 점수: {agent_score:.3f} (70%)")
                                        st.write(f"- LLM 점수: {llm_score:.3f} (30%)")
                                        st.write(f"- 통합 점수: {score_breakdown.get('hybrid_score', 0):.3f}")
                            with col2:
                                score = rec.get('score') or rec.get('최종점수') or rec.get('MAUT점수') or 0
                                st.metric("적합도", f"{score:.2f}")
                                
                                # METT-C 점수 배지 (있는 경우)
                                score_breakdown = rec.get("score_breakdown", {})
                                mett_c_scores = score_breakdown.get("mett_c") or rec.get("mett_c")
                                if mett_c_scores:
                                    mett_c_total = mett_c_scores.get("total", 0)
                                    civilian_score = mett_c_scores.get("civilian", 1.0)
                                    time_score = mett_c_scores.get("time", 1.0)
                                    
                                    # METT-C 종합 점수
                                    st.caption(f"METT-C: {mett_c_total:.2f}")
                                    
                                    # 민간인/시간 경고
                                    if civilian_score < 0.3:
                                        st.warning("⚠️ 민간인 보호 낮음", icon="🏘️")
                                    elif civilian_score < 0.5:
                                        st.caption(f"민간인: {civilian_score:.2f}")
                                    
                                    if time_score == 0.0:
                                        st.error("❌ 시간 위반", icon="⏰")
                                    elif time_score < 0.5:
                                        st.caption(f"시간: {time_score:.2f}")
                                    
                                    # 상세 정보는 확장 가능한 섹션에
                                    with st.expander("METT-C 상세", expanded=False):
                                        st.markdown("**METT-C 요소별 점수:**")
                                        mett_c_elements = {
                                            "mission": "🎯 임무",
                                            "enemy": "⚠️ 적군",
                                            "terrain": "🌍 지형",
                                            "troops": "👥 부대",
                                            "civilian": "🏘️ 민간인",
                                            "time": "⏰ 시간"
                                        }
                                        for key, label in mett_c_elements.items():
                                            element_score = mett_c_scores.get(key, 0)
                                            st.write(f"{label}: {element_score:.3f}")
                            st.divider()
                    
                    # 상세 분석은 탭2로 이동 안내
                    st.info("💡 **추천 근거 상세 분석**은 **탭 2: 추천 근거 분석**에서 확인하세요.")
                else:
                    st.warning("추천된 방책이 없습니다.")
        elif selected_agent:
            st.info(f"💡 '{selected_agent}' Agent는 방책 추천 기능을 지원하지 않습니다. **5단계: Agent 실행** 페이지에서 사용하세요.")
        else:
            st.info("💡 방책 추천을 위해 Agent를 선택해주세요.")
    else:
        st.info("💡 상황 정보를 입력해주세요. (위협 중심 또는 임무 중심)")

