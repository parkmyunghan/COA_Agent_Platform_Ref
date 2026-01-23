"""
COA Scorer RelevanceMapper 통합 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.coa_scorer import COAScorer

def test_relevance_mapper_integration():
    """RelevanceMapper 통합 테스트"""
    
    print("=" * 80)
    print("COAScorer + RelevanceMapper 통합 테스트")
    print("=" * 80)
    
    # 1. COAScorer 초기화
    print("\n1. COAScorer 초기화...")
    scorer = COAScorer(coa_type="defense")
    
    # RelevanceMapper 초기화 확인
    has_mapper = hasattr(scorer, 'relevance_mapper') and scorer.relevance_mapper is not None
    print(f"   RelevanceMapper 초기화: {'✅ 성공' if has_mapper else '❌ 실패'}")
    
    if has_mapper:
        stats = scorer.relevance_mapper.get_type_mapping_stats()
        print(f"   매핑 로드: {stats['total_mappings']}개")
        print(f"   COA 유형: {stats['coa_types']}")
        print(f"   위협 유형: {stats['threat_types']}")
    
    # 2. 체인 점수 계산 테스트
    print(f"\n2. 체인 점수 계산 테스트...")
    
    test_contexts = [
        {
            'name': 'Defense + 침투',
            'context': {
                'coa_type': 'Defense',
                'coa_id': 'COA_DEF_002',
                'threat_type': '침투',
                'threat_id': 'THR001',
                'situation_id': 'MSN008',
                'is_first_coa': True,
                'chain_info': {
                    'chains': [
                        {'path': 'chain1', 'avg_confidence': 0.7},
                        {'path': 'chain2', 'avg_confidence': 0.8},
                        {'path': 'chain3', 'avg_confidence': 0.6},
                    ]
                }
            },
            'expected': '> 0.5'
        },
        {
            'name': 'Offensive + 침투',
            'context': {
                'coa_type': 'Offensive',
                'coa_id': 'COA_OFF_005',
                'threat_type': '침투',
                'threat_id': 'THR001',
                'is_first_coa': False,
                'chain_info': {
                    'chains': [
                        {'path': 'chain1', 'avg_confidence': 0.6},
                    ]
                }
            },
            'expected': '< 0.6'
        },
        {
            'name': 'Preemptive + 포격',
            'context': {
                'coa_type': 'Preemptive',
                'coa_id': 'COA_PRE_003',
                'threat_type': '포격',
                'threat_id': 'THR002',
                'is_first_coa': False,
                'chain_info': {
                    'chains': [
                        {'path': 'chain1', 'avg_confidence': 0.8},
                        {'path': 'chain2', 'avg_confidence': 0.9},
                    ]
                }
            },
            'expected': '> 0.7'
        },
    ]
    
    for test_case in test_contexts:
        print(f"\n   테스트: {test_case['name']}")
        chain_score = scorer._calculate_chain_score(test_case['context'])
        print(f"   결과: {chain_score:.3f} (기대: {test_case['expected']})")
        
        # 검증
        if test_case['expected'].startswith('>'):
            threshold = float(test_case['expected'].split()[1])
            result = '✅ 통과' if chain_score > threshold else '❌ 실패'
        else:  # <
            threshold = float(test_case['expected'].split()[1])
            result = '✅ 통과' if chain_score < threshold else '❌ 실패'
        
        print(f"   검증: {result}")
    
    # 3. 전체 점수 계산 테스트
    print(f"\n3. 전체 점수 계산 테스트...")
    
    full_context = {
        'coa_uri': 'http://coa-agent-platform.org/ontology#COA_Library_COA_DEF_002',
        'coa_id': 'COA_DEF_002',
        'coa_type': 'Defense',
        'situation_id': 'MSN008',
        'threat_id': 'THR001',
        'threat_type': '침투',
        'threat_level': 0.8,
        'resource_availability': 0.7,
        'environment_fit': 0.9,
        'expected_success_rate': 0.65,
        'is_first_coa': True,
        'chain_info': {
            'chains': [
                {'path': 'chain1', 'avg_confidence': 0.7},
                {'path': 'chain2', 'avg_confidence': 0.8},
                {'path': 'chain3', 'avg_confidence': 0.9},
            ]
        },
        'mission_type': '방어',
    }
    
    result = scorer.calculate_score(full_context)
    
    print(f"\n   총점: {result['total']:.4f}")
    print(f"   세부 점수:")
    for key, value in result['breakdown'].items():
        print(f"     - {key}: {value:.3f}")
    
    print(f"\n   체인 점수 분석:")
    if result.get('reasoning'):
        for r in result['reasoning']:
            if 'chain' in r.lower() or '연계' in r.lower() or '관련' in r.lower():
                print(f"     {r}")
    
    # 개선 확인
    chain_score = result['breakdown'].get('chain', 0)
    if chain_score > 0.5:
        print(f"\n✅ 성공: 체인 점수가 {chain_score:.3f}로 개선되었습니다 (기존 0.00 → {chain_score:.3f})")
    else:
        print(f"\n⚠️ 주의: 체인 점수가 {chain_score:.3f}입니다")
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

if __name__ == "__main__":
    test_relevance_mapper_integration()
