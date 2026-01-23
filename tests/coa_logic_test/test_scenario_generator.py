
import random
from datetime import datetime

class TestScenarioGenerator:
    """COA 로직 테스트를 위한 다양한 시나리오 생성기"""

    THREAT_TYPES = [
        "기습공격", "정면공격", "측면공격", "포위공격", 
        "지속공격", "정밀타격", "사이버공격", "화생방공격", 
        "집결징후", "침투", "포격", "국지도발", "전면전", "공중위협", "해상위협"
    ]

    THREAT_LEVELS = [
        (0.2, "Low"),
        (0.5, "Medium"),
        (0.8, "High"),
        (1.0, "Critical")
    ]

    LOCATIONS = ["전방기지", "후방기지", "해안가", "국경지대", "주요도시", "보급로"]

    ENVIRONMENT_CONDITIONS = [
        {"weather": "Clear", "terrain": "Flat"},
        {"weather": "Rain", "terrain": "Muddy"},
        {"weather": "Fog", "terrain": "Mountainous"},
        {"weather": "Storm", "terrain": "Complex"}
    ]

    AVAILABLE_ASSETS = [
         {"name": "1기갑여단", "type": "Armor", "capability": 0.9},
         {"name": "2보병사단", "type": "Infantry", "capability": 0.7},
         {"name": "3포병여단", "type": "Artillery", "capability": 0.8},
         {"name": "특전사팀", "type": "SpecialForces", "capability": 0.9},
         {"name": "사이버대응팀", "type": "Cyber", "capability": 0.8},
         {"name": "방공대대", "type": "AirDefense", "capability": 0.7}
    ]

    def generate_scenarios(self, num_scenarios=20):
        """다양한 조합의 테스트 시나리오 생성"""
        scenarios = []
        for i in range(num_scenarios):
            # Random selections
            threat_type = random.choice(self.THREAT_TYPES)
            threat_level_val, threat_level_label = random.choice(self.THREAT_LEVELS)
            location = random.choice(self.LOCATIONS)
            env = random.choice(self.ENVIRONMENT_CONDITIONS)
            
            # Asset selection (random subset)
            num_assets = random.randint(1, 4)
            assets = random.sample(self.AVAILABLE_ASSETS, num_assets)
            
            situation_info = {
                "situation_id": f"TEST_SCENARIO_{i+1:03d}",
                "위협유형": threat_type,
                "threat_type": threat_type, # 영문 키도 추가
                "threat_level": threat_level_val,
                "위협수준": threat_level_label, # 문자열 레이블
                "발생장소": location,
                "location": location,
                "environment": env,
                "defense_assets": assets,
                "enemy_units": f"Enemy Force for {threat_type}",
                "timestamp": datetime.now().isoformat(),
                "description": f"{location}에서 {threat_type} 발생. 위협수준 {threat_level_label}."
            }
            scenarios.append(situation_info)
        
        return scenarios

if __name__ == "__main__":
    gen = TestScenarioGenerator()
    scenarios = gen.generate_scenarios(5)
    for s in scenarios:
        print(s)
