# scripts/analyze_schema_issues.py
# 스키마 문서와 실제 Excel 파일 간의 불일치 분석
import pandas as pd
import yaml
import json
import os
from pathlib import Path
from collections import defaultdict

data_lake_path = "data_lake"
schema_registry_path = "metadata/schema_registry.yaml"
excel_columns_path = "scripts/excel_columns.json"

print("=== 스키마 불일치 분석 ===\n")

# 1. schema_registry.yaml 로드
schema_registry = {}
if os.path.exists(schema_registry_path):
    with open(schema_registry_path, 'r', encoding='utf-8') as f:
        schema_registry = yaml.safe_load(f)

# 2. excel_columns.json 로드
excel_columns = {}
if os.path.exists(excel_columns_path):
    with open(excel_columns_path, 'r', encoding='utf-8') as f:
        excel_columns = json.load(f)

# 3. 실제 Excel 파일 컬럼 확인
def get_actual_columns(table_name):
    excel_file = os.path.join(data_lake_path, f"{table_name}.xlsx")
    if not os.path.exists(excel_file):
        return None
    try:
        df = pd.read_excel(excel_file, nrows=0)
        return list(df.columns)
    except:
        return None

# 4. 중복/상충 컬럼 분석
def analyze_duplicate_columns():
    """테이블 내 및 테이블 간 중복/상충 컬럼 분석"""
    
    issues = {
        "within_table": {},  # 테이블 내 중복
        "across_tables": defaultdict(list),  # 테이블 간 중복
        "naming_inconsistency": [],  # 명명 불일치
        "type_inconsistency": []  # 타입 불일치
    }
    
    # 주요 테이블 분석
    tables = {
        "위협상황": get_actual_columns("위협상황"),
        "아군부대현황": get_actual_columns("아군부대현황"),
        "적군부대현황": get_actual_columns("적군부대현황"),
        "지형셀": get_actual_columns("지형셀"),
        "전장축선": get_actual_columns("전장축선"),
        "임무정보": get_actual_columns("임무정보"),
        "COA_Library": get_actual_columns("COA_Library")
    }
    
    # 테이블 내 중복 검사
    for table_name, columns in tables.items():
        if not columns:
            continue
        
        # 동일한 컬럼명이 여러 번 나타나는지
        from collections import Counter
        counter = Counter(columns)
        duplicates = {col: count for col, count in counter.items() if count > 1}
        if duplicates:
            issues["within_table"][table_name] = duplicates
        
        # 유사한 의미의 컬럼명 찾기
        similar_pairs = []
        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                # 유사도 체크 (간단한 휴리스틱)
                if col1.lower() in col2.lower() or col2.lower() in col1.lower():
                    if col1 != col2:
                        similar_pairs.append((col1, col2))
        if similar_pairs:
            if table_name not in issues["within_table"]:
                issues["within_table"][table_name] = {}
            issues["within_table"][table_name]["similar_names"] = similar_pairs
    
    # 테이블 간 중복 검사
    all_columns = {}
    for table_name, columns in tables.items():
        if not columns:
            continue
        for col in columns:
            if col not in all_columns:
                all_columns[col] = []
            all_columns[col].append(table_name)
    
    for col, table_list in all_columns.items():
        if len(table_list) > 1:
            issues["across_tables"][col] = table_list
    
    # 명명 불일치 검사
    naming_patterns = {
        "전투력": ["전투력지수", "전투력"],
        "이동속도": ["이동속도", "이동속도_kmh"],
        "좌표": ["좌표정보", "X좌표", "Y좌표"],
        "위협유형": ["위협유형코드", "위협유형"],
        "지형셀목록": ["주요지형셀목록", "구성지형셀목록"]
    }
    
    for pattern, variants in naming_patterns.items():
        found_in = {}
        for variant in variants:
            for table_name, columns in tables.items():
                if columns and variant in columns:
                    if variant not in found_in:
                        found_in[variant] = []
                    found_in[variant].append(table_name)
        if len(found_in) > 1:
            issues["naming_inconsistency"].append({
                "pattern": pattern,
                "variants": found_in
            })
    
    return issues

# 5. 스키마 문서와 실제 파일 비교
def compare_with_schema_registry():
    """schema_registry.yaml과 실제 Excel 파일 비교"""
    
    if not schema_registry or "tables" not in schema_registry:
        return {}
    
    mismatches = {}
    
    for table_name, table_def in schema_registry["tables"].items():
        actual_cols = get_actual_columns(table_name)
        if not actual_cols:
            continue
        
        schema_cols = list(table_def.get("columns", {}).keys())
        
        missing_in_schema = set(actual_cols) - set(schema_cols)
        missing_in_actual = set(schema_cols) - set(actual_cols)
        
        if missing_in_schema or missing_in_actual:
            mismatches[table_name] = {
                "missing_in_schema": list(missing_in_schema),
                "missing_in_actual": list(missing_in_actual),
                "actual_count": len(actual_cols),
                "schema_count": len(schema_cols)
            }
    
    return mismatches

# 실행
print("1. 중복/상충 컬럼 분석\n")
duplicate_issues = analyze_duplicate_columns()

if duplicate_issues["within_table"]:
    print("📋 테이블 내 중복/유사 컬럼:")
    for table, issues in duplicate_issues["within_table"].items():
        print(f"  {table}:")
        if "similar_names" in issues:
            for pair in issues["similar_names"]:
                print(f"    - 유사한 이름: {pair[0]} vs {pair[1]}")
        print()

if duplicate_issues["across_tables"]:
    print("📋 테이블 간 공통 컬럼 (의도된 것일 수 있음):")
    for col, tables in list(duplicate_issues["across_tables"].items())[:10]:
        print(f"  '{col}': {', '.join(tables)}")
    print()

if duplicate_issues["naming_inconsistency"]:
    print("📋 명명 불일치:")
    for issue in duplicate_issues["naming_inconsistency"]:
        print(f"  패턴: {issue['pattern']}")
        for variant, tables in issue["variants"].items():
            print(f"    - '{variant}': {', '.join(tables)}")
    print()

print("\n2. schema_registry.yaml과 실제 파일 비교\n")
schema_mismatches = compare_with_schema_registry()

if schema_mismatches:
    print("📋 스키마 문서 불일치:")
    for table, mismatch in schema_mismatches.items():
        print(f"  {table}:")
        print(f"    실제 컬럼 수: {mismatch['actual_count']}, 스키마 컬럼 수: {mismatch['schema_count']}")
        if mismatch["missing_in_schema"]:
            print(f"    ⚠️ 스키마에 없는 컬럼: {mismatch['missing_in_schema'][:5]}{'...' if len(mismatch['missing_in_schema']) > 5 else ''}")
        if mismatch["missing_in_actual"]:
            print(f"    ⚠️ 실제 파일에 없는 컬럼: {mismatch['missing_in_actual'][:5]}{'...' if len(mismatch['missing_in_actual']) > 5 else ''}")
        print()

# 우선순위별 문제점 정리
print("\n3. 우선순위별 문제점\n")

critical_issues = []
high_issues = []
medium_issues = []

# Critical: PK/FK 관련 문제
for table, mismatch in schema_mismatches.items():
    if table in ["위협상황", "아군부대현황", "적군부대현황", "임무정보"]:
        if "위협ID" in mismatch.get("missing_in_schema", []) or \
           "아군부대ID" in mismatch.get("missing_in_schema", []) or \
           "적군부대ID" in mismatch.get("missing_in_schema", []):
            critical_issues.append(f"{table}: PK 컬럼 누락 가능성")

# High: 명명 불일치
for issue in duplicate_issues["naming_inconsistency"]:
    if issue["pattern"] in ["전투력", "이동속도", "위협유형"]:
        high_issues.append(f"명명 불일치: {issue['pattern']}")

# Medium: 추가 컬럼
for table, mismatch in schema_mismatches.items():
    if mismatch["missing_in_schema"]:
        medium_issues.append(f"{table}: 추가 컬럼 {len(mismatch['missing_in_schema'])}개")

print("🔴 Critical:")
for issue in critical_issues:
    print(f"  - {issue}")

print("\n🟠 High:")
for issue in high_issues:
    print(f"  - {issue}")

print("\n🟡 Medium:")
for issue in medium_issues[:10]:
    print(f"  - {issue}")
