# 추론 개수 비교 가이드

## 개선 전후 비교

### 개선 전 (하드코딩된 절대값 기준)

**로그 예시**:
```
2026-01-23 12:58:04,627 - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 시작: 원본 트리플 수 = 6613
2026-01-23 12:58:18,145 - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 완료: 6221개 새로운 트리플 생성 (13.53초)
2026-01-23 12:58:18,145 - core_pipeline.owl_reasoner - INFO -   원본: 6613 → 추론: 12834 triples

... (LLM/RAG/규칙 파일 로드) ...

2026-01-23 12:58:42,951 - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 시작: 원본 트리플 수 = 12834
2026-01-23 12:58:49,218 - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 완료: 541개 새로운 트리플 생성 (6.47초)
2026-01-23 12:58:49,219 - core_pipeline.owl_reasoner - INFO -   원본: 12834 → 추론: 13375 triples
```

**문제점**:
- 추론이 **2번 실행**됨
- 첫 번째 추론: 6,613 → 12,834 triples (+6,221)
- 두 번째 추론: 12,834 → 13,375 triples (+541)
- 총 추론 시간: 약 20초 (13.53초 + 6.47초)

### 개선 후 (동적 비율 기반 판단)

**예상 로그**:
```
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 기존 온톨로지 파일 발견: instances.ttl. 자동 로드를 시도합니다.
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 온톨로지 로드 중... (knowledge\ontology\schema.ttl)
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 온톨로지 로드 완료. 현재 트리플 수: 624
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 온톨로지 로드 중... (knowledge\ontology\instances.ttl)
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 온톨로지 로드 완료. 현재 트리플 수: 6613
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 'instances.ttl' 기반으로 그래프 초기화 완료. 원본 크기: 6613 triples
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - instances_reasoned.ttl이 없어 OWL-RL 추론을 자동 실행합니다...
2026-01-23 XX:XX:XX,XXX - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 시작: 원본 트리플 수 = 6613
2026-01-23 XX:XX:XX,XXX - core_pipeline.owl_reasoner - INFO - RDFS 추론 실행 중...
2026-01-23 XX:XX:XX,XXX - core_pipeline.owl_reasoner - INFO - RDFS 추론 후: 9359 triples (+2746)
2026-01-23 XX:XX:XX,XXX - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 실행 중...
2026-01-23 XX:XX:XX,XXX - core_pipeline.owl_reasoner - INFO - OWL-RL 추론 완료: 6221개 새로운 트리플 생성 (XX.XX초)
2026-01-23 XX:XX:XX,XXX - core_pipeline.owl_reasoner - INFO -   원본: 6613 → 추론: 12834 triples
2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - OWL-RL 추론 완료: 6221개 새로운 트리플 생성

... (LLM/RAG/규칙 파일 로드) ...

2026-01-23 XX:XX:XX,XXX - OntologyManager - INFO - 추론 여부 판단 - 원본: 6613 triples, 현재: 12834 triples, 비율: 1.94x
2026-01-23 XX:XX:XX,XXX - api.dependencies - INFO - 이미 추론이 실행되었습니다. 중복 추론을 건너뜁니다.
```

**개선점**:
- 추론이 **1번만 실행**됨
- 첫 번째 추론: 6,613 → 12,834 triples (+6,221)
- 두 번째 추론: **스킵됨** (비율 1.94x >= 1.3x 기준 충족)
- 총 추론 시간: 약 13-14초 (첫 번째 추론만 실행)
- **시간 절약**: 약 6-7초

## 확인 방법

### 1. 로그 파일 확인

```bash
# 최신 로그 파일 확인
cat logs/platform_20260123.log | grep -E "OWL-RL 추론|추론 여부 판단|원본 크기|이미 추론이 실행되었습니다"
```

### 2. 확인할 항목

1. **원본 크기 저장 확인**:
   ```
   'instances.ttl' 기반으로 그래프 초기화 완료. 원본 크기: 6613 triples
   ```

2. **추론 여부 판단 로그 확인**:
   ```
   추론 여부 판단 - 원본: 6613 triples, 현재: 12834 triples, 비율: 1.94x
   ```

3. **중복 추론 스킵 확인**:
   ```
   이미 추론이 실행되었습니다. 중복 추론을 건너뜁니다.
   ```

4. **추론 실행 횟수 확인**:
   - "OWL-RL 추론 시작" 메시지가 **1번만** 나타나야 함
   - "OWL-RL 추론 완료" 메시지가 **1번만** 나타나야 함

### 3. 트리플 수 확인

**개선 전**:
- 최종 트리플 수: **13,375 triples** (두 번째 추론 후)

**개선 후**:
- 최종 트리플 수: **12,834 triples** (첫 번째 추론 후)

## 예상 결과

서버 재시작 후:

1. ✅ 추론이 **1번만** 실행됨
2. ✅ 최종 트리플 수: **12,834 triples**
3. ✅ 추론 시간: 약 **13-14초** (이전 대비 약 6-7초 절약)
4. ✅ 로그에 "추론 여부 판단" 및 "중복 추론을 건너뜁니다" 메시지 확인

## 문제 발생 시

만약 여전히 추론이 2번 실행된다면:

1. **원본 크기 저장 확인**:
   - 로그에 "원본 크기: XXXX triples" 메시지가 있는지 확인
   - 없으면 `_original_graph_size` 저장 로직 확인 필요

2. **비율 계산 확인**:
   - 로그에 "비율: X.XXx" 메시지가 있는지 확인
   - 비율이 1.3 이상인데도 추론이 실행되면 판단 로직 확인 필요

3. **플래그 확인**:
   - `_inference_performed` 플래그가 제대로 설정되는지 확인
   - `CorePipeline`에서 플래그 확인 로직 확인 필요
