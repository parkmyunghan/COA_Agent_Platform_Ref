# 방책 추천 로직 온톨로지 기반 생성 문제 해결

## 문제 원인

기존 Streamlit 시스템에서는 온톨로지 기반으로 3개 방책을 추천했지만, React 시스템에서는 온톨로지 기능이 작동하지 않았습니다.

### 발견된 문제점

1. **`EnhancedCOAGenerator`가 `generate_coas` 메서드를 오버라이드하지 않음**
   - `EnhancedCOAGenerator`는 `generate_coas_with_ontology` 메서드만 제공
   - `COAService.generate_coas_unified`에서 `self.coa_generator.generate_coas()`를 호출하면 부모 클래스의 기본 `generate_coas`가 호출됨
   - 결과적으로 온톨로지 기반 보강이 실행되지 않음

2. **무한 재귀 가능성**
   - `generate_coas_with_ontology` 내부에서 `super().generate_coas()`를 호출하면 오버라이드된 메서드가 다시 호출될 수 있음

## 해결 방법

### 수정 내용

1. **`EnhancedCOAGenerator.generate_coas` 메서드 오버라이드 추가**
   ```python
   def generate_coas(
       self,
       mission_id: str,
       axis_states: List[AxisState],
       user_params: Optional[Dict] = None
   ) -> List[COA]:
       """
       COA 생성 메서드 오버라이드
       온톨로지 기능이 활성화된 경우 generate_coas_with_ontology를 호출
       """
       if self.enable_ontology_enhancement and self.ontology_manager:
           return self.generate_coas_with_ontology(mission_id, axis_states, user_params)
       else:
           # 온톨로지 기능이 비활성화된 경우 기본 생성 메서드 사용
           return super().generate_coas(mission_id, axis_states, user_params)
   ```

2. **무한 재귀 방지**
   - `generate_coas_with_ontology` 내부에서 부모 클래스의 `generate_coas`를 직접 호출하도록 수정
   ```python
   # 부모 클래스의 generate_coas를 직접 호출하여 무한 재귀 방지
   from core_pipeline.coa_engine.coa_generator import COAGenerator
   rule_based_coas = COAGenerator.generate_coas(self, mission_id, axis_states, user_params)
   ```

## 확인 사항

1. **온톨로지 매니저 초기화 확인**
   - `api/dependencies.py`의 `GlobalStateManager.initialize()`에서 `orchestrator.core.ontology_manager`가 제대로 전달되는지 확인
   - `COAService.initialize_llm_services()`가 호출되어 `EnhancedCOAGenerator`가 생성되는지 확인

2. **온톨로지 기능 활성화 확인**
   - `enable_ontology_enhancement=True`로 설정되어 있는지 확인
   - `ontology_manager`가 `None`이 아닌지 확인

## 테스트 방법

1. 방책 추천 실행 버튼 클릭
2. 백엔드 로그에서 다음 메시지 확인:
   - `[INFO] EnhancedCOAGenerator: 온톨로지 기반 COA 보강 시작`
   - `[DEBUG] _search_coas_from_ontology: threat_type='...'`
3. 생성된 COA가 3개인지 확인
4. COA 설명에 온톨로지 기반 정보가 포함되어 있는지 확인

## 관련 파일

- `core_pipeline/coa_engine/coa_generator_enhanced.py` - 수정됨
- `core_pipeline/coa_service.py` - 확인 필요
- `api/dependencies.py` - 확인 필요
