import pandas as pd
import os
import shutil

def add_columns_to_file(file_path, default_values):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Backup
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    print(f"Backed up {file_path} to {backup_path}")

    try:
        df = pd.read_excel(file_path)
        updated = False
        
        for col, default_val in default_values.items():
            if col not in df.columns:
                print(f"Adding column '{col}' to {os.path.basename(file_path)}")
                df[col] = default_val
                updated = True
            else:
                print(f"Column '{col}' already exists in {os.path.basename(file_path)}")

        if updated:
            df.to_excel(file_path, index=False)
            print(f"Successfully updated {file_path}")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Failed to update {file_path}: {e}")
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            print("Restored backup.")

def main():
    # Common columns for both files
    common_cols = {
        "SIDC": "SFG*------*****", # Placeholder
        "전투력지수": 100,
        "이동속도_kmh": 40,
        "감지범위_km": 15
    }
    
    # 1. Friendly Assets
    friendly_path = r'c:\POC\COA_Agent_Platform\data_lake\아군가용자산.xlsx'
    add_columns_to_file(friendly_path, common_cols)
    
    # 2. Enemy Units
    enemy_path = r'c:\POC\COA_Agent_Platform\data_lake\적군부대현황.xlsx'
    # Enemy might have different default SIDC
    enemy_cols = common_cols.copy()
    enemy_cols["SIDC"] = "SHG*------*****"
    add_columns_to_file(enemy_path, enemy_cols)

if __name__ == "__main__":
    main()
