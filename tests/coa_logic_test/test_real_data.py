import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core_pipeline.coa_scorer import COAScorer

def test_real_threats():
    """실제 위협상황 데이터(THR001, THR002, THR006)에 대한 상세 분석"""
    
    # 1. Load Real Data
    data_path = "data_lake/위협상황.xlsx"
    try:
        df = pd.read_excel(data_path)
        print(f"Loaded {len(df)} threats from {data_path}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    
    # 2. Filter THR001, THR002, THR006
    threat_ids = ["THR001", "THR002", "THR006"]
    threats = df[df['위협ID'].isin(threat_ids)]
    
    if threats.empty:
        print(f"No threats found with IDs: {threat_ids}")
        print(f"Available IDs: {df['위협ID'].tolist()}")
        return
    
    print(f"\nFound {len(threats)} threats:")
    print(threats[['위협ID', '위협유형코드', '위협수준']].to_string())
    
    # 3. Define COA Types
    COA_TYPES = [
        "defense", "offensive", "counter_attack", 
        "preemptive", "deterrence", "maneuver", "information_ops"
    ]
    
    results = []
    
    for _, threat in threats.iterrows():
        threat_id = threat['위협ID']
        threat_type = threat.get('위협유형코드', 'Unknown')
        threat_level_raw = threat.get('위협수준', 50)
        
        # Normalize threat level
        if isinstance(threat_level_raw, str):
            threat_level_upper = threat_level_raw.upper()
            if threat_level_upper in ['HIGH', '높음', 'H']:
                threat_level = 0.9
            elif threat_level_upper in ['MEDIUM', '중간', 'M']:
                threat_level = 0.5
            elif threat_level_upper in ['LOW', '낮음', 'L']:
                threat_level = 0.2
            else:
                try:
                    threat_level = float(threat_level_raw) / 100.0
                except:
                    threat_level = 0.5
        else:
            threat_level = float(threat_level_raw) / 100.0 if threat_level_raw > 1 else threat_level_raw
        
        print(f"\n{'='*60}")
        print(f"Threat: {threat_id} | Type: {threat_type} | Level: {threat_level}")
        print(f"{'='*60}")
        
        coa_scores = []
        
        for coa_type in COA_TYPES:
            scorer = COAScorer(coa_type=coa_type)
            
            # Build context as realistically as possible
            context = {
                "situation_id": threat_id,
                "threat_level": threat_level,
                "threat_type": threat_type,
                "coa_type": coa_type,
                # Real scenario assumptions (from UI logic or defaults)
                "resource_availability": 0.7,
                "asset_capability": 0.6,
                "environment_compatible": True,
                "historical_success": 0.5
            }
            
            score_result = scorer.calculate_score(context)
            total_score = score_result['total']
            breakdown = score_result['breakdown']
            
            coa_scores.append({
                "coa_type": coa_type,
                "score": total_score,
                "breakdown": breakdown
            })
            
            print(f"  {coa_type:18s}: {total_score:.4f} | Threat:{breakdown.get('threat', 0):.3f}, Mission:{breakdown.get('mission_alignment', 0):.3f}, Res:{breakdown.get('resources', 0):.3f}, Env:{breakdown.get('environment', 0):.3f}, Hist:{breakdown.get('historical', 0):.3f}")
        
        # Sort by score
        coa_scores.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n  >>> TOP CHOICE: {coa_scores[0]['coa_type'].upper()} (Score: {coa_scores[0]['score']:.4f})")
        
        results.append({
            "threat_id": threat_id,
            "threat_type": threat_type,
            "threat_level": threat_level,
            "top_choice": coa_scores[0]['coa_type'],
            "top_score": coa_scores[0]['score'],
            "all_scores": {c['coa_type']: c['score'] for c in coa_scores}
        })
    
    # Save results
    df_results = pd.DataFrame(results)
    output_path = "tests/coa_logic_test/real_data_test_results.csv"
    df_results.to_csv(output_path, index=False)
    print(f"\n\nResults saved to {output_path}")
    
    return results

if __name__ == "__main__":
    test_real_threats()
