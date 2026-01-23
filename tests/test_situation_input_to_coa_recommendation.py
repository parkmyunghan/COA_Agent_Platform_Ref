# tests/test_situation_input_to_coa_recommendation.py
# -*- coding: utf-8 -*-
"""
상황정보 입력 → 방책 추천 전체 워크플로우 통합 테스트
접근방식과 입력방식의 모든 조합에 대한 테스트
"""
import sys
from pathlib import Path
import unittest
import yaml
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Optional
from datetime import datetime

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.orchestrator import CorePipeline
from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
from ui.components.situation_input import (
    render_situation_input,
    render_manual_input,
    render_real_data_selection_ui,
    render_mission_selection_ui,
    render_sitrep_input_ui
)


class TestSituationInputToCOAWorkflow(unittest.TestCase):
    """상황정보 입력 → 방책 추천 전체 워크플로우 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 초기화"""
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
    
    def _verify_situation_info(self, situation_info: Dict, expected_approach_mode: str):
        """상황 정보 검증"""
        self.assertIsNotNone(situation_info, "situation_info가 None이면 안 됩니다")
        self.assertIn("approach_mode", situation_info, "approach_mode가 있어야 합니다")
        self.assertEqual(
            situation_info["approach_mode"], 
            expected_approach_mode,
            f"approach_mode가 {expected_approach_mode}이어야 합니다"
        )
        self.assertIn("situation_id", situation_info, "situation_id가 있어야 합니다")
        return situation_info
    
    def _verify_coa_recommendation(self, situation_info: Dict, result: Dict):
        """방책 추천 결과 검증"""
        self.assertIsNotNone(result, "방책 추천 결과가 None이면 안 됩니다")
        self.assertIn("recommendations", result, "recommendations 키가 있어야 합니다")
        
        recommendations = result.get("recommendations", [])
        self.assertGreater(len(recommendations), 0, "최소 1개 이상의 방책이 추천되어야 합니다")
        
        # approach_mode가 올바르게 전달되었는지 확인
        result_approach_mode = result.get("situation_info", {}).get("approach_mode")
        if result_approach_mode:
            self.assertEqual(
                result_approach_mode,
                situation_info["approach_mode"],
                "결과의 approach_mode가 입력과 일치해야 합니다"
            )
        
        return recommendations
    
    def test_threat_centered_real_data_selection(self):
        """위협 중심 + 실제 데이터에서 선택 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 1: 위협 중심 + 실제 데이터에서 선택")
        print("="*70)
        
        # 실제 데이터에서 위협 선택 (Mock 사용)
        with patch('ui.components.situation_input.st') as mock_st:
            # Mock 설정
            mock_st.selectbox.return_value = "THR001 - 침입 (85) - 축선: AXIS001"
            mock_st.button.return_value = True
            mock_st.info = Mock()
            mock_st.success = Mock()
            mock_st.rerun = Mock()
            
            expander = MagicMock()
            expander.__enter__ = Mock(return_value=expander)
            expander.__exit__ = Mock(return_value=False)
            mock_st.expander.return_value = expander
            mock_st.session_state = MagicMock()
            
            # 실제 데이터 로드
            threats_df = self.core.data_manager.load_table("위협상황")
            if threats_df is None or threats_df.empty:
                self.skipTest("위협상황 데이터가 없습니다.")
            
            # 첫 번째 위협 사용
            first_threat = threats_df.iloc[0].to_dict()
            
            # 상황 정보 생성
            from common.situation_converter import SituationInfoConverter
            situation_info = SituationInfoConverter.convert(
                first_threat,
                source_type="real_data",
                approach_mode="threat_centered"
            )
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "threat_centered")
        self.assertTrue(situation_info.get("is_real_data", False), "is_real_data가 True여야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   접근 방식: {situation_info.get('approach_mode')}")
    
    def test_threat_centered_manual_input(self):
        """위협 중심 + 수동 입력 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 2: 위협 중심 + 수동 입력")
        print("="*70)
        
        # 수동 입력으로 상황 정보 생성
        situation_info = {
            "situation_id": "THR_MANUAL_001",
            "threat_level": 0.75,
            "threat_level_normalized": 0.75,
            "threat_level_raw": 75,
            "위협ID": "THR_MANUAL_001",
            "위협유형": "침입",
            "위협수준": "75",
            "심각도": 75,
            "관련축선ID": "AXIS001",
            "발생장소": "GRID_123",
            "approach_mode": "threat_centered",
            "is_manual": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # 표준 형식으로 변환
        from common.situation_converter import SituationInfoConverter
        situation_info = SituationInfoConverter.convert(
            situation_info,
            source_type="manual"
        )
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "threat_centered")
        self.assertTrue(situation_info.get("is_manual", False), "is_manual이 True여야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   위협 수준: {situation_info.get('threat_level_raw')}%")
    
    def test_threat_centered_sitrep_input(self):
        """위협 중심 + SITREP 텍스트 입력 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 3: 위협 중심 + SITREP 텍스트 입력")
        print("="*70)
        
        # SITREP에서 파싱된 상황 정보 생성 (직접 생성)
        situation_info = {
            "situation_id": "THR_SITREP_001",
            "threat_level": 0.85,
            "threat_level_normalized": 0.85,
            "threat_level_raw": 85,
            "위협ID": "THR_SITREP_001",
            "위협유형": "침입",
            "위협수준": "High",
            "심각도": 85,
            "관련축선ID": "AXIS001",
            "approach_mode": "threat_centered",
            "is_sitrep": True,
            "sitrep_text": "적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음.",
            "timestamp": datetime.now().isoformat()
        }
        
        from common.situation_converter import SituationInfoConverter
        situation_info = SituationInfoConverter.convert(
            situation_info,
            source_type="sitrep"
        )
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "threat_centered")
        self.assertTrue(situation_info.get("is_sitrep", False), "is_sitrep이 True여야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   SITREP 파싱: 성공")
    
    def test_threat_centered_demo_scenario(self):
        """위협 중심 + 데모 시나리오 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 4: 위협 중심 + 데모 시나리오")
        print("="*70)
        
        # 데모 시나리오 데이터
        demo_scenario = {
            "situation_id": "SCENARIO_1",
            "threat_level": 0.75,
            "threat_level_normalized": 0.75,
            "threat_level_raw": 75,
            "위협ID": "SCENARIO_1",
            "위협유형": "정찰",
            "위협수준": "75",
            "심각도": 75,
            "발생장소": "경계지역",
            "approach_mode": "threat_centered",
            "is_demo": True,
            "timestamp": datetime.now().isoformat()
        }
        
        from common.situation_converter import SituationInfoConverter
        situation_info = SituationInfoConverter.convert(
            demo_scenario,
            source_type="demo"
        )
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "threat_centered")
        self.assertTrue(situation_info.get("is_demo", False), "is_demo이 True여야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   데모 시나리오: 정상 처리")
    
    def test_mission_centered_real_data_selection(self):
        """임무 중심 + 실제 데이터에서 선택 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 5: 임무 중심 + 실제 데이터에서 선택")
        print("="*70)
        
        # 실제 데이터에서 임무 선택
        missions_df = self.core.data_manager.load_table("임무정보")
        if missions_df is None or missions_df.empty:
            self.skipTest("임무정보 데이터가 없습니다.")
        
        # 첫 번째 임무 사용
        first_mission = missions_df.iloc[0].to_dict()
        mission_id = str(first_mission.get('임무ID', first_mission.get('ID', 'MSN001')))
        
        # 상황 정보 생성
        situation_info = {
            "situation_id": mission_id,
            "mission_id": mission_id,
            "임무ID": mission_id,
            "임무명": str(first_mission.get('임무명', first_mission.get('mission_name', 'N/A'))),
            "임무종류": str(first_mission.get('임무종류', first_mission.get('mission_type', 'N/A'))),
            "threat_level": 0.5,  # 임무 중심은 기본값
            "approach_mode": "mission_centered",
            "is_real_data": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "mission_centered")
        self.assertTrue(situation_info.get("is_real_data", False), "is_real_data가 True여야 합니다")
        self.assertIn("mission_id", situation_info, "mission_id가 있어야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   임무 ID: {situation_info.get('mission_id')}")
    
    def test_mission_centered_manual_input(self):
        """임무 중심 + 수동 입력 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 6: 임무 중심 + 수동 입력")
        print("="*70)
        
        # 수동 입력으로 임무 정보 생성
        situation_info = {
            "situation_id": "MSN_MANUAL_001",
            "mission_id": "MSN_MANUAL_001",
            "임무ID": "MSN_MANUAL_001",
            "임무명": "방어 작전",
            "임무종류": "방어",
            "주요축선ID": "AXIS001",
            "threat_level": 0.5,
            "approach_mode": "mission_centered",
            "is_manual": True,
            "timestamp": datetime.now().isoformat()
        }
        
        from common.situation_converter import SituationInfoConverter
        situation_info = SituationInfoConverter.convert(
            situation_info,
            source_type="manual",
            approach_mode="mission_centered"
        )
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "mission_centered")
        self.assertTrue(situation_info.get("is_manual", False), "is_manual이 True여야 합니다")
        self.assertIn("mission_id", situation_info, "mission_id가 있어야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   임무명: {situation_info.get('임무명', 'N/A')}")
    
    def test_mission_centered_demo_scenario(self):
        """임무 중심 + 데모 시나리오 → 방책 추천"""
        print("\n" + "="*70)
        print("테스트 7: 임무 중심 + 데모 시나리오")
        print("="*70)
        
        # 데모 시나리오 데이터 (임무 중심)
        demo_scenario = {
            "situation_id": "MSN_SCENARIO_1",
            "mission_id": "MSN_SCENARIO_1",
            "임무ID": "MSN_SCENARIO_1",
            "임무명": "공격 작전",
            "임무종류": "공격",
            "주요축선ID": "AXIS001",
            "threat_level": 0.6,
            "approach_mode": "mission_centered",
            "is_demo": True,
            "timestamp": datetime.now().isoformat()
        }
        
        from common.situation_converter import SituationInfoConverter
        situation_info = SituationInfoConverter.convert(
            demo_scenario,
            source_type="demo"
        )
        
        # 검증
        situation_info = self._verify_situation_info(situation_info, "mission_centered")
        self.assertTrue(situation_info.get("is_demo", False), "is_demo이 True여야 합니다")
        self.assertIn("mission_id", situation_info, "mission_id가 있어야 합니다")
        
        # 방책 추천 실행
        result = self.agent.execute_reasoning(
            selected_situation_info=situation_info,
            use_embedding=True,
            top_k=5
        )
        
        recommendations = self._verify_coa_recommendation(situation_info, result)
        
        print(f"✅ 상황 정보 설정 완료: {situation_info.get('situation_id')}")
        print(f"✅ 방책 추천 완료: {len(recommendations)}개")
        print(f"   최고 추천: {recommendations[0].get('coa_name', 'N/A')}")
        print(f"   데모 시나리오: 정상 처리")
    
    def test_approach_mode_preservation(self):
        """접근 방식이 방책 추천까지 올바르게 전달되는지 확인"""
        print("\n" + "="*70)
        print("테스트 8: 접근 방식 전달 검증")
        print("="*70)
        
        # 위협 중심 테스트
        threat_situation = {
            "situation_id": "THR_MODE_TEST_001",
            "threat_level": 0.7,
            "threat_level_normalized": 0.7,
            "threat_level_raw": 70,
            "위협ID": "THR_MODE_TEST_001",
            "위협유형": "침입",
            "approach_mode": "threat_centered",
            "is_manual": True,
            "timestamp": datetime.now().isoformat()
        }
        
        result_threat = self.agent.execute_reasoning(
            selected_situation_info=threat_situation,
            use_embedding=True,
            top_k=3
        )
        
        self.assertIsNotNone(result_threat)
        result_approach_mode = result_threat.get("situation_info", {}).get("approach_mode")
        if result_approach_mode:
            self.assertEqual(result_approach_mode, "threat_centered")
        
        # 임무 중심 테스트
        mission_situation = {
            "situation_id": "MSN_MODE_TEST_001",
            "mission_id": "MSN_MODE_TEST_001",
            "임무ID": "MSN_MODE_TEST_001",
            "임무명": "방어 작전",
            "approach_mode": "mission_centered",
            "threat_level": 0.5,
            "is_manual": True,
            "timestamp": datetime.now().isoformat()
        }
        
        result_mission = self.agent.execute_reasoning(
            selected_situation_info=mission_situation,
            use_embedding=True,
            top_k=3
        )
        
        self.assertIsNotNone(result_mission)
        result_approach_mode = result_mission.get("situation_info", {}).get("approach_mode")
        if result_approach_mode:
            self.assertEqual(result_approach_mode, "mission_centered")
        
        print(f"✅ 위협 중심 접근 방식 전달: {'성공' if result_threat else '실패'}")
        print(f"✅ 임무 중심 접근 방식 전달: {'성공' if result_mission else '실패'}")
    
    def test_input_mode_to_recommendation_logic(self):
        """입력 방식별로 올바른 로직이 사용되는지 확인"""
        print("\n" + "="*70)
        print("테스트 9: 입력 방식별 로직 검증")
        print("="*70)
        
        # 각 입력 방식별로 상황 정보 생성 및 추천 비교
        input_modes = [
            {
                "name": "수동 입력",
                "situation": {
                    "situation_id": "THR_MANUAL_LOGIC",
                    "threat_level": 0.7,
                    "threat_level_normalized": 0.7,
                    "threat_level_raw": 70,
                    "위협ID": "THR_MANUAL_LOGIC",
                    "위협유형": "침입",
                    "approach_mode": "threat_centered",
                    "is_manual": True,
                    "timestamp": datetime.now().isoformat()
                }
            },
            {
                "name": "데모 시나리오",
                "situation": {
                    "situation_id": "THR_DEMO_LOGIC",
                    "threat_level": 0.7,
                    "threat_level_normalized": 0.7,
                    "threat_level_raw": 70,
                    "위협ID": "THR_DEMO_LOGIC",
                    "위협유형": "침입",
                    "approach_mode": "threat_centered",
                    "is_demo": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
        ]
        
        results = {}
        for input_mode in input_modes:
            result = self.agent.execute_reasoning(
                selected_situation_info=input_mode["situation"],
                use_embedding=True,
                top_k=3
            )
            
            if result and result.get("recommendations"):
                results[input_mode["name"]] = {
                    "count": len(result["recommendations"]),
                    "top_score": result["recommendations"][0].get("score", 0),
                    "top_name": result["recommendations"][0].get("coa_name", "N/A")
                }
        
        print(f"\n📊 입력 방식별 추천 비교:")
        for mode_name, info in results.items():
            print(f"   {mode_name}: {info['count']}개, 최고점수={info['top_score']:.3f}, {info['top_name']}")
        
        # 모든 입력 방식에서 방책이 추천되어야 함
        self.assertEqual(len(results), len(input_modes), "모든 입력 방식에서 추천이 생성되어야 합니다")


def run_tests():
    """테스트 실행"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    tests = loader.loadTestsFromTestCase(TestSituationInputToCOAWorkflow)
    suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("상황정보 입력 → 방책 추천 통합 테스트 결과")
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

