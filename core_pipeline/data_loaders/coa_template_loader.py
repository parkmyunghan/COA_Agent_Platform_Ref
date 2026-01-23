# core_pipeline/data_loaders/coa_template_loader.py
# -*- coding: utf-8 -*-
"""
COA Template Data Loader
방책템플릿 로더
"""
from typing import Dict, Optional, List
import pandas as pd
from .base_loader import GenericDataLoader


class COATemplateLoader(GenericDataLoader):
    """방책템플릿 로더 (특수 메서드: get_templates_by_strategy 등)
    
    GenericDataLoader를 상속하여 기본 검증 로직을 재사용합니다.
    위협수준조건에 대해서만 특수 검증(부분 매칭)을 추가합니다.
    """
    
    def _validate_data(self, df: pd.DataFrame) -> None:
        """방책템플릿 데이터 검증 (기본 검증 + 위협수준조건 특수 검증)"""
        # 위협수준조건을 제외한 스키마로 기본 검증 수행
        schema = self.load_schema()
        
        # 위협수준조건을 임시로 제거한 스키마 복사본 생성
        schema_without_threat = schema.copy()
        if '위협수준조건' in schema_without_threat.get('valid_values', {}):
            schema_without_threat['valid_values'] = {
                k: v for k, v in schema_without_threat['valid_values'].items() 
                if k != '위협수준조건'
            }
        
        # 임시로 스키마를 교체하여 부모 클래스 검증 호출
        original_schema = self._schema
        self._schema = schema_without_threat
        
        try:
            # 부모 클래스의 기본 검증 수행 (위협수준조건 제외)
            super()._validate_data(df)
        finally:
            # 원래 스키마 복원
            self._schema = original_schema
        
        # 위협수준조건 특수 검증 (부분 매칭 - 수식 포함 가능)
        if '위협수준조건' in df.columns:
            valid_levels = self.get_valid_values('위협수준조건')
            if valid_levels:
                # 위협수준조건은 수식이 포함될 수 있으므로 부분 매칭만 수행
                invalid = df[df['위협수준조건'].notna() & 
                            ~df['위협수준조건'].astype(str).str.contains('|'.join(valid_levels), case=False, na=False) &
                            ~df['위협수준조건'].astype(str).str.contains('>|<|>=|<=|=', na=False)]
                if not invalid.empty:
                    print(f"[WARN] 일부 위협수준조건이 표준 형식이 아닙니다: {invalid['위협수준조건'].unique().tolist()}")
    
    def get_active_templates(self) -> pd.DataFrame:
        """활성화된 템플릿만 반환"""
        df = self.load()
        if '활성여부' in df.columns:
            return df[df['활성여부'].isin(['Y', 'YES', 'y'])]
        return df
    
    def get_templates_by_strategy(self, strategy_type: str) -> pd.DataFrame:
        """전략유형별 템플릿 반환"""
        df = self.get_active_templates()
        if '전략유형' in df.columns:
            return df[df['전략유형'] == strategy_type]
        return pd.DataFrame()
    
    def get_templates_by_threat_level(self, threat_level: str) -> pd.DataFrame:
        """위협수준별 템플릿 반환"""
        df = self.get_active_templates()
        if '위협수준조건' in df.columns:
            # 위협수준조건에 해당 레벨이 포함된 템플릿 반환
            return df[df['위협수준조건'].astype(str).str.contains(threat_level, case=False, na=False)]
        return pd.DataFrame()
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """템플릿ID로 템플릿 조회"""
        df = self.load()
        
        # PK 컬럼을 테이블정의서에서 가져오기
        pk_col = self._get_pk_column()
        if not pk_col or pk_col not in df.columns:
            return None
        
        template = df[df[pk_col] == template_id]
        if template.empty:
            return None
        
        return template.iloc[0].to_dict()

