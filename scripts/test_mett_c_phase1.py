# scripts/test_mett_c_phase1.py
# -*- coding: utf-8 -*-
"""
Phase 1 구현 검증 테스트
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.data_models import CivilianArea
import pandas as pd

def test_civilian_area():
    """CivilianArea 데이터 모델 테스트"""
    print("=== Phase 1 검증 테스트 ===")
    
    # Excel 파일 로드
    excel_file = BASE_DIR / "data_lake" / "민간인지역.xlsx"
    if not excel_file.exists():
        print(f"❌ Excel 파일이 없습니다: {excel_file}")
        return False
    
    df = pd.read_excel(excel_file)
    print(f"✅ Excel 파일 로드 성공: {len(df)}개 레코드")
    
    # CivilianArea 객체 생성
    areas = []
    for _, row in df.iterrows():
        try:
            area = CivilianArea.from_row(row.to_dict())
            areas.append(area)
            print(f"  - {area.area_name} (ID: {area.area_id}, 우선순위: {area.protection_priority})")
        except Exception as e:
            print(f"❌ 객체 생성 실패: {e}")
            return False
    
    print(f"✅ CivilianArea 객체 생성 성공: {len(areas)}개")
    
    # 필드 검증
    for area in areas:
        assert area.area_id, "area_id가 없습니다"
        assert area.area_name, "area_name이 없습니다"
        if area.evacuation_routes:
            print(f"  - {area.area_name} 대피경로: {area.evacuation_routes}")
        if area.critical_facilities:
            print(f"  - {area.area_name} 중요시설: {area.critical_facilities}")
    
    print("\n✅ Phase 1 검증 완료!")
    return True

if __name__ == "__main__":
    success = test_civilian_area()
    sys.exit(0 if success else 1)



