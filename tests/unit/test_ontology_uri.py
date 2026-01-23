
import sys
import os
import re
from urllib.parse import quote
from rdflib import URIRef, Namespace

# 프로젝트 루트 경로 설정
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager

def test_make_uri_safe():
    print("Testing _make_uri_safe function...")
    
    # Mock OntologyManager (we only need the method)
    manager = EnhancedOntologyManager({"ontology_path": "./knowledge/ontology"})
    
    test_cases = [
        ("NormalName", "NormalName"),
        ("Name With Spaces", "Name_With_Spaces"),
        ("Name  With   Multiple    Spaces", "Name_With_Multiple_Spaces"),
        ("Name_With_Underscores", "Name_With_Underscores"),
        ("Name(With)Parens", "NameWithParens"),
        ("Name[With]Brackets", "NameWithBrackets"),
        ("Name<With>Angles", "NameWithAngles"),
        ("Name/With/Slashes", "Name/With/Slashes"), # Slashes might be kept or removed depending on regex
        ("Name:With:Colons", "NameWithColons"),
        ("Mixed & Special + Chars", "Mixed_Special_Chars"),
        ("한글 이름 테스트", "한글_이름_테스트"),
        ("한글(괄호)포함", "한글괄호포함"),
    ]
    
    # Manager의 실제 regex 확인 (우리가 수정한 regex)
    # s = re.sub(r'[(){}\[\]<>|\\^`"\':;,?#%&+=]', '', s)
    
    for input_str, expected in test_cases:
        result = manager._make_uri_safe(input_str)
        print(f"Input: '{input_str}' -> Output: '{result}'")
        
        # 기본 검증: 공백이 없어야 함
        if ' ' in result:
            print(f"❌ FAILED: Result contains spaces: '{result}'")
        else:
            print("✅ Space check passed")
            
        # 특수문자 검증
        if any(char in result for char in '()[]<>'):
            print(f"❌ FAILED: Result contains forbidden chars: '{result}'")
        else:
            print("✅ Forbidden char check passed")

    # URIRef 생성 테스트
    print("\nTesting URIRef creation...")
    ns = Namespace("http://defense-ai.kr/ontology#")
    
    try:
        uri = URIRef(ns[manager._make_uri_safe("Test String With Spaces")])
        print(f"✅ URIRef created successfully: {uri}")
        
        uri_korean = URIRef(ns[manager._make_uri_safe("한글 테스트 문자열")])
        print(f"✅ Korean URIRef created successfully: {uri_korean}")
        
    except Exception as e:
        print(f"❌ URIRef creation failed: {e}")

if __name__ == "__main__":
    test_make_uri_safe()
