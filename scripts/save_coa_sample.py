
import pandas as pd
from pathlib import Path
import json

def save_sample_json():
    file_path = Path("data_lake/COA_Library.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    sample = df.head(10).to_dict(orient='records')
    
    # Handle non-serializable objects (like NaN)
    def clean_json(obj):
        if isinstance(obj, list):
            return [clean_json(i) for i in obj]
        if isinstance(obj, dict):
            return {k: clean_json(v) for k, v in obj.items()}
        if pd.isna(obj):
            return None
        return obj

    clean_sample = clean_json(sample)
    
    with open("coa_sample.json", "w", encoding='utf-8') as f:
        json.dump(clean_sample, f, ensure_ascii=False, indent=2)
    
    print("Sample saved to coa_sample.json")

if __name__ == "__main__":
    save_sample_json()
