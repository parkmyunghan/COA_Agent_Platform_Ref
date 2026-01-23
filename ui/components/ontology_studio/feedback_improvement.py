# ui/components/ontology_studio/feedback_improvement.py
# -*- coding: utf-8 -*-
"""
피드백 및 개선 컴포넌트
온톨로지 문제 식별 및 개선 계획 수립
"""
import streamlit as st
from datetime import datetime
from typing import Dict
import json
from pathlib import Path

def render_feedback_improvement(orchestrator):
    """피드백 및 개선 렌더링"""
    st.markdown("### 🔄 피드백 및 개선")
    st.info("💡 온톨로지 사용 중 발견된 문제를 기록하고 개선 계획을 수립합니다.")
    
    # 개선 이슈 저장 파일
    base_dir = Path(__file__).parent.parent.parent.parent
    issues_file = base_dir / "metadata" / "improvement_issues.json"
    issues_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 이슈 로드
    if issues_file.exists():
        try:
            with open(issues_file, 'r', encoding='utf-8') as f:
                issues = json.load(f)
        except:
            issues = []
    else:
        issues = []
    
    # 새 이슈 등록
    st.markdown("#### 📝 새 문제 등록")
    with st.form("new_issue_form"):
        issue_title = st.text_input("문제 제목", key="new_issue_title")
        issue_description = st.text_area("문제 설명", key="new_issue_description")
        issue_severity = st.selectbox("심각도", ["낮음", "중간", "높음", "긴급"], key="new_issue_severity")
        
        if st.form_submit_button("문제 등록", type="primary"):
            if issue_title and issue_description:
                new_issue = {
                    "id": len(issues) + 1,
                    "title": issue_title,
                    "description": issue_description,
                    "severity": issue_severity,
                    "detected_at": datetime.now().isoformat(),
                    "status": "등록됨",
                    "improvement_plan": None
                }
                issues.append(new_issue)
                
                with open(issues_file, 'w', encoding='utf-8') as f:
                    json.dump(issues, f, ensure_ascii=False, indent=2)
                
                st.success("✅ 문제가 등록되었습니다.")
                st.rerun()
    
    st.divider()
    
    # 등록된 문제 목록
    if not issues:
        st.info("등록된 문제가 없습니다.")
        return
    
    st.markdown(f"#### ⚠️ 등록된 문제 ({len(issues)}개)")
    
    for i, issue in enumerate(issues):
        with st.expander(f"문제 #{issue.get('id', i+1)}: {issue.get('title', '제목 없음')} [{issue.get('status', '등록됨')}]", expanded=(i == 0)):
            st.markdown(f"**설명**: {issue.get('description', '')}")
            st.markdown(f"**심각도**: {issue.get('severity', '중간')}")
            st.markdown(f"**등록 일시**: {issue.get('detected_at', '')}")
            
            # 개선 계획 수립
            if issue.get('improvement_plan') is None:
                if st.button(f"개선 계획 수립", key=f"improve_{i}"):
                    improvement_plan = {
                        "title": f"{issue.get('title', '문제')} 개선 계획",
                        "description": f"문제: {issue.get('description', '')}",
                        "priority": issue.get('severity', '중간'),
                        "steps": [
                            "문제 원인 분석",
                            "해결 방안 수립",
                            "수정 작업 수행",
                            "재검증"
                        ],
                        "created_at": datetime.now().isoformat()
                    }
                    issues[i]['improvement_plan'] = improvement_plan
                    issues[i]['status'] = "개선 계획 수립됨"
                    
                    with open(issues_file, 'w', encoding='utf-8') as f:
                        json.dump(issues, f, ensure_ascii=False, indent=2)
                    
                    st.success("✅ 개선 계획이 수립되었습니다.")
                    st.rerun()
            else:
                st.markdown("**개선 계획**:")
                st.json(issue['improvement_plan'])
                
                if st.button(f"개선 완료 처리", key=f"complete_{i}"):
                    issues[i]['status'] = "개선 완료"
                    issues[i]['completed_at'] = datetime.now().isoformat()
                    
                    with open(issues_file, 'w', encoding='utf-8') as f:
                        json.dump(issues, f, ensure_ascii=False, indent=2)
                    
                    st.success("✅ 개선 완료 처리되었습니다.")
                    st.rerun()
    
    st.divider()
    
    # 개선 계획 요약
    improvement_plans = [
        issue.get('improvement_plan') 
        for issue in issues 
        if issue.get('improvement_plan')
    ]
    
    if improvement_plans:
        st.markdown("#### 📋 개선 계획 요약")
        
        for plan in improvement_plans:
            st.markdown(f"- **{plan.get('title', '제목 없음')}**")
            st.caption(f"  우선순위: {plan.get('priority', '중간')}")

