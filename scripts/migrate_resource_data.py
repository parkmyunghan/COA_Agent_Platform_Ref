
import pandas as pd
import os
from pathlib import Path

def migrate_resource_data():
    base_path = Path("c:/POC/COA_Agent_Platform_화면 리팩토링/data_lake")
    old_file = base_path / "가용자원.xlsx"
    asset_file = base_path / "아군가용자산.xlsx"
    new_file = base_path / "임무별_자원할당.xlsx"

    if not old_file.exists():
        print(f"Error: {old_file} not found.")
        return

    print("Loading data...")
    df_old = pd.read_excel(old_file)
    df_asset = pd.read_excel(asset_file)

    # 자산명 -> 자산ID 매핑 딕셔너리 생성
    asset_map = dict(zip(df_asset['자산명'], df_asset['자산ID']))

    new_rows = []
    print(f"Migrating {len(df_old)} rows...")

    for i, row in df_old.iterrows():
        # 수량 통합 로직
        qty = row.get('available_quantity')
        if pd.isna(qty) or qty == 0:
            qty = row.get('수량', 0)
        
        # 만약 둘 다 없으면 기본값 1 또는 0
        qty = int(qty) if not pd.isna(qty) else 0

        resource_name = str(row.get('resource_name', '')).strip()
        
        # asset_id 매핑 시도
        asset_id = asset_map.get(resource_name, "AST_UNKNOWN")
        
        # 새로운 행 생성
        new_row = {
            'allocation_id': f"RA_{i+1:03d}",
            'mission_id': row.get('situation_id'),
            'asset_id': asset_id,
            'resource_alias': resource_name,
            'quantity': qty,
            'status': row.get('status', '사용가능'),
            'note': row.get('notes', row.get('note', ''))
        }
        new_rows.append(new_row)

    df_new = pd.DataFrame(new_rows)

    print(f"Saving new file to {new_file}...")
    df_new.to_excel(new_file, index=False)

    # 레거시 백업
    backup_file = old_file.with_suffix(".xlsx.bak")
    if not backup_file.exists():
        os.rename(old_file, backup_file)
        print(f"Original file backed up to {backup_file}")
    else:
        print(f"Backup already exists at {backup_file}")

    print("Migration complete!")

if __name__ == "__main__":
    migrate_resource_data()
