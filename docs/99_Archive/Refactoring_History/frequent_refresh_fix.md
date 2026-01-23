# 프론트엔드 자주 새로고침 문제 해결

## 문제점 분석

### 증상
- 프론트엔드 페이지가 자주 새로고침되는 것처럼 보임
- 설정값을 변경하거나 테스트 중에 화면이 계속 리렌더링됨

### 원인
1. **`SystemDataContext.tsx`의 `refetch` 함수가 매번 새로 생성됨**
   - `fetchData` 함수가 일반 함수로 선언되어 매 렌더링마다 새로 생성
   - `refetch: fetchData`로 전달되어 `refetch`도 매번 변경됨
   - Context의 `value` 객체가 매번 새로 생성되어 하위 컴포넌트들이 리렌더링됨

2. **`Header.tsx`의 `useEffect`가 `refetch` 변경 시마다 재실행됨**
   - `useEffect`의 의존성 배열에 `refetch`가 포함되어 있음
   - `refetch`가 변경될 때마다 `useEffect`가 재실행되고 interval이 재생성됨
   - 이로 인해 불필요한 새로고침이 발생하는 것처럼 보임

## 수정 내용

### 1. SystemDataContext.tsx - useCallback으로 메모이제이션

**변경 사항**:
- `useCallback` import 추가
- `fetchData` 함수를 `useCallback`으로 메모이제이션
- 의존성 배열을 빈 배열로 설정하여 한 번만 생성되도록 함

```typescript
import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';

// ...

// fetchData를 useCallback으로 메모이제이션하여 refetch가 안정적으로 유지되도록 함
const fetchData = useCallback(async () => {
    // 이미 요청 중이면 중복 요청 방지
    if (isFetchingRef.current) {
        return;
    }
    
    try {
        isFetchingRef.current = true;
        setLoading(true);
        const [missionsRes, threatsRes, healthRes] = await Promise.all([
            api.get<MissionListResponse>('/data/missions'),
            api.get<ThreatListResponse>('/data/threats'),
            api.get<SystemHealthResponse>('/system/health')
        ]);

        setMissions(missionsRes.data.missions);
        setThreats(threatsRes.data.threats);
        setHealth(healthRes.data);
        setError(null);
        hasFetchedRef.current = true;
    } catch (err: any) {
        setError('데이터를 불러오는데 실패했습니다.');
        console.error(err);
    } finally {
        setLoading(false);
        isFetchingRef.current = false;
    }
}, []); // 의존성 배열이 비어있어서 한 번만 생성됨
```

### 2. Header.tsx - useRef로 안정적인 참조 사용

**변경 사항**:
- `useRef` import 추가
- `refetch`를 `useRef`로 감싸서 안정적인 참조로 유지
- `useEffect`의 의존성 배열에서 `refetch` 제거

```typescript
import { useEffect, useRef } from 'react';

// ...

export const Header: React.FC<HeaderProps> = () => {
    const location = useLocation();
    const { health, refetch } = useSystemData();
    
    // refetch를 useRef로 안정적인 참조로 유지하여 useEffect가 불필요하게 재실행되지 않도록 함
    const refetchRef = useRef(refetch);
    useEffect(() => {
        refetchRef.current = refetch;
    }, [refetch]);

    // Dashboard 페이지일 때 주기적으로 health 갱신 (30초마다)
    useEffect(() => {
        if (location.pathname === '/dashboard') {
            const interval = setInterval(() => {
                refetchRef.current(); // useRef를 통해 최신 refetch 함수 호출
            }, 30000); // 30초마다 갱신
            return () => clearInterval(interval);
        }
    }, [location.pathname]); // refetch를 의존성 배열에서 제거
```

## 수정 효과

### Before (수정 전)
1. `SystemDataContext`가 리렌더링될 때마다 `fetchData` 함수가 새로 생성
2. `refetch`가 변경되어 Context의 `value` 객체가 새로 생성
3. `Header` 컴포넌트가 리렌더링되고 `useEffect`가 재실행
4. interval이 계속 재생성되어 불필요한 새로고침 발생

### After (수정 후)
1. `fetchData`가 `useCallback`으로 메모이제이션되어 한 번만 생성
2. `refetch`가 안정적으로 유지되어 Context의 `value` 객체가 불필요하게 재생성되지 않음
3. `Header`의 `useEffect`가 `location.pathname` 변경 시에만 실행
4. interval이 안정적으로 유지되어 불필요한 새로고침 제거

## 수정된 파일

1. `frontend/src/contexts/SystemDataContext.tsx`
   - `useCallback` import 추가
   - `fetchData` 함수를 `useCallback`으로 메모이제이션

2. `frontend/src/components/Header.tsx`
   - `useRef` import 추가
   - `refetch`를 `useRef`로 안정적인 참조로 유지
   - `useEffect`의 의존성 배열에서 `refetch` 제거

## 테스트 방법

1. 브라우저 개발자 도구 → Network 탭 열기
2. `/dashboard` 페이지 접속
3. 30초마다 `/api/v1/system/health` 요청이 한 번만 발생하는지 확인
4. 설정값을 변경해도 불필요한 새로고침이 발생하지 않는지 확인
5. React DevTools → Profiler로 리렌더링 횟수 확인

## 참고 사항

- `useCallback`을 사용하여 함수를 메모이제이션하면 불필요한 재생성을 방지할 수 있음
- `useRef`를 사용하여 최신 값을 참조하면서도 의존성 배열에 포함시키지 않을 수 있음
- 이 패턴은 `setInterval`이나 `setTimeout`과 함께 사용할 때 특히 유용함
