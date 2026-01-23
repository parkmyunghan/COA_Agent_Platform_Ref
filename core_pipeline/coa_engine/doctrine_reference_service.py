# core_pipeline/coa_engine/doctrine_reference_service.py
# -*- coding: utf-8 -*-
"""
교리 인용 서비스
COA 추천 시 교리 문장을 검색하고 인용 정보를 생성합니다.
"""
import re
from typing import List, Dict, Optional, Any
from core_pipeline.coa_engine.llm_services import DoctrineSearchService


class DoctrineReferenceService:
    """COA 추천 시 교리 인용 서비스"""
    
    def __init__(self, rag_manager, doctrine_search_service: Optional[DoctrineSearchService] = None):
        """
        Args:
            rag_manager: RAGManager 인스턴스
            doctrine_search_service: DoctrineSearchService 인스턴스 (선택적)
        """
        self.rag_manager = rag_manager
        if doctrine_search_service:
            self.doctrine_search_service = doctrine_search_service
        else:
            self.doctrine_search_service = DoctrineSearchService(rag_manager)
    
    def find_doctrine_references(
        self,
        coa: Any,
        mett_c_analysis: Dict,
        axis_states: List[Any],
        top_k: int = 3
    ) -> List[Dict]:
        """
        COA에 대한 교리 참조 검색
        
        Args:
            coa: COA 객체 (coa_id, coa_name, description 속성 필요)
            mett_c_analysis: METT-C 분석 결과
            axis_states: 축선별 전장상태 리스트
            top_k: 반환할 교리 문장 수
        
        Returns:
            교리 참조 리스트
        """
        # RAG 매니저가 없어도 Fallback 제공
        if not self.rag_manager or not self.rag_manager.is_available():
            return self._get_fallback_references(coa)
        
        try:
            # 1. METT-C 분석 결과 기반 쿼리 생성
            query = self._build_doctrine_query(coa, mett_c_analysis, axis_states)
            
            # 2. RAG 검색
            rag_results = self.doctrine_search_service.search_doctrine_references(
                query, top_k=top_k * 2,  # 더 많이 검색하여 필터링
                coa_context=coa
            )
            
            # 3. 교리 문장 파싱 및 메타데이터 추출 (Diversity 고려)
            doctrine_candidates = []
            general_candidates = []
            
            for result in rag_results:
                parsed = self._parse_doctrine_statement(result)
                if parsed:
                    if parsed.get('reference_type') == 'general':
                        general_candidates.append(parsed)
                    else:
                        doctrine_candidates.append(parsed)
            
            # 최종 리스트 구성 (Top-K 내에서 적절히 섞기)
            # 기본전략: 교리 우선, 하지만 일반 문서가 있으면 최소 1개는 포함 시도
            final_refs = []
            
            # 1. 최상위 교리 문서 추가
            final_refs.extend(doctrine_candidates)
            
            # 2. 일반 문서가 있으면 섞기
            if general_candidates:
                # Top-K가 찼는데 일반 문서가 하나도 없다면 마지막 교리를 일반으로 교체 (다양성)
                # 단, 교리 문서 점수가 월등히 높으면 교체하지 않는게 맞을 수도.. 
                # 여기서는 테스트 목적상(사용자 요청) 일반 문서 노출을 보장
                
                # 현재 리스트가 Top-K를 넘으면 자르되, 일반 문서 공간 확보
                if len(final_refs) >= top_k:
                    final_refs = final_refs[:top_k-1]
                
                final_refs.append(general_candidates[0])
            
            # Top-K로 제한
            final_refs = final_refs[:top_k]
            
            # 검색 결과가 없으면 Fallback 제공
            if not final_refs:
                return self._get_fallback_references(coa)
            
            return final_refs
            
        except Exception as e:
            print(f"[WARN] 교리 참조 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_references(coa)

    def _get_fallback_references(self, coa: Any) -> List[Dict]:
        """검색 실패 시 제공할 예시 데이터"""
        coa_name = getattr(coa, 'coa_name', 'Unknown') or getattr(coa, 'coa_id', 'Unknown')
        
        # COA 이름에 따른 맞춤형 예시
        if '방어' in coa_name or 'Defense' in coa_name:
            main_excerpt = f"[시스템 예시] '{coa_name}' 수행 간 지휘관은 가용 부대의 전투력을 통합하여 적의 중심을 타격하고 방어선을 고수해야 한다."
            sub_excerpt = "[시스템 예시] 방어 작전의 성공 요건은 적절한 예비대 운용과 적의 공격 기세를 꺾는 시적절한 화력 집중이다."
        elif '공격' in coa_name or 'Offense' in coa_name:
            main_excerpt = f"[시스템 예시] '{coa_name}' 수행 시 기습과 속도가 생명이며, 적의 약점을 집중 타격하여 조기에 승기를 잡아야 한다."
            sub_excerpt = "[시스템 예시] 공격 기세 유지를 위해 화력 지원과 병참선의 안전 확보가 필수적이다."
        else:
            main_excerpt = f"[시스템 예시] '{coa_name}' 수행 시 지휘관은 가용 자원을 효율적으로 배분하여 작전 목표를 달성해야 한다."
            sub_excerpt = "[시스템 예시] 모든 작전에서 지휘통제(C2)의 안정성과 정보 공유가 작전 성공의 핵심 요소이다."

        return [
            {
                "reference_type": "doctrine",
                "doctrine_id": "검색 결과 없음 (예시 데이터)",
                "statement_id": "EXAMPLE-001",
                "excerpt": main_excerpt,
                "relevance_score": 0.0,
                "mett_c_elements": ["Mission", "Troops"]
            },
            {
                "reference_type": "doctrine",
                "doctrine_id": "작전 일반 (예시)",
                "statement_id": "EXAMPLE-002",
                "excerpt": sub_excerpt,
                "relevance_score": 0.0,
                "mett_c_elements": ["General"]
            }
        ]
    
    def _build_doctrine_query(
        self,
        coa: Any,
        mett_c_analysis: Dict,
        axis_states: List[Any]
    ) -> str:
        """교리 검색 쿼리 생성 (개선된 버전)"""
        query_parts = []
        
        # 🔥 개선: COA 설명/설명 포함
        coa_name = getattr(coa, 'coa_name', None) or getattr(coa, 'coa_id', 'Unknown')
        coa_description = getattr(coa, 'description', None) or ""
        
        # COA 핵심 키워드 추출
        if coa_description:
            # 간단한 키워드 추출 (예: "방어", "기동", "차단" 등)
            keywords = []
            for keyword in ["방어", "기동", "차단", "공격", "지연", "유지", "강화"]:
                if keyword in coa_description:
                    keywords.append(keyword)
            if keywords:
                query_parts.append(" ".join(keywords))
        
        query_parts.append(coa_name)
        
        # 🔥 개선: METT-C 핵심 정보만 추출 (요약이 아닌 핵심 키워드)
        if isinstance(mett_c_analysis, dict):
            # Mission: 핵심 목표만
            mission = mett_c_analysis.get('mission', {})
            if isinstance(mission, dict):
                mission_key = mission.get('key', '') or mission.get('summary', '')
            else:
                mission_key = str(mission)
            if mission_key and len(mission_key) < 50:  # 너무 긴 설명 제외
                query_parts.append(mission_key)
            
            # Terrain: 지형 특징만
            terrain = mett_c_analysis.get('terrain', {})
            if isinstance(terrain, dict):
                terrain_key = terrain.get('key', '') or terrain.get('summary', '')
            else:
                terrain_key = str(terrain)
            if terrain_key and len(terrain_key) < 50:
                query_parts.append(terrain_key)
            
            # Troops: 부대 유형/능력만
            troops = mett_c_analysis.get('troops', {})
            if isinstance(troops, dict):
                troops_key = troops.get('key', '') or troops.get('summary', '')
            else:
                troops_key = str(troops)
            if troops_key and len(troops_key) < 50:
                query_parts.append(troops_key)
        
        # 🔥 개선: 축선 정보는 간단히
        if axis_states:
            threat_levels = []
            for axis in axis_states[:2]:  # 상위 2개만
                threat_level = getattr(axis, 'threat_level', None) or getattr(axis, 'threat_index', 0)
                if threat_level:
                    if threat_level > 0.7:
                        threat_levels.append("고위협")
                    elif threat_level > 0.4:
                        threat_levels.append("중위협")
                    else:
                        threat_levels.append("저위협")
            if threat_levels:
                query_parts.append(" ".join(threat_levels))
        
        query = " ".join(query_parts)
        print(f"[DEBUG] Generated RAG Query: {query}")
        return query
    
    def _parse_doctrine_statement(self, rag_result: Dict) -> Optional[Dict]:
        """
        RAG 결과에서 교리 문장 파싱 (개선된 버전)
        
        Args:
            rag_result: RAG 검색 결과 {
                "text": str,
                "score": float,
                "index": int,
                "metadata": dict,
                "doctrine_id": str (메타데이터),
                "statement_id": str (메타데이터),
                "statement_text": str (메타데이터),
                "mett_c_elements": List[str] (메타데이터)
            }
        
        Returns:
            {
                "doctrine_id": str,
                "statement_id": str,
                "excerpt": str,
                "relevance_score": float,
                "mett_c_elements": List[str]
            } 또는 None
        """
        text = rag_result.get('text', '')
        score = rag_result.get('score', 0.0)
        metadata = rag_result.get('metadata', {})
        
        if not text:
            return None
        
        # 🔥 개선: 메타데이터 우선 사용 (교리 문서 전용 청킹 사용 시)
        doctrine_id = (
            metadata.get('doctrine_id') or 
            rag_result.get('doctrine_id') or 
            self._extract_doctrine_id_from_text(text)
        )
        statement_id = (
            metadata.get('statement_id') or 
            rag_result.get('statement_id') or 
            self._extract_statement_id_from_text(text)
        )
        
        # 🔥 개선: statement_text 메타데이터가 있으면 우선 사용
        statement_text = (
            metadata.get('statement_text') or 
            rag_result.get('statement_text')
        )
        
        if statement_text:
            # 메타데이터에서 교리 문장 본문을 가져옴
            excerpt = self._clean_doctrine_text(statement_text)
        else:
            # 폴백: 텍스트에서 추출
            excerpt = self._extract_doctrine_excerpt(text)
        
        # 🔥 개선: METT-C 요소는 메타데이터 우선, 없으면 텍스트에서 추출
        mett_c_elements = (
            metadata.get('mett_c_elements') or 
            rag_result.get('mett_c_elements') or 
            self._extract_mett_c_elements(text)
        )
        
        # 🔥 디버깅: 점수 및 파싱 정보 출력
        print(f"[DEBUG] RAG Result Parse: ID={doctrine_id}, Score={score}, CleanExcerpt={excerpt[:30]}...")

        # 관련도 점수가 너무 낮으면 제외 (0.3 -> 0.05로 대폭 완화)
        # 테스트 단계에서는 최대한 많은 결과를 보여주는 것이 유리함
        if float(score) < 0.05:
            print(f"[DEBUG] Score filtered: {score} < 0.05")
            return None
        
        # 🔥 개선: 교리 문서와 일반 문서 구분
        is_doctrine = bool(doctrine_id and doctrine_id != "UNKNOWN")
        
        if is_doctrine:
            # 교리 문서인 경우
            return {
                "reference_type": "doctrine",
                "doctrine_id": doctrine_id,
                "statement_id": statement_id or f"STMT-{rag_result.get('index', 0)}",
                "excerpt": excerpt,
                "relevance_score": float(score),
                "mett_c_elements": mett_c_elements if mett_c_elements else []
            }
        else:
            # 🔥 일반 문서인 경우도 포함 (COA 추천 근거로 활용)
            source = (
                metadata.get('source') or 
                rag_result.get('source', '') or 
                'general_document'
            )
            
            # 일반 문서도 의미있는 정보이면 포함
            return {
                "reference_type": "general",
                "doctrine_id": None,  # 일반 문서는 교리 ID 없음
                "statement_id": None,  # 일반 문서는 문장 ID 없음
                "source": source,  # 문서 소스 (예: "방책_연계_원칙.txt")
                "excerpt": excerpt,
                "relevance_score": float(score),
                "mett_c_elements": mett_c_elements if mett_c_elements else []
            }
    
    def _extract_doctrine_id_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 교리 ID 추출"""
        # 패턴: DOCTRINE-XXX 또는 Doctrine_ID: DOCTRINE-XXX
        patterns = [
            r'DOCTRINE-[\w-]+',
            r'Doctrine_ID:\s*(DOCTRINE-[\w-]+)',
            r'#\s*Doctrine_ID:\s*(DOCTRINE-[\w-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def _extract_statement_id_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 교리 문장 ID 추출"""
        # 패턴: D-XXX-001 또는 Doctrine_Statement_ID: D-XXX-001
        patterns = [
            r'D-[\w-]+-\d+',
            r'Doctrine_Statement_ID:\s*(D-[\w-]+-\d+)',
            r'###\s*Doctrine_Statement_ID:\s*(D-[\w-]+-\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def _clean_doctrine_text(self, text: str) -> str:
        """교리 텍스트 정리 (마크다운, 헤더 제거)"""
        if not text:
            return ""
        
        # 마크다운 리스트 항목 기호 제거
        text = re.sub(r'^[-*]\s*', '', text, flags=re.MULTILINE)
        
        # 볼드 텍스트 제거 (예: **작전적 해석**:)
        text = re.sub(r'\*\*[^*]+\*\*:\s*', '', text)
        
        # 주석 제거 (#으로 시작하는 줄)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # 주석, 헤더, 빈 줄 제거
            if line and not line.startswith('#') and not line.startswith('*'):
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines).strip()
    
    def _extract_doctrine_excerpt(self, text: str, max_length: int = 200) -> str:
        """교리 문장 본문 추출 (개선된 버전)"""
        # 먼저 정리
        text = self._clean_doctrine_text(text)
        
        # 교리 ID, 문장 ID 패턴 제거
        text = re.sub(r'#\s*Doctrine_ID:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'###\s*Doctrine_Statement_ID:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'##\s*[^\n]+\n?', '', text)  # 헤더 제거
        
        # 첫 번째 의미있는 문장 추출
        sentences = re.split(r'[.!?]\s+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            # 너무 짧거나 의미없는 문장 제외
            if len(sentence) > 20 and not sentence.startswith('#'):
                if len(sentence) > max_length:
                    return sentence[:max_length] + "..."
                return sentence
        
        # 문장이 없으면 전체 텍스트 반환 (제한)
        text_clean = text.strip()
        if len(text_clean) > max_length:
            return text_clean[:max_length] + "..."
        return text_clean
    
    def _extract_mett_c_elements(self, text: str) -> List[str]:
        """텍스트에서 METT-C 요소 추출 (개선된 버전)"""
        elements = []
        
        # 🔥 개선: 먼저 헤더에서 METT-C 요소 추출 시도
        mett_c_header_match = re.search(
            r'##\s*관련\s*METT-C\s*요소:\s*([^\n]+)',
            text,
            re.IGNORECASE
        )
        if mett_c_header_match:
            mett_c_str = mett_c_header_match.group(1).strip()
            # 쉼표로 구분된 요소 추출
            header_elements = [e.strip() for e in mett_c_str.split(',') if e.strip()]
            # 표준 METT-C 요소명으로 매핑
            mett_c_mapping = {
                "mission": "Mission",
                "enemy": "Enemy",
                "terrain": "Terrain",
                "troops": "Troops",
                "time": "Time",
                "civilian": "Civilian"
            }
            for elem in header_elements:
                elem_lower = elem.lower()
                if elem_lower in mett_c_mapping:
                    elements.append(mett_c_mapping[elem_lower])
                elif elem in ["Mission", "Enemy", "Terrain", "Troops", "Time", "Civilian"]:
                    elements.append(elem)
        
        # 헤더에서 추출 실패 시 키워드 기반 추출
        if not elements:
            text_lower = text.lower()
            mett_c_keywords = {
                "Mission": ["임무", "mission", "목표", "objective"],
                "Enemy": ["적", "enemy", "위협", "threat"],
                "Terrain": ["지형", "terrain", "지면", "지리"],
                "Troops": ["부대", "troops", "전력", "자원", "resource"],
                "Time": ["시간", "time", "시기", "timing"],
                "Civilian": ["민간", "civilian", "시민", "주민"]
            }
            
            for element, keywords in mett_c_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    elements.append(element)
        
        # 중복 제거
        elements = list(dict.fromkeys(elements))
        
        return elements  # 빈 리스트 반환 가능 (기본값 제거)


