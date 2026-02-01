# COA Agent Platform Documentation INDEX

이 문서는 COA Agent Platform의 문서 구조와 관리 규칙을 설명합니다. 본 플랫폼은 기존 Streamlit 기반에서 **React + FastAPI** 기반의 현대적 아키텍처로 고도화되었습니다.

## 📁 최신 성과 및 분석 보고서 (New)

최근 진행된 16개 핵심 데이터 테이블 분석 및 통합 검증 성과 보고서입니다.
- **상세 보고서 위치**: [docs/reports/](reports/)
- **주요 문서**:
    - [종합 성과 보고서](reports/final_project_summary_report.md): 프로젝트 전반의 개선 성과 요약
    - [온톨로지 전략 보고서](reports/ontology_strategy_report.md): 지식 그래프 기반 추론 체계 고도화 전략
    - [통합 검증 결과](reports/walkthrough.md): 실데이터 기반 엔드투엔드 시나리오 테스트 결과

## 🌐 외부 접근 및 네트워크 (Remote Access)
- 동일 네트워크 내 IP 접속 가이드: [ROOT README.md](../README.md#외부-접근-및-네트워크-설정-remote-access) 참고
- 백엔드 호스트: `0.0.0.0:8000` (모든 인터페이스 허용)
- 프론트엔드 API 설정: `window.location.hostname` 기반 동적 연결 적용

---

## 문서 디렉토리 구조

문서는 성격에 따라 다음과 같이 분류하여 관리합니다.

### 📁 [00_Management](00_Management)
프로젝트 관리, 로드맵, 운영 메뉴얼 등 관리 차원의 문서입니다.
- **COA_SYSTEM_ROADMAP.md**: 시스템 개발 로드맵
- **operational_manual.md**: 시스템 운영 메뉴얼

### 📁 [10_Architecture](10_Architecture)
시스템의 핵심 설계, 아키텍처, 데이터 모델 등을 다루는 기술 문서입니다.
- **[시스템_아키텍처.md](10_Architecture/시스템_아키텍처.md)**: React/FastAPI 기반 전체 아키텍처 (최신)
- **온톨로지_설계.md**: 지식 그래프 모델 설계
- **점수_산정_시스템.md**: 상황 적응형 가중치(Adaptive Weights) 알고리즘 상세

### 📁 [20_Components](20_Components)
각 계층(Layer)별 컴포넌트의 상세 구현 명세입니다.
- **agent_layer**: 지능형 에이전트 (COAScorer, OntologyReasoner 등) 구현 명세
- **data_layer**: 16개 테이블 기반 데이터 파이프라인 및 온톨로지 변환 명세
- **command_layer**: React 기반 대시보드 및 전술 시각화 명세

### 📁 [30_Guides](30_Guides)
사용자 및 개발자를 위한 각종 가이드 문서입니다.
- **사용자_가이드.md**: React 대시보드 및 프로젝트 실행 매뉴얼
- **관리자_가이드.md**: 시스템 설정 및 모델 관리 가이드
- **데이터_관리_가이드.md**: 16개 데이터 테이블 관리 지침
- **[system_architecture.html](system_architecture.html)**: 인터랙티브 아키텍처 다이어그램 (최신)

### 📁 [99_Archive](99_Archive)
현재는 유효하지 않거나 완료된 작업의 기록, 또는 참고용 레거시 문서들을 보관합니다.
- Streamlit 기반의 레거시 설계 및 초기 리팩토링 기록 등

---

## 문서 작성 및 관리 규칙

본 프로젝트의 모든 문서화 작업은 다음 규칙을 **현행화하여 반드시 준수**해야 합니다.

### 1. 언어 규칙 (Language Rule)
- 생성되는 모든 마크다운(`.md`) 문서는 **반드시 한글(Korean)로 작성**합니다.

### 2. 자동 분류 규칙 (Auto-Categorization)
새로운 문서를 생성할 때는 문서의 성격에 따라 적절한 디렉토리에 위치시켜야 합니다.

| 분류 | 대상 문서 성격 |
| :--- | :--- |
| **00_Management** | 프로젝트 관리, 일정, 로드맵, 운영 정책 |
| **10_Architecture** | 시스템 설계, 구조, 알고리즘, 데이터 모델링 |
| **20_Components** | 특정 기능/모듈의 상세 명세 및 구현 내용 |
| **30_Guides** | 사용자 매뉴얼, 설치/배포 가이드, 튜토리얼 |
| **reports** | 데이터 분석 결과 및 통합 검증 성과 보고서 |
| **99_Archive** | 완료된 작업, 구버전 문서, 임시 메모 (보관용) |

### 3. 최신화 원칙
- 코드가 변경되거나 아키텍처가 전환(예: React 전환)되면 관련된 모든 문서를 즉시 업데이트하여 정합성을 유지합니다.
