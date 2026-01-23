"""
Generate axis entity instances for ontology
Based on 전장축선.xlsx data
"""
import pandas as pd

# Load axis table
df = pd.read_excel('data_lake/전장축선.xlsx')

print("# Axis Entity Instances for instances.ttl")
print("# Generated from 전장축선.xlsx")
print()

for idx, row in df.iterrows():
    axis_id = row['축선ID']
    axis_name = row['축선명']
    axis_type = row['축선유형']
    start_cell = row['시작지형셀ID']
    end_cell = row['종단지형셀ID']
    cell_path = row['주요지형셀목록']
    description = row.get('축선설명', '—')
    
    # Create ontology instance
    print(f"ns:{axis_id} a ns:전장축선 ;")
    print(f'    rdfs:label "{axis_name}" ;')
    print(f'    ns:축선유형 "{axis_type}" ;')
    print(f'    ns:시작지형셀 ns:{start_cell} ;')
    print(f'    ns:종단지형셀 ns:{end_cell} ;')
    print(f'    ns:주요지형셀목록 "{cell_path}" ;')
    
    if description and description != '—':
        print(f'    ns:축선설명 "{description}" .')
    else:
        print(f'    ns:축선설명 "—" .')
    
    print()

print("\n# Total:", len(df), "axis instances generated")
