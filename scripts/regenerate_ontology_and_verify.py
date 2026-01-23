# scripts/regenerate_ontology_and_verify.py
# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import pandas as pd

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent))

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.data_manager import DataManager

def main():
    print("=== 온톨로지 재생성 및 최종 검증 시작 ===\n")
    
    # 1. 데이터 로드
    config = {
        "data_lake_path": "data_lake",
        "metadata_path": "metadata",
        "ontology_path": "knowledge/ontology",
        "output_path": "outputs"
    }
    
    dm = DataManager(config)
    data = dm.load_all()
    print(f"✅ {len(data)}개 테이블 데이터 로드 완료")
    
    # 2. 온톨로지 매니저 초기화 및 생성
    om = EnhancedOntologyManager(config)
    print("🔄 온톨로지 생성 중 (instances, schema)...")
    
    # instances 생성
    om.generate_instances(data)
    
    # 저장 (knowledge/ontology 폴더에 저장됨)
    success = om.save_graph(
        save_schema_separately=True,
        save_instances_separately=True,
        save_reasoned_separately=True,
        enable_semantic_inference=True
    )
    
    if success:
        print(f"✅ 온톨로지 파일 저장 완료: {config['ontology_path']}")
    else:
        print("❌ 온톨로지 저장 실패")
        return

    # 3. 교리적 통합 검증 스크립트 실행
    print("\n🔄 교리적 통합 재검증 중...")
    import subprocess
    result = subprocess.run(["python", "scripts/verify_doctrinal_integration.py"], capture_output=True, text=True)
    print(result.stdout)
    
    if result.returncode == 0:
        print("🎉 모든 검증이 성공적으로 완료되었습니다!")
    else:
        print("❌ 교리적 통합 검증 실패")
        print(result.stderr)

if __name__ == "__main__":
    main()
