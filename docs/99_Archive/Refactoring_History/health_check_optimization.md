# Health Check 중복 요청 최적화

## 문제점 분석

### 현재 상태
- `/api/v1/system/health` 엔드포인트에 중복 요청 발생
- 여러 컴포넌트에서 독립적으로 health check 수행

### 원인
1. **`CommandControlPage`**: `useSystemData()` 호출 → health check
2. **`SituationInputPanel`**: `useSystemData()` 호출 → health check (중복)
3. **`Header`**: `/dashboard`일 때 별도 health check → 추가 중복

### 문제점
- 비효율적: 동일한 데이터를 여러 번 요청
- 서버 부하: 불필요한 요청 증가
- 네트워크 낭비: 중복 트래픽

## 수정 내용

### 1. SystemDataContext 생성

**파일**: `frontend/src/contexts/SystemDataContext.tsx` (신규)

**변경 사항**:
- Context API를 사용하여 시스템 데이터 상태를 전역으로 관리
- 단일 인스턴스로 health check 수행
- 모든 컴포넌트가 동일한 데이터를 공유

```typescript
export const SystemDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [missions, setMissions] = useState<MissionBase[]>([]);
    const [threats, setThreats] = useState<ThreatEventBase[]>([]);
    const [health, setHealth] = useState<SystemHealthResponse | null>(null);
    // ... 상태 관리
    
    const fetchData = async () => {
        // 단일 요청으로 모든 데이터 가져오기
        const [missionsRes, threatsRes, healthRes] = await Promise.all([
            api.get<MissionListResponse>('/data/missions'),
            api.get<ThreatListResponse>('/data/threats'),
            api.get<SystemHealthResponse>('/system/health')
        ]);
        // ...
    };
    
    // ...
};
```

### 2. App.tsx에 Provider 추가

**파일**: `frontend/src/App.tsx`

**변경 사항**:
- `SystemDataProvider`를 최상위에 추가
- 모든 페이지에서 시스템 데이터 공유

```typescript
function App() {
  return (
    <ErrorBoundary>
      <SystemDataProvider>
        <ExecutionProvider>
          <Router>
            {/* ... */}
          </Router>
        </ExecutionProvider>
      </SystemDataProvider>
    </ErrorBoundary>
  );
}
```

### 3. useSystemData 훅 변경

**파일**: `frontend/src/hooks/useSystemData.ts`

**변경 사항**:
- Context 기반으로 변경
- 하위 호환성을 위해 re-export

```typescript
// 이제 SystemDataContext에서 export된 useSystemData를 re-export
export { useSystemData } from '../contexts/SystemDataContext';
```

### 4. Header 컴포넌트 최적화

**파일**: `frontend/src/components/Header.tsx`

**변경 사항**:
- 별도 health check 제거
- Context의 health 사용
- 주기적 갱신은 `refetch()` 사용

```typescript
export const Header: React.FC<HeaderProps> = () => {
    const location = useLocation();
    const { health, refetch } = useSystemData();

    // Dashboard 페이지일 때 주기적으로 health 갱신 (30초마다)
    useEffect(() => {
        if (location.pathname === '/dashboard') {
            const interval = setInterval(() => {
                refetch();
            }, 30000);
            return () => clearInterval(interval);
        }
    }, [location.pathname, refetch]);
    
    // health를 직접 사용
    {location.pathname === '/dashboard' && health && (
        <span>{health.status === 'ok' ? '✓' : '⚠'}</span>
    )}
};
```

## 수정된 파일

1. `frontend/src/contexts/SystemDataContext.tsx` (신규)
   - Context API 기반 시스템 데이터 관리
   - 단일 인스턴스로 health check 수행

2. `frontend/src/App.tsx`
   - `SystemDataProvider` 추가

3. `frontend/src/hooks/useSystemData.ts`
   - Context 기반으로 변경 (하위 호환성 유지)

4. `frontend/src/components/Header.tsx`
   - 별도 health check 제거
   - Context의 health 사용

## 예상 결과

### Before (수정 전)
```
GET /api/v1/system/health (CommandControlPage)
GET /api/v1/system/health (SituationInputPanel)
GET /api/v1/system/health (Header)
→ 총 3번의 중복 요청
```

### After (수정 후)
```
GET /api/v1/system/health (SystemDataContext - 단일 인스턴스)
→ 총 1번의 요청만 발생
```

## 장점

1. **성능 향상**: 중복 요청 제거로 네트워크 트래픽 감소
2. **서버 부하 감소**: 불필요한 요청 제거
3. **일관성**: 모든 컴포넌트가 동일한 데이터 사용
4. **유지보수성**: 중앙 집중식 데이터 관리

## 테스트 방법

### 1. 네트워크 탭 확인
1. 브라우저 개발자 도구 열기
2. Network 탭에서 `/api/v1/system/health` 필터링
3. 페이지 로드 시 요청이 1번만 발생하는지 확인

### 2. 백엔드 로그 확인
1. 백엔드 서버 로그 확인
2. `/api/v1/system/health` 요청이 줄어든 것 확인

### 3. 기능 테스트
1. Dashboard 페이지 로드
2. Header에 health 상태 표시 확인
3. 30초 후 자동 갱신 확인

## 참고 사항

- Context는 최상위 레벨에서 제공되므로 모든 페이지에서 사용 가능
- `refetch()`를 호출하면 모든 컴포넌트가 자동으로 업데이트됨
- 하위 호환성: 기존 `useSystemData()` 사용 코드는 그대로 동작
