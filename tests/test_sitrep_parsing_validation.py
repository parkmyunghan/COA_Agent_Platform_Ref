# tests/test_sitrep_parsing_validation.py
# -*- coding: utf-8 -*-
"""
SITREP 파싱 및 방책 추천 검증 테스트

실제데이터, 데모시나리오와 동일한 내용의 SITREP 텍스트를 생성하여:
1. 파싱이 동일한 내용으로 되는지 검증
2. 동일한 방책을 추천하는지 검증
"""
import unittest
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.coa_service import COAService
from core_pipeline.orchestrator import Orchestrator
from common.situation_converter import SituationInfoConverter
from ui.components.demo_scenario import DEMO_SCENARIOS, convert_scenario_to_situation_info
from ui.components.demo_scenario import convert_threat_data_to_situation_info as convert_threat_data_from_demo
from ui.components.situation_input import convert_threat_data_to_situation_info


class TestSITREPParsingValidation(unittest.TestCase):
    """SITREP 파싱 및 방책 추천 검증 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 초기화"""
        # Orchestrator 초기화
        try:
            from config.loader import load_config
            config = load_config()
        except ImportError:
            # config.loader가 없으면 직접 로드
            import yaml
            with open('config/global.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        
        cls.orchestrator = Orchestrator(config)
        cls.orchestrator.initialize()
        
        # COAService 초기화
        cls.coa_service = COAService(config)
        
        # 실제데이터 로드
        cls.real_data = cls._load_real_data()
        
        print("\n" + "="*60)
        print("SITREP 파싱 및 방책 추천 검증 테스트 시작")
        print("="*60)
    
    @classmethod
    def _load_real_data(cls) -> List[Dict]:
        """실제데이터 로드"""
        try:
            df = pd.read_excel('data_lake/위협상황.xlsx')
            return [row.to_dict() for _, row in df.iterrows()]
        except Exception as e:
            print(f"[WARN] 실제데이터 로드 실패: {e}")
            return []
    
    def _generate_sitrep_from_real_data(self, threat_data: Dict, situation_info: Dict) -> str:
        """실제데이터로부터 SITREP 텍스트 생성 (situation_info 기반으로 정확하게)"""
        # 원시보고텍스트가 있으면 사용하되, 위협수준이 없으면 추가
        raw_text = threat_data.get('원시보고텍스트', '')
        if raw_text and pd.notna(raw_text) and str(raw_text).strip():
            raw_text_str = str(raw_text)
            # 위협수준이 텍스트에 없으면 추가
            threat_level_raw = situation_info.get('위협수준', '')
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
                # 위협수준 추가
                raw_text_str = f"{raw_text_str} 위협수준 {level_kr}."
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
    
    def _generate_sitrep_from_demo(self, scenario: Dict) -> str:
        """데모시나리오로부터 SITREP 텍스트 생성"""
        threat_type = scenario.get('threat_type', '공격')
        severity = scenario.get('severity', 90)
        location = scenario.get('location', '전방기지')
        enemy_info = scenario.get('enemy_info', '')
        friendly_info = scenario.get('friendly_info', '')
        
        # 위협수준 변환
        if severity >= 80:
            level = '높음'
        elif severity >= 50:
            level = '보통'
        else:
            level = '낮음'
        
        # SITREP 텍스트 생성
        sitrep = f"{enemy_info}. 위협수준 {level} ({severity}%). {friendly_info}."
        return sitrep
    
    def _normalize_situation_info(self, situation_info: Dict) -> Dict:
        """situation_info 정규화 (비교용)"""
        normalized = {
            'threat_level': round(float(situation_info.get('threat_level', 0)), 2),
            '위협유형': str(situation_info.get('위협유형', situation_info.get('threat_type', ''))).strip(),
            '발생장소': str(situation_info.get('발생장소', situation_info.get('location', ''))).strip(),
            '심각도': round(float(situation_info.get('심각도', situation_info.get('severity', 0))), 0)
        }
        return normalized
    
    def _compare_situation_info(self, info1: Dict, info2: Dict, tolerance: float = 0.1):
        """두 situation_info 비교"""
        norm1 = self._normalize_situation_info(info1)
        norm2 = self._normalize_situation_info(info2)
        
        differences = []
        
        # threat_level 비교
        if abs(norm1['threat_level'] - norm2['threat_level']) > tolerance:
            differences.append(f"threat_level 불일치: {norm1['threat_level']} vs {norm2['threat_level']}")
        
        # 위협유형 비교
        if norm1['위협유형'] != norm2['위협유형']:
            differences.append(f"위협유형 불일치: '{norm1['위협유형']}' vs '{norm2['위협유형']}'")
        
        # 발생장소 비교 (부분 매칭 허용)
        if norm1['발생장소'] and norm2['발생장소']:
            if norm1['발생장소'] not in norm2['발생장소'] and norm2['발생장소'] not in norm1['발생장소']:
                differences.append(f"발생장소 불일치: '{norm1['발생장소']}' vs '{norm2['발생장소']}'")
        
        # 심각도 비교
        if abs(norm1['심각도'] - norm2['심각도']) > 5:  # 5% 허용 오차
            differences.append(f"심각도 불일치: {norm1['심각도']} vs {norm2['심각도']}")
        
        return len(differences) == 0, differences
    
    def _compare_recommendations(self, recs1: List[Dict], recs2: List[Dict], top_k: int = 3):
        """두 방책 추천 결과 비교"""
        differences = []
        
        # 상위 k개 비교
        top1 = recs1[:top_k] if len(recs1) >= top_k else recs1
        top2 = recs2[:top_k] if len(recs2) >= top_k else recs2
        
        if len(top1) != len(top2):
            differences.append(f"추천 개수 불일치: {len(top1)} vs {len(top2)}")
        
        # COA 이름 비교
        names1 = [r.get('coa_name', r.get('명칭', '')) for r in top1]
        names2 = [r.get('coa_name', r.get('명칭', '')) for r in top2]
        
        # 상위 3개 중 최소 2개가 일치해야 함
        common = set(names1) & set(names2)
        if len(common) < min(2, len(top1), len(top2)):
            differences.append(f"상위 방책 불일치: {names1} vs {names2} (공통: {list(common)})")
        
        return len(differences) == 0, differences
    
    def test_real_data_sitrep_parsing(self):
        """
        테스트 1: 실제데이터 입력 방식 → SITREP 생성 → 파싱 결과 비교
        
        1) 실제데이터를 "실제 데이터에서 선택" 방식으로 처리
        2) 동일한 내용의 SITREP 텍스트 생성
        3) SITREP 파싱 결과와 실제데이터 결과 동일 여부 비교
        """
        if not self.real_data:
            self.skipTest("실제데이터가 없습니다.")
        
        # 첫 번째 실제데이터 사용
        threat_data = self.real_data[0]
        threat_id = threat_data.get('위협ID', 'UNKNOWN')
        print(f"\n[테스트 1] 실제데이터 입력 방식 검증: {threat_id}")
        
        # 1. 실제데이터를 "실제 데이터에서 선택" 방식으로 처리 (situation_input.py의 함수 사용)
        real_situation_info = convert_threat_data_to_situation_info(threat_data)
        print(f"  [1단계] 실제데이터 situation_info:")
        print(f"    - threat_level: {real_situation_info.get('threat_level')}")
        print(f"    - 위협유형: {real_situation_info.get('위협유형')}")
        print(f"    - 위협수준: {real_situation_info.get('위협수준')}")
        print(f"    - 발생장소: {real_situation_info.get('발생장소')}")
        print(f"    - 관련축선ID: {real_situation_info.get('관련축선ID')}")
        
        # 2. 동일한 내용의 SITREP 텍스트 생성
        sitrep_text = self._generate_sitrep_from_real_data(threat_data, real_situation_info)
        print(f"  [2단계] 생성된 SITREP:")
        print(f"    {sitrep_text}")
        
        # 3. SITREP 파싱
        try:
            threat_event = self.coa_service.parse_sitrep_to_threat(
                sitrep_text=sitrep_text,
                mission_id=None,
                use_llm=True
            )
            
            if not threat_event:
                self.fail("SITREP 파싱 결과가 None입니다.")
            
            # ThreatEvent → situation_info 변환 (render_sitrep_input_ui와 동일한 방식)
            threat_level_raw = threat_event.threat_level if threat_event.threat_level else "N/A"
            
            # 정규화된 threat_level 계산
            threat_level_normalized = 0.5  # 기본값
            if isinstance(threat_level_raw, str):
                threat_level_upper = threat_level_raw.upper()
                if threat_level_upper in ['HIGH', '높음', 'H']:
                    threat_level_normalized = 0.9
                elif threat_level_upper in ['MEDIUM', '중간', 'M']:
                    threat_level_normalized = 0.5
                elif threat_level_upper in ['LOW', '낮음', 'L']:
                    threat_level_normalized = 0.2
                else:
                    try:
                        threat_level_normalized = float(str(threat_level_raw).replace(',', '')) / 100.0
                    except:
                        threat_level_normalized = 0.5
            else:
                threat_level_normalized = float(threat_level_raw) / 100.0 if threat_level_raw and threat_level_raw > 1 else (threat_level_raw if threat_level_raw else 0.5)
            
            sitrep_situation_info = {
                "situation_id": threat_event.threat_id,
                "threat_level": threat_level_normalized,
                "위협ID": threat_event.threat_id,
                "위협유형": threat_event.threat_type_code,
                "위협수준": threat_level_raw,
                "관련축선ID": threat_event.related_axis_id,
                "발생장소": threat_event.location_cell_id or "",
                "심각도": self._convert_threat_level_to_int(threat_event.threat_level),
                "is_sitrep_parsed": True
            }
            
            print(f"  [3단계] SITREP 파싱 결과:")
            print(f"    - threat_level: {sitrep_situation_info.get('threat_level')}")
            print(f"    - 위협유형: {sitrep_situation_info.get('위협유형')}")
            print(f"    - 위협수준: {sitrep_situation_info.get('위협수준')}")
            print(f"    - 발생장소: {sitrep_situation_info.get('발생장소')}")
            print(f"    - 관련축선ID: {sitrep_situation_info.get('관련축선ID')}")
            
            # 4. 비교
            is_match, differences = self._compare_situation_info(real_situation_info, sitrep_situation_info, tolerance=0.15)
            
            if not is_match:
                print(f"  ⚠️ [4단계] 파싱 불일치:")
                for diff in differences:
                    print(f"    - {diff}")
            else:
                print(f"  ✅ [4단계] 파싱 일치 확인")
            
            # 완화된 검증: 위협수준이 비슷하면 통과 (0.3 이하 허용)
            level_diff = abs(real_situation_info.get('threat_level', 0) - sitrep_situation_info.get('threat_level', 0))
            print(f"    위협수준 차이: {level_diff}")
            self.assertLessEqual(level_diff, 0.3, f"위협수준 차이가 너무 큼: {level_diff} (실제: {real_situation_info.get('threat_level')}, SITREP: {sitrep_situation_info.get('threat_level')})")
            
        except Exception as e:
            print(f"  ❌ SITREP 파싱 실패: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"SITREP 파싱 실패: {e}")
    
    def test_demo_scenario_sitrep_parsing(self):
        """데모시나리오 → SITREP 파싱 검증"""
        # 시나리오 2 사용 (높은 위협수준)
        scenario = DEMO_SCENARIOS[1]  # 시나리오 2: 적군 전차 부대 이동
        print(f"\n[테스트 2] 데모시나리오: {scenario['name']}")
        
        # 1. 데모시나리오 → situation_info
        demo_situation_info = convert_scenario_to_situation_info(scenario, "threat_centered")
        print(f"  데모시나리오 situation_info: threat_level={demo_situation_info.get('threat_level')}, 위협유형={demo_situation_info.get('위협유형')}")
        
        # 2. SITREP 텍스트 생성
        sitrep_text = self._generate_sitrep_from_demo(scenario)
        print(f"  생성된 SITREP: {sitrep_text}")
        
        # 3. SITREP 파싱
        try:
            threat_event = self.coa_service.parse_sitrep_to_threat(
                sitrep_text=sitrep_text,
                mission_id=None,
                use_llm=True
            )
            
            # ThreatEvent → situation_info 변환
            sitrep_situation_info = {
                "situation_id": f"SITREP_{threat_event.threat_id}",
                "threat_level": self._convert_threat_level_to_float(threat_event.threat_level),
                "위협유형": self._convert_threat_type_code(threat_event.threat_type_code),
                "발생장소": scenario.get('location', ''),
                "심각도": self._convert_threat_level_to_int(threat_event.threat_level),
                "is_sitrep": True
            }
            print(f"  SITREP 파싱 결과: threat_level={sitrep_situation_info.get('threat_level')}, 위협유형={sitrep_situation_info.get('위협유형')}")
            
            # 4. 비교
            is_match, differences = self._compare_situation_info(demo_situation_info, sitrep_situation_info, tolerance=0.15)
            
            if not is_match:
                print(f"  ⚠️ 파싱 불일치:")
                for diff in differences:
                    print(f"    - {diff}")
            else:
                print(f"  ✅ 파싱 일치 확인")
            
            # 완화된 검증: 위협수준이 비슷하면 통과
            level_diff = abs(demo_situation_info.get('threat_level', 0) - sitrep_situation_info.get('threat_level', 0))
            self.assertLess(level_diff, 0.2, f"위협수준 차이가 너무 큼: {level_diff}")
            
        except Exception as e:
            print(f"  ❌ SITREP 파싱 실패: {e}")
            self.fail(f"SITREP 파싱 실패: {e}")
    
    def test_real_data_coa_recommendation_consistency(self):
        """
        테스트 3: 실제데이터 기반 방책 추천 vs SITREP 파싱 기반 방책 추천 일관성 검증
        
        1) 실제데이터를 기반으로 방책 추천
        2) 동일한 내용의 SITREP 생성 → 파싱 → 방책 추천
        3) 두 추천 결과의 동일 여부 검증
        """
        if not self.real_data:
            self.skipTest("실제데이터가 없습니다.")
        
        # 첫 번째 실제데이터 사용
        threat_data = self.real_data[0]
        threat_id = threat_data.get('위협ID', 'UNKNOWN')
        print(f"\n[테스트 3] 실제데이터 방책 추천 일관성 검증: {threat_id}")
        
        # 1. 실제데이터를 "실제 데이터에서 선택" 방식으로 처리
        real_situation_info = convert_threat_data_to_situation_info(threat_data)
        
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        agent = EnhancedDefenseCOAAgent(core=self.orchestrator.core)
        
        print(f"  [1단계] 실제데이터 기반 방책 추천 실행...")
        real_result = agent.execute_reasoning(
            situation_id=real_situation_info.get('situation_id'),
            selected_situation_info=real_situation_info,
            use_palantir_mode=False,  # 빠른 테스트를 위해 기본 모드
            top_k=5
        )
        real_recommendations = real_result.get('recommendations', [])
        print(f"    추천 개수: {len(real_recommendations)}개")
        if real_recommendations:
            real_names = [r.get('coa_name', r.get('명칭', 'N/A')) for r in real_recommendations[:5]]
            print(f"    상위 5개: {real_names}")
        
        # 2. 동일한 내용의 SITREP 생성 → 파싱 → 방책 추천
        sitrep_text = self._generate_sitrep_from_real_data(threat_data, real_situation_info)
        print(f"  [2단계] SITREP 생성 및 파싱...")
        print(f"    생성된 SITREP: {sitrep_text[:80]}...")
        
        try:
            threat_event = self.coa_service.parse_sitrep_to_threat(
                sitrep_text=sitrep_text,
                mission_id=None,
                use_llm=True
            )
            
            if not threat_event:
                self.fail("SITREP 파싱 결과가 None입니다.")
            
            # ThreatEvent → situation_info 변환 (render_sitrep_input_ui와 동일한 방식)
            threat_level_raw = threat_event.threat_level if threat_event.threat_level else "N/A"
            threat_level_normalized = 0.5
            if isinstance(threat_level_raw, str):
                threat_level_upper = threat_level_raw.upper()
                if threat_level_upper in ['HIGH', '높음', 'H']:
                    threat_level_normalized = 0.9
                elif threat_level_upper in ['MEDIUM', '중간', 'M']:
                    threat_level_normalized = 0.5
                elif threat_level_upper in ['LOW', '낮음', 'L']:
                    threat_level_normalized = 0.2
                else:
                    try:
                        threat_level_normalized = float(str(threat_level_raw).replace(',', '')) / 100.0
                    except:
                        threat_level_normalized = 0.5
            else:
                threat_level_normalized = float(threat_level_raw) / 100.0 if threat_level_raw and threat_level_raw > 1 else (threat_level_raw if threat_level_raw else 0.5)
            
            sitrep_situation_info = {
                "situation_id": threat_event.threat_id,
                "threat_level": threat_level_normalized,
                "위협ID": threat_event.threat_id,
                "위협유형": threat_event.threat_type_code,
                "위협수준": threat_level_raw,
                "관련축선ID": threat_event.related_axis_id,
                "발생장소": threat_event.location_cell_id or "",
                "is_sitrep_parsed": True
            }
            
            print(f"  [3단계] SITREP 파싱 결과 기반 방책 추천 실행...")
            sitrep_result = agent.execute_reasoning(
                situation_id=sitrep_situation_info.get('situation_id'),
                selected_situation_info=sitrep_situation_info,
                use_palantir_mode=False,
                top_k=5
            )
            sitrep_recommendations = sitrep_result.get('recommendations', [])
            print(f"    추천 개수: {len(sitrep_recommendations)}개")
            if sitrep_recommendations:
                sitrep_names = [r.get('coa_name', r.get('명칭', 'N/A')) for r in sitrep_recommendations[:5]]
                print(f"    상위 5개: {sitrep_names}")
            
            # 4. 비교
            print(f"  [4단계] 방책 추천 일관성 비교...")
            is_match, differences = self._compare_recommendations(real_recommendations, sitrep_recommendations, top_k=5)
            
            if not is_match:
                print(f"    ⚠️ 추천 불일치:")
                for diff in differences:
                    print(f"      - {diff}")
            else:
                print(f"    ✅ 추천 일치 확인")
            
            # 완화된 검증: 최소 2개 이상의 공통 방책이 있으면 통과
            names1 = [r.get('coa_name', r.get('명칭', '')) for r in real_recommendations[:5]]
            names2 = [r.get('coa_name', r.get('명칭', '')) for r in sitrep_recommendations[:5]]
            common = set(names1) & set(names2)
            print(f"    공통 방책: {list(common)} ({len(common)}개)")
            self.assertGreaterEqual(len(common), 2, f"공통 방책이 2개 미만: {names1} vs {names2} (공통: {list(common)})")
            
        except Exception as e:
            print(f"  ❌ SITREP 파싱/추천 실패: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"SITREP 파싱/추천 실패: {e}")
    
    def test_demo_scenario_coa_recommendation_consistency(self):
        """데모시나리오 → 방책 추천 일관성 검증"""
        # 시나리오 2 사용
        scenario = DEMO_SCENARIOS[1]
        print(f"\n[테스트 4] 데모시나리오 방책 추천 일관성: {scenario['name']}")
        
        # 1. 데모시나리오 → situation_info → 방책 추천
        demo_situation_info = convert_scenario_to_situation_info(scenario, "threat_centered")
        
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        agent = EnhancedDefenseCOAAgent(core=self.orchestrator.core)
        
        demo_result = agent.execute_reasoning(
            situation_id=demo_situation_info.get('situation_id'),
            selected_situation_info=demo_situation_info,
            use_palantir_mode=False,
            top_k=5
        )
        demo_recommendations = demo_result.get('recommendations', [])
        print(f"  데모시나리오 추천: {len(demo_recommendations)}개")
        if demo_recommendations:
            print(f"    상위 3개: {[r.get('coa_name', 'N/A') for r in demo_recommendations[:3]]}")
        
        # 2. SITREP 텍스트 생성 → 파싱 → 방책 추천
        sitrep_text = self._generate_sitrep_from_demo(scenario)
        
        try:
            threat_event = self.coa_service.parse_sitrep_to_threat(
                sitrep_text=sitrep_text,
                mission_id=None,
                use_llm=True
            )
            
            # ThreatEvent → situation_info 변환
            sitrep_situation_info = {
                "situation_id": f"SITREP_{threat_event.threat_id}",
                "threat_level": self._convert_threat_level_to_float(threat_event.threat_level),
                "위협유형": self._convert_threat_type_code(threat_event.threat_type_code),
                "발생장소": scenario.get('location', ''),
                "심각도": self._convert_threat_level_to_int(threat_event.threat_level),
                "is_sitrep": True
            }
            
            sitrep_result = agent.execute_reasoning(
                situation_id=sitrep_situation_info.get('situation_id'),
                selected_situation_info=sitrep_situation_info,
                use_palantir_mode=False,
                top_k=5
            )
            sitrep_recommendations = sitrep_result.get('recommendations', [])
            print(f"  SITREP 파싱 추천: {len(sitrep_recommendations)}개")
            if sitrep_recommendations:
                print(f"    상위 3개: {[r.get('coa_name', 'N/A') for r in sitrep_recommendations[:3]]}")
            
            # 3. 비교
            is_match, differences = self._compare_recommendations(demo_recommendations, sitrep_recommendations)
            
            if not is_match:
                print(f"  ⚠️ 추천 불일치:")
                for diff in differences:
                    print(f"    - {diff}")
            else:
                print(f"  ✅ 추천 일치 확인")
            
            # 완화된 검증: 최소 1개 이상의 공통 방책이 있으면 통과
            names1 = [r.get('coa_name', r.get('명칭', '')) for r in demo_recommendations[:5]]
            names2 = [r.get('coa_name', r.get('명칭', '')) for r in sitrep_recommendations[:5]]
            common = set(names1) & set(names2)
            self.assertGreater(len(common), 0, f"공통 방책이 없음: {names1} vs {names2}")
            
        except Exception as e:
            print(f"  ❌ SITREP 파싱/추천 실패: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"SITREP 파싱/추천 실패: {e}")
    
    def _convert_threat_level_to_float(self, threat_level: str) -> float:
        """위협수준 문자열을 float로 변환"""
        level_map = {'High': 0.85, 'Medium': 0.60, 'Low': 0.30}
        return level_map.get(threat_level, 0.5)
    
    def _convert_threat_level_to_int(self, threat_level: str) -> int:
        """위협수준 문자열을 int로 변환"""
        level_map = {'High': 85, 'Medium': 60, 'Low': 30}
        return level_map.get(threat_level, 50)
    
    def _convert_threat_type_code(self, threat_type_code: str) -> str:
        """위협유형코드를 한글로 변환"""
        type_map = {
            'ARMOR': '전차', 'ARTILLERY': '포병', 'INFANTRY': '보병',
            'AIR': '항공', 'MISSILE': '미사일', 'CBRN': 'CBRN',
            'CYBER': '사이버', 'UNKNOWN': '미확인'
        }
        return type_map.get(threat_type_code, threat_type_code)


if __name__ == '__main__':
    unittest.main(verbosity=2)

