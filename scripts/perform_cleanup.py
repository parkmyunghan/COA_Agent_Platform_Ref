import os
import shutil
import glob
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path("c:/POC/COA_Agent_Platform_Ref")

# List of precise files/directories to delete based on the approved plan
DELETION_TARGETS = [
    # 1. Legacy Streamlit App
    "run_streamlit.py",
    "ui", # Directory
    "scripts/kill_streamlit.py",

    # 2. Test & Verification
    "tests", # Directory
    "frontend/src/test", # Directory
    "test_*.py", # Root patterns will be expanded
    "scripts/test_*.py",
    
    # 3. Debug & Ad-hoc Scripts
    "modules", # Directory
    "debug_*.py",
    "analyze_*.py",
    "scripts/analyze_*.py",
    "inspect_*.py",
    "scripts/inspect_*.py",
    "fix_*.py",
    "scripts/fix_*.py",
    "create_*.py",
    "scripts/create_*.py",
    "dummy_*.py", # If any
    "run_map_server.py", # Usually dev tool
    
    # 4. Old Verification Reports & Logs
    "*.log", 
    "logs/*.log",
    "check_output.txt",
    "consistency_report.txt",
    "verification_*.txt",
    "profile_result.txt",
    "test_options_output.txt",
    "test_report_*.md",
    
    # 5. Temporary Dumps
    "temp_*.json",
    "*_dump.json",
    "*_dump.txt",
    
    # 6. Specific Scripts (as per plan)
    "scripts/fill_*.py",
    "scripts/enrich_*.py",
    "scripts/migrate_*.py",
    "scripts/performance_monitor.py",
    "scripts/reproduce_*.py",
    "scripts/verify_*.py", # Self-delete verification scripts too
    "scripts/trace_*.py",
    "scripts/dump_*.py",
    
    # Cleanup self (optional, but good for final sweep)
    # "scripts/perform_cleanup.py" # Don't delete self while running
    "scripts/verify_deletion_safety.py"
]

# Exceptions (Files to FORCE KEEP even if they match patterns)
KEEP_LIST = [
    "README.md",
    "ENV_SETUP.md",
    "requirements.txt",
    "scripts/validate_data_integrity.py", 
    "scripts/validate_fk_integrity.py",
    "scripts/setup_offline_assets.py",
    "scripts/doc_manager.py",
    "ADD_TO_COA_SERVICE.txt"
]

def delete_path(path_obj):
    if not path_obj.exists():
        return
    
    # Double check keep list
    if path_obj.name in KEEP_LIST or str(path_obj.relative_to(PROJECT_ROOT)) in KEEP_LIST:
        print(f"[SKIP] Preserving {path_obj.name}")
        return

    try:
        if path_obj.is_dir():
            shutil.rmtree(path_obj)
            print(f"[DIR DELETED] {path_obj}")
        else:
            path_obj.unlink()
            print(f"[FILE DELETED] {path_obj}")
    except Exception as e:
        print(f"[ERROR] Could not delete {path_obj}: {e}")

def resolve_glob(pattern):
    # If pattern contains directory parts, use glob with recursive if needed
    # but simplest is to use Path.glob or glob module
    full_pattern = str(PROJECT_ROOT / pattern)
    return [Path(p) for p in glob.glob(full_pattern, recursive=True)]

def main():
    print(">>> Starting Production Cleanup...")
    print(f"Project Root: {PROJECT_ROOT}")
    
    processed_files = set()
    
    for target in DELETION_TARGETS:
        # Resolve patterns
        matches = resolve_glob(target)
        
        for path_obj in matches:
            if path_obj in processed_files:
                continue
            
            # Additional safety: Ensure we are inside PROJECT_ROOT
            try:
                path_obj.relative_to(PROJECT_ROOT)
            except ValueError:
                print(f"[SKIP] Safety Check Failed: {path_obj} is outside project root")
                continue
                
            delete_path(path_obj)
            processed_files.add(path_obj)
            
    print("\n>>> Cleanup Complete.")

if __name__ == "__main__":
    main()
