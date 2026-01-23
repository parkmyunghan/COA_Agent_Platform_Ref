# Streamlit to React 리팩토링 가이드 및 프롬프트

본 문서는 Pilot 시스템의 Streamlit 코드를 React(Frontend)와 FastAPI(Backend) 구조로 안정적으로 전환하기 위한 단계별 프롬프트 모음입니다.

---

## 1단계: 분석 및 아키텍처 매핑 (Analysis)
**목적:** Streamlit의 단일 스크립트 구조를 React의 컴포넌트 구조로 재설계합니다.

> **Prompt:**
> "현재 첨부된 Streamlit 코드(@파일명)를 분석해서 React + FastAPI 구조로 전환하기 위한 기술 스택을 제안해줘. 특히 다음 사항에 집중해줘:
> 1. Streamlit의 `st.session_state`를 대체할 React 상태 관리 방식 (Context API 또는 TanStack Query 추천).
> 2. `st.dataframe`이나 `st.chart`를 대체할 최적의 React 라이브러리 (예: TanStack Table, Recharts).
> 3. Streamlit의 각 위젯(Sidebar, Button, Input)을 Shadcn UI 컴포넌트로 어떻게 매핑할지 리스트업해줘."

---

## 2단계: 백엔드 API 추출 (Backend Separation)
**목적:** Python 비즈니스 로직을 API 서버로 분리합니다.

> **Prompt:**
> "기존 Streamlit 코드에서 UI 부분을 제외한 **비즈니스 로직과 데이터 처리 부분만 추출해서 FastAPI 엔드포인트**로 만들어줘. 
> - 요청과 응답은 JSON 형식을 사용하고, Pydantic 모델로 타입을 정의해줘.
> - React에서 호출할 수 있도록 CORS 설정(`CORSMiddleware`)을 포함한 `main.py`를 작성해줘.
> - 기존에 사용하던 라이브러리(Pandas, Scikit-learn 등)는 그대로 유지하되, 효율적인 비동기(async) 처리를 적용해줘."

---

## 3단계: 프론트엔드 UI 스캐폴딩 (Frontend Implementation)
**목적:** 현대적인 UI 프레임워크를 사용하여 프론트엔드 뼈대를 구축합니다.

> **Prompt:**
> "프론트엔드를 구축해줘. 기술 스택은 **Vite + React + TypeScript + Tailwind CSS** 환경을 기준으로 해.
> 1. UI 스타일은 **Shadcn UI**를 사용해서 현대적이고 깔끔하게 디자인해줘.
> 2. Streamlit의 레이아웃(Sidebar + Main Content)을 그대로 복제한 대시보드 레이아웃을 생성해줘.
> 3. 아까 만든 FastAPI 엔드포인트를 호출하기 위해 `axios`와 `TanStack Query`를 사용한 데이터 페칭 로직을 포함해줘.
> 4. `@filename`의 UI 로직을 각 React 컴포넌트로 분리해서 작성해줘."

---

## 4단계: 상태 관리 및 통합 디버깅 (Integration)
**목적:** 프론트와 백엔드를 연결하고 Streamlit에서 겪었던 구현 오류를 해결합니다.

> **Prompt:**
> "React의 `useState`를 사용해서 사용자의 입력값을 관리하고, '실행' 버튼을 눌렀을 때 백엔드 API로 데이터를 보내고 결과를 화면에 출력하는 전체 흐름을 완성해줘. 
> - Streamlit에서 발생하던 '버튼 클릭 시 상태 초기화'나 '불필요한 전체 재실행' 문제가 발생하지 않도록 리액트의 생명주기에 맞게 최적화해줘.
> - 로딩 상태(Loading Spinner)와 에러 핸들링을 추가해서 사용자 경험을 개선해줘."

---

## 💡 성공적인 리팩토링을 위한 팁
* **시각적 참고:** Streamlit 실행 화면을 스크린샷 찍어 함께 업로드하며 "이 이미지와 똑같이 만들어줘"라고 지시하면 UI 정확도가 훨씬 높아집니다.
* **점진적 전환:** 전체를 한 번에 바꾸기보다, 가장 에러가 잦은 특정 기능(예: 데이터 입력 폼, 차트 대시보드)부터 하나씩 리액트 컴포넌트로 요청하세요.
* **타입 정의:** TypeScript를 사용하면 데이터 구조에서 발생하는 오류를 사전에 방지할 수 있으므로, AI에게 항상 "TypeScript 타입을 명확히 정의해줘"라고 요구하세요.