#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 인덱스 재구축 스크립트
신규 추가된 RAG 문서를 인덱스에 반영
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.orchestrator import Orchestrator
from core_pipeline.rag_manager import RAGManager
import yaml

def load_config():
    """설정 파일 로드"""
    config_path = project_root / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

def rebuild_rag_index():
    """RAG 인덱스 재구축"""
    print("=" * 60)
    print("RAG 인덱스 재구축 시작")
    print("=" * 60)
    
    # 설정 로드
    config = load_config()
    
    # Orchestrator 초기화
    print("\n[1/3] Orchestrator 초기화 중...")
    orchestrator = Orchestrator(config)
    
    # RAG Manager 확인
    rag_manager = orchestrator.core.rag_manager
    if not rag_manager:
        print("[ERROR] RAG Manager를 초기화할 수 없습니다.")
        return False
    
    # 임베딩 모델 확인
    if rag_manager.embedding_model is None:
        print("[INFO] 임베딩 모델 로드 중...")
        rag_manager.load_embeddings()
        if rag_manager.embedding_model is None:
            print("[ERROR] 임베딩 모델을 로드할 수 없습니다.")
            return False
    
    # RAG 문서 디렉토리 확인
    rag_docs_path = project_root / "knowledge" / "rag_docs"
    if not rag_docs_path.exists():
        print(f"[ERROR] RAG 문서 디렉토리가 없습니다: {rag_docs_path}")
        return False
    
    # 문서 파일 목록 확인
    doc_files = list(rag_docs_path.glob("*.txt")) + list(rag_docs_path.glob("*.md"))
    if not doc_files:
        print(f"[ERROR] RAG 문서가 없습니다: {rag_docs_path}")
        return False
    
    print(f"\n[2/3] 문서 로드 중... ({len(doc_files)}개 파일)")
    docs = []
    doc_names = []
    for doc_file in sorted(doc_files):
        try:
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    docs.append(content)
                    doc_names.append(doc_file.name)
                    print(f"  ✓ {doc_file.name}")
        except Exception as e:
            print(f"  ✗ {doc_file.name}: {e}")
    
    if not docs:
        print("[ERROR] 로드할 문서가 없습니다.")
        return False
    
    # 🔥 개선: 청킹 및 인덱스 구축 (교리 문서는 전용 청킹 사용)
    print(f"\n[3/3] 인덱스 구축 중... ({len(docs)}개 문서)")
    try:
        # 교리 문서와 일반 문서 분리
        doctrine_docs = []
        doctrine_names = []
        normal_docs = []
        normal_names = []
        
        for doc, name in zip(docs, doc_names):
            if name and name.startswith("DOCTRINE-") and name.endswith(".md"):
                doctrine_docs.append(doc)
                doctrine_names.append(name)
            else:
                normal_docs.append(doc)
                normal_names.append(name)
        
        all_chunks = []
        
        # 교리 문서는 전용 청킹 함수 사용
        if doctrine_docs:
            print(f"  📚 교리 문서 청킹 중... ({len(doctrine_docs)}개)")
            doctrine_chunks = rag_manager.chunk_doctrine_documents(doctrine_docs, doc_names=doctrine_names)
            all_chunks.extend(doctrine_chunks)
            print(f"  ✓ 교리 문서 청크 생성 완료: {len(doctrine_chunks)}개 청크")
        
        # 일반 문서는 기본 청킹 함수 사용
        if normal_docs:
            print(f"  📄 일반 문서 청킹 중... ({len(normal_docs)}개)")
            normal_chunks = rag_manager.chunk_documents(normal_docs, doc_names=normal_names)
            all_chunks.extend(normal_chunks)
            print(f"  ✓ 일반 문서 청크 생성 완료: {len(normal_chunks)}개 청크")
        
        print(f"  ✓ 총 청크 생성 완료: {len(all_chunks)}개 청크")
        
        rag_manager.build_index(all_chunks, use_faiss=True)
        print(f"  ✓ FAISS 인덱스 구축 완료")
        
        # 인덱스 저장
        rag_manager.save_index()
        print(f"  ✓ 인덱스 저장 완료")
        
        print("\n" + "=" * 60)
        print("✅ RAG 인덱스 재구축 완료!")
        print("=" * 60)
        print(f"  - 문서 수: {len(docs)}개 (교리: {len(doctrine_docs)}개, 일반: {len(normal_docs)}개)")
        print(f"  - 청크 수: {len(all_chunks)}개")
        if rag_manager.faiss_index:
            print(f"  - FAISS 인덱스 크기: {rag_manager.faiss_index.ntotal}개 벡터")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 인덱스 구축 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = rebuild_rag_index()
    sys.exit(0 if success else 1)

