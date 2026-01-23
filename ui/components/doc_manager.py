# ui/components/doc_manager.py
# -*- coding: utf-8 -*-
"""
RAG 문서 관리 패널
사용자가 새로운 문서를 업로드하고 RAG 인덱스 자동 갱신
"""
import streamlit as st
import os
from pathlib import Path
from datetime import datetime
from typing import Dict
import pandas as pd
import traceback


def get_rag_index_status(rag_manager) -> Dict:
    """RAG 인덱스 상태 종합 확인"""
    has_chunks = len(rag_manager.chunks) > 0
    has_index = bool(rag_manager.index)
    has_faiss = rag_manager.faiss_index is not None
    
    # FAISS 인덱스 크기 확인
    faiss_size = 0
    if has_faiss:
        try:
            faiss_size = rag_manager.faiss_index.ntotal
        except:
            faiss_size = 0
    
    # 종합 상태 판단
    if has_faiss and (has_chunks or has_index):
        status = "완전"
        status_level = "success"
        message = "인덱스가 정상적으로 구성되었습니다."
    elif has_faiss:
        status = "부분"
        status_level = "warning"
        message = "FAISS 인덱스는 있지만 청크 데이터가 없습니다."
    elif has_chunks or has_index:
        status = "부분"
        status_level = "warning"
        message = "청크 데이터는 있지만 FAISS 인덱스가 없습니다."
    else:
        status = "없음"
        status_level = "info"
        message = "인덱스가 생성되지 않았습니다."
    
    return {
        "status": status,
        "status_level": status_level,
        "message": message,
        "has_chunks": has_chunks,
        "has_index": has_index,
        "has_faiss": has_faiss,
        "chunks_count": len(rag_manager.chunks),
        "index_size": len(rag_manager.index) if rag_manager.index else 0,
        "faiss_size": faiss_size
    }


def rebuild_index_from_docs(core):
    """문서 디렉토리에서 인덱스 재구축"""
    with st.spinner("인덱스 재구축 중..."):
        try:
            # 문서 디렉토리에서 모든 문서 로드
            rag_docs_path = Path("./knowledge/rag_docs")
            doc_files = list(rag_docs_path.glob("*.*"))
            doc_files = [f for f in doc_files if f.suffix.lower() in ['.txt', '.pd', '.md', '.docx']]
            
            if not doc_files:
                st.error("재구축할 문서가 없습니다. 먼저 문서를 업로드하세요.")
                return
            
            # 모든 문서 읽기 및 분리 (교리 vs 일반)
            doctrine_docs = []
            doctrine_doc_names = []
            general_docs = []
            general_doc_names = []
            
            for doc_file in doc_files:
                if doc_file.suffix.lower() in ['.txt', '.md']:
                    try:
                        with open(doc_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.strip():
                                # 파일명이나 내용으로 교리 문서 판단
                                is_doctrine = (
                                    doc_file.name.upper().startswith("DOCTRINE") or 
                                    "# Doctrine_ID:" in content
                                )
                                
                                if is_doctrine:
                                    doctrine_docs.append(content)
                                    doctrine_doc_names.append(doc_file.name)
                                else:
                                    general_docs.append(content)
                                    general_doc_names.append(doc_file.name)
                    except Exception as e:
                        st.warning(f"문서 읽기 실패 ({doc_file.name}): {e}")
                else:
                    st.warning(f"{doc_file.suffix} 형식은 아직 지원되지 않습니다: {doc_file.name}")
            
            all_chunks = []
            
            # 1. 교리 문서 청킹 (특수 로직)
            if doctrine_docs:
                try:
                    doctrine_chunks = core.rag_manager.chunk_doctrine_documents(
                        doctrine_docs, 
                        doc_names=doctrine_doc_names
                    )
                    all_chunks.extend(doctrine_chunks)
                    st.info(f"교리 문서 {len(doctrine_docs)}개 처리됨 ({len(doctrine_chunks)} 청크)")
                except Exception as e:
                    st.warning(f"교리 문서 청킹 중 오류: {e}")
            
            # 2. 일반 문서 청킹
            if general_docs:
                try:
                    general_chunks = core.rag_manager.chunk_documents(
                        general_docs, 
                        doc_names=general_doc_names
                    )
                    all_chunks.extend(general_chunks)
                    st.info(f"일반 문서 {len(general_docs)}개 처리됨 ({len(general_chunks)} 청크)")
                except Exception as e:
                    st.warning(f"일반 문서 청킹 중 오류: {e}")

            if all_chunks:
                # 인덱스 재구축 (전체 청크로)
                core.rag_manager.build_index(all_chunks, use_faiss=True)
                core.rag_manager.save_index()
                st.success(f"✅ 인덱스 재구축 완료! (총 {len(all_chunks)} 청크)")
                st.rerun()
            else:
                st.error("생성된 청크가 없습니다. 문서 내용을 확인하세요.")
                
        except Exception as e:
            st.error(f"인덱스 재구축 실패: {e}")
            with st.expander("오류 상세"):
                st.code(traceback.format_exc())


def rebuild_faiss_index(rag_manager):
    """FAISS 인덱스만 재구축"""
    with st.spinner("FAISS 인덱스 재구축 중..."):
        try:
            if not rag_manager.chunks:
                st.error("청크 데이터가 없어 FAISS 인덱스를 구축할 수 없습니다.")
                return
            
            if rag_manager.embedding_model is None:
                st.error("임베딩 모델이 로드되지 않았습니다.")
                return
            
            # FAISS 인덱스 재구축
            embeddings = rag_manager.compute_embeddings(rag_manager.chunks)
            if embeddings is not None:
                import faiss
                dimension = embeddings.shape[1]
                rag_manager.faiss_index = faiss.IndexFlatL2(dimension)
                rag_manager.faiss_index.add(embeddings.astype('float32'))
                rag_manager.embeddings = embeddings
                
                # 저장
                rag_manager.save_index()
                st.success("✅ FAISS 인덱스 재구축 완료!")
                st.rerun()
            else:
                st.error("임베딩 생성 실패")
        except Exception as e:
            st.error(f"FAISS 인덱스 재구축 실패: {e}")
            with st.expander("오류 상세"):
                st.code(traceback.format_exc())


def render_index_status(index_status: Dict, rag_manager=None, core=None, show_fix_option: bool = True, key_prefix: str = "index_status"):
    """인덱스 상태 표시 및 수정 옵션 제공"""
    # 종합 상태 메시지
    if index_status["status_level"] == "success":
        st.success(f"✅ {index_status['message']}")
    elif index_status["status_level"] == "warning":
        st.warning(f"⚠️ {index_status['message']}")
    else:
        st.info(f"ℹ️ {index_status['message']}")
    
    # 상세 정보
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if index_status["has_chunks"] or index_status["has_index"]:
            size = max(index_status["chunks_count"], index_status["index_size"])
            st.metric("청크 인덱스", f"{size}개")
        else:
            st.metric("청크 인덱스", "0개")
    
    with col2:
        if index_status["has_faiss"]:
            st.metric("FAISS 인덱스", f"{index_status['faiss_size']}개")
        else:
            st.metric("FAISS 인덱스", "없음")
    
    with col3:
        if index_status["has_chunks"] and index_status["has_faiss"]:
            st.success("✅ 완전")
        elif index_status["has_chunks"] or index_status["has_faiss"]:
            st.warning("⚠️ 부분")
        else:
            st.info("ℹ️ 없음")
    
    # 불일치 상태일 때 수정 옵션 제공
    if show_fix_option and index_status["status"] == "부분" and rag_manager and core:
        st.divider()
        st.warning("⚠️ 인덱스 불일치 감지")
        
        if index_status["has_faiss"] and not (index_status["has_chunks"] or index_status["has_index"]):
            st.markdown("""
            **문제:** FAISS 인덱스는 있지만 청크 데이터가 없습니다.
            
            **원인:** `rag_index.json` 파일이 없거나 손상되었을 수 있습니다.
            
            **해결 방법:** 아래 버튼을 클릭하여 인덱스를 재구축하세요.
            """)
            
            if st.button("🔄 인덱스 재구축", type="primary", key=f"{key_prefix}_fix_index_mismatch"):
                rebuild_index_from_docs(core)
        elif (index_status["has_chunks"] or index_status["has_index"]) and not index_status["has_faiss"]:
            st.markdown("""
            **문제:** 청크 데이터는 있지만 FAISS 인덱스가 없습니다.
            
            **해결 방법:** 아래 버튼을 클릭하여 FAISS 인덱스를 재구축하세요.
            """)
            
            if st.button("🔄 FAISS 인덱스 재구축", type="primary", key=f"{key_prefix}_rebuild_faiss_index"):
                rebuild_faiss_index(rag_manager)


def render_doc_manager(core, key_prefix="doc_manager"):
    """RAG 문서 관리 패널 렌더링"""
    """RAG 문서 관리 패널 렌더링"""
    # st.header("RAG 문서 관리") - Parent View에서 제어하도록 제거
    
    # 문서 디렉토리 경로
    rag_docs_path = Path("./knowledge/rag_docs")
    rag_docs_path.mkdir(parents=True, exist_ok=True)
    
    # 현재 문서 목록
    doc_files = list(rag_docs_path.glob("*.*"))
    doc_files = [f for f in doc_files if f.suffix.lower() in ['.txt', '.pdf', '.md', '.docx']]
    
    # 문서 목록 표시
    st.subheader("현재 문서 목록")
    
    # 인덱스된 문서 목록 가져오기
    try:
        indexed_sources = core.rag_manager.get_indexed_sources()
    except AttributeError:
        # Streamlit 핫 리로딩 시 오래된 객체가 남아있을 경우 대비
        st.warning("⚠️ 시스템 업데이트가 감지되었습니다. 최신 기능을 적용하려면 페이지를 새로고침하세요.")
        if st.button("🔄 페이지 새로고침"):
            st.rerun()
        indexed_sources = set()
    
    if doc_files:
        doc_data = []
        for doc_file in doc_files:
            stat = doc_file.stat()
            is_indexed = doc_file.name in indexed_sources
            
            doc_data.append({
                "파일명": doc_file.name,
                "크기(KB)": f"{stat.st_size / 1024:.2f}",
                "수정일": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "상태": "✅Indexed" if is_indexed else "❌Not Indexed"
            })
        
        doc_df = pd.DataFrame(doc_data)
        st.dataframe(doc_df, width='stretch', hide_index=True)
        st.caption(f"총 {len(doc_files)}개 문서 중 {len(indexed_sources)}개 인덱스됨")
    else:
        st.info("등록된 문서가 없습니다.")
    
    # 상시 노출: 전체 인덱스 재구축 버튼
    if st.button("🔄 전체 인덱스 재구축 (메타데이터 갱신)", key=f"{key_prefix}_rebuild_index_main", width="stretch"):
        rebuild_index_from_docs(core)
    
    st.divider()
    
    # 파일 업로드
    st.subheader("문서 업로드")
    uploaded_file = st.file_uploader(
        "문서 파일 선택",
        type=['txt', 'pdf', 'md', 'docx'],
        help="텍스트, PDF, Markdown, Word 문서를 업로드할 수 있습니다.",
        key=f"{key_prefix}_file_uploader"
    )
    
    if uploaded_file is not None:
        # 파일 저장
        file_path = rag_docs_path / uploaded_file.name
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"[OK] 파일 업로드 완료: {uploaded_file.name}")
        
        st.success(f"[OK] 파일 업로드 완료: {uploaded_file.name}")
        
        st.success(f"[OK] 파일 업로드 완료: {uploaded_file.name}")
        
        # 1. 인덱스 업데이트 (증분)
        if st.button("➕ 이 파일만 인덱스 추가", key=f"{key_prefix}_add_to_index"):
            with st.spinner("인덱스에 추가 중..."):
                try:
                    # 문서 읽기
                    if file_path.suffix == '.txt':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    else:
                        st.warning(f"{file_path.suffix} 형식은 아직 지원되지 않습니다.")
                        content = ""
                        
                    if content:
                        # 청킹 (파일명 메타데이터 포함)
                        chunks = core.rag_manager.chunk_documents([content], doc_names=[uploaded_file.name])
                        
                        # 증분 색인 (기존 인덱스에 추가)
                        core.rag_manager.add_to_index(chunks)
                        
                        # 저장
                        core.rag_manager.save_index()
                        
                        st.success(f"[OK] '{uploaded_file.name}' 인덱스 추가 완료!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"인덱스 추가 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    st.divider()
    
    st.divider()
    
    # 문서 삭제
    if doc_files:
        st.subheader("문서 삭제")
        selected_doc = st.selectbox(
            "삭제할 문서 선택",
            [""] + [f.name for f in doc_files],
            key=f"{key_prefix}_delete_selector"
        )
        
        if selected_doc and st.button("삭제", key=f"{key_prefix}_delete_button"):
            doc_path = rag_docs_path / selected_doc
            try:
                doc_path.unlink()
                st.success(f"[OK] 문서 삭제 완료: {selected_doc}")
                st.rerun()
            except Exception as e:
                st.error(f"문서 삭제 실패: {e}")
    
    # 인덱스 정보
    st.divider()
    st.subheader("인덱스 정보")
    
    # 인덱스 상태 종합 확인
    index_status = get_rag_index_status(core.rag_manager)
    render_index_status(index_status, rag_manager=core.rag_manager, core=core, show_fix_option=True, key_prefix="doc_manager_index_status")





