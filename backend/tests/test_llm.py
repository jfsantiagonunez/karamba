"""Tests for LLM components."""
import pytest
from pydantic import ValidationError

from karamba.llm import (
    BaseLLM, LLMConfig, LLMMessage, LLMResponse,
    create_llm, OllamaClient, AnthropicClient
)


class TestLLMMessage:
    """Tests for LLMMessage model."""

    def test_create_llm_message(self):
        """Test creating an LLM message."""
        message = LLMMessage(role="user", content="Hello")

        assert message.role == "user"
        assert message.content == "Hello"

    def test_llm_message_roles(self):
        """Test different message roles."""
        user_msg = LLMMessage(role="user", content="Question")
        assistant_msg = LLMMessage(role="assistant", content="Answer")
        system_msg = LLMMessage(role="system", content="Instructions")

        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"
        assert system_msg.role == "system"


class TestLLMResponse:
    """Tests for LLMResponse model."""

    def test_create_llm_response(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Generated response",
            model="test-model"
        )

        assert response.content == "Generated response"
        assert response.model == "test-model"
        assert response.usage == {}
        assert response.metadata == {}

    def test_llm_response_with_usage(self):
        """Test LLM response with usage information."""
        response = LLMResponse(
            content="Response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )

        assert response.usage["total_tokens"] == 30
        assert response.usage["prompt_tokens"] == 10


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_create_llm_config(self):
        """Test creating an LLM configuration."""
        config = LLMConfig(
            provider="ollama",
            model="llama3.2:3b"
        )

        assert config.provider == "ollama"
        assert config.model == "llama3.2:3b"
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 2000  # default

    def test_llm_config_with_api_key(self):
        """Test LLM config with API key."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4",
            api_key="test-key-123"
        )

        assert config.api_key == "test-key-123"

    def test_llm_config_with_base_url(self):
        """Test LLM config with custom base URL."""
        config = LLMConfig(
            provider="ollama",
            model="llama3.2",
            base_url="http://custom-server:11434"
        )

        assert config.base_url == "http://custom-server:11434"

    def test_llm_config_temperature_validation(self):
        """Test temperature validation."""
        # Valid temperatures
        config1 = LLMConfig(provider="ollama", model="test", temperature=0.0)
        config2 = LLMConfig(provider="ollama", model="test", temperature=1.0)
        config3 = LLMConfig(provider="ollama", model="test", temperature=2.0)

        assert config1.temperature == 0.0
        assert config2.temperature == 1.0
        assert config3.temperature == 2.0

        # Invalid temperatures
        with pytest.raises(ValidationError):
            LLMConfig(provider="ollama", model="test", temperature=-0.1)

        with pytest.raises(ValidationError):
            LLMConfig(provider="ollama", model="test", temperature=2.1)

    def test_llm_config_max_tokens_validation(self):
        """Test max_tokens validation."""
        config = LLMConfig(provider="ollama", model="test", max_tokens=4000)
        assert config.max_tokens == 4000

        # Invalid max_tokens
        with pytest.raises(ValidationError):
            LLMConfig(provider="ollama", model="test", max_tokens=0)

        with pytest.raises(ValidationError):
            LLMConfig(provider="ollama", model="test", max_tokens=-100)


class TestBaseLLM:
    """Tests for BaseLLM abstract class."""

    def test_base_llm_init(self, mock_llm):
        """Test BaseLLM initialization."""
        assert mock_llm.model == "mock-model"
        assert mock_llm.temperature == 0.7  # default from BaseLLM

    @pytest.mark.asyncio
    async def test_mock_llm_generate(self, mock_llm):
        """Test MockLLM generate method."""
        messages = [LLMMessage(role="user", content="Test question")]

        response = await mock_llm.generate(messages)

        assert isinstance(response, LLMResponse)
        assert response.content
        assert response.model == "mock-model"
        assert mock_llm.call_count == 1

    @pytest.mark.asyncio
    async def test_mock_llm_multiple_calls(self, mock_llm):
        """Test MockLLM with multiple calls."""
        messages = [LLMMessage(role="user", content="Test")]

        response1 = await mock_llm.generate(messages)
        response2 = await mock_llm.generate(messages)
        response3 = await mock_llm.generate(messages)

        assert mock_llm.call_count == 3
        # First call uses first response
        assert "Planning" in response1.content
        # Second call uses second response
        assert "Retrieval" in response2.content
        # Third call uses third response
        assert "Reasoning" in response3.content

    @pytest.mark.asyncio
    async def test_mock_llm_stream(self, mock_llm):
        """Test MockLLM streaming."""
        messages = [LLMMessage(role="user", content="Test")]

        chunks = []
        async for chunk in mock_llm.generate_stream(messages):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0


class TestCreateLLM:
    """Tests for create_llm factory function."""

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        config = LLMConfig(
            provider="ollama",
            model="llama3.2:3b",
            base_url="http://localhost:11434"
        )

        llm = create_llm(config)

        assert isinstance(llm, OllamaClient)
        assert llm.model == "llama3.2:3b"

    def test_create_anthropic_client(self):
        """Test creating Anthropic client."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4",
            api_key="test-key"
        )

        llm = create_llm(config)

        assert isinstance(llm, AnthropicClient)
        assert llm.model == "claude-sonnet-4"

    def test_create_llm_unknown_provider(self):
        """Test creating LLM with unknown provider."""
        config = LLMConfig(
            provider="unknown-provider",
            model="test"
        )

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm(config)

    def test_create_openai_not_implemented(self):
        """Test that OpenAI client is not yet implemented."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4"
        )

        with pytest.raises(NotImplementedError, match="OpenAI client not yet implemented"):
            create_llm(config)


class TestOllamaClient:
    """Tests for OllamaClient."""

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        client = OllamaClient(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.8
        )

        assert client.model == "llama3.2:3b"
        assert client.temperature == 0.8
        assert client.base_url == "http://localhost:11434"

    def test_ollama_client_default_base_url(self):
        """Test Ollama client with default base URL."""
        client = OllamaClient(model="llama3.2")

        assert client.base_url == "http://localhost:11434"


class TestAnthropicClient:
    """Tests for AnthropicClient."""

    def test_create_anthropic_client(self):
        """Test creating Anthropic client."""
        client = AnthropicClient(
            model="claude-sonnet-4",
            api_key="test-key",
            temperature=0.9
        )

        assert client.model == "claude-sonnet-4"
        assert client.temperature == 0.9
        assert client.api_key == "test-key"

    def test_anthropic_client_requires_api_key(self):
        """Test that Anthropic client requires API key."""
        # Should not raise on initialization (API key can be from env)
        client = AnthropicClient(model="claude-sonnet-4")
        assert client.model == "claude-sonnet-4"
