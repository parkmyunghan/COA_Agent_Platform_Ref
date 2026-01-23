# core_pipeline/ontology_history.py
# -*- coding: utf-8 -*-
"""
온톨로지 변경 히스토리 관리
관계 변경 이력 추적 및 롤백 기능
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

class OntologyHistory:
    """온톨로지 변경 히스토리 관리"""
    
    def __init__(self, history_file: str = "metadata/ontology_history.jsonl"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
    
    def record_change(self, change_type: str, source: str, target: str, 
                     relation: str, old_value: Optional[Dict] = None,
                     new_value: Optional[Dict] = None, user: str = "system") -> str:
        """
        변경 이력 기록
        
        Args:
            change_type: "ADD", "UPDATE", "DELETE"
            source: 소스 노드 ID
            target: 타겟 노드 ID
            relation: 관계명
            old_value: 변경 전 값
            new_value: 변경 후 값
            user: 사용자 ID
        
        Returns:
            entry_id: 기록된 항목의 ID
        """
        entry_id = str(uuid.uuid4())
        entry = {
            "entry_id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "change_type": change_type,
            "source": source,
            "target": target,
            "relation": relation,
            "old_value": old_value,
            "new_value": new_value,
            "user": user
        }
        
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return entry_id
    
    def get_history(self, source: Optional[str] = None, 
                   target: Optional[str] = None,
                   relation: Optional[str] = None,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
        """
        히스토리 조회
        
        Args:
            source: 소스 노드 필터
            target: 타겟 노드 필터
            relation: 관계명 필터
            date_from: 시작 날짜 (ISO 형식)
            date_to: 종료 날짜 (ISO 형식)
            limit: 최대 조회 개수
        
        Returns:
            히스토리 항목 리스트
        """
        entries = []
        
        if not self.history_file.exists():
            return entries
        
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    
                    # 필터링
                    if source and source not in entry.get("source", ""):
                        continue
                    if target and target not in entry.get("target", ""):
                        continue
                    if relation and relation not in entry.get("relation", ""):
                        continue
                    if date_from and entry.get("timestamp", "") < date_from:
                        continue
                    if date_to and entry.get("timestamp", "") > date_to:
                        continue
                    
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        # 최신순 정렬 및 제한
        entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return entries[:limit]
    
    def rollback(self, entry_id: str, ontology_manager: Any) -> bool:
        """
        특정 변경 롤백
        
        Args:
            entry_id: 롤백할 항목 ID
            ontology_manager: OntologyManager 인스턴스
        
        Returns:
            성공 여부
        """
        # 히스토리에서 항목 찾기
        entries = self.get_history(limit=10000)
        target_entry = None
        
        for entry in entries:
            if entry.get("entry_id") == entry_id:
                target_entry = entry
                break
        
        if not target_entry:
            return False
        
        try:
            change_type = target_entry.get("change_type")
            source = target_entry.get("source")
            target = target_entry.get("target")
            relation = target_entry.get("relation")
            old_value = target_entry.get("old_value")
            
            # 롤백 실행
            if change_type == "ADD":
                # 추가된 관계 삭제
                ontology_manager.remove_relationship(source, target, relation)
            elif change_type == "DELETE":
                # 삭제된 관계 복구
                if old_value:
                    ontology_manager.add_relationship(source, target, relation)
            elif change_type == "UPDATE":
                # 업데이트 롤백
                new_value = target_entry.get("new_value")
                if old_value and new_value:
                    # 이전 값으로 복구
                    ontology_manager.update_relationship(
                        source, target, relation,
                        old_value.get("relation", relation),
                        old_value.get("target", target)
                    )
            
            # 롤백 이력 기록
            self.record_change(
                "ROLLBACK",
                source, target, relation,
                new_value=target_entry,
                old_value=None,
                user=f"rollback_{entry_id}"
            )
            
            return True
        except Exception as e:
            print(f"[ERROR] 롤백 실패: {e}")
            return False

