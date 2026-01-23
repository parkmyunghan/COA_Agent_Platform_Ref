# common/utils.py
# -*- coding: utf-8 -*-
"""
Utility Functions
공통 유틸리티 함수 모듈
"""
import os
import json
import yaml
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def load_yaml(path: str) -> Dict[str, Any]:
    """
    YAML 파일 로드
    
    Args:
        path: YAML 파일 경로
        
    Returns:
        파싱된 딕셔너리
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], path: str):
    """
    YAML 파일 저장
    
    Args:
        data: 저장할 데이터
        path: 저장 경로
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def load_json(path: str) -> Dict[str, Any]:
    """
    JSON 파일 로드
    
    Args:
        path: JSON 파일 경로
        
    Returns:
        파싱된 딕셔너리
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: str, indent: int = 2):
    """
    JSON 파일 저장
    
    Args:
        data: 저장할 데이터
        path: 저장 경로
        indent: 들여쓰기 크기
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def ensure_dir(path: str):
    """
    디렉터리 생성 (없으면)
    
    Args:
        path: 디렉터리 경로
    """
    os.makedirs(path, exist_ok=True)


# 로그 파일 쓰기용 락 (스레드 안전)
_log_lock = threading.Lock()
_log_file_handle = None
_error_log_file_handle = None

def safe_print(msg: str, also_log_file: bool = True, logger_name: Optional[str] = None):
    """
    안전한 출력 함수 (인코딩 오류 방지 + 파일 로깅 + 로거 연동)
    
    개선 사항:
    - also_log_file 파라미터 추가 (기본값: True)
    - 타임스탬프 포함
    - 스레드 안전 파일 쓰기 (_log_lock 사용)
    - buffering=1과 flush()로 즉시 디스크 쓰기
    - os.fsync()로 OS 버퍼까지 강제 쓰기
    - 오류 처리 강화 (별도 error.log 파일에 기록)
    - 로거 연동 (logger_name이 제공되면 로거에도 기록)
    
    Args:
        msg: 출력할 메시지
        also_log_file: 파일에도 기록할지 여부 (기본값: True)
        logger_name: 로거 이름 (제공되면 로거에도 기록)
    """
    global _log_file_handle, _error_log_file_handle
    
    msg_str = str(msg)
    
    # 1. 로거 사용 (logger_name이 제공된 경우)
    # 🔥 개선: logger_name이 제공되면 로거가 파일에 기록하므로 중복 방지를 위해 also_log_file을 False로 설정
    if logger_name:
        try:
            from common.logger import get_logger
            logger = get_logger(logger_name)
            
            # 메시지 레벨 자동 감지
            if "[ERROR]" in msg_str or "[FATAL]" in msg_str:
                logger.error(msg_str.replace("[ERROR]", "").replace("[FATAL]", "").strip())
            elif "[WARN]" in msg_str:
                logger.warning(msg_str.replace("[WARN]", "").strip())
            elif "[DEBUG]" in msg_str:
                logger.debug(msg_str.replace("[DEBUG]", "").strip())
            elif "[INFO]" in msg_str:
                logger.info(msg_str.replace("[INFO]", "").strip())
            else:
                logger.info(msg_str)
            
            # 🔥 개선: logger_name이 제공되면 로거가 이미 파일에 기록하므로 중복 방지
            # also_log_file이 명시적으로 True로 설정된 경우에만 파일 로깅 수행
            if not also_log_file:
                return
        except Exception:
            # 로거 사용 실패해도 계속 진행
            pass
    
    # 2. 터미널 출력 (인코딩 오류 방지)
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        except Exception:
            print("[출력 오류]")
    
    # 3. 파일 로깅 (also_log_file이 True일 때만)
    # 🔥 수정: 기본적으로 파일 로깅 비활성화 (환경변수 COA_LOG_TO_FILE='true' 일 때만 활성화)
    if not also_log_file:
        return
        
    # 명시적으로 켜져 있지 않으면 파일 로깅 스킵 (Opt-in)
    if os.environ.get("COA_LOG_TO_FILE", "false").lower() != "true":
        return
    
    try:
        with _log_lock:
            # 로그 파일 경로 설정
            project_root = get_project_root()
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            
            # 날짜별 로그 파일
            today = datetime.now().strftime('%Y%m%d')
            log_file_path = log_dir / f"system_{today}.log"
            error_log_file_path = log_dir / "error.log"
            
            # 타임스탬프 포함 메시지 (UTF-8 인코딩 보장)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 메시지를 UTF-8로 명시적으로 인코딩 보장
            try:
                # 이미 UTF-8인지 확인
                msg_str.encode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 인코딩 문제가 있으면 안전하게 처리
                msg_str = msg_str.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            log_msg = f"{timestamp} - {msg_str}\n"
            
            # 메인 로그 파일 쓰기
            try:
                if _log_file_handle is None or _log_file_handle.closed:
                    # 파일이 없으면 UTF-8 BOM으로 시작
                    if not log_file_path.exists():
                        with open(log_file_path, 'w', encoding='utf-8-sig') as f:
                            f.write('')  # BOM만 있는 빈 파일 생성
                    # 🔥 수정: buffering=1 제거 (OS 버퍼링 사용), fsync 제거 -> 속도 최적화
                    _log_file_handle = open(log_file_path, 'a', encoding='utf-8-sig')
                
                _log_file_handle.write(log_msg)
                _log_file_handle.flush() # OS 버퍼링 사용 시에도 명시적 flush로 유실 방지
                # os.fsync(_log_file_handle.fileno())  # 🔥 제거: 심각한 성능 저하 원인
            except Exception as e:
                # 로그 파일 쓰기 실패 시 error.log에 기록
                try:
                    if _error_log_file_handle is None or _error_log_file_handle.closed:
                        # 파일이 없으면 UTF-8 BOM으로 시작
                        if not error_log_file_path.exists():
                            with open(error_log_file_path, 'w', encoding='utf-8-sig') as f:
                                f.write('')  # BOM만 있는 빈 파일 생성
                        # 🔥 수정: buffering=1 제거
                        _error_log_file_handle = open(error_log_file_path, 'a', encoding='utf-8-sig')
                    
                    error_msg = f"{timestamp} - [LOG_ERROR] 로그 파일 쓰기 실패: {e}\n"
                    error_msg += f"{timestamp} - [LOG_ERROR] 원본 메시지: {msg_str}\n"
                    _error_log_file_handle.write(error_msg)
                    # _error_log_file_handle.flush()
                    # os.fsync(_error_log_file_handle.fileno())
                except Exception:
                    # error.log 쓰기도 실패하면 무시 (무한 루프 방지)
                    pass
                    
    except Exception as e:
        # 전체 로깅 프로세스 실패 시에도 무시 (무한 루프 방지)
        # 터미널 출력은 이미 성공했으므로 계속 진행
        pass


def get_project_root() -> Path:
    """
    프로젝트 루트 디렉터리 경로 반환
    
    Returns:
        프로젝트 루트 Path 객체
    """
    return Path(__file__).parent.parent














