"""Core data models for Karamba agent."""
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class PhaseStatus(str, Enum):
    """Status of a phase."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PhaseType(str, Enum):
    """Type of phase."""
    PLANNING = "planning"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    GENERATION = "generation"


class VerificationResult(BaseModel):
    """Result of verification check."""
    passed: bool
    rule_name: str
    message: str
    score: Optional[float] = None


class PhaseResult(BaseModel):
    """Result from executing a phase."""
    phase_name: str
    phase_type: PhaseType
    status: PhaseStatus
    output: Any
    verification_results: List[VerificationResult] = []
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None


class AgentRequest(BaseModel):
    """Request to agent."""
    query: str
    session_id: str
    document_ids: List[str] = []
    config: dict = {}


class AgentResponse(BaseModel):
    """Response from agent."""
    answer: str
    phase_results: List[PhaseResult]
    citations: List[dict] = []
    metadata: dict = {}


class ResearchPlan(BaseModel):
    """Research plan from planning phase."""
    main_question: str
    sub_questions: List[str] = []
    required_documents: List[str] = []
    approach: str = ""