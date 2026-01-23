# agents/ccir_recommendation_agent/logic_ccir.py
# -*- coding: utf-8 -*-
"""
CCIR Recommendation Agent Logic
중요정보요구(CCIR) 추천 에이전트의 핵심 로직

주요 기능:
1. 정보요구 접수: 핵심정보 자동 분류 (PIR, FFIR, EEFI)
2. 첩보수집 계획: 적합 자산 자동 추천
3. 요청관리: 자동 요약·경보
4. 상황 변화: Dynamic CCIR 갱신
"""
import os
import sys
import pandas as pd
import yaml
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'core_pipeline'))
sys.path.insert(0, os.path.join(BASE_DIR, 'agents'))
sys.path.insert(0, os.path.join(BASE_DIR, 'config'))

from agents.base_agent import BaseAgent


class CCIRRecommendationAgent(BaseAgent):
    """중요정보요구(CCIR) 추천 에이전트"""
    
    def __init__(self, core, config: Optional[Dict] = None):
        """
        Args:
            core: CorePipeline 인스턴스
            config: Agent별 설정 딕셔너리 (선택적)
        """
        super().__init__(core, config)
        self.name = "CCIRRecommendationAgent"
        
        # CCIR 규칙 로드
        self.ccir_rules = self._load_ccir_rules()
        
        # CCIR 요청 히스토리 (동적 갱신을 위해)
        self.ccir_history = []
    
    def _load_ccir_rules(self) -> Dict:
        """CCIR 규칙 파일 로드"""
        rules_path = os.path.join(
            BASE_DIR,
            "agents",
            "ccir_recommendation_agent",
            "rules_ccir.yaml"
        )
        
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"[WARN] Failed to load CCIR rules: {e}")
            return {}
    
    def execute_reasoning(
        self,
        information_request: Optional[str] = None,
        situation_id: Optional[str] = None,
        threat_level: Optional[float] = None,
        **kwargs
    ) -> Dict:
        """
        CCIR 추천 추론 실행
        
        Args:
            information_request: 정보 요구 내용 (선택적)
            situation_id: 상황 ID (선택적)
            threat_level: 위협 수준 (0-1, 선택적)
            **kwargs: 추가 인자
                - enable_rag_search: RAG 검색 활성화 (기본: True)
                - enable_dynamic_update: 동적 갱신 활성화 (기본: True)
        
        Returns:
            실행 결과 딕셔너리
        """
        try:
            # 1단계: 정보요구 접수 및 분류
            classification_result = self._classify_information_request(
                information_request or "정보 요구 없음"
            )
            
            # 2단계: 첩보수집 계획 (적합 자산 추천)
            asset_recommendation = self._recommend_collection_assets(
                classification_result,
                threat_level
            )
            
            # 3단계: 요청관리 (자동 요약·경보)
            request_management = self._manage_request(
                classification_result,
                asset_recommendation,
                threat_level
            )
            
            # 4단계: 상황 변화 감지 및 동적 갱신
            dynamic_update = None
            if kwargs.get("enable_dynamic_update", True):
                dynamic_update = self._check_dynamic_update(
                    situation_id,
                    threat_level
                )
            
            # 컨텍스트 구성
            context = {
                "classification": classification_result,
                "asset_recommendation": asset_recommendation,
                "request_management": request_management,
                "dynamic_update": dynamic_update,
                "situation_id": situation_id,
                "threat_level": threat_level,
                "graph": self.core.ontology_manager.graph if hasattr(self.core.ontology_manager, 'graph') else None,
                "ontology_manager": self.core.ontology_manager
            }
            
            # CCIR 규칙 실행
            raw_result = self.core.reasoning_engine.run_ccir_rules(context)
            
            # LLM을 사용한 요약
            summary = self._generate_summary(raw_result, context)
            
            # 결과 구성
            result = {
                "agent": self.name,
                "status": "completed",
                "situation_id": situation_id,
                "raw_result": raw_result,
                "summary": summary,
                "classification": classification_result,
                "asset_recommendation": asset_recommendation,
                "request_management": request_management,
                "dynamic_update": dynamic_update,
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            # 히스토리에 추가
            self.ccir_history.append({
                "timestamp": datetime.now(),
                "situation_id": situation_id,
                "result": result
            })
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "agent": self.name,
                "status": "failed",
                "error": str(e),
                "summary": f"에러 발생: {str(e)}"
            }
    
    def _classify_information_request(self, request: str) -> Dict:
        """
        1단계: 정보요구 접수 및 핵심정보 자동 분류
        
        Args:
            request: 정보 요구 내용
            
        Returns:
            분류 결과 (PIR, FFIR, EEFI)
        """
        classification_rules = self.ccir_rules.get("ccir_classification", {})
        
        # 키워드 기반 분류
        request_lower = request.lower()
        
        scores = {
            "PIR": 0.0,
            "FFIR": 0.0,
            "EEFI": 0.0
        }
        
        # 각 카테고리별 키워드 매칭
        for category_key, category_info in classification_rules.items():
            category = category_info.get("category", "")
            keywords = category_info.get("keywords", [])
            
            for keyword in keywords:
                if keyword.lower() in request_lower:
                    scores[category] += 1.0
        
        # 정규화
        total_score = sum(scores.values())
        if total_score > 0:
            scores = {k: v / total_score for k, v in scores.items()}
        
        # 최고 점수 카테고리 결정
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        
        # RAG 검색으로 추가 컨텍스트 확보 (선택적)
        rag_context = []
        if self.core.rag_manager.is_available():
            try:
                rag_results = self.core.rag_manager.retrieve_with_context(
                    request,
                    top_k=3
                )
                rag_context = rag_results
            except Exception:
                pass
        
        return {
            "category": best_category,
            "confidence": round(confidence, 2),
            "scores": {k: round(v, 2) for k, v in scores.items()},
            "priority": classification_rules.get(
                best_category.lower(),
                {}
            ).get("priority", 3),
            "rag_context": rag_context
        }
    
    def _recommend_collection_assets(
        self,
        classification: Dict,
        threat_level: Optional[float]
    ) -> Dict:
        """
        2단계: 첩보수집 계획 - 적합 자산 자동 추천
        
        Args:
            classification: 분류 결과
            threat_level: 위협 수준
            
        Returns:
            자산 추천 결과
        """
        asset_rules = self.ccir_rules.get("asset_recommendation", {})
        asset_types = asset_rules.get("asset_types", [])
        
        category = classification.get("category", "PIR")
        recommended_assets = []
        
        # 카테고리에 적합한 자산 필터링
        for asset in asset_types:
            suitable_for = asset.get("suitable_for", [])
            if category in suitable_for:
                # 위협 수준에 따른 점수 조정
                base_score = asset.get("capability_score", 0.5)
                
                if threat_level is not None:
                    # 위협 수준이 높을수록 점수 증가
                    adjusted_score = base_score * (0.7 + 0.3 * threat_level)
                else:
                    adjusted_score = base_score
                
                recommended_assets.append({
                    "name": asset.get("name", ""),
                    "suitability_score": round(adjusted_score, 2),
                    "coverage": asset.get("coverage", ""),
                    "category": category
                })
        
        # 적합성 점수 순으로 정렬
        recommended_assets.sort(
            key=lambda x: x["suitability_score"],
            reverse=True
        )
        
        # 온톨로지에서 실제 자산 정보 조회 (선택적)
        ontology_assets = []
        if hasattr(self.core.ontology_manager, 'graph') and self.core.ontology_manager.graph:
            try:
                # 그래프에서 직접 자산 정보 조회
                graph = self.core.ontology_manager.graph
                ns = self.core.ontology_manager.ns
                
                # Type 속성을 가진 모든 리소스 탐색
                for s, p, o in graph.triples((None, ns.Type, None)):
                    # Capability 속성도 조회
                    capabilities = list(graph.objects(s, ns.Capability))
                    if capabilities:
                        ontology_assets.append({
                            "name": str(s).split("#")[-1],
                            "type": str(o).split("#")[-1],
                            "capability": str(capabilities[0]).split("#")[-1]
                        })
                    
                    if len(ontology_assets) >= 10:
                        break
            except Exception as e:
                print(f"[WARN] 온톨로지 자산 조회 실패: {e}")
        
        return {
            "recommended_assets": recommended_assets[:5],  # 상위 5개
            "total_assets": len(recommended_assets),
            "ontology_assets": ontology_assets,
            "category": category
        }
    
    def _manage_request(
        self,
        classification: Dict,
        asset_recommendation: Dict,
        threat_level: Optional[float]
    ) -> Dict:
        """
        3단계: 요청관리 - 자동 요약·경보
        
        Args:
            classification: 분류 결과
            asset_recommendation: 자산 추천 결과
            threat_level: 위협 수준
            
        Returns:
            요청 관리 결과
        """
        management_rules = self.ccir_rules.get("request_management", {})
        priority_criteria = management_rules.get("priority_criteria", {})
        alert_thresholds = management_rules.get("alert_thresholds", {})
        
        # 우선순위 점수 계산
        priority_score = 0.0
        
        # 위협 수준 기여도
        if threat_level is not None:
            priority_score += threat_level * priority_criteria.get("threat_level", 0.4)
        
        # 분류 신뢰도 기여도
        confidence = classification.get("confidence", 0.5)
        priority_score += confidence * priority_criteria.get("timeliness", 0.3)
        
        # 정보 갭 기여도 (간단히 자산 추천 수로 대체)
        asset_count = len(asset_recommendation.get("recommended_assets", []))
        info_gap = 1.0 - (asset_count / 10.0)  # 자산이 적을수록 갭 큼
        priority_score += info_gap * priority_criteria.get("information_gap", 0.2)
        
        # 우선순위 결정
        if priority_score >= alert_thresholds.get("high_priority", 0.8):
            priority = "HIGH"
            alert = True
        elif priority_score >= alert_thresholds.get("medium_priority", 0.5):
            priority = "MEDIUM"
            alert = False
        else:
            priority = "LOW"
            alert = False
        
        # 자동 요약 생성
        summary = self._generate_request_summary(
            classification,
            asset_recommendation,
            priority_score
        )
        
        return {
            "priority": priority,
            "priority_score": round(priority_score, 2),
            "alert": alert,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_request_summary(
        self,
        classification: Dict,
        asset_recommendation: Dict,
        priority_score: float
    ) -> str:
        """요청 자동 요약 생성"""
        category = classification.get("category", "UNKNOWN")
        assets = asset_recommendation.get("recommended_assets", [])
        top_assets = [a["name"] for a in assets[:3]]
        
        summary = f"""
[CCIR 요약]
- 분류: {category} (신뢰도: {classification.get('confidence', 0.0):.2f})
- 우선순위 점수: {priority_score:.2f}
- 추천 자산: {', '.join(top_assets) if top_assets else '없음'}
- 총 자산 수: {len(assets)}
        """.strip()
        
        # LLM을 사용한 요약 (선택적)
        if self.core.llm_manager.is_available():
            try:
                prompt = f"다음 CCIR 요청을 간결하게 요약하세요:\n{summary}\n---\n요약:"
                llm_summary = self.core.llm_manager.generate(prompt, max_tokens=100)
                if llm_summary:
                    summary = llm_summary
            except Exception:
                pass
        
        return summary
    
    def _check_dynamic_update(
        self,
        situation_id: Optional[str],
        threat_level: Optional[float]
    ) -> Dict:
        """
        4단계: 상황 변화 감지 및 동적 갱신
        
        Args:
            situation_id: 상황 ID
            threat_level: 현재 위협 수준
            
        Returns:
            동적 갱신 결과
        """
        update_rules = self.ccir_rules.get("dynamic_update", {})
        update_triggers = update_rules.get("update_triggers", [])
        
        needs_update = False
        update_reasons = []
        
        # 히스토리에서 이전 상황 확인
        if self.ccir_history and situation_id:
            last_result = None
            for entry in reversed(self.ccir_history):
                if entry.get("situation_id") == situation_id:
                    last_result = entry.get("result")
                    break
            
            if last_result:
                last_threat = last_result.get("raw_result", {}).get("threat_level")
                
                # 위협 수준 변화 확인
                if threat_level is not None and last_threat is not None:
                    threat_change = abs(threat_level - last_threat)
                    threshold = update_triggers[0].get("threat_level_change", 0.1)
                    
                    if threat_change >= threshold:
                        needs_update = True
                        update_reasons.append(
                            f"위협 수준 변화: {last_threat:.2f} → {threat_level:.2f} "
                            f"(변화량: {threat_change:.2f})"
                        )
        
        # 시간 경과 확인
        if self.ccir_history:
            last_entry = self.ccir_history[-1]
            last_time = last_entry.get("timestamp")
            if isinstance(last_time, datetime):
                time_elapsed = (datetime.now() - last_time).total_seconds()
                threshold = update_triggers[-1].get("time_elapsed", 3600)
                
                if time_elapsed >= threshold:
                    needs_update = True
                    update_reasons.append(
                        f"시간 경과: {time_elapsed/60:.1f}분 (임계값: {threshold/60:.1f}분)"
                    )
        
        # 갱신 빈도 결정
        update_frequency = None
        if needs_update:
            frequency_rules = update_rules.get("update_frequency", {})
            # 우선순위에 따라 갱신 빈도 결정 (간단한 구현)
            if threat_level and threat_level > 0.7:
                update_frequency = frequency_rules.get("high_priority", 300)
            elif threat_level and threat_level > 0.4:
                update_frequency = frequency_rules.get("medium_priority", 1800)
            else:
                update_frequency = frequency_rules.get("low_priority", 3600)
        
        return {
            "needs_update": needs_update,
            "update_reasons": update_reasons,
            "update_frequency": update_frequency,
            "last_update": self.ccir_history[-1].get("timestamp").isoformat() if self.ccir_history else None
        }
    
    def _generate_summary(self, raw_result: Dict, context: Dict) -> str:
        """결과 요약 생성"""
        classification = context.get("classification", {})
        asset_rec = context.get("asset_recommendation", {})
        request_mgmt = context.get("request_management", {})
        
        summary_parts = [
            f"CCIR 분류: {classification.get('category', 'UNKNOWN')} "
            f"(신뢰도: {classification.get('confidence', 0.0):.2f})",
            f"우선순위: {request_mgmt.get('priority', 'UNKNOWN')} "
            f"(점수: {request_mgmt.get('priority_score', 0.0):.2f})",
            f"추천 자산: {len(asset_rec.get('recommended_assets', []))}개"
        ]
        
        # LLM을 사용한 요약 (선택적)
        if self.core.llm_manager.is_available():
            try:
                result_text = "\n".join(summary_parts)
                prompt = f"다음 CCIR 추천 결과를 요약하세요:\n{result_text}\n---\n요약:"
                llm_summary = self.core.llm_manager.generate(prompt, max_tokens=128)
                if llm_summary:
                    return llm_summary
            except Exception:
                pass
        
        return " | ".join(summary_parts)


if __name__ == "__main__":
    # 테스트용 실행
    from core_pipeline.orchestrator import CorePipeline
    config = {"data_paths": {}, "ontology_path": "./knowledge/ontology"}
    core = CorePipeline(config)
    core.initialize()
    
    agent = CCIRRecommendationAgent(core=core)
    result = agent.execute_reasoning(
        information_request="적군의 이동 경로와 규모 파악 필요",
        threat_level=0.8
    )
    print(f"\n결과: {result}")












