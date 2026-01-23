
import pandas as pd
from pathlib import Path

def fill_terrain_cells():
    file_path = Path("data_lake/지형셀.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    
    descriptions = {
        "TERR001": "방어 및 관측에 유리한 고지군",
        "TERR002": "기동 및 병력 전개가 용이한 평탄한 계곡",
        "TERR003": "전략적 가치가 높은 주요 능선 감제고지",
        "TERR004": "소규모 민간인 거주 지역 및 엄폐 공간",
        "TERR005": "기동로 확보를 위한 핵심 교통 통제 지점",
        "TERR006": "측후방 경계 및 화력 지원에 적합한 거점",
        "TERR007": "관측 및 화력 노출 위험이 높은 평야 지대",
        "TERR008": "도하 및 수변 작전 시 기동 제약이 있는 연약 지반",
        "TERR009": "신속한 증원 및 군수 지원이 가능한 주요 간선 도로",
        "TERR010": "전방 감시 및 방어 태세 구축의 중심지"
    }
    
    def fill_desc(row):
        if pd.isna(row['설명']):
            return descriptions.get(row['지형셀ID'], row['설명'])
        return row['설명']
        
    df['설명'] = df.apply(fill_desc, axis=1)
    
    try:
        df.to_excel(file_path, index=False)
        print(f"Successfully filled missing values in {file_path}")
    except Exception as e:
        print(f"Error saving to Excel: {e}")

if __name__ == "__main__":
    fill_terrain_cells()
