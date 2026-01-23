
import pandas as pd
from pathlib import Path

def enrich_data():
    base_path = Path("c:/POC/COA_Agent_Platform_화면 리팩토링/data_lake")
    alloc_file = base_path / "임무별_자원할당.xlsx"
    asset_file = base_path / "아군가용자산.xlsx"

    if not alloc_file.exists() or not asset_file.exists():
        print("Required files not found.")
        return

    df_alloc = pd.read_excel(alloc_file)
    df_asset = pd.read_excel(asset_file)
    asset_dict = df_asset.set_index('자산ID')['자산명'].to_dict()

    def assign_role(row):
        name = asset_dict.get(row['asset_id'], '')
        if '전차' in name: return '충격군(Shock Force)'
        if '포병' in name or '자주포' in name: return '화력지원(Fire Support)'
        if '보병' in name: return '기동차단(Fixing Force)'
        if '항공' in name or '헬기' in name: return '항공타격(Air Strike)'
        if '공병' in name: return '장애물제거(Engineer)'
        return '예비대(Reserve)'

    # 1. 전술적 역할 부여
    df_alloc['tactical_role'] = df_alloc.apply(assign_role, axis=1)

    # 2. 할당 수량 다양화 (대부분 1, 특정 역할 2)
    df_alloc['allocated_quantity'] = 1
    df_alloc.loc[df_alloc['tactical_role'] == '기동차단(Fixing Force)', 'allocated_quantity'] = 2

    # 3. 계획 상태 (현재 마스터 상태와 동일하게 초기화)
    status_map = df_asset.set_index('자산ID')['가용상태'].to_dict()
    df_alloc['plan_status'] = df_alloc['asset_id'].map(status_map).fillna('사용가능')

    df_alloc.to_excel(alloc_file, index=False)
    print(f"Update complete: {len(df_alloc)} rows enriched.")

if __name__ == "__main__":
    enrich_data()
