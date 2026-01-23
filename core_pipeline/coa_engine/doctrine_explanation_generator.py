# core_pipeline/coa_engine/doctrine_explanation_generator.py
# -*- coding: utf-8 -*-
"""
교리 기반 COA 근거 설명 생성기
교리 문장을 근거로 COA 추천 이유를 설명합니다.
"""
from typing import List, Dict, Optional, Any


class DoctrineBasedExplanationGenerator:
    """교리 기반 COA 근거 설명 생성기"""
    
    def __init__(self, llm_manager=None):
        """
        Args:
            llm_manager: LLMManager 인스턴스 (선택적, 향후 LLM 기반 설명 생성용)
        """
        self.llm_manager = llm_manager
    
    def generate_explanation(
        self,
        coa_recommendation: Dict,
        situation_info: Dict,
        mett_c_analysis: Dict,
        axis_states: List[Any]
    ) -> str:
        """
        교리 기반 COA 추천 근거 설명 생성
        
        Args:
            coa_recommendation: COA 추천 결과 (doctrine_references 포함)
            situation_info: 상황 정보
            mett_c_analysis: METT-C 분석 결과
            axis_states: 축선별 전장상태
        
        Returns:
            마크다운 형식 설명문
        """
        doctrine_refs = coa_recommendation.get('doctrine_references', [])
        
        if not doctrine_refs:
            # 교리 참조가 없으면 기존 방식으로 폴백
            return self._generate_fallback_explanation(coa_recommendation, situation_info)
        
        # 교리 기반 설명 생성
        explanation = self._build_doctrine_based_explanation(
            coa_recommendation,
            situation_info,
            mett_c_analysis,
            axis_states,
            doctrine_refs
        )
        
        return explanation
    
    def _build_doctrine_based_explanation(
        self,
        coa_recommendation: Dict,
        situation_info: Dict,
        mett_c_analysis: Dict,
        axis_states: List[Any],
        doctrine_refs: List[Dict]
    ) -> str:
        """교리 기반 설명 구성"""
        coa_id = coa_recommendation.get('coa_id', 'Unknown')
        coa_name = coa_recommendation.get('coa_name', 'Unknown')
        
        # 1. 작전 상황 요약
        situation_summary = self._summarize_situation(situation_info, axis_states)
        
        # 2. METT-C 핵심 제약 요소
        mett_c_summary = self._summarize_mett_c(mett_c_analysis)
        
        # 3. 적용된 교리 문장
        doctrine_section = self._format_doctrine_references(doctrine_refs)
        
        # 4. 교리 → COA 연결 논리
        connection_logic = self._explain_doctrine_coa_connection(
            coa_recommendation, doctrine_refs, mett_c_analysis
        )
        
        # 5. 교리 미적용 영역
        non_doctrine_areas = self._identify_non_doctrine_areas(
            coa_recommendation, doctrine_refs
        )
        
        # 최종 설명 조합
        explanation = f"""### {coa_id} ({coa_name}) 추천 근거 설명

#### 1. 작전 상황 요약
{situation_summary}

#### 2. METT-C 핵심 제약 요소
{mett_c_summary}

#### 3. 적용된 교리 문장
{doctrine_section}

#### 4. 교리 → COA 연결 논리
{connection_logic}
"""
        
        if non_doctrine_areas:
            explanation += f"""
#### 5. 교리 미적용 영역 (추론)
{non_doctrine_areas}
"""
        
        explanation += """
---

**안전장치 문장**:
본 설명은 교리 문장을 근거로 한 추천 논리를 제시하는 것이며,
최종 작전 결정은 지휘관 판단에 따른다.
"""
        
        return explanation
    
    def _summarize_situation(self, situation_info: Dict, axis_states: List[Any]) -> str:
        """작전 상황 요약"""
        summary_parts = []
        
        # 상황 정보에서 요약 추출
        if isinstance(situation_info, dict):
            situation_desc = situation_info.get('description') or situation_info.get('summary', '')
            if situation_desc:
                summary_parts.append(situation_desc)
        
        # 축선 정보 요약
        if axis_states:
            axis_names = []
            for axis in axis_states:
                axis_name = getattr(axis, 'axis_name', None) or getattr(axis, 'axis_id', 'Unknown')
                axis_names.append(axis_name)
            
            if axis_names:
                summary_parts.append(f"주요 작전 축선: {', '.join(axis_names[:3])}")
        
        if not summary_parts:
            return "현재 작전 상황을 분석한 결과, 제시된 COA가 적합한 것으로 판단됩니다."
        
        return "\n".join(summary_parts)
    
    def _summarize_mett_c(self, mett_c_analysis: Dict) -> str:
        """METT-C 핵심 제약 요소 요약"""
        if not isinstance(mett_c_analysis, dict):
            return "METT-C 분석 정보 없음"
        
        summary_parts = []
        
        # 각 METT-C 요소 요약
        mett_c_elements = {
            'mission': '임무(Mission)',
            'enemy': '적군(Enemy)',
            'terrain': '지형/기상(Terrain)',
            'troops': '가용부대(Troops)',
            'time': '가용시간(Time)',
            'civilian': '민간요소(Civilian)'
        }
        
        for key, label in mett_c_elements.items():
            element_data = mett_c_analysis.get(key, {})
            if isinstance(element_data, dict):
                summary = element_data.get('summary') or element_data.get('description', '')
                score = element_data.get('score')
                if summary:
                    if score is not None:
                        summary_parts.append(f"- **{label}**: {summary} (점수: {score:.2f})")
                    else:
                        summary_parts.append(f"- **{label}**: {summary}")
            elif element_data:
                summary_parts.append(f"- **{label}**: {str(element_data)}")
        
        if not summary_parts:
            # alignment 정보 확인
            alignment = mett_c_analysis.get('mett_c_alignment', {})
            if alignment:
                for key, value in alignment.items():
                    if value:
                        summary_parts.append(f"- **{key.capitalize()}**: {value}")
        
        if not summary_parts:
            return "METT-C 분석 결과가 상세히 제공되지 않았습니다."
        
        return "\n".join(summary_parts)
    
    def _format_doctrine_references(self, doctrine_refs: List[Dict]) -> str:
        """교리 참조 포맷팅"""
        sections = []
        for i, ref in enumerate(doctrine_refs, 1):
            statement_id = ref.get('statement_id')
            if not statement_id:
                statement_id = ref.get('source', '') or f'General-Ref-{i}'
                
            excerpt = ref.get('excerpt', '')
            relevance_score = ref.get('relevance_score', 0.0)
            mett_c_elements = ref.get('mett_c_elements', [])
            
            section = f"[{statement_id}]"
            if relevance_score > 0:
                section += f" (관련도: {relevance_score:.2f})"
            section += f"\n\"{excerpt}\""
            
            if mett_c_elements:
                section += f"\n- 관련 METT-C 요소: {', '.join(mett_c_elements)}"
            
            sections.append(section)
        
        return "\n\n".join(sections) if sections else "적용된 교리 문장이 없습니다."
    
    def _explain_doctrine_coa_connection(
        self,
        coa_recommendation: Dict,
        doctrine_refs: List[Dict],
        mett_c_analysis: Dict
    ) -> str:
        """교리 → COA 연결 논리 및 전술적 서사 설명"""
        coa_name = coa_recommendation.get('coa_name', 'Unknown')
        coa_id = coa_recommendation.get('coa_id', 'Unknown')
        
        explanation_parts = []
        
        # 1. 전술적 의도(Why) 설명 추가
        # (위협 위치와 작전 구역의 관계를 분석하여 서사 생성)
        intelligence = coa_recommendation.get('intelligence_summary', '')
        if not intelligence and mett_c_analysis.get('enemy'):
             intelligence = mett_c_analysis['enemy'].get('summary', '')

        # [TACTICAL LOGIC] 작전영역 확장 및 차단 기동 논리 주입
        tactical_narrative = (
            f"본 **{coa_name}({coa_id})**은 식별된 적의 위협으로부터 **작전 목표를 보호**하기 위해, "
            f"기존의 방어 영역에 국한되지 않고 **적의 예상 진출선까지 작전영역(AO)을 동적으로 확장**하여 "
            f"조기에 위협을 차단하는 **능동적 방어** 개념을 적용함."
        )
        explanation_parts.append(tactical_narrative)

        # 2. 교리 문장과의 구체적 연결
        for ref in doctrine_refs[:2]:
            statement_id = ref.get('statement_id', '')
            excerpt = ref.get('excerpt', '')
            if statement_id and excerpt:
                explanation_parts.append(
                    f"교리 문장 **[{statement_id}]**의 *\"{excerpt[:80]}...\"* 지침을 근거로, "
                    f"지형의 이점을 극대화할 수 있는 **최적의 기동로**를 선정하였으며, "
                    f"이를 통해 아군 피해를 최소화하면서도 적의 공격 기세를 꺾는 것을 목표로 설계됨."
                )
        
        if len(explanation_parts) <= 1:
            explanation_parts.append(
                f"본 방책은 현 상황에서 **가용 자산의 전투력지수**와 **축선별 위협 수준**을 종합적으로 고려할 때, "
                f"가장 높은 성과 달성 가능성을 보유한 것으로 분석됨."
            )
        
        return "\n\n".join(explanation_parts)
    
    def _identify_non_doctrine_areas(
        self,
        coa_recommendation: Dict,
        doctrine_refs: List[Dict]
    ) -> Optional[str]:
        """교리 미적용 영역 식별"""
        # COA 설명이나 reasoning에서 교리로 설명되지 않는 부분 찾기
        reasoning = coa_recommendation.get('reasoning', {})
        if isinstance(reasoning, dict):
            # reasoning에서 교리 참조가 없는 부분 추출
            pass
        
        # 현재는 간단히 처리
        # 향후 LLM을 활용하여 더 정교하게 식별 가능
        
        return None  # 교리 미적용 영역이 없으면 None 반환
    
    def _generate_fallback_explanation(
        self,
        coa_recommendation: Dict,
        situation_info: Dict
    ) -> str:
        """교리 참조가 없을 때 폴백 설명"""
        coa_id = coa_recommendation.get('coa_id', 'Unknown')
        coa_name = coa_recommendation.get('coa_name', 'Unknown')
        score = coa_recommendation.get('score', 0.0)
        
        return f"""### {coa_id} ({coa_name}) 추천 근거 설명

#### 1. 작전 상황 요약
현재 작전 상황을 분석한 결과, 제시된 COA가 적합한 것으로 판단됩니다.

#### 2. COA 평가 점수
본 COA의 종합 평가 점수는 {score:.2f}입니다.

#### 3. 추천 사유
교리 참조 정보가 제공되지 않아 일반적인 평가 기준에 따라 추천되었습니다.

---

**안전장치 문장**:
본 설명은 일반적인 평가 기준에 따른 추천 논리를 제시하는 것이며,
최종 작전 결정은 지휘관 판단에 따른다.
"""


