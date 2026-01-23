# ui/components/chat_interface_v2.py
# -*- coding: utf-8 -*-
"""
채팅 인터페이스 v2 (인용 모드)
LLM 응답에 RAG 검색 결과 근거를 표시
"""
import streamlit as st
import json
from datetime import datetime
from ui.components.citation_panel import render_citation_panel, highlight_citations_in_text, render_citation_summary
from ui.components.user_friendly_errors import render_user_friendly_error


def render_chat_interface(orchestrator, selected_agent, agents_list, coa_type_filter=None):
    """채팅 인터페이스 v2 (인용 모드)"""
    st.subheader("LLM 실시간 상호작용 (인용 모드)")
    
    # 모델 선택 UI 추가 (프롬프트 입력창 위에 배치)
    from ui.components.llm_model_selector import render_llm_model_selector
    selected_model_key = render_llm_model_selector(orchestrator.core.llm_manager, key_prefix="chat_")
    
    # 전역 세션 상태에 저장 (대시보드와 동기화)
    st.session_state["selected_llm_manager"] = selected_model_key
    
    st.divider()
    
    # 인용 모드 설명
    st.info("참고: 인용 모드: LLM 응답에 참고 문서 근거 번호가 자동으로 포함됩니다.")
    
    # 메시지 히스토리 초기화
    if "messages_v2" not in st.session_state:
        st.session_state.messages_v2 = []
    
    if "citations_v2" not in st.session_state:
        st.session_state.citations_v2 = {}
    
    # 이전 메시지 표시
    for msg in st.session_state.messages_v2:
        with st.chat_message(msg["role"]):
            # 인용 번호 하이라이트
            if msg["role"] == "assistant" and "citations" in msg:
                # 인용 번호가 포함된 텍스트 하이라이트
                highlighted_content = highlight_citations_in_text(msg["content"])
                st.markdown(highlighted_content, unsafe_allow_html=True)
            else:
                st.write(msg["content"])
            
            if "timestamp" in msg:
                st.caption(msg["timestamp"])
            
            # 근거 표시 (어시스턴트 메시지인 경우)
            if msg["role"] == "assistant" and "citations" in msg and msg["citations"]:
                with st.expander("📚 참고 문서 근거", expanded=False):
                    render_citation_panel(msg["citations"], highlight_query=msg.get("query", ""))
            
            # 🔥 NEW: 진행 상황 로그 표시 (영구 보관)
            if msg["role"] == "assistant" and "metadata" in msg and "progress_logs" in msg["metadata"]:
                logs = msg["metadata"]["progress_logs"]
                if logs:
                    with st.status("✅ 분석 완료 (100%)", state="complete", expanded=False):
                        for log in logs:
                            st.write(log)
    
    # 사용자 입력
    user_prompt = st.chat_input("질문을 입력하세요 (예: 적군 위협 상황 근거 포함 요약)")
    
    if user_prompt:
        # 사용자 메시지 추가
        user_msg = {
            "role": "user",
            "content": user_prompt,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.messages_v2.append(user_msg)
        
        # 사용자 메시지 화면에 표시
        with st.chat_message("user"):
            st.write(user_prompt)
            st.caption(user_msg["timestamp"])
        
        # 응답 생성
        with st.chat_message("assistant"):
            with st.status("처리 중...", expanded=False) as status:
                try:
                    # 진행 상황 데이터를 저장할 리스트 (메시지 메타데이터에 저장 예정)
                    progress_logs = []
                    
                    # 1. RAG 검색 (근거 문서 검색)
                    label = "지식 데이터베이스 검색 중..."
                    status.update(label=label)
                    progress_logs.append(f"  - {label}")
                    
                    retrieved = []
                    if orchestrator.core.rag_manager.embedding_model is not None:
                        try:
                            retrieved = orchestrator.core.rag_manager.retrieve_with_context(
                                user_prompt, top_k=3
                            )
                        except Exception as e:
                            render_user_friendly_error(e, "RAG 검색")
                    
                    # 2. Agent 실행 (선택된 경우)
                    agent_result = None
                    if selected_agent:
                        label = f"에이전트 분석 중: {selected_agent}"
                        status.update(label=label)
                        progress_logs.append(f"  - {label}")
                        
                        try:
                            agent_info = next(
                                (a for a in agents_list if a.get("name") == selected_agent),
                                None
                            )
                            if agent_info:
                                cls_path = agent_info.get("class")
                                if cls_path:
                                    AgentClass = orchestrator.load_agent_class(cls_path)
                                    agent = AgentClass(core=orchestrator.core)
                                    
                                    # 진행 상황 콜백 함수 정의 (퍼센트 지원)
                                    def on_status_update(msg, progress=None):
                                        log_entry = f"  - {msg}"
                                        if progress is not None:
                                            log_entry = f"  - [{progress}%] {msg}"
                                            curr_label = f"분석 중: {progress}% - {msg}"
                                        else:
                                            curr_label = f"분석 중: {msg}"
                                        
                                        st.write(log_entry)
                                        status.update(label=curr_label)
                                        progress_logs.append(log_entry)

                                    # 팔란티어 모드 설정 가져오기 (여러 키 확인, 기본값 True)
                                    use_palantir_mode = (
                                        st.session_state.get("use_palantir_mode", True) or
                                        st.session_state.get("dashboard_use_palantir_mode", False) or
                                        st.session_state.get("agent_page_use_palantir_mode", False)
                                    )
                                    # RAG 검색은 항상 활성화 (팔란티어 모드에서 과거 성공률 계산 및 LLM 컨텍스트로 사용)
                                    enable_rag_search = True
                                    
                                    # 선택한 위협상황 정보 가져오기
                                    # 레거시 호환: demo_scenario_data도 확인
                                    selected_situation_info = st.session_state.get("selected_situation_info") or st.session_state.get("demo_scenario_data")
                                    situation_id = None
                                    if selected_situation_info:
                                        # situation_id 우선, 없으면 위협ID 사용
                                        situation_id = selected_situation_info.get("situation_id") or selected_situation_info.get("위협ID")
                                    
                                    agent_result = agent.execute_reasoning(
                                        situation_id=situation_id,  # 선택한 위협상황의 situation_id 전달
                                        user_query=user_prompt,  # 사용자 질문 전달
                                        selected_situation_info=selected_situation_info,  # ✅ 추가: 선택한 위협상황 정보 직접 전달
                                        use_palantir_mode=use_palantir_mode,
                                        enable_rag_search=enable_rag_search,
                                        coa_type_filter=coa_type_filter,  # ✅ 추가: 방책 유형 필터 전달
                                        status_callback=on_status_update
                                    )
                                    
                                    # ... (중략 - 이후 텍스트 구성 로직)
                                    status.update(label="에이전트 분석 완료 (100%)", state="complete")
                                    progress_logs.append("  - 에이전트 분석 완료")
                                    
                                    # Agent 결과를 컨텍스트에 추가 (LLM이 자연스럽게 답변할 수 있도록 원본 데이터 제공)
                                    # agent_result가 없거나 실패한 경우에도 selected_situation_info 사용
                                    if agent_result or selected_situation_info:
                                        import json
                                        # Agent 결과에서 situation_info 가져오기 (없으면 selected_situation_info 사용)
                                        situation_info = agent_result.get("situation_info", {}) if agent_result else {}
                                        if not situation_info and selected_situation_info:
                                            situation_info = selected_situation_info
                                        
                                        recommendations = agent_result.get("recommendations", []) if agent_result else []
                                        
                                        # 상황 정보를 읽기 쉬운 형태로 구성
                                        # ... (생략된 경우 툴에서 원본을 유지하지 않으므로 주의해서 작성)
                                        # 여기서는 원본 코드를 그대로 활용하여 context logic만 status 바깥으로 뺌
                                        # 또는 spinner 내부에 둠.
                                        status.update(label="LLM 답변 생성 중...")
                                        progress_logs.append("  - LLM 답변 생성 중...")
                                        if situation_info:
                                            situation_text = "=== 선택한 위협상황 정보 ===\n"
                                            situation_text += f"위협 ID: {situation_info.get('위협ID', situation_info.get('ID', situation_info.get('situation_id', 'N/A')))}\n"
                                            # 위협 유형 추출 (여러 필드명 지원)
                                            threat_type = (situation_info.get('위협유형') or 
                                                          situation_info.get('threat_type') or 
                                                          'N/A')
                                            situation_text += f"위협 유형: {threat_type}\n"
                                            # 심각도 및 위협수준 추출 (여러 필드명 지원)
                                            severity = (situation_info.get('심각도') or 
                                                       situation_info.get('위협수준'))
                                            threat_level = situation_info.get('threat_level')
                                            
                                            if severity is None:
                                                # threat_level이 있으면 변환
                                                if threat_level is not None:
                                                    severity = int(float(threat_level) * 100)
                                            
                                            if threat_level is None:
                                                # severity가 있으면 threat_level로 변환
                                                if severity is not None:
                                                    try:
                                                        severity_float = float(severity)
                                                        threat_level = severity_float / 100.0 if severity_float > 1.0 else severity_float
                                                    except:
                                                        pass
                                            
                                            situation_text += f"심각도: {severity if severity is not None else 'N/A'}\n"
                                            # 위협수준도 명시적으로 표시 (강조) - 여러 번 반복하여 강조
                                            if threat_level is not None:
                                                threat_level_pct = int(float(threat_level) * 100)
                                                if threat_level >= 0.95:
                                                    threat_level_desc = "매우 높음 (최고 위협)"
                                                    threat_level_warning = "⚠️⚠️⚠️ 매우 높은 위협: 강력한 방어 방책(Main_Defense) 필수"
                                                elif threat_level > 0.8:
                                                    threat_level_desc = "높음"
                                                    threat_level_warning = "⚠️⚠️ 높은 위협: 강력한 방어 방책(Main_Defense) 권장"
                                                elif threat_level > 0.5:
                                                    threat_level_desc = "보통"
                                                    threat_level_warning = "ℹ️ 보통 위협: 중간 방어 방책(Moderate_Defense) 적합"
                                                elif threat_level > 0.3:
                                                    threat_level_desc = "낮음"
                                                    threat_level_warning = "ℹ️ 낮은 위협: 최소 방어 방책(Minimal_Defense) 적합"
                                                else:
                                                    threat_level_desc = "매우 낮음"
                                                    threat_level_warning = "ℹ️ 매우 낮은 위협: 최소 방어 방책(Minimal_Defense) 충분"
                                                # 위협수준을 여러 번 강조
                                                situation_text += f"\n🔴 **위협수준: {threat_level_pct}%** ({threat_level_desc})\n"
                                                situation_text += f"🔴 **위협수준: {threat_level_pct}%** ({threat_level_desc})\n"
                                                situation_text += f"{threat_level_warning}\n"
                                                situation_text += f"\n**중요**: 위협수준은 {threat_level_pct}%입니다. 이 값을 정확히 반영하세요.\n"
                                            location = situation_info.get('발생장소', situation_info.get('장소', 'N/A'))
                                            if location and location != 'N/A':
                                                situation_text += f"발생 장소: {location}\n"
                                            if situation_info.get('탐지시각'):
                                                situation_text += f"탐지 시각: {situation_info.get('탐지시각')}\n"
                                            if situation_info.get('근거'):
                                                situation_text += f"근거: {situation_info.get('근거')}\n"
                                            situation_text += "\n"
                                        
                                        # 추천 방책을 읽기 쉬운 형태로 구성
                                        recommendations_text = ""
                                        if recommendations:
                                            recommendations_text = "=== 추천 방책 (점수 순위) ===\n"
                                            for i, rec in enumerate(recommendations[:5], 1):  # 상위 5개만
                                                coa_name = rec.get('coa_name', 'N/A')
                                                score = rec.get('score', 0)
                                                reason = rec.get('reason', 'N/A')
                                                score_breakdown = rec.get('score_breakdown', {})
                                                
                                                # 방책 유형 판단
                                                coa_type = ""
                                                if 'main' in coa_name.lower() or '주요' in coa_name.lower() or '강력' in coa_name.lower():
                                                    coa_type = " [강력한 방책]"
                                                elif 'moderate' in coa_name.lower() or '중간' in coa_name.lower():
                                                    coa_type = " [중간 방책]"
                                                elif 'minimal' in coa_name.lower() or '최소' in coa_name.lower():
                                                    coa_type = " [최소 방책]"
                                                
                                                recommendations_text += f"{i}. {coa_name}{coa_type} (종합 점수: {score:.3f})\n"
                                                if score_breakdown:
                                                    threat_score = score_breakdown.get('threat', 0)
                                                    recommendations_text += f"   - 위협 점수: {threat_score:.3f}\n"
                                                if reason and reason != 'N/A':
                                                    recommendations_text += f"   - 추천 사유: {reason}\n"
                                            recommendations_text += "\n"
                                        
                                        # 전체 Agent 결과를 JSON으로도 포함 (상세 정보용)
                                        agent_data = {
                                            "situation_info": situation_info,
                                            "recommendations": recommendations,
                                            "status": agent_result.get("status", ""),
                                            "situation_id": agent_result.get("situation_id")
                                        }
                                        
                                        # 구조화된 텍스트 + JSON 형태로 전달
                                        # 위협수준을 명확하게 강조
                                        threat_level_emphasis = ""
                                        if threat_level is not None:
                                            threat_level_pct = int(float(threat_level) * 100)
                                            threat_level_emphasis = f"\n\n🔴 **중요**: 현재 위협수준은 {threat_level_pct}%입니다. "
                                            if threat_level >= 0.95:
                                                threat_level_emphasis += "매우 높은 위협이므로 반드시 Main_Defense 방책을 추천해야 합니다."
                                            elif threat_level > 0.8:
                                                threat_level_emphasis += "높은 위협이므로 Main_Defense 방책을 우선 추천해야 합니다."
                                            elif threat_level > 0.5:
                                                threat_level_emphasis += "보통 위협이므로 Moderate_Defense 방책이 적합합니다."
                                            else:
                                                threat_level_emphasis += "낮은 위협이므로 Minimal_Defense 방책으로 충분합니다."
                                        
                                        agent_result_text = f"""[Agent 실행 결과 데이터]

{situation_text}{threat_level_emphasis}{recommendations_text}
[상세 데이터 (JSON)]
{json.dumps(agent_data, ensure_ascii=False, indent=2)}"""
                                        
                                        retrieved.append({
                                            "doc_id": -1,
                                            "text": agent_result_text,
                                            "score": 1.0,
                                            "index": -1,
                                            "metadata": {"source": "agent", "agent_result": agent_result}
                                        })
                        except Exception as e:
                            render_user_friendly_error(e, "Agent 실행")
                    
                    # 3. LLM 응답 생성 (인용 포함)
                    llm_reply = None
                    if orchestrator.core.llm_manager.is_available():
                        try:
                            if retrieved:
                                # 인용 모드로 생성
                                llm_reply = orchestrator.core.llm_manager.generate_with_citations(
                                    user_prompt, retrieved, max_tokens=512
                                )
                            else:
                                # 근거 없이 기본 생성
                                llm_reply = orchestrator.core.llm_manager.generate(
                                    user_prompt, max_tokens=512
                                )
                        except Exception as e:
                            render_user_friendly_error(e, "LLM 응답 생성")
                            llm_reply = "[LLM 응답 생성에 실패했습니다. Agent 결과만 표시합니다.]"
                    else:
                        # LLM이 없으면 Agent 결과만 표시
                        if agent_result:
                            llm_reply = agent_result.get("summary", "Agent 실행 완료")
                        else:
                            llm_reply = "[LLM 모델이 로드되지 않았습니다.]"
                    
                    # 4. 응답 표시 (인용 번호 하이라이트)
                    highlighted_reply = highlight_citations_in_text(llm_reply)
                    st.markdown(highlighted_reply, unsafe_allow_html=True)
                    
                    # 5. 근거 패널 표시
                    if retrieved:
                        st.divider()
                        render_citation_panel(retrieved, highlight_query=user_prompt)
                        
                        # 근거 요약 (간단 버전)
                        with st.expander("📋 근거 요약", expanded=False):
                            render_citation_summary(retrieved)
                    
                    # 6. 상세 정보
                    with st.expander("📋 상세 정보", expanded=False):
                        if agent_result:
                            st.markdown("**Agent 실행 결과:**")
                            st.json(agent_result)
                        
                        st.markdown("**RAG 검색 결과:**")
                        st.json({
                            "query": user_prompt,
                            "results_count": len(retrieved),
                            "results": retrieved
                        })
                    
                    # 어시스턴트 메시지 추가
                    assistant_msg = {
                        "role": "assistant",
                        "content": llm_reply,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "citations": retrieved,
                        "query": user_prompt,
                        "metadata": {
                            "agent_result": agent_result if agent_result else None,
                            "progress_logs": progress_logs # 🔥 추가: 진행 상황 로그 저장
                        }
                    }
                    st.session_state.messages_v2.append(assistant_msg)
                    
                    # 인용 정보 저장
                    st.session_state.citations_v2[len(st.session_state.messages_v2) - 1] = retrieved
                    
                    # LLM-Agent 협력 정보 표시 (새로 추가)
                    if agent_result:
                        llm_collab = agent_result.get("llm_collaboration", {})
                        if llm_collab:
                            st.divider()
                            with st.expander("🤝 LLM-Agent 협력 정보", expanded=False):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**상황 분석**:", "✅ 사용" if llm_collab.get("situation_analysis_used") else "❌ 미사용")
                                    st.write("**방책 평가**:", "✅ 사용" if llm_collab.get("strategy_evaluation_used") else "❌ 미사용")
                                with col2:
                                    insights = llm_collab.get("llm_insights", {})
                                    st.write("**주요 고려사항**:", len(insights.get("key_factors", [])))
                                    st.write("**제약조건**:", len(insights.get("constraints", [])))
                    
                except Exception as e:
                    render_user_friendly_error(e, "채팅 인터페이스")
                    error_msg = "오류가 발생했습니다. 위의 해결 방법을 참고하세요."
                    st.session_state.messages_v2.append({
                        "role": "assistant",
                        "content": error_msg,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
    
    # 채팅 히스토리 관리
    if st.session_state.messages_v2:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ 대화 기록 삭제"):
                st.session_state.messages_v2 = []
                st.session_state.citations_v2 = {}
                st.rerun()
        with col2:
            st.caption(f"총 {len(st.session_state.messages_v2)}개 메시지")
        with col3:
            citation_count = sum(len(c) for c in st.session_state.citations_v2.values())
            st.caption(f"총 {citation_count}개 근거 문서")

