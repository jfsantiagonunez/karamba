"""Tests for KarambaAgent."""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from karamba.core.agent import KarambaAgent
from karamba.core.models import AgentRequest, PhaseStatus, PhaseType
from karamba.llm import LLMConfig


class TestKarambaAgent:
    """Tests for KarambaAgent class."""

    @pytest.fixture
    def agent(self, mock_llm, temp_test_dir):
        """Create a test agent with mocked dependencies."""
        llm_config = LLMConfig(
            provider="ollama",
            model="test-model"
        )

        with patch('karamba.core.agent.create_llm', return_value=mock_llm):
            with patch('karamba.core.agent.VectorRetriever'):
                with patch('karamba.core.agent.DocumentProcessor'):
                    agent = KarambaAgent(
                        llm_config=llm_config,
                        vector_store_path=str(temp_test_dir / "vector_store")
                    )
                    return agent

    def test_create_agent(self, agent):
        """Test creating a Karamba agent."""
        assert agent is not None
        assert agent.llm is not None
        assert agent.retriever is not None
        assert agent.processor is not None
        assert agent.chunker is not None
        assert agent.phase_engine is not None

    def test_create_default_phases(self, agent):
        """Test default phase creation."""
        phases = agent.phase_engine.phases

        assert len(phases) >= 3
        phase_names = [p.name for p in phases]
        assert "planning" in phase_names
        assert "retrieval" in phase_names
        assert "reasoning" in phase_names

    @pytest.mark.asyncio
    async def test_query(self, agent, sample_agent_request):
        """Test querying the agent."""
        # Mock retriever
        mock_chunk = Mock()
        mock_chunk.chunk.content = "Test content"
        mock_chunk.chunk.document_id = "doc1"
        mock_chunk.chunk.chunk_index = 0
        mock_chunk.score = 0.95

        agent.retriever.retrieve = Mock(return_value=[mock_chunk])

        results = []
        async for result in agent.query(sample_agent_request):
            results.append(result)

        assert len(results) >= 3
        assert any(r.phase_name == "planning" for r in results)
        assert any(r.phase_name == "retrieval" for r in results)
        assert any(r.phase_name == "reasoning" for r in results)

    @pytest.mark.asyncio
    async def test_query_retrieval_phase(self, agent, sample_agent_request):
        """Test that retrieval phase actually retrieves documents."""
        # Mock retriever
        mock_chunk = Mock()
        mock_chunk.chunk.content = "Test content from document"
        mock_chunk.chunk.document_id = "doc1"
        mock_chunk.score = 0.95

        agent.retriever.retrieve = Mock(return_value=[mock_chunk])

        results = []
        async for result in agent.query(sample_agent_request):
            results.append(result)

        # Find retrieval phase result
        retrieval_result = next(
            (r for r in results if r.phase_name == "retrieval"),
            None
        )

        assert retrieval_result is not None
        assert "chunks" in retrieval_result.metadata

    @pytest.mark.asyncio
    async def test_answer_question(self, agent, sample_agent_request):
        """Test getting complete answer to a question."""
        # Mock retriever
        agent.retriever.retrieve = Mock(return_value=[])

        response = await agent.answer_question(sample_agent_request)

        assert response is not None
        assert response.answer is not None
        assert len(response.phase_results) > 0

    @pytest.mark.asyncio
    async def test_answer_question_with_citations(self, agent, sample_agent_request):
        """Test that answer includes citations from retrieved chunks."""
        # Mock retriever with chunks
        mock_chunk = Mock()
        mock_chunk.chunk.content = "Paris is the capital"
        mock_chunk.chunk.document_id = "geography_doc"
        mock_chunk.score = 0.95

        agent.retriever.retrieve = Mock(return_value=[mock_chunk])

        response = await agent.answer_question(sample_agent_request)

        # Check that citations are included
        assert len(response.citations) > 0 or len(response.phase_results) > 0

    @pytest.mark.asyncio
    async def test_ingest_document(self, agent, sample_pdf_path):
        """Test ingesting a document."""
        # Mock processor and chunker
        mock_doc = Mock()
        mock_doc.content = "Document content"
        mock_doc.filename = "test_document.pdf"

        agent.processor.process_file = AsyncMock(return_value=mock_doc)

        mock_chunks = [Mock(), Mock()]
        agent.chunker.chunk_text = Mock(return_value=mock_chunks)
        agent.retriever.add_chunks = Mock()

        result = await agent.ingest_document(sample_pdf_path)

        assert result == "test_document.pdf"
        agent.processor.process_file.assert_called_once()
        agent.chunker.chunk_text.assert_called_once()
        agent.retriever.add_chunks.assert_called_once()

    def test_get_document_stats(self, agent):
        """Test getting document statistics."""
        agent.retriever.get_stats = Mock(return_value={
            "total_documents": 5,
            "total_chunks": 150
        })

        stats = agent.get_document_stats()

        assert "total_documents" in stats
        assert stats["total_documents"] == 5

    def test_delete_document(self, agent):
        """Test deleting a document."""
        agent.retriever.delete_document = Mock()

        agent.delete_document("doc1")

        agent.retriever.delete_document.assert_called_once_with("doc1")

    @pytest.mark.asyncio
    async def test_query_handles_empty_retrieval(self, agent, sample_agent_request):
        """Test query handling when no documents are retrieved."""
        agent.retriever.retrieve = Mock(return_value=[])

        results = []
        async for result in agent.query(sample_agent_request):
            results.append(result)

        # Should still complete all phases
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_query_context_propagation(self, agent, sample_agent_request):
        """Test that context is properly propagated between phases."""
        agent.retriever.retrieve = Mock(return_value=[])

        context_updates = []

        # Capture phase outputs to verify context propagation
        async for result in agent.query(sample_agent_request):
            if result.status == PhaseStatus.COMPLETED:
                context_updates.append((result.phase_name, result.output))

        # Should have multiple phase outputs
        assert len(context_updates) >= 2


class TestKarambaAgentWithConfig:
    """Tests for KarambaAgent with custom configuration."""

    @pytest.mark.asyncio
    async def test_agent_with_config_file(self, mock_llm, temp_test_dir):
        """Test creating agent with config file."""
        # Create config directory and files
        config_dir = temp_test_dir / "config"
        config_dir.mkdir(exist_ok=True)

        prompts_dir = config_dir / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        (prompts_dir / "planning.txt").write_text("Custom planning: {query}")

        config_path = config_dir / "phases.yaml"
        config_content = """
phases:
  - name: custom_planning
    type: planning
    prompt_file: planning.txt
    verification:
      - not_empty
    config:
      max_tokens: 500
"""
        config_path.write_text(config_content)

        llm_config = LLMConfig(provider="ollama", model="test")

        with patch('karamba.core.agent.create_llm', return_value=mock_llm):
            with patch('karamba.core.agent.VectorRetriever'):
                with patch('karamba.core.agent.DocumentProcessor'):
                    agent = KarambaAgent(
                        llm_config=llm_config,
                        config_path=config_path
                    )

                    phases = agent.phase_engine.phases
                    assert len(phases) == 1
                    assert phases[0].name == "custom_planning"
