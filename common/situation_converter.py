# utils/situation_converter.py
# -*- coding: utf-8 -*-
"""
통합 상황 정보 변환기
모든 입력 방식(실제 데이터, SITREP, 수동, 데모)을 표준 situation_info로 변환
"""
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import pandas as pd


class SituationInfoConverter:
    """모든 입력 방식을 표준 situation_info로 변환하는 통합 변환기"""
    
    # 위협수준 매핑 테이블
    THREAT_LEVEL_MAPPING = {
        # 영어 (대소문자 무관)
        "critical": 0.95, "very high": 0.90, "high": 0.85,
        "medium": 0.60, "moderate": 0.60,
        "low": 0.30, "minimal": 0.15,
        # 한글
        "위급": 0.95, "매우높음": 0.90, "높음": 0.85,
        "중간": 0.60, "보통": 0.60,
        "낮음": 0.30, "미미": 0.15,
        # 약어
        "h": 0.85, "m": 0.60, "l": 0.30
    }
    
    @classmethod
    def convert(cls, data: Dict, source_type: str, **kwargs) -> Dict:
        """
        입력 데이터를 표준 situation_info로 변환
        
        Args:
            data: 원본 데이터 딕셔너리
            source_type: "real_data" | "sitrep" | "manual" | "demo"
            **kwargs: 추가 컨텍스트 (approach_mode 등)
        
        Returns:
            표준 situation_info 딕셔너리
        """
        if source_type == "real_data":
            return cls._convert_real_data(data, **kwargs)
        elif source_type == "sitrep":
            return cls._convert_sitrep(data, **kwargs)
        elif source_type == "manual":
            return cls._convert_manual(data, **kwargs)
        elif source_type == "demo":
            return cls._convert_demo(data, **kwargs)
        else:
            raise ValueError(f"Unknown source_type: {source_type}")
    
    @classmethod
    def normalize_threat_level(cls, raw_value) -> Tuple[float, int, str]:
        """
        위협수준 정규화
        
        Args:
            raw_value: 원본 값 (문자열, 숫자, None)
        
        Returns:
            (normalized 0-1, raw 0-100, label "HIGH"|"MEDIUM"|"LOW")
        """
        # 1. 문자열 매핑 시도
        if isinstance(raw_value, str):
            raw_str = raw_value.strip().lower()
            for key, normalized_val in cls.THREAT_LEVEL_MAPPING.items():
                if key in raw_str:
                    raw_val = int(normalized_val * 100)
                    label = cls._get_label(normalized_val)
                    return normalized_val, raw_val, label
            
            # 2. 문자열→숫자 변환 시도
            try:
                raw_value = float(raw_value.replace(',', ''))
            except (ValueError, AttributeError):
                # 변환 실패 시 기본값
                return 0.7, 70, "MEDIUM"
        
        # 3. 숫자 처리
        if raw_value is not None:
            try:
                val = float(raw_value)
                # 0-1 범위면 그대로, 아니면 100으로 나눔
                normalized = val if val <= 1.0 else val / 100.0
                # 범위 제한
                normalized = max(0.0, min(1.0, normalized))
                raw = int(val) if val > 1.0 else int(val * 100)
                label = cls._get_label(normalized)
                return normalized, raw, label
            except (ValueError, TypeError):
                pass
        
        # 4. 기본값
        return 0.7, 70, "MEDIUM"
    
    @staticmethod
    def _get_label(normalized: float) -> str:
        """정규화 값 → 레이블"""
        if normalized >= 0.85:
            return "HIGH"
        elif normalized >= 0.60:
            return "MEDIUM"
        else:
            return "LOW"
    
    @classmethod
    def normalize_threat_type(cls, raw_type: str) -> str:
        """위협유형 표준화"""
        if not raw_type or not isinstance(raw_type, str) or raw_type == "N/A":
            return "일반적 침입"
            
        raw_type = raw_type.strip()
        
        # 매핑 테이블
        mapping = {
            "침투": ["침투", "침입", "intrusion", "infiltration"],
            "포격": ["포격", "포탄", "shelling", "artillery"],
            "기습공격": ["기습", "공격", "surprise", "attack"],
            "사이버": ["사이버", "해킹", "cyber", "hacking"],
            "국지도발": ["도발", "분쟁", "provocation"],
            "공중위협": ["공중", "항공", "헬기", "air", "aviation", "helicopter"]
        }
        
        for standardized, keywords in mapping.items():
            if any(k.lower() in raw_type.lower() for k in keywords):
                return standardized
                
        return raw_type # 매칭되는 게 없으면 원본 반환
    
    @classmethod
    def _convert_real_data(cls, data: Dict, **kwargs) -> Dict:
        """실제 데이터 테이블 변환"""
        # ID 추출
        situation_id = cls._extract_field(data, [
            '위협ID', 'ID', 'threat_id', '임무ID', 'mission_id'
        ])
        
        # 위협수준 추출 및 정규화
        threat_level_raw_value = cls._extract_field(data, [
            '위협수준', '위협수준_숫자', '심각도', 'threat_level', 'severity'
        ])
        normalized, raw, label = cls.normalize_threat_level(threat_level_raw_value)
        
        # 위협유형 (위협유형코드 우선)
        raw_threat_type = cls._extract_field(data, [
            '위협유형코드', '위협유형', 'threat_type_code', 'threat_type'
        ])
        threat_type = cls.normalize_threat_type(raw_threat_type)
        
        # 위치
        location = cls._extract_field(data, [
            '발생장소', '발생위치', 'location', '발생위치셀ID'
        ])
        
        # 축선
        axis_id = cls._extract_field(data, [
            '관련축선ID', 'axis_id', 'related_axis_id'
        ])
        
        # 탐지시각
        detection_time = cls._extract_field(data, [
            '탐지시각', '발생시각', 'detection_time', 'occurrence_time'
        ])
        
        # 근거
        evidence = cls._extract_field(data, [
            '근거', '원시보고텍스트', 'evidence', 'raw_report_text'
        ])
        
        return {
            # 필수 (새 표준 필드)
            "situation_id": situation_id or f"UNK_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "threat_level_normalized": normalized,
            "threat_level_raw": raw,
            "threat_level_label": label,
            "approach_mode": kwargs.get("approach_mode", "threat_centered"),
            "timestamp": datetime.now().isoformat(),
            
            # 선택 (위협 중심)
            "threat_id": situation_id,
            "threat_type": threat_type,
            "threat_type_original": raw_threat_type,
            "threat_type_code": threat_type,
            "location": location or "N/A",
            "axis_id": axis_id or "N/A",
            "detection_time": str(detection_time) if detection_time else "",
            "evidence": evidence or "",
            
            # 메타데이터
            "source_type": "real_data",
            "is_real_data": True,
            "is_manual": False,
            "is_demo": False,
            "is_sitrep": False,
            
            # 하위호환 (기존 필드명)
            "위협ID": situation_id,
            "위협유형": threat_type or "N/A",
            "위협수준": threat_level_raw_value if threat_level_raw_value is not None else str(raw),
            "심각도": raw,
            "threat_level": normalized,
            "발생장소": location or "N/A",
            "관련축선ID": axis_id or "N/A"
        }
    
    @classmethod
    def _convert_manual(cls, data: Dict, **kwargs) -> Dict:
        """수동 입력 변환"""
        # 수동 입력은 이미 정규화된 값 사용
        threat_level_val = data.get("threat_level", 0.7)
        normalized = float(threat_level_val)
        raw = int(normalized * 100) if normalized <= 1.0 else int(normalized)
        label = cls._get_label(normalized)
        
        # 접근 방식 (kwargs에서 우선, 없으면 data에서)
        approach_mode = kwargs.get("approach_mode") or data.get("approach_mode", "threat_centered")
        
        result = {
            "situation_id": data.get("situation_id"),
            "threat_level_normalized": normalized,
            "threat_level_raw": raw,
            "threat_level_label": label,
            "approach_mode": approach_mode,
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            
            # 메타데이터
            "source_type": "manual",
            "is_manual": True,
            "is_real_data": False,
            "is_demo": False,
            "is_sitrep": False,
            
            # 추가 정보
            "location": data.get("location", "N/A"),
            "defense_assets": data.get("defense_assets", {}),
            "enemy_units": data.get("enemy_units", ""),
            "friendly_units": data.get("friendly_units", ""),
            "additional_context": data.get("additional_context", ""),
            
            # 하위호환
            "threat_level": normalized,
            "위협수준": str(raw),
            "심각도": raw
        }
        
        # 임무 중심인 경우 mission_id 보존
        if approach_mode == "mission_centered":
            mission_id = data.get("mission_id") or data.get("임무ID")
            if mission_id:
                result["mission_id"] = mission_id
                result["임무ID"] = mission_id
            # 임무 관련 필드 보존
            for field in ["임무명", "임무종류", "주요축선ID", "주축선ID", "임무목표"]:
                if field in data:
                    result[field] = data[field]
        
        # 위협 중심인 경우 위협 관련 필드 보존
        if approach_mode == "threat_centered":
            for field in ["위협ID", "위협유형", "위협유형코드", "관련축선ID", "발생장소"]:
                if field in data:
                    result[field] = data[field]
        
        return result
    
    @classmethod
    def _convert_sitrep(cls, data: Dict, **kwargs) -> Dict:
        """SITREP 텍스트 변환 (LLM 파싱 결과)"""
        # SITREP은 LLM이 이미 파싱한 결과 사용
        normalized, raw, label = cls.normalize_threat_level(
            data.get("estimated_threat_level", 0.7)
        )
        
        return {
            "situation_id": data.get("situation_id", f"SITREP_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            "threat_level_normalized": normalized,
            "threat_level_raw": raw,
            "threat_level_label": label,
            "approach_mode": "threat_centered",
            "timestamp": datetime.now().isoformat(),
            
            # SITREP 특화
            "evidence": data.get("sitrep_text", ""),
            "threat_type": data.get("parsed_threat_type", "N/A"),
            "location": data.get("parsed_location", "N/A"),
            
            # 메타데이터
            "source_type": "sitrep",
            "is_sitrep": True,
            "is_manual": False,
            "is_real_data": False,
            "is_demo": False,
            
            # 하위호환
            "threat_level": normalized,
            "위협수준": str(raw),
            "심각도": raw
        }
    
    @classmethod
    def _convert_demo(cls, data: Dict, **kwargs) -> Dict:
        """데모 시나리오 변환"""
        normalized, raw, label = cls.normalize_threat_level(
            data.get("threat_level", 0.85)
        )
        
        return {
            **data,  # 데모는 이미 완전한 형식
            "threat_level_normalized": normalized,
            "threat_level_raw": raw,
            "threat_level_label": label,
            "timestamp": datetime.now().isoformat(),
            
            # 메타데이터
            "source_type": "demo",
            "is_demo": True,
            "is_manual": False,
            "is_real_data": False,
            "is_sitrep": False,
            
            # 하위호환
            "threat_level": normalized,
            "위협수준": str(raw) if "위협수준" not in data else data["위협수준"],
            "심각도": raw if "심각도" not in data else data["심각도"]
        }
    
    @staticmethod
    def _extract_field(data: Dict, field_candidates: List[str]) -> Optional[str]:
        """여러 필드명 후보에서 값 추출"""
        for field in field_candidates:
            if field in data and data[field] is not None:
                val = data[field]
                # Pandas NaT, None, NaN 처리
                if pd.isna(val):
                    continue
                return str(val) if not isinstance(val, str) else val
        return None
    
    @classmethod
    def validate(cls, situation_info: Dict) -> Tuple[bool, List[str]]:
        """
        situation_info 검증
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # 필수 필드 확인
        required = ["situation_id", "threat_level_normalized", "approach_mode"]
        for field in required:
            if field not in situation_info or situation_info[field] is None:
                errors.append(f"필수 필드 누락: {field}")
        
        # 값 범위 확인
        if "threat_level_normalized" in situation_info:
            val = situation_info["threat_level_normalized"]
            try:
                val_float = float(val)
                if not (0.0 <= val_float <= 1.0):
                    errors.append(f"threat_level_normalized 범위 오류: {val} (0-1 필요)")
            except (ValueError, TypeError):
                errors.append(f"threat_level_normalized 타입 오류: {val}")
        
        if "threat_level_raw" in situation_info:
            val = situation_info["threat_level_raw"]
            try:
                val_int = int(val)
                if not (0 <= val_int <= 100):
                    errors.append(f"threat_level_raw 범위 오류: {val} (0-100 필요)")
            except (ValueError, TypeError):
                errors.append(f"threat_level_raw 타입 오류: {val}")
        
        # approach_mode 확인
        if "approach_mode" in situation_info:
            val = situation_info["approach_mode"]
            if val not in ["threat_centered", "mission_centered"]:
                errors.append(f"approach_mode 값 오류: {val}")
        
        return (len(errors) == 0, errors)
