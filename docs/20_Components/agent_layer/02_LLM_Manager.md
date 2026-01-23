# LLM Manager

## 1. 개요

- **역할**: LLM 모델 관리 및 텍스트 생성
- **위치**: Agent Layer
- **클래스**: `core_pipeline.llm_manager.LLMManager`
- **다이어그램 표시**: "LLM Manager"

LLM Manager는 OpenAI API, 사내망 모델, 로컬 모델을 통합 관리하여 Agent에 자연어 처리 기능을 제공합니다. 우선순위에 따라 자동으로 모델을 선택하고, 실패 시 폴백 메커니즘을 제공합니다.

---

## 2. 주요 기능

### 2.1 다중 모델 지원
- **OpenAI API**: GPT-4o 우선 사용
- **사내망 모델**: 내부 API 서버 모델
- **로컬 모델**: beomi-gemma-ko-2b (폴백)

### 2.2 자동 모델 선택
- 우선순위: OpenAI → 사내망 → 로컬
- Lazy Loading: 외부 모델 실패 시에만 로컬 모델 로드

### 2.3 텍스트 생성
- **`generate()`**: 프롬프트 기반 텍스트 생성
- 상황 분석, COA 적응화, 설명 생성 등에 사용

---

## 3. 구현 상세

### 3.1 클래스 위치
```python
# core_pipeline/llm_manager.py
class LLMManager:
    """LLM 모델 관리자 클래스 (OpenAI API 우선, 로컬 모델 폴백)"""
```

### 3.2 주요 메서드

#### `generate(prompt: str, max_tokens: int = 512, **kwargs) -> str`
텍스트를 생성합니다.

```python
# 사용 예시
llm_manager = LLMManager()
result = llm_manager.generate(
    prompt="위협 상황을 분석하세요: 침투 위협, 심각도 85%",
    max_tokens=512
)
```

#### `get_available_models() -> Dict`
사용 가능한 모델 목록을 반환합니다.

```python
# 사용 예시
available = llm_manager.get_available_models()
# 결과: {'openai': {'available': True, ...}, 'local': {...}, ...}
```

---

## 4. 데이터 흐름

```
Agent 요청
    ↓
LLMManager.generate()
    ↓
모델 선택 (우선순위)
    ├─→ OpenAI API (우선)
    ├─→ 사내망 모델 (폴백)
    └─→ 로컬 모델 (최종 폴백)
    ↓
텍스트 생성
    ↓
결과 반환
```

---

## 5. 설정 및 파라미터

### 5.1 설정 파일
- **위치**: `config/model_config.yaml`
- **설정**:
  ```yaml
  llm:
    use_openai: true  # OpenAI 우선 사용
    model_name: "beomi-gemma-ko-2b"
    model_path: "./models/llm/beomi-gemma-ko-2b"
  
  openai:
    api_key: "..."
    model: "gpt-4o"
    max_tokens: 512
    temperature: 0.7
  ```

### 5.2 모델 우선순위
1. **OpenAI API** (gpt-4o)
2. **사내망 모델** (설정된 경우)
3. **로컬 모델** (beomi-gemma-ko-2b)

---

## 6. 사용 예시

### 6.1 기본 사용
```python
from core_pipeline.llm_manager import LLMManager

llm_manager = LLMManager()

# 텍스트 생성
prompt = "위협 상황을 분석하세요: 침투 위협, 심각도 85%"
result = llm_manager.generate(prompt, max_tokens=512)
```

### 6.2 Agent에서 사용
```python
# agents/defense_coa_agent/logic_defense_enhanced.py
# 상황 분석
llm_insights = self.core.llm_manager.generate(
    prompt=f"다음 상황을 분석하세요:\n{situation_text}",
    max_tokens=512
)

# COA 적응화
adapted_coa = self.core.llm_manager.generate(
    prompt=f"다음 방책을 현재 상황에 맞게 적응화하세요:\n{coa_description}",
    max_tokens=256
)
```

---

## 7. 관련 컴포넌트

### 7.1 입력
- **Agent**: 상황 분석, COA 적응화 요청

### 7.2 출력
- **Agent**: 자연어 분석 결과 및 설명 제공
- **사용자 인터페이스**: 추천 이유 생성

---

## 8. 참고 자료

- **코드 위치**: `core_pipeline/llm_manager.py`
- **관련 문서**: 
  - `docs/방책추천_시스템.md`
- **설정 파일**: 
  - `config/model_config.yaml`

---

## 9. 중요 사항

### 9.1 Lazy Loading
외부 모델(OpenAI, 사내망)이 사용 가능하면 로컬 모델은 로드하지 않아 메모리와 시작 시간을 최적화합니다.

### 9.2 폴백 메커니즘
OpenAI API 실패 시 자동으로 사내망 모델 또는 로컬 모델로 전환됩니다.

---

**작성일**: 2025년 12월  
**버전**: 1.0

