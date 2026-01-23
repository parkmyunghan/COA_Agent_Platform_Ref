import pandas as pd
import os

terrain_path = "data_lake/지형셀.xlsx"
df_terrain = pd.read_excel(terrain_path)
axis_path = "data_lake/전장축선.xlsx"
df_axis = pd.read_excel(axis_path)

with open("data_dump.txt", "w", encoding="utf-8") as f:
    f.write(f"--- TERRAIN DATA ---\n")
    f.write(f"Columns: {df_terrain.columns.tolist()}\n\n")
    for _, row in df_terrain.iterrows():
        f.write(f"{row['지형셀ID']} | {row['지형명']} | {row['좌표정보']}\n")
    
    f.write(f"\n--- AXIS DATA ---\n")
    f.write(f"Columns: {df_axis.columns.tolist()}\n\n")
    for _, row in df_axis.iterrows():
        f.write(f"{row['축선ID']} | {row['축선명']} | {row['시작지형셀ID']} -> {row['종단지형셀ID']}\n")

print("Done writing to data_dump.txt")
