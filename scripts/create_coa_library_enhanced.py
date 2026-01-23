# scripts/create_coa_library_enhanced.py
# -*- coding: utf-8 -*-
"""
Week 4 Day 1-2: COA 라이브러리 확장 스크립트
7가지 COA 타입별로 10개씩 총 70개의 방책 데이터를 생성하여 엑셀 파일로 저장합니다.
"""
import pandas as pd
import os
from datetime import datetime

def create_enhanced_coa_library():
    print("=" * 60)
    print("Week 4: COA 라이브러리 확장 (70개 방책 생성)")
    print("=" * 60)

    # 7가지 COA 타입 정의
    coa_types = {
        "Defense": "방어방책",
        "Offensive": "공격방책",
        "CounterAttack": "반격방책",
        "Preemptive": "선제방책",
        "Deterrence": "억제방책",
        "Maneuver": "기동방책",
        "InformationOps": "정보방책"
    }

    # 방책 데이터 생성 로직
    data = []
    
    # 1. Defense (방어) - 10개
    defense_coas = [
        ("COA_DEF_001", "주방어 진지 고수", "적 주공에 대해 주방어 진지를 고수하여 돌파를 저지함", "threat_level > 0.7"),
        ("COA_DEF_002", "지연 방어", "공간을 내주며 시간을 확보하여 적의 공격 기세를 약화시킴", "threat_level > 0.8 and resources < 0.5"),
        ("COA_DEF_003", "거점 방어", "핵심 요충지를 중심으로 원형 방어 태세 구축", "assets > 0.6"),
        ("COA_DEF_004", "기동 방어", "적을 유인하여 예비대로 격멸하는 적극적 방어", "mobility > 0.7"),
        ("COA_DEF_005", "사주 방어", "전 방향 위협에 대비한 방어 태세", "threat_direction == 'all'"),
        ("COA_DEF_006", "역경사면 방어", "적 직사화기 효력을 회피하기 위한 능선 후면 방어", "terrain == 'mountain'"),
        ("COA_DEF_007", "도심지 방어", "건물을 이용한 매복 및 근접 전투 수행", "terrain == 'urban'"),
        ("COA_DEF_008", "대공 방어 강화", "적 항공 공격에 대비한 방공 자산 집중 운용", "air_threat > 0.7"),
        ("COA_DEF_009", "해안 경계 강화", "상륙 위협에 대비한 해안선 방어 강화", "location == 'coastal'"),
        ("COA_DEF_010", "후방 지역 방호", "특수작전부대 침투에 대비한 후방 중요시설 방호", "rear_threat > 0.5")
    ]
    
    # 2. Offensive (공격) - 10개
    offensive_coas = [
        ("COA_OFF_001", "정면 공격", "적의 정면을 강타하여 주력을 격멸", "attack_power > 0.8"),
        ("COA_OFF_002", "포위 공격", "적의 측후방을 차단하여 포위 섬멸", "mobility > 0.7"),
        ("COA_OFF_003", "우회 기동", "적의 주방어 지대를 우회하여 심장부 타격", "terrain_adaptability > 0.8"),
        ("COA_OFF_004", "돌파 공격", "적 방어선의 약점을 집중 타격하여 돌파구 형성", "breakthrough_capability > 0.8"),
        ("COA_OFF_005", "침투 공격", "소부대를 적진 깊숙이 침투시켜 교란 및 타격", "infiltration > 0.8"),
        ("COA_OFF_006", "강습 도하", "하천 장애물을 극복하고 교두보 확보", "river_crossing > 0.7"),
        ("COA_OFF_007", "공중 강습", "헬기를 이용하여 적 후방에 병력 투사", "air_assault > 0.8"),
        ("COA_OFF_008", "화력 타격", "포병 및 항공 화력으로 적 주요 표적 제압", "firepower > 0.9"),
        ("COA_OFF_009", "추격 작전", "퇴각하는 적을 추격하여 재편성 기회 박탈", "enemy_retreat == True"),
        ("COA_OFF_010", "수색 정찰 공격", "적 정보 수집과 동시에 위력 수색 실시", "intelligence_need > 0.7")
    ]

    # 3. CounterAttack (반격) - 10개
    counter_coas = [
        ("COA_CNT_001", "충격 반격", "적 공격 기세가 둔화된 시점에 대규모 반격", "enemy_momentum < 0.5"),
        ("COA_CNT_002", "역습", "방어 진지 내로 진입한 적을 즉각적으로 격퇴", "penetration == True"),
        ("COA_CNT_003", "차단 반격", "적의 증원 및 퇴로를 차단하고 반격", "logistics_cut > 0.7"),
        ("COA_CNT_004", "유인 반격", "거짓 후퇴로 적을 유인한 후 기습 반격", "deception > 0.8"),
        ("COA_CNT_005", "측면 반격", "적 공격 부대의 노출된 측면을 타격", "flank_exposed == True"),
        ("COA_CNT_006", "제한적 반격", "특정 지역 회복을 위한 국지적 반격", "objective == 'limited'"),
        ("COA_CNT_007", "공세 이전", "방어에서 공격으로 전면적인 태세 전환", "superiority > 0.6"),
        ("COA_CNT_008", "화력 반격", "기동 부대 투입 전 대규모 화력으로 반격 여건 조성", "firepower > 0.8"),
        ("COA_CNT_009", "예비대 투입 반격", "신선한 예비대를 결정적 시기/장소에 투입", "reserve_available == True"),
        ("COA_CNT_010", "연합 반격", "인접 부대와 협조하여 동시 다발적 반격", "coordination > 0.7")
    ]

    # 4. Preemptive (선제) - 10개
    preemptive_coas = [
        ("COA_PRE_001", "선제 타격", "적의 공격 징후가 명확할 때 선제적으로 타격", "imminent_threat == True"),
        ("COA_PRE_002", "예방 타격", "적의 잠재적 위협을 사전에 제거", "future_threat > 0.8"),
        ("COA_PRE_003", "지휘부 정밀 타격", "적 지휘통제 체계를 마비시키기 위한 참수 작전", "c2_target_identified == True"),
        ("COA_PRE_004", "미사일 발사대 타격", "적의 미사일 위협을 발사 전 제거", "missile_threat == True"),
        ("COA_PRE_005", "사이버 선제 공격", "적 네트워크를 마비시켜 공격 능력 무력화", "cyber_capability > 0.8"),
        ("COA_PRE_006", "특수전 선제 타격", "특수부대를 투입하여 핵심 시설 파괴", "sof_capability > 0.8"),
        ("COA_PRE_007", "전자전 선제 공격", "강력한 재밍으로 적 통신 및 레이더 무력화", "ew_capability > 0.8"),
        ("COA_PRE_008", "봉쇄 작전", "적의 기동로를 사전에 봉쇄하여 공격 기도 차단", "blockade_possible == True"),
        ("COA_PRE_009", "기만적 선제 행동", "아군의 의도를 숨기고 적의 오판을 유도하는 선제 행동", "deception > 0.7"),
        ("COA_PRE_010", "정보 우위 선점", "감시 정찰 자산을 총동원하여 정보 우위 확보", "isr_assets > 0.8")
    ]

    # 5. Deterrence (억제) - 10개
    deterrence_coas = [
        ("COA_DET_001", "무력 시위", "대규모 훈련이나 전력을 노출하여 의지 과시", "show_of_force > 0.8"),
        ("COA_DET_002", "전력 증강 배치", "핵심 지역에 전력을 증강 배치하여 억제력 제고", "reinforcement_available == True"),
        ("COA_DET_003", "경고 사격", "적의 도발에 대해 강력한 경고 메시지 전달", "provocation_level > 0.4"),
        ("COA_DET_004", "전략 자산 전개", "항공모함, 폭격기 등 전략 자산 전개", "strategic_assets == True"),
        ("COA_DET_005", "심리전 활동", "전단 살포, 방송 등을 통해 적 사기 저하 유도", "psyops > 0.7"),
        ("COA_DET_006", "외교적 압박", "동맹국과 연계하여 외교적 압박 가중", "diplomatic_support == True"),
        ("COA_DET_007", "경제 제재 위협", "적의 경제적 취약점을 겨냥한 제재 경고", "economic_leverage > 0.6"),
        ("COA_DET_008", "사이버 억제", "사이버 보복 능력을 과시하여 공격 억제", "cyber_deterrence > 0.7"),
        ("COA_DET_009", "비례적 대응 경고", "적 도발 시 동일 수준 이상의 보복 경고", "proportionality == True"),
        ("COA_DET_010", "핵 억제 과시", "핵 우산 또는 확장 억제 능력 과시 (가상)", "nuclear_deterrence == True")
    ]

    # 6. Maneuver (기동) - 10개
    maneuver_coas = [
        ("COA_MAN_001", "신속 전개", "위기 발생 지역으로 부대를 신속하게 이동", "mobility_speed > 0.8"),
        ("COA_MAN_002", "전략적 재배치", "전구 내 전력 균형을 위해 부대 재배치", "strategic_balance < 0.5"),
        ("COA_MAN_003", "우회 기동", "장애물이나 적 방어 지대를 우회하여 이동", "bypass_route == True"),
        ("COA_MAN_004", "입체 기동", "지상, 공중, 해상을 연계한 입체적 기동", "joint_ops > 0.7"),
        ("COA_MAN_005", "야간 기동", "적 관측이 제한되는 야간을 이용한 은밀 기동", "night_ops_capability > 0.8"),
        ("COA_MAN_006", "철수 작전", "불리한 상황에서 전투력을 보존하며 질서 있게 철수", "situation == 'unfavorable'"),
        ("COA_MAN_007", "도하 작전", "하천 장애물을 극복하기 위한 도하", "river_crossing_assets == True"),
        ("COA_MAN_008", "공중 이동", "수송기를 이용하여 병력과 장비를 원거리 이동", "air_transport > 0.7"),
        ("COA_MAN_009", "해상 수송", "선박을 이용하여 대규모 물자 및 병력 이동", "sea_transport > 0.8"),
        ("COA_MAN_010", "기만 기동", "적을 기만하기 위한 양동 작전 또는 거짓 이동", "deception > 0.7")
    ]

    # 7. InformationOps (정보) - 10개
    info_coas = [
        ("COA_INF_001", "전자전 공격", "적 통신 및 레이더에 대한 재밍 실시", "ew_assets > 0.7"),
        ("COA_INF_002", "사이버 공격", "적 지휘통제 네트워크 침투 및 마비", "cyber_offense > 0.8"),
        ("COA_INF_003", "기만 작전", "허위 정보를 유포하여 적의 오판 유도", "deception_plan == True"),
        ("COA_INF_004", "심리전", "적군 및 민간인 대상 심리전 수행", "psyops_assets == True"),
        ("COA_INF_005", "보안 작전", "아군 정보 유출 방지를 위한 보안 활동 강화", "opsec_level < 0.9"),
        ("COA_INF_006", "첩보 수집", "UAV, 정찰대 등을 활용한 적 정보 수집", "isr_capability > 0.7"),
        ("COA_INF_007", "표적 획득", "정밀 타격을 위한 핵심 표적 위치 식별", "target_acquisition > 0.8"),
        ("COA_INF_008", "전투 피해 평가", "타격 후 적 피해 상황 확인 및 분석", "bda_required == True"),
        ("COA_INF_009", "통신 감청", "적 무선 통신 감청을 통한 의도 파악", "sigint_capability > 0.7"),
        ("COA_INF_010", "여론전", "미디어 등을 활용하여 우호적 여론 조성", "public_affairs > 0.6")
    ]

    # 데이터 통합
    all_coas = []
    all_coas.extend([(c[0], c[1], "Defense", c[2], c[3]) for c in defense_coas])
    all_coas.extend([(c[0], c[1], "Offensive", c[2], c[3]) for c in offensive_coas])
    all_coas.extend([(c[0], c[1], "CounterAttack", c[2], c[3]) for c in counter_coas])
    all_coas.extend([(c[0], c[1], "Preemptive", c[2], c[3]) for c in preemptive_coas])
    all_coas.extend([(c[0], c[1], "Deterrence", c[2], c[3]) for c in deterrence_coas])
    all_coas.extend([(c[0], c[1], "Maneuver", c[2], c[3]) for c in maneuver_coas])
    all_coas.extend([(c[0], c[1], "InformationOps", c[2], c[3]) for c in info_coas])

    # DataFrame 생성
    df = pd.DataFrame(all_coas, columns=["COA_ID", "명칭", "방책유형", "설명", "적용조건"])
    
    # 저장 경로 설정
    output_path = "data_lake/COA_Library.xlsx"
    
    # 엑셀 파일 저장
    try:
        df.to_excel(output_path, index=False)
        print(f"✅ 파일 생성 완료: {output_path}")
        print(f"   총 {len(df)}개 방책 데이터 저장됨")
        
        # 타입별 개수 확인
        print("\n[타입별 방책 수]")
        print(df['방책유형'].value_counts())
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")

if __name__ == "__main__":
    create_enhanced_coa_library()
