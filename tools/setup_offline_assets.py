import os
import requests
import io
import math
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_LIB_DIR = os.path.join(BASE_DIR, "ui", "static", "lib")
TILE_DIR_DARK = os.path.join(BASE_DIR, "data", "tiles", "dark")
TILE_DIR_SAT = os.path.join(BASE_DIR, "data", "tiles", "sat")

# Resources to Download
LIBRARIES = {
    "leaflet.css": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
    "leaflet.js": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
    "milsymbol.js": "https://unpkg.com/milsymbol@2.0.0/dist/milsymbol.js",
    "react.production.min.js": "https://unpkg.com/react@18/umd/react.production.min.js",
    "react-dom.production.min.js": "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js",
    "babel.min.js": "https://unpkg.com/babel-standalone@6/babel.min.js"
}

# Map Tile Configuration (Full Korea Peninsula)
ZOOM_LEVELS = range(6, 12) # Zoom 6 to 11
LAT_RANGE = (33.0, 43.5)
LON_RANGE = (124.0, 132.0)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_file(url, path):
    try:
        if os.path.exists(path):
            print(f"Skipping existing: {os.path.basename(path)}")
            return
            
        print(f"Downloading: {url}...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(path, "wb") as f:
            f.write(response.content)
        print(f"Saved: {path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tile(zoom, x, y, tile_type="dark"):
    # CartoDB Dark Matter
    if tile_type == "dark":
        url = f"https://a.basemaps.cartocdn.com/dark_all/{zoom}/{x}/{y}.png"
        target_dir = os.path.join(TILE_DIR_DARK, str(zoom), str(x))
        filename = f"{y}.png"
    # Esri Satellite
    else:
        url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}"
        target_dir = os.path.join(TILE_DIR_SAT, str(zoom), str(x))
        filename = f"{y}.jpg" # Esri is usually JPG

    ensure_dir(target_dir)
    target_path = os.path.join(target_dir, filename)
    
    if os.path.exists(target_path):
        return # Skip
        
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if response.status_code == 200:
            with open(target_path, "wb") as f:
                f.write(response.content)
            # print(f"Tile {zoom}/{x}/{y} saved.")
        else:
            print(f"Failed {zoom}/{x}/{y}: {response.status_code}")
    except Exception as e:
        print(f"Error {zoom}/{x}/{y}: {e}")

def main():
    print("=== COA Agent Offline Assets Downloader ===")
    
    # 1. Download Libraries
    print("\n[1/3] Downloading JavaScript Libraries...")
    ensure_dir(STATIC_LIB_DIR)
    for name, url in LIBRARIES.items():
        download_file(url, os.path.join(STATIC_LIB_DIR, name))
        
    # 2. Download Dark Tiles
    print("\n[2/3] Downloading Map Tiles (Dark Mode)...")
    tasks = []
    
    total_tiles = 0
    for z in ZOOM_LEVELS:
        min_x, min_y = deg2num(LAT_RANGE[1], LAT_RANGE[0], z) # Top-Left
        max_x, max_y = deg2num(LAT_RANGE[0], LAT_RANGE[1], z) # Bottom-Right
        
        count = (max_x - min_x + 1) * (max_y - min_y + 1)
        total_tiles += count
        print(f"Zoom {z}: {count} tiles estimate.")

    print(f"Total tiles to verify/download: {total_tiles}")
    
    if input("Proceed with tile download? (y/n): ").lower() != 'y':
        print("Aborted.")
        return

    with ThreadPoolExecutor(max_workers=10) as executor:
        for z in ZOOM_LEVELS:
            min_x, min_y = deg2num(LAT_RANGE[1], LAT_RANGE[0], z)
            max_x, max_y = deg2num(LAT_RANGE[0], LAT_RANGE[1], z)
            
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    executor.submit(download_tile, z, x, y, "dark")
                    
    print("Download Complete.")

if __name__ == "__main__":
    main()
