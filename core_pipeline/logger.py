# core_pipeline/logger.py
# -*- coding: utf-8 -*-
"""
성능 로깅 및 모니터링
단계별 실행 시간, 토큰 수, GPU 메모리 사용률 기록
"""
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# UTF-8 인코딩 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class PerformanceLogger:
    """성능 로깅 클래스"""
    
    def __init__(self):
        self.logs: List[Dict] = []
        self.current_step: Optional[str] = None
        self.start_time: Optional[float] = None
        self.step_times: Dict[str, float] = {}
        
    def start_step(self, step_name: str):
        """단계 시작"""
        if self.current_step:
            self.end_step()
        
        self.current_step = step_name
        self.start_time = time.time()
    
    def end_step(self, tokens: int = None, gpu_memory_mb: float = None):
        """단계 종료 및 로그 기록"""
        if not self.current_step or not self.start_time:
            return
        
        elapsed_ms = (time.time() - self.start_time) * 1000
        
        log_entry = {
            "step": self.current_step,
            "time_ms": elapsed_ms,
            "tokens": tokens,
            "gpu_memory_mb": gpu_memory_mb,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logs.append(log_entry)
        self.step_times[self.current_step] = elapsed_ms
        
        self.current_step = None
        self.start_time = None
        
        return log_entry
    
    def get_gpu_memory(self) -> Optional[float]:
        """GPU 메모리 사용량 조회 (MB)"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / (1024 ** 2)  # MB
        except ImportError:
            pass
        return None
    
    def log_step(self, step_name: str, tokens: int = None, auto_gpu: bool = True):
        """컨텍스트 매니저로 사용 가능한 로그 함수"""
        class StepLogger:
            def __init__(self, logger, step_name, tokens, auto_gpu):
                self.logger = logger
                self.step_name = step_name
                self.tokens = tokens
                self.auto_gpu = auto_gpu
            
            def __enter__(self):
                self.logger.start_step(self.step_name)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                gpu_memory = None
                if self.auto_gpu:
                    gpu_memory = self.logger.get_gpu_memory()
                self.logger.end_step(tokens=self.tokens, gpu_memory_mb=gpu_memory)
                return False
        
        return StepLogger(self, step_name, tokens, auto_gpu)
    
    def get_summary(self) -> Dict:
        """성능 요약 반환"""
        if not self.logs:
            return {}
        
        total_time = sum(log.get("time_ms", 0) for log in self.logs)
        total_tokens = sum(log.get("tokens", 0) or 0 for log in self.logs)
        avg_gpu_memory = None
        
        gpu_values = [log.get("gpu_memory_mb") for log in self.logs if log.get("gpu_memory_mb")]
        if gpu_values:
            avg_gpu_memory = sum(gpu_values) / len(gpu_values)
        
        return {
            "total_time_ms": total_time,
            "total_tokens": total_tokens,
            "avg_gpu_memory_mb": avg_gpu_memory,
            "step_count": len(self.logs)
        }
    
    def get_recent_logs(self, n: int = 10) -> List[Dict]:
        """최근 n개 로그 반환"""
        return self.logs[-n:] if self.logs else []
    
    def clear(self):
        """로그 초기화"""
        self.logs = []
        self.step_times = {}
        self.current_step = None
        self.start_time = None


# 전역 인스턴스
_performance_logger = None

def get_performance_logger() -> PerformanceLogger:
    """전역 PerformanceLogger 인스턴스 반환"""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger














