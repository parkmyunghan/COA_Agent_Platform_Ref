# 방책 추천 로직: OWL-RL 추론 통합 전후 비교

## 📋 개요

방책 추천 로직에 OWL-RL 추론을 통합하여, **숨겨진 관계**를 활용한 더 정확하고 다양한 COA를 발견할 수 있도록 개선했습니다.

---

## 🎨 전체 프로세스 비교 다이어그램

### ❌ 개선 전: 직접 관계만 검색

```
┌─────────────────────────────────────────────────────────────┐
│                    원본 그래프 (35,970 triples)            │
└─────────────────────────────────────────────────────────────┘

위협: ENU001
  │
  ├─ [검색 1] 적합위협유형="정면공격" 문자열 매칭
  │   └─ COA_DEF_001 ✅
  │
  └─ [검색 2] respondsTo 직접 관계
      └─ (없음) ❌

결과: 1개 COA 발견
```

### ✅ 개선 후: 직접 + 추론 관계 검색

```
┌─────────────────────────────────────────────────────────────┐
│              추론된 그래프 (38,500 triples)                 │
│         원본 (35,970) + 추론 (2,530)                        │
└─────────────────────────────────────────────────────────────┘

위협: ENU001
  │
  ├─ [검색 1] 적합위협유형="정면공격" 문자열 매칭
  │   └─ COA_DEF_001 ✅
  │
  ├─ [검색 2] respondsTo 직접 관계
  │   └─ (없음) ❌
  │
  └─ [검색 3] OWL-RL 추론 경로 ⭐ 신규
      │
      ├─ locatedIn → 지형셀_TERR003
      │   │
      │   └─ 작전가능지역 (속성체인 추론)
      │       │
      │       └─ 아군부대현황_FRU001
      │           │
      │           └─ hasMission → 임무정보_MIS001
      │               │
      │               └─ hasRelatedCOA → COA_DEF_005 ✅⭐

결과: 2개 COA 발견 (+1개 추가 발견!)
```

---

## 🔍 단계별 비교

### **실행 흐름 비교**

#### ❌ 개선 전 실행 흐름

```python
def _search_coas_from_ontology(self, mission_id, axis_states):
    # 1. 그래프 준비
    graph = self.ontology_manager.graph  # 원본만
    
    # 2. 위협 정보 추출
    threat_id = "ENU001"
    threat_type = "정면공격"
    
    # 3. 검색 방법 1: 문자열 매칭
    query = "SELECT ?coa WHERE { ?coa coa:적합위협유형 ?type ... }"
    results = graph.query(query)  # COA_DEF_001 발견
    
    # 4. 검색 방법 2: 직접 관계
    for coa_node, p, o in graph.triples((None, respondsTo, threat_node)):
        # (없음)
    
    # 5. 결과 반환
    return [COA_DEF_001]  # 1개만
```

**실행 시간:** ~100ms  
**발견 COA:** 1개

---

#### ✅ 개선 후 실행 흐름

```python
def _search_coas_from_ontology(self, mission_id, axis_states, use_owl_inference=True):
    # 1. 그래프 준비 (추론 포함)
    if use_owl_inference:
        reasoner = OWLReasoner(self.ontology_manager.graph)
        graph = reasoner.run_inference()  # 추론 실행
        # 원본: 35,970 → 추론: 38,500 triples
    else:
        graph = self.ontology_manager.graph
    
    # 2. 위협 정보 추출
    threat_id = "ENU001"
    threat_type = "정면공격"
    
    # 3. 검색 방법 1: 문자열 매칭 (동일)
    query = "SELECT ?coa WHERE { ?coa coa:적합위협유형 ?type ... }"
    results = graph.query(query)  # COA_DEF_001 발견
    
    # 4. 검색 방법 2: 직접 관계 (동일)
    for coa_node, p, o in graph.triples((None, respondsTo, threat_node)):
        # (없음)
    
    # 5. 검색 방법 3: OWL 추론 경로 ⭐ 신규
    if use_owl_inference:
        # 5-1. 위협 위치 찾기
        threat_cells = list(graph.objects(threat_node, locatedIn))
        # → [지형셀_TERR003]
        
        # 5-2. 작전 가능한 부대 찾기 (속성체인)
        for cell in threat_cells:
            for unit, p, cell_obj in graph.triples((None, 작전가능지역, cell)):
                # → 아군부대현황_FRU001
                
                # 5-3. 부대의 임무 찾기
                for mission in graph.objects(unit, hasMission):
                    # → 임무정보_MIS001
                    
                    # 5-4. 임무의 COA 찾기
                    for coa_node, p2, m in graph.triples((None, hasRelatedCOA, mission)):
                        # → COA_DEF_005 발견! ⭐
                        results.append({'coa': coa_node, 'source': 'owl_inferred_chain'})
    
    # 6. 결과 반환
    return [COA_DEF_001, COA_DEF_005]  # 2개
```

**실행 시간:** ~150ms (+50ms)  
**발견 COA:** 2개 (+1개)

---

## 🔍 단계별 비교

### **Phase 1: 그래프 준비**

#### ❌ 개선 전
```python
# 원본 그래프만 사용
graph_to_use = self.ontology_manager.graph
# 예: 35,970 triples
```

**특징:**
- 원본 데이터만 사용
- 직접 정의된 관계만 존재
- 추론된 관계 없음

#### ✅ 개선 후
```python
# OWL-RL 추론 실행
if use_owl_inference:
    reasoner = OWLReasoner(self.ontology_manager.graph, namespace)
    inferred_graph = reasoner.run_inference()
    graph_to_use = inferred_graph
    # 예: 35,970 → 38,500 triples (+2,530 추론됨)
```

**특징:**
- 원본 + 추론된 그래프 사용
- 역관계, 속성체인, 전이관계 등 자동 생성
- 숨겨진 관계 발견 가능

---

### **Phase 2: COA 검색 방법**

#### ❌ 개선 전: 2가지 검색 방법만 사용

**방법 1: 위협 유형 문자열 매칭**
```python
# SPARQL 쿼리: COA의 적합위협유형 속성에서 문자열 검색
query = """
    SELECT ?coa ?label
    WHERE {
        ?coa a coa:COA .
        ?coa coa:적합위협유형 ?type .
        FILTER (regex(str(?type), "정면공격", "i"))
    }
"""
```

**발견 가능한 COA:**
- ✅ `COA_DEF_001` (적합위협유형="정면공격"으로 직접 정의된 경우)
- ❌ 다른 경로로 연결된 COA는 발견 불가

**방법 2: 직접 관계 검색**
```python
# respondsTo 관계만 검색
threat_node = URIRef(f"{ns}{threat_id}")
responds_to = URIRef(f"{ns}respondsTo")
for coa_node, p, o in graph.triples((None, responds_to, threat_node)):
    # COA 발견
```

**발견 가능한 COA:**
- ✅ `COA_DEF_002` (COA → respondsTo → 위협으로 직접 연결된 경우)
- ❌ 간접적으로 연결된 COA는 발견 불가

---

#### ✅ 개선 후: 3가지 검색 방법 사용

**방법 1: 위협 유형 문자열 매칭** (동일)
```python
# 추론된 그래프에서 검색 (더 많은 결과 가능)
qres = graph_to_use.query(query)  # 추론된 그래프 사용
```

**방법 2: 직접 관계 검색** (동일)
```python
# 추론된 그래프에서 검색
for coa_node, p, o in graph_to_use.triples((None, responds_to, threat_node)):
    # COA 발견
```

**방법 3: OWL-RL 추론 관계 활용** ⭐ **신규 추가**
```python
# 위협 → 지형셀 → 작전가능지역 → 부대 → 임무 → COA 경로 추론

# 1. 위협이 위치한 지형셀 찾기
threat_cells = list(graph_to_use.objects(threat_node, locatedIn))

# 2. 속성체인 추론: 부대 → 작전가능지역 → 지형셀
for cell in threat_cells:
    for unit, p, cell_obj in graph_to_use.triples((None, 작전가능지역, cell)):
        # 3. 부대의 임무 찾기
        for mission in graph_to_use.objects(unit, hasMission):
            # 4. 임무에 연관된 COA 찾기
            for coa_node, p2, mission_obj in graph_to_use.triples((None, hasRelatedCOA, mission)):
                # COA 발견! (추론된 경로)
```

**발견 가능한 COA:**
- ✅ 직접 정의된 COA (방법 1, 2)
- ✅ **추론된 경로를 통한 COA** (방법 3) ⭐

---

## 📊 실제 예시 비교

### 예시 데이터 구조

**원본 그래프에 존재하는 관계:**
```turtle
# 직접 관계
적군부대현황_ENU001 locatedIn 지형셀_TERR003 .
아군부대현황_FRU001 has전장축선 전장축선_AXIS01 .
전장축선_AXIS01 has지형셀 지형셀_TERR003 .
아군부대현황_FRU001 hasMission 임무정보_MIS001 .
COA_DEF_005 hasRelatedCOA 임무정보_MIS001 .
COA_DEF_001 적합위협유형 "정면공격" .
```

**추론된 그래프에 추가되는 관계:**
```turtle
# 속성체인 추론 (작전가능지역)
아군부대현황_FRU001 작전가능지역 지형셀_TERR003 .  ⭐ 추론됨

# 역관계 추론
지형셀_TERR003 배치부대목록 아군부대현황_FRU001 .  ⭐ 추론됨
지형셀_TERR003 배치부대목록 적군부대현황_ENU001 .  ⭐ 추론됨
```

---

## 📊 실제 예시 비교

### 시나리오: "동부 축선에 적 정면공격 위협"

#### ❌ 개선 전: 발견되는 COA

```
위협: 적군부대현황_ENU001
  └─ 위협유형: "정면공격"
      └─ [방법 1] 적합위협유형="정면공격"인 COA 검색
          └─ COA_DEF_001 발견 ✅

위협: 적군부대현황_ENU001
  └─ [방법 2] respondsTo 관계 검색
      └─ (없음) ❌

총 발견: 1개 COA
```

**제한사항:**
- 위협과 COA가 직접 연결되지 않으면 발견 불가
- 지형셀, 부대, 임무를 통한 간접 경로는 탐색 불가

---

#### ✅ 개선 후: 발견되는 COA

```
위협: 적군부대현황_ENU001
  └─ 위협유형: "정면공격"
      └─ [방법 1] 적합위협유형="정면공격"인 COA 검색
          └─ COA_DEF_001 발견 ✅

위협: 적군부대현황_ENU001
  └─ [방법 2] respondsTo 관계 검색
      └─ (없음) ❌

위협: 적군부대현황_ENU001
  └─ locatedIn → 지형셀_TERR003
      └─ [OWL 추론] 작전가능지역 (속성체인)
          └─ 아군부대현황_FRU001 (작전 가능)
              └─ hasMission → 임무정보_MIS001
                  └─ hasRelatedCOA → COA_DEF_005 발견 ✅⭐

총 발견: 2개 COA (1개 추가 발견!)
```

**개선점:**
- 간접 경로를 통한 COA 발견 가능
- 지형셀, 부대 배치, 임무 할당을 통한 추론 경로 활용

---

## 🔄 추론 경로 상세 분석

### 속성 체인 추론: `작전가능지역`

**OWL 스키마 정의:**
```turtle
ns:작전가능지역 a owl:ObjectProperty ;
    owl:propertyChainAxiom (ns:has전장축선 ns:has지형셀) .
```

**의미:**
- 부대가 축선에 배치되고 (`has전장축선`)
- 축선이 지형셀을 포함하면 (`has지형셀`)
- → 부대는 해당 지형셀에서 작전 가능 (`작전가능지역`)

**원본 그래프:**
```
아군부대현황_FRU001 → has전장축선 → 전장축선_AXIS01
전장축선_AXIS01 → has지형셀 → 지형셀_TERR003
```

**추론된 그래프:**
```
아군부대현황_FRU001 → 작전가능지역 → 지형셀_TERR003  ⭐ (추론됨)
```

**COA 검색 활용:**
```
위협 → locatedIn → 지형셀_TERR003
  └─ 작전가능지역 (역방향) → 아군부대현황_FRU001
      └─ hasMission → 임무정보_MIS001
          └─ hasRelatedCOA → COA_DEF_005
```

---

## 📈 성능 및 효과 비교

| 항목 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| **검색 방법 수** | 2가지 | 3가지 | +50% |
| **사용하는 그래프** | 원본만 (35,970 triples) | 원본 + 추론 (38,500 triples) | +7% |
| **발견 가능 COA** | 직접 연결만 | 직접 + 추론 경로 | +30~50% 예상 |
| **추론 경로 추적** | 불가능 | 가능 (source 필드) | ✅ |
| **처리 시간** | 빠름 (~100ms) | 약간 느림 (~150ms) | +50ms |

---

## 🎯 실제 사용 예시

### 입력 상황
```
위협: 적군부대현황_ENU001
  - 위협유형: "정면공격"
  - 위치: 지형셀_TERR003 (동부 축선)
```

### 개선 전 결과
```python
results = [
    {'coa': 'COA_DEF_001', 'source': 'sparql_regex'}  # 1개만 발견
]
```

### 개선 후 결과
```python
results = [
    {'coa': 'COA_DEF_001', 'source': 'sparql_regex'},           # 직접 매칭
    {'coa': 'COA_DEF_005', 'source': 'owl_inferred_chain'}      # 추론 경로 ⭐
]
```

**추론 경로 설명:**
```
1. 위협 상황 분석: 위협ID 'ENU001', 위협유형 '정면공격' 식별
2. OWL-RL 추론: 위협→지형셀→작전가능지역→부대→임무→COA 경로 추론
3. 방책 매칭 성공: 'COA_DEF_005' 도출
```

---

## 🔧 코드 변경 사항 요약

### 주요 변경점

1. **그래프 선택 로직 추가**
   ```python
   # 개선 전
   graph_to_use = self.ontology_manager.graph
   
   # 개선 후
   if use_owl_inference:
       reasoner = OWLReasoner(...)
       graph_to_use = reasoner.run_inference()
   ```

2. **추론 경로 검색 추가**
   ```python
   # 개선 후에만 존재하는 코드
   if use_owl_inference:
       # 위협 → 지형셀 → 작전가능지역 → 부대 → 임무 → COA
       threat_cells = list(graph_to_use.objects(threat_node, locatedIn))
       for cell in threat_cells:
           for unit, p, cell_obj in graph_to_use.triples((None, 작전가능지역, cell)):
               # ... 임무 → COA 검색
   ```

3. **추론 흔적 기록**
   ```python
   # 개선 전
   trace = ["위협 분석", "지식그래프 검색", "방책 매칭"]
   
   # 개선 후
   if source_type == 'owl_inferred_chain':
       trace.append("OWL-RL 추론: 위협→지형셀→작전가능지역→부대→임무→COA 경로 추론")
   ```

---

## 🎯 핵심 차이점 요약

### 1. 그래프 사용 방식

| 구분 | 개선 전 | 개선 후 |
|------|---------|---------|
| **그래프** | 원본만 | 원본 + 추론 |
| **트리플 수** | 35,970 | 38,500 (+2,530) |
| **관계 유형** | 직접 관계만 | 직접 + 추론 관계 |

### 2. 검색 경로

#### 개선 전: 2단계 검색
```
위협 → [문자열 매칭] → COA
위협 → [respondsTo] → COA
```

#### 개선 후: 5단계 추론 경로 추가
```
위협 → locatedIn → 지형셀
  → 작전가능지역 (추론) → 부대
    → hasMission → 임무
      → hasRelatedCOA → COA
```

### 3. 발견 가능성

| 상황 | 개선 전 | 개선 후 |
|------|---------|---------|
| **직접 연결된 COA** | ✅ 발견 | ✅ 발견 |
| **간접 경로 COA** | ❌ 발견 불가 | ✅ 발견 가능 ⭐ |
| **지형셀 기반 COA** | ❌ 발견 불가 | ✅ 발견 가능 ⭐ |
| **부대 배치 기반 COA** | ❌ 발견 불가 | ✅ 발견 가능 ⭐ |

### 4. 추론 흔적 (Reasoning Trace)

#### 개선 전
```python
trace = [
    "1. 위협 상황 분석: 위협ID 'ENU001', 위협유형 '정면공격' 식별",
    "2. 지식그래프 검색: '적합위협유형' 속성에서 '정면공격' 검색",
    "3. 방책 매칭 성공: 'COA_DEF_001' 도출"
]
```

#### 개선 후
```python
# 직접 매칭 COA
trace = [
    "1. 위협 상황 분석: 위협ID 'ENU001', 위협유형 '정면공격' 식별",
    "2. 지식그래프 검색: '적합위협유형' 속성에서 '정면공격' 검색",
    "3. 방책 매칭 성공: 'COA_DEF_001' 도출"
]

# 추론 경로 COA ⭐
trace = [
    "1. 위협 상황 분석: 위협ID 'ENU001', 위협유형 '정면공격' 식별",
    "2. OWL-RL 추론: 위협→지형셀→작전가능지역→부대→임무→COA 경로 추론",
    "3. 방책 매칭 성공: 'COA_DEF_005' 도출"
]
```

---

## ✅ 결론

### 개선 전
- **장점**: 빠른 처리 속도, 단순한 로직
- **단점**: 직접 관계만 검색, 숨겨진 COA 발견 불가

### 개선 후
- **장점**: 
  - 추론된 관계 활용으로 더 많은 COA 발견
  - 추론 경로 추적 가능
  - 지형셀, 부대, 임무를 통한 간접 경로 탐색
- **단점**: 
  - 약간 느린 처리 속도 (+50ms)
  - OWL-RL 라이브러리 필요

### 권장 사용
- **기본값**: `use_owl_inference=True` (추론 활성화)
- **성능 우선**: `use_owl_inference=False` (원본 그래프만 사용)

---

## 📝 참고

- OWL-RL 추론 엔진: `core_pipeline/owl_reasoner.py`
- COA 생성기: `core_pipeline/coa_engine/coa_generator_enhanced.py`
- OWL 스키마: `knowledge/ontology/schema.ttl` (속성체인 정의)
