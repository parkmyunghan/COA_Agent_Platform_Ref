
import pandas as pd
import sys
import os

def analyze_results(csv_path="tests/coa_logic_test/test_results.csv"):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    total_scenarios = len(df)
    unique_recommendations = df['top_choice'].nunique()
    
    print(f"Total Scenarios: {total_scenarios}")
    print(f"Unique COA Types Recommended: {unique_recommendations}")
    
    # 1. Distribution of Recommendations
    distribution = df['top_choice'].value_counts()
    print("\n[Recommendation Distribution]")
    print(distribution)
    
    # 2. Dominance Analysis
    dominant_type = distribution.idxmax()
    dominance_rate = distribution.max() / total_scenarios
    
    print(f"\nDominant Type: {dominant_type} ({dominance_rate*100:.1f}%)")
    
    # 3. Sensitivity Check (Do recommendations change with Threat Type?)
    # Group by threat type (from scenario string or add column in test runner)
    # Parsing 'scenario' column string is messy, so we rely on the fact that test_scenario_generator included 'threat_type'
    # But csv stringifies dicts. Let's do a simple string check/grouping.
    
    report_content = f"""# COA Logic Diversity Analysis Report

## Summary
- **Total Scenarios**: {total_scenarios}
- **Unique Recommendations**: {unique_recommendations}
- **Dominant COA Type**: **{dominant_type}** ({dominance_rate*100:.1f}%)

## Recommendation Distribution
```
{distribution.to_string()}
```

## Observations
- If Dominant Rate > 80%, the logic is highly biased towards that specific COA type.
- If Unique Recommendations < 3 (out of 7), the logic lacks sensitivity.

## Raw Results (First 5)
{df.head().to_markdown()}
"""
    
    with open("tests/coa_logic_test/analysis_report.md", "w") as f:
        f.write(report_content)
    
    print("\nReport saved to tests/coa_logic_test/analysis_report.md")

if __name__ == "__main__":
    analyze_results()
