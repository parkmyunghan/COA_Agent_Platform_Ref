#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COP 시각화 데이터 생성 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.visualization_generator import VisualizationDataGenerator
from core_pipeline.data_manager import DataManager
import yaml
import json

def test_axis_coordinates():
    """축선 좌표 해결 테스트"""
    print("=" * 60)
    print("테스트 1: 축선 좌표 해결")
    print("=" * 60)
    
    viz_gen = VisualizationDataGenerator()
    
    # 테스트할 축선 ID 목록
    test_axis_ids = ["AXIS01", "AXIS02", "AXIS03"]
    
    for axis_id in test_axis_ids:
        print(f"\n축선 ID: {axis_id}")
        coordinates, metadata = viz_gen.resolve_axis_coordinates(axis_id)
        
        if coordinates:
            print(f"  ✅ 성공: {len(coordinates)}개 좌표")
            print(f"  축선명: {metadata.get('name', 'N/A')}")
            print(f"  축선유형: {metadata.get('type', 'N/A')}")
            print(f"  첫 번째 좌표: {coordinates[0] if coordinates else 'N/A'}")
        else:
            print(f"  ⚠️  실패: 좌표를 찾을 수 없음")
    
    print()

def test_operational_path():
    """방책 작전 경로 생성 테스트"""
    print("=" * 60)
    print("테스트 2: 방책 작전 경로 생성")
    print("=" * 60)
    
    viz_gen = VisualizationDataGenerator()
    
    # 테스트 데이터
    coa = {
        "coa_name": "방어 작전",
        "coa_type": "defense"
    }
    
    friendly_units = [
        {"unit_id": "UNIT01", "좌표정보": "127.0,37.5"},
        {"unit_id": "UNIT02", "배치지형셀ID": "CELL01"}
    ]
    
    threat_position = [127.2, 37.7]  # [lng, lat]
    main_axis_id = "AXIS01"
    
    path = viz_gen.generate_operational_path(
        coa=coa,
        friendly_units=friendly_units,
        threat_position=threat_position,
        main_axis_id=main_axis_id
    )
    
    if path:
        print(f"  ✅ 성공: 작전 경로 생성")
        print(f"  경로 타입: {path.get('path_type', 'N/A')}")
        print(f"  Waypoints 수: {len(path.get('waypoints', []))}")
        for i, wp in enumerate(path.get('waypoints', [])):
            print(f"    Waypoint {i+1}: {wp}")
    else:
        print(f"  ⚠️  실패: 경로 생성 실패")
    
    print()

def test_operational_area():
    """방책 작전 영역 생성 테스트"""
    print("=" * 60)
    print("테스트 3: 방책 작전 영역 생성")
    print("=" * 60)
    
    viz_gen = VisualizationDataGenerator()
    
    friendly_units = [
        {"unit_id": "UNIT01", "좌표정보": "127.0,37.5"},
        {"unit_id": "UNIT02", "좌표정보": "127.1,37.6"}
    ]
    
    threat_position = [127.2, 37.7]  # [lng, lat]
    
    area = viz_gen.generate_operational_area(
        friendly_units=friendly_units,
        threat_position=threat_position
    )
    
    if area:
        print(f"  ✅ 성공: 작전 영역 생성")
        if "deployment_area" in area:
            print(f"  배치 영역: {len(area['deployment_area'].get('polygon', []))}개 좌표")
        if "engagement_area" in area:
            print(f"  교전 영역: {len(area['engagement_area'].get('polygon', []))}개 좌표")
    else:
        print(f"  ⚠️  실패: 영역 생성 실패")
    
    print()

def test_terrain_cell_coordinates():
    """지형셀 좌표 조회 테스트"""
    print("=" * 60)
    print("테스트 4: 지형셀 좌표 조회")
    print("=" * 60)
    
    viz_gen = VisualizationDataGenerator()
    
    # 직접 지형셀 파일 읽기
    try:
        import pandas as pd
        terrain_file = project_root / "data_lake" / "지형셀.xlsx"
        if terrain_file.exists():
            terrain_df = pd.read_excel(terrain_file)
        
        if terrain_df is not None and not terrain_df.empty:
            test_cell_ids = terrain_df['지형셀ID'].head(5).tolist()
            
            for cell_id in test_cell_ids:
                coords = viz_gen._get_terrain_cell_coordinates(cell_id)
                if coords:
                    print(f"  ✅ {cell_id}: {coords}")
                else:
                    print(f"  ⚠️  {cell_id}: 좌표 없음")
        else:
            print("  ⚠️  지형셀 데이터를 불러올 수 없음")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    print()

def test_data_requirements():
    """시각화에 필요한 데이터 요구사항 확인"""
    print("=" * 60)
    print("테스트 5: 시각화 데이터 요구사항 확인")
    print("=" * 60)
    
    # config 로드
    try:
        config_path = project_root / "config" / "global.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        data_manager = DataManager(config)
    except Exception as e:
        print(f"  ⚠️  DataManager 초기화 실패: {e}")
        print("  대신 직접 Excel 파일 확인")
        import pandas as pd
        data_lake_path = project_root / "data_lake"
        
        requirements = {
        "전장축선": ["축선ID", "축선명", "축선유형", "주요지형셀목록", "시작지형셀ID", "종단지형셀ID"],
        "지형셀": ["지형셀ID", "좌표정보", "X좌표", "Y좌표"],
        "아군부대현황": ["아군부대ID", "부대명", "제대", "병종", "배치지형셀ID", "배치축선ID", "좌표정보", "전투력지수"],
        "위협상황": ["위협ID", "위협유형코드", "위협수준", "발생위치셀ID", "관련축선ID", "좌표정보"],
    }
    
    for table_name, required_columns in requirements.items():
        print(f"\n{table_name}:")
        try:
            if 'data_manager' in locals():
                df = data_manager.load_table(table_name)
            else:
                # 직접 Excel 파일 읽기
                excel_file = data_lake_path / f"{table_name}.xlsx"
                if excel_file.exists():
                    df = pd.read_excel(excel_file)
                else:
                    df = None
            
            if df is not None and not df.empty:
                missing = [col for col in required_columns if col not in df.columns]
                if missing:
                    print(f"  ⚠️  누락된 컬럼: {missing}")
                else:
                    print(f"  ✅ 모든 필수 컬럼 존재")
                
                # NULL 값 확인
                for col in required_columns:
                    if col in df.columns:
                        null_count = df[col].isna().sum()
                        if null_count > 0:
                            print(f"    - {col}: {null_count}개 NULL 값")
            else:
                print(f"  ❌ 테이블을 불러올 수 없음")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    
    print()

def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("COP 시각화 데이터 생성 테스트")
    print("=" * 60 + "\n")
    
    try:
        test_axis_coordinates()
        test_terrain_cell_coordinates()
        test_operational_path()
        test_operational_area()
        test_data_requirements()
        
        print("=" * 60)
        print("테스트 완료")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
