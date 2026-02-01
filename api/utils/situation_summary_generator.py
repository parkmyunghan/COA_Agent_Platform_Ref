# api/utils/situation_summary_generator.py
# -*- coding: utf-8 -*-
"""
정황보고 생성 유틸리티
LLM 기반 생성 실패 시 템플릿 기반 fallback 제공
"""
from typing import Dict, Any, Optional
import math
import re

try:
    from .code_label_mapper import get_mapper
    _mapper = get_mapper()
except Exception as e:
    print(f"[SituationSummaryGenerator] 코드 매핑 로더 초기화 실패: {e}")
    _mapper = None


def generate_template_based_summary(situation_info: Dict[str, Any]) -> str:
    """
    템플릿 기반 정황보고 생성 (프론트엔드 로직과 동일)
    
    Args:
        situation_info: 상황 정보 딕셔너리
        
    Returns:
        정황보고 문자열 (Markdown 형식)
    """
    if not situation_info:
        return ""
    
    approach_mode = situation_info.get('approach_mode', 'threat_centered')
    is_mission_centered = approach_mode == 'mission_centered'
    
    # 시간 정보 (ISO 8601 형식을 사용자 친화적 형식으로 변환)
    time_str = situation_info.get('time_str') or situation_info.get('occurrence_time') or situation_info.get('timestamp') or ''
    
    # ISO 8601 형식 변환 (예: "2025-01-01T23:10:00" -> "23:10")
    if time_str:
        try:
            from datetime import datetime
            # ISO 8601 형식 파싱 시도
            if 'T' in str(time_str):
                # ISO 8601 형식: "2025-01-01T23:10:00" 또는 "2025-01-01T23:10:00.000Z"
                dt = datetime.fromisoformat(str(time_str).replace('Z', '+00:00'))
                # 시간만 추출 (예: "23:10")
                time_str = dt.strftime('%H:%M')
            elif ':' in str(time_str):
                # 이미 시간 형식인 경우 (예: "23:10")
                time_str = str(time_str)
            else:
                # 다른 형식은 그대로 사용
                time_str = str(time_str)
        except (ValueError, AttributeError, TypeError):
            # 파싱 실패 시 원본 사용
            time_str = str(time_str)
    
    time_prefix = f"{time_str} 현재, " if time_str else ''
    
    # 위치 정보 (우선순위: 발생지역+발생지형명 > 발생지형명 > 발생장소 > location)
    location_region = situation_info.get('발생지역') or situation_info.get('location_region') or ''
    location_name = situation_info.get('발생지형명') or situation_info.get('location_name') or ''
    location_cell = situation_info.get('발생장소') or situation_info.get('location') or ''
    
    location_display = ''
    if location_region and location_name and location_region != 'N/A' and location_name != 'N/A':
        location_display = f"{location_region} {location_name}"
    elif location_name and location_name != 'N/A':
        location_display = location_name
    elif location_cell:
        # 코드를 한글로 변환 시도
        if _mapper:
            loc_label = _mapper.get_terrain_label(location_cell)
            if loc_label and loc_label != location_cell:
                location_display = f"{loc_label} ({location_cell})"
            else:
                location_display = location_cell
        else:
            location_display = location_cell
    else:
        location_display = '작전 지역'
    
    # 축선 정보 (코드-한글 매핑 적용)
    axis_id = situation_info.get('관련축선ID') or situation_info.get('axis_id') or ''
    axis_name = situation_info.get('관련축선명') or situation_info.get('axis_name') or ''
    axis_display = ''
    if axis_id:
        # 코드를 한글로 변환
        if _mapper:
            axis_label = _mapper.get_axis_label(axis_id)
            if axis_label and axis_label != axis_id:
                axis_display = f"{axis_label} ({axis_id})"
            else:
                axis_display = axis_id
        elif axis_name and axis_name != 'N/A':
            axis_display = f"{axis_name} ({axis_id})"
        else:
            axis_display = axis_id
    
    # 위협 수준/임무 성공 가능성
    threat_level = situation_info.get('threat_level') or situation_info.get('위협수준')
    level_text = '미상'
    level_percent = ''
    
    # pandas NaN 체크
    try:
        import pandas as pd
        if pd.isna(threat_level):
            threat_level = None
    except (ImportError, AttributeError, TypeError):
        pass
    
    if threat_level is not None and threat_level != '' and str(threat_level).strip().lower() not in ['', 'n/a', 'none', 'null', 'nan', 'inf', 'infinity']:
        try:
            # 이미 float인 경우 (NaN 체크)
            if isinstance(threat_level, (int, float)):
                if math.isnan(threat_level) or math.isinf(threat_level):
                    raise ValueError("Invalid numeric value (NaN or Inf)")
                level = float(threat_level)
            # 문자열인 경우 숫자 부분만 추출
            elif isinstance(threat_level, str):
                # NaN 문자열 체크
                threat_level_lower = threat_level.lower().strip()
                if threat_level_lower in ['nan', 'none', 'null', '', 'inf', 'infinity']:
                    raise ValueError("Invalid string value")
                # 숫자만 추출 (예: "50.0", "50%", "50.0%" 등)
                match = re.search(r'(\d+\.?\d*)', str(threat_level))
                if match:
                    level = float(match.group(1))
                    # NaN 체크
                    if math.isnan(level) or math.isinf(level):
                        raise ValueError("Extracted value is NaN or Inf")
                else:
                    raise ValueError("No numeric value found")
            else:
                level = float(threat_level)
                if math.isnan(level) or math.isinf(level):
                    raise ValueError("Converted value is NaN or Inf")
            
            # 유효한 범위인지 확인
            if not (0 <= level <= 100):
                # 0-1 범위로 정규화된 값일 수 있음
                if 0 <= level <= 1:
                    normalized_level = level
                else:
                    raise ValueError("Level out of valid range")
            else:
                normalized_level = level / 100 if level > 1 else level
            
            # 정규화된 레벨이 유효한 범위인지 확인 (NaN 체크 포함)
            if not math.isnan(normalized_level) and not math.isinf(normalized_level) and 0 <= normalized_level <= 1:
                percent_value = normalized_level * 100
                # NaN이나 무한대가 아닌지 확인
                if not math.isnan(percent_value) and not math.isinf(percent_value):
                    percent_int = int(round(percent_value))
                    # 최종 정수 값도 NaN이 아닌지 확인
                    if not math.isnan(percent_int) and not math.isinf(percent_int) and 0 <= percent_int <= 100:
                        level_percent = f"{percent_int}%"
                        
                        if is_mission_centered:
                            if normalized_level >= 0.8:
                                level_text = '낮음'
                            elif normalized_level >= 0.5:
                                level_text = '보통'
                            else:
                                level_text = '높음'
                        else:
                            if normalized_level >= 0.8:
                                level_text = '높음'
                            elif normalized_level >= 0.5:
                                level_text = '중간'
                            else:
                                level_text = '낮음'
                    else:
                        # 최종 값이 유효하지 않으면 level_percent는 빈 문자열로 유지
                        pass
                else:
                    # NaN이나 무한대면 level_percent는 빈 문자열로 유지
                    pass
            else:
                # 유효하지 않은 값이면 level_percent는 빈 문자열로 유지
                pass
        except (ValueError, TypeError, AttributeError, OverflowError) as e:
            # 파싱 실패 시 level_percent는 빈 문자열로 유지
            pass
    
    # 상황 설명
    description = situation_info.get('상황설명') or situation_info.get('description') or situation_info.get('raw_report_text') or ''
    
    if is_mission_centered:
        # 임무 중심 모드
        mission_name = situation_info.get('임무명') or situation_info.get('mission_name') or '기본 임무'
        mission_id = situation_info.get('임무ID') or situation_info.get('mission_id') or 'N/A'
        mission_type = situation_info.get('임무유형') or situation_info.get('mission_type') or ''
        mission_objective = situation_info.get('임무목표') or situation_info.get('mission_objective') or ''
        
        summary = f"{time_prefix}{location_display} 일대에서 **{mission_name}**({mission_id}) 임무가 하달되었습니다."
        
        if mission_type:
            summary += f" 임무 유형은 **{mission_type}**이며,"
        
        if axis_display:
            summary += f" 주요 작전 축선은 **{axis_display}** 방향입니다."
        else:
            summary += " 주요 작전 축선은 미지정입니다."
        
        if mission_objective:
            summary += f" 임무 목표는 {mission_objective}입니다."
        
        if level_percent:
            summary += f" 현재 분석된 임무 성공 가능성은 **{level_text}** 수준({level_percent})으로 평가됩니다."
        
        if description:
            summary += f" {description}"
        
        return summary
    else:
        # 위협 중심 모드
        threat_type_raw = situation_info.get('위협유형') or situation_info.get('threat_type') or situation_info.get('threat_type_code') or '미상'
        
        # 위협 유형 코드를 한글로 변환
        threat_type = '미상'
        if _mapper and threat_type_raw and threat_type_raw != '미상':
            threat_type_label = _mapper.get_threat_type_label(threat_type_raw)
            # 코드와 라벨이 다른 경우 병행 표기
            if threat_type_label and threat_type_label != threat_type_raw:
                threat_type = f"{threat_type_label} ({threat_type_raw})"
            else:
                threat_type = threat_type_raw
        else:
            threat_type = threat_type_raw if threat_type_raw else '미상'
        
        enemy_unit = situation_info.get('enemy_units') or situation_info.get('적부대') or ''
        threat_id = situation_info.get('selected_threat_id') or situation_info.get('threat_id') or situation_info.get('situation_id') or 'N/A'
        
        summary = f"{time_prefix}{location_display} 일대에서"
        
        if enemy_unit and enemy_unit not in ['****', 'N/A', '']:
            summary += f" **{enemy_unit}**에 의한"
        else:
            summary += " 미상의 위협원에 의한"
        
        summary += f" **{threat_type}** 위협이 식별되었습니다."
        
        if threat_id and threat_id != 'N/A':
            # 위협 ID에 위협 유형 정보 추가 (선택적)
            if _mapper:
                threat_id_label = _mapper.get_threat_id_label(threat_id)
                if threat_id_label:
                    summary += f" 위협 식별 번호는 **{threat_id} ({threat_id_label})**입니다."
                else:
                    summary += f" 위협 식별 번호는 **{threat_id}**입니다."
            else:
                summary += f" 위협 식별 번호는 **{threat_id}**입니다."
        
        if axis_display:
            summary += f" **{axis_display}** 방향 위협 수준은 **{level_text}** 상태"
        else:
            summary += f" 위협 수준은 **{level_text}** 상태"
        
        if level_percent:
            summary += f"({level_percent})로 분석됩니다."
        else:
            summary += "입니다."
        
        if description:
            summary += f" {description}"
        
        return summary
