
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def generate_correction_report():
    print("=== 위협 데이터 정제 가이드 생성 ===")
    
    # 1. 파일 경로 설정
    data_lake = Path("data_lake")
    files = {
        'Master': data_lake / '위협유형_마스터.xlsx',
        'Situation': data_lake / '위협상황.xlsx',
        'Relevance': data_lake / '방책유형_위협유형_관련성.xlsx'
    }
    
    # 2. 마스터 데이터 로드 (기준)
    if not files['Master'].exists():
        print("❌ 마스터 파일이 없습니다.")
        return
        
    master_df = pd.read_excel(files['Master'])
    name_to_code = {}
    
    print(f"\n[1] 마스터 데이터 로드 ({len(master_df)}건)")
    for _, row in master_df.iterrows():
        code = str(row.get('위협유형코드', '')).strip()
        name = str(row.get('위협유형명', '')).strip()
        if code and name:
            name_to_code[name] = code
            print(f"  - {name} -> {code}")
            
    # 3. 위협상황 파일 분석
    print(f"\n[2] 위협상황.xlsx 분석")
    if files['Situation'].exists():
        sit_df = pd.read_excel(files['Situation'])
        corrections = []
        
        for idx, row in sit_df.iterrows():
            curr_val = str(row.get('위협유형코드', '')).strip()
            # 이미 코드가 아니고, 이름이 마스터에 있다면
            if not curr_val.startswith('THR_TYPE_') and curr_val in name_to_code:
                new_code = name_to_code[curr_val]
                corrections.append({
                    'Row': idx + 2, # 엑셀 행 번호 (헤더 포함)
                    'Current': curr_val,
                    'Suggested': new_code
                })
        
        if corrections:
            print(f"⚠️ {len(corrections)}건의 수정 필요 항목 발견!")
            print("   (위협유형코드 컬럼을 아래 값으로 변경하세요)")
            for c in corrections[:5]:
                print(f"   - 행 {c['Row']}: '{c['Current']}' -> '{c['Suggested']}'")
            if len(corrections) > 5:
                print(f"   ... 외 {len(corrections)-5}건")
        else:
            print("✅ 수정할 항목이 없습니다 (모두 코드 형식이거나 매핑 불가).")
    else:
        print("❌ 파일 없음")

    # 4. 관련성 파일 분석
    print(f"\n[3] 방책유형_위협유형_관련성.xlsx 분석")
    if files['Relevance'].exists():
        rel_df = pd.read_excel(files['Relevance'])
        corrections = []
        target_col = 'threat_type' # 영문 컬럼명 확인됨
        
        if target_col in rel_df.columns:
            for idx, row in rel_df.iterrows():
                curr_val = str(row.get(target_col, '')).strip()
                if not curr_val.startswith('THR_TYPE_') and curr_val in name_to_code:
                    new_code = name_to_code[curr_val]
                    corrections.append({
                        'Row': idx + 2,
                        'Current': curr_val,
                        'Suggested': new_code
                    })
            
            if corrections:
                print(f"⚠️ {len(corrections)}건의 수정 필요 항목 발견!")
                print("   (threat_type 컬럼을 아래 값으로 변경하세요)")
                for c in corrections[:5]:
                    print(f"   - 행 {c['Row']}: '{c['Current']}' -> '{c['Suggested']}'")
                if len(corrections) > 5:
                    print(f"   ... 외 {len(corrections)-5}건")
            else:
                print("✅ 수정할 항목이 없습니다.")
        else:
            print(f"❌ '{target_col}' 컬럼을 찾을 수 없습니다.")
    else:
        print("❌ 파일 없음")

    print("\n[안내] 위 내용은 제안 사항이며, 시스템은 현재 상태로도 정상 작동하도록 패치되었습니다.")

if __name__ == "__main__":
    generate_correction_report()
