# core_pipeline/data_manager.py
# -*- coding: utf-8 -*-
"""
Data Manager
데이터 로딩 및 관리 모듈 (로더 기반 구조로 개선)
"""
import os
import pandas as pd
from typing import Dict, Optional
from pathlib import Path

# 로더 모듈 임포트 (선택적, 없어도 동작)
try:
    from .data_loaders.base_loader import BaseDataLoader, GenericDataLoader
    # 특수 로더는 최소화 (실제 특수 로직이 필요한 경우만)
    from .data_loaders.axis_loader import AxisLoader
    from .data_loaders.coa_template_loader import COATemplateLoader
    LOADERS_AVAILABLE = True
except ImportError as e:
    LOADERS_AVAILABLE = False
    BaseDataLoader = None
    GenericDataLoader = None
    AxisLoader = None
    COATemplateLoader = None


class DataManager:
    """데이터 관리자 클래스 (로더 기반 구조 지원)"""
    
    # 특수 로더 매핑 (최소화 - 실제 특수 로직이 필요한 경우만)
    # 기본적으로는 GenericDataLoader 사용 (테이블정의서 기반 자동 검증)
    OPTIONAL_LOADER_MAP = {
        'COA_Library': 'COATemplateLoader',  # 방책템플릿이 COA_Library로 통합됨
        '전장축선': 'AxisLoader',  # 문자열 파싱 로직 포함 (get_related_terrain_cells)
    }
    
    def __init__(self, config: Dict):
        """
        Args:
            config: 설정 딕셔너리 (data_paths 포함)
        """
        self.config = config
        self.data_paths = config.get("data_paths", {})
        self._loaders: Dict[str, BaseDataLoader] = {}
        self._use_loaders = LOADERS_AVAILABLE and config.get("use_data_loaders", True)
    
    def get_loader(self, table_name: str) -> Optional[BaseDataLoader]:
        """
        특정 테이블의 로더 인스턴스 반환 (동적 선택)
        
        Args:
            table_name: 테이블명
            
        Returns:
            로더 인스턴스 또는 None
        """
        if not self._use_loaders:
            return None
        
        if table_name not in self._loaders:
            # 1. 특수 로더가 있으면 사용 (선택적)
            loader_class_name = self.OPTIONAL_LOADER_MAP.get(table_name)
            if loader_class_name:
                loader_class = self._get_loader_class(loader_class_name)
                if loader_class:
                    path = self.data_paths.get(table_name)
                    if not path:
                        # data_lake에서 경로 찾기
                        path = self._find_data_lake_path(table_name)
                    if path:
                        try:
                            self._loaders[table_name] = loader_class(path, self.config)
                            return self._loaders[table_name]
                        except Exception as e:
                            print(f"[WARN] Failed to create special loader for {table_name}, falling back to GenericDataLoader: {e}")
            
            # 2. 기본은 GenericDataLoader 사용 (완전 자동화)
            path = self.data_paths.get(table_name)
            if not path:
                path = self._find_data_lake_path(table_name)
            
            if path and GenericDataLoader:
                try:
                    self._loaders[table_name] = GenericDataLoader(path, self.config)
                    return self._loaders[table_name]
                except Exception as e:
                    print(f"[WARN] Failed to create generic loader for {table_name}: {e}")
        
        return self._loaders.get(table_name)
    
    def _get_loader_class(self, loader_class_name: str):
        """특수 로더 클래스 반환 (최소화된 매핑)"""
        loader_class_map = {
            'AxisLoader': AxisLoader,
            'COATemplateLoader': COATemplateLoader,
        }
        return loader_class_map.get(loader_class_name)
    
    def _find_data_lake_path(self, table_name: str) -> Optional[str]:
        """data_lake 폴더에서 파일 경로 찾기"""
        data_lake_path = self.config.get("data_lake_path", "./data_lake")
        base_dir = Path(__file__).parent.parent
        data_lake_dir = base_dir / data_lake_path
        
        if not data_lake_dir.exists():
            return None
        
        # 파일명으로 찾기
        for ext in ['.xlsx', '.xls']:
            file_path = data_lake_dir / f"{table_name}{ext}"
            if file_path.exists():
                return str(file_path.relative_to(base_dir))
        
        return None
    
    def _find_in_data_lake(self, table_name: str) -> Optional[str]:
        """data_lake 폴더에서 파일 경로 찾기"""
        data_lake_path = self.config.get("data_lake_path", "./data_lake")
        base_dir = Path(__file__).parent.parent
        data_lake_dir = base_dir / data_lake_path
        
        if not data_lake_dir.exists():
            # config에 경로가 상대경로로 잡혀있을 수 있음
            if not Path(data_lake_path).is_absolute():
                 data_lake_dir = Path(os.getcwd()) / data_lake_path
            
            if not data_lake_dir.exists():
                return None
        
        # 파일명으로 찾기
        for ext in ['.xlsx', '.xls']:
            file_path = data_lake_dir / f"{table_name}{ext}"
            if file_path.exists():
                return str(file_path)
        
        return None

    def invalidate_table_cache(self, table_name: str):
        """특정 테이블의 캐시 무효화"""
        loader = self.get_loader(table_name)
        if loader and hasattr(loader, 'invalidate_cache'):
            loader.invalidate_cache()
    
    def invalidate_all_cache(self):
        """모든 테이블의 캐시 무효화"""
        for table_name in list(self._loaders.keys()):
            self.invalidate_table_cache(table_name)
    
    def load_table(self, name: str) -> pd.DataFrame:
        """
        테이블 데이터 로드 (로더 우선 사용, 하위 호환성 유지)
        
        Args:
            name: 데이터 테이블 이름
            
        Returns:
            pandas DataFrame
            
        Raises:
            FileNotFoundError: 파일이 없을 경우
        """
        # 로더 사용 시도
        loader = self.get_loader(name)
        if loader:
            try:
                return loader.load()
            except Exception as e:
                print(f"[WARN] Loader failed for {name}, falling back to legacy method: {e}")
        
        # 하위 호환성: 레거시 방식
        return self._load_table_legacy(name)
    
    def _load_table_legacy(self, name: str) -> pd.DataFrame:
        """
        레거시 로딩 방식 (하위 호환성)
        
        Args:
            name: 데이터 테이블 이름
            
        Returns:
            pandas DataFrame
            
        Raises:
            FileNotFoundError: 파일이 없을 경우
        """
        path = self.data_paths.get(name)
        if not path:
            # Config에 없으면 data_lake에서 검색 시도
            found_path = self._find_in_data_lake(name)
            if found_path:
                path = found_path
                print(f"[INFO] Found {name} in data_lake: {path}")
            else:
                raise FileNotFoundError(f"Data path for {name} not found in config and data_lake")
        
        # Path 객체로 변환
        if isinstance(path, Path):
            path_obj = path
        else:
            path_obj = Path(path)
        
        # 상대 경로를 절대 경로로 변환
        if not path_obj.is_absolute():
            base_dir = Path(__file__).parent.parent
            path_obj = base_dir / path_obj
        
        path_str = str(path_obj)
        
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"Data file for {name} not found: {path_str}")
        
        # 파일 확장자에 따라 로드
        if path_str.endswith(".xlsx") or path_str.endswith(".xls"):
            return pd.read_excel(path_str)
        elif path_str.endswith(".csv"):
            return pd.read_csv(path_str)
        else:
            # 기본적으로 CSV로 시도
            return pd.read_csv(path_str)
    
    def load_all(self) -> Dict[str, pd.DataFrame]:
        """
        모든 데이터 테이블 로드
        
        Returns:
            {테이블명: DataFrame} 딕셔너리
        """
        result = {}
        failed_tables = []
        
        for name in self.data_paths:
            try:
                df = self.load_table(name)
                if df is not None and not df.empty:
                    result[name] = df
                    print(f"[INFO] 테이블 '{name}' 로드 성공: {len(df)}행")
                else:
                    failed_tables.append(f"{name} (빈 DataFrame)")
                    print(f"[WARN] 테이블 '{name}'가 비어있습니다.")
            except FileNotFoundError as e:
                failed_tables.append(f"{name} (파일 없음)")
                print(f"[WARN] Failed to load {name}: {e}")
            except Exception as e:
                failed_tables.append(f"{name} (오류: {str(e)[:50]})")
                print(f"[WARN] Failed to load {name}: {e}")
        
        # data_lake_path가 설정되어 있으면 추가로 로드 시도
        data_lake_path = self.config.get("data_lake_path", "./data_lake")
        if os.path.exists(data_lake_path):
            try:
                data_lake_data = self._load_from_data_lake(data_lake_path)
                # 기존 결과와 병합 (data_lake 우선)
                result.update(data_lake_data)
                print(f"[INFO] data_lake에서 {len(data_lake_data)}개 테이블 추가 로드")
            except Exception as e:
                print(f"[WARN] Failed to load from data_lake: {e}")
        
        if failed_tables:
            print(f"[WARN] {len(failed_tables)}개 테이블 로드 실패: {', '.join(failed_tables)}")
        
        print(f"[INFO] 총 {len(result)}개 테이블 로드 완료")
        return result
    
    def _load_from_data_lake(self, data_lake_path: str) -> Dict[str, pd.DataFrame]:
        """
        data_lake 폴더에서 모든 Excel 파일 로드 (로더 사용)
        
        Args:
            data_lake_path: data_lake 폴더 경로
        
        Returns:
            {파일명(확장자 제외): DataFrame} 딕셔너리
        """
        result = {}
        data_lake_dir = Path(data_lake_path)
        
        if not data_lake_dir.exists():
            return result
        
        # Excel 파일 찾기
        excel_files = list(data_lake_dir.glob("*.xlsx")) + list(data_lake_dir.glob("*.xls"))
        
        for excel_file in excel_files:
            try:
                table_name = excel_file.stem
                
                # 이미 로드된 테이블은 스킵
                if table_name in result:
                    continue
                
                # 로더를 통해 로드 (제네릭 로더 사용)
                loader = self.get_loader(table_name)
                if loader:
                    df = loader.load()
                    result[table_name] = df
                else:
                    # 로더가 없으면 직접 로드 (하위 호환성)
                    df = pd.read_excel(excel_file)
                    result[table_name] = df
                    
            except Exception as e:
                print(f"[WARN] Failed to load {excel_file}: {e}")
        
        return result
    
    def save_table(self, name: str, df: pd.DataFrame, path: Optional[str] = None):
        """
        테이블 데이터 저장
        
        Args:
            name: 데이터 테이블 이름
            df: 저장할 DataFrame
            path: 저장 경로 (None이면 config의 경로 사용)
        """
        if path is None:
            path = self.data_paths.get(name)
            if not path:
                raise ValueError(f"Data path for {name} not found in config")
        
        # 상대 경로를 절대 경로로 변환
        if not os.path.isabs(path):
            base_dir = Path(__file__).parent.parent
            path = base_dir / path
        
        # 디렉터리 생성
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # 파일 확장자에 따라 저장
        if path.endswith(".xlsx") or path.endswith(".xls"):
            df.to_excel(path, index=False)
        elif path.endswith(".csv"):
            df.to_csv(path, index=False)
        else:
            # 기본적으로 CSV로 저장
            df.to_csv(path, index=False)

