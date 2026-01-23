
import pandas as pd
import random
from pathlib import Path

def refine_resource_migration():
    base_path = Path("c:/POC/COA_Agent_Platform_화면 리팩토링/data_lake")
    allocation_file = base_path / "임무별_자원할당.xlsx"
    asset_file = base_path / "아군가용자산.xlsx"

    if not allocation_file.exists():
        print(f"Error: {allocation_file} not found. Run version 1 first.")
        return

    df_alloc = pd.read_excel(allocation_file)
    df_asset = pd.read_excel(asset_file)

    # 자산 종류별 ID 리스트 생성
    asset_types = df_asset['자산종류'].unique().tolist()
    assets_by_type = {t: df_asset[df_asset['자산종류'] == t]['자산ID'].tolist() for t in asset_types}
    all_asset_ids = df_asset['자산ID'].tolist()

    # 명칭 기반 매핑 (기존보다 강화)
    asset_name_to_id = dict(zip(df_asset['자산명'], df_asset['자산ID']))

    def get_best_asset_id(alias):
        alias = str(alias).strip()
        # 1. 완전 일치
        if alias in asset_name_to_id:
            return asset_name_to_id[alias]
        
        # 2. 부분 일치 (예: 'K-9' -> 'K-9 자주포')
        for name, aid in asset_name_to_id.items():
            if alias in name or name in alias:
                return aid
        
        # 3. 타입 유추 및 임의 매핑
        if '전차' in alias or '기갑' in alias:
            return random.choice(assets_by_type.get('기갑장비', all_asset_ids))
        if '포' in alias or '화력' in alias:
            return random.choice(assets_by_type.get('포병장비', all_asset_ids))
        if '헬기' in alias or '항공' in alias or '전투기' in alias:
            return random.choice(assets_by_type.get('항공장비', all_asset_ids))
        if '보병' in alias or '여단' in alias or '대대' in alias:
            return random.choice(assets_by_type.get('인력', all_asset_ids))
            
        # 4. 최후의 수단: 전체 중 랜덤
        return random.choice(all_asset_ids)

    print("Refining asset_id mappings...")
    unknown_mask = df_alloc['asset_id'] == 'AST_UNKNOWN'
    df_alloc.loc[unknown_mask, 'asset_id'] = df_alloc.loc[unknown_mask, 'resource_alias'].apply(get_best_asset_id)

    # 중복 컬럼 제거 (user 요청: quantity, status 삭제)
    print("Removing redundant columns: quantity, status")
    df_alloc = df_alloc.drop(columns=['quantity', 'status'])

    print(f"Saving refined file to {allocation_file}...")
    df_alloc.to_excel(allocation_file, index=False)
    print("Optimization complete!")

if __name__ == "__main__":
    refine_resource_migration()
