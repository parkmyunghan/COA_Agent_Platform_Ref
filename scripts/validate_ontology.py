"""
온톨로지 생성 및 데이터 매핑 검증 스크립트
THR006 공중위협 문제를 포함한 전체 온톨로지 검증
"""
import pandas as pd
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS

def check_excel_data():
    """Excel 원본 데이터 확인"""
    print("=" * 80)
    print("1. Excel 원본 데이터 확인")
    print("=" * 80)
    
    threat_file = Path("data_lake/위협상황.xlsx")
    df = pd.read_excel(threat_file)
    
    print(f"\n컬럼: {list(df.columns)}")
    print(f"총 {len(df)}개 위협 데이터")
    
    # THR001-THR010 확인
    print("\n위협 ID별 위협유형:")
    for idx, row in df.head(10).iterrows():
        threat_id = row.iloc[0]
        threat_name = row.iloc[1]
        threat_type = row.iloc[2] if len(row) > 2 else "N/A"
        print(f"  {threat_id}: {threat_name} -> 위협유형: {threat_type}")
    
    return df

def check_ontology_instances():
    """생성된 온톨로지 인스턴스 확인"""
    print("\n" + "=" * 80)
    print("2. 생성된 온톨로지 인스턴스 확인")
    print("=" * 80)
    
    instances_file = Path("knowledge/ontology/instances.ttl")
    if not instances_file.exists():
        print(f"❌ {instances_file} 파일이 없습니다!")
        return None
    
    g = Graph()
    g.parse(instances_file, format="turtle")
    
    ns = Namespace("http://coa-agent-platform.org/ontology#")
    
    print(f"\n총 {len(g)} 트리플")
    
    # 위협상황 인스턴스 확인
    print("\n위협상황 인스턴스 (처음 10개):")
    threat_instances = list(g.subjects(RDF.type, ns.위협상황))
    
    for threat_uri in threat_instances[:10]:
        threat_id = str(threat_uri).split('#')[-1]
        
        # 위협유형 찾기
        threat_type = None
        for obj in g.objects(threat_uri, ns.has위협유형):
            threat_type = str(obj).split('#')[-1] if '#' in str(obj) else str(obj)
            break
        
        # 위협명 찾기
        threat_name = None
        for obj in g.objects(threat_uri, RDFS.label):
            threat_name = str(obj)
            break
        
        print(f"  {threat_id}: {threat_name} -> 위협유형: {threat_type}")
    
    return g

def check_threat_chain_mapping():
    """위협-전략체인 매핑 확인"""
    print("\n" + "=" * 80)
    print("3. 위협-전략체인 매핑 확인")
    print("=" * 80)
    
    instances_file = Path("knowledge/ontology/instances.ttl")
    if not instances_file.exists():
        print(f"❌ {instances_file} 파일이 없습니다!")
        return
    
    g = Graph()
    g.parse(instances_file, format="turtle")
    
    ns = Namespace("http://coa-agent-platform.org/ontology#")
    
    # 위협상황 -> 전략체인 연결 확인
    print("\n위협상황 -> 전략체인 연결 (처음 10개):")
    threat_instances = list(g.subjects(RDF.type, ns.위협상황))
    
    for threat_uri in threat_instances[:10]:
        threat_id = str(threat_uri).split('#')[-1]
        
        # has전략체인 관계 찾기
        chains = []
        for chain_uri in g.objects(threat_uri, ns.has전략체인):
            chain_name = str(chain_uri).split('#')[-1] if '#' in str(chain_uri) else str(chain_uri)
            chains.append(chain_name)
        
        if chains:
            print(f"  {threat_id} -> {', '.join(chains)}")
        else:
            print(f"  {threat_id} -> (전략체인 없음)")

def check_specific_thr006():
    """THR006 상세 확인"""
    print("\n" + "=" * 80)
    print("4. THR006 상세 확인")
    print("=" * 80)
    
    # Excel 데이터
    df = pd.read_excel("data_lake/위협상황.xlsx")
    thr006_excel = df[df.iloc[:, 0] == 'THR006']
    
    if not thr006_excel.empty:
        print("\nExcel 데이터:")
        row = thr006_excel.iloc[0]
        print(f"  위협ID: {row.iloc[0]}")
        print(f"  위협명: {row.iloc[1]}")
        print(f"  위협유형: {row.iloc[2] if len(row) > 2 else 'N/A'}")
    
    # 온톨로지 데이터
    instances_file = Path("knowledge/ontology/instances.ttl")
    if instances_file.exists():
        g = Graph()
        g.parse(instances_file, format="turtle")
        
        ns = Namespace("http://coa-agent-platform.org/ontology#")
        thr006_uri = ns['위협상황_THR006']
        
        print("\n온톨로지 데이터:")
        print(f"  URI: {thr006_uri}")
        
        # 모든 속성 확인
        for pred, obj in g.predicate_objects(thr006_uri):
            pred_name = str(pred).split('#')[-1] if '#' in str(pred) else str(pred)
            obj_value = str(obj).split('#')[-1] if '#' in str(obj) else str(obj)
            print(f"    {pred_name}: {obj_value}")

def check_coa_threat_relevance():
    """방책-위협 관련성 매핑 확인"""
    print("\n" + "=" * 80)
    print("5. 방책-위협 관련성 매핑 확인")
    print("=" * 80)
    
    rel_file = Path("data_lake/방책유형_위협유형_관련성.xlsx")
    if not rel_file.exists():
        print(f"❌ {rel_file} 파일이 없습니다!")
        return
    
    df = pd.read_excel(rel_file)
    print(f"\n총 {len(df)}개 매핑")
    print("\n샘플 (처음 10개):")
    print(df.head(10).to_string(index=False))
    
    # 공중위협 관련 매핑 확인
    print("\n공중위협 관련 매핑:")
    air_threat = df[df['threat_type'].str.contains('공중', na=False)]
    if not air_threat.empty:
        print(air_threat.to_string(index=False))
    else:
        print("  공중위협 관련 매핑 없음")

def main():
    print("온톨로지 생성 및 데이터 매핑 전체 검증")
    print("=" * 80)
    
    try:
        # 1. Excel 원본 데이터 확인
        excel_df = check_excel_data()
        
        # 2. 온톨로지 인스턴스 확인
        ontology_graph = check_ontology_instances()
        
        # 3. 위협-전략체인 매핑 확인
        check_threat_chain_mapping()
        
        # 4. THR006 상세 확인
        check_specific_thr006()
        
        # 5. 방책-위협 관련성 확인
        check_coa_threat_relevance()
        
        print("\n" + "=" * 80)
        print("검증 완료")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
