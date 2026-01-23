"""
Phase 1-2 통합 테스트
모든 개선사항이 실제 COA 점수 계산에 적용되는지 검증
"""
import sys
from pathlib import Path
import pandas as pd

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.coa_scorer import COAScorer
from core_pipeline.relevance_mapper import RelevanceMapper
from core_pipeline.resource_priority_parser import ResourcePriorityParser

def test_integration():
    """통합 테스트: Phase 1-2 모든 개선사항 검증"""
    
    print("=" * 100)
    print("Phase 1-2 통합 테스트 시작")
    print("=" * 100)
    
    # 1. 데이터 테이블 검증
    print("\n" + "=" * 100)
    print("1. 데이터 테이블 검증")
    print("=" * 100)
    
    data_lake = Path("data_lake")
    
    # 1-1. 위협유형 컬럼 확인
    print("\n[1-1] 위협상황.xlsx - 위협유형 컬럼")
    threat_df = pd.read_excel(data_lake / "위협상황.xlsx")
    if '위협유형' in threat_df.columns:
        print(f"  ✅ 위협유형 컬럼 존재")
        print(f"  - 위협 개수: {len(threat_df)}")
        print(f"  - 위협유형: {threat_df['위협유형'].unique().tolist()}")
    else:
        print(f"  ❌ 위협유형 컬럼 없음")
    
    # 1-2. 관련성 테이블 확인
    print("\n[1-2] 방책유형_위협유형_관련성.xlsx")
    try:
        relevance_df = pd.read_excel(data_lake / "방책유형_위협유형_관련성.xlsx")
        print(f"  ✅ 파일 존재")
        print(f"  - 매핑 개수: {len(relevance_df)}")
        print(f"  - COA 유형: {relevance_df['coa_type'].unique().tolist()}")
        print(f"  - 위협 유형: {relevance_df['threat_type'].unique().tolist()}")
        print(f"  - 평균 관련성: {relevance_df['base_relevance'].mean():.3f}")
    except FileNotFoundError:
        print(f"  ❌ 파일 없음")
    
    # 1-3. 가용자원 테이블 확인
    print("\n[1-3] 가용자원.xlsx")
    try:
        resource_df = pd.read_excel(data_lake / "가용자원.xlsx")
        print(f"  ✅ 파일 존재")
        print(f"  - 자원 개수: {len(resource_df)}")
        print(f"  - MSN008 자원: {len(resource_df[resource_df['situation_id'] == 'MSN008'])}")
        print(f"  - 사용가능: {len(resource_df[resource_df['status'] == '사용가능'])}")
    except FileNotFoundError:
        print(f"  ❌ 파일 없음")
    
    # 1-4. COA Library 신규 컬럼 확인
    print("\n[1-4] COA_Library.xlsx - 신규 컬럼")
    coa_df = pd.read_excel(data_lake / "COA_Library.xlsx")
    new_columns = ['적합위협유형', '자원우선순위', '전장환경_최적조건', '연계방책', '적대응전술']
    for col in new_columns:
        if col in coa_df.columns:
            print(f"  ✅ {col} 컬럼 존재")
        else:
            print(f"  ❌ {col} 컬럼 없음")
    
    # 2. 모듈 초기화 검증
    print("\n" + "=" * 100)
    print("2. 모듈 초기화 검증")
    print("=" * 100)
    
    # 2-1. RelevanceMapper
    print("\n[2-1] RelevanceMapper")
    try:
        mapper = RelevanceMapper()
        stats = mapper.get_type_mapping_stats()
        print(f"  ✅ 초기화 성공")
        print(f"  - 매핑 개수: {stats['total_mappings']}")
        print(f"  - 평균 관련성: {stats['avg_relevance']:.3f}")
    except Exception as e:
        print(f"  ❌ 초기화 실패: {e}")
    
    # 2-2. ResourcePriorityParser
    print("\n[2-2] ResourcePriorityParser")
    try:
        parser = ResourcePriorityParser()
        test_string = "포병대대(필수), 보병여단(권장), 공격헬기(선택)"
        parsed = parser.parse_resource_priority(test_string)
        print(f"  ✅ 초기화 성공")
        print(f"  - 파싱 테스트: {len(parsed)}개 자원 파싱됨")
        for p in parsed:
            print(f"    • {p['resource']} ({p['priority']}, 가중치={p['weight']})")
    except Exception as e:
        print(f"  ❌ 초기화 실패: {e}")
    
    # 2-3. COAScorer
    print("\n[2-3] COAScorer")
    try:
        scorer = COAScorer(coa_type="defense")
        has_relevance = hasattr(scorer, 'relevance_mapper') and scorer.relevance_mapper
        has_resource = hasattr(scorer, 'resource_parser') and scorer.resource_parser
        print(f"  ✅ 초기화 성공")
        print(f"  - RelevanceMapper 통합: {'✅' if has_relevance else '❌'}")
        print(f"  - ResourcePriorityParser 통합: {'✅' if has_resource else '❌'}")
    except Exception as e:
        print(f"  ❌ 초기화 실패: {e}")
    
    # 3. 점수 계산 테스트
    print("\n" + "=" * 100)
    print("3. COA 점수 계산 테스트 (Before vs After)")
    print("=" * 100)
    
    # 테스트용 컨텍스트 (MSN008 시나리오)
    test_context = {
        'coa_uri': 'http://coa-agent-platform.org/ontology#COA_Library_COA_DEF_002',
        'coa_id': 'COA_DEF_002',
        'coa_type': 'Defense',
        'situation_id': 'MSN008',
        'threat_id': 'THR001',
        'threat_type': '침투',
        'threat_level': 0.8,
        'is_first_coa': True,
        'mission_type': '방어',
        
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
        'resource_priority_string': '포병대대(필수), 보병여단(필수), 공격헬기(권장)',
        'available_resources': [
            {'resource_name': '포병대대', 'available_quantity': 18, 'status': '사용가능'},
            {'resource_name': '보병여단', 'available_quantity': 3000, 'status': '사용가능'},
            {'resource_name': '공격헬기', 'available_quantity': 8, 'status': '정비중'},
        ]
    }
    
    # COA 점수 계산
    print("\n테스트 시나리오: COA_DEF_002 (방어진지 구축)")
    print(f"  - 위협: {test_context['threat_type']} (레벨 {test_context['threat_level']})")
    print(f"  - 임무: {test_context['mission_type']}")
    
    result = scorer.calculate_score(test_context)
    
    print(f"\n총점: {result['total']:.4f}")
    print(f"\n세부 점수:")
    breakdown = result['breakdown']
    print(f"  - 위협 대응:    {breakdown.get('threat', 0):.3f}")
    print(f"  - 자원 가용성:  {breakdown.get('resources', 0):.3f}  ← ResourcePriorityParser")
    print(f"  - 환경 적합성:  {breakdown.get('environment', 0):.3f}")
    print(f"  - 과거 성공률:  {breakdown.get('historical', 0):.3f}")
    print(f"  - 체인 점수:    {breakdown.get('chain', 0):.3f}  ← RelevanceMapper")
    print(f"  - 임무 부합성:  {breakdown.get('mission_alignment', 0):.3f}")
    
    # 4. 개선 효과 분석
    print("\n" + "=" * 100)
    print("4. 개선 효과 분석")
    print("=" * 100)
    
    chain_score = breakdown.get('chain', 0)
    resource_score = breakdown.get('resources', 0)
    
    print(f"\n[체인 점수]")
    print(f"  - Before: 0.00 (고정, 로그 분석 확인)")
    print(f"  - After:  {chain_score:.3f}")
    if chain_score > 0.5:
        print(f"  ✅ 개선 성공! (+{chain_score:.3f})")
    else:
        print(f"  ⚠️ 추가 조사 필요")
    
    print(f"\n[자원 점수]")
    print(f"  - Before: 0.20 (fallback, 로그 분석 확인)")
    print(f"  - After:  {resource_score:.3f}")
    if resource_score > 0.5:
        print(f"  ✅ 개선 성공! (+{resource_score - 0.2:.3f})")
    else:
        print(f"  ⚠️ 추가 조사 필요")
    
    print(f"\n[총점 예상 개선]")
    # 가중치 적용 계산
    weights = scorer.get_weights()
    before_total = (
        0.8 * weights.get('threat', 0.2) +
        0.2 * weights.get('resources', 0.15) +  # Before: 0.2
        0.9 * weights.get('environment', 0.12) +
        0.65 * weights.get('historical', 0.12) +
        0.0 * weights.get('chain', 0.09) +  # Before: 0.0
        breakdown.get('mission_alignment', 0.5) * weights.get('mission_alignment', 0.2)
    )
    
    after_total = result['total']
    
    print(f"  - Before: {before_total:.4f} (추정)")
    print(f"  - After:  {after_total:.4f}")
    improvement = ((after_total - before_total) / before_total * 100) if before_total > 0 else 0
    print(f"  ✅ 개선율: +{improvement:.1f}%")
    
    # 5. 최종 요약
    print("\n" + "=" * 100)
    print("5. 최종 요약")
    print("=" * 100)
    
    checks = [
        ("위협유형 컬럼 추가", '위협유형' in threat_df.columns),
        ("관련성 테이블 생성", Path("data_lake/방책유형_위협유형_관련성.xlsx").exists()),
        ("가용자원 테이블 생성", Path("data_lake/가용자원.xlsx").exists()),
        ("COA Library 컬럼 추가", all(col in coa_df.columns for col in new_columns)),
        ("RelevanceMapper 작동", has_relevance),
        ("ResourcePriorityParser 작동", has_resource),
        ("체인 점수 개선", chain_score > 0.3),
        ("자원 점수 개선", resource_score > 0.4),
    ]
    
    passed = sum(1 for _, status in checks if status)
    total = len(checks)
    
    print(f"\n체크리스트: {passed}/{total} 통과\n")
    for name, status in checks:
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}")
    
    print(f"\n종합 평가:")
    if passed == total:
        print(f"  🎉 모든 테스트 통과! Phase 1-2 개선 완료.")
    elif passed >= total * 0.75:
        print(f"  ✅ 대부분 성공. 일부 항목 추가 작업 필요.")
    else:
        print(f"  ⚠️ 추가 작업 필요. 실패 항목 검토 요망.")
    
    print("\n" + "=" * 100)
    print("통합 테스트 완료")
    print("=" * 100)
    
    return {
        'passed': passed,
        'total': total,
        'improvement_rate': improvement,
        'chain_score': chain_score,
        'resource_score': resource_score,
        'total_score': after_total
    }

if __name__ == "__main__":
    try:
        results = test_integration()
        
        # 결과 저장
        print(f"\n결과를 저장합니다...")
        with open("logs/integration_test_results.txt", "w", encoding="utf-8") as f:
            f.write("Phase 1-2 통합 테스트 결과\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"통과: {results['passed']}/{results['total']}\n")
            f.write(f"개선율: +{results['improvement_rate']:.1f}%\n")
            f.write(f"체인 점수: {results['chain_score']:.3f}\n")
            f.write(f"자원 점수: {results['resource_score']:.3f}\n")
            f.write(f"총점: {results['total_score']:.4f}\n")
        
        print(f"✅ 결과 저장 완료: logs/integration_test_results.txt")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
