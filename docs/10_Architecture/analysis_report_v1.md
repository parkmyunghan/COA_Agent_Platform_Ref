# 온톨로지 기반 방책 추천 시스템(Pilot) 종합 분석 보고서

## 1. 개요 (Overview)
본 문서는 구축된 **온톨로지 기반 방책 추천 에이전트 시스템(Pilot)**의 아키텍처, 구현 로직, 데이터 처리를 심층 분석하여 그 결과를 기술합니다. 특히 **Palantir AIP (Artificial Intelligence Platform)** 수준의 국방 AI 시스템을 지향하기 위한 격차(Gap) 분석과, 교육용 자료로서의 활용 가능성에 초점을 맞추었습니다.

---

## 2. 현황 분석 (Current Status)

### 2.1 아키텍처 및 데이터 파이프라인
*   **구조:** Data Layer (Excel/Docs) → ETL Layer (Ontology/Vector) → Reasoning Layer (Rule/Hybrid) → Application Layer (Streamlit)의 4계층 구조가 명확히 분리되어 있습니다.
*   **데이터 통합:** `EnhancedOntologyManager`를 통해 정형 데이터(Excel)를 RDF 지식그래프로, `RAGManager`를 통해 비정형 문서(PDF)를 벡터 DB로 변환하는 하이브리드 파이프라인이 구축되어 있습니다.
*   **평가:** 파일럿 시스템으로서 **데이터 흐름의 완결성**은 우수하나, 실시간성이 결여된 배치(Batch) 위주의 처리 방식입니다.

### 2.2 핵심 로직 및 추론 (Reasoning)
*   **COA 생성:** `EnhancedCOAGenerator`는 규칙 기반 생성에 온톨로지 조회 결과를 보강하는 **하이브리드 방식**을 채택했습니다.
*   **COA 평가:** 7대 평가 요소를 기반으로 정량적 평가를 수행하며, 자원 매칭(`_extract_resource_availability`) 로직에서 계층/속성/키워드 매칭을 복합적으로 사용하는 등 **정교한 구현**이 돋보입니다.
*   **LLM 활용:** SITREP 파싱, COA 적응화(Adaptation), 설명 생성(Explanation) 등 적재적소에 LLM이 배치되어 있습니다. 그러나 LLM이 온톨로지 구조를 "이해"하고 추론하기보다는, 검색된 텍스트를 "요약/변형"하는 수준에 머물러 있습니다.

---

## 3. 팔란티어(Palantir) 대비 격차 분석 (Gap Analysis)

| 평가 항목 | 현재 시스템 (As-Is) | 팔란티어 AIP 목표 (To-Be) | 격차 수준 |
| :--- | :--- | :--- | :--- |
| **Ontology Dynamics** | **정적(Static):** 사전에 정의된 `effectiveness` 속성이나 고정된 관계(`countsThreat`)를 단순 조회함. | **동적(Dynamic):** 날씨, 지형, 부대 피로도 등 변수에 따라 관계와 속성값이 실시간으로 변화하고 계산됨. | **Critical** |
| **Reasoning Depth** | **1차원적 연결:** A는 B에 효과적이다(A -> respondsTo -> B) 수준의 직접 연결 확인. | **다차원 추론:** A가 B에 효과적이나, C(지형) 조건에서는 D(날씨) 때문에 효율이 30% 감소한다는 복합 추론. | **High** |
| **COA Adaptation** | **템플릿 매칭:** 유사 템플릿을 찾아 텍스트를 일부 수정. | **Generative Planning:** 가용 자원 제약(Constraint)을 온톨로지에서 확인하며 실행 가능한(Executable) 계획을 생성. | **High** |
| **Simulation** | 없음. | **Wargaming:** 추천된 방책의 성공 확률을 시뮬레이션을 통해 검증(Monte Carlo 등). | **Medium** |
| **Transparency** | 텍스트 설명 및 단순 관계망 시각화. | **Decision Path:** 데이터의 출처(Source)부터 결론(Decision)까지의 추론 경로를 Drill-down으로 추적 가능. | **High** |

---

## 4. 개선을 위한 주요 제언 (Recommendations)

### 4.1 [단기] Dynamic Reasoning 도입 (즉시 개선)
현재의 정적 점수 조회 방식을 **SWRL(Semantic Web Rule Language)** 또는 **Python 기반 동적 함수**로 대체해야 합니다.

*   **As-Is:** `get_score(COA_ID) -> returns 0.8` (고정값)
*   **To-Be:** `calculate_score(COA, Terrain, Weather, EnemyStatus)`
    ```python
    def calculate_effectiveness(coa, context):
        base_score = coa.base_effectiveness
        if context.terrain == 'Mountain' and coa.type == 'Mechanized':
            base_score *= 0.6  # 산악 지형에서 기계화부대 페널티
        if context.enemy_status == 'Entrenched':
            base_score *= 0.8  # 참호 방어 시 공격 효율 감소
        return base_score
    ```

### 4.2 [중기] LLM-Ontology Integration 강화
LLM에게 단순 텍스트가 아닌 **Graph Schema**를 인지시켜야 합니다. LLM이 온톨로지를 탐색(Traverse)하는 SPARQL을 스스로 생성하여 "왜?"라는 질문에 답할 수 있게 해야 합니다.

*   **제안:** `Text-to-SPARQL` 에이전트 도입. 사용자가 "왜 이 방책이 추천됐어?"라고 물으면, 에이전트가 `SELECT ?reason WHERE { ... }` 쿼리를 생성하여 근거 데이터를 조회.

### 4.3 [장기] 교육용 콘텐츠화 전략
이 코드는 훌륭한 **"AI Agent Engineering 교보재"**가 될 수 있습니다.
*   **Module 1: 데이터 엔지니어링** - 비정형 문서의 지식그래프 변환 과정.
*   **Module 2: 하이브리드 AI** - Rule(신뢰성) + LLM(유연성) + Ontology(지식)의 결합 패턴.
*   **Module 3: 설명 가능한 AI (XAI)** - 추천 결과의 근거를 추적하는 시각화 기법.

---

## 5. 결론 (Conclusion)
현재 시스템은 **"온톨로지 기반 의사결정 지원 시스템"의 프로토타입으로서 매우 훌륭한 완성도**를 갖추고 있습니다. 특히 데이터 파이프라인과 하이브리드 평가 로직은 상용 솔루션의 초기 버전과 견주어도 손색이 없습니다.

다만, '팔란티어' 수준의 고도화된 시스템으로 발전하기 위해서는 **"정적 데이터 조회"를 넘어선 "동적 상황 추론"** 기능을 강화하고, LLM을 단순 언어 처리기가 아닌 **"추론 엔진의 오케스트레이터"**로 격상시키는 작업이 필요합니다.

### 🚀 Next Step 제안
가장 효과적인 개선 효과를 보여줄 수 있는 **"동적 지형 패널티 적용 로직"**을 `ReasoningEngine`에 시범 구현하여, 똑같은 방책이라도 평지와 산악 지형에서 추천 순위가 달라지는 것을 시연하는 것을 추천합니다.
