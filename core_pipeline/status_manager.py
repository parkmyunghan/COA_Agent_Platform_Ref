# core_pipeline/status_manager.py
# -*- coding: utf-8 -*-
"""
Status Manager
전장 엔티티(부대, 위협 등)의 실시간 상태(좌표, 잔여량 등) 관리 전담 모듈
지식(Ontology)과 상태(Status)를 분리하여 처리
"""
import pandas as pd
from typing import Dict, Optional, Any, List
from pathlib import Path

class StatusManager:
    """엔티티의 실시간 상태 정보를 관리하는 클래스"""
    
    # 상태 정보를 포함하는 핵심 테이블 정의
    STATUS_TABLES = [
        "위협상황",
        "아군부대현황",
        "적군부대현황"
    ]
    
    # ID 컬럼 후보군
    ID_COLUMNS = ['ID', '위협ID', '부대ID', 'UNIT_ID', 'THREAT_ID', 'SITUATION_ID', 
                  '아군부대ID', '적군부대ID', '부대명', '위협명']
    
    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 인스턴스 (데이터 로드용)
        """
        self.data_manager = data_manager
        self._status_cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        
    def initialize(self, force: bool = False):
        """상태 정보 캐시 초기화"""
        if self._initialized and not force:
            return
            
        self._status_cache = {}
        for table_name in self.STATUS_TABLES:
            try:
                df = self.data_manager.load_table(table_name)
                if df is not None and not df.empty:
                    self._update_cache_from_df(table_name, df)
            except Exception as e:
                print(f"[WARN] StatusManager: Failed to load status table {table_name}: {e}")
                
        self._initialized = True
        print(f"[INFO] StatusManager initialized with {len(self._status_cache)} entities.")

    def _update_cache_from_df(self, table_name: str, df: pd.DataFrame):
        """DataFrame 데이터를 기반으로 내부 상태 캐시 업데이트"""
        # ID 컬럼 찾기 (테이블별 우선순위)
        id_col = None
        if table_name == "아군부대현황":
            id_col = next((c for c in df.columns if c in ['아군부대ID', '부대명']), None)
        elif table_name == "적군부대현황":
            id_col = next((c for c in df.columns if c in ['적군부대ID', '부대명']), None)
        elif table_name == "위협상황":
            id_col = next((c for c in df.columns if c in ['위협ID', '위협명']), None)
        
        # 일반적인 ID 컬럼 찾기
        if not id_col:
            id_col = next((c for c in df.columns if c.upper() in [col.upper() for col in self.ID_COLUMNS]), None)
        
        if not id_col:
            # 첫 번째 컬럼을 ID로 간주 (폴백)
            id_col = df.columns[0]
        
        # 부대명도 인덱스로 추가 (부대명으로도 조회 가능하도록)
        name_col = None
        if table_name in ["아군부대현황", "적군부대현황"]:
            name_col = next((c for c in df.columns if c == '부대명'), None)
        elif table_name == "위협상황":
            name_col = next((c for c in df.columns if c == '위협명'), None)
            
        for _, row in df.iterrows():
            entity_id = str(row[id_col]).strip()
            if not entity_id or entity_id == 'nan':
                continue
                
            # 기존 정보와 병합 (여러 테이블에 존재할 경우 대비)
            if entity_id not in self._status_cache:
                self._status_cache[entity_id] = {}
            
            # 행 데이터를 딕셔너리로 변환하여 업데이트
            row_dict = row.to_dict()
            self._status_cache[entity_id].update(row_dict)
            self._status_cache[entity_id]['_source_table'] = table_name
            
            # [FIX] 부대명도 인덱스로 추가 (부대명으로도 조회 가능하도록)
            if name_col and name_col != id_col:
                name_value = str(row[name_col]).strip()
                if name_value and name_value != 'nan':
                    if name_value not in self._status_cache:
                        self._status_cache[name_value] = {}
                    self._status_cache[name_value].update(row_dict)
                    self._status_cache[name_value]['_source_table'] = table_name

    def invalidate_cache(self, table_name: Optional[str] = None):
        """캐시 무효화 및 재로드"""
        if table_name and table_name in self.STATUS_TABLES:
            # 특정 테이블만 업데이트
            try:
                df = self.data_manager.load_table(table_name)
                if df is not None:
                    # 해당 테이블 출처인 기존 캐시 항목들 정리 (선택사항, 보통은 덮어씀)
                    self._update_cache_from_df(table_name, df)
                    print(f"[INFO] StatusManager: Updated status from {table_name}")
            except Exception as e:
                print(f"[WARN] StatusManager: Failed to refresh {table_name}: {e}")
        else:
            # 전체 초기화
            self.initialize(force=True)

    def get_entity_status(self, entity_id: str) -> Dict[str, Any]:
        """특정 엔티티의 실시간 상태 정보 반환"""
        if not self._initialized:
            self.initialize()
        return self._status_cache.get(entity_id, {})

    def get_coordinates(self, entity_id: str) -> Optional[tuple]:
        """
        특정 엔티티의 실시간 좌표(위경도) 조회
        우선순위: 실시간 상태 테이블의 명시적 좌표 > 통합 좌표정보 문자열
        """
        status = self.get_entity_status(entity_id)
        if not status:
            return None
            
        # 1. 명시적 위도/경도 필드 확인
        lat_fields = ['위도', 'latitude', 'lat', 'LAT', 'hasLatitude']
        lng_fields = ['경도', 'longitude', 'lng', 'LNG', 'hasLongitude']
        
        lat_val = next((status.get(f) for f in lat_fields if status.get(f) is not None), None)
        lng_val = next((status.get(f) for f in lng_fields if status.get(f) is not None), None)
        
        if lat_val is not None and lng_val is not None:
            try:
                return float(lat_val), float(lng_val)
            except (ValueError, TypeError):
                pass
                
        # 2. 통합 '좌표정보' 문자열 확인 (예: "127.5, 37.9")
        coord_info = status.get('좌표정보') or status.get('coordinates')
        if coord_info and isinstance(coord_info, str) and ',' in coord_info:
            try:
                parts = [p.strip() for p in coord_info.split(',')]
                if len(parts) >= 2:
                    # 엑셀 관례상 [경도, 위도] 순서가 많음
                    lng, lat = float(parts[0]), float(parts[1])
                    return lat, lng
            except (ValueError, IndexError):
                pass
                
        return None

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """전체 상태 정보 반환"""
        if not self._initialized:
            self.initialize()
        return self._status_cache
