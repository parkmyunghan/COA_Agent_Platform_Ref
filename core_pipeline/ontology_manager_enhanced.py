# core_pipeline/ontology_manager_enhanced.py
# -*- coding: utf-8 -*-
"""
Enhanced Ontology Manager
현재 시스템의 온톨로지 생성 및 인스턴스 생성 로직 통합
"""
import os
import sys
import json
import re
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
import pandas as pd
from pathlib import Path

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, OWL, XSD, BNode
    from rdflib.plugins.sparql import prepareQuery
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False
    from common.logger import get_logger
    logger = get_logger("OntologyManager")
    logger.warning("rdflib not installed. Ontology features will be limited.")


def _localname(u) -> str:
    """URI에서 로컬 이름 추출 (Enhanced)"""
    s = str(u)
    if '#' in s:
        return s.split('#')[-1]
    return s.split('/')[-1]


def _make_uri_safe(s: str) -> str:
    """문자열을 URI 안전한 형식으로 변환"""
    if not s:
        return ""
    # 공백 및 특수문자 처리 (공백을 언더바로)
    s = str(s).strip().replace(" ", "_").replace("\t", "_").replace("\n", "_")
    # URI에 부적합한 특수문자 제거 (한글, 영문, 숫자, 언더바, 대시만 허용)
    import re
    s = re.sub(r'[^\w\d_가-힣\-]', '', s)
    return s


def _get_label(g: Graph, ns: Namespace, u) -> str:
    """
    그래프에서 노드의 라벨 가져오기
    
    주의: 이 함수는 rdfs:label을 우선 반환하지만,
    to_json()에서 ID와 조합하여 표시하므로 실제 표시는 ID 우선이 됩니다.
    """
    for _, _, lbl in g.triples((u, RDFS.label, None)):
        try:
            return str(lbl)
        except Exception:
            pass
    for _, _, lbl in g.triples((u, ns.name, None)):
        try:
            return str(lbl)
        except Exception:
            pass
    return _localname(u)


def safe_print(msg, also_log_file: bool = True):
    """안전한 출력 함수 (개선된 버전 사용)"""
    from common.utils import safe_print as _safe_print
    _safe_print(msg, also_log_file=also_log_file, logger_name="OntologyManager")


# 테이블별 표준 ID 컬럼명 매핑
STANDARD_ID_COLUMNS = {
    "임무정보": ["임무ID", "mission_id", "ID"],
    "전장축선": ["축선ID", "axis_id", "ID"],
    "지형셀": ["지형셀ID", "terrain_cell_id", "ID"],
    "아군부대현황": ["아군부대ID", "friendly_unit_id", "ID"],
    "적군부대현황": ["적군부대ID", "enemy_unit_id", "ID"],
    "위협상황": ["위협ID", "threat_id", "ID"],
    "제약조건": ["제약ID", "constraint_id", "ID"],
    "COA_Library": ["COA_ID", "coa_id", "ID"],
    "방책유형_위협유형_관련성": ["coa_type"],
    "임무별_자원할당": ["allocation_id", "ID"],
    "기상상황": ["weather_id"],
}

# 테이블별 표준 라벨 컬럼명 매핑
STANDARD_LABEL_COLUMNS = {
    "임무정보": ["임무명", "mission_name", "name"],
    "전장축선": ["축선명", "axis_name", "name"],
    "지형셀": ["지형명", "terrain_name", "name"],
    "아군부대현황": ["아군부대명", "부대명", "unit_name", "name"],
    "적군부대현황": ["적군부대명", "부대명", "unit_name", "name"],
    "위협상황": [],  # 라벨 컬럼 없음 (ID만 사용)
    "제약조건": [],  # 라벨 컬럼 없음 (ID만 사용)
    "COA_Library": ["명칭", "name", "coa_name"],
    "임무별_자원할당": ["resource_alias", "resource_name", "name"],
}


def suggest_id_column(table_name: str, columns: List[str]) -> str:
    """
    테이블의 식별자 컬럼을 자동 제안 (개선 버전)
    
    우선순위:
    1. 테이블별 표준 ID 컬럼명
    2. 패턴 기반 감지
    3. 첫 번째 컬럼 (폴백)
    """
    # 1. 테이블별 표준 ID 컬럼명 우선 확인
    if table_name in STANDARD_ID_COLUMNS:
        for standard_col in STANDARD_ID_COLUMNS[table_name]:
            if standard_col in columns:
                # 🔥 최적화: 반복 로그 제거 (200회 이상 출력 방지)
                # safe_print(f"[DEBUG] 표준 ID 컬럼 감지: {table_name}.{standard_col}")
                return standard_col
    
    # 2. 패턴 기반 감지 (기존 로직 개선)
    patterns = [
        r"^.*_id$|^.*_key$|^id$",  # 영문 형식 (mission_id, axis_id 등)
        r"^.*id$|^.*ID$",  # 대소문자 모두 인식 (임무ID, 축선ID 등)
        r"식별자|키",
    ]
    for col in columns:
        col_l = col.lower()
        for p in patterns:
            if re.search(p, col_l):
                # 🔥 최적화: 반복 로그 제거
                # safe_print(f"[DEBUG] 패턴 기반 ID 컬럼 감지: {table_name}.{col}")
                return col
    
    # 3. 폴백: 첫 번째 컬럼
    fallback_col = columns[0] if columns else ""
    if fallback_col:
        safe_print(f"[WARN] {table_name} 테이블에서 ID 컬럼을 찾지 못해 첫 번째 컬럼 사용: {fallback_col}")
    return fallback_col


def suggest_label_column(table_name: str, columns: List[str]) -> str:
    """
    테이블의 라벨 컬럼을 자동 제안 (ID 컬럼 제외)
    
    Args:
        table_name: 테이블명
        columns: 컬럼 리스트
    """
    # ID 컬럼 감지 (제외 대상)
    id_col = suggest_id_column(table_name, columns)
    
    # ID 컬럼 제외 리스트 생성
    exclude_columns = set()
    if id_col:
        exclude_columns.add(id_col)
    
    # ID 패턴을 포함하는 컬럼도 제외
    id_patterns = [
        r"^.*_id$|^.*_key$|^id$",  # 영문 형식
        r"^.*id$|^.*ID$",  # 대소문자 모두
        r"식별자|키",
    ]
    for col in columns:
        if col in exclude_columns:
            continue
        col_l = col.lower()
        for p in id_patterns:
            if re.search(p, col_l):
                exclude_columns.add(col)
                break
    
    # 1. 테이블별 표준 라벨 컬럼명 우선 확인
    if table_name in STANDARD_LABEL_COLUMNS:
        for standard_col in STANDARD_LABEL_COLUMNS[table_name]:
            if standard_col in columns and standard_col not in exclude_columns:
                safe_print(f"[DEBUG] 표준 라벨 컬럼 감지: {table_name}.{standard_col}")
                return standard_col
        # 표준 라벨 컬럼이 빈 리스트면 라벨 컬럼 없음 (ID만 사용)
        if STANDARD_LABEL_COLUMNS[table_name] == []:
            safe_print(f"[DEBUG] {table_name} 테이블은 라벨 컬럼이 없습니다 (ID만 사용)")
            return ""
    
    # 2. 패턴 기반 감지 (ID 컬럼 제외)
    patterns = [
        r"name|label|title|명|이름",
        r"description|설명|내용",
        r"^.*_name$|^.*_label$",
    ]
    for col in columns:
        if col in exclude_columns:
            continue
        col_l = col.lower()
        for p in patterns:
            if re.search(p, col_l):
                safe_print(f"[DEBUG] 패턴 기반 라벨 컬럼 감지: {table_name}.{col}")
                return col
    
    # 3. 패턴 매칭 실패 시 빈 문자열 반환 (ID만 사용)
    safe_print(f"[DEBUG] {table_name} 테이블에서 라벨 컬럼을 찾지 못해 ID만 사용합니다")
    return ""


class EnhancedOntologyManager:
    """강화된 온톨로지 관리자 (현재 시스템 로직 통합)"""
    
    # 영문 관계명 매핑 테이블 (한글 테이블명 -> 영문 관계명)
    RELATION_NAME_MAPPING = {
        "임무정보": "hasMission",
        "지형셀": "locatedIn",
        "전장축선": "hasAxis",
        "적군부대현황": "hasEnemyUnit",
        "아군부대현황": "hasFriendlyUnit",
        "위협상황": "hasThreat",
        "제약조건": "appliesTo"
    }
    
    # 전략유형 값 매핑 (영문 ↔ 한글)
    STRATEGY_TYPE_MAPPING = {
        'offensive': ['공격', 'offensive'],
        'defensive': ['방어', 'defensive'],
        '공격': ['offensive', '공격'],
        '방어': ['defensive', '방어']
    }
    
    def __init__(self, config: Dict):
        """
        Args:
            config: 설정 딕셔너리
        """
        self.config = config
        
        # [NEW] 통계용 카운터
        self.virtual_entities_count = 0
        
        # 네임스페이스 직접 초기화 (base 의존성 제거)
        if RDFLIB_AVAILABLE:
            self.graph = Graph()
            # 통일된 네임스페이스 사용 (COA Agent Platform)
            self.ns = Namespace("http://coa-agent-platform.org/ontology#")
            self.ns_legacy = Namespace("http://coa-agent-platform.org/ontology#")  # Legacy alias updated to match standard
            # [NEW] 가상 엔티티 전용 네임스페이스
            self.virtual_ns = Namespace("http://coa-agent-platform.org/ontology/virtual#")
        else:
            self.graph = None
            self.ns = None
            self.ns_legacy = None
            self.virtual_ns = None # Ensure virtual_ns is also None if RDFLib is not available
        
        # [INFO] 초기화 완료 메시지
        # safe_print(f"[INFO] EnhancedOntologyManager 초기화 완료")
        
        # OntologyManager와 동일한 속성 추가
        self.ontology_path = config.get("ontology_path", "./knowledge/ontology")
        # data_manager는 나중에 설정 (순환 참조 방지)
        self.data_manager = None
        
        # 메타데이터 경로
        self.metadata_path = config.get("metadata_path", "./metadata")
        self.data_lake_path = config.get("data_lake_path", "./data_lake")
        self.output_path = config.get("output_path", "./outputs")
        
        # 추론 여부 판단을 위한 원본 그래프 크기 추적
        self._original_graph_size = None  # instances.ttl 로드 직후의 원본 크기
        self._inference_performed = False  # 추론 실행 여부 플래그
        
        # 추론 실행 여부 플래그 (중복 추론 방지)
        self._inference_performed = False
        
        # 스키마 레지스트리 로드
        self.schema_registry = self._load_schema_registry()
        
        # 기존 그래프 자동 로드 시도
        self.try_load_existing_graph()
        
        # 관계 매핑 캐시
        self._relation_mappings = None
        self._relation_mappings_cache_time = {}  # 파일별 수정 시간 캐시
        
        # [NEW] JSON 직렬화 캐시
        self._json_cache = None
        self._last_graph_hash = None

    def _load_schema_registry(self) -> Dict:
        """Schema Registry 로드 (YAML)"""
        import yaml
        registry_path = os.path.join(self.metadata_path, "schema_registry.yaml")
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f).get('tables', {})
            except Exception as e:
                safe_print(f"[WARN] Schema Registry 로드 실패: {e}")
                return {}
        return {}

    def get_id_column(self, table_name: str, columns: List[str]) -> str:
        """ID 컬럼 조회 (Schema Registry 우선)"""
        # 1. Schema Registry 확인
        if table_name in self.schema_registry:
            table_info = self.schema_registry[table_name]
            for col_name, col_info in table_info.get('columns', {}).items():
                if col_info.get('pk'):
                    if col_name in columns:
                        return col_name
                    # 대소문자 차이 등으로 못 찾을 경우를 대비해 컬럼 목록에서 검색
                    for c in columns:
                        if c.lower() == col_name.lower():
                            return c
        
        # 2. 기존 로직 폴백
        return suggest_id_column(table_name, columns)

    def get_label_column(self, table_name: str, columns: List[str]) -> str:
        """Label 컬럼 조회 (Schema Registry 우선)"""
        # 1. Schema Registry 확인
        if table_name in self.schema_registry:
            table_info = self.schema_registry[table_name]
            for col_name, col_info in table_info.get('columns', {}).items():
                if col_info.get('label'):
                    if col_name in columns:
                        return col_name
                    for c in columns:
                        if c.lower() == col_name.lower():
                            return c
        
        # 2. 기존 로직 폴백
        return suggest_label_column(table_name, columns)
    
    
    def get_schema_summary(self) -> str:
        """
        [NEW] 온톨로지 스키마 요약 정보 추출 (LLM 프롬프트용)
        그래프에 정의된 클래스와 주요 속성을 요약하여 문자열로 반환
        """
        if not self.graph:
            return "Ontology graph is empty."
        
        summary = ["# Ontology Schema Summary"]
        
        try:
            # 1. 주요 클래스 추출
            query_classes = """
            SELECT DISTINCT ?type WHERE {
                ?s a ?type .
                FILTER(STRSTARTS(STR(?type), STR(def:)))
            }
            LIMIT 20
            """
            
            # 2. 주요 속성 추출 (ObjectProperty & DatatypeProperty)
            query_props = """
            SELECT DISTINCT ?prop WHERE {
                ?s ?prop ?o .
                FILTER(STRSTARTS(STR(?prop), STR(def:)))
            }
            LIMIT 30
            """
            
            # 네임스페이스 바인딩 (쿼리에 def: 사용을 위해 필요할 수 있음, 여기선 전체 URI 사용하거나 bind 필요)
            # 여기서는 편의상 query 메서드 내부에서 처리되거나, 풀 URI 매칭 등 고려
            # 단순화를 위해 graph.predicates(), graph.objects() 등 활용 가능하나 SPARQL이 확실함
            
            # 클래스 수집 (간소화)
            classes = set()
            for s, p, o in self.graph.triples((None, RDF.type, None)):
                if str(o).startswith(str(self.ns)):
                    classes.add(_localname(o))
            
            summary.append(f"## Classes ({len(classes)}):")
            summary.append(", ".join(sorted(list(classes))))
            
            # 속성 수집 (Domain/Range 포함하면 좋으나 일단 이름만)
            props = set()
            for s, p, o in self.graph:
                if str(p).startswith(str(self.ns)):
                    props.add(_localname(p))
            
            summary.append(f"\n## Properties ({len(props)}):")
            summary.append(", ".join(sorted(list(props))))
            
            # 주요 관계 샘플 (Few-shot)
            summary.append("\n## Relationships:")
            relationships = [
                "def:OptimizationGoal -> def:hasMechanism -> def:Mechanism",
                "def:COA -> def:respondsTo -> def:ThreatEvent",
                "def:Unit -> def:hasType -> xsd:string",
                "def:Terrain -> def:hasEffect -> def:Effect"
            ]
            summary.extend([f"- {r}" for r in relationships])
            
        except Exception as e:
            summary.append(f"Error extracting schema: {e}")
            
        return "\n".join(summary)

    def load_relation_mappings(self, force_reload: bool = False) -> List[Dict]:
        """
        관계 매핑 로드 (Schema Registry 통합)
        """
        # 강제 재로드가 아니고 캐시가 있으면 반환
        if not force_reload and self._relation_mappings is not None:
            return self._relation_mappings
        
        relation_mappings = []
        
        # 1. Schema Registry에서 관계 로드 (최우선)
        for table_name, table_info in self.schema_registry.items():
            relations = table_info.get('relations', [])
            for rel in relations:
                mapping = {
                    "src_table": table_name,
                    "src_col": rel.get('source_col'),
                    "tgt_table": rel.get('target_table'),
                    "relation": rel.get('name'),
                    "source": "schema_registry"
                }
                
                # 동적 매핑 처리
                if rel.get('target_table') == 'dynamic':
                    mapping['dynamic'] = True
                    mapping['type_col'] = rel.get('type_col')
                    mapping['type_mapping'] = rel.get('type_mapping')
                
                # 추론 관계 처리
                if rel.get('type') == 'inference':
                    mapping['inferred'] = True
                    mapping['confidence'] = rel.get('confidence', 0.8)
                
                relation_mappings.append(mapping)
        
        # 2. 기존 relation_mappings.json 로드 (하위 호환성)
        # Schema Registry에 없는 테이블만 추가
        existing_tables = set(self.schema_registry.keys())
        
        rel_mapping_path = os.path.join(self.metadata_path, "relation_mappings.json")
        if os.path.exists(rel_mapping_path):
            try:
                with open(rel_mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                
                if isinstance(mapping_data, dict):
                    for src_table, col_mappings in mapping_data.items():
                        if src_table in existing_tables:
                            continue  # 이미 Registry에서 로드함
                            
                        for src_col, mapping_value in col_mappings.items():
                            # 동적 FK 관계 처리
                            if isinstance(mapping_value, dict) and mapping_value.get("type_column"):
                                relation_mappings.append({
                                    "src_table": src_table,
                                    "src_col": src_col,
                                    "tgt_table": mapping_value.get("target", "동적"),
                                    "tgt_col": None,
                                    "relation": mapping_value.get("relation", "appliesTo"),
                                    "type_column": mapping_value.get("type_column"),
                                    "type_mapping": mapping_value.get("type_mapping", {}),
                                    "dynamic": True,
                                    "inferred": False,
                                    "confidence": 1.0,
                                    "source": "relation_mappings.json"
                                })
                                continue
                            
                            # 객체 형태 FK 관계 처리 (사용자 지정 관계명)
                            if isinstance(mapping_value, dict):
                                # relation 필드가 있으면 그대로 사용, 없으면 기본값 사용
                                relation_name = mapping_value.get("relation")
                                if not relation_name:
                                    target_table = mapping_value.get("target")
                                    relation_name = f"has{target_table}"  # 기본값: has{테이블명}
                                
                                relation_mappings.append({
                                    "src_table": src_table,
                                    "src_col": src_col,
                                    "tgt_table": mapping_value.get("target"),
                                    "tgt_col": None,
                                    "relation": relation_name,
                                    "inferred": False,
                                    "confidence": 1.0,
                                    "source": "relation_mappings.json"
                                })
                                continue
                            
                            # 일반 FK 관계 처리 (단순 문자열)
                            if isinstance(mapping_value, str):
                                # 기본값: has{테이블명} (사용자가 relation_mappings.json에 명시적으로 지정하지 않으면)
                                relation_mappings.append({
                                    "src_table": src_table,
                                    "src_col": src_col,
                                    "tgt_table": mapping_value,
                                    "tgt_col": None,
                                    "relation": f"has{mapping_value}",
                                    "inferred": False,
                                    "confidence": 1.0,
                                    "source": "relation_mappings.json"
                                })
                
                elif isinstance(mapping_data, list):
                    relation_mappings = mapping_data
                    for rel_map in relation_mappings:
                        rel_map["source"] = "relation_mappings.json"
            
            except Exception as e:
                safe_print(f"관계 매핑 로드 오류: {e}")
        
        # 2. schema_registry.yaml에서 FK 정보 로드 및 통합 (테이블정의서 대체)
        try:
            # schema_registry.yaml의 relations 섹션에서 FK 정보 추출
            for table_name, table_info in self.schema_registry.items():
                if not isinstance(table_info, dict):
                    continue
                
                # relations 섹션 확인
                relations = table_info.get('relations', [])
                if not relations:
                    continue
                
                for relation in relations:
                    if not isinstance(relation, dict):
                        continue
                    
                    source_col = relation.get('source_col')
                    target_table = relation.get('target_table')
                    relation_name = relation.get('name')
                    
                    if not source_col or not target_table:
                        continue
                    
                        # 중복 체크 (이미 relation_mappings.json에 있는 관계는 제외)
                        is_duplicate = False
                        for existing_rel in relation_mappings:
                            if (existing_rel.get('src_table') == table_name and 
                            existing_rel.get('src_col') == source_col):
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            # 관계명이 없으면 기본값 사용
                            if not relation_name:
                                relation_name = f"has{target_table}"
                            
                            relation_mappings.append({
                                "src_table": table_name,
                            "src_col": source_col,
                            "tgt_table": target_table,
                            "tgt_col": None,  # schema_registry.yaml에는 target_col 정보가 없음
                                "relation": relation_name,
                                "inferred": False,
                                "confidence": 1.0,
                            "source": "schema_registry.yaml"
                            })
                        safe_print(f"[INFO] schema_registry.yaml에서 FK 발견: {table_name}.{source_col} -> {target_table} (관계명: {relation_name})")
        
        except Exception as e:
            safe_print(f"[WARN] schema_registry.yaml FK 로드 오류: {e}")
        
        # 캐시 시간 업데이트
        self._update_cache_times()
        
        self._relation_mappings = relation_mappings
        return relation_mappings
    
    def _check_files_changed(self) -> bool:
        """관계 매핑 관련 파일들의 변경 시간 확인"""
        try:
            # 1. relation_mappings.json 확인
            rel_mapping_path = os.path.join(self.metadata_path, "relation_mappings.json")
            if os.path.exists(rel_mapping_path):
                current_mtime = os.path.getmtime(rel_mapping_path)
                cached_mtime = self._relation_mappings_cache_time.get(rel_mapping_path)
                if cached_mtime is None or current_mtime > cached_mtime:
                    return True
            
            # 2. schema_registry.yaml 확인
            schema_registry_path = os.path.join(self.metadata_path, "schema_registry.yaml")
            if os.path.exists(schema_registry_path):
                current_mtime = os.path.getmtime(schema_registry_path)
                cached_mtime = self._relation_mappings_cache_time.get(schema_registry_path)
                if cached_mtime is None or current_mtime > cached_mtime:
                    return True
            
            return False
        except Exception as e:
            safe_print(f"[WARN] 파일 변경 확인 오류: {e}")
            return True  # 오류 시 재로드
    
    def _update_cache_times(self):
        """캐시 시간 업데이트"""
        try:
            # relation_mappings.json
            rel_mapping_path = os.path.join(self.metadata_path, "relation_mappings.json")
            if os.path.exists(rel_mapping_path):
                self._relation_mappings_cache_time[rel_mapping_path] = os.path.getmtime(rel_mapping_path)
            
            # schema_registry.yaml
            schema_registry_path = os.path.join(self.metadata_path, "schema_registry.yaml")
            if os.path.exists(schema_registry_path):
                self._relation_mappings_cache_time[schema_registry_path] = os.path.getmtime(schema_registry_path)
        except Exception as e:
            safe_print(f"[WARN] 캐시 시간 업데이트 오류: {e}")
    
    def clear_relation_mappings_cache(self):
        """관계 매핑 캐시 무효화"""
        self._relation_mappings = None
        self._relation_mappings_cache_time = {}
        safe_print("[INFO] 관계 매핑 캐시가 무효화되었습니다.")
    
    # ========== Schema Auto-Sync Methods (NEW) ==========
    
    def _infer_dtype(self, series: pd.Series) -> str:
        """
        pandas Series에서 YAML 타입 추론
        
        Args:
            series: pandas Series
            
        Returns:
            "string", "number", "datetime", "boolean" 중 하나
        """
        dtype = str(series.dtype)
        
        if 'int' in dtype or 'float' in dtype:
            return "number"
        elif 'datetime' in dtype:
            return "datetime"
        elif 'bool' in dtype:
            return "boolean"
        else:
            return "string"
    
    def _infer_fk_target(self, col_name: str) -> Optional[str]:
        """
        컬럼명에서 FK 대상 테이블 추론
        
        Args:
            col_name: 컬럼명 (예: "임무ID", "mission_id")
            
        Returns:
            FK 대상 문자열 (예: "임무정보.임무ID") 또는 None
        """
        # FK 패턴: {테이블명}ID -> {테이블명}
        patterns = {
            '임무ID': '임무정보.임무ID',
            '축선ID': '전장축선.축선ID',
            '지형셀ID': '지형셀.지형셀ID',
            '아군부대ID': '아군부대현황.부대ID',
            '적군부대ID': '적군부대현황.부대ID',
            '위협ID': '위협상황.위협ID',
            '제약ID': '제약조건.제약ID',
            'mission_id': '임무정보.임무ID',
            'axis_id': '전장축선.축선ID',
            'terrain_cell_id': '지형셀.지형셀ID',
            'friendly_unit_id': '아군부대현황.부대ID',
            'enemy_unit_id': '적군부대현황.부대ID',
            'threat_id': '위협상황.위협ID',
        }
        
        # 직접 매핑 확인
        if col_name in patterns:
            return patterns[col_name]
        
        # 패턴 기반 추론 (부분 매칭)
        for pattern, target in patterns.items():
            if pattern.lower() in col_name.lower():
                return target
        
        return None
    
    def _save_schema_registry(self, registry_path: str):
        """
        schema_registry를 YAML 파일로 저장
        
        Args:
            registry_path: YAML 파일 경로
        """
        import yaml
        
        try:
            # 기존 파일 백업
            if os.path.exists(registry_path):
                backup_path = registry_path + '.backup'
                shutil.copy2(registry_path, backup_path)
                safe_print(f"[INFO] 기존 schema_registry.yaml 백업: {backup_path}")
            
            # YAML 저장
            with open(registry_path, 'w', encoding='utf-8') as f:
                yaml_data = {
                    'version': '1.1',
                    'last_updated': datetime.now().strftime('%Y-%m-%d'),
                    'tables': self.schema_registry
                }
                yaml.dump(yaml_data, f, allow_unicode=True, sort_keys=False)
            
            safe_print(f"[INFO] schema_registry.yaml 저장 완료: {registry_path}")
            
        except Exception as e:
            safe_print(f"[ERROR] schema_registry.yaml 저장 실패: {e}")
            raise
    
    def _infer_schema(self, table_name: str, df: pd.DataFrame) -> Dict:
        """
        DataFrame에서 스키마 자동 추론
        
        Args:
            table_name: 테이블명
            df: pandas DataFrame
            
        Returns:
            스키마 딕셔너리
        """
        schema = {
            'description': f'{table_name} (자동 생성)',
            'file_name': f'{table_name}.xlsx',
            'columns': {}
        }
        
        # PK 및 라벨 컬럼 추론
        columns_list = list(df.columns)
        id_col = self.get_id_column(table_name, columns_list)
        label_col = self.get_label_column(table_name, columns_list)
        
        for col in df.columns:
            col_info = {'type': self._infer_dtype(df[col])}
            
            if col == id_col:
                col_info['pk'] = True
            if col == label_col and label_col:
                col_info['label'] = True
            
            # FK 추론
            fk_target = self._infer_fk_target(col)
            if fk_target:
                col_info['fk'] = fk_target
            
            schema['columns'][col] = col_info
        
        safe_print(f"[INFO] {table_name} 스키마 자동 추론 완료 (PK: {id_col}, 라벨: {label_col if label_col else 'N/A'})")
        return schema
    
    def _sync_schema_registry(self, data: Dict[str, pd.DataFrame], 
                               auto_update: bool = True) -> Dict:
        """
        실제 데이터와 schema_registry.yaml 동기화
        
        Args:
            data: {테이블명: DataFrame} 딕셔너리
            auto_update: True일 경우 자동으로 YAML 파일 업데이트
            
        Returns:
            {
                'has_changes': bool,
                'new_tables': List[str],
                'updated_tables': List[str],
                'summary': str
            }
        """
        # 1. 현재 등록된 테이블 목록
        registered_tables = set(self.schema_registry.keys())
        
        # 2. 실제 존재하는 테이블 목록
        actual_tables = set(data.keys())
        
        # 3. 차이 분석
        new_tables = actual_tables - registered_tables
        
        if not new_tables:
            return {
                'has_changes': False,
                'new_tables': [],
                'updated_tables': [],
                'summary': '변경사항 없음'
            }
        
        safe_print(f"[INFO] 신규 테이블 {len(new_tables)}개 발견: {list(new_tables)}")
        
        # 4. 신규 테이블 스키마 자동 생성
        for table_name in new_tables:
            df = data[table_name]
            auto_schema = self._infer_schema(table_name, df)
            self.schema_registry[table_name] = auto_schema
            safe_print(f"[INFO] {table_name} 스키마 자동 등록 완료")
        
        # 5. YAML 파일 업데이트 (옵션)
        if auto_update:
            registry_path = os.path.join(self.metadata_path, "schema_registry.yaml")
            self._save_schema_registry(registry_path)
        
        return {
            'has_changes': True,
            'new_tables': sorted(list(new_tables)),
            'updated_tables': [],
            'summary': f"신규 테이블 {len(new_tables)}개 등록: {', '.join(sorted(list(new_tables)))}"
        }
    
    def _load_fk_from_schema(self, table_name: str, excel_file: Path) -> List[Dict]:
        """테이블정의서에서 FK 정보 추출"""
        fk_list = []
        
        try:
            # 엑셀 파일의 시트 목록 확인
            excel_file_obj = pd.ExcelFile(excel_file)
            sheet_names = excel_file_obj.sheet_names
            
            # 테이블정의서 시트 찾기
            schema_sheet = None
            for sheet in sheet_names:
                if "정의서" in sheet or "schema" in sheet.lower() or "정의" in sheet:
                    schema_sheet = sheet
                    break
            
            if not schema_sheet:
                return fk_list
            
            # 테이블정의서 읽기
            schema_df = pd.read_excel(excel_file, sheet_name=schema_sheet)
            
            # 컬럼명 정규화
            field_col = None
            fk_col = None
            relation_col = None
            
            for col in schema_df.columns:
                col_lower = str(col).lower()
                col_str = str(col)
                if "필드" in col_str or "field" in col_lower or "컬럼" in col_str:
                    field_col = col
                elif col_str == "FK" or col_lower == "fk":
                    fk_col = col
                elif "관계" in col_str or "relation" in col_lower:
                    relation_col = col
            
            if not field_col:
                return fk_list
            
            # FK 정보 추출
            for idx, row in schema_df.iterrows():
                field_name = str(row[field_col]).strip() if field_col in row else ""
                if pd.isna(field_name) or field_name == "":
                    continue
                
                # FK 컬럼에서 Y 값 확인
                if fk_col and fk_col in row:
                    fk_value = row[fk_col]
                    if not pd.isna(fk_value) and str(fk_value).upper() in ['Y', 'YES', 'TRUE', '1', '예', 'O']:
                        # 관계 컬럼에서 FK 관계 정보 추출
                        if relation_col and relation_col in row:
                            relation = str(row[relation_col]) if not pd.isna(row[relation_col]) else ""
                            if relation and relation.strip():
                                # 지원 형식:
                                # 1. "전장축선:축선ID" (실제 사용 형식, 콜론 구분)
                                # 2. "전장축선.축선ID" (점 구분)
                                # 3. "FK→전장축선.축선ID" (FK→ 접두사 포함, 점 구분)
                                # 예: 전장축선:축선ID, 지형셀:지형셀ID
                                
                                # FK→ 접두사 제거 (있으면)
                                relation_clean = re.sub(r'^FK\s*→\s*', '', relation, flags=re.IGNORECASE)
                                relation_clean = relation_clean.strip()
                                
                                # 테이블명과 컬럼명 추출 (콜론 또는 점으로 구분)
                                # 정규식: ([^:.,]+) - 테이블명 (콜론/점/쉼표 제외), [:.,] - 구분자, ([^\s,]+) - 컬럼명
                                fk_match = re.search(r'([^:.,]+)[:.,]\s*([^\s,]+)', relation_clean)
                                if fk_match:
                                    target_table = fk_match.group(1).strip()
                                    target_column = fk_match.group(2).strip()
                                    fk_list.append({
                                        "column": field_name,
                                        "target_table": target_table,
                                        "target_column": target_column
                                    })
                                else:
                                    # 파싱 실패 시 경고 (디버깅용)
                                    safe_print(f"[WARN] FK 관계 파싱 실패: {table_name}.{field_name} = '{relation}'")
        
        except Exception as e:
            safe_print(f"[WARN] 테이블정의서 FK 추출 실패 ({table_name}): {e}")
        
        return fk_list

    def _load_coa_library_data(self) -> Optional[pd.DataFrame]:
        """COA 라이브러리 데이터 로드 (파일 직접 읽기)"""
        try:
            # 설정된 데이터 경로 또는 기본 경로 사용
            data_lake_path = self.config.get("data_lake_path", "./data_lake")
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / data_lake_path / "COA_Library.xlsx"
            
            if file_path.exists():
                return pd.read_excel(file_path)
            else:
                safe_print(f"[WARN] COA Library 파일이 존재하지 않습니다: {file_path}")
                return None
        except Exception as e:
            safe_print(f"[ERROR] COA Library 로드 실패: {e}")
            return None

    def _add_coa_library_to_graph(self):
        """COA Library 데이터를 온톨로지 그래프 인스턴스로 변환 (Phase 1)"""
        if self.graph is None:
            return

        df = self._load_coa_library_data()
        if df is None or df.empty:
            return

        safe_print(f"[INFO] COA Library 데이터를 온톨로지로 변환 시작 ({len(df)}개 방책)")
        
        # 네임스페이스 단축어
        NS = self.ns
        
        # Property 정의 (없으면 생성)
        properties = {
            "countersThreat": "countersThreat",
            "requiresResource": "requiresResource",
            "hasConstraint": "hasConstraint",
            "hasSuccessRate": "hasSuccessRate",
            "compatibleWith": "compatibleWith",  # 🔥 NEW: 환경 호환성
            "incompatibleWith": "incompatibleWith"  # 🔥 NEW: 환경 비호환성
        }
        
        for p_name, p_uri_suffix in properties.items():
            p_uri = URIRef(NS[p_uri_suffix])
            if (p_uri, RDF.type, OWL.ObjectProperty) not in self.graph:
                self.graph.add((p_uri, RDF.type, OWL.ObjectProperty))
        
        # 데이터형 속성 (DatatypeProperty) 정의
        success_rate_prop = URIRef(NS["hasSuccessRateValue"])
        self.graph.add((success_rate_prop, RDF.type, OWL.DatatypeProperty))
        
        # 🔥 NEW: 환경 호환성 점수 속성
        compatibility_score_prop = URIRef(NS["compatibilityScore"])
        if (compatibility_score_prop, RDF.type, OWL.DatatypeProperty) not in self.graph:
            self.graph.add((compatibility_score_prop, RDF.type, OWL.DatatypeProperty))

        # 🔥 NEW: 시각화 속성 추가 (Visualization Properties)
        vis_props = {
            "hasPhaseInfo": "hasPhaseInfo",       # 단계 정보 (Phase 1, 2...)
            "isMainEffort": "isMainEffort",       # 주노력 여부 (Y/N)
            "hasVisualStyle": "hasVisualStyle"    # 시각화 스타일 (Solid, Dashed...)
        }
        for prop_name, prop_uri_suffix in vis_props.items():
            p_uri = URIRef(NS[prop_uri_suffix])
            if (p_uri, RDF.type, OWL.DatatypeProperty) not in self.graph:
                 self.graph.add((p_uri, RDF.type, OWL.DatatypeProperty))
        
        count = 0
        for _, row in df.iterrows():
            try:
                # 1. COA 인스턴스 생성
                # 컬럼명 유연성 확보: 'ID', 'COA_ID', '방책ID', '식별자' 등 확인
                raw_id = row.get('COA_ID') or row.get('ID') or row.get('방책ID') or row.get('식별자')
                coa_id = str(raw_id) if pd.notna(raw_id) else f'COA_{count}'
                coa_name = str(row.get('명칭', 'Unknown Strategy'))
                desc = str(row.get('설명', ''))
                
                coa_uri = URIRef(NS[self._make_uri_safe(coa_id)])
                
                if count == 0:
                     safe_print(f"[DEBUG] First COA ID processing: '{coa_id}'")
                
                # 타입 정의 (def:COA)
                self.graph.add((coa_uri, RDF.type, URIRef(NS["COA"])))
                self.graph.add((coa_uri, RDFS.label, Literal(coa_name)))
                self.graph.add((coa_uri, RDFS.comment, Literal(desc)))
                
                # 🔥 세부 타입 추론 (ID 기반)
                # COA_DEF -> DefenseCOA
                # COA_OFF -> OffensiveCOA
                # COA_CAT -> CounterAttackCOA
                # COA_PRE -> PreemptiveCOA
                # COA_DET -> DeterrenceCOA
                # COA_MAN -> ManeuverCOA
                # COA_INF -> InformationOpsCOA
                
                specific_type = None
                if "COA_DEF" in coa_id:
                    specific_type = "DefenseCOA"
                elif "COA_OFF" in coa_id:
                    specific_type = "OffensiveCOA"
                elif "COA_CAT" in coa_id:
                    specific_type = "CounterAttackCOA"
                elif "COA_PRE" in coa_id:
                    specific_type = "PreemptiveCOA"
                elif "COA_DET" in coa_id:
                    specific_type = "DeterrenceCOA"
                elif "COA_MAN" in coa_id:
                    specific_type = "ManeuverCOA"
                elif "COA_INF" in coa_id:
                    specific_type = "InformationOpsCOA"
                
                if specific_type:
                    self.graph.add((coa_uri, RDF.type, URIRef(NS[specific_type])))
                    safe_print(f"[DEBUG] COA 타입 상세화: {coa_id} -> {specific_type}")
                
                # 2. 위협 대응 관계 (countersThreat)
                threat_type = row.get('키워드') or row.get('Keywords')
                if pd.notna(threat_type):
                    for threat in str(threat_type).split(','):
                        t_safe = self._make_uri_safe(threat.strip())
                        if t_safe:
                            # 위협 노드가 없으면 생성 (개념적 노드)
                            threat_uri = URIRef(NS[t_safe])
                            self.graph.add((threat_uri, RDF.type, URIRef(NS["Threat"])))
                            self.graph.add((coa_uri, URIRef(NS["countersThreat"]), threat_uri))

                # 3. 필요 자원 관계 (requiresResource)
                resources = row.get('필요자원') or row.get('Required_Resources')
                if pd.notna(resources):
                    for res in str(resources).split(','):
                        r_safe = self._make_uri_safe(res.strip())
                        if r_safe:
                            res_uri = URIRef(NS[r_safe])
                            self.graph.add((res_uri, RDF.type, URIRef(NS["Resource"])))
                            self.graph.add((coa_uri, URIRef(NS["requiresResource"]), res_uri))
                
                # 4. 제약 조건 (hasConstraint)
                constraints = row.get('전장환경_제약') or row.get('Environmental_Constraints')
                if pd.notna(constraints):
                    for con in str(constraints).split(','):
                        c_safe = self._make_uri_safe(con.strip())
                        if c_safe:
                            con_uri = URIRef(NS[c_safe])
                            self.graph.add((con_uri, RDF.type, URIRef(NS["Constraint"])))
                            self.graph.add((coa_uri, URIRef(NS["hasConstraint"]), con_uri))

                # 5. 성공률 (hasSuccessRate) - Literal로 추가
                success_rate = row.get('워게임_모의_분석_승률') or row.get('예상성공률') or row.get('Estimated_Success_Rate')
                if pd.notna(success_rate):
                    try:
                        rate_val = float(success_rate)
                        self.graph.add((coa_uri, success_rate_prop, Literal(rate_val, datatype=XSD.float)))
                    except:
                        pass
                
                # 🔥 NEW: 시각화 속성 매핑
                # 단계 정보
                phase_info = row.get('단계정보') or row.get('Phase_Info')
                if pd.notna(phase_info):
                    self.graph.add((coa_uri, URIRef(NS["hasPhaseInfo"]), Literal(str(phase_info))))
                
                # 주노력 여부
                main_effort = row.get('주노력여부') or row.get('Main_Effort')
                if pd.notna(main_effort):
                    self.graph.add((coa_uri, URIRef(NS["isMainEffort"]), Literal(str(main_effort))))

                # 시각화 스타일
                vis_style = row.get('시각화스타일') or row.get('Visual_Style')
                if pd.notna(vis_style):
                    self.graph.add((coa_uri, URIRef(NS["hasVisualStyle"]), Literal(str(vis_style))))
                
                count += 1
            except Exception as e:
                safe_print(f"[WARN] COA 변환 중 오류 ({coa_id}): {e}")
        
        safe_print(f"[INFO] COA Library 온톨로지 변환 완료: {count}개 인스턴스 생성")
    
    def generate_owl_ontology(self, data: Dict[str, pd.DataFrame], 
                             meta_t: Optional[pd.DataFrame] = None,
                             meta_c: Optional[pd.DataFrame] = None) -> Optional[Graph]:
        """
        OWL 온톨로지 생성 (현재 시스템의 generate_ontology.py 로직)
        
        Args:
            data: {테이블명: DataFrame} 딕셔너리
            meta_t: 테이블 메타데이터 (없으면 자동 생성)
            meta_c: 컬럼 메타데이터 (없으면 자동 생성)
        
        Returns:
            RDF Graph 객체
        """
        if not RDFLIB_AVAILABLE:
            return None
        
        # 그래프 초기화 (매번 새로 생성하여 관계 변경 사항 반영)
        # 기존 그래프를 유지하면 이전 관계가 남아있을 수 있으므로 매번 초기화
        self.graph = Graph()
        safe_print("[DEBUG] generate_owl_ontology: 그래프 초기화 완료 (기존 그래프 제거)")
        
        # 네임스페이스 바인딩
        self.graph.bind("ns", self.ns)  # 통일된 네임스페이스 사용
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("rdf", RDF)
        
        # 메타데이터 자동 생성 (없는 경우)
        if meta_t is None or meta_c is None:
            meta_t, meta_c = self._generate_metadata(data)
        
        # 관계 매핑 로드 (강제 재로드하여 최신 상태 보장)
        relation_mappings = self.load_relation_mappings(force_reload=True)
        # 🔥 로그 최적화: 불필요한 DEBUG 로그 제거
        # safe_print(f"[DEBUG] 로드된 관계 매핑 수: {len(relation_mappings)}개")
        # for i, rel_map in enumerate(relation_mappings[:5]):  # 처음 5개만 출력
        #     safe_print(f"[DEBUG] 관계 {i+1}: {rel_map.get('src_table')}.{rel_map.get('src_col')} -> {rel_map.get('tgt_table')} (소스: {rel_map.get('source', 'unknown')})")
        
        # 클래스 계층 구조 로드
        class_hierarchy = self._load_class_hierarchy()
        
        # 클래스 정의 (OWL Class)
        for _, t in meta_t.iterrows():
            table_name = t['table_name']
            class_uri = URIRef(self.ns[self._make_uri_safe(table_name)])
            
            # owl:Class로 정의
            self.graph.add((class_uri, RDF.type, OWL.Class))
            
            # 상위 클래스가 있으면 추가
            if table_name in class_hierarchy:
                super_uri = URIRef(self.ns[class_hierarchy[table_name]])
                self.graph.add((class_uri, RDFS.subClassOf, super_uri))
        
        safe_print(f"클래스 정의 완료: {len(meta_t)}개")
        
        # ✨ COA 타입별 클래스 및 속성 추가 (Week 1 개선)
        self._add_coa_type_classes()
        
        # 메타데이터에 정의된 테이블명 집합 (빠른 조회를 위해)
        defined_tables = set(meta_t['table_name'].tolist()) if not meta_t.empty else set()
        
        # ObjectProperty 정의 (테이블 간 관계)
        # 실제 데이터 파일이 있는 테이블 간의 관계만 Property로 생성
        property_count = 0
        skipped_count = 0
        dynamic_relations = {}  # 동적 FK 관계 추적 (같은 관계명, 다른 타겟 테이블)
        
        for rel_map in relation_mappings:
            rel_name = rel_map.get('relation', '')
            if not rel_name:
                continue
            
            src_table = rel_map.get('src_table', '')
            tgt_table = rel_map.get('tgt_table', '')
            is_dynamic = rel_map.get('dynamic', False)
            type_mapping = rel_map.get('type_mapping', {})
            
            # 소스 테이블 확인
            if src_table not in defined_tables:
                # 가상 타겟(Ontology.로 시작)이 아닌 경우에만 경고 출력
                if not src_table.startswith("Ontology."):
                    safe_print(f"[WARN] relation_mappings에서 참조된 소스 테이블 '{src_table}'에 대한 데이터 파일이 없어 Property 생성을 건너뜁니다.")
                skipped_count += 1
                continue
            
            # 동적 FK 관계 처리: 각 타겟 테이블에 대해 별도 Property 생성
            if is_dynamic and type_mapping:
                for target_type, actual_tgt_table in type_mapping.items():
                    if actual_tgt_table not in defined_tables:
                        continue
                    
                    # 동적 관계는 타겟 테이블별로 Property 생성
                    prop_uri = URIRef(self.ns[rel_name])
                    self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
                    
                    domain_uri = URIRef(self.ns[src_table])
                    range_uri = URIRef(self.ns[actual_tgt_table])
                    
                    self.graph.add((prop_uri, RDFS.domain, domain_uri))
                    self.graph.add((prop_uri, RDFS.range, range_uri))
                    
                    property_count += 1
                    safe_print(f"[DEBUG] Property 생성 (동적 FK): {rel_name} (domain: {src_table}, range: {actual_tgt_table})")
            # 일반 FK 관계 처리
            elif tgt_table in defined_tables:
                prop_uri = URIRef(self.ns[rel_name])
                self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
                
                domain_uri = URIRef(self.ns[src_table])
                range_uri = URIRef(self.ns[tgt_table])
                
                self.graph.add((prop_uri, RDFS.domain, domain_uri))
                self.graph.add((prop_uri, RDFS.range, range_uri))
                
                property_count += 1
                safe_print(f"[DEBUG] Property 생성: {rel_name} (domain: {src_table}, range: {tgt_table}, 소스: {rel_map.get('source', 'unknown')})")
            else:
                # 가상 타겟(Ontology.로 시작)이 아닌 경우에만 경고 출력
                if not tgt_table.startswith("Ontology."):
                    safe_print(f"[WARN] relation_mappings에서 참조된 타겟 테이블 '{tgt_table}'에 대한 데이터 파일이 없어 Property 생성을 건너뜁니다.")
                skipped_count += 1
        
        safe_print(f"ObjectProperty 정의 완료: {property_count}개 (건너뜀: {skipped_count}개)")
        if property_count == 0 and len(relation_mappings) > 0:
            safe_print(f"[WARN] 관계 매핑은 {len(relation_mappings)}개 있지만 Property가 생성되지 않았습니다. 테이블명이 일치하는지 확인하세요.")
            safe_print(f"[DEBUG] 정의된 테이블 목록: {sorted(defined_tables)}")
            relation_tables = sorted(set([r.get('src_table') for r in relation_mappings] + [r.get('tgt_table') for r in relation_mappings]))
            safe_print(f"[DEBUG] 관계 매핑의 테이블 목록: {relation_tables}")
        
        # COA 라이브러리 데이터는 generate_instances()에서 일반 테이블로 처리됩니다.
        # 중복 생성을 방지하기 위해 _add_coa_library_to_graph() 호출을 제거했습니다.
        
        # [MOD] 중복 저장 방지: save_graph()에서 통합 처리하므로 여기서는 저장하지 않음
        # output_file = os.path.join(self.output_path, "k_c4i_ontology_owl.ttl")
        # os.makedirs(self.output_path, exist_ok=True)
        # self.graph.serialize(destination=output_file, format="turtle")
        # safe_print(f"OWL 온톨로지 저장 완료: {output_file}")
        
        # 그래프 상태 확인
        triples_count = len(list(self.graph.triples((None, None, None))))
        safe_print(f"[INFO] generate_owl_ontology: 그래프 생성 완료 - {triples_count} triples")
        
        return self.graph
    
    def _generate_metadata(self, data: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        메타데이터 자동 생성 (엑셀의 "테이블정의서" 시트 우선 사용)
        
        엑셀 파일의 "테이블정의서" 시트에서 스키마 정보를 읽고,
        없으면 DataFrame에서 자동 추론합니다.
        """
        meta_t_rows = []
        meta_c_rows = []
        
        # DataManager를 통해 로더 사용 시도
        data_manager = getattr(self, 'data_manager', None)
        if data_manager is None:
            # config에서 data_paths 가져오기
            data_paths = self.config.get("data_paths", {})
        
        for table_name, df in data.items():
            # 테이블 메타데이터
            meta_t_rows.append({
                'table_name': table_name,
                'row_count': len(df)
            })
            
            # 엑셀의 "테이블정의서" 시트에서 스키마 정보 읽기 시도
            schema_info = None
            if data_manager:
                try:
                    loader = data_manager.get_loader(table_name)
                    if loader:
                        schema_info = loader.load_schema()
                except Exception as e:
                    safe_print(f"[WARN] Failed to load schema for {table_name}: {e}")
            
            # 스키마 정보가 있으면 사용, 없으면 DataFrame에서 추론
            if schema_info and schema_info.get('fields'):
                # 테이블정의서에서 필드 정보 사용
                for field_info in schema_info['fields']:
                    field_name = field_info.get('name', '')
                    field_type = field_info.get('type', 'string')
                    
                    meta_c_rows.append({
                        'table_name': table_name,
                        'column_name': field_name,
                        'data_type': field_type
                    })
            # Schema Registry 확인
            elif table_name in self.schema_registry:
                table_info = self.schema_registry[table_name]
                for col_name, col_info in table_info.get('columns', {}).items():
                    meta_c_rows.append({
                        'table_name': table_name,
                        'column_name': col_name,
                        'data_type': col_info.get('type', 'string')
                    })
            else:
                # DataFrame에서 자동 추론 (하위 호환성)
                for col in df.columns:
                    meta_c_rows.append({
                        'table_name': table_name,
                        'column_name': col,
                        'data_type': str(df[col].dtype)
                    })
        
        meta_t = pd.DataFrame(meta_t_rows)
        meta_c = pd.DataFrame(meta_c_rows)
        
        return meta_t, meta_c
    
    def _load_class_hierarchy(self) -> Dict[str, str]:
        """클래스 계층 구조 로드"""
        onto_config_path = os.path.join(self.metadata_path, "ontology_config.xlsx")
        if not os.path.exists(onto_config_path):
            return {}
        
        try:
            onto_config = pd.read_excel(onto_config_path, sheet_name=None)
            if 'ClassHierarchy' not in onto_config:
                return {}
            
            class_hierarchy = {}
            class_df = onto_config['ClassHierarchy']
            for _, row in class_df.iterrows():
                table_name = row.get('table_name', '')
                super_class = row.get('super_class', '')
                if table_name and super_class:
                    class_hierarchy[table_name] = super_class
            
            return class_hierarchy
        except Exception as e:
            safe_print(f"클래스 계층 구조 로드 오류: {e}")
            return {}
    
    def _add_coa_type_classes(self):
        """
        COA 타입별 클래스 및 속성 정의 추가 (Week 1 개선)
        
        7가지 COA 타입에 대한 OWL 클래스를 정의하고,
        각 타입별로 필요한 속성(DataProperty)을 추가합니다.
        """
        # COA 타입별 클래스 정의
        coa_types = {
            "방어방책": "DefenseCOA",
            "공격방책": "OffensiveCOA",
            "반격방책": "CounterAttackCOA",
            "선제방책": "PreemptiveCOA",
            "억제방책": "DeterrenceCOA",
            "기동방책": "ManeuverCOA",
            "정보방책": "InformationOpsCOA"
        }
        
        # 1. 상위 방책 클래스 정의 (COA)
        coa_class_uri = URIRef(self.ns["COA"])
        self.graph.add((coa_class_uri, RDF.type, OWL.Class))
        self.graph.add((coa_class_uri, RDFS.label, Literal("방책", lang="ko")))
        self.graph.add((coa_class_uri, RDFS.label, Literal("Course of Action", lang="en")))
        
        # 2. 각 타입별 클래스 생성
        for korean_name, english_name in coa_types.items():
            class_uri = URIRef(self.ns[english_name])
            
            # OWL Class로 정의
            self.graph.add((class_uri, RDF.type, OWL.Class))
            
            # COA의 하위 클래스로 설정
            self.graph.add((class_uri, RDFS.subClassOf, coa_class_uri))
            
            # 한글/영문 라벨 추가
            self.graph.add((class_uri, RDFS.label, Literal(korean_name, lang="ko")))
            self.graph.add((class_uri, RDFS.label, Literal(english_name, lang="en")))
            
            safe_print(f"[DEBUG] COA 타입 클래스 생성: {korean_name} ({english_name})")
        
        # 3. 방어 방책 전용 속성
        defense_strength = URIRef(self.ns["defenseStrength"])
        self.graph.add((defense_strength, RDF.type, OWL.DatatypeProperty))
        self.graph.add((defense_strength, RDFS.domain, URIRef(self.ns["DefenseCOA"])))
        self.graph.add((defense_strength, RDFS.range, XSD.float))
        self.graph.add((defense_strength, RDFS.label, Literal("방어강도", lang="ko")))
        
        defense_coverage = URIRef(self.ns["defenseCoverage"])
        self.graph.add((defense_coverage, RDF.type, OWL.DatatypeProperty))
        self.graph.add((defense_coverage, RDFS.domain, URIRef(self.ns["DefenseCOA"])))
        self.graph.add((defense_coverage, RDFS.range, XSD.string))
        self.graph.add((defense_coverage, RDFS.label, Literal("방어범위", lang="ko")))
        
        # 4. 공격 방책 전용 속성
        attack_power = URIRef(self.ns["attackPower"])
        self.graph.add((attack_power, RDF.type, OWL.DatatypeProperty))
        self.graph.add((attack_power, RDFS.domain, URIRef(self.ns["OffensiveCOA"])))
        self.graph.add((attack_power, RDFS.range, XSD.float))
        self.graph.add((attack_power, RDFS.label, Literal("공격력", lang="ko")))
        
        breakthrough_capability = URIRef(self.ns["breakthroughCapability"])
        self.graph.add((breakthrough_capability, RDF.type, OWL.DatatypeProperty))
        self.graph.add((breakthrough_capability, RDFS.domain, URIRef(self.ns["OffensiveCOA"])))
        self.graph.add((breakthrough_capability, RDFS.range, XSD.float))
        self.graph.add((breakthrough_capability, RDFS.label, Literal("돌파능력", lang="ko")))
        
        # 5. 공통 속성 (모든 COA 타입)
        effectiveness = URIRef(self.ns["effectiveness"])
        self.graph.add((effectiveness, RDF.type, OWL.DatatypeProperty))
        self.graph.add((effectiveness, RDFS.domain, coa_class_uri))
        self.graph.add((effectiveness, RDFS.range, XSD.float))
        self.graph.add((effectiveness, RDFS.label, Literal("효과성", lang="ko")))
        
        resource_requirement = URIRef(self.ns["resourceRequirement"])
        self.graph.add((resource_requirement, RDF.type, OWL.DatatypeProperty))
        self.graph.add((resource_requirement, RDFS.domain, coa_class_uri))
        self.graph.add((resource_requirement, RDFS.range, XSD.string))
        self.graph.add((resource_requirement, RDFS.label, Literal("자원요구", lang="ko")))
        
        safe_print(f"[INFO] COA 타입별 클래스 7개 및 속성 추가 완료")
    
    def generate_instances(self, data: Dict[str, pd.DataFrame], 
                          enable_virtual_entities: bool = True) -> Optional[Graph]:
        """
        인스턴스 생성 (현재 시스템의 generate_instances.py 로직)
        
        Args:
            data: {테이블명: DataFrame} 딕셔너리
            enable_virtual_entities: 가상 엔티티 생성 활성화
        
        Returns:
            RDF Graph 객체
        """
        if not RDFLIB_AVAILABLE:
            return None
        
        # 기존 그래프가 없으면 새로 생성
        if self.graph is None:
            self.graph = Graph()
            safe_print("[DEBUG] generate_instances: 그래프 초기화 완료")
        
        # 온톨로지 스키마 확인 및 로드 (기존 그래프에 추가)
        self.virtual_entities_count = 0  # 카운터 초기화
        # [MOD] 3단계 구조(schema.ttl) 우선 순위 적용
        schema_file = Path(self.ontology_path) / "schema.ttl"
        legacy_ontology_file = Path(self.output_path) / "k_c4i_ontology_owl.ttl"
        
        # 이미 그래프가 채워져 있으면(예: generate_owl_ontology에서) 추가 로드 건너뜀
        schema_triples = len(list(self.graph.triples((None, RDFS.subClassOf, None))))
        if schema_triples > 0:
            # safe_print(f"[DEBUG] generate_instances: 이미 {schema_triples}개의 스키마 정보가 메모리에 있음. 로딩 건너뜀.")
            is_owl = True
        elif schema_file.exists():
            self.graph.parse(str(schema_file), format="turtle")
            # safe_print(f"[INFO] 스키마 로드 완료 (3단계 표준): {schema_file}")
            is_owl = True
        elif legacy_ontology_file.exists():
            self.graph.parse(str(legacy_ontology_file), format="turtle")
            # safe_print(f"[INFO] 레거시 온톨로지 로드 완료: {legacy_ontology_file}")
            is_owl = True
        else:
            # safe_print("[WARN] 온톨로지 스키마를 찾을 수 없습니다 (schema.ttl 또는 legacy). 인스턴스만 생성합니다.")
            is_owl = False
        
        # 관계 매핑 로드
        relation_mappings = self.load_relation_mappings()
        
        # [MOD] 테이블 처리 순서 최적화 (마스터 데이터 우선 처리)
        # 위협유형_마스터 등 기준 정보를 먼저 처리해야 COA_Library 등에서 시맨틱 링크를 걸 수 있음
        prioritized_tables = ["위협유형_마스터", "임무정보", "부대공통속성", "지형유형_마스터"]
        sorted_tables = [t for t in prioritized_tables if t in data] + \
                        [t for t in data.keys() if t not in prioritized_tables]
        
        for table_name in sorted_tables:
            df = data[table_name]
            if df.empty:
                continue
            
            # ID 컬럼 자동 감지 (Schema Registry 활용)
            id_col = self.get_id_column(table_name, list(df.columns))
            label_col = self.get_label_column(table_name, list(df.columns))
            
            for idx, row in df.iterrows():
                # 인스턴스 URI 생성
                # ID 컬럼 값 가져오기 (비어있거나 NaN인 경우 처리)
                row_id = None
                if id_col and id_col in row:
                    id_value = row[id_col]
                    # NaN, None, 빈 문자열 체크
                    if pd.notna(id_value) and str(id_value).strip() and str(id_value).lower() != 'nan':
                        row_id = str(id_value).strip()
                
                # ID 값이 없으면 인덱스 사용 (경고 로그 출력)
                if not row_id:
                    row_id = f"{table_name}_{idx}"
                    safe_print(f"[WARN] {table_name} 테이블의 {idx}번째 행에 ID 컬럼('{id_col}') 값이 없어 인덱스 기반 ID 사용: {row_id}")
                
                instance_id_safe = self._make_uri_safe(f"{table_name}_{row_id}")
                instance_uri = URIRef(self.ns[instance_id_safe])
                
                # 클래스 타입 추가
                class_uri = URIRef(self.ns[self._make_uri_safe(table_name)])
                self.graph.add((instance_uri, RDF.type, class_uri))
                
                # 라벨 추가
                if label_col and label_col in row:
                    label_val = str(row[label_col])
                    self.graph.add((instance_uri, RDFS.label, Literal(label_val)))
                
                # Literal 속성 추가
                for col in df.columns:
                    if col == id_col or col == label_col:
                        continue
                    
                    val = row[col]
                    if pd.notna(val) and val != "":
                        # FK 컬럼인지 확인
                        is_fk = self._is_foreign_key(table_name, col, relation_mappings)
                        
                        if not is_fk:
                            # Literal 속성으로 추가
                            prop_uri = URIRef(self.ns[col])

                            # [NEW] 부대/자산 상세 속성 매핑 (표준화된 프로퍼티 사용)
                            if col == "SIDC":
                                prop_uri = URIRef(self.ns["hasSIDC"])
                                self.graph.add((instance_uri, prop_uri, Literal(str(val))))
                                continue # 아래의 기본 추가 로직 건너뜀
                            
                            elif col == "전투력지수" or col == "Combat_Power":
                                try:
                                    prop_uri = URIRef(self.ns["hasCombatPower"])
                                    self.graph.add((instance_uri, prop_uri, Literal(float(val), datatype=XSD.float)))
                                except:
                                    pass
                                continue

                            elif col == "이동속도_kmh" or col == "Max_Speed":
                                try:
                                    prop_uri = URIRef(self.ns["hasMaxSpeed"])
                                    self.graph.add((instance_uri, prop_uri, Literal(float(val), datatype=XSD.float)))
                                except:
                                    pass
                                continue

                            elif col == "감지범위_km" or col == "Detection_Range":
                                try:
                                    prop_uri = URIRef(self.ns["hasDetectionRange"])
                                    self.graph.add((instance_uri, prop_uri, Literal(float(val), datatype=XSD.float)))
                                except:
                                    pass
                                continue
                            
                            # 적용조건 필드 특수 처리: expression → 키워드 리스트
                            if col == "적용조건" or col == "Apply_Condition":
                                # expression 형식 (예: "threat_level > 0.8")을 키워드로 추출
                                # 간단한 키워드 추출 로직: 변수명과 연산자 기반
                                keywords = self._extract_keywords_from_condition(str(val))
                                for keyword in keywords:
                                    if keyword:
                                        self.graph.add((instance_uri, prop_uri, Literal(keyword)))
                                continue
                            
                            # 기본 매핑 (위에서 처리되지 않은 경우)
                            self.graph.add((instance_uri, prop_uri, Literal(str(val))))

                            # [NEW] 좌표 정보 특수 처리 (모든 테이블 적용)
                            # 지형셀, 위협상황, 아군부대현황 등 어떤 테이블이든 "좌표정보" 컬럼이 있으면 처리
                            if col == "좌표정보" or col == "coordinates":
                                try:
                                    # "경도, 위도" 형식 파싱 (예: "127.5, 36.5")
                                    coords = str(val).split(',')
                                    if len(coords) >= 2:
                                        # GeoJSON 순서 (x, y) = (경도, 위도) 준수
                                        lon = float(coords[0].strip())
                                        lat = float(coords[1].strip())
                                        
                                        self.graph.add((instance_uri, URIRef(self.ns["hasLongitude"]), Literal(lon, datatype=XSD.float)))
                                        self.graph.add((instance_uri, URIRef(self.ns["hasLatitude"]), Literal(lat, datatype=XSD.float)))
                                        # safe_print(f"[DEBUG] 좌표 등록 ({table_name}): {row_id} ({lon}, {lat})")
                                except Exception as e:
                                    safe_print(f"[WARN] 좌표 파싱 실패 ({table_name} - {row_id}): {val} - {e}")
                
                # COA_Library 테이블 특수 처리: 키워드, 필요자원, 전장환경_제약을 관계로 변환
                if table_name == "COA_Library":
                    self._process_coa_library_relations(instance_uri, row, enable_virtual_entities)
                
                # 위협상황 테이블 특수 처리: 위협유형을 관계로 변환 (전략체인 연결용)
                if table_name == "위협상황":
                    self._process_threat_situation_relations(instance_uri, row, data)
                
                # FK 관계 생성
                self._create_fk_relationships(
                    instance_uri, table_name, row, df.columns, 
                    relation_mappings, data, enable_virtual_entities
                )
        
        # [MOD] 중복 저장 방지: save_graph()에서 통합 처리하므로 여기서는 저장하지 않음
        # output_file = os.path.join(self.output_path, "k_c4i_instances_owl.ttl")
        # self.graph.serialize(destination=output_file, format="turtle")
        # safe_print(f"인스턴스 TTL 파일 저장 완료: {output_file}")
        
        # 그래프 상태 확인
        triples_count = len(list(self.graph.triples((None, None, None))))
        schema_subclass = len(list(self.graph.triples((None, RDFS.subClassOf, None))))
        schema_domain = len(list(self.graph.triples((None, RDFS.domain, None))))
        schema_range = len(list(self.graph.triples((None, RDFS.range, None))))
        safe_print(f"[INFO] generate_instances: 그래프 생성 완료 - {triples_count} triples (가상 엔티티: {self.virtual_entities_count}개)")
        safe_print(f"[DEBUG] generate_instances: 스키마 상태 - subClassOf={schema_subclass}, domain={schema_domain}, range={schema_range}")
        
        return self.graph
    
    def _is_foreign_key(self, table_name: str, col_name: str, 
                       relation_mappings: List[Dict]) -> bool:
        """컬럼이 외래키인지 확인 (relation_mappings + 테이블정의서 기반)"""
        # 1. relation_mappings에서 확인
        for rel_map in relation_mappings:
            if rel_map.get('src_table') == table_name and rel_map.get('src_col') == col_name:
                return True
        
        # 2. 테이블정의서에서 확인 (캐시된 relation_mappings에 이미 포함되어 있음)
        # relation_mappings에 source="table_schema"인 항목이 있으면 이미 처리됨
        
        # 3. 자동 감지: *ID 패턴 (폴백, relation_mappings와 테이블정의서에 없을 때만)
        if col_name.endswith('ID') or col_name.endswith('id') or col_name.endswith('_id'):
            return True
        
        return False
    
    def _create_fk_relationships(self, src_uri: URIRef, table_name: str, row: pd.Series,
                                columns: List[str], relation_mappings: List[Dict],
                                data: Dict[str, pd.DataFrame], 
                                enable_virtual_entities: bool):
        """FK 관계 생성"""
        for rel_map in relation_mappings:
            if rel_map.get('src_table') != table_name:
                continue
            
            # 동적 FK 관계 처리
            if rel_map.get('dynamic', False):
                self._create_dynamic_fk_relationship(
                    src_uri, table_name, row, columns, rel_map, data, enable_virtual_entities
                )
                continue
            
            # 일반 FK 관계 처리
            src_col = rel_map.get('src_col')
            if src_col not in columns:
                continue
            
            fk_val = str(row[src_col]).strip()
            if not fk_val or pd.isna(row[src_col]):
                continue
            
            tgt_table = rel_map.get('tgt_table')
            relation_name = rel_map.get('relation', f"has{tgt_table}")
            is_inferred = rel_map.get('inferred', False)
            
            # 추론 관계인 경우 값 매핑 및 실제 데이터 확인 강화
            if is_inferred:
                tgt_uri = self._find_target_instance_with_mapping(
                    tgt_table, fk_val, data, src_col
                )
            else:
                # 일반 FK 관계: 타겟 테이블에서 인스턴스 찾기
                tgt_uri = self._find_target_instance(tgt_table, fk_val, data)
            
            if tgt_uri:
                # 실제 데이터에서 찾은 경우 관계 생성
                prop_uri = URIRef(self.ns[relation_name])
                self.graph.add((src_uri, prop_uri, tgt_uri))
            elif enable_virtual_entities and is_inferred:
                # 추론 관계이고 실제 데이터에 없을 때만 가상 엔티티 생성
                # 중복 체크 후 생성
                virtual_uri = self._create_virtual_entity_safe(tgt_table, fk_val)
                if virtual_uri:
                    prop_uri = URIRef(self.ns[relation_name])
                    self.graph.add((src_uri, prop_uri, virtual_uri))
                    safe_print(f"[INFO] 추론 관계 가상 노드 생성: {table_name}.{src_col}='{fk_val}' -> {tgt_table}")
            elif enable_virtual_entities:
                # 일반 FK 관계에서도 가상 엔티티 생성 (기존 동작 유지)
                virtual_uri = self._create_virtual_entity_safe(tgt_table, fk_val)
                if virtual_uri:
                    prop_uri = URIRef(self.ns[relation_name])
                    self.graph.add((src_uri, prop_uri, virtual_uri))
    
    def _create_dynamic_fk_relationship(self, src_uri: URIRef, table_name: str, row: pd.Series,
                                        columns: List[str], rel_map: Dict,
                                        data: Dict[str, pd.DataFrame], 
                                        enable_virtual_entities: bool):
        """동적 FK 관계 생성 (제약조건 등)"""
        type_col = rel_map.get('type_column')
        type_mapping = rel_map.get('type_mapping', {})
        src_col = rel_map.get('src_col')
        
        if not type_col or not src_col:
            return
        
        if type_col not in row or src_col not in row:
            return
        
        # 적용대상유형 값 확인
        target_type = str(row[type_col]).strip()
        if not target_type or pd.isna(row[type_col]):
            return
        
        # 타입 매핑에서 타겟 테이블 찾기
        target_table = type_mapping.get(target_type)
        if not target_table:
            safe_print(f"[WARN] 알 수 없는 적용대상유형: {target_type} (테이블: {table_name})")
            return
        
        # FK 값 확인
        fk_val = str(row[src_col]).strip()
        if not fk_val or pd.isna(row[src_col]):
            return
        
        # 관계명 가져오기
        relation_name = rel_map.get('relation', 'appliesTo')
        
        # 타겟 테이블에서 인스턴스 찾기
        tgt_uri = self._find_target_instance(target_table, fk_val, data)
        
        if tgt_uri:
            # 관계 생성
            prop_uri = URIRef(self.ns[relation_name])
            self.graph.add((src_uri, prop_uri, tgt_uri))
            safe_print(f"[INFO] 동적 FK 관계 생성: {table_name} -[{relation_name}]-> {target_table} ({fk_val})")
        elif enable_virtual_entities:
            # 가상 엔티티 생성
            virtual_uri = self._create_virtual_entity(target_table, fk_val)
            if virtual_uri:
                prop_uri = URIRef(self.ns[relation_name])
                self.graph.add((src_uri, prop_uri, virtual_uri))
                safe_print(f"[INFO] 동적 FK 관계 생성 (가상 엔티티): {table_name} -[{relation_name}]-> {target_table} ({fk_val})")
    
    def _find_target_instance(self, tgt_table: str, fk_val: str, 
                             data: Dict[str, pd.DataFrame]) -> Optional[URIRef]:
        """타겟 테이블에서 인스턴스 찾기"""
        if tgt_table not in data:
            return None
        
        df = data[tgt_table]
        if df.empty:
            return None
        
        # ID 컬럼 찾기
        id_col = suggest_id_column(tgt_table, list(df.columns))
        
        # 매칭되는 행 찾기
        matching_rows = df[df[id_col].astype(str).str.strip() == fk_val]
        if matching_rows.empty:
            return None
        
        row_id = str(matching_rows.iloc[0][id_col]).strip()
        safe_instance_id = self._make_uri_safe(f"{tgt_table}_{row_id}")
        return URIRef(self.ns[safe_instance_id])
    
    def _find_target_instance_with_mapping(self, tgt_table: str, fk_val: str,
                                          data: Dict[str, pd.DataFrame],
                                          src_col: str) -> Optional[URIRef]:
        """
        타겟 테이블에서 인스턴스 찾기 (값 매핑 지원)
        
        추론 관계에서 사용: 전략유형 값(offensive/defensive/공격/방어)을
        실제 임무정보 데이터의 임무종류 컬럼과 매칭
        """
        if tgt_table not in data:
            return None
        
        df = data[tgt_table]
        if df.empty:
            return None
        
        # 전략유형 컬럼인 경우 값 매핑 적용
        if src_col == '전략유형' and tgt_table == '임무정보':
            # 임무정보 테이블의 임무종류 컬럼 찾기
            mission_type_col = None
            for col in df.columns:
                if '임무종류' in str(col) or 'mission_type' in str(col).lower():
                    mission_type_col = col
                    break
            
            if mission_type_col:
                # 값 매핑: offensive ↔ 공격, defensive ↔ 방어
                mapped_values = self.STRATEGY_TYPE_MAPPING.get(fk_val.lower(), [fk_val])
                
                # 매핑된 값들로 검색
                for mapped_val in mapped_values:
                    matching_rows = df[df[mission_type_col].astype(str).str.strip().str.lower() == mapped_val.lower()]
                    if not matching_rows.empty:
                        # ID 컬럼 찾기
                        id_col = suggest_id_column(tgt_table, list(df.columns))
                        row_id = str(matching_rows.iloc[0][id_col]).strip()
                        safe_print(f"[INFO] 추론 관계 매칭 성공: '{fk_val}' -> '{mapped_val}' (임무정보_{row_id})")
                        safe_instance_id = self._make_uri_safe(f"{tgt_table}_{row_id}")
                        return URIRef(self.ns[safe_instance_id])
        
        # 일반 FK 관계로 처리 (ID 컬럼 직접 매칭)
        return self._find_target_instance(tgt_table, fk_val, data)
    
    def _process_coa_library_relations(self, coa_uri: URIRef, row: pd.Series, enable_virtual_entities: bool):
        """
        COA_Library 테이블의 특수 관계 처리
        키워드, 필요자원, 전장환경_제약 컬럼을 관계로 변환
        """
        NS = self.ns  # 통일된 네임스페이스 사용
        
        # [DEBUG]
        if "TW01" in str(coa_uri):
             safe_print(f"[DEBUG] Processing TW01. Row keys: {list(row.keys())}")
             safe_print(f"[DEBUG] 적합위협유형 value: {row.get('적합위협유형')}")
        
        # 1. 키워드 -> respondsTo 관계 (표준화)
        keywords = row.get('키워드') or row.get('Keywords')
        if pd.notna(keywords):
            for threat in str(keywords).split(','):
                keyword_clean = threat.strip()
                if keyword_clean:
                    threat_uri = URIRef(NS[self._make_uri_safe(keyword_clean)])
                    # 위협 노드가 없으면 생성 (개념적 노드)
                    if (threat_uri, RDF.type, None) not in self.graph:
                        self.graph.add((threat_uri, RDF.type, URIRef(NS["Threat"])))
                    # [MOD] countersThreat 대신 표준화된 respondsTo 사용
                    self.graph.add((coa_uri, URIRef(NS["respondsTo"]), threat_uri))
        
        # 2. 필요자원 -> requiresResource 관계
        resources = row.get('필요자원') or row.get('Required_Resources')
        if pd.notna(resources):
            for resource in str(resources).split(','):
                resource_clean = resource.strip()
                if resource_clean:
                    res_uri = URIRef(NS[self._make_uri_safe(resource_clean)])
                    # 자원 노드가 없으면 생성
                    if (res_uri, RDF.type, None) not in self.graph:
                        self.graph.add((res_uri, RDF.type, URIRef(NS["Resource"])))
                    self.graph.add((coa_uri, URIRef(NS["requiresResource"]), res_uri))
        
        # 3. 전장환경_제약 -> hasConstraint 관계
        constraints = row.get('전장환경_제약') or row.get('Environmental_Constraints')
        if pd.notna(constraints):
            for constraint in str(constraints).split(','):
                constraint_clean = constraint.strip()
                if constraint_clean:
                    con_uri = URIRef(NS[self._make_uri_safe(constraint_clean)])
                    # 제약 노드가 없으면 생성
                    if (con_uri, RDF.type, None) not in self.graph:
                        self.graph.add((con_uri, RDF.type, URIRef(NS["Constraint"])))
                    self.graph.add((coa_uri, URIRef(NS["hasConstraint"]), con_uri))
        
        # 4. 워게임_모의_분석_승률 -> hasSuccessRateValue (Literal)
        success_rate = row.get('워게임_모의_분석_승률') or row.get('예상성공률') or row.get('Estimated_Success_Rate')
        if pd.notna(success_rate):
            try:
                rate_val = float(success_rate)
                success_rate_prop = URIRef(NS["hasSuccessRateValue"])
                self.graph.add((coa_uri, success_rate_prop, Literal(rate_val, datatype=XSD.float)))
            except:
                pass
        
        # 5. 환경 호환성 -> compatibleWith 관계 (NEW)
        compatible_envs = row.get('환경호환성') or row.get('Environmental_Compatibility')
        if pd.notna(compatible_envs):
            for env in str(compatible_envs).split(','):
                env_clean = env.strip()
                if env_clean:
                    env_uri = URIRef(NS[self._make_uri_safe(env_clean)])
                    # 환경 노드가 없으면 생성
                    if (env_uri, RDF.type, None) not in self.graph:
                        self.graph.add((env_uri, RDF.type, URIRef(NS["Environment"])))
                    self.graph.add((coa_uri, URIRef(NS["compatibleWith"]), env_uri))
                    # 호환성 점수 추가 (호환 환경은 높은 점수)
                    compatibility_score_prop = URIRef(NS["compatibilityScore"])
                    self.graph.add((coa_uri, compatibility_score_prop, Literal(1.0, datatype=XSD.float)))
        
        # 6. 환경 비호환성 -> incompatibleWith 관계 (NEW)
        incompatible_envs = row.get('환경비호환성') or row.get('Environmental_Incompatibility')
        if pd.notna(incompatible_envs):
            for env in str(incompatible_envs).split(','):
                env_clean = env.strip()
                if env_clean:
                    env_uri = URIRef(NS[self._make_uri_safe(env_clean)])
                    # 환경 노드가 없으면 생성
                    if (env_uri, RDF.type, None) not in self.graph:
                        self.graph.add((env_uri, RDF.type, URIRef(NS["Environment"])))
                    self.graph.add((coa_uri, URIRef(NS["incompatibleWith"]), env_uri))
                    # 비호환성 점수 추가 (비호환 환경은 낮은 점수)
                    compatibility_score_prop = URIRef(NS["compatibilityScore"])
                    self.graph.add((coa_uri, compatibility_score_prop, Literal(0.2, datatype=XSD.float)))
        
        # 7. 적합위협유형 -> 적합위협유형 (Literal List) + respondsTo (Semantic Link)
        threat_types = row.get('적합위협유형') or row.get('Suitable_Threat_Types')
        if pd.notna(threat_types):
            prop_uri = URIRef(NS["적합위협유형"])
            responds_to_prop = URIRef(NS["respondsTo"])
            for t_type in str(threat_types).split(','):
                t_clean = t_type.strip()
                if t_clean:
                    # 기존 주석 리터럴 유지
                    self.graph.add((coa_uri, prop_uri, Literal(t_clean)))
                    
                    # [NEW] 라벨 및 키워드 기반 시맨틱 링크(respondsTo) 자동 생성
                    keyword_prop = URIRef(NS["대표키워드"])
                    for threat_master_uri in self.graph.subjects(RDF.type, URIRef(NS["위협유형_마스터"])):
                        found = False
                        # 1. 라벨(명칭/위협유형명) 대조
                        for label in self.graph.objects(threat_master_uri, RDFS.label):
                            if str(label) == t_clean:
                                found = True
                                break
                        
                        # 2. 대표키워드 대조 (쉼표 분리 후 정확히 일치하는지 확인)
                        if not found:
                            for keywords_literal in self.graph.objects(threat_master_uri, keyword_prop):
                                kw_list = [k.strip() for k in str(keywords_literal).split(',')]
                                if t_clean in kw_list:
                                    found = True
                                    break
                        
                        if found:
                            self.graph.add((coa_uri, responds_to_prop, threat_master_uri))
                            # safe_print(f"[DEBUG] Semantic Link: {coa_uri} -[respondsTo]-> {threat_master_uri} (Matched via: {t_clean})")
        
        # [NEW] 7.1 설명(Description) 필드 기반 폴백 매칭
        # 적합위협유형이 비어있거나 부족한 경우 설명을 스캔하여 추가 매핑 시도
        description = row.get('설명') or row.get('Description')
        if pd.notna(description) and str(description).strip():
            desc_text = str(description)
            responds_to_prop = URIRef(NS["respondsTo"])
            keyword_prop = URIRef(NS["대표키워드"])
            
            for threat_master_uri in self.graph.subjects(RDF.type, URIRef(NS["위협유형_마스터"])):
                # 이미 매핑된 경우는 스킵 (선택 사항)
                if (coa_uri, responds_to_prop, threat_master_uri) in self.graph:
                    continue
                    
                found = False
                # 1. 라벨/명칭 포함 여부 확인
                for label in self.graph.objects(threat_master_uri, RDFS.label):
                    if str(label) in desc_text:
                        found = True
                        break
                
                # 2. 대표키워드 포함 여부 확인
                if not found:
                    for keywords_literal in self.graph.objects(threat_master_uri, keyword_prop):
                        kw_list = [k.strip() for k in str(keywords_literal).split(',') if k.strip()]
                        for kw in kw_list:
                            if kw in desc_text:
                                found = True
                                break
                        if found: break
                
                if found:
                    self.graph.add((coa_uri, responds_to_prop, threat_master_uri))
                    # safe_print(f"[DEBUG] Description Fallback Link: {coa_uri} -[respondsTo]-> {threat_master_uri}")

        # 8. 자원우선순위 -> 자원우선순위 (Literal List)
        res_priorities = row.get('자원우선순위') or row.get('Resource_Priorities')
        if pd.notna(res_priorities):
            prop_uri = URIRef(NS["자원우선순위"])
            for res_p in str(res_priorities).split(','):
                p_clean = res_p.strip()
                if p_clean:
                    self.graph.add((coa_uri, prop_uri, Literal(p_clean)))
                    
        # 9. 연계방책 -> hasRelatedCOA (Relation) - 서술형 필드는 제거, 관계만 유지
        # 값 예시: COA_ATK_001(후행)
        # [MOD] 연계방책 서술형 필드는 제거되었으나, Excel 데이터에서 읽어서 관계만 생성
        related_coas = row.get('연계방책') or row.get('Related_COAs')
        if pd.notna(related_coas):
            for r_coa in str(related_coas).split(','):
                r_clean = r_coa.strip()
                if r_clean:
                    # 간단한 파싱: ID만 추출 (괄호 제거)
                    r_id = r_clean.split('(')[0].strip()
                    if r_id:
                        r_uri = URIRef(NS[self._make_uri_safe(r_id)])
                        self.graph.add((coa_uri, URIRef(NS["hasRelatedCOA"]), r_uri))
        
        # 10. 적용부대 -> participating_units (Literal)
        participating_units = row.get('적용부대') or row.get('Participating_Units')
        if pd.notna(participating_units):
            self.graph.add((coa_uri, URIRef(NS["participating_units"]), Literal(str(participating_units))))
            # also as hasMainEffort for backward compatibility
            self.graph.add((coa_uri, URIRef(NS["hasMainEffort"]), Literal(str(participating_units))))

        # 11. 전술그래픽 -> hasTacticalGraphics (Literal)
        tactical_graphics = row.get('전술그래픽') or row.get('Tactical_Graphics')
        if pd.notna(tactical_graphics):
            self.graph.add((coa_uri, URIRef(NS["hasTacticalGraphics"]), Literal(str(tactical_graphics))))

        # 12. 단계정보 -> hasPhasingInfo (Literal)
        phasing_info = row.get('단계정보') or row.get('Phasing_Info')
        if pd.notna(phasing_info):
            self.graph.add((coa_uri, URIRef(NS["hasPhasingInfo"]), Literal(str(phasing_info))))

        # 13. 주노력여부 -> isMainEffort (Literal)
        is_main_effort = row.get('주노력여부') or row.get('Main_Effort')
        if pd.notna(is_main_effort):
            self.graph.add((coa_uri, URIRef(NS["isMainEffort"]), Literal(str(is_main_effort))))

        # 14. 시각화스타일 -> hasVisualStyle (Literal)
        vis_style = row.get('시각화스타일') or row.get('Visual_Style')
        if pd.notna(vis_style):
            self.graph.add((coa_uri, URIRef(NS["hasVisualStyle"]), Literal(str(vis_style))))

        # [REMOVED] 연계방책 서술형 필드는 더 이상 온톨로지에 저장하지 않음 (RAG로 이동)

        # [REMOVED] 적대응전술 필드 제거 - RAG 문서로 이동
        # 적대응전술 설명은 RAG 문서에서 검색하도록 변경
        
        # 7. COA 타입 추론 (ID 기반) - COA_Library_COA_DEF_001 -> DefenseCOA
        coa_id = str(row.get('COA_ID', ''))
        if coa_id:
            specific_type = None
            if "COA_DEF" in coa_id:
                specific_type = "DefenseCOA"
            elif "COA_OFF" in coa_id:
                specific_type = "OffensiveCOA"
            elif "COA_CNT" in coa_id or "COA_CAT" in coa_id:
                specific_type = "CounterAttackCOA"
            elif "COA_PRE" in coa_id:
                specific_type = "PreemptiveCOA"
            elif "COA_DET" in coa_id:
                specific_type = "DeterrenceCOA"
            elif "COA_MAN" in coa_id:
                specific_type = "ManeuverCOA"
            elif "COA_INF" in coa_id:
                specific_type = "InformationOpsCOA"
            
            if specific_type:
                self.graph.add((coa_uri, RDF.type, URIRef(NS[specific_type])))
                # COA 상위 클래스도 추가
                self.graph.add((coa_uri, RDF.type, URIRef(NS["COA"])))
                
                # [NEW] 파일럿 시각화 데이터 주입 (Visualization Pilot Data Injection)
                # 엑셀 데이터가 없는 경우에만 폴백용으로 데이터 주입
                vis_props = {}
                
                # 기존에 등록된 속성 확인용
                has_efforts = (coa_uri, URIRef(NS["hasMainEffort"]), None) in self.graph
                has_graphics = (coa_uri, URIRef(NS["hasTacticalGraphics"]), None) in self.graph
                has_phasing = (coa_uri, URIRef(NS["hasPhasingInfo"]), None) in self.graph

                if not has_efforts or not has_graphics or not has_phasing:
                    if "COA_DEF" in coa_id:
                         vis_props = {
                            "hasMainEffort": "제1기계화보병여단",
                            "hasPhasingInfo": "1단계:지연전,2단계:방어,3단계:편제화력지원",
                            "hasActionType": "Defend",
                            "hasTacticalGraphics": "Block:[(37.8,126.9),(37.9,127.1)]", # 파주 축선 차단
                            "hasExpectedEffect": "적 기계화부대 진출 48시간 지연"
                         }
                    elif "COA_OFF" in coa_id: # Counter Attack 포함
                         vis_props = {
                            "hasMainEffort": "제7기동군단",
                            "hasPhasingInfo": "1단계:접적기동,2단계:돌파,3단계:목표확보",
                            "hasActionType": "Attack",
                            "hasTacticalGraphics": "Axis:[(37.5,127.0),(37.9,126.8),(38.1,126.6)]", # 개성 방향 진격
                            "hasExpectedEffect": "적 지휘소 무력화 및 영토 회복"
                         }
                    elif "COA_PRE" in coa_id or "COA_DET" in coa_id:
                         vis_props = {
                            "hasMainEffort": "전략미사일사령부",
                            "hasPhasingInfo": "1단계:표적식별,2단계:선제타격,3단계:피해평가",
                            "hasActionType": "Strike",
                            "hasTacticalGraphics": "PointTarget:[(39.0,125.7)]", # 평양 인근
                            "hasExpectedEffect": "적 미사일 발사 능력 70% 감소"
                         }
                    
                    for prop, val in vis_props.items():
                        # 해당 속성이 없는 경우에만 추가
                        if (coa_uri, URIRef(NS[prop]), None) not in self.graph:
                            self.graph.add((coa_uri, URIRef(NS[prop]), Literal(val)))

    def _process_threat_situation_relations(self, threat_uri: URIRef, row: pd.Series, data: Dict[str, pd.DataFrame]):
        """
        위협상황 테이블의 특수 관계 처리
        위협유형 컬럼을 URI 기반의 ns:Threat 관계로 변환하여 전략체인 연결성 확보
        [NEW] 위협상황과 현재 가용자원 간의 스냅샷 관계(hasResourceSnapshot) 생성
        """
        NS = self.ns
        
        # 1. 위협유형 -> ns:Threat 관계 (전략체인 탐색용 핵심 연결고리)
        # [FIX] 마스터 데이터 URI 형식에 맞게 생성 (위협유형_마스터_THR_TYPE_xxx)
        threat_type = row.get('위협유형코드') or row.get('위협유형') or row.get('threat_type')
        if pd.notna(threat_type):
            type_clean = str(threat_type).strip()
            if type_clean:
                # 마스터 테이블 ID 패턴인 경우 해당 URI 사용
                if type_clean.startswith("THR_TYPE_"):
                    keyword_uri = URIRef(self.ns[self._make_uri_safe(f"위협유형_마스터_{type_clean}")])
                else:
                    keyword_uri = URIRef(NS[self._make_uri_safe(type_clean)])
                    
                if (keyword_uri, RDF.type, None) not in self.graph:
                    self.graph.add((keyword_uri, RDF.type, URIRef(NS["위협유형_마스터"])))
                self.graph.add((threat_uri, URIRef(NS["has위협유형"]), keyword_uri))
        
        # 2. [NEW]가용자원 스냅샷 연결
        # 위협 상황 발생 시점의 가용 자원들을 연결하여 추론 엔진이 자원 가용성을 파악할 수 있게 함
        if '가용자원' in data:
            resource_df = data['가용자원']
            # ID 컬럼 감지
            res_id_col = self.get_id_column('가용자원', list(resource_df.columns))
            
            for _, res_row in resource_df.iterrows():
                res_id = str(res_row.get(res_id_col)).strip()
                if res_id and res_id.lower() != 'nan':
                    res_instance_id = self._make_uri_safe(f"가용자원_{res_id}")
                    res_uri = URIRef(NS[res_instance_id])
                    
                    # 관계 추가: Threat -> hasResourceSnapshot -> Resource
                    self.graph.add((threat_uri, URIRef(NS["hasResourceSnapshot"]), res_uri))
            
            # safe_print(f"[DEBUG] 위협상황 {threat_uri}에 가용자원 스냅샷 연결 완료")
    
    def _create_virtual_entity(self, entity_type: str, entity_id: str) -> Optional[URIRef]:
        """가상 엔티티 생성 (레거시 호환용)"""
        return self._create_virtual_entity_safe(entity_type, entity_id)
    
    def _create_virtual_entity_safe(self, entity_type: str, entity_id: str) -> Optional[URIRef]:
        """
        가상 엔티티 생성 (중복 체크 및 메타데이터 추가)
        
        Args:
            entity_type: 엔티티 타입 (예: '임무정보')
            entity_id: 엔티티 ID (예: 'offensive')
        
        Returns:
            가상 엔티티 URI 또는 None (이미 존재하는 경우)
        """
        if not entity_type or not entity_id:
            return None
        
        # URI-safe 문자열 생성
        entity_type_clean = self._make_uri_safe(entity_type)
        entity_id_clean = self._make_uri_safe(str(entity_id))
        
        virtual_id = f"{entity_type_clean}_{entity_id_clean}"
        virtual_uri = URIRef(self.virtual_ns[virtual_id]) # Use virtual_ns for virtual entities
        
        # 이미 존재하는지 확인 (중복 생성 방지)
        if (virtual_uri, RDF.type, None) in self.graph:
            # 이미 존재하는 경우 기존 URI 반환
            return virtual_uri
        
        # 가상 엔티티 생성
        class_uri = URIRef(self.ns[entity_type_clean])
        self.graph.add((virtual_uri, RDF.type, class_uri))
        self.graph.add((virtual_uri, RDFS.label, Literal(f"가상_{entity_type_clean}_{entity_id_clean}")))
        
        # 통계 카운트 증가
        self.virtual_entities_count += 1
        
        # [NEW] 가상 엔티티 속성 추가 (원본 메타데이터 보존)
        # (향후 통계에서 실제 데이터와 구분 가능)
        self.graph.add((virtual_uri, URIRef(self.ns["isVirtualEntity"]), Literal(True, datatype=XSD.boolean)))
        self.graph.add((virtual_uri, URIRef(self.ns["virtualEntitySource"]), Literal("inferred_relation")))
        
        return virtual_uri
    
    # ========== OntologyManager 호환 메서드 추가 ==========
    
    def _is_schema_triple(self, s, p, o) -> bool:
        """스키마 정의 트리플인지 확인 (클래스/속성/계층구조 등)"""
        from rdflib import RDF, RDFS, OWL
        # 기술적 속성들
        if p in [RDFS.subClassOf, RDFS.domain, RDFS.range, RDFS.subPropertyOf,
                 OWL.inverseOf, OWL.equivalentClass, OWL.equivalentProperty,
                 OWL.disjointWith, OWL.unionOf, OWL.intersectionOf]:
            return True
        # 클래스/속성 정의 타입
        if p == RDF.type and o in [OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, 
                                 OWL.TransitiveProperty, OWL.SymmetricProperty, 
                                 OWL.FunctionalProperty, OWL.InverseFunctionalProperty,
                                 RDFS.Class, OWL.Ontology, OWL.Restriction, OWL.Axiom]:
            return True
        return False

    def save_graph(self, output_path: Optional[str] = None,
                   save_schema_separately: bool = True,
                   save_instances_separately: bool = True,
                   save_reasoned_separately: bool = False,
                   enable_semantic_inference: bool = True,
                   reasoned_graph: Optional[Graph] = None,
                   cleanup_old_files: bool = True,
                   backup_old_files: bool = True) -> Dict[str, Any]:
        """
        RDF 그래프를 TTL 파일로 저장 (3단계 구조: schema.ttl + instances.ttl + instances_reasoned.ttl)
        
        Args:
            output_path: 출력 경로 (기본값: self.ontology_path)
            save_schema_separately: schema.ttl 저장 여부
            save_instances_separately: instances.ttl 저장 여부
            save_reasoned_separately: instances_reasoned.ttl 저장 여부 (추론 결과 포함)
            enable_semantic_inference: 추론 그래프 생성 시 의미 기반 추론 활성화 여부
            reasoned_graph: [NEW] 이미 계산된 추론 그래프가 있는 경우 전달 (중복 추론 방지)
            cleanup_old_files: 기존 중간 생성물 파일 삭제 여부
            backup_old_files: 기존 파일 백업 여부
        
        Returns:
            Dict: 저장 통계 (success, schema_triples, instances_triples, reasoned_triples 등)
        """
        stats = {
            "success": False,
            "schema_triples": 0,
            "instances_triples": 0,
            "reasoned_triples": 0,
            "message": ""
        }
        
        if not RDFLIB_AVAILABLE or self.graph is None:
            stats["message"] = "RDFLib not available or graph is None"
            safe_print(f"[WARN] {stats['message']}")
            return stats
        
        if output_path is None:
            output_path = self.ontology_path
        
        # output_path가 파일 경로인지 디렉토리 경로인지 확인
        output_path_obj = Path(output_path)
        if output_path_obj.suffix in ['.ttl', '.owl', '.rdf']:
            # 파일 경로로 전달된 경우, 디렉토리 경로로 변환
            ontology_dir = output_path_obj.parent
            safe_print(f"[WARN] output_path가 파일 경로로 전달되었습니다. 디렉토리 경로로 변환: {ontology_dir}")
        else:
            # 디렉토리 경로로 전달된 경우
            ontology_dir = output_path_obj
        
        ontology_dir.mkdir(parents=True, exist_ok=True)
        
        # [NEW] 저장 전 모든 중요 파일 백업 (안정성 강화)
        if backup_old_files:
            for filename in ["schema.ttl", "instances.ttl", "instances_reasoned.ttl"]:
                source_file = ontology_dir / filename
                if source_file.exists():
                    try:
                        backup_dir = ontology_dir / "backup"
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_path = backup_dir / f"{filename}.backup_{timestamp}"
                        shutil.copy2(source_file, backup_path)
                        safe_print(f"[INFO] 사전 백업 완료: {backup_path}")
                    except Exception as backup_e:
                        safe_print(f"[WARN] 사전 백업 실패 ({filename}): {backup_e}")
        
        try:
            # 1. 스키마만 추출하여 저장 (schema.ttl)
            if save_schema_separately:
                schema_graph = Graph()
                # 네임스페이스 바인딩 복사
                for prefix, namespace in self.graph.namespaces():
                    schema_graph.bind(prefix, namespace)
                
                # 스키마 관련 트리플만 추출
                for s, p, o in self.graph:
                    if self._is_schema_triple(s, p, o):
                        schema_graph.add((s, p, o))
                
                schema_path = ontology_dir / "schema.ttl"
                schema_graph.serialize(destination=str(schema_path), format="turtle")
                stats["schema_triples"] = len(list(schema_graph.triples((None, None, None))))
                safe_print(f"[INFO] 스키마 저장 완료: {schema_path} ({stats['schema_triples']} triples)")
            
            # 2. 인스턴스만 추출하여 저장 (instances.ttl)
            if save_instances_separately:
                instances_graph = Graph()
                # 네임스페이스 바인딩 복사
                for prefix, namespace in self.graph.namespaces():
                    instances_graph.bind(prefix, namespace)
                
                # 인스턴스 데이터만 추출 (스키마 제외 및 추론 결과 제외)
                inferred_triples_count = 0
                for s, p, o in self.graph:
                    # [MOD] 스키마 트리플 제외
                    if self._is_schema_triple(s, p, o):
                        continue
                        
                    # [FIX] 추론된 트리플 제외 (원본 순수성 유지)
                    if self._is_inferred_triple(s, p, o):
                        inferred_triples_count += 1
                        continue
                        
                    instances_graph.add((s, p, o))
                
                if inferred_triples_count > 0:
                    safe_print(f"[INFO] {inferred_triples_count}개의 추론된 트리플을 instances.ttl 저장에서 제외했습니다.")
                
                instances_path = ontology_dir / "instances.ttl"
                instances_graph.serialize(destination=str(instances_path), format="turtle")
                stats["instances_triples"] = len(list(instances_graph.triples((None, None, None))))
                safe_print(f"[INFO] 인스턴스 저장 완료: {instances_path} ({stats['instances_triples']} triples)")
            
            # 3. 추론된 그래프 저장 (instances_reasoned.ttl)
            if save_reasoned_separately:
                # [FIX] reasoned_graph가 인자로 전달되었으면 그것을 사용, 없으면 생성
                if reasoned_graph is None:
                    safe_print("[INFO] 저장용 추론 그래프 생성 중...")
                    reasoned_graph = self.generate_reasoned_graph(enable_semantic_inference=enable_semantic_inference)
                else:
                    safe_print("[INFO] 전달받은 추론 그래프를 사용하여 저장합니다. (중복 생성 스킵)")
                
                if reasoned_graph:
                    reasoned_instances_graph = Graph()
                    # 네임스페이스 바인딩 복사
                    for prefix, namespace in reasoned_graph.namespaces():
                        reasoned_instances_graph.bind(prefix, namespace)
                    
                    # 추론된 그래프의 모든 트리플 복사 (스키마 제외)
                    for s, p, o in reasoned_graph:
                        # [MOD] 동일한 방식으로 스키마 제외
                        if self._is_schema_triple(s, p, o):
                            continue
                        reasoned_instances_graph.add((s, p, o))
                    
                    reasoned_path = ontology_dir / "instances_reasoned.ttl"
                    reasoned_instances_graph.serialize(destination=str(reasoned_path), format="turtle")
                    stats["reasoned_triples"] = len(list(reasoned_instances_graph.triples((None, None, None))))
                    safe_print(f"[INFO] 추론된 인스턴스 저장 완료: {reasoned_path} ({stats['reasoned_triples']} triples)")
                    
                    # [FIX] 원본 오염 방지를 위해 self.graph를 reasoned_graph로 자동 교체하는 로직 제거
                    # self.graph = reasoned_graph
                    # safe_print(f"[INFO] 메모리 그래프 업데이트 완료: {len(reasoned_graph)} triples")
                    pass
                else:
                    safe_print("[WARN] 추론 그래프 생성 실패. instances_reasoned.ttl 저장 건너뜀")
            
            # 4. 기존 중간 생성물 파일 및 구형 통합 파일 정리
            if cleanup_old_files:
                old_files = [
                    Path(self.ontology_path) / "updated_graph.ttl",
                ]
                
                for old_file in old_files:
                    if old_file.exists():
                        try:
                            # 백업 (파일 위치에 맞는 백업 디렉토리 사용)
                            if backup_old_files:
                                # 파일이 ontology_path에 있으면 ontology_path/backup, 아니면 output_path/backup
                                if str(old_file).startswith(str(Path(self.ontology_path))):
                                    backup_dir = Path(self.ontology_path) / "backup"
                                else:
                                    backup_dir = ontology_dir / "backup" # Use ontology_dir here
                                backup_dir.mkdir(parents=True, exist_ok=True)
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                backup_path = backup_dir / f"{old_file.name}.backup_{timestamp}"
                                shutil.copy2(old_file, backup_path)
                                safe_print(f"[INFO] 백업 완료: {backup_path}")
                            
                            # 삭제
                            old_file.unlink()
                            safe_print(f"[INFO] 기존 파일 삭제: {old_file}")
                        except Exception as e:
                            safe_print(f"[WARN] 파일 정리 실패: {old_file}, {e}")
            
            stats["success"] = True
            stats["message"] = "Graph saved successfully"
            return stats
            
        except Exception as e:
            stats["message"] = f"Failed to save RDF graph: {str(e)}"
            safe_print(f"[WARN] {stats['message']}")
            import traceback
            traceback.print_exc()
            return stats
    
    def _is_inferred_triple(self, s, p, o) -> bool:
        """
        특정 트리플이 추론된 것인지 판단
        
        판단 기준:
        1. Axiom(주석) 정보가 있는지 확인
        2. 특정 추론 전용 프레디케이트인지 확인 (hasAdvantage 등)
        """
        if self.graph is None:
            return False
            
        # 1. Axiom 정보 확인 (annotatedSource/Property/Target)
        # 이 작업은 성능에 영향을 줄 수 있으므로 주의
        from rdflib import OWL, RDF, RDFS
        # [MOD] 효율성을 위해 모든 Axiom을 먼저 찾지 않고, 
        # (Axiom, annotatedSource, s)가 있는 노드만 필터링
        for axiom in self.graph.subjects(OWL.annotatedSource, s):
            if (axiom, RDF.type, OWL.Axiom) in self.graph and \
               (axiom, OWL.annotatedProperty, p) in self.graph and \
               (axiom, OWL.annotatedTarget, o) in self.graph:
                # Axiom 설명 확인
                for _, _, comment in self.graph.triples((axiom, RDFS.comment, None)):
                    if str(comment) == "inferred_relation":
                        return True
        
        # 2. 추론 전용 프레디케이트 확인 (전술 규칙 등에서 생성)
        # NS가 초기화되지 않았을 경우를 대비해 문자열 평탄화
        ns_str = str(self.ns) if self.ns else "http://coa-agent-platform.org/ontology#"
        inferred_predicates = [
            ns_str + "hasAdvantage", 
            ns_str + "hasDisadvantage",
            ns_str + "tacticalEffect",
            ns_str + "inferred_relation"
        ]
        if str(p) in inferred_predicates:
            return True
            
        return False

    def generate_reasoned_graph(self, 
                               enable_semantic_inference: bool = True,
                               run_tactical_rules: bool = True,
                               run_owl_reasoner: bool = True) -> Optional[Graph]:
        """
        추론 엔진을 사용하여 추론된 그래프 생성
        
        Args:
            enable_semantic_inference: 의미 기반 추론(LLM/Search) 활성화 여부
            run_tactical_rules: SPARQL 기반 전술 규칙 실행 여부
            run_owl_reasoner: OWL-RL 추론기 실행 여부
        
        Returns:
            추론 결과가 추가된 Graph 객체 (instances_reasoned.ttl로 저장될 그래프)
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            safe_print("[WARN] RDFLib not available or graph is None. Cannot generate reasoned graph.")
            return None
        
        import time
        start_total = time.time()
        
        try:
            # 기존 그래프 복사 (추론 결과를 추가하기 위해)
            reasoned_graph = Graph()
            
            # 네임스페이스 바인딩 복사
            for prefix, namespace in self.graph.namespaces():
                reasoned_graph.bind(prefix, namespace)
            
            # 기존 그래프의 모든 트리플 복사
            for s, p, o in self.graph:
                reasoned_graph.add((s, p, o))
            
            safe_print("[INFO] 추론 그래프 생성 시작...")
            
            # SemanticInference를 사용한 의미 기반 추론
            if enable_semantic_inference:
                try:
                    from core_pipeline.semantic_inference import SemanticInference
                    semantic_inference = SemanticInference(self.config)
                    
                    # 그래프의 주요 엔티티들에 대해 추론 수행
                    # COA, Threat, Asset 등의 주요 엔티티 타입 추출
                    from rdflib import RDF, RDFS
                    
                    # COA 클래스 찾기 (통일된 네임스페이스 사용)
                    coa_class = self.ns["COA"]
                    coa_library_class = self.ns["COA_Library"]
                    
                    # COA 인스턴스 찾기 (COA 타입이거나 COA_Library 타입인 모든 인스턴스)
                    coa_instances = []
                    # 직접 COA 타입인 것들
                    coa_instances.extend(list(self.graph.triples((None, RDF.type, coa_class))))
                    # COA_Library 타입인 것들도 포함 (실제 데이터는 COA_Library로 저장됨)
                    coa_instances.extend(list(self.graph.triples((None, RDF.type, coa_library_class))))
                    
                    # COA의 하위 클래스들도 검색
                    for s, p, o in self.graph.triples((None, RDFS.subClassOf, coa_class)):
                        # 하위 클래스의 인스턴스들도 찾기
                        subclass_instances = list(self.graph.triples((None, RDF.type, s)))
                        coa_instances.extend(subclass_instances)
                    
                    # 중복 제거
                    coa_instances = list(set(coa_instances))
                    safe_print(f"[INFO] COA 인스턴스 {len(coa_instances)}개 발견")
                    
                    if len(coa_instances) == 0:
                        safe_print("[WARN] COA 인스턴스를 찾을 수 없습니다.")
                    
                    # [PERFORMANCE] 처리할 인스턴스 수 제한 및 로그 강화
                    max_coa_to_process = self.config.get("max_coa_semantic_inference", 20)
                    process_count = min(len(coa_instances), max_coa_to_process)
                    safe_print(f"[INFO] Semantic Inference 시작 (대상: {process_count}/{len(coa_instances)}개)")
                    
                    inferred_count = 0
                    start_semantic = time.time()
                    for idx, (coa_subj, _, _) in enumerate(coa_instances[:process_count]):
                        if idx > 0 and idx % 5 == 0:
                            safe_print(f"  - 진행률: {idx}/{process_count}...")
                        # [FIX] Subject URI에 공백이 있는 경우 처리
                        coa_str = str(coa_subj)
                        if " " in coa_str:
                            coa_subj = URIRef(coa_str.replace(" ", "_"))
                        
                        coa_uri = str(coa_subj)
                        coa_local = _localname(coa_subj)
                        
                        # 의미 기반 관계 추론
                        relations = semantic_inference.infer_relations(self.graph, coa_local, max_depth=2)
                        
                        # 추론된 관계를 그래프에 추가
                        for rel in relations.get('direct', []) + relations.get('indirect', []):
                            related_entity = rel.get('entity', '')
                            predicate = rel.get('predicate', '')
                            
                            if related_entity and predicate:
                                try:
                                    # URI 변환
                                    if not related_entity.startswith('http://'):
                                        safe_related = _make_uri_safe(related_entity)
                                        related_uri = URIRef(self.ns[safe_related])
                                    else:
                                        # 이미 URI인 경우에도 공백이 있으면 처리 (모든 공백 문자 대상)
                                        safe_related = re.sub(r'\s+', '_', related_entity)
                                        related_uri = URIRef(safe_related)
                                    
                                    if not predicate.startswith('http://'):
                                        safe_pred = _make_uri_safe(predicate)
                                        pred_uri = URIRef(self.ns[safe_pred])
                                    else:
                                        # 이미 URI인 경우에도 공백이 있으면 처리 (모든 공백 문자 대상)
                                        safe_pred = re.sub(r'\s+', '_', predicate)
                                        pred_uri = URIRef(safe_pred)
                                    
                                    
                                    # [NEW] 추론 필터링 (과도한 추론 방지)
                                    # [MOD] rdf:type, sameAs, equivalentClass 등은 추론 결과로 추가하지 않음 (오염 방지)
                                    from rdflib import RDF, OWL
                                    if pred_uri in [RDF.type, OWL.sameAs, OWL.equivalentClass, OWL.equivalentProperty]:
                                        continue

                                    if hasattr(semantic_inference, '_should_exclude_inference'):
                                        if semantic_inference._should_exclude_inference(str(coa_subj), str(pred_uri), str(related_uri)):
                                            continue
                                            
                                    # 추론된 관계 추가 (중복 체크)

                                    if (coa_subj, pred_uri, related_uri) not in reasoned_graph:
                                        reasoned_graph.add((coa_subj, pred_uri, related_uri))
                                        inferred_count += 1
                                        
                                        # 추론된 관계임을 표시하는 메타데이터 추가
                                        from rdflib import BNode
                                        inference_node = BNode()
                                        reasoned_graph.add((inference_node, RDF.type, OWL.Axiom))
                                        reasoned_graph.add((inference_node, OWL.annotatedSource, coa_subj))
                                        reasoned_graph.add((inference_node, OWL.annotatedProperty, pred_uri))
                                        reasoned_graph.add((inference_node, OWL.annotatedTarget, related_uri))
                                        reasoned_graph.add((inference_node, RDFS.comment, Literal("inferred_relation")))
                                        
                                except Exception as e:
                                    safe_print(f"[WARN] 추론 관계 추가 실패: {e}")
                    
                    safe_print(f"[INFO] Semantic Inference 완료: {inferred_count}개 관계 추가 (시간: {time.time() - start_semantic:.2f}초)")
                    
                except ImportError as e:
                    safe_print(f"[WARN] SemanticInference를 임포트할 수 없습니다: {e}")
                except Exception as e:
                    safe_print(f"[WARN] 의미 기반 추론 실패: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 🔥 NEW: SPARQL 기반 전술적 유불리 추론 (hasAdvantage, hasDisadvantage)
            tactical_rules_path = Path(self.ontology_path) / "tactical_rules.sparql"
            if run_tactical_rules and tactical_rules_path.exists():
                start_tactical = time.time()
                try:
                    safe_print(f"[INFO] 전술 추론 규칙 실행 중: {tactical_rules_path}")
                    with open(tactical_rules_path, 'r', encoding='utf-8') as f:
                        rules_content = f.read()
                    
                    # PREFIX 추출
                    prefixes = []
                    for line in rules_content.split('\n'):
                        if line.strip().upper().startswith('PREFIX'):
                            prefixes.append(line.strip())
                    prefix_str = '\n'.join(prefixes) + '\n'
                    
                    # SPARQL CONSTRUCT 쿼리 분리
                    raw_queries = re.split(r'(?=CONSTRUCT)', rules_content, flags=re.IGNORECASE)
                    
                    tactical_inferred_count = 0
                    for q in raw_queries:
                        if 'CONSTRUCT' not in q.upper():
                            continue
                        
                        # PREFIX와 결합
                        full_query = prefix_str + q
                        
                        # [DEBUG] 쿼리 실행 시도
                        try:
                            result_graph = reasoned_graph.query(full_query)
                            for s, p, o in result_graph:
                                if (s, p, o) not in reasoned_graph:
                                    reasoned_graph.add((s, p, o))
                                    tactical_inferred_count += 1
                        except Exception as qe:
                            safe_print(f"[WARN] 개별 전술 쿼리 실행 실패: {qe}")
                    
                    safe_print(f"[INFO] 전술 추론 완료: {tactical_inferred_count}개 유불리 관계 추가 (시간: {time.time() - start_tactical:.2f}초)")
                    
                except Exception as e:
                    safe_print(f"[WARN] 전술 추론 규칙 실행 중 오류: {e}")
                    import traceback
                    traceback.print_exc()
            
            # OWL-RL 추론 실행 (SemanticInference 이후)
            if run_owl_reasoner:
                start_owl = time.time()
                try:
                    from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
                    if OWLRL_AVAILABLE:
                        # [PERFORMANCE] 대규모 그래프 자동 체크 및 보호
                        graph_size = len(reasoned_graph)
                        include_rdfs = self.config.get("include_rdfs_inference", False) # 기본값 False로 변경
                        
                        if graph_size > 20000 and include_rdfs:
                            safe_print(f"[WARN] 대규모 그래프 감지 ({graph_size} triples). 안전을 위해 RDFS 추론을 비활성화합니다.")
                            include_rdfs = False
                            
                        safe_print(f"[INFO] OWL-RL 추론기 가동 중 (대상: {graph_size} triples, RDFS: {include_rdfs})...")
                        namespace = str(self.ns) if self.ns else None
                        reasoner = OWLReasoner(reasoned_graph, namespace)
                        inferred_graph = reasoner.run_inference(include_rdfs=include_rdfs)
                        
                        if inferred_graph is not None:
                            stats = reasoner.get_stats()
                            if stats.get("success"):
                                owl_new_count = stats.get("new_inferences", 0)
                                if owl_new_count > 0:
                                    safe_print(f"[INFO] OWL-RL 추론 완료: {owl_new_count}개 새로운 트리플 생성 (시간: {time.time() - start_owl:.2f}초)")
                                    # OWL-RL 추론 결과를 reasoned_graph에 반영
                                    reasoned_graph = inferred_graph
                                else:
                                    safe_print(f"[INFO] OWL-RL 추론 완료: 새로운 트리플 없음 (시간: {time.time() - start_owl:.2f}초)")
                            else:
                                safe_print(f"[WARN] OWL-RL 추론 실패: {stats.get('error', 'Unknown error')}")
                    else:
                        safe_print("[INFO] owlrl 라이브러리가 없어 OWL-RL 추론을 건너뜁니다.")
                except Exception as e:
                    safe_print(f"[WARN] OWL-RL 추론 실행 실패: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 추론된 그래프의 트리플 수 확인 (정확한 측정)
            reasoned_triples_set = set(reasoned_graph)
            reasoned_triples = len(reasoned_triples_set)
            original_triples_set = set(self.graph)
            original_triples = len(original_triples_set)
            new_triples = reasoned_triples - original_triples
            
            safe_print(f"[INFO] 전체 추론 프로세스 완료: 원본 {original_triples}개 -> 최종 {reasoned_triples}개 (총 소요시간: {time.time() - start_total:.2f}초)")
            
            return reasoned_graph
            
        except Exception as e:
            safe_print(f"[WARN] 추론 그래프 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_from_file(self, file_path: str):
        """
        파일로부터 온톨로지 로드
        
        Args:
            file_path: OWL, TTL 등의 온톨로지 파일 경로
            
        Returns:
            RDF Graph 객체
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            safe_print(f"[WARN] 파일을 찾을 수 없습니다: {file_path}")
            return None
            
        try:
            # 포맷 자동 감지 (확장자 기반)
            fmt = 'turtle' if path_obj.suffix == '.ttl' else 'xml'
            if path_obj.suffix == '.nt':
                fmt = 'nt'
                
            safe_print(f"[INFO] 온톨로지 로드 중... ({file_path})")
            
            # 기존 그래프 병합 (새로운 Graph 객체 생성이 아닌 병합)
            # [FIX] rdflib parse 시 인코딩 문제로 인한 가상 변수 오류(AttributeError) 가능성 대비 예외 처리 강화
            try:
                self.graph.parse(str(path_obj), format=fmt)
            except AttributeError as ae:
                if 'newUniversal' in str(ae):
                    safe_print(f"[CRITICAL] 온톨로지 파싱 중 변수 생성 오류 발생. 파일에 규칙에 어긋나는 '?' 기호가 있는지 확인하십시오. ({file_path})")
                raise ae
                
            safe_print(f"[INFO] 온톨로지 로드 완료. 현재 트리플 수: {len(self.graph)}")
            return self.graph
        except Exception as e:
            safe_print(f"[ERROR] 온톨로지 로드 실패 ({file_path}): {e}")
            import traceback
            safe_print(traceback.format_exc())
            return None
            
    def try_load_existing_graph(self):
        """
        기존에 저장된 온톨로지 그래프 자동 로드 시도
        우선순위: instances_reasoned.ttl > instances.ttl > schema.ttl
        
        instances.ttl만 있는 경우 OWL-RL 추론을 자동 실행하여 추론 트리플 생성
        """
        if not RDFLIB_AVAILABLE:
            return

        ontology_dir = Path(self.ontology_path)
        if not ontology_dir.exists():
            return

        # 로드 우선순위 파일 목록
        load_candidates = [
            "instances_reasoned.ttl", # 추론된 완성본
            "instances.ttl",          # 추론 전 인스턴스
            "schema.ttl"              # 스키마만
        ]
        
        loaded = False
        loaded_filename = None
        for filename in load_candidates:
            file_path = ontology_dir / filename
            if file_path.exists():
                safe_print(f"[INFO] 기존 온톨로지 파일 발견: {filename}. 자동 로드를 시도합니다.")
                
                # instances.ttl 로드 시 원본 크기를 추적하기 위해
                # 스키마 로드 전에 원본 크기 측정
                if filename == "instances.ttl":
                    # 스키마가 분리되어 있을 수 있으므로 schema.ttl은 항상 먼저 로드 시도
                    schema_path = ontology_dir / "schema.ttl"
                    if schema_path.exists():
                        self.load_from_file(str(schema_path))
                    
                    # instances.ttl 로드 전 그래프 크기 저장 (스키마만 있는 상태)
                    before_instances_size = len(set(self.graph)) if self.graph else 0
                    
                    # instances.ttl 로드
                    if self.load_from_file(str(file_path)):
                        loaded = True
                        loaded_filename = filename
                        # instances.ttl 로드 직후의 원본 크기 저장 (스키마 + 인스턴스)
                        # 이 크기를 기준으로 추론 여부를 판단
                        self._original_graph_size = len(set(self.graph)) if self.graph else 0
                        safe_print(f"[INFO] '{filename}' 기반으로 그래프 초기화 완료. 원본 크기: {self._original_graph_size} triples")
                        break
                else:
                    # instances_reasoned.ttl 또는 schema.ttl 로드 시
                    # 스키마가 분리되어 있을 수 있으므로 schema.ttl은 항상 먼저 로드 시도 (instances_reasoned 로드 시)
                    if filename != "schema.ttl":
                        schema_path = ontology_dir / "schema.ttl"
                        if schema_path.exists():
                             self.load_from_file(str(schema_path))
                    
                    if self.load_from_file(str(file_path)):
                        loaded = True
                        loaded_filename = filename
                        safe_print(f"[INFO] '{filename}' 기반으로 그래프 초기화 완료.")
                        # instances_reasoned.ttl이 로드된 경우, 이미 추론된 그래프로 간주
                        if filename == "instances_reasoned.ttl":
                            self._inference_performed = True
                        break
        
        if not loaded:
            safe_print("[INFO] 로드할 기존 온톨로지 파일이 없습니다. 새로운 생성이 필요합니다.")
            return
        
        # instances.ttl만 로드된 경우 (instances_reasoned.ttl이 없는 경우) OWL-RL 추론 자동 실행
        # 단, 이미 추론이 실행되었는지 확인 (중복 추론 방지)
        if loaded_filename == "instances.ttl":
            # 이미 추론이 실행되었는지 확인 (플래그 또는 그래프 크기로 판단)
            # instances.ttl만 로드된 경우 기본적으로 추론이 필요하지만,
            # 이미 추론된 그래프인 경우 스킵
            enable_auto_inference = self.config.get("enable_auto_owl_inference", True)
            
            # 추론 실행 여부 확인: 이미 추론된 그래프인지 체크
            # 원본 그래프 크기를 동적으로 추적하여 비율 기반으로 판단
            current_triples = len(set(self.graph)) if self.graph else 0
            
            # 원본 그래프 크기가 저장되어 있는지 확인
            if self._original_graph_size is not None and self._original_graph_size > 0:
                # 원본 대비 비율로 판단 (추론된 그래프는 일반적으로 원본의 약 1.5배 이상)
                # 안전 마진을 두어 1.3배 이상이면 추론된 것으로 간주
                ratio = current_triples / self._original_graph_size
                is_already_inferred = ratio >= 1.3  # 원본 대비 1.3배 이상
                safe_print(f"[INFO] 추론 여부 판단 - 원본: {self._original_graph_size} triples, 현재: {current_triples} triples, 비율: {ratio:.2f}x")
            else:
                # 원본 크기가 저장되지 않은 경우 (이론적으로 발생하지 않아야 함)
                # 기본값으로 현재 크기가 0보다 크면 추론된 것으로 간주하지 않음
                is_already_inferred = False
                safe_print(f"[WARN] 원본 그래프 크기가 저장되지 않았습니다. 추론을 실행합니다.")
            
            if enable_auto_inference and not is_already_inferred:
                try:
                    from core_pipeline.owl_reasoner import OWLReasoner, OWLRL_AVAILABLE
                    if OWLRL_AVAILABLE:
                        safe_print("[INFO] instances_reasoned.ttl이 없어 OWL-RL 추론을 자동 실행합니다...")
                        namespace = str(self.ns) if self.ns else None
                        reasoner = OWLReasoner(self.graph, namespace)
                        inferred_graph = reasoner.run_inference()
                        
                        if inferred_graph is not None:
                            stats = reasoner.get_stats()
                            if stats.get("success"):
                                new_count = stats.get("new_inferences", 0)
                                if new_count > 0:
                                    safe_print(f"[INFO] OWL-RL 추론 완료: {new_count}개 새로운 트리플 생성")
                                    # 추론된 그래프를 메모리에 적용
                                    self.graph = inferred_graph
                                    
                                    # 추론 실행 플래그 설정 (중복 방지)
                                    self._inference_performed = True
                                    # 원본 크기는 유지 (추론 여부 판단에 계속 사용)
                                    
                                    # 추론된 그래프 저장 (선택적)
                                    save_reasoned = self.config.get("save_reasoned_graph_on_startup", False)
                                    if save_reasoned:
                                        try:
                                            reasoned_path = ontology_dir / "instances_reasoned.ttl"
                                            inferred_graph.serialize(destination=str(reasoned_path), format="turtle")
                                            safe_print(f"[INFO] 추론된 그래프 저장: {reasoned_path}")
                                        except Exception as e:
                                            safe_print(f"[WARN] 추론된 그래프 저장 실패: {e}")
                                else:
                                    safe_print("[INFO] OWL-RL 추론 완료: 새로운 트리플 없음 (이미 모든 관계가 존재)")
                            else:
                                safe_print(f"[WARN] OWL-RL 추론 실패: {stats.get('error', 'Unknown error')}")
                    else:
                        safe_print("[INFO] owlrl 라이브러리가 없어 OWL-RL 추론을 건너뜁니다.")
                except Exception as e:
                    safe_print(f"[WARN] OWL-RL 추론 자동 실행 실패: {e}")
            elif is_already_inferred:
                safe_print("[INFO] 이미 추론된 그래프입니다. 추론을 건너뜁니다.")
                self._inference_performed = True
    
    def query(self, query_string: str, bindings: Optional[Dict] = None, return_format: str = 'list') -> Union[List[Dict], pd.DataFrame]:
        """
        SPARQL 쿼리 문자열 직접 실행
        
        Args:
            query_string: SPARQL 쿼리 문자열
            bindings: 쿼리 변수 바인딩
            return_format: 반환 형식 ('list', 'dataframe')
            
        Returns:
            쿼리 결과 (리스트 또는 DataFrame)
        """
        if not RDFLIB_AVAILABLE:
            safe_print("[WARN] rdflib not available. Cannot run SPARQL query.")
            return [] if return_format == 'list' else pd.DataFrame()
        
        if self.graph is None:
            safe_print("[WARN] Graph not initialized. Cannot run SPARQL query.")
            return [] if return_format == 'list' else pd.DataFrame()
        
        try:
            # 쿼리 준비
            query = prepareQuery(query_string)
            
            # 바인딩이 있으면 적용
            if bindings:
                query_result = self.graph.query(query, initBindings=bindings)
            else:
                query_result = self.graph.query(query)
            
            # 반환 형식에 따라 변환
            if return_format == 'dataframe':
                return self._results_to_dataframe(query_result)
            else:
                return self._results_to_list(query_result)
                
        except Exception as e:
            safe_print(f"[ERROR] SPARQL query execution failed: {e}")
            import traceback
            traceback.print_exc()
            return [] if return_format == 'list' else pd.DataFrame()
    
    def run_sparql(self, query_path: str, bindings: Optional[Dict] = None, return_format: str = 'list') -> Union[List[Dict], pd.DataFrame]:
        """
        SPARQL 쿼리 실행
        
        Args:
            query_path: SPARQL 쿼리 파일 경로
            bindings: 쿼리 변수 바인딩 (예: {'?situation': URIRef(NS['SIT_001'])})
            return_format: 반환 형식 ('list', 'dataframe')
            
        Returns:
            쿼리 결과 (리스트 또는 DataFrame)
        """
        if not RDFLIB_AVAILABLE:
            safe_print("[WARN] rdflib not available. Cannot run SPARQL query.")
            return [] if return_format == 'list' else pd.DataFrame()
        
        if self.graph is None:
            safe_print("[WARN] Graph not initialized. Cannot run SPARQL query.")
            return [] if return_format == 'list' else pd.DataFrame()
        
        if not os.path.exists(query_path):
            raise FileNotFoundError(f"SPARQL query file not found: {query_path}")
        
        with open(query_path, 'r', encoding='utf-8') as f:
            query_str = f.read()
        
        return self.query(query_str, bindings=bindings, return_format=return_format)
    
    def _results_to_dataframe(self, sparql_results) -> pd.DataFrame:
        """SPARQL 결과를 DataFrame으로 변환"""
        rows = []
        for row in sparql_results:
            row_dict = {}
            for key in row.labels:
                value = row[key]
                # URIRef를 문자열로 변환
                if hasattr(value, 'toPython'):
                    row_dict[key] = str(value.toPython())
                else:
                    row_dict[key] = str(value)
            rows.append(row_dict)
        
        if not rows:
            return pd.DataFrame()
        
        return pd.DataFrame(rows)
    
    def _results_to_list(self, sparql_results) -> List[Dict]:
        """SPARQL 결과를 리스트로 변환"""
        rows = []
        for row in sparql_results:
            row_dict = {}
            for key in row.labels:
                value = row[key]
                if hasattr(value, 'toPython'):
                    row_dict[key] = str(value.toPython())
                else:
                    row_dict[key] = str(value)
            rows.append(row_dict)
        return rows
    
    def to_json(self) -> Dict:
        """
        그래프를 JSON 형식으로 변환 (기존 graph_loader.py의 반환 형식)
        
        Returns:
            {"instances": {"nodes": [...], "links": [...]}, "schema": {"nodes": [...], "links": [...]}}
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return {
                "instances": {"nodes": [], "links": []}, 
                "schema": {"nodes": [], "links": []},
                "stats": {}
            }
        
        # 디버깅: 그래프 상태 확인
        # [OPTIMIZATION] 불필요한 len(list(triples)) 호출 제거 (매우 느림)
        # safe_print(f"[DEBUG] to_json 시작")
        
        # [OPTIMIZATION] 캐시 확인
        # 그래프 변경 감지를 위해 id와 사이즈 체크
        current_graph_hash = (id(self.graph), len(self.graph))
        if self._json_cache and self._last_graph_hash == current_graph_hash:
            # safe_print("[DEBUG] Using cached JSON data")
            return self._json_cache
            
        # 변수 초기화 (Stats 생성용)
        total_triples = len(self.graph)
        owl_class_count = 0
        owl_property_count = 0
        subClassOf_count = 0
        domain_count = 0
        range_count = 0
            
        instances = {"nodes": [], "links": []}
        schema = {"nodes": [], "links": []}
        
        # [OPTIMIZATION] 한 번의 순회로 필요한 모든 정보 수집 (RDFLib triples 탐색 최소화)
        node_groups = {}      # {uri: group_name} (최종 결정된 그룹)
        node_labels = {}      # {uri: label}
        virtual_status = {}   # {uri: bool}
        
        # 엔티티 타입 우선순위 (가장 구체적이고 사용자에게 친숙한 타입 우선)
        type_priority = [
            "DefenseCOA", "OffensiveCOA", "CounterAttackCOA", "PreemptiveCOA",
            "DeterrenceCOA", "ManeuverCOA", "InformationOpsCOA",
            "COA", "COA_Library",
            "아군부대현황", "적군부대현황", "아군가용자산", "위협상황", "임무정보", 
            "전장축선", "지형셀", "기상상황", "제약조건", "민간인지역", "시나리오모음",
            "위협유형_마스터", "임무별_자원할당"
        ]
        priority_set = set(type_priority)
        
        # 1. 타입 정보 수집 및 그룹 결정
        for s, _, o in self.graph.triples((None, RDF.type, None)):
            if isinstance(s, BNode): continue
            
            local_type = _localname(o)
            
            # 이미 우선순위가 높은 그룹으로 결정된 경우 스킵 (단, 더 높은 우선순위가 나오면 교체)
            current_group = node_groups.get(s)
            
            if local_type in priority_set:
                # 우선순위 타입 발견!
                # 기존 그룹이 없거나, 기존 그룹이 우선순위 목록에 없거나(기타 등), 
                # 현재 타입이 더 높은 우선순위라면 교체
                if not current_group or current_group not in priority_set:
                    node_groups[s] = local_type
                else:
                    # 둘 다 우선순위 목록에 있다면, 리스트 인덱스로 비교 (낮은 인덱스가 높은 우선순위)
                    try:
                        curr_idx = type_priority.index(current_group)
                        new_idx = type_priority.index(local_type)
                        if new_idx < curr_idx:
                            node_groups[s] = local_type
                    except ValueError:
                        pass # should not happen
            elif not current_group:
                # 아직 그룹이 없으면 일반 타입 할당 (단, NamedIndividual 등 제외)
                if local_type not in ["NamedIndividual", "Thing", "Resource"]:
                    node_groups[s] = local_type
            
        # 2. 라벨 정보 수집
        for s, _, o in self.graph.triples((None, RDFS.label, None)):
            if isinstance(s, BNode): continue
            node_labels[s] = str(o)
            
        # 3. 가상 엔티티 정보 수집
        is_virtual_uri = URIRef(self.ns["isVirtualEntity"])
        for s, _, o in self.graph.triples((None, is_virtual_uri, None)):
            virtual_status[s] = str(o).lower() in ['true', '1']

        inst_nodes = {}
        virtual_entity_count = 0
        actual_data_node_count = 0
        
        # 수집된 노드들 생성
        # (타입이 하나라도 있는 노드들 대상)
        # 주의: 타입이 없는 노드(라벨만 있는 경우 등)는 여기서 누락될 수 있으므로, 
        # node_groups, node_labels, virtual_status의 합집합을 순회해야 함
        all_subjects = set(node_groups.keys()) | set(node_labels.keys()) | set(virtual_status.keys())
        
        for s in all_subjects:
            local_name = _localname(s)
            
            # 그룹 결정 (없으면 '기타')
            type_name = node_groups.get(s, "기타")
            
            # 인덱싱된 정보 사용 (성능 향상)
            is_virtual = virtual_status.get(s, False)
            if is_virtual:
                virtual_entity_count += 1
            else:
                actual_data_node_count += 1
            
            rdfs_label = node_labels.get(s)
            
            # 노드 표시: ID를 기본으로 하고, rdfs:label이 있으면 ID (Label) 형식 사용
            if rdfs_label and rdfs_label != local_name:
                display_label = f"{local_name} ({rdfs_label})"
            else:
                display_label = local_name
            
            inst_nodes[local_name] = {
                "id": local_name,
                "label": display_label,
                "group": type_name,
                "is_virtual": is_virtual
            }
        
        instances["nodes"] = list(inst_nodes.values())
        
        # 인스턴스 링크 추출
        inst_links = []
        excluded_predicates = {str(RDF.type), str(RDFS.label)}
        
        # [NEW] 타겟 노드가 노드 리스트에 없는 경우 자동 추가 (고립 방지)
        missing_targets = set()
        
        for u, p, a in self.graph.triples((None, None, None)):
            if str(p) in excluded_predicates:
                continue
            if not isinstance(a, URIRef) and not isinstance(a, BNode): # 리터럴 제외
                continue
            # BNode 체크는 이미 했으므로 생략 가능하나 안전장치
            if isinstance(u, BNode) or isinstance(a, BNode):
                continue
                
            u_local = _localname(u)
            a_local = _localname(a)
            
            # 소스 노드가 있으면 링크 생성 시도, 없으면 자동 생성
            if u_local not in inst_nodes:
                # 소스 노드 자동 생성 (타입/라벨 정보가 없었던 경우)
                inst_nodes[u_local] = {
                    "id": u_local,
                    "label": u_local, # 기본 라벨
                    "group": "기타", # 기본 그룹
                    "is_virtual": False
                }
                # 나중에 라벨/타입 보강을 위해 missing_targets처럼 관리할 수도 있으나, 
                # 일단 링크 연결성이 중요하므로 즉시 생성
            
            # 타겟 노드가 없으면 추가 리스트에 넣음
            if a_local not in inst_nodes:
                missing_targets.add(a)
            
            inst_links.append({
                "source": u_local,
                "target": a_local,
                "relation": _localname(p)
            })
        
        # [NEW] 누락된 타겟 노드 추가
        for missing_uri in missing_targets:
             local = _localname(missing_uri)
             if local not in inst_nodes:
                # 라벨 가져오기 시도
                label = local
                for _, _, lbl in self.graph.triples((missing_uri, RDFS.label, None)):
                    label = f"{local} ({str(lbl)})"
                    break
                
                # 타입 추론 (간단히 첫번째 타입 사용)
                type_name = "기타"
                for _, _, t in self.graph.triples((missing_uri, RDF.type, None)):
                    t_local = _localname(t)
                    if t_local not in ["NamedIndividual", "Thing"]:
                        type_name = t_local
                        break
                
                inst_nodes[local] = {
                    "id": local,
                    "label": label,
                    "group": type_name,
                    "is_virtual": False
                }
        
        # 노드 리스트 재갱신
        instances["nodes"] = list(inst_nodes.values())
        inst_links = [l for l in inst_links if l['target'] in inst_nodes] # 최종 유효성 검사
        instances["links"] = inst_links
        
        instances["links"] = inst_links
        
        # 스키마 노드 추출
        sch_nodes = {}
        schema_class_count = 0
        schema_property_count = 0
        
        # Table/Column 노드 (레거시)
        for s, _, _ in self.graph.triples((None, RDF.type, self.ns.Table)):
            sch_nodes[_localname(s)] = {"id": _localname(s), "label": _get_label(self.graph, self.ns, s), "group": "Table"}
        for s, _, _ in self.graph.triples((None, RDF.type, self.ns.Column)):
            sch_nodes[_localname(s)] = {"id": _localname(s), "label": _get_label(self.graph, self.ns, s), "group": "Column"}
        
        # OWL.Class 노드 추출 (ns와 ns_legacy 모두 확인)
        for s, _, _ in self.graph.triples((None, RDF.type, OWL.Class)):
            s_str = str(s)
            if s_str.startswith(str(self.ns)) or s_str.startswith(str(self.ns_legacy)):
                node_id = _localname(s)
                if node_id not in sch_nodes:
                    sch_nodes[node_id] = {"id": node_id, "label": _get_label(self.graph, self.ns, s), "group": "Class"}
                    schema_class_count += 1
        
        # ObjectProperty 노드 추가
        for s, _, _ in self.graph.triples((None, RDF.type, OWL.ObjectProperty)):
            s_str = str(s)
            if s_str.startswith(str(self.ns)) or s_str.startswith(str(self.ns_legacy)):
                node_id = _localname(s)
                if node_id not in sch_nodes:
                    sch_nodes[node_id] = {"id": node_id, "label": _get_label(self.graph, self.ns, s), "group": "Property"}
                    schema_property_count += 1
        
        # DatatypeProperty 노드 추가
        for s, _, _ in self.graph.triples((None, RDF.type, OWL.DatatypeProperty)):
            s_str = str(s)
            if s_str.startswith(str(self.ns)) or s_str.startswith(str(self.ns_legacy)):
                node_id = _localname(s)
                if node_id not in sch_nodes:
                    sch_nodes[node_id] = {"id": node_id, "label": _get_label(self.graph, self.ns, s), "group": "Property"}
                    schema_property_count += 1
        
        # 🔥 로그 최적화: 불필요한 DEBUG 로그 제거
        # safe_print(f"[DEBUG] to_json: 스키마 노드 추출 - Class {schema_class_count}개, Property {schema_property_count}개")
        
        # 스키마 링크 추출
        sch_links = []
        
        # hasColumn 관계 (기존)
        for t, _, c in self.graph.triples((None, self.ns.hasColumn, None)):
            t_local = _localname(t)
            c_local = _localname(c)
            if t_local not in sch_nodes:
                sch_nodes[t_local] = {"id": t_local, "label": _get_label(self.graph, self.ns, t), "group": "Table"}
            if c_local not in sch_nodes:
                sch_nodes[c_local] = {"id": c_local, "label": _get_label(self.graph, self.ns, c), "group": "Column"}
            sch_links.append({"source": t_local, "target": c_local, "relation": "컬럼"})
        
        # subClassOf 관계
        subClassOf_count = 0
        for s, _, o in self.graph.triples((None, RDFS.subClassOf, None)):
            s_local = _localname(s)
            o_local = _localname(o)
            s_str = str(s)
            o_str = str(o)
            if not (s_str.startswith(str(self.ns)) or s_str.startswith(str(self.ns_legacy))):
                continue
            if not (o_str.startswith(str(self.ns)) or o_str.startswith(str(self.ns_legacy))):
                continue
            
            if s_local not in sch_nodes:
                sch_nodes[s_local] = {"id": s_local, "label": _get_label(self.graph, self.ns, s), "group": "Class"}
            if o_local not in sch_nodes:
                sch_nodes[o_local] = {"id": o_local, "label": _get_label(self.graph, self.ns, o), "group": "Class"}
            sch_links.append({"source": s_local, "target": o_local, "relation": "subClassOf"})
            subClassOf_count += 1
        
        # domain 관계 (Property -> Class)
        domain_count = 0
        for prop, _, cls in self.graph.triples((None, RDFS.domain, None)):
            prop_local = _localname(prop)
            cls_local = _localname(cls)
            prop_str = str(prop)
            cls_str = str(cls)
            if not (prop_str.startswith(str(self.ns)) or prop_str.startswith(str(self.ns_legacy))):
                continue
            if not (cls_str.startswith(str(self.ns)) or cls_str.startswith(str(self.ns_legacy))):
                continue
            
            if prop_local not in sch_nodes:
                sch_nodes[prop_local] = {"id": prop_local, "label": _get_label(self.graph, self.ns, prop), "group": "Property"}
            if cls_local not in sch_nodes:
                sch_nodes[cls_local] = {"id": cls_local, "label": _get_label(self.graph, self.ns, cls), "group": "Class"}
            sch_links.append({"source": prop_local, "target": cls_local, "relation": "domain"})
            domain_count += 1
        
        # range 관계 (Property -> Class)
        range_count = 0
        for prop, _, cls in self.graph.triples((None, RDFS.range, None)):
            prop_local = _localname(prop)
            cls_local = _localname(cls)
            prop_str = str(prop)
            cls_str = str(cls)
            if not (prop_str.startswith(str(self.ns)) or prop_str.startswith(str(self.ns_legacy))):
                continue
            if not (cls_str.startswith(str(self.ns)) or cls_str.startswith(str(self.ns_legacy))):
                continue
            
            if prop_local not in sch_nodes:
                sch_nodes[prop_local] = {"id": prop_local, "label": _get_label(self.graph, self.ns, prop), "group": "Property"}
            if cls_local not in sch_nodes:
                sch_nodes[cls_local] = {"id": cls_local, "label": _get_label(self.graph, self.ns, cls), "group": "Class"}
            sch_links.append({"source": prop_local, "target": cls_local, "relation": "range"})
            range_count += 1
        
        schema["nodes"] = list(sch_nodes.values())
        schema["links"] = sch_links
        
        # 🔥 로그 최적화: 불필요한 DEBUG 로그 제거
        # safe_print(f"[DEBUG] to_json: 스키마 링크 추출 완료 - subClassOf={subClassOf_count}, domain={domain_count}, range={range_count}, 총 {len(sch_links)}개")
        
        # 상세 통계 계산
        # rdf:type triples (인스턴스 타입 선언)
        instance_type_triples = len(list(self.graph.triples((None, RDF.type, None))))
        # rdfs:label triples
        label_triples = len(list(self.graph.triples((None, RDFS.label, None))))
        # Literal 값이 있는 triples (엣지로 변환되지 않음)
        literal_triples = 0
        for s, p, o in self.graph.triples((None, None, None)):
            if isinstance(o, Literal):
                literal_triples += 1
        
        # 그룹별 노드 수 계산
        group_counts = {}
        for node in instances["nodes"]:
            group = node.get("group", "기타")
            group_counts[group] = group_counts.get(group, 0) + 1
        
        # 노드별 연결도 계산
        node_degrees = {}
        for link in instances["links"]:
            source = link.get("source")
            target = link.get("target")
            node_degrees[source] = node_degrees.get(source, 0) + 1
            node_degrees[target] = node_degrees.get(target, 0) + 1
        
        # 평균 연결도 계산
        avg_degree = sum(node_degrees.values()) / len(node_degrees) if node_degrees else 0
        
        # 통계 정보 구성
        stats = {
            "total_triples": total_triples,
            "triples_by_category": {
                "instance_type": instance_type_triples,  # rdf:type (인스턴스)
                "labels": label_triples,  # rdfs:label
                "relationships": len(inst_links),  # 관계 (엣지로 변환됨)
                "literals": literal_triples,  # Literal 값 (엣지로 변환 안 됨)
                "schema": owl_class_count + owl_property_count + subClassOf_count + domain_count + range_count,  # 스키마 정보
            },
            "visualization": {
                "nodes": len(instances["nodes"]),
                "edges": len(inst_links),
                "groups": len(group_counts),
                "node_to_triple_ratio": len(instances["nodes"]) / total_triples * 100 if total_triples > 0 else 0,
                "edge_to_triple_ratio": len(inst_links) / total_triples * 100 if total_triples > 0 else 0,
            },
            "node_breakdown": {
                "total_nodes": len(instances["nodes"]),
                "actual_data_nodes": actual_data_node_count,  # 실제 데이터 행에서 생성된 노드
                "virtual_entities": virtual_entity_count,  # 가상 엔티티 (추론 관계용)
                "virtual_to_actual_ratio": virtual_entity_count / actual_data_node_count * 100 if actual_data_node_count > 0 else 0,
            },
            "group_details": {
                group: {
                    "count": count,
                    "avg_degree": sum(node_degrees.get(node["id"], 0) for node in instances["nodes"] if node.get("group") == group) / count if count > 0 else 0
                }
                for group, count in group_counts.items()
            },
            "excluded": {
                "rdf_type_triples": instance_type_triples - len(instances["nodes"]),  # 노드 생성에 사용되었지만 엣지로는 표시 안 됨
                "rdfs_label_triples": label_triples,  # 라벨에 사용되었지만 엣지로는 표시 안 됨
                "literal_triples": literal_triples,  # Literal 값은 엣지로 표시 안 됨
            }
        }
        
        result = {
            "instances": instances,
            "schema": schema,
            "stats": stats
        }
        
        # [OPTIMIZATION] 캐시 저장
        self._json_cache = result
        self._last_graph_hash = current_graph_hash
        
        return result

    def get_node_details(self, node_id: str) -> Dict[str, Any]:
        """
        특정 노드의 상세 정보(모든 속성)를 조회합니다.
        
        Args:
            node_id: 노드 ID (Local Name 또는 URI)
            
        Returns:
            속성 딕셔너리
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return {}
            
        # URI 해결
        node_uri = None
        if node_id.startswith("http"):
            node_uri = URIRef(node_id)
        else:
            # 1. Try direct namespace lookup with strict error handling
            try:
                node_uri = self.ns[node_id]
            except Exception:
                # 2. Try legacy namespace
                try:
                    node_uri = self.ns_legacy[node_id]
                except Exception:
                    # 3. Fallback: Search by Label (rdfs:label or exact match in subjects)
                    found = False
                    # Search subjects ending with node_id
                    for s in self.graph.subjects():
                        if str(s).endswith(f"/{node_id}") or str(s).endswith(f"#{node_id}"):
                            node_uri = s
                            found = True
                            break
                    
                    if not found:
                        # Search by label (Language-insensitive)
                        logger.info(f"Searching for node by label: {node_id}")
                        for s, p, o in self.graph.triples((None, None, None)):
                             # Check for label-like predicates
                             if _localname(p) in ['label', 'name', 'prefLabel', 'altLabel']:
                                 # Handle Literal values (ignore language tags)
                                 val = o.value if hasattr(o, 'value') else str(o)
                                 if val == node_id: 
                                     node_uri = s
                                     found = True
                                     logger.info(f"Found node by label: {node_uri}")
                                     break
                    
                    if not found:
                        logger.warning(f"Node ID not found in graph: {node_id}")
                        # Final check: Iterate all subjects and check endswith (slower but safer)
                        for s in self.graph.subjects():
                            if str(s).endswith(node_id):
                                node_uri = s
                                found = True
                            logger.info(f"Found node by suffix match: {node_uri}")
                            break
                    
                    # [NEW] Ultimate Fallback: Check Schema Registry (for Table Names/Class Labels)
                    if not found and hasattr(self, 'schema_registry'):
                        # 1. Exact Match
                        if node_id in self.schema_registry:
                            target_key = node_id
                        else:
                            # 2. Partial Match (reversed): e.g. "PSYOPS팀" -> User wants "PSYOPS" or similar? 
                            # Actually, usually it's the other way around: "공병대대" might be mapped to "아군부대현황" or "Engineer"
                            # Let's try to find if any key contains this node_id or vice versa
                            target_key = next((k for k in self.schema_registry if k in node_id or node_id in k), None)

                        if target_key:
                            logger.info(f"Found node in Schema Registry (fallback): {target_key}")
                            table_info = self.schema_registry[target_key]
                            return {
                                "_id": node_id,
                                "_uri": f"schema:{target_key}",
                                "type": "Class/Table",
                                "description": table_info.get("description", f"Schema Table: {target_key}"),
                                "columns": list(table_info.get("columns", {}).keys()),
                                "source": "SchemaRegistry",
                                "matched_key": target_key
                            }

                    if not found:
                             logger.error(f"Node lookup failed completely for: {node_id}")
                             return {}

        # 속성 조회
        properties = {}
        if (node_uri, None, None) not in self.graph:
             logger.warning(f"Node URI found but no triples: {node_uri}")
             return {}

        for _, p, o in self.graph.triples((node_uri, None, None)):
            p_name = _localname(p)
            
            # 값 처리
            if isinstance(o, Literal):
                value = str(o)
            elif isinstance(o, URIRef):
                value = _localname(o)
            else:
                value = str(o)
            
            if p_name in properties:
                if not isinstance(properties[p_name], list):
                    properties[p_name] = [properties[p_name]]
                properties[p_name].append(value)
            else:
                properties[p_name] = value
                
        # 기본 정보 추가
        if not properties and (node_uri, None, None) not in self.graph:
             return {"id": node_id, "error": "Node not found"}

        properties["_id"] = node_id
        properties["_uri"] = str(node_uri)
        return properties
    
    def load_graph(self, inst_path: Optional[str] = None, onto_path: Optional[str] = None, 
                   load_all_files: bool = False, enable_semantic_inference: bool = False) -> Optional[Graph]:
        """
        그래프 로드 (우선순위: instances_reasoned.ttl > instances.ttl > schema.ttl)
        
        Args:
            inst_path: 인스턴스 TTL 파일 경로 (사용되지 않음, 자동 감지)
            onto_path: 온톨로지 TTL 파일 경로 (사용되지 않음, 자동 감지)
            load_all_files: True이면 모든 관련 TTL 파일을 로드 (기본값: False, 우선순위 기반 로드)
            enable_semantic_inference: 의미 기반 추론 활성화 (미구현)
            
        Returns:
            RDF Graph 객체
        """
        if not RDFLIB_AVAILABLE:
            safe_print("[WARN] rdflib not available. Cannot load graph.")
            return None
        
        # 그래프를 완전히 새로 로드 (기존 그래프 초기화)
        self.graph = Graph()
        
        loaded_any = False
        
        # 우선순위 1: instances_reasoned.ttl (추론 결과, 최우선)
        reasoned_path = Path(self.ontology_path) / "instances_reasoned.ttl"
        if reasoned_path.exists():
            try:
                self.graph.parse(str(reasoned_path), format="turtle")
                loaded_any = True
                safe_print(f"[INFO] 추론된 인스턴스 로드: {reasoned_path}")
            except Exception as e:
                safe_print(f"[WARN] 추론된 인스턴스 로드 실패: {reasoned_path}, {e}")
        
        # 우선순위 2: instances.ttl (인스턴스 전용)
        instances_path = Path(self.ontology_path) / "instances.ttl"
        if instances_path.exists():
            try:
                self.graph.parse(str(instances_path), format="turtle")
                loaded_any = True
                safe_print(f"[INFO] 인스턴스 로드: {instances_path}")
            except Exception as e:
                safe_print(f"[WARN] 인스턴스 로드 실패: {instances_path}, {e}")
        
        # 우선순위 3: schema.ttl (스키마)
        schema_path = Path(self.ontology_path) / "schema.ttl"
        if schema_path.exists():
            try:
                self.graph.parse(str(schema_path), format="turtle")
                loaded_any = True
                safe_print(f"[INFO] 스키마 로드: {schema_path}")
            except Exception as e:
                safe_print(f"[WARN] 스키마 로드 실패: {schema_path}, {e}")
        
        # 레거시 파일 지원 (하위 호환성) - 제거됨 (Outputs Cleanup)
        if not loaded_any:
             safe_print("[INFO] 레거시 파일 로드 로직이 제거되었습니다 (k_c4i_*).")
        
        if enable_semantic_inference and loaded_any:
            safe_print("[INFO] Semantic inference is not yet implemented. Skipping.")
        
        if not loaded_any:
            safe_print("[WARN] 로드할 그래프 파일이 없습니다.")
            return None
        
        return self.graph
    
    def build_from_data(self, data: Dict[str, pd.DataFrame], force_rebuild: bool = False,
                         auto_sync_schema: bool = True) -> Optional[Graph]:
        """
        데이터프레임으로부터 온톨로지 그래프 구축 (호환성 래퍼)
        
        EnhancedOntologyManager는 generate_owl_ontology() + generate_instances()를 사용하지만,
        기존 코드와의 호환성을 위해 이 메서드를 제공합니다.
        
        Args:
            data: {테이블명: DataFrame} 딕셔너리
            force_rebuild: 캐시를 무시하고 강제로 재구축 (기본: False)
            auto_sync_schema: 스키마 레지스트리 자동 동기화 (기본: True)
            
        Returns:
            RDF Graph 객체
        """
        global _cached_graph, _cached_data_hash
        
        # 강제 재구축이면 캐시 클리어
        if force_rebuild:
            _cached_graph = None
            _cached_data_hash = None
            safe_print("[INFO] 캐시 클리어: 강제 재구축 모드")
        
        if not RDFLIB_AVAILABLE:
            safe_print("[WARN] rdflib not available. Cannot build ontology graph.")
            return None
        
        # ========== [NEW] 선행 단계: 스키마 검증 및 자동 업데이트 ==========
        if auto_sync_schema:
            try:
                safe_print("[INFO] 스키마 레지스트리 동기화 시작...")
                schema_sync_result = self._sync_schema_registry(data, auto_update=True)
                
                if schema_sync_result['has_changes']:
                    safe_print(f"[INFO] ✓ 스키마 레지스트리 업데이트 완료: {schema_sync_result['summary']}")
                    # 레지스트리 재로드
                    self.schema_registry = self._load_schema_registry()
                else:
                    safe_print(f"[INFO] ✓ 스키마 레지스트리 검증 완료: {schema_sync_result['summary']}")
            except Exception as e:
                safe_print(f"[WARN] 스키마 자동 동기화 실패 (계속 진행): {e}")
        # ==============================================================
        
        # 데이터 해시 계산 (캐싱을 위해)
        data_hash = None
        try:
            data_hash = self._calculate_data_hash(data)
            
            # 캐시된 그래프가 있고 데이터가 동일하면 재사용 (force_rebuild가 False인 경우만)
            if not force_rebuild and _cached_graph is not None and _cached_data_hash == data_hash:
                safe_print("[INFO] 캐시된 온톨로지 그래프 재사용")
                self.graph = _cached_graph
                return self.graph
        except Exception as e:
            safe_print(f"[WARN] 데이터 해시 계산 실패 (캐싱 건너뜀): {e}")
            data_hash = None
        
        # Enhanced 방식으로 그래프 생성
        # 1. OWL 온톨로지 생성 (스키마)
        graph = self.generate_owl_ontology(data)
        if not graph:
            safe_print("[WARN] OWL 온톨로지 생성 실패")
            return None
        
        # 2. 인스턴스 생성
        graph = self.generate_instances(data, enable_virtual_entities=True)
        if not graph:
            safe_print("[WARN] 인스턴스 생성 실패")
            return None
        
        # 자동으로 TTL 파일로 저장 (2단계 구조: schema.ttl + instances.ttl)
        # instances_reasoned.ttl은 필요시 별도로 생성 (성능 고려)
        self.save_graph(
            save_schema_separately=True,
            save_instances_separately=True,
            save_reasoned_separately=False,  # 기본적으로는 추론 그래프 생성 안 함 (성능 고려)
            cleanup_old_files=True,
            backup_old_files=True
        )
        
        # 캐시 저장
        try:
            _cached_graph = self.graph
            _cached_data_hash = data_hash
            safe_print("[INFO] 온톨로지 그래프 캐시 저장 완료")
        except Exception as e:
            safe_print(f"[WARN] 캐시 저장 실패: {e}")
        
        return self.graph
    
    def _calculate_data_hash(self, data: Dict[str, pd.DataFrame]) -> str:
        """
        데이터 딕셔너리의 해시 계산 (캐싱을 위해)
        
        Args:
            data: {테이블명: DataFrame} 딕셔너리
            
        Returns:
            해시 문자열
        """
        try:
            # 각 DataFrame의 해시 계산
            hash_str = ""
            for name, df in sorted(data.items()):
                # DataFrame의 내용을 문자열로 변환하여 해시 계산
                df_str = df.to_string()
                hash_str += f"{name}:{hashlib.sha1(df_str.encode('utf-8')).hexdigest()}\n"
            
            # 전체 해시 계산
            return hashlib.sha1(hash_str.encode('utf-8')).hexdigest()
        except Exception as e:
            safe_print(f"[WARN] 데이터 해시 계산 실패: {e}")
            return ""
    
    def _extract_keywords_from_condition(self, condition: str) -> List[str]:
        """
        적용조건 expression에서 키워드 추출
        예: "threat_level > 0.8" -> ["고위협"]
        예: "penetration == True" -> ["침투"]
        예: "resources < 0.5" -> ["자원부족"]
        """
        keywords = []
        condition_lower = condition.lower().strip()
        
        # 키워드 매핑 테이블
        keyword_mapping = {
            # 위협 관련
            "threat_level": "위협수준",
            "threat_level > 0.8": "고위협",
            "threat_level >= 0.8": "고위협",
            "threat_level < 0.3": "저위협",
            "threat_level <= 0.3": "저위협",
            # 침투 관련
            "penetration": "침투",
            "penetration == true": "침투",
            "penetration == True": "침투",
            # 자원 관련
            "resources": "자원",
            "resources < 0.5": "자원부족",
            "resources <= 0.5": "자원부족",
            "resource": "자원",
            # 기동 관련
            "enemy_momentum": "적기세",
            "enemy_momentum < 0.5": "적기세약화",
            "logistics_cut": "보급차단",
            "logistics_cut > 0.7": "보급차단",
            "deception": "기만",
            "deception > 0.8": "기만",
            "flank_exposed": "측면노출",
            "flank_exposed == true": "측면노출",
            "objective == 'limited'": "제한목표",
            "superiority": "우위",
            "superiority > 0.6": "우위",
            "firepower": "화력",
            "firepower > 0.8": "화력우위",
            "reserve_available": "예비대가용",
            "reserve_available == true": "예비대가용",
        }
        
        # 정확한 매칭 시도
        if condition_lower in keyword_mapping:
            keywords.append(keyword_mapping[condition_lower])
        else:
            # 부분 매칭: 변수명 추출
            import re
            # 변수명 패턴 (영문자, 언더스코어)
            var_pattern = r'\b([a-z_]+)\b'
            matches = re.findall(var_pattern, condition_lower)
            for match in matches:
                if match in keyword_mapping:
                    keywords.append(keyword_mapping[match])
                elif match not in ['and', 'or', 'not', 'true', 'false', 'level', 'available']:
                    # 일반 변수명을 한글로 변환 시도
                    var_keywords = {
                        'threat': '위협',
                        'resource': '자원',
                        'penetration': '침투',
                        'momentum': '기세',
                        'logistics': '보급',
                        'deception': '기만',
                        'flank': '측면',
                        'exposed': '노출',
                        'objective': '목표',
                        'superiority': '우위',
                        'firepower': '화력',
                        'reserve': '예비대',
                    }
                    if match in var_keywords:
                        keywords.append(var_keywords[match])
        
        # 키워드가 없으면 원본을 키워드로 사용 (최소한의 정보 보존)
        if not keywords:
            # 숫자와 연산자 제거 후 키워드 추출
            cleaned = re.sub(r'[0-9.><=!&\|()\s]+', ' ', condition)
            cleaned_keywords = [k.strip() for k in cleaned.split() if k.strip() and len(k.strip()) > 2]
            keywords.extend(cleaned_keywords[:3])  # 최대 3개
        
        return keywords if keywords else [condition[:20]]  # 최소한 원본 일부 반환
    
    def _make_uri_safe(self, name: str) -> str:
        """
        URI에 사용할 수 있도록 문자열을 변환
        공백과 특수문자를 언더스코어로 변환
        
        Args:
            name: 변환할 문자열
            
        Returns:
            URI-safe 문자열
        """
        if not name:
            return str(name) if name is not None else ""
        
        s = str(name).strip()
        # 공백 -> 언더스코어
        s = re.sub(r'\s+', '_', s)
        # URI에 위험한 특수문자 제거 (한글, 영문, 숫자는 유지)
        # 제거 대상: ( ) { } [ ] < > | \ ^ ` " ' : ; , ? # % & + =
        s = re.sub(r'[(){}\[\]<>|\\^`"\':;,?#%&+=]', '', s)
        
        # 연속된 언더스코어 정리
        s = re.sub(r'_+', '_', s)
        s = s.strip('_')
        
        # 빈 문자열이면 default 반환
        if not s:
            return "unknown"
            
        return s
    
    def get_sparql_template(self, template_name: str, **kwargs) -> str:
        """
        SPARQL 쿼리 템플릿 가져오기
        
        Args:
            template_name: 템플릿 이름 (find_suitable_coas, find_related_threats 등)
            **kwargs: 템플릿 변수 (top_k, situation_uri 등)
            
        Returns:
            완성된 SPARQL 쿼리 문자열
        """
        try:
            import yaml
            from pathlib import Path
            
            template_path = Path(__file__).parent.parent / "config" / "sparql_templates.yaml"
            
            if not template_path.exists():
                safe_print(f"[WARN] SPARQL template file not found: {template_path}")
                return ""
            
            with open(template_path, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
            
            template = templates.get(template_name, "")
            
            if not template:
                safe_print(f"[WARN] SPARQL template '{template_name}' not found")
                return ""
            
            # 템플릿 변수 치환
            # URI 변환
            if 'situation_uri' in kwargs:
                situation_uri = kwargs['situation_uri']
                if isinstance(situation_uri, str):
                    # URI 형식으로 변환
                    if not situation_uri.startswith('http://'):
                        # 안전한 URI로 변환
                        situation_uri = self._make_uri_safe(situation_uri)
                        situation_uri = URIRef(self.ns[situation_uri])
                    else:
                        situation_uri = URIRef(situation_uri)
                template = template.replace('?situation_uri', f'<{situation_uri}>')
            
            if 'coa_uri' in kwargs:
                coa_uri = kwargs['coa_uri']
                if isinstance(coa_uri, str):
                    if not coa_uri.startswith('http://'):
                        # 안전한 URI로 변환
                        coa_uri = self._make_uri_safe(coa_uri)
                        coa_uri = URIRef(self.ns[coa_uri])
                    else:
                        coa_uri = URIRef(coa_uri)
                template = template.replace('?coa_uri', f'<{coa_uri}>')
            
            # 기타 변수 치환
            for key, value in kwargs.items():
                if key not in ['situation_uri', 'coa_uri']:
                    template = template.replace(f'{{{key}}}', str(value))
            
            return template
            
        except Exception as e:
            safe_print(f"[WARN] Failed to load SPARQL template: {e}")
            return ""
    
    def execute_template_query(self, template_name: str, **kwargs) -> Union[List[Dict], pd.DataFrame]:
        """
        SPARQL 템플릿 쿼리 실행
        
        Args:
            template_name: 템플릿 이름
            **kwargs: 템플릿 변수 및 return_format
            
        Returns:
            쿼리 결과 (리스트 또는 DataFrame)
        """
        return_format = kwargs.pop('return_format', 'list')
        
        query_str = self.get_sparql_template(template_name, **kwargs)
        if not query_str:
            return [] if return_format == 'list' else pd.DataFrame()
        
        return self.query(query_str, return_format=return_format)
    
    def add_relationship(self, source_node_id: str, target_node_id: str, 
                       relation_name: str) -> bool:
        """
        제안된 관계를 그래프에 추가
        
        Args:
            source_node_id: 소스 노드 ID (예: "임무정보_MSN001")
            target_node_id: 타겟 노드 ID (예: "전장축선_AXIS001")
            relation_name: 관계명 (예: "relatedTo", "hasMission")
        
        Returns:
            성공 여부
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return False
        
        try:
            # URI 생성
            source_uri = URIRef(self.ns[source_node_id])
            target_uri = URIRef(self.ns[target_node_id])
            relation_uri = URIRef(self.ns[relation_name])
            
            # 이미 관계가 있는지 확인
            if (source_uri, relation_uri, target_uri) in self.graph:
                safe_print(f"[INFO] 관계가 이미 존재합니다: {source_node_id} -[{relation_name}]-> {target_node_id}")
                return True
            
            # 관계 추가
            self.graph.add((source_uri, relation_uri, target_uri))
            
            # 관계명이 OWL ObjectProperty로 정의되어 있는지 확인하고 없으면 추가
            if (relation_uri, RDF.type, OWL.ObjectProperty) not in self.graph:
                self.graph.add((relation_uri, RDF.type, OWL.ObjectProperty))
                safe_print(f"[INFO] 새로운 관계 Property 생성: {relation_name}")
            
            safe_print(f"[INFO] 관계 추가 완료: {source_node_id} -[{relation_name}]-> {target_node_id}")
            return True
        except Exception as e:
            safe_print(f"[ERROR] 관계 추가 실패: {e}")
            return False
    
    def add_relationships_batch(self, relationships: List[Dict]) -> Dict[str, int]:
        """
        여러 관계를 일괄 추가
        
        Args:
            relationships: [{"source": "...", "target": "...", "relation": "..."}, ...]
        
        Returns:
            {"success": 성공 수, "failed": 실패 수}
        """
        success_count = 0
        failed_count = 0
        
        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")
            relation = rel.get("relation", "relatedTo")
            
            if self.add_relationship(source, target, relation):
                success_count += 1
            else:
                failed_count += 1
        
        return {"success": success_count, "failed": failed_count}
    
    def remove_relationship(self, source_node_id: str, target_node_id: str, 
                           relation_name: str) -> bool:
        """
        관계 삭제
        
        Args:
            source_node_id: 소스 노드 ID
            target_node_id: 타겟 노드 ID
            relation_name: 관계명
        
        Returns:
            성공 여부
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return False
        
        try:
            source_uri = URIRef(self.ns[source_node_id])
            target_uri = URIRef(self.ns[target_node_id])
            relation_uri = URIRef(self.ns[relation_name])
            
            # 관계가 존재하는지 확인
            if (source_uri, relation_uri, target_uri) not in self.graph:
                safe_print(f"[WARN] 삭제할 관계가 존재하지 않습니다: {source_node_id} -[{relation_name}]-> {target_node_id}")
                return False
            
            # 관계 삭제
            self.graph.remove((source_uri, relation_uri, target_uri))
            safe_print(f"[INFO] 관계 삭제 완료: {source_node_id} -[{relation_name}]-> {target_node_id}")
            return True
        except Exception as e:
            safe_print(f"[ERROR] 관계 삭제 실패: {e}")
            return False
    
    def update_relationship(self, source_node_id: str, target_node_id: str,
                           old_relation_name: str, new_relation_name: str,
                           new_target_node_id: Optional[str] = None) -> bool:
        """
        관계 수정 (관계명 변경 또는 타겟 노드 변경)
        
        Args:
            source_node_id: 소스 노드 ID
            target_node_id: 기존 타겟 노드 ID
            old_relation_name: 기존 관계명
            new_relation_name: 새로운 관계명
            new_target_node_id: 새로운 타겟 노드 ID (선택적, None이면 타겟 노드는 변경 안 함)
        
        Returns:
            성공 여부
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return False
        
        try:
            # 기존 관계 삭제
            if not self.remove_relationship(source_node_id, target_node_id, old_relation_name):
                return False
            
            # 새로운 타겟 노드 결정
            final_target = new_target_node_id if new_target_node_id else target_node_id
            
            # 새로운 관계 추가
            if not self.add_relationship(source_node_id, final_target, new_relation_name):
                # 실패 시 기존 관계 복구 시도
                self.add_relationship(source_node_id, target_node_id, old_relation_name)
                return False
            
            safe_print(f"[INFO] 관계 수정 완료: {source_node_id} -[{old_relation_name}]-> {target_node_id} → -[{new_relation_name}]-> {final_target}")
            return True
        except Exception as e:
            safe_print(f"[ERROR] 관계 수정 실패: {e}")
            return False
    
    def get_all_relationships(self, source_node_id: Optional[str] = None,
                            target_node_id: Optional[str] = None,
                            relation_name: Optional[str] = None) -> List[Dict]:
        """
        관계 조회
        
        Args:
            source_node_id: 소스 노드 ID (선택적, 필터링)
            target_node_id: 타겟 노드 ID (선택적, 필터링)
            relation_name: 관계명 (선택적, 필터링)
        
        Returns:
            [{"source": "...", "target": "...", "relation": "...", "source_label": "...", "target_label": "..."}, ...]
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return []
        
        relationships = []
        
        try:
            # 필터링 조건 설정
            source_uri = URIRef(self.ns[source_node_id]) if source_node_id else None
            target_uri = URIRef(self.ns[target_node_id]) if target_node_id else None
            relation_uri = URIRef(self.ns[relation_name]) if relation_name else None
            
            # 그래프에서 관계 조회
            if source_uri:
                # 특정 소스 노드의 outgoing 관계
                for _, p, o in self.graph.triples((source_uri, None, None)):
                    if isinstance(o, URIRef):
                        if target_uri and o != target_uri:
                            continue
                        if relation_uri and p != relation_uri:
                            continue
                        
                        source_local = _localname(source_uri)
                        target_local = _localname(o)
                        relation_local = _localname(p)
                        
                        # 라벨 가져오기
                        source_label = self._get_node_label(source_uri)
                        target_label = self._get_node_label(o)
                        
                        relationships.append({
                            "source": source_local,
                            "target": target_local,
                            "relation": relation_local,
                            "source_label": source_label,
                            "target_label": target_label
                        })
            elif target_uri:
                # 특정 타겟 노드의 incoming 관계
                for s, p, _ in self.graph.triples((None, None, target_uri)):
                    if isinstance(s, URIRef):
                        if relation_uri and p != relation_uri:
                            continue
                        
                        source_local = _localname(s)
                        target_local = _localname(target_uri)
                        relation_local = _localname(p)
                        
                        source_label = self._get_node_label(s)
                        target_label = self._get_node_label(target_uri)
                        
                        relationships.append({
                            "source": source_local,
                            "target": target_local,
                            "relation": relation_local,
                            "source_label": source_label,
                            "target_label": target_label
                        })
            else:
                # 모든 관계 조회
                for s, p, o in self.graph.triples((None, None, None)):
                    if isinstance(o, URIRef) and str(s).startswith(str(self.ns_legacy)) and str(o).startswith(str(self.ns_legacy)):
                        if relation_uri and p != relation_uri:
                            continue
                        
                        source_local = _localname(s)
                        target_local = _localname(o)
                        relation_local = _localname(p)
                        
                        source_label = self._get_node_label(s)
                        target_label = self._get_node_label(o)
                        
                        relationships.append({
                            "source": source_local,
                            "target": target_local,
                            "relation": relation_local,
                            "source_label": source_label,
                            "target_label": target_label
                        })
            
            return relationships
        except Exception as e:
            safe_print(f"[ERROR] 관계 조회 실패: {e}")
            return []
    
    def _get_node_label(self, node_uri: URIRef) -> str:
        """노드의 라벨 가져오기"""
        try:
            for _, _, label in self.graph.triples((node_uri, RDFS.label, None)):
                return str(label)
            # 라벨이 없으면 local name 반환
            return _localname(node_uri)
        except Exception:
            return _localname(node_uri)
    
    def search_relationships(self, query: str, search_in_labels: bool = True) -> List[Dict]:
        """
        관계 검색 (노드 ID, 라벨, 관계명으로 검색)
        
        Args:
            query: 검색어
            search_in_labels: 라벨에서도 검색할지 여부
        
        Returns:
            검색된 관계 목록
        """
        if not query:
            return []
        
        query_lower = query.lower()
        all_relationships = self.get_all_relationships()
        matched = []
        
        for rel in all_relationships:
            # 소스 노드 ID/라벨 검색
            if query_lower in rel.get("source", "").lower():
                matched.append(rel)
                continue
            
            if search_in_labels and query_lower in rel.get("source_label", "").lower():
                matched.append(rel)
                continue
            
            # 타겟 노드 ID/라벨 검색
            if query_lower in rel.get("target", "").lower():
                matched.append(rel)
                continue
            
            if search_in_labels and query_lower in rel.get("target_label", "").lower():
                matched.append(rel)
                continue
            
            # 관계명 검색
            if query_lower in rel.get("relation", "").lower():
                matched.append(rel)
                continue
        
        return matched

    def get_entity_properties(self, entity_id: str) -> Dict[str, str]:
        """
        특정 엔티티의 모든 데이터형 속성(DatatypeProperty) 조회
        
        Args:
            entity_id: 엔티티 ID (예: TERR003, THR001)
            
        Returns:
            {프로퍼티명: 값} 딕셔너리
        """
        if not RDFLIB_AVAILABLE or self.graph is None:
            return {}
            
        # URI 생성 시도 (ns[entity_id] 또는 ns[메이크_URI_safe(entity_id)])
        # instances.ttl에 저장된 형식을 고려하여 여러 패턴 시도
        candidates = [
            URIRef(self.ns[entity_id]),
            URIRef(self.ns[self._make_uri_safe(entity_id)])
        ]
        
        # 지형셀_ID 등의 접두어가 붙은 경우도 고려
        prefixes = ["지형셀_", "위협_", "아군부대_", "적군부대_"]
        for p in prefixes:
            candidates.append(URIRef(self.ns[f"{p}{entity_id}"]))
            candidates.append(URIRef(self.ns[self._make_uri_safe(f"{p}{entity_id}")]))
            
        properties = {}
        target_uri = None
        
        # 실제 존재하는 URI 찾기
        for uri in candidates:
            if (uri, RDF.type, None) in self.graph:
                target_uri = uri
                break
        
        if not target_uri:
            return {}
            
        # 해당 URI의 모든 속성 조회
        for _, p, o in self.graph.triples((target_uri, None, None)):
            if isinstance(o, Literal):
                p_name = _localname(p)
                properties[p_name] = str(o)
                
        return properties

    def get_coordinates(self, entity_id: str) -> Optional[tuple]:
        """
        특정 엔티티의 온톨로지 기반 좌표(위경도) 조회
        
        Args:
            entity_id: 엔티티 ID (예: TERR003)
            
        Returns:
            (latitude, longitude) 튜플 또는 None
        """
        props = self.get_entity_properties(entity_id)
        if not props:
            return None
            
        # 1. 명시적 위경도 필드 확인 (ns:hasLatitude, ns:hasLongitude)
        lat = props.get("hasLatitude")
        lng = props.get("hasLongitude")
        
        if lat and lng:
            try:
                return float(lat), float(lng)
            except ValueError:
                pass
                
        # 2. 통합 좌표정보 필드 확인 (ns:좌표정보 - "lng, lat" 형식)
        coord_info = props.get("좌표정보")
        if coord_info and "," in coord_info:
            try:
                parts = [p.strip() for p in coord_info.split(",")]
                if len(parts) >= 2:
                    # 엑셀 데이터상 127.0, 37.9 (lng, lat) 순서임을 고려
                    return float(parts[1]), float(parts[0])
            except (ValueError, IndexError):
                pass
                
        return None


