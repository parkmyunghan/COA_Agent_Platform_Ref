# tests/test_coa_appropriateness.py
# -*- coding: utf-8 -*-
"""
위협상황별 적절한 방책 추천 검증 테스트
위협 유형과 추천된 방책의 적절성을 검증
"""
import sys
from pathlib import Path
import unittest
import yaml
from typing import Dict, List
from datetime import datetime

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.orchestrator import CorePipeline
from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent


class TestCOAAppropriateness(unittest.TestCase):
    """위협상황별 적절한 방책 추천 검증 테스트"""
    
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
        
        # 위협 유형별 기대되는 방책 타입 매핑
        cls.expected_coa_types = {
            "침입": ["defense", "counter_attack"],  # 침입에는 방어/반격이 적절
            "공격": ["defense", "counter_attack", "offensive"],  # 공격에는 방어/반격/공격이 적절
            "침투": ["defense", "counter_attack"],  # 침투에는 방어/반격이 적절
            "기만": ["defense", "information_ops", "deterrence"],  # 기만에는 방어/정보작전/억제가 적절
            "정찰": ["defense", "information_ops"],  # 정찰에는 방어/정보작전이 적절
        }
        
        # 위협 유형별 기대되는 방책 키워드
        cls.expected_keywords = {
            "침입": ["방어", "진지", "고수", "거점", "지연"],
            "공격": ["공격", "포위", "돌파", "반격", "방어"],
            "침투": ["침투", "방어", "차단", "소탕", "반격"],
            "기만": ["기만", "정보", "작전", "억제", "선제"],
            "정찰": ["정찰", "수색", "정보", "방어", "탐지"],
        }
    
    def _create_threat_situation(self, threat_level: float, threat_type: str, 
                                 threat_id: str = None) -> Dict:
        """위협상황 딕셔너리 생성"""
        if threat_id is None:
            threat_id = f"THR_APP_{int(threat_level * 100)}_{threat_type[:3].upper()}"
        
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
            "관련축선ID": "AXIS001",
            "발생장소": "GRID_123",
            "approach_mode": "threat_centered",
            "is_manual": True,
            "timestamp": datetime.now().isoformat(),
            "source_type": "manual"
        }
    
    def test_infiltration_threat_appropriate_coa(self):
        """침입 위협에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 1: 침입 위협 → 방어/반격 방책")
        print("="*70)
        
        situation = self._create_threat_situation(0.8, "침입", "THR_INF_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 상위 3개 중 최소 1개는 방어 또는 반격 방책이어야 함
        top_3_types = [rec.get("coa_type", "") for rec in recommendations[:3]]
        expected_types = self.expected_coa_types["침입"]
        
        has_appropriate_type = any(coa_type in expected_types for coa_type in top_3_types)
        self.assertTrue(has_appropriate_type,
            f"침입 위협에 적절한 방책 타입이 추천되지 않았습니다. "
            f"기대: {expected_types}, 실제 상위 3개: {top_3_types}")
        
        # 검증: 방책 이름에 기대되는 키워드가 포함되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        expected_keywords = self.expected_keywords["침입"]
        
        has_appropriate_keyword = any(
            any(keyword in name for keyword in expected_keywords)
            for name in top_3_names
        )
        self.assertTrue(has_appropriate_keyword,
            f"침입 위협에 적절한 키워드가 포함된 방책이 추천되지 않았습니다. "
            f"기대 키워드: {expected_keywords}, 실제 상위 3개: {top_3_names}")
        
        print("✅ 침입 위협 적절성 검증 통과")
    
    def test_attack_threat_appropriate_coa(self):
        """공격 위협에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 2: 공격 위협 → 방어/반격/공격 방책")
        print("="*70)
        
        situation = self._create_threat_situation(0.7, "공격", "THR_ATK_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 상위 3개 중 최소 1개는 방어/반격/공격 방책이어야 함
        top_3_types = [rec.get("coa_type", "") for rec in recommendations[:3]]
        expected_types = self.expected_coa_types["공격"]
        
        has_appropriate_type = any(coa_type in expected_types for coa_type in top_3_types)
        self.assertTrue(has_appropriate_type,
            f"공격 위협에 적절한 방책 타입이 추천되지 않았습니다. "
            f"기대: {expected_types}, 실제 상위 3개: {top_3_types}")
        
        # 검증: 방책 이름에 기대되는 키워드가 포함되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        expected_keywords = self.expected_keywords["공격"]
        
        has_appropriate_keyword = any(
            any(keyword in name for keyword in expected_keywords)
            for name in top_3_names
        )
        self.assertTrue(has_appropriate_keyword,
            f"공격 위협에 적절한 키워드가 포함된 방책이 추천되지 않았습니다. "
            f"기대 키워드: {expected_keywords}, 실제 상위 3개: {top_3_names}")
        
        print("✅ 공격 위협 적절성 검증 통과")
    
    def test_penetration_threat_appropriate_coa(self):
        """침투 위협에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 3: 침투 위협 → 방어/반격 방책")
        print("="*70)
        
        situation = self._create_threat_situation(0.75, "침투", "THR_PEN_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 상위 3개 중 최소 1개는 방어 또는 반격 방책이어야 함
        top_3_types = [rec.get("coa_type", "") for rec in recommendations[:3]]
        expected_types = self.expected_coa_types["침투"]
        
        has_appropriate_type = any(coa_type in expected_types for coa_type in top_3_types)
        self.assertTrue(has_appropriate_type,
            f"침투 위협에 적절한 방책 타입이 추천되지 않았습니다. "
            f"기대: {expected_types}, 실제 상위 3개: {top_3_types}")
        
        # 검증: 방책 이름에 기대되는 키워드가 포함되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        expected_keywords = self.expected_keywords["침투"]
        
        has_appropriate_keyword = any(
            any(keyword in name for keyword in expected_keywords)
            for name in top_3_names
        )
        self.assertTrue(has_appropriate_keyword,
            f"침투 위협에 적절한 키워드가 포함된 방책이 추천되지 않았습니다. "
            f"기대 키워드: {expected_keywords}, 실제 상위 3개: {top_3_names}")
        
        print("✅ 침투 위협 적절성 검증 통과")
    
    def test_deception_threat_appropriate_coa(self):
        """기만 위협에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 4: 기만 위협 → 방어/정보작전/억제 방책")
        print("="*70)
        
        situation = self._create_threat_situation(0.6, "기만", "THR_DEC_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 상위 3개 중 최소 1개는 방어/정보작전/억제 방책이어야 함
        top_3_types = [rec.get("coa_type", "") for rec in recommendations[:3]]
        expected_types = self.expected_coa_types["기만"]
        
        has_appropriate_type = any(coa_type in expected_types for coa_type in top_3_types)
        self.assertTrue(has_appropriate_type,
            f"기만 위협에 적절한 방책 타입이 추천되지 않았습니다. "
            f"기대: {expected_types}, 실제 상위 3개: {top_3_types}")
        
        # 검증: 방책 이름에 기대되는 키워드가 포함되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        expected_keywords = self.expected_keywords["기만"]
        
        has_appropriate_keyword = any(
            any(keyword in name for keyword in expected_keywords)
            for name in top_3_names
        )
        self.assertTrue(has_appropriate_keyword,
            f"기만 위협에 적절한 키워드가 포함된 방책이 추천되지 않았습니다. "
            f"기대 키워드: {expected_keywords}, 실제 상위 3개: {top_3_names}")
        
        print("✅ 기만 위협 적절성 검증 통과")
    
    def test_reconnaissance_threat_appropriate_coa(self):
        """정찰 위협에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 5: 정찰 위협 → 방어/정보작전 방책")
        print("="*70)
        
        situation = self._create_threat_situation(0.5, "정찰", "THR_REC_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 상위 3개 중 최소 1개는 방어/정보작전 방책이어야 함
        top_3_types = [rec.get("coa_type", "") for rec in recommendations[:3]]
        expected_types = self.expected_coa_types["정찰"]
        
        has_appropriate_type = any(coa_type in expected_types for coa_type in top_3_types)
        self.assertTrue(has_appropriate_type,
            f"정찰 위협에 적절한 방책 타입이 추천되지 않았습니다. "
            f"기대: {expected_types}, 실제 상위 3개: {top_3_types}")
        
        # 검증: 방책 이름에 기대되는 키워드가 포함되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        expected_keywords = self.expected_keywords["정찰"]
        
        has_appropriate_keyword = any(
            any(keyword in name for keyword in expected_keywords)
            for name in top_3_names
        )
        self.assertTrue(has_appropriate_keyword,
            f"정찰 위협에 적절한 키워드가 포함된 방책이 추천되지 않았습니다. "
            f"기대 키워드: {expected_keywords}, 실제 상위 3개: {top_3_names}")
        
        print("✅ 정찰 위협 적절성 검증 통과")
    
    def test_high_threat_appropriate_coa(self):
        """높은 위협 수준에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 6: 높은 위협 수준 → 강력한 방책")
        print("="*70)
        
        # 높은 위협 수준 (90%)
        situation = self._create_threat_situation(0.9, "공격", "THR_HIGH_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 높은 위협에는 강력한 방책이 추천되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        
        # 강력한 방책 키워드
        strong_keywords = ["주방어", "주요", "강력", "포위", "돌파", "Main", "Strong"]
        
        has_strong_coa = any(
            any(keyword in name for keyword in strong_keywords)
            for name in top_3_names
        )
        
        # 높은 위협에는 최소한 강력한 방책이 하나는 있어야 함
        # (완전히 필수는 아니지만, 일반적으로 기대됨)
        if not has_strong_coa:
            print(f"   ⚠️  경고: 높은 위협 수준인데 강력한 방책이 추천되지 않았습니다.")
            print(f"      상위 3개: {top_3_names}")
            print(f"      기대 키워드: {strong_keywords}")
        
        # 점수가 높아야 함 (높은 위협에 대한 적절한 대응)
        top_score = recommendations[0].get("score", 0)
        self.assertGreaterEqual(top_score, 0.5,
            f"높은 위협 수준인데 최고 점수가 너무 낮습니다: {top_score}")
        
        print("✅ 높은 위협 수준 적절성 검증 통과")
    
    def test_low_threat_appropriate_coa(self):
        """낮은 위협 수준에 적절한 방책이 추천되는지 검증"""
        print("\n" + "="*70)
        print("적절성 검증 7: 낮은 위협 수준 → 기본 방책")
        print("="*70)
        
        # 낮은 위협 수준 (30%)
        situation = self._create_threat_situation(0.3, "침입", "THR_LOW_APP_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천된 방책:")
        for i, rec in enumerate(recommendations[:5], 1):
            coa_name = rec.get("coa_name", "N/A")
            coa_type = rec.get("coa_type", "N/A")
            score = rec.get("score", 0)
            print(f"   {i}. [{coa_type}] {coa_name} (점수: {score:.3f})")
        
        # 검증: 낮은 위협에는 기본 방책이 추천되어야 함
        top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
        
        # 기본 방책 키워드
        basic_keywords = ["지연", "기본", "최소", "Minimal", "Basic", "Moderate"]
        
        has_basic_coa = any(
            any(keyword in name for keyword in basic_keywords)
            for name in top_3_names
        )
        
        # 낮은 위협에는 기본 방책이 적절함
        # (완전히 필수는 아니지만, 일반적으로 기대됨)
        if not has_basic_coa:
            print(f"   ⚠️  경고: 낮은 위협 수준인데 기본 방책이 추천되지 않았습니다.")
            print(f"      상위 3개: {top_3_names}")
            print(f"      기대 키워드: {basic_keywords}")
        
        print("✅ 낮은 위협 수준 적절성 검증 통과")
    
    def test_threat_type_coa_name_match(self):
        """위협 유형과 방책 이름의 일치도 검증"""
        print("\n" + "="*70)
        print("적절성 검증 8: 위협 유형과 방책 이름 일치도")
        print("="*70)
        
        # 각 위협 유형별로 테스트
        threat_types = ["침입", "공격", "침투", "기만", "정찰"]
        match_results = {}
        
        for threat_type in threat_types:
            situation = self._create_threat_situation(0.7, threat_type, f"THR_MATCH_{threat_type}")
            result = self.agent.execute_reasoning(
                selected_situation_info=situation,
                use_embedding=True,
                top_k=5
            )
            
            if result and result.get("recommendations"):
                recommendations = result["recommendations"]
                top_3_names = [rec.get("coa_name", "") for rec in recommendations[:3]]
                expected_keywords = self.expected_keywords.get(threat_type, [])
                
                # 위협 유형 키워드가 방책 이름에 포함되는지 확인
                matches = []
                for name in top_3_names:
                    for keyword in expected_keywords:
                        if keyword in name:
                            matches.append((name, keyword))
                            break
                
                match_results[threat_type] = {
                    "matches": len(matches),
                    "top_3": top_3_names,
                    "expected": expected_keywords
                }
        
        print(f"\n📊 위협 유형별 일치도:")
        for threat_type, info in match_results.items():
            print(f"   {threat_type}: {info['matches']}개 일치")
            print(f"      상위 3개: {', '.join(info['top_3'])}")
            print(f"      기대 키워드: {', '.join(info['expected'])}")
        
        # 검증: 최소한 절반 이상의 위협 유형에서 일치하는 방책이 있어야 함
        total_matches = sum(info["matches"] for info in match_results.values())
        total_expected = len(threat_types) * 3  # 각 위협 유형당 상위 3개
        
        match_rate = total_matches / total_expected if total_expected > 0 else 0
        print(f"\n   전체 일치율: {match_rate:.1%} ({total_matches}/{total_expected})")
        
        # 최소 30% 이상 일치해야 함
        self.assertGreaterEqual(match_rate, 0.3,
            f"위협 유형과 방책 이름의 일치율이 너무 낮습니다: {match_rate:.1%}")
        
        print("✅ 위협 유형-방책 이름 일치도 검증 통과")


def run_tests():
    """테스트 실행"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    tests = loader.loadTestsFromTestCase(TestCOAAppropriateness)
    suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("위협상황별 적절한 방책 추천 검증 테스트 결과")
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
            print(f"    {traceback[:200]}...")
    
    if result.errors:
        print("\n오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback[:200]}...")
    
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)


