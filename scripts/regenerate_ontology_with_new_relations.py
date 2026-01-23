# scripts/regenerate_ontology_with_new_relations.py
# -*- coding: utf-8 -*-
"""
누락된 관계 규칙 추가 후 온톨로지 재생성 및 검증 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "core_pipeline"))
sys.path.insert(0, str(project_root / "config"))
sys.path.insert(0, str(project_root / "common"))

import yaml
from core_pipeline.orchestrator import Orchestrator
from core_pipeline.ontology_validator import OntologyValidator

def main():
    print("=" * 80)
    print("온톨로지 재생성 및 검증 스크립트")
    print("=" * 80)
    
    # 설정 파일 로드
    try:
        config_path = project_root / "config" / "global.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✅ 설정 파일 로드 완료: {config_path}")
    except Exception as e:
        print(f"❌ 설정 파일 로드 실패: {e}")
        return False
    
    # Orchestrator 초기화
    print("\n🔄 Orchestrator 초기화 중...")
    try:
        orchestrator = Orchestrator(config, use_enhanced_ontology=True)
        orchestrator.initialize()
        print("✅ Orchestrator 초기화 완료")
    except Exception as e:
        print(f"❌ Orchestrator 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 데이터 로드
    print("\n📊 데이터 로드 중...")
    try:
        data = orchestrator.core.data_manager.load_all()
        print(f"✅ 데이터 로드 완료: {len(data)}개 테이블")
        for table_name, df in data.items():
            print(f"   - {table_name}: {len(df)}행")
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 온톨로지 재생성
    print("\n🔄 온톨로지 재생성 중...")
    try:
        enhanced_om = orchestrator.core.enhanced_ontology_manager
        
        # 기존 그래프 초기화
        from rdflib import Graph
        if enhanced_om.graph is not None:
            enhanced_om.graph = Graph()
        print("   - 기존 그래프 초기화 완료")
        
        # OWL 온톨로지 생성 (스키마)
        print("   - OWL 스키마 생성 중...")
        graph = enhanced_om.generate_owl_ontology(data)
        if not graph:
            print("❌ OWL 스키마 생성 실패")
            return False
        print("   ✅ OWL 스키마 생성 완료")
        
        # 인스턴스 생성
        print("   - 인스턴스 생성 중...")
        graph = enhanced_om.generate_instances(data, enable_virtual_entities=True)
        if not graph:
            print("❌ 인스턴스 생성 실패")
            return False
        
        # 그래프 저장
        print("   - 그래프 저장 중...")
        try:
            save_success = enhanced_om.save_graph(
                save_schema_separately=True,
                save_instances_separately=True,
                save_reasoned_separately=False,
                enable_semantic_inference=True,
                cleanup_old_files=True,
                backup_old_files=True
            )
        except TypeError:
            save_success = enhanced_om.save_graph()
        
        if save_success:
            triples_count = len(list(enhanced_om.graph.triples((None, None, None))))
            print(f"   ✅ 그래프 저장 완료: {triples_count:,} triples")
        else:
            print("   ⚠️ 그래프 저장 실패")
        
        # core.ontology_manager.graph 동기화
        orchestrator.core.ontology_manager.graph = enhanced_om.graph
        print("✅ 온톨로지 재생성 완료")
        
    except Exception as e:
        print(f"❌ 온톨로지 재생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 온톨로지 검증
    print("\n🔍 온톨로지 검증 중...")
    try:
        validator = OntologyValidator(enhanced_om)
        report = validator.validate_schema_compliance()
        
        print(f"\n📊 검증 결과:")
        print(f"   - 종합 점수: {report['overall_score']}%")
        
        # Axis 검증
        axis_res = report.get('axis_compliance', {})
        print(f"\n   1. 전장축선(Axis) 객체화 검증:")
        for check in axis_res.get('checks', []):
            status = "✅" if check.get('status') == 'PASS' else "❌"
            print(f"      {status} {check.get('name', '')}: {check.get('message', '')}")
        
        # 연결성 검증
        conn_res = report.get('connectivity_health', {})
        print(f"\n   2. 데이터 연결성 검증:")
        for check in conn_res.get('checks', []):
            status = "✅" if check.get('status') == 'PASS' else "⚠️"
            print(f"      {status} {check.get('name', '')}: {check.get('message', '')}")
        
        # 추론 엔진 상태
        if 'reasoning_status' in report:
            reason_res = report.get('reasoning_status', {})
            print(f"\n   3. 추론 엔진 상태:")
            for check in reason_res.get('checks', []):
                status = "✅" if check.get('status') == 'PASS' else "⚪"
                print(f"      {status} {check.get('name', '')}: {check.get('message', '')}")
        
        # 종합 평가
        if report['overall_score'] >= 80:
            print(f"\n✅ 스키마 검증 통과! (점수: {report['overall_score']}%)")
        else:
            print(f"\n⚠️ 스키마 검증 점수: {report['overall_score']}% (80% 이상 권장)")
        
        print("\n✅ 온톨로지 검증 완료")
        
    except Exception as e:
        print(f"❌ 온톨로지 검증 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ 모든 작업 완료!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

