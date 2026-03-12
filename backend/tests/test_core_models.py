"""Tests for core data models."""
import pytest
from pydantic import ValidationError

from karamba.core.models import (
    PhaseStatus, PhaseType, PhaseResult, AgentRequest,
    AgentResponse, VerificationResult, ResearchPlan
)


class TestPhaseStatus:
    """Tests for PhaseStatus enum."""

    def test_phase_status_values(self):
        """Test PhaseStatus has expected values."""
        assert PhaseStatus.PENDING == "pending"
        assert PhaseStatus.RUNNING == "running"
        assert PhaseStatus.COMPLETED == "completed"
        assert PhaseStatus.FAILED == "failed"
        assert PhaseStatus.SKIPPED == "skipped"


class TestPhaseType:
    """Tests for PhaseType enum."""

    def test_phase_type_values(self):
        """Test PhaseType has expected values."""
        assert PhaseType.PLANNING == "planning"
        assert PhaseType.RETRIEVAL == "retrieval"
        assert PhaseType.REASONING == "reasoning"
        assert PhaseType.GENERATION == "generation"


class TestVerificationResult:
    """Tests for VerificationResult model."""

    def test_create_verification_result(self):
        """Test creating a verification result."""
        result = VerificationResult(
            passed=True,
            rule_name="not_empty",
            message="Output is not empty"
        )

        assert result.passed is True
        assert result.rule_name == "not_empty"
        assert result.message == "Output is not empty"
        assert result.score is None

    def test_verification_result_with_score(self):
        """Test verification result with score."""
        result = VerificationResult(
            passed=True,
            rule_name="quality_check",
            message="High quality output",
            score=0.95
        )

        assert result.score == 0.95


class TestPhaseResult:
    """Tests for PhaseResult model."""

    def test_create_phase_result(self, sample_phase_result):
        """Test creating a phase result."""
        assert sample_phase_result.phase_name == "planning"
        assert sample_phase_result.phase_type == PhaseType.PLANNING
        assert sample_phase_result.status == PhaseStatus.COMPLETED
        assert sample_phase_result.output == "Test output"
        assert len(sample_phase_result.verification_results) == 1

    def test_phase_result_defaults(self):
        """Test PhaseResult default values."""
        result = PhaseResult(
            phase_name="test",
            phase_type=PhaseType.PLANNING,
            status=PhaseStatus.PENDING,
            output=None
        )

        assert result.verification_results == []
        assert result.metadata == {}
        assert result.error is None

    def test_phase_result_with_error(self):
        """Test PhaseResult with error."""
        result = PhaseResult(
            phase_name="test",
            phase_type=PhaseType.PLANNING,
            status=PhaseStatus.FAILED,
            output=None,
            error="Connection timeout"
        )

        assert result.status == PhaseStatus.FAILED
        assert result.error == "Connection timeout"


class TestAgentRequest:
    """Tests for AgentRequest model."""

    def test_create_agent_request(self, sample_agent_request):
        """Test creating an agent request."""
        assert sample_agent_request.query == "What is the capital of France?"
        assert sample_agent_request.session_id == "test-session-123"
        assert sample_agent_request.document_ids == ["doc1", "doc2"]

    def test_agent_request_defaults(self):
        """Test AgentRequest default values."""
        request = AgentRequest(
            query="Test query",
            session_id="session-1"
        )

        assert request.document_ids == []
        assert request.config == {}

    def test_agent_request_validation(self):
        """Test AgentRequest validation."""
        with pytest.raises(ValidationError):
            AgentRequest(query="", session_id="")


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_create_agent_response(self, sample_phase_result):
        """Test creating an agent response."""
        response = AgentResponse(
            answer="Paris is the capital of France",
            phase_results=[sample_phase_result]
        )

        assert response.answer == "Paris is the capital of France"
        assert len(response.phase_results) == 1
        assert response.citations == []
        assert response.metadata == {}

    def test_agent_response_with_citations(self):
        """Test AgentResponse with citations."""
        response = AgentResponse(
            answer="Answer based on documents",
            phase_results=[],
            citations=[
                {"document_id": "doc1", "score": 0.95},
                {"document_id": "doc2", "score": 0.87}
            ]
        )

        assert len(response.citations) == 2
        assert response.citations[0]["document_id"] == "doc1"


class TestResearchPlan:
    """Tests for ResearchPlan model."""

    def test_create_research_plan(self):
        """Test creating a research plan."""
        plan = ResearchPlan(
            main_question="What is climate change?",
            sub_questions=[
                "What causes climate change?",
                "What are the effects?"
            ],
            required_documents=["doc1", "doc2"],
            approach="First analyze causes, then effects"
        )

        assert plan.main_question == "What is climate change?"
        assert len(plan.sub_questions) == 2
        assert len(plan.required_documents) == 2
        assert "causes" in plan.approach

    def test_research_plan_defaults(self):
        """Test ResearchPlan default values."""
        plan = ResearchPlan(main_question="Test question")

        assert plan.sub_questions == []
        assert plan.required_documents == []
        assert plan.approach == ""
