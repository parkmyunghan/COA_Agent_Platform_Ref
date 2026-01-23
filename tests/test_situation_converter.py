# tests/test_situation_converter.py
# -*- coding: utf-8 -*-
"""
SituationInfoConverter 단위 테스트
"""
import sys
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from common.situation_converter import SituationInfoConverter


def test_normalize_threat_level_string():
    """문자열 위협수준 변환 테스트"""
    # 영어
    assert SituationInfoConverter.normalize_threat_level("High") == (0.85, 85, "HIGH")
    assert SituationInfoConverter.normalize_threat_level("Medium") == (0.60, 60, "MEDIUM")
    assert SituationInfoConverter.normalize_threat_level("Low") == (0.30, 30, "LOW")
    
    # 한글
    assert SituationInfoConverter.normalize_threat_level("높음") == (0.85, 85, "HIGH")
    assert SituationInfoConverter.normalize_threat_level("중간") == (0.60, 60, "MEDIUM")
    assert SituationInfoConverter.normalize_threat_level("낮음") == (0.30, 30, "LOW")
    
    # 대소문자 무관
    assert SituationInfoConverter.normalize_threat_level("HIGH") == (0.85, 85, "HIGH")
    assert SituationInfoConverter.normalize_threat_level("high") == (0.85, 85, "HIGH")
    
    print("✅ 문자열 위협수준 변환 테스트 통과")


def test_normalize_threat_level_numeric():
    """숫자 위협수준 변환 테스트"""
    # 0-1 범위
    assert SituationInfoConverter.normalize_threat_level(0.85) == (0.85, 85, "HIGH")
    assert SituationInfoConverter.normalize_threat_level(0.6) == (0.6, 60, "MEDIUM")
    assert SituationInfoConverter.normalize_threat_level(0.3) == (0.3, 30, "LOW")
    
    # 0-100 범위
    assert SituationInfoConverter.normalize_threat_level(85) == (0.85, 85, "HIGH")
    assert SituationInfoConverter.normalize_threat_level(60) == (0.60, 60, "MEDIUM")
    assert SituationInfoConverter.normalize_threat_level(30) == (0.30, 30, "LOW")
    
    print("✅ 숫자 위협수준 변환 테스트 통과")


def test_normalize_threat_level_edge_cases():
    """엣지 케이스 테스트"""
    # None
    assert SituationInfoConverter.normalize_threat_level(None) == (0.7, 70, "MEDIUM")
    
    # 빈 문자열
    assert SituationInfoConverter.normalize_threat_level("") == (0.7, 70, "MEDIUM")
    
    # 범위 초과 (정규화)
    normalized, raw, label = SituationInfoConverter.normalize_threat_level(150)
    assert normalized == 1.0  # 최대값으로 제한
    
    print("✅ 엣지 케이스 테스트 통과")


def test_convert_real_data():
    """실제 데이터 변환 테스트"""
    real_data = {
        "위협ID": "THR001",
        "위협유형코드": "침투",
        "위협수준": "High",  # 문자열
        "발생장소": "GRID_123",
        "관련축선ID": "AXIS001"
    }
    
    result = SituationInfoConverter.convert(real_data, source_type="real_data")
    
    # 표준 필드 확인
    assert result["situation_id"] == "THR001"
    assert result["threat_level_normalized"] == 0.85
    assert result["threat_level_raw"] == 85
    assert result["threat_level_label"] == "HIGH"
    assert result["source_type"] == "real_data"
    assert result["is_real_data"] == True
    
    # 하위호환 필드 확인
    assert result["threat_level"] == 0.85
    assert result["위협ID"] == "THR001"
    assert result["위협유형"] == "침투"
    
    print("✅ 실제 데이터 변환 테스트 통과")


def test_convert_manual():
    """수동 입력 변환 테스트"""
    manual_data = {
        "situation_id": "MAN001",
        "threat_level": 0.75,
        "approach_mode": "threat_centered",
        "location": "GRID_456"
    }
    
    result = SituationInfoConverter.convert(manual_data, source_type="manual")
    
    assert result["situation_id"] == "MAN001"
    assert result["threat_level_normalized"] == 0.75
    assert result["threat_level_raw"] == 75
    assert result["threat_level_label"] == "MEDIUM"
    assert result["source_type"] == "manual"
    assert result["is_manual"] == True
    
    print("✅ 수동 입력 변환 테스트 통과")


def test_validate():
    """검증 로직 테스트"""
    # 올바른 데이터
    valid_data = {
        "situation_id": "TEST001",
        "threat_level_normalized": 0.85,
        "threat_level_raw": 85,
        "approach_mode": "threat_centered"
    }
    is_valid, errors = SituationInfoConverter.validate(valid_data)
    assert is_valid == True
    assert len(errors) == 0
    
    # 필수 필드 누락
    invalid_data = {
        "situation_id": "TEST002"
        # threat_level_normalized 누락
    }
    is_valid, errors = SituationInfoConverter.validate(invalid_data)
    assert is_valid == False
    assert len(errors) > 0
    
    # 범위 오류
    invalid_data2 = {
        "situation_id": "TEST003",
        "threat_level_normalized": 1.5,  # 범위 초과
        "approach_mode": "threat_centered"
    }
    is_valid, errors = SituationInfoConverter.validate(invalid_data2)
    assert is_valid == False
    
    print("✅ 검증 로직 테스트 통과")


if __name__ == "__main__":
    print("SituationInfoConverter 테스트 시작...\n")
    
    test_normalize_threat_level_string()
    test_normalize_threat_level_numeric()
    test_normalize_threat_level_edge_cases()
    test_convert_real_data()
    test_convert_manual()
    test_validate()
    
    print("\n🎉 모든 테스트 통과!")
