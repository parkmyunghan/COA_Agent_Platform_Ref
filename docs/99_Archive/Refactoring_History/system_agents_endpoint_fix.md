# /system/agents 엔드포인트 추가

## 문제점 분석

### 현재 상태
- 프론트엔드 `AgentSelector.tsx`에서 `/system/agents` 엔드포인트 호출
- 백엔드에 해당 엔드포인트가 없어 404 Not Found 발생
- 프론트엔드는 에러 처리로 기본 Agent 목록 사용 (기능상 문제 없음)

### 원인
- 백엔드에 `/system/agents` 엔드포인트가 구현되지 않음
- Agent 레지스트리(`config/agent_registry.yaml`)는 존재하지만 API로 노출되지 않음

## 수정 내용

### 1. /system/agents 엔드포인트 추가

**파일**: `api/routers/system.py`

**변경 사항**:
- `yaml` import 추가
- `/system/agents` GET 엔드포인트 추가
- `agent_registry.yaml` 파일을 읽어서 Agent 목록 반환

```python
@router.get("/agents")
def get_agents():
    """
    사용 가능한 Agent 목록을 반환합니다.
    
    Returns:
        Agent 목록 (name, description, enabled 필드 포함)
    """
    # Agent 레지스트리 파일 경로
    base_dir = Path(__file__).parent.parent.parent
    registry_path = base_dir / "config" / "agent_registry.yaml"
    
    if not registry_path.exists():
        return {"agents": []}
    
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f)
        
        agents = registry.get("agents", [])
        
        # 프론트엔드가 기대하는 형식으로 변환
        return {
            "agents": [
                {
                    "name": agent.get("name"),
                    "description": agent.get("description", ""),
                    "enabled": agent.get("enabled", True)
                }
                for agent in agents
            ]
        }
    except Exception as e:
        # 에러 발생 시 빈 목록 반환 (프론트엔드가 기본값 사용)
        return {"agents": []}
```

## API 응답 형식

### 요청
```
GET /api/v1/system/agents
```

### 응답
```json
{
  "agents": [
    {
      "name": "coa_recommendation_agent",
      "description": "전술 방책 추천 Agent (7가지 타입 지원: 방어/공격/반격/선제/억제/기동/정보작전, 위협수준 기반 추천, 4가지 입력방식 지원: 실제데이터/SITREP/수동입력/데모시나리오, 팔란티어 모드: 6개 요소 종합 평가 활성화)",
      "enabled": true
    },
    {
      "name": "intel_management_agent",
      "description": "첩보 수집 및 신뢰도 평가 Agent (레거시)",
      "enabled": false
    }
  ]
}
```

## 수정된 파일

1. `api/routers/system.py`
   - `yaml` import 추가
   - `/system/agents` GET 엔드포인트 추가

## 테스트 방법

### 1. 백엔드 API 테스트
1. 백엔드 서버 재시작
2. `/api/v1/system/agents` 엔드포인트 호출
3. 응답에서 Agent 목록 확인:
   ```bash
   curl http://localhost:8000/api/v1/system/agents
   ```

### 2. 프론트엔드 테스트
1. 프론트엔드 새로고침
2. 브라우저 개발자 도구 네트워크 탭 확인
3. `/api/v1/system/agents` 요청이 200 OK로 성공하는지 확인
4. Agent 선택 드롭다운에 Agent 목록이 표시되는지 확인

### 3. 로그 확인
1. 백엔드 서버 로그 확인
2. 404 Not Found 에러가 더 이상 발생하지 않는지 확인

## 예상 결과

- ✅ `/api/v1/system/agents` 엔드포인트가 200 OK 응답
- ✅ 프론트엔드에서 Agent 목록을 동적으로 가져옴
- ✅ 404 Not Found 에러가 더 이상 발생하지 않음
- ✅ `agent_registry.yaml`에 새 Agent를 추가하면 자동으로 프론트엔드에 반영됨

## 장점

1. **확장성**: 새 Agent 추가 시 프론트엔드 수정 불필요
2. **일관성**: `chat.py`와 동일한 레지스트리 사용
3. **유지보수성**: 중앙 집중식 Agent 관리
4. **에러 제거**: 404 에러 로그 제거

## 참고 사항

- Agent 레지스트리 파일: `config/agent_registry.yaml`
- 프론트엔드는 `enabled: false`인 Agent를 필터링하여 표시
- 에러 발생 시 빈 목록 반환 (프론트엔드가 기본값 사용)
