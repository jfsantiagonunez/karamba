"""Ollama LLM client implementation."""
import json
from typing import Any, AsyncIterator, Optional
import httpx
from pydantic import BaseModel
from loguru import logger

from .base import BaseLLM, LLMMessage, LLMResponse


class OllamaClient(BaseLLM):
    """Ollama local LLM client."""
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        temperature: float = 0.7,
        base_url: str = "http://localhost:11434",
        **kwargs: Any
    ):
        super().__init__(model, temperature, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate response from Ollama."""
        ollama_messages = self._format_messages(messages, system)
        
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return LLMResponse(
                content=result["message"]["content"],
                model=self.model,
                usage={
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                }
            )
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream response from Ollama."""
        ollama_messages = self._format_messages(messages, system)
        
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise
    
    async def generate_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        system: Optional[str] = None,
        **kwargs: Any
    ) -> BaseModel:
        """Generate structured output."""
        # Add JSON schema instruction to system prompt
        schema = response_model.model_json_schema()
        json_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"Do not include any markdown formatting or explanation."
        )
        
        enhanced_system = (system or "") + json_instruction
        
        response = await self.generate(
            messages=messages,
            system=enhanced_system,
            max_tokens=kwargs.get("max_tokens", 2000)
        )
        
        # Parse JSON response
        try:
            # Clean potential markdown formatting
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            return response_model(**data)
        except Exception as e:
            logger.error(f"Failed to parse structured output: {e}")
            logger.error(f"Raw content: {response.content}")
            raise ValueError(f"Failed to parse structured response: {e}")
    
    def _format_messages(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None
    ) -> list[dict[str, str]]:
        """Format messages for Ollama API."""
        formatted = []
        
        if system:
            formatted.append({"role": "system", "content": system})
        
        for msg in messages:
            formatted.append({"role": msg.role, "content": msg.content})
        
        return formatted
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()