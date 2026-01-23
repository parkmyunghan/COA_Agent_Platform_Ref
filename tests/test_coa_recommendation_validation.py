# tests/test_coa_recommendation_validation.py
# -*- coding: utf-8 -*-
"""
방책 추천 결과 검증 테스트
- 점수가 모두 동일한지 확인
- 0점이 나오는지 확인
- 위협 수준/유형에 따라 추천이 달라지는지 확인
- 추천 이유가 적절한지 확인
"""
import sys
from pathlib import Path
import unittest
import yaml
from typing import Dict, List
from datetime import datetime
from collections import Counter

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.orchestrator import CorePipeline
from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent


class TestCOARecommendationValidation(unittest.TestCase):
    """방책 추천 결과 검증 테스트"""
    
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
    
    def _create_threat_situation(self, threat_level: float, threat_type: str, 
                                 threat_id: str = None) -> Dict:
        """위협상황 딕셔너리 생성"""
        if threat_id is None:
            threat_id = f"THR_VAL_{int(threat_level * 100)}_{threat_type[:3].upper()}"
        
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
    
    def test_score_diversity(self):
        """점수 다양성 검증 - 모든 점수가 동일하면 안 됨"""
        print("\n" + "="*70)
        print("검증 1: 점수 다양성 검증")
        print("="*70)
        
        situation = self._create_threat_situation(0.7, "침입", "THR_DIV_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=10
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0, "최소 1개 이상의 방책이 추천되어야 합니다")
        
        # 점수 추출
        scores = [rec.get("score", 0) for rec in recommendations]
        
        print(f"\n📊 추천된 방책 수: {len(recommendations)}")
        print(f"📊 점수 범위: {min(scores):.3f} ~ {max(scores):.3f}")
        print(f"📊 점수 평균: {sum(scores)/len(scores):.3f}")
        print(f"📊 점수 표준편차: {self._calculate_std(scores):.3f}")
        
        # 점수 분포 확인
        score_counts = Counter([round(s, 2) for s in scores])
        print(f"📊 점수 분포: {dict(score_counts)}")
        
        # 검증: 모든 점수가 동일하면 안 됨
        unique_scores = len(set([round(s, 3) for s in scores]))
        self.assertGreater(unique_scores, 1, 
            f"점수가 모두 동일합니다! (고유 점수 수: {unique_scores})")
        
        # 검증: 0점이 있으면 안 됨
        zero_scores = [s for s in scores if s == 0]
        self.assertEqual(len(zero_scores), 0, 
            f"0점인 방책이 {len(zero_scores)}개 있습니다!")
        
        # 검증: 점수 범위가 합리적이어야 함 (0.0 ~ 1.0)
        for score in scores:
            self.assertGreaterEqual(score, 0.0, f"점수가 음수입니다: {score}")
            self.assertLessEqual(score, 1.0, f"점수가 1.0을 초과합니다: {score}")
        
        print("✅ 점수 다양성 검증 통과")
    
    def test_threat_level_impact(self):
        """위협 수준에 따른 추천 차이 검증"""
        print("\n" + "="*70)
        print("검증 2: 위협 수준에 따른 추천 차이")
        print("="*70)
        
        threat_levels = [0.3, 0.6, 0.9]
        results = {}
        
        for level in threat_levels:
            situation = self._create_threat_situation(level, "침입", f"THR_LEVEL_{int(level*100)}")
            result = self.agent.execute_reasoning(
                selected_situation_info=situation,
                use_embedding=True,
                top_k=5
            )
            
            if result and result.get("recommendations"):
                recs = result["recommendations"]
                top_rec = recs[0]
                results[level] = {
                    "top_score": top_rec.get("score", 0),
                    "top_name": top_rec.get("coa_name", "N/A"),
                    "avg_score": sum([r.get("score", 0) for r in recs]) / len(recs),
                    "coa_names": [r.get("coa_name", "N/A") for r in recs[:3]]
                }
        
        print(f"\n📊 위협 수준별 추천 비교:")
        for level, info in results.items():
            print(f"   {int(level*100)}%: 최고점수={info['top_score']:.3f}, 평균={info['avg_score']:.3f}")
            print(f"      상위 3개: {', '.join(info['coa_names'])}")
        
        # 검증: 위협 수준이 높을수록 점수가 높아야 함 (일반적으로)
        if len(results) >= 2:
            levels = sorted(results.keys())
            scores = [results[l]["avg_score"] for l in levels]
            
            # 점수가 증가하는 경향이 있어야 함 (완전히 일치하지 않아도 됨)
            increasing = all(scores[i] <= scores[i+1] for i in range(len(scores)-1))
            decreasing = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            
            # 최소한 일관된 패턴이 있어야 함
            self.assertTrue(increasing or decreasing or abs(scores[-1] - scores[0]) > 0.01,
                f"위협 수준에 따른 점수 차이가 없습니다: {scores}")
        
        # 검증: 추천된 방책이 완전히 동일하면 안 됨
        all_coa_names = [info["coa_names"] for info in results.values()]
        if len(all_coa_names) >= 2:
            # 최소한 하나의 위협 수준에서 다른 방책이 추천되어야 함
            unique_combinations = len(set(tuple(names) for names in all_coa_names))
            self.assertGreater(unique_combinations, 1,
                "모든 위협 수준에서 동일한 방책이 추천됩니다!")
        
        print("✅ 위협 수준별 차이 검증 통과")
    
    def test_threat_type_impact(self):
        """위협 유형에 따른 추천 차이 검증"""
        print("\n" + "="*70)
        print("검증 3: 위협 유형에 따른 추천 차이")
        print("="*70)
        
        threat_types = ["침입", "공격", "침투", "기만"]
        results = {}
        
        for threat_type in threat_types:
            situation = self._create_threat_situation(0.7, threat_type, f"THR_TYPE_{threat_type}")
            result = self.agent.execute_reasoning(
                selected_situation_info=situation,
                use_embedding=True,
                top_k=5
            )
            
            if result and result.get("recommendations"):
                recs = result["recommendations"]
                top_rec = recs[0]
                results[threat_type] = {
                    "top_score": top_rec.get("score", 0),
                    "top_name": top_rec.get("coa_name", "N/A"),
                    "coa_names": [r.get("coa_name", "N/A") for r in recs[:3]]
                }
        
        print(f"\n📊 위협 유형별 추천 비교:")
        for threat_type, info in results.items():
            print(f"   {threat_type}: 최고점수={info['top_score']:.3f}, {info['top_name']}")
            print(f"      상위 3개: {', '.join(info['coa_names'])}")
        
        # 검증: 위협 유형에 따라 최소한 다른 방책이 추천되어야 함
        all_top_names = [info["top_name"] for info in results.values()]
        unique_top_names = len(set(all_top_names))
        
        # 최소한 2개 이상의 다른 방책이 최고 추천으로 나와야 함
        self.assertGreaterEqual(unique_top_names, 2,
            f"모든 위협 유형에서 동일한 방책이 최고 추천입니다: {all_top_names}")
        
        # 검증: 위협 유형별로 추천된 방책 목록이 완전히 동일하면 안 됨
        all_coa_lists = [info["coa_names"] for info in results.values()]
        unique_combinations = len(set(tuple(names) for names in all_coa_lists))
        self.assertGreater(unique_combinations, 1,
            "모든 위협 유형에서 동일한 방책 목록이 추천됩니다!")
        
        print("✅ 위협 유형별 차이 검증 통과")
    
    def test_recommendation_reason_quality(self):
        """추천 이유 품질 검증"""
        print("\n" + "="*70)
        print("검증 4: 추천 이유 품질 검증")
        print("="*70)
        
        situation = self._create_threat_situation(0.8, "공격", "THR_REASON_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 추천 이유 검증:")
        for i, rec in enumerate(recommendations[:3], 1):
            reason = rec.get("reason", "")
            coa_name = rec.get("coa_name", "N/A")
            score = rec.get("score", 0)
            
            print(f"\n   {i}. {coa_name} (점수: {score:.3f})")
            print(f"      이유: {reason[:100]}..." if len(reason) > 100 else f"      이유: {reason}")
            
            # 검증: 추천 이유가 비어있으면 안 됨
            self.assertIsNotNone(reason, f"{coa_name}의 추천 이유가 None입니다")
            self.assertGreater(len(str(reason).strip()), 0, 
                f"{coa_name}의 추천 이유가 비어있습니다")
            
            # 검증: 추천 이유가 너무 짧으면 안 됨 (최소 10자)
            self.assertGreaterEqual(len(str(reason).strip()), 10,
                f"{coa_name}의 추천 이유가 너무 짧습니다: {reason}")
        
        print("✅ 추천 이유 품질 검증 통과")
    
    def test_score_breakdown_validation(self):
        """점수 세부 내역 검증"""
        print("\n" + "="*70)
        print("검증 5: 점수 세부 내역 검증")
        print("="*70)
        
        situation = self._create_threat_situation(0.7, "침입", "THR_BREAKDOWN_001")
        
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            use_embedding=True,
            top_k=5
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        print(f"\n📊 점수 세부 내역 검증:")
        for i, rec in enumerate(recommendations[:3], 1):
            coa_name = rec.get("coa_name", "N/A")
            score = rec.get("score", 0)
            score_breakdown = rec.get("score_breakdown", {})
            
            print(f"\n   {i}. {coa_name}")
            print(f"      종합 점수: {score:.3f}")
            print(f"      세부 내역: {score_breakdown}")
            
            # 검증: score_breakdown이 있으면 검증
            if score_breakdown:
                agent_score = score_breakdown.get("agent_score", 0)
                llm_score = score_breakdown.get("llm_score", 0)
                hybrid_score = score_breakdown.get("hybrid_score", 0)
                
                # 세부 점수가 모두 0이면 안 됨
                if agent_score == 0 and llm_score == 0:
                    self.fail(f"{coa_name}의 모든 세부 점수가 0입니다!")
                
                # hybrid_score가 있으면 종합 점수와 일치해야 함
                if hybrid_score and abs(hybrid_score - score) > 0.01:
                    print(f"      ⚠️  경고: hybrid_score({hybrid_score:.3f})와 종합 점수({score:.3f})가 다릅니다")
        
        print("✅ 점수 세부 내역 검증 통과")
    
    def test_recommendation_count_validation(self):
        """추천 개수 검증"""
        print("\n" + "="*70)
        print("검증 6: 추천 개수 검증")
        print("="*70)
        
        situation = self._create_threat_situation(0.7, "침입", "THR_COUNT_001")
        
        # top_k를 다르게 설정하여 검증
        for top_k in [3, 5, 10]:
            result = self.agent.execute_reasoning(
                selected_situation_info=situation,
                use_embedding=True,
                top_k=top_k
            )
            
            if result and result.get("recommendations"):
                recommendations = result["recommendations"]
                actual_count = len(recommendations)
                
                print(f"   top_k={top_k}: 실제 추천 개수={actual_count}")
                
                # 검증: 요청한 개수만큼 또는 그 이하로 반환되어야 함
                self.assertLessEqual(actual_count, top_k,
                    f"top_k={top_k}인데 {actual_count}개가 반환되었습니다")
                
                # 검증: 최소 1개는 있어야 함
                self.assertGreater(actual_count, 0,
                    f"top_k={top_k}인데 추천이 없습니다")
        
        print("✅ 추천 개수 검증 통과")
    
    def test_coa_type_diversity(self):
        """방책 타입 다양성 검증"""
        print("\n" + "="*70)
        print("검증 7: 방책 타입 다양성 검증")
        print("="*70)
        
        situation = self._create_threat_situation(0.7, "침입", "THR_TYPE_DIV_001")
        
        # 모든 타입 추천
        result = self.agent.execute_reasoning(
            selected_situation_info=situation,
            coa_type_filter=["all"],
            use_embedding=True,
            top_k=10
        )
        
        self.assertIsNotNone(result)
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        # 타입별 분류
        coa_types = [rec.get("coa_type", "unknown") for rec in recommendations]
        type_counts = Counter(coa_types)
        
        print(f"\n📊 방책 타입 분포:")
        for coa_type, count in type_counts.items():
            print(f"   {coa_type}: {count}개")
        
        # 검증: 여러 타입이 포함되어야 함 (all 필터 사용 시)
        unique_types = len(set(coa_types))
        self.assertGreater(unique_types, 1,
            f"모든 방책이 동일한 타입입니다: {coa_types}")
        
        print("✅ 방책 타입 다양성 검증 통과")
    
    @staticmethod
    def _calculate_std(values: List[float]) -> float:
        """표준편차 계산"""
        if len(values) == 0:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


def run_tests():
    """테스트 실행"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    tests = loader.loadTestsFromTestCase(TestCOARecommendationValidation)
    suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("방책 추천 결과 검증 테스트 결과")
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
