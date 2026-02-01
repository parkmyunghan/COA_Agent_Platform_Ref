# 검증 권장사항 연동 시스템 구현 가이드

## 구현 완료 사항

### 1. 스키마 검증 탭 (`ui/components/ontology_studio/schema_manager.py`)

#### 변경 사항:
- **권장사항 추출 함수 추가**: `_extract_recommendations(report)` 함수 구현
  - 축선-지형 연결성 문제 감지 및 권장사항 생성
  - 전장축선 객체화 문제 감지 및 권장사항 생성
  - 고립된 노드 문제 감지 및 권장사항 생성
  - 순환 참조 문제 감지 및 권장사항 생성

- **검증 실행 시 권장사항 저장**:
  ```python
  if st.button("🚀 스키마 검증 실행"):
      report = validator.validate_schema_compliance()
      recommendations = _extract_recommendations(report)
      if recommendations:
          st.session_state.validation_recommendations = recommendations
          st.session_state.validation_recommendations_timestamp = datetime.now()
  ```

- **권장사항 표시 및 관계 관리 탭 이동 버튼**:
  - 권장사항 요약 테이블 표시
  - "관계 관리 탭으로 이동" 버튼 제공
  - 권장사항 상세 정보 안내

### 2. 관계 관리 탭 (`ui/components/ontology_studio/relationship_manager.py`)

#### 변경 사항:
- **권장사항 배너 함수 추가**: `_render_validation_recommendations_banner()` 함수 구현
  - 해결되지 않은 권장사항만 표시
  - 우선순위별 색상 표시 (높음: 🔴, 중간: 🟡, 낮음: 🟢)
  - 상세 조치 방법 표시
  - 조치 완료 버튼
  - 권장사항 닫기 버튼

- **관계 관리 탭 상단에 배너 표시**:
  ```python
  if 'validation_recommendations' in st.session_state:
      _render_validation_recommendations_banner()
  ```

- **관계 생성 규칙 서브탭 하이라이트**:
  - 권장사항과 관련된 테이블 선택 시 안내 메시지 표시
  - 상세 조치 방법 제공

- **관계 조회 서브탭 하이라이트**:
  - 권장사항과 관련된 경우 하이라이트 표시

### 3. 메인 페이지 (`ui/views/ontology_studio.py`)

#### 변경 사항:
- **페이지 상단 권장사항 알림**:
  ```python
  if 'validation_recommendations' in st.session_state:
      unresolved = [r for r in st.session_state.validation_recommendations 
                    if not r.get('resolved', False)]
      if unresolved:
          st.warning(f"⚠️ **{len(unresolved)}개의 검증 권장사항**이 있습니다.")
          # 관계 관리 탭으로 이동 버튼
  ```

## 사용 흐름

1. **스키마 검증 실행**
   - "스키마 관리" 탭 → "스키마 검증" 서브탭
   - "🚀 스키마 검증 실행" 버튼 클릭
   - 검증 결과에 따라 권장사항 자동 추출 및 저장

2. **권장사항 확인**
   - 스키마 검증 탭에서 권장사항 요약 테이블 확인
   - "🔗 관계 관리 탭으로 이동" 버튼 클릭

3. **관계 관리 탭에서 조치**
   - 관계 관리 탭 상단에 권장사항 배너 표시
   - 관련 서브탭으로 이동하여 상세 조치 방법 확인
   - 관계 규칙 추가/수정 수행

4. **조치 완료**
   - "✅ 조치 완료" 버튼 클릭
   - 또는 "❌ 권장사항 닫기" 버튼으로 닫기

## 권장사항 데이터 구조

```python
{
    "id": "axis_terrain_connectivity",
    "우선순위": "높음",
    "항목": "축선-지형 연결성",
    "문제": "0개의 지형 연결 확인",
    "조치": "관계 규칙 확인 및 추가",
    "대상": "전장축선",
    "관련_탭": "관계 관리",
    "관련_서브탭": "관계 생성 규칙",
    "상세_조치": [
        "1. 관계 관리 탭의 '관계 생성 규칙' 서브탭으로 이동",
        "2. '전장축선' 테이블 선택",
        "3. 시작지형셀ID, 종단지형셀ID 관계 규칙 확인",
        "4. 관계 규칙이 없으면 추가 (지형셀 타겟, has지형셀 관계)",
        "5. 온톨로지 재생성하여 관계 적용"
    ],
    "관련_테이블": ["전장축선", "지형셀"],
    "관련_관계": ["has지형셀"],
    "resolved": False  # 조치 완료 여부
}
```

## 확인 방법

1. **Streamlit 서버 재시작**:
   ```bash
   # 기존 서버 종료 후 재시작
   streamlit run ui/main.py
   ```

2. **테스트 절차**:
   - 온톨로지 스튜디오 페이지 접속
   - "스키마 관리" 탭 → "스키마 검증" 서브탭
   - "🚀 스키마 검증 실행" 버튼 클릭
   - 검증 결과 확인 (점수가 80% 미만이면 권장사항 생성)
   - "관계 관리" 탭으로 이동하여 배너 확인

3. **디버깅**:
   - `st.session_state.validation_recommendations` 확인
   - 브라우저 개발자 도구에서 콘솔 에러 확인
   - Streamlit 로그 확인

## 주요 함수 위치

- `_extract_recommendations()`: `ui/components/ontology_studio/schema_manager.py:580`
- `_render_validation_recommendations_banner()`: `ui/components/ontology_studio/relationship_manager.py:253`
- 권장사항 저장: `ui/components/ontology_studio/schema_manager.py:448-458`
- 권장사항 표시: `ui/components/ontology_studio/schema_manager.py:547-578`
- 배너 표시: `ui/components/ontology_studio/relationship_manager.py:19-20`

