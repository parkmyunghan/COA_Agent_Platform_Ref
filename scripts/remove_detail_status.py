# scripts/remove_detail_status.py
# -*- coding: utf-8 -*-
"""전체 파이프라인 상세 상태 섹션 제거"""
file_path = 'ui/components/pipeline_status.py'

with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Line 794부터 Line 828까지 제거 (st.divider()부터 마지막 st.info까지)
# Line 790: st.graphviz_chart(dot, width='stretch')
# Line 794-828: 제거할 부분

new_lines = []
skip_until_line = None

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Line 794부터 시작하는 divider와 상세 상태 섹션 제거
    if line_num == 794:
        # st.divider() 제거
        continue
    elif line_num >= 795 and line_num <= 828:
        # 상세 상태 표시 부분 모두 제거
        continue
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 전체 파이프라인 상세 상태 섹션 제거 완료")



