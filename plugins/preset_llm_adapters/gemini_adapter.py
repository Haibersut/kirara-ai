from pydantic import BaseModel
import requests
from framework.llm.adapter import LLMBackendAdapter
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse

class GeminiConfig(BaseModel):
    api_key: str
    api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    class Config:
        frozen = True

class GeminiAdapter(LLMBackendAdapter):
    def __init__(self, config: GeminiConfig):
        self.config = config

    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        api_url = f"{self.config.api_base}/models/{req.model}:generateContent"
        headers = {
            "x-goog-api-key": self.config.api_key,
            "Content-Type": "application/json"
        }

        data = {
            "contents": [{
                "role": msg.role,
                "parts": [{"text": msg.content}]
            } for msg in req.messages],
            "generationConfig": {
                "temperature": req.temperature,
                "topP": req.top_p,
                "topK": 40,
                "maxOutputTokens": req.max_tokens,
                "stopSequences": req.stop
            },
            "safetySettings": []
        }

        # Remove None fields
        data = {k: v for k, v in data.items() if v is not None}
        
        response = requests.post(api_url, json=data, headers=headers)
        try:
            response.raise_for_status()
            response_data = response.json()
        except Exception as e:
            print(f"API Response: {response.text}")
            raise e
        print(response_data)
        
        # Transform Gemini response format to match expected LLMChatResponse format
        transformed_response = {
            "id": response_data.get("promptFeedback", {}).get("blockReason", ""),
            "object": "chat.completion",
            "created": 0,  # Gemini doesn't provide creation timestamp
            "model": req.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_data["candidates"][0]["content"]["parts"][0]["text"]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,  # Gemini doesn't provide token counts
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        return LLMChatResponse(**transformed_response)
