# COP 시각화 수정 사항

## 수정 일자: 2025-01-XX

### 문제점
- 선택한 상황정보(위협)가 지도에 시각화되어야 하는데 현재는 모든 적정보가 표기되어 있고 선택된 위협정보는 식별이 안됨

### 수정 내용

#### 1. 선택된 위협만 표시하도록 필터링

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedThreat`가 있을 때 선택된 위협만 표시하도록 필터링 추가
- 선택되지 않은 위협은 마커 목록에서 제외

```typescript
// Add hostile units from threats
threats.forEach((t, idx) => {
    const isSelected = selectedThreat?.threat_id === t.threat_id;
    
    // selectedThreat가 있고 현재 위협이 선택되지 않았으면 표시하지 않음
    if (selectedThreat && !isSelected) {
        return; // 선택된 위협만 표시
    }
    // ... 마커 생성
});
```

#### 2. 선택된 위협 마커 강조 효과

**파일**: `frontend/src/lib/milsymbol-wrapper.ts`

**변경 사항**:
- 선택된 마커에 외곽 강조 원 추가
- 펄스 애니메이션 지원

**파일**: `frontend/src/index.css`

**변경 사항**:
- 선택된 위협 마커 펄스 애니메이션 CSS 추가
- 강조 스타일 (drop-shadow, z-index)

```css
@keyframes threatPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.1);
  }
}

.milsymbol-icon.selected-threat {
  filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.8));
  z-index: 10000 !important;
}
```

#### 3. 선택된 위협의 영향 범위만 표시

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedThreat`가 있을 때 선택된 위협의 영향 범위만 표시

```typescript
{layerToggle.threatInfluence && markers
    .filter(m => {
        if (m.type !== 'HOSTILE' || m.threat_level === undefined) return false;
        // selectedThreat가 있으면 선택된 위협만 표시
        if (selectedThreat) {
            return m.selected === true;
        }
        return true;
    })
    .map((marker) => {
        // 영향 범위 Circle 생성
    })}
```

#### 4. 배경 적군 숨김

**파일**: `frontend/src/components/TacticalMap.tsx`

**변경 사항**:
- `selectedThreat`가 있을 때 배경 적군은 표시하지 않음 (선택된 위협에 집중)

```typescript
// 배경 적군 부대 추가
if (!selectedThreat) {
    enemyUnits.forEach((enemy) => {
        // 배경 적군 마커 추가
    });
}
```

#### 5. situationInfo 변경 시 selectedThreat 자동 설정

**파일**: `frontend/src/pages/CommandControlPage.tsx`

**변경 사항**:
- `situationInfo`에 `selected_threat_id`가 있으면 자동으로 `selectedThreat` 설정

```typescript
useEffect(() => {
    if (situationInfo && situationInfo.selected_threat_id) {
        const threatId = situationInfo.selected_threat_id;
        const threat = threats.find(t => t.threat_id === threatId);
        if (threat && (!selectedThreat || selectedThreat.threat_id !== threatId)) {
            setSelectedThreat(threat);
        }
    }
}, [situationInfo, threats, selectedThreat]);
```

### 테스트 방법

1. **위협 선택 테스트**:
   - SituationInputPanel에서 위협 선택
   - 지도에 선택된 위협만 표시되는지 확인
   - 선택된 위협 마커에 펄스 효과 확인
   - 선택된 위협의 영향 범위만 표시되는지 확인

2. **위협 해제 테스트**:
   - 위협 선택 해제
   - 모든 위협이 다시 표시되는지 확인

### 예상 결과

- ✅ 선택된 위협만 지도에 표시
- ✅ 선택된 위협 마커에 펄스 효과 및 강조 스타일 적용
- ✅ 선택된 위협의 영향 범위만 표시
- ✅ 배경 적군은 선택된 위협이 있을 때 숨김
- ✅ situationInfo 변경 시 자동으로 selectedThreat 설정
