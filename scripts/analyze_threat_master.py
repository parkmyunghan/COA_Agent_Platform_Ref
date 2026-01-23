
import pandas as pd
from pathlib import Path

def analyze_threat_master():
    data_lake = Path("data_lake")
    target_file = data_lake / "위협유형_마스터.xlsx"
    
    if not target_file.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {target_file}")
        return

    try:
        # 데이터 로드
        df = pd.read_excel(target_file)
        print(f"\n=== 위협유형_마스터.xlsx 분석 ===")
        print(f"전체 행 수: {len(df)}")
        print(f"컬럼 목록: {df.columns.tolist()}")
        
        print("\n[컬럼별 세부 분석]")
        for col in df.columns:
            # 고유값 및 샘플 데이터 확인
            unique_vals = df[col].dropna().unique()
            n_unique = len(unique_vals)
            
            sample = unique_vals[:5] if n_unique > 0 else []
            
            print(f"- {col}:")
            print(f"  타입: {df[col].dtype}")
            print(f"  고유값 개수: {n_unique}")
            print(f"  결측치 수: {df[col].isnull().sum()}")
            if n_unique > 0:
                print(f"  샘플: {sample}")
            
    except Exception as e:
        print(f"[오류] 분석 중 예외 발생: {e}")

if __name__ == "__main__":
    analyze_threat_master()
