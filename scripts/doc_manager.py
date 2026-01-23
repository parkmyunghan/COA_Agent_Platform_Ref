import os
import shutil
import sys
import datetime
import argparse
from pathlib import Path

# Configuration
DOCS_ROOT = Path("docs")
ARCHIVE_DIR = DOCS_ROOT / "99_Archive"
MANAGEMENT_DIR = DOCS_ROOT / "00_Management"

def setup_dirs():
    if not DOCS_ROOT.exists():
        print(f"Error: {DOCS_ROOT} directory not found.")
        sys.exit(1)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    MANAGEMENT_DIR.mkdir(parents=True, exist_ok=True)

def archive_file(file_path):
    """Moves a file to the archive directory with a timestamp."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File {file_path} not found.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = f"{path.stem}_{timestamp}{path.suffix}"
    dest = ARCHIVE_DIR / new_name
    
    try:
        shutil.move(str(path), str(dest))
        print(f"Archived: {path} -> {dest}")
    except Exception as e:
        print(f"Error archiving file: {e}")

def create_log(title, content_file=None, content_text=None):
    """Creates a new log file in the archive directory."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    # Sanitize title
    safe_title = "".join([c if c.isalnum() or c in (' ', '_', '-') else '' for c in title]).strip().replace(' ', '_')
    filename = f"작업_로그_{timestamp}_{safe_title}.md"
    dest = ARCHIVE_DIR / filename
    
    content = ""
    if content_file:
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading content file: {e}")
            return
    elif content_text:
        content = content_text
    else:
        print("Error: No content provided.")
        return

    try:
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(content)
        print(f"Log created: {dest}")
    except Exception as e:
        print(f"Error creating log: {e}")

def validate_docs():
    """Checks for loose files in docs root and warns about language."""
    print("Checking documentation structure...")
    issues = []
    
    # Check root docs files
    for item in DOCS_ROOT.glob("*"):
        if item.is_file() and item.name != "README.md":
            issues.append(f"File in root docs folder: {item.name} (Should be in a subdirectory)")
            
    if issues:
        print("\n[Issues Found]")
        for issue in issues:
            print(f"- {issue}")
        print("\nPlease move these files to appropriate subdirectories (00-99).")
    else:
        print("Documentation structure looks good.")

def main():
    parser = argparse.ArgumentParser(description="Documentation Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Archive command
    archive_parser = subparsers.add_parser("archive", help="Archive a file")
    archive_parser.add_argument("file", help="Path of the file to archive")

    # Log command
    log_parser = subparsers.add_parser("log", help="Create a work log")
    log_parser.add_argument("title", help="Title of the log")
    log_parser.add_argument("--file", help="File containing log content")
    log_parser.add_argument("--text", help="Text string content")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate doc structure")

    args = parser.parse_args()
    
    setup_dirs()

    if args.command == "archive":
        archive_file(args.file)
    elif args.command == "log":
        create_log(args.title, content_file=args.file, content_text=args.text)
    elif args.command == "validate":
        validate_docs()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
