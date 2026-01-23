
import pandas as pd
from pathlib import Path

def inspect_coordinates():
    data_lake = Path("data_lake")
    
    # Load Terrain Cells
    df_terrain = pd.read_excel(data_lake / "지형셀.xlsx")
    print("\n=== 지형셀 좌표 샘플 ===")
    if '좌표정보' in df_terrain.columns:
        print(df_terrain[['지형셀ID', '좌표정보']].head(5))
    else:
        print("좌표정보 컬럼 없음")
        
    # Load Axis
    df_axis = pd.read_excel(data_lake / "전장축선.xlsx")
    print("\n=== 전장축선 경로 샘플 ===")
    if '주요지형셀목록' in df_axis.columns:
        print(df_axis[['축선ID', '주요지형셀목록']].head(5))

if __name__ == "__main__":
    inspect_coordinates()
