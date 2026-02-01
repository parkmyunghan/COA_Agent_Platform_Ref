# core_pipeline/coa_service.py
# -*- coding: utf-8 -*-
"""
COA Service
COA Agent 데모를 위한 통합 서비스 레이어
비즈니스 로직을 UI에서 분리하여 백엔드로 이동
"""
from typing import List, Dict, Optional
from pathlib import Path
import yaml
import pandas as pd

from core_pipeline.data_manager import DataManager
from core_pipeline.axis_state_builder import AxisStateBuilder
from core_pipeline.coa_engine import (
    COAGenerator,
    COAEvaluator,
    EnhancedCOAGenerator,
    EnhancedCOAEvaluator,
    SITREPParser,
    COAExplanationGenerator,
    COALLMAdapter
)
from core_pipeline.data_models import ThreatEvent, AxisState
from core_pipeline.coa_engine.coa_models import COA
from core_pipeline.coa_engine.coa_evaluator import COAEvaluationResult
from core_pipeline.relevance_mapper import RelevanceMapper
from core_pipeline.resource_priority_parser import ResourcePriorityParser
from core_pipeline.reasoning_engine import ReasoningEngine


class COAService:
    """COA Agent 데모를 위한 통합 서비스"""
    
    def __init__(self, config: Optional[Dict] = None, ontology_manager=None):
        """
        Args:
            config: 설정 딕셔너리 (None이면 global.yaml 로드)
            ontology_manager: OntologyManager 인스턴스 (선택적)
        """
        if config is None:
            config_path = Path(__file__).parent.parent / "config" / "global.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        
        self.config = config
        
        # 데이터 관리자 초기화
        self.data_manager = DataManager(config)
        
        # LLM/RAG 매니저는 선택적 (없어도 동작)
        self.llm_manager = None
        self.rag_manager = None
        self.ontology_manager = ontology_manager
        
        # Axis State Builder 초기화 (ontology_manager 전달)
        self.axis_state_builder = AxisStateBuilder(self.data_manager, ontology_manager)
        
        # 템플릿 로더 가져오기 (선택적)
        template_loader = None
        if self.data_manager:
            template_loader = self.data_manager.get_loader('COA_Library')
        
        # COA 엔진 초기화 (기본 버전)
        self.coa_generator = COAGenerator(
            use_llm_assistance=False,
            template_loader=template_loader
        )
        self.coa_evaluator = COAEvaluator()
        
        
        # [FIXED] 핵심 매퍼 인스턴스 싱글톤 관리 (중복 초기화 방지)
        self.relevance_mapper = None
        self.resource_parser = None
        
        try:
            base_path = Path(__file__).parent.parent
            data_lake_path = base_path / "data_lake"
            self.relevance_mapper = RelevanceMapper(data_lake_path=str(data_lake_path))
            self.resource_parser = ResourcePriorityParser()
            print("[INFO] COAService: RelevanceMapper 및 ResourcePriorityParser 초기화 완료")
        except Exception as e:
            print(f"[WARN] COAService: 매퍼 초기화 실패: {e}")
        
        # Reasoning Engine 초기화 (매퍼 주입)
        self.reasoning_engine = ReasoningEngine(
            config=self.config,
            relevance_mapper=self.relevance_mapper,
            resource_parser=self.resource_parser
        )
        
        # LLM 어댑터 (선택적)
        self.llm_adapter = None
    
    def initialize_llm_services(
        self,
        llm_manager=None,
        rag_manager=None,
        ontology_manager=None,
        use_enhanced: bool = True
    ):
        """
        LLM/RAG/온톨로지 서비스 초기화 (선택적)
        
        Args:
            llm_manager: LLMManager 인스턴스
            rag_manager: RAGManager 인스턴스
            ontology_manager: OntologyManager 인스턴스
            use_enhanced: Enhanced 버전 사용 여부
        """
        self.llm_manager = llm_manager
        self.rag_manager = rag_manager
        self.ontology_manager = ontology_manager
        
        # AxisStateBuilder에 온톨로지 매니저 주입
        if self.axis_state_builder:
            self.axis_state_builder.ontology_manager = ontology_manager
            # 데이터 캐시 초기화 (새로운 온톨로지 정보 반영)
            self.axis_state_builder._data_cache = None
            self.axis_state_builder._model_cache = {}
        
        # LLM 어댑터 초기화
        if llm_manager:
            self.llm_adapter = COALLMAdapter(
                llm_manager=llm_manager,
                rag_manager=rag_manager
            )
        
        # 템플릿 로더 가져오기 (선택적)
        template_loader = None
        if self.data_manager:
            template_loader = self.data_manager.get_loader('COA_Library')
        
        # Enhanced 버전 사용 시
        if use_enhanced:
            self.coa_generator = EnhancedCOAGenerator(
                ontology_manager=ontology_manager,
                rag_manager=rag_manager,
                llm_manager=llm_manager,
                use_llm_assistance=True,
                enable_ontology_enhancement=(ontology_manager is not None),
                template_loader=template_loader
            )
            self.coa_evaluator = EnhancedCOAEvaluator(
                ontology_manager=ontology_manager,
                rag_manager=rag_manager,
                llm_manager=llm_manager,
                reasoning_engine=self.reasoning_engine # [FIXED] 주입
            )
        else:
            # 기본 버전도 LLM 지원 가능하도록 설정
            self.coa_generator = COAGenerator(
                use_llm_assistance=(llm_manager is not None),
                llm_manager=llm_manager,
                template_loader=template_loader
            )
    
    def get_available_missions(self) -> List[Dict]:
        """
        사용 가능한 임무 목록 조회
        
        Returns:
            임무 정보 리스트 [{"mission_id": "...", "mission_name": "...", ...}]
        """
        try:
            missions_df = self.data_manager.load_table('임무정보')
            if missions_df is None or missions_df.empty:
                return []
            
            missions = []
            for _, row in missions_df.iterrows():
                # 지휘관의도 컬럼에서 값을 가져옴
                commander_intent_val = row.get('지휘관의도', '')
                # NaN 또는 빈 값 처리
                if pd.isna(commander_intent_val) or (isinstance(commander_intent_val, str) and commander_intent_val.strip() == ''):
                    commander_intent = None
                else:
                    commander_intent = str(commander_intent_val).strip()
                
                # 임무종류 처리
                mission_type_val = row.get('임무종류', '')
                mission_type = None
                if not pd.isna(mission_type_val) and str(mission_type_val).strip():
                    mission_type = str(mission_type_val).strip()
                
                # 주공축선ID 처리
                primary_axis_id_val = row.get('주공축선ID', '')
                primary_axis_id = None
                if not pd.isna(primary_axis_id_val) and str(primary_axis_id_val).strip():
                    primary_axis_id = str(primary_axis_id_val).strip()
                
                # 임무설명 처리
                description_val = row.get('임무설명', '')
                description = None
                if not pd.isna(description_val) and str(description_val).strip():
                    description = str(description_val).strip()
                
                # 작전지역 처리
                operation_area_val = row.get('작전지역', row.get('operation_area', row.get('구역', row.get('지역', ''))))
                operation_area = None
                if not pd.isna(operation_area_val) and str(operation_area_val).strip():
                    operation_area = str(operation_area_val).strip()
                
                missions.append({
                    "mission_id": str(row.get('임무ID', '')),
                    "mission_name": str(row.get('임무명', '')),
                    "mission_type": mission_type,
                    "commander_intent": commander_intent,
                    "primary_axis_id": primary_axis_id,
                    "operation_area": operation_area,
                    "description": description
                })
            return missions
        except Exception as e:
            print(f"[ERROR] Failed to load missions: {e}")
            return []
    
    def parse_sitrep_to_threat(
        self,
        sitrep_text: str,
        mission_id: Optional[str] = None,
        use_llm: bool = True
    ) -> Optional[ThreatEvent]:
        """
        SITREP 텍스트를 위협상황으로 변환
        
        Args:
            sitrep_text: 상황보고 텍스트
            mission_id: 임무ID (선택적, 위협상황 중심 접근 시 None 가능)
            use_llm: LLM 사용 여부
            
        Returns:
            ThreatEvent 객체 또는 None
        """
        if not self.llm_adapter:
            # LLM 어댑터가 없으면 직접 생성
            sitrep_parser = SITREPParser(llm_manager=self.llm_manager)
            return sitrep_parser.parse_sitrep_to_threat_event(
                sitrep_text, mission_id or "TEMP_MISSION", use_llm=use_llm
            )
        
        return self.llm_adapter.parse_sitrep(sitrep_text, mission_id or "TEMP_MISSION", use_llm=use_llm)
    
    def build_axis_states(self, mission_id: str) -> List[AxisState]:
        """
        임무ID를 기반으로 축선별 전장상태 빌드
        
        Args:
            mission_id: 임무ID
            
        Returns:
            AxisState 객체 리스트
        """
        return self.axis_state_builder.build_axis_states(mission_id)
    
    def generate_coas_unified(
        self,
        mission_id: Optional[str] = None,
        threat_id: Optional[str] = None,
        threat_event: Optional[ThreatEvent] = None,
        axis_states: Optional[List[AxisState]] = None,
        user_params: Optional[Dict] = None
    ) -> Dict:
        """
        통합 COA 생성 메서드 (두 가지 접근 방식 지원)
        
        Args:
            mission_id: 임무ID (임무 중심 접근)
            threat_id: 위협상황ID (위협상황 중심 접근)
            threat_event: ThreatEvent 객체 (위협상황 중심 접근)
            axis_states: 축선별 전장상태 (선택적, 없으면 자동 빌드)
            user_params: 사용자 설정 파라미터
                - max_coas: 최대 COA 수 (기본값: 5)
                - preferred_strategy: 선호 전략 ("defensive", "offensive", "balanced")
                - approach_mode: 접근 방식 ("auto", "threat_centered", "mission_centered")
        
        Returns:
            {
                "approach_mode": "threat_centered" | "mission_centered",
                "mission_id": str,
                "threat_id": Optional[str],
                "axis_states": [...],
                "coas": [...],
                "evaluations": [...],
                "top_coas": [...]
            }
        """
        import logging
        import time
        from common.logger import debug_log
        logger = logging.getLogger(__name__)
        
        start_time = time.time()
        user_params = user_params or {}
        approach_mode = user_params.get("approach_mode", "auto")
        
        # 기본 정보는 항상 기록
        logger.info(f"[COA Service] 통합 COA 생성 시작 - mission_id: {mission_id}, threat_id: {threat_id}, approach_mode: {approach_mode}")
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[COA Service] 상세 파라미터 - user_params: {user_params}")
        
        # 1. 접근 방식 결정
        if threat_id or threat_event:
            # 위협상황 중심 접근
            approach_mode = "threat_centered"
            debug_log(logger, f"[COA Service] 위협상황 중심 접근 방식 선택 - threat_id: {threat_id}")
            result = self._generate_coas_from_threat(
                threat_id=threat_id,
                threat_event=threat_event,
                axis_states=axis_states,
                user_params=user_params
            )
        elif mission_id:
            # 임무 중심 접근
            approach_mode = "mission_centered"
            debug_log(logger, f"[COA Service] 임무 중심 접근 방식 선택 - mission_id: {mission_id}")
            result = self._generate_coas_from_mission(
                mission_id=mission_id,
                axis_states=axis_states,
                user_params=user_params
            )
        else:
            logger.error("[COA Service] mission_id 또는 threat_id/threat_event 중 하나는 필수입니다.")
            return {
                "error": "mission_id 또는 threat_id/threat_event 중 하나는 필수입니다.",
                "approach_mode": None
            }
        
        elapsed_time = time.time() - start_time
        coas_count = len(result.get("coas", []))
        evaluations_count = len(result.get("evaluations", []))
        top_coas_count = len(result.get("top_coas", []))
        
        # 기본 정보는 항상 기록
        logger.info(f"[COA Service] 통합 COA 생성 완료 ({elapsed_time:.2f}초) - 생성된 COA: {coas_count}개, 상위 COA: {top_coas_count}개")
        # 상세 정보는 디버깅 모드에서만 기록
        debug_log(logger, f"[COA Service] 상세 결과 - 평가 완료: {evaluations_count}개")
        
        if top_coas_count > 0:
            top_coa = result.get("top_coas", [])[0]
            top_score = getattr(top_coa, 'total_score', None) if hasattr(top_coa, 'total_score') else top_coa.get('total_score', 'N/A') if isinstance(top_coa, dict) else 'N/A'
            top_name = getattr(top_coa, 'coa_name', None) if hasattr(top_coa, 'coa_name') else top_coa.get('coa_name', 'N/A') if isinstance(top_coa, dict) else 'N/A'
            debug_log(logger, f"[COA Service] 최상위 COA: {top_name} (점수: {top_score})")
        
        result["approach_mode"] = approach_mode
        return result
    
    def _generate_coas_from_threat(
        self,
        threat_id: Optional[str] = None,
        threat_event: Optional[ThreatEvent] = None,
        axis_states: Optional[List[AxisState]] = None,
        user_params: Optional[Dict] = None
    ) -> Dict:
        """
        위협상황 중심 COA 생성
        
        Args:
            threat_id: 위협상황ID
            threat_event: ThreatEvent 객체
            axis_states: 축선별 전장상태
            user_params: 사용자 설정
        
        Returns:
            COA 생성 결과
        """
        # 1. 위협상황 조회
        if threat_event is None:
            if threat_id:
                threat_events_df = self.data_manager.load_table('위협상황')
                if threat_events_df is None or threat_events_df.empty:
                    return {"error": f"위협상황 테이블을 불러올 수 없습니다."}
                
                # ID 컬럼 찾기 (대소문자 무시)
                id_col = None
                for col in threat_events_df.columns:
                    if col.upper() in ['ID', '위협ID', 'THREAT_ID', 'THREATID']:
                        id_col = col
                        break
                
                if id_col is None:
                    return {"error": "위협상황 테이블에 ID 컬럼을 찾을 수 없습니다."}
                
                threat_row = threat_events_df[threat_events_df[id_col] == threat_id]
                if threat_row.empty:
                    return {"error": f"위협상황을 찾을 수 없습니다: {threat_id}"}
                
                threat_event = ThreatEvent.from_row(threat_row.iloc[0].to_dict())
            else:
                return {"error": "threat_id 또는 threat_event가 필요합니다."}
        
        # 2. 위협상황에 맞는 임무 찾기
        mission_id = self._find_defense_mission_for_threat(threat_event)
        if not mission_id:
            return {"error": "위협상황에 맞는 방어임무를 찾을 수 없습니다."}
        
        # 3. 위협상황 중심으로 axis_states 빌드
        if axis_states is None:
            axis_states = self.axis_state_builder.build_axis_states_from_threat(
                threat_event, mission_id
            )
        
        if not axis_states:
            return {"error": "축선별 전장상태를 생성할 수 없습니다."}
        
        # 4. 방어 전략으로 COA 생성
        user_params = user_params or {}
        if "preferred_strategy" not in user_params:
            user_params["preferred_strategy"] = "defensive"  # 위협상황 중심은 방어 전략
        
        # 5. COA 생성 및 평가
        import logging
        import time
        from common.logger import debug_log
        logger = logging.getLogger(__name__)
        
        debug_log(logger, f"[COA Service] COA 생성 시작 - mission_id: {mission_id}, preferred_strategy: {user_params.get('preferred_strategy', 'defensive')}")
        coa_gen_start = time.time()
        
        coas = self.coa_generator.generate_coas(
            mission_id=mission_id,
            axis_states=axis_states,
            user_params=user_params
        )
        
        coa_gen_time = time.time() - coa_gen_start
        logger.info(f"[COA Service] COA 생성 완료 ({coa_gen_time:.2f}초) - 생성된 COA 수: {len(coas)}개")
        
        if not coas:
            logger.warning(f"[COA Service] COA 후보를 생성할 수 없습니다 - mission_id: {mission_id}, threat_id: {threat_event.threat_id}")
            return {
                "mission_id": mission_id,
                "threat_id": threat_event.threat_id,
                "axis_states": axis_states,
                "coas": [],
                "evaluations": [],
                "top_coas": [],
                "error": "COA 후보를 생성할 수 없습니다."
            }
        
        # 6. COA 평가
        debug_log(logger, f"[COA Service] COA 평가 시작 - 평가 대상: {len(coas)}개")
        eval_start = time.time()
        
        evaluations = self.coa_evaluator.evaluate_coas(
            mission_id=mission_id,
            axis_states=axis_states,
            coa_list=coas
        )
        
        eval_time = time.time() - eval_start
        logger.info(f"[COA Service] COA 평가 완료 ({eval_time:.2f}초) - 평가 완료: {len(evaluations)}개")
        
        evaluations_sorted = sorted(
            evaluations,
            key=lambda x: x.total_score,
            reverse=True
        )
        
        top_coas = evaluations_sorted[:3]
        
        return {
            "mission_id": mission_id,
            "threat_id": threat_event.threat_id,
            "threat_event": threat_event,
            "axis_states": axis_states,
            "coas": coas,
            "evaluations": evaluations_sorted,
            "top_coas": top_coas
        }
    
    def _generate_coas_from_mission(
        self,
        mission_id: str,
        axis_states: Optional[List[AxisState]] = None,
        user_params: Optional[Dict] = None
    ) -> Dict:
        """
        임무 중심 COA 생성 (기존 메서드 래핑)
        
        Args:
            mission_id: 임무ID
            axis_states: 축선별 전장상태
            user_params: 사용자 설정
        
        Returns:
            COA 생성 결과
        """
        # 기존 메서드 재사용
        return self.generate_and_evaluate_coas(
            mission_id=mission_id,
            axis_states=axis_states,
            user_params=user_params
        )
    
    def _find_defense_mission_for_threat(
        self,
        threat_event: ThreatEvent
    ) -> Optional[str]:
        """
        위협상황에 맞는 방어임무 찾기
        
        로직:
        1. 위협상황의 related_mission_id 확인
        2. 위협상황의 related_axis_id로 해당 축선의 방어임무 찾기
        3. 위협유형에 맞는 기본 방어임무 사용
        
        Args:
            threat_event: 위협상황 객체
        
        Returns:
            임무ID 또는 None
        """
        missions_df = self.data_manager.load_table('임무정보')
        if missions_df is None or missions_df.empty:
            return None
        
        # 방법 1: 위협상황에 이미 임무가 연결되어 있으면 사용
        if threat_event.related_mission_id:
            mission_id_col = None
            mission_type_col = None
            for col in missions_df.columns:
                if col.upper() in ['임무ID', 'MISSION_ID', 'MISSIONID']:
                    mission_id_col = col
                elif col.upper() in ['임무종류', 'MISSION_TYPE', 'MISSIONTYPE']:
                    mission_type_col = col
            
            if mission_id_col:
                mission_row = missions_df[missions_df[mission_id_col] == threat_event.related_mission_id]
                if not mission_row.empty:
                    if mission_type_col:
                        mission_type = mission_row.iloc[0].get(mission_type_col, '')
                        if mission_type in ['방어', 'defense', 'DEFENSE']:
                            return threat_event.related_mission_id
                    else:
                        return threat_event.related_mission_id
        
        # 방법 2: 위협상황의 축선으로 방어임무 찾기
        if threat_event.related_axis_id:
            mission_id_col = None
            mission_type_col = None
            primary_axis_col = None
            priority_col = None
            
            for col in missions_df.columns:
                if col.upper() in ['임무ID', 'MISSION_ID', 'MISSIONID']:
                    mission_id_col = col
                elif col.upper() in ['임무종류', 'MISSION_TYPE', 'MISSIONTYPE']:
                    mission_type_col = col
                elif col.upper() in ['주요축선ID', 'PRIMARY_AXIS_ID', 'PRIMARYAXISID']:
                    primary_axis_col = col
                elif col.upper() in ['우선순위', 'PRIORITY']:
                    priority_col = col
            
            if mission_type_col and primary_axis_col:
                defense_missions = missions_df[
                    missions_df[mission_type_col].isin(['방어', 'defense', 'DEFENSE']) &
                    (missions_df[primary_axis_col] == threat_event.related_axis_id)
                ]
                if not defense_missions.empty:
                    # 우선순위가 높은 임무 선택
                    if priority_col:
                        defense_missions = defense_missions.sort_values(priority_col)
                    if mission_id_col:
                        return defense_missions.iloc[0][mission_id_col]
        
        # 방법 3: 기본 방어임무 사용
        mission_id_col = None
        mission_type_col = None
        priority_col = None
        
        for col in missions_df.columns:
            if col.upper() in ['임무ID', 'MISSION_ID', 'MISSIONID']:
                mission_id_col = col
            elif col.upper() in ['임무종류', 'MISSION_TYPE', 'MISSIONTYPE']:
                mission_type_col = col
            elif col.upper() in ['우선순위', 'PRIORITY']:
                priority_col = col
        
        if mission_type_col:
            default_defense = missions_df[
                missions_df[mission_type_col].isin(['방어', 'defense', 'DEFENSE'])
            ]
            if not default_defense.empty:
                if priority_col:
                    default_defense = default_defense.sort_values(priority_col)
                if mission_id_col:
                    return default_defense.iloc[0][mission_id_col]
        
        return None
    
    def generate_and_evaluate_coas(
        self,
        mission_id: str,
        axis_states: Optional[List[AxisState]] = None,
        user_params: Optional[Dict] = None
    ) -> Dict:
        """
        COA 후보 생성 및 평가 (기존 메서드, 하위 호환성 유지)
        
        Args:
            mission_id: 임무ID
            axis_states: 축선별 전장상태 (None이면 자동 빌드)
            user_params: 사용자 설정 파라미터
                - max_coas: 최대 COA 수 (기본값: 5)
                - preferred_strategy: 선호 전략 ("defensive", "offensive", "balanced")
        
        Returns:
            {
                "axis_states": [...],
                "coas": [...],
                "evaluations": [...],
                "top_coas": [...]  # 상위 3개
            }
        """
        # Axis states 빌드 (없으면)
        if axis_states is None:
            axis_states = self.build_axis_states(mission_id)
        
        if not axis_states:
            return {
                "axis_states": [],
                "coas": [],
                "evaluations": [],
                "top_coas": [],
                "error": "축선별 전장상태를 생성할 수 없습니다."
            }
        
        # [NEW] 임무 정보(작전지역 등)를 user_params에 주입하여 Generator에서 활용 가능하게 함
        try:
            # user_params가 None이면 생성
            if user_params is None:
                user_params = {}
                
            # data_manager를 통해 임무 정보 조회
            missions_df = self.data_manager.load_table('임무정보')
            if missions_df is not None and not missions_df.empty:
                # 임무ID 컬럼 찾기
                id_col = next((c for c in missions_df.columns if c.upper() in ['임무ID', 'MISSION_ID']), None)
                if id_col:
                    mission_row = missions_df[missions_df[id_col] == mission_id]
                    if not mission_row.empty:
                        # 작전지역 추출
                        row_dict = mission_row.iloc[0].to_dict()
                        op_area = row_dict.get('작전지역', row_dict.get('operation_area', row_dict.get('구역')))
                        if op_area and str(op_area).strip():
                            user_params['operation_area'] = str(op_area).strip()
                            print(f"[INFO] COA 생성 컨텍스트에 작전지역 추가: {op_area}")
                        
                        # [NEW] 시간 정보 추출
                        start_time = row_dict.get('작전개시시각', row_dict.get('start_time'))
                        end_time = row_dict.get('작전종료예상', row_dict.get('end_time', row_dict.get('시간제한')))
                        
                        if start_time:
                            user_params['start_time'] = str(start_time)
                        if end_time:
                            user_params['end_time'] = str(end_time)
                            
                        if start_time:
                            print(f"[INFO] COA 생성 컨텍스트에 시간 정보 추가: {start_time} ~ {end_time}")
        except Exception as e:
            print(f"[WARN] 임무 정보 주입 실패: {e}")

        # COA 생성
        coas = self.coa_generator.generate_coas(
            mission_id=mission_id,
            axis_states=axis_states,
            user_params=user_params
        )
        
        if not coas:
            return {
                "axis_states": axis_states,
                "coas": [],
                "evaluations": [],
                "top_coas": [],
                "error": "COA 후보를 생성할 수 없습니다."
            }
        
        # COA 평가 (Enhanced 버전이면 온톨로지 기반 평가 사용)
        # COA 평가 (Enhanced 버전 여부와 관계없이 인터페이스 통일)
        evaluations = self.coa_evaluator.evaluate_coas(
            mission_id=mission_id,
            axis_states=axis_states,
            coa_list=coas
        )
        
        # 점수 순으로 정렬 (이미 정렬되어 있을 수 있지만 안전하게)
        evaluations_sorted = sorted(
            evaluations,
            key=lambda x: x.total_score,
            reverse=True
        )
        
        # 상위 3개 선택
        top_coas = evaluations_sorted[:3]
        
        return {
            "axis_states": axis_states,
            "coas": coas,
            "evaluations": evaluations_sorted,
            "top_coas": top_coas
        }
    
    def generate_coa_explanation(
        self,
        coa_evaluation: COAEvaluationResult,
        axis_states: List[AxisState],
        language: str = 'ko',
        use_llm: bool = True
    ) -> str:
        """
        COA 평가 결과에 대한 상세 설명 생성
        
        Args:
            coa_evaluation: COA 평가 결과
            axis_states: 축선별 전장상태 리스트
            language: 언어 ('ko' 또는 'en')
            use_llm: LLM 사용 여부
            
        Returns:
            설명문 텍스트
        """
        if not self.llm_adapter:
            # LLM 어댑터가 없으면 직접 생성
            explanation_generator = COAExplanationGenerator(llm_manager=self.llm_manager)
            return explanation_generator.generate_coa_explanation(
                coa_evaluation, axis_states, language=language, use_llm=use_llm
            )
        
        return self.llm_adapter.generate_explanation(
            coa_evaluation, axis_states, language=language, use_llm=use_llm
        )
    
    def get_axis_state_summary(self, axis_state: AxisState) -> Dict:
        """
        축선별 전장상태 요약 정보 반환
        
        Args:
            axis_state: AxisState 객체
            
        Returns:
            요약 정보 딕셔너리
        """
        return {
            "axis_id": axis_state.axis_id,
            "axis_name": axis_state.axis_name or axis_state.axis_id,
            "threat_level": axis_state.threat_level,
            "friendly_combat_power": axis_state.friendly_combat_power_total,
            "enemy_combat_power": axis_state.enemy_combat_power_total,
            "combat_power_ratio": (
                axis_state.friendly_combat_power_total / axis_state.enemy_combat_power_total
                if axis_state.enemy_combat_power_total > 0 else 0
            ),
            "mobility_grade": axis_state.avg_mobility_grade,
            "constraint_count": len(axis_state.constraints),
            "friendly_unit_count": len(axis_state.friendly_units),
            "enemy_unit_count": len(axis_state.enemy_units)
        }
    
    def get_coa_summary(self, coa_evaluation: COAEvaluationResult) -> Dict:
        """
        COA 평가 결과 요약 정보 반환
        
        Args:
            coa_evaluation: COA 평가 결과
            
        Returns:
            요약 정보 딕셔너리
        """
        return {
            "coa_id": coa_evaluation.coa_id,
            "coa_name": coa_evaluation.coa_name or coa_evaluation.coa_id,
            "total_score": coa_evaluation.total_score,
            "combat_power_score": coa_evaluation.combat_power_score,
            "mobility_score": coa_evaluation.mobility_score,
            "constraint_compliance_score": coa_evaluation.constraint_compliance_score,
            "threat_response_score": coa_evaluation.threat_response_score,
            "risk_score": coa_evaluation.risk_score,
            "weights": coa_evaluation.weights
        }

    def generate_coas_with_agent(
        self,
        mission_id=None,
        threat_id=None,
        threat_event=None,
        user_params=None
    ):
        """EnhancedDefenseCOAAgent direct call for agent-based generation"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from agents.defense_coa_agent.logic_defense_enhanced import EnhancedDefenseCOAAgent
            
            if not hasattr(self, '_agent_core') or self._agent_core is None:
                logger.warning('[COAService] agent_core not set, falling back')
                return self.generate_coas_unified(
                    mission_id=mission_id,
                    threat_id=threat_id,
                    threat_event=threat_event,
                    user_params=user_params
                )
            
            agent = EnhancedDefenseCOAAgent(self._agent_core)
            situation_info = user_params.copy() if user_params else {}
            
            if threat_event:
                from common.situation_converter import SituationInfoConverter
                normalized_level, _, _ = SituationInfoConverter.normalize_threat_level(
                    threat_event.threat_level if hasattr(threat_event, 'threat_level') else 0.5
                )
                situation_info.update({
                    'threat_id': threat_event.threat_id,
                    'threat_type': threat_event.threat_type_code,
                    'threat_level': normalized_level,
                    'location': threat_event.location_cell_id,
                    'axis_id': threat_event.related_axis_id,
                })
            
            if mission_id:
                situation_info['mission_id'] = mission_id
            
            agent_result = agent.execute_reasoning(
                user_query='Situation analysis and COA recommendation',
                situation_info=situation_info
            )
            
            return {
                'coas': agent_result.get('recommendations', []),
                'situation_assessment': agent_result.get('situation_assessment'),
                'situation_summary': agent_result.get('situation_summary') or agent_result.get('overall_summary'),
                'axis_states': agent_result.get('axis_states', []),
                'approach_mode': situation_info.get('approach_mode', 'threat_centered'),
                'mission_id': mission_id,
                'threat_id': threat_id or (threat_event.threat_id if threat_event else None),
                'threat_event': threat_event,
            }
            
        except Exception as e:
            logger.error(f'[COAService] Agent call failed: {e}')
            import traceback
            traceback.print_exc()
            return self.generate_coas_unified(
                mission_id=mission_id,
                threat_id=threat_id,
                threat_event=threat_event,
                user_params=user_params
            )
    
    def set_agent_core(self, core):
        """Set agent core for agent-based generation"""
        self._agent_core = core