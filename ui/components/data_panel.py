# ui/components/data_panel.py
# -*- coding: utf-8 -*-
"""
실데이터 패널 컴포넌트 (데이터 편집 및 컬럼 추가 기능 포함)
"""
import streamlit as st
import pandas as pd
import os
from pathlib import Path


def render_data_panel(config, core):
    """실데이터 테이블 표시 및 편집"""
    st.subheader("실데이터 확인 및 편집")
    
    data_paths = config.get("data_paths", {})
    data_lake_path = config.get("data_lake_path", "./data_lake")
    
    if not data_paths:
        st.info("데이터 경로가 설정되지 않았습니다.")
        return
    
    # data_lake 폴더에 실제로 존재하는 파일만 필터링
    base_dir = Path(__file__).parent.parent.parent
    data_lake_dir = base_dir / data_lake_path
    
    # data_lake 폴더의 Excel 파일 목록 가져오기 (backup 폴더 제외)
    available_tables = {}
    if data_lake_dir.exists():
        excel_files = list(data_lake_dir.glob("*.xlsx")) + list(data_lake_dir.glob("*.xls"))
        for excel_file in excel_files:
            table_name = excel_file.stem
            # config에 있는 테이블만 추가 (파일명 기반으로 매칭)
            if table_name in data_paths:
                available_tables[table_name] = data_paths[table_name]
            else:
                # config에 없어도 data_lake에 있으면 추가 (상대 경로 형식으로 저장)
                rel_path = excel_file.relative_to(base_dir)
                available_tables[table_name] = f"./{rel_path.as_posix()}"
    
    # 데이터 로드 버튼
    if st.button("데이터 새로고침"):
        try:
            data = core.data_manager.load_all()
            if data:
                st.session_state.loaded_data = data
                st.success(f"[OK] {len(data)}개 테이블 로드 완료")
                st.rerun()
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
    
    # 테이블 선택 (data_lake에 실제 존재하는 테이블만)
    table_names = list(available_tables.keys())
    if not table_names:
        st.warning("data_lake 폴더에 등록된 데이터 테이블이 없습니다.")
        return
    
    selected_table = st.selectbox("편집할 테이블 선택", table_names, key="data_panel_table_selector")
    
    if selected_table:
        path = available_tables[selected_table]
        
        # 경로 변환
        if not os.path.isabs(path):
            base_dir = Path(__file__).parent.parent.parent
            path = base_dir / path
            path = str(path)
        
        if os.path.exists(path):
            try:
                # Excel 파일 읽기
                if path.endswith('.xlsx') or path.endswith('.xls'):
                    df = pd.read_excel(path)
                elif path.endswith('.csv'):
                    df = pd.read_csv(path)
                else:
                    st.error(f"지원하지 않는 파일 형식: {path}")
                    return
                
                # 통계 정보
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("행 수", len(df))
                with col2:
                    st.metric("열 수", len(df.columns))
                with col3:
                    st.metric("파일", os.path.basename(path))
                
                st.divider()
                
                # 컬럼 추가 기능
                with st.expander("컬럼 추가", expanded=False):
                    new_col_name = st.text_input("새 컬럼명", key=f"new_col_{selected_table}")
                    col_type = st.selectbox("컬럼 타입", ["TEXT", "NUMBER", "DATE"], key=f"col_type_{selected_table}")
                    
                    if st.button(f"컬럼 추가", key=f"add_col_{selected_table}"):
                        if new_col_name:
                            if new_col_name in df.columns:
                                st.error("이미 존재하는 컬럼명입니다.")
                            else:
                                # 기본값 설정
                                if col_type == "TEXT":
                                    default_val = ""
                                elif col_type == "NUMBER":
                                    default_val = 0
                                else:  # DATE
                                    default_val = None
                                
                                df[new_col_name] = default_val
                                
                                # 파일 저장
                                try:
                                    if path.endswith('.xlsx') or path.endswith('.xls'):
                                        df.to_excel(path, index=False, engine='openpyxl')
                                    else:
                                        df.to_csv(path, index=False)
                                    
                                    st.success(f"컬럼 '{new_col_name}' 추가 완료.")
                                    st.info("참고: 원천 DB가 변경되었습니다. 아래 후속 작업을 진행하세요.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"저장 오류: {e}")
                        else:
                            st.warning("컬럼명을 입력하세요.")
                
                st.divider()
                
                # 데이터 편집기
                st.markdown(f"### {selected_table} 데이터 편집")
                edited_df = st.data_editor(
                    df,
                    num_rows="dynamic",
                    width='stretch',
                    height=400,
                    key=f"data_editor_{selected_table}"
                )
                
                # 저장 버튼
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("원천 DB 수정 저장", key=f"save_{selected_table}", type="primary"):
                        try:
                            # 변경사항 확인
                            if not edited_df.equals(df):
                                # 파일 저장
                                if path.endswith('.xlsx') or path.endswith('.xls'):
                                    edited_df.to_excel(path, index=False, engine='openpyxl')
                                else:
                                    edited_df.to_csv(path, index=False)
                                
                                st.success(f"[OK] {selected_table} 수정 저장 완료")
                                st.session_state["db_saved"] = True
                                st.info("참고: 원천 DB가 변경되었습니다. 아래 후속 작업을 진행하세요.")
                                st.rerun()
                            else:
                                st.info("변경사항이 없습니다.")
                        except Exception as e:
                            st.error(f"저장 오류: {e}")
                
                with col2:
                    if st.session_state.get("db_saved", False):
                        st.success("[OK] 데이터가 저장되었습니다. 그래프를 재생성하세요.")
                
            except Exception as e:
                st.error(f"{selected_table} 로드 실패: {e}")
        else:
            st.warning(f"[WARN] {selected_table}: 파일을 찾을 수 없습니다 ({path})")
    
    st.divider()
    
    # 데이터 요약
    if st.checkbox("데이터 요약 보기"):
        try:
            data = core.data_manager.load_all()
            if data:
                st.markdown("#### 데이터 요약")
                summary_data = []
                for name, df in data.items():
                    summary_data.append({
                        "테이블": name,
                        "행 수": len(df),
                        "열 수": len(df.columns),
                        "열 이름": ", ".join(df.columns[:5].tolist()) + ("..." if len(df.columns) > 5 else "")
                    })
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, width='stretch')
        except Exception as e:
            st.error(f"데이터 요약 생성 실패: {e}")

