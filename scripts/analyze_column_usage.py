
import os
import json
import re

# Directories to search
SEARCH_DIRS = ['core_pipeline', 'api', 'scripts', 'ui', 'frontend/src', 'metadata']
EXTENSIONS = ['.py', '.tsx', '.ts', '.yaml', '.json']

def load_columns(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_usage(column_name, search_dirs):
    usage_count = 0
    patterns = [
        re.compile(fr'["\']{re.escape(column_name)}["\']'),  # Exact string match in quotes
        re.compile(fr'\.{re.escape(column_name)}\b'),        # Attribute access
    ]
    
    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for root, dirs, files in os.walk(sdir):
            for file in files:
                if any(file.endswith(ext) for ext in EXTENSIONS):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            for pattern in patterns:
                                usage_count += len(pattern.findall(content))
                    except Exception as e:
                        pass
    return usage_count

def main():
    table_columns = load_columns('table_columns.json')
    report = {}
    
    print("Analyzing column usage...")
    for table, columns in table_columns.items():
        print(f"Checking table: {table}")
        report[table] = []
        for col in columns:
            count = find_usage(col, SEARCH_DIRS)
            report[table].append({
                "column": col,
                "usage_count": count
            })
            
    with open('column_usage_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Analysis complete. Report saved to column_usage_report.json")

if __name__ == "__main__":
    main()
