# common/error_handler.py
# -*- coding: utf-8 -*-
"""
Error Handler Module
에러 처리 유틸리티 모듈
"""
import traceback
import sys
from typing import Optional, Callable, Any
from common.logger import get_logger

logger = get_logger("ErrorHandler")


class DefenseAIError(Exception):
    """기본 Defense AI 에러 클래스"""
    pass


class DataLoadError(DefenseAIError):
    """데이터 로드 에러"""
    pass


class ModelLoadError(DefenseAIError):
    """모델 로드 에러"""
    pass


class AgentExecutionError(DefenseAIError):
    """Agent 실행 에러"""
    pass


def handle_error(error: Exception, context: Optional[str] = None, raise_again: bool = False):
    """
    에러 처리
    
    Args:
        error: 발생한 에러
        context: 에러 컨텍스트 설명
        raise_again: 다시 raise할지 여부
    """
    error_msg = f"Error occurred"
    if context:
        error_msg += f" in {context}"
    error_msg += f": {str(error)}"
    
    logger.error(error_msg)
    logger.debug(traceback.format_exc())
    
    if raise_again:
        raise


def safe_execute(func: Callable, default_return: Any = None, error_message: Optional[str] = None):
    """
    안전한 함수 실행 (에러 발생 시 기본값 반환)
    
    Args:
        func: 실행할 함수
        default_return: 에러 발생 시 반환할 기본값
        error_message: 에러 메시지 (None이면 기본 메시지)
        
    Returns:
        함수 실행 결과 또는 default_return
    """
    try:
        return func()
    except Exception as e:
        msg = error_message or f"Error in {func.__name__}"
        handle_error(e, msg)
        return default_return

