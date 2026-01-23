# COA 평가 시스템 개선 - 운영 매뉴얼

**버전**: 1.0  
**작성일**: 2025-12-27  
**대상**: 시스템 운영자, 데이터 관리자

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [일일 운영 체크리스트](#일일-운영-체크리스트)
3. [데이터 관리](#데이터-관리)
4. [모니터링 및 검증](#모니터링-및-검증)
5. [문제 해결](#문제-해결)
6. [성능 최적화](#성능-최적화)

---

## 시스템 개요

### 주요 구성 요소

| 구성 요소 | 파일 | 역할 |
|----------|------|------|
| **RelevanceMapper** | `core_pipeline/relevance_mapper.py` | COA-위협 관련성 계산 |
| **ResourcePriorityParser** | `core_pipeline/resource_priority_parser.py` | 자원 우선순위 파싱 및 점수 계산 |
| **SituationIDMapper** | `core_pipeline/situation_id_mapper.py` | Situation ID 정규화 |
| **COAScorer** | `core_pipeline/coa_scorer.py` | 종합 점수 계산 |

### 데이터 테이블

| 테이블 | 용도 | 업데이트 빈도 |
|--------|------|---------------|
| `위협상황.xlsx` | 위협 정보 + 위협유형 | 신규 위협 발생 시 |
| `방책유형_위협유형_관련성.xlsx` | 유형 레벨 관련성 | 월 1회 검토 |
| `가용자원.xlsx` | 시나리오별 가용 자원 | 주 1회 업데이트 |
| `COA_Library.xlsx` | COA 상세 정보 | 신규 COA 추가 시 |

---

## 일일 운영 체크리스트

### 오전 체크 (09:00)

```bash
# 1. 데이터 품질 검증
cd c:\POC\COA_Agent_Platform
python scripts/validate_data_quality.py

# 2. 단위 테스트 실행
python tests/test_core_improvements.py

# 3. 통합 테스트 (주 1회)
python scripts/test_integration_phase1_2.py
```

**예상 결과**:
- 데이터 검증: 0 에러
- 단위 테스트: 20/20 통과
- 통합 테스트: 8/8 체크리스트 통과

### 오후 체크 (17:00)

1. 로그 파일 확인
   ```bash
   # 최신 로그 확인
   Get-Content logs/system_$(Get-Date -Format "yyyyMMdd").log -Tail 100
   ```

2. 에러/경고 확인
   - `[ERROR]` 태그 검색
   - `[WARN]` 태그 검색 (가용 자원 없음 경고 확인)

3. 성능 지표 확인
   - COA 평가 평균 시간
   - 관련성 점수 분포 (0.5~0.9 범위)
   - 자원 점수 분포 (0.3~1.0 범위)

---

## 데이터 관리

### 신규 위협 추가

**파일**: `data_lake/위협상황.xlsx`

1. 새 행 추가
2. 필수 컬럼 입력:
   - `situation_id`: MSN### 또는 THR### 형식
   - `위협유형`: 침투, 포격, 기습공격, 사이버, 전면공격, 국지도발 중 선택
3. 검증:
   ```bash
   python scripts/validate_data_quality.py
   ```

### 신규 시나리오 자원 추가

**파일**: `data_lake/가용자원.xlsx`

**템플릿**:
```
situation_id | resource_name | available_quantity | status
MSN009      | 포병대대      | 12                | 사용가능
MSN009      | 보병여단      | 2000              | 사용가능
MSN009      | 전차대대      | 24                | 정비중
```

**상태 값**:
- `사용가능`: 즉시 투입 가능
- `정비중`: 50% 가용성
- `제한적`: 부분 가용
- `미보유`: 0% 가용성

### COA Library 데이터 입력

**파일**: `data_lake/COA_Library.xlsx`

**신규 컬럼 입력 가이드**:

1. **적합위협유형**: 쉼표로 구분
   ```
   예: "침투, 기습공격"
   ```

2. **자원우선순위**: 괄호로 우선순위 표시
   ```
   예: "포병대대(필수), 보병여단(필수), 공격헬기(권장), 공병대대(선택)"
   ```
   - 필수: 반드시 있어야 함 (가중치 1.0)
   - 권장: 있으면 좋음 (가중치 0.6)
   - 선택: 선택사항 (가중치 0.3)

3. **전장환경_최적조건**:
   ```
   예: "가시거리>5km, 주간작전, 평지지형"
   ```

4. **연계방책**:
   ```
   예: "COA_DEF_001(선행), COA_DEF_003(동시)"
   ```

5. **적대응전술**:
   ```
   예: "우회기동, 화력집중, 전자전 교란"
   ```

---

## 모니터링 및 검증

### 자동 검증 실행

```bash
# 매일 자동 실행 (Windows 작업 스케줄러)
python scripts/validate_data_quality.py > logs/validation_$(Get-Date -Format "yyyyMMdd").log
```

### 수동 검증

#### 1. 관련성 점수 검증

```python
from core_pipeline.relevance_mapper import RelevanceMapper

mapper = RelevanceMapper()
stats = mapper.get_type_mapping_stats()

print(f"총 매핑: {stats['total_mappings']}")  # 42개 확인
print(f"평균 관련성: {stats['avg_relevance']:.2f}")  # 0.6~0.7
```

#### 2. 자원 우선순위 검증

```python
from core_pipeline.resource_priority_parser import ResourcePriorityParser

parser = ResourcePriorityParser()
result = parser.parse_resource_priority("포병대대(필수), 공격헬기(권장)")

# 정상: [{'resource': '포병대대', 'priority': '필수', 'weight': 1.0}, ...]
print(result)
```

#### 3. Situation ID 검증

```python
from core_pipeline.situation_id_mapper import SituationIDMapper

# THREAT001 → THR001 변환 확인
normalized = SituationIDMapper._normalize_id('THREAT001')
print(normalized)  # THR001

# 검증
is_valid = SituationIDMapper.is_valid_situation_id('MSN008')
print(is_valid)  # True
```

---

## 문제 해결

### 문제 1: 관련성 점수가 0.00으로 표시

**증상**:
```log
[INFO] 체인 점수 계산: 관련성=0.00
```

**원인**:
- RelevanceMapper 초기화 실패
- COA 타입 또는 위협 유형 누락

**해결**:
```bash
# 1. RelevanceMapper 초기화 확인
python core_pipeline/relevance_mapper.py

# 2. 데이터 검증
python scripts/validate_data_quality.py

# 3. COA 타입 확인
# context에 'coa_type'과 'threat_type'이 있는지 확인
```

### 문제 2: 자원 점수가 항상 0.2 (fallback)

**증상**:
```log
[WARN] 필요한 자원이 있지만 가용 자원이 없음. 낮은 점수(0.2) 사용
```

**원인**:
- `가용자원.xlsx`에 해당 시나리오 데이터 없음
- `resource_priority_string` 누락

**해결**:
1. `가용자원.xlsx`에 시나리오 자원 추가
2. COA Library에 `자원우선순위` 입력
3. Context에 두 정보 모두 전달 확인

### 문제 3: Situation ID 불일치

**증상**:
```log
[WARN] 상황 THREAT001에 대한 가용 자원을 찾을 수 없습니다.
```

**원인**:
- THREAT001과 THR001 표기 불일치

**해결**:
```python
# SituationIDMapper 사용
from core_pipeline.situation_id_mapper import SituationIDMapper

# 자동 정규화
situation_id = SituationIDMapper.extract_situation_id(situation_info)
# THREAT001 → THR001로 자동 변환
```

### 문제 4: 테스트 실패

**증상**:
```
FAILED test_defense_infiltration_relevance
```

**원인**:
- 데이터 테이블 손상 또는 누락
- 파일 경로 문제

**해결**:
```bash
# 1. 데이터 재생성
python scripts/create_improvement_tables.py

# 2. 테스트 재실행
python tests/test_core_improvements.py -v
```

---

## 성능 최적화

### RelevanceMapper 캐싱

RelevanceMapper는 초기화 시 Excel 파일을 로드하므로, 반복 사용 시 인스턴스 재사용:

```python
# ❌ 비효율적
for coa in coas:
    mapper = RelevanceMapper()  # 매번 로드
    score = mapper.get_relevance_score(...)

# ✅ 효율적
mapper = RelevanceMapper()  # 한 번만 로드
for coa in coas:
    score = mapper.get_relevance_score(...)
```

### 대량 COA 평가 최적화

```python
# COAScorer 인스턴스 재사용
scorer = COAScorer(coa_type="defense")

for coa in coa_list:
    context = prepare_context(coa)
    result = scorer.calculate_score(context)
```

### 로그 레벨 조정

프로덕션 환경에서는 INFO 레벨만 유지:

```python
import logging
logging.basicConfig(level=logging.INFO)  # DEBUG 제거
```

---

## 백업 및 복구

### 일일 백업

```powershell
# 데이터 테이블 백업 (매일 02:00)
$date = Get-Date -Format "yyyyMMdd"
Copy-Item data_lake\*.xlsx backup\$date\
```

### 복구

```powershell
# 특정 날짜로 복구
$date = "20251227"
Copy-Item backup\$date\*.xlsx data_lake\ -Force
```

---

## 연락처 및 지원

**기술 지원**: COA Agent Platform Team  
**긴급 연락**: (내부 문의)  
**문서 위치**: `logs/` 디렉토리

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-12-27  
**검토 주기**: 분기 1회
