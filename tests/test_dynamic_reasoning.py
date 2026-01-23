import unittest
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_pipeline.reasoning_engine import ReasoningEngine
from core_pipeline.coa_engine.coa_models import COA
from core_pipeline.data_models import AxisState

class TestDynamicReasoning(unittest.TestCase):
    def setUp(self):
        self.engine = ReasoningEngine()
        
    def test_calculate_dynamic_score(self):
        # 테스트 케이스 1: 기계화부대 COA
        mech_coa = COA(
            coa_id="COA_MECH_001",
            coa_name="기계화부대 돌파",
            description="전차 및 장갑차를 이용한 신속한 돌파 작전",
            mission_id="M001"
        )
        
        # 1. 평지(Plains) 상황 - 보너스 예상
        context_plains = {'base_score': 0.5, 'terrain': 'Plains', 'weather': 'Clear'}
        score_plains = self.engine.calculate_dynamic_score(mech_coa, context_plains)
        print(f"\n[평지] 기계화부대 점수: {score_plains} (기본값 0.5)")
        
        # 2. 산악(Mountains) 상황 - 페널티 예상
        context_mountains = {'base_score': 0.5, 'terrain': 'Mountains', 'weather': 'Clear'}
        score_mountains = self.engine.calculate_dynamic_score(mech_coa, context_mountains)
        print(f"[산악] 기계화부대 점수: {score_mountains} (기본값 0.5)")
        
        # 검증: 평지 점수가 산악 점수보다 높아야 함
        self.assertGreater(score_plains, score_mountains)
        
        # 3. 악천후(Rain) 상황 - 항공 지원 페널티 확인
        air_coa = COA(
            coa_id="COA_AIR_001",
            coa_name="항공 근접지원",
            description="공격헬기를 이용한 화력 지원",
            mission_id="M001"
        )
        context_clear = {'base_score': 0.5, 'terrain': 'Plains', 'weather': 'Clear'}
        context_rain = {'base_score': 0.5, 'terrain': 'Plains', 'weather': 'Rain'}
        
        score_clear = self.engine.calculate_dynamic_score(air_coa, context_clear)
        score_rain = self.engine.calculate_dynamic_score(air_coa, context_rain)
        print(f"[맑음] 항공지원 점수: {score_clear}")
        print(f"[강우] 항공지원 점수: {score_rain}")
        
        # 검증: 맑은 날 점수가 비오는 날 점수보다 높아야 함
        self.assertGreater(score_clear, score_rain)
        
if __name__ == '__main__':
    unittest.main()
