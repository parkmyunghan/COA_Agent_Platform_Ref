
import pandas as pd
from pathlib import Path

def analyze_remaining_tables():
    data_lake = Path("data_lake")
    targets = [
        "전장축선.xlsx",
        "아군부대현황.xlsx",
        "아군가용자산.xlsx",
        "임무별_자원할당.xlsx"
    ]
    
    for target in targets:
        target_file = data_lake / target
        if not target_file.exists():
            print(f"\n[오류] 파일을 찾을 수 없습니다: {target}")
            continue

        try:
            df = pd.read_excel(target_file)
            print(f"\n=== {target} 분석 ===")
            print(f"전체 행 수: {len(df)}")
            print(f"컬럼 목록: {df.columns.tolist()}")
            
            print("\n[컬럼별 세부 분석]")
            for col in df.columns:
                unique_vals = df[col].dropna().unique()
                n_unique = len(unique_vals)
                sample = unique_vals[:5] if n_unique > 0 else []
                
                print(f"- {col}:")
                print(f"  타입: {df[col].dtype}")
                print(f"  결측치 수: {df[col].isnull().sum()}")
                if n_unique > 0:
                    print(f"  샘플: {sample}")
        except Exception as e:
            print(f"[오류] {target} 분석 실패: {e}")

if __name__ == "__main__":
    analyze_remaining_tables()
