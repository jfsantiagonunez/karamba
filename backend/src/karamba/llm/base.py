"""Abstract LLM interface for Karamba framework."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """Single message in conversation."""
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, model: str, temperature: float = 0.7, **kwargs: Any):
        self.model = model
        self.temperature = temperature
        self.kwargs = kwargs
    
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate a response from messages."""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        system: Optional[str] = None,
        **kwargs: Any
    ) -> BaseModel:
        """Generate structured output matching a Pydantic model."""
        pass


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""
    provider: str = Field(..., description="Provider name: 'ollama', 'anthropic', 'openai'")
    model: str = Field(..., description="Model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0)
    api_key: Optional[str] = Field(default=None, description="API key if needed")
    base_url: Optional[str] = Field(default=None, description="Custom base URL")
    
    class Config:
        extra = "allow"