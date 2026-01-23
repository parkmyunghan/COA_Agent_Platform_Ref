"""
Week 2 Day 3: 추천 이유 생성 기능 검증 테스트

이 스크립트는:
1. EnhancedDefenseCOAAgent 인스턴스 생성 (Mock CorePipeline 사용)
2. 가상의 방책 데이터(reasoning 포함) 준비
3. _generate_recommendation_reason 메서드 호출
4. 생성된 자연어 추천 이유 검증
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))
sys.path.insert(0, str(BASE_DIR / "agents"))

os.chdir(BASE_DIR)

from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent

def main():
    print("=" * 60)
    print("Week 2: 추천 이유 생성 기능 검증")
    print("=" * 60)
    print()
    
    # 1. Agent 초기화 (Mock CorePipeline)
    print("[1/3] Agent 초기화...")
    mock_core = MagicMock()
    agent = EnhancedDefenseCOAAgent(mock_core)
    print("   초기화 완료")
    print()
    
    # 2. 테스트 데이터 준비
    print("[2/3] 테스트 데이터 준비...")
    
    # Case 1: Reasoning 로그가 있는 경우
    strategy_with_reasoning = {
        'name': 'Test Strategy 1',
        'reasoning': [
            {'factor': 'threat', 'weighted_score': 0.25, 'reason': '위협 수준 90%에 대한 대응 점수'},
            {'factor': 'resources', 'weighted_score': 0.15, 'reason': '자원 가용성 80% 반영'},
            {'factor': 'assets', 'weighted_score': 0.10, 'reason': '가용 방어 자산 5개의 평균 능력치 반영'}
        ]
    }
    
    # Case 2: Reasoning 로그가 없는 경우
    strategy_without_reasoning = {
        'name': 'Test Strategy 2',
        'agent_score': 0.85
    }
    
    situation_info = {
        'threat_level': 0.9
    }
    
    # 3. 검증 실행
    print("[3/3] 추천 이유 생성 및 검증...")
    
    # Case 1 검증
    reason1 = agent._generate_recommendation_reason(strategy_with_reasoning, situation_info)
    print(f"   Case 1 (Reasoning 있음): {reason1}")
    
    if "위협 수준 90%" in reason1 and "자원 가용성 80%" in reason1:
        print("   ✅ Case 1 통과")
    else:
        print("   ❌ Case 1 실패")
        
    # Case 2 검증
    reason2 = agent._generate_recommendation_reason(strategy_without_reasoning, situation_info)
    print(f"   Case 2 (Reasoning 없음): {reason2}")
    
    if "위협 수준 90%" in reason2 and "높은 적합도" in reason2:
        print("   ✅ Case 2 통과")
    else:
        print("   ❌ Case 2 실패")
    
    print()
    print("=" * 60)
    return True

if __name__ == "__main__":
    main()
