# 필요 자원 섹션 차이점 분석

## 현재 상황

모달에서 두 가지 자원 관련 섹션이 있습니다:

### 1. "필요 자원 목록" (COAExecutionPlanPanel.tsx)

**위치**: `COAExecutionPlanPanel` 컴포넌트 내부 (89-117줄)

**특징**:
- **데이터 소스**: 하드코딩된 시뮬레이션 데이터 (`extractRequiredResources` 함수)
- **자원 유형**: 고정된 4가지 유형
  - 인력 (자원 점수 기반 동적 계산)
  - 장비 (고정값)
  - 보급품 (고정값)
  - 통신장비 (고정값)
- **표시 정보**:
  - 필요량
  - 가용량
  - 충족도 (충분/부분/부족) - 인력만 동적, 나머지는 고정
- **현재 상태**: 부족한 자원이 표기됨

**코드 위치**: `frontend/src/components/COAExecutionPlanPanel.tsx:265-290`

```typescript
function extractRequiredResources(recommendation: COASummary): Record<string, any> {
    const resourceScore = recommendation.score_breakdown?.resources || 0;
    
    return {
        인력: {
            required: '1개 대대',
            available: '1개 대대',
            status: resourceScore > 0.7 ? 'sufficient' : resourceScore < 0.5 ? 'insufficient' : 'partial'
        },
        // ... 고정된 데이터
    };
}
```

### 2. "필요 자원" (COADetailModal.tsx)

**위치**: `COADetailModal` 컴포넌트 내부 (362-386줄)

**특징**:
- **데이터 소스**: `coa.required_resources` 배열 (백엔드에서 온톨로지 추출)
- **자원 정보**: 온톨로지에서 `ns:requiresResource` 또는 `ns:필요자원` 관계로 추출
- **표시 정보**:
  - 자원명 (`resource.name` 또는 `resource.resource_id`)
  - 자원 유형 (`resource.type`)
- **현재 상태**: "정보없음" (데이터가 없음)

**코드 위치**: `frontend/src/components/COADetailModal.tsx:362-386`

```typescript
{coa.required_resources && coa.required_resources.length > 0 ? (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {coa.required_resources.map((resource: any, idx: number) => (
            // 자원 카드 표시
        ))}
    </div>
) : (
    <p className="text-gray-500 dark:text-gray-400 italic">필요 자원 정보 없음</p>
)}
```

## 차이점 요약

| 항목 | 필요 자원 목록 | 필요 자원 |
|------|---------------|----------|
| **데이터 소스** | 하드코딩된 시뮬레이션 데이터 | 온톨로지에서 추출한 실제 데이터 |
| **자원 유형** | 고정된 4가지 (인력, 장비, 보급품, 통신장비) | 온톨로지에 정의된 실제 자원 |
| **가용량 정보** | 포함 (시뮬레이션) | 없음 (필요량만) |
| **충족도 분석** | 포함 (인력만 동적) | 없음 |
| **현재 상태** | 부족한 자원 표기됨 | 정보없음 |

## 문제점

1. **중복**: 두 섹션이 비슷한 목적을 가지고 있으나 다른 데이터를 표시
2. **데이터 불일치**: "필요 자원 목록"은 시뮬레이션 데이터, "필요 자원"은 실제 데이터
3. **정보 부족**: "필요 자원"에 실제 데이터가 없어 "정보없음" 상태
4. **혼란**: 사용자가 두 섹션의 차이를 이해하기 어려움

## 개선 방안

### 옵션 1: 두 섹션 통합 (권장)

**방법**: "필요 자원" 섹션을 제거하고 "필요 자원 목록"에 실제 온톨로지 데이터를 통합

**장점**:
- 중복 제거
- 일관된 정보 표시
- 실제 데이터 활용

**구현**:
1. `extractRequiredResources` 함수를 수정하여 `coa.required_resources`를 우선 사용
2. 온톨로지 데이터가 없을 때만 시뮬레이션 데이터 사용
3. 가용량 정보는 별도 API나 상황 정보에서 가져오기

### 옵션 2: 섹션 역할 명확화

**방법**: 두 섹션의 역할을 명확히 구분

**구현**:
- **"필요 자원 목록"**: 자원 가용성 분석 (필요량 vs 가용량, 충족도)
- **"필요 자원"**: 온톨로지에서 추출한 실제 자원 목록 (필요량만)

**표시 방식**:
- "필요 자원 목록" → "자원 가용성 분석"으로 제목 변경
- "필요 자원" → "필요 자원 (온톨로지)"로 제목 변경

### 옵션 3: "필요 자원" 섹션 제거

**방법**: "필요 자원" 섹션을 제거하고 "필요 자원 목록"만 유지

**장점**:
- 단순화
- 중복 제거

**단점**:
- 실제 온톨로지 데이터 표시 불가

## 권장 사항

**옵션 1 (통합)**을 권장합니다:
1. 실제 온톨로지 데이터를 우선 사용
2. 가용량 정보는 상황 정보(`situation_info.resource_availability`)에서 가져오기
3. 온톨로지 데이터가 없을 때만 시뮬레이션 데이터 사용
4. "필요 자원" 섹션 제거

이렇게 하면:
- 중복 제거
- 실제 데이터 활용
- 일관된 정보 표시
- 사용자 혼란 감소
