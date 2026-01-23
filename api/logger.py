import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# 디버깅 모드 체크 함수 (common.logger에서 가져오기)
def is_debug_mode() -> bool:
    """디버깅 모드 여부 확인"""
    try:
        from common.logger import is_debug_mode as _is_debug_mode
        return _is_debug_mode()
    except ImportError:
        # common.logger를 사용할 수 없는 경우 설정 파일 직접 확인
        try:
            import yaml
            config_path = Path(__file__).parent.parent / "config" / "global.yaml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    return config.get("debug_mode", False)
        except Exception:
            pass
        return False

def debug_log(logger: logging.Logger, message: str, *args, **kwargs):
    """디버깅 모드에서만 로그 기록 (INFO 레벨)"""
    if is_debug_mode():
        logger.info(message, *args, **kwargs)

def debug_log_debug(logger: logging.Logger, message: str, *args, **kwargs):
    """디버깅 모드에서만 로그 기록 (DEBUG 레벨)"""
    if is_debug_mode():
        logger.debug(message, *args, **kwargs)

def setup_logging(log_path: str = "./logs", log_level: str = "INFO"):
    """
    중앙 집중식 로깅 설정.
    콘솔과 파일 모두에 로그를 기록합니다.
    """
    # 로그 디렉토리 생성
    log_dir = Path(log_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 로그 파일명 (날짜별)
    log_filename = f"platform_{datetime.now().strftime('%Y%m%d')}.log"
    log_file = log_dir / log_filename
    
    # 로깅 포맷 설정
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 루트 로거 가져오기
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # 기존 핸들러 제거 (중복 방지)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (RotatingFileHandler 적용)
    try:
        # 10MB 단위로 회전, 최대 10개 백업 파일 유지
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024, # 10MB
            backupCount=10, 
            encoding='utf-8'
        )
        
        # Fresh Start: 서버 시작 시 기존 로그가 있다면 즉시 회전하여 새 파일 생성
        if log_file.exists() and log_file.stat().st_size > 0:
            file_handler.doRollover()
            
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        logging.info(f"Logging initialized. File: {log_file}")
    except Exception as e:
        logging.error(f"Failed to initialize file logging: {e}")

def get_logger(name: str):
    """지정된 이름의 로거 반환"""
    return logging.getLogger(name)
