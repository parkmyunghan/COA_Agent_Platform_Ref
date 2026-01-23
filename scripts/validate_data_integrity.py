# scripts/validate_data_integrity.py
# -*- coding: utf-8 -*-
import pandas as pd
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent))

DATA_LAKE = "data_lake"

def check_nulls(df, table_name, essential_cols):
    results = []
    for col in essential_cols:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                results.append(f"❌ {table_name}: '{col}' 컬럼에 {null_count}개의 NULL 데이터 발견")
        else:
            results.append(f"⚠️ {table_name}: 필수 컬럼 '{col}'이 존재하지 않음")
    return results

def check_ranges(df, table_name, col, min_val, max_val):
    if col in df.columns:
        invalid = df[(df[col] < min_val) | (df[col] > max_val)]
        if not invalid.empty:
            return [f"❌ {table_name}: '{col}' 컬럼에 범위 외 데이터 {len(invalid)}개 발견 (범위: {min_val}~{max_val})"]
    return []

def main():
    print("=== 데이터 무결성 검증 시작 ===\n")
    
    validation_errors = []
    
    # 1. 위협상황 검증
    if os.path.exists(f"{DATA_LAKE}/위협상황.xlsx"):
        df = pd.read_excel(f"{DATA_LAKE}/위협상황.xlsx")
        validation_errors.extend(check_nulls(df, "위협상황", ["위협ID", "위협유형코드", "발생위치셀ID"]))
        # 위협수준 0~1 검증 (문자열일 가능성 대비)
        if "위협수준" in df.columns:
            try:
                df["위협수준_num"] = pd.to_numeric(df["위협수준"], errors='coerce')
                validation_errors.extend(check_ranges(df, "위협상황", "위협수준_num", 0, 1))
            except:
                pass

    # 2. 부대현황 검증
    for table in ["아군부대현황", "적군부대현황"]:
        if os.path.exists(f"{DATA_LAKE}/{table}.xlsx"):
            df = pd.read_excel(f"{DATA_LAKE}/{table}.xlsx")
            pk = "아군부대ID" if "아군" in table else "적군부대ID"
            validation_errors.extend(check_nulls(df, table, [pk, "부대명", "배치지형셀ID"]))
            if "전투력지수" in df.columns:
                validation_errors.extend(check_ranges(df, table, "전투력지수", 0, 10000)) # 임의 최대값

    # 3. 좌표정보 형식 검증 (단순 존재 여부 및 형식 힌트)
    for table in ["위협상황", "아군부대현황", "적군부대현황", "지형셀"]:
        if os.path.exists(f"{DATA_LAKE}/{table}.xlsx"):
            df = pd.read_excel(f"{DATA_LAKE}/{table}.xlsx")
            if "좌표정보" in df.columns:
                invalid_geo = df[df["좌표정보"].notnull() & ~df["좌표정보"].astype(str).str.contains(",")]
                if not invalid_geo.empty:
                    validation_errors.append(f"⚠️ {table}: '좌표정보' 형식이 부정확함 (콤마 미포함 {len(invalid_geo)}개)")

    if not validation_errors:
        print("✅ 모든 기본 무결성 검증 통과!")
    else:
        print("\n".join(validation_errors))

if __name__ == "__main__":
    main()
