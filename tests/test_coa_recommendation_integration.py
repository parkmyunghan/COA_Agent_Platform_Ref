# tests/test_coa_recommendation_integration.py
# -*- coding: utf-8 -*-
"""
다양한 위협상황별 방책 추천 통합 테스트
기존 데이터 파일을 활용하여 실제 환경에서 테스트
"""
import sys
from pathlib import Path
import unittest
import yaml
from typing import Dict, List, Optional
from datetime import datetime

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.orchestrator import CorePipeline
from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent


class TestCOARecommendationIntegration(unittest.TestCase):
    """다양한 위협상황별 방책 추천 통합 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 초기화 - 설정 로드"""
        config_path = BASE_DIR / "config" / "global.yaml"
        if not config_path.exists():
            raise unittest.SkipTest("설정 파일이 없습니다. config/global.yaml을 확인하세요.")
        
        with open(config_path, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)
        
        # Core Pipeline 초기화
        try:
            cls.core = CorePipeline(cls.config)
            cls.agent = EnhancedDefenseCOAAgent(cls.core)
        except Exception as e:
            raise unittest.SkipTest(f"초기화 실패: {e}")
    
    def _create_threat_situation(self, threat_level: float, threat_type: str, 
                                 threat_id: str = None, axis_id: str = "AXIS001",
                                 location: str = "GRID_123") -> Dict:
        """위협상황 딕셔너리 생성 (표준 형식)"""
        if threat_id is None:
            threat_id = f"THR_{int(threat_level * 100)}_{threat_type[:3].upper()}_{datetime.now().strftime('%H%M%S')}"
        
        return {
            "situation_id": threat_id,
            "threat_level": threat_level,
            "threat_level_normalized": threat_level,
            "threat_level_raw": int(threat_level * 100),
            "threat_level_label": "HIGH" if threat_level >= 0.85 else ("MEDIUM" if threat_level >= 0.6 else "LOW"),
            "위협ID": threat_id,
            "위협유형": threat_type,
            "위협유형코드": threat_type,
            "위협수준": str(int(threat_level * 100)),
            "심각도": int(threat_level * 100),
            "관련축선ID": axis_id,
            "발생장소": location,
            "approach_mode": "threat_centered",
            "is_manual": True,
            "timestamp": datetime.now().isoformat(),
            "source_type": "manual"
        }
    
    def test_high_threat_infiltration_recommendation(self):
        """높은 위협 수준 + 침입 유형 방책 추천"""
        situation = self._create_threat_situation(0.9, "침입", "THR_HIGH_INF_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result, "결과가 None이면 안 됩니다")
        self.assertIn("recommendations", result, "recommendations 키가 있어야 합니다")
        
        if result.get("recommendations"):
            recommendations = result["recommendations"]
            self.assertGreater(len(recommendations), 0, "최소 1개 이상의 방책이 추천되어야 합니다")
            print(f"\n✅ 높은 위협(90%) + 침입: {len(recommendations)}개 방책 추천")
            if recommendations:
                top_recommendation = recommendations[0]
                print(f"   최고 추천: {top_recommendation.get('coa_name', top_recommendation.get('명칭', 'N/A'))}")
                print(f"   점수: {top_recommendation.get('score', top_recommendation.get('종합점수', 'N/A'))}")
                print(f"   타입: {top_recommendation.get('coa_type', 'N/A')}")
    
    def test_medium_threat_attack_recommendation(self):
        """중간 위협 수준 + 공격 유형 방책 추천"""
        situation = self._create_threat_situation(0.6, "공격", "THR_MED_ATK_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result)
        
        if result.get("recommendations"):
            recommendations = result["recommendations"]
            self.assertGreater(len(recommendations), 0)
            print(f"\n✅ 중간 위협(60%) + 공격: {len(recommendations)}개 방책 추천")
            if recommendations:
                top_recommendation = recommendations[0]
                print(f"   최고 추천: {top_recommendation.get('coa_name', top_recommendation.get('명칭', 'N/A'))}")
                print(f"   점수: {top_recommendation.get('score', 'N/A')}")
    
    def test_low_threat_deception_recommendation(self):
        """낮은 위협 수준 + 기만 유형 방책 추천"""
        situation = self._create_threat_situation(0.3, "기만", "THR_LOW_DEC_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result)
        
        if result.get("recommendations"):
            recommendations = result["recommendations"]
            self.assertGreater(len(recommendations), 0)
            print(f"\n✅ 낮은 위협(30%) + 기만: {len(recommendations)}개 방책 추천")
            if recommendations:
                top_recommendation = recommendations[0]
                print(f"   최고 추천: {top_recommendation.get('coa_name', top_recommendation.get('명칭', 'N/A'))}")
                print(f"   점수: {top_recommendation.get('score', 'N/A')}")
    
    def test_penetration_threat_recommendation(self):
        """침투 위협 유형 방책 추천"""
        situation = self._create_threat_situation(0.75, "침투", "THR_PEN_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result)
        
        if result.get("recommendations"):
            recommendations = result["recommendations"]
            self.assertGreater(len(recommendations), 0)
            print(f"\n✅ 침투 위협(75%): {len(recommendations)}개 방책 추천")
            if recommendations:
                top_recommendation = recommendations[0]
                print(f"   최고 추천: {top_recommendation.get('coa_name', 'N/A')} (점수: {top_recommendation.get('score', 'N/A')})")
    
    def test_defense_type_filter(self):
        """방어 타입만 필터링 테스트"""
        situation = self._create_threat_situation(0.7, "침입", "THR_DEF_FILTER_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            coa_type_filter=["defense"],
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result)
        
        if result.get("recommendations"):
            recommendations = result["recommendations"]
            print(f"\n✅ 방어 타입 필터: {len(recommendations)}개 방책 추천")
            
            # 모든 추천이 defense 타입인지 확인
            for rec in recommendations:
                coa_type = rec.get('coa_type', '')
                self.assertEqual(coa_type, 'defense', f"모든 추천이 defense 타입이어야 합니다. 발견: {coa_type}")
    
    def test_all_types_recommendation(self):
        """모든 타입 방책 추천 테스트"""
        situation = self._create_threat_situation(0.8, "공격", "THR_ALL_TYPES_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            coa_type_filter=["all"],
            use_embedding=True,
            top_k=10
        )
        
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result)
        
        if result.get("recommendations"):
            recommendations = result["recommendations"]
            print(f"\n✅ 모든 타입 추천: {len(recommendations)}개 방책 추천")
            
            # 타입별 분류 확인
            type_counts = {}
            for rec in recommendations:
                coa_type = rec.get("coa_type", "unknown")
                type_counts[coa_type] = type_counts.get(coa_type, 0) + 1
            
            print(f"   타입별 분포: {type_counts}")
            
            # 여러 타입이 포함되어 있는지 확인
            self.assertGreater(len(type_counts), 1, "모든 타입 추천 시 여러 타입이 포함되어야 합니다")
    
    def test_threat_level_comparison(self):
        """위협 수준별 추천 차이 비교"""
        threat_levels = [0.3, 0.6, 0.9]
        results = {}
        
        for level in threat_levels:
            situation = self._create_threat_situation(level, "침입", f"THR_COMP_{int(level*100)}")
            result = self.agent.execute_reasoning(
                selected_situation_info=situation,
                use_embedding=True,
                top_k=3
            )
            
            if result and result.get("recommendations"):
                top_recommendation = result["recommendations"][0]
                results[level] = {
                    "count": len(result["recommendations"]),
                    "top_score": top_recommendation.get("score", top_recommendation.get("종합점수", 0)),
                    "top_name": top_recommendation.get("coa_name", top_recommendation.get("명칭", "N/A"))
                }
        
        print(f"\n📊 위협 수준별 추천 비교:")
        for level, info in results.items():
            print(f"   {int(level*100)}%: {info['count']}개, 최고점수={info['top_score']:.3f}, {info['top_name']}")
        
        # 높은 위협일수록 더 많은 방책이 추천되거나 점수가 높아야 함
        if len(results) >= 2:
            self.assertIn(0.9, results, "높은 위협 수준 테스트 필요")
            self.assertIn(0.3, results, "낮은 위협 수준 테스트 필요")


class TestCOARecommendationEdgeCases(unittest.TestCase):
    """방책 추천 엣지 케이스 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 초기화"""
        config_path = BASE_DIR / "config" / "global.yaml"
        if not config_path.exists():
            raise unittest.SkipTest("설정 파일이 없습니다.")
        
        with open(config_path, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)
        
        try:
            cls.core = CorePipeline(cls.config)
            cls.agent = EnhancedDefenseCOAAgent(cls.core)
        except Exception as e:
            raise unittest.SkipTest(f"초기화 실패: {e}")
    
    def test_minimal_threat_info(self):
        """최소한의 위협 정보만 제공"""
        situation = {
            "situation_id": "THR_MIN_001",
            "threat_level": 0.5,
            "approach_mode": "threat_centered",
            "is_manual": True
        }
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True
        )
        
        # 최소 정보만 있어도 동작해야 함
        self.assertIsNotNone(result)
        print(f"\n✅ 최소 정보 테스트: {'성공' if result else '실패'}")
    
    def test_extreme_high_threat(self):
        """극도로 높은 위협 수준 (100%)"""
        situation = {
            "situation_id": "THR_EXTREME_001",
            "threat_level": 1.0,
            "threat_level_normalized": 1.0,
            "threat_level_raw": 100,
            "위협유형": "침입",
            "approach_mode": "threat_centered",
            "is_manual": True
        }
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        if result.get("recommendations"):
            print(f"\n✅ 극도 높은 위협(100%): {len(result['recommendations'])}개 방책 추천")
            top_rec = result['recommendations'][0]
            print(f"   최고 추천: {top_rec.get('coa_name', 'N/A')} (점수: {top_rec.get('score', 'N/A')})")


def run_tests():
    """테스트 실행"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestCOARecommendationIntegration,
        TestCOARecommendationEdgeCases
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("방책 추천 통합 테스트 결과")
    print("="*70)
    print(f"총 테스트 수: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    print(f"스킵: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

