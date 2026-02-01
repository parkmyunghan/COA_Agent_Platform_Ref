# Python 환경 설정 가이드

## 현재 설정

- **Python 버전**: 3.12.8
- **가상환경**: `.venv` (Python 3.12.8 기반)
- **프로젝트 Python 버전 지정**: `.python-version` 파일에 3.12.8 지정

## 사용 방법

### 가상환경 활성화

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# 또는
.venv\Scripts\activate
```

### 가상환경 비활성화

```powershell
deactivate
```
## 7. 사내망 프록시(Proxy) 설정

사내망 등 외부 인터넷 연결이 제한된 환경에서는 패키지 설치 시 프록시 설정이 필요합니다.

### Backend (Python/pip)
패키지 설치 시 `--proxy` 옵션을 사용합니다.
```powershell
pip install --proxy http://아이피:포트 -r requirements.txt
```

### Frontend (Node.js/npm)
npm 설정에 프록시를 추가합니다.
```powershell
npm config set proxy http://아이피:포트
npm config set https-proxy http://아이피:포트
npm install
```

### LLM (Runtime)
OpenAI API 등을 외부망 연결을 통해 사용해야 하는 경우, 시스템 환경 변수를 설정합니다. OpenAI SDK는 이를 자동으로 인식합니다.
```powershell
$env:HTTP_PROXY="http://아이피:포트"
$env:HTTPS_PROXY="http://아이피:포트"
```

---
*최종 업데이트: 2026-02-01 (Antigravity)*

### 프로젝트 실행

가상환경 활성화 후:

```powershell
# 백엔드 실행
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 또는 Streamlit 실행
python run_streamlit.py
```

## 중요 사항

1. **항상 가상환경 사용**: 프로젝트 작업 시 반드시 가상환경을 활성화하세요.
2. **Python 버전 확인**: `.python-version` 파일이 프로젝트 루트에 있어 Python 버전이 자동으로 지정됩니다.
3. **패키지 설치**: 가상환경 활성화 후 `pip install -r requirements.txt` 실행

## Python 3.14.2 삭제 상태

Python 3.14.2는 대부분 삭제되었습니다. 일부 파일이 사용 중이어서 완전히 삭제되지 않았다면:
- 시스템 재시작 후 `C:\Python314` 디렉토리를 수동으로 삭제할 수 있습니다.
- 또는 다음 명령으로 강제 삭제 시도:
  ```powershell
  Remove-Item -Path C:\Python314 -Recurse -Force -ErrorAction SilentlyContinue
  ```

## 문제 해결

### Python 버전이 잘못된 경우

```powershell
# Python 3.12.8 명시적 사용
py -3.12 -m venv .venv

# 가상환경 재생성
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
