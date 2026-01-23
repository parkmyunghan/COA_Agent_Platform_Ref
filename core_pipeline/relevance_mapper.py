"""
관련성 점수 계산을 위한 RelevanceMapper 클래스
3-Tier 전략: 핵심 조합 → 유형 레벨 → 키워드 유사도
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Set
import logging

class RelevanceMapper:
    """COA-위협 관련성 점수 계산 클래스"""
    
    def __init__(self, data_lake_path: str = "data_lake"):
        self.data_lake_path = Path(data_lake_path)
        self.logger = logging.getLogger(__name__)
        
        # [NEW] 위협 마스터 데이터 로드 (코드 정규화용) - 다른 로드보다 먼저 실행되어야 함
        self.threat_master_map = self._load_threat_master()
        
        # Tier 1: 유형 레벨 매핑 로딩
        self.type_mapping = self._load_type_mapping()
        
        # Tier 2: 핵심 조합 매핑 (있으면 로딩)
        self.critical_mapping = self._load_critical_mapping()
        
        # COA 유형 캐시
        self.coa_type_cache = {}
        
    def _load_threat_master(self) -> dict:
        """위협 마스터 데이터 로드 (이름 -> 코드 매핑)"""
        mapping = {}
        try:
            # DataManager를 사용하지 않고 직접 로드 (순환 참조 방지 및 독립성 유지)
            master_path = self.data_lake_path / "위협유형_마스터.xlsx"
            if master_path.exists():
                df = pd.read_excel(master_path)
                for _, row in df.iterrows():
                    code = str(row.get('위협유형코드', '')).strip()
                    name = str(row.get('위협유형명', '')).strip()
                    if code and name:
                        mapping[name] = code
                        # 코드 자체도 매핑 (code -> code)
                        mapping[code] = code
                self.logger.info(f"위협 마스터 매핑 로드 완료: {len(mapping)}개 항목")
            else:
                self.logger.warning(f"위협 마스터 파일 없음: {master_path}")
        except Exception as e:
            self.logger.warning(f"위협 마스터 로드 실패: {e}")
            
        return mapping

    def _normalize_threat_type(self, threat_type: str) -> str:
        """위협 유형을 코드로 정규화 (이름 -> 코드)"""
        if not threat_type:
            return threat_type
            
        key = str(threat_type).strip()
        
        # 마스터 맵에 있으면 코드로 반환
        if key in self.threat_master_map:
            return self.threat_master_map[key]
            
        # 없으면 그대로 반환 (이미 코드이거나 매핑되지 않은 값)
        return key
        
    def _load_type_mapping(self) -> pd.DataFrame:
        """유형 레벨 관련성 매핑 로딩"""
        file_path = self.data_lake_path / "방책유형_위협유형_관련성.xlsx"
        
        try:
            df = pd.read_excel(file_path)
            
            # [NEW] 위협 유형을 코드로 정규화 (데이터 로드 시점)
            if 'threat_type' in df.columns and self.threat_master_map:
                original_count = len(df)
                df['threat_type_original'] = df['threat_type']  # 원본 보존
                df['threat_type'] = df['threat_type'].apply(self._normalize_threat_type)
                self.logger.info("관련성 테이블의 위협 유형을 코드로 정규화했습니다.")
            
            self.logger.info(f"유형 레벨 매핑 로드 완료: {len(df)}개 매핑")
            return df
        except FileNotFoundError:
            self.logger.warning(f"유형 레벨 매핑 파일 없음: {file_path}")
            return pd.DataFrame(columns=['coa_type', 'threat_type', 'base_relevance'])
    
    def _load_critical_mapping(self) -> Optional[pd.DataFrame]:
        """핵심 조합 매핑 로딩 (선택적)"""
        file_path = self.data_lake_path / "COA_위협_관련성_핵심.xlsx"
        
        try:
            df = pd.read_excel(file_path)
            self.logger.info(f"핵심 조합 매핑 로드 완료: {len(df)}개 매핑")
            return df
        except FileNotFoundError:
            self.logger.debug(f"핵심 조합 매핑 파일 없음 (선택적): {file_path}")
            return None
    
    def get_relevance_score(
        self, 
        coa_id: str, 
        coa_type: str,
        threat_id: str, 
        threat_type: str,
        coa_keywords: Optional[Set[str]] = None,
        threat_keywords: Optional[Set[str]] = None
    ) -> float:
        """
        3-Tier 전략으로 관련성 점수 계산
        
        Args:
            coa_id: COA ID (예: "COA_DEF_002")
            coa_type: COA 유형 (예: "Defense")
            threat_id: 위협 ID (예: "THR001")
            threat_type: 위협 유형 (예: "침투")
            coa_keywords: COA 키워드 집합 (선택)
            threat_keywords: 위협 키워드 집합 (선택)
        
        Returns:
            관련성 점수 (0.0 ~ 1.0)
        """
        
        # [NEW] 입력된 위협 유형 정규화 (이름 -> 코드)
        normalized_threat_type = self._normalize_threat_type(threat_type)
        if normalized_threat_type != threat_type:
             self.logger.debug(f"위협 유형 정규화: {threat_type} -> {normalized_threat_type}")
        
        # Tier 2: 핵심 조합 테이블 확인 (최우선)
        critical_score = self._check_critical_mapping(coa_id, threat_id)
        if critical_score is not None:
            self.logger.debug(
                f"Tier 2 매핑 사용: COA={coa_id}, Threat={threat_id}, Score={critical_score:.2f}"
            )
            return critical_score
        
        
        # Tier 1: 유형 레벨 매핑 (정규화된 위협 유형 사용)
        type_score = self._check_type_mapping(coa_type, normalized_threat_type)
        if type_score is not None:
            # Tier 3: 키워드 유사도로 미세 조정
            if coa_keywords and threat_keywords:
                keyword_adjustment = self._calculate_keyword_similarity(
                    coa_keywords, threat_keywords
                )
                # 유형 점수에 ±10% 범위 조정
                adjusted_score = type_score * (0.9 + keyword_adjustment * 0.2)
                adjusted_score = min(max(adjusted_score, 0.0), 1.0)  # 0-1 범위 제한
                
                self.logger.debug(
                    f"Tier 1+3 매핑: Type={coa_type}×{threat_type}, "
                    f"Base={type_score:.2f}, Keyword={keyword_adjustment:.2f}, "
                    f"Final={adjusted_score:.2f}"
                )
                return adjusted_score
            else:
                self.logger.debug(
                    f"Tier 1 매핑: Type={coa_type}×{threat_type}, Score={type_score:.2f}"
                )
                return type_score
        
        # Fallback: 키워드만으로 계산
        if coa_keywords and threat_keywords:
            fallback_score = self._calculate_keyword_similarity(coa_keywords, threat_keywords)
            self.logger.debug(
                f"Fallback (키워드만): COA={coa_id}, Threat={threat_id}, Score={fallback_score:.2f}"
            )
            return fallback_score
        
        # 모든 방법 실패 시 (0.0 -> 0.5로 상향 조정하여 불필요한 배제 방지)
        self.logger.warning(
            f"관련성 점수 계산 실패: COA={coa_id} ({coa_type}), "
            f"Threat={threat_id} ({threat_type}) -> Fallback 0.5"
        )
        return 0.5
    
    def _check_critical_mapping(self, coa_id: str, threat_id: str) -> Optional[float]:
        """핵심 조합 테이블에서 점수 조회"""
        if self.critical_mapping is None:
            return None
        
        match = self.critical_mapping[
            (self.critical_mapping['coa_id'] == coa_id) &
            (self.critical_mapping['threat_id'] == threat_id)
        ]
        
        if not match.empty:
            return float(match.iloc[0]['relevance_score'])
        
        return None
    
    def _check_type_mapping(self, coa_type: str, threat_type: str) -> Optional[float]:
        """유형 레벨 매핑 테이블에서 점수 조회 (대소문자 무시)"""
        if self.type_mapping.empty:
            return None
        
        # 대소문자 무시 검색 (threat_type은 이미 정규화됨)
        match = self.type_mapping[
            (self.type_mapping['coa_type'].str.lower() == coa_type.lower()) &
            (self.type_mapping['threat_type'] == threat_type)
        ]
        
        if not match.empty:
            return float(match.iloc[0]['base_relevance'])
        
        return None
    
    def _calculate_keyword_similarity(
        self, 
        coa_keywords: Set[str], 
        threat_keywords: Set[str]
    ) -> float:
        """키워드 기반 Jaccard 유사도 계산"""
        if not coa_keywords or not threat_keywords:
            return 0.0
        
        intersection = len(coa_keywords & threat_keywords)
        union = len(coa_keywords | threat_keywords)
        
        return intersection / union if union > 0 else 0.0
    
    def get_type_mapping_stats(self) -> dict:
        """유형 레벨 매핑 통계"""
        if self.type_mapping.empty:
            return {
                'total_mappings': 0,
                'coa_types': [],
                'threat_types': [],
                'avg_relevance': 0.0
            }
        
        return {
            'total_mappings': len(self.type_mapping),
            'coa_types': self.type_mapping['coa_type'].unique().tolist(),
            'threat_types': self.type_mapping['threat_type'].unique().tolist(),
            'avg_relevance': self.type_mapping['base_relevance'].mean(),
            'min_relevance': self.type_mapping['base_relevance'].min(),
            'max_relevance': self.type_mapping['base_relevance'].max()
        }


# 테스트 코드
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    mapper = RelevanceMapper()
    
    print("=" * 80)
    print("RelevanceMapper 테스트")
    print("=" * 80)
    
    # 통계 출력
    stats = mapper.get_type_mapping_stats()
    print(f"\n📊 유형 레벨 매핑 통계:")
    print(f"- 총 매핑 수: {stats['total_mappings']}")
    print(f"- COA 유형: {stats['coa_types']}")
    print(f"- 위협 유형: {stats['threat_types']}")
    print(f"- 평균 관련성: {stats['avg_relevance']:.2f}")
    print(f"- 범위: {stats['min_relevance']:.2f} ~ {stats['max_relevance']:.2f}")
    
    # 테스트 케이스
    print(f"\n🧪 테스트 케이스:")
    
    test_cases = [
        ("COA_DEF_002", "Defense", "THR001", "침투", {"방어", "진지", "구축"}, {"침투", "적군", "차단"}),
        ("COA_OFF_005", "Offensive", "THR001", "침투", {"공격", "기습", "타격"}, {"침투", "적군", "차단"}),
        ("COA_PRE_003", "Preemptive", "THR002", "포격", {"선제", "타격", "파괴"}, {"포격", "화력", "준비"}),
        ("COA_INF_005", "InformationOps", "THR006", "사이버", {"정보", "사이버", "교란"}, {"사이버", "정보", "공격"}),
    ]
    
    for coa_id, coa_type, threat_id, threat_type, coa_kw, threat_kw in test_cases:
        score = mapper.get_relevance_score(
            coa_id, coa_type, threat_id, threat_type, coa_kw, threat_kw
        )
        print(f"\n{coa_id} ({coa_type}) × {threat_id} ({threat_type})")
        print(f"  → 관련성 점수: {score:.3f}")
