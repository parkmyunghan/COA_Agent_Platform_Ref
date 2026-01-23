# agents/base_agent.py
# -*- coding: utf-8 -*-
"""
Base Agent
모든 Agent의 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseAgent(ABC):
    """Base Agent 클래스"""
    
    def __init__(self, core, config: Optional[Dict] = None):
        """
        Args:
            core: CorePipeline 인스턴스
            config: Agent별 설정 딕셔너리 (선택적)
        """
        self.core = core
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def execute_reasoning(self, **kwargs) -> Dict:
        """
        추론 실행 (각 Agent에서 구현해야 함)
        
        Args:
            **kwargs: Agent별 추가 인자
            
        Returns:
            실행 결과 딕셔너리
        """
        raise NotImplementedError("Subclasses must implement execute_reasoning method")
    
    def get_summary(self, result: Dict) -> str:
        """
        결과 요약 생성
        
        Args:
            result: 실행 결과 딕셔너리
            
        Returns:
            요약 문자열
        """
        if "summary" in result:
            return result["summary"]
        
        # LLM을 사용하여 요약 생성
        if self.core.llm_manager.is_available():
            try:
                items_str = "\n".join([f"{k}: {v}" for k, v in result.items() if k != "summary"])
                prompt = f"다음 결과를 요약하세요:\n{items_str}\n---\n요약:"
                summary = self.core.llm_manager.generate(prompt, max_tokens=128)
                return summary
            except Exception as e:
                print(f"[WARN] Failed to generate summary with LLM: {e}")
        
        # 기본 요약
        return str(result)[:200]














