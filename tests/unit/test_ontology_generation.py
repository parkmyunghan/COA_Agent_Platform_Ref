"""
온톨로지 재생성 테스트 스크립트
아군가용자산, 기상상황 테이블이 포함되었는지 확인
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    from core_pipeline.data_manager import DataManager
    import yaml
    
    print("=" * 60)
    print("온톨로지 재생성 테스트")
    print("=" * 60)
    
    # 설정 로드
    with open("config/global.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # DataManager 초기화
    data_manager = DataManager(config)
    
    # OntologyManager 초기화
    ontology_manager = EnhancedOntologyManager(config)
    ontology_manager.data_manager = data_manager
    
    # 데이터 로드
    print("\n[1] 데이터 로드 중...")
    data = data_manager.load_all()
    print(f"✅ 로드된 테이블: {list(data.keys())}")
    
    # 아군가용자산, 기상상황 테이블 확인
    if "아군가용자산" in data:
        print(f"✅ 아군가용자산: {len(data['아군가용자산'])}개 행")
    else:
        print("⚠️ 아군가용자산 테이블이 없습니다")
    
    if "기상상황" in data:
        print(f"✅ 기상상황: {len(data['기상상황'])}개 행")
    else:
        print("⚠️ 기상상황 테이블이 없습니다")
    
    # 온톨로지 생성
    print("\n[2] 온톨로지 생성 중...")
    ontology_manager.generate_owl_ontology(data)
    ontology_manager.generate_instances(data)
    
    # 그래프 확인
    if ontology_manager.graph:
        triples_count = len(list(ontology_manager.graph.triples((None, None, None))))
        print(f"✅ 온톨로지 그래프 생성 완료: {triples_count}개 triples")
        
        # 아군가용자산 인스턴스 확인
        from rdflib import RDF
        ns = ontology_manager.ns
        
        asset_query = f"""
        PREFIX ns: <http://coa-agent-platform.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT (COUNT(?asset) AS ?count) WHERE {{
            ?asset rdf:type ns:아군가용자산 .
        }}
        """
        asset_results = ontology_manager.query(asset_query, return_format='list')
        if asset_results:
            print(f"✅ 아군가용자산 인스턴스: {asset_results[0].get('count', 0)}개")
        
        # 기상상황 인스턴스 확인
        weather_query = f"""
        PREFIX ns: <http://coa-agent-platform.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT (COUNT(?weather) AS ?count) WHERE {{
            ?weather rdf:type ns:기상상황 .
        }}
        """
        weather_results = ontology_manager.query(weather_query, return_format='list')
        if weather_results:
            print(f"✅ 기상상황 인스턴스: {weather_results[0].get('count', 0)}개")
    else:
        print("⚠️ 온톨로지 그래프가 생성되지 않았습니다")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

