# core_pipeline/coa_engine/__init__.py
# -*- coding: utf-8 -*-
"""
COA Engine Module
COA 후보 생성 및 평가 엔진

**아키텍처 원칙**:
- 핵심 로직(규칙 기반 COA 생성/평가)은 순수 Python으로 구현
- LLM/RAG/온톨로지는 보조 레이어로만 활용:
  1) SITREP → 위협상황 변환
  2) COA 설명문 생성
  3) 교범/지침 참고 자료 검색
"""

from .coa_models import COA, AxisAssignment, UnitAssignment
from .coa_generator import COAGenerator
from .coa_evaluator import COAEvaluator, COAEvaluationResult
from .coa_generator_enhanced import EnhancedCOAGenerator
from .coa_evaluator_enhanced import EnhancedCOAEvaluator
from .llm_services import (
    SITREPParser,
    COAExplanationGenerator,
    DoctrineSearchService
)
from .coa_llm_adapter import COALLMAdapter
from .doctrine_reference_service import DoctrineReferenceService
from .doctrine_explanation_generator import DoctrineBasedExplanationGenerator

__all__ = [
    'COA',
    'AxisAssignment',
    'UnitAssignment',
    'COAGenerator',
    'COAEvaluator',
    'COAEvaluationResult',
    'EnhancedCOAGenerator',
    'EnhancedCOAEvaluator',
    'SITREPParser',
    'COAExplanationGenerator',
    'DoctrineSearchService',
    'COALLMAdapter',
    'DoctrineReferenceService',
    'DoctrineBasedExplanationGenerator',
]

