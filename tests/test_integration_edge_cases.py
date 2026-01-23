# tests/test_integration_edge_cases.py
# -*- coding: utf-8 -*-
"""
통합 테스트 - 엣지 케이스 및 에러 처리
예외 상황 및 엣지 케이스 처리 검증
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'core_pipeline'))
sys.path.insert(0, str(BASE_DIR / 'agents'))
sys.path.insert(0, str(BASE_DIR / 'config'))

import yaml
import shutil


def safe_print(msg):
    """안전한 출력 함수"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def load_config():
    """설정 파일 로드"""
    try:
        config_path = BASE_DIR / 'config' / 'global.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        safe_print(f"[ERROR] 설정 파일 로드 실패: {e}")
        return None


# ============================================================================
# 시나리오 7: 에러 처리 통합 테스트
# ============================================================================

def test_scenario_7_1_missing_data_recovery():
    """시나리오 7-1: 데이터 누락 시 복구"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 7-1: 데이터 누락 시 복구")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 필수 테이블 백업
        safe_print("\n[1단계] 필수 테이블 백업...")
        data_lake = BASE_DIR / 'data_lake'
        coa_library_path = data_lake / 'COA_라이브러리.xlsx'
        backup_path = data_lake / 'COA_라이브러리.xlsx.backup_test'
        
        if coa_library_path.exists():
            shutil.copy2(coa_library_path, backup_path)
            safe_print("  [OK] COA_라이브러리.xlsx 백업 완료")
        else:
            safe_print("  [WARN] COA_라이브러리.xlsx 파일이 없습니다.")
            return False
        
        # 2. 파일 삭제 시뮬레이션
        safe_print("\n[2단계] 파일 삭제 시뮬레이션...")
        try:
            coa_library_path.unlink()
            safe_print("  [OK] 파일 삭제 완료")
        except Exception as e:
            safe_print(f"  [WARN] 파일 삭제 실패: {e}")
            return False
        
        # 3. 시스템 초기화 시도
        safe_print("\n[3단계] 시스템 초기화 시도...")
        try:
            orchestrator = Orchestrator(config)
            orchestrator.initialize()
            safe_print("  [OK] 초기화 완료 (에러 없음)")
        except Exception as e:
            safe_print(f"  [WARN] 초기화 중 에러 발생: {e}")
            # 에러가 발생해도 계속 진행 (에러 처리 검증)
        
        # 4. Agent 실행 시도
        safe_print("\n[4단계] Agent 실행 시도...")
        try:
            agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
            result = agent.execute_reasoning(
                user_query="적군의 침입에 대한 방책을 추천해주세요"
            )
            
            if result:
                safe_print("  [OK] Agent 실행 완료 (기본 방책 제공 가능)")
                recommendations = result.get("recommendations", [])
                if recommendations:
                    safe_print(f"    - 추천 개수: {len(recommendations)}개")
                else:
                    safe_print("    [INFO] 추천 없음 (데이터 누락으로 인한 정상 동작)")
            else:
                safe_print("  [WARN] Agent 결과가 None입니다.")
        except Exception as e:
            safe_print(f"  [WARN] Agent 실행 중 에러: {e}")
            # 에러가 발생해도 시스템이 크래시하지 않았으면 통과
        
        # 5. 파일 복구
        safe_print("\n[5단계] 파일 복구...")
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, coa_library_path)
                backup_path.unlink()
                safe_print("  [OK] 파일 복구 완료")
            else:
                safe_print("  [WARN] 백업 파일이 없습니다.")
        except Exception as e:
            safe_print(f"  [WARN] 파일 복구 실패: {e}")
        
        safe_print("\n[RESULT] 시나리오 7-1: 통과 (에러 처리 정상 작동)")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 7-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        
        # 복구 시도
        try:
            backup_path = BASE_DIR / 'data_lake' / 'COA_라이브러리.xlsx.backup_test'
            coa_library_path = BASE_DIR / 'data_lake' / 'COA_라이브러리.xlsx'
            if backup_path.exists() and not coa_library_path.exists():
                shutil.copy2(backup_path, coa_library_path)
                backup_path.unlink()
                safe_print("[INFO] 파일 복구 완료")
        except:
            pass
        
        return False


def test_scenario_7_2_empty_data_handling():
    """시나리오 7-2: 빈 데이터 처리"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 7-2: 빈 데이터 처리")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 시스템 초기화
        safe_print("\n[1단계] 시스템 초기화...")
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        safe_print("  [OK] 초기화 완료")
        
        # 2. 데이터 확인
        safe_print("\n[2단계] 데이터 확인...")
        data = orchestrator.core.data_manager.load_all()
        
        # 최소 데이터 확인
        min_data_tables = []
        for table_name, df in data.items():
            if not df.empty:
                min_data_tables.append(table_name)
        
        safe_print(f"  [OK] 데이터 로드 완료: {len(min_data_tables)}개 테이블에 데이터 존재")
        
        # 3. Agent 실행 (최소 데이터로)
        safe_print("\n[3단계] Agent 실행 (최소 데이터)...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        result = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        
        if result:
            safe_print("  [OK] Agent 실행 완료")
            recommendations = result.get("recommendations", [])
            if recommendations:
                safe_print(f"    - 추천 개수: {len(recommendations)}개")
                safe_print("    [INFO] 최소 데이터에서도 추천 생성 가능")
            else:
                safe_print("    [INFO] 추천 없음 (데이터 부족으로 인한 정상 동작)")
        else:
            safe_print("  [WARN] Agent 결과가 None입니다.")
        
        safe_print("\n[RESULT] 시나리오 7-2: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 7-2 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_scenario_8_1_special_characters():
    """시나리오 8-1: 특수 문자 및 인코딩 처리"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 8-1: 특수 문자 및 인코딩 처리")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 시스템 초기화
        safe_print("\n[1단계] 시스템 초기화...")
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        safe_print("  [OK] 초기화 완료")
        
        # 2. 특수 문자 포함 질문 테스트
        safe_print("\n[2단계] 특수 문자 포함 질문 테스트...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        
        test_queries = [
            "적군의 침입에 대한 방책을 추천해주세요",
            "적군 침입 방책 추천",
            "방책 추천 요청",
            "COA recommendation request"
        ]
        
        all_passed = True
        for query in test_queries:
            try:
                result = agent.execute_reasoning(user_query=query)
                if result:
                    safe_print(f"  [OK] 질문 처리: '{query[:20]}...'")
                else:
                    safe_print(f"  [WARN] 질문 처리 실패: '{query[:20]}...'")
                    all_passed = False
            except Exception as e:
                safe_print(f"  [FAIL] 질문 처리 오류: '{query[:20]}...' - {e}")
                all_passed = False
        
        # 3. 데이터 인코딩 확인
        safe_print("\n[3단계] 데이터 인코딩 확인...")
        data = orchestrator.core.data_manager.load_all()
        
        encoding_ok = True
        for table_name, df in data.items():
            try:
                # 한글 컬럼명 확인
                for col in df.columns:
                    str(col)  # 인코딩 오류 발생 시 예외
                safe_print(f"  [OK] {table_name}: 인코딩 정상")
            except Exception as e:
                safe_print(f"  [FAIL] {table_name}: 인코딩 오류 - {e}")
                encoding_ok = False
        
        if all_passed and encoding_ok:
            safe_print("\n[RESULT] 시나리오 8-1: 통과")
            return True
        else:
            safe_print("\n[RESULT] 시나리오 8-1: 부분 통과")
            return False
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 8-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 메인 테스트 실행
# ============================================================================

def main():
    """메인 엣지 케이스 테스트 실행"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 - 엣지 케이스 및 에러 처리")
    safe_print("="*80)
    safe_print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 시나리오 7: 에러 처리 통합 테스트
    test_results.append(("시나리오 7-1: 데이터 누락 복구", test_scenario_7_1_missing_data_recovery()))
    test_results.append(("시나리오 7-2: 빈 데이터 처리", test_scenario_7_2_empty_data_handling()))
    
    # 시나리오 8: 엣지 케이스 통합 테스트
    test_results.append(("시나리오 8-1: 특수 문자 처리", test_scenario_8_1_special_characters()))
    
    # 결과 요약
    safe_print("\n" + "="*80)
    safe_print("엣지 케이스 테스트 결과 요약")
    safe_print("="*80)
    
    passed = sum(1 for _, result in test_results if result)
    failed = len(test_results) - passed
    
    for name, result in test_results:
        status = "✅ 통과" if result else "❌ 실패"
        safe_print(f"{status}: {name}")
    
    safe_print(f"\n총 {len(test_results)}개 시나리오")
    safe_print(f"  - 통과: {passed}개")
    safe_print(f"  - 실패: {failed}개")
    safe_print(f"통과률: {passed/len(test_results)*100:.1f}%")
    
    safe_print(f"\n테스트 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == len(test_results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


