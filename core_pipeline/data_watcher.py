# core_pipeline/data_watcher.py
# -*- coding: utf-8 -*-
"""
Data Watcher
데이터 변경 감지 및 자동 갱신 모듈
"""
import os
import time
from threading import Thread
from typing import Dict, Optional
from pathlib import Path


class DataWatcher:
    """데이터 변경 감지 및 자동 갱신"""
    
    def __init__(self, data_manager, ontology_manager, status_manager=None):
        """
        Args:
            data_manager: DataManager 인스턴스
            ontology_manager: OntologyManager 인스턴스
            status_manager: StatusManager 인스턴스 (선택 사항)
        """
        self.data_manager = data_manager
        self.ontology_manager = ontology_manager
        self.status_manager = status_manager
        self.last_modified = {}
        self.watch_interval = 5  # 5초마다 체크
        self.watching = False
        self.watch_thread = None
        self.change_callbacks = []  # 변경 감지 시 호출할 콜백 함수들
        # 이전 데이터 스냅샷 저장 (증분 업데이트를 위해)
        self.last_data_snapshot = {}
    
    def start_watching(self):
        """데이터 감시 시작"""
        if self.watching:
            return
        
        self.watching = True
        self.watch_thread = Thread(target=self._watch_loop, daemon=True)
        self.watch_thread.start()
        print("[INFO] 데이터 변경 감시 시작")
    
    def stop_watching(self):
        """데이터 감시 중지"""
        self.watching = False
        if self.watch_thread:
            self.watch_thread.join(timeout=1)
        print("[INFO] 데이터 변경 감시 중지")
    
    def register_change_callback(self, callback):
        """변경 감지 시 호출할 콜백 등록"""
        self.change_callbacks.append(callback)
    
    def _watch_loop(self):
        """감시 루프"""
        while self.watching:
            try:
                changes = self.watch_data_changes()
                if changes:
                    for callback in self.change_callbacks:
                        try:
                            callback(changes)
                        except Exception as e:
                            print(f"[WARN] 콜백 실행 실패: {e}")
                time.sleep(self.watch_interval)
            except Exception as e:
                print(f"[ERROR] 데이터 감시 오류: {e}")
                time.sleep(self.watch_interval)
    
    def watch_data_changes(self) -> Dict[str, bool]:
        """
        데이터 파일 변경 감지
        
        Returns:
            {테이블명: 변경여부} 딕셔너리
        """
        changes = {}
        
        # data_paths에서 모든 테이블 확인
        # DataManager에서 data_paths 가져오기
        if hasattr(self.data_manager, 'config') and 'data_paths' in self.data_manager.config:
            data_paths = self.data_manager.config['data_paths']
        elif hasattr(self.data_manager, 'data_paths'):
            data_paths = self.data_manager.data_paths
        else:
            data_paths = {}
        
        for table_name, path in data_paths.items():
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    base_dir = Path(__file__).parent.parent
                    path_obj = base_dir / path_obj
                
                if path_obj.exists():
                    current_mtime = path_obj.stat().st_mtime
                    
                    if table_name in self.last_modified:
                        if current_mtime > self.last_modified[table_name]:
                            # 변경 감지
                            changes[table_name] = True
                            self._handle_data_change(table_name, str(path_obj))
                    
                    self.last_modified[table_name] = current_mtime
            except Exception as e:
                print(f"[WARN] {table_name} 변경 감지 실패: {e}")
        
        # 2. data_lake 폴더에서 새 파일 감지
        data_lake_path = self.data_manager.config.get("data_lake_path", "./data_lake")
        base_dir = Path(__file__).parent.parent.parent
        data_lake_dir = base_dir / data_lake_path
        
        if data_lake_dir.exists():
            excel_files = list(data_lake_dir.glob("*.xlsx")) + list(data_lake_dir.glob("*.xls"))
            
            for excel_file in excel_files:
                table_name = excel_file.stem
                
                try:
                    current_mtime = excel_file.stat().st_mtime
                    
                    # 새 파일 감지
                    if table_name not in self.last_modified:
                        changes[table_name] = True
                        self.last_modified[table_name] = current_mtime
                        print(f"[INFO] 새 테이블 감지: {table_name}")
                        self._handle_data_change(table_name, str(excel_file))
                    else:
                        # 기존 파일 변경 감지
                        if current_mtime > self.last_modified[table_name]:
                            changes[table_name] = True
                            self._handle_data_change(table_name, str(excel_file))
                            self.last_modified[table_name] = current_mtime
                except Exception as e:
                    print(f"[WARN] {table_name} 변경 감지 실패: {e}")
        
        return changes
    
    def _handle_data_change(self, table_name: str, path: str) -> Dict:
        """
        데이터 변경 처리 (증분 업데이트 사용)
        
        Args:
            table_name: 테이블명
            path: 파일 경로
            
        Returns:
            처리 결과 딕셔너리
        """
        print(f"[INFO] 데이터 변경 감지: {table_name}")
        
        try:
            import pandas as pd
            
            # 로더 캐시 무효화
            if hasattr(self.data_manager, 'invalidate_table_cache'):
                self.data_manager.invalidate_table_cache(table_name)
            
            # 1. 새 데이터 로드
            new_data = self.data_manager.load_table(table_name)
            
            if new_data is None or new_data.empty:
                print(f"[WARN] {table_name} 데이터가 비어있어 업데이트 건너뜀")
                return {
                    "changed": False,
                    "table": table_name,
                    "error": "Empty data"
                }
            
            # 2. 이전 데이터 가져오기 (스냅샷)
            old_data = self.last_data_snapshot.get(table_name)
            
            # 3. 상태 관리자 업데이트 (좌표 등 동적 데이터)
            if self.status_manager:
                # 상태 관리자의 캐시 무효화
                self.status_manager.invalidate_cache()
                print(f"[INFO] StatusManager 캐시 무효화 완료: {table_name}")

            # 4. 온톨로지 업데이트 분기 처리
            # 좌표/상태 정보 테이블인 경우 온톨로지 전체 재구축 건너뜀 (성능 최적화)
            status_tables = ["위협상황", "아군부대현황", "적군부대현황"]
            is_status_table = any(st_table in table_name for st_table in status_tables)
            
            if is_status_table:
                print(f"[INFO] 상태 정보 업데이트 감지 - 온톨로지 전체 재구축 건너뜀: {table_name}")
                # 필요한 경우 온톨로지의 특정 속성만 업데이트하는 가벼운 로직을 수행할 수 있음
            else:
                # 지식 기반(스키마, 매핑 등) 변경인 경우 온톨로지 업데이트 수행
                # 3. 온톨로지 그래프가 있고 이전 데이터가 있으면 증분 업데이트 사용
                if (self.ontology_manager.graph is not None and 
                    old_data is not None and 
                    not old_data.empty and
                    hasattr(self.ontology_manager, 'incremental_update')):
                    
                    try:
                        print(f"[INFO] 증분 업데이트 시작: {table_name}")
                        self.ontology_manager.incremental_update(
                            table_name, old_data, new_data
                        )
                        print(f"[INFO] 증분 업데이트 완료: {table_name}")
                    except Exception as e:
                        print(f"[WARN] 증분 업데이트 실패, 전체 재구축으로 대체: {e}")
                        # 증분 업데이트 실패 시 전체 재구축
                        try:
                            data = self.data_manager.load_all()
                            self.ontology_manager.build_from_data(data)
                        except Exception as e2:
                            print(f"[ERROR] 전체 재구축도 실패: {e2}")
                else:
                    # 첫 변경이거나 그래프가 없으면 전체 재구축
                    try:
                        data = self.data_manager.load_all()
                        self.ontology_manager.build_from_data(data)
                    except Exception as e:
                        print(f"[ERROR] 전체 구축 실패: {e}")
            
            # 5. 스냅샷 업데이트 (다음 변경 감지를 위해)
            self.last_data_snapshot[table_name] = new_data.copy()
            
            # 6. 결과 반환
            return {
                "changed": True,
                "table": table_name,
                "path": path,
                "timestamp": time.time(),
                "incremental": not is_status_table and old_data is not None and not old_data.empty,
                "status_only": is_status_table
            }
        except Exception as e:
            print(f"[ERROR] 데이터 변경 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                "changed": False,
                "error": str(e),
                "table": table_name
            }
    
    def force_check(self) -> Dict[str, bool]:
        """
        강제로 변경 감지 체크 (수동 호출)
        
        Returns:
            {테이블명: 변경여부} 딕셔너리
        """
        return self.watch_data_changes()

