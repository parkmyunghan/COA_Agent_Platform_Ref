"""
실제 에이전트 실행 테스트 스크립트
Phase 3.2: 로그 분석으로 문제점 재확인
"""
import sys
from pathlib import Path
import logging
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
log_file = f"logs/agent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def test_coa_scoring_with_improvements():
    """개선된 COA 점수 계산 테스트"""
    
    logger.info("=" * 80)
    logger.info("실제 에이전트 COA 평가 테스트 시작")
    logger.info("=" * 80)
    
    try:
        from core_pipeline.coa_scorer import COAScorer
        from core_pipeline.relevance_mapper import RelevanceMapper
        from core_pipeline.resource_priority_parser import ResourcePriorityParser
        from core_pipeline.situation_id_mapper import SituationIDMapper
        
        logger.info("✅ 모든 모듈 import 성공")
        
        # COAScorer 초기화
        scorer = COAScorer(coa_type="defense")
        logger.info(f"✅ COAScorer 초기화 완료")
        logger.info(f"   - RelevanceMapper: {'활성화' if hasattr(scorer, 'relevance_mapper') and scorer.relevance_mapper else '비활성화'}")
        logger.info(f"   - ResourcePriorityParser: {'활성화' if hasattr(scorer, 'resource_parser') and scorer.resource_parser else '비활성화'}")
        
        # 테스트 시나리오 구성
        test_scenarios = [
            {
                'name': 'MSN008 - Defense COA (침투 위협)',
                'context': {
                    'coa_uri': 'http://coa-agent-platform.org/ontology#COA_Library_COA_DEF_002',
                    'coa_id': 'COA_DEF_002',
                    'coa_type': 'Defense',
                    'situation_id': 'MSN008',
                    'threat_id': 'THR001',
                    'threat_type': '침투',
                    'threat_level': 0.8,
                    'mission_type': '방어',
                    'is_first_coa': True,
                    
                    # 체인 정보
                    'chain_info': {
                        'chains': [
                            {'path': 'chain1', 'avg_confidence': 0.7},
                            {'path': 'chain2', 'avg_confidence': 0.8},
                            {'path': 'chain3', 'avg_confidence': 0.9},
                        ]
                    },
                    
                    # 환경
                    'environment_fit': 0.9,
                    
                    # 과거 성공률
                    'expected_success_rate': 0.65,
                    
                    # 자원 (우선순위 기반)
                    'resource_priority_string': '포병대대(필수), 보병여단(필수), 전차중대(권장)',
                    'available_resources': [
                        {'resource_name': '포병대대', 'available_quantity': 18, 'status': '사용가능'},
                        {'resource_name': '보병여단', 'available_quantity': 3000, 'status': '사용가능'},
                        {'resource_name': '전차중대', 'available_quantity': 10, 'status': '정비중'},
                    ]
                }
            },
            {
                'name': 'MSN003 - Preemptive COA (기습공격)',
                'context': {
                    'coa_uri': 'http://coa-agent-platform.org/ontology#COA_Library_COA_PRE_001',
                    'coa_id': 'COA_PRE_001',
                    'coa_type': 'Preemptive',
                    'situation_id': 'MSN003',
                    'threat_id': 'THR002',
                    'threat_type': '기습공격',
                    'threat_level': 0.9,
                    'mission_type': '선제대응',
                    'is_first_coa': False,
                    
                    'chain_info': {
                        'chains': [
                            {'path': 'chain1', 'avg_confidence': 0.85},
                            {'path': 'chain2', 'avg_confidence': 0.90},
                        ]
                    },
                    
                    'environment_fit': 0.7,
                    'expected_success_rate': 0.75,
                    
                    'resource_priority_string': '정찰드론(필수), 특수전부대(필수), 포병대대(권장)',
                    'available_resources': [
                        {'resource_name': '정찰드론', 'available_quantity': 30, 'status': '사용가능'},
                        {'resource_name': '특수전부대', 'available_quantity': 800, 'status': '사용가능'},
                        {'resource_name': '포병대대', 'available_quantity': 36, 'status': '사용가능'},
                    ]
                }
            },
            {
                'name': 'MSN002 - InformationOps COA (사이버)',
                'context': {
                    'coa_uri': 'http://coa-agent-platform.org/ontology#COA_Library_COA_INF_001',
                    'coa_id': 'COA_INF_001',
                    'coa_type': 'InformationOps',
                    'situation_id': 'MSN002',
                    'threat_id': 'THR006',
                    'threat_type': '사이버',
                    'threat_level': 0.7,
                    'mission_type': '정보작전',
                    'is_first_coa': False,
                    
                    'chain_info': {
                        'chains': [
                            {'path': 'chain1', 'avg_confidence': 0.75},
                        ]
                    },
                    
                    'environment_fit': 1.0,
                    'expected_success_rate': 0.60,
                    
                    'resource_priority_string': '사이버전팀(필수), 정보부대(필수)',
                    'available_resources': [
                        {'resource_name': '사이버전팀', 'available_quantity': 50, 'status': '사용가능'},
                        {'resource_name': '정보부대', 'available_quantity': 400, 'status': '사용가능'},
                    ]
                }
            }
        ]
        
        # 테스트 실행
        results = []
        for i, scenario in enumerate(test_scenarios, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"테스트 {i}/{len(test_scenarios)}: {scenario['name']}")
            logger.info(f"{'='*80}")
            
            context = scenario['context']
            result = scorer.calculate_score(context)
            
            # 결과 기록
            logger.info(f"\n📊 COA 평가 결과:")
            logger.info(f"   총점: {result['total']:.4f}")
            logger.info(f"   세부 점수:")
            for key, value in result['breakdown'].items():
                logger.info(f"     - {key}: {value:.3f}")
            
            # 특별히 개선된 점수 강조
            chain_score = result['breakdown'].get('chain', 0)
            resource_score = result['breakdown'].get('resources', 0)
            
            logger.info(f"\n✨ 개선 효과:")
            logger.info(f"   - 체인 점수: {chain_score:.3f} (Before: 0.00 → After: {chain_score:.3f})")
            logger.info(f"   - 자원 점수: {resource_score:.3f} (Before: 0.20 → After: {resource_score:.3f})")
            
            results.append({
                'scenario': scenario['name'],
                'total': result['total'],
                'chain': chain_score,
                'resources': resource_score,
                'breakdown': result['breakdown']
            })
        
        # 최종 요약
        logger.info(f"\n{'='*80}")
        logger.info(f"전체 테스트 요약")
        logger.info(f"{'='*80}")
        
        avg_total = sum(r['total'] for r in results) / len(results)
        avg_chain = sum(r['chain'] for r in results) / len(results)
        avg_resource = sum(r['resources'] for r in results) / len(results)
        
        logger.info(f"\n평균 점수:")
        logger.info(f"   - 총점: {avg_total:.4f}")
        logger.info(f"   - 체인: {avg_chain:.3f} (개선: +{avg_chain:.3f})")
        logger.info(f"   - 자원: {avg_resource:.3f} (개선: +{avg_resource - 0.2:.3f})")
        
        # 성공 여부 판단
        success = True
        if avg_chain < 0.5:
            logger.warning("   ⚠️ 체인 점수가 기대치보다 낮습니다")
            success = False
        if avg_resource < 0.4:
            logger.warning("   ⚠️ 자원 점수가 기대치보다 낮습니다")
            success = False
        
        if success:
            logger.info(f"\n✅ 모든 개선 사항이 정상 작동합니다!")
        else:
            logger.warning(f"\n⚠️ 일부 개선 사항 추가 검토 필요")
        
        logger.info(f"\n로그 파일: {log_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    test_coa_scoring_with_improvements()
