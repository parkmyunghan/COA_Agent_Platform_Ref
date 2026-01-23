
import pandas as pd
from pathlib import Path
import shutil
import os

def migrate_columns():
    data_lake = Path("data_lake")
    target_file = data_lake / "아군부대현황.xlsx"
    backup_file = data_lake / "아군부대현황.xlsx.bak"
    
    if not target_file.exists():
        print(f"[ERROR] Target file not found: {target_file}")
        return
    
    # Backup
    try:
        shutil.copy2(target_file, backup_file)
        print(f"[INFO] Created backup: {backup_file}")
    except Exception as e:
        print(f"[ERROR] Failed to create backup: {e}")
        return

    try:
        # Load
        df = pd.read_excel(target_file)
        original_columns = df.columns.tolist()
        print(f"[INFO] Original Columns: {original_columns}")
        
        # Rename
        if '이동속도' in df.columns:
            df.rename(columns={'이동속도': '이동속도_kmh'}, inplace=True)
            print("[INFO] Renamed '이동속도' to '이동속도_kmh'.")
        else:
            print("[WARN] Column '이동속도' not found. Migration might have already run.")
        
        # Save
        df.to_excel(target_file, index=False)
        print(f"[INFO] Saved migrated file to {target_file}")
        
        # Verify
        df_new = pd.read_excel(target_file)
        print(f"[INFO] New Columns: {df_new.columns.tolist()}")
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        # Restore backup
        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            print("[INFO] Restored from backup due to error.")

if __name__ == "__main__":
    migrate_columns()
