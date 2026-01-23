# scripts/generate_doctrine_documents.py
# -*- coding: utf-8 -*-
"""
교리 문서 생성 스크립트
다양한 작전유형에 대한 교리 문서를 생성하고 RAG 인덱스에 추가합니다.
"""
import os
import sys
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import yaml
from core_pipeline.doctrine_generator import DoctrineGenerator
from core_pipeline.llm_manager import get_llm_manager
from core_pipeline.rag_manager import RAGManager


def generate_doctrine_documents():
    """교리 문서 생성 및 RAG 인덱스 추가"""
    
    print("=" * 60)
    print("교리 문서 생성 스크립트")
    print("=" * 60)
    
    # 설정 로드
    config_path = BASE_DIR / "config" / "global.yaml"
    if not config_path.exists():
        print(f"[ERROR] 설정 파일을 찾을 수 없습니다: {config_path}")
        return
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 초기화
    print("\n[1/4] LLM Manager 초기화 중...")
    llm_manager = get_llm_manager()
    
    print("[2/4] RAG Manager 초기화 중...")
    rag_manager = RAGManager(config)
    rag_manager.load_embeddings()
    
    if not rag_manager.is_available():
        print("[WARN] RAG Manager를 사용할 수 없습니다. 계속 진행합니다...")
    
    print("[3/4] Doctrine Generator 초기화 중...")
    generator = DoctrineGenerator(llm_manager, rag_manager)
    
    # 생성할 교리 문서 목록
    doctrine_configs = [
        {
            "operation_type": "defense",
            "mett_c_focus": ["Mission", "Terrain", "Troops"],
            "coa_purpose": ["기동 제한", "방어선 설정", "예비전력 운용"],
            "doctrine_name": "방어 작전 교리 - 지형 제약 기반"
        },
        {
            "operation_type": "defense",
            "mett_c_focus": ["Enemy", "Time", "Civilian"],
            "coa_purpose": ["위협 대응", "민간인 보호", "시간 제약 고려"],
            "doctrine_name": "방어 작전 교리 - 위협 및 민간인 고려"
        },
        {
            "operation_type": "counter_attack",
            "mett_c_focus": ["Mission", "Troops", "Time"],
            "coa_purpose": ["반격 시기", "전력 집중", "기동성 확보"],
            "doctrine_name": "반격 작전 교리"
        },
        {
            "operation_type": "offensive",
            "mett_c_focus": ["Mission", "Enemy", "Terrain"],
            "coa_purpose": ["주공축 선정", "적 전력 파악", "지형 활용"],
            "doctrine_name": "공격 작전 교리"
        }
    ]
    
    print(f"\n[4/4] 교리 문서 생성 시작 ({len(doctrine_configs)}개)...")
    print("-" * 60)
    
    generated_docs = []
    
    for i, doc_config in enumerate(doctrine_configs, 1):
        print(f"\n[{i}/{len(doctrine_configs)}] 교리 문서 생성 중...")
        print(f"  - 작전유형: {doc_config['operation_type']}")
        print(f"  - METT-C 중점: {', '.join(doc_config['mett_c_focus'])}")
        print(f"  - COA 목적: {', '.join(doc_config['coa_purpose'])}")
        
        try:
            # 교리 문서 생성
            doctrine_doc = generator.generate_doctrine_document(
                operation_type=doc_config['operation_type'],
                mett_c_focus=doc_config['mett_c_focus'],
                coa_purpose=doc_config['coa_purpose'],
                num_statements=5,
                doctrine_name=doc_config.get('doctrine_name')
            )
            
            print(f"  ✅ 생성 완료: {doctrine_doc['doctrine_id']}")
            print(f"     - 교리명: {doctrine_doc['doctrine_name']}")
            print(f"     - 교리 문장 수: {len(doctrine_doc['statements'])}")
            
            # RAG 인덱스에 추가
            print(f"  📝 RAG 인덱스에 추가 중...")
            success = generator.save_to_rag(doctrine_doc, save_to_file=True)
            
            if success:
                print(f"  ✅ RAG 인덱스 추가 완료")
                generated_docs.append(doctrine_doc)
            else:
                print(f"  ⚠️  RAG 인덱스 추가 실패 (파일은 저장됨)")
                generated_docs.append(doctrine_doc)
            
        except Exception as e:
            print(f"  ❌ 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("생성 완료 요약")
    print("=" * 60)
    print(f"총 {len(generated_docs)}개 교리 문서 생성됨")
    
    if generated_docs:
        print("\n생성된 교리 문서:")
        for doc in generated_docs:
            print(f"  - {doc['doctrine_id']}: {doc['doctrine_name']}")
            print(f"    문장 수: {len(doc['statements'])}개")
            print(f"    파일: knowledge/rag_docs/{doc['doctrine_id']}.md")
    
    print("\n✅ 교리 문서 생성 완료!")
    print("\n다음 단계:")
    print("  1. 생성된 교리 문서 확인: knowledge/rag_docs/")
    print("  2. RAG 인덱스 재구축 (필요시): python scripts/rebuild_rag_index.py")
    print("  3. COA 추천 실행하여 교리 인용 확인")


if __name__ == "__main__":
    try:
        generate_doctrine_documents()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n[ERROR] 스크립트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


