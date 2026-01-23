
import pandas as pd
from pathlib import Path
import shutil
import os

def add_distance_column():
    data_lake = Path("data_lake")
    target_file = data_lake / "전장축선.xlsx"
    backup_file = data_lake / "전장축선.xlsx.bak"
    
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
        
        # Add Column
        if '거리_km' not in df.columns:
            # Add empty column or default value (e.g., None or 0)
            # Using 0 or None. Let's use None (NaN) so we can distinguish missing data.
            df['거리_km'] = None
            print("[INFO] Added '거리_km' column.")
            
            # Save
            df.to_excel(target_file, index=False)
            print(f"[INFO] Saved migrated file to {target_file}")
            
            # Verify
            df_new = pd.read_excel(target_file)
            print(f"[INFO] New Columns: {df_new.columns.tolist()}")
        else:
            print("[WARN] Column '거리_km' already exists.")
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        # Restore backup
        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            print("[INFO] Restored from backup due to error.")

if __name__ == "__main__":
    add_distance_column()
