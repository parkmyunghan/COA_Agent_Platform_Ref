
import sys
import os
from unittest.mock import MagicMock
import pandas as pd

# Mocking modules that might fail in a script environment
sys.modules['common.logger'] = MagicMock()
sys.modules['common.utils'] = MagicMock()

from core_pipeline.palantir_search import PalantirSearch

def test_palantir_search_unified():
    print("Starting PalantirSearch integration test...")
    
    # Setup mocks
    rag_manager = MagicMock()
    rag_manager.is_available.return_value = True
    rag_manager.retrieve_with_context.return_value = [{"text": "Doc 1", "score": 0.8, "metadata": {"source": "doc1.txt"}}]
    
    ontology_manager = MagicMock()
    ontology_manager.graph = MagicMock()
    
    # Mock DataManager for structured search
    data_manager = MagicMock()
    unit_df = pd.DataFrame([{
        "부대명": "테스트부대",
        "병종": "보병",
        "임무역할": "방어",
        "상급부대": "1군단",
        "배치축선ID": "AXIS_01",
        "가용상태": "가용"
    }])
    data_manager.load_table.return_value = unit_df
    ontology_manager.data_manager = data_manager
    
    semantic_inference = MagicMock()
    semantic_inference.keyword_mappings = {}
    
    reasoning_engine = MagicMock()
    reasoning_engine.analyze_situation_hypothesis.return_value = ["가설 1"]
    
    # Initialize Search
    searcher = PalantirSearch(rag_manager, ontology_manager, semantic_inference, reasoning_engine)
    
    # 1. Test query with friendly keywords
    print("\nTesting '아군부대 현황' query...")
    results = searcher.search("아군부대 현황 알려줘")
    
    # Check if structured results are present
    unit_info_found = any(res.get('type') == 'friendly_unit_info' for res in results)
    hypothesis_found = any(res.get('type') == 'hypothesis' for res in results)
    
    if unit_info_found:
        print("✅ Structured unit info found in results.")
    else:
        print("❌ Structured unit info MISSING in results.")
        
    if hypothesis_found:
        print("✅ Tactical hypothesis found in results.")
    else:
        print("❌ Tactical hypothesis MISSING in results.")

    # 3. Test query with threat keywords
    print("\nTesting '현재 위협 상황' query...")
    results_threat = searcher.search("현재 가장 위험한 위협은 뭐야?")
    threat_info_found = any(res.get('type') == 'structured_threat_situation' for res in results_threat)
    
    if threat_info_found:
        print("✅ Structured threat info found in results.")
    else:
        print("❌ Structured threat info MISSING in results.")

    # 4. Test query with terrain keywords
    print("\nTesting '지형 정보' query...")
    results_terrain = searcher.search("이 지역의 지형이 어때?")
    terrain_info_found = any(res.get('type') == 'structured_terrain_cell' for res in results_terrain)
    
    if terrain_info_found:
        print("✅ Structured terrain info found in results.")
    else:
        print("❌ Structured terrain info MISSING in results.")

if __name__ == "__main__":
    try:
        test_palantir_search_unified()
        print("\nAll integration tests passed!")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
