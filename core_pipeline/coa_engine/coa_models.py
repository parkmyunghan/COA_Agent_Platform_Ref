# core_pipeline/coa_engine/coa_models.py
# -*- coding: utf-8 -*-
"""
COA Data Models
COA 데이터 구조 정의
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RoleType(Enum):
    """부대 역할 타입"""
    MAIN_ATTACK = "주공"
    SUPPORTING_ATTACK = "조공"
    RESERVE = "예비"
    DECEPTION = "기만"
    SUPPORT = "지원"
    DEFENSE = "방어"


class AxisRole(Enum):
    """축선 역할 타입"""
    PRIMARY = "주공"
    SECONDARY = "조공"
    RESERVE = "예비"
    DECEPTION = "기만"
    DEFENSE = "방어"


@dataclass
class AxisAssignment:
    """축선 배치 정보"""
    axis_id: str
    role: AxisRole
    priority: int = 1  # 1이 가장 높은 우선순위
    
    def to_dict(self) -> Dict:
        return {
            'axis_id': self.axis_id,
            'role': self.role.value,
            'priority': self.priority
        }


@dataclass
class UnitAssignment:
    """부대 배치 정보"""
    unit_id: str
    axis_id: str
    role: RoleType
    primary_mission: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'unit_id': self.unit_id,
            'axis_id': self.axis_id,
            'role': self.role.value,
            'primary_mission': self.primary_mission
        }


@dataclass
class COA:
    """COA (Course of Action) 객체"""
    coa_id: str
    coa_name: Optional[str] = None
    description: Optional[str] = None
    
    # 축선 배치 정보
    axis_assignments: Dict[str, AxisAssignment] = field(default_factory=dict)
    
    # 부대 배치 정보
    unit_assignments: Dict[str, UnitAssignment] = field(default_factory=dict)
    
    # 메타데이터
    mission_id: Optional[str] = None
    created_by: str = "rule_based"  # "rule_based", "llm_assisted", or "ontology_search"
    llm_suggestion: Optional[str] = None  # LLM 보충 설명
    reasoning_trace: Optional[List[str]] = field(default_factory=list)  # 온톨로지 추론 과정
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'coa_id': self.coa_id,
            'coa_name': self.coa_name,
            'description': self.description,
            'axis_assignments': {
                axis_id: assignment.to_dict()
                for axis_id, assignment in self.axis_assignments.items()
            },
            'unit_assignments': {
                unit_id: assignment.to_dict()
                for unit_id, assignment in self.unit_assignments.items()
            },
            'mission_id': self.mission_id,
            'created_by': self.created_by,
            'llm_suggestion': self.llm_suggestion,
            'reasoning_trace': self.reasoning_trace
        }
    
    def add_axis_assignment(self, axis_id: str, role: AxisRole, priority: int = 1):
        """축선 배치 추가"""
        self.axis_assignments[axis_id] = AxisAssignment(axis_id, role, priority)
    
    def add_unit_assignment(self, unit_id: str, axis_id: str, role: RoleType, primary_mission: Optional[str] = None):
        """부대 배치 추가"""
        self.unit_assignments[unit_id] = UnitAssignment(unit_id, axis_id, role, primary_mission)
    
    def get_units_by_axis(self, axis_id: str) -> List[UnitAssignment]:
        """특정 축선에 배치된 부대 목록"""
        return [
            assignment for assignment in self.unit_assignments.values()
            if assignment.axis_id == axis_id
        ]
    
    def get_primary_axis(self) -> Optional[str]:
        """주공 축선 ID 반환"""
        for axis_id, assignment in self.axis_assignments.items():
            if assignment.role == AxisRole.PRIMARY:
                return axis_id
        return None

