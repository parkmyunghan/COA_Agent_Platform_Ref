#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
추론 차이 분석 스크립트
첫 번째 추론과 두 번째 추론의 차이를 분석하여 추가된 트리플의 내용을 확인
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL
from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
from collections import defaultdict
import json

def analyze_inference_difference():
    """첫 번째 추론과 두 번째 추론의 차이를 분석"""
    
    if not OWLRL_AVAILABLE:
        print("[ERROR] owlrl 라이브러리가 설치되지 않았습니다.")
        return
    
    # 원본 그래프 로드
    ontology_dir = project_root / "knowledge" / "ontology"
    schema_path = ontology_dir / "schema.ttl"
    instances_path = ontology_dir / "instances.ttl"
    
    if not instances_path.exists():
        print(f"[ERROR] instances.ttl 파일을 찾을 수 없습니다: {instances_path}")
        return
    
    print("[INFO] 원본 그래프 로드 중...")
    original_graph = Graph()
    
    # 스키마 로드
    if schema_path.exists():
        original_graph.parse(str(schema_path), format="turtle")
        print(f"[INFO] 스키마 로드 완료: {len(original_graph)} triples")
    
    # 인스턴스 로드
    original_graph.parse(str(instances_path), format="turtle")
    original_count = len(set(original_graph))
    print(f"[INFO] 원본 그래프 로드 완료: {original_count} triples")
    
    # 첫 번째 추론 실행
    print("\n[INFO] 첫 번째 추론 실행 중...")
    reasoner1 = OWLReasoner(original_graph)
    first_inferred = reasoner1.run_inference(include_rdfs=True)
    
    if first_inferred is None:
        print("[ERROR] 첫 번째 추론 실패")
        return
    
    first_count = len(set(first_inferred))
    stats1 = reasoner1.get_stats()
    print(f"[INFO] 첫 번째 추론 완료: {original_count} → {first_count} triples (+{stats1.get('new_inferences', 0)})")
    
    # 두 번째 추론 실행 (첫 번째 추론 결과를 입력으로)
    print("\n[INFO] 두 번째 추론 실행 중...")
    reasoner2 = OWLReasoner(first_inferred)
    second_inferred = reasoner2.run_inference(include_rdfs=True)
    
    if second_inferred is None:
        print("[ERROR] 두 번째 추론 실패")
        return
    
    second_count = len(set(second_inferred))
    stats2 = reasoner2.get_stats()
    print(f"[INFO] 두 번째 추론 완료: {first_count} → {second_count} triples (+{stats2.get('new_inferences', 0)})")
    
    # 차이 분석
    print("\n[INFO] 트리플 차이 분석 중...")
    first_triples = set(first_inferred)
    second_triples = set(second_inferred)
    
    additional_triples = second_triples - first_triples
    additional_count = len(additional_triples)
    
    print(f"\n[결과] 추가된 트리플 수: {additional_count}개")
    
    if additional_count == 0:
        print("[INFO] 추가 트리플이 없습니다. 첫 번째 추론이 완전합니다.")
        return
    
    # 추가된 트리플 분석
    print(f"\n[분석] 추가된 {additional_count}개 트리플 분석 중...")
    
    # 1. 속성(프레디케이트)별 분류
    predicate_count = defaultdict(int)
    predicate_examples = defaultdict(list)
    
    for triple in additional_triples:
        s, p, o = triple
        predicate_str = str(p)
        predicate_count[predicate_str] += 1
        
        # 각 속성별로 최대 5개 예시 저장
        if len(predicate_examples[predicate_str]) < 5:
            predicate_examples[predicate_str].append({
                'subject': str(s),
                'object': str(o)
            })
    
    print(f"\n[분석 1] 속성(프레디케이트)별 분류:")
    print(f"{'속성':<60} {'개수':<10} {'비율':<10}")
    print("-" * 80)
    
    sorted_predicates = sorted(predicate_count.items(), key=lambda x: x[1], reverse=True)
    for pred, count in sorted_predicates:
        ratio = (count / additional_count) * 100
        print(f"{pred:<60} {count:<10} {ratio:>6.2f}%")
    
    # 2. 주제(Subject)별 분류
    subject_count = defaultdict(int)
    subject_examples = defaultdict(list)
    
    for triple in additional_triples:
        s, p, o = triple
        subject_str = str(s)
        subject_count[subject_str] += 1
        
        if len(subject_examples[subject_str]) < 3:
            subject_examples[subject_str].append({
                'predicate': str(p),
                'object': str(o)
            })
    
    print(f"\n[분석 2] 주제(Subject)별 분류 (상위 20개):")
    print(f"{'주제':<80} {'개수':<10}")
    print("-" * 90)
    
    sorted_subjects = sorted(subject_count.items(), key=lambda x: x[1], reverse=True)[:20]
    for subj, count in sorted_subjects:
        print(f"{subj:<80} {count:<10}")
    
    # 3. 객체(Object)별 분류
    object_count = defaultdict(int)
    
    for triple in additional_triples:
        s, p, o = triple
        object_str = str(o)
        object_count[object_str] += 1
    
    print(f"\n[분석 3] 객체(Object)별 분류 (상위 20개):")
    print(f"{'객체':<80} {'개수':<10}")
    print("-" * 90)
    
    sorted_objects = sorted(object_count.items(), key=lambda x: x[1], reverse=True)[:20]
    for obj, count in sorted_objects:
        print(f"{obj:<80} {count:<10}")
    
    # 4. RDF 타입 트리플 분석
    rdf_type_triples = [t for t in additional_triples if t[1] == RDF.type]
    print(f"\n[분석 4] RDF 타입 트리플: {len(rdf_type_triples)}개")
    if len(rdf_type_triples) > 0:
        print("예시 (최대 10개):")
        for i, (s, p, o) in enumerate(rdf_type_triples[:10]):
            print(f"  {i+1}. {s} -> {o}")
    
    # 5. RDFS 관련 트리플 분석
    rdfs_triples = [t for t in additional_triples if str(t[1]).startswith(str(RDFS))]
    print(f"\n[분석 5] RDFS 관련 트리플: {len(rdfs_triples)}개")
    if len(rdfs_triples) > 0:
        print("예시 (최대 10개):")
        for i, (s, p, o) in enumerate(rdfs_triples[:10]):
            print(f"  {i+1}. {s} --{p}--> {o}")
    
    # 6. OWL 관련 트리플 분석
    owl_triples = [t for t in additional_triples if str(t[1]).startswith(str(OWL))]
    print(f"\n[분석 6] OWL 관련 트리플: {len(owl_triples)}개")
    if len(owl_triples) > 0:
        print("예시 (최대 10개):")
        for i, (s, p, o) in enumerate(owl_triples[:10]):
            print(f"  {i+1}. {s} --{p}--> {o}")
    
    # 7. 도메인 온톨로지 트리플 분석 (실제 데이터 관계)
    domain_triples = [t for t in additional_triples 
                     if not str(t[1]).startswith(str(RDF)) 
                     and not str(t[1]).startswith(str(RDFS))
                     and not str(t[1]).startswith(str(OWL))]
    print(f"\n[분석 7] 도메인 온톨로지 트리플 (실제 데이터 관계): {len(domain_triples)}개")
    if len(domain_triples) > 0:
        print("예시 (최대 20개):")
        for i, (s, p, o) in enumerate(domain_triples[:20]):
            print(f"  {i+1}. {s}")
            print(f"      --{p}-->")
            print(f"      {o}")
            print()
    
    # 8. 상세 예시 출력 (주요 속성별)
    print(f"\n[분석 8] 주요 속성별 상세 예시:")
    for pred, count in sorted_predicates[:10]:
        if count > 0:
            print(f"\n속성: {pred} ({count}개)")
            examples = predicate_examples[pred]
            for i, ex in enumerate(examples[:3]):
                print(f"  {i+1}. {ex['subject']}")
                print(f"     --{pred}-->")
                print(f"     {ex['object']}")
    
    # 9. 결과를 파일로 저장
    output_file = project_root / "outputs" / "inference_difference_analysis.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    analysis_result = {
        "summary": {
            "original_triples": original_count,
            "first_inference_triples": first_count,
            "second_inference_triples": second_count,
            "additional_triples": additional_count,
            "first_inference_new": stats1.get('new_inferences', 0),
            "second_inference_new": stats2.get('new_inferences', 0)
        },
        "predicate_analysis": {
            pred: {
                "count": count,
                "ratio": (count / additional_count) * 100,
                "examples": predicate_examples[pred]
            }
            for pred, count in sorted_predicates
        },
        "sample_triples": [
            {
                "subject": str(s),
                "predicate": str(p),
                "object": str(o)
            }
            for s, p, o in list(additional_triples)[:100]  # 최대 100개 샘플
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[INFO] 분석 결과가 파일로 저장되었습니다: {output_file}")
    
    # 10. 결론 및 권장사항
    print(f"\n[결론]")
    print(f"- 추가된 트리플 수: {additional_count}개")
    print(f"- 주요 속성 수: {len(predicate_count)}개")
    
    # RDF/RDFS/OWL 메타데이터 트리플 비율
    metadata_triples = len(rdf_type_triples) + len(rdfs_triples) + len(owl_triples)
    metadata_ratio = (metadata_triples / additional_count) * 100 if additional_count > 0 else 0
    domain_ratio = (len(domain_triples) / additional_count) * 100 if additional_count > 0 else 0
    
    print(f"- 메타데이터 트리플 (RDF/RDFS/OWL): {metadata_triples}개 ({metadata_ratio:.1f}%)")
    print(f"- 도메인 온톨로지 트리플 (실제 데이터 관계): {len(domain_triples)}개 ({domain_ratio:.1f}%)")
    
    if domain_ratio > 50:
        print("\n[권장사항] 도메인 온톨로지 트리플이 50% 이상입니다. 이 트리플들은 실제 데이터 관계이므로 유의미할 가능성이 높습니다.")
    elif metadata_ratio > 80:
        print("\n[권장사항] 메타데이터 트리플이 80% 이상입니다. 이 트리플들은 주로 스키마 정보이므로 중복일 가능성이 높습니다.")
    else:
        print("\n[권장사항] 메타데이터와 도메인 트리플이 혼재되어 있습니다. 상세 분석이 필요합니다.")

if __name__ == "__main__":
    analyze_inference_difference()
