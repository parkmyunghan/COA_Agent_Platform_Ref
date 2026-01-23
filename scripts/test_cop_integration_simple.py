#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COP 시각화 통합 테스트 스크립트 (간소화 버전)
실제 데이터를 사용하여 시각화 데이터 생성 검증
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
# 한글 경로 문제 해결: __file__의 절대 경로 사용
script_path = Path(__file__).resolve()
base_dir = script_path.parent.parent
sys.path.insert(0, str(base_dir))

# 작업 디렉토리 변경
os.chdir(str(base_dir))

import pandas as pd
import yaml

def test_visualization_data_generation():
    """시각화 데이터 생성 통합 테스트"""
    print("=" * 70)
    print("COP 시각화 통합 테스트")
    print("=" * 70)
    
    try:
        # 1. VisualizationDataGenerator 초기화
        from core_pipeline.visualization_generator import VisualizationDataGenerator
        viz_gen = VisualizationDataGenerator()
        print("\n✅ VisualizationDataGenerator 초기화 성공")
        
        # 2. 실제 데이터 로드
        data_lake = base_dir / "data_lake"
        
        # 위협상황 데이터
        threat_file = data_lake / "위협상황.xlsx"
        if not threat_file.exists():
            print(f"❌ 위협상황.xlsx 파일을 찾을 수 없습니다: {threat_file}")
            return False
        
        threats_df = pd.read_excel(threat_file)
        print(f"✅ 위협상황 데이터 로드: {len(threats_df)}개")
        
        # 아군부대현황 데이터
        friendly_units_file = data_lake / "아군부대현황.xlsx"
        friendly_units_df = None
        if friendly_units_file.exists():
            friendly_units_df = pd.read_excel(friendly_units_file)
            print(f"✅ 아군부대현황 데이터 로드: {len(friendly_units_df)}개")
        
        # 전장축선 데이터
        axis_file = data_lake / "전장축선.xlsx"
        axis_df = None
        if axis_file.exists():
            axis_df = pd.read_excel(axis_file)
            print(f"✅ 전장축선 데이터 로드: {len(axis_df)}개")
        
        # 지형셀 데이터
        terrain_file = data_lake / "지형셀.xlsx"
        terrain_df = None
        if terrain_file.exists():
            terrain_df = pd.read_excel(terrain_file)
            print(f"✅ 지형셀 데이터 로드: {len(terrain_df)}개")
        
        # 3. 위협 시각화 데이터 검증
        print("\n" + "-" * 70)
        print("위협 시각화 데이터 검증")
        print("-" * 70)
        
        test_threats = threats_df.head(3)
        threat_results = []
        
        for idx, threat_row in test_threats.iterrows():
            threat_id = threat_row.get("위협ID", "")
            threat_type_code = threat_row.get("위협유형코드", "")
            threat_level = threat_row.get("위협수준", "0.5")
            location_cell_id = threat_row.get("발생위치셀ID", "")
            related_axis_id = threat_row.get("관련축선ID", "")
            
            print(f"\n[위협 {threat_id}]")
            print(f"  위협유형코드: {threat_type_code}")
            print(f"  위협수준: {threat_level} (타입: {type(threat_level).__name__})")
            
            # 위협 수준 파싱
            try:
                if isinstance(threat_level, str):
                    threat_level_num = float(threat_level) if threat_level.replace('.', '').replace('-', '').isdigit() else 0.5
                else:
                    threat_level_num = float(threat_level) if threat_level else 0.5
            except:
                threat_level_num = 0.5
            
            # 위치 해결
            position = None
            if location_cell_id:
                position = viz_gen._get_terrain_cell_coordinates(str(location_cell_id))
            
            if position:
                print(f"  ✅ 위치: [{position[0]:.6f}, {position[1]:.6f}]")
                
                # 영향 범위 계산
                base_radius = 5.0
                level_multiplier = 1.0 + threat_level_num
                threat_type_radius = {
                    '미사일': 10.0, 'MISSILE': 10.0,
                    '포병': 8.0, 'ARTILLERY': 8.0,
                    '기갑': 5.0, 'ARMOR': 5.0,
                    '보병': 3.0, 'INFANTRY': 3.0,
                }
                type_bonus = threat_type_radius.get(threat_type_code, 0.0)
                radius = min(base_radius * level_multiplier + type_bonus, 50.0)
                print(f"  ✅ 영향 범위 반경: {radius:.2f} km")
                threat_results.append(True)
            else:
                print(f"  ⚠️  위치 해결 실패 (location_cell_id: {location_cell_id})")
                threat_results.append(False)
        
        # 4. 축선 좌표 해결 검증
        print("\n" + "-" * 70)
        print("축선 좌표 해결 검증")
        print("-" * 70)
        
        axis_results = []
        if axis_df is not None and not axis_df.empty:
            test_axes = axis_df.head(3)
            for idx, axis_row in test_axes.iterrows():
                axis_id = axis_row.get("축선ID", "")
                axis_name = axis_row.get("축선명", axis_id)
                
                print(f"\n[축선 {axis_id}] {axis_name}")
                coordinates, metadata = viz_gen.resolve_axis_coordinates(axis_id)
                
                if coordinates:
                    print(f"  ✅ 좌표 해결 성공: {len(coordinates)}개 waypoints")
                    print(f"  축선유형: {metadata.get('type', 'N/A')}")
                    print(f"  첫 번째 좌표: [{coordinates[0][0]:.6f}, {coordinates[0][1]:.6f}]")
                    axis_results.append(True)
                else:
                    print(f"  ⚠️  좌표 해결 실패")
                    axis_results.append(False)
        
        # 5. 아군 부대 시각화 데이터 검증
        print("\n" + "-" * 70)
        print("아군 부대 시각화 데이터 검증")
        print("-" * 70)
        
        unit_results = []
        if friendly_units_df is not None and not friendly_units_df.empty:
            test_units = friendly_units_df.head(5)
            for idx, unit_row in test_units.iterrows():
                unit_id = unit_row.get("아군부대ID", "")
                unit_name = unit_row.get("부대명", unit_id)
                제대 = unit_row.get("제대", "")
                병종 = unit_row.get("병종", "")
                
                print(f"\n[부대 {unit_name} ({unit_id})]")
                print(f"  제대: {제대}, 병종: {병종}")
                
                # 위치 해결
                position = None
                coord_str = unit_row.get("좌표정보")
                if coord_str and pd.notna(coord_str):
                    try:
                        parts = str(coord_str).strip().split(',')
                        if len(parts) == 2:
                            position = [float(parts[0].strip()), float(parts[1].strip())]
                    except:
                        pass
                
                if not position:
                    cell_id = unit_row.get("배치지형셀ID")
                    if cell_id and pd.notna(cell_id):
                        position = viz_gen._get_terrain_cell_coordinates(str(cell_id))
                
                if position:
                    print(f"  ✅ 위치: [{position[0]:.6f}, {position[1]:.6f}]")
                    unit_results.append(True)
                else:
                    print(f"  ⚠️  위치 해결 실패")
                    unit_results.append(False)
        
        # 6. 작전 경로 및 영역 생성 테스트
        print("\n" + "-" * 70)
        print("작전 경로 및 영역 생성 테스트")
        print("-" * 70)
        
        # 테스트용 COA 및 부대 데이터
        if friendly_units_df is not None and not friendly_units_df.empty and test_threats is not None:
            test_unit = friendly_units_df.iloc[0]
            test_threat = test_threats.iloc[0]
            
            # 부대 정보 구성
            friendly_units = [{
                "unit_id": test_unit.get("아군부대ID", ""),
                "부대명": test_unit.get("부대명", ""),
                "제대": test_unit.get("제대", ""),
                "병종": test_unit.get("병종", ""),
                "배치지형셀ID": test_unit.get("배치지형셀ID", ""),
                "좌표정보": test_unit.get("좌표정보", ""),
            }]
            
            # 위협 위치
            threat_position = None
            location_cell_id = test_threat.get("발생위치셀ID")
            if location_cell_id:
                threat_position = viz_gen._get_terrain_cell_coordinates(str(location_cell_id))
            
            # 주요 축선
            main_axis_id = test_threat.get("관련축선ID", "")
            
            # 작전 경로 생성
            coa = {
                "coa_name": "방어 작전",
                "coa_type": "defense"
            }
            
            operational_path = viz_gen.generate_operational_path(
                coa=coa,
                friendly_units=friendly_units,
                threat_position=threat_position,
                main_axis_id=main_axis_id if main_axis_id else None
            )
            
            if operational_path:
                print(f"  ✅ 작전 경로 생성 성공")
                print(f"    경로 타입: {operational_path.get('path_type', 'N/A')}")
                print(f"    Waypoints: {len(operational_path.get('waypoints', []))}개")
            else:
                print(f"  ⚠️  작전 경로 생성 실패")
            
            # 작전 영역 생성
            operational_area = viz_gen.generate_operational_area(
                friendly_units=friendly_units,
                threat_position=threat_position
            )
            
            if operational_area:
                print(f"  ✅ 작전 영역 생성 성공")
                if "deployment_area" in operational_area:
                    print(f"    배치 영역: {len(operational_area['deployment_area'].get('polygon', []))}개 좌표")
                if "engagement_area" in operational_area:
                    print(f"    교전 영역: {len(operational_area['engagement_area'].get('polygon', []))}개 좌표")
            else:
                print(f"  ⚠️  작전 영역 생성 실패")
        
        # 결과 요약
        print("\n" + "=" * 70)
        print("테스트 결과 요약")
        print("=" * 70)
        
        success_count = sum([
            sum(threat_results) if threat_results else 0,
            sum(axis_results) if axis_results else 0,
            sum(unit_results) if unit_results else 0,
        ])
        total_count = len(threat_results) + len(axis_results) + len(unit_results)
        
        print(f"위협 시각화: {sum(threat_results)}/{len(threat_results)} 성공")
        print(f"축선 좌표 해결: {sum(axis_results)}/{len(axis_results)} 성공")
        print(f"아군 부대 시각화: {sum(unit_results)}/{len(unit_results)} 성공")
        print(f"\n전체 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        if success_count == total_count:
            print("\n✅ 모든 테스트 통과!")
            return True
        else:
            print("\n⚠️  일부 테스트 실패 (데이터 누락 가능성)")
            return False
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_visualization_data_generation()
    sys.exit(0 if success else 1)
