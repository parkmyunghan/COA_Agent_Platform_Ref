# core_pipeline/data_loaders/axis_loader.py
# -*- coding: utf-8 -*-
"""
Axis Data Loader
전장축선 로더
"""
from typing import Dict, Optional, List
import pandas as pd
from .base_loader import GenericDataLoader


class AxisLoader(GenericDataLoader):
    """전장축선 로더 (특수 메서드: get_related_terrain_cells)
    
    GenericDataLoader를 상속하여 기본 검증 로직을 재사용합니다.
    _validate_data()는 부모 클래스의 것을 사용하므로 중복 코드가 없습니다.
    """
    
    def get_related_terrain_cells(self, axis_id: str) -> List[str]:
        """특정 축선과 연관된 지형셀 ID 목록 반환 (특수 메서드)"""
        df = self.load()
        if '관련지형셀리스트' not in df.columns:
            return []
        
        # PK 컬럼을 테이블정의서에서 가져오기
        pk_col = self._get_pk_column()
        if not pk_col or pk_col not in df.columns:
            return []
        
        axis_row = df[df[pk_col] == axis_id]
        if axis_row.empty:
            return []
        
        cell_list_str = axis_row.iloc[0]['관련지형셀리스트']
        if pd.isna(cell_list_str):
            return []
        
        # 쉼표로 구분된 ID 목록 파싱
        cell_ids = [cell_id.strip() for cell_id in str(cell_list_str).split(',')]
        return [cell_id for cell_id in cell_ids if cell_id]
    
    def get_high_priority_axes(self, min_importance: int = 3) -> pd.DataFrame:
        """고중요도 축선 조회"""
        df = self.load()
        if '중요도' in df.columns:
            return df[df['중요도'] <= min_importance].copy()
        return pd.DataFrame()

