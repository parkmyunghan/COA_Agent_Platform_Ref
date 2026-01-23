"""
자원 우선순위 파싱 및 점수 계산 모듈
COA_Library.xlsx의 '자원우선순위' 컬럼을 파싱하여 필수/권장/선택 구분
"""
from typing import Dict, List, Tuple, Optional, Any
import re
import logging

class ResourcePriorityParser:
    """자원 우선순위 파싱 및 점수 계산"""
    
    # 우선순위별 가중치
    PRIORITY_WEIGHTS = {
        '필수': 1.0,
        'required': 1.0,
        '권장': 0.6,
        'recommended': 0.6,
        '선택': 0.3,
        'optional': 0.3
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_resource_priority(self, priority_string: str) -> List[Dict]:
        """
        자원우선순위 문자열 파싱
        
        Args:
            priority_string: "포병대대(필수), 보병여단(권장), 공격헬기(선택)"
        
        Returns:
            [
                {'resource': '포병대대', 'priority': '필수', 'weight': 1.0},
                {'resource': '보병여단', 'priority': '권장', 'weight': 0.6},
                {'resource': '공격헬기', 'priority': '선택', 'weight': 0.3}
            ]
        """
        if not priority_string or str(priority_string).strip() == '' or str(priority_string) == 'nan':
            return []
        
        resources = []
        
        # 쉼표로 구분
        items = str(priority_string).split(',')
        
        for item in items:
            item = item.strip()
            if not item:
                continue
            
            # 패턴 매칭: "자원명(우선순위)"
            match = re.match(r'^(.+?)\s*\((.+?)\)\s*$', item)
            
            if match:
                resource_name = match.group(1).strip()
                priority = match.group(2).strip()
                
                # 우선순위 정규화
                priority_normalized = self._normalize_priority(priority)
                weight = self.PRIORITY_WEIGHTS.get(priority_normalized, 0.5)
                
                resources.append({
                    'resource': resource_name,
                    'priority': priority_normalized,
                    'weight': weight
                })
                
                self.logger.debug(f"파싱 성공: {resource_name} ({priority_normalized}, {weight})")
            else:
                # 우선순위 없는 경우: 기본 '권장'으로 처리
                resource_name = item.strip()
                if resource_name:
                    resources.append({
                        'resource': resource_name,
                        'priority': '권장',
                        'weight': 0.6
                    })
                    self.logger.debug(f"우선순위 없음: {resource_name} (기본값 '권장' 적용)")
        
        return resources
    
    def _normalize_priority(self, priority: str) -> str:
        """우선순위 문자열 정규화"""
        priority_lower = priority.lower().strip()
        
        # 한글/영어 매핑
        mapping = {
            '필수': '필수',
            'required': '필수',
            'mandatory': '필수',
            'must': '필수',
            '권장': '권장',
            'recommended': '권장',
            'suggested': '권장',
            '선택': '선택',
            'optional': '선택',
            'choice': '선택'
        }
        
        return mapping.get(priority_lower, '권장')  # 기본값: 권장
    
    def calculate_resource_score_with_priority(
        self,
        required_resources: List[Dict],
        available_resources: List[Dict],
        asset_master_data: Optional[Dict[str, Dict]] = None
    ) -> Tuple[float, Dict]:
        """
        우선순위를 고려한 자원 점수 계산
        
        Args:
            required_resources: [{'resource': '포병대대', 'priority': '필수', 'weight': 1.0}, ...]
            available_resources: [{'resource_alias': '포병대대', 'asset_id': 'AST_001'}, ...]
            asset_master_data: {asset_id: {'수량': 10, '가용상태': '사용가능'}} (선택적)
        
        Returns:
            (score: float, detail: dict)
        """
        if not required_resources:
            return 1.0, {'message': '필요 자원 없음'}
        
        if not available_resources:
            return 0.2, {'error': '가용 자원 데이터 없음'}
        
        # 가용 자원 정보 집합 구성
        available_dict = {}
        for res in available_resources:
            asset_id = res.get('asset_id')
            master_info = asset_master_data.get(asset_id) if asset_master_data and asset_id else None
            
            # 매칭 후보 이름들 (1. 마스터 자산명, 2. 전술적 역할, 3. legacy 필드)
            names_to_register = []
            
            # 1. 마스터 자산명
            master_name = None
            if master_info:
                master_name = master_info.get('자산명', master_info.get('name'))
                if master_name:
                    names_to_register.append(master_name)
            
            # 2. 전술적 역할 (교리적 보완)
            tactical_role = res.get('tactical_role')
            if tactical_role and tactical_role != '미지정':
                names_to_register.append(tactical_role)
                
            # 3. legacy 필드 (resource_alias 등)
            alias = res.get('resource_alias', res.get('resource_name', res.get('resource')))
            if alias:
                names_to_register.append(alias)
            
            for name in names_to_register:
                name_normalized = self._normalize_resource_name(name)
                available_dict[name_normalized] = {
                    'original_res': res,
                    'master_info': master_info,
                    'asset_id': asset_id
                }
        
        available_names = set(available_dict.keys())
        
        # 우선순위별 매칭
        total_weight = 0.0
        matched_weight = 0.0
        matched_resources = []
        missing_resources = []
        
        for req in required_resources:
            resource_name = req['resource']
            priority = req['priority']
            weight = req['weight']
            
            total_weight += weight
            
            # 정규화된 이름으로 매칭
            req_name_normalized = self._normalize_resource_name(resource_name)
            
            # 매칭 확인 (완전 일치 또는 포함 관계)
            matched = False
            matched_entry = None
            
            for avail_name in available_names:
                if self._is_matching(req_name_normalized, avail_name):
                    matched = True
                    matched_entry = available_dict[avail_name]
                    break
            
            if matched:
                asset_id = matched_entry.get('asset_id')
                master_info = matched_entry.get('master_info')
                matched_res = matched_entry.get('original_res')
                
                # 수량 조회 우선순위:
                # 1. 할당 테이블의 allocated_quantity (교리적 보완)
                # 2. 할당 테이블의 quantity/available_quantity (legacy)
                # 3. 마스터 테이블의 수량
                avail_qty = matched_res.get('allocated_quantity')
                if avail_qty is None:
                    avail_qty = matched_res.get('quantity', matched_res.get('available_quantity'))
                if avail_qty is None and master_info:
                    avail_qty = master_info.get('수량', master_info.get('quantity', 1))
                if avail_qty is None:
                    avail_qty = 1
                
                # 상태 조회 우선순위:
                # 1. 할당 테이블의 plan_status (Snapshot)
                # 2. 마스터 데이터의 실시간 상태 (Latest)
                # NOTE: 계획 시점과 현재 시점의 차이를 분석할 수도 있으나, 여기서는 우선 가용한 것을 택함
                status = matched_res.get('plan_status')
                if status is None and master_info:
                    status = master_info.get('가용상태', master_info.get('status', '사용가능'))
                if status is None:
                    status = '사용가능'
                
                # 점수 반영
                if str(status) == '사용가능' and int(avail_qty) > 0:
                    matched_weight += weight
                    matched_resources.append({
                        'resource': resource_name,
                        'priority': priority,
                        'qty': avail_qty,
                        'status': status,
                        'asset_id': asset_id,
                        'tactical_role': matched_res.get('tactical_role', '미지정')
                    })
                else:
                    missing_resources.append({
                        'resource': resource_name, 
                        'priority': priority,
                        'reason': f'상태({status}) 또는 수량({avail_qty}) 부족'
                    })
            else:
                missing_resources.append({'resource': resource_name, 'priority': priority})
        
        # 최종 점수 계산
        if total_weight > 0:
            score = matched_weight / total_weight
        else:
            score = 0.5
        
        # 필수 자원 체크
        missing_required = [m for m in missing_resources if m['priority'] == '필수']
        if missing_required:
            # 필수 자원이 하나라도 없으면 점수 크게 감점
            score = min(score, 0.3)
            self.logger.warning(
                f"필수 자원 부족: {len(missing_required)}개 - "
                f"{[m['resource'] for m in missing_required]}"
            )
        
        detail = {
            'total_required': len(required_resources),
            'matched_count': len(matched_resources),
            'missing_count': len(missing_resources),
            'matched': matched_resources,
            'missing': missing_resources,
            'required_priority_breakdown': {
                '필수': len([r for r in required_resources if r['priority'] == '필수']),
                '권장': len([r for r in required_resources if r['priority'] == '권장']),
                '선택': len([r for r in required_resources if r['priority'] == '선택'])
            }
        }
        
        return round(score, 3), detail
    
    def _normalize_resource_name(self, name: str) -> str:
        """자원 이름 정규화 (공백, 특수문자 제거, 소문자 변환)"""
        if not name:
            return ""
        # 공백, 하이픈, 언더스코어 제거
        normalized = str(name).lower().replace(' ', '').replace('-', '').replace('_', '')
        return normalized
    
    def _is_matching(self, req_name: str, avail_name: str) -> bool:
        """자원 이름 매칭 (완전 일치 또는 포함 관계)"""
        if not req_name or not avail_name:
            return False
        
        # 1. 완전 일치
        if req_name == avail_name:
            return True
        
        # 2. 포함 관계
        if req_name in avail_name or avail_name in req_name:
            return True
        
        # 3. 유사 단어 (예: "포병" vs "자주포")
        # 추후 확장 가능
        
        return False


# 테스트 코드
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    parser = ResourcePriorityParser()
    
    print("=" * 80)
    print("ResourcePriorityParser 테스트")
    print("=" * 80)
    
    # 테스트 1: 파싱
    print("\n1. 자원우선순위 문자열 파싱")
    test_strings = [
        "포병대대(필수), 보병여단(권장), 공격헬기(선택)",
        "전차대대(required), 공병대대(recommended)",
        "특수전팀, 사이버전팀",  # 우선순위 없음
        "",  # 빈 문자열
    ]
    
    for test_str in test_strings:
        print(f"\n입력: '{test_str}'")
        result = parser.parse_resource_priority(test_str)
        if result:
            for r in result:
                print(f"  - {r['resource']} ({r['priority']}, 가중치={r['weight']})")
        else:
            print("  (결과 없음)")
    
    # 테스트 2: 점수 계산
    print("\n\n2. 우선순위 기반 자원 점수 계산")
    
    required = [
        {'resource': '포병대대', 'priority': '필수', 'weight': 1.0},
        {'resource': '보병여단', 'priority': '필수', 'weight': 1.0},
        {'resource': '공격헬기', 'priority': '권장', 'weight': 0.6},
        {'resource': '사이버전팀', 'priority': '선택', 'weight': 0.3}
    ]
    
    available = [
        {'resource_alias': '포병대대', 'quantity': 18, 'status': '사용가능'},
        {'resource_alias': '보병여단', 'quantity': 3000, 'status': '사용가능'},
        {'resource_alias': '공격헬기', 'quantity': 8, 'status': '정비중'},
        # 사이버전팀 없음
    ]
    
    score, detail = parser.calculate_resource_score_with_priority(required, available)
    
    print(f"\n점수: {score:.3f}")
    print(f"매칭: {detail['matched_count']}/{detail['total_required']}")
    print(f"우선순위 분포: {detail['required_priority_breakdown']}")
    print(f"\n매칭된 자원:")
    for m in detail['matched']:
        print(f"  ✅ {m['resource']} ({m['priority']}) - {m['status']}, 점수={m['score']:.2f}")
    print(f"\n부족한 자원:")
    for m in detail['missing']:
        print(f"  ❌ {m['resource']} ({m['priority']})")
    
    # 테스트 3: 필수 자원 부족 케이스
    print("\n\n3. 필수 자원 부족 케이스")
    
    available_limited = [
        {'resource_alias': '공격헬기', 'quantity': 8, 'status': '정비중'},
    ]
    
    score2, detail2 = parser.calculate_resource_score_with_priority(required, available_limited)
    
    print(f"\n점수: {score2:.3f} (필수 자원 부족으로 감점)")
    print(f"매칭: {detail2['matched_count']}/{detail2['total_required']}")
    
    print("\n" + "=" * 80)
