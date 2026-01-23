# core_pipeline/coa_engine/coa_llm_adapter.py
# -*- coding: utf-8 -*-
"""
COA LLM Adapter
COA 엔진과 LLM 서비스 간의 어댑터 레이어
비즈니스 로직과 LLM 호출을 분리
"""
from typing import Dict, List, Optional

from core_pipeline.coa_engine.llm_services import (
    SITREPParser,
    COAExplanationGenerator,
    DoctrineSearchService
)


class COALLMAdapter:
    """COA 엔진용 LLM 어댑터"""
    
    def __init__(self, llm_manager=None, rag_manager=None):
        """
        Args:
            llm_manager: LLMManager 인스턴스 (선택적)
            rag_manager: RAGManager 인스턴스 (선택적)
        """
        self.llm_manager = llm_manager  # llm_manager 속성 추가
        self.rag_manager = rag_manager  # rag_manager 속성 추가
        self.sitrep_parser = SITREPParser(llm_manager=llm_manager)
        self.explanation_generator = COAExplanationGenerator(llm_manager=llm_manager)
        self.doctrine_search = DoctrineSearchService(rag_manager=rag_manager)
    
    def parse_sitrep(self, sitrep_text: str, mission_id: str, use_llm: bool = True):
        """
        SITREP 텍스트를 ThreatEvent로 변환
        
        Args:
            sitrep_text: 상황보고 텍스트
            mission_id: 임무ID
            use_llm: LLM 사용 여부
            
        Returns:
            ThreatEvent 객체
        """
        return self.sitrep_parser.parse_sitrep_to_threat_event(
            sitrep_text, mission_id, use_llm=use_llm
        )
    
    def generate_explanation(
        self,
        coa_result,
        axis_states: List,
        language: str = 'ko',
        use_llm: bool = True
    ) -> str:
        """
        COA 설명문 생성
        
        Args:
            coa_result: COAEvaluationResult 객체
            axis_states: 축선별 전장상태 리스트
            language: 언어 ('ko' 또는 'en')
            use_llm: LLM 사용 여부
            
        Returns:
            설명문 텍스트
        """
        return self.explanation_generator.generate_coa_explanation(
            coa_result, axis_states, language=language, use_llm=use_llm
        )
    
    def search_references(
        self,
        query: str,
        top_k: int = 5,
        coa_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        교범/지침 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 k개 결과
            coa_context: COA 컨텍스트 (선택적)
            
        Returns:
            검색 결과 리스트
        """
        return self.doctrine_search.search_doctrine_references(
            query, top_k=top_k, coa_context=coa_context
        )
    
    def search_similar_cases(
        self,
        coa,
        axis_states: List,
        top_k: int = 3
    ) -> List[Dict]:
        """
        유사 작전 사례 검색
        
        Args:
            coa: COA 객체
            axis_states: 축선별 전장상태 리스트
            top_k: 반환할 상위 k개 결과
            
        Returns:
            유사 사례 리스트
        """
        return self.doctrine_search.search_similar_operations(
            coa, axis_states, top_k=top_k
        )

