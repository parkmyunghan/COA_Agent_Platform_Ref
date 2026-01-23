# ui/components/sparql_query_panel.py
# -*- coding: utf-8 -*-
"""
SPARQL 쿼리 패널 컴포넌트
지식그래프 조회를 위한 SPARQL 쿼리 실행 UI
"""
import streamlit as st
import pandas as pd
from rdflib import Graph


def render_sparql_query_panel(core):
    """SPARQL 쿼리 실행 패널"""
    st.subheader("SPARQL 쿼리 실행")
    
    graph = core.ontology_manager.graph
    
    if graph is None or len(list(graph.triples((None, None, None)))) == 0:
        st.warning("[WARN] 그래프가 생성되지 않았습니다. 먼저 그래프를 생성하세요.")
        return
    
    # 예제 쿼리 (현재 데이터 구조에 맞게 수정)
    example_queries = {
        "모든 위협 상황 조회": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?threat ?threatType ?threatLevel ?location ?axis ?mission WHERE {
  ?threat a ns:위협상황 .
  OPTIONAL { ?threat ns:위협유형코드 ?threatType . }
  OPTIONAL { ?threat ns:위협수준 ?threatLevel . }
  OPTIONAL { ?threat ns:발생위치셀ID ?location . }
  OPTIONAL { ?threat ns:관련축선ID ?axis . }
  OPTIONAL { ?threat ns:관련임무ID ?mission . }
}
LIMIT 50
""",
        "위협 수준이 높은 위협 상황 조회 (High)": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?threat ?threatType ?threatLevel ?location ?axis WHERE {
  ?threat a ns:위협상황 .
  ?threat ns:위협수준 ?threatLevel .
  OPTIONAL { ?threat ns:위협유형코드 ?threatType . }
  OPTIONAL { ?threat ns:발생위치셀ID ?location . }
  OPTIONAL { ?threat ns:관련축선ID ?axis . }
  FILTER (CONTAINS(STR(?threatLevel), "High") || CONTAINS(STR(?threatLevel), "high") || ?threatLevel = "3" || ?threatLevel = "4" || ?threatLevel = "5")
}
ORDER BY ?threatLevel
LIMIT 20
""",
        "특정 축선의 위협 상황 조회": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?threat ?threatType ?threatLevel ?location ?axis ?axisName WHERE {
  ?threat a ns:위협상황 .
  { ?threat ns:관련축선ID ?axis . } UNION { ?threat ns:has전장축선 ?axis . }
  OPTIONAL { ?axis rdfs:label ?axisName . }
  OPTIONAL { ?threat ns:위협유형코드 ?threatType . }
  OPTIONAL { ?threat ns:위협수준 ?threatLevel . }
  OPTIONAL { ?threat ns:발생위치셀ID ?location . }
}
LIMIT 20
""",
        "아군 부대 현황 조회": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?unit ?unitName ?combatPower ?sidc ?axis ?axisLabel WHERE {
  # 아군부대현황(Unit)과 아군가용자산(Asset) 모두 조회
  { ?unit a ns:아군가용자산 . } UNION { ?unit a ns:아군부대현황 . }
  
  OPTIONAL { ?unit rdfs:label ?unitName . }
  
  # 전투력: hasCombatPower(신규) 또는 전투력(기존)
  OPTIONAL { 
    { ?unit ns:hasCombatPower ?combatPower . } 
    UNION 
    { ?unit ns:전투력 ?combatPower . } 
    UNION
    { ?unit ns:전투력지수 ?combatPower . }
  }
  
  OPTIONAL { ?unit ns:hasSIDC ?sidc . }
  
  OPTIONAL { 
    { ?unit ns:has전장축선 ?axis . } UNION { ?unit ns:locatedIn ?axis . } UNION { ?unit ns:배치축선ID ?axis . }
    OPTIONAL { ?axis rdfs:label ?axisLabel . }
  }
}
ORDER BY DESC(xsd:decimal(?combatPower))
LIMIT 30
""",
        "적군 부대 현황 조회": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?unit ?unitName ?combatPower ?sidc ?axis ?axisLabel WHERE {
  ?unit a ns:적군부대현황 .
  OPTIONAL { ?unit rdfs:label ?unitName . }
  
  # 전투력: hasCombatPower(신규) 또는 전투력(기존)
  OPTIONAL { 
    { ?unit ns:hasCombatPower ?combatPower . } 
    UNION 
    { ?unit ns:전투력 ?combatPower . } 
    UNION
    { ?unit ns:전투력지수 ?combatPower . }
  }
  
  OPTIONAL { ?unit ns:hasSIDC ?sidc . }
  
  OPTIONAL { 
    { ?unit ns:has전장축선 ?axis . } UNION { ?unit ns:locatedIn ?axis . } UNION { ?unit ns:배치축선ID ?axis . }
    OPTIONAL { ?axis rdfs:label ?axisLabel . }
  }
}
ORDER BY DESC(xsd:decimal(?combatPower))
LIMIT 30
""",
        "전장축선 정보 조회": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?axis ?axisName ?axisType ?description WHERE {
  ?axis a ns:전장축선 .
  OPTIONAL { ?axis ns:축선명 ?axisName . }
  OPTIONAL { ?axis ns:축선유형 ?axisType . }
  OPTIONAL { ?axis ns:축선설명 ?description . }
}
LIMIT 20
""",
        "임무 정보 조회": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?mission ?missionName ?missionType ?primaryAxis ?commanderIntent WHERE {
  ?mission a ns:임무정보 .
  OPTIONAL { ?mission ns:임무명 ?missionName . }
  OPTIONAL { ?mission ns:임무종류 ?missionType . }
  OPTIONAL { ?mission ns:주공축선ID ?primaryAxis . }
  OPTIONAL { ?mission ns:지휘관의도 ?commanderIntent . }
}
LIMIT 20
""",
        "관계 탐색 (2-hop)": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?entity1 ?relation1 ?entity2 ?relation2 ?entity3 WHERE {
  ?entity1 ?relation1 ?entity2 .
  ?entity2 ?relation2 ?entity3 .
  FILTER (?entity1 != ?entity3)
}
LIMIT 20
""",
        "적군부대현황 클래스 확인 (디버깅용)": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?unit ?type WHERE {
  ?unit rdf:type ns:적군부대현황 .
  BIND("ns:적군부대현황" AS ?type)
}
LIMIT 10
""",
        "적군부대현황 모든 속성 확인 (디버깅용)": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?unit ?predicate ?object WHERE {
  ?unit rdf:type ns:적군부대현황 .
  ?unit ?predicate ?object .
}
LIMIT 50
""",
        "모든 클래스 타입 확인 (디버깅용)": """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?class (COUNT(?instance) AS ?count) WHERE {
  ?instance rdf:type ?class .
}
GROUP BY ?class
ORDER BY DESC(?count)
LIMIT 20
""",
        "모든 속성 조회 (디버깅용)": """
PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
}
LIMIT 50
"""
    }
    
    # 쿼리 선택 변경 시 쿼리 텍스트 업데이트 함수
    def update_query():
        if st.session_state.sparql_example_selector != "직접 입력":
            st.session_state.sparql_query_input = example_queries[st.session_state.sparql_example_selector]
        else:
            st.session_state.sparql_query_input = """PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
}
LIMIT 10"""
    
    # 초기값 설정
    if "sparql_query_input" not in st.session_state:
        st.session_state.sparql_query_input = """PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
}
LIMIT 10"""
    
    # 쿼리 선택
    selected_example = st.selectbox(
        "예제 쿼리 선택",
        ["직접 입력"] + list(example_queries.keys()),
        key="sparql_example_selector",
        on_change=update_query
    )
    
    # 선택이 변경되었을 때 쿼리 텍스트 업데이트 (on_change가 실행되지 않는 경우 대비)
    if selected_example != "직접 입력":
        if st.session_state.sparql_query_input != example_queries[selected_example]:
            st.session_state.sparql_query_input = example_queries[selected_example]
    else:
        default_query = """PREFIX ns: <http://coa-agent-platform.org/ontology#>
SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
}
LIMIT 10"""
        if st.session_state.sparql_query_input != default_query:
            st.session_state.sparql_query_input = default_query
    
    query_text = st.text_area(
        "SPARQL 쿼리 입력",
        value=st.session_state.sparql_query_input,
        height=200,
        key="sparql_query_input",
        help="SPARQL 쿼리를 입력하세요. PREFIX는 자동으로 추가됩니다."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        execute_button = st.button("▶ 쿼리 실행", type="primary")
    
    with col2:
        if st.button("쿼리 초기화"):
            st.rerun()
    
    if execute_button:
        if not query_text.strip():
            st.error("쿼리를 입력하세요.")
            return
        
        try:
            with st.spinner("쿼리 실행 중..."):
                # PREFIX 자동 추가 (통일된 네임스페이스 사용)
                if "PREFIX" not in query_text.upper():
                    query_text = """PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
""" + query_text
                
                # 쿼리 실행
                results = core.ontology_manager.query(query_text)
                original_query = query_text
                auto_fixed = False
                
                # 결과가 없고 다른 네임스페이스를 사용한 경우 자동으로 ns:로 변환 시도
                if not results and ("def:" in query_text or "ns1:" in query_text):
                    # def: 또는 ns1:를 ns:로 자동 변환
                    fixed_query = query_text.replace("def:", "ns:").replace("ns1:", "ns:")
                    fixed_query = fixed_query.replace(
                        "PREFIX def: <http://defense-ai.kr/ontology#>",
                        "PREFIX ns: <http://coa-agent-platform.org/ontology#>"
                    )
                    # 추가로 rdfs: PREFIX가 없으면 추가 (부대명 등에서 사용)
                    if "PREFIX rdfs:" not in fixed_query and ("부대명" in fixed_query or "rdfs:label" in fixed_query):
                        fixed_query = fixed_query.replace(
                            "PREFIX ns: <http://coa-agent-platform.org/ontology#>",
                            """PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"""
                        )
                    
                    # 속성명 자동 변환
                    # 부대명 -> rdfs:label
                    fixed_query = fixed_query.replace("ns:부대명", "rdfs:label")
                    # 전투력 -> 전투력지수
                    fixed_query = fixed_query.replace("ns:전투력 ", "ns:전투력지수 ")
                    fixed_query = fixed_query.replace("ns:전투력)", "ns:전투력지수)")
                    fixed_query = fixed_query.replace("ns:전투력.", "ns:전투력지수.")
                    fixed_query = fixed_query.replace("ns:전투력;", "ns:전투력지수;")
                    # 배치축선ID -> has전장축선
                    fixed_query = fixed_query.replace("ns:배치축선ID", "ns:has전장축선")
                    
                    try:
                        results = core.ontology_manager.query(fixed_query)
                        if results:
                            auto_fixed = True
                            query_text = fixed_query
                            st.success("💡 쿼리를 자동으로 수정하여 재실행했습니다. (네임스페이스 및 속성명 변환)")
                    except Exception as e:
                        pass  # 변환된 쿼리도 실패하면 원래 쿼리 결과 사용
                
                if results:
                    # 결과를 DataFrame으로 변환
                    if isinstance(results, list):
                        if len(results) > 0 and isinstance(results[0], dict):
                            df = pd.DataFrame(results)
                        else:
                            # 튜플 리스트인 경우
                            if len(results) > 0:
                                # 첫 번째 결과로 컬럼명 추정
                                first_row = results[0]
                                if isinstance(first_row, tuple):
                                    columns = [f"변수_{i+1}" for i in range(len(first_row))]
                                    df = pd.DataFrame(results, columns=columns)
                                else:
                                    df = pd.DataFrame(results)
                            else:
                                df = pd.DataFrame()
                    else:
                        df = pd.DataFrame(results)
                    
                    if not df.empty:
                        st.success(f"[OK] 쿼리 실행 완료: {len(df)}개 결과")
                        
                        # 결과 표시
                        st.dataframe(df, width='stretch', hide_index=True)
                        
                        # 결과 다운로드
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 결과 CSV 다운로드",
                            data=csv,
                            file_name="sparql_results.csv",
                            mime="text/csv"
                        )
                        
                        # 통계 정보
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("결과 수", len(df))
                        with col2:
                            st.metric("컬럼 수", len(df.columns))
                        with col3:
                            st.metric("그래프 Triples", len(list(graph.triples((None, None, None)))))
                    else:
                        # 결과가 없을 때 도움말 제공 (자동 수정이 시도되지 않은 경우만)
                        if not auto_fixed:
                            _show_no_results_help(original_query)
                else:
                    # 결과가 없을 때 도움말 제공 (자동 수정이 시도되지 않은 경우만)
                    if not auto_fixed:
                        _show_no_results_help(original_query)
                    
        except Exception as e:
            st.error(f"쿼리 실행 실패: {e}")
            import traceback
            with st.expander("오류 상세 정보"):
                st.code(traceback.format_exc())
            
            # 네임스페이스 관련 오류인 경우 도움말 제공
            if ("def:" in query_text or "ns1:" in query_text) and "ns:" not in query_text:
                st.warning("💡 **도움말**: 쿼리에서 `def:` 또는 `ns1:` 네임스페이스를 사용하고 있습니다. 현재 데이터는 `ns:` (`http://coa-agent-platform.org/ontology#`) 네임스페이스를 사용합니다. `ns:`로 변경해보세요.")
    
    # 그래프 통계 정보
    st.divider()
    st.subheader("그래프 통계")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        triples_count = len(list(graph.triples((None, None, None))))
        st.metric("Triples", triples_count)
    
    with col2:
        subjects = set()
        for s, p, o in graph:
            subjects.add(str(s))
        st.metric("고유 주체", len(subjects))
    
    with col3:
        predicates = set()
        for s, p, o in graph:
            predicates.add(str(p))
        st.metric("고유 속성", len(predicates))
    
    with col4:
        objects = set()
        for s, p, o in graph:
            if not _is_literal(str(o)):
                objects.add(str(o))
        st.metric("고유 객체", len(objects))
    
    # 네임스페이스 정보
    st.divider()
    with st.expander("네임스페이스 정보"):
        st.code("""
PREFIX ns: <http://coa-agent-platform.org/ontology#>  # 통일된 네임스페이스
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
        """)
        st.info("""
**참고**: 
- `ns:` (`http://coa-agent-platform.org/ontology#`) - 표준 네임스페이스
- `def:` (`http://defense-ai.kr/ontology#`) - 레거시 호환
- 위 PREFIX는 쿼리에서 자동으로 추가됩니다.
- 클래스명은 테이블명과 동일합니다 (예: `ns:적군부대현황`, `ns:아군부대현황`, `ns:위협상황`)
        """)


def _is_literal(value):
    """리터럴 값인지 확인"""
    return isinstance(value, str) and (
        value.startswith('"') or 
        value.replace('.', '').replace('-', '').isdigit()
    )


def _show_no_results_help(query_text: str):
    """쿼리 결과가 없을 때 도움말 표시"""
    st.info("쿼리 결과가 없습니다.")
    
    # 네임스페이스 관련 도움말
    help_messages = []
    
    if ("def:" in query_text or "ns1:" in query_text) and "ns:" not in query_text:
        help_messages.append("💡 **네임스페이스**: 쿼리에서 `def:` 또는 `ns1:` 네임스페이스를 사용하고 있습니다. 현재 데이터는 `ns:` (`http://coa-agent-platform.org/ontology#`) 네임스페이스를 사용합니다. `ns:`로 변경해보세요.")
    
    # 속성명 관련 도움말
    if "부대명" in query_text:
        help_messages.append("💡 **속성명**: `부대명` 속성은 `rdfs:label`을 사용합니다. `PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>`를 추가하고 `?unit rdfs:label ?unitName` 형태로 쿼리를 수정해보세요.")
    
    if "배치축선ID" in query_text:
        help_messages.append("💡 **속성명**: `배치축선ID`는 객체 속성 `ns:has전장축선`을 사용합니다. `?unit ns:has전장축선 ?axis` 형태로 쿼리를 수정해보세요.")
    
    if "전투력" in query_text and "전투력지수" not in query_text:
        help_messages.append("💡 **속성명**: `전투력` 속성은 `전투력지수`를 사용합니다. `ns:전투력지수`로 변경해보세요.")
    
    if help_messages:
        with st.expander("🔍 쿼리 개선 제안"):
            for msg in help_messages:
                st.markdown(msg)
            
            st.markdown("---")
            st.markdown("**올바른 예제 쿼리:**")
            st.code("""
PREFIX ns: <http://coa-agent-platform.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?unit ?unitName ?combatPower ?axis WHERE {
  ?unit a ns:적군부대현황 .
  OPTIONAL { ?unit rdfs:label ?unitName . }
  OPTIONAL { ?unit ns:전투력지수 ?combatPower . }
  OPTIONAL { ?unit ns:has전장축선 ?axis . }
}
ORDER BY DESC(xsd:integer(?combatPower))
LIMIT 30
""", language="sparql")







