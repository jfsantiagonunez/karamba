"""Session storage using LangGraph checkpointers."""
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from .models import SessionState, ConversationHistory, MessageRole


class SessionStore:
    """Manages conversation sessions with persistent storage."""

    def __init__(self, db_path: str = "./data/sessions.db"):
        """Initialize session store with SQLite checkpointer."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._checkpointer: Optional[AsyncSqliteSaver] = None
        self._checkpointer_cm = None  # Context manager reference
        self._sessions: Dict[str, SessionState] = {}  # In-memory cache
        logger.info(f"Session store initialized with DB: {self.db_path}")

    async def __aenter__(self):
        """Async context manager entry."""
        checkpointer_cm = AsyncSqliteSaver.from_conn_string(str(self.db_path))
        self._checkpointer = await checkpointer_cm.__aenter__()
        self._checkpointer_cm = checkpointer_cm  # Keep reference for cleanup
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, '_checkpointer_cm') and self._checkpointer_cm:
            await self._checkpointer_cm.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def checkpointer(self) -> Optional[BaseCheckpointSaver]:
        """Get the LangGraph checkpointer (None if not initialized)."""
        return self._checkpointer

    async def create_session(
        self,
        session_id: str,
        thread_id: Optional[str] = None
    ) -> SessionState:
        """Create a new conversation session."""
        if thread_id is None:
            thread_id = f"thread_{session_id}"

        conversation = ConversationHistory(session_id=session_id)
        state = SessionState(
            session_id=session_id,
            thread_id=thread_id,
            conversation_history=conversation
        )

        self._sessions[session_id] = state
        logger.info(f"Created session: {session_id}")
        return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve a session by ID."""
        # Check in-memory cache first
        if session_id in self._sessions:
            return self._sessions[session_id]

        # TODO: Load from checkpoint if needed
        logger.debug(f"Session not found in cache: {session_id}")
        return None

    async def update_session(self, state: SessionState) -> None:
        """Update session state."""
        state.update_activity()
        self._sessions[state.session_id] = state
        logger.debug(f"Updated session: {state.session_id}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Add a message to session conversation."""
        state = await self.get_session(session_id)
        if not state:
            state = await self.create_session(session_id)

        state.conversation_history.add_message(role, content, metadata or {})

        # Auto-generate title from first user message (max 50 chars)
        if not state.title and role == MessageRole.USER and content.strip():
            title = content.strip()[:50]
            # Add ellipsis if truncated
            if len(content.strip()) > 50:
                title += "..."
            state.title = title
            logger.info(f"Generated title for session {session_id}: {title}")

        await self.update_session(state)

    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> Optional[ConversationHistory]:
        """Get conversation history for a session."""
        state = await self.get_session(session_id)
        if not state:
            return None

        if limit:
            # Create a copy with limited messages
            history = state.conversation_history.model_copy(deep=True)
            history.messages = history.get_recent_messages(limit)
            return history

        return state.conversation_history

    async def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        state = await self.get_session(session_id)
        if not state:
            return False

        state.conversation_history.clear()
        await self.update_session(state)
        logger.info(f"Cleared conversation for session: {session_id}")
        return True

    async def list_sessions(self) -> list[dict]:
        """List all active sessions with metadata."""
        sessions = []
        for session_id, state in self._sessions.items():
            sessions.append({
                "session_id": session_id,
                "title": state.title or f"Chat {session_id[:8]}",
                "last_activity": state.last_activity.isoformat(),
                "message_count": state.conversation_history.get_message_count(),
                "document_count": len(state.document_ids)
            })
        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s["last_activity"], reverse=True)
        return sessions

    async def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self._sessions)

    async def request_approval(
        self,
        session_id: str,
        action: Dict[str, Any]
    ) -> None:
        """Request human approval for an action."""
        state = await self.get_session(session_id)
        if state:
            state.request_approval(action)
            await self.update_session(state)
            logger.info(f"Approval requested for session {session_id}: {action.get('action_id')}")

    async def approve_action(
        self,
        session_id: str,
        action_id: str
    ) -> bool:
        """Approve a pending action."""
        state = await self.get_session(session_id)
        if not state:
            return False

        state.approve_action(action_id)
        await self.update_session(state)
        logger.info(f"Action approved for session {session_id}: {action_id}")
        return True

    async def has_pending_approval(self, session_id: str) -> bool:
        """Check if session has pending approval."""
        state = await self.get_session(session_id)
        return state.has_pending_approval() if state else False
