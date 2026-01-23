# core_pipeline/coa_scorer.py
# -*- coding: utf-8 -*-
"""
COA Scorer
방책(COA) 종합 점수 계산 모듈
팔란티어 방식: 다중 요소 기반 점수 계산
"""
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path

# 관련성 점수 계산을 위한 RelevanceMapper 추가
try:
    from core_pipeline.relevance_mapper import RelevanceMapper
except ImportError:
    RelevanceMapper = None

# 자원 우선순위 파싱을 위한 ResourcePriorityParser 추가
try:
    from core_pipeline.resource_priority_parser import ResourcePriorityParser
except ImportError:
    ResourcePriorityParser = None


class COAScorer:
    """COA 종합 점수 계산기"""
    
    # 평가기준_가중치.xlsx의 기준명 → COAScorer 키 매핑
    CRITERIA_MAPPING = {
        '위험도': 'threat',
        '자원가용성': 'resources',
        '전력능력': 'assets',
        '환경적합성': 'environment',
        '효과성': 'historical',
        '연계성': 'chain',
        '임무부합성': 'mission_alignment'
    }
    
    # 임무 타입과 COA 타입 간 부합성 매트릭스
    MISSION_COA_ALIGNMENT = {
        "공격": {
            "offensive": 1.0,
            "preemptive": 0.8,
            "counter_attack": 0.6,
            "maneuver": 0.5,
            "information_ops": 0.4,
            "defense": 0.2,
            "deterrence": 0.1
        },
        "방어": {
            "defense": 1.0,
            "deterrence": 0.9,
            "counter_attack": 0.7,
            "maneuver": 0.5,
            "information_ops": 0.5,
            "offensive": 0.2,
            "preemptive": 0.3
        },
        "반격": {
            "counter_attack": 1.0,
            "offensive": 0.8,
            "defense": 0.6,
            "maneuver": 0.5,
            "preemptive": 0.4,
            "deterrence": 0.3,
            "information_ops": 0.4
        },
        "기동": {
            "maneuver": 1.0,
            "offensive": 0.7,
            "counter_attack": 0.6,
            "preemptive": 0.5,
            "defense": 0.4,
            "deterrence": 0.3,
            "information_ops": 0.5
        },
        "지연": {
            "defense": 0.9,
            "maneuver": 0.8,
            "deterrence": 0.6,
            "counter_attack": 0.5,
            "information_ops": 0.4,
            "preemptive": 0.2,
            "offensive": 0.1
        },
        "기만": {
            "information_ops": 1.0,
            "maneuver": 0.8,
            "deterrence": 0.6,
            "defense": 0.4,
            "offensive": 0.3,
            "preemptive": 0.3,
            "counter_attack": 0.2
        },
        "방공": {
            "defense": 1.0,
            "preemptive": 0.9,
            "deterrence": 0.7,
            "counter_attack": 0.6,
            "maneuver": 0.4,
            "offensive": 0.2,
            "information_ops": 0.2
        },
        "지원": {
            "maneuver": 0.8,
            "information_ops": 0.7,
            "defense": 0.6,
            "deterrence": 0.5,
            "offensive": 0.4,
            "counter_attack": 0.4,
            "preemptive": 0.3
        }
    }
    
    # 위협 유형과 COA 타입 간 적절성 매트릭스 (8개 위협 유형 지원)
    THREAT_COA_APPROPRIATENESS = {
        "기습공격": {
            "defense": 0.9,  # 기습공격에 대한 방어가 가장 적절
            "counter_attack": 0.8,  # 반격도 효과적
            "preemptive": 0.7,  # 선제 대응 가능
            "deterrence": 0.6,  # 억제 효과
            "maneuver": 0.5,  # 기동으로 대응 가능
            "information_ops": 0.4,  # 정보전으로 대응 가능
            "offensive": 0.2  # 공격은 부적절
        },
        "정면공격": {
            "defense": 0.9,  # 정면공격에 대한 방어가 적절
            "counter_attack": 0.8,  # 반격 효과적
            "deterrence": 0.7,  # 억제 효과
            "maneuver": 0.6,  # 기동으로 우회 가능
            "preemptive": 0.5,  # 선제 대응 가능
            "information_ops": 0.4,  # 정보전으로 대응 가능
            "offensive": 0.3  # 공격은 상대적으로 부적절
        },
        "측면공격": {
            "maneuver": 0.9,  # 측면공격에 대한 기동 대응이 적절
            "defense": 0.8,  # 방어도 효과적
            "counter_attack": 0.7,  # 반격 가능
            "preemptive": 0.6,  # 선제 대응 가능
            "deterrence": 0.5,  # 억제 효과
            "information_ops": 0.4,  # 정보전으로 대응 가능
            "offensive": 0.3  # 공격은 부적절
        },
        "포위공격": {
            "maneuver": 0.9,  # 포위공격에 대한 기동 탈출이 적절
            "defense": 0.8,  # 방어로 버티기
            "counter_attack": 0.7,  # 반격으로 돌파
            "preemptive": 0.6,  # 선제 대응 가능
            "deterrence": 0.5,  # 억제 효과
            "information_ops": 0.4,  # 정보전으로 대응 가능
            "offensive": 0.2  # 공격은 부적절
        },
        "지속공격": {
            "defense": 0.9,  # 지속공격에 대한 방어가 적절
            "deterrence": 0.8,  # 억제로 지속 공격 방지
            "counter_attack": 0.7,  # 반격으로 전환
            "maneuver": 0.6,  # 기동으로 회피
            "preemptive": 0.5,  # 선제 대응 가능
            "information_ops": 0.4,  # 정보전으로 대응 가능
            "offensive": 0.3  # 공격은 상대적으로 부적절
        },
        "정밀타격": {
            "defense": 0.9,  # 정밀타격에 대한 방어가 적절
            "preemptive": 0.8,  # 선제 대응 효과적
            "counter_attack": 0.7,  # 반격 가능
            "information_ops": 0.6,  # 정보전으로 대응 가능
            "deterrence": 0.5,  # 억제 효과
            "maneuver": 0.4,  # 기동으로 회피 가능
            "offensive": 0.2  # 공격은 부적절
        },
        "사이버공격": {
            "information_ops": 1.0,  # 사이버공격에 대한 정보전 대응이 가장 적절
            "defense": 0.8,  # 방어도 효과적
            "preemptive": 0.7,  # 선제 대응 가능
            "deterrence": 0.6,  # 억제 효과
            "counter_attack": 0.5,  # 반격 가능
            "maneuver": 0.3,  # 기동은 부적절
            "offensive": 0.2  # 공격은 부적절
        },
        "화생방공격": {
            "defense": 0.9,  # 화생방공격에 대한 방어가 적절
            "preemptive": 0.8,  # 선제 대응 효과적
            "deterrence": 0.7,  # 억제 효과
            "counter_attack": 0.6,  # 반격 가능
            "information_ops": 0.5,  # 정보전으로 대응 가능
            "maneuver": 0.4,  # 기동으로 회피 가능
            "offensive": 0.2  # 공격은 부적절
        },
        "집결징후": {
            "preemptive": 0.9,  # 집결징후에 대한 선제 공격이 가장 적절
            "offensive": 0.8,  # 공격으로 집결 전 타격
            "information_ops": 0.7,  # 정보전으로 상황 파악
            "deterrence": 0.6,  # 억제로 집결 방지
            "defense": 0.5,  # 방어 준비
            "counter_attack": 0.4,  # 반격 준비
            "maneuver": 0.3  # 기동은 상대적으로 부적절
        },
        "침투": {
            "defense": 0.9,
            "maneuver": 0.8,
            "counter_attack": 0.7,
            "information_ops": 0.6,
            "deterrence": 0.4,
            "preemptive": 0.3,
            "offensive": 0.2
        },
        "포격": {
            "defense": 0.9,
            "preemptive": 0.9,
            "deterrence": 0.8,
            "counter_attack": 0.7,
            "information_ops": 0.6,
            "maneuver": 0.4,
            "offensive": 0.3
        },
        "국지도발": {
            "deterrence": 0.9,
            "defense": 0.8,
            "information_ops": 0.7,
            "counter_attack": 0.6,
            "preemptive": 0.5,
            "maneuver": 0.4,
            "offensive": 0.2
        },
        "전면전": {
            "defense": 0.9,
            "offensive": 0.9,
            "counter_attack": 0.9,
            "maneuver": 0.8,
            "preemptive": 0.7,
            "deterrence": 0.6,
            "information_ops": 0.5
        },
        "사이버": {
            "information_ops": 1.0,
            "defense": 0.8,
            "preemptive": 0.7,
            "deterrence": 0.6,
            "counter_attack": 0.5,
            "maneuver": 0.3,
            "offensive": 0.2
        },
        "공중위협": {
            "defense": 1.0,    # 대공 방어 최우선
            "preemptive": 0.95, # 선제 타격 효과적 (경쟁 유도)
            "deterrence": 0.7, 
            "counter_attack": 0.8, # 반격(대공사격) 효과적
            "maneuver": 0.4,
            "information_ops": 0.3,
            "offensive": 0.3
        },
        "일반적 침입": {
            "defense": 0.8,
            "deterrence": 0.7,
            "maneuver": 0.6,
            "information_ops": 0.5,
            "counter_attack": 0.5,
            "offensive": 0.3,
            "preemptive": 0.3
        },
        "General": {
            "defense": 0.7,
            "deterrence": 0.7,
            "maneuver": 0.6,
            "information_ops": 0.6,
            "counter_attack": 0.5,
            "offensive": 0.5,
            "preemptive": 0.5
        },
        "Intrusion": {
            "defense": 0.9,
            "maneuver": 0.8,
            "counter_attack": 0.7,
            "information_ops": 0.6,
            "deterrence": 0.4,
            "preemptive": 0.3,
            "offensive": 0.2
        },
        "포격": {
            "counter_attack": 1.0, # 대포병 사격
            "preemptive": 0.9,
            "defense": 0.8,
            "maneuver": 0.6,
            "deterrence": 0.5,
            "information_ops": 0.5,
            "offensive": 0.4
        },
        "도하": {
            "counter_attack": 1.0, # 도하 중 타격
            "defense": 0.9, # 강안 방어
            "preemptive": 0.8,
            "maneuver": 0.5,
            "deterrence": 0.4,
            "information_ops": 0.3,
            "offensive": 0.7
        },
        "기만징후": {
            "information_ops": 1.0,
            "preemptive": 0.6,
            "defense": 0.5,
            "deterrence": 0.5,
            "maneuver": 0.4,
            "counter_attack": 0.3,
            "offensive": 0.2
        },
        "포병준비": {
            "preemptive": 1.0, # 선제 타격
            "counter_attack": 0.9,
            "information_ops": 0.8,
            "defense": 0.6,
            "deterrence": 0.5,
            "maneuver": 0.4,
            "offensive": 0.7
        },
        "Shelling": {
            "defense": 0.9,
            "preemptive": 0.9,
            "deterrence": 0.8,
            "counter_attack": 0.7,
            "information_ops": 0.6,
            "maneuver": 0.4,
            "offensive": 0.3
        }
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None,
                 data_manager=None, config: Optional[Dict] = None,
                 coa_type: str = "defense",
                 context: Optional[Dict] = None,
                 relevance_mapper=None,  # [NEW] 주입
                 resource_parser=None):  # [NEW] 주입
        """
        Args:
            weights: 요소별 가중치 딕셔너리 (None이면 평가기준_가중치.xlsx에서 로드)
            data_manager: DataManager 인스턴스 (평가기준_가중치.xlsx 로드용)
            config: 설정 딕셔너리 (data_paths 포함)
            coa_type: 방책 타입 (기본값: "defense")
            context: 컨텍스트 정보 (threat_level, mission_type 등) - 적응형 가중치용
        """
        self.data_manager = data_manager
        self.config = config
        self.coa_type = coa_type
        
        # [FIXED] RelevanceMapper 주입 또는 지연 초기화
        self.relevance_mapper = relevance_mapper
        if self.relevance_mapper is None and RelevanceMapper is not None:
            try:
                # data_lake 경로 결정
                if config and 'data_paths' in config:
                    # config에서 경로 추출
                    base_path = Path(__file__).parent.parent
                    data_lake_path = base_path / "data_lake"
                else:
                    data_lake_path = Path(__file__).parent.parent / "data_lake"
                
                self.relevance_mapper = RelevanceMapper(data_lake_path=str(data_lake_path))
                
                # 통계 로깅
                stats = self.relevance_mapper.get_type_mapping_stats()
                if stats['total_mappings'] > 0:
                    try:
                        from common.utils import safe_print
                        safe_print(
                            f"[INFO] RelevanceMapper 내부 초기화 완료: {stats['total_mappings']}개 매핑 로드됨",
                            logger_name="COAScorer"
                        )
                    except:
                        pass
            except Exception as e:
                pass
        elif self.relevance_mapper is not None:
            # 주입된 경우 로깅 (선택적)
            pass
        
        # [FIXED] ResourcePriorityParser 주입 또는 지연 초기화
        self.resource_parser = resource_parser
        if self.resource_parser is None and ResourcePriorityParser is not None:
            try:
                self.resource_parser = ResourcePriorityParser()
                try:
                    from common.utils import safe_print
                    safe_print(
                        f"[INFO] ResourcePriorityParser 초기화 완료",
                        logger_name="COAScorer"
                    )
                except:
                    pass
            except Exception as e:
                try:
                    from common.utils import safe_print
                    safe_print(
                        f"[WARN] ResourcePriorityParser 초기화 실패: {e}",
                        logger_name="COAScorer"
                    )
                except:
                    pass
        
        # 가중치 설정 (우선순위: manual > context > excel default)
        if weights is not None:
            # 직접 가중치 제공된 경우
            self.weights = weights
        elif context:
            # 🔥 NEW: 컨텍스트 기반 적응형 가중치 계산
            self.weights = self._calculate_adaptive_weights(context, coa_type)
        else:
            # 평가기준_가중치.xlsx에서 로드 시도
            self.weights = self._load_weights_from_excel(coa_type)

    def _calculate_adaptive_weights(self, context: Dict, coa_type: str) -> Dict[str, float]:
        """컨텍스트 기반 적응형 가중치 계산"""
        # 1. Base Weights from Excel/Default
        base_weights = self._load_weights_from_excel(coa_type)
        
        # Context extraction
        threat_level = context.get('threat_level')
        if isinstance(threat_level, (int, float)):
             # normalize if needed (Assuming inputs might be 0-100)
             if threat_level > 1.0: threat_level /= 100.0
        else:
             threat_level = 0.5
             
        mission_type = context.get('mission_type') or context.get('임무유형')
        
        # 2. Adjust based on context
        new_weights = base_weights.copy()
        
        # Case A: High Threat (Survival Priority)
        # 위협 수준이 80% 이상이면 생존 위주로 가중치 재편
        if threat_level >= 0.8:
            new_weights = {
                'threat': 0.40,  # Massive boost
                'mission_alignment': 0.05,
                'resources': 0.20,
                'assets': 0.15,
                'environment': 0.10,
                'historical': 0.10,
                'chain': 0.00
            }
            
            try:
                from common.utils import safe_print
                # safe_print(f"[INFO] 고위협 상황(Level {threat_level:.2f}) 감지: 위협 대응 가중치 상향 (40%)", logger_name="COAScorer")
            except: pass
            
        # Case B: Mission Oriented (Mission Priority)
        # 임무가 명확하면 임무 달성 위주로 가중치 재편
        elif mission_type:
            new_weights = {
                'mission_alignment': 0.35, # Boost
                'threat': 0.20,
                'resources': 0.15,
                'assets': 0.10,
                'environment': 0.10,
                'historical': 0.10,
                'chain': 0.00
            }
            try:
                from common.utils import safe_print
                # safe_print(f"[INFO] 임무 중심 상황({mission_type}) 감지: 임무 부합성 가중치 상향 (35%)", logger_name="COAScorer")
            except: pass
            
        return new_weights
    
    def _load_weights_from_excel(self, coa_type: str = "defense") -> Dict[str, float]:
        """
        평가기준_가중치.xlsx에서 가중치 로드
        
        Returns:
            {키: 가중치} 딕셔너리
        """
        default_weights = {
            'threat': 0.20,
            'resources': 0.15,
            'assets': 0.12,
            'environment': 0.12,
            'historical': 0.12,
            'chain': 0.09,
            'mission_alignment': 0.20  # NEW: 임무-방책 부합성
        }
        
        # 타입별 기본 가중치 정의 (파일 로드 실패 시 폴백용)
        type_defaults = {
            "defense": default_weights,
            "offensive": {'threat': 0.20, 'resources': 0.25, 'assets': 0.25, 'environment': 0.20, 'historical': 0.10, 'chain': 0.0},
            "counter_attack": {'threat': 0.25, 'resources': 0.25, 'assets': 0.20, 'environment': 0.10, 'historical': 0.20, 'chain': 0.0},
            "preemptive": {'threat': 0.20, 'resources': 0.20, 'assets': 0.25, 'environment': 0.20, 'historical': 0.15, 'chain': 0.0},
            "deterrence": {'threat': 0.15, 'resources': 0.15, 'assets': 0.30, 'environment': 0.20, 'historical': 0.20, 'chain': 0.0},
            "maneuver": {'threat': 0.20, 'resources': 0.20, 'assets': 0.20, 'environment': 0.25, 'historical': 0.15, 'chain': 0.0},
            "information_ops": {'threat': 0.15, 'resources': 0.20, 'assets': 0.15, 'environment': 0.20, 'historical': 0.20, 'chain': 0.10}
        }
        
        target_defaults = type_defaults.get(coa_type.lower(), default_weights)
        
        try:
            # data_manager를 통해 로드 시도
            if self.data_manager is not None:
                df = self.data_manager.load_table("평가기준_가중치")
            elif self.config is not None:
                # config에서 직접 경로 가져오기
                data_paths = self.config.get("data_paths", {})
                if "평가기준_가중치" in data_paths:
                    path = Path(data_paths["평가기준_가중치"])
                    if not path.is_absolute():
                        base_dir = Path(__file__).parent.parent
                        path = base_dir / path
                    df = pd.read_excel(str(path))
                else:
                    print("[WARN] 평가기준_가중치 경로를 찾을 수 없습니다. 기본 가중치 사용.")
                    return target_defaults
            else:
                print("[WARN] data_manager 또는 config가 제공되지 않았습니다. 기본 가중치 사용.")
                return target_defaults
            
            # DataFrame에서 가중치 추출
            # TODO: 향후 엑셀 구조가 변경되면 여기서 coa_type에 따른 시트 선택이나 필터링 로직 추가 필요
            # 현재는 단일 시트 구조라고 가정하고, 만약 타입별 컬럼이 없다면 기본 로직 유지
            
            weights = {}
            # 타입별 필터링 로직 (엑셀에 '방책유형' 컬럼이 있다고 가정하거나, 시트가 분리되어 있다고 가정)
            # 현재는 단순화를 위해 기존 로직 유지하되, 추후 확장 가능성 열어둠
            for _, row in df.iterrows():
                criteria = str(row.get('평가요소', row.get('기준', ''))).strip()
                weight_value = float(row.get('가중치', 0.0))
                
                # 기준명을 COAScorer 키로 매핑
                if criteria in self.CRITERIA_MAPPING:
                    key = self.CRITERIA_MAPPING[criteria]
                    weights[key] = weight_value
                elif criteria in self.CRITERIA_MAPPING.values():
                    # 이미 영어 키인 경우 (e.g. 'threat', 'resources')
                    weights[criteria] = weight_value
                else:
                    print(f"[WARN] 알 수 없는 기준명: {criteria}. 건너뜁니다.")
            
            # 매핑되지 않은 키는 기본값 사용
            for key in default_weights:
                if key not in weights:
                    weights[key] = default_weights[key]
                    print(f"[INFO] {key}에 대한 가중치가 없어 기본값({default_weights[key]}) 사용.")
            
            # 가중치 정규화 (총합이 1.0이 되도록)
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}
            
            print(f"[INFO] 평가기준_가중치.xlsx에서 가중치 로드 완료: {weights}")
            return weights
            
        except Exception as e:
            print(f"[WARN] 평가기준_가중치.xlsx 로드 실패: {e}. 기본 가중치 사용.")
            import traceback
            traceback.print_exc()
            return target_defaults
    
    def calculate_score_with_mett_c(self, context: Dict, mett_c_evaluator=None) -> Dict:
        """
        METT-C 평가를 포함한 종합 점수 계산
        
        Args:
            context: COA 컨텍스트 정보
            mett_c_evaluator: METT-C 평가기 (None이면 기본 평가만 수행)
        
        Returns:
            기존 calculate_score 결과 + METT-C 점수
        """
        # 기존 점수 계산
        base_result = self.calculate_score(context)
        
        # METT-C 평가 (있는 경우)
        if mett_c_evaluator:
            try:
                from core_pipeline.mett_c_evaluator import METTCEvaluator
                
                # METT-C 평가기 인스턴스 확인
                if isinstance(mett_c_evaluator, METTCEvaluator):
                    evaluator = mett_c_evaluator
                else:
                    # None이면 기본 평가기 생성
                    evaluator = METTCEvaluator()
                
                # METT-C 점수 계산
                mett_c_score = evaluator.evaluate_coa(
                    coa_context=context,
                    mission=context.get('mission'),
                    enemy_units=context.get('enemy_units'),
                    terrain_cells=context.get('terrain_cells'),
                    friendly_units=context.get('friendly_units'),
                    civilian_areas=context.get('civilian_areas'),  # NEW
                    constraints=context.get('constraints'),
                    axis_states=context.get('axis_states')
                )
                
                # METT-C 점수를 기존 점수에 통합 (선택적)
                # 옵션 1: METT-C 점수를 별도 필드로 추가
                base_result['mett_c'] = mett_c_score.to_dict()
                
                # 옵션 2: METT-C 점수를 기존 점수에 가중치로 반영 (선택적)
                # 사용자가 원하면 활성화
                use_mett_c_weight = context.get('use_mett_c_weight', False)
                if use_mett_c_weight:
                    mett_c_weight = 0.3  # METT-C 점수 가중치
                    base_result['total'] = (
                        base_result['total'] * (1 - mett_c_weight) +
                        mett_c_score.total_score * mett_c_weight
                    )
                    base_result['mett_c_integrated'] = True
                else:
                    base_result['mett_c_integrated'] = False
                    
            except ImportError:
                # METTCEvaluator가 없으면 기본 평가만 수행
                pass
            except Exception as e:
                # METT-C 평가 실패 시 기본 평가만 수행
                try:
                    from common.utils import safe_print
                    safe_print(f"[WARN] METT-C 평가 실패: {e}", logger_name="COAScorer")
                except:
                    pass
        
        return base_result
    
    def calculate_score(self, context: Dict) -> Dict:
        """
        종합 점수 계산
        
        Args:
            context: 컨텍스트 딕셔너리
                - threat_score: 위협 점수 (0-1)
                - resource_availability: 자원 가용성 (0-1)
                - asset_capability: 방어 자산 능력 (0-1)
                - environment_fit: 환경 적합성 (0-1)
                - historical_success: 과거 성공률 (0-1)
                - coa_suitability: COA 적합도 점수 (0-1, 선택적)
        
        Returns:
            {
                'total': 총점 (0-1),
                'breakdown': {
                    'threat': 위협 점수,
                    'resources': 자원 점수,
                    'assets': 자산 점수,
                    'environment': 환경 점수,
                    'historical': 과거 성공률
                }
            }
        """
        scores = {
            'threat': self._calculate_threat_score(context),
            'resources': self._calculate_resource_score(context),
            'assets': self._calculate_asset_score(context),
            'environment': self._calculate_environment_score(context),
            'historical': self._calculate_historical_score(context),
            'chain': self._calculate_chain_score(context),
            'mission_alignment': self._calculate_mission_alignment_score(context)  # NEW
        }
        
        # COA 적합도 점수가 있으면 추가 반영
        coa_suitability = context.get('coa_suitability', 1.0)
        try:
            coa_suitability = float(coa_suitability)
        except (TypeError, ValueError):
            coa_suitability = 1.0
            
        if coa_suitability < 1.0:
            # 적합도 점수를 모든 요소에 곱하여 조정
            for key in scores:
                scores[key] *= coa_suitability
        
        # 가중치 적용하여 총점 계산
        total_score = 0.0
        reasoning_log = []
        
        # 🔥 로그 최적화: 반복되는 DEBUG 로그 제거 (각 COA마다 호출되므로)
        # 디버그 로깅은 필요시에만 활성화 (주석 처리)
        # try:
        #     from common.utils import safe_print
        #     safe_print(f"[DEBUG] 점수 계산 시작: {list(scores.keys())}", logger_name="COAScorer")
        # except:
        #     pass
        
        for key in self.weights:
            score = scores.get(key, 0.0)
            weight = self.weights.get(key, 0.0)
            weighted_score = score * weight
            total_score += weighted_score
            
            # 설명 생성
            reason = self._explain_score(key, score, context)
            
            reasoning_log.append({
                "factor": key,
                "score": round(score, 4),
                "weight": round(weight, 4),
                "weighted_score": round(weighted_score, 4),
                "reason": reason
            })
            
            # 🔥 로그 최적화: 반복되는 DEBUG 로그 제거
            # try:
            #     from common.utils import safe_print
            #     safe_print(f"[DEBUG] {key}: score={score:.4f}, weight={weight:.4f}, weighted={weighted_score:.4f}", logger_name="COAScorer")
            # except:
            #     pass
        
        # 🔥 최종 총점 로깅 (로그 파일과 터미널 일치성 확보)
        try:
            from common.utils import safe_print
            coa_id = context.get('coa_id', context.get('coa_uri', 'Unknown'))
            # COA ID에서 실제 ID만 추출 (URI인 경우)
            if isinstance(coa_id, str) and '#' in coa_id:
                coa_id = coa_id.split('#')[-1]
            safe_print(f"[INFO] COA 점수 계산 완료: COA={coa_id}, 최종총점={total_score:.4f} (위협:{scores.get('threat', 0):.3f}, 자원:{scores.get('resources', 0):.3f}, 환경:{scores.get('environment', 0):.3f}, 과거:{scores.get('historical', 0):.3f}, 체인:{scores.get('chain', 0):.3f}, Mission:{scores.get('mission_alignment', 0):.3f})", logger_name="COAScorer")
        except Exception:
            pass
        
        # Phase 2: 설명 가능성 및 검증 가능성 향상
        # 각 요소별 기여도 계산
        contributions = {}
        for key in self.weights:
            score = scores.get(key, 0.0)
            weight = self.weights.get(key, 0.0)
            weighted_score = score * weight
            contributions[key] = {
                'score': round(score, 4),
                'weight': round(weight, 4),
                'contribution': round(weighted_score, 4),
                'contribution_percent': round((weighted_score / total_score * 100) if total_score > 0 else 0, 2)
            }
        
        # 계산 과정 추적 (검증 가능성)
        trace = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'input': {
                'coa_uri': context.get('coa_uri'),
                'situation_id': context.get('situation_id'),
                'threat_level': context.get('threat_level'),
                'threat_type': context.get('threat_type'),
                'mission_type': context.get('mission_type'),
                'coa_type': context.get('coa_type')
            },
            'weights': {k: round(v, 4) for k, v in self.weights.items()},
            'calculations': reasoning_log,
            'data_sources': self._get_data_sources(context),
            'result': {
                'total_score': round(total_score, 4),
                'breakdown': {k: round(v, 4) for k, v in scores.items()},
                'contributions': contributions
            }
        }
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(scores, context)
        
        # 강점/약점 분석
        strengths, weaknesses = self._identify_strengths_weaknesses(scores, contributions, context)
        
        # 🔥 FIX: 중복 점수 방지를 위한 미세 변동치(Epsilon) 추가
        # 방책 ID의 해시값을 활용하여 동일 조건에서도 미세한 차이를 부여 (정렬 안정성 확보)
        if coa_id := context.get('coa_id', context.get('coa_uri', '')):
            import hashlib
            epsilon = (int(hashlib.md5(str(coa_id).encode()).hexdigest(), 16) % 1000) * 1e-6
            total_score = min(1.0, total_score + epsilon)

        return {
            'total': round(total_score, 4),
            'breakdown': {k: round(v, 4) for k, v in scores.items()},
            'reasoning': reasoning_log,
            'contributions': contributions,  # Phase 2: 기여도 정보
            'trace': trace,  # Phase 2: 계산 과정 추적
            'confidence': confidence,  # Phase 2: 신뢰도
            'strengths': strengths,  # Phase 2: 강점
            'weaknesses': weaknesses  # Phase 2: 약점
        }
    
    def _explain_score(self, factor: str, score: float, context: Dict) -> str:
        """
        점수별 설명 생성 (Week 2 개선)
        
        Args:
            factor: 평가 요소 (threat, resources, etc.)
            score: 계산된 점수 (0-1)
            context: 컨텍스트 정보
            
        Returns:
            자연어 설명 문자열
        """
        if factor == 'threat':
            threat_level = context.get('threat_level')
            if threat_level is not None:
                if isinstance(threat_level, (int, float)) and threat_level > 1.0:
                    level_pct = threat_level
                else:
                    level_pct = (threat_level or 0) * 100
                return f"위협 수준 {level_pct:.0f}%에 대한 대응 점수"
            return f"기본 위협 점수 ({score:.2f})"
            
        elif factor == 'resources':
            res_avail = context.get('resource_availability')
            if res_avail is not None and res_avail != 0.5:
                # context에 값이 명시적으로 있으면 그것을 사용
                return f"자원 가용성 {res_avail*100:.0f}% 반영"
            # 계산된 점수 사용
            return f"자원 가용성 {score*100:.0f}% 반영 (필요자원 매칭)"
            
        elif factor == 'assets':
            assets = context.get('defense_assets', [])
            if assets:
                count = len(assets) if isinstance(assets, list) else 1
                return f"가용 방어 자산 {count}개의 평균 능력치 반영"
            return "자산 정보 부족 (기본값)"
            
        elif factor == 'environment':
            compatible = context.get('environment_compatible')
            if compatible is not None:
                status = "적합" if compatible else "부적합"
                return f"현재 작전 환경에 {status}"
            ratio = context.get('environment_compatibility_ratio')
            if ratio:
                return f"환경 적합률 {ratio*100:.0f}%"
            return "환경 정보 부족 (기본값)"
            
        elif factor == 'historical':
            success_rate = context.get('historical_success')
            if success_rate is not None:
                return f"워게임 모의 분석 승률 {success_rate*100:.0f}%"
            # 🔥 NEW: 예상 성공률 설명
            expected_rate = context.get('expected_success_rate')
            if expected_rate is not None:
                return f"워게임 모의 분석 승률 {float(expected_rate)*100:.0f}% (데이터 기반)"
            return "워게임 데이터 없음 (기본값)"
            
        elif factor == 'chain':
            chain_bonus = context.get('chain_bonus', 0.0)
            if chain_bonus > 0:
                return f"연계 작전 보너스 +{chain_bonus:.2f}"
            return "연계 작전 없음"
            
        return "기본 점수"
    
    def _calculate_threat_score(self, context: Dict) -> float:
        """위협 점수 계산"""
        # threat_level 우선 확인 (threat_score보다 우선)
        threat_level = context.get('threat_level')
        if threat_level is not None:
            if isinstance(threat_level, (int, float)):
                # 0-100 범위를 0-1로 정규화
                if threat_level > 1.0:
                    threat_score = threat_level / 100.0
                else:
                    threat_score = threat_level
            else:
                threat_score = 0.5
        else:
            # threat_level이 없으면 threat_score 확인
            threat_score = context.get('threat_score', 0.0)
            if threat_score == 0.0:
                # 둘 다 없으면 기본값
                threat_score = 0.5
        
        # 디버깅: 위협수준과 계산된 점수 로깅
        if isinstance(threat_level, (int, float)) and threat_level > 0.8:
            print(f"[DEBUG] _calculate_threat_score: threat_level={threat_level}, threat_score={threat_score}")
        
        # 위치 근접도 가중치 적용 (있는 경우)
        location_proximity = context.get('location_proximity', 1.0)
        if location_proximity != 1.0:
            threat_score = min(1.0, threat_score * (1.0 + (location_proximity - 1.0) * 0.2))
        
        return min(1.0, max(0.0, threat_score))
    
    def _calculate_resource_score(self, context: Dict) -> float:
        """자원 가용성 점수 계산 (개선된 스키마 반영)"""
        # 직접 제공된 자원 가용성 사용 (우선순위 1)
        resource_availability = context.get('resource_availability')
        if resource_availability is not None and 'resource_availability' in context and resource_availability != 0.5:
             return min(1.0, max(0.0, resource_availability))
             
        # 리소스 파서가 있으면 고도화된 계산 수행
        if self.resource_parser:
            required_resources = context.get('required_resources', [])
            available_resources = context.get('available_resources', [])
            
            # 마스터 자산 데이터 로드 (매핑용)
            asset_master_data = {}
            if self.data_manager:
                try:
                    df_asset = self.data_manager.load_table('아군가용자산')
                    if df_asset is not None and not df_asset.empty:
                        # 자산ID를 키로 하는 딕셔너리로 변환
                        asset_master_data = df_asset.set_index('자산ID').to_dict('index')
                except Exception as e:
                    print(f"[WARN] 마스터 자산 데이터 로드 실패: {e}")

            # 필요 자원이 문자열 리스트인 경우 파싱 시도 (Library에서 온 경우 등)
            parsed_required = []
            if isinstance(required_resources, list):
                for req in required_resources:
                    if isinstance(req, str):
                        # "자원명(필수)" 형식 파싱
                        parsed = self.resource_parser.parse_resource_priority(req)
                        parsed_required.extend(parsed)
                    elif isinstance(req, dict) and 'resource' in req:
                        parsed_required.append(req)
            
            if parsed_required and available_resources:
                # 1. 리소스 파서를 통한 기본 매칭 및 점수 계산
                score, detail = self.resource_parser.calculate_resource_score_with_priority(
                    parsed_required, 
                    available_resources,
                    asset_master_data=asset_master_data
                )
                
                # 2. [교리적 보완] 계획 상태(Snapshot)와 실시간 상태(Latest) 비교 로직
                # 계획 당시엔 가용했으나 현재 불가해진 자산이 있다면 추가 감점 또는 경고
                mismatch_found = False
                for matched in detail.get('matched', []):
                    asset_id = matched.get('asset_id')
                    plan_status = matched.get('status') # Parser logic takes plan_status first
                    
                    if asset_master_data and asset_id in asset_master_data:
                        latest_status = asset_master_data[asset_id].get('가용상태', '사용가능')
                        if plan_status == '사용가능' and latest_status != '사용가능':
                            mismatch_found = True
                            print(f"[WARN] 자산 상태 불일치 발견: {asset_id} (계획:{plan_status} -> 현재:{latest_status})")
                
                if mismatch_found:
                    # 상태 불일치 시 신뢰도 점수 감점 (예: 5% 감점)
                    score *= 0.95
                    
                return score

        # 폴백: 기존의 단순 매칭 로직 (데이터가 부족하거나 파서 실패 시)
        required_resources = context.get('required_resources', [])
        available_resources = context.get('available_resources', [])
        
        if required_resources and available_resources:
            if isinstance(required_resources, list) and isinstance(available_resources, list):
                # 이름 기반 단순 매칭 (legacy support)
                avail_names = [str(r.get('resource_alias', r.get('resource_name', r))).strip() for r in available_resources]
                matched = [r for r in required_resources if str(r).strip() in avail_names]
                if len(required_resources) > 0:
                    return len(matched) / len(required_resources)
        
        return resource_availability if resource_availability is not None else 0.5
    
    def _calculate_asset_score(self, context: Dict) -> float:
        """방어 자산 능력 점수 계산 (COA별 필요 자원 고려)"""
        # 🔥 FIX: COA별 필요 자원과 가용 자원을 비교하여 점수 계산
        coa_uri = context.get('coa_uri')
        required_resources = context.get('required_resources', [])
        available_resources = context.get('available_resources', [])
        defense_assets = context.get('defense_assets', [])
        
        # COA별 필요 자원이 있으면 가용 자원과 비교
        if coa_uri and required_resources:
            # 자원 매칭률 계산 (resources 점수와 유사한 로직)
            if isinstance(required_resources, list) and len(required_resources) > 0:
                if isinstance(available_resources, list) and len(available_resources) > 0:
                    # 리스트 매칭
                    matched = set(required_resources) & set(available_resources)
                    match_ratio = len(matched) / len(required_resources) if len(required_resources) > 0 else 1.0
                    # 매칭률을 asset_capability로 사용
                    asset_capability = match_ratio
                else:
                    # 가용 자원이 없으면 낮은 점수
                    asset_capability = 0.2
            else:
                # 필요 자원이 없으면 기본값 사용
                asset_capability = context.get('asset_capability', 0.5)
        else:
            # 직접 제공된 자산 능력 사용
            asset_capability = context.get('asset_capability', 0.5)
        
        # 자산 정보가 있으면 계산 (기존 로직 유지)
        if asset_capability == 0.5 or (coa_uri and not required_resources):
            defense_assets = context.get('defense_assets', [])
            
            if defense_assets:
                if isinstance(defense_assets, list):
                    # 리스트인 경우 평균 화력/사기 계산
                    firepowers = []
                    morales = []
                    
                    for asset in defense_assets:
                        if isinstance(asset, dict):
                            if 'firepower' in asset:
                                firepowers.append(float(asset['firepower']))
                            if 'morale' in asset:
                                morales.append(float(asset['morale']))
                        elif isinstance(asset, (int, float)):
                            firepowers.append(float(asset))
                    
                    if firepowers:
                        avg_firepower = sum(firepowers) / len(firepowers)
                        asset_capability = avg_firepower / 100.0  # 0-1 정규화
                    elif morales:
                        avg_morale = sum(morales) / len(morales)
                        asset_capability = avg_morale / 100.0
                elif isinstance(defense_assets, dict):
                    # 딕셔너리인 경우
                    firepower = defense_assets.get('firepower', 50)
                    morale = defense_assets.get('morale', 50)
                    asset_capability = ((firepower + morale) / 2) / 100.0
                elif isinstance(defense_assets, (int, float)):
                    asset_capability = float(defense_assets) / 100.0
        
        return min(1.0, max(0.0, asset_capability))
    
    def _calculate_environment_score(self, context: Dict) -> float:
        """환경 적합성 점수 계산"""
        # 직접 제공된 환경 적합성 사용
        environment_fit = context.get('environment_fit', 0.5)
        
        # 환경 정보가 있으면 계산
        if environment_fit == 0.5:
            # 환경 호환 여부 확인
            is_compatible = context.get('environment_compatible', False)
            if is_compatible:
                environment_fit = 1.0
            else:
                # 부분 호환
                # 부분 호환
                compatibility_ratio = context.get('environment_compatibility_ratio', 0.5)
                environment_fit = compatibility_ratio
            
            # 🔥 NEW: 텍스트 기반 제약조건 확인
            env_constraints = context.get('environmental_constraints', '')
            if env_constraints and env_constraints != 'nan':
                # 현재 환경 정보 (context에 environment_info가 있다고 가정)
                current_env = context.get('environment_info', {})
                # 간단한 키워드 매칭 (예: "강풍"이 제약인데 현재 "강풍"이면 감점)
                # 실제로는 더 복잡한 로직이 필요하지만 예시로 구현
                if "강풍" in env_constraints and current_env.get("wind_speed", 0) > 10:
                     environment_fit = max(0.1, environment_fit - 0.3)
                if "험지" in env_constraints and current_env.get("terrain") == "mountain":
                     environment_fit = max(0.1, environment_fit - 0.2)
        
        return min(1.0, max(0.0, environment_fit))
    
    def _calculate_historical_score(self, context: Dict) -> float:
        """
        과거 성공률 점수 계산
        
        설계 문서 우선순위 (docs/coa_recommendation_process.md):
        1. Excel의 예상성공률 사용 (expected_success_rate from 워게임_모의_분석_승률)
        2. RAG 검색 결과에서 키워드 기반 계산
        3. Fallback: 0.5 (중립)
        """
        # 직접 제공된 과거 성공률 사용 (최우선)
        historical_success = context.get('historical_success')
        if historical_success is not None:
            return min(1.0, max(0.0, float(historical_success)))
        
        # 우선순위 1: Excel의 예상성공률 사용 (워게임_모의_분석_승률)
        # 설계 문서: expected_success_rate가 있으면 무조건 사용
        expected_rate = context.get('expected_success_rate')
        if expected_rate is not None:
            try:
                expected_rate_float = float(expected_rate)
                # expected_success_rate가 있으면 무조건 사용 (설계 문서 부합)
                try:
                    from common.utils import safe_print
                    safe_print(f"[INFO] 과거 성공률: 워게임_모의_분석_승률 사용 = {expected_rate_float:.3f}", logger_name="COAScorer")
                except:
                    pass
                return min(1.0, max(0.0, expected_rate_float))
            except (ValueError, TypeError):
                pass
        
        # 우선순위 2: RAG 검색 결과에서 키워드 기반 계산
        # expected_success_rate가 없을 때만 사용
        rag_results = context.get('rag_results', [])
        if rag_results:
            # 성공 사례 비율 계산
            success_keywords = ['성공', '효과적', '승리', '완료', '달성']
            success_count = 0
            
            for result in rag_results:
                if isinstance(result, dict):
                    text = result.get('text', '')
                else:
                    text = str(result)
                
                if any(keyword in text for keyword in success_keywords):
                    success_count += 1
            
            if len(rag_results) > 0:
                historical_success = success_count / len(rag_results)
                try:
                    from common.utils import safe_print
                    safe_print(f"[INFO] 과거 성공률: RAG 검색 결과 사용 = {historical_success:.3f} ({success_count}/{len(rag_results)})", logger_name="COAScorer")
                except:
                    pass
                return min(1.0, max(0.0, historical_success))
        
        # 우선순위 3: Fallback (기본값)
        try:
            from common.utils import safe_print
            safe_print("[WARN] 과거 성공률: 데이터 없음, 기본값 0.5 사용", logger_name="COAScorer")
        except:
            pass
        return 0.5
    
    def _calculate_chain_score(self, context: Dict) -> float:
        """
        체인 점수 계산 (개선: 팔란티어 방식 - 품질 및 관련성 기반)
        """
        # 직접 제공된 체인 점수 사용 (우선순위 1)
        chain_score = context.get('chain_score')
        chain_score_provided = 'chain_score' in context
        
        # chain_score가 명시적으로 제공되지 않았거나 기본값(0.5)인 경우에만 재계산 시도
        if not chain_score_provided or chain_score == 0.5:
            chain_info = context.get('chain_info', {})
            if chain_info:
                chains = chain_info.get('chains', [])
                if chains:
                    # 팔란티어 방식: 다차원 평가
                    # 1. 체인 개수 기반 점수 (40% 가중치)
                    chain_count = len(chains)
                    count_score = min(1.0, 0.5 + (chain_count * 0.05))  # 0.5~1.0 (10개 이상이면 1.0)
                    
                    # 2. 체인 품질 기반 점수 (40% 가중치)
                    quality_scores = []
                    for chain in chains:
                        # 체인의 평균 신뢰도 (있는 경우)
                        avg_confidence = chain.get('avg_confidence', chain.get('confidence', 0.5))
                        if isinstance(avg_confidence, (int, float)):
                            quality_scores.append(float(avg_confidence))
                        else:
                            quality_scores.append(0.5)
                    
                    quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
                    
                    # 3. 체인 관련성 기반 점수 (20% 가중치)
                    # RelevanceMapper를 사용한 관련성 계산 (개선)
                    relevance_score = 0.0
                    
                    # RelevanceMapper 사용 가능 여부 확인
                    use_relevance_mapper = hasattr(self, 'relevance_mapper') and self.relevance_mapper
                    
                    if use_relevance_mapper:
                        # COA 정보 추출
                        coa_type = context.get('coa_type', '')
                        coa_id = context.get('coa_id', context.get('coa_uri', ''))  
                        if isinstance(coa_id, str) and '#' in coa_id:
                            coa_id = coa_id.split('#')[-1]
                        
                        # 위협 정보 추출
                        threat_type = context.get('threat_type', '')
                        threat_id = context.get('threat_id', context.get('situation_id', ''))
                        
                        # 키워드 추출 (있으면)
                        coa_keywords = set()
                        threat_keywords = set()
                        
                        # COA 키워드 (context에서 또는 체인에서 추출)
                        coa_keywords_raw = context.get('coa_keywords', [])
                        if isinstance(coa_keywords_raw, (list, set)):
                            coa_keywords = set(str(k).lower() for k in coa_keywords_raw if k)
                        
                        # 위협 키워드
                        threat_keywords_raw = context.get('threat_keywords', [])
                        if isinstance(threat_keywords_raw, (list, set)):
                            threat_keywords = set(str(k).lower() for k in threat_keywords_raw if k)
                        
                        # RelevanceMapper로 점수 계산
                        if coa_type and threat_type:
                            try:
                                relevance_score = self.relevance_mapper.get_relevance_score(
                                    coa_id=coa_id,
                                    coa_type=coa_type,
                                    threat_id=threat_id,
                                    threat_type=threat_type,
                                    coa_keywords=coa_keywords if coa_keywords else None,
                                    threat_keywords=threat_keywords if threat_keywords else None
                                )
                                
                                # 성공 로깅 (첫 번째 COA에서만)
                                if context.get('is_first_coa', False):
                                    try:
                                        from common.utils import safe_print
                                        safe_print(
                                            f"[INFO] RelevanceMapper 사용: COA={coa_type}, Threat={threat_type}, "
                                            f"Score={relevance_score:.3f}",
                                            logger_name="COAScorer"
                                        )
                                    except:
                                        pass
                            except Exception as e:
                                # RelevanceMapper 실패 시 fallback
                                if context.get('is_first_coa', False):
                                    try:
                                        from common.utils import safe_print
                                        safe_print(
                                            f"[WARN] RelevanceMapper 실패, fallback 사용: {e}",
                                            logger_name="COAScorer"
                                        )
                                    except:
                                        pass
                                relevance_score = 0.5
                        else:
                            relevance_score = 0.5
                    else:
                        # Fallback: 기존 방식 (위협 URI/ID 기반)
                        situation_id = context.get('situation_id', '')
                        threat_uri = context.get('threat_uri', '')
                        relevance_count = 0
                        
                        for chain in chains:
                            chain_path = str(chain.get('path', ''))
                            chain_nodes = chain.get('nodes', [])
                            # 위협 URI나 상황 ID가 체인에 포함되어 있는지 확인
                            if situation_id and situation_id in chain_path:
                                relevance_count += 1
                            elif threat_uri and threat_uri in chain_path:
                                relevance_count += 1
                            elif chain_nodes:
                                # 체인 노드에 위협 관련 노드가 있는지 확인
                                for node in chain_nodes:
                                    node_str = str(node)
                                    if situation_id in node_str or threat_uri in node_str:
                                        relevance_count += 1
                                        break
                        
                        relevance_score = relevance_count / len(chains) if chains else 0.0
                    
                    # 4. 가중 합산
                    final_score = (
                        count_score * 0.4 +
                        quality_score * 0.4 +
                        relevance_score * 0.2
                    )
                    
                    chain_score = final_score
                    
                    # 디버깅 로그 (첫 번째 COA에서만)
                    if context.get('is_first_coa', False):
                        try:
                            from common.utils import safe_print
                            safe_print(f"[INFO] 체인 점수 계산: 개수={chain_count} (점수={count_score:.2f}), 품질={quality_score:.2f}, 관련성={relevance_score:.2f} → 최종={final_score:.2f}", logger_name="COAScorer")
                        except:
                            pass
                else:
                    # 체인 정보는 있지만 체인이 없으면 summary 확인
                    chain_summary = chain_info.get('summary', {})
                    avg_score = chain_summary.get('avg_score')
                    if avg_score is not None and avg_score != 0.5:
                        chain_score = float(avg_score)
                    else:
                        chain_score = 0.3  # 체인 없으면 낮은 점수 (기존 0.5에서 0.3으로 변경)
            else:
                chain_score = 0.3  # 체인 정보 없으면 낮은 점수
        
        if chain_score is None:
            chain_score = 0.3  # 기본값도 낮은 점수로 변경
        
        return min(1.0, max(0.0, chain_score))
    
    def _calculate_mission_alignment_score(self, context: Dict) -> float:
        """임무-방책 타입 부합성 점수 계산 (위협 유형 적절성 반영)"""
        import random
        call_id = f"{random.randint(1000, 9999)}"
        mission_type = context.get('mission_type')
        coa_type = context.get('coa_type')
        threat_type = context.get('threat_type')
        coa_id = context.get('coa_id', 'unknown')
        
        # 위협 유형 적절성 점수 계산 (60% 가중치)
        threat_appropriateness_score = 0.5  # 기본값
        if threat_type and coa_type:
            # 위협 유형 정규화 (대소문자 무시, 공백/언더스코어/하이픈 제거)
            def normalize_text(text):
                """텍스트 정규화: 공백, 언더스코어, 하이픈 제거 및 소문자 변환"""
                if not text:
                    return ""
                return str(text).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            
            threat_type_normalized = normalize_text(threat_type)
            
            # 🔥 개선: 더 유연한 매칭 알고리즘
            threat_matrix = None
            best_match_key = None
            best_match_score = 0.0
            
            for key in self.THREAT_COA_APPROPRIATENESS.keys():
                key_normalized = normalize_text(key)
                
                # 1. 완전 일치 (최우선)
                if key_normalized == threat_type_normalized:
                    threat_matrix = self.THREAT_COA_APPROPRIATENESS.get(key, {})
                    best_match_key = key
                    best_match_score = 1.0
                    break
                
                # 2. 포함 관계 확인 (부분 매칭)
                if threat_type_normalized in key_normalized or key_normalized in threat_type_normalized:
                    # 더 긴 문자열이 포함된 경우 우선순위 높음
                    match_score = min(len(threat_type_normalized), len(key_normalized)) / max(len(threat_type_normalized), len(key_normalized))
                    if match_score > best_match_score:
                        threat_matrix = self.THREAT_COA_APPROPRIATENESS.get(key, {})
                        best_match_key = key
                        best_match_score = match_score
                
                # 3. 공통 문자 비율 계산 (유사도 기반 매칭)
                common_chars = set(threat_type_normalized) & set(key_normalized)
                if common_chars:
                    similarity = len(common_chars) / max(len(set(threat_type_normalized)), len(set(key_normalized)), 1)
                    # 유사도가 0.7 이상이고 기존 매칭보다 좋으면 업데이트
                    if similarity >= 0.7 and similarity > best_match_score:
                        threat_matrix = self.THREAT_COA_APPROPRIATENESS.get(key, {})
                        best_match_key = key
                        best_match_score = similarity
            
            if threat_matrix and best_match_key:
                # Normalize coa_type for matrix lookup
                coa_type_norm = str(coa_type).lower().strip()
                threat_appropriateness_score = threat_matrix.get(coa_type_norm, 0.5)
                # 매칭 성공 시 로그
                try:
                    from common.utils import safe_print
                    safe_print(f"[INFO][{call_id}][COA:{coa_id}] 위협 매칭: '{threat_type}'(norm='{threat_type_normalized}') -> '{best_match_key}', COA='{coa_type}'(norm='{coa_type_norm}') -> weight: {threat_appropriateness_score:.2f}", logger_name="COAScorer")
                except:
                    pass
            else:
                # 매칭 실패 시 기본값 사용
                try:
                    from common.utils import safe_print
                    safe_print(f"[INFO][{call_id}][COA:{coa_id}] 위협 매칭 실패: '{threat_type}', COA='{coa_type}' -> defaults to 0.5", logger_name="COAScorer")
                except:
                    pass
        
        # [NEW] COA Library Suitability Check (엑셀 기반 정밀 적합성)
        # 엑셀의 '적합위협유형' 컬럼을 활용하여 특화 방책 우대 및 범용 방책 독주 방지
        coa_suitability = str(context.get('coa_suitability', '')).strip()
        suitability_bonus = 0.0
        
        if coa_suitability and coa_suitability.lower() != 'nan':
             # 적합 위협이 명시된 경우
             threat_norm = normalize_text(threat_type)
             suit_norm = normalize_text(coa_suitability)
             
             # 적합성에 현재 위협이 포함되어 있는지 확인 (여러 개일 수 있음, 콤마 구분 등)
             if threat_norm in suit_norm or suit_norm in threat_norm:
                 suitability_bonus = 0.25 # 특화 방책 보너스 (강력)
                 try:
                     from common.utils import safe_print
                     safe_print(f"[INFO][Match] {coa_id} is explicitly suitable for {threat_type} (+0.25)", logger_name="COAScorer")
                 except:
                     pass
             else:
                 # 🔥 FIX: 부적합 페널티 완화 (-0.3 -> -0.15) 및 범용 방책 예외 처리
                 suit_lower = suit_norm.lower()
                 if any(x in suit_lower for x in ['범용', 'common', 'all', '1.0']):
                     suitability_bonus = -0.05
                 else:
                     suitability_bonus = -0.15
                 try:
                     from common.utils import safe_print
                     safe_print(f"[INFO][Mismatch] {coa_id} targets '{coa_suitability}', not '{threat_type}' (bonus: {suitability_bonus})", logger_name="COAScorer")
                 except:
                     pass
        else:
             # 적합 위협이 없는 경우 (범용 방책)
             # 범용 방책(후방지역 방호 등)이 모든 상황에서 1위를 차지하는 것을 방지하기 위해 미세 패널티 부여
             suitability_bonus = -0.05 
             
        threat_appropriateness_score = min(1.0, max(0.0, threat_appropriateness_score + suitability_bonus))
        
        # 위협 수준 및 단계 반영 (개선: 팔란티어 방식)
        threat_level = context.get('threat_level', 0.5)
        threat_stage = context.get('threat_stage', None)  # '징후', '준비', '실행', '완료'
        
        # 위협 수준이 높을수록 방어/반격이 더 적절
        if isinstance(threat_level, (int, float)):
            if threat_level > 0.7:  # 높은 위협 수준
                if coa_type in ['defense', 'counter_attack']:
                    threat_appropriateness_score = min(1.0, threat_appropriateness_score + 0.1)
                elif coa_type in ['offensive', 'preemptive']:
                    threat_appropriateness_score = max(0.0, threat_appropriateness_score - 0.1)
            elif threat_level < 0.3:  # 낮은 위협 수준
                if coa_type in ['preemptive', 'deterrence']:
                    threat_appropriateness_score = min(1.0, threat_appropriateness_score + 0.1)
        
        # 위협 단계 반영 (NEW)
        if threat_stage:
            threat_stage_lower = str(threat_stage).lower()
            if threat_stage_lower in ['징후', '징후단계', 'indication']:
                # 선제 공격이 더 적절
                if coa_type == 'preemptive':
                    threat_appropriateness_score = min(1.0, threat_appropriateness_score + 0.2)
                elif coa_type == 'defense':
                    threat_appropriateness_score = min(1.0, threat_appropriateness_score + 0.1)
            elif threat_stage_lower in ['실행', '실행단계', 'execution']:
                # 방어가 더 적절
                if coa_type == 'defense':
                    threat_appropriateness_score = min(1.0, threat_appropriateness_score + 0.2)
                elif coa_type == 'preemptive':
                    threat_appropriateness_score = max(0.0, threat_appropriateness_score - 0.1)
            elif threat_stage_lower in ['준비', '준비단계', 'preparation']:
                # 선제 공격 또는 방어 준비
                if coa_type in ['preemptive', 'defense']:
                    threat_appropriateness_score = min(1.0, threat_appropriateness_score + 0.1)
        
        # 임무 부합성 점수 계산 (40% 가중치)
        mission_alignment_score = 0.5  # 기본값
        if mission_type and coa_type:
            # Normalize coa_type for matrix lookup
            coa_type_norm = str(coa_type).lower().strip()
            alignment_matrix = self.MISSION_COA_ALIGNMENT.get(mission_type, {})
            mission_alignment_score = alignment_matrix.get(coa_type_norm, 0.5)
            try:
                from common.utils import safe_print
                safe_print(f"[INFO][{call_id}][COA:{coa_id}] 미션 매칭 결과: '{mission_type}' + COA='{coa_type}' -> weight: {mission_alignment_score:.2f}", logger_name="COAScorer")
            except:
                pass
        
        # 가중 평균 계산: 위협 유형 적절성 60%, 임무 부합성 40%
        final_score = (threat_appropriateness_score * 0.6) + (mission_alignment_score * 0.4)
        
        # 위협 수준/단계 반영 정보 로깅 (첫 번째 COA에서만)
        if context.get('is_first_coa', False) and (threat_level != 0.5 or threat_stage):
            try:
                from common.utils import safe_print
                adjustment_info = []
                if threat_level != 0.5:
                    adjustment_info.append(f"위협수준={threat_level:.2f}")
                if threat_stage:
                    adjustment_info.append(f"위협단계={threat_stage}")
                if adjustment_info:
                    safe_print(f"[INFO] 위협 특성 반영: {', '.join(adjustment_info)} → 최종 적절성: {threat_appropriateness_score:.2f}", logger_name="COAScorer")
            except:
                pass
        
        try:
            from common.utils import safe_print
            safe_print(f"[INFO][{call_id}][COA:{coa_id}] Mission-COA Alignment Score: 위협 적절성({threat_appropriateness_score:.2f}*0.6) + 임무 부합성({mission_alignment_score:.2f}*0.4) = {final_score:.2f}", logger_name="COAScorer")
        except:
            pass
        
        return min(1.0, max(0.0, final_score))
    
    def _get_data_sources(self, context: Dict) -> List[Dict]:
        """
        사용된 데이터 소스 목록 반환 (검증 가능성)
        
        Returns:
            데이터 소스 목록 (테이블명, 컬럼, 사용 여부 등)
        """
        data_sources = []
        
        # 위협 점수 데이터 소스
        if context.get('threat_score') is not None or context.get('threat_level') is not None:
            data_sources.append({
                'factor': 'threat',
                'source': '위협상황',
                'columns': ['위협수준', '위협유형'],
                'used': True
            })
        
        # 자원 가용성 데이터 소스
        if context.get('resource_availability') is not None:
            data_sources.append({
                'factor': 'resources',
                'source': '아군부대현황, 아군가용자산',
                'columns': ['병종', '제대', '자산종류'],
                'used': True
            })
        
        # 환경 적합성 데이터 소스
        if context.get('environment_fit') is not None:
            data_sources.append({
                'factor': 'environment',
                'source': '기상상황, COA_Library',
                'columns': ['기상유형', '환경호환성', '환경비호환성'],
                'used': True
            })
        
        # 과거 성공률 데이터 소스
        if context.get('historical_success') is not None or context.get('expected_success_rate') is not None:
            data_sources.append({
                'factor': 'historical',
                'source': '워게임_모의_분석_승률',
                'columns': ['예상성공률'],
                'used': True
            })
        
        # 체인 점수 데이터 소스
        if context.get('chain_info') is not None:
            data_sources.append({
                'factor': 'chain',
                'source': '온톨로지 관계 체인',
                'columns': ['관계 경로'],
                'used': True
            })
        
        return data_sources
    
    def _calculate_confidence(self, scores: Dict[str, float], context: Dict) -> float:
        """
        신뢰도 계산 (데이터 품질 및 완전성 기반)
        
        Returns:
            신뢰도 점수 (0.0~1.0)
        """
        confidence_factors = []
        
        # 1. 데이터 완전성 (각 점수가 기본값이 아닌지 확인)
        default_values = {
            'threat': 0.5,
            'resources': 0.5,
            'environment': 0.5,
            'historical': 0.5,
            'chain': 0.5,
            'mission_alignment': 0.5
        }
        
        data_completeness = 0.0
        total_factors = 0
        for key, default_value in default_values.items():
            score = scores.get(key, default_value)
            total_factors += 1
            # 기본값이 아니면 데이터가 있다고 간주
            if abs(score - default_value) > 0.01:
                data_completeness += 1.0
        
        if total_factors > 0:
            data_completeness = data_completeness / total_factors
        confidence_factors.append(data_completeness * 0.4)  # 40% 가중치
        
        # 2. 점수 분산 (점수가 극단적이지 않은지 확인)
        score_values = [v for v in scores.values() if isinstance(v, (int, float))]
        if len(score_values) > 1:
            score_range = max(score_values) - min(score_values)
            # 점수 범위가 적절하면 신뢰도 높음 (0.3~0.7 범위가 이상적)
            if 0.2 <= score_range <= 0.8:
                variance_score = 1.0
            elif score_range < 0.2:
                variance_score = 0.7  # 점수 차이가 너무 작음
            else:
                variance_score = 0.8  # 점수 차이가 큼
            confidence_factors.append(variance_score * 0.3)  # 30% 가중치
        else:
            confidence_factors.append(0.5 * 0.3)
        
        # 3. 컨텍스트 정보 완전성
        context_keys = ['coa_uri', 'situation_id', 'threat_type', 'mission_type']
        context_completeness = sum(1 for key in context_keys if context.get(key) is not None) / len(context_keys)
        confidence_factors.append(context_completeness * 0.3)  # 30% 가중치
        
        # 최종 신뢰도
        confidence = sum(confidence_factors)
        return min(1.0, max(0.0, confidence))
    
    def _identify_strengths_weaknesses(self, scores: Dict[str, float], contributions: Dict[str, Dict], context: Dict) -> tuple:
        """
        강점 및 약점 분석
        
        Returns:
            (strengths: List[str], weaknesses: List[str])
        """
        strengths = []
        weaknesses = []
        
        # 각 요소별 임계값
        thresholds = {
            'threat': 0.6,
            'resources': 0.5,
            'assets': 0.5,
            'environment': 0.5,
            'historical': 0.6,
            'chain': 0.5,
            'mission_alignment': 0.6
        }
        
        factor_names = {
            'threat': '위협 대응',
            'resources': '자원 가용성',
            'assets': '자산 능력',
            'environment': '환경 적합성',
            'historical': '과거 성공률',
            'chain': '연계 작전',
            'mission_alignment': '임무 부합성'
        }
        
        for key, score in scores.items():
            factor_name = factor_names.get(key, key)
            threshold = thresholds.get(key, 0.5)
            
            if score >= threshold + 0.1:  # 임계값보다 0.1 이상 높으면 강점
                contribution = contributions.get(key, {}).get('contribution_percent', 0)
                strengths.append(f"{factor_name} 점수가 높음 ({score:.2f}, 기여도: {contribution:.1f}%)")
            elif score <= threshold - 0.1:  # 임계값보다 0.1 이상 낮으면 약점
                contribution = contributions.get(key, {}).get('contribution_percent', 0)
                weaknesses.append(f"{factor_name} 점수가 낮음 ({score:.2f}, 기여도: {contribution:.1f}%)")
        
        # 특별한 경우 분석
        if scores.get('resources', 0.5) < 0.3:
            weaknesses.append("자원 가용성이 매우 낮아 실행 가능성에 의문")
        
        if scores.get('environment', 0.5) < 0.4:
            weaknesses.append("환경 적합성이 낮아 현실성에 제약")
        
        if scores.get('mission_alignment', 0.5) > 0.7:
            strengths.append("임무와의 부합성이 높아 적절한 선택")
        
        if scores.get('historical', 0.5) > 0.8:
            strengths.append("과거 성공률이 높아 검증된 방책")
        
        return strengths, weaknesses
    
    def update_weights(self, new_weights: Dict[str, float]):
        """가중치 업데이트"""
        self.weights.update(new_weights)
    
    def get_weights(self) -> Dict[str, float]:
        """현재 가중치 반환"""
        return self.weights.copy()
    
    def compare_alternatives(self, coa_results: List[Dict], top_n: int = 3) -> Dict:
        """
        대안 분석: 상위 COA 비교 및 장단점 분석
        
        Args:
            coa_results: COA 평가 결과 리스트 (각각 calculate_score 결과 포함)
            top_n: 비교할 상위 COA 개수
        
        Returns:
            {
                'top_coas': 상위 COA 목록,
                'comparison': 비교 분석,
                'recommendations': 추천 사항
            }
        """
        if not coa_results:
            return {
                'top_coas': [],
                'comparison': {},
                'recommendations': []
            }
        
        # 점수 기준으로 정렬 (타입 안전성 확보)
        sorted_coas = sorted(
            coa_results, 
            key=lambda x: (
                float(x.get('total', 0) or 0), 
                str(x.get('coa_id') or x.get('coa_name') or '')
            ), 
            reverse=True
        )
        top_coas = sorted_coas[:top_n]
        
        if not top_coas:
            return {
                'top_coas': [],
                'comparison': {},
                'recommendations': []
            }
        
        # 비교 분석
        comparison = {
            'score_range': {
                'min': min(c.get('total', 0) for c in sorted_coas),
                'max': max(c.get('total', 0) for c in sorted_coas),
                'avg': sum(c.get('total', 0) for c in sorted_coas) / len(sorted_coas) if sorted_coas else 0
            },
            'top_coas': []
        }
        
        for i, coa in enumerate(top_coas, 1):
            coa_info = {
                'rank': i,
                'coa_id': coa.get('coa_id', 'Unknown'),
                'coa_name': coa.get('coa_name', 'Unknown'),
                'total_score': coa.get('total', 0),
                'breakdown': coa.get('breakdown', {}),
                'strengths': coa.get('strengths', []),
                'weaknesses': coa.get('weaknesses', []),
                'confidence': coa.get('confidence', 0.5)
            }
            comparison['top_coas'].append(coa_info)
        
        # 추천 사항 생성
        recommendations = []
        
        if len(top_coas) >= 2:
            top_score = top_coas[0].get('total', 0)
            second_score = top_coas[1].get('total', 0)
            
            if top_score - second_score < 0.05:
                recommendations.append("상위 COA 간 점수 차이가 작아 상황에 따라 선택 가능")
            elif top_score - second_score > 0.15:
                recommendations.append("최상위 COA가 다른 대안보다 현저히 우수함")
        
        # 각 COA의 강점/약점 기반 추천
        for coa in top_coas[:2]:  # 상위 2개만
            coa_name = coa.get('coa_name', 'Unknown')
            strengths = coa.get('strengths', [])
            weaknesses = coa.get('weaknesses', [])
            
            if strengths:
                recommendations.append(f"{coa_name}: {', '.join(strengths[:2])}")
            if weaknesses:
                recommendations.append(f"{coa_name} 주의사항: {', '.join(weaknesses[:2])}")
        
        return {
            'top_coas': comparison['top_coas'],
            'comparison': comparison,
            'recommendations': recommendations
        }

