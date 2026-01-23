import pandas as pd
import os

# 현재 파일 읽기
file_path = "c:\\POC\\(NEW)Defense_Intelligent_Agent_Platform\\data_lake\\평가기준_가중치.xlsx"
df = pd.read_excel(file_path)

print("현재 데이터:")
print(df)
print()

# 새로운 row 추가
new_row = {
    '기준ID': 'C007',
    '평가요소': 'mission_alignment',
    '가중치': 0.20,
    '설명': '임무 타입과 방책 타입의 부합성 (공격임무-공격방책)'
}

# 기존 가중치 조정
df.loc[df['평가요소'] == 'threat', '가중치'] = 0.20
df.loc[df['평가요소'] == 'resources', '가중치'] = 0.15
df.loc[df['평가요소'] == 'assets', '가중치'] = 0.12
df.loc[df['평가요소'] == 'environment', '가중치'] = 0.12
df.loc[df['평가요소'] == 'historical', '가중치'] = 0.12
df.loc[df['평가요소'] == 'chain', '가중치'] = 0.09

# mission_alignment이 없으면 추가
if 'mission_alignment' not in df['평가요소'].values:
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

print("\n업데이트 후:")
print(df)
print(f"\n총 가중치 합계: {df['가중치'].sum():.2f}")

# 저장
df.to_excel(file_path, index=False)
print(f"\n✅ 파일 저장 완료: {file_path}")
