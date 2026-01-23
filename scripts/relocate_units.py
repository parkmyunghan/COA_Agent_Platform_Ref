import pandas as pd
import os
import sys

BASE_DIR = r"C:\POC\COA_Agent_Platform_Ref\data_lake"
UNIT_FILE = os.path.join(BASE_DIR, "아군부대현황.xlsx")
ASSET_FILE = os.path.join(BASE_DIR, "아군가용자산.xlsx")
TERRAIN_FILE = os.path.join(BASE_DIR, "지형셀.xlsx")

def update_terrain_cells():
    print("=== 1. Updating Terrain Cells (지형셀.xlsx) ===")
    if not os.path.exists(TERRAIN_FILE):
        print(f"[ERROR] {TERRAIN_FILE} not found")
        return False
        
    df = pd.read_excel(TERRAIN_FILE)
    
    # New cells to add
    new_cells = [
        {'지형셀ID': 'TERR021', '지형명': '파주(문산)', '좌표정보': '37.85, 126.78'},
        {'지형셀ID': 'TERR022', '지형명': '파주(법원)', '좌표정보': '37.82, 126.90'},
        {'지형셀ID': 'TERR023', '지형명': '연천(전곡)', '좌표정보': '38.02, 127.06'},
        {'지형셀ID': 'TERR024', '지형명': '양주(광적)', '좌표정보': '37.82, 126.98'},
        {'지형셀ID': 'TERR025', '지형명': '동두천', '좌표정보': '37.90, 127.05'},
        {'지형셀ID': 'TERR026', '지형명': '포천', '좌표정보': '37.89, 127.20'},
        {'지형셀ID': 'TERR027', '지형명': '고양(일산)', '좌표정보': '37.66, 126.77'},
        {'지형셀ID': 'TERR028', '지형명': '의정부', '좌표정보': '37.74, 127.04'},
        {'지형셀ID': 'TERR029', '지형명': '김포', '좌표정보': '37.62, 126.70'},
        {'지형셀ID': 'TERR030', '지형명': '철원(남)', '좌표정보': '38.15, 127.25'}
    ]
    
    # Check if exists and append
    updated = False
    for cell in new_cells:
        if cell['지형셀ID'] not in df['지형셀ID'].values:
            df = pd.concat([df, pd.DataFrame([cell])], ignore_index=True)
            print(f"  [Added] {cell['지형셀ID']} - {cell['지형명']}")
            updated = True
        else:
            # Update existing if needed (optional)
            idx = df[df['지형셀ID'] == cell['지형셀ID']].index
            df.loc[idx, '좌표정보'] = cell['좌표정보'] # Force update coords
            print(f"  [Updated] {cell['지형셀ID']} coords")
            updated = True
            
    if updated:
        df.to_excel(TERRAIN_FILE, index=False)
        print(">> Saved Terrain File.")
    else:
        print(">> No changes to Terrain File.")
        
    return True

def update_units_and_assets():
    print("\n=== 2. Relocating Units & Syncing Assets ===")
    
    # Load files
    if not os.path.exists(UNIT_FILE) or not os.path.exists(ASSET_FILE):
        print("[ERROR] Unit or Asset file not found")
        return False
        
    df_unit = pd.read_excel(UNIT_FILE)
    df_asset = pd.read_excel(ASSET_FILE)
    
    # Mapping Logic
    # Unit ID -> { New Coords, New Cell, Mapped Asset ID }
    relocation_map = {
        'FRU001': {'coord': '37.85, 126.85', 'cell': 'TERR021', 'asset': None}, # 기계화여단
        'FRU002': {'coord': '37.92, 127.05', 'cell': 'TERR023', 'asset': 'AST005'}, # 보병여단
        'FRU003': {'coord': '37.78, 126.95', 'cell': 'TERR024', 'asset': 'AST012'}, # 기갑여단
        'FRU004': {'coord': '37.75, 126.90', 'cell': 'TERR024', 'asset': 'AST015'}, # 포병여단
        'FRU005': {'coord': '37.96, 126.92', 'cell': 'TERR022', 'asset': 'AST008'}, # 수색대대
        'FRU006': {'coord': '37.82, 126.80', 'cell': 'TERR021', 'asset': None}, # 전차대대
        'FRU007': {'coord': '37.72, 126.98', 'cell': 'TERR028', 'asset': 'AST009'}, # 공병대대
        'FRU008': {'coord': '37.65, 127.02', 'cell': 'TERR028', 'asset': None}, # 통신대대
        'FRU009': {'coord': '37.62, 127.05', 'cell': 'TERR028', 'asset': None}, # 의무중대
        'FRU010': {'coord': '37.60, 127.00', 'cell': 'TERR027', 'asset': None}, # 보급대대
        'FRU011': {'coord': '37.55, 126.75', 'cell': 'TERR029', 'asset': None}, # 1항공여단
        'FRU012': {'coord': '37.98, 127.15', 'cell': 'TERR030', 'asset': 'AST023'}, # 특수작전팀
        'FRU013': {'coord': '37.80, 126.88', 'cell': 'TERR027', 'asset': 'AST022'}, # 공격헬기대대
    }
    
    # Process Relocation
    for unit_id, info in relocation_map.items():
        # 1. Update Unit
        idx = df_unit[df_unit['아군부대ID'] == unit_id].index
        if not idx.empty:
            df_unit.loc[idx, '좌표정보'] = info['coord']
            df_unit.loc[idx, '배치지형셀ID'] = info['cell']
            unit_name = df_unit.loc[idx, '부대명'].values[0]
            print(f"  [Unit] {unit_name} ({unit_id}) moved to {info['cell']} ({info['coord']})")
            
            # 2. Update Asset (if mapped)
            if info['asset']:
                asset_id = info['asset']
                a_idx = df_asset[df_asset['자산ID'] == asset_id].index
                if not a_idx.empty:
                     # Asset table might not have '좌표정보', usually links via '배치지형셀ID'
                     # checking columns
                    df_asset.loc[a_idx, '배치지형셀ID'] = info['cell']
                    print(f"    -> [Asset Asset] {asset_id} synced to {info['cell']}")
        else:
            print(f"  [WARN] Unit {unit_id} not found")

    # Save
    df_unit.to_excel(UNIT_FILE, index=False)
    print(">> Saved Unit File.")
    
    df_asset.to_excel(ASSET_FILE, index=False)
    print(">> Saved Asset File.")
    
    return True

if __name__ == "__main__":
    if update_terrain_cells() and update_units_and_assets():
        print("\n[SUCCESS] Relocation Complete.")
    else:
        print("\n[FAIL] Relocation Failed.")
