# api/utils/code_label_mapper.py
# -*- coding: utf-8 -*-
"""
코드-한글 라벨 매핑 유틸리티
위협 유형, 축선 등의 코드를 한글 명칭으로 변환
"""
import os
from typing import Dict, Optional
import pandas as pd
from pathlib import Path


class CodeLabelMapper:
    """
    코드-한글 라벨 매핑을 제공하는 싱글톤 클래스
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CodeLabelMapper, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.threat_type_map: Dict[str, str] = {}
            self.axis_map: Dict[str, str] = {}
            self.threat_id_map: Dict[str, str] = {}
            self._load_mappings()
            CodeLabelMapper._initialized = True
    
    def _get_data_lake_path(self) -> Path:
        """data_lake 디렉토리 경로 반환"""
        # api/utils에서 프로젝트 루트로 이동
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        data_lake = project_root / "data_lake"
        return data_lake
    
    def _load_mappings(self):
        """Excel 파일에서 매핑 데이터 로드"""
        try:
            data_lake = self._get_data_lake_path()
            
            # 위협 유형 매핑 로드
            threat_type_file = data_lake / "위협유형_마스터.xlsx"
            if threat_type_file.exists():
                df = pd.read_excel(threat_type_file)
                # 위협유형코드 -> 위협유형명 매핑
                if '위협유형코드' in df.columns and '위협유형명' in df.columns:
                    for _, row in df.iterrows():
                        code = str(row['위협유형코드']).strip()
                        name = str(row['위협유형명']).strip()
                        if code and name and code != 'nan' and name != 'nan':
                            self.threat_type_map[code] = name
                    print(f"[CodeLabelMapper] 위협 유형 매핑 로드 완료: {len(self.threat_type_map)}개")
                else:
                    print(f"[CodeLabelMapper] 경고: 위협유형_마스터.xlsx에 필요한 컬럼이 없습니다.")
            else:
                print(f"[CodeLabelMapper] 경고: {threat_type_file} 파일을 찾을 수 없습니다.")
            
            # 축선 매핑 로드
            axis_file = data_lake / "전장축선.xlsx"
            if axis_file.exists():
                df = pd.read_excel(axis_file)
                # 축선ID -> 축선명 매핑
                if '축선ID' in df.columns and '축선명' in df.columns:
                    for _, row in df.iterrows():
                        code = str(row['축선ID']).strip()
                        name = str(row['축선명']).strip()
                        if code and name and code != 'nan' and name != 'nan':
                            self.axis_map[code] = name
                    print(f"[CodeLabelMapper] 축선 매핑 로드 완료: {len(self.axis_map)}개")
                else:
                    print(f"[CodeLabelMapper] 경고: 전장축선.xlsx에 필요한 컬럼이 없습니다.")
            else:
                print(f"[CodeLabelMapper] 경고: {axis_file} 파일을 찾을 수 없습니다.")
            
            # 위협 ID -> 위협 유형 매핑 로드 (위협상황.xlsx에서)
            threat_file = data_lake / "위협상황.xlsx"
            if threat_file.exists():
                df = pd.read_excel(threat_file)
                # 위협ID -> 위협유형코드 매핑 후 위협유형명으로 변환
                if '위협ID' in df.columns and '위협유형코드' in df.columns:
                    for _, row in df.iterrows():
                        threat_id = str(row['위협ID']).strip()
                        threat_type_code = str(row['위협유형코드']).strip()
                        if threat_id and threat_type_code and threat_id != 'nan' and threat_type_code != 'nan':
                            # 위협유형코드를 위협유형명으로 변환
                            threat_type_name = self.threat_type_map.get(threat_type_code, threat_type_code)
                            self.threat_id_map[threat_id] = threat_type_name
                    print(f"[CodeLabelMapper] 위협 ID 매핑 로드 완료: {len(self.threat_id_map)}개")
                else:
                    print(f"[CodeLabelMapper] 경고: 위협상황.xlsx에 필요한 컬럼이 없습니다.")
            else:
                print(f"[CodeLabelMapper] 경고: {threat_file} 파일을 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"[CodeLabelMapper] 매핑 데이터 로드 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    def get_threat_type_label(self, code: str) -> str:
        """
        위협 유형 코드를 한글 라벨로 변환
        
        Args:
            code: 위협 유형 코드 (예: "THR_TYPE_001", "침투")
            
        Returns:
            한글 라벨 (예: "침투")
        """
        if not code or str(code).strip() in ['', 'nan', 'None', 'N/A']:
            return '미상'
        
        code_str = str(code).strip()
        
        # 이미 한글인 경우 그대로 반환
        if code_str in self.threat_type_map.values():
            return code_str
        
        # 코드를 한글로 변환
        return self.threat_type_map.get(code_str, code_str)
    
    def get_axis_label(self, code: str) -> str:
        """
        축선 코드를 한글 라벨로 변환
        
        Args:
            code: 축선 코드 (예: "AXIS01")
            
        Returns:
            한글 라벨 (예: "동부 주공축선")
        """
        if not code or str(code).strip() in ['', 'nan', 'None', 'N/A']:
            return ''
        
        code_str = str(code).strip()
        
        # 이미 한글인 경우 그대로 반환
        if code_str in self.axis_map.values():
            return code_str
        
        # 코드를 한글로 변환
        return self.axis_map.get(code_str, code_str)
    
    def get_threat_id_label(self, threat_id: str) -> str:
        """
        위협 ID를 위협 유형명으로 변환
        
        Args:
            threat_id: 위협 ID (예: "THR001")
            
        Returns:
            위협 유형명 (예: "침투")
        """
        if not threat_id or str(threat_id).strip() in ['', 'nan', 'None', 'N/A']:
            return ''
        
        threat_id_str = str(threat_id).strip()
        return self.threat_id_map.get(threat_id_str, '')
    
    def format_with_code(self, label: str, code: str) -> str:
        """
        라벨과 코드를 병행 표기 형식으로 포맷팅
        
        Args:
            label: 한글 라벨
            code: 코드
            
        Returns:
            "라벨 (코드)" 형식 문자열
        """
        if not code or str(code).strip() in ['', 'nan', 'None', 'N/A']:
            return label or '미상'
        
        if not label or label == code:
            return code
        
        return f"{label} ({code})"
    
    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        모든 매핑 정보를 반환 (API 응답용)
        
        Returns:
            매핑 정보 딕셔너리
        """
        return {
            "threat_types": self.threat_type_map,
            "axes": self.axis_map,
            "threat_ids": self.threat_id_map
        }


# 싱글톤 인스턴스 생성
_mapper_instance = None

def get_mapper() -> CodeLabelMapper:
    """CodeLabelMapper 싱글톤 인스턴스 반환"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = CodeLabelMapper()
    return _mapper_instance
