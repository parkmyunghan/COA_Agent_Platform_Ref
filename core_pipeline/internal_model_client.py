# core_pipeline/internal_model_client.py
# -*- coding: utf-8 -*-
"""
사내망 모델 API 클라이언트
단순 API 호출만 수행 (대화 기록 관리 없음)
"""
import requests
from typing import Optional, Dict


class InternalModelClient:
    """사내망 모델 API 클라이언트"""
    
    def __init__(
        self, 
        model: str, 
        base_url: str, 
        api_key: str,
        models_parameter: str = None,
        api_type: str = "completions",
        reasoning_effort: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        frequency_penalty: float = 0.1,
        enable_thinking: bool = False
    ):
        """
        사내망 모델 클라이언트 초기화
        
        Args:
            model: 모델 이름
            base_url: API 베이스 URL (엔드포인트 포함)
            api_key: API 키
            models_parameter: 특정 모델용 models 파라미터 (예: "mnt/models")
            api_type: API 타입 ("completions" 또는 "chat")
            reasoning_effort: reasoning 모델용 파라미터 (예: "medium")
            max_tokens: 최대 토큰 수
            temperature: 온도 파라미터
            frequency_penalty: 빈도 페널티
            enable_thinking: 사고 과정 활성화 여부
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.models_parameter = models_parameter
        self.api_type = api_type
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.enable_thinking = enable_thinking
    
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: Optional[int] = None) -> str:
        """
        프롬프트를 받아 LLM 응답을 반환
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택사항)
            max_tokens: 최대 토큰 수 (None이면 self.max_tokens 사용)
            
        Returns:
            LLM 응답 내용
        """
        # models 파라미터 설정
        models_value = self.models_parameter if self.models_parameter else self.model
        
        # max_tokens 설정
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        # API 타입에 따라 다른 형식으로 요청
        if self.api_type == "chat":
            # Chat API 형식 (messages 배열)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "models": models_value,
                "messages": messages,
                "max_tokens": tokens
            }
            
            # reasoning_effort 파라미터가 있으면 추가
            if self.reasoning_effort:
                payload["reasoning_effort"] = self.reasoning_effort
        else:
            # Completions API 형식 (prompt 문자열)
            # 시스템 프롬프트가 있으면 포함
            if system_prompt:
                full_prompt = f"시스템: {system_prompt}\n\n사용자: {prompt}\n어시스턴트: "
            else:
                full_prompt = f"사용자: {prompt}\n어시스턴트: "
            
            payload = {
                "models": models_value,
                "prompt": full_prompt,
                "max_tokens": tokens,
                "temperature": self.temperature,
                "frequency_penalty": self.frequency_penalty,
                "enable_thinking": str(self.enable_thinking)
            }
        
        # 헤더 설정
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*"
        }
        
        # API 호출
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                proxies={"http": None, "https": None},  # 프록시 비활성화
                timeout=120  # 타임아웃 120초
            )
            
            # 응답 확인
            response.raise_for_status()
            result = response.json()
            
            # 응답 추출 (API 타입에 따라 다름)
            if self.api_type == "chat":
                # Chat API 응답 형식
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice:
                        content = choice["message"].get("content")
                        if content is None:
                            # Tool calls 확인
                            tool_calls = choice["message"].get("tool_calls")
                            if tool_calls:
                                import json
                                content = f"[Tool Calls] {json.dumps(tool_calls, ensure_ascii=False)}"
                            
                            # Reasoning content 확인 (일부 모델 지원)
                            if not content:
                                reasoning = choice["message"].get("reasoning_content")
                                if reasoning:
                                    content = f"[Reasoning] {reasoning}"
                        
                        assistant_response = (content if content is not None else "").strip()
                    else:
                        text = choice.get("text")
                        assistant_response = (text if text is not None else "").strip()
                else:
                    assistant_response = str(result)
            else:
                # Completions API 응답 형식
                if "choices" in result and len(result["choices"]) > 0:
                    text = result["choices"][0].get("text")
                    assistant_response = (text if text is not None else "").strip()
                elif "text" in result:
                    text = result.get("text")
                    assistant_response = (text if text is not None else "").strip()
                else:
                    assistant_response = str(result)
                
                # 응답 정리 (completions 형식: "어시스턴트: " 접두사 제거)
                if assistant_response:
                    if assistant_response.startswith("어시스턴트:"):
                        assistant_response = assistant_response[len("어시스턴트:"):].strip()
                    if assistant_response.startswith("Assistant:"):
                        assistant_response = assistant_response[len("Assistant:"):].strip()
            
            return assistant_response
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"사내망 모델 API 호출 실패: {str(e)}")
        except Exception as e:
            # 상세 디버깅 정보 출력
            import traceback
            error_trace = traceback.format_exc()
            print(f"[DEBUG] Internal Model Error Trace: {error_trace}")
            try:
                print(f"[DEBUG] Raw Response: {response.text[:500]}")
            except:
                pass
            
            # 원본 에러 다시 발생 (상위에서 처리)
            if "'NoneType' object has no attribute 'strip'" in str(e):
                raise Exception(f"API 응답 파싱 실패 (NoneType): {str(e)}")
            raise e

