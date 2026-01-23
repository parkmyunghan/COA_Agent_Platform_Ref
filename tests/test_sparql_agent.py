import unittest
import sys
import os
from unittest.mock import MagicMock

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.ontology_agent.sparql_agent import SparqlQueryAgent
from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager

class MockLLMManager:
    """테스트용 Mock LLM Manager"""
    def generate(self, prompt, max_tokens=None):
        if "[Ontology Schema]" in prompt:
            # SPARQL 생성 요청인 경우
            return """
            ```sparql
            PREFIX def: <http://coa-agent-platform.org/ontology#>
            SELECT ?weapon WHERE {
                ?weapon def:effectiveAgainst ?target .
                FILTER(CONTAINS(STR(?target), "Mechanized"))
            }
            ```
            """
        else:
            # 답변 생성 요청인 경우
            return "기계화부대에 효과적인 무기체계로는 대전차 미사일, 공격헬기 등이 있습니다."

class TestSparqlAgent(unittest.TestCase):
    def setUp(self):
        # Config 설정
        self.config = {
            "ontology_path": "./knowledge/ontology",
            "metadata_path": "./metadata"
        }
        
        # Manager 초기화
        self.ontology_manager = EnhancedOntologyManager(self.config)
        
        # [FIX] 그래프에 샘플 데이터 주입 (Mocking)
        if self.ontology_manager.graph is not None:
            try:
                from rdflib import URIRef, RDF, RDFS, Namespace, OWL
                ns = Namespace("http://coa-agent-platform.org/ontology#")
                
                # 클래스 정의
                self.ontology_manager.graph.add((ns.MechanizedUnit, RDF.type, RDFS.Class))
                self.ontology_manager.graph.add((ns.AntiTankWeapon, RDF.type, RDFS.Class))
                
                # 속성 정의
                self.ontology_manager.graph.add((ns.effectiveAgainst, RDF.type, OWL.ObjectProperty))
                
                print("[Test] In-memory graph initialized with mock data.")
            except ImportError:
                print("[Test] rdflib not found, skipping graph population.")

        self.llm_manager = MockLLMManager()
        
        # Agent 생성
        self.agent = SparqlQueryAgent(self.llm_manager, self.ontology_manager)
        
    def test_end_to_end_flow(self):
        """자연어 질문 -> SPARQL -> 답변 End-to-End 테스트"""
        question = "기계화부대에 효과적인 무기체계는 무엇인가?"
        
        print(f"\n[Test] 질문: {question}")
        
        # 1. 스키마 추출 테스트
        schema = self.ontology_manager.get_schema_summary()
        print(f"[Schema Summary] {schema[:100]}...")  # 앞부분만 출력
        self.assertIn("Classes", schema)
        
        # 2. SPARQL 생성 테스트 (Mock LLM)
        sparql = self.agent._generate_sparql(question, schema)
        print(f"[Generated SPARQL]\n{sparql}")
        self.assertIn("SELECT", sparql)
        
        # 3. 전체 흐름 실행
        # (실제 쿼리 실행은 온톨로지 데이터가 없으면 빈 리스트를 반환하지만 오류는 안 나야 함)
        answer = self.agent.answer_question(question)
        print(f"[Agent Answer] {answer}")
        
        self.assertIsNotNone(answer)
        self.assertNotEqual(answer, "죄송합니다. 쿼리를 생성할 수 없습니다.")

if __name__ == '__main__':
    unittest.main()
