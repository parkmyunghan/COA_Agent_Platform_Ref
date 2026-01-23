# core_pipeline/llm_manager.py
# -*- coding: utf-8 -*-
"""
LLM 모델 관리자
로컬 LLM 모델을 로드하고 관리합니다.
"""
import os
import sys
from typing import List, Dict

# UTF-8 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def safe_print(msg, also_log_file: bool = True):
    """안전한 출력 함수 (개선된 버전 사용)"""
    from common.utils import safe_print as _safe_print
    _safe_print(msg, also_log_file=also_log_file, logger_name="LLMManager")

# 전역 변수로 모델 캐싱
_cached_model = None
_cached_tokenizer = None
_cached_model_path = None

# 전역 로그 제어 변수 (모든 인스턴스에서 공유)
_last_logged_model = None
_llm_init_logged = False  # LLM 초기화 로그 출력 여부
_internal_models_logged = False  # 사내망 모델 로그 출력 여부

class LLMManager:
    """LLM 모델 관리자 클래스 (OpenAI API 우선, 로컬 모델 폴백)"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_path = None
        self.openai_client = None
        self.openai_available = False
        self.use_openai = False
        self.openai_model = "gpt-4o"
        
        # 사내망 모델 관련 변수 추가
        self.internal_models = {}
        self.internal_models_available = {}
        self.internal_model_clients = {}  # 모델별 클라이언트 캐시
        
        # 선택된 모델 (세션 상태에서 관리)
        self.selected_model_key = None  # 'openai', 'local', 'internal_xxx' 형식
        
        # OpenAI API 초기화
        self._init_openai()
        
        # 사내망 모델 초기화 추가
        self._init_internal_models()
    
    def _init_openai(self):
        """OpenAI API 초기화"""
        global _llm_init_logged  # 함수 시작 부분에 global 선언
        
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                    # OpenAI 설정 읽기
                    openai_config = config.get('openai', {})
                    api_key = openai_config.get('api_key') or os.environ.get('OPENAI_API_KEY')
                    self.use_openai = config.get('llm', {}).get('use_openai', False)
                    self.openai_model = openai_config.get('model', 'gpt-4o')
                    
                    if api_key and self.use_openai:
                        try:
                            from openai import OpenAI
                            self.openai_client = OpenAI(api_key=api_key)
                            
                            # 네트워크 연결 확인 (오프라인 감지)
                            try:
                                import socket
                                socket.setdefaulttimeout(3)  # 3초 타임아웃
                                socket.create_connection(("api.openai.com", 443), timeout=3)
                                
                                # 연결 성공 시 추가 검증: 실제 생성 요청을 통해 API 키, 권한, Quota 모두 확인
                                try:
                                    # models.retrieve는 Quota를 확인하지 못하므로, 실제 생성을 시도합니다 (최소 토큰)
                                    self.openai_client.chat.completions.create(
                                        model=self.openai_model,
                                        messages=[{"role": "user", "content": "1"}],
                                        max_tokens=1
                                    )
                                    self.openai_available = True
                                    if not _llm_init_logged:
                                        safe_print(f"[INFO] OpenAI API 초기화 및 검증(생성 테스트) 완료 (모델: {self.openai_model})")
                                        _llm_init_logged = True
                                except Exception as auth_error:
                                    self.openai_available = False
                                    if not _llm_init_logged:
                                        error_type = type(auth_error).__name__
                                        safe_print(f"[WARN] OpenAI API 연결 성공했으나 사용 불가 ({error_type}): {str(auth_error)[:100]}")
                                        safe_print("       -> 키 만료, 한도 초과(Quota), 또는 권한 문제일 수 있습니다.")
                                        safe_print("       -> 로컬 모델 또는 사내망 모델을 우선 사용합니다.")
                                        _llm_init_logged = True
                                        
                            except (socket.timeout, socket.gaierror, OSError) as net_error:
                                # 네트워크 연결 실패 (오프라인)
                                self.openai_available = False
                                if not _llm_init_logged:
                                    safe_print("[INFO] 인터넷 연결 불가: OpenAI API 사용 불가. 로컬 모델을 사용합니다.")
                                    _llm_init_logged = True
                            except Exception as net_error:
                                # 기타 네트워크 오류
                                self.openai_available = False
                                if not _llm_init_logged:
                                    safe_print(f"[INFO] 네트워크 연결 확인 실패: {str(net_error)[:100]}. 로컬 모델을 사용합니다.")
                                    _llm_init_logged = True
                        except ImportError:
                            safe_print("[WARN] openai 라이브러리가 설치되지 않았습니다.")
                            safe_print("       pip install openai 필요")
                            self.openai_available = False
                        except Exception as e:
                            safe_print(f"[WARN] OpenAI API 초기화 실패: {e}")
                            self.openai_available = False
                    else:
                        if not api_key:
                            safe_print("[INFO] OpenAI API 키가 설정되지 않았습니다. 로컬 모델을 사용합니다.")
                        if not self.use_openai:
                            safe_print("[INFO] OpenAI 사용이 비활성화되어 있습니다. 로컬 모델을 사용합니다.")
        except Exception as e:
            safe_print(f"[WARN] OpenAI 초기화 중 오류: {e}")
            self.openai_available = False
    
    def _init_internal_models(self):
        """사내망 모델 초기화 (설정 파일에서 직접 로드)"""
        global _internal_models_logged  # 함수 시작 부분에 global 선언
        
        try:
            import yaml
            import socket
            from urllib.parse import urlparse
            
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                # 사내망 모델 설정 로드
                internal_config = config.get('internal_models', {})
                if not internal_config.get('enabled', False):
                    self.internal_models = {}
                    self.internal_models_available = {}
                    return
                
                # 모델 목록 로드
                models_config = internal_config.get('models', {})
                self.internal_models = models_config
                default_api_key = internal_config.get('api_key', 'dummy')
                
                # 각 모델의 사용 가능 여부 확인
                self.internal_models_available = {}
                for model_key, model_info in self.internal_models.items():
                    self.internal_models_available[model_key] = self._check_internal_model_availability(model_info)
                    
                    # 사용 가능한 모델의 API 키 설정
                    if 'api_key' not in model_info:
                        model_info['api_key'] = default_api_key
                        
                if self.internal_models:
                    available_count = sum(1 for v in self.internal_models_available.values() if v)
                    if not _internal_models_logged:
                        safe_print(f"[INFO] 사내망 모델 {len(self.internal_models)}개 중 {available_count}개 사용 가능")
                        _internal_models_logged = True
        except Exception as e:
            safe_print(f"[WARN] 사내망 모델 초기화 실패: {e}")
            self.internal_models = {}
            self.internal_models_available = {}

    def _check_internal_model_availability(self, model_info: Dict) -> bool:
        """사내망 모델 사용 가능 여부 확인"""
        try:
            import socket
            from urllib.parse import urlparse
            
            url = model_info.get('url', '')
            if not url:
                return False
            
            # URL에서 호스트 추출
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            
            if not host:
                return False
            
            # 연결 테스트 (타임아웃 3초)
            socket.setdefaulttimeout(3)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return result == 0
        except Exception as e:
            return False

    def _get_internal_model_client(self, model_key: str):
        """사내망 모델 클라이언트 가져오기 (캐싱)"""
        if model_key not in self.internal_models:
            raise ValueError(f"사내망 모델 '{model_key}'를 찾을 수 없습니다.")
        
        # 캐시 확인
        if model_key in self.internal_model_clients:
            return self.internal_model_clients[model_key]
        
        # 새 클라이언트 생성
        model_info = self.internal_models[model_key]
        from core_pipeline.internal_model_client import InternalModelClient
        
        client = InternalModelClient(
            model=model_info.get('name', model_key),
            base_url=model_info.get('url'),
            api_key=model_info.get('api_key', 'dummy'),
            models_parameter=model_info.get('models_parameter'),
            api_type=model_info.get('api_type', 'completions'),
            reasoning_effort=model_info.get('reasoning_effort'),
            max_tokens=model_info.get('max_tokens', 4096),
            temperature=model_info.get('temperature', 0.3),
            frequency_penalty=model_info.get('frequency_penalty', 0.1),
            enable_thinking=model_info.get('enable_thinking', False)
        )
        
        # 캐시에 저장
        self.internal_model_clients[model_key] = client
        return client

    def set_selected_model(self, model_key: str):
        """선택된 모델 설정"""
        self.selected_model_key = model_key

    def get_available_models(self) -> Dict:
        """사용 가능한 모든 모델 목록 반환"""
        # 로컬 모델 사용 가능 여부 확인 (모델이 로드되어 있거나 로드 가능한 경우)
        local_available = False
        if self.model is not None and self.tokenizer is not None:
            local_available = True
        else:
            # 모델 경로가 있으면 사용 가능으로 간주 (Lazy Loading)
            try:
                import yaml
                config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        model_path = config.get('llm', {}).get('model_path', './models/llm/beomi-gemma-ko-2b')
                        if model_path and not os.path.isabs(model_path):
                            base_dir = os.path.dirname(os.path.dirname(__file__))
                            model_path = os.path.join(base_dir, model_path)
                            model_path = os.path.normpath(model_path)
                        if model_path and os.path.exists(model_path):
                            local_available = True
            except:
                pass
        
        models = {
            'openai': {
                'name': f'OpenAI {self.openai_model}',
                'type': 'openai',
                'available': self.openai_available,
                'description': 'OpenAI GPT-4o (외부 인터넷 필요)'
            },
            'local': {
                'name': '로컬 모델',
                'type': 'local',
                'available': local_available,
                'description': '로컬 LLM 모델 (beomi-gemma-ko-2b)'
            }
        }
        
        # 사내망 모델 추가
        for model_key, model_info in self.internal_models.items():
            models[f'internal_{model_key}'] = {
                'name': model_info.get('name', model_key),
                'type': 'internal',
                'available': self.internal_models_available.get(model_key, False),
                'description': model_info.get('description', '사내망 모델'),
                'model_key': model_key
            }
        
        return models
    
    def load_model(self, force_reload=False, force_gpu=False):
        """
        로컬 LLM 모델을 로드합니다 (GPTQ 양자화 모델 지원, 캐싱 지원).
        
        Args:
            force_reload: True면 캐시 무시하고 재로드
            force_gpu: True면 GPU 강제 사용
        
        Returns:
            (model, tokenizer) 튜플 또는 (None, None) (로드 실패 시)
        """
        global _cached_model, _cached_tokenizer, _cached_model_path
        
        try:
            # config에서 모델 경로 가져오기
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
            model_path = None
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    model_path = config.get('llm', {}).get('model_path', './models/llm/beomi-gemma-ko-2b')
            
            # 상대 경로를 절대 경로로 변환
            if model_path and not os.path.isabs(model_path):
                base_dir = os.path.dirname(os.path.dirname(__file__))
                model_path = os.path.join(base_dir, model_path)
                model_path = os.path.normpath(model_path)
            
            # 모델 경로 확인
            if not model_path or not os.path.exists(model_path):
                safe_print(f"[WARN] LLM 모델 경로가 없습니다: {model_path}")
                safe_print(f"   설정 파일: {config_path}")
                safe_print(f"   예상 경로: {model_path}")
                safe_print("   모델을 복사하려면 다음 명령을 실행하세요:")
                safe_print("   python scripts/copy_models_from_poc.py")
                safe_print("   또는 HuggingFace에서 자동 다운로드를 시도합니다...")
                
                # HuggingFace 자동 다운로드 시도
                # config에서 모델 이름 가져오기
                try:
                    import yaml
                    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                            model_name = config.get('llm', {}).get('model_name', 'beomi/gemma-ko-2b')
                            
                            # HuggingFace 모델 다운로드 시도
                            safe_print(f"모델 경로가 없습니다. HuggingFace에서 다운로드 시도: {model_name}")
                            try:
                                from huggingface_hub import snapshot_download
                                base_dir = os.path.dirname(os.path.dirname(__file__))
                                target_path = model_path or os.path.join(base_dir, "models", "llm", "beomi-gemma-ko-2b")
                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                snapshot_download(repo_id=model_name, local_dir=target_path)
                                model_path = target_path
                                safe_print(f"[OK] 모델 다운로드 완료: {model_path}")
                            except ImportError:
                                safe_print("[WARN] huggingface_hub가 설치되지 않았습니다. pip install huggingface_hub 필요")
                            except Exception as e:
                                safe_print(f"[WARN] 모델 다운로드 실패: {e}")
                except Exception as e:
                    safe_print(f"[WARN] 설정 로드 실패: {e}")
            
            if not model_path or not os.path.exists(model_path):
                safe_print(f"LLM 모델 경로가 없습니다: {model_path}")
                return None, None
            
            # 캐시된 모델이 있고 경로가 같으면 재사용
            if not force_reload and _cached_model is not None and _cached_tokenizer is not None:
                if _cached_model_path == model_path:
                    try:
                        import torch
                        cached_device = next(_cached_model.parameters()).device
                        cuda_available = torch.cuda.is_available()
                        
                        # 개선 2: 캐시된 모델이 CPU에 있으면 그대로 사용 (GPU 이동 제거)
                        if cached_device.type == 'cpu':
                            safe_print("✅ 캐시된 모델 재사용 (CPU 모드)")
                            self.model = _cached_model
                            self.tokenizer = _cached_tokenizer
                            self.model_path = model_path
                            return self.model, self.tokenizer
                        # 캐시된 모델이 GPU에 있으면 그대로 사용
                        elif cached_device.type == 'cuda':
                            safe_print(f"✅ 캐시된 모델 재사용 (GPU: {torch.cuda.get_device_name(0)})")
                            self.model = _cached_model
                            self.tokenizer = _cached_tokenizer
                            self.model_path = model_path
                            return self.model, self.tokenizer
                        # 기타 경우 (meta 등)
                        else:
                            safe_print("✅ 캐시된 모델 재사용")
                            self.model = _cached_model
                            self.tokenizer = _cached_tokenizer
                            self.model_path = model_path
                            return self.model, self.tokenizer
                    except Exception as e:
                        safe_print(f"⚠️ 캐시된 모델 디바이스 확인 실패: {e}")
                        pass
            
            # 모델 파일 확인
            model_files = os.listdir(model_path)
            has_model = any(f.startswith("model") or f == "config.json" for f in model_files)
            if not has_model:
                safe_print(f"LLM 모델 파일이 없습니다: {model_path}")
                return None, None
            
            # GPTQ 설정 파일 확인
            quantize_config_path = os.path.join(model_path, "quantize_config.json")
            has_quantize_config = os.path.exists(quantize_config_path)
            
            # config.json에서 실제 모델 타입 확인
            import json
            config_path = os.path.join(model_path, "config.json")
            is_gptq_model = False
            if has_quantize_config and os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        if 'quantization_config' not in config:
                            is_gptq_model = False
                        else:
                            is_gptq_model = True
                except:
                    is_gptq_model = has_quantize_config
            else:
                is_gptq_model = has_quantize_config
            
            safe_print(f"LLM 모델 로딩 시도: {model_path}")
            if is_gptq_model:
                safe_print("  GPTQ 양자화 모델 감지됨")
            
            # transformers 라이브러리 확인
            try:
                from transformers import AutoTokenizer
            except ImportError:
                safe_print("transformers 라이브러리가 설치되지 않았습니다. pip install transformers 필요")
                return None, None
            
            # PyTorch 확인
            try:
                import torch
            except ImportError:
                safe_print("torch 라이브러리가 설치되지 않았습니다. pip install torch 필요")
                return None, None
            
            # accelerate 라이브러리 확인 (device_map 사용 시 필요)
            try:
                import accelerate
                accelerate_available = True
            except ImportError:
                accelerate_available = False
                safe_print("[WARN] accelerate 라이브러리가 설치되지 않았습니다.")
                safe_print("       device_map='auto' 사용 시 필요합니다. pip install accelerate")
            
            # bitsandbytes 라이브러리 확인 (8-bit 양자화 사용 시 필요)
            try:
                import bitsandbytes as bnb
                from transformers import BitsAndBytesConfig
                bitsandbytes_available = True
            except ImportError:
                bitsandbytes_available = False
                safe_print("[INFO] bitsandbytes 라이브러리가 설치되지 않았습니다.")
                safe_print("       8-bit 양자화를 사용하려면: pip install bitsandbytes")
            
            # 토크나이저 로드
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
            except Exception as e:
                safe_print(f"토크나이저 로딩 실패: {e}")
                return None, None
            
            # 모델 로드
            try:
                cuda_available = torch.cuda.is_available()
                safe_print(f"  CUDA 사용 가능 여부: {cuda_available}")
                if cuda_available:
                    safe_print(f"  CUDA 버전: {torch.version.cuda}")
                    safe_print(f"  GPU 개수: {torch.cuda.device_count()}")
                    safe_print(f"  GPU 이름: {torch.cuda.get_device_name(0)}")
                
                device_map = "auto" if cuda_available else None
                
                if is_gptq_model:
                    # GPTQ 양자화 모델 로드
                    try:
                        from auto_gptq import AutoGPTQForCausalLM
                        
                        safe_print("  AutoGPTQ를 사용하여 GPTQ 모델 로딩 중...")
                        
                        model = AutoGPTQForCausalLM.from_quantized(
                            model_path,
                            device_map=device_map,
                            trust_remote_code=True,
                            use_safetensors=True,
                            low_cpu_mem_usage=True
                        )
                        
                        safe_print(f"✅ GPTQ 모델 로딩 성공: {model_path}")
                        if torch.cuda.is_available():
                            safe_print(f"   GPU 사용: {torch.cuda.get_device_name(0)}")
                        else:
                            safe_print("   CPU 모드 사용 (GPTQ 모델은 CPU에서 느릴 수 있습니다)")
                        
                        # 캐시에 저장
                        _cached_model = model
                        _cached_tokenizer = tokenizer
                        _cached_model_path = model_path
                        
                        self.model = model
                        self.tokenizer = tokenizer
                        self.model_path = model_path
                        
                        return self.model, self.tokenizer
                        
                    except ImportError:
                        safe_print("⚠️ auto-gptq 라이브러리가 설치되지 않았습니다.")
                        safe_print("   GPTQ 모델을 로드하려면 다음 명령어를 실행하세요:")
                        safe_print("   pip install auto-gptq")
                        return None, None
                    except Exception as e:
                        safe_print(f"GPTQ 모델 로딩 실패: {e}")
                        import traceback
                        traceback.print_exc()
                        return None, None
                else:
                    # 일반 모델 로드
                    cuda_available = torch.cuda.is_available()
                    dtype = torch.float16 if cuda_available else torch.float32
                    
                    from transformers import AutoModelForCausalLM
                    
                    # 개선 1: CPU 우선 정책 - GPU 메모리 사전 확인
                    gpu_memory_free = 0.0
                    if cuda_available:
                        try:
                            gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                            gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
                            gpu_memory_free = gpu_memory_total - gpu_memory_allocated
                            safe_print(f"  GPU 메모리 상태: {gpu_memory_free:.2f} GB 사용 가능 / {gpu_memory_total:.2f} GB 전체")
                            
                            # GPU 메모리가 3GB 미만이면 CPU 우선 정책 적용
                            if gpu_memory_free < 3.0:
                                safe_print(f"  ⚠️ GPU 메모리 부족 ({gpu_memory_free:.2f} GB). CPU 우선 정책 적용.")
                                cuda_available = False
                                force_gpu = False
                        except Exception:
                            pass
                    
                    # accelerate 없으면 device_map 사용 불가 - CPU 모드로 전환
                    if not accelerate_available and cuda_available:
                        safe_print("  ⚠️ accelerate 없음. CPU 모드로 로드합니다.")
                        cuda_available = False
                    
                    # CPU 우선 정책: GPU 메모리 부족하거나 force_gpu가 False면 바로 CPU 모드
                    if not force_gpu and (not cuda_available or (cuda_available and gpu_memory_free < 3.0)):
                        safe_print("  CPU 우선 정책: CPU 모드로 빠른 로딩...")
                        model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            torch_dtype=torch.float32,
                            device_map=None,
                            low_cpu_mem_usage=False,
                            trust_remote_code=True
                        )
                        model = model.to('cpu')
                        safe_print("  ✅ CPU 모드 로드 완료")
                        
                        # 캐시에 저장
                        _cached_model = model
                        _cached_tokenizer = tokenizer
                        _cached_model_path = model_path
                        
                        self.model = model
                        self.tokenizer = tokenizer
                        self.model_path = model_path
                        
                        return self.model, self.tokenizer
                    
                    if cuda_available and accelerate_available:
                        model = None
                        last_error = None
                        
                        # 방법 0: 양자화 (bitsandbytes 사용) - 가장 먼저 시도
                        if bitsandbytes_available and model is None:
                            # GPU 메모리 확인 및 정리
                            gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                            gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
                            gpu_memory_free = gpu_memory_total - gpu_memory_allocated
                            
                            # GPU 캐시 정리
                            torch.cuda.empty_cache()
                            gpu_memory_free = gpu_memory_total - torch.cuda.memory_allocated(0) / 1024**3
                            
                            safe_print(f"  GPU 메모리 상태: {gpu_memory_free:.2f} GB 사용 가능")
                            
                            # 4-bit 양자화 시도 (더 작은 메모리 사용)
                            try:
                                safe_print("  방법 0-1: 4-bit 양자화 (bitsandbytes) 시도...")
                                safe_print(f"    → 모델 크기: 약 10GB → 1.25GB로 감소")
                                
                                # GPU 메모리 확인
                                torch.cuda.empty_cache()
                                gpu_memory_free = gpu_memory_total - torch.cuda.memory_allocated(0) / 1024**3
                                safe_print(f"    → 사용 가능 GPU 메모리: {gpu_memory_free:.2f} GB")
                                
                                quantization_config = BitsAndBytesConfig(
                                    load_in_4bit=True,
                                    bnb_4bit_compute_dtype=torch.float16,
                                    bnb_4bit_use_double_quant=True,
                                    bnb_4bit_quant_type="nf4"
                                )
                                
                                # 처음부터 device_map="auto"로 한 번만 로드 (최적화)
                                safe_print("    → 모델 로딩 중... (이 작업은 몇 분 걸릴 수 있습니다)")
                                
                                if gpu_memory_free > 1.5:  # GPU 메모리가 충분하면 GPU 우선 사용
                                    max_memory = {
                                        0: f"{int(gpu_memory_free * 0.85 * 1024)}MB",  # GPU 메모리의 85% 사용
                                        "cpu": "20GB"
                                    }
                                    safe_print(f"    → GPU 우선 모드 (최대 {gpu_memory_free * 0.85:.2f} GB 사용)")
                                else:
                                    max_memory = {
                                        "cpu": "20GB"
                                    }
                                    safe_print("    → CPU 모드 (GPU 메모리 부족)")
                                
                                # 한 번만 로드 (device_map="auto"가 자동으로 GPU/CPU 분배)
                                # torch_dtype을 명시하여 meta tensor 오류 방지
                                model = AutoModelForCausalLM.from_pretrained(
                                    model_path,
                                    quantization_config=quantization_config,
                                    device_map="auto",
                                    max_memory=max_memory,
                                    torch_dtype=torch.float16,  # meta tensor 오류 방지
                                    low_cpu_mem_usage=False,  # meta tensor 오류 방지
                                    trust_remote_code=True
                                )
                                
                                safe_print("    → 모델 로딩 완료")
                                
                                # 실제 GPU/CPU 할당 확인
                                gpu_params = sum(p.numel() for p in model.parameters() if p.device.type == 'cuda')
                                cpu_params = sum(p.numel() for p in model.parameters() if p.device.type == 'cpu')
                                total_params = sum(p.numel() for p in model.parameters())
                                
                                if gpu_params > 0:
                                    safe_print(f"    → GPU에 {gpu_params/total_params*100:.1f}% 할당됨")
                                if cpu_params > 0:
                                    safe_print(f"    → CPU에 {cpu_params/total_params*100:.1f}% 할당됨")
                                
                                safe_print("  ✅ 방법 0-1 성공: 4-bit 양자화 완료")
                                
                            except Exception as e0_1:
                                error_msg = str(e0_1)
                                safe_print(f"  ⚠️ 방법 0-1 (4-bit) 실패: {error_msg[:150]}")
                                # 모델 정리
                                if 'model' in locals() and model is not None:
                                    try:
                                        del model
                                        torch.cuda.empty_cache()
                                    except:
                                        pass
                                model = None
                                
                                # 8-bit 양자화 시도 (4-bit 실패 시)
                                try:
                                    safe_print("  방법 0-2: 8-bit 양자화 (bitsandbytes) 시도...")
                                    safe_print(f"    → 모델 크기: 약 10GB → 2.5GB로 감소")
                                    
                                    # GPU 메모리 재확인
                                    torch.cuda.empty_cache()
                                    gpu_memory_free = gpu_memory_total - torch.cuda.memory_allocated(0) / 1024**3
                                    safe_print(f"    → 사용 가능 GPU 메모리: {gpu_memory_free:.2f} GB")
                                    
                                    quantization_config = BitsAndBytesConfig(
                                        load_in_8bit=True,
                                        llm_int8_threshold=6.0,
                                        llm_int8_has_fp16_weight=False
                                    )
                                    
                                    # 처음부터 device_map="auto"로 한 번만 로드 (최적화)
                                    safe_print("    → 모델 로딩 중... (이 작업은 몇 분 걸릴 수 있습니다)")
                                    
                                    if gpu_memory_free > 2.0:  # GPU 메모리가 충분하면 GPU 우선 사용
                                        max_memory = {
                                            0: f"{int(gpu_memory_free * 0.85 * 1024)}MB",  # GPU 메모리의 85% 사용
                                            "cpu": "20GB"
                                        }
                                        safe_print(f"    → GPU 우선 모드 (최대 {gpu_memory_free * 0.85:.2f} GB 사용)")
                                    else:
                                        max_memory = {
                                            "cpu": "20GB"
                                        }
                                        safe_print("    → CPU 모드 (GPU 메모리 부족)")
                                    
                                    # 한 번만 로드 (device_map="auto"가 자동으로 GPU/CPU 분배)
                                    # torch_dtype을 명시하여 meta tensor 오류 방지
                                    model = AutoModelForCausalLM.from_pretrained(
                                        model_path,
                                        quantization_config=quantization_config,
                                        device_map="auto",
                                        max_memory=max_memory,
                                        torch_dtype=torch.float16,  # meta tensor 오류 방지
                                        low_cpu_mem_usage=False,  # meta tensor 오류 방지
                                        trust_remote_code=True
                                    )
                                    
                                    safe_print("    → 모델 로딩 완료")
                                    
                                    # 실제 GPU/CPU 할당 확인
                                    gpu_params = sum(p.numel() for p in model.parameters() if p.device.type == 'cuda')
                                    cpu_params = sum(p.numel() for p in model.parameters() if p.device.type == 'cpu')
                                    total_params = sum(p.numel() for p in model.parameters())
                                    
                                    if gpu_params > 0:
                                        safe_print(f"    → GPU에 {gpu_params/total_params*100:.1f}% 할당됨")
                                    if cpu_params > 0:
                                        safe_print(f"    → CPU에 {cpu_params/total_params*100:.1f}% 할당됨")
                                    
                                    safe_print("  ✅ 방법 0-2 성공: 8-bit 양자화 완료")
                                        
                                except Exception as e0_2:
                                    last_error = e0_2
                                    error_msg = str(e0_2)
                                    safe_print(f"  ⚠️ 방법 0-2 (8-bit) 실패: {error_msg[:150]}")
                                    safe_print("    → 양자화 실패, 일반 로드 방법 시도")
                                    # 모델 정리
                                    if 'model' in locals() and model is not None:
                                        try:
                                            del model
                                            torch.cuda.empty_cache()
                                        except:
                                            pass
                                    model = None
                        
                        # 방법 1: CPU에 로드 후 GPU 이동 (메모리 부족 시 실패 가능)
                        if model is None:
                            try:
                                safe_print("  방법 1: CPU에 로드 후 GPU 이동 시도...")
                                model = AutoModelForCausalLM.from_pretrained(
                                    model_path,
                                    torch_dtype=dtype,  # dtype 대신 torch_dtype 사용
                                    device_map=None,
                                    low_cpu_mem_usage=False,  # meta tensor 오류 방지
                                    trust_remote_code=True
                                )
                                # GPU 메모리 확인 후 이동
                                try:
                                    # GPU 캐시 정리 시도
                                    torch.cuda.empty_cache()
                                    model = model.to('cuda:0')
                                    safe_print("  ✅ 방법 1 성공: CPU 로드 후 GPU 이동")
                                except torch.cuda.OutOfMemoryError as oom:
                                    safe_print(f"  ⚠️ 방법 1 GPU 이동 실패 (메모리 부족)")
                                    safe_print("  → 방법 2 (device_map='auto')로 시도합니다.")
                                    # 모델 해제 (방법 2에서 다시 로드)
                                    del model
                                    torch.cuda.empty_cache()
                                    model = None  # 방법 2에서 다시 로드하도록
                                    # 방법 2로 진행하기 위해 예외 발생
                                    raise Exception("GPU 메모리 부족으로 방법 2 시도")
                            except Exception as e1:
                                last_error = e1
                                if "GPU 메모리 부족" not in str(e1):
                                    safe_print(f"  ⚠️ 방법 1 실패: {str(e1)[:100]}")
                                
                                # 방법 2: device_map='auto' (accelerate 필요) - 모델이 GPU 메모리에 맞지 않을 때 분할 로드
                                if accelerate_available and model is None:
                                    try:
                                        safe_print("  방법 2: device_map='auto' 시도...")
                                        model = AutoModelForCausalLM.from_pretrained(
                                            model_path,
                                            torch_dtype=dtype,  # dtype 대신 torch_dtype 사용, meta tensor 오류 방지
                                            device_map="auto",
                                            low_cpu_mem_usage=False,  # meta tensor 오류 방지
                                            trust_remote_code=True
                                        )
                                        safe_print("  ✅ 방법 2 성공: device_map='auto'")
                                    except Exception as e2:
                                        last_error = e2
                                        safe_print(f"  ⚠️ 방법 2 실패: {str(e2)[:100]}")
                                        
                                        # 방법 3: CPU 모드로 전환
                                        try:
                                            safe_print("  방법 3: CPU 모드로 로드 시도...")
                                            model = AutoModelForCausalLM.from_pretrained(
                                                model_path,
                                                torch_dtype=torch.float32,  # dtype 대신 torch_dtype 사용
                                                device_map=None,
                                                low_cpu_mem_usage=False,  # meta tensor 오류 방지
                                                trust_remote_code=True
                                            )
                                            model = model.to('cpu')
                                            safe_print("  ✅ 방법 3 성공: CPU 모드")
                                            cuda_available = False
                                        except Exception as e3:
                                            last_error = e3
                                            safe_print(f"  ❌ 모든 방법 실패")
                                            raise e3
                            else:
                                # accelerate 없으면 바로 CPU 모드
                                safe_print("  방법 2: CPU 모드로 로드 시도...")
                                model = AutoModelForCausalLM.from_pretrained(
                                    model_path,
                                    torch_dtype=torch.float32,  # dtype 대신 torch_dtype 사용
                                    device_map=None,
                                    low_cpu_mem_usage=False,  # meta tensor 오류 방지
                                    trust_remote_code=True
                                )
                                model = model.to('cpu')
                                safe_print("  ✅ CPU 모드 로드 성공")
                                cuda_available = False
                        
                        if model is None:
                            raise Exception("모델 로딩 실패: 모든 방법이 실패했습니다.")
                    else:
                        # CPU 모드 (accelerate 없거나 GPU 메모리 부족)
                        safe_print("  CPU 모드로 로드 중...")
                        model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            torch_dtype=torch.float32,  # dtype 대신 torch_dtype 사용
                            device_map=None,
                            low_cpu_mem_usage=False,  # meta tensor 오류 방지
                            trust_remote_code=True
                        )
                        model = model.to('cpu')
                    
                    safe_print(f"✅ LLM 모델 로딩 성공: {model_path}")
                    model_device = next(model.parameters()).device
                    if model_device.type == 'cuda':
                        safe_print(f"   GPU 사용: {torch.cuda.get_device_name(0)} (디바이스: {model_device})")
                    else:
                        safe_print(f"   CPU 모드 사용 (디바이스: {model_device})")
                        # GPU로 이동 시도하지 않음 (이미 메모리 부족으로 실패했을 수 있음)
                    
                    # 캐시에 저장
                    _cached_model = model
                    _cached_tokenizer = tokenizer
                    _cached_model_path = model_path
                    
                    self.model = model
                    self.tokenizer = tokenizer
                    self.model_path = model_path
                    
                    return self.model, self.tokenizer
                    
            except Exception as e:
                safe_print(f"모델 로딩 실패: {e}")
                import traceback
                traceback.print_exc()
                return None, None
                
        except Exception as e:
            safe_print(f"LLM 모델 로딩 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def is_available(self):
        """LLM 모델이 사용 가능한지 확인 (OpenAI, 사내망 모델, 또는 로컬 모델)"""
        # OpenAI 사용 가능하면 True
        if self.openai_available:
            return True
        
        # 사내망 모델 사용 가능 여부 확인
        if self.internal_models:
            available_internal = any(
                self.internal_models_available.get(model_key, False)
                for model_key in self.internal_models.keys()
            )
            if available_internal:
                return True
        
        # OpenAI와 사내망 모델이 모두 사용 불가할 때만 로컬 모델 확인
        # 로컬 모델은 Lazy Loading (필요할 때만 로드)
        if self.model is None or self.tokenizer is None:
            # 로컬 모델 경로 확인만 하고 실제 로드는 하지 않음 (초기화 시간 절약)
            try:
                import yaml
                config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        model_path = config.get('llm', {}).get('model_path', './models/llm/beomi-gemma-ko-2b')
                        if model_path and not os.path.isabs(model_path):
                            base_dir = os.path.dirname(os.path.dirname(__file__))
                            model_path = os.path.join(base_dir, model_path)
                            model_path = os.path.normpath(model_path)
                        # 경로만 확인 (실제 로드는 하지 않음)
                        if model_path and os.path.exists(model_path):
                            return True  # 경로가 있으면 사용 가능하다고 간주 (실제 로드는 나중에)
            except:
                pass
            return False  # 모델이 로드되지 않았고 경로도 확인 불가
        
        return self.model is not None and self.tokenizer is not None
    
    def generate(self, prompt: str, max_tokens: int = 512, **kwargs):
        """
        텍스트 생성 (선택된 모델에 따라 라우팅)
        
        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            **kwargs: 추가 생성 파라미터
            
        Returns:
            생성된 텍스트
        """
        # 전역 변수 선언 (함수 시작 부분에 위치)
        global _last_logged_model
        
        # 선택된 모델 확인 (세션 상태 또는 기본값)
        selected_model = self.selected_model_key
        
        # 선택된 모델이 없으면 기본 우선순위 사용
        if not selected_model:
            # 우선순위: gpt-4o → 사내망 첫 번째 → 로컬 모델
            if self.openai_available and self.use_openai:
                selected_model = 'openai'
            elif self.internal_models:
                # 사용 가능한 첫 번째 사내망 모델 선택
                available_internal = [
                    f'internal_{model_key}' for model_key in self.internal_models.keys()
                    if self.internal_models_available.get(model_key, False)
                ]
                if available_internal:
                    selected_model = available_internal[0]
                else:
                    selected_model = 'local'
            else:
                selected_model = 'local'
        
        # 모델 타입에 따라 라우팅
        if selected_model.startswith('internal_'):
            # 사내망 모델 사용
            model_key = selected_model.replace('internal_', '')
            if model_key not in self.internal_models:
                safe_print(f"[WARN] 사내망 모델 '{model_key}'를 찾을 수 없습니다. 다른 모델로 폴백합니다.")
                # 다른 사용 가능한 모델 찾기
                if self.openai_available and self.use_openai:
                    selected_model = 'openai'
                else:
                    selected_model = 'local'
            else:
                try:
                    client = self._get_internal_model_client(model_key)
                    system_prompt = kwargs.get('system_prompt', 'You are a helpful assistant. Respond in Korean.')
                    response = client.generate(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
                    # 중복 로그 방지: 모델이 변경되거나 첫 호출 시에만 로그 출력 (전역 변수 사용)
                    current_model_key = f'internal_{model_key}'
                    if _last_logged_model != current_model_key:
                        safe_print(f"[INFO] 사내망 모델 사용: {model_key}")
                        _last_logged_model = current_model_key
                    return response
                except Exception as e:
                    import traceback
                    safe_print(f"[DEBUG] Error Traceback: {traceback.format_exc()}")
                    safe_print(f"[WARN] 사내망 모델 호출 실패: {e}. 다른 모델로 폴백합니다.")
                    # 다른 사용 가능한 모델 찾기 (우선순위: OpenAI > 다른 사내망 모델 > 로컬 모델)
                    if self.openai_available and self.use_openai:
                        selected_model = 'openai'
                    else:
                        # 다른 사용 가능한 사내망 모델 찾기
                        other_internal = [
                            f'internal_{k}' for k in self.internal_models.keys()
                            if k != model_key and self.internal_models_available.get(k, False)
                        ]
                        if other_internal:
                            selected_model = other_internal[0]
                            fallback_key = selected_model.replace('internal_', '')
                            safe_print(f"[INFO] 다른 사내망 모델로 폴백: {fallback_key}")
                            
                            # 폴백 모델 즉시 실행
                            try:
                                client = self._get_internal_model_client(fallback_key)
                                system_prompt = kwargs.get('system_prompt', 'You are a helpful assistant. Respond in Korean.')
                                response = client.generate(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
                                
                                # 로그 업데이트
                                if _last_logged_model != selected_model:
                                    safe_print(f"[INFO] 사내망 모델 사용 (폴백): {fallback_key}")
                                    _last_logged_model = selected_model
                                return response
                            except Exception as e_fallback:
                                import traceback
                                safe_print(f"[DEBUG] Fallback Error Trace: {traceback.format_exc()}")
                                safe_print(f"[WARN] 폴백 모델({fallback_key}) 호출 실패: {e_fallback}")
                                # 실패 시 계속 진행하여 로컬 모델로 넘어감
                                selected_model = 'local'
                        else:
                            selected_model = 'local'
        
        # OpenAI 또는 로컬 모델 사용 (기존 로직)
        if selected_model == 'openai' and self.openai_available and self.use_openai:
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Respond in Korean."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=kwargs.get("temperature", 0.0),
                )
                content = response.choices[0].message.content
                generated_text = (content if content is not None else "").strip()
                # 중복 로그 방지: 모델이 변경되거나 첫 호출 시에만 로그 출력 (전역 변수 사용)
                if _last_logged_model != 'openai':
                    safe_print(f"[INFO] OpenAI API 사용: {self.openai_model}")
                    _last_logged_model = 'openai'
                return generated_text
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                safe_print(f"[WARN] OpenAI API 호출 실패 ({error_type}): {error_msg[:150]}")
                
                # 치명적인 오류(인증, 요금, 할당량)인 경우 OpenAI 비활성화하여 이후 호출부터는 즉시 폴백
                start_fallback = False
                if 'AuthenticationError' in error_type or 'RateLimitError' in error_type or 'insufficient_quota' in error_msg:
                    self.openai_available = False
                    start_fallback = True
                    safe_print(f"[WARN] OpenAI API 키가 유효하지 않거나 한도 초과입니다. 세션 동안 OpenAI를 비활성화합니다.")
                elif 'APIConnectionError' in error_type:
                    # 연결 오류는 일시적일 수 있으나, 반복되면 느리므로 우선 비활성화 고려 (현재는 폴백만 수행)
                    start_fallback = True
                    safe_print(f"[WARN] OpenAI API 연결 실패. 폴백을 시도합니다.")
                else:
                    # 기타 오류는 폴백 시도
                    start_fallback = True
                
                # 다른 사용 가능한 모델 찾기 (사내망 모델 우선, 없으면 로컬 모델)
                if self.internal_models:
                    available_internal = [
                        model_key for model_key in self.internal_models.keys()
                        if self.internal_models_available.get(model_key, False)
                    ]
                    if available_internal:
                        # 첫 번째 사용 가능한 사내망 모델 사용
                        fallback_model_key = available_internal[0]
                        safe_print(f"[INFO] 사내망 모델로 폴백합니다: {fallback_model_key}")
                        
                        # 선택된 모델 변경 (선택사항)
                        if self.openai_available is False:
                            self.selected_model_key = f'internal_{fallback_model_key}'
                            
                        try:
                            client = self._get_internal_model_client(fallback_model_key)
                            system_prompt = kwargs.get('system_prompt', 'You are a helpful assistant. Respond in Korean.')
                            response = client.generate(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
                            return response
                        except Exception as e2:
                            safe_print(f"[WARN] 사내망 모델 폴백도 실패: {e2}. 로컬 모델로 폴백합니다.")
                
                # 사내망 모델도 없거나 실패하면 로컬 모델 로드 (Lazy Loading)
                safe_print("[INFO] 로컬 모델로 폴백합니다.")
                
                # 선택된 모델 영구 변경 (OpenAI 사용 불가 시)
                if self.openai_available is False:
                    self.selected_model_key = 'local'
                    
                if self.model is None or self.tokenizer is None:
                    safe_print("[INFO] 로컬 모델 로딩 중... (이 작업은 몇 분 걸릴 수 있습니다)")
                    result = self.load_model()
                    if result is None or result[0] is None:
                        safe_print("[WARN] 로컬 모델 로딩 실패.")
                        return f"[OpenAI Error] {error_msg[:200]} \n[Fallback Error] Local model loading failed."
        
        # 로컬 모델 사용 (폴백)
        # 로컬 모델이 로드되지 않았으면 로드 시도
        if self.model is None or self.tokenizer is None:
            # 다른 모델이 모두 실패했을 때만 로컬 모델 로드
            safe_print("[INFO] 로컬 모델 로딩 중... (외부/사내망 모델 모두 사용 불가)")
            result = self.load_model()
            if result is None or result[0] is None:
                return f"[LLM not available] Prompt: {prompt[:100]}..."
        
        try:
            import torch
            
            # 입력 토크나이징
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            # 디바이스 설정
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # 생성 파라미터
            generation_kwargs = {
                "max_new_tokens": max_tokens,
                "do_sample": kwargs.get("do_sample", False),
                "temperature": kwargs.get("temperature", 0.0),
                "top_p": kwargs.get("top_p", 0.9),
            }
            generation_kwargs.update(kwargs)
            
            # 텍스트 생성
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **generation_kwargs)
            
            # 디코딩
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 프롬프트 제거 (생성된 부분만 반환)
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):].strip()
            
            safe_print("[INFO] 로컬 모델 사용")
            return generated_text
            
        except Exception as e:
            safe_print(f"[WARN] LLM generation failed: {e}")
            return f"[Generation Error] {str(e)}"
    
    def summarize(self, items):
        """
        항목 요약
        
        Args:
            items: 요약할 항목들 (리스트 또는 문자열)
            
        Returns:
            요약 텍스트
        """
        if isinstance(items, list):
            joined = "\n".join([str(i) for i in items])
        else:
            joined = str(items)
        
        prompt = f"요약:\n{joined}\n---\n요약 결과:"
        return self.generate(prompt, max_tokens=128)
    
    def generate_with_prompt(self, agent_name: str, context: str, **kwargs) -> str:
        """
        프롬프트 템플릿을 사용하여 응답 생성
        
        Args:
            agent_name: Agent 이름 (DefenseCOAAgent, IntelManagementAgent 등)
            context: 컨텍스트 데이터
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 텍스트
        """
        try:
            import yaml
            from pathlib import Path
            
            # 프롬프트 템플릿 로드
            template_path = Path(__file__).parent.parent / "config" / "prompt_templates.yaml"
            
            if not template_path.exists():
                # 기본 프롬프트 사용
                prompt = f"질문: {context}\n답변:"
                return self.generate(prompt, **kwargs)
            
            with open(template_path, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
            
            # Agent별 템플릿 찾기
            agent_template = templates.get(agent_name, templates.get("Default", {}))
            
            system_prompt = agent_template.get("system", "너는 AI 어시스턴트이다.")
            user_template = agent_template.get("user_template", "{context}")
            
            # 컨텍스트 삽입
            user_prompt = user_template.format(context=context, **kwargs)
            
            # 최종 프롬프트 구성
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            return self.generate(full_prompt, **kwargs)
            
        except Exception as e:
            safe_print(f"[WARN] Prompt template loading failed: {e}")
            # 기본 생성으로 폴백
            return self.generate(context, **kwargs)
    
    def generate_with_citations(self, query: str, contexts: List[Dict], max_tokens: int = 1024) -> str:
        """
        인용 포함 응답 생성 (고도화됨)
        RAG 결과뿐만 아니라 전술적 추론 가설, 지식 그래프 문맥 등을 종합하여 답변 생성
        
        Args:
            query: 사용자 질문
            contexts: 검색 결과 리스트 
            max_tokens: 최대 토큰 수
            
        Returns:
            답변 텍스트
        """
        # 사용 가능한 모델이 있는지 확인
        has_available_model = (
            self.openai_available or
            any(self.internal_models_available.get(k, False) for k in self.internal_models.keys()) or
            (self.model is not None and self.tokenizer is not None)
        )
        
        if not has_available_model:
            # 로컬 모델 경로 확인 등 기존 로직 유지
            try:
                import yaml
                config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'model_config.yaml')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        model_path = config.get('llm', {}).get('model_path', './models/llm/beomi-gemma-ko-2b')
                        if model_path and not os.path.isabs(model_path):
                            base_dir = os.path.dirname(os.path.dirname(__file__))
                            model_path = os.path.join(base_dir, model_path)
                            model_path = os.path.normpath(model_path)
                        if not (model_path and os.path.exists(model_path)):
                            return f"[LLM not available] 질문: {query}"
            except:
                return f"[LLM not available] 질문: {query}"
        
        # 컨텍스트 분류 및 정리
        agent_result_text = None
        hypothesis_text = None
        situation_text = None
        coa_text = None
        graph_contexts = []
        rag_contexts = []
        
        for i, ctx in enumerate(contexts):
            text = ctx.get('text', '')
            metadata = ctx.get('metadata', {})
            source = metadata.get('source', '')
            ctx_type = metadata.get('type', '')
            
            # 1. Agent 실행 결과
            if source == 'agent' or '[Agent 실행 결과 데이터]' in text:
                agent_result_text = text
            # 2. 전술적 가설 (Reasoning Engine)
            elif source == 'ReasoningEngine' and ctx_type == 'hypothesis':
                hypothesis_text = text
            # 3. 상황 정보 (Situation Info)
            elif ctx_type == 'situation_info':
                situation_text = text
            # 4. 방책 추천 정보 (CoA Recommendation)
            elif ctx_type == 'coa_recommendation':
                coa_text = text
            # 5. 지식 그래프 문맥, 온톨로지 엔티티
            elif ctx_type == 'graph' or source == 'ontology':
                graph_contexts.append(f"- {text}")
            # 6. 일반 RAG 문서
            else:
                # 메타데이터 정보 추가 (doc_id 또는 title)
                # [Doc undefined] 방지를 위해 가용 정보 최대한 활용
                doc_info = ""
                if metadata.get('title'):
                    doc_info = f"<{metadata['title']}> "
                elif metadata.get('source'):
                    src = str(metadata['source']).split('/')[-1].split('\\')[-1] # 파일명만 추출
                    doc_info = f"[{src}] "
                elif metadata.get('doc_id') and metadata['doc_id'] != -1:
                    doc_info = f"[Doc {metadata['doc_id']}] "
                
                rag_contexts.append(f"[{len(rag_contexts)+1}] {doc_info}{text}")
        
        # 프롬프트 섹션 구성
        context_section = ""
        
        if situation_text:
            context_section += f"\n[현재 상황 정보]\n🚨 현재 사용자가 보고 있는 위협/임무 상황입니다. 답변 시 이 상황을 최우선으로 고려하세요.\n{situation_text}\n"

        if coa_text:
            context_section += f"\n[추천된 방책 정보]\n🛡️ 시스템이 분석하여 추천한 방책 목록입니다. 답변에 적극 활용하세요.\n{coa_text}\n"

        if hypothesis_text:
             context_section += f"\n[전술적 추론 가설]\n⚠️ 모델이 사전에 추론한 전술적 가설입니다. 답변의 논리적 방향을 잡는 데 참고하세요.\n{hypothesis_text}\n"
             
        if graph_contexts:
             context_section += f"\n[지식 그래프 문맥]\n💡 온톨로지에서 추출한 연관 지식입니다. 개념 간의 관계를 설명할 때 활용하세요.\n" + "\n".join(graph_contexts) + "\n"
             
        if agent_result_text:
             context_section += f"\n[Agent 실행 결과 데이터]\n📊 현재 수행된 에이전트의 분석 결과입니다. 가장 최신의 정확한 상황 데이터로 간주하세요.\n{agent_result_text}\n"
             
        if rag_contexts:
             context_section += f"\n[교리 및 참고 문서]\n📚 교범 및 지침 문서입니다. 답변의 구체적인 근거(인용)로 사용하세요.\n" + "\n\n".join(rag_contexts) + "\n"
        
        # 위협 수준 추출 (Agent 결과가 있을 때만)
        threat_level_text = ""
        if agent_result_text:
            # (기존 위협 수준 추출 로직 유지 - 생략 없이 복사)
            threat_level = None
            import re
            severity_match = re.search(r'심각도[:\s]+(\d+(?:\.\d+)?)', agent_result_text)
            if severity_match:
                try:
                    severity = float(severity_match.group(1))
                    threat_level = severity / 100.0 if severity > 1.0 else severity
                except: pass
            
            if threat_level is None:
                threat_level_match = re.search(r'위협수준[:\s]+(\d+)%', agent_result_text)
                if threat_level_match:
                    try:
                        threat_level_pct = int(threat_level_match.group(1))
                        threat_level = threat_level_pct / 100.0
                    except: pass
            
            if threat_level is not None:
                if threat_level >= 0.95:
                    threat_level_text = f"\n\n⚠️ **중요 지시**: 현재 위협수준이 {int(threat_level*100)}%로 매우 높습니다. 반드시 강력한 방어 방책(Main_Defense)을 추천해야 합니다."
                elif threat_level > 0.8:
                    threat_level_text = f"\n\n⚠️ **중요 지시**: 현재 위협수준이 {int(threat_level*100)}%로 높습니다. 강력한 방어 방책(Main_Defense)을 우선 추천하세요."
                elif threat_level > 0.5:
                    threat_level_text = f"\n\n⚠️ **주의**: 현재 위협수준이 {int(threat_level*100)}%로 보통입니다. 적절한 방어 방책(Moderate_Defense)을 추천하세요."
                else:
                    threat_level_text = f"\n\nℹ️ **정보**: 현재 위협수준이 {int(threat_level*100)}%로 낮습니다. 최소 방어 방책(Minimal_Defense)을 고려하세요."

        # 시스템 롤 정의 (상황 정보가 있을 때 명확한 역할 부여)
        system_role = ""
        if situation_text:
            system_role = """
**너의 역할:** 당신은 대한민국 군의 전술 작전 참모입니다. 현재 작전실에서 지휘관을 보좌하고 있으며, 실시간 위협 상황에 대해 분석하고 조언하는 것이 당신의 임무입니다.
**중요:** 지휘관이 "현재 위협은?", "상황은?", "어떤 상황이야?" 같은 질문을 하면, 반드시 [현재 상황 정보]를 바탕으로 구체적이고 명확하게 답변해야 합니다.
"""
        
        # 최종 프롬프트 작성
        prompt = f"""{system_role}질문: {query}

다음은 답변을 구성하는 데 필요한 지식 정보입니다:
{context_section}

**지시사항:**
1. **최우선**: [현재 상황 정보]가 있다면 이를 답변의 핵심으로 사용하세요. "현재 위협은?", "상황은?" 같은 질문에는 상황 정보의 구체적인 내용(위협ID, 위협유형, 발생장소, 위협수준 등)을 명확하게 설명하세요.
2. [추천된 방책 정보]가 있다면 이를 함께 제시하여 지휘관의 의사결정을 지원하세요.
3. [전술적 추론 가설]과 [지식 그래프 문맥]을 통해 질문의 배경과 전술적 의미를 먼저 이해하세요.
4. [Agent 실행 결과 데이터]가 있다면 이를 가장 우선순위가 높은 "현재 상황"으로 간주하세요.
5. [교리 및 참고 문서]를 사용하여 답변의 구체적인 근거를 제시하세요.
6. 답변 작성 시, 어떤 정보가 "온톨로지 추론"에서 왔고 어떤 정보가 "교리 문서"에서 왔는지 구분하여 설명하면 좋습니다.
   예: "현재 상황(위협 ID: THR001)에 대해 온톨로지는 적 접근을 예상하며, 교범 3-2에 따라 지연 작전을 추천합니다."
{threat_level_text}

**답변 형식:**
- **요약**: 질문에 대한 핵심 결론 (현재 상황 요약 포함)
- **지식 기반 분석**: 온톨로지 가설과 그래프 관계를 활용한 상세 설명
- **교리적 근거**: 참고 문서를 인용한 근거 제시 (번호 포함)
- **권고 사항**: 최종 전술적 제언 (방책 추천 기반)

답변:"""
        
        try:
            answer = self.generate(prompt, max_tokens=max_tokens)
            return answer
        except Exception as e:
            safe_print(f"[WARN] Citation generation failed: {e}")
            return self.generate(query, max_tokens=max_tokens)

# 전역 인스턴스
_llm_manager = None

def get_llm_manager():
    """전역 LLM Manager 인스턴스 반환"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

if __name__ == "__main__":
    # 테스트
    print("LLM 모델 로딩 테스트...")
    manager = LLMManager()
    model, tokenizer = manager.load_model()
    if model and tokenizer:
        print("✅ LLM 모델 로딩 성공")
    else:
        print("❌ LLM 모델 로딩 실패")

