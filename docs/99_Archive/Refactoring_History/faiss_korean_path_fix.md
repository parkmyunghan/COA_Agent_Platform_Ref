# FAISS 인덱스 한글 경로 처리 문제 수정

## 문제점 분석

### 현재 상태
- FAISS 인덱스 로드 시 "Illegal byte sequence" 오류 발생
- Windows에서 한글 경로(`C:\POC\COA_Agent_Platform_화면 리팩토링\knowledge\embeddings\faiss_index.bin`)를 처리하지 못함

### 원인
1. **FAISS C++ 라이브러리 한계**:
   - FAISS는 C++ 기반 라이브러리로 파일 경로를 처리할 때 UTF-8 인코딩을 제대로 처리하지 못함
   - Windows에서 한글 경로를 직접 전달하면 "Illegal byte sequence" 오류 발생

2. **경로 인코딩 문제**:
   - Windows 파일 시스템은 UTF-16을 사용하지만, FAISS는 바이트 시퀀스를 기대
   - 한글 문자가 포함된 경로를 처리할 때 인코딩 변환 실패

## 수정 내용

### 1. Windows 짧은 경로 변환 함수 추가

**파일**: `core_pipeline/rag_manager.py`

**변경 사항**:
- `_get_windows_short_path()` 함수 추가
- Windows API `GetShortPathNameW`를 사용하여 한글 경로를 8.3 형식 짧은 경로로 변환
- 비-Windows 플랫폼에서는 원본 경로 반환

```python
def _get_windows_short_path(path: str) -> str:
    """
    Windows에서 한글 경로를 짧은 경로(8.3 형식)로 변환
    
    Args:
        path: 원본 경로
        
    Returns:
        짧은 경로 또는 원본 경로 (변환 실패 시)
    """
    if sys.platform != 'win32':
        return path
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # GetShortPathNameW 함수 사용
        kernel32 = ctypes.windll.kernel32
        kernel32.GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        kernel32.GetShortPathNameW.restype = wintypes.DWORD
        
        # 버퍼 크기 확인
        buffer_size = kernel32.GetShortPathNameW(path, None, 0)
        if buffer_size == 0:
            return path
        
        # 버퍼 할당 및 변환
        buffer = ctypes.create_unicode_buffer(buffer_size)
        result = kernel32.GetShortPathNameW(path, buffer, buffer_size)
        
        if result > 0:
            return buffer.value
        else:
            return path
    except Exception:
        return path
```

### 2. FAISS 인덱스 로드 시 경로 변환 적용

**파일**: `core_pipeline/rag_manager.py`

**변경 사항**:
- `load_embeddings()` 메서드에서 FAISS 인덱스 로드 시 경로 변환
- `load_index()` 메서드에서 FAISS 인덱스 로드 시 경로 변환

```python
# load_embeddings() 메서드
if chunks_loaded and self.faiss_index is None and os.path.exists(faiss_path) and FAISS_AVAILABLE:
    try:
        # Windows에서 한글 경로 처리
        faiss_path_normalized = _get_windows_short_path(faiss_path)
        self.faiss_index = faiss.read_index(faiss_path_normalized)
        # ...
    except Exception as e:
        # ...

# load_index() 메서드
if has_faiss_file:
    try:
        # Windows에서 한글 경로 처리
        faiss_path_normalized = _get_windows_short_path(faiss_path)
        self.faiss_index = faiss.read_index(faiss_path_normalized)
        # ...
    except Exception as e:
        # ...
```

### 3. FAISS 인덱스 저장 시 경로 변환 적용

**파일**: `core_pipeline/rag_manager.py`

**변경 사항**:
- `save_index()` 메서드에서 FAISS 인덱스 저장 시 경로 변환

```python
# save_index() 메서드
if self.faiss_index is not None and FAISS_AVAILABLE:
    faiss_path = self.config.get("embedding", {}).get("index_path", 
                                                       os.path.join(self.embedding_path, "faiss_index.bin"))
    try:
        # Windows에서 한글 경로 처리
        faiss_path_normalized = _get_windows_short_path(faiss_path)
        faiss.write_index(self.faiss_index, faiss_path_normalized)
        # ...
    except Exception as e:
        # ...
```

## 수정된 파일

1. `core_pipeline/rag_manager.py`
   - `sys` import 추가
   - `_get_windows_short_path()` 함수 추가
   - FAISS 인덱스 로드/저장 시 경로 변환 적용

## Windows 짧은 경로 변환 원리

### 8.3 형식 경로
- Windows는 긴 경로를 짧은 경로(8.3 형식)로 변환 가능
- 예: `C:\POC\COA_Agent_Platform_화면 리팩토링\` → `C:\POC\COA_AG~1\`
- 한글 문자를 ASCII 문자로 변환하여 FAISS가 처리 가능

### GetShortPathNameW API
- Windows API 함수로 긴 경로를 짧은 경로로 변환
- UTF-16 기반으로 동작하여 한글 경로도 처리 가능
- 변환 실패 시 원본 경로 반환 (안전한 폴백)

## 예상 결과

### Before (수정 전)
```
[WARN] FAISS index load failed: Error: 'f' failed: could not open 
C:\POC\COA_Agent_Platform_화면 리팩토링\knowledge\embeddings\faiss_index.bin 
for reading: Illegal byte sequence
```

### After (수정 후)
```
[INFO] FAISS index loaded: C:\POC\COA_AG~1\knowledge\embeddings\faiss_index.bin
```

## 테스트 방법

### 1. 백엔드 서버 재시작
1. 백엔드 서버 재시작
2. 로그에서 FAISS 인덱스 로드 성공 메시지 확인

### 2. RAG 검색 테스트
1. Agent 실행하여 RAG 검색 기능 테스트
2. FAISS 인덱스를 사용한 검색이 정상 동작하는지 확인

### 3. 인덱스 재구축 테스트
1. FAISS 인덱스 파일 삭제
2. 시스템 재시작하여 인덱스 자동 재구축 확인
3. 인덱스 저장 시 경로 변환이 정상 동작하는지 확인

## 참고 사항

- Windows에서만 적용되는 수정사항 (비-Windows에서는 원본 경로 사용)
- 짧은 경로 변환 실패 시 원본 경로로 폴백 (안전성 보장)
- FAISS 인덱스는 정상적으로 로드되지만, 로그에는 원본 경로가 표시됨 (사용자 편의성)
