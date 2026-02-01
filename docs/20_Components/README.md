# 시스템 컴포넌트 상세 설명

이 폴더에는 Defense Intelligent Agent Platform의 각 컴포넌트에 대한 상세 설명 문서가 포함되어 있습니다.

## 📋 목차

### 🏗️ Data Layer (원천 데이터 관리자) - 5개
- [데이터관리자 (Data Manager)](data_layer/01_데이터관리자.md)
- [온톨로지 변환기 (EnhancedOntologyManager)](data_layer/02_온톨로지변환기.md)
- [임베딩 엔진 (rogel-embedding-v2)](data_layer/03_임베딩엔진.md)
- [지식그래프 (RDF/TTL)](data_layer/04_지식그래프.md)
- [벡터 DB (FAISS)](data_layer/05_벡터DB.md)

### ⚙️ Orchestration Layer (파이프라인 조율) - 1개
- [Orchestrator (CorePipeline)](orchestration_layer/01_Orchestrator.md)

### 🤖 Agent Layer (지능형 에이전트) - 4개
- [COA 추천 Agent (EnhancedDefenseCOAAgent)](agent_layer/01_COA_추천_Agent.md)
- [LLM Manager](agent_layer/02_LLM_Manager.md)
- [점수 계산기 (COA Scorer)](agent_layer/03_점수계산기.md)
- [온톨로지 추론기 (SPARQL)](agent_layer/04_온톨로지추론기.md)

### 👤 Command Layer (지휘통제) - 4개
- [상황 입력 (Dashboard)](command_layer/01_상황입력.md)
- [방책 결과 시각화 (Top 3)](command_layer/02_방책결과시각화.md)
- [전략 체인 시각화 (Graphviz)](command_layer/03_전략체인시각화.md)
- [사용자 피드백](command_layer/04_사용자피드백.md)

**총 14개 컴포넌트 문서**

---

## 🔍 사용 방법

1. **시스템 학습 가이드 페이지**: React 대시보드의 "SYSTEM GUIDE" 페이지에서 컴포넌트별 문서를 확인할 수 있습니다.
2. **직접 접근**: 각 문서 파일을 직접 열어서 확인할 수 있습니다.
3. **다이어그램 연동**: 시스템 아키텍처 다이어그램과 함께 참고하면 더욱 이해하기 쉽습니다.

---

## 📝 문서 작성 가이드

각 컴포넌트 문서는 다음 구조를 따릅니다:

1. **개요**: 컴포넌트의 역할과 목적
2. **주요 기능**: 핵심 기능 목록
3. **구현 상세**: 클래스/모듈 위치, 주요 메서드
4. **데이터 흐름**: 입력 → 처리 → 출력
5. **설정 및 파라미터**: 설정 파일, 주요 파라미터
6. **사용 예시**: 실제 사용 코드
7. **관련 컴포넌트**: 연관된 다른 컴포넌트
8. **참고 자료**: 관련 문서, 코드 위치

---

**작성일**: 2025년 12월  
**버전**: 1.0

