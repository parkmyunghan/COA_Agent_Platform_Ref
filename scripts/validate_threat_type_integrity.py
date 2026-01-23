"""
위협 유형 참조 무결성 검증 스크립트
"""
import pandas as pd
from pathlib import Path

def validate_threat_type_integrity():
    """위협 유형 참조 무결성 검증"""
    
    print("=" * 80)
    print("위협 유형 참조 무결성 검증")
    print("=" * 80)
    
    # 1. 데이터 로드
    threats = pd.read_excel('data_lake/위협상황.xlsx')
    relevance = pd.read_excel('data_lake/방책유형_위협유형_관련성.xlsx')
    
    # 2. 위협 유형 추출
    threat_types = set(threats['위협유형코드'].dropna().unique())
    relevance_types = set(relevance['threat_type'].dropna().unique())
    
    # 3. 차이 분석
    missing_in_relevance = threat_types - relevance_types
    extra_in_relevance = relevance_types - threat_types
    common_types = threat_types & relevance_types
    
    # 4. 결과 출력
    print(f"\n📊 통계:")
    print(f"  - 위협상황 위협 유형: {len(threat_types)}개")
    print(f"  - 관련성 테이블 위협 유형: {len(relevance_types)}개")
    print(f"  - 공통 위협 유형: {len(common_types)}개")
    
    print(f"\n위협상황 위협 유형:")
    for t in sorted(threat_types):
        print(f"  - {t}")
    
    print(f"\n관련성 테이블 위협 유형:")
    for t in sorted(relevance_types):
        print(f"  - {t}")
    
    if missing_in_relevance:
        print(f"\n⚠️ 관련성 테이블에 누락된 위협 유형:")
        for t in sorted(missing_in_relevance):
            print(f"  - {t}")
            # 해당 위협이 사용된 위협상황 찾기
            threat_rows = threats[threats['위협유형코드'] == t]
            print(f"    사용처: {', '.join(threat_rows['위협ID'].astype(str).tolist())}")
    else:
        print(f"\n✅ 모든 위협 유형이 관련성 테이블에 존재합니다.")
    
    if extra_in_relevance:
        print(f"\n⚠️ 관련성 테이블에만 존재하는 위협 유형 (사용되지 않음):")
        for t in sorted(extra_in_relevance):
            print(f"  - {t}")
    
    # 5. 각 위협 유형별 매핑 개수 확인
    print(f"\n📋 위협 유형별 방책 매핑 개수:")
    mapping_counts = relevance.groupby('threat_type').size().sort_values(ascending=False)
    for threat_type, count in mapping_counts.items():
        status = "✅" if threat_type in threat_types else "⚠️"
        print(f"  {status} {threat_type}: {count}개 매핑")
    
    # 6. 권장 조치사항
    print(f"\n" + "=" * 80)
    print("권장 조치사항")
    print("=" * 80)
    
    if missing_in_relevance:
        print(f"\n1. 누락된 위협 유형 {len(missing_in_relevance)}개에 대한 관련성 매핑 추가 필요:")
        print(f"   python scripts/add_missing_threat_mappings.py")
    
    if extra_in_relevance:
        print(f"\n2. 사용되지 않는 위협 유형 {len(extra_in_relevance)}개 정리 고려")
    
    if not missing_in_relevance and not extra_in_relevance:
        print(f"\n✅ 참조 무결성 정상 - 조치 불필요")
    
    return {
        'threat_types': threat_types,
        'relevance_types': relevance_types,
        'missing_in_relevance': missing_in_relevance,
        'extra_in_relevance': extra_in_relevance,
        'common_types': common_types
    }

if __name__ == "__main__":
    result = validate_threat_type_integrity()
