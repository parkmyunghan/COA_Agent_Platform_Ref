import pandas as pd
import os
import shutil

def add_columns():
    file_path = r'c:\POC\COA_Agent_Platform\data_lake\COA_Library.xlsx'
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Backup the file
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    print(f"Backed up original file to {backup_path}")

    try:
        df = pd.read_excel(file_path)
        print(f"Loaded {file_path}. Rows: {len(df)}")

        # Define new columns and defaults
        new_columns = {
            "단계정보": "Phase 1",
            "주노력여부": "N",
            "시각화스타일": "Default"
        }

        updated = False
        for col, default_val in new_columns.items():
            if col not in df.columns:
                print(f"Adding column: {col}")
                df[col] = default_val
                updated = True
            else:
                print(f"Column already exists: {col}")

        if updated:
            # Save back to Excel
            df.to_excel(file_path, index=False)
            print(f"Successfully updated {file_path}")
        else:
            print("No changes needed.")
            
    except Exception as e:
        print(f"Failed to update Excel file: {e}")
        # Restore backup if failed
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            print("Restored backup due to failure.")

if __name__ == "__main__":
    add_columns()
