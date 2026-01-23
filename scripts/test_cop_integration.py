#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COP 시각화 통합 테스트 스크립트
실제 데이터를 사용하여 전체 파이프라인 테스트
"""

import sys
from pathlib import Path
import json
import pandas as pd

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.coa_service import COAService
from core_pipeline.visualization_generator import VisualizationDataGenerator
import yaml

def load_test_data():
    """테스트용 실제 데이터 로드"""
    data_lake_path = project_root / "data_lake"
    
    # 위협상황 데이터 로드
    threat_file = data_lake_path / "위협상황.xlsx"
    threats_df = None
    if threat_file.exists():
        threats_df = pd.read_excel(threat_file)
    
    # 임무정보 데이터 로드
    mission_file = data_lake_path / "임무정보.xlsx"
    missions_df = None
    if mission_file.exists():
        missions_df = pd.read_excel(mission_file)
    
    # 아군부대현황 데이터 로드
    friendly_units_file = data_lake_path / "아군부대현황.xlsx"
    friendly_units_df = None
    if friendly_units_file.exists():
        friendly_units_df = pd.read_excel(friendly_units_file)
    
    return {
        "threats": threats_df,
        "missions": missions_df,
        "friendly_units": friendly_units_df
    }

def test_coa_generation_with_visualization():
    """COA 생성 및 시각화 데이터 통합 테스트"""
    print("=" * 60)
    print("통합 테스트: COA 생성 및 시각화 데이터")
    print("=" * 60)
    
    try:
        # COA Service 초기화
        config_path = project_root / "config" / "global.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        service = COAService(config)
        
        # 테스트 데이터 로드
        test_data = load_test_data()
        
        # 실제 위협 또는 임무 선택
        threat_id = None
        mission_id = None
        
        if test_data["threats"] is not None and not test_data["threats"].empty:
            # 첫 번째 위협 사용
            first_threat = test_data["threats"].iloc[0]
            threat_id = first_threat.get("위협ID")
            print(f"\n테스트 위협: {threat_id}")
            print(f"  위협유형코드: {first_threat.get('위협유형코드', 'N/A')}")
            print(f"  위협수준: {first_threat.get('위협수준', 'N/A')}")
            print(f"  발생위치셀ID: {first_threat.get('발생위치셀ID', 'N/A')}")
            print(f"  관련축선ID: {first_threat.get('관련축선ID', 'N/A')}")
        
        if test_data["missions"] is not None and not test_data["missions"].empty:
            # 첫 번째 임무 사용
            first_mission = test_data["missions"].iloc[0]
            mission_id = first_mission.get("임무ID")
            print(f"\n테스트 임무: {mission_id}")
            print(f"  임무명: {first_mission.get('임무명', 'N/A')}")
            print(f"  주공축선ID: {first_mission.get('주공축선ID', 'N/A')}")
        
        # COA 생성
        print(f"\nCOA 생성 중...")
        result = service.generate_coas_unified(
            mission_id=mission_id,
            threat_id=threat_id,
            user_params={"max_coas": 3}
        )
        
        if "error" in result:
            print(f"  ❌ COA 생성 실패: {result['error']}")
            return False
        
        top_coas = result.get("top_coas", [])
        axis_states = result.get("axis_states", [])
        
        print(f"  ✅ COA 생성 성공: {len(top_coas)}개 방책")
        print(f"  ✅ 축선 상태: {len(axis_states)}개")
        
        # 시각화 데이터 생성기 초기화
        viz_generator = VisualizationDataGenerator()
        
        # 위협 위치 추출
        threat_position = None
        main_axis_id = None
        if threat_id and test_data["threats"] is not None:
            threat_row = test_data["threats"][test_data["threats"]["위협ID"] == threat_id]
            if not threat_row.empty:
                location_cell_id = threat_row.iloc[0].get("발생위치셀ID")
                if location_cell_id:
                    threat_position = viz_generator._get_terrain_cell_coordinates(str(location_cell_id))
                main_axis_id = threat_row.iloc[0].get("관련축선ID")
        
        # 각 COA에 대해 시각화 데이터 생성 및 검증
        print(f"\n시각화 데이터 생성 및 검증:")
        print("-" * 60)
        
        for idx, coa_eval in enumerate(top_coas):
            coa_id = coa_eval.coa_id
            coa_name = coa_eval.coa_name or coa_id
            print(f"\n[방책 {idx + 1}] {coa_name} ({coa_id})")
            
            # COA 요약 정보
            summary = service.get_coa_summary(coa_eval)
            
            # 참여 부대 정보 추출
            coa_obj = coa_eval.coa if hasattr(coa_eval, 'coa') else None
            friendly_units = []
            
            if coa_obj and hasattr(coa_obj, 'unit_assignments') and coa_obj.unit_assignments:
                for unit_id, assignment in coa_obj.unit_assignments.items():
                    unit_info = {"unit_id": unit_id}
                    try:
                        if test_data["friendly_units"] is not None:
                            unit_row = test_data["friendly_units"][test_data["friendly_units"]["아군부대ID"] == unit_id]
                            if not unit_row.empty:
                                unit_info.update({
                                    "부대명": unit_row.iloc[0].get('부대명', ''),
                                    "제대": unit_row.iloc[0].get('제대', ''),
                                    "병종": unit_row.iloc[0].get('병종', ''),
                                    "배치지형셀ID": unit_row.iloc[0].get('배치지형셀ID', ''),
                                    "배치축선ID": assignment.axis_id if hasattr(assignment, 'axis_id') else unit_row.iloc[0].get('배치축선ID', ''),
                                    "좌표정보": unit_row.iloc[0].get('좌표정보', ''),
                                })
                                friendly_units.append(unit_info)
                    except Exception as e:
                        print(f"    ⚠️  부대 정보 조회 실패 ({unit_id}): {e}")
            
            print(f"  참여 부대: {len(friendly_units)}개")
            for unit in friendly_units:
                unit_name = unit.get("부대명", unit.get("unit_id", "Unknown"))
                print(f"    - {unit_name}")
            
            # 작전 경로 생성
            operational_path = viz_generator.generate_operational_path(
                coa=summary,
                friendly_units=friendly_units,
                threat_position=threat_position,
                main_axis_id=main_axis_id
            )
            
            if operational_path:
                print(f"  ✅ 작전 경로: {len(operational_path.get('waypoints', []))}개 waypoints")
                print(f"    경로 타입: {operational_path.get('path_type', 'N/A')}")
            else:
                print(f"  ⚠️  작전 경로 생성 실패 (부대 위치 또는 위협 위치 부족)")
            
            # 작전 영역 생성
            operational_area = viz_generator.generate_operational_area(
                friendly_units=friendly_units,
                threat_position=threat_position
            )
            
            if operational_area:
                if "deployment_area" in operational_area:
                    print(f"  ✅ 배치 영역: {len(operational_area['deployment_area'].get('polygon', []))}개 좌표")
                if "engagement_area" in operational_area:
                    print(f"  ✅ 교전 영역: {len(operational_area['engagement_area'].get('polygon', []))}개 좌표")
            else:
                print(f"  ⚠️  작전 영역 생성 실패")
        
        # 축선 좌표 검증
        print(f"\n축선 좌표 검증:")
        print("-" * 60)
        enriched_axis_states = viz_generator.enrich_axis_states_with_coordinates(axis_states)
        
        for axis_state in enriched_axis_states:
            axis_id = axis_state.get('axis_id', 'Unknown')
            axis_name = axis_state.get('axis_name', axis_id)
            
            if 'coordinates' in axis_state and axis_state['coordinates']:
                coord_count = len(axis_state['coordinates'])
                print(f"  ✅ {axis_name} ({axis_id}): {coord_count}개 좌표")
            else:
                print(f"  ⚠️  {axis_name} ({axis_id}): 좌표 없음")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_threat_visualization_data():
    """위협 시각화 데이터 검증"""
    print("\n" + "=" * 60)
    print("위협 시각화 데이터 검증")
    print("=" * 60)
    
    test_data = load_test_data()
    viz_generator = VisualizationDataGenerator()
    
    if test_data["threats"] is None or test_data["threats"].empty:
        print("  ⚠️  위협상황 데이터 없음")
        return
    
    # 첫 3개 위협 테스트
    test_threats = test_data["threats"].head(3)
    
    for idx, threat_row in test_threats.iterrows():
        threat_id = threat_row.get("위협ID")
        threat_type_code = threat_row.get("위협유형코드", "")
        threat_level_str = threat_row.get("위협수준", "0.5")
        location_cell_id = threat_row.get("발생위치셀ID")
        
        print(f"\n위협 {threat_id}:")
        print(f"  위협유형코드: {threat_type_code}")
        print(f"  위협수준: {threat_level_str} (타입: {type(threat_level_str).__name__})")
        
        # 위협 수준 파싱
        try:
            if isinstance(threat_level_str, str):
                threat_level = float(threat_level_str) if threat_level_str.replace('.', '').isdigit() else 0.5
            else:
                threat_level = float(threat_level_str) if threat_level_str else 0.5
        except:
            threat_level = 0.5
        
        # 위치 해결
        position = None
        if location_cell_id:
            position = viz_generator._get_terrain_cell_coordinates(str(location_cell_id))
        
        if position:
            print(f"  ✅ 위치: {position}")
            
            # 영향 범위 계산 (Python에서 직접 계산)
            base_radius = 5.0
            level_multiplier = 1.0 + threat_level
            threat_type_radius = {
                '미사일': 10.0, 'MISSILE': 10.0,
                '포병': 8.0, 'ARTILLERY': 8.0,
                '기갑': 5.0, 'ARMOR': 5.0,
                '보병': 3.0, 'INFANTRY': 3.0,
            }
            type_bonus = threat_type_radius.get(threat_type_code, 0.0)
            radius = base_radius * level_multiplier + type_bonus
            radius = min(radius, 50.0)
            
            print(f"  ✅ 영향 범위 반경: {radius:.2f} km")
        else:
            print(f"  ⚠️  위치 해결 실패")

def test_friendly_unit_visualization():
    """아군 부대 시각화 데이터 검증"""
    print("\n" + "=" * 60)
    print("아군 부대 시각화 데이터 검증")
    print("=" * 60)
    
    test_data = load_test_data()
    viz_generator = VisualizationDataGenerator()
    
    if test_data["friendly_units"] is None or test_data["friendly_units"].empty:
        print("  ⚠️  아군부대현황 데이터 없음")
        return
    
    # 첫 5개 부대 테스트
    test_units = test_data["friendly_units"].head(5)
    
    for idx, unit_row in test_units.iterrows():
        unit_id = unit_row.get("아군부대ID")
        unit_name = unit_row.get("부대명", unit_id)
        제대 = unit_row.get("제대", "")
        병종 = unit_row.get("병종", "")
        
        print(f"\n부대 {unit_name} ({unit_id}):")
        print(f"  제대: {제대}, 병종: {병종}")
        
        # 위치 해결
        position = None
        coord_str = unit_row.get("좌표정보")
        if coord_str:
            try:
                parts = str(coord_str).strip().split(',')
                if len(parts) == 2:
                    position = [float(parts[0].strip()), float(parts[1].strip())]
            except:
                pass
        
        if not position:
            cell_id = unit_row.get("배치지형셀ID")
            if cell_id:
                position = viz_generator._get_terrain_cell_coordinates(str(cell_id))
        
        if position:
            print(f"  ✅ 위치: {position}")
        else:
            print(f"  ⚠️  위치 해결 실패")
        
        # MIL-STD-2525D 심볼 결정 (간단한 매핑)
        sidc_mapping = {
            ('보병',): 'SFGPUCI----K---',
            ('기갑', '기계화'): 'SFGPUCA----K---',
            ('포병',): 'SFGPUCF----K---',
        }
        # 실제로는 더 정교한 매핑 필요
        print(f"  SIDC 결정 필요: 제대={제대}, 병종={병종}")

def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("COP 시각화 통합 테스트")
    print("=" * 60 + "\n")
    
    results = {
        "coa_generation": False,
        "threat_visualization": False,
        "friendly_unit_visualization": False
    }
    
    # 1. COA 생성 및 시각화 데이터 통합 테스트
    try:
        results["coa_generation"] = test_coa_generation_with_visualization()
    except Exception as e:
        print(f"\n❌ COA 생성 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. 위협 시각화 데이터 검증
    try:
        test_threat_visualization_data()
        results["threat_visualization"] = True
    except Exception as e:
        print(f"\n❌ 위협 시각화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. 아군 부대 시각화 데이터 검증
    try:
        test_friendly_unit_visualization()
        results["friendly_unit_visualization"] = True
    except Exception as e:
        print(f"\n❌ 아군 부대 시각화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"COA 생성 및 시각화: {'✅ 성공' if results['coa_generation'] else '❌ 실패'}")
    print(f"위협 시각화 데이터: {'✅ 성공' if results['threat_visualization'] else '❌ 실패'}")
    print(f"아군 부대 시각화: {'✅ 성공' if results['friendly_unit_visualization'] else '❌ 실패'}")
    
    all_passed = all(results.values())
    print(f"\n전체 결과: {'✅ 모든 테스트 통과' if all_passed else '⚠️  일부 테스트 실패'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
