#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
541개 트리플 상세 분석 스크립트
첫 번째 추론 후 검증 전(12,834)과 검증 후(13,375)의 차이를 분석
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL
from owlrl import DeductiveClosure, OWLRL_Semantics, RDFS_Semantics
from collections import defaultdict
import json

def analyze_541_triples():
    """첫 번째 추론 후 검증 전/후의 차이를 분석하여 541개 트리플의 내용 확인"""
    
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
    
    # 첫 번째 추론 실행 (검증 전)
    print("\n[INFO] 첫 번째 추론 실행 중 (검증 전)...")
    inferred_graph = Graph()
    for triple in original_graph:
        inferred_graph.add(triple)
    
    # RDFS 추론
    DeductiveClosure(RDFS_Semantics).expand(inferred_graph)
    rdfs_count = len(set(inferred_graph))
    print(f"[INFO] RDFS 추론 후: {rdfs_count} triples")
    
    # OWL-RL 추론
    DeductiveClosure(OWLRL_Semantics).expand(inferred_graph)
    before_verification_count = len(set(inferred_graph))
    print(f"[INFO] OWL-RL 추론 후 (검증 전): {before_verification_count} triples")
    
    # 검증: 한 번 더 추론 실행
    print("\n[INFO] 완전성 검증 실행 중...")
    before_verification_triples = set(inferred_graph)
    
    # RDFS 추론 한 번 더
    DeductiveClosure(RDFS_Semantics).expand(inferred_graph)
    
    # OWL-RL 추론 한 번 더
    DeductiveClosure(OWLRL_Semantics).expand(inferred_graph)
    
    after_verification_count = len(set(inferred_graph))
    after_verification_triples = set(inferred_graph)
    print(f"[INFO] 검증 후: {after_verification_count} triples")
    
    # 차이 분석
    additional_triples = after_verification_triples - before_verification_triples
    additional_count = len(additional_triples)
    
    print(f"\n[결과] 추가된 트리플 수: {additional_count}개")
    print(f"  검증 전: {before_verification_count} triples")
    print(f"  검증 후: {after_verification_count} triples")
    print(f"  차이: +{additional_count} triples")
    
    if additional_count == 0:
        print("[INFO] 추가 트리플이 없습니다.")
        return
    
    # 추가된 트리플 상세 분석
    print(f"\n[상세 분석] 추가된 {additional_count}개 트리플 분석 중...")
    
    # 1. 속성(프레디케이트)별 분류
    predicate_count = defaultdict(int)
    predicate_examples = defaultdict(list)
    
    for triple in additional_triples:
        s, p, o = triple
        predicate_str = str(p)
        predicate_count[predicate_str] += 1
        
        if len(predicate_examples[predicate_str]) < 10:
            predicate_examples[predicate_str].append({
                'subject': str(s),
                'object': str(o)
            })
    
    print(f"\n[분석 1] 속성(프레디케이트)별 분류:")
    print(f"{'속성':<80} {'개수':<10} {'비율':<10}")
    print("-" * 100)
    
    sorted_predicates = sorted(predicate_count.items(), key=lambda x: x[1], reverse=True)
    for pred, count in sorted_predicates:
        ratio = (count / additional_count) * 100
        print(f"{pred:<80} {count:<10} {ratio:>6.2f}%")
    
    # 2. RDFS subClassOf 트리플 상세 분석 (가장 많은 트리플)
    rdfs_subclass_triples = [t for t in additional_triples if t[1] == RDFS.subClassOf]
    print(f"\n[분석 2] RDFS subClassOf 트리플 상세 분석 ({len(rdfs_subclass_triples)}개):")
    
    # 리터럴 값별 분류
    literal_subjects = defaultdict(list)
    for s, p, o in rdfs_subclass_triples:
        if isinstance(s, Literal):
            literal_value = str(s)
            literal_subjects[literal_value].append(str(o))
    
    print(f"\n리터럴 값별 분류 (상위 30개):")
    print(f"{'리터럴 값':<40} {'개수':<10} {'타입':<50}")
    print("-" * 100)
    
    sorted_literals = sorted(literal_subjects.items(), key=lambda x: len(x[1]), reverse=True)[:30]
    for literal_val, types in sorted_literals:
        print(f"{literal_val:<40} {len(types):<10} {', '.join(set(types))[:50]}")
    
    # 3. RDF type 트리플 분석
    rdf_type_triples = [t for t in additional_triples if t[1] == RDF.type]
    print(f"\n[분석 3] RDF type 트리플 ({len(rdf_type_triples)}개):")
    for i, (s, p, o) in enumerate(rdf_type_triples[:20]):
        print(f"  {i+1}. {s}")
        print(f"     --type--> {o}")
    
    # 4. OWL sameAs 트리플 분석
    owl_sameas_triples = [t for t in additional_triples if t[1] == OWL.sameAs]
    print(f"\n[분석 4] OWL sameAs 트리플 ({len(owl_sameas_triples)}개):")
    for i, (s, p, o) in enumerate(owl_sameas_triples[:20]):
        print(f"  {i+1}. {s}")
        print(f"     --sameAs--> {o}")
    
    # 5. 에러 관련 트리플 분석
    error_triples = [t for t in additional_triples if 'error' in str(t[1]).lower()]
    print(f"\n[분석 5] 에러 관련 트리플 ({len(error_triples)}개):")
    for i, (s, p, o) in enumerate(error_triples[:20]):
        print(f"  {i+1}. {s}")
        print(f"     --{p}-->")
        print(f"     {o}")
    
    # 6. 도메인 온톨로지 트리플 (실제 데이터 관계)
    domain_triples = [t for t in additional_triples 
                     if not str(t[1]).startswith(str(RDF)) 
                     and not str(t[1]).startswith(str(RDFS))
                     and not str(t[1]).startswith(str(OWL))]
    print(f"\n[분석 6] 도메인 온톨로지 트리플 (실제 데이터 관계): {len(domain_triples)}개")
    for i, (s, p, o) in enumerate(domain_triples):
        print(f"  {i+1}. {s}")
        print(f"     --{p}-->")
        print(f"     {o}")
    
    # 7. 결과 요약 및 평가
    print(f"\n[결론 및 평가]")
    print(f"=" * 100)
    
    # 메타데이터 트리플 비율
    metadata_triples = len(rdf_type_triples) + len(rdfs_subclass_triples) + len(owl_sameas_triples)
    metadata_ratio = (metadata_triples / additional_count) * 100 if additional_count > 0 else 0
    domain_ratio = (len(domain_triples) / additional_count) * 100 if additional_count > 0 else 0
    
    print(f"\n1. 트리플 구성:")
    print(f"   - 총 추가 트리플: {additional_count}개")
    print(f"   - 메타데이터 트리플 (RDF/RDFS/OWL): {metadata_triples}개 ({metadata_ratio:.1f}%)")
    print(f"   - 도메인 온톨로지 트리플 (실제 데이터 관계): {len(domain_triples)}개 ({domain_ratio:.1f}%)")
    
    print(f"\n2. 주요 속성:")
    for pred, count in sorted_predicates[:5]:
        ratio = (count / additional_count) * 100
        print(f"   - {pred}: {count}개 ({ratio:.1f}%)")
    
    print(f"\n3. 유의미성 평가:")
    
    # RDFS subClassOf는 리터럴 값의 타입 정보이므로 대부분 불필요
    if len(rdfs_subclass_triples) > additional_count * 0.8:
        print(f"   ⚠️  RDFS subClassOf 트리플이 {len(rdfs_subclass_triples)}개 ({len(rdfs_subclass_triples)/additional_count*100:.1f}%)로 대부분을 차지합니다.")
        print(f"      → 이 트리플들은 리터럴 값(숫자, 문자열 등)이 rdfs:Literal의 하위 클래스임을 나타냅니다.")
        print(f"      → 실제 데이터 관계가 아닌 메타데이터이므로 유의미하지 않을 가능성이 높습니다.")
    
    # 에러 관련 트리플은 문제를 나타냄
    if len(error_triples) > 0:
        print(f"   ⚠️  에러 관련 트리플이 {len(error_triples)}개 발견되었습니다.")
        print(f"      → 이는 온톨로지에 불일치(inconsistency)가 있음을 나타낼 수 있습니다.")
        print(f"      → 예: 'Disjoint classes boolean and float have a common individual'")
    
    # 도메인 트리플이 적으면 대부분 메타데이터
    if domain_ratio < 10:
        print(f"   ✅ 도메인 온톨로지 트리플이 {domain_ratio:.1f}%로 매우 적습니다.")
        print(f"      → 추가된 트리플의 대부분이 메타데이터이므로 유의미하지 않을 가능성이 높습니다.")
        print(f"      → 첫 번째 추론 결과(12,834)가 실제 데이터 관계 측면에서 완전합니다.")
    else:
        print(f"   ⚠️  도메인 온톨로지 트리플이 {domain_ratio:.1f}%로 상당합니다.")
        print(f"      → 일부 실제 데이터 관계가 누락되었을 수 있습니다.")
    
    # 결과를 파일로 저장
    output_file = project_root / "outputs" / "541_triples_analysis.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    analysis_result = {
        "summary": {
            "before_verification": before_verification_count,
            "after_verification": after_verification_count,
            "additional_triples": additional_count
        },
        "predicate_analysis": {
            pred: {
                "count": count,
                "ratio": (count / additional_count) * 100,
                "examples": predicate_examples[pred][:5]
            }
            for pred, count in sorted_predicates
        },
        "rdfs_subclass_analysis": {
            "count": len(rdfs_subclass_triples),
            "ratio": (len(rdfs_subclass_triples) / additional_count) * 100,
            "literal_examples": dict(list(literal_subjects.items())[:20])
        },
        "error_triples": [
            {
                "subject": str(s),
                "predicate": str(p),
                "object": str(o)
            }
            for s, p, o in error_triples
        ],
        "domain_triples": [
            {
                "subject": str(s),
                "predicate": str(p),
                "object": str(o)
            }
            for s, p, o in domain_triples
        ],
        "all_triples_sample": [
            {
                "subject": str(s),
                "predicate": str(p),
                "object": str(o)
            }
            for s, p, o in list(additional_triples)[:100]
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[INFO] 분석 결과가 파일로 저장되었습니다: {output_file}")

if __name__ == "__main__":
    analyze_541_triples()
