import re
from typing import Dict, List, Optional
from core_pipeline.llm_manager import LLMManager
from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager

class SparqlQueryAgent:
    """
    자연어 질문을 SPARQL 쿼리로 변환하고 실행하는 에이전트
    """
    
    def __init__(self, llm_manager: LLMManager, ontology_manager: EnhancedOntologyManager):
        self.llm_manager = llm_manager
        self.ontology_manager = ontology_manager
    
    def answer_question(self, question: str) -> str:
        """
        자연어 질문에 대한 답변 생성 (End-to-End)
        Strategy:
        1. 질문 의도 파악
        2. SPARQL 생성
        3. 쿼리 실행
        4. 결과 요약 및 답변 생성
        """
        # 1. 스키마 정보 로드
        schema_summary = self.ontology_manager.get_schema_summary()
        
        # 2. SPARQL 생성
        sparql_query = self._generate_sparql(question, schema_summary)
        if not sparql_query:
            return "죄송합니다. 쿼리를 생성할 수 없습니다."
        
        print(f"[DEBUG] Generated SPARQL:\n{sparql_query}")
        
        # 3. 쿼리 실행
        try:
            results = self.ontology_manager.query(sparql_query, return_format='list')
        except Exception as e:
            return f"쿼리 실행 중 오류가 발생했습니다: {e}"
            
        # 4. 답변 생성
        answer = self._generate_natural_answer(question, results)
        return answer
        
    def _generate_sparql(self, question: str, schema_context: str) -> str:
        """LLM을 이용하여 SPARQL 쿼리 생성"""
        prompt = f"""
        당신은 온톨로지 전문가이자 SPARQL 마스터입니다.
        사용자의 질문을 온톨로지 지식그래프를 조회하기 위한 SPARQL 쿼리로 변환하세요.
        
        [Ontology Schema]
        {schema_context}
        
        [Prefixes]
        PREFIX def: <http://coa-agent-platform.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        [Rules]
        1. 오직 실행 가능한 SPARQL 쿼리만 작성하세요. (마크다운 코드 블록 제외)
        2. 반환되는 변수는 알아보기 쉽게 설정하세요 (예: ?name, ?type).
        3. 문자열 매칭 시 `FILTER(CONTAINS(LCASE(?label), "keyword"))` 를 사용하세요.
        
        [Question]
        "{question}"
        
        [SPARQL Query]
        """
        
        response = self.llm_manager.generate(prompt, max_tokens=200)
        
        # 코드 블록 제거나 트리밍 등 후처리
        query = response.strip().replace("```sparql", "").replace("```", "")
        return query
    
    def _generate_natural_answer(self, question: str, query_results: List[Dict]) -> str:
        """쿼리 결과를 바탕으로 자연어 답변 생성"""
        if not query_results:
            return "지식그래프에서 관련된 정보를 찾을 수 없습니다."
            
        prompt = f"""
        다음 질문에 대해 SPARQL 쿼리 실행 결과를 바탕으로 자연스러운 답변을 작성하세요.
        
        [Question]
        "{question}"
        
        [Query Results]
        {query_results}
        
        [Answer]
        """
        
        return self.llm_manager.generate(prompt)
