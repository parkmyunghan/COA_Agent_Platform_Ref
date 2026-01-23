import pandas as pd
import os

# Load axis table
df = pd.read_excel('data_lake/전장축선.xlsx')

ttl_content = "\n\n# ===========================================================================\n"
ttl_content += "# Axis Entity Instances (Refactored Object-Centric Model)\n"
ttl_content += "# ===========================================================================\n\n"

for idx, row in df.iterrows():
    axis_id = row['축선ID']
    axis_name = row['축선명']
    axis_type = row['축선유형']
    start_cell = row['시작지형셀ID']
    end_cell = row['종단지형셀ID']
    cell_path = row['주요지형셀목록']
    description = row.get('축선설명', '—')
    
    # Create ontology instance
    ttl_content += f"ns:{axis_id} a ns:전장축선 ;\n"
    ttl_content += f'    rdfs:label "{axis_name}" ;\n'
    ttl_content += f'    ns:축선유형 "{axis_type}" ;\n'
    ttl_content += f'    ns:시작지형셀 ns:{start_cell} ;\n'
    ttl_content += f'    ns:종단지형셀 ns:{end_cell} ;\n'
    ttl_content += f'    ns:주요지형셀목록 "{cell_path}" ;\n'
    
    if pd.isna(description) or description == '—':
        ttl_content += f'    ns:축선설명 "—" .\n\n'
    else:
        ttl_content += f'    ns:축선설명 "{description}" .\n\n'

# File path
instances_path = 'knowledge/ontology/instances.ttl'

# Append to file
with open(instances_path, 'a', encoding='utf-8') as f:
    f.write(ttl_content)

print(f"✅ Successfully appended {len(df)} axis instances to {instances_path}")
