import pandas as pd

df = pd.read_excel('data_lake/제약조건.xlsx')
print('=== 우선순위별 제약조건 분석 ===\n')

for priority in sorted(df['우선순위'].unique()):
    subset = df[df['우선순위'] == priority]
    print(f'우선순위 {priority}:')
    for _, row in subset.iterrows():
        print(f'  - {row["제약ID"]}: {row["제약유형"]} - {row["제약내용"]}')
    print()
