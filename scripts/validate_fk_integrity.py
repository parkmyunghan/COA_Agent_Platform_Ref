# scripts/validate_fk_integrity.py
# Foreign Key 참조 무결성 검증
import pandas as pd
import os
import yaml
from pathlib import Path
from collections import defaultdict

data_lake_path = "data_lake"
schema_registry_path = "metadata/schema_registry.yaml"

print("=== FK 참조 무결성 검증 ===\n")

# schema_registry.yaml 로드
schema_registry = {}
if os.path.exists(schema_registry_path):
    with open(schema_registry_path, 'r', encoding='utf-8') as f:
        schema_registry = yaml.safe_load(f)

# 테이블 데이터 로드
def load_table(table_name):
    excel_file = os.path.join(data_lake_path, f"{table_name}.xlsx")
    if not os.path.exists(excel_file):
        return None
    try:
        return pd.read_excel(excel_file)
    except Exception as e:
        print(f"⚠️ {table_name} 로드 실패: {e}")
        return None

# FK 관계 정의
fk_relations = [
    {
        "source_table": "위협상황",
        "source_col": "발생위치셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "위협상황",
        "source_col": "관련축선ID",
        "target_table": "전장축선",
        "target_col": "축선ID"
    },
    {
        "source_table": "위협상황",
        "source_col": "관련_적부대ID",
        "target_table": "적군부대현황",
        "target_col": "적군부대ID"
    },
    {
        "source_table": "위협상황",
        "source_col": "관련임무ID",
        "target_table": "임무정보",
        "target_col": "임무ID"
    },
    {
        "source_table": "아군부대현황",
        "source_col": "배치지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "아군부대현황",
        "source_col": "배치축선ID",
        "target_table": "전장축선",
        "target_col": "축선ID"
    },
    {
        "source_table": "적군부대현황",
        "source_col": "배치지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "적군부대현황",
        "source_col": "배치축선ID",
        "target_table": "전장축선",
        "target_col": "축선ID"
    },
    {
        "source_table": "임무정보",
        "source_col": "주공축선ID",
        "target_table": "전장축선",
        "target_col": "축선ID"
    },
    {
        "source_table": "임무정보",
        "source_col": "조공축선ID",
        "target_table": "전장축선",
        "target_col": "축선ID"
    },
    {
        "source_table": "임무정보",
        "source_col": "예비축선ID",
        "target_table": "전장축선",
        "target_col": "축선ID"
    },
    {
        "source_table": "전장축선",
        "source_col": "시작지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "전장축선",
        "source_col": "종단지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "민간인지역",
        "source_col": "위치지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "아군가용자산",
        "source_col": "배치지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    },
    {
        "source_table": "기상상황",
        "source_col": "지형셀ID",
        "target_table": "지형셀",
        "target_col": "지형셀ID"
    }
]

# 모든 테이블 로드
tables = {}
table_names = set()
for rel in fk_relations:
    table_names.add(rel["source_table"])
    table_names.add(rel["target_table"])

for table_name in table_names:
    df = load_table(table_name)
    if df is not None:
        tables[table_name] = df

# FK 검증
results = {
    "valid": [],
    "invalid": [],
    "orphan_records": []
}

for rel in fk_relations:
    source_table = rel["source_table"]
    source_col = rel["source_col"]
    target_table = rel["target_table"]
    target_col = rel["target_col"]
    
    if source_table not in tables or target_table not in tables:
        continue
    
    source_df = tables[source_table]
    target_df = tables[target_table]
    
    if source_col not in source_df.columns:
        print(f"⚠️ {source_table}.{source_col} 컬럼 없음")
        continue
    
    if target_col not in target_df.columns:
        print(f"⚠️ {target_table}.{target_col} 컬럼 없음")
        continue
    
    # FK 값 추출 (NULL 제외)
    fk_values = source_df[source_col].dropna().unique()
    target_values = set(target_df[target_col].dropna().unique())
    
    # 고아 레코드 찾기
    orphan_values = [v for v in fk_values if v not in target_values and str(v).strip() != "" and str(v).strip().upper() != "N/A"]
    
    if orphan_values:
        results["invalid"].append({
            "relation": f"{source_table}.{source_col} → {target_table}.{target_col}",
            "orphan_count": len(orphan_values),
            "orphan_values": orphan_values[:10]  # 최대 10개만 표시
        })
        results["orphan_records"].extend([
            {
                "source_table": source_table,
                "source_col": source_col,
                "fk_value": v,
                "target_table": target_table
            }
            for v in orphan_values[:10]
        ])
    else:
        results["valid"].append(f"{source_table}.{source_col} → {target_table}.{target_col}")

# 결과 출력
print(f"✅ 정상 FK 관계: {len(results['valid'])}개\n")
for rel in results["valid"]:
    print(f"  - {rel}")

print(f"\n❌ 무결성 위반 FK 관계: {len(results['invalid'])}개\n")
for issue in results["invalid"]:
    print(f"  - {issue['relation']}")
    print(f"    고아 레코드 수: {issue['orphan_count']}개")
    if issue['orphan_values']:
        print(f"    예시: {issue['orphan_values']}")
    print()

# 요약 리포트
print("\n=== 요약 리포트 ===\n")
print(f"총 검증한 FK 관계: {len(fk_relations)}개")
print(f"정상: {len(results['valid'])}개")
print(f"무결성 위반: {len(results['invalid'])}개")

if results["invalid"]:
    print("\n⚠️ 조치 필요:")
    for issue in results["invalid"]:
        print(f"  - {issue['relation']}: {issue['orphan_count']}개 고아 레코드")
