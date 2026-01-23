from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
from api.dependencies import get_orchestrator, get_coa_service, get_global_state
from core_pipeline.orchestrator import Orchestrator
from core_pipeline.axis_state_builder import AxisStateBuilder
from core_pipeline.coa_service import COAService
from api.schemas import COAResponse, COAGenerationRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

class AgentExecutionRequest(BaseModel):
    agent_class_path: str = "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent"
    situation_id: Optional[str] = None
    situation_info: Optional[Dict[str, Any]] = None
    use_palantir_mode: bool = True
    enable_rag_search: bool = True
    coa_type_filter: Optional[List[str]] = None
    user_params: Optional[Dict[str, Any]] = None

def convert_agent_result_to_coa_response(agent_result: Dict) -> Dict:
    """
    Agent 실행 결과를 COAResponse 형식으로 변환
    
    Args:
        agent_result: Agent.execute_reasoning()의 결과
        
    Returns:
        COAResponse 형식의 딕셔너리
    """
    recommendations = agent_result.get("recommendations", [])
    
    # 점수 기준으로 정렬 (이미 정렬되어 있을 수 있지만 확실히 하기 위해)
    def get_score(rec):
        # Agent 결과에서 점수 추출 (여러 필드명 시도, None 체크 명시)
        score = None
        if "score" in rec and rec["score"] is not None:
            score = rec["score"]
        elif "최종점수" in rec and rec["최종점수"] is not None:
            score = rec["최종점수"]
        elif "MAUT점수" in rec and rec["MAUT점수"] is not None:
            score = rec["MAUT점수"]
        elif "total_score" in rec and rec["total_score"] is not None:
            score = rec["total_score"]
        else:
            score = 0.0
        
        # 점수가 1보다 크면 0-1 범위로 정규화 (0-100 범위로 저장된 경우)
        if isinstance(score, (int, float)) and score > 1.0:
            score = score / 100.0
        return float(score)
    
    sorted_recommendations = sorted(
        recommendations,
        key=get_score,
        reverse=True
    )
    
    # COA 리스트 변환
    coas = []
    for idx, rec in enumerate(sorted_recommendations[:3]):  # 상위 3개만
        # 점수 추출 및 정규화
        total_score = get_score(rec)
        
        # score_breakdown 추출 (COAScorer의 breakdown 구조)
        score_breakdown = rec.get("score_breakdown", {})
        # 🔥 FIX: breakdown이 딕셔너리가 아닌 경우 처리
        if not isinstance(score_breakdown, dict):
            logger.warning(f"  [WARNING] COA {idx+1}: score_breakdown이 dict가 아닙니다! (type={type(score_breakdown)}, value={score_breakdown})")
            score_breakdown = {}
        
        # 디버깅: 점수 추출 로그 (상세)
        logger.info(f"COA {idx+1} ({rec.get('coa_name', 'Unknown')}) 점수 추출:")
        logger.info(f"  - 총점: {total_score}")
        logger.info(f"  - 원본 필드: score={rec.get('score')}, 최종점수={rec.get('최종점수')}, MAUT점수={rec.get('MAUT점수')}")
        logger.info(f"  - score_breakdown 키들: {list(score_breakdown.keys()) if score_breakdown else 'None'}")
        if score_breakdown:
            logger.info(f"  - breakdown 값들: {score_breakdown}")
            # 🔥 FIX: breakdown이 비어있거나 키가 없는 경우 경고
            if not score_breakdown or len(score_breakdown) == 0:
                logger.warning(f"  [WARNING] COA {idx+1}: score_breakdown이 비어있습니다!")
        else:
            logger.warning(f"  [WARNING] COA {idx+1}: score_breakdown이 None입니다!")
        
        # 🔥 FIX: rec에 직접 필드가 있는지 확인 (하드코딩된 값일 수 있음)
        direct_fields = {
            'combat_power_score': rec.get('combat_power_score'),
            'mobility_score': rec.get('mobility_score'),
            'constraint_score': rec.get('constraint_score'),
            'threat_response_score': rec.get('threat_response_score'),
            'risk_score': rec.get('risk_score')
        }
        if any(v is not None for v in direct_fields.values()):
            logger.warning(f"  [WARNING] COA {idx+1}: rec에 직접 필드가 있습니다! (하드코딩된 값일 수 있음)")
            logger.warning(f"    - direct_fields: {direct_fields}")
        
        # COAScorer breakdown 키 → 프론트엔드 필드명 매핑
        # COAScorer breakdown: threat, resources, assets, environment, historical, chain, mission_alignment
        def safe_get_score(key, default=0.0):
            """score_breakdown에서 안전하게 점수 추출"""
            if not score_breakdown or key is None:
                return default
            value = score_breakdown.get(key)
            if value is None:
                return default
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        
        # 디버깅: 각 COA별 breakdown 값 확인 (각 COA가 다른 값을 가져야 함)
        if score_breakdown:
            logger.info(f"  - COA {idx+1} ({rec.get('coa_id', 'Unknown')}) breakdown 값:")
            logger.info(f"    * threat={safe_get_score('threat'):.4f}, assets={safe_get_score('assets'):.4f}")
            logger.info(f"    * resources={safe_get_score('resources'):.4f}, environment={safe_get_score('environment'):.4f}")
            logger.info(f"    * historical={safe_get_score('historical'):.4f}, chain={safe_get_score('chain'):.4f}")
            logger.info(f"    * mission_alignment={safe_get_score('mission_alignment'):.4f}")
        else:
            logger.warning(f"  - COA {idx+1} ({rec.get('coa_id', 'Unknown')}): score_breakdown이 없습니다!")
        
        # 점수 필드 매핑 (COAScorer breakdown → 프론트엔드 필드명)
        # 주의: COAScorer breakdown과 COAEvaluator 점수 필드는 의미가 다를 수 있음
        # COAScorer: threat, resources, assets, environment, historical, chain, mission_alignment
        # COAEvaluator: combat_power_score, mobility_score, constraint_compliance_score, threat_response_score, risk_score
        # 
        # 매핑 규칙:
        # - threat → threat_response_score (위협 대응)
        # - assets → combat_power_score (전력능력/자산 능력)
        # - resources → mobility_score (자원 가용성 → 기동성으로 해석, 의미는 다르지만 가장 가까운 매핑)
        # - environment → constraint_score (환경 적합성 → 제약조건 준수도로 해석)
        # - risk_score는 breakdown에 없으므로 threat 기반 계산 또는 기본값
        
        # 점수 추출 헬퍼 함수 (breakdown 우선 사용)
        def extract_score(field_name, breakdown_key, default=0.0):
            """점수 필드 추출 (breakdown 우선, rec 직접 필드는 fallback)"""
            # 🔥 FIX: breakdown을 우선 사용 (COA별로 다를 수 있음)
            # rec의 직접 필드는 하드코딩된 값일 수 있으므로 fallback으로만 사용
            if breakdown_key is not None and score_breakdown and isinstance(score_breakdown, dict):
                breakdown_value = safe_get_score(breakdown_key, None)
                # None이 아니고 0.0도 유효한 값으로 처리 (0.0은 기본값과 구분 필요)
                if breakdown_value is not None:
                    # breakdown에서 유효한 값이 있으면 사용
                    logger.info(f"    [DEBUG] {field_name}: breakdown['{breakdown_key}']에서 추출 = {breakdown_value:.4f} (breakdown 키 존재: {breakdown_key in score_breakdown})")
                    return breakdown_value
                elif breakdown_key in score_breakdown:
                    # 키는 있지만 값이 None인 경우도 로그
                    logger.warning(f"    [WARNING] {field_name}: breakdown['{breakdown_key}'] 키는 있지만 값이 None")
                else:
                    # 키가 없는 경우
                    logger.warning(f"    [WARNING] {field_name}: breakdown['{breakdown_key}'] 키가 없습니다. (사용 가능한 키: {list(score_breakdown.keys())})")
            
            # breakdown에 없으면 rec에서 직접 필드 확인 (fallback)
            direct_value = rec.get(field_name)
            if direct_value is not None:
                try:
                    direct_score = float(direct_value)
                    logger.info(f"    [DEBUG] {field_name}: rec에서 직접 추출 = {direct_score:.4f} (breakdown 없음)")
                    return direct_score
                except (TypeError, ValueError):
                    pass
            
            # 둘 다 없으면 기본값
            if breakdown_key is not None:
                logger.warning(f"    [WARNING] {field_name}: breakdown['{breakdown_key}']와 rec['{field_name}'] 모두 없음, 기본값 {default} 사용")
            return default
        
        # constraint_score는 여러 필드 시도 (breakdown 우선)
        def extract_constraint_score():
            """제약조건 점수 추출 (breakdown 우선, 여러 필드 시도)"""
            # 🔥 FIX: breakdown의 environment를 우선 사용
            if score_breakdown:
                env_value = safe_get_score("environment", None)
                if env_value is not None:
                    logger.info(f"    [DEBUG] constraint_score: breakdown['environment']에서 추출 = {env_value:.4f}")
                    return env_value
            
            # breakdown에 없으면 rec에서 직접 필드 확인 (fallback)
            # 1순위: constraint_compliance_score
            value = rec.get("constraint_compliance_score")
            if value is not None:
                try:
                    score = float(value)
                    logger.info(f"    [DEBUG] constraint_score: rec['constraint_compliance_score']에서 추출 = {score:.4f}")
                    return score
                except (TypeError, ValueError):
                    pass
            
            # 2순위: constraint_score
            value = rec.get("constraint_score")
            if value is not None:
                try:
                    score = float(value)
                    logger.info(f"    [DEBUG] constraint_score: rec['constraint_score']에서 추출 = {score:.4f}")
                    return score
                except (TypeError, ValueError):
                    pass
            
            # 3순위: 기본값
            logger.warning(f"    [WARNING] constraint_score: breakdown['environment']와 rec 필드 모두 없음, 기본값 0.0 사용")
            return 0.0
        
        # risk_score 추출 (breakdown 우선)
        def extract_risk_score():
            """위험도 점수 추출 (breakdown 우선, threat 기반 계산은 fallback)"""
            # 🔥 FIX: breakdown에 risk_score가 있으면 우선 사용 (향후 추가 가능성 고려)
            # 현재는 breakdown에 risk_score가 없으므로 rec 확인 후 threat 기반 계산
            
            # 1순위: rec에서 직접 필드 확인
            value = rec.get("risk_score")
            if value is not None:
                try:
                    score = float(value)
                    logger.info(f"    [DEBUG] risk_score: rec['risk_score']에서 추출 = {score:.4f}")
                    return score
                except (TypeError, ValueError):
                    pass
            
            # 2순위: threat 기반 계산 (risk = 1.0 - threat)
            threat_score = safe_get_score("threat", 0.0)
            if threat_score > 0:
                calculated_risk = 1.0 - threat_score
                logger.info(f"    [DEBUG] risk_score: threat 기반 계산 = {calculated_risk:.4f} (from threat={threat_score:.4f})")
                return calculated_risk
            
            # 3순위: 기본값
            logger.warning(f"    [WARNING] risk_score: rec['risk_score']와 threat 기반 계산 모두 불가, 기본값 0.0 사용")
            return 0.0
        
        # 최종 점수 필드 추출 (각 COA별로 다른 값이어야 함)
        threat_response_score = extract_score("threat_response_score", "threat", 0.0)
        combat_power_score = extract_score("combat_power_score", "assets", 0.0)
        mobility_score = extract_score("mobility_score", "resources", 0.0)
        constraint_score = extract_constraint_score()
        risk_score = extract_risk_score()
        
        # 디버깅: 추출된 최종 점수 로그 (상세)
        logger.info(f"  - COA {idx+1} ({rec.get('coa_id', 'Unknown')}) 최종 추출 점수:")
        logger.info(f"    * threat_response_score={threat_response_score:.4f} (from threat={safe_get_score('threat', 0.0):.4f}, rec.direct={rec.get('threat_response_score', 'None')})")
        logger.info(f"    * combat_power_score={combat_power_score:.4f} (from assets={safe_get_score('assets', 0.0):.4f}, rec.direct={rec.get('combat_power_score', 'None')})")
        logger.info(f"    * mobility_score={mobility_score:.4f} (from resources={safe_get_score('resources', 0.0):.4f}, rec.direct={rec.get('mobility_score', 'None')})")
        logger.info(f"    * constraint_score={constraint_score:.4f} (from environment={safe_get_score('environment', 0.0):.4f}, rec.direct={rec.get('constraint_score', 'None')}, rec.constraint_compliance={rec.get('constraint_compliance_score', 'None')})")
        logger.info(f"    * risk_score={risk_score:.4f} (rec.direct={rec.get('risk_score', 'None')}, calculated_from_threat={1.0 - safe_get_score('threat', 0.0):.4f})")
        
        # 경고: 모든 COA가 동일한 점수를 가지는 경우
        if idx > 0:
            prev_coa = coas[-1] if coas else None
            if prev_coa:
                if (abs(prev_coa.get('threat_response_score', 0) - threat_response_score) < 0.001 and
                    abs(prev_coa.get('combat_power_score', 0) - combat_power_score) < 0.001 and
                    abs(prev_coa.get('mobility_score', 0) - mobility_score) < 0.001 and
                    abs(prev_coa.get('constraint_score', 0) - constraint_score) < 0.001 and
                    abs(prev_coa.get('risk_score', 0) - risk_score) < 0.001):
                    logger.warning(f"  [WARNING] COA {idx+1}의 점수가 이전 COA와 동일합니다! breakdown이 제대로 전달되지 않았을 수 있습니다.")
                    logger.warning(f"    - score_breakdown 키: {list(score_breakdown.keys()) if score_breakdown else 'None'}")
                    logger.warning(f"    - score_breakdown 값: {score_breakdown if score_breakdown else 'None'}")
        
        # METT-C 점수 추출 (별도 평가 체계로 구분)
        # METT-C는 Mission, Enemy, Terrain, Troops, Civilian, Time을 평가하는 별도 프레임워크
        # COAScorer breakdown과는 다른 평가 체계이므로 별도로 구분
        mett_c_data = rec.get("mett_c", {}) if isinstance(rec.get("mett_c"), dict) else {}
        mett_c_scores = None
        if mett_c_data:
            # METT-C 점수를 별도 객체로 구성
            mett_c_scores = {}
            if mett_c_data.get("mission_score") is not None:
                mett_c_scores["mission_score"] = float(mett_c_data["mission_score"])
            if mett_c_data.get("enemy_score") is not None:
                mett_c_scores["enemy_score"] = float(mett_c_data["enemy_score"])
            if mett_c_data.get("terrain_score") is not None:
                mett_c_scores["terrain_score"] = float(mett_c_data["terrain_score"])
            if mett_c_data.get("troops_score") is not None:
                mett_c_scores["troops_score"] = float(mett_c_data["troops_score"])
            if mett_c_data.get("civilian_score") is not None:
                mett_c_scores["civilian_score"] = float(mett_c_data["civilian_score"])
            if mett_c_data.get("time_score") is not None:
                mett_c_scores["time_score"] = float(mett_c_data["time_score"])
            if mett_c_data.get("total") is not None:
                mett_c_scores["total_score"] = float(mett_c_data["total"])
        
        # 적합성, 타당성, 수용성 점수 추출 (NATO 교범 AJP-5 기준, COAScorer breakdown 기반)
        # 
        # NATO 교범 AJP-5 "Allied Joint Doctrine for the Planning of Operations" 기준:
        # 이 세 가지 평가 기준은 COA 평가의 표준 프레임워크이며, 총합점수(total_score)와는 별개의 평가 체계입니다.
        # 총합점수는 COAScorer breakdown의 가중합으로 계산되며, 이 세 항목의 합이 아닙니다.
        # 
        # 1. Suitability (적합성): COA가 임무를 달성하고 계획 지침을 준수하는지 평가
        #    → mission_alignment (임무 부합성) 사용
        # 2. Feasibility (타당성): 시간, 공간, 자원이 가용하고 작전 환경에 적합한지 평가
        #    → resources (자원 가용성) 사용 (시간/공간은 별도 고려 필요)
        # 3. Acceptability (수용성): 예상 성과가 예상 비용(전력, 자원, 사상자, 위험 등)을 정당화하는지 평가
        #    → environment (환경 적합성)과 risk (위험도) 조합 사용
        # 
        # 주의: METT-C와는 별개의 평가 체계입니다. METT-C는 Mission, Enemy, Terrain, Troops, Civilian, Time을
        # 평가하는 별도 프레임워크이며, 적합성/타당성/수용성과는 다른 관점에서 COA를 평가합니다.
        suitability_score = (
            rec.get("suitability_score") if rec.get("suitability_score") is not None else
            safe_get_score("mission_alignment", 0.0)  # 임무 부합성 → 적합성
        )
        feasibility_score = (
            rec.get("feasibility_score") if rec.get("feasibility_score") is not None else
            safe_get_score("resources", 0.0)  # 자원 가용성 → 타당성
        )
        # 수용성은 위험 대비 이익을 고려해야 하므로, environment와 risk를 조합
        acceptability_score = (
            rec.get("acceptability_score") if rec.get("acceptability_score") is not None else
            # environment (환경 적합성)과 risk (위험도)를 조합하여 수용성 계산
            # 위험이 낮고 환경 적합성이 높을수록 수용성 높음
            max(0.0, min(1.0, (safe_get_score("environment", 0.0) * 0.7 + (1.0 - risk_score) * 0.3)))
        )
        
        # 타입 변환 및 범위 확인
        try:
            suitability_score = float(suitability_score) if suitability_score is not None else 0.0
            feasibility_score = float(feasibility_score) if feasibility_score is not None else 0.0
            acceptability_score = float(acceptability_score) if acceptability_score is not None else 0.0
        except (TypeError, ValueError):
            suitability_score = 0.0
            feasibility_score = 0.0
            acceptability_score = 0.0
        
        # 디버깅: 최종 추출된 점수 값 확인
        logger.info(f"  - COA {idx+1} 최종 추출 점수:")
        logger.info(f"    * COAScorer breakdown 기반:")
        logger.info(f"      - threat_response_score={threat_response_score:.4f}, combat_power_score={combat_power_score:.4f}")
        logger.info(f"      - mobility_score={mobility_score:.4f}, constraint_score={constraint_score:.4f}, risk_score={risk_score:.4f}")
        logger.info(f"    * 적합성/타당성/수용성 (COAScorer breakdown 기반):")
        logger.info(f"      - suitability_score={suitability_score:.4f}, feasibility_score={feasibility_score:.4f}, acceptability_score={acceptability_score:.4f}")
        if mett_c_scores:
            logger.info(f"    * METT-C 점수 (별도 평가 체계): {mett_c_scores}")
        
        coa = {
            "coa_id": rec.get("coa_id") or rec.get("방책ID") or rec.get("ID") or f"COA_{idx+1}",
            "coa_name": rec.get("명칭") or rec.get("방책명") or rec.get("name") or rec.get("coa_name", "Unknown"),
            "total_score": float(total_score),
            "rank": idx + 1,
            "description": rec.get("추천사유") or rec.get("reason") or rec.get("설명") or rec.get("description", ""),
            # 점수 필드들 (COAScorer breakdown에서 매핑, 각 COA별로 다른 값이어야 함)
            # COAScorer breakdown 키: threat, resources, assets, environment, historical, chain, mission_alignment
            "threat_response_score": threat_response_score,
            "combat_power_score": combat_power_score,
            "mobility_score": mobility_score,
            "constraint_score": constraint_score,
            "risk_score": risk_score,
            # 적합성, 타당성, 수용성 점수 (NATO 교범 AJP-5 기준, COAScorer breakdown 기반)
            # 주의: 이들은 총합점수(total_score)와는 별개의 평가 기준이며, METT-C와도 별개의 평가 체계입니다.
            # 총합점수는 COAScorer breakdown의 가중합으로 계산되며, 이 세 항목의 합이 아닙니다.
            "suitability_score": suitability_score,
            "feasibility_score": feasibility_score,
            "acceptability_score": acceptability_score,
            # METT-C 점수 (별도 평가 체계로 구분)
            "mett_c_scores": mett_c_scores,
            # Agent 결과의 추가 정보
            "reasoning": rec.get("reasoning") or {},
            "reasoning_trace": rec.get("reasoning_trace") or [],
            "doctrine_references": rec.get("doctrine_references") or [],
            "coa_geojson": rec.get("coa_geojson"),
            "unit_positions": rec.get("unit_positions"),
            "score_breakdown": {
                # 원본 COAScorer breakdown 유지 (threat, resources, assets, environment, historical, chain, mission_alignment)
                **(score_breakdown or {}),
                # 프론트엔드 비교표가 기대하는 필드명으로도 추가 (COAEvaluator 스타일)
                "combat_power_score": extract_score("combat_power_score", "assets", 0.0),
                "mobility_score": extract_score("mobility_score", "resources", 0.0),
                "threat_response_score": extract_score("threat_response_score", "threat", 0.0),
                "constraint_score": extract_constraint_score(),
                "risk_score": extract_risk_score(),
                # 원본 breakdown 키도 유지 (디버깅 및 호환성)
                "_original_keys": list(score_breakdown.keys()) if score_breakdown else [],
            },
            "execution_plan": rec.get("execution_plan"),
            "chain_info": rec.get("chain_info") or {},
            "chain_info_details": rec.get("chain_info_details"),
            "coa_type": rec.get("coa_type") or rec.get("방책유형", ""),
            "participating_units": rec.get("participating_units") or []
        }
        coas.append(coa)
    
    # Axis states 변환 및 좌표 보강
    from core_pipeline.visualization_generator import VisualizationDataGenerator
    viz_generator = VisualizationDataGenerator()
    
    axis_states = agent_result.get("axis_states", [])
    if not axis_states:
        situation_analysis = agent_result.get("situation_analysis", {})
        axis_states = situation_analysis.get("axis_states", [])
    
    # 🔥 FIX: 만약 axis_states가 여전히 비어있다면, AxisStateBuilder를 사용하여 자동 생성 시도
    if not axis_states:
        logger.info("[시각화 보강] 결과에 axis_states가 없음. 자동 빌드 시도...")
        try:
            from core_pipeline.axis_state_builder import AxisStateBuilder
            from core_pipeline.coa_service import COAService
            from core_pipeline.data_models import ThreatEvent
            
            service = COAService()
            builder = AxisStateBuilder(service.data_manager, service.ontology_manager)
            
            # 상황 정보 추출
            situation_info = agent_result.get("situation_info", {})
            threat_id = agent_result.get("situation_id") or situation_info.get("위협ID") or situation_info.get("threat_id")
            mission_id = situation_info.get("임무ID") or situation_info.get("mission_id")
            
            # 위협 정보가 있으면 위협 중심 빌드
            if threat_id:
                # ThreatEvent 객체 생성 시도
                try:
                    threat_events_df = service.data_manager.load_table('위협상황')
                    id_col = None
                    for col in threat_events_df.columns:
                        if col.upper() in ['ID', '위협ID', 'THREAT_ID']:
                            id_col = col; break
                    
                    if id_col:
                        row = threat_events_df[threat_events_df[id_col].astype(str).str.strip() == str(threat_id).strip()]
                        if not row.empty:
                            threat_event = ThreatEvent.from_row(row.iloc[0].to_dict())
                            axis_states = builder.build_axis_states_from_threat(threat_event, mission_id)
                            logger.info(f"  - 위협 {threat_id} 기반 축선 빌드 성공: {len(axis_states)}개 축선")
                except Exception as e:
                    logger.warning(f"  - 위협 기반 축선 빌드 실패: {e}")
            
            # 위협 기반 빌드 실패 시 임무 기반 빌드
            if not axis_states and mission_id:
                axis_states = builder.build_axis_states(mission_id)
                logger.info(f"  - 임무 {mission_id} 기반 축선 빌드 성공: {len(axis_states)}개 축선")
            
            # 그래도 없으면 모든 축선 빌드 (최종 수단)
            if not axis_states:
                axis_states = builder.build_axis_states("") # 빈 mission_id는 모든 축선 로드
                logger.info(f"  - 모든 축선 빌드 (Fallback): {len(axis_states)}개 축선")
                
        except Exception as e:
            logger.error(f"[시각화 보강] 축선 정보 복구 중 오류: {e}")
    
    # 축선 좌표 보강
    axis_states_data = viz_generator.enrich_axis_states_with_coordinates(axis_states)
    
    # 위협 위치 추출
    threat_position = None
    situation_info = agent_result.get("situation_info", {})
    location_cell_id = situation_info.get("location_cell_id") or situation_info.get("발생장소") or situation_info.get("location")
    if location_cell_id:
        threat_position = viz_generator._get_terrain_cell_coordinates(str(location_cell_id))
    
    # 각 COA별 시각화 데이터 보강 (만약 비어있다면)
    for coa in coas:
        if coa is None: continue # Safety
        
        # 🔥 FIX: participating_units가 문자열인 경우 배열로 변환
        # Agent가 "보병여단, 공병대대, 포병대대" 같은 문자열로 반환하는 경우 처리
        participating_units = coa.get("participating_units", [])
        if isinstance(participating_units, str):
            # 쉼표로 구분된 문자열을 배열로 변환
            participating_units = [u.strip() for u in participating_units.split(',') if u.strip()]
            coa["participating_units"] = participating_units
            logger.info(f"[시각화 데이터 생성] COA {coa.get('coa_id')}: participating_units를 문자열에서 배열로 변환: {participating_units}")
        
        # 만약 coa_geojson이나 unit_positions가 없으면 생성 시도
        # 🔥 FIX: 빈 객체나 features가 없는 경우도 감지
        unit_positions = coa.get("unit_positions")
        should_generate_unit_positions = (
            not unit_positions or  # None 또는 빈 객체
            not isinstance(unit_positions, dict) or  # dict가 아닌 경우
            not unit_positions.get("features") or  # features 키가 없는 경우
            len(unit_positions.get("features", [])) == 0  # features가 빈 배열인 경우
        )
        
        if should_generate_unit_positions:
            logger.info(f"[시각화 데이터 생성] COA {coa.get('coa_id')}: unit_positions가 없거나 비어있음, 재생성 시작")
            logger.info(f"  - unit_positions 상태: {unit_positions}")
            logger.info(f"  - participating_units: {participating_units}")
            logger.info(f"  - participating_units 개수: {len(participating_units) if participating_units else 0}")
            
            # participating_units를 기반으로 생성
            friendly_units = []
            # data_manager에서 부대 상세 정보 조회
            from core_pipeline.coa_service import COAService
            service = COAService() # Orchestrator에서 가져오는게 좋지만 일단 생성
            
            # participating_units 정규화: 약칭을 정식 부대명으로 변환
            friendly_units_data = service.data_manager.load_table('아군부대현황')
            normalized_participating_units = []
            
            for unit_name_or_id in participating_units:
                unit_info = {"unit_id": unit_name_or_id}
                try:
                    resource_alloc_data = service.data_manager.load_table('임무별_자원할당')
                    
                    if friendly_units_data is not None and not friendly_units_data.empty:
                        # 1. ID로 정확히 매칭 시도
                        unit_row = friendly_units_data[friendly_units_data['아군부대ID'] == unit_name_or_id]
                        
                        # 2. ID 매칭 실패 시, 이름 정규화 매칭 시도
                        if unit_row.empty:
                            # 2-1. 정확한 이름 매칭 (우선순위 최상)
                            unit_row = friendly_units_data[friendly_units_data['부대명'] == unit_name_or_id]
                            
                            # 2-2. 약칭 처리를 위한 스마트 정규식 매칭
                            if unit_row.empty:
                                try:
                                    # 숫자와 텍스트를 분리하여 유연한 매칭 패턴 생성
                                    # 예: "1여단" -> pattern: ".*1.*여단.*" -> "제1보병여단" 매칭 가능
                                    # 예: "3군단" -> pattern: ".*3.*군단.*" -> "제3군단" 매칭 가능
                                    import re
                                    # 숫자를 기준으로 토큰 분리 (예: "1여단" -> ['', '1', '여단'])
                                    tokens = re.split(r'(\d+)', unit_name_or_id)
                                    tokens = [t for t in tokens if t.strip()] # 빈 문자열 제거
                                    
                                    if tokens:
                                        # 토큰 사이에 .* 삽입 (아무 문자나 올 수 있음)
                                        pattern_str = ".*".join([re.escape(t) for t in tokens])
                                        # 앞뒤에도 유연성 부여 (접두어 '제', 접미어 등)
                                        regex_pattern = f".*{pattern_str}.*"
                                        
                                        # 정규식 매칭 수행
                                        unit_row = friendly_units_data[
                                            friendly_units_data['부대명'].str.match(regex_pattern, na=False)
                                        ]
                                        
                                        if not unit_row.empty:
                                            # 매칭된 결과가 여러 개일 경우, 가장 짧은 이름(가장 일반적인 이름)이나 첫 번째 선택
                                            # 여기서는 첫 번째 선택
                                            logger.info(f"  - 스마트 정규식 매칭 성공: '{unit_name_or_id}' (pattern: {regex_pattern}) → '{unit_row.iloc[0]['부대명']}'")
                                except Exception as e:
                                    logger.warning(f"  - 스마트 정규식 매칭 중 오류: {e}")

                            # 2-3. 기존 단순 부분 문자열 매칭 (Fallback)
                            if unit_row.empty:
                                unit_row = friendly_units_data[
                                    friendly_units_data['부대명'].str.contains(unit_name_or_id, na=False, regex=False)
                                ]
                                if not unit_row.empty:
                                    logger.info(f"  - 부대명 부분 매칭 성공: '{unit_name_or_id}' → '{unit_row.iloc[0]['부대명']}'")
                        
                        # 3. 병종 기반 폴백 매칭 (예: "포병대대" → "포병" 병종으로 검색)
                        if unit_row.empty:
                            # 병종 추출 (예: "포병대대" → "포병")
                            unit_type_keywords = ['보병', '포병', '공병', '기갑', '수색', '통신', '의무', '군수', '기계화']
                            extracted_type = None
                            for keyword in unit_type_keywords:
                                if keyword in unit_name_or_id:
                                    extracted_type = keyword
                                    break
                            
                            if extracted_type:
                                # 병종으로 검색 (병종 컬럼 사용)
                                unit_row = friendly_units_data[
                                    friendly_units_data['병종'].str.contains(extracted_type, na=False, regex=False)
                                ]
                                
                                # 부대명에서도 검색 (보조)
                                if unit_row.empty:
                                    unit_row = friendly_units_data[
                                        friendly_units_data['부대명'].str.contains(extracted_type, na=False, regex=False)
                                    ]
                                
                                if not unit_row.empty:
                                    logger.info(f"  - 병종 기반 폴백 매칭 성공: '{unit_name_or_id}' → '{extracted_type}' → '{unit_row.iloc[0]['부대명']}'")
                        
                        if not unit_row.empty:
                            actual_unit_id = unit_row.iloc[0].get('아군부대ID', unit_name_or_id)
                            actual_unit_name = unit_row.iloc[0].get('부대명', unit_name_or_id)
                            
                            # normalized_participating_units에 정식 부대명 추가
                            normalized_participating_units.append(actual_unit_name)
                            
                            # numpy 타입을 Python 네이티브 타입으로 변환
                            def convert_numpy_types(value):
                                """numpy 타입을 Python 네이티브 타입으로 변환"""
                                import numpy as np
                                if isinstance(value, (np.integer, np.int64, np.int32)):
                                    return int(value)
                                elif isinstance(value, (np.floating, np.float64, np.float32)):
                                    return float(value)
                                elif isinstance(value, np.ndarray):
                                    return value.tolist()
                                return value
                            
                            unit_info.update({
                                "unit_id": actual_unit_id,
                                "부대명": actual_unit_name,
                                "제대": str(unit_row.iloc[0].get('제대', '')),
                                "병종": str(unit_row.iloc[0].get('병종', '')),
                                "배치지형셀ID": str(unit_row.iloc[0].get('배치지형셀ID', '')),
                                "좌표정보": str(unit_row.iloc[0].get('좌표정보', '')),
                                "전투력지수": convert_numpy_types(unit_row.iloc[0].get('전투력지수', 0)),
                            })
                            
                            # 2. 임무별 특수 할당 정보 조회
                            if resource_alloc_data is not None and not resource_alloc_data.empty:
                                alloc_row = resource_alloc_data[resource_alloc_data['asset_id'] == actual_unit_id]
                                if not alloc_row.empty:
                                    unit_info.update({
                                        "tactical_role": str(alloc_row.iloc[0].get('tactical_role', '')),
                                        "allocated_quantity": convert_numpy_types(alloc_row.iloc[0].get('allocated_quantity', 1)),
                                        "plan_status": str(alloc_row.iloc[0].get('plan_status', '사용가능')),
                                    })
                            
                            logger.info(f"  - 부대 정보 조회 성공: {unit_name_or_id} → {actual_unit_name} (ID: {actual_unit_id})")
                        else:
                            logger.warning(f"  - 부대 정보 조회 실패: {unit_name_or_id} (데이터 없음)")
                            normalized_participating_units.append(unit_name_or_id)  # 실패 시 원본 유지
                            
                            # 🔥 FIX: 누락된 부대 정보를 추적하기 위해 coa 객체에 추가 (프론트엔드 알림용)
                            if "missing_units" not in coa: coa["missing_units"] = []
                            coa["missing_units"].append(unit_name_or_id)
                except Exception as e:
                    logger.warning(f"  - 부대 정보 조회 실패: {unit_name_or_id} - {e}")
                    normalized_participating_units.append(unit_name_or_id)  # 실패 시 원본 유지
                friendly_units.append(unit_info)
            
            # 🔥 FIX: participating_units를 정식 부대명으로 업데이트
            if normalized_participating_units:
                coa["participating_units"] = normalized_participating_units
                logger.info(f"  - participating_units 정규화 완료: {participating_units} → {normalized_participating_units}")
            
            logger.info(f"  - 조회된 부대 수: {len(friendly_units)}")
            
            generated_unit_positions = viz_generator.generate_unit_positions_geojson(friendly_units)
            coa["unit_positions"] = generated_unit_positions
            logger.info(f"  - 생성 완료: features 개수 = {len(generated_unit_positions.get('features', [])) if generated_unit_positions else 0}")
            
            # 작전 경로도 생성
            if not coa.get("visualization_data") or not (coa.get("visualization_data") or {}).get("operational_path"):
                main_axis_id = (coa.get("reasoning") or {}).get("primary_axis_id") or (coa.get("chain_info") or {}).get("axis_id")
                
                # 🔥 FIX: 만약 방책에 축선 ID가 없으면, 복구된 axis_states 중 첫 번째를 폴백으로 사용
                if not main_axis_id and axis_states_data:
                    main_axis_id = axis_states_data[0].get("axis_id")
                    logger.info(f"  - COA {coa.get('coa_id')}: 축선 ID 없음, '{main_axis_id}'로 폴백 적용")
                
                op_path = viz_generator.generate_operational_path(
                    coa=coa,
                    friendly_units=friendly_units,
                    threat_position=threat_position,
                    main_axis_id=main_axis_id
                )
                if op_path:
                    if not coa.get("visualization_data"): coa["visualization_data"] = {}
                    coa["visualization_data"]["operational_path"] = op_path
                    logger.info(f"  - 작전 경로 생성 완료: waypoints 개수 = {len(op_path.get('waypoints', []))}")
            
            # 작전 영역도 생성
            if not coa.get("visualization_data") or not (coa.get("visualization_data") or {}).get("operational_area"):
                op_area = viz_generator.generate_operational_area(
                    friendly_units=friendly_units,
                    threat_position=threat_position
                )
                if op_area:
                    if not coa.get("visualization_data"): coa["visualization_data"] = {}
                    coa["visualization_data"]["operational_area"] = op_area
                    logger.info(f"  - 작전 영역 생성 완료")

    # COAResponse 형식으로 변환
    # 정황보고 생성 방식 확인 (Agent가 생성한 경우 LLM 사용 가능성 높음)
    situation_summary = agent_result.get("situation_summary")
    situation_summary_source = None
    if situation_summary:
        # Agent가 생성한 정황보고는 일반적으로 LLM 기반
        # 하지만 확실하지 않으므로 "llm" 또는 None으로 표시
        situation_summary_source = "llm"  # Agent 결과는 LLM 기반으로 가정
    
    return {
        "coas": coas,
        "axis_states": axis_states_data,
        "situation_summary": situation_summary,
        "situation_summary_source": situation_summary_source,
        "situation_analysis": agent_result.get("situation_analysis", {}),
        "approach_mode": agent_result.get("situation_info", {}).get("approach_mode", "threat_centered"),
        "mission_id": agent_result.get("situation_info", {}).get("임무ID") or agent_result.get("situation_info", {}).get("mission_id"),
        "threat_id": agent_result.get("situation_id") or agent_result.get("situation_info", {}).get("위협ID") or agent_result.get("situation_info", {}).get("threat_id"),
        "_agent_metadata": {
            "agent": agent_result.get("agent"),
            "status": agent_result.get("status"),
            "llm_collaboration": agent_result.get("llm_collaboration", {}),
            "palantir_mode": agent_result.get("palantir_mode", False)
        }
    }

@router.post("/execute")
async def execute_agent(
    request: AgentExecutionRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Agent 실행 엔드포인트 (Streamlit과 동일한 로직 사용)
    
    이 엔드포인트는 EnhancedDefenseCOAAgent.execute_reasoning()을 호출하여
    온톨로지, RAG, LLM을 모두 활용한 통합 방책 추천을 수행합니다.
    """
    try:
        # 정황보고 캐시 확인 (SITREP이 아닌 경우만)
        from api.dependencies import get_global_state
        global_state = get_global_state()
        
        situation_info_for_cache = {}
        if request.situation_info:
            situation_info_for_cache.update(request.situation_info)
        if request.situation_id:
            situation_info_for_cache['threat_id'] = request.situation_id
            situation_info_for_cache['위협ID'] = request.situation_id
        if request.user_params and request.user_params.get('mission_id'):
            situation_info_for_cache['mission_id'] = request.user_params.get('mission_id')
            situation_info_for_cache['임무ID'] = request.user_params.get('mission_id')
        if request.user_params and request.user_params.get('approach_mode'):
            situation_info_for_cache['approach_mode'] = request.user_params.get('approach_mode')
        
        cached_summary = global_state.situation_summary_cache.get(situation_info_for_cache)
        
        # Agent 클래스 로드
        agent_class = orchestrator.load_agent_class(request.agent_class_path)
        if agent_class is None:
            raise HTTPException(
                status_code=404,
                detail=f"Agent 클래스를 찾을 수 없습니다: {request.agent_class_path}"
            )
        
        # Agent 인스턴스 생성
        agent = agent_class(core=orchestrator.core)
        
        # 진행 상황 로그 수집
        progress_logs = []
        
        # 진행 상황 콜백 (선택적)
        def on_status_update(msg: str, progress: Optional[int] = None):
            logger.info(f"[Agent Progress] {progress}%: {msg}")
            # 진행 상황 로그에 추가
            progress_logs.append({
                "message": msg,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
            # TODO: WebSocket을 통한 실시간 진행 상황 전송 가능
        
        # Agent 실행
        agent_result = agent.execute_reasoning(
            situation_id=request.situation_id,
            selected_situation_info=request.situation_info,
            use_palantir_mode=request.use_palantir_mode,
            enable_rag_search=request.enable_rag_search,
            coa_type_filter=request.coa_type_filter,
            user_params=request.user_params,
            status_callback=on_status_update
        )
        
        # 캐시된 정황보고가 있으면 Agent 결과에 적용 (Agent가 생성한 것보다 우선)
        situation_summary_source_for_agent = None
        if cached_summary and agent_result:
            agent_result["situation_summary"] = cached_summary
            situation_summary_source_for_agent = "cache"
        
        # 결과 변환
        result = convert_agent_result_to_coa_response(agent_result)
        
        # 캐시에서 가져온 경우 source 설정
        if situation_summary_source_for_agent == "cache":
            result["situation_summary_source"] = "cache"
        
        # 정황보고 캐시 처리 (Agent가 생성한 정황보고를 캐시에 저장)
        situation_summary = result.get("situation_summary")
        if situation_summary:
            from api.dependencies import get_global_state
            global_state = get_global_state()
            
            # 상황 정보 구성 (캐시 키 생성용)
            situation_info = {}
            if request.situation_info:
                situation_info.update(request.situation_info)
            if request.situation_id:
                situation_info['threat_id'] = request.situation_id
                situation_info['위협ID'] = request.situation_id
            if result.get("mission_id"):
                situation_info['mission_id'] = result["mission_id"]
                situation_info['임무ID'] = result["mission_id"]
            if result.get("approach_mode"):
                situation_info['approach_mode'] = result["approach_mode"]
            
            # 캐시에 저장 (SITREP이 아닌 경우만)
            global_state.situation_summary_cache.set(situation_info, situation_summary)
        
        # COAResponse 스키마에 맞게 original_request 추가
        result["original_request"] = COAGenerationRequest(
            threat_id=request.situation_id or result.get("threat_id"),
            mission_id=result.get("mission_id"),
            threat_data=None,
            user_params=request.user_params or {}
        ).dict()
        
        # analysis_time 추가
        result["analysis_time"] = datetime.now().isoformat()
        
        # 진행 상황 로그를 응답에 포함
        result["progress_logs"] = progress_logs
        
        return result
        
    except Exception as e:
        logger.error(f"Agent 실행 오류: {e}", exc_info=True)
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Agent 실행 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )
