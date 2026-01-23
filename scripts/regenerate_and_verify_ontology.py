"""
온톨로지 재생성 및 검증 스크립트
업데이트된 schema_registry.yaml을 사용하여 온톨로지를 재생성하고,
주요 객체와 관계가 정상적으로 생성되었는지 검증합니다.
"""
import sys
from pathlib import Path
import json
import pandas as pd

# 결과 파일로 출력 리다이렉션 (디버깅용)
output_path = Path(__file__).parent.parent / "outputs" / "regen_debug.log"
sys.stdout = open(output_path, 'w', encoding='utf-8')
sys.stderr = sys.stdout

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
    from rdflib import Graph, URIRef, Literal, Namespace
    from rdflib.namespace import RDF, RDFS, OWL
except ImportError as e:
    print(f"❌ Import 실패: {e}")
    sys.exit(1)

def load_all_excel_files(data_lake_path: Path):
    """모든 엑셀 파일 로드"""
    data = {}
    excel_files = list(data_lake_path.glob("*.xlsx"))
    print(f"📂 엑셀 파일 로드 중... ({len(excel_files)}개)")
    
    for file_path in sorted(excel_files):
        try:
            # 첫 번째 시트만 로드
            df = pd.read_excel(file_path, sheet_name=0)
            table_name = file_path.stem
            data[table_name] = df
            print(f"  - {table_name}: {len(df)} 행")
        except Exception as e:
            print(f"  ❌ {file_path.name} 로드 실패: {e}")
    
    return data

def generate_ontology():
    """온톨로지 재생성"""
    print("\n🔄 온톨로지 재생성 시작...")
    
    # 설정
    data_lake_path = project_root / "data_lake"
    knowledge_dir = project_root / "knowledge"
    schema_path = project_root / "metadata" / "schema_registry.yaml"
    
    config = {
        "data_lake_dir": str(data_lake_path),
        "knowledge_dir": str(knowledge_dir),
        "schema_registry_path": str(schema_path),
        "base_uri": "http://example.org/ontology/",
        "force_refresh": True
    }
    
    # 매니저 초기화
    manager = EnhancedOntologyManager(config)
    manager.clear_relation_mappings_cache()
    
    # 데이터 로드
    data = load_all_excel_files(data_lake_path)
    
    # 그래프 생성 (build_from_data 사용)
    try:
        g = manager.build_from_data(data, force_rebuild=True, auto_sync_schema=False)
        
        if g:
            print(f"✅ 온톨로지 생성 완료. 트리플 수: {len(g)}")
            return g, manager
        else:
            print("❌ 온톨로지 생성 실패 (그래프가 None 반환)")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 온톨로지 생성 중 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def validate_ontology(g, manager):
    """생성된 온톨로지 검증"""
    print("\n🔍 온톨로지 검증 시작...")
    
    # 네임스페이스 설정 (Manager 내부의 ns 사용)
    NS = manager.ns
    
    # 1. 위협상황 속성 검증
    print("\n[검증 1] 위협상황 속성 확인")
    
    query_threat = f"""
    PREFIX : <{NS}>
    SELECT ?threat ?type ?level ?axis ?loc
    WHERE {{
        ?threat a :위협상황 .
        OPTIONAL {{ ?threat :위협유형 ?type }}
        OPTIONAL {{ ?threat :위협수준 ?level }}
        OPTIONAL {{ ?threat :has전장축선 ?axis }}
        OPTIONAL {{ ?threat :locatedIn ?loc }}
    }}
    LIMIT 5
    """
    
    try:
        results = g.query(query_threat)
        count = 0
        for row in results:
            count += 1
            print(f"  - Threat: {row.threat.split('#')[-1]}")
            print(f"    Type: {row.type}, Level: {row.level}")
            print(f"    Axis: {row.axis.split('#')[-1] if row.axis else 'None'}")
            print(f"    Loc: {row.loc.split('#')[-1] if row.loc else 'None'}")
        
        if count == 0:
            print("  ⚠️ 위협상황 인스턴스가 조회되지 않았습니다.")
    except Exception as e:
        print(f"  ❌ 쿼리 실행 실패: {e}")

    # 2. COA 속성 검증
    print("\n[검증 2] COA 라이브러리 속성 확인 (새로 추가된 속성)")
    query_coa = f"""
    PREFIX : <{NS}>
    SELECT ?coa ?name ?res ?wargame
    WHERE {{
        ?coa a :COA_Library .
        OPTIONAL {{ ?coa :명칭 ?name }}
        OPTIONAL {{ ?coa :필요자원 ?res }}
        OPTIONAL {{ ?coa :워게임_모의_분석_승률 ?wargame }}
    }}
    LIMIT 5
    """
    
    try:
        results = g.query(query_coa)
        count = 0
        for row in results:
            count += 1
            print(f"  - COA: {row.coa.split('#')[-1]}")
            print(f"    Name: {row.name}")
            print(f"    Resource: {row.res}")
            print(f"    Wargame: {row.wargame}")
            
        if count == 0:
            print("  ⚠️ COA 인스턴스가 조회되지 않았습니다.")
    except Exception as e:
        print(f"  ❌ 쿼리 실행 실패: {e}")

    # 3. 임무정보 관계 검증
    print("\n[검증 3] 임무정보-축선 관계 확인")
    query_mission = f"""
    PREFIX : <{NS}>
    SELECT ?mission ?main_axis ?sub_axis
    WHERE {{
        ?mission a :임무정보 .
        OPTIONAL {{ ?mission :has전장축선 ?main_axis }} 
    }}
    LIMIT 5
    """
    try:
        results = g.query(query_mission)
        for row in results:
             print(f"  - Mission: {row.mission.split('#')[-1]}")
             print(f"    Axis: {row.main_axis.split('#')[-1] if row.main_axis else 'None'}")
    except Exception as e:
        print(f"  ❌ 쿼리 실행 실패: {e}")

    print("\n✅ 검증 완료")

if __name__ == "__main__":
    g, manager = generate_ontology()
    validate_ontology(g, manager)
