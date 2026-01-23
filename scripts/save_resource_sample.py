
import pandas as pd
from pathlib import Path
import json

def save_sample_json():
    file_path = Path("data_lake/임무별_자원할당.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    sample = df.head(20).to_dict(orient='records')
    
    def clean_json(obj):
        if isinstance(obj, list):
            return [clean_json(i) for i in obj]
        if isinstance(obj, dict):
            return {k: clean_json(v) for k, v in obj.items()}
        if pd.isna(obj):
            return None
        return obj

    clean_sample = clean_json(sample)
    
    with open("resource_sample.json", "w", encoding='utf-8') as f:
        json.dump(clean_sample, f, ensure_ascii=False, indent=2)
    
    print("Sample saved to resource_sample.json")

if __name__ == "__main__":
    save_sample_json()
