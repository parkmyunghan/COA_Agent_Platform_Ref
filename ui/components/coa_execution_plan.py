# ui/components/coa_execution_plan.py
# -*- coding: utf-8 -*-
"""
방책 실행 계획 컴포넌트
추천된 방책의 실행 계획 생성 및 표시
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta


def render_coa_execution_plan(recommendation: Dict, situation_info: Optional[Dict] = None, approach_mode: str = "threat_centered"):
    """
    방책 실행 계획 생성 및 표시
    
    Args:
        recommendation: 추천된 방책 정보
        situation_info: 상황 정보 (선택적)
        approach_mode: "threat_centered" 또는 "mission_centered"
    """
    if not recommendation:
        st.info("추천된 방책이 없습니다.")
        return
    
    header_text = "📋 임무 수행 계획" if approach_mode == "mission_centered" else "📋 방책 실행 계획"
    st.subheader(header_text)
    
    coa_name = recommendation.get("coa_name", "Unknown")
    coa_id = recommendation.get("coa_id", "N/A")
    score = recommendation.get("score", 0)
    
    # [NEW] 부대 운용 근거 표시
    reasoning = recommendation.get("reasoning", {})
    unit_rationale = reasoning.get("unit_rationale")
    if unit_rationale:
        st.info(f"🛡️ **부대 운용 근거**: {unit_rationale}")

    st.divider()
    
    # 1. 단계별 실행 계획
    execution_steps = generate_execution_steps(recommendation, situation_info, approach_mode=approach_mode)
    render_execution_steps(execution_steps, approach_mode=approach_mode)
    
    # 2. 필요 자원 목록
    required_resources = extract_required_resources(recommendation, situation_info)
    render_required_resources(required_resources)
    
    # 3. 위험 요소 및 대응 방안
    risk_assessment = assess_risks(recommendation, situation_info, approach_mode=approach_mode)
    render_risk_assessment(risk_assessment)
    
    # 4. 예상 소요 시간
    estimated_time = estimate_execution_time(recommendation, approach_mode=approach_mode)
    render_time_estimate(estimated_time)
    
    # 5. 승인 워크플로우 (실전 적용 시)
    render_approval_workflow(recommendation)


def generate_execution_steps(recommendation: Dict, situation_info: Optional[Dict] = None, approach_mode: str = "threat_centered") -> List[Dict]:
    """실행 단계 생성"""
    coa_name = recommendation.get("coa_name", "")

    # 기본 실행 단계 (방책 유형에 따라 다를 수 있음)
    base_steps = [
        {
            "단계": "1. 초기 배치",
            "내용": "임무 수행을 위한 초기 부대 및 자원 배치" if approach_mode == "mission_centered" else "방책 실행을 위한 초기 부대 및 자원 배치",
            "소요시간": "30분",
            "담당": "작전 계획 담당",
            "우선순위": "높음"
        },
        {
            "단계": "2. 자원 배치",
            "내용": "필요한 자원(인력, 장비, 보급품) 배치",
            "소요시간": "1시간",
            "담당": "보급 담당",
            "우선순위": "높음"
        },
        {
            "단계": "3. 통신망 구축",
            "내용": "작전 통신망 구축 및 연락 체계 확립",
            "소요시간": "30분",
            "담당": "통신 담당",
            "우선순위": "중간"
        },
        {
            "단계": "4. 작전 수행" if approach_mode == "mission_centered" else "4. 방책 실행",
            "내용": f"{coa_name} 임무 수행" if approach_mode == "mission_centered" else f"{coa_name} 방책 본격 실행",
            "소요시간": "2시간",
            "담당": "작전 담당",
            "우선순위": "높음"
        },
        {
            "단계": "5. 모니터링 및 조정",
            "내용": "실행 상황 모니터링 및 필요시 조정",
            "소요시간": "지속",
            "담당": "지휘부",
            "우선순위": "중간"
        }
    ]
    
    # 방책 유형에 따른 추가 단계
    if "공격" in coa_name or "공세" in coa_name:
        base_steps.insert(3, {
            "단계": "3-1. 공격 준비",
            "내용": "공격 작전 준비 및 최종 점검",
            "소요시간": "1시간",
            "담당": "작전 담당",
            "우선순위": "높음"
        })
    
    return base_steps


def render_execution_steps(steps: List[Dict], approach_mode: str = "threat_centered"):
    """실행 단계 표시"""
    header = "📝 단계별 임무 수행 계획" if approach_mode == "mission_centered" else "📝 단계별 실행 계획"
    st.markdown(f"#### {header}")
    
    for step in steps:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                priority_icon = "🔴" if step["우선순위"] == "높음" else "🟡" if step["우선순위"] == "중간" else "🟢"
                st.markdown(f"**{priority_icon} {step['단계']}**")
                st.write(step["내용"])
            
            with col2:
                st.metric("소요시간", step["소요시간"])
            
            with col3:
                st.caption(f"담당: {step['담당']}")
            
            st.divider()


def extract_required_resources(recommendation: Dict, situation_info: Optional[Dict] = None) -> Dict:
    """필요 자원 추출"""
    # 점수 breakdown에서 자원 정보 추출
    score_breakdown = recommendation.get("score_breakdown", {})
    resource_score = score_breakdown.get("resources", 0)
    
    # 기본 자원 목록 (실제로는 온톨로지에서 추출해야 함)
    required_resources = {
        "인력": {
            "필요량": "1개 대대",
            "가용량": "1개 대대",
            "충족도": "100%" if resource_score > 0.7 else "부족" if resource_score < 0.5 else "부분"
        },
        "장비": {
            "필요량": "전차 10대, 장갑차 5대",
            "가용량": "전차 12대, 장갑차 6대",
            "충족도": "충분"
        },
        "보급품": {
            "필요량": "연료 1000L, 탄약 5000발",
            "가용량": "연료 1200L, 탄약 6000발",
            "충족도": "충분"
        },
        "통신 장비": {
            "필요량": "무선기 10대",
            "가용량": "무선기 15대",
            "충족도": "충분"
        }
    }
    
    return required_resources


def render_required_resources(resources: Dict):
    """필요 자원 목록 표시"""
    st.markdown("#### 📦 필요 자원 목록")
    
    resource_data = []
    for resource_type, info in resources.items():
        resource_data.append({
            "자원 유형": resource_type,
            "필요량": info["필요량"],
            "가용량": info["가용량"],
            "충족도": info["충족도"]
        })
    
    df = pd.DataFrame(resource_data)
    st.dataframe(df, width='stretch', hide_index=True)


def assess_risks(recommendation: Dict, situation_info: Optional[Dict] = None, approach_mode: str = "threat_centered") -> List[Dict]:
    """위험 요소 평가"""
    if approach_mode == "mission_centered":
        risks = [
            {
                "위험 요소": "임무 방해 요소",
                "위험도": "중간",
                "설명": "적군 또는 환경 요인에 의한 임무 달성 방해 가능성",
                "대응 방안": "우발 계획 수립 및 실시간 모니터링"
            },
            {
                "위험 요소": "기상 및 지형",
                "위험도": "낮음",
                "설명": "작전 지역의 지형지물 또는 기상 변화에 따른 제한",
                "대응 방안": "상세 지형 분석 및 기상 정찰 강화"
            },
            {
                "위험 요소": "자원 무결성",
                "위험도": "낮음",
                "설명": "임무 수행 중 자원의 소모 또는 손실",
                "대응 방안": "예비대 편성 및 보급로 확보"
            }
        ]
    else:
        risks = [
            {
                "위험 요소": "적군 대응",
                "위험도": "중간",
                "설명": "적군의 대응 작전으로 인한 예상치 못한 상황 발생 가능",
                "대응 방안": "실시간 정찰 및 상황 모니터링 강화"
            },
            {
                "위험 요소": "기상 악화",
                "위험도": "낮음",
                "설명": "기상 조건 악화로 인한 작전 지연 가능",
                "대응 방안": "기상 정보 지속 모니터링 및 대체 계획 수립"
            },
            {
                "위험 요소": "자원 부족",
                "위험도": "낮음",
                "설명": "예상치 못한 자원 소모로 인한 부족 가능",
                "대응 방안": "비상 자원 확보 및 우선순위 조정"
            }
        ]
    
    return risks


def render_risk_assessment(risks: List[Dict]):
    """위험 요소 및 대응 방안 표시"""
    st.markdown("#### ⚠️ 위험 요소 및 대응 방안")
    
    for risk in risks:
        with st.container():
            risk_level = risk["위험도"]
            if risk_level == "높음":
                st.error(f"🔴 **{risk['위험 요소']}** (위험도: {risk_level})")
            elif risk_level == "중간":
                st.warning(f"🟡 **{risk['위험 요소']}** (위험도: {risk_level})")
            else:
                st.info(f"🟢 **{risk['위험 요소']}** (위험도: {risk_level})")
            
            st.write(f"**설명:** {risk['설명']}")
            st.write(f"**대응 방안:** {risk['대응 방안']}")
            st.divider()


def estimate_execution_time(recommendation: Dict, approach_mode: str = "threat_centered") -> Dict:
    """예상 소요 시간 추정"""
    steps = generate_execution_steps(recommendation, approach_mode=approach_mode)
    
    total_time_minutes = 0
    for step in steps:
        time_str = step["소요시간"]
        if "시간" in time_str:
            hours = int(time_str.replace("시간", "").strip())
            total_time_minutes += hours * 60
        elif "분" in time_str:
            minutes = int(time_str.replace("분", "").strip())
            total_time_minutes += minutes
    
    estimated_start = datetime.now()
    estimated_end = estimated_start + timedelta(minutes=total_time_minutes)
    
    return {
        "총 소요 시간": f"{total_time_minutes // 60}시간 {total_time_minutes % 60}분",
        "예상 시작 시간": estimated_start.strftime("%Y-%m-%d %H:%M"),
        "예상 완료 시간": estimated_end.strftime("%Y-%m-%d %H:%M"),
        "단계 수": len(steps)
    }


def render_time_estimate(time_info: Dict):
    """예상 소요 시간 표시"""
    st.markdown("#### ⏱️ 예상 소요 시간")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 소요 시간", time_info["총 소요 시간"])
    with col2:
        st.metric("예상 시작", time_info["예상 시작 시간"])
    with col3:
        st.metric("예상 완료", time_info["예상 완료 시간"])


def render_approval_workflow(recommendation: Dict):
    """승인 워크플로우 표시"""
    st.markdown("#### ✅ 방책 승인")
    
    st.info("""
    💡 **실전 적용 시:** 방책 승인 워크플로우가 여기에 표시됩니다.
    - 지휘관 승인
    - 작전 계획 검토
    - 자원 배치 확인
    - 최종 실행 승인
    """)
    
    # 데모용 승인 버튼
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 방책 검토 요청", width='stretch'):
            st.success("✅ 방책 검토가 요청되었습니다.")
    with col2:
        if st.button("✅ 방책 승인", type="primary", width='stretch'):
            st.success("✅ 방책이 승인되었습니다!")
    with col3:
        if st.button("❌ 방책 반려", width='stretch'):
            st.warning("⚠️ 방책이 반려되었습니다. 다른 방책을 검토하세요.")


