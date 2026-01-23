#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
온톨로지 재생성 스크립트
적용조건 필드 변경 사항 반영
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.orchestrator import Orchestrator
import yaml

def load_config():
    """설정 파일 로드"""
    config_path = project_root / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

def regenerate_ontology():
    """온톨로지 재생성"""
    print("=" * 60)
    print("온톨로지 재생성 시작")
    print("=" * 60)
    
    # 설정 로드
    config = load_config()
    
    # Orchestrator 초기화
    print("\n[1/4] Orchestrator 초기화 중...")
    orchestrator = Orchestrator(config)
    orchestrator.initialize()
    
    # 데이터 로드
    print("\n[2/4] 데이터 로드 중...")
    try:
        data = orchestrator.core.data_manager.load_all()
        print(f"  ✓ 데이터 로드 완료: {len(data)}개 테이블")
        for table_name, df in data.items():
            print(f"    - {table_name}: {df.shape[0]}행")
    except Exception as e:
        print(f"[ERROR] 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 온톨로지 재생성
    print("\n[3/4] 온톨로지 재생성 중...")
    try:
        enhanced_om = orchestrator.core.enhanced_ontology_manager
        
        # 기존 그래프 초기화
        from rdflib import Graph
        if enhanced_om.graph is not None:
            enhanced_om.graph = Graph()
        print("  ✓ 기존 그래프 초기화 완료")
        
        # OWL 온톨로지 생성 (스키마)
        print("  - OWL 스키마 생성 중...")
        graph = enhanced_om.generate_owl_ontology(data)
        if not graph:
            print("[ERROR] OWL 스키마 생성 실패")
            return False
        print("  ✓ OWL 스키마 생성 완료")
        
        # 인스턴스 생성
        print("  - 인스턴스 생성 중...")
        graph = enhanced_om.generate_instances(data, enable_virtual_entities=True)
        if not graph:
            print("[ERROR] 인스턴스 생성 실패")
            return False
        print("  ✓ 인스턴스 생성 완료")
        
        # 그래프 저장
        print("  - 그래프 저장 중...")
        try:
            save_success = enhanced_om.save_graph(
                save_schema_separately=True,
                save_instances_separately=True,
                save_reasoned_separately=True,
                enable_semantic_inference=True,
                cleanup_old_files=True,
                backup_old_files=True
            )
        except TypeError:
            save_success = enhanced_om.save_graph()
        
        if save_success:
            triples_count = len(list(enhanced_om.graph.triples((None, None, None))))
            print(f"  ✓ 그래프 저장 완료: {triples_count:,}개 트리플")
        else:
            print("  ⚠️ 그래프 저장 실패")
        
        print("\n" + "=" * 60)
        print("✅ 온톨로지 재생성 완료!")
        print("=" * 60)
        print(f"  - 트리플 수: {triples_count:,}개")
        return True
    except Exception as e:
        print(f"[ERROR] 인스턴스 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = regenerate_ontology()
    sys.exit(0 if success else 1)

