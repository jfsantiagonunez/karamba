"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from fastapi import FastAPI
from karamba.core.models import AgentResponse, PhaseResult, PhaseStatus, PhaseType


@pytest.fixture
def mock_agent():
    """Create a mock agent for API testing."""
    agent = Mock()
    agent.answer_question = AsyncMock()
    agent.get_document_stats = Mock(return_value={"total_documents": 5, "total_chunks": 150})
    agent.ingest_document = AsyncMock(return_value="test_doc.pdf")
    agent.delete_document = Mock()
    return agent


@pytest.fixture
def test_app(mock_agent):
    """Create a test FastAPI app with mocked dependencies."""
    from api.routes.agent import router as agent_router
    from api.routes.documents import router as docs_router

    app = FastAPI()

    # Override dependency to return mock agent
    def get_mock_agent():
        return mock_agent

    # Add routers with prefix
    app.include_router(agent_router, prefix="/api/v1/agent", tags=["agent"])
    app.include_router(docs_router, prefix="/api/v1/documents", tags=["documents"])

    # Override the dependency
    from api import dependencies
    app.dependency_overrides[dependencies.get_agent] = get_mock_agent

    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestAgentEndpoints:
    """Tests for agent endpoints."""

    def test_query_agent_success(self, client, mock_agent):
        """Test successful agent query."""
        # Setup mock response
        mock_phase_result = PhaseResult(
            phase_name="reasoning",
            phase_type=PhaseType.REASONING,
            status=PhaseStatus.COMPLETED,
            output="Paris is the capital of France"
        )

        mock_response = AgentResponse(
            answer="Paris is the capital of France",
            phase_results=[mock_phase_result],
            citations=[{"document_id": "doc1", "score": 0.95}]
        )

        mock_agent.answer_question.return_value = mock_response

        # Make request
        response = client.post(
            "/api/v1/agent/query",
            json={
                "query": "What is the capital of France?",
                "document_ids": ["doc1"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert data["answer"] == "Paris is the capital of France"
        assert "phase_results" in data
        assert "citations" in data
        assert "session_id" in data
        assert len(data["citations"]) == 1

    def test_query_agent_with_session_id(self, client, mock_agent):
        """Test query with provided session ID."""
        mock_response = AgentResponse(
            answer="Test answer",
            phase_results=[],
            citations=[]
        )
        mock_agent.answer_question.return_value = mock_response

        response = client.post(
            "/api/v1/agent/query",
            json={
                "query": "Test query",
                "session_id": "custom-session-123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "custom-session-123"

    def test_query_agent_generates_session_id(self, client, mock_agent):
        """Test that session ID is generated if not provided."""
        mock_response = AgentResponse(
            answer="Test answer",
            phase_results=[],
            citations=[]
        )
        mock_agent.answer_question.return_value = mock_response

        response = client.post(
            "/api/v1/agent/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_query_agent_empty_query(self, client):
        """Test query with empty string."""
        response = client.post(
            "/api/v1/agent/query",
            json={"query": ""}
        )

        # Should fail validation
        assert response.status_code == 422

    def test_query_agent_missing_query(self, client):
        """Test query without query field."""
        response = client.post(
            "/api/v1/agent/query",
            json={}
        )

        assert response.status_code == 422

    def test_query_agent_error_handling(self, client, mock_agent):
        """Test error handling in query endpoint."""
        mock_agent.answer_question.side_effect = Exception("LLM error")

        response = client.post(
            "/api/v1/agent/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_get_stats(self, client, mock_agent):
        """Test getting agent statistics."""
        response = client.get("/api/v1/agent/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert data["total_documents"] == 5
        assert data["total_chunks"] == 150


class TestDocumentEndpoints:
    """Tests for document endpoints."""

    def test_upload_document_success(self, client, mock_agent):
        """Test successful document upload."""
        # Create a mock file
        file_content = b"PDF content here"
        files = {"file": ("test.pdf", file_content, "application/pdf")}

        response = client.post("/api/v1/documents/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["document_id"] == "test_doc.pdf"

    def test_upload_document_missing_file(self, client):
        """Test upload without file."""
        response = client.post("/api/v1/documents/upload")

        assert response.status_code == 422

    def test_list_documents(self, client, mock_agent):
        """Test listing documents."""
        mock_agent.get_document_stats.return_value = {
            "documents": [
                {"id": "doc1", "name": "document1.pdf"},
                {"id": "doc2", "name": "document2.pdf"}
            ]
        }

        response = client.get("/api/v1/documents/list")

        assert response.status_code == 200
        # The actual response format depends on implementation
        # Just verify it returns successfully

    def test_delete_document_success(self, client, mock_agent):
        """Test successful document deletion."""
        response = client.delete("/api/v1/documents/doc1")

        assert response.status_code == 200
        mock_agent.delete_document.assert_called_once_with("doc1")

    def test_delete_document_error(self, client, mock_agent):
        """Test document deletion error handling."""
        mock_agent.delete_document.side_effect = Exception("Document not found")

        response = client.delete("/api/v1/documents/doc1")

        assert response.status_code == 500


class TestAPIValidation:
    """Tests for API request validation."""

    def test_query_request_validation(self, client):
        """Test QueryRequest validation."""
        # Valid request
        response = client.post(
            "/api/v1/agent/query",
            json={
                "query": "Valid query",
                "document_ids": ["doc1", "doc2"]
            }
        )
        # Should process (might fail for other reasons but not validation)
        assert response.status_code in [200, 500]

        # Invalid request - missing query
        response = client.post(
            "/api/v1/agent/query",
            json={"document_ids": ["doc1"]}
        )
        assert response.status_code == 422

    def test_query_response_structure(self, client, mock_agent):
        """Test that response matches expected structure."""
        mock_response = AgentResponse(
            answer="Test answer",
            phase_results=[],
            citations=[]
        )
        mock_agent.answer_question.return_value = mock_response

        response = client.post(
            "/api/v1/agent/query",
            json={"query": "Test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        required_fields = ["answer", "phase_results", "citations", "session_id"]
        for field in required_fields:
            assert field in data

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/api/v1/agent/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


class TestAPIIntegration:
    """Integration tests for API."""

    @pytest.mark.asyncio
    async def test_full_query_flow(self, client, mock_agent):
        """Test complete query flow."""
        # Setup mock
        mock_phase = PhaseResult(
            phase_name="reasoning",
            phase_type=PhaseType.REASONING,
            status=PhaseStatus.COMPLETED,
            output="Answer based on documents"
        )

        mock_response = AgentResponse(
            answer="Answer based on documents",
            phase_results=[mock_phase],
            citations=[{"doc": "test.pdf", "score": 0.9}]
        )

        mock_agent.answer_question.return_value = mock_response

        # Make query
        response = client.post(
            "/api/v1/agent/query",
            json={
                "query": "What is the main topic?",
                "document_ids": ["test.pdf"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify complete flow
        assert data["answer"] == "Answer based on documents"
        assert len(data["phase_results"]) == 1
        assert len(data["citations"]) == 1

        # Verify agent was called correctly
        mock_agent.answer_question.assert_called_once()
        call_args = mock_agent.answer_question.call_args[0][0]
        assert call_args.query == "What is the main topic?"
        assert "test.pdf" in call_args.document_ids
