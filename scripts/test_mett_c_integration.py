# scripts/test_mett_c_integration.py
# -*- coding: utf-8 -*-
"""
METT-C 평가 통합 테스트
"""
import sys
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.mett_c_evaluator import METTCEvaluator, METTCScore
from core_pipeline.data_models import (
    Mission, EnemyUnit, TerrainCell, FriendlyUnit,
    CivilianArea, Constraint, ThreatEvent, AxisState
)
from core_pipeline.data_manager import DataManager
from core_pipeline.axis_state_builder import AxisStateBuilder

def test_mett_c_evaluation():
    """METT-C 평가 테스트"""
    print("=" * 80)
    print("METT-C 평가 통합 테스트")
    print("=" * 80)
    
    # 설정 로드
    config_path = BASE_DIR / "config" / "global.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # DataManager 초기화
    print("\n[1] 데이터 로드 중...")
    data_manager = DataManager(config)
    data = data_manager.load_all()
    
    # 샘플 데이터 생성
    print("\n[2] 샘플 데이터 생성 중...")
    
    # Mission
    mission = Mission(
        mission_id="TEST_MISSION",
        mission_type="방어",
        priority=8,
        time_limit=None
    )
    
    # Enemy Units
    enemy_units = [
        EnemyUnit(
            enemy_unit_id="ENEMY001",
            unit_name="적군 제1사단",
            combat_power=100,
            threat_level="High"
        )
    ]
    
    # Terrain Cells
    terrain_cells = [
        TerrainCell(
            terrain_cell_id="TERR001",
            terrain_name="철원 평야",
            mobility_grade=4,
            defense_advantage=3
        )
    ]
    
    # Friendly Units
    friendly_units = [
        FriendlyUnit(
            friendly_unit_id="FRIENDLY001",
            unit_name="아군 제1사단",
            combat_power=120
        )
    ]
    
    # Civilian Areas (NEW)
    civilian_areas = [
        CivilianArea(
            area_id="CIV001",
            area_name="철원읍 중심가",
            location_cell_id="TERR001",
            population_density=1200,
            protection_priority="High",
            evacuation_routes=["철원역", "철원시청"],
            critical_facilities=["철원병원", "철원초등학교"]
        )
    ]
    
    # Constraints (시간 제약 포함)
    constraints = [
        Constraint(
            constraint_id="CONST001",
            constraint_type="시간제약",
            time_critical=True,
            max_duration_hours=24.0
        )
    ]
    
    # Axis States
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
    
    # COA 컨텍스트
    print("\n[3] COA 컨텍스트 생성 중...")
    coa_context = {
        'coa_type': 'defense',
        'threat_score': 0.8,
        'resource_availability': 0.7,
        'asset_capability': 0.6,
        'environment_fit': 0.75,
        'impact_terrain_cells': ['TERR001'],
        'estimated_duration_hours': 20.0
    }
    
    # METT-C 평가기 초기화
    print("\n[4] METT-C 평가 실행 중...")
    evaluator = METTCEvaluator()
    
    score = evaluator.evaluate_coa(
        coa_context=coa_context,
        mission=mission,
        enemy_units=enemy_units,
        terrain_cells=terrain_cells,
        friendly_units=friendly_units,
        civilian_areas=civilian_areas,
        constraints=constraints,
        axis_states=axis_states
    )
    
    # 결과 출력
    print("\n[5] METT-C 평가 결과:")
    print(f"   Mission 점수: {score.mission_score:.3f}")
    print(f"   Enemy 점수: {score.enemy_score:.3f}")
    print(f"   Terrain 점수: {score.terrain_score:.3f}")
    print(f"   Troops 점수: {score.troops_score:.3f}")
    print(f"   Civilian 점수: {score.civilian_score:.3f} (NEW)")
    print(f"   Time 점수: {score.time_score:.3f} (NEW)")
    print(f"   종합 점수: {score.total_score:.3f}")
    
    # 검증
    print("\n[6] 검증 중...")
    assert isinstance(score, METTCScore), "METTCScore 객체가 아닙니다"
    assert 0.0 <= score.mission_score <= 1.0, "Mission 점수가 범위를 벗어났습니다"
    assert 0.0 <= score.enemy_score <= 1.0, "Enemy 점수가 범위를 벗어났습니다"
    assert 0.0 <= score.terrain_score <= 1.0, "Terrain 점수가 범위를 벗어났습니다"
    assert 0.0 <= score.troops_score <= 1.0, "Troops 점수가 범위를 벗어났습니다"
    assert 0.0 <= score.civilian_score <= 1.0, "Civilian 점수가 범위를 벗어났습니다"
    assert 0.0 <= score.time_score <= 1.0, "Time 점수가 범위를 벗어났습니다"
    assert 0.0 <= score.total_score <= 1.0, "종합 점수가 범위를 벗어났습니다"
    
    print("✅ 모든 점수가 유효한 범위 내에 있습니다")
    
    # 민간인 보호 점수 검증
    if score.civilian_score < 0.3:
        print(f"⚠️ 민간인 보호 점수가 낮습니다: {score.civilian_score:.3f}")
    else:
        print(f"✅ 민간인 보호 점수 양호: {score.civilian_score:.3f}")
    
    # 시간 제약 점수 검증
    if score.time_score == 0.0:
        print("❌ 시간 제약 위반 (점수 0.0)")
    elif score.time_score < 0.5:
        print(f"⚠️ 시간 제약 준수도 낮음: {score.time_score:.3f}")
    else:
        print(f"✅ 시간 제약 준수 양호: {score.time_score:.3f}")
    
    # 상세 분석 출력
    print("\n[7] 상세 분석:")
    for element, details in score.breakdown.items():
        print(f"   {element}:")
        print(f"     - 점수: {details['score']:.3f}")
        print(f"     - 가중치: {details['weight']:.3f}")
        print(f"     - 기여도: {details['contribution']:.3f}")
    
    print("\n" + "=" * 80)
    print("✅ METT-C 평가 통합 테스트 완료!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_mett_c_evaluation()
    sys.exit(0 if success else 1)



