# scripts/test_coa_scorer_mett_c.py
# -*- coding: utf-8 -*-
"""
COAScorer와 METT-C 평가 통합 테스트
"""
import sys
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.coa_scorer import COAScorer
from core_pipeline.mett_c_evaluator import METTCEvaluator
from core_pipeline.data_models import (
    Mission, EnemyUnit, TerrainCell, FriendlyUnit,
    CivilianArea, Constraint, AxisState
)

def test_coa_scorer_with_mett_c():
    """COAScorer와 METT-C 평가 통합 테스트"""
    print("=" * 80)
    print("COAScorer와 METT-C 평가 통합 테스트")
    print("=" * 80)
    
    # COAScorer 초기화
    print("\n[1] COAScorer 초기화 중...")
    scorer = COAScorer()
    
    # METT-C 평가기 초기화
    print("\n[2] METT-C 평가기 초기화 중...")
    mett_c_evaluator = METTCEvaluator()
    
    # 샘플 데이터 생성
    print("\n[3] 샘플 데이터 생성 중...")
    
    mission = Mission(
        mission_id="TEST_MISSION",
        mission_type="방어",
        priority=8
    )
    
    enemy_units = [
        EnemyUnit(
            enemy_unit_id="ENEMY001",
            unit_name="적군 제1사단",
            combat_power=100,
            threat_level="High"
        )
    ]
    
    terrain_cells = [
        TerrainCell(
            terrain_cell_id="TERR001",
            terrain_name="철원 평야",
            mobility_grade=4,
            defense_advantage=3
        )
    ]
    
    friendly_units = [
        FriendlyUnit(
            friendly_unit_id="FRIENDLY001",
            unit_name="아군 제1사단",
            combat_power=120
        )
    ]
    
    civilian_areas = [
        CivilianArea(
            area_id="CIV001",
            area_name="철원읍 중심가",
            location_cell_id="TERR001",
            population_density=1200,
            protection_priority="High"
        )
    ]
    
    constraints = [
        Constraint(
            constraint_id="CONST001",
            constraint_type="시간제약",
            time_critical=True,
            max_duration_hours=24.0
        )
    ]
    
    axis_states = [
        AxisState(
            axis_id="AXIS001",
            axis_name="주요축선",
            friendly_combat_power_total=120,
            friendly_unit_count=1,
            friendly_units=friendly_units,
            enemy_combat_power_total=100,
            enemy_unit_count=1,
            enemy_units=enemy_units,
            terrain_cells=terrain_cells,
            avg_mobility_grade=4.0,
            avg_defense_advantage=3.0,
            constraints=constraints
        )
    ]
    
    # COA 컨텍스트 (기존 방식)
    print("\n[4] COA 컨텍스트 생성 중...")
    context = {
        'threat_level': 0.8,
        'defense_assets': ['tank', 'artillery'],
        'resource_availability': 0.7,
        'asset_capability': 0.6,
        'environment_fit': 0.75,
        'historical_success': 0.8,
        'coa_suitability': 0.9,
        'mission_type': '방어',
        'coa_type': 'defense',
        'threat_type': '침입',
        # METT-C 관련 정보 추가
        'mission': mission,
        'enemy_units': enemy_units,
        'terrain_cells': terrain_cells,
        'friendly_units': friendly_units,
        'civilian_areas': civilian_areas,
        'constraints': constraints,
        'axis_states': axis_states,
        'impact_terrain_cells': ['TERR001'],
        'estimated_duration_hours': 20.0
    }
    
    # 기존 점수 계산 (METT-C 없이)
    print("\n[5] 기존 점수 계산 (METT-C 없이)...")
    base_result = scorer.calculate_score(context)
    print(f"   종합 점수: {base_result['total']:.3f}")
    print(f"   위협 점수: {base_result['breakdown']['threat']:.3f}")
    print(f"   자원 점수: {base_result['breakdown']['resources']:.3f}")
    print(f"   자산 점수: {base_result['breakdown']['assets']:.3f}")
    print(f"   환경 점수: {base_result['breakdown']['environment']:.3f}")
    
    # METT-C 포함 점수 계산
    print("\n[6] METT-C 포함 점수 계산...")
    mett_c_result = scorer.calculate_score_with_mett_c(context, mett_c_evaluator=mett_c_evaluator)
    
    print(f"   종합 점수: {mett_c_result['total']:.3f}")
    
    # METT-C 점수 확인
    if 'mett_c' in mett_c_result:
        mett_c_scores = mett_c_result['mett_c']
        print("\n   METT-C 점수:")
        print(f"     - Mission: {mett_c_scores.get('mission', 0):.3f}")
        print(f"     - Enemy: {mett_c_scores.get('enemy', 0):.3f}")
        print(f"     - Terrain: {mett_c_scores.get('terrain', 0):.3f}")
        print(f"     - Troops: {mett_c_scores.get('troops', 0):.3f}")
        print(f"     - Civilian: {mett_c_scores.get('civilian', 0):.3f}")
        print(f"     - Time: {mett_c_scores.get('time', 0):.3f}")
        print(f"     - Total: {mett_c_scores.get('total', 0):.3f}")
        
        # METT-C 통합 여부 확인
        if mett_c_result.get('mett_c_integrated', False):
            print("\n   ✅ METT-C 점수가 기존 점수에 통합되었습니다")
        else:
            print("\n   ℹ️ METT-C 점수가 별도로 저장되었습니다 (통합 안 함)")
    else:
        print("   ⚠️ METT-C 점수가 없습니다")
    
    # 검증
    print("\n[7] 검증 중...")
    assert 'total' in mett_c_result, "종합 점수가 없습니다"
    assert 'breakdown' in mett_c_result, "상세 분석이 없습니다"
    assert 'mett_c' in mett_c_result, "METT-C 점수가 없습니다"
    
    print("✅ 모든 필수 필드가 포함되어 있습니다")
    
    # 민간인 보호 점수 검증
    if 'mett_c' in mett_c_result:
        civilian_score = mett_c_result['mett_c'].get('civilian', 1.0)
        if civilian_score < 0.3:
            print(f"⚠️ 민간인 보호 점수가 낮습니다: {civilian_score:.3f} (필터링 대상)")
        else:
            print(f"✅ 민간인 보호 점수 양호: {civilian_score:.3f}")
    
    # 시간 제약 점수 검증
    if 'mett_c' in mett_c_result:
        time_score = mett_c_result['mett_c'].get('time', 1.0)
        if time_score == 0.0:
            print("❌ 시간 제약 위반 (필터링 대상)")
        elif time_score < 0.5:
            print(f"⚠️ 시간 제약 준수도 낮음: {time_score:.3f}")
        else:
            print(f"✅ 시간 제약 준수 양호: {time_score:.3f}")
    
    print("\n" + "=" * 80)
    print("✅ COAScorer와 METT-C 평가 통합 테스트 완료!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_coa_scorer_with_mett_c()
    sys.exit(0 if success else 1)



