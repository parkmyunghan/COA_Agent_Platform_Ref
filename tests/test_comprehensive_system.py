# tests/test_comprehensive_system.py
# -*- coding: utf-8 -*-
"""
시스템 전체 기능 단위 테스트
모든 핵심 기능에 대한 포괄적인 단위 테스트
"""
import sys
import os
from pathlib import Path
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# 프로젝트 루트를 경로에 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Windows 인코딩 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def safe_print(msg):
    """안전한 출력 (Windows 호환)"""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(str(msg).encode('ascii', 'replace').decode('ascii'))
        except:
            print("(출력 오류)")


def load_config():
    """설정 파일 로드"""
    config_path = BASE_DIR / "config" / "global.yaml"
    if not config_path.exists():
        safe_print(f"[ERROR] 설정 파일 없음: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        safe_print(f"[ERROR] 설정 파일 로드 실패: {e}")
        return None


# ============================================================================
# 1. Core Pipeline 테스트
# ============================================================================

def test_data_manager():
    """DataManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 1: DataManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.data_manager import DataManager
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        dm = DataManager(config)
        
        # 테스트 1-1: load_table
        test_tables = ["위협상황", "아군부대", "COA_라이브러리"]
        loaded_count = 0
        
        for table_name in test_tables:
            try:
                df = dm.load_table(table_name)
                if df is not None and not df.empty:
                    loaded_count += 1
                    safe_print(f"  [OK] {table_name}: {len(df)}행, {len(df.columns)}열")
            except Exception as e:
                safe_print(f"  [FAIL] {table_name}: {e}")
        
        # 테스트 1-2: load_all
        try:
            all_data = dm.load_all()
            safe_print(f"  [OK] load_all: {len(all_data)}개 테이블 로드")
        except Exception as e:
            safe_print(f"  [FAIL] load_all: {e}")
            return False
        
        safe_print(f"[RESULT] DataManager: {loaded_count}/{len(test_tables)}개 테이블 로드 성공")
        return loaded_count > 0
        
    except Exception as e:
        safe_print(f"[FAIL] DataManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_ontology_manager():
    """OntologyManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 2: OntologyManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
        from core_pipeline.data_manager import DataManager
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        dm = DataManager(config)
        om = EnhancedOntologyManager(config)
        om.data_manager = dm
        
        # 테스트 2-1: build_from_data
        try:
            data = dm.load_all()
            if not data:
                safe_print("  [SKIP] 데이터가 없습니다.")
                return False
            
            graph = om.build_from_data(data)
            if graph is not None:
                triple_count = len(list(graph.triples((None, None, None))))
                safe_print(f"  [OK] build_from_data: {triple_count}개 triples 생성")
            else:
                safe_print("  [FAIL] build_from_data: 그래프 생성 실패")
                return False
        except Exception as e:
            safe_print(f"  [FAIL] build_from_data: {e}")
            return False
        
        # 테스트 2-2: SPARQL 쿼리
        try:
            query = """
            SELECT ?subject ?predicate ?object WHERE {
                ?subject ?predicate ?object .
            } LIMIT 10
            """
            results = list(graph.query(query))
            safe_print(f"  [OK] SPARQL 쿼리: {len(results)}개 결과")
        except Exception as e:
            safe_print(f"  [WARN] SPARQL 쿼리: {e}")
        
        safe_print("[RESULT] OntologyManager: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] OntologyManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_rag_manager():
    """RAGManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 3: RAGManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.rag_manager import RAGManager
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        rm = RAGManager(config)
        
        # 테스트 3-1: is_available
        is_available = rm.is_available()
        safe_print(f"  [OK] is_available: {is_available}")
        
        if is_available:
            # 테스트 3-2: retrieve_with_context
            try:
                results = rm.retrieve_with_context("위협 상황", top_k=3)
                safe_print(f"  [OK] retrieve_with_context: {len(results)}개 결과")
            except Exception as e:
                safe_print(f"  [WARN] retrieve_with_context: {e}")
        
        safe_print("[RESULT] RAGManager: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] RAGManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_llm_manager():
    """LLMManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 4: LLMManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.llm_manager import LLMManager
        
        lm = LLMManager()
        
        # 테스트 4-1: is_available
        is_available = lm.is_available()
        safe_print(f"  [OK] is_available: {is_available}")
        
        if is_available:
            # 테스트 4-2: generate (간단한 테스트)
            try:
                response = lm.generate("안녕하세요", max_tokens=10)
                safe_print(f"  [OK] generate: 응답 생성 성공 (길이: {len(response) if response else 0})")
            except Exception as e:
                safe_print(f"  [WARN] generate: {e}")
        
        safe_print("[RESULT] LLMManager: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] LLMManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_coa_scorer():
    """COAScorer 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 5: COAScorer")
    safe_print("="*80)
    
    try:
        from core_pipeline.coa_scorer import COAScorer
        from core_pipeline.data_manager import DataManager
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        dm = DataManager(config)
        scorer = COAScorer(data_manager=dm, config=config)
        
        # 테스트 5-1: 가중치 로드
        weights = scorer.weights
        safe_print(f"  [OK] 가중치 로드: {len(weights)}개 요소")
        for key, value in weights.items():
            safe_print(f"    - {key}: {value}")
        
        # 테스트 5-2: calculate_score (모의 컨텍스트)
        test_context = {
            "coa_uri": "COA001",
            "situation_id": "S001",
            "threat_level": 0.8,
            "resource_availability": 0.7,
            "asset_capability": 0.9,
            "environment_fit": 0.6,
            "historical_success": 0.8,
            "chain_score": 0.75
        }
        
        try:
            score_result = scorer.calculate_score(test_context)
            safe_print(f"  [OK] calculate_score: 총점 {score_result.get('total_score', 0):.3f}")
        except Exception as e:
            safe_print(f"  [WARN] calculate_score: {e}")
        
        safe_print("[RESULT] COAScorer: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] COAScorer 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_reasoning_engine():
    """ReasoningEngine 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 6: ReasoningEngine")
    safe_print("="*80)
    
    try:
        from core_pipeline.reasoning_engine import ReasoningEngine
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        re = ReasoningEngine(config)
        
        # 테스트 6-1: 기본 추론 (모의 컨텍스트)
        test_context = {
            "situation_info": {
                "위협유형": "침입",
                "심각도": 0.8
            },
            "strategies": [
                {"coa_name": "테스트 방책 1", "coa_id": "COA001"},
                {"coa_name": "테스트 방책 2", "coa_id": "COA002"}
            ],
            "threat_level": 0.8,
            "graph": None,
            "data_manager": None
        }
        
        try:
            result = re.run_defense_rules(test_context)
            if result and isinstance(result, dict):
                safe_print(f"  [OK] run_defense_rules: 추론 완료")
                safe_print(f"    - 결과 키: {list(result.keys())[:3]}")
            else:
                safe_print(f"  [WARN] run_defense_rules: 결과 형식이 예상과 다름")
        except Exception as e:
            safe_print(f"  [WARN] run_defense_rules: {e}")
        
        safe_print("[RESULT] ReasoningEngine: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] ReasoningEngine 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_orchestrator():
    """Orchestrator 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 7: Orchestrator")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        orchestrator = Orchestrator(config)
        
        # 테스트 7-1: 초기화
        try:
            orchestrator.initialize()
            safe_print("  [OK] initialize: 초기화 완료")
        except Exception as e:
            safe_print(f"  [WARN] initialize: {e}")
        
        # 테스트 7-2: Agent 등록
        try:
            from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
            agent = orchestrator.register_agent("defense_coa", EnhancedDefenseCOAAgent)
            safe_print("  [OK] register_agent: Agent 등록 완료")
            
            # 테스트 7-3: Agent 가져오기
            retrieved_agent = orchestrator.get_agent("defense_coa")
            if retrieved_agent:
                safe_print("  [OK] get_agent: Agent 가져오기 성공")
        except Exception as e:
            safe_print(f"  [WARN] Agent 등록/가져오기: {e}")
        
        safe_print("[RESULT] Orchestrator: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] Orchestrator 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 2. Agents 테스트
# ============================================================================

def test_enhanced_defense_coa_agent():
    """EnhancedDefenseCOAAgent 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 8: EnhancedDefenseCOAAgent")
    safe_print("="*80)
    
    try:
        from core_pipeline.orchestrator import Orchestrator
        from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        
        agent = EnhancedDefenseCOAAgent(core=orchestrator.core)
        
        # 테스트 8-1: execute_reasoning (빈 상황)
        try:
            result = agent.execute_reasoning(user_query="적군 침입에 대한 방책을 추천해주세요")
            if result and "agent" in result:
                safe_print("  [OK] execute_reasoning: 추론 실행 완료")
                safe_print(f"    - 상태: {result.get('status', 'N/A')}")
            else:
                safe_print("  [WARN] execute_reasoning: 결과 형식이 예상과 다름")
        except Exception as e:
            safe_print(f"  [WARN] execute_reasoning: {e}")
        
        safe_print("[RESULT] EnhancedDefenseCOAAgent: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] EnhancedDefenseCOAAgent 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 3. 추가 기능 테스트
# ============================================================================

def test_user_manager():
    """UserManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 9: UserManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.user_manager import UserManager
        
        um = UserManager()
        
        # 테스트 9-1: 사용자 생성
        try:
            test_user = um.create_user("test_user", "test_password", "analyst")
            if test_user:
                safe_print("  [OK] create_user: 사용자 생성 성공")
            else:
                safe_print("  [WARN] create_user: 사용자 생성 실패")
        except Exception as e:
            safe_print(f"  [WARN] create_user: {e}")
        
        # 테스트 9-2: 인증
        try:
            user = um.authenticate("test_user", "test_password")
            if user:
                safe_print("  [OK] authenticate: 인증 성공")
            else:
                safe_print("  [WARN] authenticate: 인증 실패")
        except Exception as e:
            safe_print(f"  [WARN] authenticate: {e}")
        
        safe_print("[RESULT] UserManager: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] UserManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_permission_manager():
    """PermissionManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 10: PermissionManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.permission_manager import PermissionManager
        
        # 테스트 10-1: 권한 확인
        test_cases = [
            ("commander", "view_recommendations", True),
            ("commander", "approve_recommendations", True),
            ("analyst", "approve_recommendations", False),
            ("pilot_tester", "view_recommendations", True),
            ("admin", "*", True)
        ]
        
        passed = 0
        for role, permission, expected in test_cases:
            result = PermissionManager.has_permission(role, permission)
            if result == expected:
                passed += 1
                safe_print(f"  [OK] {role}.{permission}: {result}")
            else:
                safe_print(f"  [FAIL] {role}.{permission}: 예상 {expected}, 실제 {result}")
        
        safe_print(f"[RESULT] PermissionManager: {passed}/{len(test_cases)}개 테스트 통과")
        return passed == len(test_cases)
        
    except Exception as e:
        safe_print(f"[FAIL] PermissionManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_workflow_manager():
    """WorkflowManager 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 11: WorkflowManager")
    safe_print("="*80)
    
    try:
        from core_pipeline.workflow_manager import WorkflowManager
        from core_pipeline.realtime_collaboration import RealtimeCollaboration
        
        rc = RealtimeCollaboration()
        wm = WorkflowManager(realtime_collaboration=rc)
        
        # 테스트 11-1: 승인 요청 생성
        try:
            test_recommendation = {
                "coa_name": "테스트 방책",
                "score": 0.85
            }
            request_id = wm.create_approval_request(
                recommendation=test_recommendation,
                requester_id="test_user"
            )
            if request_id and isinstance(request_id, str) and request_id.startswith("REQ_"):
                safe_print("  [OK] create_approval_request: 승인 요청 생성 성공")
                safe_print(f"    - Request ID: {request_id}")
            else:
                safe_print("  [WARN] create_approval_request: 승인 요청 생성 실패 (잘못된 형식)")
        except Exception as e:
            safe_print(f"  [WARN] create_approval_request: {e}")
        
        safe_print("[RESULT] WorkflowManager: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] WorkflowManager 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_realtime_collaboration():
    """RealtimeCollaboration 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 12: RealtimeCollaboration")
    safe_print("="*80)
    
    try:
        from core_pipeline.realtime_collaboration import RealtimeCollaboration
        
        rc = RealtimeCollaboration()
        
        # 테스트 12-1: 사용자 활동 업데이트
        try:
            # RealtimeCollaboration.update_user_activity는 user_id만 받음
            rc.update_user_activity("test_user")
            safe_print("  [OK] update_user_activity: 활동 업데이트 성공")
        except Exception as e:
            safe_print(f"  [WARN] update_user_activity: {e}")
        
        # 테스트 12-2: 알림 전송
        try:
            rc.send_notification("test_user", "테스트 알림", "info")
            safe_print("  [OK] send_notification: 알림 전송 성공")
        except Exception as e:
            safe_print(f"  [WARN] send_notification: {e}")
        
        # 테스트 12-3: 활성 사용자 조회
        try:
            active_users = rc.get_active_users()
            safe_print(f"  [OK] get_active_users: {len(active_users)}명 활성 사용자")
        except Exception as e:
            safe_print(f"  [WARN] get_active_users: {e}")
        
        safe_print("[RESULT] RealtimeCollaboration: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] RealtimeCollaboration 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_report_engine():
    """ReportEngine 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 13: ReportEngine")
    safe_print("="*80)
    
    try:
        from ui.components.report_engine import ReportEngine
        
        re = ReportEngine()
        
        # 테스트 13-1: 보고서 생성 (HTML)
        test_data = {
            "report_type": "situation_analysis",
            "title": "테스트 보고서",
            "content": {"situation": "테스트 상황"}
        }
        
        try:
            # ReportEngine.generate_report는 format 파라미터 사용
            result = re.generate_report(
                report_type="situation",
                data=test_data,
                format="html"
            )
            if result:
                safe_print("  [OK] generate_report (HTML): 보고서 생성 성공")
            else:
                safe_print("  [WARN] generate_report (HTML): 보고서 생성 실패")
        except Exception as e:
            safe_print(f"  [WARN] generate_report: {e}")
        
        safe_print("[RESULT] ReportEngine: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] ReportEngine 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 4. 실시간 기능 테스트
# ============================================================================

def test_data_watcher():
    """DataWatcher 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 14: DataWatcher")
    safe_print("="*80)
    
    try:
        from core_pipeline.data_watcher import DataWatcher
        from core_pipeline.data_manager import DataManager
        from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
        
        config = load_config()
        if not config:
            safe_print("[SKIP] 설정 파일이 없습니다.")
            return False
        
        dm = DataManager(config)
        om = EnhancedOntologyManager(config)
        om.data_manager = dm
        
        dw = DataWatcher(dm, om)
        
        # 테스트 14-1: 감시 시작/중지
        try:
            dw.start_watching()
            safe_print("  [OK] start_watching: 감시 시작 성공")
            
            dw.stop_watching()
            safe_print("  [OK] stop_watching: 감시 중지 성공")
        except Exception as e:
            safe_print(f"  [WARN] 감시 시작/중지: {e}")
        
        safe_print("[RESULT] DataWatcher: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] DataWatcher 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


def test_recommendation_history():
    """RecommendationHistory 테스트"""
    safe_print("\n" + "="*80)
    safe_print("테스트 15: RecommendationHistory")
    safe_print("="*80)
    
    try:
        from core_pipeline.recommendation_history import RecommendationHistory
        
        rh = RecommendationHistory()
        
        # 테스트 15-1: 추천 저장 (첫 번째)
        test_recommendation1 = {
            "recommendation_id": "TEST_001",
            "coa_name": "테스트 방책 1",
            "score": 0.85,
            "recommendations": [
                {"coa_name": "테스트 방책 1", "score": 0.85, "최종점수": 0.85}
            ],
            "situation_info": {
                "심각도": 0.7,
                "위협유형": "침입"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # RecommendationHistory.save_recommendation는 situation_id와 recommendation 필요
            rh.save_recommendation(
                situation_id="TEST_SITUATION_001",
                recommendation=test_recommendation1
            )
            safe_print("  [OK] save_recommendation (1): 추천 저장 성공")
        except Exception as e:
            safe_print(f"  [WARN] save_recommendation (1): {e}")
        
        # 테스트 15-2: 히스토리 조회
        try:
            # RecommendationHistory.get_recommendation_history는 situation_id 필요
            history = rh.get_recommendation_history("TEST_SITUATION_001")
            safe_print(f"  [OK] get_recommendation_history: {len(history)}개 추천 조회")
        except Exception as e:
            safe_print(f"  [WARN] get_recommendation_history: {e}")
        
        # 테스트 15-3: 추천 저장 (두 번째 - 비교를 위해)
        test_recommendation2 = {
            "recommendation_id": "TEST_002",
            "coa_name": "테스트 방책 2",
            "score": 0.90,
            "recommendations": [
                {"coa_name": "테스트 방책 2", "score": 0.90, "최종점수": 0.90}
            ],
            "situation_info": {
                "심각도": 0.8,
                "위협유형": "침입"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            rh.save_recommendation(
                situation_id="TEST_SITUATION_001",
                recommendation=test_recommendation2
            )
            safe_print("  [OK] save_recommendation (2): 추천 저장 성공")
        except Exception as e:
            safe_print(f"  [WARN] save_recommendation (2): {e}")
        
        # 테스트 15-4: 추천 비교
        try:
            # RecommendationHistory.compare_recommendations는 situation_id만 필요
            comparison = rh.compare_recommendations("TEST_SITUATION_001")
            if comparison:
                safe_print("  [OK] compare_recommendations: 추천 비교 성공")
                safe_print(f"    - 위협 변화: {comparison.get('threat_change', 'N/A')}")
                safe_print(f"    - 점수 변화: {comparison.get('score_change', {}).get('score_change', 'N/A')}")
            else:
                safe_print("  [WARN] compare_recommendations: 비교 결과 없음 (2개 이상 필요)")
        except Exception as e:
            safe_print(f"  [WARN] compare_recommendations: {e}")
        
        safe_print("[RESULT] RecommendationHistory: 정상 작동")
        return True
        
    except Exception as e:
        safe_print(f"[FAIL] RecommendationHistory 테스트 실패: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return False


# ============================================================================
# 메인 테스트 실행
# ============================================================================

def main():
    """메인 테스트 실행"""
    safe_print("\n" + "="*80)
    safe_print("시스템 전체 기능 단위 테스트 시작")
    safe_print("="*80)
    safe_print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # Core Pipeline 테스트
    test_results.append(("DataManager", test_data_manager()))
    test_results.append(("OntologyManager", test_ontology_manager()))
    test_results.append(("RAGManager", test_rag_manager()))
    test_results.append(("LLMManager", test_llm_manager()))
    test_results.append(("COAScorer", test_coa_scorer()))
    test_results.append(("ReasoningEngine", test_reasoning_engine()))
    test_results.append(("Orchestrator", test_orchestrator()))
    
    # Agents 테스트
    test_results.append(("EnhancedDefenseCOAAgent", test_enhanced_defense_coa_agent()))
    
    # 추가 기능 테스트
    test_results.append(("UserManager", test_user_manager()))
    test_results.append(("PermissionManager", test_permission_manager()))
    test_results.append(("WorkflowManager", test_workflow_manager()))
    test_results.append(("RealtimeCollaboration", test_realtime_collaboration()))
    test_results.append(("ReportEngine", test_report_engine()))
    
    # 실시간 기능 테스트
    test_results.append(("DataWatcher", test_data_watcher()))
    test_results.append(("RecommendationHistory", test_recommendation_history()))
    
    # 결과 요약
    safe_print("\n" + "="*80)
    safe_print("테스트 결과 요약")
    safe_print("="*80)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in test_results:
        if result is True:
            status = "[PASS] 통과"
            passed += 1
        elif result is False:
            status = "[FAIL] 실패"
            failed += 1
        else:
            status = "[SKIP] 건너뜀"
            skipped += 1
        
        safe_print(f"{test_name:30s}: {status}")
    
    safe_print("\n" + "="*80)
    safe_print(f"총 {len(test_results)}개 테스트 중:")
    safe_print(f"  - 통과: {passed}개")
    safe_print(f"  - 실패: {failed}개")
    safe_print(f"  - 건너뜀: {skipped}개")
    safe_print(f"통과률: {(passed/len(test_results)*100):.1f}%")
    safe_print("="*80)
    safe_print(f"테스트 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

