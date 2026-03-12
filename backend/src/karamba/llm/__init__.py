"""LLM module for Karamba framework."""
from .base import BaseLLM, LLMConfig, LLMMessage, LLMResponse
from .ollama_client import OllamaClient
from .anthropic_client import AnthropicClient


def create_llm(config: LLMConfig) -> BaseLLM:
    """Factory function to create LLM client based on provider."""
    if config.provider == "ollama":
        return OllamaClient(
            model=config.model,
            temperature=config.temperature,
            base_url=config.base_url or "http://localhost:11434"
        )
    elif config.provider == "anthropic":
        return AnthropicClient(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key
        )
    elif config.provider == "openai":
        # TODO: Implement OpenAI client
        raise NotImplementedError("OpenAI client not yet implemented")
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")


__all__ = [
    "BaseLLM",
    "LLMConfig",
    "LLMMessage",
    "LLMResponse",
    "OllamaClient",
    "AnthropicClient",
    "create_llm",
]