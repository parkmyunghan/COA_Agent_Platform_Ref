# 방책 추천 진행 상황 표시 개선 계획

## 현재 문제점

1. **진척율이 20%에서 한참 머물다가 갑자기 100%로 점프**
   - 프론트엔드에서 20%로 설정한 후 백엔드 응답을 기다림
   - 백엔드에서 진행 상황을 보고하지만 프론트엔드로 실시간 전달되지 않음
   - 백엔드 처리가 완료되면 응답이 오고, 프론트엔드에서 50%, 80%, 90%, 100%로 빠르게 업데이트

2. **중간 단계 진행 상황이 보이지 않음**
   - 백엔드에서 보고하는 세부 진행 상황(온톨로지 로드, 상황 분석, 방책 검색 등)이 프론트엔드에 표시되지 않음

## 현재 백엔드 진행 상황 보고 지점

백엔드 `EnhancedDefenseCOAAgent.execute_reasoning()`에서 보고하는 진행 상황:

- **0%**: 방책 분석 시작
- **5%**: 온톨로지 데이터 로드 및 지식 그래프 구축
- **10%**: 전술 상황 분석 및 위협 요소 식별
- **20%**: 통합 후보 검색 및 병렬 최적화
- **25%**: 임무별 최적 방책 유형 및 대응 전략 수립
- **25-65%**: 방책 유형별 분석 (각 유형마다 분산)
- **70%**: 추천 방책 종합 점수 계산 및 최종 순위 생성
- **85%**: LLM 기반 방책 구체화 (Hybrid Adaptation)
- **90%**: 방책 선정사유 및 상세 정보 생성 시작
- **90-95%**: 각 방책별 선정사유 생성 (1/3, 2/3, 3/3)
- **95%**: 방책 선정사유 생성 완료
- **100%**: 방책 분석 및 추천 완료

## 개선 방안

### 옵션 1: 프론트엔드에서 단계별 진행률 시뮬레이션 (단기 해결책)

**방법**: 백엔드 응답을 기다리는 동안 예상 단계별로 진행률을 점진적으로 증가

**장점**:
- 구현이 간단함
- 즉시 적용 가능
- 사용자에게 진행 중임을 명확히 전달

**단점**:
- 실제 진행 상황과 다를 수 있음
- 백엔드 처리 시간에 따라 부정확할 수 있음

**구현**:
```typescript
// COAGenerator.tsx
const simulateProgress = () => {
    const steps = [
        { progress: 5, message: '온톨로지 데이터 로드 중...', delay: 500 },
        { progress: 10, message: '전술 상황 분석 중...', delay: 1000 },
        { progress: 20, message: '방책 후보 검색 중...', delay: 2000 },
        { progress: 30, message: '방책 유형 분석 중...', delay: 1500 },
        { progress: 50, message: '방책 점수 계산 중...', delay: 2000 },
        { progress: 70, message: '종합 점수 계산 중...', delay: 1500 },
        { progress: 85, message: 'LLM 기반 구체화 중...', delay: 2000 },
        { progress: 90, message: '선정사유 생성 중...', delay: 2000 },
    ];
    
    let currentStep = 0;
    const interval = setInterval(() => {
        if (currentStep < steps.length) {
            const step = steps[currentStep];
            executionContext?.updateProgress(step.progress, step.message);
            currentStep++;
        } else {
            clearInterval(interval);
        }
    }, 500); // 0.5초마다 업데이트
};
```

### 옵션 2: 백엔드 응답에 진행 상황 로그 포함 (중기 해결책)

**방법**: 백엔드에서 진행 상황을 로그로 수집하고, 응답에 포함시켜 프론트엔드에서 재생

**장점**:
- 실제 진행 상황을 정확히 반영
- 구현이 비교적 간단함
- WebSocket 없이도 가능

**단점**:
- 여전히 실시간이 아님 (완료 후 재생)
- 응답 크기가 커질 수 있음

**구현**:
```python
# api/routers/agent.py
progress_logs = []

def on_status_update(msg: str, progress: Optional[int] = None):
    logger.info(f"[Agent Progress] {progress}%: {msg}")
    progress_logs.append({
        "message": msg,
        "progress": progress,
        "timestamp": datetime.now().isoformat()
    })

# 응답에 포함
result["progress_logs"] = progress_logs
```

```typescript
// COAGenerator.tsx
if (res.data.progress_logs) {
    // 진행 상황 로그를 시간 순서대로 재생
    res.data.progress_logs.forEach((log, idx) => {
        setTimeout(() => {
            executionContext?.updateProgress(log.progress, log.message);
        }, idx * 300); // 0.3초 간격으로 재생
    });
}
```

### 옵션 3: Server-Sent Events (SSE)를 통한 실시간 진행 상황 (장기 해결책)

**방법**: SSE를 사용하여 백엔드에서 진행 상황을 실시간으로 전송

**장점**:
- 실제 실시간 진행 상황 표시
- 가장 정확한 사용자 경험
- WebSocket보다 구현이 간단함

**단점**:
- 백엔드와 프론트엔드 모두 수정 필요
- 구현 복잡도가 높음

**구현**:
```python
# api/routers/agent.py
@router.post("/execute/stream")
async def execute_agent_stream(
    request: AgentExecutionRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    async def event_generator():
        progress_logs = []
        
        def on_status_update(msg: str, progress: Optional[int] = None):
            progress_logs.append({
                "message": msg,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
            # SSE로 전송
            yield f"data: {json.dumps({'type': 'progress', 'message': msg, 'progress': progress})}\n\n"
        
        # Agent 실행 (비동기)
        # ...
        
        # 최종 결과 전송
        yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

```typescript
// COAGenerator.tsx
const eventSource = new EventSource('/api/v1/agent/execute/stream', {
    method: 'POST',
    body: JSON.stringify(agentPayload)
});

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'progress') {
        executionContext?.updateProgress(data.progress, data.message);
    } else if (data.type === 'complete') {
        // 결과 처리
    }
};
```

## 권장 사항

### 단기 (즉시 적용 가능)
**옵션 1 + 옵션 2 조합**:
1. 프론트엔드에서 단계별 진행률 시뮬레이션 (옵션 1)
2. 백엔드 응답에 진행 상황 로그 포함 (옵션 2)
3. 응답이 오면 실제 진행 상황 로그로 업데이트

### 중기 (1-2주 내)
**옵션 2 완전 구현**:
- 백엔드에서 진행 상황 로그 수집
- 프론트엔드에서 로그 재생
- 실제 진행 상황을 정확히 반영

### 장기 (1개월 내)
**옵션 3 (SSE) 구현**:
- 실시간 진행 상황 전달
- 최고의 사용자 경험 제공

## 구현 우선순위

1. **1단계**: 옵션 1 구현 (프론트엔드 시뮬레이션)
   - 즉시 사용자 경험 개선
   - 구현 시간: 1-2시간

2. **2단계**: 옵션 2 구현 (백엔드 로그 포함)
   - 실제 진행 상황 반영
   - 구현 시간: 2-3시간

3. **3단계**: 옵션 3 구현 (SSE 실시간 전달)
   - 최종 목표
   - 구현 시간: 1-2일
