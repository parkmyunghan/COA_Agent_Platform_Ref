# ui/components/ontology_cop_mapper.py
# -*- coding: utf-8 -*-
"""
Ontology-aware COP Mapper
온톨로지 기반 COA 추천 결과를 COP 표시용 데이터로 변환
"""
from typing import Dict, List, Optional, Any
from ui.components.scenario_mapper import ScenarioMapper

class OntologyCOPMapper:
    """온톨로지 인식 COP 매퍼"""
    
    @staticmethod
    def map_coa_recommendations_to_cop_data(
        coa_evaluations: List[Any],
        threat_data: Optional[Dict] = None,
        unit_data: Optional[Dict] = None,
        ontology_manager=None
    ) -> Dict:
        """
        COA 평가 결과를 COP 표시용 데이터로 변환
        
        Args:
            coa_evaluations: COAEvaluationResult 리스트
            threat_data: 위협 GeoJSON 데이터
            unit_data: 부대 GeoJSON 데이터
            ontology_manager: 온톨로지 매니저 (추론 경로 조회용)
        
        Returns:
            COP 표시용 데이터 딕셔너리
        """
        cop_recommendations = []
        
        for eval_result in coa_evaluations:
            coa = eval_result.coa if hasattr(eval_result, 'coa') else None
            if not coa:
                continue
            
            # COA 정보 추출
            coa_info = {
                "coa_id": getattr(coa, 'coa_id', ''),
                "coa_name": getattr(coa, 'coa_name', getattr(coa, 'name', 'Unknown')),
                "coa_type": getattr(coa, 'coa_type', 'unknown'),
                "coa_uri": getattr(coa, 'coa_uri', None),
                "total_score": eval_result.total_score if hasattr(eval_result, 'total_score') else 0.0,
                "description": getattr(coa, 'description', ''),
                "path": [],  # 기동 경로 (나중에 채움)
                "participating_units": [],
                "exposed_threats": [],
                "success_probability": 0.0,
                "estimated_losses": 0,
                "reasoning": []
            }
            
            # 점수 세부 정보
            if hasattr(eval_result, 'breakdown'):
                coa_info["breakdown"] = eval_result.breakdown
            
            # 추론 근거
            if hasattr(eval_result, 'reasoning_log'):
                coa_info["reasoning"] = eval_result.reasoning_log
            elif hasattr(eval_result, 'reasoning'):
                coa_info["reasoning"] = eval_result.reasoning
            
            # 온톨로지에서 추론 경로 조회
            if ontology_manager and coa_info["coa_uri"]:
                reasoning_path = OntologyCOPMapper._get_reasoning_path(
                    ontology_manager,
                    coa_info["coa_uri"],
                    threat_data
                )
                if reasoning_path:
                    coa_info["ontology_reasoning_path"] = reasoning_path
            
            cop_recommendations.append(coa_info)
        
        return {
            "coaRecommendations": cop_recommendations,
            "threatData": threat_data or {"type": "FeatureCollection", "features": []},
            "unitData": unit_data or {"type": "FeatureCollection", "features": []}
        }
    
    @staticmethod
    def _get_reasoning_path(
        ontology_manager,
        coa_uri: str,
        threat_data: Optional[Dict] = None
    ) -> Optional[List[Dict]]:
        """
        온톨로지에서 COA 추론 경로 조회
        
        Args:
            ontology_manager: 온톨로지 매니저
            coa_uri: COA URI
            threat_data: 위협 데이터 (위협 URI 추출용)
        
        Returns:
            추론 경로 리스트
        """
        if not ontology_manager or not hasattr(ontology_manager, 'query'):
            return None
        
        try:
            # 위협 URI 추출
            threat_uris = []
            if threat_data and threat_data.get("features"):
                for feature in threat_data["features"]:
                    threat_uri = feature.get("properties", {}).get("threat_uri")
                    if threat_uri:
                        threat_uris.append(threat_uri)
            
            # 직접 그래프 조회로 추론 경로 탐색
            if threat_uris:
                from rdflib import URIRef, RDF
                coa_node = URIRef(coa_uri)
                ns = ontology_manager.ns
                
                results = []
                for p, o in ontology_manager.graph.predicate_objects(coa_node):
                    if isinstance(o, URIRef) and str(o) in threat_uris:
                        # ns:Threat 타입이거나 관련 클래스인지 확인 (간소화)
                        results.append({
                            'coa': coa_uri,
                            'relation': str(p),
                            'threat': str(o)
                        })
                
                if results:
                    return results
        except Exception as e:
            print(f"[WARN] 추론 경로 조회 실패: {e}")
        
        return None
    
    @staticmethod
    def enhance_threat_data_with_ontology(
        threat_geojson: Dict,
        ontology_manager=None
    ) -> Dict:
        """
        위협 GeoJSON 데이터에 온톨로지 정보 추가
        
        Args:
            threat_geojson: 위협 GeoJSON
            ontology_manager: 온톨로지 매니저
        
        Returns:
            향상된 위협 GeoJSON
        """
        if not threat_geojson or not threat_geojson.get("features"):
            return threat_geojson
        
        enhanced_features = []
        for feature in threat_geojson["features"]:
            props = feature.get("properties", {})
            
            # 온톨로지에서 위협 정보 조회
            threat_uri = props.get("threat_uri")
            if threat_uri and ontology_manager:
                threat_info = OntologyCOPMapper._get_threat_info_from_ontology(
                    ontology_manager,
                    threat_uri
                )
                if threat_info:
                    props.update(threat_info)
            
            enhanced_features.append({
                **feature,
                "properties": props
            })
        
        return {
            **threat_geojson,
            "features": enhanced_features
        }
    
    @staticmethod
    def _get_threat_info_from_ontology(
        ontology_manager,
        threat_uri: str
    ) -> Optional[Dict]:
        """온톨로지에서 위협 정보 조회"""
        if not ontology_manager or not hasattr(ontology_manager, 'query'):
            return None
        
        try:
            from rdflib import URIRef, RDF, RDFS
            threat_node = URIRef(threat_uri)
            ns = ontology_manager.ns
            
            # 타입 조회
            types = list(ontology_manager.graph.objects(threat_node, RDF.type))
            type_uri = types[0] if types else None
            
            # 확신도 조회
            confidences = list(ontology_manager.graph.objects(threat_node, ns.confidence))
            confidence = float(confidences[0]) if confidences else 0.5
            
            # 대응 COA 조회
            affected_coas = []
            for coa, p, o in ontology_manager.graph.triples((None, ns.countersThreat, threat_node)):
                labels = list(ontology_manager.graph.objects(coa, RDFS.label))
                if labels:
                    affected_coas.append(str(labels[0]))
            
            return {
                "threat_type": str(type_uri).split("#")[-1] if type_uri else None,
                "confidence": confidence,
                "affected_coa": affected_coas
            }
        except Exception as e:
            print(f"[WARN] 위협 정보 조회 실패: {e}")
        
        return None



















