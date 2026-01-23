# 위협 유형 데이터 아키텍처 문제 분석 및 개선방향

**작성일**: 2025-12-27  
**이슈**: 위협 유형 컬럼 중복 및 참조 무결성 문제

---

## 🔴 현재 문제점

### 1. **데이터 중복 및 불일치**

#### 위협상황.xlsx
```
컬럼:
- 위협유형 (삭제됨) 
- 위협유형코드 (현재 사용 중)

데이터 예시:
THR001: 위협유형코드 = "침투"
THR006: 위협유형코드 = "공중위협"
```

#### 방책유형_위협유형_관련성.xlsx
```
컬럼:
- threat_type

데이터 예시:
threat_type = ["침투", "포격", "기습공격", "사이버", "전면공격", "국지도발", "공중위협"]
```

### 2. **참조 무결성 문제**

```
위협상황.xlsx (위협유형코드)  ←→  방책유형_위협유형_관련성.xlsx (threat_type)
         ↓                                    ↓
    "공중위협"                            "공중위협" ✅ (방금 추가)
    "침투"                                "침투" ✅
    "사이버"                              "사이버" ✅
    
문제: 두 테이블 간 값이 수동으로 관리되어 불일치 가능성 높음
```

### 3. **아키텍처 문제점**

1. **단일 진실 공급원(Single Source of Truth) 부재**
   - 위협 유형이 여러 곳에 중복 정의됨
   - 마스터 데이터 테이블 없음

2. **참조 무결성 검증 메커니즘 없음**
   - 위협상황.xlsx의 위협유형코드가 관련성 테이블에 존재하는지 검증 안 됨
   - 새로운 위협 추가 시 수동으로 관련성 테이블 업데이트 필요

3. **데이터 정규화 부족**
   - 위협 유형이 코드 테이블로 분리되지 않음
   - 중복 데이터 입력 및 오타 가능성

4. **온톨로지 생성 로직의 가정**
   - 코드가 '위협유형코드' 컬럼을 읽지만, 이 값이 관련성 테이블과 일치한다고 가정
   - 런타임에 불일치 발견 시 처리 로직 없음

---

## 🎯 개선 방향

### 방안 1: **마스터 데이터 테이블 도입** (권장 ⭐)

#### 새 파일: `위협유형_마스터.xlsx`
```
위협유형코드 | 위협유형명 | 위협카테고리 | 설명
-----------|----------|------------|-----
THR_TYPE_001 | 침투 | 지상 | 적 보병의 침투 공격
THR_TYPE_002 | 포격 | 화력 | 적 포병의 화력 공격
THR_TYPE_003 | 기습공격 | 지상 | 적의 기습 공격
THR_TYPE_004 | 사이버 | 비전통 | 사이버 공격
THR_TYPE_005 | 공중위협 | 공중 | 적 항공기 위협
THR_TYPE_006 | 전면공격 | 지상 | 적의 전면 공격
THR_TYPE_007 | 국지도발 | 국지 | 국지적 도발
```

#### 데이터 관계
```
위협유형_마스터.xlsx (마스터)
    ↓ (FK: 위협유형코드)
    ├─→ 위협상황.xlsx (위협유형코드)
    └─→ 방책유형_위협유형_관련성.xlsx (threat_type)
```

#### 장점
- ✅ 단일 진실 공급원
- ✅ 참조 무결성 검증 가능
- ✅ 새 위협 추가 시 한 곳만 수정
- ✅ 위협 유형 메타데이터 관리 용이

#### 구현
```python
# 1. 마스터 테이블 생성
master_df = pd.DataFrame({
    '위협유형코드': ['침투', '포격', '기습공격', '사이버', '공중위협', '전면공격', '국지도발'],
    '위협카테고리': ['지상', '화력', '지상', '비전통', '공중', '지상', '국지'],
    '설명': [...]
})

# 2. 참조 무결성 검증 함수
def validate_threat_type_integrity():
    master = pd.read_excel('data_lake/위협유형_마스터.xlsx')
    threats = pd.read_excel('data_lake/위협상황.xlsx')
    relevance = pd.read_excel('data_lake/방책유형_위협유형_관련성.xlsx')
    
    master_types = set(master['위협유형코드'])
    threat_types = set(threats['위협유형코드'].dropna())
    relevance_types = set(relevance['threat_type'].dropna())
    
    # 검증
    invalid_threats = threat_types - master_types
    invalid_relevance = relevance_types - master_types
    
    if invalid_threats:
        raise ValueError(f"위협상황에 미정의 위협 유형: {invalid_threats}")
    if invalid_relevance:
        raise ValueError(f"관련성 테이블에 미정의 위협 유형: {invalid_relevance}")
```

---

### 방안 2: **자동 동기화 메커니즘** (보완책)

#### 온톨로지 생성 시 자동 검증 및 동기화
```python
def sync_threat_types():
    """위협상황.xlsx의 위협유형코드를 기준으로 관련성 테이블 자동 업데이트"""
    
    # 1. 위협상황에서 모든 위협 유형 추출
    threats_df = pd.read_excel('data_lake/위협상황.xlsx')
    unique_types = threats_df['위협유형코드'].dropna().unique()
    
    # 2. 관련성 테이블 로드
    relevance_df = pd.read_excel('data_lake/방책유형_위협유형_관련성.xlsx')
    existing_types = set(relevance_df['threat_type'].unique())
    
    # 3. 누락된 위협 유형 찾기
    missing_types = set(unique_types) - existing_types
    
    # 4. 기본 관련성 매핑 자동 생성
    if missing_types:
        new_mappings = []
        for threat_type in missing_types:
            for coa_type in ['Defense', 'Offensive', 'CounterAttack', 'Maneuver', 
                            'Deterrence', 'Preemptive', 'InformationOps']:
                new_mappings.append({
                    'coa_type': coa_type,
                    'threat_type': threat_type,
                    'base_relevance': 0.50,  # 기본값
                    'description': f'{coa_type} 방책과 {threat_type} 위협 (자동 생성)'
                })
        
        # 5. 추가 및 저장
        new_df = pd.DataFrame(new_mappings)
        updated_df = pd.concat([relevance_df, new_df], ignore_index=True)
        updated_df.to_excel('data_lake/방책유형_위협유형_관련성.xlsx', index=False)
        
        print(f"⚠️ 자동 동기화: {len(missing_types)}개 위협 유형 추가됨")
```

---

### 방안 3: **컬럼명 통일** (단기 해결책)

#### 현재 불일치
```
위협상황.xlsx: 위협유형코드
방책유형_위협유형_관련성.xlsx: threat_type
```

#### 통일안
```
모든 테이블: 위협유형 (또는 threat_type)
```

#### 구현
```python
# 위협상황.xlsx 수정
threats_df = pd.read_excel('data_lake/위협상황.xlsx')
threats_df.rename(columns={'위협유형코드': '위협유형'}, inplace=True)

# 관련성 테이블 수정
relevance_df = pd.read_excel('data_lake/방책유형_위협유형_관련성.xlsx')
relevance_df.rename(columns={'threat_type': '위협유형'}, inplace=True)

# 코드 수정
# ontology_manager_enhanced.py 라인 1680
threat_type = row.get('위협유형') or row.get('threat_type')
```

---

## 📊 권장 구현 순서

### Phase 1: 즉시 조치 (단기)
1. ✅ **공중위협 매핑 추가** (완료)
2. **컬럼명 통일**
   - `위협유형코드` → `위협유형`
   - `threat_type` → `위협유형`
3. **코드 업데이트**
   - 온톨로지 생성 로직 수정
   - RelevanceMapper 수정

### Phase 2: 구조 개선 (중기)
1. **위협유형_마스터.xlsx 생성**
2. **참조 무결성 검증 함수 구현**
3. **온톨로지 생성 시 자동 검증 추가**

### Phase 3: 자동화 (장기)
1. **자동 동기화 메커니즘 구현**
2. **데이터 품질 모니터링 대시보드**
3. **CI/CD 파이프라인에 검증 추가**

---

## 🔧 즉시 적용 가능한 코드

### 1. 참조 무결성 검증 스크립트
```python
# scripts/validate_threat_type_integrity.py
import pandas as pd
from pathlib import Path

def validate():
    threats = pd.read_excel('data_lake/위협상황.xlsx')
    relevance = pd.read_excel('data_lake/방책유형_위협유형_관련성.xlsx')
    
    threat_types = set(threats['위협유형코드'].dropna().unique())
    relevance_types = set(relevance['threat_type'].dropna().unique())
    
    missing_in_relevance = threat_types - relevance_types
    extra_in_relevance = relevance_types - threat_types
    
    print("=" * 80)
    print("위협 유형 참조 무결성 검증")
    print("=" * 80)
    print(f"\n위협상황 위협 유형: {sorted(threat_types)}")
    print(f"\n관련성 테이블 위협 유형: {sorted(relevance_types)}")
    
    if missing_in_relevance:
        print(f"\n⚠️ 관련성 테이블에 누락: {missing_in_relevance}")
    if extra_in_relevance:
        print(f"\n⚠️ 관련성 테이블에 불필요: {extra_in_relevance}")
    
    if not missing_in_relevance and not extra_in_relevance:
        print("\n✅ 참조 무결성 정상")
    
    return missing_in_relevance, extra_in_relevance

if __name__ == "__main__":
    validate()
```

### 2. 온톨로지 생성 전 자동 검증
```python
# ontology_manager_enhanced.py에 추가
def generate_instances(self, data, ...):
    # 기존 코드 전에 추가
    self._validate_threat_type_integrity(data)
    
    # 기존 generate_instances 로직...

def _validate_threat_type_integrity(self, data):
    """위협 유형 참조 무결성 검증"""
    if '위협상황' not in data:
        return
    
    threats_df = data['위협상황']
    threat_types = set(threats_df['위협유형코드'].dropna().unique())
    
    # 관련성 테이블 로드
    relevance_file = Path(self.data_lake_path) / "방책유형_위협유형_관련성.xlsx"
    if relevance_file.exists():
        relevance_df = pd.read_excel(relevance_file)
        relevance_types = set(relevance_df['threat_type'].dropna().unique())
        
        missing = threat_types - relevance_types
        if missing:
            safe_print(f"⚠️ 경고: 관련성 테이블에 누락된 위협 유형: {missing}")
            safe_print("   → 기본 관련성 매핑을 자동 생성합니다.")
            self._auto_generate_missing_mappings(missing, relevance_file)

def _auto_generate_missing_mappings(self, missing_types, relevance_file):
    """누락된 위협 유형에 대한 기본 매핑 자동 생성"""
    # 구현...
```

---

## 📈 기대 효과

### 즉시
- ✅ 공중위협 정상 작동
- ✅ 데이터 불일치 감지

### 중기
- ✅ 새 위협 추가 시 자동 동기화
- ✅ 데이터 품질 향상
- ✅ 유지보수 용이성 증가

### 장기
- ✅ 확장 가능한 데이터 아키텍처
- ✅ 자동화된 데이터 검증
- ✅ 운영 안정성 향상

---

## 🎯 결론

**핵심 문제**: 위협 유형 데이터가 여러 곳에 중복 정의되어 있고, 참조 무결성 검증 메커니즘이 없음

**권장 해결책**:
1. **단기**: 컬럼명 통일 + 자동 검증
2. **중기**: 마스터 데이터 테이블 도입
3. **장기**: 자동 동기화 메커니즘

**다음 단계**: 위 스크립트를 실행하여 현재 불일치 상태를 확인하고, 필요한 조치를 결정
