from core_pipeline.coa_scorer import COAScorer

class MockDataManager:
    def __init__(self):
        self.coa_library = None

def test_scorer():
    try:
        data_manager = MockDataManager()
        scorer = COAScorer(data_manager=data_manager, config={})
        print("✅ COAScorer initialized successfully")
        
        # Test a mock score calculation
        score = scorer._calculate_mission_alignment_score(
            context={
                'threat_type': '인침', 
                'coa_type': 'defense', 
                'coa_suitability': '인침', 
                'coa_id': 'TEST_001'
            }
        )
        print(f"✅ Score calculation worked: {score}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scorer()
