# ui/components/doctrine_reference_display.py
# -*- coding: utf-8 -*-
"""
교리 참조 표시 컴포넌트
COA 추천 결과에서 교리 참조 정보를 표시합니다.
"""
import streamlit as st
from typing import Dict, List, Optional


def render_doctrine_references(coa_recommendation: Dict):
    """
    COA 추천 결과에서 교리 참조 정보를 표시
    
    Args:
        coa_recommendation: COA 추천 결과 딕셔너리 (doctrine_references 포함)
    """
    doctrine_refs = coa_recommendation.get('doctrine_references', [])
    
    st.markdown("---")
    st.subheader("📚 적용된 참고 자료")
    
    if not doctrine_refs:
        st.info("참고 자료 데이터가 비어 있습니다.")
        return
    
    st.caption("본 COA 추천은 다음 교리 문장 및 참고 자료를 근거로 합니다.")
    
    # 🔥 개선: 교리 문서와 일반 문서 구분 (하위 호환성 지원)
    doctrine_refs_list = []
    general_refs_list = []
    
    for ref in doctrine_refs:
        ref_type = ref.get('reference_type')
        # reference_type이 없으면 자동 판단 (하위 호환성)
        if not ref_type:
            # doctrine_id가 있고 UNKNOWN이 아니면 교리 문서
            if ref.get('doctrine_id') and ref.get('doctrine_id') != 'UNKNOWN':
                ref_type = 'doctrine'
            # source가 'doctrine'이면 교리로 분류
            elif str(ref.get('source', '')).strip().lower() == 'doctrine':
                ref_type = 'doctrine'
            else:
                ref_type = 'general'
        
        if ref_type == 'doctrine':
            doctrine_refs_list.append(ref)
        elif ref_type == 'general':
            general_refs_list.append(ref)
        else:
            # reference_type이 없고 판단도 안되면 교리 문서로 간주 (기본값)
            doctrine_refs_list.append(ref)
    
    # 교리 문서 표시
    if doctrine_refs_list:
        st.markdown("#### 📖 교리 문서")
        for i, ref in enumerate(doctrine_refs_list, 1):
            statement_id = ref.get('statement_id', f'Unknown-{i}')
            excerpt = ref.get('excerpt', '')
            relevance_score = ref.get('relevance_score', 0.0)
            mett_c_elements = ref.get('mett_c_elements', [])
            doctrine_id = ref.get('doctrine_id', 'Unknown')
            
            # 교리 참조 카드
            with st.expander(f"**[{statement_id}]** (관련도: {relevance_score:.2f})", expanded=(i == 1)):
                # 교리 문장 본문
                st.markdown(f"""
                <div style="
                    padding: 12px;
                    background-color: rgba(88, 166, 255, 0.1);
                    border-left: 4px solid #58a6ff;
                    border-radius: 4px;
                    margin: 8px 0;
                ">
                    <div style="font-style: italic; color: #a5d6ff;">
                        "{excerpt}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 메타데이터
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"**교리 ID**: {doctrine_id}")
                with col2:
                    if mett_c_elements:
                        st.caption(f"**관련 METT-C**: {', '.join(mett_c_elements)}")
                
                # 관련도 표시
                st.progress(relevance_score, text=f"관련도: {relevance_score:.1%}")
    else:
        st.info("교리 문서 참조가 없습니다.")
    
    # 🔥 일반 문서 표시
    if general_refs_list:
        st.markdown("#### 📄 일반 참고 문서")
        for i, ref in enumerate(general_refs_list, 1):
            source = ref.get('source', f'문서-{i}')
            excerpt = ref.get('excerpt', '')
            relevance_score = ref.get('relevance_score', 0.0)
            mett_c_elements = ref.get('mett_c_elements', [])
            
            # 일반 문서 참조 카드
            with st.expander(f"**{source}** (관련도: {relevance_score:.2f})", expanded=(i == 1 and not doctrine_refs_list)):
                # 문서 내용
                st.markdown(f"""
                <div style="
                    padding: 12px;
                    background-color: rgba(255, 193, 7, 0.1);
                    border-left: 4px solid #ffc107;
                    border-radius: 4px;
                    margin: 8px 0;
                ">
                    <div style="font-style: italic; color: #ffd54f;">
                        "{excerpt}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 메타데이터
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"**문서 소스**: {source}")
                with col2:
                    if mett_c_elements:
                        st.caption(f"**관련 METT-C**: {', '.join(mett_c_elements)}")
                
                # 관련도 표시
                st.progress(relevance_score, text=f"관련도: {relevance_score:.1%}")
    else:
        if not doctrine_refs_list:
            st.info("참고 자료가 없습니다. (일반/교리 데이터 부재)")
        else:
            st.info("일반 참고 문서가 없습니다.")


def render_doctrine_based_explanation(
    coa_recommendation: Dict,
    situation_info: Optional[Dict] = None,
    mett_c_analysis: Optional[Dict] = None
):
    """
    교리 기반 COA 추천 근거 설명 표시
    
    Args:
        coa_recommendation: COA 추천 결과 (doctrine_references 포함)
        situation_info: 상황 정보 (선택적)
        mett_c_analysis: METT-C 분석 결과 (선택적)
    """
    doctrine_refs = coa_recommendation.get('doctrine_references', [])
    
    if not doctrine_refs:
        return
    
    try:
        from core_pipeline.coa_engine.doctrine_explanation_generator import DoctrineBasedExplanationGenerator
        
        generator = DoctrineBasedExplanationGenerator()
        
        explanation = generator.generate_explanation(
            coa_recommendation=coa_recommendation,
            situation_info=situation_info or {},
            mett_c_analysis=mett_c_analysis or {},
            axis_states=[]  # 필요시 전달
        )
        
        st.markdown("---")
        st.subheader("📖 교리 기반 추천 근거 설명")
        
        # 마크다운 형식으로 표시
        st.markdown(explanation)
        
    except Exception as e:
        st.warning(f"교리 기반 설명 생성 실패: {e}")
        # 폴백: 교리 참조만 표시
        render_doctrine_references(coa_recommendation)


def render_doctrine_references_inline(coa_recommendation: Dict):
    """
    인라인 형식으로 교리 참조 간단 표시 (카드 내부 등)
    
    Args:
        coa_recommendation: COA 추천 결과
    """
    doctrine_refs = coa_recommendation.get('doctrine_references', [])
    
    if not doctrine_refs:
        return
    
    # 🔥 개선: 교리 문서와 일반 문서 구분 (Fallback 로직 포함)
    doctrine_count = 0
    general_count = 0
    doctrine_ids = []
    
    for ref in doctrine_refs:
        ref_type = ref.get('reference_type')
        if not ref_type:
            # Fallback determination
            if ref.get('doctrine_id') and ref.get('doctrine_id') != 'UNKNOWN':
                ref_type = 'doctrine'
            elif str(ref.get('source', '')).strip().lower() == 'doctrine':
                ref_type = 'doctrine'
            else:
                ref_type = 'general'
        
        if ref_type == 'doctrine':
            doctrine_count += 1
            doctrine_ids.append(ref.get('statement_id', 'Unknown'))
        else:
            general_count += 1
    
    ref_summary = []
    if doctrine_count > 0:
        # 최대 3개까지 표시하고 남으면 +N 표기
        display_limit = 3
        ids_display = doctrine_ids[:display_limit]
        ids_str = ', '.join(ids_display)
        if doctrine_count > display_limit:
            ids_str += f", ...(+{doctrine_count - display_limit})"
        ref_summary.append(f"교리: {ids_str}")
        
    if general_count > 0:
        ref_summary.append(f"일반: {general_count}개")
    
    st.markdown(f"""<div style="margin-top: 8px; padding: 8px; background-color: rgba(88, 166, 255, 0.05); border: 1px dashed rgba(88, 166, 255, 0.3); border-radius: 4px; font-size: 0.85em;">
    <div style="color: #58a6ff; font-weight: 600; margin-bottom: 4px;">
        📚 참고 자료: {len(doctrine_refs)}개{f' (교리 {doctrine_count}개, 일반 {general_count}개)' if general_count > 0 else ''}
    </div>
    <div style="color: #a5d6ff; font-size: 0.9em;">
        {', '.join(ref_summary) if ref_summary else '참고 자료 없음'}
    </div>
</div>""", unsafe_allow_html=True)


