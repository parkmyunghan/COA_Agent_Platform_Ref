# 방책추천 성능 최적화 분석 및 개선 방안

## 1. 로그 분석 결과 요약

### 1.1 전체 실행 시간
- **시작 시간**: 2026-01-23 13:49:28
- **종료 시간**: 2026-01-23 13:52:58
- **총 소요 시간**: 약 **3분 30초** (210초)

### 1.2 주요 단계별 시간 분석
1. **시스템 초기화**: ~42초
   - OWL-RL 추론: 12.49초
   - LLM 초기화: ~2초
   - RAG 모델 로드: ~13초
   - COAService 초기화: ~0.5초

2. **방책추천 실행**: ~168초 (13:50:57 ~ 13:52:58)
   - 정황보고 생성: ~23초
   - 방책 분석 및 평가: ~145초

## 2. 발견된 성능 병목

### 2.1 🔴 심각: RelevanceMapper 중복 초기화

**문제점**:
- 로그에서 `RelevanceMapper`와 `ResourcePriorityParser`가 **수십 번** 중복 초기화됨
- 각 COA 평가마다 새로운 `COAScorer` 인스턴스가 생성되면서 매퍼도 새로 초기화됨

**로그 증거**:
```
2026-01-23 13:51:47,408 - core_pipeline.relevance_mapper - INFO - 위협 마스터 매핑 로드 완료: 22개 항목
2026-01-23 13:51:47,436 - core_pipeline.relevance_mapper - INFO - 위협 마스터 매핑 로드 완료: 22개 항목
2026-01-23 13:51:47,451 - core_pipeline.relevance_mapper - INFO - 위협 마스터 매핑 로드 완료: 22개 항목
... (반복)
2026-01-23 13:51:47,554 - COAScorer - INFO - RelevanceMapper 내부 초기화 완료: 77개 매핑 로드됨
2026-01-23 13:51:47,559 - COAScorer - INFO - ResourcePriorityParser 초기화 완료
... (반복)
```

**영향**:
- 각 매퍼 초기화마다 파일 I/O 발생 (Excel 파일 읽기)
- 메모리 사용량 증가
- **예상 성능 저하**: COA 평가 시간의 10-20%가 매퍼 초기화에 소요될 것으로 추정

### 2.2 원인 분석

**코드 흐름**:
1. `COAService.__init__()`에서 `RelevanceMapper`와 `ResourcePriorityParser` 초기화 (1회)
2. `EnhancedDefenseCOAAgent`가 `COAScorer`를 생성할 때 매퍼를 주입하지 않음
3. `COAScorer.__init__()`에서 매퍼가 `None`이면 새로 초기화

**문제 코드 위치**:
- `agents/defense_coa_agent/logic_defense_enhanced.py:526`
  ```python
  scorer = COAScorer(data_manager=self.core.data_manager, config=self.core.config, context=situation_info)
  # relevance_mapper와 resource_parser가 주입되지 않음!
  ```

- `agents/defense_coa_agent/logic_defense_enhanced.py:2860`
  ```python
  scorer = COAScorer(data_manager=self.core.data_manager, config=self.core.config, coa_type=coa_type, context=situation_info)
  # 마찬가지로 매퍼가 주입되지 않음!
  ```

## 3. 개선 방안

### 3.1 즉시 적용 가능한 개선 (우선순위: 높음)

#### 방안 1: CorePipeline에 매퍼 추가 및 Agent에 전달

**장점**:
- Agent가 `self.core.relevance_mapper`로 직접 접근 가능
- 코드 변경 최소화
- COAService와 CorePipeline 간 일관성 유지

**구현**:
1. `CorePipeline.__init__()`에서 `RelevanceMapper`와 `ResourcePriorityParser` 초기화
2. `EnhancedDefenseCOAAgent`에서 `COAScorer` 생성 시 `self.core.relevance_mapper`와 `self.core.resource_parser` 주입

**예상 효과**:
- 매퍼 초기화 시간 제거: ~0.1초 × N회 → 0초
- 전체 방책추천 시간 단축: **10-20초** (약 10-15% 개선)

#### 방안 2: COAService의 매퍼를 CorePipeline에 전달

**장점**:
- COAService에서 이미 초기화된 매퍼 재사용
- 중복 초기화 완전 제거

**구현**:
1. `GlobalStateManager.initialize()`에서 `COAService`의 매퍼를 `CorePipeline`에 설정
2. Agent가 `self.core.relevance_mapper` 사용

### 3.2 중기 개선 방안 (우선순위: 중간)

#### 방안 3: COAScorer 싱글톤 패턴 또는 캐싱

**목적**:
- 동일한 설정으로 여러 번 생성되는 `COAScorer` 인스턴스 재사용

**구현**:
- `COAScorer` 팩토리 함수 또는 싱글톤 매니저 추가
- `(data_manager, config, coa_type, context)` 조합을 키로 캐싱

**예상 효과**:
- 추가적인 5-10초 단축 가능

#### 방안 4: 병렬 처리 최적화

**현재 상태**:
- COA 평가가 순차적으로 실행됨

**개선**:
- 여러 COA 평가를 병렬로 실행 (ThreadPoolExecutor 또는 asyncio)
- 단, 스레드 안전성 확인 필요 (RDF 그래프 접근 등)

**예상 효과**:
- COA 평가 시간: ~145초 → **50-70초** (약 50-60% 개선)

### 3.3 장기 개선 방안 (우선순위: 낮음)

#### 방안 5: 데이터베이스 캐싱

**목적**:
- 매퍼 초기화 시 Excel 파일 읽기 대신 DB 캐시 사용

**구현**:
- SQLite 또는 Redis에 매핑 데이터 캐싱
- 파일 변경 감지 시 캐시 갱신

#### 방안 6: 점진적 로딩

**목적**:
- 필요한 매핑만 지연 로딩

**구현**:
- `RelevanceMapper`에서 실제 사용 시점에 매핑 로드

## 4. 권장 구현 순서

1. ✅ **즉시**: 방안 1 구현 (CorePipeline에 매퍼 추가)
2. ✅ **즉시**: EnhancedDefenseCOAAgent에서 매퍼 주입
3. ⏳ **중기**: 방안 3 (COAScorer 캐싱) 검토
4. ⏳ **장기**: 방안 4 (병렬 처리) 검토

## 5. 예상 성능 개선 효과

### 현재 상태
- 전체 시간: **210초** (3분 30초)
- 매퍼 초기화: ~20-30초 (추정)
- COA 평가: ~145초

### 개선 후 (방안 1 적용)
- 전체 시간: **180-190초** (3분 ~3분 10초)
- 매퍼 초기화: 0초 (1회만)
- COA 평가: ~145초 (동일)

### 개선 후 (방안 1 + 방안 3 적용)
- 전체 시간: **170-180초** (2분 50초 ~3분)
- 매퍼 초기화: 0초
- COA 평가: ~135초

### 개선 후 (방안 1 + 방안 3 + 방안 4 적용)
- 전체 시간: **60-90초** (1분 ~1분 30초)
- 매퍼 초기화: 0초
- COA 평가: ~50-70초 (병렬 처리)

## 6. 구현 체크리스트

- [x] `CorePipeline.__init__()`에 `RelevanceMapper`와 `ResourcePriorityParser` 추가
- [x] `EnhancedDefenseCOAAgent`에서 `COAScorer` 생성 시 매퍼 주입
- [x] `_recommend_by_type()`에서 불필요한 선정사유 생성 제거
- [x] 병렬 처리 구현 (ThreadPoolExecutor)
- [ ] 로그에서 중복 초기화 메시지 제거 확인
- [ ] 성능 테스트 및 시간 측정
- [ ] 문서 업데이트

## 7. 참고 사항

- 매퍼 초기화는 파일 I/O가 포함되어 있어 느릴 수 있음
- Excel 파일 크기에 따라 초기화 시간이 달라질 수 있음
- 향후 데이터베이스로 전환 시 추가 성능 개선 가능
