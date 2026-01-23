# ui/components/natural_language_explanation.py
# -*- coding: utf-8 -*-
"""
자연어 설명 생성 컴포넌트
LLM을 사용하여 방책 추천 사유를 사람이 이해하기 쉬운 자연어로 설명
"""
import streamlit as st
import json
from typing import Dict, List, Optional


def generate_natural_language_explanation(agent_result: Dict, core) -> str:
    """
    LLM을 사용하여 추천 방책의 사유를 자연어로 설명 생성
    
    Args:
        agent_result: Agent 실행 결과 딕셔너리
        core: CorePipeline 인스턴스 (LLM 접근용)
    
    Returns:
        자연어 설명 텍스트
    """
    if not agent_result or not core:
        return "설명을 생성할 수 없습니다."
    
    # LLM 사용 가능 여부 확인
    if not core.llm_manager.is_available():
        return _generate_fallback_explanation(agent_result)
    
    try:
        # 1. 추천 정보 추출
        recommendations = agent_result.get("recommendations", [])
        if not recommendations:
            return "추천된 방책이 없습니다."
        
        top_recommendation = recommendations[0]
        situation_info = agent_result.get("situation_info", {})
        score_breakdown = top_recommendation.get("score_breakdown", {})
        situation_analysis = agent_result.get("situation_analysis", {})
        
        # 2. 상황 정보 정리
        threat_level = situation_info.get('심각도', situation_info.get('위협수준', 'N/A'))
        if isinstance(threat_level, (int, float)):
            if threat_level > 1.0:
                threat_level = threat_level / 100.0
            threat_level_text = f"{threat_level:.1%}"
        else:
            threat_level_text = str(threat_level)
        
        threat_type = situation_info.get('위협유형', 'N/A')
        location = situation_info.get('발생장소', situation_info.get('장소', 'N/A'))
        
        # 3. 점수 breakdown 정보 정리
        breakdown_text = ""
        if score_breakdown:
            factor_names = {
                "threat": "위협 수준",
                "resources": "자원 가용성",
                "assets": "전력 능력",
                "environment": "환경 적합성",
                "historical": "과거 효과성",
                "chain": "연계성"
            }
            
            breakdown_items = []
            for key, name in factor_names.items():
                score = score_breakdown.get(key, 0)
                if score > 0:
                    breakdown_items.append(f"- {name}: {score:.3f}")
            
            if breakdown_items:
                breakdown_text = "\n".join(breakdown_items)
        
        # 4. 비교 정보 (상위 3개 방책)
        comparison_text = ""
        if len(recommendations) > 1:
            top3 = recommendations[:3]
            comparison_items = []
            for i, rec in enumerate(top3, 1):
                coa_name = rec.get('coa_name', 'Unknown')
                score = rec.get('score', 0)
                comparison_items.append(f"{i}. {coa_name} (점수: {score:.3f})")
            
            if comparison_items:
                comparison_text = "\n".join(comparison_items)
        
        # 5. LLM 프롬프트 구성
        prompt = f"""다음 정보를 바탕으로 방책 추천 사유를 사람이 이해하기 쉽게 설명해주세요.

## 현재 상황
- 위협 수준: {threat_level_text}
- 위협 유형: {threat_type}
- 발생 장소: {location}

## 추천 방책
- 방책명: {top_recommendation.get('coa_name', 'N/A')}
- 종합 점수: {top_recommendation.get('score', 0):.3f}
- 기존 추천 사유: {top_recommendation.get('reason', 'N/A')}

## 평가 요소별 점수
{breakdown_text if breakdown_text else "점수 상세 정보 없음"}

## 다른 방책과의 비교
{comparison_text if comparison_text else "비교할 다른 방책 없음"}

## 설명 요청사항
다음 형식으로 설명해주세요:

### 1. 현재 상황 요약
현재 상황을 간단히 요약해주세요.

### 2. 이 방책이 선택된 주요 이유 (3가지)
왜 이 방책이 현재 상황에 가장 적합한지 3가지 주요 이유를 설명해주세요.

### 3. 각 평가 요소별 평가 결과
각 평가 요소(위협 수준, 자원 가용성, 전력 능력, 환경 적합성, 과거 효과성, 연계성)별로 어떻게 평가되었는지 설명해주세요.

### 4. 예상 효과 및 주의사항
이 방책을 실행했을 때 예상되는 효과와 주의해야 할 사항을 설명해주세요.

설명은 군사 작전 담당자가 이해하기 쉽도록 전문적이면서도 명확하게 작성해주세요."""

        # 6. LLM 호출
        explanation = core.llm_manager.generate(prompt, max_tokens=800, temperature=0.7)
        
        return explanation
        
    except Exception as e:
        st.warning(f"자연어 설명 생성 중 오류 발생: {e}")
        return _generate_fallback_explanation(agent_result)


def _generate_fallback_explanation(agent_result: Dict) -> str:
    """
    LLM을 사용할 수 없을 때 기본 설명 생성
    
    Args:
        agent_result: Agent 실행 결과 딕셔너리
    
    Returns:
        기본 설명 텍스트
    """
    recommendations = agent_result.get("recommendations", [])
    if not recommendations:
        return "추천된 방책이 없습니다."
    
    top_recommendation = recommendations[0]
    situation_info = agent_result.get("situation_info", {})
    
    coa_name = top_recommendation.get('coa_name', 'Unknown')
    score = top_recommendation.get('score', 0)
    reason = top_recommendation.get('reason', 'N/A')
    
    threat_level = situation_info.get('심각도', situation_info.get('위협수준', 'N/A'))
    if isinstance(threat_level, (int, float)):
        if threat_level > 1.0:
            threat_level = threat_level / 100.0
        threat_level_text = f"{threat_level:.1%}"
    else:
        threat_level_text = str(threat_level)
    
    explanation = f"""## 방책 추천 설명

### 현재 상황
- 위협 수준: {threat_level_text}
- 위협 유형: {situation_info.get('위협유형', 'N/A')}
- 발생 장소: {situation_info.get('발생장소', situation_info.get('장소', 'N/A'))}

### 추천 방책
**{coa_name}** (종합 점수: {score:.3f})

### 추천 사유
{reason if reason != 'N/A' else '추천 사유 정보가 없습니다.'}

### 참고사항
LLM을 사용한 상세 설명을 생성하려면 LLM 모델을 로드하거나 OpenAI API를 설정하세요."""
    
    return explanation


def render_natural_language_explanation(agent_result: Dict, core, key_prefix: str = "nl_explanation"):
    """
    자연어 설명을 Streamlit에 렌더링
    
    Args:
        agent_result: Agent 실행 결과 딕셔너리
        core: CorePipeline 인스턴스
        key_prefix: Streamlit 위젯 키 접두사
    """
    if not agent_result:
        st.info("추천 결과가 없어 설명을 생성할 수 없습니다.")
        return
    
    st.subheader("💬 자연어 설명")
    st.markdown("추천 방책의 사유를 사람이 이해하기 쉬운 자연어로 설명합니다.")
    
    # 설명 생성 버튼
    if st.button("📝 설명 생성", key=f"{key_prefix}_generate"):
        with st.spinner("자연어 설명을 생성하는 중..."):
            explanation = generate_natural_language_explanation(agent_result, core)
            
            # 세션 상태에 저장
            st.session_state[f"{key_prefix}_explanation"] = explanation
            st.session_state[f"{key_prefix}_generated"] = True
    
    # 저장된 설명이 있으면 표시
    if st.session_state.get(f"{key_prefix}_generated", False):
        explanation = st.session_state.get(f"{key_prefix}_explanation", "")
        
        if explanation:
            # 설명 표시
            st.markdown("---")
            st.markdown(explanation)
            
            # 다시 생성 버튼
            if st.button("🔄 설명 다시 생성", key=f"{key_prefix}_regenerate"):
                with st.spinner("자연어 설명을 다시 생성하는 중..."):
                    explanation = generate_natural_language_explanation(agent_result, core)
                    st.session_state[f"{key_prefix}_explanation"] = explanation
                    st.rerun()
        else:
            st.warning("설명 생성에 실패했습니다.")


def render_inline_natural_language_explanation(agent_result: Dict, core) -> str:
    """
    자연어 설명을 인라인으로 생성 (자동 생성, 버튼 없음)
    
    Args:
        agent_result: Agent 실행 결과 딕셔너리
        core: CorePipeline 인스턴스
    
    Returns:
        자연어 설명 텍스트
    """
    return generate_natural_language_explanation(agent_result, core)




