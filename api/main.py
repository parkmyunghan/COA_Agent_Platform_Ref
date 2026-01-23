# Force reload for rule update
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

from api.routers import system, data, threat, coa, chat, report, ontology, data_management, ontology_studio, rag, agent
from api.dependencies import get_global_state

# Import routers from their modules
# (Assuming routers/__init__.py exposes them or we import directly)

def prompt_debug_mode():
    """
    실행 시 디버깅 모드 선택을 위한 대화형 프롬프트
    
    Returns:
        bool: 디버깅 모드 활성화 여부
    """
    # 환경 변수로 강제 설정된 경우 우선 사용
    env_debug = os.environ.get("DEBUG_MODE", "").upper()
    if env_debug == "TRUE" or env_debug == "1" or env_debug == "Y":
        return True
    elif env_debug == "FALSE" or env_debug == "0" or env_debug == "N":
        return False
    
    # 설정 파일에서 기본값 로드
    from api.dependencies import load_global_config
    config = load_global_config()
    default_debug_mode = config.get("debug_mode", False)
    
    # 비대화형 환경(예: uvicorn 직접 실행, Docker 등)에서는 설정 파일 값 사용
    if not sys.stdin.isatty():
        return default_debug_mode
    
    # 대화형 프롬프트
    print("\n" + "=" * 60)
    print("디버깅 모드 선택")
    print("=" * 60)
    print(f"현재 설정 파일 기본값: {'디버깅 모드' if default_debug_mode else '운영 모드'}")
    print("\n디버깅 모드를 활성화하시겠습니까?")
    print("  - 디버깅 모드: 상세한 로그 기록 (성능에 영향 있음)")
    print("  - 운영 모드: 기본 로그만 기록 (성능 최적화)")
    print()
    
    while True:
        try:
            response = input("디버깅 모드 활성화? [Y/N] (기본값: " + ("Y" if default_debug_mode else "N") + "): ").strip().upper()
            
            # 엔터만 입력한 경우 기본값 사용
            if not response:
                return default_debug_mode
            
            if response in ['Y', 'YES']:
                return True
            elif response in ['N', 'NO']:
                return False
            else:
                print("잘못된 입력입니다. Y 또는 N을 입력해주세요.")
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C 또는 EOF 입력 시 기본값 사용
            print(f"\n기본값 사용: {'디버깅 모드' if default_debug_mode else '운영 모드'}")
            return default_debug_mode

# 모듈 로드 시 디버깅 모드 선택 (앱 생성 전)
_DEBUG_MODE = None

def get_debug_mode():
    """디버깅 모드 여부 반환 (한 번만 프롬프트 표시)"""
    global _DEBUG_MODE
    if _DEBUG_MODE is None:
        _DEBUG_MODE = prompt_debug_mode()
    return _DEBUG_MODE

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Logging initialization
    import logging
    from api.dependencies import load_global_config
    from api.logger import setup_logging
    from common.logger import set_debug_mode
    config = load_global_config()
    
    # 디버깅 모드 설정 (대화형 입력 또는 설정 파일)
    debug_mode = get_debug_mode()
    set_debug_mode(debug_mode)
    
    setup_logging(
        log_path=config.get("log_path", "./logs"),
        log_level=config.get("log_level", "INFO")
    )
    
    if debug_mode:
        logging.info(f"[시스템] 디버깅 모드 활성화됨 - 상세 로그가 기록됩니다.")
        print(">> [시스템] 디버깅 모드 활성화됨 - 상세 로그가 기록됩니다.")
    else:
        logging.info(f"[시스템] 운영 모드 - 기본 로그만 기록됩니다.")
        print(">> [시스템] 운영 모드 - 기본 로그만 기록됩니다.")
    
    # Startup
    print(">> [API] Starting up... Initializing Global State.")
    state = get_global_state()
    # Eager initialization
    state.initialize()
    
    # Inject orchestrator into routers
    orchestrator = state.get_orchestrator()
    ontology.set_orchestrator(orchestrator)
    data_management.set_orchestrator(orchestrator)
    ontology_studio.set_orchestrator(orchestrator)
    rag.set_orchestrator(orchestrator)
    
    yield
    # Shutdown
    print(">> [API] Shutting down...")

app = FastAPI(
    title="COA Agent Platform API",
    version="1.0.0",
    description="Backend API for COA Agent Platform (React Refactoring)",
    lifespan=lifespan
)

# CORS Config
origins = [
    "http://localhost:5173", # Vite Default
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(system.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(threat.router, prefix="/api/v1")
app.include_router(coa.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
app.include_router(agent.router)

# Phase 3: Knowledge & Data Management
app.include_router(ontology.router)
app.include_router(data_management.router)

# Phase 4: Advanced Ontology Tools
app.include_router(ontology_studio.router)
app.include_router(rag.router)

if __name__ == "__main__":
    import uvicorn
    # 디버깅 모드 선택 (대화형 프롬프트)
    debug_mode = get_debug_mode()
    print(f"\n>> 서버 시작 중... (디버깅 모드: {'활성화' if debug_mode else '비활성화'})")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
