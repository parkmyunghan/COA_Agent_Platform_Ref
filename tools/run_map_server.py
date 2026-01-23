from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_LIB_DIR = os.path.join(BASE_DIR, "ui", "static", "lib")
TILE_DIR_DARK = os.path.join(BASE_DIR, "data", "tiles", "dark")
TILE_DIR_SAT = os.path.join(BASE_DIR, "data", "tiles", "sat")

app = FastAPI()

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories
# 1. JS/CSS Libraries
if os.path.exists(STATIC_LIB_DIR):
    app.mount("/static/lib", StaticFiles(directory=STATIC_LIB_DIR), name="lib")
else:
    print(f"Warning: {STATIC_LIB_DIR} not found. Run setup_offline_assets.py first.")

# 2. Dynamic Tile Endpoints (for {z}/{x}/{y}.png structure)
@app.get("/tiles/dark/{z}/{x}/{y}.png")
async def get_dark_tile(z: int, x: int, y: int):
    """Serve dark mode map tiles from {z}/{x}/{y}.png structure"""
    tile_path = os.path.join(TILE_DIR_DARK, str(z), str(x), f"{y}.png")
    if os.path.exists(tile_path):
        return FileResponse(tile_path, media_type="image/png")
    raise HTTPException(status_code=404, detail=f"Tile not found: {z}/{x}/{y}.png")

@app.get("/tiles/sat/{z}/{x}/{y}.jpg")
async def get_sat_tile(z: int, x: int, y: int):
    """Serve satellite map tiles from {z}/{x}/{y}.jpg structure"""
    tile_path = os.path.join(TILE_DIR_SAT, str(z), str(x), f"{y}.jpg")
    if os.path.exists(tile_path):
        return FileResponse(tile_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail=f"Tile not found: {z}/{x}/{y}.jpg")

@app.get("/")
def health_check():
    return {
        "status": "ok", 
        "message": "COA Agent Map Server is running",
        "tiles_dark_available": os.path.exists(TILE_DIR_DARK),
        "tiles_sat_available": os.path.exists(TILE_DIR_SAT)
    }

if __name__ == "__main__":
    print(f"Starting Map Server on http://localhost:8080")
    print(f"Serving libraries from: {STATIC_LIB_DIR}")
    print(f"Serving tiles from: {TILE_DIR_DARK}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
