#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
아군부대현황 표준화 스크립트
부대명을 {병종}{제대} 형식으로 통일
"""
import pandas as pd
import os

def standardize_friendly_units():
    """아군부대현황의 부대명을 표준화"""
    
    file_path = 'data_lake/아군부대현황.xlsx'
    
    print("=" * 60)
    print("아군부대현황 부대명 표준화")
    print("=" * 60)
    
    # 기존 파일 로드
    df = pd.read_excel(file_path)
    
    print(f"\n원본 데이터 ({len(df)}개 부대):")
    print(df[['아군부대ID', '부대명', '제대', '병종']].to_string(index=False))
    
    # 부대명 표준화 매핑
    name_mapping = {
        '00사단 1여단': '기계화여단',
        '00사단 2여단': '보병여단',
        '00사단 3여단': '기갑여단',
        '00포병여단': '포병여단',
        '00수색대대': '수색대대',
        '00전차대대': '전차대대',
        '00공병대대': '공병대대',
        '00통신대대': '통신대대',
        '00의무중대': '의무중대',
        '00보급대대': '보급대대',
    }
    
    # 부대명 변경
    df['부대명'] = df['부대명'].replace(name_mapping)
    
    print(f"\n\n표준화된 데이터:")
    print(df[['아군부대ID', '부대명', '제대', '병종']].to_string(index=False))
    
    # 변경사항 확인
    print(f"\n\n변경사항:")
    for old_name, new_name in name_mapping.items():
        if old_name != new_name:
            print(f"  - {old_name:15s} → {new_name}")
    
    # 파일 저장
    df.to_excel(file_path, index=False)
    print(f"\n✅ 파일 저장 완료: {file_path}")
    print(f"   백업 파일: {file_path}.bak")
    
    return df

if __name__ == "__main__":
    standardize_friendly_units()
