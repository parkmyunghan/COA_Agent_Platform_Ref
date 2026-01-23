# core_pipeline/coa_engine/llm_services.py
# -*- coding: utf-8 -*-
"""
LLM Services for COA Engine
COA 엔진을 위한 LLM 서비스 레이어 (보조 기능만)
"""
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
import re

from core_pipeline.data_models import ThreatEvent

if TYPE_CHECKING:
    from core_pipeline.coa_engine.coa_models import COA
    from core_pipeline.coa_engine.coa_evaluator import COAEvaluationResult


class SITREPParser:
    """SITREP 텍스트 파서 (LLM 기반)"""
    
    def __init__(self, llm_manager=None):
        """
        Args:
            llm_manager: LLMManager 인스턴스 (선택적)
        """
        self.llm_manager = llm_manager
    
    def parse_sitrep_to_threat_event(
        self,
        sitrep_text: str,
        mission_id: str,
        use_llm: bool = True
    ) -> ThreatEvent:
        """
        SITREP 텍스트를 ThreatEvent 객체로 변환
        
        Args:
            sitrep_text: 상황보고(SITREP) 텍스트
            mission_id: 임무ID
            use_llm: LLM 사용 여부 (False면 규칙 기반 파싱)
            
        Returns:
            ThreatEvent 객체
        """
        if use_llm and self.llm_manager and self.llm_manager.is_available():
            return self._parse_with_llm(sitrep_text, mission_id)
        else:
            return self._parse_with_rules(sitrep_text, mission_id)
    
    def _parse_with_llm(self, sitrep_text: str, mission_id: str, max_retries: int = 3) -> ThreatEvent:
        """
        LLM을 사용한 SITREP 파싱 (재시도 로직 포함)
        
        Args:
            sitrep_text: SITREP 텍스트
            mission_id: 임무ID
            max_retries: 최대 재시도 횟수 (기본: 3)
        """
        prompt = f"""다음 상황보고(SITREP) 텍스트를 분석하여 구조화된 위협상황 정보를 JSON 형식으로 추출하세요.

## 입력 텍스트:
{sitrep_text}

## 출력 형식 (JSON):
    "threat_type_code": "위협유형코드 (ARMOR, ARTILLERY, INFANTRY, AIR, MISSILE, CBRN, CYBER, INFILTRATION, UNKNOWN 중 하나)",
    "threat_type_original": "원문에 표현된 구체적인 위협/행동 명칭 (예: 남하 침투, 포격 도발 등)",
    "threat_level": "위협수준 (High, Medium, Low 중 하나)",
    "location_cell_id": "발생위치셀ID (TERR001, GRID_1234 등. 텍스트에 지명이나 ID가 있으면 반드시 추출)",
    "related_axis_id": "관련축선ID (키워드 매핑 규칙 준수)",
    "occurrence_time": "발생시각 (HH:MM 또는 YYYY-MM-DD HH:MM:SS 형식)",
    "related_enemy_unit_id": "관련 적부대ID (ENU_ESTIMATED 등)",
    "enemy_unit_original": "원문에 표현된 구체적인 적 부대 명칭 (예: 기계화보병 대대, 미상의 특수작전부대 등)",
    "confidence": "확실도 (0-100 숫자)",
    "related_mission_id": "관련 임무ID (MSN으로 시작하는 ID가 언급된 경우, 예: MSN001)",
    "remarks": "핵심 상황 요약 (원문의 구체성을 살려 1문장으로 작성. 예: 기계화보병 대대가 TERR003 지역으로 남하 침투 중)"
}}

## 추출 규칙:
1. **related_axis_id (관련축선ID)**:
   - 텍스트에 방향/축선 관련 키워드가 **있는 경우에만** 추출
   - 키워드 매핑 (우선순위 높은 것부터 적용):
     * "동해안", "동해" → "AXIS11" (동해안축선)
     * "상륙축선", "상륙" → "AXIS08" (북부 보조축선/상륙축선)
     * "동부 주공축선" 또는 "주공축선" 또는 "주공" → "AXIS01"
     * "서부 조공축선" 또는 "조공축선" 또는 "조공" → "AXIS02"
     * "북부" 또는 "북쪽" → "AXIS03"
     * "남부" 또는 "남쪽" → "AXIS04"
     * "동부" (단독) → "AXIS01" (단, "동해안/동해"가 아닌 경우만)
     * "서부" (단독) → "AXIS02"
     * "해안" (단독) → "AXIS11" (기본적으로 동해안)
   - **키워드가 없으면 null 사용**

2. **location_cell_id (발생위치셀ID)**:
   - 명시적 ID가 있으면 그대로 추출: TERR001, GRID_1234 등
   - 자연어 위치 키워드 매핑 (우선순위 순서):
     * "동해안 휴전선", "동해안", "동해" → "TERR031" (동해안 휴전선 해안 지역)
     * "상륙", "상륙축선" → "TERR008" (서해안 상륙 지역)
     * "휴전선", "DMZ", "전방" → "TERR001" (중부 휴전선)
     * "고지", "능선" → "TERR003"
     * "계곡", "평야" → "TERR002"
     * "해안" (단독) → "TERR031" (기본적으로 동해안)
   - **명확한 위치가 없으면 null 사용**

3. **related_enemy_unit_id (관련 적부대ID)**:
   - 텍스트에 적군 부대가 언급된 경우 "ENU_ESTIMATED" 사용
   - 인식 키워드 (조사 포함 가능):
     * "적 전차부대", "적 전차부대가", "적 전차부대는", "적 전차부대를" 등
     * "적군 기갑부대", "적군 기갑부대가" 등
     * "적 부대", "적군 부대" 등
     * "전차부대", "기갑부대", "보병부대" 등 (단독 언급 시)
     * "적", "적군", "적 정찰기", "정찰기" (단독 언급 시)
   - 구체적인 부대ID (예: ENU001, ENU002)가 있으면 그대로 사용
   - **언급이 없으면 null 사용**

4. **threat_type_code (위협유형코드)**:
   - "침투" → "INFILTRATION"
   - "전차", "기갑" → "ARMOR"
   - "포병", "포격", "포" → "ARTILLERY"
   - "보병" → "INFANTRY"
   - "항공", "비행기", "헬기", "정찰기", "공중" → "AIR"
   - "미사일" → "MISSILE"
   - 없으면 "UNKNOWN"

5. **threat_level (위협수준)**:
   - "높음", "high", "위험" → "High"
   - "낮음", "low", "미약" → "Low"
   - "보통", "medium", 기본값 → "Medium"

6. **related_mission_id (관련 임무ID)**:
   - 텍스트에 "MSN"으로 시작하는 패턴 (예: MSN001, MSN002)이 있으면 추출
   - 없으면 null 사용

## 예시 1 (축선 정보 있음):
입력: "적 전차부대가 동부 주공축선쪽으로 공격해 오고 있음. 위협수준 높음. (MSN001 관련)"
출력: {{
    "threat_type_code": "ARMOR",
    "threat_level": "High",
    "location_cell_id": null,
    "related_axis_id": "AXIS01",
    "related_enemy_unit_id": "ENU_ESTIMATED",
    "occurrence_time": null,
    "confidence": 80,
    "related_mission_id": "MSN001",
    "remarks": "동부 주공축선 방향 공격"
}}

## 예시 2 (축선 정보 없음):
입력: "적 전차부대가 공격해 오고 있음. 위협수준 높음"
출력: {{
    "threat_type_code": "ARMOR",
    "threat_level": "High",
    "location_cell_id": null,
    "related_axis_id": null,
    "related_enemy_unit_id": "ENU_ESTIMATED",
    "occurrence_time": null,
    "confidence": 70,
    "related_mission_id": null,
    "remarks": "축선 정보 없음"
}}

**중요**: 
- JSON 형식으로만 응답하세요 (설명이나 추가 텍스트 없이)
- 키워드가 **있는 경우에만** 추출하고, **없으면 null을 사용**하세요
- 텍스트를 정확히 분석하여 키워드가 있으면 반드시 추출하세요"""

        # 재시도 로직으로 LLM 파싱 시도
        for attempt in range(max_retries):
            try:
                # 재시도 시 프롬프트 강화
                current_prompt = prompt
                if attempt > 0:
                    # 재시도 시 축선 정보 추출 강조
                    axis_keywords = ['축선', '동부', '서부', '주공', '조공']
                    has_axis_keyword = any(kw in sitrep_text for kw in axis_keywords)
                    if has_axis_keyword:
                        current_prompt = prompt + f"""

**재시도 주의사항 (시도 {attempt + 1}/{max_retries}):**
- 입력 텍스트에 "{', '.join([kw for kw in axis_keywords if kw in sitrep_text])}" 키워드가 있습니다.
- related_axis_id 필드에 반드시 값을 설정하세요 (null이 아닌 값).
- 키워드 매핑을 다시 확인하세요."""
                
                response = self.llm_manager.generate(current_prompt, max_tokens=512)
                
                # JSON 추출 (LLM 활용 포함)
                import json
                data = self._extract_json_with_llm_fallback(response, sitrep_text, mission_id, attempt)
                
                if data:
                    # ThreatEvent 객체 생성
                    # 🔥 FIX: 항상 고유한 SITREP 전용 ID 생성 (기존 THR* ID와 충돌 방지)
                    threat_id = f"SITREP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    threat_level = data.get('threat_level', 'Medium')
                    
                    # 위협수준 정규화
                    if isinstance(threat_level, str):
                        threat_level_map = {'High': 'High', 'Medium': 'Medium', 'Low': 'Low', 
                                          'high': 'High', 'medium': 'Medium', 'low': 'Low',
                                          '높음': 'High', '보통': 'Medium', '낮음': 'Low'}
                        threat_level = threat_level_map.get(threat_level, 'Medium')
                    
                    # 발생시각 파싱 강화
                    occurrence_time = None
                    time_val = data.get('occurrence_time')
                    if time_val:
                        try:
                            # 1단계: YYYY-MM-DD HH:MM:SS 시도
                            occurrence_time = datetime.strptime(time_val, '%Y-%m-%d %H:%M:%S')
                        except:
                            try:
                                # 2단계: HH:MM 시도 (오늘 날짜 결합)
                                time_match = re.search(r'(\d{1,2}):(\d{2})', time_val)
                                if time_match:
                                    h, m = time_match.groups()
                                    now = datetime.now()
                                    occurrence_time = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                            except:
                                pass
                    
                    # null 값 정규화
                    location_cell_id = self._normalize_null_value(data.get('location_cell_id'))
                    related_enemy_unit_id = self._normalize_null_value(data.get('related_enemy_unit_id'))
                    related_axis_id = self._normalize_null_value(data.get('related_axis_id'))
                    
                    # 필수 필드 검증 및 재시도
                    if attempt < max_retries - 1:
                        # 관련축선ID가 없고 텍스트에 축선 키워드가 있으면 재시도
                        if not related_axis_id and any(kw in sitrep_text for kw in ['축선', '동부', '서부', '주공', '조공', 'axis']):
                            print(f"[INFO] LLM 파싱 재시도 {attempt + 1}/{max_retries}: 축선 정보 추출 실패")
                            continue
                    
                    return ThreatEvent(
                        threat_id=threat_id,
                        threat_type_code=data.get('threat_type_code', 'UNKNOWN'),
                        threat_level=threat_level,
                        location_cell_id=location_cell_id,
                        related_axis_id=related_axis_id,
                        occurrence_time=occurrence_time,
                        related_enemy_unit_id=related_enemy_unit_id,
                        related_mission_id=self._normalize_null_value(data.get('related_mission_id')) or mission_id,
                        raw_report_text=sitrep_text,
                        confidence=data.get('confidence'),
                        threat_type_original=data.get('threat_type_original'), # NEW
                        enemy_unit_original=data.get('enemy_unit_original'), # NEW
                        remarks=data.get('remarks')
                    )
                else:
                    # JSON 추출 실패 시 재시도
                    if attempt < max_retries - 1:
                        print(f"[INFO] LLM 파싱 재시도 {attempt + 1}/{max_retries}: JSON 추출 실패")
                        continue
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] LLM 파싱 재시도 {attempt + 1}/{max_retries}: {e}")
                    continue
                else:
                    print(f"[ERROR] LLM 기반 SITREP 파싱 최종 실패: {e}")
        
        # 모든 재시도 실패 시 기본값으로 ThreatEvent 생성
        print("[WARN] LLM 파싱 실패. 기본값으로 ThreatEvent 생성합니다.")
        return ThreatEvent(
            threat_id=f"SITREP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            threat_type_code='UNKNOWN',
            threat_level='Medium',
            location_cell_id=None,
            related_axis_id=None,
            occurrence_time=None,
            related_enemy_unit_id=None,
            related_mission_id=mission_id,
            raw_report_text=sitrep_text,
            confidence=0,
            remarks="LLM 파싱 실패"
        )
    
    def _normalize_null_value(self, value) -> Optional[str]:
        """null 값을 None으로 정규화"""
        if value in [None, '', 'null', 'NULL', 'None', 'UNKNOWN', 'unknown']:
            return None
        return str(value) if value is not None else None
    
    def _extract_json_with_llm_fallback(self, response: str, sitrep_text: str, mission_id: str, attempt: int = 0) -> Optional[Dict]:
        """
        LLM 응답에서 JSON 추출 (LLM을 활용한 파싱 포함)
        
        Args:
            response: LLM 응답 텍스트
            sitrep_text: 원본 SITREP 텍스트 (재요청 시 사용)
            mission_id: 임무ID (재요청 시 사용)
            
        Returns:
            파싱된 JSON 딕셔너리 또는 None
        """
        import json
        data = None
        
        # 방법 1: 코드 블록에서 JSON 추출
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if code_block_match:
            try:
                data = json.loads(code_block_match.group(1))
                return data
            except:
                pass
        
        # 방법 2: 첫 번째 { 부터 마지막 } 까지 추출 (중첩된 중괄호 처리)
        if not data:
            brace_count = 0
            start_idx = -1
            for i, char in enumerate(response):
                if char == '{':
                    if start_idx == -1:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        try:
                            json_str = response[start_idx:i+1]
                            data = json.loads(json_str)
                            return data
                        except:
                            start_idx = -1
                            brace_count = 0
        
        # 방법 3: 간단한 패턴 매칭
        if not data:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return data
                except:
                    pass
        
        # 방법 4: LLM을 활용한 JSON 재추출 (파싱 실패 시, 재시도 횟수에 따라)
        if not data and self.llm_manager and self.llm_manager.is_available() and attempt < 2:
            try:
                extraction_prompt = f"""다음 텍스트에서 JSON 형식의 데이터만 정확히 추출하고, 원본 SITREP 텍스트를 참고하여 누락된 정보를 보완하세요.

## 원본 SITREP 텍스트:
{sitrep_text}

## LLM 응답 텍스트:
{response}

## 보완 규칙:
1. JSON 객체만 추출하세요 (설명이나 다른 텍스트는 제외)
2. 유효한 JSON 형식이어야 합니다
3. 원본 SITREP 텍스트를 참고하여 다음 정보를 보완:
   - related_axis_id가 null이거나 없으면, 원본 텍스트에서 "동부", "서부", "주공축선", "조공축선" 등의 키워드를 찾아서 설정
     * "동부" 또는 "주공축선" → "AXIS01"
     * "서부" 또는 "조공축선" → "AXIS02"
     * 키워드가 없으면 null 유지
   - related_enemy_unit_id가 null이거나 없으면, 원본 텍스트에서 적군 부대 언급 확인:
     * "적 전차부대", "적 전차부대가", "적 전차부대는", "적군 기갑부대" 등 → "ENU_ESTIMATED"
     * "적", "적군", "전차부대", "기갑부대" 등 단독 언급 → "ENU_ESTIMATED"
     * 언급이 없으면 null 유지
   - related_mission_id가 null이거나 없으면, 원본 텍스트에서 "MSN" 패턴 확인:
     * "MSN001", "MSN01" 등 → 해당 ID 추출
     * 없으면 null 유지
4. 값이 없으면 null을 사용하세요
5. JSON 형식으로만 응답하세요 (설명 없이)

JSON:"""
                
                extracted_response = self.llm_manager.generate(extraction_prompt, max_tokens=256)
                
                # 추출된 응답에서 JSON 다시 파싱 시도
                # 코드 블록 제거
                extracted_response = re.sub(r'```(?:json)?\s*', '', extracted_response)
                extracted_response = re.sub(r'```\s*', '', extracted_response)
                
                # JSON 객체 추출
                json_match = re.search(r'\{.*\}', extracted_response, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        print("[INFO] LLM을 활용한 JSON 재추출 성공")
                        return data
                    except json.JSONDecodeError as e:
                        print(f"[WARN] LLM 재추출 JSON 파싱 실패: {e}")
                        # 마지막 시도: LLM에게 직접 수정 요청
                        return self._fix_json_with_llm(extracted_response, sitrep_text, mission_id)
            except Exception as e:
                print(f"[WARN] LLM JSON 재추출 실패: {e}")
        
        return None
    
    def _fix_json_with_llm(self, json_text: str, sitrep_text: str, mission_id: str) -> Optional[Dict]:
        """
        잘못된 JSON을 LLM을 활용하여 수정
        
        Args:
            json_text: 파싱 실패한 JSON 텍스트
            sitrep_text: 원본 SITREP 텍스트
            mission_id: 임무ID
            
        Returns:
            수정된 JSON 딕셔너리 또는 None
        """
        import json
        
        fix_prompt = f"""다음 JSON 텍스트에 문법 오류가 있습니다. 올바른 JSON 형식으로 수정하고, 원본 SITREP 텍스트를 참고하여 누락된 정보를 보완하세요.

## 원본 SITREP 텍스트:
{sitrep_text}

## 잘못된 JSON:
{json_text}

## 요구사항:
1. JSON 문법 오류를 수정하세요 (따옴표, 쉼표, 중괄호 등)
2. 다음 필드가 포함되어야 합니다:
   - threat_id: 문자열
   - threat_type_code: 문자열 (ARMOR, ARTILLERY, INFANTRY, AIR, MISSILE, CBRN, CYBER, UNKNOWN 중 하나)
   - threat_level: 문자열 (High, Medium, Low) 또는 숫자
   - location_cell_id: 문자열 또는 null
   - related_axis_id: 문자열 또는 null (원본 텍스트에 "동부", "서부", "주공축선" 등이 있으면 추출, 없으면 null)
   - related_enemy_unit_id: 문자열 또는 null (원본 텍스트에 "적 전차부대", "적 전차부대가", "적군 기갑부대", "적", "적군", "전차부대" 등이 있으면 "ENU_ESTIMATED", 없으면 null)
   - related_mission_id: 문자열 또는 null (MSN 패턴이 있으면 추출, 없으면 null)
   - occurrence_time: 문자열 (YYYY-MM-DD HH:MM:SS) 또는 null
   - confidence: 숫자 (0-100) 또는 null
   - remarks: 문자열 또는 null
3. 원본 SITREP 텍스트를 참고하여 누락된 정보를 보완하세요
4. 값이 없으면 null을 사용하세요
5. JSON 형식으로만 응답하세요 (설명 없이)

수정된 JSON:"""
        
        try:
            fixed_response = self.llm_manager.generate(fix_prompt, max_tokens=256)
            
            # 코드 블록 제거
            fixed_response = re.sub(r'```(?:json)?\s*', '', fixed_response)
            fixed_response = re.sub(r'```\s*', '', fixed_response)
            
            # JSON 객체 추출
            json_match = re.search(r'\{.*\}', fixed_response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    print("[INFO] LLM을 활용한 JSON 수정 성공")
                    return data
                except json.JSONDecodeError as e:
                    print(f"[WARN] LLM 수정 JSON 파싱 실패: {e}")
        except Exception as e:
            print(f"[WARN] LLM JSON 수정 실패: {e}")
        
        return None
    
    def _extract_axis_from_text(self, text: str) -> Optional[str]:
        """
        텍스트에서 축선 정보 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            축선ID 또는 None
        """
        text_lower = text.lower()
        
        # 🔥 FIX: 동해안 키워드 우선 매칭 (가장 높은 우선순위)
        if any(kw in text for kw in ['동해안', '동해']):
            return 'AXIS11'  # 동해안축선
        
        # 상륙 관련 키워드
        if any(kw in text for kw in ['상륙축선', '상륙']):
            return 'AXIS08'  # 상륙축선
        
        # 해안 키워드 (동해안/상륙이 아닌 경우)
        if '해안' in text:
            return 'AXIS11'  # 기본적으로 동해안
        
        # 복합 키워드 우선 매칭 (더 구체적인 패턴)
        if '동부' in text and '주공' in text:
            return 'AXIS01'  # 동부 주공축선
        if '서부' in text and '조공' in text:
            return 'AXIS02'  # 서부 조공축선
        if '동부' in text and '조공' in text:
            return 'AXIS02'  # 동부 조공축선
        if '서부' in text and '주공' in text:
            return 'AXIS01'  # 서부 주공축선
        
        # 단일 키워드 매칭
        axis_keywords = {
            '주공': ['주공', '주공축선', 'main', 'primary'],
            '조공': ['조공', '조공축선', 'secondary'],
            '동부': ['동부', '동쪽', 'east', 'eastern'],
            '서부': ['서부', '서쪽', 'west', 'western'],
            '북부': ['북부', '북쪽', 'north', 'northern'],
            '남부': ['남부', '남쪽', 'south', 'southern']
        }
        
        for axis_type, keywords in axis_keywords.items():
            if any(kw in text_lower for kw in keywords):
                # 축선ID 추정 (실제 데이터와 매칭 필요시 개선)
                if axis_type == '주공':
                    return 'AXIS01'  # 주공축선 기본값
                elif axis_type == '조공':
                    return 'AXIS02'  # 조공축선 기본값
                elif axis_type == '동부':
                    return 'AXIS01'  # 동부축선 기본값
                elif axis_type == '서부':
                    return 'AXIS02'  # 서부축선 기본값
                elif axis_type == '북부':
                    return 'AXIS03'  # 북부축선 기본값
                elif axis_type == '남부':
                    return 'AXIS04'  # 남부축선 기본값
        
        return None
    
    def _parse_with_rules(self, sitrep_text: str, mission_id: str) -> ThreatEvent:
        """규칙 기반 SITREP 파싱 (LLM 없이)"""
        # 기본값 - SITREP 전용 ID로 기존 THR* ID와 충돌 방지
        threat_id = f"SITREP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        threat_type_code = 'UNKNOWN'
        threat_level = 'Medium'
        location_cell_id = None
        related_axis_id = None
        related_enemy_unit_id = None
        
        # 위협유형 키워드 매칭
        text_lower = sitrep_text.lower()
        if any(kw in text_lower for kw in ['침투', 'infiltration']):
            threat_type_code = 'INFILTRATION'
        elif any(kw in text_lower for kw in ['전차', 'tank', 'armor', '기갑']):
            threat_type_code = 'ARMOR'
        elif any(kw in text_lower for kw in ['포병', 'artillery', '포']):
            threat_type_code = 'ARTILLERY'
        elif any(kw in text_lower for kw in ['보병', 'infantry']):
            threat_type_code = 'INFANTRY'
        elif any(kw in text_lower for kw in ['항공', 'air', '비행기', '헬기']):
            threat_type_code = 'AIR'
        elif any(kw in text_lower for kw in ['미사일', 'missile']):
            threat_type_code = 'MISSILE'
        
        # 위협수준 키워드 매칭
        if any(kw in text_lower for kw in ['높음', 'high', '심각', '긴급', '높']):
            threat_level = 'High'
        elif any(kw in text_lower for kw in ['낮음', 'low', '경미']):
            threat_level = 'Low'
        
        # 축선 정보 추출
        related_axis_id = self._extract_axis_from_text(sitrep_text)
        
        # 지형셀ID 또는 그리드 좌표 추출
        # 먼저 명시적 TERR ID 패턴 확인
        terrain_pattern = re.search(r'TERR\d+', sitrep_text, re.IGNORECASE)
        if terrain_pattern:
            location_cell_id = terrain_pattern.group().upper()
        else:
            # 🔥 FIX: 자연어 위치 키워드 매핑 (우선순위 순서)
            if any(kw in sitrep_text for kw in ['동해안 휴전선', '동해안', '동해']):
                location_cell_id = 'TERR031'  # 동해안 휴전선
            elif any(kw in sitrep_text for kw in ['상륙', '상륙축선']):
                location_cell_id = 'TERR008'  # 서해안 상륙 지역
            elif any(kw in sitrep_text for kw in ['휴전선', 'DMZ', '전방']):
                location_cell_id = 'TERR001'  # 중부 휴전선
            elif any(kw in sitrep_text for kw in ['해안']):
                location_cell_id = 'TERR031'  # 기본적으로 동해안
            else:
                # GRID_1234 같은 패턴
                grid_pattern = re.search(r'GRID[_\s]?(\d+)', sitrep_text, re.IGNORECASE)
                if grid_pattern:
                    location_cell_id = f"GRID_{grid_pattern.group(1)}"
                else:
                    # 일반 숫자 패턴 (마지막 수단) - 시간 데이터와 혼동 방지를 위해 제거
                    # numbers = re.findall(r'\d+', sitrep_text)
                    # if numbers:
                    #     location_cell_id = f"GRID_{numbers[0]}"
                    pass
        
        # 적군부대 정보 추출
        if any(kw in sitrep_text for kw in ['적', '적군', 'enemy']):
            # 구체적인 부대ID가 없으면 추정 ID 사용
            related_enemy_unit_id = 'ENU_ESTIMATED'
        
        return ThreatEvent(
            threat_id=threat_id,
            threat_type_code=threat_type_code,
            threat_level=threat_level,
            location_cell_id=location_cell_id,
            related_axis_id=related_axis_id,
            related_enemy_unit_id=related_enemy_unit_id,
            related_mission_id=mission_id,
            raw_report_text=sitrep_text,
            confidence=50,  # 기본값
            remarks="규칙 기반 파싱 결과"
        )


class COAExplanationGenerator:
    """COA 설명문 생성기 (LLM 기반)"""
    
    def __init__(self, llm_manager=None, doctrine_explanation_generator=None):
        """
        Args:
            llm_manager: LLMManager 인스턴스 (선택적)
            doctrine_explanation_generator: DoctrineBasedExplanationGenerator 인스턴스 (선택적)
        """
        self.llm_manager = llm_manager
        self.doctrine_explanation_generator = doctrine_explanation_generator
    
    def generate_coa_explanation(
        self,
        coa_result: 'COAEvaluationResult',
        axis_states: List,
        language: str = 'ko',
        use_llm: bool = True,
        coa_recommendation: Optional[Dict] = None,
        situation_info: Optional[Dict] = None,
        mett_c_analysis: Optional[Dict] = None
    ) -> str:
        """
        COA 평가 결과를 바탕으로 설명문 생성
        
        Args:
            coa_result: COA 평가 결과
            axis_states: 축선별 전장상태 리스트
            language: 언어 ('ko' 또는 'en')
            use_llm: LLM 사용 여부 (False면 템플릿 기반)
            coa_recommendation: COA 추천 결과 (doctrine_references 포함, 선택적)
            situation_info: 상황 정보 (선택적)
            mett_c_analysis: METT-C 분석 결과 (선택적)
            
        Returns:
            설명문 텍스트
        """
        # 🔥 NEW: 교리 참조가 있으면 교리 기반 설명 사용
        if (self.doctrine_explanation_generator and 
            coa_recommendation and 
            coa_recommendation.get('doctrine_references')):
            
            try:
                return self.doctrine_explanation_generator.generate_explanation(
                    coa_recommendation=coa_recommendation,
                    situation_info=situation_info or {},
                    mett_c_analysis=mett_c_analysis or {},
                    axis_states=axis_states
                )
            except Exception as e:
                print(f"[WARN] 교리 기반 설명 생성 실패: {e}. 기본 방식으로 폴백합니다.")
        
        # 기존 방식 (LLM 또는 템플릿 기반)
        if use_llm and self.llm_manager and self.llm_manager.is_available():
            return self._generate_with_llm(coa_result, axis_states, language)
        else:
            return self._generate_with_template(coa_result, axis_states, language)
    
    def _generate_with_llm(
        self,
        coa_result: 'COAEvaluationResult',
        axis_states: List,
        language: str
    ) -> str:
        """LLM을 사용한 설명문 생성"""
        lang_prompt = "한국어로" if language == 'ko' else "in English"
        
        # 축선 정보 요약
        axis_summary = []
        for axis in axis_states[:3]:  # 상위 3개만
            axis_summary.append(
                f"- {axis.axis_name or axis.axis_id}: 위협레벨 {axis.threat_level}, "
                f"전투력 비율 {axis.friendly_combat_power_total}/{axis.enemy_combat_power_total}"
            )
        
        prompt = f"""다음 COA(작전 방안) 평가 결과를 바탕으로 {lang_prompt} 상세한 설명문을 작성하세요.

## COA 정보
- COA ID: {coa_result.coa_id}
- COA 이름: {coa_result.coa_name or 'N/A'}
- 종합 점수: {coa_result.total_score:.4f}

## 평가 요소별 점수
- 전투력 우세도: {coa_result.combat_power_score:.2%}
- 기동 가능성: {coa_result.mobility_score:.2%}
- 제약조건 준수도: {coa_result.constraint_compliance_score:.2%}
- 위협 대응도: {coa_result.threat_response_score:.2%}
- 위험도: {coa_result.risk_score:.2%}

## 축선 정보
{chr(10).join(axis_summary) if axis_summary else "축선 정보 없음"}

## 설명 요청사항
다음 형식으로 설명해주세요:

### 1. COA 개요
이 COA의 주요 특징과 전략을 간단히 설명하세요.

### 2. 장점 (3가지)
이 COA의 주요 장점을 3가지로 나열하세요.

### 3. 단점 및 주의사항 (2가지)
이 COA의 단점이나 주의해야 할 사항을 2가지로 나열하세요.

### 4. 평가 근거
각 평가 요소별로 왜 이 점수가 나왔는지 설명하세요.

### 5. 실행 권고사항
이 COA를 실행할 때 고려해야 할 사항을 제시하세요.

설명은 군사 작전 담당자가 이해하기 쉽도록 전문적이면서도 명확하게 작성해주세요."""

        try:
            explanation = self.llm_manager.generate(prompt, max_tokens=1024)
            return explanation
        except Exception as e:
            print(f"[WARN] LLM 기반 설명문 생성 실패: {e}. 템플릿 기반으로 폴백합니다.")
            return self._generate_with_template(coa_result, axis_states, language)
    
    def _generate_with_template(
        self,
        coa_result: 'COAEvaluationResult',
        axis_states: List,
        language: str
    ) -> str:
        """템플릿 기반 설명문 생성 (LLM 없이)"""
        # 축선 정보 요약
        axis_details = []
        for axis in axis_states:
            axis_name = axis.axis_name or axis.axis_id
            ratio = (axis.friendly_combat_power_total / axis.enemy_combat_power_total 
                     if axis.enemy_combat_power_total > 0 else 0)
            axis_details.append(
                f"- **{axis_name}**: 위협 수준 {axis.threat_level}, 전투력 비율 {ratio:.1f} (아군 {axis.friendly_combat_power_total} / 적군 {axis.enemy_combat_power_total})"
            )
        
        # 상세 결과 메시지 구성
        details = coa_result.details or {}
        detail_msg = "\n".join([f"- {k}: {v}" for k, v in details.items()])
        
        if language == 'ko':
            template = f"""### 1. COA 개요
**COA 명칭**: {coa_result.coa_name or coa_result.coa_id}
이 방책은 종합 점수 **{coa_result.total_score:.2f}**로 평가되었습니다.

### 2. 주요 평가 결과
- **전투력 우세도**: {coa_result.combat_power_score:.0%}
- **기동 가능성**: {coa_result.mobility_score:.0%}
- **위협 대응도**: {coa_result.threat_response_score:.0%}
- **위험도**: {coa_result.risk_score:.0%}

### 3. 축선별 상황 분석
{chr(10).join(axis_details) if axis_details else "분석된 축선 정보가 없습니다."}

### 4. 세부 평가 내용
{detail_msg if detail_msg else coa_result.summary or "평가 결과 요약 참조"}

### 5. 아군 부대 운용 계획
해당 방책의 작전 목표 달성을 위해 배정된 아군 부대는 각 축선의 지형 이점과 전투력 비율을 고려하여 최적화된 위치에 배치되었습니다.
"""
            return template
        else:
            template = f"""## COA Explanation: {coa_result.coa_name or coa_result.coa_id}

### Overview
This COA received a total score of {coa_result.total_score:.4f}.

### Scores by Evaluation Factor
- Combat Power Superiority: {coa_result.combat_power_score:.2%}
- Mobility: {coa_result.mobility_score:.2%}
- Constraint Compliance: {coa_result.constraint_compliance_score:.2%}
- Threat Response: {coa_result.threat_response_score:.2%}
- Risk: {coa_result.risk_score:.2%}

### Summary
{coa_result.summary or "Evaluation completed."}
"""
            return template


class DoctrineSearchService:
    """교범/지침 검색 서비스 (RAG 기반)"""
    
    def __init__(self, rag_manager=None):
        """
        Args:
            rag_manager: RAGManager 인스턴스 (선택적)
        """
        self.rag_manager = rag_manager
    
    def search_doctrine_references(
        self,
        query: str,
        top_k: int = 5,
        coa_context: Optional['COA'] = None
    ) -> List[Dict]:
        """
        RAG 기반 교범/지침 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 k개 결과
            coa_context: COA 컨텍스트 (있는 경우 쿼리 보강)
            
        Returns:
            검색 결과 리스트 [{"text": str, "score": float, "source": str, ...}]
        """
        if not self.rag_manager or not self.rag_manager.is_available():
            return []
        
        # COA 컨텍스트가 있으면 쿼리 보강
        enhanced_query = query
        if coa_context:
            coa_info = f"COA: {coa_context.coa_name or coa_context.coa_id}, "
            coa_info += f"설명: {coa_context.description or 'N/A'}"
            enhanced_query = f"{query} {coa_info}"
        
        try:
            results = self.rag_manager.retrieve_with_context(enhanced_query, top_k=top_k)
            
            # 결과에 메타데이터 추가
            for result in results:
                # 기존 source가 없으면 'doctrine'으로 설정
                if 'source' not in result and 'metadata' in result:
                    result['source'] = result['metadata'].get('source', 'doctrine')
                elif 'source' not in result:
                    result['source'] = 'doctrine'
                
                result['type'] = 'reference'  # 참고 자료 타입
                
                # metadata의 주요 필드를 상위 레벨로 복사 (접근 편의성)
                if 'metadata' in result:
                    for key in ['doctrine_id', 'statement_id', 'mett_c_elements', 'excerpt']:
                        if key in result['metadata'] and key not in result:
                            result[key] = result['metadata'][key]
            
            return results
        except Exception as e:
            print(f"[WARN] 교범 검색 실패: {e}")
            return []
    
    def search_similar_operations(
        self,
        coa: 'COA',
        axis_states: List,
        top_k: int = 3
    ) -> List[Dict]:
        """
        유사 작전 사례 검색
        
        Args:
            coa: COA 객체
            axis_states: 축선별 전장상태 리스트
            top_k: 반환할 상위 k개 결과
            
        Returns:
            유사 사례 리스트
        """
        if not self.rag_manager or not self.rag_manager.is_available():
            return []
        
        # 위협상황 요약
        threat_summary = []
        for axis in axis_states:
            if axis.threat_events:
                threat_types = [t.threat_type_code for t in axis.threat_events if t.threat_type_code]
                if threat_types:
                    threat_summary.append(f"{axis.axis_name}: {', '.join(set(threat_types))}")
        
        query = f"유사 작전 사례: {coa.coa_name or coa.coa_id}. "
        query += f"위협상황: {'; '.join(threat_summary) if threat_summary else 'N/A'}"
        
        try:
            results = self.rag_manager.retrieve_with_context(query, top_k=top_k)
            
            # 결과에 메타데이터 추가
            for result in results:
                result['source'] = 'historical_case'  # 과거 사례 표시
                result['type'] = 'case_study'  # 사례 연구 타입
            
            return results
        except Exception as e:
            print(f"[WARN] 유사 작전 사례 검색 실패: {e}")
            return []

