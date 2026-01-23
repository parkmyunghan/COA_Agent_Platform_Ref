import re
import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Fix COA summary scores and fields
    replacements = [
        (r'summary\.get\(\'coa_name\', coa_eval\.coa_id\)', r'str(summary.get("coa_name", coa_eval.coa_id))'),
        (r'summary\.get\(\'total_score\', 0\.0\)', r'float(summary.get("total_score", 0.0))'),
        (r'summary\.get\(\'description\', \'\'\)', r'str(summary.get("description", ""))'),
        (r'summary\.get\(\'combat_power_score\', 0\.0\)', r'float(summary.get("combat_power_score", 0.0))'),
        (r'summary\.get\(\'mobility_score\', 0\.0\)', r'float(summary.get("mobility_score", 0.0))'),
        (r'summary\.get\(\'constraint_compliance_score\', summary\.get\(\'constraint_score\', 0\.0\)\)', r'float(summary.get("constraint_compliance_score", summary.get("constraint_score", 0.0)))'),
        (r'summary\.get\(\'threat_response_score\', 0\.0\)', r'float(summary.get("threat_response_score", 0.0))'),
        (r'summary\.get\(\'risk_score\', 0\.0\)', r'float(summary.get("risk_score", 0.0))'),
        (r'unit_row\.iloc\[0\]\.get\(\'전투력지수\', 0\)', r'float(unit_row.iloc[0].get("전투력지수", 0))'),
        (r'unit_row\.iloc\[0\]\.get\(\'부대명\', \'\'\)', r'str(unit_row.iloc[0].get("부대명", ""))'),
        (r'unit_row\.iloc\[0\]\.get\(\'제대\', \'\'\)', r'str(unit_row.iloc[0].get("제대", ""))'),
        (r'unit_row\.iloc\[0\]\.get\(\'병종\', \'\'\)', r'str(unit_row.iloc[0].get("병종", ""))'),
        (r'unit_row\.iloc\[0\]\.get\(\'배치지형셀ID\', \'\'\)', r'str(unit_row.iloc[0].get("배치지형셀ID", ""))'),
        (r'unit_row\.iloc\[0\]\.get\(\'좌표정보\', \'\'\)', r'str(unit_row.iloc[0].get("좌표정보", ""))'),
    ]
    
    for old, new in replacements:
        content = re.sub(old, new, content)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {filepath}")

if __name__ == "__main__":
    fix_file('api/routers/coa.py')
    fix_file('core_pipeline/visualization_generator.py')
