import json
from pathlib import Path

def extract_coastline(input_file, output_file):
    print(f"Extracting coastline from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    coastline_features = []
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        if props.get('natural') == 'coastline' or props.get('place') in ['island', 'islet']:
            coastline_features.append(feature)
            
    print(f"Found {len(coastline_features)} coastline features.")
    
    output_data = {
        "type": "FeatureCollection",
        "features": coastline_features
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
        
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    extract_coastline(
        Path('c:/POC/COA_Agent_Platform/data/maps/korea_osm.geojson.backup'),
        Path('c:/POC/COA_Agent_Platform/data/maps/korea_detailed_coastline.geojson')
    )
