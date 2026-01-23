import pandas as pd
import json

# Read terrain data
df_terrain = pd.read_excel('data_lake/지형셀.xlsx')
terrain_cols = df_terrain.columns.tolist()

# Read axis data  
df_axis = pd.read_excel('data_lake/전장축선.xlsx')
axis_cols = df_axis.columns.tolist()

# Find TERR002
terr_row = None
for col in df_terrain.columns:
    matches = df_terrain[df_terrain[col].astype(str) == 'TERR002']
    if not matches.empty:
        terr_row = matches.iloc[0].to_dict()
        break

# Find AXIS02
axis_row = None
for col in df_axis.columns:
    matches = df_axis[df_axis[col].astype(str) == 'AXIS02']
    if not matches.empty:
        axis_row = matches.iloc[0].to_dict()
        break

# Save as JSON
result = {
    "terrain_columns": terrain_cols,
    "axis_columns": axis_cols,
    "TERR002_data": terr_row,
    "AXIS02_data": axis_row
}

with open('data_check.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Data saved to data_check.json")
