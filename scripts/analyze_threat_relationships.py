
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_threat_relationships():
    print("=== 위협 데이터 관계 분석 (PK-FK) ===\n")
    
    # 1. 파일 로드
    files = {
        'Master': 'data_lake/위협유형_마스터.xlsx',
        'Situation': 'data_lake/위협상황.xlsx',
        'Relevance': 'data_lake/방책유형_위협유형_관련성.xlsx'
    }
    
    dfs = {}
    for key, path in files.items():
        try:
            if Path(path).exists():
                dfs[key] = pd.read_excel(path)
                print(f"[{key}] 로드 성공 ({len(dfs[key])}행)")
            else:
                print(f"[{key}] 파일 없음: {path}")
        except Exception as e:
            print(f"[{key}] 로드 실패: {e}")
            
    if len(dfs) < 3:
        print("모든 파일을 로드하지 못해 분석을 중단합니다.")
        return

    # 2. Key 컬럼 값 비교
    print("\n--- Key 값 샘플 비교 ---")
    
    # Master (PK)
    master_codes = set(dfs['Master']['위협유형코드'].astype(str))
    master_names = set(dfs['Master']['위협유형명'].astype(str))
    print(f"[Master] 위협유형코드 (PK): {list(master_codes)[:5]} ...")
    print(f"[Master] 위협유형명: {list(master_names)[:5]} ...")
    
    # Situation (FK?)
    sit_codes = dfs['Situation']['위협유형코드'].astype(str).unique()
    print(f"\n[Situation] 위협유형코드 (FK추정): {list(sit_codes)[:5]} ...")
    
    # Relevance (FK?)
    # 관련성 테이블의 컬럼명 확인 필요
    # Relevance (FK?)
    rel_cols = dfs['Relevance'].columns.tolist()
    print(f"\n[Relevance] 컬럼 목록: {rel_cols}")
    
    # 영문으로 된 threat_type 컬럼 확인
    target_col = 'threat_type'
    if target_col in rel_cols:
        rel_vals = dfs['Relevance'][target_col].astype(str).unique()
        print(f"[Relevance] {target_col} 값: {list(rel_vals)[:5]} ...")
        
        # 3. 매칭률 분석
        print("\n--- 매칭률 분석 (PK: Master Code) ---")
        
        # Situation -> Master (Code)
        sit_code_match = [c for c in sit_codes if c in master_codes]
        sit_name_match = [c for c in sit_codes if c in master_names]
        print(f"[Situation -> Master]")
        print(f"  - 코드로 매칭: {len(sit_code_match)} / {len(sit_codes)} ({sit_code_match[:3]}...)")
        print(f"  - 이름으로 매칭: {len(sit_name_match)} / {len(sit_codes)} ({sit_name_match[:3]}...)")
        
        # Relevance -> Master (Code)
        rel_code_match = [c for c in rel_vals if c in master_codes]
        rel_name_match = [c for c in rel_vals if c in master_names]
        print(f"[Relevance -> Master]")
        print(f"  - 코드로 매칭: {len(rel_code_match)} / {len(rel_vals)} ({rel_code_match[:3]}...)")
        print(f"  - 이름으로 매칭: {len(rel_name_match)} / {len(rel_vals)} ({rel_name_match[:3]}...)")
    else:
        print(f"\n[Relevance] '{target_col}' 컬럼을 찾을 수 없습니다.")

if __name__ == "__main__":
    analyze_threat_relationships()
