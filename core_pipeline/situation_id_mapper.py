"""
Situation ID 추출 및 URI 생성 유틸리티
Phase 2.3: Situation ID 매핑 수정
"""
from typing import Optional
import re


class SituationIDMapper:
    """Situation ID 추출 및 표준화 유틸리티"""
    
    @staticmethod
    def extract_situation_id(situation_info: dict) -> str:
        """
        다양한 소스에서 Situation ID 추출
        
        Args:
            situation_info: 상황 정보 딕셔너리
            
        Returns:
            표준화된 situation ID (예: MSN008, THR001)
        """
        # 1순위: selected_situation_info의 situation_id
        if 'situation_id' in situation_info:
            sit_id = situation_info['situation_id']
            if sit_id and str(sit_id).strip() != '' and str(sit_id) != 'nan':
                return SituationIDMapper._normalize_id(str(sit_id))
        
        # 2순위: URI에서 추출
        if 'uri' in situation_info:
            uri = str(situation_info['uri'])
            # http://...#위협상황_MSN008 -> MSN008
            # http://...#위협상황_THR001 -> THR001
            if '#위협상황_' in uri:
                extracted = uri.split('#위협상황_')[1]
                return SituationIDMapper._normalize_id(extracted)
            elif '#' in uri:
                # 일반적인 URI fragment에서 추출
                extracted = uri.split('#')[-1]
                if extracted and not extracted.startswith('http'):
                    return SituationIDMapper._normalize_id(extracted)
        
        # 3순위: name에서 추출
        if 'name' in situation_info:
            name = str(situation_info['name'])
            # "MSN008: 북한군 대규모 침투" -> MSN008
            # "THR001: 포병 포격 위협" -> THR001
            match = re.match(r'^([A-Z]{2,3}\d{3})[:\s]', name)
            if match:
                return SituationIDMapper._normalize_id(match.group(1))
        
        # 4순위: threat_id (있을 경우)
        if 'threat_id' in situation_info:
            threat_id = situation_info['threat_id']
            if threat_id and str(threat_id).strip() != '':
                return SituationIDMapper._normalize_id(str(threat_id))
        
        # Fallback: UNKNOWN
        return "UNKNOWN"
    
    @staticmethod
    def _normalize_id(raw_id: str) -> str:
        """
        ID 정규화
        
        THREAT001 -> THR001
        threat001 -> THR001
        MSN008 -> MSN008
        THR001 -> THR001
        """
        if not raw_id or str(raw_id).strip() == '':
            return "UNKNOWN"
        
        raw_id = str(raw_id).strip().upper()
        
        # THREAT001, THREAT_001 등을 THR001로 변환
        if raw_id.startswith('THREAT'):
            # THREAT001, THREAT_001 등에서 숫자 추출
            numbers = re.findall(r'\d+', raw_id)
            if numbers:
                num = numbers[0].zfill(3)  # 3자리로 패딩
                return f"THR{num}"
        
        # 이미 표준 형식인 경우 (MSN008, THR001 등)
        if re.match(r'^[A-Z]{2,3}\d{3}$', raw_id):
            return raw_id
        
        # 숫자만 있는 경우 (001 -> THR001)
        if raw_id.isdigit():
            return f"THR{raw_id.zfill(3)}"
        
        return raw_id
    
    @staticmethod
    def generate_threat_uri(situation_id: str, namespace: str = "http://coa-agent-platform.org/ontology#") -> str:
        """
        표준화된 위협상황 URI 생성
        
        Args:
            situation_id: MSN008, THR001 등
            namespace: 온톨로지 네임스페이스
            
        Returns:
            http://coa-agent-platform.org/ontology#위협상황_MSN008
        """
        normalized_id = SituationIDMapper._normalize_id(situation_id)
        return f"{namespace}위협상황_{normalized_id}"
    
    @staticmethod
    def is_valid_situation_id(situation_id: str) -> bool:
        """Situation ID가 유효한지 검증"""
        if not situation_id or situation_id == "UNKNOWN":
            return False
        
        # MSN008, THR001 등의 형식
        return bool(re.match(r'^[A-Z]{2,3}\d{3}$', str(situation_id).upper()))


# 테스트 코드
if __name__ == "__main__":
    print("=" * 80)
    print("SituationIDMapper 테스트")
    print("=" * 80)
    
    # 테스트 케이스
    test_cases = [
        # (입력, 예상 출력)
        ({'situation_id': 'MSN008'}, 'MSN008'),
        ({'situation_id': 'THREAT001'}, 'THR001'),
        ({'situation_id': 'threat001'}, 'THR001'),
        ({'uri': 'http://example.org#위협상황_MSN008'}, 'MSN008'),
        ({'uri': 'http://example.org#위협상황_THR001'}, 'THR001'),
        ({'name': 'MSN008: 북한군 침투'}, 'MSN008'),
        ({'name': 'THR001: 포격 위협'}, 'THR001'),
        ({'threat_id': 'THREAT001'}, 'THR001'),
        ({}, 'UNKNOWN'),
    ]
    
    print("\n[추출 테스트]")
    for i, (input_data, expected) in enumerate(test_cases, 1):
        result = SituationIDMapper.extract_situation_id(input_data)
        status = "✅" if result == expected else "❌"
        print(f"{status} Test {i}: {input_data} -> {result} (예상: {expected})")
    
    # 정규화 테스트
    print("\n[정규화 테스트]")
    normalize_cases = [
        ('THREAT001', 'THR001'),
        ('threat_001', 'THR001'),
        ('MSN008', 'MSN008'),
        ('THR001', 'THR001'),
        ('001', 'THR001'),
    ]
    
    for raw, expected in normalize_cases:
        result = SituationIDMapper._normalize_id(raw)
        status = "✅" if result == expected else "❌"
        print(f"{status} {raw} -> {result} (예상: {expected})")
    
    # URI 생성 테스트
    print("\n[URI 생성 테스트]")
    uri_cases = [
        ('MSN008', 'http://coa-agent-platform.org/ontology#위협상황_MSN008'),
        ('THREAT001', 'http://coa-agent-platform.org/ontology#위협상황_THR001'),
    ]
    
    for sit_id, expected in uri_cases:
        result = SituationIDMapper.generate_threat_uri(sit_id)
        status = "✅" if result == expected else "❌"
        print(f"{status} {sit_id} -> {result}")
    
    # 검증 테스트
    print("\n[검증 테스트]")
    validation_cases = [
        ('MSN008', True),
        ('THR001', True),
        ('UNKNOWN', False),
        ('invalid', False),
        ('', False),
    ]
    
    for sit_id, expected in validation_cases:
        result = SituationIDMapper.is_valid_situation_id(sit_id)
        status = "✅" if result == expected else "❌"
        print(f"{status} {sit_id} -> {result} (예상: {expected})")
    
    print("\n" + "=" * 80)
