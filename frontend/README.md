# Defense Intelligent Agent Platform - Frontend

이 프로젝트는 국방 지능형 방책(COA) 분석 플랫폼의 사용자 인터페이스를 제공하는 React 어플리케이션입니다.

## 🛠 기술 스택
- **Framework**: React 19 (TypeScript)
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **State Management**: React Context API
- **Visualization**: Recharts, React Leaflet (Map), React Force Graph (Ontology)
- **API Client**: Axios

## 🚀 시작하기

### 1. 환경 설정
Node.js (v18 이상 권장)가 설치되어 있어야 합니다.

```bash
# 의존성 설치
npm install

# 사내망 프록시가 필요한 경우
npm config set proxy http://proxy_url:port
npm install
```

### 2. 백엔드 연결 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 필요에 따라 수정합니다.

```bash
# Windows
copy .env.example .env
```

`.env` 내용:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. 개발 서버 실행
```bash
npm run dev
```
기본적으로 `http://localhost:5173`에서 실행됩니다.

### 4. 빌드
```bash
npm run build
```
결과물은 `dist` 폴더에 생성됩니다.

## 📂 주요 폴더 구조
- `src/components`: 재사용 가능한 UI 컴포넌트
- `src/pages`: 주요 페이지 (대시보드, 상황관리, 스튜디오 등)
- `src/lib`: API 클라이언트 및 유틸리티
- `src/hooks`: 커스텀 React 훅
- `src/types`: TypeScript 타입 정의

## 📝 가이드
상황 분석 및 방책 생성을 위해서는 백엔드 서버(FastAPI)가 실행 중이어야 합니다.
백엔드 설정은 프로젝트 루트의 `ENV_SETUP.md`를 참고하세요.
