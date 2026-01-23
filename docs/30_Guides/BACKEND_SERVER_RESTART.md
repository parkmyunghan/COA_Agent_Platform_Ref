# 백엔드 서버 재시작 가이드

## 방법 1: 현재 터미널에서 재시작 (권장)

### 1단계: 현재 서버 종료
현재 백엔드 서버가 실행 중인 터미널에서:
```
Ctrl + C
```

### 2단계: 서버 다시 시작
같은 터미널에서:
```powershell
# 가상환경 활성화 (아직 활성화되지 않은 경우)
venv\Scripts\activate

# 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## 방법 2: 포트를 사용하는 프로세스 강제 종료 후 재시작

### 1단계: 포트 8000을 사용하는 프로세스 찾기
```powershell
netstat -ano | findstr :8000
```

출력 예시:
```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       12345
```

마지막 숫자(12345)가 프로세스 ID(PID)입니다.

### 2단계: 프로세스 종료
```powershell
taskkill /PID 12345 /F
```

또는 한 번에:
```powershell
# 포트 8000을 사용하는 프로세스 찾아서 종료
$port = 8000
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($process) {
    Stop-Process -Id $process -Force
    Write-Host "포트 $port 를 사용하는 프로세스(PID: $process)를 종료했습니다."
} else {
    Write-Host "포트 $port 를 사용하는 프로세스가 없습니다."
}
```

### 3단계: 서버 다시 시작
```powershell
# 가상환경 활성화
venv\Scripts\activate

# 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## 방법 3: Python 프로세스 모두 종료 후 재시작

### 1단계: 모든 Python 프로세스 종료
```powershell
# 주의: 실행 중인 모든 Python 프로세스가 종료됩니다
taskkill /IM python.exe /F
```

### 2단계: 서버 다시 시작
```powershell
# 가상환경 활성화
venv\Scripts\activate

# 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## 방법 4: PowerShell 스크립트로 자동화

다음 스크립트를 `restart_backend.ps1`로 저장:

```powershell
# restart_backend.ps1
Write-Host "백엔드 서버 재시작 중..." -ForegroundColor Yellow

# 포트 8000을 사용하는 프로세스 찾기
$port = 8000
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($process) {
    Write-Host "포트 $port 를 사용하는 프로세스(PID: $process)를 종료합니다..." -ForegroundColor Yellow
    Stop-Process -Id $process -Force
    Start-Sleep -Seconds 2
}

# 가상환경 활성화
Write-Host "가상환경 활성화 중..." -ForegroundColor Green
& "venv\Scripts\Activate.ps1"

# 서버 실행
Write-Host "백엔드 서버 시작 중..." -ForegroundColor Green
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

실행:
```powershell
.\restart_backend.ps1
```

## 서버 실행 확인

서버가 정상적으로 실행되면 다음 메시지가 표시됩니다:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

다음 URL에서 API 문서를 확인할 수 있습니다:
- **API 문서**: http://localhost:8000/docs
- **대체 문서**: http://localhost:8000/redoc

## 문제 해결

### 포트가 이미 사용 중인 경우
```powershell
# 포트 8000을 사용하는 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료
taskkill /PID <PID> /F
```

### 가상환경이 활성화되지 않는 경우
```powershell
# PowerShell 실행 정책 확인
Get-ExecutionPolicy

# 실행 정책 변경 (필요한 경우)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 가상환경 활성화
venv\Scripts\Activate.ps1
```

### uvicorn이 설치되지 않은 경우
```powershell
# 가상환경 활성화
venv\Scripts\activate

# uvicorn 설치
pip install uvicorn[standard]
```

## 참고 사항

- `--reload` 옵션을 사용하면 코드 변경 시 자동으로 서버가 재시작됩니다.
- 프로덕션 환경에서는 `--reload` 옵션을 제거하고 프로세스 관리자(예: systemd, supervisor)를 사용하세요.
- 포트를 변경하려면 `--port` 옵션을 사용하세요: `--port 8001`
