import sys
from pathlib import Path
import logging
from collections import OrderedDict
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Mocking st.session_state is not right for FastAPI.
# We need a proper Singleton or Dependency Injection pattern.

from core_pipeline.coa_service import COAService
from core_pipeline.orchestrator import Orchestrator
import yaml

def load_global_config():
    config_path = BASE_DIR / "config" / "global.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

logger = logging.getLogger("api.dependencies")

class SituationSummaryCache:
    """정황보고 캐시 (LRU 방식, 최대 10개)"""
    
    def __init__(self, max_size: int = 10):
        self.cache: OrderedDict[str, str] = OrderedDict()
        self.max_size = max_size
    
    def _generate_cache_key(self, situation_info: Dict[str, Any]) -> Optional[str]:
        """
        캐시 키 생성
        SITREP 입력 또는 수동 입력인 경우 None 반환 (캐시 사용 안 함)
        """
        # 1. SITREP 여부 판단: raw_report_text 또는 sitrep_text가 있고 길이가 50자 이상이면 SITREP으로 간주
        raw_text = situation_info.get('raw_report_text') or situation_info.get('sitrep_text') or ''
        if raw_text and len(str(raw_text).strip()) >= 50:
            return None  # SITREP은 캐시 사용 안 함
        
        # 2. 수동 입력 여부 판단
        is_manual = situation_info.get('is_manual', False)
        if is_manual:
            return None  # 수동 입력은 캐시 사용 안 함
        
        # 3. 수동 입력 ID 패턴 확인 (SIT_로 시작하는 경우)
        threat_id = situation_info.get('threat_id') or situation_info.get('위협ID') or ''
        situation_id = situation_info.get('situation_id') or ''
        if (threat_id and str(threat_id).startswith('SIT_')) or (situation_id and str(situation_id).startswith('SIT_')):
            return None  # 수동 입력 ID 패턴은 캐시 사용 안 함
        
        # approach_mode 확인
        approach_mode = situation_info.get('approach_mode', 'threat_centered')
        mission_id = situation_info.get('mission_id') or situation_info.get('임무ID')
        
        # 4. 임무 중심 모드: mission_id 우선 (더 세분화된 키 사용)
        if approach_mode == 'mission_centered' and mission_id:
            # 임무 중심 모드에서는 mission_id + mission_name으로 더 정밀한 키 생성
            mission_name = situation_info.get('mission_name') or situation_info.get('임무명') or ''
            # 위협 정보도 포함 (예상 위협이 다를 수 있음)
            threat_type = situation_info.get('threat_type') or situation_info.get('위협유형') or ''
            return f"mission:{mission_id}:{mission_name}:{threat_type}:mission_centered"
        
        # 5. 위협 중심: threat_id 기반 (실제 데이터에서 선택한 경우만)
        if threat_id and not str(threat_id).startswith('SIT_'):
            return f"threat:{threat_id}:{approach_mode}"
        
        # 6. 그 외 (임무 ID만 있고 위협 중심 모드인 경우 등)
        if mission_id:
            return f"mission:{mission_id}:{approach_mode}"
        
        return None  # 키를 생성할 수 없으면 캐시 사용 안 함
    
    def get(self, situation_info: Dict[str, Any]) -> Optional[str]:
        """캐시에서 정황보고 조회"""
        cache_key = self._generate_cache_key(situation_info)
        if cache_key is None:
            return None  # SITREP이거나 키를 생성할 수 없으면 캐시 사용 안 함
        
        if cache_key in self.cache:
            # LRU: 사용된 항목을 맨 뒤로 이동
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        return None
    
    def set(self, situation_info: Dict[str, Any], summary: str):
        """캐시에 정황보고 저장"""
        cache_key = self._generate_cache_key(situation_info)
        if cache_key is None:
            return  # SITREP이거나 키를 생성할 수 없으면 캐시 저장 안 함
        
        # 캐시 크기 제한
        if len(self.cache) >= self.max_size:
            # 가장 오래된 항목 제거 (FIFO)
            self.cache.popitem(last=False)
        
        self.cache[cache_key] = summary
        # LRU: 새로 추가된 항목을 맨 뒤로 이동
        self.cache.move_to_end(cache_key)
    
    def clear(self):
        """캐시 초기화"""
        self.cache.clear()

class GlobalStateManager:
    _instance = None
    
    def __init__(self):
        self.config = load_global_config()
        self.orchestrator: Orchestrator | None = None
        self.coa_service: COAService | None = None
        self.situation_summary_cache: SituationSummaryCache = SituationSummaryCache(max_size=10)
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        if not self.orchestrator:
            logger.info("Initializing Orchestrator...")
            self.orchestrator = Orchestrator(self.config, use_enhanced_ontology=True)
            self.orchestrator.initialize()
            
        if not self.coa_service:
            logger.info("Initializing COAService...")
            # Orchestrator에서 OntologyManager 가져오기
            ontology_manager = None
            if self.orchestrator:
                ontology_manager = self.orchestrator.core.ontology_manager
                
            self.coa_service = COAService(self.config, ontology_manager=ontology_manager)
            
            # Connect LLM services if available
            if self.orchestrator and self.orchestrator.core:
                 self.coa_service.initialize_llm_services(
                    llm_manager=self.orchestrator.core.llm_manager,
                    rag_manager=self.orchestrator.core.rag_manager,
                    ontology_manager=self.orchestrator.core.ontology_manager,
                    use_enhanced=True
                )
        logger.info("Global State Initialized.")

    def get_coa_service(self) -> COAService:
        if not self.coa_service:
            self.initialize()
        return self.coa_service

    def get_orchestrator(self) -> Orchestrator:
        if not self.orchestrator:
            self.initialize()
        return self.orchestrator

# Dependency functions for FastAPI
def get_global_state() -> GlobalStateManager:
    return GlobalStateManager.get_instance()

def get_coa_service() -> COAService:
    return GlobalStateManager.get_instance().get_coa_service()

def get_orchestrator() -> Orchestrator:
    return GlobalStateManager.get_instance().get_orchestrator()
