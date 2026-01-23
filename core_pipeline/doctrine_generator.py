# core_pipeline/doctrine_generator.py
# -*- coding: utf-8 -*-
"""
교리 문서 자동 생성기
RAG 시스템에 저장될 가상 교리 문서를 생성합니다.
"""
import os
import re
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


class DoctrineGenerator:
    """교리 문서 자동 생성기"""
    
    # 작전유형별 접두사 매핑
    OPERATION_TYPE_PREFIX = {
        "defense": "DEF",
        "offensive": "OFF",
        "counter_attack": "CA",
        "preemptive": "PRE",
        "deterrence": "DET",
        "maneuver": "MAN",
        "information_ops": "INFO"
    }
    
    # 교리 생성 프롬프트 템플릿
    DOCTRINE_GENERATION_PROMPT = """너는 군사 교리 집필 보조 AI이다.

목표:
- 실제 교범을 인용하거나 요약하지 말고,
- "군 교리 문장 형식"을 따르는 가상 교리 문서를 생성하라.
- 생성된 문서는 RAG 시스템에 저장되어
  COA 추천 시 근거 문장으로 사용된다.

생성 규칙:
1. 각 교리 문장은 단문·명시적 판단 기준 형태로 작성
2. 하나의 문장은 하나의 작전 판단 논리만 포함
3. METT-C 요소 중 최소 1개 이상을 명시적으로 언급
4. "권장된다 / 고려한다 / 제한된다" 와 같은 규범적 표현 사용
5. 역사적 사례, 실제 교범 명칭, 실존 문서 언급 금지

출력 형식:
- MD 형식
- 각 교리 문장은 고유 ID 부여 (예: D-{PREFIX}-001)
- 교리명, 적용 작전유형, 관련 METT-C 요소 명시

생성 대상:
- 작전유형: {operation_type}
- METT-C 중점: {mett_c_focus}
- COA 활용 목적: {coa_purpose}

이제 교리 문서를 생성하라. 다음 형식으로 출력하라:

# Doctrine_ID: DOCTRINE-{PREFIX}-XXX
## 교리명: [교리명]
## 적용 작전유형: {operation_type}
## 관련 METT-C 요소: {mett_c_focus}

### Doctrine_Statement_ID: D-{PREFIX}-001
- [교리 문장 1]
- **작전적 해석**: [해석]
- **COA 판단 시 활용 포인트**: 
  - [포인트 1]
  - [포인트 2]

### Doctrine_Statement_ID: D-{PREFIX}-002
- [교리 문장 2]
- **작전적 해석**: [해석]
- **COA 판단 시 활용 포인트**: 
  - [포인트 1]
  - [포인트 2]

[추가 교리 문장들...]
"""
    
    def __init__(self, llm_manager, rag_manager=None):
        """
        Args:
            llm_manager: LLMManager 인스턴스
            rag_manager: RAGManager 인스턴스 (선택적, 자동 저장용)
        """
        self.llm_manager = llm_manager
        self.rag_manager = rag_manager
        self.doctrine_id_counter = {}  # 작전유형별 카운터
    
    def generate_doctrine_document(
        self,
        operation_type: str,
        mett_c_focus: List[str],
        coa_purpose: List[str],
        num_statements: int = 5,
        doctrine_name: Optional[str] = None
    ) -> Dict:
        """
        교리 문서 생성
        
        Args:
            operation_type: 작전유형 (defense, offensive, counter_attack 등)
            mett_c_focus: METT-C 중점 요소 리스트 (예: ["Mission", "Terrain", "Troops"])
            coa_purpose: COA 활용 목적 리스트 (예: ["기동 제한", "방어선 설정"])
            num_statements: 생성할 교리 문장 수
            doctrine_name: 교리명 (None이면 자동 생성)
        
        Returns:
            {
                "doctrine_id": "DOCTRINE-DEF-001",
                "doctrine_name": "교리명",
                "content": "마크다운 형식 교리 문서",
                "statements": [
                    {
                        "statement_id": "D-DEF-001",
                        "text": "교리 문장",
                        "interpretation": "작전적 해석",
                        "coa_points": ["포인트1", "포인트2"],
                        "mett_c_elements": ["Terrain", "Mission"],
                        "operation_type": "defense"
                    }
                ],
                "metadata": {
                    "operation_type": "defense",
                    "mett_c_focus": ["Mission", "Terrain"],
                    "coa_purpose": ["기동 제한", "방어선 설정"],
                    "created_at": "2026-01-06T10:00:00Z"
                }
            }
        """
        # 작전유형 접두사 가져오기
        prefix = self.OPERATION_TYPE_PREFIX.get(operation_type, "GEN")
        
        # 교리 ID 생성
        if operation_type not in self.doctrine_id_counter:
            self.doctrine_id_counter[operation_type] = 0
        self.doctrine_id_counter[operation_type] += 1
        doctrine_id = f"DOCTRINE-{prefix}-{self.doctrine_id_counter[operation_type]:03d}"
        
        # 프롬프트 생성
        prompt = self.DOCTRINE_GENERATION_PROMPT.format(
            operation_type=operation_type,
            mett_c_focus=", ".join(mett_c_focus),
            coa_purpose=", ".join(coa_purpose),
            PREFIX=prefix
        )
        
        # LLM으로 교리 문서 생성
        try:
            response = self.llm_manager.generate(
                prompt,
                max_tokens=2048,
                temperature=0.7
            )
            
            # 응답 파싱
            parsed = self._parse_doctrine_response(
                response,
                doctrine_id,
                operation_type,
                mett_c_focus,
                doctrine_name
            )
            
            return parsed
            
        except Exception as e:
            print(f"[ERROR] 교리 문서 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_doctrine(
                doctrine_id,
                operation_type,
                mett_c_focus,
                coa_purpose,
                num_statements,
                doctrine_name
            )
    
    def _parse_doctrine_response(
        self,
        response: str,
        doctrine_id: str,
        operation_type: str,
        mett_c_focus: List[str],
        doctrine_name: Optional[str]
    ) -> Dict:
        """LLM 응답을 파싱하여 구조화된 교리 문서 생성"""
        statements = []
        current_statement = None
        
        lines = response.split('\n')
        doctrine_name_found = doctrine_name or f"{operation_type} 작전 교리"
        
        for line in lines:
            line = line.strip()
            
            # 교리명 추출
            if line.startswith('## 교리명:'):
                doctrine_name_found = line.replace('## 교리명:', '').strip()
                continue
            
            # 교리 문장 ID 추출
            if line.startswith('### Doctrine_Statement_ID:'):
                if current_statement:
                    statements.append(current_statement)
                statement_id = line.replace('### Doctrine_Statement_ID:', '').strip()
                current_statement = {
                    "statement_id": statement_id,
                    "text": "",
                    "interpretation": "",
                    "coa_points": [],
                    "mett_c_elements": [],
                    "operation_type": operation_type
                }
                continue
            
            # 교리 문장 본문
            if current_statement:
                if line.startswith('-') and not line.startswith('- **'):
                    # 교리 문장 본문
                    text = line.replace('-', '').strip()
                    if text and not current_statement["text"]:
                        current_statement["text"] = text
                elif line.startswith('- **작전적 해석**:'):
                    interpretation = line.replace('- **작전적 해석**:', '').strip()
                    current_statement["interpretation"] = interpretation
                elif line.startswith('- **COA 판단 시 활용 포인트**:'):
                    continue  # 다음 줄부터 포인트들
                elif line.startswith('  -') or line.startswith('- '):
                    # COA 활용 포인트
                    point = line.replace('-', '').replace('  ', '').strip()
                    if point and '활용 포인트' not in point:
                        current_statement["coa_points"].append(point)
        
        # 마지막 문장 추가
        if current_statement:
            statements.append(current_statement)
        
        # METT-C 요소 추출 (간단한 휴리스틱)
        for stmt in statements:
            text_lower = stmt["text"].lower()
            mett_c_elements = []
            if any(word in text_lower for word in ['임무', 'mission', '목표']):
                mett_c_elements.append("Mission")
            if any(word in text_lower for word in ['지형', 'terrain', '지면']):
                mett_c_elements.append("Terrain")
            if any(word in text_lower for word in ['부대', 'troops', '전력', '자원']):
                mett_c_elements.append("Troops")
            if any(word in text_lower for word in ['적', 'enemy', '위협']):
                mett_c_elements.append("Enemy")
            if any(word in text_lower for word in ['시간', 'time', '시기']):
                mett_c_elements.append("Time")
            if any(word in text_lower for word in ['민간', 'civilian', '시민']):
                mett_c_elements.append("Civilian")
            stmt["mett_c_elements"] = mett_c_elements if mett_c_elements else mett_c_focus[:2]
        
        # 마크다운 문서 재구성
        content = self._build_markdown_content(
            doctrine_id,
            doctrine_name_found,
            operation_type,
            mett_c_focus,
            statements
        )
        
        return {
            "doctrine_id": doctrine_id,
            "doctrine_name": doctrine_name_found,
            "content": content,
            "statements": statements,
            "metadata": {
                "operation_type": operation_type,
                "mett_c_focus": mett_c_focus,
                "created_at": datetime.now().isoformat()
            }
        }
    
    def _build_markdown_content(
        self,
        doctrine_id: str,
        doctrine_name: str,
        operation_type: str,
        mett_c_focus: List[str],
        statements: List[Dict]
    ) -> str:
        """마크다운 형식 교리 문서 구성"""
        lines = [
            f"# Doctrine_ID: {doctrine_id}",
            f"## 교리명: {doctrine_name}",
            f"## 적용 작전유형: {operation_type}",
            f"## 관련 METT-C 요소: {', '.join(mett_c_focus)}",
            ""
        ]
        
        for stmt in statements:
            lines.append(f"### Doctrine_Statement_ID: {stmt['statement_id']}")
            lines.append(f"- {stmt['text']}")
            if stmt.get('interpretation'):
                lines.append(f"- **작전적 해석**: {stmt['interpretation']}")
            if stmt.get('coa_points'):
                lines.append("- **COA 판단 시 활용 포인트**:")
                for point in stmt['coa_points']:
                    lines.append(f"  - {point}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_fallback_doctrine(
        self,
        doctrine_id: str,
        operation_type: str,
        mett_c_focus: List[str],
        coa_purpose: List[str],
        num_statements: int,
        doctrine_name: Optional[str]
    ) -> Dict:
        """LLM 실패 시 폴백 교리 문서 생성 (템플릿 기반)"""
        doctrine_name = doctrine_name or f"{operation_type} 작전 교리"
        prefix = self.OPERATION_TYPE_PREFIX.get(operation_type, "GEN")
        
        statements = []
        for i in range(1, num_statements + 1):
            statement_id = f"D-{prefix}-{i:03d}"
            # 간단한 템플릿 기반 교리 문장 생성
            if operation_type == "defense":
                templates = [
                    "적 주공축이 제한된 지형을 통해 예상될 경우, 방어 COA는 지형 차단선을 중심으로 구성되는 것이 권장된다.",
                    "아군 전력이 제한된 상황에서는 예비전력을 후방에 배치하여 유연한 대응이 가능하도록 고려한다.",
                    "민간인 지역이 인접한 경우, 작전 계획 수립 시 민간인 보호 조치를 우선적으로 반영해야 한다."
                ]
            else:
                templates = [
                    f"{operation_type} 작전에서 {mett_c_focus[0] if mett_c_focus else '작전 환경'}을 고려한 COA 선정이 중요하다.",
                    f"{coa_purpose[0] if coa_purpose else '작전 목표'} 달성을 위해 적절한 자원 배분이 필요하다."
                ]
            
            text = templates[i % len(templates)] if i <= len(templates) else templates[0]
            
            statements.append({
                "statement_id": statement_id,
                "text": text,
                "interpretation": f"{operation_type} 작전에서의 일반적 원칙",
                "coa_points": coa_purpose[:2] if coa_purpose else ["작전 목표 달성", "자원 효율성"],
                "mett_c_elements": mett_c_focus[:2] if mett_c_focus else ["Mission"],
                "operation_type": operation_type
            })
        
        content = self._build_markdown_content(
            doctrine_id,
            doctrine_name,
            operation_type,
            mett_c_focus,
            statements
        )
        
        return {
            "doctrine_id": doctrine_id,
            "doctrine_name": doctrine_name,
            "content": content,
            "statements": statements,
            "metadata": {
                "operation_type": operation_type,
                "mett_c_focus": mett_c_focus,
                "coa_purpose": coa_purpose,
                "created_at": datetime.now().isoformat()
            }
        }
    
    def save_to_rag(self, doctrine_doc: Dict, save_to_file: bool = True) -> bool:
        """
        생성된 교리 문서를 RAG 인덱스에 추가
        
        Args:
            doctrine_doc: generate_doctrine_document() 결과
            save_to_file: 파일로도 저장할지 여부
        
        Returns:
            성공 여부
        """
        if not self.rag_manager:
            print("[WARN] RAG Manager가 없어 교리 문서를 인덱스에 추가할 수 없습니다.")
            return False
        
        try:
            # 🔥 개선: 교리 문서를 문장 단위로 청킹 (메타데이터 포함)
            chunks = []
            for stmt in doctrine_doc.get("statements", []):
                # 각 교리 문장을 별도 청크로 생성
                statement_text = stmt['text']  # 실제 교리 문장 본문
                chunk_text = statement_text
                if stmt.get('interpretation'):
                    chunk_text += f"\n작전적 해석: {stmt['interpretation']}"
                
                chunk = {
                    "text": chunk_text,
                    "doctrine_id": doctrine_doc["doctrine_id"],
                    "statement_id": stmt["statement_id"],
                    "statement_text": statement_text,  # 🔥 추가: 실제 교리 문장 본문
                    "interpretation": stmt.get('interpretation', ''),
                    "operation_type": stmt.get("operation_type", ""),
                    "mett_c_elements": stmt.get("mett_c_elements", []),
                    "source": f"doctrine_{doctrine_doc['doctrine_id']}",
                    "chunk_index": len(chunks),
                    "doc_index": 0,
                    "chunk_type": "doctrine_statement"  # 🔥 추가: 청크 타입
                }
                chunks.append(chunk)
            
            # RAG 인덱스에 추가
            self.rag_manager.add_to_index(chunks)
            
            # 인덱스 저장
            self.rag_manager.save_index()
            
            print(f"[INFO] 교리 문서 {doctrine_doc['doctrine_id']}를 RAG 인덱스에 추가했습니다. ({len(chunks)}개 청크)")
            
            # 파일로도 저장 (선택적)
            if save_to_file:
                self._save_to_file(doctrine_doc)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] RAG 인덱스 추가 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _save_to_file(self, doctrine_doc: Dict):
        """교리 문서를 파일로 저장"""
        try:
            base_dir = Path(__file__).parent.parent
            rag_docs_path = base_dir / "knowledge" / "rag_docs"
            rag_docs_path.mkdir(parents=True, exist_ok=True)
            
            filename = f"{doctrine_doc['doctrine_id']}.md"
            filepath = rag_docs_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(doctrine_doc['content'])
            
            print(f"[INFO] 교리 문서를 파일로 저장했습니다: {filepath}")
            
        except Exception as e:
            print(f"[WARN] 교리 문서 파일 저장 실패: {e}")


