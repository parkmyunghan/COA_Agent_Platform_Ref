"""데이터 레이크의 모든 테이블 구조 분석"""
import pandas as pd
import os
from pathlib import Path

def analyze_tables():
    data_lake_path = Path("data_lake")
    tables = {}
    
    print("=" * 100)
    print("데이터 레이크 테이블 구조 분석")
    print("=" * 100)
    
    for excel_file in sorted(data_lake_path.glob("*.xlsx")):
        table_name = excel_file.stem
        try:
            df = pd.read_excel(excel_file)
            columns = list(df.columns)
            row_count = len(df)
            
            tables[table_name] = {
                "columns": columns,
                "row_count": row_count,
                "sample_data": df.head(2).to_dict('records')
            }
            
            print(f"\n{'=' * 100}")
            print(f"테이블: {table_name}")
            print(f"{'=' * 100}")
            print(f"행 개수: {row_count}")
            print(f"컬럼 개수: {len(columns)}")
            print(f"컬럼 목록:")
            for i, col in enumerate(columns, 1):
                print(f"  {i:2d}. {col}")
            
            # 샘플 데이터 (첫 번째 행만)
            if row_count > 0:
                print(f"\n샘플 데이터 (첫 번째 행):")
                first_row = df.iloc[0]
                for col in columns:
                    value = first_row[col]
                    # NaN 처리
                    if pd.isna(value):
                        value_str = "NULL"
                    elif isinstance(value, float):
                        value_str = f"{value:.2f}" if value < 1000 else f"{value:.0f}"
                    else:
                        value_str = str(value)
                    
                    # 긴 값은 자르기
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    
                    print(f"  - {col}: {value_str}")
        
        except Exception as e:
            print(f"\n❌ {table_name} 읽기 실패: {e}")
    
    print(f"\n{'=' * 100}")
    print(f"총 {len(tables)}개 테이블 분석 완료")
    print(f"{'=' * 100}")
    
    return tables

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    analyze_tables()
