
import pandas as pd
from pathlib import Path

def fill_resource_allocation():
    res_path = Path("data_lake/임무별_자원할당.xlsx")
    msn_path = Path("data_lake/임무정보.xlsx")
    ast_path = Path("data_lake/아군가용자산.xlsx")
    
    if not all([p.exists() for p in [res_path, msn_path, ast_path]]):
        print("Required files not found.")
        return
    
    # Load data
    df_res = pd.read_excel(res_path)
    df_msn = pd.read_excel(msn_path)
    df_ast = pd.read_excel(ast_path)
    
    # Create maps for lookup
    mission_map = df_msn.set_index('임무ID')['임무종류'].to_dict()
    asset_map = df_ast.set_index('자산ID')['자산명'].to_dict()
    
    def get_context_note(row):
        if not pd.isna(row['note']):
            return row['note']
        
        mission_type = mission_map.get(row['mission_id'], "작전")
        asset_name = asset_map.get(row['asset_id'], "부대")
        tactical_role = row['tactical_role']
        
        # Logic for generating realistic notes
        if mission_type == "방어":
            if "화력" in tactical_role:
                return f"{mission_type} 작전 시 화력 지원을 위해 {asset_name} 대기 및 화력 도발 시 즉각 대응"
            elif "예비대" in tactical_role:
                return f"주저항선 돌파 시 {asset_name} 즉각 투입을 위한 기동 준비 상태 유지"
            elif "충격군" in tactical_role:
                return f"적 기갑 세력 저지를 위해 {asset_name} 주요 길목 매복 운용"
            else:
                return f"{mission_type} 임무 성과 달성을 위해 {asset_name} {tactical_role} 임무 수행"
        
        elif mission_type == "공격":
            if "충격군" in tactical_role:
                return f"적 방어선 돌파를 위해 {asset_name} 주공 축선에 집중 운용"
            elif "화력" in tactical_role:
                return f"공격 개시 전 준비사격 및 공격 간 {asset_name} 화력 지원 지속 제공"
            elif "예비대" in tactical_role:
                return f"공격 기세 유지 및 전과 확대를 위해 {asset_name} 후방 대기"
            else:
                return f"{mission_type} 작전의 성공을 위해 {asset_name} {tactical_role} 임무 투입"
        
        elif mission_type == "지연":
            return f"적 기동 지연을 위해 {asset_name} 단계적 진지 변환 및 저지 활동 수행"
        
        elif mission_type == "기만":
            return f"적의 오판을 유도하기 위해 {asset_name} 허위 진지 구축 및 위력 수색 실시"
            
        return f"{mission_type} 임무와 연계하여 {asset_name} {tactical_role} 역할 수행"

    # Fill nulls
    df_res['note'] = df_res.apply(get_context_note, axis=1)
    
    # Save back to Excel
    try:
        df_res.to_excel(res_path, index=False)
        print(f"Successfully filled missing values in {res_path}")
    except Exception as e:
        print(f"Error saving to Excel: {e}")

if __name__ == "__main__":
    fill_resource_allocation()
