"""
COA 평가 시스템 개선을 위한 데이터 테이블 생성 스크립트
"""
import pandas as pd
import os
from pathlib import Path

def create_threat_type_mapping():
    """1. 위협상황.xlsx에 위협유형 컬럼 추가"""
    print("=" * 80)
    print("Step 1: 위협유형 컬럼 추가")
    print("=" * 80)
    
    # 기존 파일 읽기
    threat_file = Path("data_lake/위협상황.xlsx")
    df = pd.read_excel(threat_file)
    
    print(f"\n현재 컬럼: {list(df.columns)}")
    print(f"현재 데이터 수: {len(df)}개")
    
    # 위협유형 매핑 (위협ID 기반)
    threat_type_mapping = {
        'THR001': '침투',
        'THR002': '포격',  
        'THR003': '포격',
        'THR004': '침투',
        'THR005': '기습공격',
        'THR006': '사이버',
        'THR007': '전면공격',
        'THR008': '국지도발',
        'THR009': '침투',
        'THR010': '기습공격'
    }
    
    # 위협유형 컬럼이 없으면 추가
    if '위협유형' not in df.columns:
        df['위협유형'] = df['위협ID'].map(threat_type_mapping)
        df.to_excel(threat_file, index=False)
        print(f"\n✅ '위협유형' 컬럼 추가 완료")
        print(f"\n샘플 데이터:")
        print(df[['위협ID', '위협명', '위협유형']].head(5))
    else:
        print(f"\n⚠️ '위협유형' 컬럼이 이미 존재합니다")
    
    return df

def create_coa_type_threat_type_relevance():
    """2. 방책유형-위협유형 관련성 테이블 생성"""
    print("\n" + "=" * 80)
    print("Step 2: 방책유형-위협유형 관련성 테이블 생성")
    print("=" * 80)
    
    # 방책유형-위협유형 관련성 매핑 (교리 기반)
    data = [
        # Defense
        {'coa_type': 'Defense', 'threat_type': '침투', 'base_relevance': 0.85, 'description': '방어 방책은 침투 위협에 매우 효과적'},
        {'coa_type': 'Defense', 'threat_type': '포격', 'base_relevance': 0.60, 'description': '방어 방책은 포격에 중간 정도 효과'},
        {'coa_type': 'Defense', 'threat_type': '기습공격', 'base_relevance': 0.70, 'description': '방어 방책은 기습공격 대응에 효과적'},
        {'coa_type': 'Defense', 'threat_type': '사이버', 'base_relevance': 0.30, 'description': '방어 방책은 사이버 위협에 제한적'},
        {'coa_type': 'Defense', 'threat_type': '전면공격', 'base_relevance': 0.75, 'description': '방어 방책은 전면공격에 효과적'},
        {'coa_type': 'Defense', 'threat_type': '국지도발', 'base_relevance': 0.65, 'description': '방어 방책은 국지도발에 적용 가능'},
        
        # Offensive
        {'coa_type': 'Offensive', 'threat_type': '침투', 'base_relevance': 0.50, 'description': '공격 방책은 침투 대응에 제한적'},
        {'coa_type': 'Offensive', 'threat_type': '포격', 'base_relevance': 0.45, 'description': '공격 방책은 포격 대응에 제한적'},
        {'coa_type': 'Offensive', 'threat_type': '기습공격', 'base_relevance': 0.60, 'description': '공격 방책은 기습 전환에 활용 가능'},
        {'coa_type': 'Offensive', 'threat_type': '사이버', 'base_relevance': 0.35, 'description': '공격 방책은 사이버 위협에 제한적'},
        {'coa_type': 'Offensive', 'threat_type': '전면공격', 'base_relevance': 0.80, 'description': '공격 방책은 전면공격 상황에 효과적'},
        {'coa_type': 'Offensive', 'threat_type': '국지도발', 'base_relevance': 0.70, 'description': '공격 방책은 국지도발에 강력한 대응'},
        
        # CounterAttack
        {'coa_type': 'CounterAttack', 'threat_type': '침투', 'base_relevance': 0.75, 'description': '반격은 침투 저지에 효과적'},
        {'coa_type': 'CounterAttack', 'threat_type': '포격', 'base_relevance': 0.55, 'description': '반격은 포격원에 타격 가능'},
        {'coa_type': 'CounterAttack', 'threat_type': '기습공격', 'base_relevance': 0.80, 'description': '반격은 기습 대응에 매우 효과적'},
        {'coa_type': 'CounterAttack', 'threat_type': '사이버', 'base_relevance': 0.40, 'description': '반격은 사이버 위협에 제한적'},
        {'coa_type': 'CounterAttack', 'threat_type': '전면공격', 'base_relevance': 0.85, 'description': '반격은 전면공격 전환에 핵심'},
        {'coa_type': 'CounterAttack', 'threat_type': '국지도발', 'base_relevance': 0.75, 'description': '반격은 국지도발 응징에 효과적'},
        
        # Maneuver
        {'coa_type': 'Maneuver', 'threat_type': '침투', 'base_relevance': 0.70, 'description': '기동은 침투 회피 및 재배치에 유리'},
        {'coa_type': 'Maneuver', 'threat_type': '포격', 'base_relevance': 0.65, 'description': '기동은 포격 회피에 효과적'},
        {'coa_type': 'Maneuver', 'threat_type': '기습공격', 'base_relevance': 0.75, 'description': '기동은 기습 대응 유연성 제공'},
        {'coa_type': 'Maneuver', 'threat_type': '사이버', 'base_relevance': 0.30, 'description': '기동은 사이버 위협에 무관'},
        {'coa_type': 'Maneuver', 'threat_type': '전면공격', 'base_relevance': 0.80, 'description': '기동은 전면공격 시 핵심'},
        {'coa_type': 'Maneuver', 'threat_type': '국지도발', 'base_relevance': 0.60, 'description': '기동은 국지도발 대응에 활용'},
        
        # Deterrence
        {'coa_type': 'Deterrence', 'threat_type': '침투', 'base_relevance': 0.55, 'description': '억제는 침투 사전 차단에 기여'},
        {'coa_type': 'Deterrence', 'threat_type': '포격', 'base_relevance': 0.60, 'description': '억제는 포격 억지에 효과'},
        {'coa_type': 'Deterrence', 'threat_type': '기습공격', 'base_relevance': 0.70, 'description': '억제는 기습공격 예방에 효과적'},
        {'coa_type': 'Deterrence', 'threat_type': '사이버', 'base_relevance': 0.65, 'description': '억제는 사이버 공격 억지 가능'},
        {'coa_type': 'Deterrence', 'threat_type': '전면공격', 'base_relevance': 0.85, 'description': '억제는 전면공격 예방에 핵심'},
        {'coa_type': 'Deterrence', 'threat_type': '국지도발', 'base_relevance': 0.75, 'description': '억제는 국지도발 사전 차단'},
        
        # Preemptive
        {'coa_type': 'Preemptive', 'threat_type': '침투', 'base_relevance': 0.80, 'description': '선제타격은 침투 준비 파괴에 효과적'},
        {'coa_type': 'Preemptive', 'threat_type': '포격', 'base_relevance': 0.85, 'description': '선제타격은 포병 진지 제압에 최적'},
        {'coa_type': 'Preemptive', 'threat_type': '기습공격', 'base_relevance': 0.90, 'description': '선제타격은 기습 준비 파괴에 매우 효과적'},
        {'coa_type': 'Preemptive', 'threat_type': '사이버', 'base_relevance': 0.50, 'description': '선제타격은 사이버 인프라 타격 가능'},
        {'coa_type': 'Preemptive', 'threat_type': '전면공격', 'base_relevance': 0.95, 'description': '선제타격은 전면공격 준비 파괴에 최적'},
        {'coa_type': 'Preemptive', 'threat_type': '국지도발', 'base_relevance': 0.70, 'description': '선제타격은 국지도발 원천 봉쇄'},
        
        # InformationOps
        {'coa_type': 'InformationOps', 'threat_type': '침투', 'base_relevance': 0.45, 'description': '정보작전은 침투 교란에 제한적 기여'},
        {'coa_type': 'InformationOps', 'threat_type': '포격', 'base_relevance': 0.40, 'description': '정보작전은 포격에 간접 효과'},
        {'coa_type': 'InformationOps', 'threat_type': '기습공격', 'base_relevance': 0.55, 'description': '정보작전은 기습 의도 혼란 유발'},
        {'coa_type': 'InformationOps', 'threat_type': '사이버', 'base_relevance': 0.85, 'description': '정보작전은 사이버 위협에 매우 효과적'},
        {'coa_type': 'InformationOps', 'threat_type': '전면공격', 'base_relevance': 0.60, 'description': '정보작전은 전면공격 시 보조 역할'},
        {'coa_type': 'InformationOps', 'threat_type': '국지도발', 'base_relevance': 0.65, 'description': '정보작전은 국지도발 대응에 활용'},
    ]
    
    df = pd.DataFrame(data)
    
    # 파일 저장
    output_file = Path("data_lake/방책유형_위협유형_관련성.xlsx")
    df.to_excel(output_file, index=False)
    
    print(f"\n✅ 파일 생성 완료: {output_file}")
    print(f"총 {len(df)}개 매핑 생성 (7개 방책유형 × 6개 위협유형)")
    print(f"\n샘플 데이터:")
    print(df.head(10).to_string(index=False))
    
    return df

def create_available_resources():
    """3. 가용자원 테이블 생성"""
    print("\n" + "=" * 80)
    print("Step 3: 가용자원 테이블 생성")
    print("=" * 80)
    
    # MSN008 시나리오 가용 자원 정의
    data = [
        {'situation_id': 'MSN008', 'resource_type': '전차', 'resource_name': '전차대대', 'available_quantity': 30, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '포병', 'resource_name': '포병대대', 'available_quantity': 18, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '포병', 'resource_name': '자주포대대', 'available_quantity': 12, 'location': '제2사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '보병', 'resource_name': '보병여단', 'available_quantity': 3000, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '보병', 'resource_name': '기계화보병', 'available_quantity': 500, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '항공', 'resource_name': '공격헬기', 'available_quantity': 8, 'location': '항공대대', 'status': '정비중'},
        {'situation_id': 'MSN008', 'resource_type': '항공', 'resource_name': '수송헬기', 'available_quantity': 12, 'location': '항공대대', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '공병', 'resource_name': '공병대대', 'available_quantity': 200, 'location': '제2사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '특수전', 'resource_name': '특수전팀', 'available_quantity': 50, 'location': '특수부대', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '정보', 'resource_name': '사이버전팀', 'available_quantity': 0, 'location': '-', 'status': '미보유'},
        {'situation_id': 'MSN008', 'resource_type': '정보', 'resource_name': 'PSYOPS팀', 'available_quantity': 20, 'location': '심리전부대', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '정보', 'resource_name': '전자전부대', 'available_quantity': 15, 'location': '정보대대', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '정보', 'resource_name': '영상감시자산', 'available_quantity': 5, 'location': '정보대대', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '화력지원', 'resource_name': '미사일부대', 'available_quantity': 8, 'location': '포병사령부', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '지원', 'resource_name': '의무대', 'available_quantity': 100, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '지원', 'resource_name': '통신소대', 'available_quantity': 80, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '방공', 'resource_name': '방공대대', 'available_quantity': 12, 'location': '방공사령부', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '대전차', 'resource_name': '대전차미사일', 'available_quantity': 40, 'location': '제1사단', 'status': '사용가능'},
        {'situation_id': 'MSN008', 'resource_type': '도하', 'resource_name': '도하중대', 'available_quantity': 50, 'location': '공병사령부', 'status': '사용가능'},
    ]
    
    df = pd.DataFrame(data)
    
    # 파일 저장
    output_file = Path("data_lake/가용자원.xlsx")
    df.to_excel(output_file, index=False)
    
    print(f"\n✅ 파일 생성 완료: {output_file}")
    print(f"MSN008 시나리오 자원: {len(df)}개")
    print(f"\n샘플 데이터:")
    print(df.head(10).to_string(index=False))
    
    # 통계
    print(f"\n📊 자원 현황 통계:")
    print(f"- 사용가능: {len(df[df['status'] == '사용가능'])}개")
    print(f"- 정비중: {len(df[df['status'] == '정비중'])}개")
    print(f"- 미보유: {len(df[df['status'] == '미보유'])}개")
    
    return df

def add_coa_library_columns():
    """4. COA_Library.xlsx에 신규 컬럼 추가"""
    print("\n" + "=" * 80)
    print("Step 4: COA_Library.xlsx 신규 컬럼 추가")
    print("=" * 80)
    
    coa_file = Path("data_lake/COA_Library.xlsx")
    df = pd.read_excel(coa_file)
    
    print(f"\n현재 컬럼: {list(df.columns)}")
    
    # 신규 컬럼 추가
    new_columns = ['적합위협유형', '자원우선순위', '전장환경_최적조건', '연계방책', '적대응전술']
    added = []
    
    for col in new_columns:
        if col not in df.columns:
            df[col] = ''  # 빈 값으로 초기화
            added.append(col)
    
    if added:
        df.to_excel(coa_file, index=False)
        print(f"\n✅ {len(added)}개 컬럼 추가 완료: {', '.join(added)}")
    else:
        print(f"\n⚠️ 모든 컬럼이 이미 존재합니다")
    
    print(f"\n업데이트된 컬럼 ({len(df.columns)}개):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    return df

def main():
    """메인 실행 함수"""
    print("\n" + "🚀" * 40)
    print("COA 평가 시스템 개선 - 데이터 테이블 생성")
    print("🚀" * 40 + "\n")
    
    try:
        # 1. 위협유형 추가
        threat_df = create_threat_type_mapping()
        
        # 2. 방책유형-위협유형 관련성 테이블
        relevance_df = create_coa_type_threat_type_relevance()
        
        # 3. 가용자원 테이블
        resource_df = create_available_resources()
        
        # 4. COA Library 컬럼 추가
        coa_df = add_coa_library_columns()
        
        print("\n" + "✅" * 40)
        print("모든 데이터 테이블 생성 완료!")
        print("✅" * 40 + "\n")
        
        print("📋 생성된 파일:")
        print("1. data_lake/위협상황.xlsx (위협유형 컬럼 추가)")
        print("2. data_lake/방책유형_위협유형_관련성.xlsx (신규)")
        print("3. data_lake/가용자원.xlsx (신규)")
        print("4. data_lake/COA_Library.xlsx (5개 컬럼 추가)")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
