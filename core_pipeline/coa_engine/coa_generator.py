# core_pipeline/coa_engine/coa_generator.py
# -*- coding: utf-8 -*-
"""
COA Generator
COA 후보 생성 모듈
"""
from typing import List, Dict, Optional
from core_pipeline.data_models import AxisState
from core_pipeline.coa_engine.coa_models import COA, AxisRole, RoleType, AxisAssignment, UnitAssignment


class COAGenerator:
    """COA 후보 생성기"""
    
    def __init__(self, use_llm_assistance: bool = False, llm_manager=None, template_loader=None):
        """
        Args:
            use_llm_assistance: LLM 보조 생성 사용 여부
            llm_manager: LLM Manager 인스턴스 (선택적)
            template_loader: 방책템플릿 로더 인스턴스 (선택적)
        """
        self.use_llm_assistance = use_llm_assistance
        self.llm_manager = llm_manager
        self.template_loader = template_loader
    
    def generate_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        user_params: Optional[Dict] = None
    ) -> List[COA]:
        """
        COA 후보 생성
        
        Args:
            mission_id: 임무ID
            axis_states: 축선별 전장상태 요약 리스트
            user_params: 사용자 설정 파라미터
                - max_coas: 최대 COA 수 (기본값: 5)
                - preferred_strategy: 선호 전략 ("defensive", "offensive", "balanced")
                - min_units_per_axis: 축선당 최소 부대 수 (기본값: 1)
        
        Returns:
            COA 후보 리스트
        """
        if not axis_states:
            return []
        
        user_params = user_params or {}
        max_coas = user_params.get('max_coas', 5)
        preferred_strategy = user_params.get('preferred_strategy', 'balanced')
        min_units_per_axis = user_params.get('min_units_per_axis', 1)
        use_templates = user_params.get('use_templates', True)  # 템플릿 사용 여부
        
        coas = []
        
        # 1. 템플릿 기반 COA 생성 (우선)
        if use_templates and self.template_loader:
            template_coas = self._generate_template_based_coas(
                mission_id, axis_states, preferred_strategy, min_units_per_axis
            )
            coas.extend(template_coas)
        
        # 2. 규칙 기반 COA 생성 (템플릿이 없거나 부족한 경우)
        if len(coas) < max_coas:
            rule_based_coas = self._generate_rule_based_coas(
                mission_id, axis_states, preferred_strategy, min_units_per_axis
            )
            # 템플릿 기반과 중복되지 않는 COA만 추가
            existing_names = {coa.coa_name for coa in coas if coa.coa_name}
            for coa in rule_based_coas:
                if coa.coa_name not in existing_names:
                    coas.append(coa)
        
        # LLM 보조 생성 (옵션)
        if self.use_llm_assistance and self.llm_manager:
            coas = self._enhance_with_llm(coas, mission_id, axis_states)
        
        # 최대 개수 제한
        return coas[:max_coas]
    
    def _generate_template_based_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        preferred_strategy: str,
        min_units_per_axis: int
    ) -> List[COA]:
        """템플릿 기반 COA 생성"""
        if not self.template_loader:
            return []
        
        coas = []
        
        try:
            # 1. 전략유형에 맞는 템플릿 로드
            templates_df = self.template_loader.get_templates_by_strategy(preferred_strategy)
            
            # 2. 위협수준별로 템플릿 필터링
            if axis_states:
                # 가장 높은 위협수준 확인
                max_threat_level = max(
                    (axis.threat_level for axis in axis_states),
                    key=lambda x: {'High': 3, 'Medium': 2, 'Low': 1}.get(x, 0)
                )
                
                # 위협수준에 맞는 템플릿 추가 필터링
                threat_templates = self.template_loader.get_templates_by_threat_level(max_threat_level)
                if not threat_templates.empty:
                    # 전략과 위협수준 모두 일치하는 템플릿 우선
                    templates_df = templates_df[
                        templates_df['템플릿ID'].isin(threat_templates['템플릿ID'])
                    ] if not templates_df.empty else threat_templates
            
            # 3. 우선순위로 정렬
            if '우선순위' in templates_df.columns:
                templates_df = templates_df.sort_values('우선순위')
            
            # 4. 템플릿별로 COA 생성
            for _, template_row in templates_df.iterrows():
                template_id = template_row.get('템플릿ID', '')
                template_name = template_row.get('템플릿명', '')
                description = template_row.get('설명', '')
                actions = template_row.get('기본액션', '')
                
                # COA 생성
                coa = COA(
                    coa_id=f"{mission_id}_{template_id}",
                    coa_name=template_name,
                    description=description,
                    mission_id=mission_id,
                    created_by="template_based"
                )
                
                # 템플릿 액션에 따라 축선/부대 배치
                self._apply_template_actions(
                    coa, template_row, axis_states, min_units_per_axis
                )
                
                coas.append(coa)
                
        except Exception as e:
            print(f"[WARN] 템플릿 기반 COA 생성 실패: {e}")
        
        return coas
    
    def _apply_template_actions(
        self,
        coa: COA,
        template_row: Dict,
        axis_states: List[AxisState],
        min_units_per_axis: int
    ):
        """템플릿 액션을 COA에 적용"""
        template_name = template_row.get('템플릿명', '')
        actions = template_row.get('기본액션', '')
        action_list = [a.strip() for a in str(actions).split('|') if a.strip()]
        
        # 위협레벨별로 축선 정렬
        sorted_axes = sorted(
            axis_states,
            key=lambda x: {'High': 3, 'Medium': 2, 'Low': 1}.get(x.threat_level, 0),
            reverse=True
        )
        
        if not sorted_axes:
            return
        
        # 템플릿명 기반 패턴 매칭
        if '고위협' in template_name or '집중' in template_name:
            # 고위협 축선 집중 방어
            high_threat_axes = [a for a in sorted_axes if a.threat_level == 'High']
            if high_threat_axes:
                primary_axis = high_threat_axes[0]
                coa.add_axis_assignment(primary_axis.axis_id, AxisRole.DEFENSE, priority=1)
                for unit in primary_axis.friendly_units[:min_units_per_axis]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        primary_axis.axis_id,
                        RoleType.DEFENSE,
                        "고위협 축선 방어"
                    )
            
            # 나머지 축선 방어
            for axis in sorted_axes[1:]:
                coa.add_axis_assignment(axis.axis_id, AxisRole.DEFENSE, priority=2)
                for unit in axis.friendly_units[:min_units_per_axis]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        axis.axis_id,
                        RoleType.DEFENSE,
                        "축선 방어"
                    )
        
        elif '균형' in template_name or '균등' in template_name:
            # 균형 방어
            for axis in sorted_axes:
                coa.add_axis_assignment(axis.axis_id, AxisRole.DEFENSE, priority=1)
                for unit in axis.friendly_units[:min_units_per_axis]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        axis.axis_id,
                        RoleType.DEFENSE,
                        "균형 방어"
                    )
        
        elif '주공' in template_name and '조공' in template_name:
            # 주공-조공 구조
            if len(sorted_axes) >= 2:
                primary_axis = sorted_axes[0]
                coa.add_axis_assignment(primary_axis.axis_id, AxisRole.PRIMARY, priority=1)
                for unit in primary_axis.friendly_units[:min_units_per_axis + 1]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        primary_axis.axis_id,
                        RoleType.MAIN_ATTACK,
                        "주공 축선 공격"
                    )
                
                secondary_axis = sorted_axes[1]
                coa.add_axis_assignment(secondary_axis.axis_id, AxisRole.SECONDARY, priority=2)
                for unit in secondary_axis.friendly_units[:min_units_per_axis]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        secondary_axis.axis_id,
                        RoleType.SUPPORTING_ATTACK,
                        "조공 축선 공격"
                    )
        
        elif '선제' in template_name or '공격' in template_name:
            # 선제 공격
            if sorted_axes:
                primary_axis = sorted_axes[0]
                coa.add_axis_assignment(primary_axis.axis_id, AxisRole.PRIMARY, priority=1)
                for unit in primary_axis.friendly_units[:min_units_per_axis + 1]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        primary_axis.axis_id,
                        RoleType.MAIN_ATTACK,
                        "선제 공격"
                    )
        
        elif '최소' in template_name or '기본' in template_name:
            # 최소 방어
            for axis in sorted_axes[:1]:  # 첫 번째 축선만
                coa.add_axis_assignment(axis.axis_id, AxisRole.DEFENSE, priority=3)
                for unit in axis.friendly_units[:1]:  # 최소 부대만
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        axis.axis_id,
                        RoleType.DEFENSE,
                        "기본 감시"
                    )
        
        else:
            # 기본 패턴: 첫 번째 축선에 집중
            if sorted_axes:
                primary_axis = sorted_axes[0]
                coa.add_axis_assignment(primary_axis.axis_id, AxisRole.DEFENSE, priority=1)
                for unit in primary_axis.friendly_units[:min_units_per_axis]:
                    coa.add_unit_assignment(
                        unit.friendly_unit_id,
                        primary_axis.axis_id,
                        RoleType.DEFENSE,
                        "기본 배치"
                    )
    
    def _generate_rule_based_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        preferred_strategy: str,
        min_units_per_axis: int
    ) -> List[COA]:
        """규칙 기반 COA 생성 (핵심 로직)"""
        coas = []
        
        # 위협레벨별로 축선 정렬 (High → Medium → Low)
        sorted_axes = sorted(
            axis_states,
            key=lambda x: {'High': 3, 'Medium': 2, 'Low': 1}.get(x.threat_level, 0),
            reverse=True
        )
        
        # 전략별 COA 생성
        if preferred_strategy == 'defensive':
            coas.extend(self._generate_defensive_coas(mission_id, sorted_axes, min_units_per_axis))
        elif preferred_strategy == 'offensive':
            coas.extend(self._generate_offensive_coas(mission_id, sorted_axes, min_units_per_axis))
        else:  # balanced
            coas.extend(self._generate_balanced_coas(mission_id, sorted_axes, min_units_per_axis))
        
        return coas
    
    def _generate_defensive_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        min_units_per_axis: int
    ) -> List[COA]:
        """방어 중심 COA 생성"""
        coas = []
        
        # COA 1: 고위협 축선 집중 방어
        if axis_states:
            coa1 = COA(
                coa_id=f"{mission_id}_DEFENSE_01",
                coa_name="고위협 축선 집중 방어",
                description="고위협 축선에 주공 배치, 나머지 축선은 방어",
                mission_id=mission_id
            )
            
            # 고위협 축선에 주공 배치
            high_threat_axes = [a for a in axis_states if a.threat_level == 'High']
            if high_threat_axes:
                primary_axis = high_threat_axes[0]
                coa1.add_axis_assignment(primary_axis.axis_id, AxisRole.DEFENSE, priority=1)
                
                # 해당 축선의 아군부대 배치
                for unit in primary_axis.friendly_units[:min_units_per_axis]:
                    coa1.add_unit_assignment(
                        unit.friendly_unit_id,
                        primary_axis.axis_id,
                        RoleType.DEFENSE,
                        "고위협 축선 방어"
                    )
            
            # 나머지 축선은 방어
            for axis in axis_states[1:]:
                coa1.add_axis_assignment(axis.axis_id, AxisRole.DEFENSE, priority=2)
                for unit in axis.friendly_units[:min_units_per_axis]:
                    coa1.add_unit_assignment(
                        unit.friendly_unit_id,
                        axis.axis_id,
                        RoleType.DEFENSE,
                        "축선 방어"
                    )
            
            coas.append(coa1)
        
        # COA 2: 균형 방어
        if len(axis_states) >= 2:
            coa2 = COA(
                coa_id=f"{mission_id}_DEFENSE_02",
                coa_name="균형 방어",
                description="모든 축선에 균등하게 부대 배치",
                mission_id=mission_id
            )
            
            for axis in axis_states:
                coa2.add_axis_assignment(axis.axis_id, AxisRole.DEFENSE, priority=1)
                for unit in axis.friendly_units[:min_units_per_axis]:
                    coa2.add_unit_assignment(
                        unit.friendly_unit_id,
                        axis.axis_id,
                        RoleType.DEFENSE,
                        "균형 방어"
                    )
            
            coas.append(coa2)
        
        return coas
    
    def _generate_offensive_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        min_units_per_axis: int
    ) -> List[COA]:
        """공격 중심 COA 생성"""
        coas = []
        
        # COA 1: 주공-조공 구조
        if len(axis_states) >= 2:
            coa1 = COA(
                coa_id=f"{mission_id}_OFFENSE_01",
                coa_name="주공-조공 구조",
                description="주공 축선에 집중, 조공 축선으로 분산",
                mission_id=mission_id
            )
            
            # 첫 번째 축선을 주공으로
            primary_axis = axis_states[0]
            coa1.add_axis_assignment(primary_axis.axis_id, AxisRole.PRIMARY, priority=1)
            
            for unit in primary_axis.friendly_units[:min_units_per_axis + 1]:
                coa1.add_unit_assignment(
                    unit.friendly_unit_id,
                    primary_axis.axis_id,
                    RoleType.MAIN_ATTACK,
                    "주공 축선 공격"
                )
            
            # 두 번째 축선을 조공으로
            if len(axis_states) > 1:
                secondary_axis = axis_states[1]
                coa1.add_axis_assignment(secondary_axis.axis_id, AxisRole.SECONDARY, priority=2)
                
                for unit in secondary_axis.friendly_units[:min_units_per_axis]:
                    coa1.add_unit_assignment(
                        unit.friendly_unit_id,
                        secondary_axis.axis_id,
                        RoleType.SUPPORTING_ATTACK,
                        "조공 축선 공격"
                    )
            
            coas.append(coa1)
        
        return coas
    
    def _generate_balanced_coas(
        self,
        mission_id: str,
        axis_states: List[AxisState],
        min_units_per_axis: int
    ) -> List[COA]:
        """균형 COA 생성 (방어 + 공격 혼합)"""
        coas = []
        
        # 방어 COA와 공격 COA를 모두 포함
        coas.extend(self._generate_defensive_coas(mission_id, axis_states, min_units_per_axis))
        coas.extend(self._generate_offensive_coas(mission_id, axis_states, min_units_per_axis))
        
        # COA 3: 위협레벨 기반 적응형
        if axis_states:
            coa3 = COA(
                coa_id=f"{mission_id}_BALANCED_01",
                coa_name="위협레벨 기반 적응형",
                description="위협레벨에 따라 축선별 역할 자동 배정",
                mission_id=mission_id
            )
            
            for axis in axis_states:
                if axis.threat_level == 'High':
                    role = AxisRole.DEFENSE
                    unit_role = RoleType.DEFENSE
                elif axis.threat_level == 'Medium':
                    role = AxisRole.SECONDARY
                    unit_role = RoleType.SUPPORTING_ATTACK
                else:
                    role = AxisRole.RESERVE
                    unit_role = RoleType.RESERVE
                
                coa3.add_axis_assignment(axis.axis_id, role, priority=1)
                for unit in axis.friendly_units[:min_units_per_axis]:
                    coa3.add_unit_assignment(
                        unit.friendly_unit_id,
                        axis.axis_id,
                        unit_role,
                        f"{axis.threat_level} 위협 대응"
                    )
            
            coas.append(coa3)
        
        return coas
    
    def _enhance_with_llm(
        self,
        coas: List[COA],
        mission_id: str,
        axis_states: List[AxisState]
    ) -> List[COA]:
        """LLM을 사용하여 COA 보강 (보충 설명/변형안 제안)"""
        if not self.llm_manager:
            return coas
        
        # LLM은 보충 설명만 추가 (핵심 구조는 변경하지 않음)
        for coa in coas:
            try:
                # 간단한 프롬프트로 보충 설명 생성
                prompt = f"""
다음 COA에 대한 간단한 보충 설명을 제공하세요:
- COA ID: {coa.coa_id}
- COA 이름: {coa.coa_name}
- 설명: {coa.description}
- 축선 수: {len(coa.axis_assignments)}
- 부대 수: {len(coa.unit_assignments)}

한 문장으로 간단히 설명하세요.
"""
                # LLM 호출 (실제 구현은 LLM Manager에 따라 다름)
                # coa.llm_suggestion = self.llm_manager.generate(prompt)
                coa.created_by = "llm_assisted"
            except Exception as e:
                print(f"[WARN] LLM 보강 실패: {e}")
        
        return coas

