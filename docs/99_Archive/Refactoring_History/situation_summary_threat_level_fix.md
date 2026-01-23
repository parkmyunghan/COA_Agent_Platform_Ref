# 상황요약 위협수준 NaN% 문제 수정

## 문제점 분석

### 현재 상태
- 상황요약(SituationSummaryPanel)에서 위협수준이 "NaN%"로 표시됨
- `SituationInputPanel`의 위협 수준 슬라이더 레이블도 NaN% 표시 가능

### 원인
1. **데이터 타입 불일치**:
   - `situation.threat_level`이 문자열로 저장될 수 있음 (예: "0.7", "70", "70%")
   - 숫자 연산(`Math.round(situation.threat_level * 100)`) 수행 시 NaN 발생

2. **파싱 로직 누락**:
   - `SituationSummaryPanel.tsx`에서 `threat_level`을 숫자로 가정
   - 문자열 형식의 `threat_level` 처리 로직 없음

3. **다른 컴포넌트와의 불일치**:
   - `SituationBanner.tsx`와 `CommandControlPage.tsx`에는 파싱 로직이 있음
   - `SituationSummaryPanel.tsx`와 `SituationInputPanel.tsx`에는 파싱 로직 없음

## 수정 내용

### 1. SituationSummaryPanel.tsx: 위협 수준 파싱 로직 추가

**파일**: `frontend/src/components/SituationSummaryPanel.tsx`

**변경 사항**:
- `threat_level` 파싱 로직 추가
- 문자열 형식 지원 ("0.7", "70", "70%")
- NaN 방지

```typescript
{(() => {
    // 위협 수준 파싱 (문자열일 수 있음)
    const threatLevelRaw = situation.threat_level || situation.위협수준;
    if (threatLevelRaw === undefined || threatLevelRaw === null) {
        return null;
    }
    
    let threatLevel: number = 0.7;
    if (typeof threatLevelRaw === 'string') {
        // 문자열인 경우 파싱 (예: "0.7", "70", "70%")
        const cleaned = threatLevelRaw.replace('%', '').trim();
        const parsed = parseFloat(cleaned);
        if (!isNaN(parsed)) {
            // 100보다 크면 백분율로 간주 (예: 70 -> 0.7)
            threatLevel = parsed > 1 ? parsed / 100 : parsed;
        }
    } else {
        threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
    }
    
    const threatLevelPercent = Math.round(threatLevel * 100);
    
    return (
        <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">위협 수준:</span>
            <span className={`font-semibold ${
                threatLevel >= 0.8 ? 'text-red-600 dark:text-red-400' :
                threatLevel >= 0.5 ? 'text-yellow-600 dark:text-yellow-400' :
                'text-green-600 dark:text-green-400'
            }`}>
                {threatLevelPercent}%
            </span>
        </div>
    );
})()}
```

### 2. SituationInputPanel.tsx: 위협 수준 표시 및 슬라이더 값 파싱

**파일**: `frontend/src/components/SituationInputPanel.tsx`

**변경 사항**:
- 위협 수준 레이블 파싱 로직 추가
- 슬라이더 초기값 파싱 로직 추가
- 위협 수준 배지 조건부 표시 파싱 로직 추가

```typescript
// 레이블 표시
<Label className="text-sm">위협 수준: {(() => {
    const threatLevelRaw = situation.threat_level || situation.위협수준;
    if (threatLevelRaw === undefined || threatLevelRaw === null) {
        return '70%';
    }
    
    let threatLevel: number = 0.7;
    if (typeof threatLevelRaw === 'string') {
        const cleaned = String(threatLevelRaw).replace('%', '').trim();
        const parsed = parseFloat(cleaned);
        if (!isNaN(parsed)) {
            threatLevel = parsed > 1 ? parsed / 100 : parsed;
        }
    } else {
        threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
    }
    
    return `${Math.round(threatLevel * 100)}%`;
})()}</Label>

// 슬라이더 값
<Slider
    value={[(() => {
        const threatLevelRaw = situation.threat_level || situation.위협수준;
        if (threatLevelRaw === undefined || threatLevelRaw === null) {
            return 70;
        }
        
        let threatLevel: number = 0.7;
        if (typeof threatLevelRaw === 'string') {
            const cleaned = String(threatLevelRaw).replace('%', '').trim();
            const parsed = parseFloat(cleaned);
            if (!isNaN(parsed)) {
                threatLevel = parsed > 1 ? parsed / 100 : parsed;
            }
        } else {
            threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
        }
        
        return Math.round(threatLevel * 100);
    })()]}
    // ...
/>

// 배지 표시
<div className="flex gap-2 text-xs">
    {(() => {
        const threatLevelRaw = situation.threat_level || situation.위협수준;
        if (threatLevelRaw === undefined || threatLevelRaw === null) {
            return null;
        }
        
        let threatLevel: number = 0.7;
        if (typeof threatLevelRaw === 'string') {
            const cleaned = String(threatLevelRaw).replace('%', '').trim();
            const parsed = parseFloat(cleaned);
            if (!isNaN(parsed)) {
                threatLevel = parsed > 1 ? parsed / 100 : parsed;
            }
        } else {
            threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
        }
        
        if (threatLevel >= 0.8) {
            return <Badge variant="destructive">높음</Badge>;
        } else if (threatLevel >= 0.5) {
            return <Badge variant="default">중간</Badge>;
        } else {
            return <Badge variant="secondary">낮음</Badge>;
        }
    })()}
</div>
```

## 위협 수준 파싱 규칙

| 입력 형식 | 파싱 결과 | 예시 |
|----------|----------|------|
| `"0.7"` | `0.7` | 정상 |
| `"70"` | `0.7` (100으로 나눔) | 정상 |
| `"70%"` | `0.7` (%, 100으로 나눔) | 정상 |
| `0.7` (숫자) | `0.7` | 정상 |
| `null` / `undefined` | `0.7` (기본값) 또는 숨김 | 정상 |
| `"invalid"` | `0.7` (기본값) | 정상 |

## 수정된 파일

1. `frontend/src/components/SituationSummaryPanel.tsx`
   - 위협 수준 파싱 로직 추가
   - NaN 방지

2. `frontend/src/components/SituationInputPanel.tsx`
   - 위협 수준 레이블 파싱 로직 추가
   - 슬라이더 초기값 파싱 로직 추가
   - 배지 조건부 표시 파싱 로직 추가

## 테스트 방법

### 1. 상황요약 위협수준 표시 테스트
1. 상황정보 설정에서 위협 선택 또는 수동 입력
2. 상황요약 패널 확인
3. 위협 수준이 올바르게 표시되는지 확인:
   - `70%` ✅
   - `NaN%` ❌ (수정 전)

### 2. 위협 수준 슬라이더 테스트
1. 상황정보 설정에서 수동 입력 모드 선택
2. 위협 수준 슬라이더 확인
3. 레이블과 슬라이더 값이 올바르게 표시되는지 확인

### 3. 다양한 데이터 형식 테스트
1. `threat_level`이 문자열인 경우 ("0.7", "70", "70%")
2. `threat_level`이 숫자인 경우 (0.7)
3. `threat_level`이 null/undefined인 경우

## 예상 결과

- ✅ 상황요약에 올바른 위협 수준 표시 (예: "70%")
- ✅ 위협 수준이 NaN%로 표시되지 않음
- ✅ 다양한 위협 수준 형식 지원 (문자열, 숫자, 백분율)
- ✅ 위협 수준 슬라이더가 올바른 초기값 표시

## 참고 사항

- `threat_level`은 다양한 형식으로 저장될 수 있으므로 항상 파싱 필요
- `SituationBanner.tsx`와 `CommandControlPage.tsx`에는 이미 파싱 로직이 있음
- 이제 모든 컴포넌트에서 일관된 파싱 로직 사용
