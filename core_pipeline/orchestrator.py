# core_pipeline/orchestrator.py
# -*- coding: utf-8 -*-
"""
Orchestrator
코어 파이프라인 오케스트레이터
"""
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from typing import Dict, Optional, Type
from core_pipeline.data_manager import DataManager
# OntologyManager는 EnhancedOntologyManager로 대체됨
# from core_pipeline.ontology_manager import OntologyManager
from core_pipeline.rag_manager import RAGManager
from core_pipeline.llm_manager import LLMManager
from core_pipeline.reasoning_engine import ReasoningEngine
from core_pipeline.semantic_inference import SemanticInference
from core_pipeline.palantir_search import PalantirSearch
from core_pipeline.relationship_chain import RelationshipChain
from core_pipeline.data_watcher import DataWatcher
from core_pipeline.event_stream import EventStream
from core_pipeline.recommendation_history import RecommendationHistory
from core_pipeline.status_manager import StatusManager

# Enhanced Ontology Manager (현재 시스템 통합)
try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    ENHANCED_ONTOLOGY_AVAILABLE = True
except ImportError:
    ENHANCED_ONTOLOGY_AVAILABLE = False

# RelevanceMapper와 ResourcePriorityParser 추가 (성능 최적화: 중복 초기화 방지)
try:
    from core_pipeline.relevance_mapper import RelevanceMapper
except ImportError:
    RelevanceMapper = None

try:
    from core_pipeline.resource_priority_parser import ResourcePriorityParser
except ImportError:
    ResourcePriorityParser = None


class CorePipeline:
    """코어 파이프라인 클래스"""
    
    def __init__(self, config: Dict, use_enhanced_ontology: bool = True):
        """
        Args:
            config: 설정 딕셔너리
            use_enhanced_ontology: Enhanced Ontology Manager 사용 여부 (현재 시스템 통합)
        """
        self.config = config
        self.data_manager = DataManager(config)
        self.status_manager = StatusManager(self.data_manager)
        
        # EnhancedOntologyManager를 기본으로 사용 (독립적)
        if ENHANCED_ONTOLOGY_AVAILABLE and use_enhanced_ontology:
            self.ontology_manager = EnhancedOntologyManager(config)
            self.ontology_manager.data_manager = self.data_manager
            self.enhanced_ontology_manager = self.ontology_manager  # 호환성을 위해 별칭 유지
        else:
            # EnhancedOntologyManager를 사용할 수 없는 경우를 위한 폴백
            # (향후 제거 예정)
            raise ImportError("EnhancedOntologyManager is required but not available")
        
        self._use_enhanced_ontology = use_enhanced_ontology  # 플래그 저장
        
        self.rag_manager = RAGManager(config)
        self.llm_manager = LLMManager()
        
        # [PERFORMANCE] RelevanceMapper와 ResourcePriorityParser 초기화 (중복 초기화 방지)
        # Agent에서 COAScorer 생성 시 재사용하여 성능 개선
        self.relevance_mapper = None
        self.resource_parser = None
        if RelevanceMapper is not None:
            try:
                from pathlib import Path
                base_path = Path(__file__).parent.parent
                data_lake_path = base_path / "data_lake"
                self.relevance_mapper = RelevanceMapper(data_lake_path=str(data_lake_path))
                print("[INFO] CorePipeline: RelevanceMapper 초기화 완료")
            except Exception as e:
                print(f"[WARN] CorePipeline: RelevanceMapper 초기화 실패: {e}")
        
        if ResourcePriorityParser is not None:
            try:
                self.resource_parser = ResourcePriorityParser()
                print("[INFO] CorePipeline: ResourcePriorityParser 초기화 완료")
            except Exception as e:
                print(f"[WARN] CorePipeline: ResourcePriorityParser 초기화 실패: {e}")
        
        # ReasoningEngine 초기화 (매퍼 주입)
        self.reasoning_engine = ReasoningEngine(
            config=config,
            relevance_mapper=self.relevance_mapper,
            resource_parser=self.resource_parser
        )
        
        self.semantic_inference = SemanticInference(config)
        self.relationship_chain = RelationshipChain(config)
        # PalantirSearch는 나중에 초기화 (순환 참조 방지)
        self.palantir_search = None
        
        # 실시간 기능 추가
        self.data_watcher = DataWatcher(self.data_manager, self.ontology_manager, self.status_manager)
        self.event_stream = EventStream(self.data_manager, self.ontology_manager)
        self.recommendation_history = RecommendationHistory()
    
    def initialize(self, progress_callback=None):
        """
        파이프라인 초기화
        
        Args:
            progress_callback: 진행 상황 업데이트 콜백 함수 (optional)
        """
        # 이미 초기화되었는지 확인
        if hasattr(self, '_initialized') and self._initialized:
            logger.info("Orchestrator가 이미 초기화되었습니다. 초기화를 건너뜜")
            if progress_callback:
                progress_callback("시스템이 이미 초기화되어 있습니다.")
            return  # 이미 초기화됨, 스킵
        
        # EnhancedOntologyManager는 __init__에서 이미 초기화됨
        if self.ontology_manager:
            logger.info("Enhanced Ontology Manager initialized (독립 모드)")
            if progress_callback:
                progress_callback("Ontology Manager 확인 완료")
        
        try:
            import torch
            HAS_TORCH = True
        except ImportError:
            HAS_TORCH = False
            print("[WARN] torch가 설치되지 않았습니다. CPU 모드로 강제 설정합니다.")
        
        # GPU 메모리 확인 및 로딩 전략 결정
        use_gpu_for_llm = False
        use_gpu_for_embedding = False
        
        if progress_callback:
            progress_callback("GPU 및 시스템 리소스 확인 중...")
        
        if HAS_TORCH and torch.cuda.is_available():
            try:
                gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
                gpu_memory_free = gpu_memory_total - gpu_memory_allocated
                logger.info(f"GPU 메모리 상태: {gpu_memory_free:.2f} GB 사용 가능 / {gpu_memory_total:.2f} GB 전체")
                
                # GPU 메모리가 3GB 미만이면 LLM만 GPU에 로드, Embedding은 CPU
                if gpu_memory_free < 3.0:
                    print("[WARN] GPU 메모리 부족 감지. LLM만 GPU에 로드하고 Embedding은 CPU에 유지합니다.")
                    use_gpu_for_llm = True
                    use_gpu_for_embedding = False
                else:
                    # 충분한 메모리가 있으면 둘 다 GPU에 로드 시도
                    use_gpu_for_llm = True
                    use_gpu_for_embedding = True
            except Exception as e:
                print(f"[WARN] GPU 정보 확인 중 오류 발생: {e}. CPU 모드로 폴백합니다.")
                use_gpu_for_llm = False
                use_gpu_for_embedding = False
        else:
            if HAS_TORCH:
                logger.info("CUDA 사용 불가 또는 torch 미설치. CPU 모드로 로드합니다.")
            use_gpu_for_llm = False
            use_gpu_for_embedding = False
        
        # LLM 모델 로드 (조건부: 외부 모델 또는 사내망 모델 사용 가능하면 로컬 모델 로드 스킵)
        try:
            if progress_callback:
                progress_callback("LLM 모델 가용성 확인 중...")
                
            # 사용 가능한 모델 확인
            available_models = self.llm_manager.get_available_models()
            has_openai = available_models.get('openai', {}).get('available', False)
            has_internal = any(
                model_info.get('available', False) 
                for model_key, model_info in available_models.items() 
                if model_key.startswith('internal_')
            )
            
            # OpenAI 또는 사내망 모델이 사용 가능하면 로컬 모델 로드 스킵 (메모리 및 시작 시간 최적화)
            if has_openai or has_internal:
                if has_openai:
                    logger.info(f"OpenAI API 사용 가능 (모델: {self.llm_manager.openai_model})")
                    if progress_callback:
                        progress_callback(f"OpenAI API 연결 확인 (모델: {self.llm_manager.openai_model})")
                if has_internal:
                    internal_count = sum(1 for k, v in available_models.items() if k.startswith('internal_') and v.get('available', False))
                    logger.info(f"사내망 모델 {internal_count}개 사용 가능")
                    if progress_callback:
                        progress_callback(f"사내망 LLM 모델 {internal_count}개 확인됨")
                
                logger.info("로컬 모델 로드를 생략하고 원격 모델을 우선 사용합니다. (지연 로드)")
            else:
                # OpenAI와 사내망 모델이 모두 사용 불가할 때만 로컬 모델 로드
                logger.info("로컬 모델을 로드합니다. 잠시만 기다려 주세요...")
                if progress_callback:
                    progress_callback("로컬 LLM 모델 로드 중 (시간이 소요될 수 있습니다)...")
                
                result = self.llm_manager.load_model(force_gpu=use_gpu_for_llm)
                if result is None or result[0] is None:
                    print("[WARN] LLM 모델 로드 실패. 일부 기능이 제한될 수 있습니다.")
                    if progress_callback:
                        progress_callback("⚠️ 로컬 LLM 모델 로드 실패 (제한된 기능으로 실행)")
                    # 의존성 확인
                    self._check_llm_dependencies()
                else:
                    logger.info("LLM 모델 로드 완료")
                    if progress_callback:
                        progress_callback("로컬 LLM 모델 로드 완료")
        except Exception as e:
            print(f"[WARN] LLM 로드 중 오류 발생: {e}")
            if progress_callback:
                progress_callback(f"⚠️ LLM 로드 중 오류: {e}")
            import traceback
            traceback.print_exc()
            # 의존성 확인
            self._check_llm_dependencies()
        
        # RAG 임베딩 모델 로드 (CPU 우선 정책 강제 적용)
        try:
            # CPU 우선 정책: 안정성을 위해 항상 CPU로 로드
            logger.info("임베딩 모델 로드 중 (RAG 인덱스 최적화)...")
            if progress_callback:
                progress_callback("RAG 임베딩 모델 로드 중...")
            
            self.rag_manager.load_embeddings(device='cpu')
            
            # 로드 확인
            if self.rag_manager.embedding_model is None:
                print("[WARN] 임베딩 모델 로드 재시도...")
                # 재시도: CPU 모드로 강제
                self.rag_manager.load_embeddings(device='cpu')
            
            if self.rag_manager.embedding_model:
                logger.info("임베딩 모델 로드 완료")
                if progress_callback:
                    progress_callback("RAG 임베딩 모델 로드 완료")
        except Exception as e:
            print(f"[WARN] 임베딩 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            # 최종 재시도
            try:
                self.rag_manager.load_embeddings(device='cpu')
            except Exception as e2:
                print(f"[ERROR] Embedding 모델 로드 최종 실패: {e2}")
        
        # PalantirSearch 초기화
        try:
            from core_pipeline.palantir_search import PalantirSearch
            self.palantir_search = PalantirSearch(
                self.rag_manager,
                self.ontology_manager,
                self.semantic_inference,
                self.reasoning_engine
            )
        except Exception as e:
            print(f"[WARN] PalantirSearch initialization failed: {e}")
        
        # RAG 인덱스 자동 구축 (인덱스가 없는 경우)
        if progress_callback:
            progress_callback("RAG 인덱스 확인 및 구축 중...")
        self._build_rag_index_if_needed()
        
        # 온톨로지 그래프 자동 구축 (그래프가 비어있는 경우)
        if progress_callback:
            progress_callback("지식 그래프(Ontology) 구축 중...")
        self._build_ontology_graph_if_needed()
        
        # 상태 관리자 초기화 (캐시 로드)
        try:
            if progress_callback:
                progress_callback("상태 관리자 초기화 중...")
            self.status_manager.initialize()
            logger.info("StatusManager 초기화 완료")
        except Exception as e:
            print(f"[WARN] StatusManager 초기화 실패: {e}")
        
        # 데이터 감시 시작 (옵션)
        enable_watching = self.config.get("enable_realtime_watching", False)
        if enable_watching:
            try:
                if progress_callback:
                    progress_callback("실시간 데이터 감시 시작...")
                self.data_watcher.start_watching()
                logger.info("실시간 데이터 감시 활성화")
            except Exception as e:
                print(f"[WARN] 실시간 데이터 감시 활성화 실패: {e}")
        
        # 초기화 완료 플래그 설정
        self._initialized = True
        if progress_callback:
            progress_callback("시스템 코어 초기화 완료")
    
    def _check_llm_dependencies(self):
        """LLM 의존성 확인"""
        print("\n[INFO] Checking LLM dependencies...")
        
        # transformers 확인
        try:
            import transformers
            print(f"  ✅ transformers: {transformers.__version__}")
        except ImportError:
            print("  ❌ transformers: NOT INSTALLED")
            print("     Install: pip install transformers")
        
        # torch 확인
        try:
            import torch
            print(f"  ✅ torch: {torch.__version__}")
            if torch.cuda.is_available():
                print(f"  ✅ CUDA available: {torch.version.cuda}")
                print(f"  ✅ GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("  ⚠️ CUDA not available (CPU mode only)")
        except ImportError:
            print("  ❌ torch: NOT INSTALLED")
            print("     Install: pip install torch")
        
        # auto-gptq 확인 (선택적)
        try:
            import auto_gptq
            print(f"  ✅ auto-gptq: {auto_gptq.__version__}")
        except ImportError:
            print("  ⚠️ auto-gptq: NOT INSTALLED (optional, for GPTQ models)")
        
        # accelerate 확인 (device_map 사용 시 필요)
        try:
            import accelerate
            print(f"  ✅ accelerate: {accelerate.__version__}")
        except ImportError:
            print("  ⚠️ accelerate: NOT INSTALLED (required for device_map='auto')")
            print("     Install: pip install accelerate")
        
        print()
    
    def _build_rag_index_if_needed(self):
        """RAG 인덱스가 없으면 자동 구축"""
        # 임베딩 모델이 없으면 인덱스 구축 불가
        if self.rag_manager.embedding_model is None:
            logger.info("Embedding 모델이 없습니다. 인덱스 구축 건너뜀.")
            return
        
        # 기존 인덱스 확인 (FAISS 인덱스와 chunks 모두 확인)
        if self.rag_manager.faiss_index is not None and len(self.rag_manager.chunks) > 0:
            logger.info(f"RAG 인덱스가 이미 존재합니다: {len(self.rag_manager.chunks)}개 청크")
            return
        
        # 저장된 인덱스 로드 시도 (load_embeddings에서 로드하지 못한 경우에만)
        # 주의: load_index() 내부에서 이미 중복 로드 방지 로직이 있지만, 
        # 여기서도 확인하여 불필요한 호출 방지
        if len(self.rag_manager.chunks) == 0 or self.rag_manager.faiss_index is None:
            try:
                # load_index()는 이미 로드된 경우 자동으로 스킵함
                self.rag_manager.load_index()
                if len(self.rag_manager.chunks) > 0 and self.rag_manager.faiss_index is not None:
                    # load_index()에서 이미 로그가 출력되므로 여기서는 추가 로그 없음
                    return
            except Exception as e:
                logger.info(f"저장된 인덱스 로드 실패, 새로 구축합니다: {e}")
        
        # knowledge/rag_docs/ 문서 로드 및 인덱싱
        from pathlib import Path
        rag_docs_path = Path("knowledge/rag_docs")
        
        if not rag_docs_path.exists():
            logger.info(f"RAG 문서 디렉토리가 없습니다: {rag_docs_path}")
            return
        
        try:
            docs = []
            doc_files = list(rag_docs_path.glob("*.txt")) + list(rag_docs_path.glob("*.md"))
            
            if not doc_files:
                logger.info(f"RAG 문서가 없습니다: {rag_docs_path}")
                return
            
            doctrine_docs = []
            doctrine_doc_names = []
            general_docs = []
            general_doc_names = []
            
            for doc_file in doc_files:
                try:
                    with open(doc_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            # 파일명으로 교리 문서 여부 판단 (DOCTRINE-*)
                            if doc_file.name.upper().startswith("DOCTRINE") or "# Doctrine_ID:" in content:
                                doctrine_docs.append(content)
                                doctrine_doc_names.append(doc_file.name)
                            else:
                                general_docs.append(content)
                                general_doc_names.append(doc_file.name)
                except Exception as e:
                    print(f"[WARN] 문서 로드 실패 {doc_file}: {e}")
            
            if doctrine_docs or general_docs:
                logger.info(f"RAG 인덱스 자동 구축 시작: 교리 {len(doctrine_docs)}개, 일반 {len(general_docs)}개")
                
                all_chunks = []
                
                # 1. 교리 문서 청킹 (특수 로직)
                if doctrine_docs:
                    print(f"  - 교리 문서 청킹 중... ({len(doctrine_docs)}개 파일)")
                    doctrine_chunks = self.rag_manager.chunk_doctrine_documents(doctrine_docs, doc_names=doctrine_doc_names)
                    all_chunks.extend(doctrine_chunks)
                    print(f"  - 교리 청크 {len(doctrine_chunks)}개 생성")
                
                # 2. 일반 문서 청킹
                if general_docs:
                    print(f"  - 일반 문서 청킹 중... ({len(general_docs)}개 파일)")
                    general_chunks = self.rag_manager.chunk_documents(general_docs, doc_names=general_doc_names)
                    all_chunks.extend(general_chunks)
                    print(f"  - 일반 청크 {len(general_chunks)}개 생성")
                
                # 3. 인덱스 구축
                if all_chunks:
                    self.rag_manager.build_index(all_chunks)
                    # 인덱스 저장 (다음 초기화 시 재사용)
                    self.rag_manager.save_index()
                    logger.info(f"RAG 인덱스 자동 구축 완료: 총 {len(all_chunks)}개 청크 (저장 경로: {self.rag_manager.embedding_path})")
                else:
                    print("[WARN] 생성된 청크가 없습니다.")
            else:
                logger.info("인덱싱할 유효한 문서 내용이 없습니다.")
        except Exception as e:
            print(f"[WARN] RAG 인덱스 자동 구축 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_ontology_graph_if_needed(self):
        """온톨로지 그래프가 비어있으면 자동 구축"""
        if self.ontology_manager.graph is None:
            logger.info("온톨로지 그래프 객체가 없습니다. 초기화합니다...")
            try:
                from rdflib import Graph
                self.ontology_manager.graph = Graph()
            except ImportError:
                print("[WARN] rdflib이 설치되지 않았습니다. 온톨로지 그래프 구축 불가.")
                return
        
        # 그래프가 비어있는지 확인
        try:
            triples_count = len(list(self.ontology_manager.graph.triples((None, None, None))))
            if triples_count == 0:
                # 새 파일 구조에 맞춘 그래프 로드 시도 (우선순위 기반)
                # load_graph()가 자동으로 우선순위에 따라 파일을 로드함
                try:
                    loaded_graph = self.ontology_manager.load_graph()
                    if loaded_graph:
                        triples_count = len(list(loaded_graph.triples((None, None, None))))
                        if triples_count > 0:
                            # COA 데이터는 generate_instances()에서 일반 테이블로 처리됩니다.
                            # 중복 생성을 방지하기 위해 _add_coa_library_to_graph() 호출을 제거했습니다.
                            logger.info(f"기존 온톨로지 그래프 로드 완료: {triples_count} triples")
                            
                            # OWL-RL 추론 자동 실행 (설정에 따라)
                            # 단, 이미 추론이 실행되었는지 확인 (중복 추론 방지)
                            enable_auto_inference = self.config.get("enable_auto_owl_inference", True)
                            
                            # EnhancedOntologyManager에서 이미 추론을 실행했는지 확인
                            inference_already_performed = getattr(self.ontology_manager, '_inference_performed', False)
                            
                            if enable_auto_inference and not inference_already_performed:
                                try:
                                    from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
                                    if OWLRL_AVAILABLE:
                                        logger.info("OWL-RL 추론 자동 실행 중...")
                                        namespace = str(self.ontology_manager.ns) if hasattr(self.ontology_manager, 'ns') and self.ontology_manager.ns else None
                                        reasoner = OWLReasoner(self.ontology_manager.graph, namespace)
                                        inferred_graph = reasoner.run_inference()
                                        
                                        if inferred_graph is not None:
                                            stats = reasoner.get_stats()
                                            if stats.get("success"):
                                                new_count = stats.get("new_inferences", 0)
                                                if new_count > 0:
                                                    logger.info(f"OWL-RL 추론 완료: {new_count}개 새로운 트리플 생성")
                                                    # 추론된 그래프를 메모리에 적용 (파일 저장은 선택적)
                                                    self.ontology_manager.graph = inferred_graph
                                                    # 추론 실행 플래그 설정
                                                    self.ontology_manager._inference_performed = True
                                                else:
                                                    print("[INFO] OWL-RL 추론 완료: 새로운 트리플 없음 (이미 모든 관계가 존재)")
                                            else:
                                                print(f"[WARN] OWL-RL 추론 실패: {stats.get('error', 'Unknown error')}")
                                    else:
                                        print("[INFO] owlrl 라이브러리가 없어 OWL-RL 추론을 건너뜁니다.")
                                except Exception as e:
                                    print(f"[WARN] OWL-RL 추론 자동 실행 실패: {e}")
                            elif inference_already_performed:
                                print("[INFO] 이미 추론이 실행되었습니다. 중복 추론을 건너뜁니다.")
                            
                            return  # 이미 그래프가 있으면 구축 스킵
                        else:
                            print("[WARN] 기존 그래프 파일이 비어있습니다. 새로 구축합니다.")
                    else:
                        print("[WARN] 기존 그래프 파일 로드 실패. 새로 구축합니다.")
                except Exception as e:
                    print(f"[WARN] 기존 그래프 로드 실패, 새로 구축합니다: {e}")

                # 그래프가 비어있고... (기존 로직 계속)
                
                # 그래프가 비어있고 기존 파일도 없거나 로드 실패한 경우 새로 구축
                print("[INFO] 온톨로지 그래프가 비어있습니다. 자동 구축을 시작합니다...")
                try:
                    # 데이터 로드 (상세 로깅)
                    print("[INFO] 데이터 로드 시작...")
                    data = self.data_manager.load_all()
                    
                    # 데이터 검증 (빈 딕셔너리 체크)
                    if not data:
                        print("[WARN] 데이터가 없습니다. 온톨로지 그래프 구축 건너뜀.")
                        print("[INFO] data_paths 설정을 확인하거나 data_lake 폴더에 Excel 파일이 있는지 확인하세요.")
                        return
                    
                    # 빈 DataFrame 필터링 (로깅은 load_all()에서 이미 출력됨)
                    valid_data = {}
                    empty_tables = []
                    for name, df in data.items():
                        if df is not None and not df.empty:
                            valid_data[name] = df
                            # 로그는 load_all()에서 이미 출력되므로 중복 제거
                        else:
                            empty_tables.append(name)
                            # 로그는 load_all()에서 이미 출력되므로 중복 제거
                    
                    if empty_tables:
                        print(f"[WARN] {len(empty_tables)}개 테이블이 비어있습니다: {', '.join(empty_tables)}")
                    
                    # 유효한 데이터가 없으면 실패
                    if not valid_data:
                        print("[ERROR] 유효한 데이터 테이블이 없습니다. 온톨로지 그래프 구축 불가.")
                        print("[INFO] data_lake 폴더에 Excel 파일이 있는지 확인하세요.")
                        return
                    
                    print(f"[INFO] {len(valid_data)}개 테이블로 온톨로지 그래프 구축 시작...")
                    
                    # 그래프 구축 (force_rebuild=True로 캐시 무시하고 스키마 포함 새로 생성)
                    graph = self.ontology_manager.build_from_data(valid_data, force_rebuild=True)
                    if graph:
                        triples_count = len(list(graph.triples((None, None, None))))
                        if triples_count > 0:
                            print(f"[INFO] ✅ 온톨로지 그래프 구축 완료: {triples_count} triples")
                            
                            # OWL-RL 추론 자동 실행 (설정에 따라)
                            # 단, 이미 추론이 실행되었는지 확인 (중복 추론 방지)
                            enable_auto_inference = self.config.get("enable_auto_owl_inference", True)
                            
                            # EnhancedOntologyManager에서 이미 추론을 실행했는지 확인
                            inference_already_performed = getattr(self.ontology_manager, '_inference_performed', False)
                            
                            if enable_auto_inference and not inference_already_performed:
                                try:
                                    from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
                                    if OWLRL_AVAILABLE:
                                        print("[INFO] OWL-RL 추론 자동 실행 중...")
                                        namespace = str(self.ontology_manager.ns) if hasattr(self.ontology_manager, 'ns') and self.ontology_manager.ns else None
                                        reasoner = OWLReasoner(self.ontology_manager.graph, namespace)
                                        inferred_graph = reasoner.run_inference()
                                        
                                        if inferred_graph is not None:
                                            stats = reasoner.get_stats()
                                            if stats.get("success"):
                                                new_count = stats.get("new_inferences", 0)
                                                if new_count > 0:
                                                    print(f"[INFO] OWL-RL 추론 완료: {new_count}개 새로운 트리플 생성")
                                                    # 추론된 그래프를 메모리에 적용
                                                    self.ontology_manager.graph = inferred_graph
                                                    # 추론 실행 플래그 설정
                                                    self.ontology_manager._inference_performed = True
                                                    # 추론된 그래프 저장 (선택적)
                                                    save_reasoned = self.config.get("save_reasoned_graph_on_startup", False)
                                                    if save_reasoned:
                                                        try:
                                                            reasoned_path = Path(self.ontology_manager.ontology_path) / "instances_reasoned.ttl"
                                                            inferred_graph.serialize(destination=str(reasoned_path), format="turtle")
                                                            print(f"[INFO] 추론된 그래프 저장: {reasoned_path}")
                                                        except Exception as e:
                                                            print(f"[WARN] 추론된 그래프 저장 실패: {e}")
                                                else:
                                                    print("[INFO] OWL-RL 추론 완료: 새로운 트리플 없음 (이미 모든 관계가 존재)")
                                            else:
                                                print(f"[WARN] OWL-RL 추론 실패: {stats.get('error', 'Unknown error')}")
                                    else:
                                        print("[INFO] owlrl 라이브러리가 없어 OWL-RL 추론을 건너뜁니다.")
                                except Exception as e:
                                    print(f"[WARN] OWL-RL 추론 자동 실행 실패: {e}")
                            elif inference_already_performed:
                                print("[INFO] 이미 추론이 실행되었습니다. 중복 추론을 건너뜁니다.")
                        else:
                            print("[WARN] 온톨로지 그래프가 구축되었지만 triples가 생성되지 않았습니다.")
                            print("[INFO] 데이터에 유효한 행이 있는지 확인하세요.")
                    else:
                        print("[WARN] 온톨로지 그래프 구축 실패 (None 반환)")
                        print("[INFO] build_from_data()에서 오류가 발생했을 수 있습니다.")
                        
                except Exception as e:
                    print(f"[ERROR] 온톨로지 그래프 자동 구축 실패: {e}")
                    import traceback
                    print("[ERROR] 상세 오류:")
                    traceback.print_exc()
                    print("[INFO] 수동으로 '2단계: 온톨로지 생성' 페이지에서 그래프를 생성할 수 있습니다.")
            else:
                print(f"[INFO] 온톨로지 그래프가 이미 구축되어 있습니다: {triples_count} triples")
                
                # 그래프가 이미 로드된 경우에도 추론 실행 (설정에 따라)
                # 단, 이미 추론이 실행되었는지 확인 (중복 추론 방지)
                enable_auto_inference = self.config.get("enable_auto_owl_inference", True)
                force_reinference = self.config.get("force_reinference_on_startup", False)
                
                # EnhancedOntologyManager에서 이미 추론을 실행했는지 확인
                inference_already_performed = getattr(self.ontology_manager, '_inference_performed', False)
                
                # instances_reasoned.ttl이 이미 로드된 경우, force_reinference가 True일 때만 재추론
                reasoned_path = Path(self.ontology_manager.ontology_path) / "instances_reasoned.ttl"
                if reasoned_path.exists() and not force_reinference:
                    print("[INFO] instances_reasoned.ttl이 이미 존재하여 추론을 건너뜁니다.")
                    print("[INFO] 재추론을 원하면 config/global.yaml에서 force_reinference_on_startup: true 설정")
                elif enable_auto_inference and not inference_already_performed:
                    try:
                        from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
                        if OWLRL_AVAILABLE:
                            print("[INFO] OWL-RL 추론 자동 실행 중...")
                            namespace = str(self.ontology_manager.ns) if hasattr(self.ontology_manager, 'ns') and self.ontology_manager.ns else None
                            reasoner = OWLReasoner(self.ontology_manager.graph, namespace)
                            inferred_graph = reasoner.run_inference()
                            
                            if inferred_graph is not None:
                                stats = reasoner.get_stats()
                                if stats.get("success"):
                                    new_count = stats.get("new_inferences", 0)
                                    if new_count > 0:
                                        print(f"[INFO] OWL-RL 추론 완료: {new_count}개 새로운 트리플 생성")
                                        self.ontology_manager.graph = inferred_graph
                                        # 추론 실행 플래그 설정
                                        self.ontology_manager._inference_performed = True
                                    else:
                                        print("[INFO] OWL-RL 추론 완료: 새로운 트리플 없음 (이미 모든 관계가 존재)")
                                else:
                                    print(f"[WARN] OWL-RL 추론 실패: {stats.get('error', 'Unknown error')}")
                        else:
                            print("[INFO] owlrl 라이브러리가 없어 OWL-RL 추론을 건너뜁니다.")
                    except Exception as e:
                        print(f"[WARN] OWL-RL 추론 자동 실행 실패: {e}")
                elif inference_already_performed:
                    print("[INFO] 이미 추론이 실행되었습니다. 중복 추론을 건너뜁니다.")
        except Exception as e:
            print(f"[ERROR] 온톨로지 그래프 상태 확인 실패: {e}")
            import traceback
            traceback.print_exc()


class Orchestrator:
    """오케스트레이터 클래스"""
    
    def __init__(self, config: Dict, use_enhanced_ontology: bool = True):
        """
        Args:
            config: 설정 딕셔너리
            use_enhanced_ontology: Enhanced Ontology Manager 사용 여부 (현재 시스템 통합)
        """
        self.config = config
        self.core = CorePipeline(config, use_enhanced_ontology=use_enhanced_ontology)
        self.agents = {}
    
    def load_agent_class(self, dotted_path: str) -> Type:
        """
        점으로 구분된 경로로부터 Agent 클래스 로드
        
        Args:
            dotted_path: 예) "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent"
            
        Returns:
            Agent 클래스
        """
        mod_name, cls_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(mod_name)
        return getattr(module, cls_name)
    
    def register_agent(self, name: str, agent_class: Type, **kwargs):
        """
        Agent 등록
        
        Args:
            name: Agent 이름
            agent_class: Agent 클래스
            **kwargs: Agent 초기화 인자
        """
        agent = agent_class(core=self.core, **kwargs)
        self.agents[name] = agent
        return agent
    
    def get_agent(self, name: str):
        """
        등록된 Agent 가져오기
        
        Args:
            name: Agent 이름
            
        Returns:
            Agent 인스턴스
        """
        return self.agents.get(name)
    
    def initialize(self, progress_callback=None):
        """
        오케스트레이터 초기화
        
        Args:
            progress_callback: 진행 상황 콜백
        """
        return self.core.initialize(progress_callback=progress_callback)

