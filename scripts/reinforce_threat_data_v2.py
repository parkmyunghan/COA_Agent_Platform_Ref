import pandas as pd
import os

file_path = r"c:\POC\COA_Agent_Platform\data_lake\위협상황.xlsx"

def reinforce_data():
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        df = pd.read_excel(file_path)
        print("Original Columns:", df.columns.tolist())

        # 매핑 데이터 정의
        threat_type_map = {
            'THR001': '정면공격',
            'THR002': '침투',
            'THR003': '집결징후',
            'THR004': '침투',
            'THR005': '정밀타격',
            'THR006': '공중위협',
            'THR007': '화생방공격',
            'THR008': '사이버',
            'THR009': '국지도발',
            'THR010': '전면전'
        }

        mission_type_map = {
            'THR001': '방어',
            'THR002': '후방지역작전',
            'THR003': '감시정찰',
            'THR004': '해안경계',
            'THR005': '방호',
            'THR006': '방공',
            'THR007': '제독',
            'THR008': '방호',
            'THR009': '초동조치',
            'THR010': '방어'
        }

        # 컬럼 추가 또는 업데이트
        # 위협유형
        if '위협유형' not in df.columns:
            print("Adding '위협유형' column...")
            df['위협유형'] = df['위협ID'].map(threat_type_map).fillna('기타')
        else:
             print("Updating '위협유형' column...")
             df['위협유형'] = df['위협ID'].map(threat_type_map).fillna(df['위협유형'])

        # 임무유형
        if '임무유형' not in df.columns:
            print("Adding '임무유형' column...")
            df['임무유형'] = df['위협ID'].map(mission_type_map).fillna('방어')
        else:
            print("Updating '임무유형' column...")
            df['임무유형'] = df['위협ID'].map(mission_type_map).fillna(df['임무유형'])

        # 자원 가용성 (예시 데이터)
        if '자원가용성' not in df.columns:
            print("Adding '자원가용성' column...")
            df['자원가용성'] = 0.8 # 기본값 80%

        # 환경 (기상, 지형, 시간) - 예시
        if '기상' not in df.columns:
             print("Adding '기상' column...")
             df['기상'] = '맑음'
        if '지형' not in df.columns:
             print("Adding '지형' column...")
             df['지형'] = '평지'
        if '시간' not in df.columns:
             print("Adding '시간' column...")
             df['시간'] = '주간'

        # 저장
        df.to_excel(file_path, index=False)
        print("File updated successfully.")
        print("New Columns:", df.columns.tolist())
        print(df[['위협ID', '위협유형', '임무유형', '자원가용성']].head())

    except Exception as e:
        print(f"Error processing excel: {e}")

if __name__ == "__main__":
    reinforce_data()
