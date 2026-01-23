"""
COA 데이터 표준화 및 업데이트 스크립트
COA_Library.xlsx에 '전면전' 대응 방책을 추가하고, 용어를 표준화합니다.
"""
import pandas as pd
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def update_coa_data():
    file_path = project_root / "data_lake" / "COA_Library.xlsx"
    print(f"📖 Loading {file_path}...")
    
    df = pd.read_excel(file_path)
    
    # 1. 신규 방책 추가: 전면전 대응
    new_coa = {
        "COA_ID": "COA_DEF_TW01",
        "명칭": "군단급 대규모 통합 방어",
        "방책유형": "Defense",
        "설명": "전면전 상황 발생 시, 가용 가능한 모든 군단급 화력 자산과 예비대를 통합 운용하여 적 전면 공격을 격퇴하고 반격 여건을 조성함.",
        "적용조건": "threat_level >= 0.8",
        "키워드": "전면전, 대규모, 통합방어",
        "필요자원": "기계화보병사단, 포병여단, 항공대대, 공병여단", # 구체적 자원
        "전장환경_제약": "없음",
        "워게임_모의_분석_승률": 0.85,
        "환경호환성": "평지,구릉지",
        "환경비호환성": "산지",
        "단계정보": "Phase 1",
        "주노력여부": "Y",
        "시각화스타일": "Heavy_Defense",
        "적합위협유형": "전면전, 기계화부대 공격", # 핵심 키워드 '전면전' 포함
        "자원우선순위": "기계화보병사단(필수), 포병여단(필수)",
        "전장환경_최적조건": "개활지",
        "연계방책": "COA_ATK_001(후행)",
        "적대응전술": "강행돌파"
    }
    
    # 중복 확인
    if "COA_DEF_TW01" not in df["COA_ID"].values:
        print("➕ Adding new COA: COA_DEF_TW01 (전면전 대응)")
        df = pd.concat([df, pd.DataFrame([new_coa])], ignore_index=True)
    else:
        print("⚠️ COA_DEF_TW01 already exists. Updating...")
        idx = df[df["COA_ID"] == "COA_DEF_TW01"].index
        for key, value in new_coa.items():
            df.loc[idx, key] = value

    # 2. 용어 표준화 (Optional)
    # 기존 '전면공격' -> '전면전' 매핑이 필요한 경우 처리 등
    # 여기서는 신규 추가에 집중
    
    # 저장
    print(f"💾 Saving to {file_path}...")
    df.to_excel(file_path, index=False)
    print("✅ Done.")

if __name__ == "__main__":
    update_coa_data()
