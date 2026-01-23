import os
import requests
import json

# URL for South Korea GeoJSON (South Korea Provinces)
# Source: https://github.com/southkorea/southkorea-maps
GEOJSON_URL = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea_provinces_2018_geo.json"

TARGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "maps")
TARGET_FILE = os.path.join(TARGET_DIR, "korea_provinces.geojson")

def download_geojson():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        
    print(f"Downloading Korea GeoJSON from {GEOJSON_URL}...")
    try:
        response = requests.get(GEOJSON_URL)
        response.raise_for_status()
        
        # Save formatted JSON
        data = response.json()
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            
        print(f"Successfully saved to {TARGET_FILE}")
        print("This file can be loaded by the Tactical Map component as a base layer.")
        
    except Exception as e:
        print(f"Error downloading GeoJSON: {e}")

if __name__ == "__main__":
    download_geojson()
