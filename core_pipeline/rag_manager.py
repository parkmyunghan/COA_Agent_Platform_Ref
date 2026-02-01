# core_pipeline/rag_manager.py
# -*- coding: utf-8 -*-
"""
RAG Manager
Retrieval-Augmented Generation 관리 모듈
기존 rag_chunking.py, rag_hybrid.py 통합
"""
import os
import re
import sys
import numpy as np
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not installed. FAISS indexing will be disabled.")


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
            # 변환 실패 시 원본 경로 반환
            return path
        
        # 버퍼 할당 및 변환
        buffer = ctypes.create_unicode_buffer(buffer_size)
        result = kernel32.GetShortPathNameW(path, buffer, buffer_size)
        
        if result > 0:
            return buffer.value
        else:
            return path
    except Exception:
        # 변환 실패 시 원본 경로 반환
        return path


class RAGManager:
    """RAG 관리자 클래스"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: 설정 딕셔너리
        """
        self.config = config
        self.index = {}
        self.chunks = []
        self.embeddings = None
        self.embedding_model = None
        self.embedding_path = config.get("embedding_path", "./knowledge/embeddings")
        self.faiss_index = None
    
    def chunk_documents(self, docs: List[str], chunk_size: int = 500, overlap: int = 50, 
                       min_chunk_size: int = 100, use_sentence_chunking: bool = True,
                       doc_names: Optional[List[str]] = None) -> List[Dict]:
        """
        문서를 청크로 분할 (기존 rag_chunking.py 통합)
        
        Args:
            docs: 문서 리스트
            chunk_size: 청크 크기 (문자 수)
            overlap: 청크 간 겹치는 문자 수
            min_chunk_size: 최소 청크 크기
            use_sentence_chunking: 문장 단위 청킹 사용 여부
            doc_names: 문서 파일명 리스트 (옵션)
            
        Returns:
            청크 리스트 [{"text": str, "start": int, "end": int, "doc_index": int, "source": str, ...}]
        """
        all_chunks = []
        
        # doc_names가 없으면 None으로 채움
        if doc_names is None:
            doc_names = [None] * len(docs)
        elif len(doc_names) != len(docs):
            logger.warning(f"문서 수({len(docs)})와 파일명 수({len(doc_names)})가 일치하지 않습니다.")
            doc_names = [None] * len(docs)
        
        for doc_idx, doc in enumerate(docs):
            if use_sentence_chunking:
                chunks = self._chunk_text_by_sentences(doc, chunk_size, overlap, min_chunk_size)
            else:
                chunks = self._chunk_text_simple(doc, chunk_size, overlap, min_chunk_size)
            
            # 메타데이터 추가
            doc_name = doc_names[doc_idx]
            for i, chunk in enumerate(chunks):
                chunk["doc_index"] = doc_idx
                chunk["chunk_index"] = i
                chunk["total_chunks"] = len(chunks)
                if doc_name:
                    chunk["source"] = doc_name
                all_chunks.append(chunk)
        
        return all_chunks
    
    def _chunk_text_by_sentences(self, text: str, chunk_size: int, overlap: int, min_chunk_size: int) -> List[Dict]:
        """문장 단위로 청킹"""
        if not text or len(text.strip()) < min_chunk_size:
            return [{"text": text.strip(), "start": 0, "end": len(text)}]
        
        sentence_pattern = r'([^.!?]+[.!?]+)'
        sentences = re.findall(sentence_pattern, text)
        
        if not sentences:
            return self._chunk_text_simple(text, chunk_size, overlap, min_chunk_size)
        
        chunks = []
        current_chunk = []
        current_length = 0
        start_pos = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text.strip()) >= min_chunk_size:
                    chunks.append({
                        "text": chunk_text.strip(),
                        "start": start_pos,
                        "end": start_pos + len(chunk_text)
                    })
                
                # Overlap 처리
                if overlap > 0 and len(current_chunk) > 0:
                    overlap_text = ""
                    overlap_sentences = []
                    for sent in reversed(current_chunk):
                        if len(overlap_text + sent) <= overlap:
                            overlap_sentences.insert(0, sent)
                            overlap_text = " ".join(overlap_sentences)
                        else:
                            break
                    
                    current_chunk = overlap_sentences + [sentence]
                    current_length = len(overlap_text) + sentence_length
                    start_pos = chunks[-1]["end"] - len(overlap_text) if chunks else 0
                else:
                    current_chunk = [sentence]
                    current_length = sentence_length
                    start_pos = start_pos + len(chunk_text) if chunks else 0
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + 1
        
        # 마지막 청크
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text.strip()) >= min_chunk_size:
                chunks.append({
                    "text": chunk_text.strip(),
                    "start": start_pos,
                    "end": start_pos + len(chunk_text)
                })
        
        return chunks if chunks else [{"text": text.strip(), "start": 0, "end": len(text)}]
    
    def _chunk_text_simple(self, text: str, chunk_size: int, overlap: int, min_chunk_size: int) -> List[Dict]:
        """단순 텍스트 분할"""
        if not text or len(text.strip()) < min_chunk_size:
            return [{"text": text.strip(), "start": 0, "end": len(text)}]
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk_text = text[start:end]
            
            # 문장 끝 찾기
            if end < text_length:
                last_period = chunk_text.rfind('.')
                last_exclamation = chunk_text.rfind('!')
                last_question = chunk_text.rfind('?')
                last_newline = chunk_text.rfind('\n')
                
                last_break = max(last_period, last_exclamation, last_question, last_newline)
                
                if last_break > chunk_size * 0.7:
                    chunk_text = chunk_text[:last_break + 1]
                    end = start + last_break + 1
            
            chunk_text = chunk_text.strip()
            if len(chunk_text) >= min_chunk_size:
                chunks.append({
                    "text": chunk_text,
                    "start": start,
                    "end": end
                })
            
            start = end - overlap if overlap > 0 else end
            if start >= end:
                start = end
        
        return chunks if chunks else [{"text": text.strip(), "start": 0, "end": len(text)}]
    
    def chunk_doctrine_documents(self, docs: List[str], doc_names: Optional[List[str]] = None) -> List[Dict]:
        """
        교리 문서를 교리 문장 단위로 청킹 (교리 문서 전용)
        
        교리 문서 형식:
        # Doctrine_ID: DOCTRINE-XXX
        ## 교리명: ...
        ## 적용 작전유형: ...
        ## 관련 METT-C 요소: ...
        
        ### Doctrine_Statement_ID: D-XXX-001
        - [교리 문장]
        - **작전적 해석**: ...
        
        Args:
            docs: 교리 문서 리스트
            doc_names: 문서 파일명 리스트 (옵션)
            
        Returns:
            청크 리스트 [{
                "text": str,
                "doctrine_id": str,
                "statement_id": str,
                "mett_c_elements": List[str],
                "statement_text": str,  # 실제 교리 문장 본문
                "source": str,
                ...
            }]
        """
        import re
        all_chunks = []
        
        if doc_names is None:
            doc_names = [None] * len(docs)
        elif len(doc_names) != len(docs):
            print(f"[WARN] 문서 수({len(docs)})와 파일명 수({len(doc_names)})가 일치하지 않습니다.")
            doc_names = [None] * len(docs)
        
        for doc_idx, doc in enumerate(docs):
            doc_name = doc_names[doc_idx] or f"doc_{doc_idx}"
            
            # 교리 문서 헤더 파싱
            doctrine_id_match = re.search(r'#\s*Doctrine_ID:\s*(DOCTRINE-[\w-]+)', doc, re.IGNORECASE)
            doctrine_id = doctrine_id_match.group(1) if doctrine_id_match else None
            
            mett_c_match = re.search(r'##\s*관련\s*METT-C\s*요소:\s*([^\n]+)', doc, re.IGNORECASE)
            mett_c_str = mett_c_match.group(1).strip() if mett_c_match else ""
            mett_c_elements = [e.strip() for e in mett_c_str.split(',') if e.strip()] if mett_c_str else []
            
            # 교리 문장 단위로 분할
            # 패턴: ### Doctrine_Statement_ID: D-XXX-001
            statement_pattern = r'###\s*Doctrine_Statement_ID:\s*(D-[\w-]+-\d+)'
            
            statements = []
            for match in re.finditer(statement_pattern, doc):
                statement_id = match.group(1)
                start_pos = match.end()
                
                # 다음 문장 ID까지 또는 문서 끝까지
                next_match = None
                for next_match_iter in re.finditer(statement_pattern, doc):
                    if next_match_iter.start() > start_pos:
                        next_match = next_match_iter
                        break
                
                end_pos = next_match.start() if next_match else len(doc)
                statement_block = doc[start_pos:end_pos].strip()
                
                # 교리 문장 본문 추출 (첫 번째 리스트 항목 또는 첫 번째 문장)
                statement_text = ""
                lines = statement_block.split('\n')
                for line in lines:
                    line = line.strip()
                    # 마크다운 리스트 항목 제거
                    if line.startswith('-'):
                        line = line[1:].strip()
                    # 볼드 제거
                    line = re.sub(r'\*\*[^*]+\*\*:\s*', '', line)
                    # 주석 제거
                    if line.startswith('#'):
                        continue
                    if line and len(line) > 10 and not line.startswith('**'):
                        statement_text = line
                        break
                
                # 작전적 해석 추출
                interpretation_match = re.search(r'\*\*작전적\s*해석\*\*:\s*([^\n]+)', statement_block, re.IGNORECASE)
                interpretation = interpretation_match.group(1).strip() if interpretation_match else ""
                
                if statement_text:
                    statements.append({
                        "statement_id": statement_id,
                        "statement_text": statement_text,
                        "interpretation": interpretation,
                        "full_block": statement_block
                    })
            
            # 각 교리 문장을 청크로 생성
            for stmt in statements:
                # 청크 텍스트: 교리 문장 본문 + 해석 (간결하게)
                chunk_text_parts = [stmt["statement_text"]]
                if stmt["interpretation"]:
                    chunk_text_parts.append(f"작전적 해석: {stmt['interpretation']}")
                
                chunk = {
                    "text": "\n".join(chunk_text_parts),
                    "doctrine_id": doctrine_id or "UNKNOWN",
                    "statement_id": stmt["statement_id"],
                    "mett_c_elements": mett_c_elements.copy(),
                    "statement_text": stmt["statement_text"],  # 실제 교리 문장 본문
                    "interpretation": stmt["interpretation"],
                    "source": doc_name,
                    "doc_index": doc_idx,
                    "chunk_type": "doctrine_statement"
                }
                all_chunks.append(chunk)
        
        return all_chunks
    
    def build_index(self, chunks: List[Dict], use_faiss: bool = True):
        """
        청크 인덱스 구축 (FAISS 지원 추가)
        
        Args:
            chunks: 청크 리스트 (Dict 또는 str)
            use_faiss: FAISS 인덱스 사용 여부
        """
        # chunks를 문자열 리스트로 변환
        # chunks를 문자열 리스트로 변환 (임베딩 생성을 위해)
        self.chunks = chunks # 원본(Dict 리스트) 유지
        
        # 임베딩용 텍스트 리스트 추출
        if chunks and isinstance(chunks[0], dict):
            text_chunks = [chunk.get("text", "") for chunk in chunks]
        else:
            text_chunks = [str(chunk) for chunk in chunks]
            # 구형 데이터 호환성을 위해 dict로 변환하여 저장
            self.chunks = [{"text": str(chunk)} for chunk in chunks]
        
        self.index = {i: chunk for i, chunk in enumerate(text_chunks)}
        
        # FAISS 인덱스 구축
        if use_faiss and FAISS_AVAILABLE and self.embedding_model is not None:
            try:
                # 텍스트 리스트로 임베딩 계산
                embeddings = self.compute_embeddings(text_chunks)
                if embeddings is not None:
                    dimension = embeddings.shape[1]
                    self.faiss_index = faiss.IndexFlatL2(dimension)
                    self.faiss_index.add(embeddings.astype('float32'))
                    self.embeddings = embeddings
                    logger.info(f"FAISS index built: {len(text_chunks)} chunks, dimension {dimension}")
            except Exception as e:
                logger.warning(f"FAISS index build failed: {e}")
                self.faiss_index = None
        else:
            self.faiss_index = None
    
    def add_to_index(self, new_chunks: List[Dict]):
        """
        기존 인덱스에 새로운 청크 추가 (증분 색인)
        
        Args:
            new_chunks: 추가할 청크 리스트
        """
        if not new_chunks:
            return

        # 1. 텍스트 추출 및 chunks 업데이트
        if new_chunks and isinstance(new_chunks[0], dict):
            new_text_chunks = [chunk.get("text", "") for chunk in new_chunks]
        else:
            new_text_chunks = [str(chunk) for chunk in new_chunks]
            new_chunks = [{"text": str(chunk)} for chunk in new_chunks] # 메타데이터 정규화
            
        # 기존 청크에 추가
        start_idx = len(self.chunks)
        self.chunks.extend(new_chunks) # 메타데이터 포함 청크 리스트 확장
        
        # 인덱스 맵 업데이트
        for i, chunk_text in enumerate(new_text_chunks):
            self.index[start_idx + i] = chunk_text
            
        # 2. FAISS 인덱스 업데이트
        if FAISS_AVAILABLE and self.embedding_model is not None:
            try:
                # 새 청크에 대한 임베딩 계산
                new_embeddings = self.compute_embeddings(new_text_chunks)
                
                if new_embeddings is not None:
                    # FAISS 인덱스가 없으면 새로 생성
                    if self.faiss_index is None:
                        dimension = new_embeddings.shape[1]
                        self.faiss_index = faiss.IndexFlatL2(dimension)
                        self.embeddings = new_embeddings
                    else:
                        # 기존 임베딩에 추가
                        self.embeddings = np.concatenate((self.embeddings, new_embeddings), axis=0)
                    
                    # FAISS에 추가
                    self.faiss_index.add(new_embeddings.astype('float32'))
                    logger.info(f"Added {len(new_chunks)} chunks to FAISS index. Total: {self.faiss_index.ntotal}")
                else:
                    logger.warning("Failed to compute embeddings for new chunks")
            except Exception as e:
                logger.warning(f"Failed to update FAISS index: {e}")
    
    def load_embeddings(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """
        임베딩 모델 로드
        models/embedding/rogel-embedding-v2 경로의 모델 사용
        
        Args:
            model_path: 임베딩 모델 경로 (None이면 config에서 가져옴)
            device: 'cpu' 또는 'cuda' (None이면 자동 선택, GPU 메모리에 따라 결정)
        """
        try:
            from sentence_transformers import SentenceTransformer
            import torch
        except Exception as e:
            logger.error(f"RAG 임베딩 라이브러리 임포트 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return
        
        if model_path is None:
            # config에서 embedding 섹션 확인
            embedding_config = self.config.get("embedding", {})
            model_path = embedding_config.get("model_path")
            
            # config에 embedding 섹션이 없으면 model_config.yaml에서 직접 로드
            if not model_path:
                try:
                    import yaml
                    base_dir = os.path.dirname(os.path.dirname(__file__))
                    model_config_path = os.path.join(base_dir, "config", "model_config.yaml")
                    if os.path.exists(model_config_path):
                        with open(model_config_path, 'r', encoding='utf-8') as f:
                            model_config = yaml.safe_load(f)
                            model_path = model_config.get("embedding", {}).get("model_path", "./models/embedding/rogel-embedding-v2")
                    else:
                        # rag_config.yaml도 확인
                        rag_config_path = os.path.join(base_dir, "config", "rag_config.yaml")
                        if os.path.exists(rag_config_path):
                            with open(rag_config_path, 'r', encoding='utf-8') as f:
                                rag_config = yaml.safe_load(f)
                                model_path = rag_config.get("embedding", {}).get("model_path", "./models/embedding/rogel-embedding-v2")
                        else:
                            model_path = "./models/embedding/rogel-embedding-v2"
                except Exception as e:
                    logger.warning(f"Config 파일 로드 실패: {e}, 기본 경로 사용")
                    model_path = "./models/embedding/rogel-embedding-v2"
        
        # 상대 경로를 절대 경로로 변환
        if model_path and not os.path.isabs(model_path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            model_path = os.path.join(base_dir, model_path)
            model_path = os.path.normpath(model_path)
        
        if not os.path.exists(model_path):
            logger.warning(f"Embedding model not found at {model_path}")
            logger.warning("   Using simple retrieval.")
            return
        
        # GPU 사용 가능 여부 확인
        cuda_available = torch.cuda.is_available()
        
        # CPU 우선 정책 강제 적용: 안정성을 위해 항상 CPU로 로드
        if device is None or device == 'cuda':
            logger.info("CPU 우선 정책: Embedding 모델을 CPU에 로드합니다.")
            device = 'cpu'
        # device가 명시적으로 'cpu'인 경우 그대로 사용
        
        # 모델 로드 (CPU 모드로 강제, 오류 처리 강화)
        model = None
        max_retries = 3
        retry_count = 0
        
        while model is None and retry_count < max_retries:
            try:
                retry_count += 1
                if retry_count > 1:
                    logger.info(f"Embedding 모델 로드 재시도 {retry_count}/{max_retries}...")
                
                # CPU 모드로 직접 로드 (안정성 우선)
                model = SentenceTransformer(model_path, device='cpu')
                logger.info(f"Embedding model loaded (CPU): {model_path}")
                device = 'cpu'
                break
                
            except Exception as e1:
                error_msg = str(e1)
                logger.warning(f"Embedding 모델 로드 실패 (시도 {retry_count}/{max_retries}): {error_msg[:150]}")
                
                if retry_count < max_retries:
                    # 재시도 전 잠시 대기
                    import time
                    time.sleep(1)
                    continue
                else:
                    # 최종 실패
                    logger.error(f"Embedding model loading failed after {max_retries} attempts: {e1}")
                    import traceback
                    traceback.print_exc()
                    
                    # 모델 경로 확인
                    if not os.path.exists(model_path):
                        logger.error(f"모델 경로가 존재하지 않습니다: {model_path}")
                    else:
                        # 모델 파일 확인
                        model_files = os.listdir(model_path)
                        logger.info(f"모델 디렉토리 파일: {model_files[:10]}")
                    
                    # None을 반환하지 않고 계속 진행 (RAG 기능은 제한적으로 작동)
                    logger.warning("Embedding 모델 없이 계속 진행합니다. RAG 기능은 제한적입니다.")
                    return
        
        self.embedding_model = model
        
        # 기존 FAISS 인덱스 및 chunks 로드 시도
        faiss_path = self.config.get("embedding", {}).get("index_path", 
                                                           os.path.join(self.embedding_path, "faiss_index.bin"))
        
        # 상대 경로를 절대 경로로 변환
        if faiss_path and not os.path.isabs(faiss_path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            faiss_path = os.path.join(base_dir, faiss_path)
            faiss_path = os.path.normpath(faiss_path)
        
        # 저장된 인덱스(chunks + FAISS) 로드 시도
        chunks_loaded = False
        try:
            self.load_index()  # chunks와 FAISS 인덱스 모두 로드 (중복 방지 로직 포함)
            if len(self.chunks) > 0:
                chunks_loaded = True
                logger.info(f"RAG 인덱스 메타데이터 로드 완료: {len(self.chunks)}개 청크")
                # load_index()에서 이미 FAISS 인덱스를 로드했으므로 여기서는 추가 로드 불필요
                if self.faiss_index is not None:
                    # FAISS 인덱스 크기와 청크 수 일치 확인
                    faiss_size = self.faiss_index.ntotal
                    chunks_size = len(self.chunks)
                    if faiss_size != chunks_size:
                        logger.warning(f"FAISS 인덱스 크기({faiss_size})와 청크 수({chunks_size})가 일치하지 않습니다.")
                        logger.warning(f"인덱스 재구축이 필요합니다.")
                        # 불일치 시 초기화
                        self.faiss_index = None
                        self.chunks = []
                        chunks_loaded = False
        except Exception as e:
            logger.info(f"저장된 인덱스 메타데이터 없음: {e}")
        
        # load_index()에서 FAISS를 로드하지 못한 경우에만 여기서 로드 시도
        if chunks_loaded and self.faiss_index is None and os.path.exists(faiss_path) and FAISS_AVAILABLE:
            try:
                # Windows에서 한글 경로 처리
                faiss_path_normalized = _get_windows_short_path(faiss_path)
                self.faiss_index = faiss.read_index(faiss_path_normalized)
                logger.info(f"FAISS index loaded: {faiss_path}")
                
                # FAISS 인덱스 크기와 청크 수 일치 확인
                faiss_size = self.faiss_index.ntotal
                chunks_size = len(self.chunks)
                if faiss_size != chunks_size:
                    logger.warning(f"FAISS 인덱스 크기({faiss_size})와 청크 수({chunks_size})가 일치하지 않습니다.")
                    logger.warning(f"인덱스 재구축이 필요합니다.")
                    # 불일치 시 초기화
                    self.faiss_index = None
                    self.chunks = []
            except Exception as e:
                logger.warning(f"FAISS index load failed: {e}")
                self.faiss_index = None
        elif os.path.exists(faiss_path) and not chunks_loaded:
            # FAISS 인덱스는 있지만 chunks가 없는 경우 (불일치 상태)
            logger.warning(f"FAISS 인덱스 파일은 있지만 청크 데이터가 없습니다.")
            logger.warning(f"인덱스 재구축이 필요합니다.")
            # FAISS 인덱스는 로드하지 않음 (불일치 방지)
    
    def compute_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        텍스트 임베딩 계산
        
        Args:
            texts: 텍스트 리스트
            
        Returns:
            임베딩 배열 (모델이 없으면 None)
        """
        if self.embedding_model is None:
            return None
        
        try:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            return embeddings
        except Exception as e:
            logger.warning(f"Failed to compute embeddings: {e}")
            return None
    
    def retrieve(self, query: str, top_k: int = 3, use_hybrid: bool = True) -> List[Dict]:
        """
        쿼리에 대한 관련 문서 검색 (하이브리드 검색 지원)
        기존 rag_hybrid.py의 hybrid_search 로직 통합
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 k개 결과
            use_hybrid: 하이브리드 검색 사용 여부 (TF-IDF + Vector)
            
        Returns:
            [{"text": str, "score": float}] 리스트
        """
        # 인덱스가 비어있으면 로드 시도 (Self-healing)
        if not self.index:
            try:
                logger.info("RAG 인덱스가 비어있어 로드를 시도합니다...")
                self.load_index()
            except Exception as e:
                logger.warning(f"RAG 인덱스 자동 로드 실패: {e}")

        if not self.index:
            logger.warning("RAG 인덱스가 여전히 비어있습니다. 검색 결과 없음.")
            return []
        
        # 하이브리드 검색 (TF-IDF + Vector)
        if use_hybrid and self.embedding_model is not None:
            try:
                # Vector 검색 (임베딩 기반)
                vector_results = self._vector_search(query, top_k)
                
                # TF-IDF 검색 (키워드 기반)
                tfidf_results = self._tfidf_search(query, top_k)
                
                # 하이브리드 점수 결합 (0.3 * TF-IDF + 0.7 * Vector)
                merged = {}
                for r in vector_results:
                    idx = r.get("index", -1)
                    if idx >= 0:
                        merged[idx] = {
                            "text": r.get("text", ""),
                            "vector_score": r.get("score", 0.0),
                            "tfidf_score": 0.0
                        }
                
                for r in tfidf_results:
                    idx = r.get("index", -1)
                    if idx >= 0:
                        if idx in merged:
                            merged[idx]["tfidf_score"] = r.get("score", 0.0)
                        else:
                            merged[idx] = {
                                "text": r.get("text", ""),
                                "vector_score": 0.0,
                                "tfidf_score": r.get("score", 0.0)
                            }
                
                # 최종 점수 계산
                final_results = []
                for idx, data in merged.items():
                    final_score = 0.3 * data["tfidf_score"] + 0.7 * data["vector_score"]
                    final_results.append({
                        "text": data["text"],
                        "score": final_score,
                        "index": idx
                    })
                
                final_results.sort(key=lambda x: -x["score"])
                return final_results[:top_k]
                
            except Exception as e:
                logger.warning(f"Hybrid search failed: {e}. Using simple retrieval.")
        
        # 단순 임베딩 검색
        if self.embedding_model is not None:
            try:
                query_embedding = self.embedding_model.encode([query], show_progress_bar=False)[0]
                
                if self.embeddings is None:
                    chunk_texts = list(self.index.values())
                    self.embeddings = self.compute_embeddings(chunk_texts)
                
                if self.embeddings is not None:
                    # FAISS 인덱스 사용
                    if self.faiss_index is not None:
                        query_emb = query_embedding.reshape(1, -1).astype('float32')
                        distances, indices = self.faiss_index.search(query_emb, top_k)
                        
                        results = []
                        for i, idx in enumerate(indices[0]):
                            if idx < len(self.chunks):
                                # 거리를 유사도로 변환 (1 / (1 + distance))
                                score = 1.0 / (1.0 + float(distances[0][i]))
                                results.append({
                                    "text": self.chunks[idx],
                                    "score": score,
                                    "index": int(idx)
                                })
                        return results
                    else:
                        # 코사인 유사도 계산
                        scores = np.dot(self.embeddings, query_embedding) / (
                            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
                        )
                        
                        top_indices = np.argsort(scores)[::-1][:top_k]
                        
                        results = []
                        for idx in top_indices:
                            results.append({
                                "text": self.index[idx],
                                "score": float(scores[idx]),
                                "index": int(idx)
                            })
                        return results
            except Exception as e:
                logger.warning(f"Embedding-based retrieval failed: {e}. Using keyword retrieval.")
        
        # 키워드 기반 검색 (fallback)
        return self._tfidf_search(query, top_k)
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict]:
        """벡터 검색"""
        if self.embedding_model is None or self.embeddings is None:
            return []
        
        try:
            query_embedding = self.embedding_model.encode([query], show_progress_bar=False)[0]
            scores = np.dot(self.embeddings, query_embedding) / (
                np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for idx in top_indices:
                results.append({
                    "text": self.index[idx],
                    "score": float(scores[idx]),
                    "index": int(idx)
                })
            return results
        except Exception:
            return []
    
    def _tfidf_search(self, query: str, top_k: int) -> List[Dict]:
        """TF-IDF 기반 키워드 검색"""
        from collections import Counter
        
        query_tokens = re.findall(r"[\w가-힣_-]+", query.lower())
        if not query_tokens:
            return []
        
        scored = []
        for idx, chunk in self.index.items():
            chunk_tokens = re.findall(r"[\w가-힣_-]+", chunk.lower())
            if not chunk_tokens:
                continue
            
            # 간단한 TF-IDF 점수 계산
            chunk_counter = Counter(chunk_tokens)
            score = sum(chunk_counter.get(token, 0) for token in query_tokens) / max(len(chunk_tokens), 1)
            
            if score > 0:
                scored.append({
                    "text": chunk,
                    "score": score,
                    "index": idx
                })
        
        scored.sort(key=lambda x: -x["score"])
        return scored[:top_k]
    
    def save_index(self, path: Optional[str] = None):
        """
        인덱스 저장 (FAISS 인덱스 포함)
        
        Args:
            path: 저장 경로
        """
        if path is None:
            path = os.path.join(self.embedding_path, "rag_index.json")
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        import json
        index_data = {
            "chunks": self.chunks,
            "index": self.index
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # FAISS 인덱스 저장
        if self.faiss_index is not None and FAISS_AVAILABLE:
            faiss_path = self.config.get("embedding", {}).get("index_path", 
                                                               os.path.join(self.embedding_path, "faiss_index.bin"))
            try:
                # Windows에서 한글 경로 처리
                faiss_path_normalized = _get_windows_short_path(faiss_path)
                faiss.write_index(self.faiss_index, faiss_path_normalized)
                logger.info(f"FAISS index saved: {faiss_path}")
            except Exception as e:
                logger.warning(f"FAISS index save failed: {e}")
    
    def load_index(self, path: Optional[str] = None):
        """
        인덱스 로드 (FAISS 인덱스 포함)
        
        Args:
            path: 로드 경로
        """
        # 이미 로드된 경우 중복 로드 방지
        if self.faiss_index is not None and len(self.chunks) > 0:
            return  # 이미 로드되었으므로 재로드 불필요
        
        if path is None:
            path = os.path.join(self.embedding_path, "rag_index.json")
        
        # 상대 경로를 절대 경로로 변환
        if path and not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            path = os.path.join(base_dir, path)
            path = os.path.normpath(path)
        
        # FAISS 인덱스 경로 확인
        faiss_path = self.config.get("embedding", {}).get("index_path", 
                                                           os.path.join(self.embedding_path, "faiss_index.bin"))
        
        # 상대 경로를 절대 경로로 변환
        if faiss_path and not os.path.isabs(faiss_path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            faiss_path = os.path.join(base_dir, faiss_path)
            faiss_path = os.path.normpath(faiss_path)
        
        has_faiss_file = os.path.exists(faiss_path) and FAISS_AVAILABLE
        
        # rag_index.json 파일 확인
        has_index_file = os.path.exists(path)
        
        # 불일치 감지 및 경고
        if has_faiss_file and not has_index_file:
            logger.warning(f"FAISS 인덱스 파일은 있지만 rag_index.json이 없습니다. 인덱스 불일치 가능성.")
            logger.warning(f"FAISS 인덱스 파일: {faiss_path}")
            logger.warning(f"rag_index.json 파일: {path}")
            logger.warning(f"청크 데이터 없이 FAISS 인덱스만 로드하지 않습니다. 인덱스 재구축이 필요합니다.")
            return
        
        if not has_index_file:
            logger.warning(f"Index file not found: {path}")
            return
        
        import json
        with open(path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        self.chunks = index_data.get("chunks", [])
        self.index = {int(k): v for k, v in index_data.get("index", {}).items()}
        
        # FAISS 인덱스 로드
        if has_faiss_file:
            try:
                # Windows에서 한글 경로 처리
                faiss_path_normalized = _get_windows_short_path(faiss_path)
                self.faiss_index = faiss.read_index(faiss_path_normalized)
                logger.info(f"FAISS index loaded: {faiss_path}")
                
                # FAISS 인덱스 크기와 청크 수 일치 확인
                faiss_size = self.faiss_index.ntotal
                chunks_size = len(self.chunks)
                if faiss_size != chunks_size:
                    logger.warning(f"FAISS 인덱스 크기({faiss_size})와 청크 수({chunks_size})가 일치하지 않습니다.")
                    logger.warning(f"인덱스 재구축을 권장합니다.")
            except Exception as e:
                logger.warning(f"FAISS index load failed: {e}")
                self.faiss_index = None
    
    def retrieve_with_context(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        하이브리드 검색 후, 각 문서 chunk와 score를 상세 정보와 함께 반환
        인용 기반 응답 생성을 위한 확장 버전
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 k개 결과
            
        Returns:
            [{"doc_id": int, "text": str, "score": float, "index": int, "metadata": dict}] 리스트
        """
        # 기본 검색 수행
        results = self.retrieve(query, top_k=top_k, use_hybrid=True)
        
        # 상세 정보 추가
        detailed_results = []
        for i, result in enumerate(results):
            idx = result.get("index", i)
            text = result.get("text", "")
            score = result.get("score", 0.0)
            
            # 🔥 개선: 메타데이터 추출 (chunk 정보에서, 교리 문서 메타데이터 포함)
            metadata = {}
            if idx < len(self.chunks):
                chunk_info = self.chunks[idx] if isinstance(self.chunks[idx], dict) else {"text": self.chunks[idx]}
                metadata = {
                    "chunk_index": idx,
                    "start": chunk_info.get("start", 0),
                    "end": chunk_info.get("end", len(text)),
                    "doc_index": chunk_info.get("doc_index", 0),
                    "chunk_index_in_doc": chunk_info.get("chunk_index", 0),
                    "source": chunk_info.get("source", "")
                }
                
                # 🔥 교리 문서 메타데이터 포함
                if chunk_info.get("chunk_type") == "doctrine_statement":
                    metadata.update({
                        "doctrine_id": chunk_info.get("doctrine_id"),
                        "statement_id": chunk_info.get("statement_id"),
                        "statement_text": chunk_info.get("statement_text"),
                        "interpretation": chunk_info.get("interpretation"),
                        "mett_c_elements": chunk_info.get("mett_c_elements", []),
                        "operation_type": chunk_info.get("operation_type")
                    })
            
            # 🔥 메타데이터를 결과에 직접 포함 (하위 호환성)
            result_dict = {
                "doc_id": idx,
                "text": text,
                "score": score,
                "index": idx,
                "metadata": metadata
            }
            
            # 🔥 교리 문서 메타데이터를 최상위 레벨에도 포함
            if metadata.get("doctrine_id"):
                result_dict.update({
                    "doctrine_id": metadata["doctrine_id"],
                    "statement_id": metadata.get("statement_id"),
                    "statement_text": metadata.get("statement_text"),
                    "mett_c_elements": metadata.get("mett_c_elements", [])
                })
            
            detailed_results.append(result_dict)
        
        return detailed_results
    
    def is_available(self) -> bool:
        """
        RAG Manager 사용 가능 여부 확인
        
        Returns:
            사용 가능 여부 (임베딩 모델과 인덱스가 있는 경우 True)
        """
        # 임베딩 모델이 있고, 인덱스가 있으면 사용 가능
        has_model = self.embedding_model is not None
        has_index = len(self.chunks) > 0 or (self.faiss_index is not None and FAISS_AVAILABLE)
        return has_model and has_index

    def get_indexed_sources(self) -> set:
        """
        현재 인덱스에 포함된 문서들의 소스(파일명) 목록 반환
        """
        sources = set()
        for chunk in self.chunks:
            if isinstance(chunk, dict) and "source" in chunk:
                sources.add(chunk["source"])
        return sources




