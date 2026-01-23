# tests/test_situation_input.py
# -*- coding: utf-8 -*-
"""
situation_input.py 포괄적 단위 테스트
모든 기능에 대한 높은 커버리지 달성
"""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import pandas as pd
from pandas import Timestamp
import numpy as np

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from ui.components.situation_input import (
    _convert_to_string,
    _find_threat_table,
    _find_mission_table,
    convert_threat_data_to_situation_info,
    convert_mission_data_to_situation_info,
    render_situation_input,
    render_manual_input,
    render_real_data_selection_ui,
    render_mission_selection_ui,
    render_sitrep_input_ui,
    render_situation_summary
)


class TestConvertToString(unittest.TestCase):
    """_convert_to_string 함수 테스트"""
    
    def test_convert_string(self):
        """일반 문자열 변환"""
        result = _convert_to_string("test")
        self.assertEqual(result, "test")
    
    def test_convert_nan(self):
        """NaN 값 처리"""
        result = _convert_to_string(pd.NA)
        self.assertEqual(result, "N/A")
        
        result = _convert_to_string(np.nan)
        self.assertEqual(result, "N/A")
    
    def test_convert_timestamp(self):
        """Timestamp 객체 변환"""
        ts = Timestamp('2024-01-01 12:00:00')
        result = _convert_to_string(ts)
        self.assertIsInstance(result, str)
        self.assertIn("2024", result)
    
    def test_convert_datetime(self):
        """datetime 객체 변환"""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = _convert_to_string(dt)
        self.assertIsInstance(result, str)
    
    def test_convert_integer(self):
        """정수 변환"""
        result = _convert_to_string(123)
        self.assertEqual(result, "123")
    
    def test_convert_float(self):
        """실수 변환"""
        result = _convert_to_string(45.67)
        self.assertEqual(result, "45.67")
    
    def test_convert_none(self):
        """None 값 처리"""
        result = _convert_to_string(None)
        self.assertEqual(result, "N/A")


class TestFindThreatTable(unittest.TestCase):
    """_find_threat_table 함수 테스트"""
    
    def test_find_threat_table_korean(self):
        """한글 키워드 테이블 찾기"""
        orchestrator = Mock()
        orchestrator.config = {
            "data_paths": {
                "위협상황": "path/to/threat.xlsx",
                "임무정보": "path/to/mission.xlsx"
            }
        }
        result = _find_threat_table(orchestrator)
        self.assertEqual(result, "위협상황")
    
    def test_find_threat_table_english(self):
        """영어 키워드 테이블 찾기"""
        orchestrator = Mock()
        orchestrator.config = {
            "data_paths": {
                "Threat": "path/to/threat.xlsx",
                "Mission": "path/to/mission.xlsx"
            }
        }
        result = _find_threat_table(orchestrator)
        self.assertEqual(result, "Threat")
    
    def test_find_threat_table_none_orchestrator(self):
        """Orchestrator가 None인 경우"""
        result = _find_threat_table(None)
        self.assertIsNone(result)
    
    def test_find_threat_table_no_config(self):
        """config가 없는 경우"""
        orchestrator = Mock()
        orchestrator.config = None
        result = _find_threat_table(orchestrator)
        self.assertIsNone(result)
    
    def test_find_threat_table_no_threat_table(self):
        """위협 테이블이 없는 경우 (첫 번째 테이블 반환)"""
        orchestrator = Mock()
        orchestrator.config = {
            "data_paths": {
                "임무정보": "path/to/mission.xlsx",
                "아군부대": "path/to/friendly.xlsx"
            }
        }
        result = _find_threat_table(orchestrator)
        # 첫 번째 테이블 반환
        self.assertIn(result, ["임무정보", "아군부대"])
    
    def test_find_threat_table_empty_data_paths(self):
        """빈 data_paths"""
        orchestrator = Mock()
        orchestrator.config = {"data_paths": {}}
        result = _find_threat_table(orchestrator)
        self.assertIsNone(result)


class TestFindMissionTable(unittest.TestCase):
    """_find_mission_table 함수 테스트"""
    
    def test_find_mission_table_korean(self):
        """한글 키워드 테이블 찾기"""
        orchestrator = Mock()
        orchestrator.config = {
            "data_paths": {
                "임무정보": "path/to/mission.xlsx",
                "위협상황": "path/to/threat.xlsx"
            }
        }
        result = _find_mission_table(orchestrator)
        self.assertEqual(result, "임무정보")
    
    def test_find_mission_table_english(self):
        """영어 키워드 테이블 찾기"""
        orchestrator = Mock()
        orchestrator.config = {
            "data_paths": {
                "Mission": "path/to/mission.xlsx",
                "Threat": "path/to/threat.xlsx"
            }
        }
        result = _find_mission_table(orchestrator)
        self.assertEqual(result, "Mission")
    
    def test_find_mission_table_none_orchestrator(self):
        """Orchestrator가 None인 경우"""
        result = _find_mission_table(None)
        self.assertIsNone(result)
    
    def test_find_mission_table_no_mission_table(self):
        """임무 테이블이 없는 경우"""
        orchestrator = Mock()
        orchestrator.config = {
            "data_paths": {
                "위협상황": "path/to/threat.xlsx",
                "아군부대": "path/to/friendly.xlsx"
            }
        }
        result = _find_mission_table(orchestrator)
        self.assertIsNone(result)


class TestConvertThreatDataToSituationInfo(unittest.TestCase):
    """convert_threat_data_to_situation_info 함수 테스트"""
    
    def test_convert_complete_threat_data(self):
        """완전한 위협 데이터 변환"""
        threat_data = {
            "위협ID": "THR001",
            "위협유형코드": "침투",
            "위협수준": 85,
            "관련축선ID": "AXIS001",
            "발생장소": "GRID_123"
        }
        result = convert_threat_data_to_situation_info(
            threat_data,
            id_col="위협ID",
            threat_type_col="위협유형코드",
            threat_level_col="위협수준",
            axis_id_col="관련축선ID",
            location_col="발생장소"
        )
        
        self.assertEqual(result["situation_id"], "THR001")
        self.assertEqual(result["위협ID"], "THR001")
        self.assertEqual(result["위협유형"], "침투")
        self.assertEqual(result["심각도"], 85)
        self.assertAlmostEqual(result["threat_level"], 0.85, places=2)
        self.assertEqual(result["관련축선ID"], "AXIS001")
        self.assertEqual(result["발생장소"], "GRID_123")
        self.assertEqual(result["approach_mode"], "threat_centered")
    
    def test_convert_dynamic_column_finding(self):
        """동적 컬럼 찾기"""
        threat_data = {
            "ID": "THR002",
            "threat_type": "공격",
            "threat_level": "High",
            "axis_id": "AXIS002",
            "location": "GRID_456"
        }
        result = convert_threat_data_to_situation_info(threat_data)
        
        self.assertEqual(result["situation_id"], "THR002")
        self.assertEqual(result["위협유형"], "공격")
        self.assertEqual(result["심각도"], 90)  # "High" -> 90
        self.assertAlmostEqual(result["threat_level"], 0.9, places=2)
    
    def test_convert_string_threat_level_high(self):
        """문자열 위협수준 - High"""
        threat_data = {"위협수준": "High"}
        result = convert_threat_data_to_situation_info(
            threat_data,
            threat_level_col="위협수준"
        )
        self.assertEqual(result["심각도"], 90)
        self.assertAlmostEqual(result["threat_level"], 0.9, places=2)
    
    def test_convert_string_threat_level_medium(self):
        """문자열 위협수준 - Medium"""
        threat_data = {"위협수준": "Medium"}
        result = convert_threat_data_to_situation_info(
            threat_data,
            threat_level_col="위협수준"
        )
        self.assertEqual(result["심각도"], 50)
        self.assertAlmostEqual(result["threat_level"], 0.5, places=2)
    
    def test_convert_string_threat_level_low(self):
        """문자열 위협수준 - Low"""
        threat_data = {"위협수준": "Low"}
        result = convert_threat_data_to_situation_info(
            threat_data,
            threat_level_col="위협수준"
        )
        self.assertEqual(result["심각도"], 20)
        self.assertAlmostEqual(result["threat_level"], 0.2, places=2)
    
    def test_convert_string_threat_level_korean(self):
        """한글 위협수준"""
        threat_data = {"위협수준": "높음"}
        result = convert_threat_data_to_situation_info(
            threat_data,
            threat_level_col="위협수준"
        )
        self.assertEqual(result["심각도"], 90)
    
    def test_convert_numeric_threat_level(self):
        """숫자 위협수준"""
        threat_data = {"위협수준": 75}
        result = convert_threat_data_to_situation_info(
            threat_data,
            threat_level_col="위협수준"
        )
        self.assertEqual(result["심각도"], 75)
        self.assertAlmostEqual(result["threat_level"], 0.75, places=2)
    
    def test_convert_no_threat_level(self):
        """위협수준이 없는 경우"""
        threat_data = {"위협ID": "THR003"}
        result = convert_threat_data_to_situation_info(threat_data)
        self.assertEqual(result["심각도"], 0)
        self.assertEqual(result["threat_level"], 0.0)
    
    def test_convert_no_id(self):
        """ID가 없는 경우"""
        threat_data = {"위협유형": "침투"}
        result = convert_threat_data_to_situation_info(threat_data)
        self.assertEqual(result["situation_id"], "UNKNOWN")
    
    def test_convert_with_detection_time_and_evidence(self):
        """탐지시각 및 근거 필드 포함"""
        threat_data = {
            "위협ID": "THR004",
            "탐지시각": "2024-01-01 12:00:00",
            "근거": "레이더 탐지"
        }
        result = convert_threat_data_to_situation_info(threat_data)
        self.assertEqual(result["탐지시각"], "2024-01-01 12:00:00")
        self.assertEqual(result["근거"], "레이더 탐지")


class TestConvertMissionDataToSituationInfo(unittest.TestCase):
    """convert_mission_data_to_situation_info 함수 테스트"""
    
    def test_convert_complete_mission_data(self):
        """완전한 임무 데이터 변환"""
        mission_data = {
            "임무ID": "MSN001",
            "임무명": "방어 작전",
            "임무종류": "방어",
            "주요축선ID": "AXIS001"
        }
        result = convert_mission_data_to_situation_info(
            mission_data,
            "MSN001",
            id_col="임무ID",
            name_col="임무명",
            type_col="임무종류"
        )
        
        self.assertEqual(result["situation_id"], "MSN001")
        self.assertEqual(result["mission_id"], "MSN001")
        self.assertEqual(result["임무ID"], "MSN001")
        self.assertEqual(result["임무명"], "방어 작전")
        self.assertEqual(result["임무종류"], "방어")
        self.assertEqual(result["주요축선ID"], "AXIS001")
        self.assertEqual(result["threat_level"], 0.5)  # 기본값
        self.assertEqual(result["approach_mode"], "mission_centered")
    
    def test_convert_dynamic_column_finding(self):
        """동적 컬럼 찾기"""
        mission_data = {
            "mission_id": "MSN002",
            "mission_name": "공격 작전",
            "mission_type": "공격",
            "primary_axis_id": "AXIS002"
        }
        result = convert_mission_data_to_situation_info(mission_data, "MSN002")
        
        self.assertEqual(result["situation_id"], "MSN002")
        self.assertEqual(result["임무명"], "공격 작전")
        self.assertEqual(result["임무종류"], "공격")
        self.assertEqual(result["주요축선ID"], "AXIS002")


class TestRenderSituationInput(unittest.TestCase):
    """render_situation_input 함수 테스트"""
    
    @patch('ui.components.situation_input.st')
    def test_render_threat_centered_real_data(self, mock_st):
        """위협 중심 - 실제 데이터 선택"""
        mock_st.radio.side_effect = ["위협 중심", "실제 데이터에서 선택"]
        mock_orchestrator = Mock()
        
        with patch('ui.components.situation_input.render_real_data_selection_ui') as mock_render:
            mock_render.return_value = {"situation_id": "THR001"}
            result = render_situation_input(mock_orchestrator, use_real_data=True)
            
            mock_render.assert_called_once_with(mock_orchestrator)
            self.assertIsNotNone(result)
    
    @patch('ui.components.situation_input.st')
    def test_render_threat_centered_manual(self, mock_st):
        """위협 중심 - 수동 입력"""
        mock_st.radio.side_effect = ["위협 중심", "수동 입력"]
        
        with patch('ui.components.situation_input.render_manual_input') as mock_render:
            mock_render.return_value = {"situation_id": "MAN001", "threat_level": 0.7}
            result = render_situation_input(use_real_data=False)
            
            mock_render.assert_called_once_with(approach_mode="threat_centered")
            self.assertIsNotNone(result)
    
    @patch('ui.components.situation_input.st')
    def test_render_mission_centered_manual(self, mock_st):
        """임무 중심 - 수동 입력"""
        mock_st.radio.side_effect = ["임무 중심", "수동 입력"]
        
        with patch('ui.components.situation_input.render_manual_input') as mock_render:
            mock_render.return_value = {"situation_id": "MSN001", "mission_id": "MSN001"}
            result = render_situation_input(use_real_data=False)
            
            mock_render.assert_called_once_with(approach_mode="mission_centered")
            self.assertIsNotNone(result)
    
    @patch('ui.components.situation_input.st')
    def test_render_no_orchestrator_warning(self, mock_st):
        """Orchestrator 없을 때 경고"""
        mock_st.radio.side_effect = ["위협 중심", "실제 데이터에서 선택"]
        mock_st.warning = Mock()
        
        result = render_situation_input(None, use_real_data=True)
        
        mock_st.warning.assert_called()
        self.assertIsNone(result)


class TestRenderManualInput(unittest.TestCase):
    """render_manual_input 함수 테스트"""
    
    @patch('ui.components.situation_input.st')
    def test_render_threat_centered_manual(self, mock_st):
        """위협 중심 수동 입력"""
        mock_st.text_input.return_value = "SIT_20240101_120000"
        mock_st.slider.return_value = 70
        mock_st.number_input.side_effect = [5, 75]  # defense_assets_count, defense_firepower
        mock_st.text_area.return_value = ""
        mock_st.button.return_value = False
        mock_st.divider = Mock()
        mock_st.info = Mock()
        mock_st.error = Mock()
        mock_st.warning = Mock()
        mock_st.success = Mock()
        
        # columns mock 설정 (context manager 지원)
        col1 = MagicMock()
        col2 = MagicMock()
        col1.__enter__ = Mock(return_value=col1)
        col1.__exit__ = Mock(return_value=False)
        col2.__enter__ = Mock(return_value=col2)
        col2.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2]
        
        # expander mock 설정
        expander = MagicMock()
        expander.__enter__ = Mock(return_value=expander)
        expander.__exit__ = Mock(return_value=False)
        mock_st.expander.return_value = expander
        
        mock_st.session_state = {}
        
        result = render_manual_input(approach_mode="threat_centered")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["approach_mode"], "threat_centered")
        self.assertEqual(result["is_manual"], True)
        self.assertIn("threat_level", result)
    
    @patch('ui.components.situation_input.st')
    def test_render_mission_centered_manual(self, mock_st):
        """임무 중심 수동 입력"""
        # text_input은 여러 번 호출됨: situation_id, mission_id, mission_name, location (expander 내부)
        mock_st.text_input.side_effect = ["SIT_20240101_120000", "MSN001", "방어 작전", "Grid 1234"]
        mock_st.number_input.side_effect = [5, 75]
        mock_st.text_area.return_value = ""
        mock_st.button.return_value = False
        mock_st.divider = Mock()
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        col1.__enter__ = Mock(return_value=col1)
        col1.__exit__ = Mock(return_value=False)
        col2.__enter__ = Mock(return_value=col2)
        col2.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2]
        
        # expander mock 설정
        expander = MagicMock()
        expander.__enter__ = Mock(return_value=expander)
        expander.__exit__ = Mock(return_value=False)
        mock_st.expander.return_value = expander
        
        mock_st.session_state = MagicMock()
        
        result = render_manual_input(approach_mode="mission_centered")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["approach_mode"], "mission_centered")
        self.assertIn("mission_id", result)
        self.assertIn("임무명", result)
    
    @patch('ui.components.situation_input.st')
    @patch('common.situation_converter.SituationInfoConverter')
    def test_render_manual_save_button_valid(self, mock_converter, mock_st):
        """저장 버튼 클릭 - 유효한 데이터"""
        mock_st.text_input.return_value = "SIT_20240101_120000"
        mock_st.slider.return_value = 70
        mock_st.number_input.side_effect = [5, 75]
        mock_st.text_area.return_value = ""
        mock_st.button.return_value = True
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        col1.__enter__ = Mock(return_value=col1)
        col1.__exit__ = Mock(return_value=False)
        col2.__enter__ = Mock(return_value=col2)
        col2.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2]
        
        # expander mock 설정
        expander = MagicMock()
        expander.__enter__ = Mock(return_value=expander)
        expander.__exit__ = Mock(return_value=False)
        mock_st.expander.return_value = expander
        
        mock_st.session_state = MagicMock()  # 속성 접근 지원
        mock_st.rerun = Mock()  # st.rerun()은 아무것도 하지 않음
        
        # Converter mock 설정
        mock_converter.convert.return_value = {
            "situation_id": "SIT_20240101_120000",
            "threat_level_normalized": 0.7,
            "approach_mode": "threat_centered"
        }
        mock_converter.validate.return_value = (True, [])
        
        result = render_manual_input(approach_mode="threat_centered")
        
        mock_converter.convert.assert_called_once()
        mock_converter.validate.assert_called_once()
        # st.rerun()이 호출되었는지 확인
        mock_st.rerun.assert_called_once()
    
    @patch('ui.components.situation_input.st')
    @patch('common.situation_converter.SituationInfoConverter')
    def test_render_manual_save_button_invalid(self, mock_converter, mock_st):
        """저장 버튼 클릭 - 검증 실패"""
        mock_st.text_input.return_value = "SIT_20240101_120000"
        mock_st.slider.return_value = 70
        mock_st.number_input.side_effect = [5, 75]
        mock_st.text_area.return_value = ""
        mock_st.button.return_value = True
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        col1.__enter__ = Mock(return_value=col1)
        col1.__exit__ = Mock(return_value=False)
        col2.__enter__ = Mock(return_value=col2)
        col2.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2]
        
        # expander mock 설정
        expander = MagicMock()
        expander.__enter__ = Mock(return_value=expander)
        expander.__exit__ = Mock(return_value=False)
        mock_st.expander.return_value = expander
        
        mock_st.session_state = {}
        mock_st.error = Mock()
        
        # Converter mock 설정
        mock_converter.convert.return_value = {
            "situation_id": "SIT_20240101_120000",
            "threat_level_normalized": 0.7
        }
        mock_converter.validate.return_value = (False, ["필수 필드 누락: approach_mode"])
        
        result = render_manual_input(approach_mode="threat_centered")
        
        mock_st.error.assert_called()
        self.assertIsNotNone(result)


class TestRenderRealDataSelectionUI(unittest.TestCase):
    """render_real_data_selection_ui 함수 테스트"""
    
    @patch('ui.components.situation_input.st')
    def test_render_real_data_selection_success(self, mock_st):
        """정상 데이터 로드 및 선택"""
        # Mock orchestrator 설정
        mock_orchestrator = Mock()
        mock_orchestrator.config = {
            "data_paths": {"위협상황": "path/to/threat.xlsx"}
        }
        
        # Mock DataFrame
        mock_df = pd.DataFrame({
            "위협ID": ["THR001", "THR002"],
            "위협유형코드": ["침투", "공격"],
            "위협수준": [85, 60],
            "관련축선ID": ["AXIS001", "AXIS002"],
            "발생장소": ["GRID_123", "GRID_456"]
        })
        
        mock_data_manager = Mock()
        mock_data_manager.load_table.return_value = mock_df
        mock_orchestrator.core.data_manager = mock_data_manager
        
        # Streamlit mock 설정
        mock_st.selectbox.return_value = "THR001 - 침투 (85) - 축선: AXIS001"
        mock_st.button.return_value = False
        mock_st.session_state = {}
        
        result = render_real_data_selection_ui(mock_orchestrator)
        
        self.assertIsNone(result)  # 버튼을 클릭하지 않았으므로 None
    
    @patch('ui.components.situation_input.st')
    def test_render_real_data_selection_no_table(self, mock_st):
        """위협 테이블을 찾을 수 없는 경우"""
        mock_orchestrator = Mock()
        mock_orchestrator.config = {"data_paths": {}}
        mock_st.warning = Mock()
        
        result = render_real_data_selection_ui(mock_orchestrator)
        
        mock_st.warning.assert_called()
        self.assertIsNone(result)
    
    @patch('ui.components.situation_input.st')
    def test_render_real_data_selection_empty_table(self, mock_st):
        """빈 테이블"""
        mock_orchestrator = Mock()
        mock_orchestrator.config = {
            "data_paths": {"위협상황": "path/to/threat.xlsx"}
        }
        mock_data_manager = Mock()
        mock_data_manager.load_table.return_value = pd.DataFrame()
        mock_orchestrator.core.data_manager = mock_data_manager
        mock_st.warning = Mock()
        
        result = render_real_data_selection_ui(mock_orchestrator)
        
        mock_st.warning.assert_called()
        self.assertIsNone(result)
    
    @patch('ui.components.situation_input.st')
    @patch('common.situation_converter.SituationInfoConverter')
    def test_render_real_data_selection_save(self, mock_converter, mock_st):
        """위협 상황 선택 및 저장"""
        mock_orchestrator = Mock()
        mock_orchestrator.config = {
            "data_paths": {"위협상황": "path/to/threat.xlsx"}
        }
        
        mock_df = pd.DataFrame({
            "위협ID": ["THR001"],
            "위협유형코드": ["침투"],
            "위협수준": [85],
            "관련축선ID": ["AXIS001"],
            "발생장소": ["GRID_123"]
        })
        
        mock_data_manager = Mock()
        mock_data_manager.load_table.return_value = mock_df
        mock_orchestrator.core.data_manager = mock_data_manager
        
        mock_st.selectbox.return_value = "THR001 - 침투 (85) - 축선: AXIS001"
        # button은 한 번만 호출됨 (저장 버튼)
        mock_st.button.return_value = True
        
        # expander mock 설정
        expander = MagicMock()
        expander.__enter__ = Mock(return_value=expander)
        expander.__exit__ = Mock(return_value=False)
        mock_st.expander.return_value = expander
        
        mock_st.session_state = MagicMock()
        mock_st.rerun = Mock()  # st.rerun()은 아무것도 하지 않음
        mock_st.success = Mock()
        mock_st.info = Mock()
        
        mock_converter.convert.return_value = {
            "situation_id": "THR001",
            "threat_level_normalized": 0.85,
            "approach_mode": "threat_centered"
        }
        mock_converter.validate.return_value = (True, [])
        
        result = render_real_data_selection_ui(mock_orchestrator)
        
        mock_converter.convert.assert_called_once()
        mock_converter.validate.assert_called_once()
        # st.rerun()이 호출되었는지 확인
        mock_st.rerun.assert_called_once()
        # 반환값 확인 (st.rerun() 후에도 return이 실행됨)
        self.assertIsNotNone(result)


class TestRenderMissionSelectionUI(unittest.TestCase):
    """render_mission_selection_ui 함수 테스트"""
    
    @patch('ui.components.situation_input.st')
    def test_render_mission_selection_success(self, mock_st):
        """정상 데이터 로드 및 선택"""
        mock_orchestrator = Mock()
        mock_orchestrator.config = {
            "data_paths": {"임무정보": "path/to/mission.xlsx"}
        }
        
        mock_df = pd.DataFrame({
            "임무ID": ["MSN001"],
            "임무명": ["방어 작전"],
            "임무종류": ["방어"]
        })
        
        mock_data_manager = Mock()
        mock_data_manager.load_table.return_value = mock_df
        mock_orchestrator.core.data_manager = mock_data_manager
        
        mock_st.selectbox.return_value = "MSN001: 방어 작전 (방어)"
        mock_st.button.return_value = False
        mock_st.session_state = {}
        
        result = render_mission_selection_ui(mock_orchestrator)
        
        self.assertIsNone(result)  # 버튼을 클릭하지 않았으므로 None
    
    @patch('ui.components.situation_input.st')
    def test_render_mission_selection_no_table(self, mock_st):
        """임무 테이블을 찾을 수 없는 경우"""
        mock_orchestrator = Mock()
        mock_orchestrator.config = {"data_paths": {}}
        mock_st.warning = Mock()
        
        result = render_mission_selection_ui(mock_orchestrator)
        
        mock_st.warning.assert_called()
        self.assertIsNone(result)


class TestRenderSitrepInputUI(unittest.TestCase):
    """render_sitrep_input_ui 함수 테스트"""
    
    @patch('ui.components.situation_input.st')
    def test_render_sitrep_input_empty(self, mock_st):
        """빈 텍스트 입력"""
        mock_st.text_area.return_value = ""
        
        result = render_sitrep_input_ui(None)
        
        self.assertIsNone(result)
    
    @patch('ui.components.situation_input.st')
    @patch('core_pipeline.coa_service.COAService')
    def test_render_sitrep_parse_success(self, mock_coa_service, mock_st):
        """SITREP 파싱 성공"""
        mock_st.text_area.return_value = "적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음."
        mock_st.button.side_effect = [True, False]  # 파싱 버튼, 설정 버튼
        
        # Mock ThreatEvent
        mock_threat_event = Mock()
        mock_threat_event.threat_id = "THR_SITREP_001"
        mock_threat_event.threat_type_code = "공격"
        mock_threat_event.threat_level = "High"
        mock_threat_event.related_axis_id = "AXIS001"
        
        mock_coa_instance = Mock()
        mock_coa_instance.parse_sitrep_to_threat.return_value = mock_threat_event
        mock_coa_service.return_value = mock_coa_instance
        
        # spinner는 context manager
        spinner = MagicMock()
        spinner.__enter__ = Mock(return_value=spinner)
        spinner.__exit__ = Mock(return_value=False)
        mock_st.spinner = Mock(return_value=spinner)
        
        mock_st.success = Mock()
        mock_st.session_state = MagicMock()
        mock_st.rerun = Mock()  # st.rerun()은 아무것도 하지 않음
        
        result = render_sitrep_input_ui(Mock())
        
        mock_coa_instance.parse_sitrep_to_threat.assert_called_once()
        # 반환값 확인
        self.assertIsNotNone(result)
    
    @patch('ui.components.situation_input.st')
    @patch('core_pipeline.coa_service.COAService')
    def test_render_sitrep_parse_failure(self, mock_coa_service, mock_st):
        """SITREP 파싱 실패"""
        mock_st.text_area.return_value = "잘못된 텍스트"
        mock_st.button.return_value = True
        mock_st.error = Mock()
        
        # spinner는 context manager
        spinner = MagicMock()
        spinner.__enter__ = Mock(return_value=spinner)
        spinner.__exit__ = Mock(return_value=False)
        mock_st.spinner = Mock(return_value=spinner)
        
        mock_st.code = Mock()
        
        mock_coa_instance = Mock()
        mock_coa_instance.parse_sitrep_to_threat.side_effect = Exception("파싱 오류")
        mock_coa_service.return_value = mock_coa_instance
        
        result = render_sitrep_input_ui(Mock())
        
        mock_st.error.assert_called()
        # 예외 발생 시 None 반환
        self.assertIsNone(result)


class TestRenderSituationSummary(unittest.TestCase):
    """render_situation_summary 함수 테스트"""
    
    @patch('ui.components.situation_input.st')
    def test_render_summary_threat_centered(self, mock_st):
        """위협 중심 요약 표시"""
        situation_info = {
            "approach_mode": "threat_centered",
            "위협유형": "침투",
            "위협수준": "85",
            "관련축선ID": "AXIS001",
            "threat_level": 0.85
        }
        
        mock_st.markdown = Mock()
        mock_st.metric = Mock()
        mock_st.warning = Mock()
        
        # columns mock 설정 (context manager 지원)
        col1 = MagicMock()
        col2 = MagicMock()
        col3 = MagicMock()
        for col in [col1, col2, col3]:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2, col3]
        
        render_situation_summary(situation_info)
        
        # 메트릭이 3번 호출되어야 함 (위협유형, 위협수준, 관련축선)
        self.assertEqual(mock_st.metric.call_count, 3)
        mock_st.warning.assert_called_once()  # 높은 위협수준 경고
    
    @patch('ui.components.situation_input.st')
    def test_render_summary_mission_centered(self, mock_st):
        """임무 중심 요약 표시"""
        situation_info = {
            "approach_mode": "mission_centered",
            "mission_id": "MSN001",
            "임무ID": "MSN001",
            "임무명": "방어 작전",
            "임무종류": "방어",
            "주요축선ID": "AXIS001"
        }
        
        mock_st.markdown = Mock()
        mock_st.metric = Mock()
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        col3 = MagicMock()
        col4 = MagicMock()
        for col in [col1, col2, col3, col4]:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2, col3, col4]
        
        render_situation_summary(situation_info)
        
        # 메트릭이 4번 호출되어야 함 (임무 ID, 임무명, 임무종류, 주요축선)
        self.assertEqual(mock_st.metric.call_count, 4)
    
    @patch('ui.components.situation_input.st')
    def test_render_summary_unknown_mode(self, mock_st):
        """알 수 없는 접근 방식"""
        situation_info = {
            "approach_mode": "unknown",
            "situation_id": "SIT001",
            "threat_level": 0.7
        }
        
        mock_st.markdown = Mock()
        mock_st.metric = Mock()
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        for col in [col1, col2]:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2]
        
        render_situation_summary(situation_info)
        
        # 메트릭이 2번 호출되어야 함 (상황 ID, 위협 수준)
        self.assertEqual(mock_st.metric.call_count, 2)
    
    @patch('ui.components.situation_input.st')
    def test_render_summary_threat_level_medium(self, mock_st):
        """중간 위협수준 권장사항"""
        situation_info = {
            "approach_mode": "threat_centered",
            "위협유형": "침투",
            "위협수준": "60",
            "관련축선ID": "AXIS001",
            "threat_level": 0.6
        }
        
        mock_st.markdown = Mock()
        mock_st.metric = Mock()
        mock_st.info = Mock()
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        col3 = MagicMock()
        for col in [col1, col2, col3]:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2, col3]
        
        render_situation_summary(situation_info)
        
        mock_st.info.assert_called_once()  # 중간 위협수준 정보
    
    @patch('ui.components.situation_input.st')
    def test_render_summary_threat_level_low(self, mock_st):
        """낮은 위협수준 권장사항"""
        situation_info = {
            "approach_mode": "threat_centered",
            "위협유형": "침투",
            "위협수준": "30",
            "관련축선ID": "AXIS001",
            "threat_level": 0.3
        }
        
        mock_st.markdown = Mock()
        mock_st.metric = Mock()
        mock_st.success = Mock()
        
        # columns mock 설정
        col1 = MagicMock()
        col2 = MagicMock()
        col3 = MagicMock()
        for col in [col1, col2, col3]:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=False)
        mock_st.columns.return_value = [col1, col2, col3]
        
        render_situation_summary(situation_info)
        
        mock_st.success.assert_called_once()  # 낮은 위협수준 성공 메시지


def run_tests():
    """모든 테스트 실행"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 모든 테스트 클래스 추가
    test_classes = [
        TestConvertToString,
        TestFindThreatTable,
        TestFindMissionTable,
        TestConvertThreatDataToSituationInfo,
        TestConvertMissionDataToSituationInfo,
        TestRenderSituationInput,
        TestRenderManualInput,
        TestRenderRealDataSelectionUI,
        TestRenderMissionSelectionUI,
        TestRenderSitrepInputUI,
        TestRenderSituationSummary
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    print(f"총 테스트 수: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    
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

