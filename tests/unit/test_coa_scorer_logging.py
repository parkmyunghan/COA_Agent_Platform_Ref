"""
Week 2 Day 1-2: COAScorer 로깅 기능 검증 테스트

이 스크립트는:
1. COAScorer 인스턴스 생성
2. 가상의 컨텍스트로 점수 계산
3. reasoning 로그가 정상적으로 생성되는지 검증
4. 각 요소별 설명이 올바른지 확인
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core_pipeline"))

os.chdir(BASE_DIR)

from core_pipeline.coa_scorer import COAScorer

def main():
    print("=" * 60)
    print("Week 2: COAScorer 로깅 기능 검증")
    print("=" * 60)
    print()
    
    # 1. COAScorer 초기화 (기본 가중치 사용)
    print("[1/3] COAScorer 초기화...")
    scorer = COAScorer(coa_type="defense")
    print("   초기화 완료")
    print()
    
    # 2. 테스트 컨텍스트 준비
    context = {
        'threat_level': 85,  # 위협 수준 85%
        'resource_availability': 0.7,  # 자원 가용성 70%
        'defense_assets': [{'firepower': 80, 'morale': 90}],  # 자산 정보
        'environment_compatible': True,  # 환경 적합
        'historical_success': 0.65,  # 과거 성공률 65%
        'chain_bonus': 0.1  # 연계 보너스
    }
    
    # 3. 점수 계산 및 검증
    print("[2/3] 점수 계산 실행...")
    result = scorer.calculate_score(context)
    
    print(f"   총점: {result['total']}")
    print(f"   세부 점수: {result['breakdown']}")
    print()
    
    print("[3/3] Reasoning 로그 검증...")
    reasoning = result.get('reasoning')
    
    if not reasoning:
        print("   ❌ Reasoning 로그가 없습니다!")
        return False
    
    print(f"   로그 항목 수: {len(reasoning)}개")
    
    all_passed = True
    for item in reasoning:
        factor = item['factor']
        reason = item['reason']
        score = item['score']
        
        print(f"   - [{factor}] 점수: {score}, 이유: {reason}")
        
        # 검증 로직
        if factor == 'threat' and "85%" not in reason:
            print(f"     ❌ 위협 수준 설명 오류: {reason}")
            all_passed = False
        elif factor == 'resources' and "70%" not in reason:
            print(f"     ❌ 자원 가용성 설명 오류: {reason}")
            all_passed = False
        elif factor == 'environment' and "적합" not in reason:
            print(f"     ❌ 환경 적합성 설명 오류: {reason}")
            all_passed = False
    
    print()
    if all_passed:
        print("✅ 모든 검증 통과!")
    else:
        print("❌ 일부 검증 실패")
    
    print("=" * 60)
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
