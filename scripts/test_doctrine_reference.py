# scripts/test_doctrine_reference.py
# -*- coding: utf-8 -*-
"""
교리 인용 기능 테스트 스크립트
COA 추천 시 교리 참조가 제대로 작동하는지 확인합니다.
"""
import os
import sys
from pathlib import Path
import json

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import yaml
import pandas as pd
from core_pipeline.orchestrator import CorePipeline
from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent


def test_doctrine_reference():
    """교리 인용 기능 테스트"""
    
    print("=" * 60)
    print("교리 인용 기능 테스트")
    print("=" * 60)
    
    # 설정 로드
    config_path = BASE_DIR / "config" / "global.yaml"
    if not config_path.exists():
        print(f"[ERROR] 설정 파일을 찾을 수 없습니다: {config_path}")
        return False
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Core Pipeline 초기화
    print("\n[1/3] Core Pipeline 초기화 중...")
    try:
        core = CorePipeline(config)
        core.initialize()
        print("  ✅ Core Pipeline 초기화 완료")
    except Exception as e:
        print(f"  ❌ Core Pipeline 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Agent 초기화
    print("\n[2/3] Defense COA Agent 초기화 중...")
    try:
        agent = EnhancedDefenseCOAAgent(core)
        print("  ✅ Agent 초기화 완료")
        
        # 교리 인용 서비스 확인
        if agent.doctrine_ref_service:
            print("  ✅ 교리 인용 서비스 활성화됨")
        else:
            print("  ⚠️  교리 인용 서비스가 없습니다")
            return False
    except Exception as e:
        print(f"  ❌ Agent 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # COA 추천 테스트
    print("\n[3/3] COA 추천 실행 (교리 인용 테스트)...")
    print("-" * 60)
    
    # 테스트용 상황 ID (실제 데이터에 있는 ID 사용)
    # 만약 데이터가 없다면 첫 번째 위협상황을 사용
    try:
        # 위협상황 목록 가져오기
        threat_data = core.data_manager.load_table('위협상황')
        if threat_data is not None and len(threat_data) > 0:
            # 첫 번째 위협상황 ID 사용
            first_row = threat_data.iloc[0]
            test_situation_id = first_row.get('위협ID') or first_row.get('ID')
            if pd.isna(test_situation_id) or not test_situation_id:
                # 인덱스 기반 ID 생성
                test_situation_id = f"THREAT_{threat_data.index[0]}"
        else:
            test_situation_id = "THREAT_001"  # 기본값
        
        print(f"  테스트 상황 ID: {test_situation_id}")
        
        # COA 추천 실행
        print("  COA 추천 실행 중...")
        result = agent.execute_reasoning(
            situation_id=test_situation_id,
            use_palantir_mode=True
        )
        
        if result.get("status") != "completed":
            print(f"  ❌ COA 추천 실패: {result.get('status')}")
            return False
        
        recommendations = result.get("recommendations", [])
        if not recommendations:
            print("  ⚠️  추천된 COA가 없습니다")
            return False
        
        print(f"  ✅ COA 추천 완료: {len(recommendations)}개 추천")
        
        # 교리 참조 확인
        print("\n" + "=" * 60)
        print("교리 참조 확인 결과")
        print("=" * 60)
        
        doctrine_found_count = 0
        for i, rec in enumerate(recommendations[:3], 1):  # 상위 3개만 확인
            coa_id = rec.get("coa_id", "Unknown")
            coa_name = rec.get("coa_name", "Unknown")
            doctrine_refs = rec.get("doctrine_references", [])
            
            print(f"\n[{i}] {coa_id} ({coa_name})")
            if doctrine_refs:
                doctrine_found_count += 1
                print(f"  ✅ 교리 참조 {len(doctrine_refs)}개 발견:")
                for j, ref in enumerate(doctrine_refs, 1):
                    statement_id = ref.get("statement_id", "Unknown")
                    excerpt = ref.get("excerpt", "")[:80]
                    score = ref.get("relevance_score", 0.0)
                    mett_c = ref.get("mett_c_elements", [])
                    print(f"    [{j}] {statement_id} (관련도: {score:.2f})")
                    print(f"        {excerpt}...")
                    print(f"        METT-C: {', '.join(mett_c) if mett_c else 'N/A'}")
            else:
                print(f"  ⚠️  교리 참조 없음")
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("테스트 결과 요약")
        print("=" * 60)
        print(f"  - 총 추천 COA: {len(recommendations)}개")
        print(f"  - 교리 참조 포함 COA: {doctrine_found_count}개")
        
        if doctrine_found_count > 0:
            print("\n  ✅ 교리 인용 기능이 정상적으로 작동합니다!")
            
            # 교리 기반 설명 생성 테스트
            print("\n" + "=" * 60)
            print("교리 기반 설명 생성 테스트")
            print("=" * 60)
            
            from core_pipeline.coa_engine.doctrine_explanation_generator import DoctrineBasedExplanationGenerator
            
            explanation_generator = DoctrineBasedExplanationGenerator()
            
            # 첫 번째 추천에 대한 설명 생성
            first_rec = recommendations[0]
            if first_rec.get("doctrine_references"):
                print(f"\nCOA {first_rec.get('coa_id')}에 대한 교리 기반 설명 생성 중...")
                try:
                    explanation = explanation_generator.generate_explanation(
                        coa_recommendation=first_rec,
                        situation_info=result.get("situation_info", {}),
                        mett_c_analysis=result.get("situation_analysis", {}).get("mett_c", {}),
                        axis_states=result.get("situation_analysis", {}).get("axis_states", [])
                    )
                    print("\n생성된 설명:")
                    print("-" * 60)
                    print(explanation)
                    print("-" * 60)
                    print("\n  ✅ 교리 기반 설명 생성 성공!")
                except Exception as e:
                    print(f"  ⚠️  설명 생성 실패: {e}")
                    import traceback
                    traceback.print_exc()
            
            return True
        else:
            print("\n  ⚠️  교리 참조가 발견되지 않았습니다.")
            print("      (RAG 인덱스에 교리 문서가 없거나 검색 쿼리가 적합하지 않을 수 있습니다)")
            return False
        
    except Exception as e:
        print(f"\n  ❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_doctrine_reference()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 스크립트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


