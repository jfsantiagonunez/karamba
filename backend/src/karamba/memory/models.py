"""Models for conversation memory and session state."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Role of a message in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    """Single message in a conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationHistory(BaseModel):
    """Full conversation history for a session."""
    session_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: MessageRole, content: str, metadata: Dict[str, Any] = None) -> None:
        """Add a message to the conversation."""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get the most recent messages."""
        return self.messages[-limit:] if len(self.messages) > limit else self.messages

    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []
        self.updated_at = datetime.utcnow()


class SessionState(BaseModel):
    """State maintained across conversation turns."""
    session_id: str
    thread_id: str  # LangGraph thread identifier
    conversation_history: ConversationHistory
    title: Optional[str] = None  # Chat title (auto-generated from first message)

    # Context accumulated across turns
    document_ids: List[str] = Field(default_factory=list)
    phase_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Human-in-the-loop state
    pending_approval: Optional[Dict[str, Any]] = None
    approved_actions: List[str] = Field(default_factory=list)

    # Tool execution history
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    config: Dict[str, Any] = Field(default_factory=dict)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def add_document(self, document_id: str) -> None:
        """Add a document to the session context."""
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)
            self.update_activity()

    def request_approval(self, action: Dict[str, Any]) -> None:
        """Request human approval for an action."""
        self.pending_approval = action
        self.update_activity()

    def approve_action(self, action_id: str) -> None:
        """Mark an action as approved."""
        self.approved_actions.append(action_id)
        self.pending_approval = None
        self.update_activity()

    def has_pending_approval(self) -> bool:
        """Check if there's a pending approval."""
        return self.pending_approval is not None


class ConversationSummary(BaseModel):
    """Summary of a conversation for context compression."""
    session_id: str
    summary_text: str
    message_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    covers_messages_until: datetime = Field(default_factory=datetime.utcnow)
