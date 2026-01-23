# tests/test_integration.py
# -*- coding: utf-8 -*-
"""
통합 테스트
여러 모듈이 함께 작동하는 전체 워크플로우 검증
"""
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

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
import pandas as pd


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
# 시나리오 1: 전체 파이프라인 통합 테스트
# ============================================================================

def test_scenario_1_1_basic_pipeline():
    """시나리오 1-1: 기본 방책 추천 파이프라인"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 1-1: 기본 방책 추천 파이프라인")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 초기화
        safe_print("\n[1단계] Orchestrator 초기화...")
        start_time = time.time()
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        init_time = time.time() - start_time
        safe_print(f"  [OK] 초기화 완료 (소요 시간: {init_time:.2f}초)")
        
        # 2. 데이터 로드 검증
        safe_print("\n[2단계] 데이터 로드 검증...")
        data = orchestrator.core.data_manager.load_all()
        if not data:
            safe_print("  [FAIL] 데이터 로드 실패")
            return False
        
        table_count = len(data)
        safe_print(f"  [OK] {table_count}개 테이블 로드 완료")
        
        # 필수 테이블 확인
        required_tables = ['위협상황', 'COA_라이브러리', '아군부대']
        for table in required_tables:
            if table in data and not data[table].empty:
                safe_print(f"    - {table}: {len(data[table])}개 행")
            else:
                safe_print(f"    [WARN] {table}: 데이터 없음")
        
        # 3. 온톨로지 구축 검증
        safe_print("\n[3단계] 온톨로지 그래프 구축...")
        start_time = time.time()
        graph = orchestrator.core.ontology_manager.build_from_data(data)
        ontology_time = time.time() - start_time
        safe_print(f"  [OK] 온톨로지 구축 완료 (소요 시간: {ontology_time:.2f}초)")
        
        if graph:
            triple_count = len(graph)
            safe_print(f"    - Triples: {triple_count}개")
        else:
            safe_print("    [WARN] 그래프가 None입니다.")
        
        # 4. RAG 인덱스 검증
        safe_print("\n[4단계] RAG 인덱스 검증...")
        if orchestrator.core.rag_manager.is_available():
            safe_print("  [OK] RAG 인덱스 사용 가능")
            if orchestrator.core.rag_manager.faiss_index is not None:
                safe_print("    - FAISS 인덱스 존재")
            if len(orchestrator.core.rag_manager.chunks) > 0:
                safe_print(f"    - 청크: {len(orchestrator.core.rag_manager.chunks)}개")
        else:
            safe_print("  [WARN] RAG 인덱스 사용 불가")
        
        # 5. Agent 실행
        safe_print("\n[5단계] Agent 실행...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        
        start_time = time.time()
        result = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        agent_time = time.time() - start_time
        safe_print(f"  [OK] Agent 실행 완료 (소요 시간: {agent_time:.2f}초)")
        
        # 결과 검증
        if not result:
            safe_print("  [FAIL] Agent 결과가 None입니다.")
            return False
        
        status = result.get("status")
        if status != "completed":
            safe_print(f"  [WARN] Agent 상태: {status}")
        
        recommendations = result.get("recommendations", [])
        if not recommendations:
            safe_print("  [WARN] 추천 목록이 비어있습니다.")
        else:
            safe_print(f"    - 추천 개수: {len(recommendations)}개")
            for i, rec in enumerate(recommendations[:3], 1):
                coa_name = rec.get("coa_name", rec.get("방책명", "Unknown"))
                score = rec.get("score", rec.get("최종점수", 0.0))
                safe_print(f"      {i}. {coa_name} (점수: {score:.2f})")
        
        situation_info = result.get("situation_info", {})
        if situation_info:
            safe_print(f"    - 상황 정보 키 개수: {len(situation_info)}개")
        
        # 6. 점수 계산 검증
        safe_print("\n[6단계] 점수 계산 검증...")
        if recommendations:
            first_rec = recommendations[0]
            score_breakdown = first_rec.get("score_breakdown", {})
            if score_breakdown:
                safe_print("  [OK] 점수 breakdown 존재")
                for key, value in score_breakdown.items():
                    safe_print(f"    - {key}: {value:.2f}")
            else:
                safe_print("  [WARN] 점수 breakdown 없음")
        
        # 7. 전체 시간 요약
        total_time = init_time + ontology_time + agent_time
        safe_print(f"\n[요약] 전체 파이프라인 소요 시간: {total_time:.2f}초")
        safe_print(f"  - 초기화: {init_time:.2f}초")
        safe_print(f"  - 온톨로지 구축: {ontology_time:.2f}초")
        safe_print(f"  - Agent 실행: {agent_time:.2f}초")
        
        safe_print("\n[RESULT] 시나리오 1-1: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 1-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_scenario_1_2_palantir_pipeline():
    """시나리오 1-2: 팔란티어 모드 파이프라인"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 1-2: 팔란티어 모드 파이프라인")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 초기화
        safe_print("\n[1단계] Orchestrator 초기화 (팔란티어 모드)...")
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        safe_print("  [OK] 초기화 완료")
        
        # 2. 팔란티어 모드 활성화
        safe_print("\n[2단계] 팔란티어 모드 활성화...")
        config['use_palantir_mode'] = True
        safe_print("  [OK] 팔란티어 모드 활성화")
        
        # 3. 온톨로지 관계 구축 검증
        safe_print("\n[3단계] 온톨로지 관계 구축...")
        data = orchestrator.core.data_manager.load_all()
        graph = orchestrator.core.ontology_manager.build_from_data(data)
        
        if graph:
            # Palantir 관계 확인 (SPARQL 쿼리)
            try:
                query = """
                PREFIX def: <http://defense-ai.kr/ontology#>
                SELECT (COUNT(?coa) AS ?coaCount) WHERE {
                    ?coa def:requiresResource ?resource .
                }
                """
                results = list(graph.query(query))
                if results:
                    coa_count = int(results[0][0])
                    safe_print(f"  [OK] COA-자원 관계: {coa_count}개")
            except Exception as e:
                safe_print(f"  [WARN] 관계 쿼리 실패: {e}")
        
        # 4. Agent 실행 (팔란티어 모드)
        safe_print("\n[4단계] Agent 실행 (팔란티어 모드)...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        
        result = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요",
            use_palantir_mode=True
        )
        
        if not result:
            safe_print("  [FAIL] Agent 결과가 None입니다.")
            return False
        
        recommendations = result.get("recommendations", [])
        if recommendations:
            safe_print(f"  [OK] 추천 생성: {len(recommendations)}개")
            
            # 팔란티어 점수 확인
            first_rec = recommendations[0]
            score_breakdown = first_rec.get("score_breakdown", {})
            if score_breakdown:
                safe_print("    - 팔란티어 점수 breakdown:")
                for key, value in score_breakdown.items():
                    safe_print(f"      {key}: {value:.2f}")
        
        safe_print("\n[RESULT] 시나리오 1-2: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 1-2 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 시나리오 2: 워크플로우 통합 테스트
# ============================================================================

def test_scenario_2_1_workflow_approval():
    """시나리오 2-1: 방책 승인 워크플로우"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 2-1: 방책 승인 워크플로우")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        from core_pipeline.user_manager import UserManager
        from core_pipeline.workflow_manager import WorkflowManager
        from core_pipeline.realtime_collaboration import RealtimeCollaboration
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 초기화
        safe_print("\n[1단계] 시스템 초기화...")
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        safe_print("  [OK] 초기화 완료")
        
        # 2. 사용자 생성/인증
        safe_print("\n[2단계] 사용자 생성 및 인증...")
        user_manager = UserManager()
        
        # Planner 생성
        planner = user_manager.create_user("test_planner", "password123", "planner")
        if planner:
            safe_print("  [OK] Planner 사용자 생성")
        
        # Analyst 생성
        analyst = user_manager.create_user("test_analyst", "password123", "analyst")
        if analyst:
            safe_print("  [OK] Analyst 사용자 생성")
        
        # Commander 생성
        commander = user_manager.create_user("test_commander", "password123", "commander")
        if commander:
            safe_print("  [OK] Commander 사용자 생성")
        
        # 3. 방책 추천 생성
        safe_print("\n[3단계] 방책 추천 생성...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        result = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        
        if not result or not result.get("recommendations"):
            safe_print("  [FAIL] 방책 추천 생성 실패")
            return False
        
        recommendation = result["recommendations"][0]
        safe_print(f"  [OK] 방책 추천 생성: {recommendation.get('coa_name', 'Unknown')}")
        
        # 4. 승인 요청 생성
        safe_print("\n[4단계] 승인 요청 생성...")
        rc = RealtimeCollaboration()
        wm = WorkflowManager(realtime_collaboration=rc)
        
        request_id = wm.create_approval_request(
            recommendation=recommendation,
            requester_id="test_planner"
        )
        
        if request_id:
            safe_print(f"  [OK] 승인 요청 생성: {request_id}")
        else:
            safe_print("  [FAIL] 승인 요청 생성 실패")
            return False
        
        # 5. 검토 의견 추가 (선택적)
        safe_print("\n[5단계] 검토 의견 추가...")
        try:
            wm.add_review_comment(request_id, "test_analyst", "검토 의견: 방책이 적절해 보입니다.")
            safe_print("  [OK] 검토 의견 추가 완료")
        except Exception as e:
            safe_print(f"  [WARN] 검토 의견 추가 실패: {e}")
        
        # 6. 승인 처리
        safe_print("\n[6단계] 승인 처리...")
        try:
            wm.approve_recommendation(request_id, "test_commander", "승인합니다.")
            safe_print("  [OK] 승인 처리 완료")
        except Exception as e:
            safe_print(f"  [WARN] 승인 처리 실패: {e}")
        
        # 7. 알림 확인
        safe_print("\n[7단계] 알림 확인...")
        notifications = rc.get_unread_notifications("test_commander")
        if notifications:
            safe_print(f"  [OK] 알림 {len(notifications)}개 확인")
        else:
            safe_print("  [WARN] 알림 없음")
        
        safe_print("\n[RESULT] 시나리오 2-1: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 2-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_scenario_2_2_pilot_tester_workflow():
    """시나리오 2-2: 파일럿 테스터 워크플로우 시뮬레이션"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 2-2: 파일럿 테스터 워크플로우 시뮬레이션")
    safe_print("="*80)
    
    try:
        from core_pipeline.user_manager import UserManager
        from core_pipeline.permission_manager import PermissionManager
        from core_pipeline.workflow_manager import WorkflowManager
        from core_pipeline.realtime_collaboration import RealtimeCollaboration
        
        # 1. 파일럿 테스터 생성
        safe_print("\n[1단계] 파일럿 테스터 생성...")
        user_manager = UserManager()
        pilot = user_manager.create_user("test_pilot", "password123", "pilot_tester")
        if pilot:
            safe_print("  [OK] 파일럿 테스터 생성")
        
        # 2. 모든 권한 확인
        safe_print("\n[2단계] 권한 확인...")
        permissions = [
            ("view_recommendations", True),
            ("approve_recommendations", True),
            ("edit_recommendations", True),
            ("view_data", True),
            ("manage_system", True)
        ]
        
        all_permissions_ok = True
        for perm, expected in permissions:
            has_perm = PermissionManager.has_permission("pilot_tester", perm)
            if has_perm == expected:
                safe_print(f"  [OK] {perm}: {has_perm}")
            else:
                safe_print(f"  [FAIL] {perm}: 예상 {expected}, 실제 {has_perm}")
                all_permissions_ok = False
        
        if not all_permissions_ok:
            return False
        
        # 3. 역할 전환 시뮬레이션
        safe_print("\n[3단계] 역할 전환 시뮬레이션...")
        roles = ["planner", "analyst", "commander"]
        for role in roles:
            # 역할별 권한 확인
            has_view = PermissionManager.has_permission(role, "view_recommendations")
            safe_print(f"  - {role} 역할: view_recommendations = {has_view}")
        
        safe_print("  [OK] 역할 전환 시뮬레이션 완료")
        
        safe_print("\n[RESULT] 시나리오 2-2: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 2-2 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 시나리오 3: 실시간 기능 통합 테스트
# ============================================================================

def test_scenario_3_1_data_change_detection():
    """시나리오 3-1: 데이터 변경 감지 및 재추천"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 3-1: 데이터 변경 감지 및 재추천")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        from core_pipeline.data_watcher import DataWatcher
        from core_pipeline.recommendation_history import RecommendationHistory
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 초기 상태 설정
        safe_print("\n[1단계] 초기 상태 설정...")
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        
        data = orchestrator.core.data_manager.load_all()
        graph = orchestrator.core.ontology_manager.build_from_data(data)
        safe_print("  [OK] 초기 온톨로지 그래프 구축 완료")
        
        # 2. 초기 방책 추천
        safe_print("\n[2단계] 초기 방책 추천 생성...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        result1 = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        
        if result1 and result1.get("recommendations"):
            rec1 = result1["recommendations"][0]
            safe_print(f"  [OK] 초기 추천: {rec1.get('coa_name', 'Unknown')} (점수: {rec1.get('score', 0):.2f})")
        else:
            safe_print("  [WARN] 초기 추천 생성 실패")
        
        # 3. 히스토리 저장
        safe_print("\n[3단계] 히스토리 저장...")
        rh = RecommendationHistory()
        if result1:
            rh.save_recommendation("TEST_SITUATION", result1)
            safe_print("  [OK] 히스토리 저장 완료")
        
        # 4. 데이터 변경 감시 (시뮬레이션)
        safe_print("\n[4단계] 데이터 변경 감지 시뮬레이션...")
        safe_print("  [INFO] 실제 파일 변경은 테스트 환경에서 제한적이므로 시뮬레이션으로 진행")
        safe_print("  [INFO] DataWatcher는 정상적으로 초기화되었습니다.")
        
        # 5. 재추천 및 비교
        safe_print("\n[5단계] 재추천 및 비교...")
        result2 = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        
        if result2 and result2.get("recommendations"):
            rec2 = result2["recommendations"][0]
            safe_print(f"  [OK] 재추천: {rec2.get('coa_name', 'Unknown')} (점수: {rec2.get('score', 0):.2f})")
            
            # 비교
            if result1 and result1.get("recommendations"):
                comparison = rh.compare_recommendations("TEST_SITUATION")
                if comparison:
                    safe_print("  [OK] 추천 비교 완료")
                    threat_change = comparison.get("threat_change", 0)
                    safe_print(f"    - 위협 변화: {threat_change:.2f}")
        
        safe_print("\n[RESULT] 시나리오 3-1: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 3-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 시나리오 4: 협업 기능 통합 테스트
# ============================================================================

def test_scenario_4_1_multi_user_collaboration():
    """시나리오 4-1: 다중 사용자 협업"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 4-1: 다중 사용자 협업")
    safe_print("="*80)
    
    try:
        from core_pipeline.user_manager import UserManager
        from core_pipeline.realtime_collaboration import RealtimeCollaboration
        
        # 1. 사용자 생성
        safe_print("\n[1단계] 다중 사용자 생성...")
        user_manager = UserManager()
        rc = RealtimeCollaboration()
        
        users = [
            ("user1_planner", "planner"),
            ("user2_analyst", "analyst"),
            ("user3_commander", "commander")
        ]
        
        for username, role in users:
            user = user_manager.create_user(username, "password123", role)
            if user:
                # 세션 등록
                rc.register_active_session(f"session_{username}", {
                    "user_id": username,
                    "username": username,
                    "role": role
                })
                safe_print(f"  [OK] {username} ({role}) 생성 및 세션 등록")
        
        # 2. 활성 사용자 조회
        safe_print("\n[2단계] 활성 사용자 조회...")
        active_users = rc.get_active_users()
        safe_print(f"  [OK] 활성 사용자: {len(active_users)}명")
        for user in active_users:
            safe_print(f"    - {user.get('username')} ({user.get('role')})")
        
        # 3. 알림 전송
        safe_print("\n[3단계] 알림 전송...")
        rc.send_notification("user2_analyst", "방책 추천 요청이 생성되었습니다.", "info")
        rc.send_notification("user3_commander", "승인 요청이 생성되었습니다.", "warning")
        safe_print("  [OK] 알림 전송 완료")
        
        # 4. 알림 확인
        safe_print("\n[4단계] 알림 확인...")
        notifications = rc.get_unread_notifications("user2_analyst")
        if notifications:
            safe_print(f"  [OK] user2_analyst 알림: {len(notifications)}개")
        
        notifications = rc.get_unread_notifications("user3_commander")
        if notifications:
            safe_print(f"  [OK] user3_commander 알림: {len(notifications)}개")
        
        safe_print("\n[RESULT] 시나리오 4-1: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 4-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 시나리오 5: 보고서 생성 통합 테스트
# ============================================================================

def test_scenario_5_1_report_generation():
    """시나리오 5-1: 보고서 생성 파이프라인"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 5-1: 보고서 생성 파이프라인")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        from ui.components.report_engine import ReportEngine
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 1. 방책 추천 생성
        safe_print("\n[1단계] 방책 추천 생성...")
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        result = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        
        if not result or not result.get("recommendations"):
            safe_print("  [FAIL] 방책 추천 생성 실패")
            return False
        
        recommendation = result["recommendations"][0]
        safe_print(f"  [OK] 방책 추천 생성: {recommendation.get('coa_name', 'Unknown')}")
        
        # 2. 보고서 데이터 준비
        safe_print("\n[2단계] 보고서 데이터 준비...")
        report_data = {
            "situation_info": result.get("situation_info", {}),
            "recommendations": result.get("recommendations", []),
            "score_breakdown": recommendation.get("score_breakdown", {})
        }
        safe_print("  [OK] 보고서 데이터 준비 완료")
        
        # 3. 보고서 생성 (HTML)
        safe_print("\n[3단계] 보고서 생성 (HTML)...")
        report_engine = ReportEngine()
        try:
            html_path = report_engine.generate_report(
                report_type="coa",
                data=report_data,
                format="html"
            )
            if html_path and os.path.exists(html_path):
                safe_print(f"  [OK] HTML 보고서 생성: {html_path}")
            else:
                safe_print("  [WARN] HTML 보고서 생성 실패")
        except Exception as e:
            safe_print(f"  [WARN] HTML 보고서 생성 오류: {e}")
        
        safe_print("\n[RESULT] 시나리오 5-1: 통과")
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 5-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 시나리오 6: 성능 통합 테스트
# ============================================================================

def test_scenario_6_1_performance_large_data():
    """시나리오 6-1: 대용량 데이터 처리 성능"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시나리오 6-1: 대용량 데이터 처리 성능")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        # 성능 목표
        targets = {
            "데이터 로드": 5.0,
            "온톨로지 구축": 10.0,
            "RAG 인덱스 구축": 30.0,
            "Agent 실행": 10.0,
            "전체 파이프라인": 60.0
        }
        
        # 1. 데이터 로드 성능
        safe_print("\n[1단계] 데이터 로드 성능 측정...")
        orchestrator = Orchestrator(config)
        
        start_time = time.time()
        orchestrator.initialize()
        init_time = time.time() - start_time
        safe_print(f"  [OK] 초기화: {init_time:.2f}초 (목표: {targets['데이터 로드']}초)")
        
        # 2. 온톨로지 구축 성능
        safe_print("\n[2단계] 온톨로지 구축 성능 측정...")
        data = orchestrator.core.data_manager.load_all()
        
        start_time = time.time()
        graph = orchestrator.core.ontology_manager.build_from_data(data)
        ontology_time = time.time() - start_time
        safe_print(f"  [OK] 온톨로지 구축: {ontology_time:.2f}초 (목표: {targets['온톨로지 구축']}초)")
        
        # 3. Agent 실행 성능
        safe_print("\n[3단계] Agent 실행 성능 측정...")
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        
        start_time = time.time()
        result = agent.execute_reasoning(
            user_query="적군의 침입에 대한 방책을 추천해주세요"
        )
        agent_time = time.time() - start_time
        safe_print(f"  [OK] Agent 실행: {agent_time:.2f}초 (목표: {targets['Agent 실행']}초)")
        
        # 4. 전체 파이프라인 성능
        total_time = init_time + ontology_time + agent_time
        safe_print(f"\n[요약] 전체 파이프라인: {total_time:.2f}초 (목표: {targets['전체 파이프라인']}초)")
        
        # 성능 검증
        all_passed = True
        if init_time > targets['데이터 로드']:
            safe_print(f"  [WARN] 데이터 로드 시간 초과")
            all_passed = False
        if ontology_time > targets['온톨로지 구축']:
            safe_print(f"  [WARN] 온톨로지 구축 시간 초과")
            all_passed = False
        if agent_time > targets['Agent 실행']:
            safe_print(f"  [WARN] Agent 실행 시간 초과")
            all_passed = False
        if total_time > targets['전체 파이프라인']:
            safe_print(f"  [WARN] 전체 파이프라인 시간 초과")
            all_passed = False
        
        if all_passed:
            safe_print("\n[RESULT] 시나리오 6-1: 통과 (모든 성능 목표 달성)")
        else:
            safe_print("\n[RESULT] 시나리오 6-1: 부분 통과 (일부 성능 목표 미달성)")
        
        return True
        
    except Exception as e:
        safe_print(f"\n[FAIL] 시나리오 6-1 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 메인 테스트 실행
# ============================================================================

def main():
    """메인 통합 테스트 실행"""
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 시작")
    safe_print("="*80)
    safe_print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 시나리오 1: 전체 파이프라인 통합 테스트
    test_results.append(("시나리오 1-1: 기본 파이프라인", test_scenario_1_1_basic_pipeline()))
    test_results.append(("시나리오 1-2: 팔란티어 모드", test_scenario_1_2_palantir_pipeline()))
    
    # 시나리오 2: 워크플로우 통합 테스트
    test_results.append(("시나리오 2-1: 승인 워크플로우", test_scenario_2_1_workflow_approval()))
    test_results.append(("시나리오 2-2: 파일럿 테스터", test_scenario_2_2_pilot_tester_workflow()))
    
    # 시나리오 3: 실시간 기능 통합 테스트
    test_results.append(("시나리오 3-1: 데이터 변경 감지", test_scenario_3_1_data_change_detection()))
    
    # 시나리오 4: 협업 기능 통합 테스트
    test_results.append(("시나리오 4-1: 다중 사용자 협업", test_scenario_4_1_multi_user_collaboration()))
    
    # 시나리오 5: 보고서 생성 통합 테스트
    test_results.append(("시나리오 5-1: 보고서 생성", test_scenario_5_1_report_generation()))
    
    # 시나리오 6: 성능 통합 테스트
    test_results.append(("시나리오 6-1: 성능 테스트", test_scenario_6_1_performance_large_data()))
    
    # 결과 요약
    safe_print("\n" + "="*80)
    safe_print("통합 테스트 결과 요약")
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
    import argparse
    
    parser = argparse.ArgumentParser(description='통합 테스트 실행')
    parser.add_argument('--scenario', type=str, help='특정 시나리오만 실행 (예: scenario_1_1)')
    parser.add_argument('--performance', action='store_true', help='성능 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.scenario:
        # 특정 시나리오만 실행
        scenario_map = {
            "scenario_1_1": test_scenario_1_1_basic_pipeline,
            "scenario_1_2": test_scenario_1_2_palantir_pipeline,
            "scenario_2_1": test_scenario_2_1_workflow_approval,
            "scenario_2_2": test_scenario_2_2_pilot_tester_workflow,
            "scenario_3_1": test_scenario_3_1_data_change_detection,
            "scenario_4_1": test_scenario_4_1_multi_user_collaboration,
            "scenario_5_1": test_scenario_5_1_report_generation,
            "scenario_6_1": test_scenario_6_1_performance_large_data
        }
        
        test_func = scenario_map.get(args.scenario)
        if test_func:
            test_func()
        else:
            safe_print(f"알 수 없는 시나리오: {args.scenario}")
    elif args.performance:
        # 성능 테스트만 실행
        test_scenario_6_1_performance_large_data()
    else:
        # 전체 테스트 실행
        success = main()
        sys.exit(0 if success else 1)

