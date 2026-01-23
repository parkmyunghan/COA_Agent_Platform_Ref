# core_pipeline/data_loaders/__init__.py
# -*- coding: utf-8 -*-
"""
Data Loaders Module
표준화된 데이터 로딩 계층

기본적으로 GenericDataLoader를 사용합니다 (테이블정의서 기반 자동 검증).
특수 로직이 필요한 경우에만 특수 로더를 사용합니다.
"""

from .base_loader import BaseDataLoader, GenericDataLoader
# 특수 로더 (실제 특수 로직이 필요한 경우만)
from .axis_loader import AxisLoader
from .coa_template_loader import COATemplateLoader

__all__ = [
    'BaseDataLoader',
    'GenericDataLoader',  # 기본 로더 (권장) - 모든 테이블에 자동 적용
    # 특수 로더 (선택적)
    'AxisLoader',  # 문자열 파싱 로직 포함
    'COATemplateLoader',  # 실제 사용 중 (coa_generator.py)
]

