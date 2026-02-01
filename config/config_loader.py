# config/config_loader.py
# -*- coding: utf-8 -*-
"""
설정 로더 모듈
YAML 설정 파일과 환경변수를 로드합니다.
"""
import os
import yaml
from pathlib import Path

def load_config():
    """환경설정 파일과 YAML 설정을 로드합니다."""
    
    # 환경설정.txt 파일 로드 (기존 방식 호환)
    config_file = os.path.join(os.path.dirname(__file__), "..", "환경설정.txt")
    if os.path.exists(config_file):
        try:
            with open(config_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    
                    if "=" in line:
                        k, v = line.split("=", 1)
                        key = k.strip()
                        value = v.strip()
                        
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        os.environ[key] = value
        except Exception as e:
            print(f"환경설정 로드 실패: {e}")
    
    # YAML 설정 파일 로드
    yaml_config = os.path.join(os.path.dirname(__file__), "model_config.yaml")
    if os.path.exists(yaml_config):
        try:
            with open(yaml_config, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                # 환경변수로 설정 값 설정
                if config_data:
                    if 'models' in config_data:
                        if 'embedding' in config_data['models']:
                            if 'path' in config_data['models']['embedding']:
                                os.environ['LOCAL_MODEL_PATH'] = config_data['models']['embedding']['path']
                        if 'llm' in config_data['models']:
                            if 'path' in config_data['models']['llm']:
                                os.environ['LLM_MODEL_PATH'] = config_data['models']['llm']['path']
                    if 'huggingface' in config_data:
                        if 'token' in config_data['huggingface'] and config_data['huggingface']['token']:
                            os.environ['HUGGINGFACE_HUB_TOKEN'] = config_data['huggingface']['token']
        except Exception as e:
            print(f"YAML 설정 로드 실패: {e}")
    
    print("환경설정 로드 완료")
    return True

def get_config(key, default=None):
    """환경변수 값을 가져옵니다."""
    return os.environ.get(key, default)

def get_huggingface_token():
    """허깅페이스 토큰을 가져옵니다."""
    return get_config("HUGGINGFACE_HUB_TOKEN")

def get_model_path():
    """로컬 임베딩 모델 경로를 가져옵니다."""
    # model_config.yaml에서 경로 가져오기
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), "model_config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                model_path = config.get('embedding', {}).get('model_path', None)
                if model_path:
                    # 상대 경로를 절대 경로로 변환
                    if not os.path.isabs(model_path):
                        base_dir = os.path.dirname(os.path.dirname(__file__))
                        model_path = os.path.join(base_dir, model_path)
                        model_path = os.path.normpath(model_path)
                    if os.path.exists(model_path):
                        return model_path
    except Exception as e:
        print(f"[WARN] Config load failed: {e}")
    
    # 기본 경로 확인
    default_path = os.path.join("models", "embedding", "rogel-embedding-v2")
    if os.path.exists(default_path) and os.path.isdir(default_path):
        if any(f.startswith("config.json") or f.startswith("modules.json") or f.startswith("sentence_bert_config.json") or f.startswith("pytorch_model") or f.startswith("model") for f in os.listdir(default_path)):
            return default_path
    
    # 환경변수 또는 기본값 사용
    return get_config("LOCAL_MODEL_PATH", default_path)

def get_llm_model_path():
    """LLM 모델 경로를 가져옵니다."""
    # model_config.yaml에서 경로 가져오기
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), "model_config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                model_path = config.get('llm', {}).get('model_path', None)
                if model_path:
                    # 상대 경로를 절대 경로로 변환
                    if not os.path.isabs(model_path):
                        base_dir = os.path.dirname(os.path.dirname(__file__))
                        model_path = os.path.join(base_dir, model_path)
                        model_path = os.path.normpath(model_path)
                    if os.path.exists(model_path):
                        return model_path
    except Exception as e:
        print(f"[WARN] Config load failed: {e}")
    
    # 기본 경로 확인
    default_path = os.path.join("models", "llm", "beomi-gemma-ko-2b")
    if os.path.exists(default_path) and os.path.isdir(default_path):
        if any(f.startswith("model") or f.startswith("config.json") for f in os.listdir(default_path)):
            return default_path
    
    # 환경변수 또는 기본값 사용
    return get_config("LLM_MODEL_PATH", default_path)

if __name__ == "__main__":
    load_config()

