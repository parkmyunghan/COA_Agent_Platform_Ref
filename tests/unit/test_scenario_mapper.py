
import sys
import os
from pathlib import Path
import json

# 프로젝트 루트 경로 추가
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ui.components.scenario_mapper import ScenarioMapper

def test_mapper():
    print("Testing ScenarioMapper...")
    
    # 1. 위협 데이터 테스트
    threats = [
        {"name": "개성 장사정포 부대", "type": "Artillery", "radius_km": 15},
        {"name": "철원 인근 보병 사단", "type": "Infantry", "radius_km": 10},
        {"name": "원산 미사일 기지", "type": "Missile", "radius_km": 30}
    ]
    
    threat_geojson = ScenarioMapper.map_threats_to_geojson(threats)
    print(f"Threat GeoJSON Features: {len(threat_geojson['features'])}")
    
    for f in threat_geojson['features']:
        print(f"- {f['properties']['name']}: {f['properties']['sidc']} at {f['geometry']['coordinates']}")
        if f['properties']['name'] == "개성 장사정포 부대":
             assert "126.5" in str(f['geometry']['coordinates'][0]) # 개성 인근
        if "미사일" in f['properties']['name']:
             assert f['properties']['sidc'] == "SHGPEWM---H----" # RED_MISSILE
             
    # 2. 방책 데이터 테스트
    coa = {
        "name": "공중 선제 타격",
        "type": "preemptive",
        "coa_name": "강릉 공중 대응"
    }
    
    coa_geojson = ScenarioMapper.map_coa_to_geojson(coa, threat_geojson)
    print(f"COA GeoJSON Features: {len(coa_geojson['features'])}")
    
    for f in coa_geojson['features']:
        print(f"- {f['properties'].get('name', 'Path')}: {f['properties'].get('sidc', 'N/A')} ({f['geometry']['type']})")
        if f['properties'].get('name') == "제18전투비행단":
             print("  ✅ 강릉 비행단 올바르게 매핑됨")

    print("\n✅ ScenarioMapper Test Completed Successfully!")

if __name__ == "__main__":
    test_mapper()
