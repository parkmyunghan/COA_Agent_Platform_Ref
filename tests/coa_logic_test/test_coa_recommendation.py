
import sys
import os
import pandas as pd
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core_pipeline.coa_scorer import COAScorer
from tests.coa_logic_test.test_scenario_generator import TestScenarioGenerator

def run_tests():
    print("Starting COA Logic Tests...")
    
    # 1. Generate Scenarios
    generator = TestScenarioGenerator()
    scenarios = generator.generate_scenarios(num_scenarios=50) # Generate 50 scenarios
    print(f"Generated {len(scenarios)} scenarios.")

    # 2. Initialize Scorer (Mocking DataManager/Config if needed, but COAScorer handles None gracefully)
    # We want to test the raw logic first.
    scorer_defense = COAScorer(coa_type="defense")
    scorer_offensive = COAScorer(coa_type="offensive")
    scorer_counter = COAScorer(coa_type="counter_attack")
    
    # Defined COA Types to test against
    COA_TYPES = [
        "defense", "offensive", "counter_attack", 
        "preemptive", "deterrence", "maneuver", "information_ops"
    ]
    
    results = []

    for scenario in scenarios:
        # Simulate getting recommendations for ALL types for each scenario
        scenario_results = []
        
        for coa_type in COA_TYPES:
            # Create a specific scorer for this type (or reuse)
            scorer = COAScorer(coa_type=coa_type)
            
            # Construct context for scoring
            # Assuming logic_defense_enhanced.py's map preparation
            context = {
                "situation_id": scenario['situation_id'],
                "threat_level": scenario['threat_level'],
                "threat_type": scenario['위협유형'],
                "coa_type": coa_type,
                "resource_availability": 0.8, # Assume some resource availability
                "asset_capability": 0.7,      # Assume some capability
                "environment_compatible": True, # Assume fit
                "historical_success": 0.6     # Assume some history
            }
            
            # Calculate Score
            score_result = scorer.calculate_score(context)
            total_score = score_result['total']
            
            scenario_results.append({
                "coa_type": coa_type,
                "score": total_score,
                "breakdown": score_result['breakdown']
            })
        
        # Determine the winner(s) for this scenario
        scenario_results.sort(key=lambda x: x['score'], reverse=True)
        top_choice = scenario_results[0]
        
        results.append({
            "scenario": scenario,
            "top_choice": top_choice['coa_type'],
            "top_score": top_choice['score'],
            "all_scores": {r['coa_type']: r['score'] for r in scenario_results}
        })

    # 3. Save Results
    df = pd.DataFrame(results)
    output_path = "tests/coa_logic_test/test_results.csv"
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")
    
    return results

if __name__ == "__main__":
    run_tests()
