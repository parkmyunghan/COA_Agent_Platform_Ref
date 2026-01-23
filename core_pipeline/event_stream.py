# core_pipeline/event_stream.py
# -*- coding: utf-8 -*-
"""
Event Stream
실시간 이벤트 스트리밍 시뮬레이터
"""
from datetime import datetime
from typing import Dict, List, Optional
from queue import Queue
import threading
import pandas as pd
from pathlib import Path


class EventStream:
    """이벤트 스트리밍 시뮬레이터"""
    
    def __init__(self, data_manager, ontology_manager):
        """
        Args:
            data_manager: DataManager 인스턴스
            ontology_manager: OntologyManager 인스턴스
        """
        self.data_manager = data_manager
        self.ontology_manager = ontology_manager
        self.event_queue = Queue()
        self.event_history = []
        self.processing = False
    
    def simulate_threat_update(self, threat_id: str, new_threat_level: float) -> Dict:
        """
        위협 상황 업데이트 이벤트
        
        Args:
            threat_id: 위협 ID
            new_threat_level: 새로운 위협 수준 (0-1)
            
        Returns:
            처리 결과 딕셔너리
        """
        # 이전 값 조회
        old_value = self._get_current_threat_level(threat_id)
        
        event = {
            "type": "threat_update",
            "entity_id": threat_id,
            "field": "심각도",
            "old_value": old_value,
            "new_value": new_threat_level,
            "timestamp": datetime.now().isoformat()
        }
        
        self.event_queue.put(event)
        return self._process_event(event)
    
    def simulate_resource_update(self, resource_id: str, new_quantity: int) -> Dict:
        """
        자원 업데이트 이벤트
        
        Args:
            resource_id: 자원 ID
            new_quantity: 새로운 수량
            
        Returns:
            처리 결과 딕셔너리
        """
        event = {
            "type": "resource_update",
            "entity_id": resource_id,
            "field": "가용수량",
            "old_value": None,
            "new_value": new_quantity,
            "timestamp": datetime.now().isoformat()
        }
        
        self.event_queue.put(event)
        return self._process_event(event)
    
    def _get_current_threat_level(self, threat_id: str) -> Optional[float]:
        """현재 위협 수준 조회"""
        try:
            # 위협상황 데이터에서 조회
            threat_df = self.data_manager.load_table("위협상황")
            if threat_df is not None and not threat_df.empty:
                id_col = None
                for col in threat_df.columns:
                    if '위협ID' in str(col) or str(col) == 'ID':
                        id_col = col
                        break
                
                if id_col:
                    row = threat_df[threat_df[id_col] == threat_id]
                    if not row.empty:
                        severity_col = None
                        for col in threat_df.columns:
                            if '심각도' in str(col) or '위협수준' in str(col):
                                severity_col = col
                                break
                        
                        if severity_col:
                            value = row.iloc[0][severity_col]
                            try:
                                return float(str(value).replace(',', ''))
                            except (ValueError, TypeError):
                                return None
        except Exception as e:
            print(f"[WARN] 위협 수준 조회 실패: {e}")
        
        return None
    
    def _process_event(self, event: Dict) -> Dict:
        """
        이벤트 처리
        
        Args:
            event: 이벤트 딕셔너리
            
        Returns:
            처리 결과 딕셔너리
        """
        try:
            if event["type"] == "threat_update":
                # 1. 데이터 업데이트 (시뮬레이션용 - 실제로는 DB 업데이트)
                self._update_data_simulation(event)
                
                # 2. 온톨로지 증분 업데이트
                self._update_ontology(event)
                
                # 3. 영향받는 추천 재계산
                affected_recommendations = self._find_affected_recommendations(event)
                
                # 4. 이벤트 히스토리 저장
                self.event_history.append(event)
                
                return {
                    "processed": True,
                    "affected_recommendations": affected_recommendations,
                    "event": event
                }
            elif event["type"] == "resource_update":
                # 자원 업데이트 처리
                self._update_ontology(event)
                self.event_history.append(event)
                
                return {
                    "processed": True,
                    "event": event
                }
        except Exception as e:
            print(f"[ERROR] 이벤트 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                "processed": False,
                "error": str(e),
                "event": event
            }
    
    def _update_data_simulation(self, event: Dict):
        """데이터 업데이트 시뮬레이션 (실제로는 DB 업데이트)"""
        # 시뮬레이션용: Excel 파일 직접 수정하지 않음
        # 실제 구현 시에는 DB 업데이트 또는 API 호출
        threat_id = event["entity_id"]
        new_value = event["new_value"]
        print(f"[INFO] 데이터 업데이트 시뮬레이션: {threat_id} = {new_value}")
    
    def _update_ontology(self, event: Dict):
        """온톨로지 증분 업데이트"""
        if not self.ontology_manager.graph:
            return
        
        try:
            from rdflib import URIRef, Literal
            
            entity_id = event["entity_id"]
            field = event["field"]
            new_value = event["new_value"]
            
            ns = self.ontology_manager.ns
            entity_uri = URIRef(ns[entity_id])
            predicate_uri = URIRef(ns[field])
            
            # 기존 값 제거
            self.ontology_manager.graph.remove((entity_uri, predicate_uri, None))
            
            # 새 값 추가
            self.ontology_manager.graph.add((entity_uri, predicate_uri, Literal(new_value)))
            
            print(f"[INFO] 온톨로지 업데이트: {entity_id}.{field} = {new_value}")
        except Exception as e:
            print(f"[WARN] 온톨로지 업데이트 실패: {e}")
    
    def _find_affected_recommendations(self, event: Dict) -> List[str]:
        """영향받는 추천 찾기"""
        # 해당 위협 상황을 사용하는 추천 찾기
        affected = []
        # 구현 필요: 추천 히스토리에서 해당 위협 상황 사용 추천 찾기
        return affected
    
    def get_event_history(self, limit: int = 10) -> List[Dict]:
        """
        이벤트 히스토리 가져오기
        
        Args:
            limit: 최대 개수
            
        Returns:
            이벤트 히스토리 리스트
        """
        return self.event_history[-limit:] if len(self.event_history) > limit else self.event_history


