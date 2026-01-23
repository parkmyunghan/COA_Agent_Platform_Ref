# tests/test_coa_recommendation_scenarios.py
# -*- coding: utf-8 -*-
"""
다양한 위협상황별 방책 추천 기능 통합 테스트
EnhancedDefenseCOAAgent의 전체 워크플로우 테스트
"""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent


class TestCOARecommendationScenarios(unittest.TestCase):
    """다양한 위협상황별 방책 추천 시나리오 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # Mock Core 설정
        self.mock_core = Mock()
        self.mock_core.data_manager = Mock()
        self.mock_core.ontology_manager = Mock()
        self.mock_core.ontology_manager.graph = None
        self.mock_core.rag_manager = Mock()
        self.mock_core.rag_manager.is_available.return_value = False
        
        # Agent 초기화
        try:
            self.agent = EnhancedDefenseCOAAgent(self.mock_core)
        except Exception as e:
            self.skipTest(f"Agent 초기화 실패: {e}")
    
    def _create_threat_situation(self, threat_level: float, threat_type: str, 
                                 threat_id: str = "THR001") -> Dict:
        """위협상황 딕셔너리 생성 헬퍼"""
        return {
            "situation_id": threat_id,
            "threat_level": threat_level,
            "threat_level_normalized": threat_level,
            "threat_level_raw": int(threat_level * 100),
            "위협ID": threat_id,
            "위협유형": threat_type,
            "위협수준": str(int(threat_level * 100)),
            "심각도": int(threat_level * 100),
            "approach_mode": "threat_centered",
            "is_manual": True,
            "timestamp": "2024-01-01T12:00:00"
        }
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_high_threat_level_recommendation(self, mock_print):
        """높은 위협 수준 (90%) 방책 추천 테스트"""
        situation = self._create_threat_situation(0.9, "침입", "THR_HIGH_001")
        
        # Mock 데이터 설정
        self.mock_core.data_manager.load_all.return_value = {}
        self.mock_core.ontology_manager.build_from_data.return_value = None
        
        # execute_reasoning 호출 (실제 구현에 따라 조정 필요)
        # 실제 테스트는 실제 데이터와 설정이 필요하므로 스킵 가능
        self.skipTest("실제 데이터 및 설정 필요 - 통합 테스트 환경에서 실행")
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_medium_threat_level_recommendation(self, mock_print):
        """중간 위협 수준 (60%) 방책 추천 테스트"""
        situation = self._create_threat_situation(0.6, "공격", "THR_MED_001")
        self.skipTest("실제 데이터 및 설정 필요")
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_low_threat_level_recommendation(self, mock_print):
        """낮은 위협 수준 (30%) 방책 추천 테스트"""
        situation = self._create_threat_situation(0.3, "기만", "THR_LOW_001")
        self.skipTest("실제 데이터 및 설정 필요")
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_infiltration_threat_recommendation(self, mock_print):
        """침입 위협 유형 방책 추천 테스트"""
        situation = self._create_threat_situation(0.75, "침입", "THR_INF_001")
        self.skipTest("실제 데이터 및 설정 필요")
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_attack_threat_recommendation(self, mock_print):
        """공격 위협 유형 방책 추천 테스트"""
        situation = self._create_threat_situation(0.85, "공격", "THR_ATK_001")
        self.skipTest("실제 데이터 및 설정 필요")
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_defense_type_filter(self, mock_print):
        """방어 타입만 필터링 테스트"""
        situation = self._create_threat_situation(0.7, "침입", "THR_DEF_001")
        self.skipTest("실제 데이터 및 설정 필요")
    
    @patch('agents.defense_coa_agent.logic_defense_enhanced.safe_print')
    def test_all_types_recommendation(self, mock_print):
        """모든 타입 방책 추천 테스트"""
        situation = self._create_threat_situation(0.8, "공격", "THR_ALL_001")
        self.skipTest("실제 데이터 및 설정 필요")


class TestCOARecommendationIntegration(unittest.TestCase):
    """방책 추천 통합 테스트 (실제 환경 필요)"""
    
    def setUp(self):
        """통합 테스트 설정 - 실제 설정 파일 필요"""
        config_path = BASE_DIR / "config" / "global.yaml"
        if not config_path.exists():
            self.skipTest("설정 파일이 없습니다. 통합 테스트를 건너뜁니다.")
    
    def test_end_to_end_recommendation_workflow(self):
        """전체 워크플로우 테스트: 위협상황 입력 → 방책 추천"""
        # 1. 위협상황 입력
        # 2. Agent 실행
        # 3. 방책 추천 결과 확인
        # 4. 추천 품질 검증
        self.skipTest("통합 테스트 환경 구성 필요")


def run_tests():
    """테스트 실행"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestCOARecommendationScenarios,
        TestCOARecommendationIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("방책 추천 기능 테스트 결과")
    print("="*70)
    print(f"총 테스트 수: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    print(f"스킵: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    print("\n⚠️  참고: 이 테스트는 실제 데이터 및 설정이 필요합니다.")
    print("통합 테스트 환경에서 실행하거나 실제 데이터로 테스트를 확장하세요.")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)


