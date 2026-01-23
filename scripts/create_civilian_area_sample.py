# scripts/create_civilian_area_sample.py
# -*- coding: utf-8 -*-
"""
민간인지역 샘플 데이터 생성 스크립트
"""
import pandas as pd
from pathlib import Path
import sys

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
DATA_LAKE = BASE_DIR / "data_lake"

def create_civilian_area_sample():
    """민간인지역 샘플 Excel 파일 생성"""
    
    # 지형셀 ID 조회 (기존 데이터 참조)
    terrain_cell_ids = []
    try:
        terrain_file = DATA_LAKE / "지형셀.xlsx"
        if terrain_file.exists():
            df_terrain = pd.read_excel(terrain_file, nrows=10)
            if '지형셀ID' in df_terrain.columns:
                terrain_cell_ids = df_terrain['지형셀ID'].tolist()[:5]
    except Exception as e:
        print(f"[WARN] 지형셀 파일 로드 실패: {e}")
    
    # 기본 지형셀 ID (폴백)
    if not terrain_cell_ids:
        terrain_cell_ids = ['TERR001', 'TERR002', 'TERR003', 'TERR004', 'TERR005']
    
    # 샘플 데이터 생성
    sample_data = [
        {
            '민간인지역ID': 'CIV001',
            '지역명': '철원읍 중심가',
            '위치지형셀ID': terrain_cell_ids[0] if len(terrain_cell_ids) > 0 else 'TERR001',
            '인구밀도': 1200,
            '보호우선순위': 'High',
            '대피경로': '철원역, 철원시청',
            '중요시설': '철원병원, 철원초등학교',
            '좌표정보': '127.3133, 38.1464',
            '비고': 'DMZ 인근 주요 거주지역'
        },
        {
            '민간인지역ID': 'CIV002',
            '지역명': '문산면 주거지',
            '위치지형셀ID': terrain_cell_ids[1] if len(terrain_cell_ids) > 1 else 'TERR002',
            '인구밀도': 800,
            '보호우선순위': 'Medium',
            '대피경로': '문산역',
            '중요시설': '문산보건소',
            '좌표정보': '126.783, 37.854',
            '비고': '주거 밀집 지역'
        },
        {
            '민간인지역ID': 'CIV003',
            '지역명': '연천군청 인근',
            '위치지형셀ID': terrain_cell_ids[2] if len(terrain_cell_ids) > 2 else 'TERR003',
            '인구밀도': 600,
            '보호우선순위': 'Medium',
            '대피경로': '연천군청, 연천역',
            '중요시설': '연천군청, 연천중학교',
            '좌표정보': '127.075, 38.096',
            '비고': '행정 중심지'
        },
        {
            '민간인지역ID': 'CIV004',
            '지역명': '화천읍 시가지',
            '위치지형셀ID': terrain_cell_ids[3] if len(terrain_cell_ids) > 3 else 'TERR004',
            '인구밀도': 500,
            '보호우선순위': 'Low',
            '대피경로': '화천역',
            '중요시설': '화천보건소',
            '좌표정보': '127.708, 38.106',
            '비고': '소규모 거주지역'
        },
        {
            '민간인지역ID': 'CIV005',
            '지역명': '양구군청 인근',
            '위치지형셀ID': terrain_cell_ids[4] if len(terrain_cell_ids) > 4 else 'TERR005',
            '인구밀도': 400,
            '보호우선순위': 'Low',
            '대피경로': '양구군청',
            '중요시설': '양구군청',
            '좌표정보': '127.990, 38.109',
            '비고': '산간 지역'
        }
    ]
    
    # DataFrame 생성
    df = pd.DataFrame(sample_data)
    
    # Excel 파일 저장
    output_file = DATA_LAKE / "민간인지역.xlsx"
    df.to_excel(output_file, index=False, sheet_name='민간인지역')
    
    print(f"[INFO] 민간인지역 샘플 데이터 생성 완료: {output_file}")
    print(f"[INFO] 생성된 레코드 수: {len(df)}")
    print(f"[INFO] 컬럼: {list(df.columns)}")
    
    return output_file

if __name__ == "__main__":
    create_civilian_area_sample()



