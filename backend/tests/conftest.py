"""Pytest configuration and fixtures for Karamba tests."""
import asyncio
from pathlib import Path
from typing import AsyncIterator, List
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from karamba.core.models import (
    PhaseStatus, PhaseType, PhaseResult, AgentRequest,
    VerificationResult
)
from karamba.llm import BaseLLM, LLMMessage, LLMResponse, LLMConfig
from karamba.document import DocumentChunk


class MockLLM(BaseLLM):
    """Mock LLM for testing."""

    def __init__(self, model: str = "mock-model", responses: List[str] = None):
        super().__init__(model=model)
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.last_messages = []

    async def generate(
        self,
        messages: List[LLMMessage],
        system: str = None,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """Generate mock response."""
        self.last_messages = messages
        response_text = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1

        return LLMResponse(
            content=response_text,
            model=self.model,
            usage={"total_tokens": len(response_text.split())}
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system: str = None,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream mock response."""
        response = await self.generate(messages, system, max_tokens, **kwargs)
        for word in response.content.split():
            yield word + " "

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        response_model: type[BaseModel],
        system: str = None,
        **kwargs
    ) -> BaseModel:
        """Generate structured mock response."""
        # Simple mock implementation
        response = await self.generate(messages, system, **kwargs)
        # Return a mock structured response
        return response_model(main_question=response.content)


@pytest.fixture
def mock_llm() -> MockLLM:
    """Create a mock LLM."""
    return MockLLM(responses=[
        "Planning phase output: Break down into sub-questions",
        "Retrieval phase output: Retrieved relevant chunks",
        "Reasoning phase output: Based on the information, the answer is X"
    ])


@pytest.fixture
def sample_agent_request() -> AgentRequest:
    """Create a sample agent request."""
    return AgentRequest(
        query="What is the capital of France?",
        session_id="test-session-123",
        document_ids=["doc1", "doc2"]
    )


@pytest.fixture
def sample_phase_result() -> PhaseResult:
    """Create a sample phase result."""
    return PhaseResult(
        phase_name="planning",
        phase_type=PhaseType.PLANNING,
        status=PhaseStatus.COMPLETED,
        output="Test output",
        verification_results=[
            VerificationResult(
                passed=True,
                rule_name="not_empty",
                message="Output is not empty"
            )
        ]
    )


@pytest.fixture
def sample_document_chunks() -> List[DocumentChunk]:
    """Create sample document chunks."""
    return [
        DocumentChunk(
            content="This is the first chunk of text.",
            chunk_id="doc1_chunk_0",
            document_id="doc1",
            metadata={"page": 1}
        ),
        DocumentChunk(
            content="This is the second chunk of text.",
            chunk_id="doc1_chunk_1",
            document_id="doc1",
            metadata={"page": 1}
        ),
        DocumentChunk(
            content="This is from another document.",
            chunk_id="doc2_chunk_0",
            document_id="doc2",
            metadata={"page": 1}
        )
    ]


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for tests."""
    test_dir = tmp_path / "karamba_test"
    test_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (test_dir / "vector_store").mkdir(exist_ok=True)
    (test_dir / "uploads").mkdir(exist_ok=True)
    (test_dir / "config").mkdir(exist_ok=True)

    return test_dir


@pytest.fixture
def sample_pdf_path(temp_test_dir: Path) -> Path:
    """Create a sample test file path."""
    file_path = temp_test_dir / "uploads" / "test_document.pdf"
    file_path.write_bytes(b"%PDF-1.4 mock content")
    return file_path


@pytest.fixture
def sample_text_content() -> str:
    """Create sample text content for testing."""
    return """
    This is a sample document for testing.
    It contains multiple paragraphs and sentences.

    The document discusses various topics including:
    - Topic A
    - Topic B
    - Topic C

    Each topic has detailed information that can be used
    for testing the chunking and retrieval functionality.
    """


@pytest.fixture
def llm_config() -> LLMConfig:
    """Create a test LLM configuration."""
    return LLMConfig(
        provider="ollama",
        model="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.7
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
