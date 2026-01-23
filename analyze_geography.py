import pandas as pd
import os

# Define paths
axis_path = "data_lake/전장축선.xlsx"
terrain_path = "data_lake/지형셀.xlsx"

if not os.path.exists(axis_path) or not os.path.exists(terrain_path):
    print("Files not found.")
    exit(1)

# Load data
df_axis = pd.read_excel(axis_path)
df_terrain = pd.read_excel(terrain_path)

# Filter for Western Supporting Axis (서부 조공)
axis_id = "AXIS04"
axis_data = df_axis[df_axis['축선ID'] == axis_id]

if axis_data.empty:
    print(f"Axis {axis_id} not found.")
    exit(1)

axis = axis_data.iloc[0]
print(f"--- Analysis for {axis['축선명']} ({axis_id}) ---")

# Get start and end IDs
start_id = axis['시작지형셀ID']
end_id = axis['종단지형셀ID']

# Function to get cell details
def get_cell_details(cell_id):
    row = df_terrain[df_terrain['지형셀ID'] == cell_id]
    if row.empty:
        return f"{cell_id} not found"
    
    cell = row.iloc[0]
    name = cell['지형명']
    # Find coordinate column
    coord_col = [c for c in df_terrain.columns if '좌표' in c][0]
    coord_val = cell[coord_col]
    return f"{cell_id} ({name}) at {coord_val}"

print(f"Start: {get_cell_details(start_id)}")
print(f"End:   {get_cell_details(end_id)}")

# Sample other points for context (e.g. TERR001 which is probably West/Central)
print("\n--- Reference Points ---")
ref_points = ['TERR001', 'TERR005', 'TERR015', 'TERR025']
for rp in ref_points:
    print(f"Ref: {get_cell_details(rp)}")
