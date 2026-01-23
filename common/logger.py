# common/logger.py
# -*- coding: utf-8 -*-
"""
Logger Module
로깅 유틸리티 모듈
"""
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# 전역 디버깅 모드 플래그 (설정 파일에서 로드)
_DEBUG_MODE = None

def is_debug_mode() -> bool:
    """
    디버깅 모드 여부 확인
    
    Returns:
        디버깅 모드가 활성화되어 있으면 True
    """
    global _DEBUG_MODE
    if _DEBUG_MODE is None:
        # 설정 파일에서 로드 시도
        try:
            import yaml
            config_path = Path(__file__).parent.parent / "config" / "global.yaml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    _DEBUG_MODE = config.get("debug_mode", False)
            else:
                _DEBUG_MODE = False
        except Exception:
            _DEBUG_MODE = False
    return _DEBUG_MODE

def set_debug_mode(enabled: bool):
    """
    디버깅 모드 설정 (런타임 변경 가능)
    
    Args:
        enabled: 디버깅 모드 활성화 여부
    """
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def setup_logger(name: str = "DefenseAI", log_level: str = "INFO", log_path: Optional[str] = None) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_path: 로그 파일 경로 (None이면 콘솔만)
        
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 기존 핸들러 제거
    logger.handlers = []
    
    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택적)
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "DefenseAI") -> logging.Logger:
    """
    로거 가져오기 (기존 로거가 있으면 반환, 없으면 새로 생성)
    
    Args:
        name: 로거 이름
        
    Returns:
        로거 인스턴스
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger

def debug_log(logger: logging.Logger, message: str, *args, **kwargs):
    """
    디버깅 모드에서만 로그 기록 (INFO 레벨)
    
    Args:
        logger: 로거 인스턴스
        message: 로그 메시지
        *args, **kwargs: logger.info()에 전달할 추가 인자
    """
    if is_debug_mode():
        logger.info(message, *args, **kwargs)

def debug_log_debug(logger: logging.Logger, message: str, *args, **kwargs):
    """
    디버깅 모드에서만 로그 기록 (DEBUG 레벨)
    
    Args:
        logger: 로거 인스턴스
        message: 로그 메시지
        *args, **kwargs: logger.debug()에 전달할 추가 인자
    """
    if is_debug_mode():
        logger.debug(message, *args, **kwargs)

