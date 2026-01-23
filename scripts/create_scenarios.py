# scripts/create_scenarios.py
# -*- coding: utf-8 -*-
"""
Week 4 Day 3-4: 시나리오 데이터 생성 스크립트
다양한 전술 상황을 반영한 10개의 시나리오 데이터를 생성하여 엑셀 파일로 저장합니다.
"""
import pandas as pd
import os

def create_scenarios():
    print("=" * 60)
    print("Week 4: 시나리오 데이터 생성 (10개 상황)")
    print("=" * 60)

    # 10개 시나리오 정의
    scenarios = [
        {
            "ID": "SIT_001",
            "상황명": "적 대규모 기계화부대 남하",
            "위협유형": "전면전",
            "심각도": 0.95,
            "설명": "적 기계화 군단이 전선을 돌파하여 고속으로 남하 중. 아군 주방어선 붕괴 위기.",
            "threat_level": 0.95,
            "enemy_type": "mechanized",
            "terrain": "plains"
        },
        {
            "ID": "SIT_002",
            "상황명": "국지적 도발 및 침투",
            "위협유형": "국지전",
            "심각도": 0.6,
            "설명": "산악 지역을 통해 적 특수부대 침투 식별. 후방 교란 시도 예상.",
            "threat_level": 0.6,
            "enemy_type": "sof",
            "terrain": "mountain"
        },
        {
            "ID": "SIT_003",
            "상황명": "해안 상륙 징후 포착",
            "위협유형": "상륙전",
            "심각도": 0.8,
            "설명": "적 상륙함정이 해안으로 접근 중. 상륙 돌격 임박.",
            "threat_level": 0.8,
            "enemy_type": "amphibious",
            "terrain": "coastal"
        },
        {
            "ID": "SIT_004",
            "상황명": "적 미사일 발사 징후",
            "위협유형": "미사일위협",
            "심각도": 0.9,
            "설명": "적 미사일 기지에서 발사 준비 활동 포착. 전략 시설 타격 예상.",
            "threat_level": 0.9,
            "enemy_type": "missile",
            "terrain": "base"
        },
        {
            "ID": "SIT_005",
            "상황명": "사이버 공격 및 통신 마비",
            "위협유형": "사이버전",
            "심각도": 0.7,
            "설명": "아군 지휘통제 네트워크에 대한 대규모 디도스 공격 발생. 일부 통신망 마비.",
            "threat_level": 0.7,
            "enemy_type": "cyber",
            "terrain": "cyber"
        },
        {
            "ID": "SIT_006",
            "상황명": "적 보급선 노출",
            "위협유형": "기회포착",
            "심각도": 0.4,
            "설명": "적 주력부대의 급속한 전진으로 보급선이 길게 늘어지고 측면이 노출됨.",
            "threat_level": 0.4,
            "enemy_type": "logistics",
            "terrain": "road"
        },
        {
            "ID": "SIT_007",
            "상황명": "도심지 시가전 상황",
            "위협유형": "시가전",
            "심각도": 0.75,
            "설명": "적 부대가 주요 도시를 점거하고 방어 태세 구축. 민간인 피해 우려.",
            "threat_level": 0.75,
            "enemy_type": "infantry",
            "terrain": "urban"
        },
        {
            "ID": "SIT_008",
            "상황명": "적 공중 강습 위협",
            "위협유형": "공중강습",
            "심각도": 0.85,
            "설명": "대규모 헬기 부대가 아군 후방 중요 거점을 향해 이동 중.",
            "threat_level": 0.85,
            "enemy_type": "air_assault",
            "terrain": "air"
        },
        {
            "ID": "SIT_009",
            "상황명": "화생방 공격 징후",
            "위협유형": "화생방",
            "심각도": 0.98,
            "설명": "적 포병 부대에서 화학탄 사용 징후 포착. 대량 살상 우려.",
            "threat_level": 0.98,
            "enemy_type": "cbrn",
            "terrain": "all"
        },
        {
            "ID": "SIT_010",
            "상황명": "평화 유지 활동 중 소요 사태",
            "위협유형": "안정화작전",
            "심각도": 0.3,
            "설명": "작전 지역 내 민간인 시위가 폭력 사태로 번질 조짐.",
            "threat_level": 0.3,
            "enemy_type": "civilian",
            "terrain": "urban"
        }
    ]

    # DataFrame 생성
    df = pd.DataFrame(scenarios)
    
    # 저장 경로 설정
    output_path = "data_lake/시나리오모음.xlsx"
    
    # 엑셀 파일 저장
    try:
        df.to_excel(output_path, index=False)
        print(f"✅ 파일 생성 완료: {output_path}")
        print(f"   총 {len(df)}개 시나리오 데이터 저장됨")
        
        # 데이터 확인
        print("\n[생성된 시나리오 목록]")
        for idx, row in df.iterrows():
            print(f"{row['ID']}: {row['상황명']} (위협수준: {row['threat_level']})")
            
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")

if __name__ == "__main__":
    create_scenarios()
