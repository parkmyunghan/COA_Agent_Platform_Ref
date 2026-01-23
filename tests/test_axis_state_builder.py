# tests/test_axis_state_builder.py
# -*- coding: utf-8 -*-
"""
Axis State Builder 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from core_pipeline.data_manager import DataManager
from core_pipeline.axis_state_builder import AxisStateBuilder
from core_pipeline.threat_scoring import ThreatScorer
from core_pipeline.data_models import ThreatEvent


def create_sample_data():
    """샘플 데이터 생성 (테스트용)"""
    # 임무정보
    mission_data = pd.DataFrame([
        {
            '임무ID': 'MISSION001',
            '임무종류': '방어',
            '지휘관의도': '주요 축선 방어',
            '주요축선ID': 'AXIS001',
            '우선순위': 1
        }
    ])
    
    # 전장축선
    axis_data = pd.DataFrame([
        {
            '축선ID': 'AXIS001',
            '축선명': '주요 방어축선',
            '중요도': 1,
            '관련지형셀리스트': 'TERR001,TERR002'
        },
        {
            '축선ID': 'AXIS002',
            '축선명': '보조 축선',
            '중요도': 2,
            '관련지형셀리스트': 'TERR003'
        }
    ])
    
    # 지형셀
    terrain_data = pd.DataFrame([
        {
            '지형셀ID': 'TERR001',
            '지형명': '321고지',
            '지형유형': '산악',
            '기동성등급': 2,
            '방어유리도': 1,
            '요충지여부': 'Y'
        },
        {
            '지형셀ID': 'TERR002',
            '지형명': '평지',
            '지형유형': '평지',
            '기동성등급': 1,
            '방어유리도': 3,
            '요충지여부': 'N'
        },
        {
            '지형셀ID': 'TERR003',
            '지형명': '도시',
            '지형유형': '도시',
            '기동성등급': 3,
            '방어유리도': 2,
            '요충지여부': 'N'
        }
    ])
    
    # 아군부대현황
    friendly_data = pd.DataFrame([
        {
            '아군부대ID': 'FRU001',
            '부대명': '1사단',
            '제대': '사단',
            '병종': '기계화',
            '전투력지수': 80,
            '배치축선ID': 'AXIS001',
            '배치지형셀ID': 'TERR001',
            '가용상태': '가용',
            '할당임무ID': 'MISSION001'
        },
        {
            '아군부대ID': 'FRU002',
            '부대명': '2여단',
            '제대': '여단',
            '병종': '보병',
            '전투력지수': 60,
            '배치축선ID': 'AXIS001',
            '배치지형셀ID': 'TERR002',
            '가용상태': '가용',
            '할당임무ID': 'MISSION001'
        }
    ])
    
    # 적군부대현황
    enemy_data = pd.DataFrame([
        {
            '적군부대ID': 'ENU001',
            '부대명': '적 1사단',
            '제대': '사단',
            '병종': '기갑',
            '전투력지수': 90,
            '배치축선ID': 'AXIS001',
            '배치지형셀ID': 'TERR001',
            '위협수준': 'High'
        },
        {
            '적군부대ID': 'ENU002',
            '부대명': '적 2여단',
            '제대': '여단',
            '병종': '보병',
            '전투력지수': 70,
            '배치축선ID': 'AXIS001',
            '배치지형셀ID': 'TERR002',
            '위협수준': 'Medium'
        }
    ])
    
    # 제약조건
    constraint_data = pd.DataFrame([
        {
            '제약ID': 'CONST001',
            '적용대상': '축선',
            '적용대상ID': 'AXIS001',
            '제약유형': '시간',
            '내용': '야간 작전 제한',
            '우선순위': 2
        }
    ])
    
    # 위협상황
    threat_data = pd.DataFrame([
        {
            '위협ID': 'THREAT001',
            '발생시각': datetime.now(),
            '위협유형코드': '침투',
            '관련축선ID': 'AXIS001',
            '발생위치셀ID': 'TERR001',
            '관련_적부대ID': 'ENU001',
            '위협수준': 'High',
            '관련임무ID': 'MISSION001'
        },
        {
            '위협ID': 'THREAT002',
            '발생시각': datetime.now(),
            '위협유형코드': '기습공격',
            '관련축선ID': 'AXIS001',
            '발생위치셀ID': 'TERR002',
            '관련_적부대ID': 'ENU002',
            '위협수준': 'Medium',
            '관련임무ID': 'MISSION001'
        },
        {
            '위협ID': 'THREAT003',
            '발생시각': datetime.now(),
            '위협유형코드': '기만징후',
            '관련축선ID': 'AXIS002',
            '발생위치셀ID': 'TERR003',
            '위협수준': 'Low',
            '관련임무ID': 'MISSION001'
        }
    ])
    
    return {
        '임무정보': mission_data,
        '전장축선': axis_data,
        '지형셀': terrain_data,
        '아군부대현황': friendly_data,
        '적군부대현황': enemy_data,
        '제약조건': constraint_data,
        '위협상황': threat_data
    }


class MockDataManager:
    """테스트용 Mock DataManager"""
    
    def __init__(self, data: dict):
        self.data = data
    
    def load_all(self):
        return self.data


def test_threat_scoring():
    """위협지수 계산 테스트"""
    print("\n=== 위협지수 계산 테스트 ===")
    
    # 테스트 케이스 1: High 위협, 침투 유형
    threat1 = ThreatEvent(
        threat_id='THREAT001',
        threat_level='High',
        threat_type_code='침투'
    )
    score1 = ThreatScorer.calculate_threat_score(threat1)
    print(f"위협1 (High, 침투): {score1} (예상: 4.5 = 3 × 1.5)")
    assert abs(score1 - 4.5) < 0.01, f"Expected 4.5, got {score1}"
    
    # 테스트 케이스 2: Medium 위협, 기만징후 유형
    threat2 = ThreatEvent(
        threat_id='THREAT002',
        threat_level='Medium',
        threat_type_code='기만징후'
    )
    score2 = ThreatScorer.calculate_threat_score(threat2)
    print(f"위협2 (Medium, 기만징후): {score2} (예상: 1.6 = 2 × 0.8)")
    assert abs(score2 - 1.6) < 0.01, f"Expected 1.6, got {score2}"
    
    # 테스트 케이스 3: 축선별 위협점수 합계
    threats = [threat1, threat2]
    total_score = ThreatScorer.calculate_axis_threat_score(threats)
    print(f"축선별 위협점수 합계: {total_score} (예상: 6.1)")
    
    # 테스트 케이스 4: 위협레벨 결정
    level1 = ThreatScorer.determine_threat_level(8.0)
    print(f"위협점수 8.0 → 레벨: {level1} (예상: High)")
    assert level1 == 'High', f"Expected High, got {level1}"
    
    level2 = ThreatScorer.determine_threat_level(5.0)
    print(f"위협점수 5.0 → 레벨: {level2} (예상: Medium)")
    assert level2 == 'Medium', f"Expected Medium, got {level2}"
    
    level3 = ThreatScorer.determine_threat_level(2.0)
    print(f"위협점수 2.0 → 레벨: {level3} (예상: Low)")
    assert level3 == 'Low', f"Expected Low, got {level3}"
    
    print("✅ 위협지수 계산 테스트 통과\n")


def test_axis_state_builder():
    """축선별 전장상태 요약 객체 생성 테스트"""
    print("\n=== 축선별 전장상태 요약 객체 생성 테스트 ===")
    
    # 샘플 데이터 생성
    sample_data = create_sample_data()
    
    # Mock DataManager 생성
    mock_data_manager = MockDataManager(sample_data)
    
    # AxisStateBuilder 생성
    builder = AxisStateBuilder(mock_data_manager)
    
    # 임무ID로 축선별 상태 생성
    mission_id = 'MISSION001'
    axis_states = builder.build_axis_states(mission_id)
    
    print(f"\n임무ID: {mission_id}")
    print(f"생성된 축선 상태 수: {len(axis_states)}")
    
    for i, axis_state in enumerate(axis_states, 1):
        print(f"\n--- 축선 {i}: {axis_state.axis_name} ({axis_state.axis_id}) ---")
        print(f"  아군 전투력: {axis_state.friendly_combat_power_total} (부대 수: {axis_state.friendly_unit_count})")
        print(f"  적군 전투력: {axis_state.enemy_combat_power_total} (부대 수: {axis_state.enemy_unit_count})")
        print(f"  평균 기동성등급: {axis_state.avg_mobility_grade}")
        print(f"  평균 방어유리도: {axis_state.avg_defense_advantage}")
        print(f"  요충지 수: {axis_state.key_point_count}")
        print(f"  제약조건 수: {len(axis_state.constraints)}")
        print(f"  위협점수 합계: {axis_state.threat_score_total:.2f}")
        print(f"  위협레벨: {axis_state.threat_level}")
        print(f"  위협상황 수: {len(axis_state.threat_events)}")
        
        # 검증
        assert axis_state.axis_id is not None, "axis_id가 없습니다"
        assert axis_state.threat_level in ['High', 'Medium', 'Low'], f"잘못된 위협레벨: {axis_state.threat_level}"
    
    # 예상 결과 검증
    if axis_states:
        axis1 = next((a for a in axis_states if a.axis_id == 'AXIS001'), None)
        if axis1:
            print(f"\n✅ AXIS001 검증:")
            print(f"  - 아군 전투력: {axis1.friendly_combat_power_total} (예상: 140 = 80 + 60)")
            print(f"  - 적군 전투력: {axis1.enemy_combat_power_total} (예상: 160 = 90 + 70)")
            print(f"  - 위협레벨: {axis1.threat_level} (예상: High, 위협점수 합계 ≥ 8)")
            assert axis1.friendly_combat_power_total == 140, "아군 전투력 계산 오류"
            assert axis1.enemy_combat_power_total == 160, "적군 전투력 계산 오류"
    
    print("\n✅ 축선별 전장상태 요약 객체 생성 테스트 통과\n")


def test_integration():
    """통합 테스트 (실제 DataManager 사용)"""
    print("\n=== 통합 테스트 (실제 DataManager) ===")
    
    try:
        # 설정 로드
        import yaml
        config_path = project_root / 'config' / 'global.yaml'
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # DataManager 생성
            data_manager = DataManager(config)
            
            # AxisStateBuilder 생성
            builder = AxisStateBuilder(data_manager)
            
            # 데이터 로드 확인
            data = data_manager.load_all()
            print(f"로드된 테이블 수: {len(data)}")
            
            # 임무정보가 있으면 테스트
            if '임무정보' in data and not data['임무정보'].empty:
                mission_df = data['임무정보']
                if '임무ID' in mission_df.columns:
                    mission_id = mission_df.iloc[0]['임무ID']
                    print(f"\n테스트할 임무ID: {mission_id}")
                    
                    # 축선별 상태 생성
                    axis_states = builder.build_axis_states(mission_id)
                    print(f"생성된 축선 상태 수: {len(axis_states)}")
                    
                    for axis_state in axis_states:
                        print(f"\n축선: {axis_state.axis_name} ({axis_state.axis_id})")
                        print(f"  위협점수: {axis_state.threat_score_total:.2f}")
                        print(f"  위협레벨: {axis_state.threat_level}")
                else:
                    print("⚠️ 임무정보 테이블에 '임무ID' 컬럼이 없습니다")
            else:
                print("⚠️ 임무정보 테이블이 없거나 비어있습니다")
        else:
            print("⚠️ config/global.yaml 파일을 찾을 수 없습니다")
    
    except Exception as e:
        print(f"⚠️ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("=" * 60)
    print("Axis State Builder 테스트 시작")
    print("=" * 60)
    
    # 단위 테스트
    test_threat_scoring()
    test_axis_state_builder()
    
    # 통합 테스트 (선택적)
    test_integration()
    
    print("=" * 60)
    print("모든 테스트 완료")
    print("=" * 60)

