# ui/components/palantir_mode_toggle.py
# -*- coding: utf-8 -*-
"""
팔란티어 모드 토글 컴포넌트
"""
import streamlit as st


def render_palantir_mode_toggle(show_details: bool = True, key_prefix: str = ""):
    """
    팔란티어 모드 토글 UI 렌더링
    
    Args:
        show_details: 상세 설명 표시 여부
        key_prefix: key에 사용할 접두사 (중복 방지용, 예: "settings_", "agent_page_")
    
    Returns:
        (use_palantir_mode, enable_rag_search) 튜플
        enable_rag_search는 항상 True (RAG 검색은 항상 활성화)
    """
    st.subheader("추론 모드 설정")
    
    # key_prefix가 있으면 사용, 없으면 기본값 사용
    checkbox_key = f"{key_prefix}use_palantir_mode" if key_prefix else "palantir_mode_toggle"
    
    use_palantir = st.checkbox(
        "팔란티어 모드 활성화",
        value=st.session_state.get("use_palantir_mode", True),  # 기본값 True
        key=checkbox_key,
        help="""모드 선택 가이드:

[OFF] 체크 안 함 (기본 모드):
• 위협 수준만으로 단순 평가 (빠른 추천)
• 위협 수준에 따라 Main/Moderate/Minimal 방책 자동 선택
• RAG 검색은 LLM 컨텍스트로만 활용

[ON] 체크 함 (팔란티어 모드):
• 6개 요소 종합 평가 (위협/자원/자산/환경/과거/체인)
• SPARQL 쿼리로 그래프 관계 분석
• RAG 검색으로 과거 성공률 계산 + LLM 컨텍스트
• 다단계 관계 체인 탐색으로 더 정확한 추천
• 각 요소별 점수 breakdown 제공"""
    )
    
    # RAG 검색은 항상 활성화 (팔란티어 모드에서 과거 성공률 계산 및 LLM 컨텍스트로 사용)
    st.info("참고: RAG 검색은 항상 활성화됩니다 (과거 사례 활용 및 LLM 컨텍스트 제공)")
    
    if show_details and use_palantir:
        with st.expander("팔란티어 모드 상세 정보", expanded=False):
            st.markdown("""
            **팔란티어 모드 특징:**
            
            ### 점수 계산 요소 (6개)
            1. **위협 수준** (25%): 그래프에서 추출 또는 사용자 입력
            2. **자원 가용성** (20%): SPARQL 템플릿으로 필요/가용 자원 비교
            3. **방어 자산 능력** (20%): 그래프에서 아군 Firepower/Morale 평균
            4. **환경 적합성** (15%): SPARQL 템플릿으로 환경 호환성 확인
            5. **과거 성공률** (10%): RAG 검색 결과에서 성공 키워드 비율
            6. **체인 점수** (10%): 위협 엔티티 → COA 체인 탐색 점수
            
            ### 고급 기능
            - **다단계 관계 체인 탐색**: 간접 관계를 통한 COA 추천
            - **RAG + 그래프 하이브리드**: 문서 검색과 그래프 관계 통합 (RAG 검색 자동 활용)
            - **의미 기반 관계 추론**: 키워드 유사도 기반 관계 발견
            - **점수 상세 정보**: 각 요소별 점수 breakdown 제공
            
            ### 기본 모드와의 차이
            - **기본 모드**: 위협 수준만으로 결정 (단순 3단계 분류), RAG는 LLM 컨텍스트로만 사용
            - **팔란티어 모드**: 6개 요소 종합 평가 (현실적이고 정확한 추천), RAG는 과거 성공률 계산 및 LLM 컨텍스트로 활용
            """)
            
            # 점수 breakdown 예시
            st.markdown("""
            **점수 Breakdown 예시:**
            ```
            총점: 0.85
            - 위협: 0.80 (25%)
            - 자원: 0.75 (20%)
            - 자산: 0.90 (20%)
            - 환경: 1.00 (15%)
            - 과거: 0.60 (10%)
            - 체인: 0.70 (10%)
            ```
            """)
    
    # RAG 검색은 항상 활성화 (팔란티어 모드에서 과거 성공률 계산 및 LLM 컨텍스트로 사용)
    return use_palantir, True


def render_palantir_result_info(result: dict):
    """
    팔란티어 모드 결과 정보 표시
    
    Args:
        result: Agent 실행 결과 딕셔너리
    """
    if not result.get("palantir_mode", False):
        return
    
    raw_result = result.get("raw_result", {})
    
    if raw_result.get("PalantirMode"):
        st.divider()
        st.subheader("팔란티어 모드 결과")
        
        # 총점 표시
        total_score = raw_result.get("TotalScore", 0)
        st.metric("종합 점수", f"{total_score:.3f}")
        
        # 점수 breakdown
        score_breakdown = raw_result.get("ScoreBreakdown", {})
        if score_breakdown:
            st.markdown("#### 점수 상세 (Breakdown)")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("위협", f"{score_breakdown.get('threat', 0):.3f}", 
                         help="위협 수준 점수 (25%)")
                st.metric("자원", f"{score_breakdown.get('resources', 0):.3f}",
                         help="자원 가용성 점수 (20%)")
            
            with col2:
                st.metric("자산", f"{score_breakdown.get('assets', 0):.3f}",
                         help="방어 자산 능력 점수 (20%)")
                st.metric("환경", f"{score_breakdown.get('environment', 0):.3f}",
                         help="환경 적합성 점수 (15%)")
            
            with col3:
                st.metric("과거", f"{score_breakdown.get('historical', 0):.3f}",
                         help="과거 성공률 점수 (10%)")
                st.metric("체인", f"{score_breakdown.get('chain', 0):.3f}",
                         help="체인 점수 (10%)")
        
        # METT-C 점수 (있는 경우)
        mett_c_scores = raw_result.get("METTCScores") or score_breakdown.get("mett_c")
        if mett_c_scores:
            st.divider()
            st.markdown("#### METT-C 종합 평가")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                mett_c_total = mett_c_scores.get("total", 0)
                st.metric("METT-C 종합", f"{mett_c_total:.3f}",
                         help="METT-C 종합 점수")
                st.metric("🎯 임무", f"{mett_c_scores.get('mission', 0):.3f}",
                         help="임무 부합성 (20%)")
            
            with col2:
                st.metric("⚠️ 적군", f"{mett_c_scores.get('enemy', 0):.3f}",
                         help="적군 대응 (20%)")
                st.metric("🌍 지형", f"{mett_c_scores.get('terrain', 0):.3f}",
                         help="지형 적합성 (15%)")
            
            with col3:
                st.metric("👥 부대", f"{mett_c_scores.get('troops', 0):.3f}",
                         help="부대 능력 (15%)")
                civilian_score = mett_c_scores.get("civilian", 1.0)
                if civilian_score < 0.3:
                    st.error(f"🏘️ 민간인: {civilian_score:.3f}", help="민간인 보호 (15%) - 경고")
                else:
                    st.metric("🏘️ 민간인", f"{civilian_score:.3f}",
                             help="민간인 보호 (15%)")
            
            with col4:
                time_score = mett_c_scores.get("time", 1.0)
                if time_score == 0.0:
                    st.error("⏰ 시간: 0.000", help="시간 제약 (15%) - 위반")
                elif time_score < 0.5:
                    st.warning(f"⏰ 시간: {time_score:.3f}", help="시간 제약 (15%) - 주의")
                else:
                    st.metric("⏰ 시간", f"{time_score:.3f}",
                             help="시간 제약 (15%)")
        
        # 체인 정보
        chain_info = raw_result.get("ChainInfo", {})
        if chain_info:
            st.divider()
            st.markdown("#### 관계 체인 정보")
            
            chain_summary = chain_info.get("summary", {})
            if chain_summary:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("체인 수", chain_summary.get("total_chains", 0))
                with col2:
                    st.metric("평균 깊이", chain_summary.get("avg_depth", 0))
                with col3:
                    st.metric("평균 점수", f"{chain_summary.get('avg_score', 0):.3f}")
            
            # 최고 체인 표시
            best_chain = chain_summary.get("best_chain")
            if best_chain:
                with st.expander("최고 점수 체인", expanded=False):
                    st.json(best_chain)
        
        # RAG 결과 수
        rag_count = result.get("rag_results_count", 0)
        if rag_count > 0:
            st.info(f"RAG 검색 결과: {rag_count}개 문서 활용")





