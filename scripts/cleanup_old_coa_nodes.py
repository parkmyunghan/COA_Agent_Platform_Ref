"""
기존 COA_* 노드 정리 스크립트

_add_coa_library_to_graph()로 생성된 중복 COA 노드들을 제거합니다.
COA_Library_* 노드만 유지하고 COA_* 노드(COA_Library_ 접두사가 없는 것)는 제거합니다.
"""

import sys
from pathlib import Path
from rdflib import Graph, URIRef, RDF, RDFS, Namespace

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def cleanup_old_coa_nodes():
    """기존 COA_* 노드 제거 (COA_Library_* 노드는 유지)"""
    
    ontology_path = project_root / "knowledge" / "ontology"
    instances_file = ontology_path / "instances.ttl"
    instances_reasoned_file = ontology_path / "instances_reasoned.ttl"
    
    if not instances_file.exists():
        print(f"[WARN] {instances_file} 파일이 존재하지 않습니다.")
        return
    
    print(f"[INFO] 기존 COA 노드 정리 시작...")
    print(f"[INFO] 대상 파일: {instances_file}")
    
    # 그래프 로드
    graph = Graph()
    try:
        graph.parse(str(instances_file), format="turtle")
        print(f"[INFO] 그래프 로드 완료: {len(list(graph.triples((None, None, None))))}개 triples")
    except Exception as e:
        print(f"[ERROR] 그래프 로드 실패: {e}")
        return
    
    # 네임스페이스
    ns_legacy = Namespace("http://coa-agent-platform.org/ontology#")
    
    # 제거할 COA 노드 찾기 (COA_Library_ 접두사가 없는 COA_* 노드)
    coa_nodes_to_remove = []
    coa_types = [
        "COA", "DefenseCOA", "OffensiveCOA", "CounterAttackCOA",
        "PreemptiveCOA", "DeterrenceCOA", "ManeuverCOA", "InformationOpsCOA"
    ]
    
    for coa_type in coa_types:
        coa_class = URIRef(ns_legacy[coa_type])
        for s, p, o in graph.triples((None, RDF.type, coa_class)):
            node_id = str(s).split('#')[-1]
            # COA_Library_ 접두사가 없는 COA_* 노드만 제거 대상
            if node_id.startswith("COA_") and not node_id.startswith("COA_Library_"):
                coa_nodes_to_remove.append(s)
    
    # 중복 제거
    coa_nodes_to_remove = list(set(coa_nodes_to_remove))
    
    if not coa_nodes_to_remove:
        print(f"[INFO] 제거할 COA 노드가 없습니다.")
        return
    
    print(f"[INFO] 제거 대상 COA 노드: {len(coa_nodes_to_remove)}개")
    
    # 백업 먼저 생성 (제거 전)
    backup_file = ontology_path / "backup" / f"instances.ttl.backup_before_cleanup"
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        import shutil
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = ontology_path / "backup" / f"instances.ttl.backup_{timestamp}"
        shutil.copy2(str(instances_file), str(backup_file))
        print(f"[INFO] 백업 생성 완료: {backup_file}")
    except Exception as e:
        print(f"[WARN] 백업 생성 실패: {e}")
    
    # 제거할 노드의 모든 트리플 찾기 및 제거
    removed_triples = 0
    triples_to_remove = []
    
    # 먼저 제거할 트리플 수집
    for node_uri in coa_nodes_to_remove:
        # 노드를 주체로 하는 모든 트리플
        for triple in graph.triples((node_uri, None, None)):
            triples_to_remove.append(triple)
        
        # 노드를 객체로 하는 모든 트리플
        for triple in graph.triples((None, None, node_uri)):
            triples_to_remove.append(triple)
    
    # 트리플 제거
    for triple in triples_to_remove:
        graph.remove(triple)
        removed_triples += 1
    
    print(f"[INFO] 제거된 트리플: {removed_triples}개")
    
    # 정리된 그래프 저장
    try:
        graph.serialize(destination=str(instances_file), format="turtle")
        remaining_triples = len(list(graph.triples((None, None, None))))
        print(f"[INFO] 정리 완료: {instances_file} ({remaining_triples}개 triples)")
    except Exception as e:
        print(f"[ERROR] 파일 저장 실패: {e}")
        return
    
    # instances_reasoned.ttl도 정리 (존재하는 경우)
    if instances_reasoned_file.exists():
        print(f"[INFO] instances_reasoned.ttl도 정리합니다...")
        reasoned_graph = Graph()
        try:
            reasoned_graph.parse(str(instances_reasoned_file), format="turtle")
            
            # 백업
            reasoned_backup = ontology_path / "backup" / f"instances_reasoned.ttl.backup_before_cleanup"
            reasoned_backup_graph = Graph()
            reasoned_backup_graph.parse(str(instances_reasoned_file), format="turtle")
            reasoned_backup_graph.serialize(destination=str(reasoned_backup), format="turtle")
            print(f"[INFO] 백업 생성 완료: {reasoned_backup}")
            
            # 제거
            reasoned_removed = 0
            for node_uri in coa_nodes_to_remove:
                for s, p, o in list(reasoned_graph.triples((node_uri, None, None))):
                    reasoned_graph.remove((s, p, o))
                    reasoned_removed += 1
                for s, p, o in list(reasoned_graph.triples((None, None, node_uri))):
                    reasoned_graph.remove((s, p, o))
                    reasoned_removed += 1
            
            reasoned_graph.serialize(destination=str(instances_reasoned_file), format="turtle")
            reasoned_remaining = len(list(reasoned_graph.triples((None, None, None))))
            print(f"[INFO] instances_reasoned.ttl 정리 완료: {reasoned_remaining}개 triples (제거: {reasoned_removed}개)")
        except Exception as e:
            print(f"[WARN] instances_reasoned.ttl 정리 실패: {e}")
    
    print(f"[INFO] 모든 작업 완료!")
    print(f"[INFO] 제거된 COA 노드 목록 (처음 10개):")
    for i, node_uri in enumerate(coa_nodes_to_remove[:10]):
        print(f"  - {str(node_uri).split('#')[-1]}")
    if len(coa_nodes_to_remove) > 10:
        print(f"  ... 외 {len(coa_nodes_to_remove) - 10}개")

if __name__ == "__main__":
    cleanup_old_coa_nodes()

