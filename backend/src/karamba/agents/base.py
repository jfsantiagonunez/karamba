"""
Base Specialist Agent

Defines the abstract base class for all specialist agents in the multi-agent framework.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from karamba.core.models import AgentRequest, AgentResponse


class AgentCapability(str, Enum):
    """Capabilities that specialist agents can provide"""
    RESEARCH = "research"
    FINANCIAL_ANALYSIS = "financial_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    DOCUMENT_QA = "document_qa"
    SUMMARIZATION = "summarization"


class ApprovalPolicy(BaseModel):
    """Defines approval requirements for an agent"""
    requires_approval: bool = Field(
        default=False,
        description="Whether this agent requires approval by default"
    )
    approval_triggers: List[str] = Field(
        default_factory=list,
        description="Keywords or patterns that trigger approval requirement"
    )
    risky_actions: List[str] = Field(
        default_factory=list,
        description="Action types that require approval (e.g., 'delete', 'modify_data', 'external_api')"
    )


class AgentMetadata(BaseModel):
    """Metadata about a specialist agent"""
    name: str
    description: str
    capabilities: List[AgentCapability]
    keywords: List[str] = Field(default_factory=list)
    example_queries: List[str] = Field(default_factory=list)
    approval_policy: ApprovalPolicy = Field(
        default_factory=ApprovalPolicy,
        description="Approval requirements for this agent"
    )


class BaseSpecialistAgent(ABC):
    """
    Abstract base class for all specialist agents.

    Each specialist agent should:
    1. Define its capabilities and metadata
    2. Implement query processing with domain-specific logic
    3. Use the appropriate phases from the phase engine
    4. Return structured responses
    """

    def __init__(self, agent_id: str, enable_reflection: bool = False):
        """
        Initialize the specialist agent.

        Args:
            agent_id: Unique identifier for this agent instance
            enable_reflection: Whether to enable reflection pattern for this agent
        """
        self.agent_id = agent_id
        self.enable_reflection = enable_reflection

    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return metadata describing this agent's capabilities"""
        pass

    @abstractmethod
    async def process_query(
        self,
        request: AgentRequest,
        session_context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a query using this specialist agent.

        Args:
            request: The incoming agent request
            session_context: Optional session context (conversation history, etc.)

        Returns:
            AgentResponse with the result
        """
        pass

    @abstractmethod
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given query.

        Args:
            query: The user's query
            context: Optional context about the query

        Returns:
            Confidence score (0.0 to 1.0) that this agent can handle the query
        """
        pass

    def requires_approval(
        self,
        query: str,
        detected_actions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if this query requires human approval.

        Args:
            query: The user's query
            detected_actions: Actions detected during planning phase
            context: Optional context

        Returns:
            Tuple of (requires_approval, reason)
        """
        policy = self.metadata.approval_policy

        # Check 1: Agent always requires approval
        if policy.requires_approval:
            return True, f"{self.metadata.name} requires approval for all operations"

        # Check 2: Query contains approval triggers
        query_lower = query.lower()
        for trigger in policy.approval_triggers:
            if trigger.lower() in query_lower:
                return True, f"Query contains trigger word: '{trigger}'"

        # Check 3: Detected actions match risky actions
        if detected_actions and policy.risky_actions:
            risky_detected = set(detected_actions) & set(policy.risky_actions)
            if risky_detected:
                actions_str = ", ".join(risky_detected)
                return True, f"Risky actions detected: {actions_str}"

        return False, None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_id='{self.agent_id}')"
