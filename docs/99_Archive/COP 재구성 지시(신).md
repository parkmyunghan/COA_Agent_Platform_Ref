너는 국방·작전 분야 전술상황도(COP) 및 지휘통제 UI를 설계·구현하는
Defense Systems Engineer 역할로 동작한다.

본 프로젝트는 단순 지도 시각화가 아니라,
온톨로지 기반 방책추천 파일럿 시스템에서
지휘관이 방책(COA)을 이해·비교·검증할 수 있도록 하는
“설명 가능한 전술상황도(COP)” 구현이 목적이다.

[현재 상황 요약]
- 기존 COP 구현은 지도 렌더링 중심으로 설계되어 본연의 기능을 상실함
- 지도 데이터 처리를 **Online/Offline 하이브리드 방식**으로 개선 필요
- **Offline 모드**에서는 로컬 MBTiles 기반 벡터 타일을 표준으로 사용
- 기존의 단순 이미지/GeoJSON 로컬 파일 로딩 방식은 삭제하여 일관성 확보
- 온톨로지 기반 방책추천 에이전트가 이미 존재하며,
  COA, Unit, Threat는 개념·인스턴스 구조로 정의되어 있음

[핵심 요구사항 – Palantir AIP 수준의 고도화]

1. COP의 역할 재정의: "Object-Centric Operation"
- COP는 단순한 상황판이 아닌, **온톨로지 객체(Object)들의 관계와 상태를 투영하는 뷰(View)**여야 한다.
- 지도상의 마커는 단순한 점이 아니라, 백엔드 온톨로지 인스턴스와 실시간으로 동기화된 "Live Object"이다.
- **핵심 차별점:** "무엇(What)"이 있는가가 아니라 "왜(Why)" 거기에 있으며 "어떤 관계(Relationship)"를 맺고 있는지를 보여주어야 한다.

2. 지도 데이터 구조 및 모드 지원
- **Hybrid Mode 지원:** Online(OSM/Carto) + Offline(Local MBTiles) 자동 전환
- **Layering:**
  - **Base Layer:** 지형 (Physical)
  - **Object Layer:** 부대, 위협 (Ontological Instances)
  - **Reasoning Layer:** 방책 추론의 근거가 되는 논리적 연결선 (Logical Links)
  - **Risk Layer:** 위협 반경 및 리스크 히트맵 (Analytical Overlay)

3. Unit/Threat 표현: "Context-Aware"
- 객체 클릭 시 **"Object 360 View"** 제공:
  - **Properties:** 제원, 상태, 전투력
  - **Links:** 상급부대, 임무, 대치 중인 적, 연관된 지형
  - **History:** 최근 식별 시점, 이동 경로
- **Contextual Highlight:** 특정 위협 선택 시, 해당 위협을 타격할 수 있는 아군 자산만 하이라이트 (Recommendation Trace)

4. COA(방책) 가시화: "Explainable & Simulation"
- **Reasoning Trace (추론 추적):** 방책이 왜 생성되었는지 지도상에 시각화
  - 예: [적 미사일 기지] --(위협)--> [아군 공항] --(방어 필요)--> [PAC-3 부대 배치]
  - 이 논리적 연결 고리를 지도상에 화살표나 점선으로 "Reasoning Layer"에 표시
- **Interactive Comparison:**
  - COA A vs COA B 버튼 클릭 시, 부대 배치와 예상 피해 규모가 즉시 전환되어야 함
- **What-If (초기 단계):**
  - 아군 부대를 드래그했을 때, 해당 위치의 지형(강, 산)이나 적 위협 반경에 따라 "Alert"를 띄우는 기능 (Rule-based feedback)

5. UI 구조 (Palantir Foundry Map 스타일)
- **Map-First Interface:** 모든 조작은 지도 위에서 이루어진다.
- **Left Panel (Knowledge Graph):** 선택한 객체의 온톨로지 관계망 표시 (Graph View)
- **Right Panel (Simulation Results):** 방책 실행 시 예상되는 시계열 변화 및 승률 차트
- **Overlay:** "왜 위험한지 / 왜 선택됐는지"를 텍스트가 아닌 **그래픽(색상, 연결선)**으로 설명

6. 고도화 기능 (Pilot Goals)
- **Multimedia Integration:** 정찰 위성 사진이나 드론 영상이 있다면 해당 위치 마커에서 팝업으로 재생
- **Tactical Assistant:** "이 위치로 이동하면 적 포병 사거리에 노출됨"과 같은 AI 조언 메세지를 지도 오버레이로 표시


[최종 목표]
COP를 통해 지휘관이
“이 방책이 왜 선택되었는지,
다른 방책과 무엇이 어떻게 다른지,
어디가 위험한지”
를 공간적으로 즉시 이해할 수 있어야 한다.

이 목적에 맞게 기존 구현을 비판적으로 재구성하고,
필요하다면 구조부터 다시 설계하라.
