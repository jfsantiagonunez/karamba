"""Anthropic Claude client implementation."""
import json
from typing import Any, AsyncIterator, Optional
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from loguru import logger

from .base import BaseLLM, LLMMessage, LLMResponse


class AnthropicClient(BaseLLM):
    """Anthropic Claude client."""
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        **kwargs: Any
    ):
        super().__init__(model, temperature, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def generate(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate response from Claude."""
        claude_messages = self._format_messages(messages)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                system=system or "",
                messages=claude_messages
            )
            
            content = response.content[0].text if response.content else ""
            
            return LLMResponse(
                content=content,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                }
            )
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise
    
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream response from Claude."""
        claude_messages = self._format_messages(messages)
        
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                system=system or "",
                messages=claude_messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    async def generate_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        system: Optional[str] = None,
        **kwargs: Any
    ) -> BaseModel:
        """Generate structured output from Claude."""
        schema = response_model.model_json_schema()
        json_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this exact schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"Do not include any markdown code blocks, explanations, or other text."
        )
        
        enhanced_system = (system or "") + json_instruction
        
        response = await self.generate(
            messages=messages,
            system=enhanced_system,
            max_tokens=kwargs.get("max_tokens", 4000)
        )
        
        try:
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            return response_model(**data)
        except Exception as e:
            logger.error(f"Failed to parse structured output: {e}")
            logger.error(f"Raw content: {response.content}")
            raise ValueError(f"Failed to parse structured response: {e}")
    
    def _format_messages(self, messages: list[LLMMessage]) -> list[dict[str, str]]:
        """Format messages for Claude API (no system in messages array)."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role != "system"
        ]