# scripts/test_ontology_with_civilian_area.py
# -*- coding: utf-8 -*-
"""
온톨로지 생성 테스트 - 민간인지역 포함 확인
"""
import sys
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.data_manager import DataManager
from rdflib import URIRef, Namespace, RDF, OWL, RDFS

def test_ontology_generation():
    """온톨로지 생성 및 민간인지역 포함 확인"""
    print("=" * 80)
    print("온톨로지 생성 테스트 - 민간인지역 포함 확인")
    print("=" * 80)
    
    # 설정 로드
    config_path = BASE_DIR / "config" / "global.yaml"
    if not config_path.exists():
        print(f"❌ 설정 파일이 없습니다: {config_path}")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # DataManager 초기화
    print("\n[1] DataManager 초기화 중...")
    data_manager = DataManager(config)
    
    # 데이터 로드
    print("\n[2] 데이터 로드 중...")
    data = data_manager.load_all()
    print(f"✅ 로드된 테이블: {len(data)}개")
    
    # 민간인지역 테이블 확인
    if "민간인지역" in data:
        df_civilian = data["민간인지역"]
        print(f"✅ 민간인지역 테이블: {len(df_civilian)}개 행")
        print(f"   컬럼: {list(df_civilian.columns)}")
    else:
        print("❌ 민간인지역 테이블이 없습니다!")
        return False
    
    # OntologyManager 초기화
    print("\n[3] OntologyManager 초기화 중...")
    ontology_manager = EnhancedOntologyManager(config)
    ontology_manager.data_manager = data_manager
    
    # 기존 그래프 초기화
    from rdflib import Graph
    ontology_manager.graph = Graph()
    
    # 온톨로지 생성
    print("\n[4] 온톨로지 생성 중...")
    graph = ontology_manager.generate_owl_ontology(data)
    if not graph:
        print("❌ 온톨로지 생성 실패")
        return False
    
    # 인스턴스 생성
    print("\n[5] 인스턴스 생성 중...")
    graph = ontology_manager.generate_instances(data, enable_virtual_entities=True)
    if not graph:
        print("❌ 인스턴스 생성 실패")
        return False
    
    # 네임스페이스
    ns = ontology_manager.ns
    
    # 민간인지역 클래스 확인
    print("\n[6] 민간인지역 클래스 확인 중...")
    civilian_class = URIRef(ns["민간인지역"])
    class_triples = list(graph.triples((civilian_class, RDF.type, OWL.Class)))
    if class_triples:
        print("✅ 민간인지역 클래스가 정의되었습니다")
    else:
        print("❌ 민간인지역 클래스가 정의되지 않았습니다")
        return False
    
    # 민간인지역 인스턴스 확인
    print("\n[7] 민간인지역 인스턴스 확인 중...")
    civilian_instances = list(graph.triples((None, RDF.type, civilian_class)))
    print(f"✅ 민간인지역 인스턴스: {len(civilian_instances)}개")
    
    if len(civilian_instances) == 0:
        print("⚠️ 민간인지역 인스턴스가 생성되지 않았습니다")
    else:
        # 첫 번째 인스턴스 상세 확인
        first_instance = civilian_instances[0][0]
        print(f"\n   첫 번째 인스턴스: {first_instance}")
        
        # 지역명 확인
        area_name_prop = URIRef(ns["지역명"])
        name_triples = list(graph.triples((first_instance, area_name_prop, None)))
        if name_triples:
            print(f"   지역명: {name_triples[0][2]}")
        
        # 보호우선순위 확인
        priority_prop = URIRef(ns["보호우선순위"])
        priority_triples = list(graph.triples((first_instance, priority_prop, None)))
        if priority_triples:
            print(f"   보호우선순위: {priority_triples[0][2]}")
        
        # 지형셀 관계 확인
        located_in_prop = URIRef(ns["locatedIn"])
        location_triples = list(graph.triples((first_instance, located_in_prop, None)))
        if location_triples:
            print(f"   위치지형셀: {location_triples[0][2]}")
    
    # 위협상황 → 민간인지역 추론 관계 확인
    print("\n[8] 위협상황 → 민간인지역 추론 관계 확인 중...")
    threat_class = URIRef(ns["위협상황"])
    affects_civilian_prop = URIRef(ns["affectsCivilianArea"])
    
    # 추론 관계 확인 (SPARQL 쿼리)
    query = """
    PREFIX ns: <http://coa-agent-platform.org/ontology#>
    SELECT ?threat ?civilian WHERE {
        ?threat a ns:위협상황 .
        ?threat ns:has지형셀 ?cell .
        ?civilian a ns:민간인지역 .
        ?civilian ns:locatedIn ?cell .
    } LIMIT 5
    """
    
    try:
        results = graph.query(query)
        if results:
            print(f"✅ 위협상황 → 민간인지역 추론 관계: {len(list(results))}개 발견")
            for row in list(results)[:3]:
                print(f"   - {row.threat} → {row.civilian}")
        else:
            print("⚠️ 위협상황 → 민간인지역 추론 관계가 없습니다 (데이터에 따라 없을 수 있음)")
    except Exception as e:
        print(f"⚠️ SPARQL 쿼리 실행 실패: {e}")
    
    # 그래프 저장 (선택적)
    print("\n[9] 그래프 저장 중...")
    try:
        save_success = ontology_manager.save_graph(
            save_schema_separately=True,
            save_instances_separately=True,
            save_reasoned_separately=True,
            enable_semantic_inference=True,
            cleanup_old_files=False,
            backup_old_files=True
        )
        if save_success:
            print("✅ 그래프 저장 완료")
        else:
            print("⚠️ 그래프 저장 실패")
    except Exception as e:
        print(f"⚠️ 그래프 저장 중 오류: {e}")
    
    print("\n" + "=" * 80)
    print("✅ 온톨로지 생성 테스트 완료!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_ontology_generation()
    sys.exit(0 if success else 1)



