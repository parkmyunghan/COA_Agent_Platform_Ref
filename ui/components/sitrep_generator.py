# ui/components/sitrep_generator.py
# -*- coding: utf-8 -*-
"""
SITREP 텍스트 생성 유틸리티
실제데이터나 데모시나리오로부터 SITREP 텍스트 생성
"""
import pandas as pd
from typing import Dict, Optional


def generate_sitrep_from_real_data(threat_data: Dict, situation_info: Dict) -> str:
    """
    실제데이터로부터 SITREP 텍스트 생성 (situation_info 기반으로 정확하게)
    
    Args:
        threat_data: 위협 데이터 딕셔너리 (DataFrame row)
        situation_info: situation_info 딕셔너리
    
    Returns:
        SITREP 텍스트
    """
    # 원시보고텍스트가 있으면 사용하되, 위협수준과 축선 정보를 situation_info 기반으로 보정
    raw_text = threat_data.get('원시보고텍스트', '')
    if raw_text and pd.notna(raw_text) and str(raw_text).strip():
        raw_text_str = str(raw_text)
        needs_update = False
        
        # situation_info에서 정확한 축선 정보 가져오기 (우선 사용)
        axis = situation_info.get('관련축선ID', threat_data.get('관련축선ID', 'AXIS01'))
        axis_map = {'AXIS01': '동부 주공축선', 'AXIS02': '서부 조공축선', 'AXIS03': '북부', 'AXIS04': '남부'}
        axis_kr = axis_map.get(axis, axis if axis != 'N/A' else '주공축선')
        
        # 원시보고텍스트에서 잘못된 축선 정보 제거 (situation_info의 정확한 정보로 교체)
        axis_keywords_to_remove = ['동부', '서부', '북부', '남부', '주공축선', '조공축선', '주공', '조공', '축선']
        has_axis_info = any(keyword in raw_text_str for keyword in axis_keywords_to_remove)
        
        # 잘못된 축선 정보가 있으면 제거하고 올바른 축선 정보로 교체
        if has_axis_info:
            # 축선 관련 패턴 제거 (예: "서부 축선", "동부 주공축선", "축선(TERR006" 등)
            import re
            # 축선 관련 패턴 찾기 및 제거
            axis_patterns = [
                r'[동서북남]부\s*(?:주공|조공)?축선',
                r'[동서북남]부\s*축선',
                r'주공\s*축선',
                r'조공\s*축선',
                r'축선\s*\([^)]+\)',
                r'축선\s*[동서북남]',
            ]
            for pattern in axis_patterns:
                raw_text_str = re.sub(pattern, '', raw_text_str, flags=re.IGNORECASE)
            # 연속된 공백 정리
            raw_text_str = re.sub(r'\s+', ' ', raw_text_str).strip()
            needs_update = True
        
        # 위협수준이 텍스트에 없으면 추가
        threat_level_raw = situation_info.get('위협수준', '')
        level_kr = None
        if threat_level_raw and '위협수준' not in raw_text_str and '위협 수준' not in raw_text_str:
            # 위협수준을 한글로 변환
            if isinstance(threat_level_raw, str):
                level_upper = threat_level_raw.upper()
                if level_upper in ['HIGH', '높음', 'H']:
                    level_kr = '높음'
                elif level_upper in ['MEDIUM', '보통', 'M', '중간']:
                    level_kr = '보통'
                elif level_upper in ['LOW', '낮음', 'L']:
                    level_kr = '낮음'
                else:
                    level_kr = '보통'
            else:
                level_num = float(threat_level_raw) if threat_level_raw else 50
                if level_num >= 80:
                    level_kr = '높음'
                elif level_num >= 50:
                    level_kr = '보통'
                else:
                    level_kr = '낮음'
            needs_update = True
        
        # 올바른 축선 정보 추가 (situation_info 기반)
        if axis and axis != 'N/A':
            needs_update = True
        
        # 필요한 정보 추가
        if needs_update:
            additions = []
            if axis and axis != 'N/A':
                additions.append(f"{axis_kr} 방향")
            if level_kr:
                additions.append(f"위협수준 {level_kr}")
            
            if additions:
                raw_text_str = f"{raw_text_str} {' '.join(additions)}."
        
        return raw_text_str
    
    # situation_info를 기반으로 SITREP 생성
    threat_type = situation_info.get('위협유형', threat_data.get('위협유형코드', '침투'))
    threat_level_raw = situation_info.get('위협수준', threat_data.get('위협수준', 'High'))
    location = situation_info.get('발생장소', threat_data.get('발생위치셀ID', 'TERR003'))
    axis = situation_info.get('관련축선ID', threat_data.get('관련축선ID', 'AXIS01'))
    time = threat_data.get('발생시각', '')
    
    # 위협수준 변환 (situation_info의 원본 값 사용)
    if isinstance(threat_level_raw, str):
        level_upper = threat_level_raw.upper()
        if level_upper in ['HIGH', '높음', 'H']:
            level_kr = '높음'
        elif level_upper in ['MEDIUM', '보통', 'M', '중간']:
            level_kr = '보통'
        elif level_upper in ['LOW', '낮음', 'L']:
            level_kr = '낮음'
        else:
            # 숫자 문자열인 경우
            try:
                level_num = float(str(threat_level_raw).replace(',', ''))
                if level_num >= 80:
                    level_kr = '높음'
                elif level_num >= 50:
                    level_kr = '보통'
                else:
                    level_kr = '낮음'
            except:
                level_kr = '보통'
    else:
        # 숫자인 경우
        level_num = float(threat_level_raw) if threat_level_raw else 50
        if level_num >= 80:
            level_kr = '높음'
        elif level_num >= 50:
            level_kr = '보통'
        else:
            level_kr = '낮음'
    
    # 축선 변환
    axis_map = {'AXIS01': '동부 주공축선', 'AXIS02': '서부 조공축선', 'AXIS03': '북부', 'AXIS04': '남부'}
    axis_kr = axis_map.get(axis, axis if axis != 'N/A' else '주공축선')
    
    # 위협유형 한글 변환
    type_map = {
        'ARMOR': '전차', 'ARTILLERY': '포병', 'INFANTRY': '보병',
        'AIR': '항공', 'MISSILE': '미사일', 'CBRN': 'CBRN',
        'CYBER': '사이버', '침투': '기계화보병', '공격': '전차'
    }
    threat_type_kr = type_map.get(threat_type, threat_type)
    
    # 시간 포맷팅
    time_str = ''
    if time and pd.notna(time):
        if isinstance(time, pd.Timestamp):
            time_str = time.strftime('%H:%M')
        else:
            time_str = str(time)
    
    # SITREP 텍스트 생성
    if time_str:
        sitrep = f"{time_str} 현재, 적 {threat_type_kr} 대대가 {axis_kr}({location}) 지역으로 침투 중으로 판단됨. 위협수준 {level_kr}."
    else:
        sitrep = f"적 {threat_type_kr} 대대가 {axis_kr}({location}) 지역으로 침투 중으로 판단됨. 위협수준 {level_kr}."
    
    return sitrep


def generate_sitrep_from_demo(scenario: Dict) -> str:
    """
    데모시나리오로부터 SITREP 텍스트 생성
    
    Args:
        scenario: 데모 시나리오 딕셔너리
    
    Returns:
        SITREP 텍스트
    """
    threat_type = scenario.get('threat_type', '공격')
    severity = scenario.get('severity', 90)
    location = scenario.get('location', '전방기지')
    enemy_info = scenario.get('enemy_info', '')
    friendly_info = scenario.get('friendly_info', '')
    
    # 축선 정보 가져오기 (시나리오에 있으면 사용, 없으면 기본값)
    axis_id = scenario.get('axis_id', scenario.get('관련축선ID', 'AXIS01'))
    axis_map = {'AXIS01': '동부 주공축선', 'AXIS02': '서부 조공축선', 'AXIS03': '북부', 'AXIS04': '남부'}
    axis_kr = axis_map.get(axis_id, axis_id if axis_id != 'N/A' else '주공축선')
    
    # 위협수준 변환
    if severity >= 80:
        level = '높음'
    elif severity >= 50:
        level = '보통'
    else:
        level = '낮음'
    
    # 위협유형 한글 변환
    type_map = {
        'ARMOR': '전차', 'ARTILLERY': '포병', 'INFANTRY': '보병',
        'AIR': '항공', 'MISSILE': '미사일', 'CBRN': 'CBRN',
        'CYBER': '사이버', '침투': '기계화보병', '공격': '전차',
        '정찰': '정찰기', '정보수집': '정보수집', '보급': '보급선'
    }
    threat_type_kr = type_map.get(threat_type, threat_type)
    
    # enemy_info에 축선 정보가 이미 포함되어 있는지 확인
    axis_keywords = ['동부', '서부', '북부', '남부', '주공축선', '조공축선', '주공', '조공', '축선']
    has_axis_in_enemy_info = any(keyword in enemy_info for keyword in axis_keywords)
    
    # SITREP 텍스트 생성 (축선 정보 포함)
    if has_axis_in_enemy_info:
        # enemy_info에 이미 축선 정보가 있으면 그대로 사용
        sitrep = f"{enemy_info}. 위협수준 {level} ({severity}%). {friendly_info}."
    else:
        # enemy_info에 축선 정보가 없으면 추가
        sitrep = f"{enemy_info} {axis_kr} 방향. 위협수준 {level} ({severity}%). {friendly_info}."
    
    return sitrep

