"""Tests for session memory and conversation management."""
import pytest
from datetime import datetime

from karamba.memory import (
    ConversationMessage, ConversationHistory, SessionState,
    MessageRole, SessionStore
)


class TestConversationMessage:
    """Tests for ConversationMessage model."""

    def test_create_message(self):
        """Test creating a conversation message."""
        msg = ConversationMessage(
            role=MessageRole.USER,
            content="Hello, how are you?"
        )

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, how are you?"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="I'm doing well!",
            metadata={"model": "llama3.2", "tokens": 50}
        )

        assert msg.metadata["model"] == "llama3.2"
        assert msg.metadata["tokens"] == 50


class TestConversationHistory:
    """Tests for ConversationHistory model."""

    def test_create_history(self):
        """Test creating conversation history."""
        history = ConversationHistory(session_id="test-123")

        assert history.session_id == "test-123"
        assert history.messages == []
        assert isinstance(history.created_at, datetime)

    def test_add_message(self):
        """Test adding messages to history."""
        history = ConversationHistory(session_id="test-123")

        history.add_message(MessageRole.USER, "First message")
        history.add_message(MessageRole.ASSISTANT, "Response")

        assert len(history.messages) == 2
        assert history.messages[0].content == "First message"
        assert history.messages[1].content == "Response"

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        history = ConversationHistory(session_id="test-123")

        # Add 15 messages
        for i in range(15):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            history.add_message(role, f"Message {i}")

        recent = history.get_recent_messages(limit=5)

        assert len(recent) == 5
        assert recent[0].content == "Message 10"
        assert recent[-1].content == "Message 14"

    def test_get_message_count(self):
        """Test getting message count."""
        history = ConversationHistory(session_id="test-123")

        history.add_message(MessageRole.USER, "Message 1")
        history.add_message(MessageRole.USER, "Message 2")

        assert history.get_message_count() == 2

    def test_clear_history(self):
        """Test clearing conversation history."""
        history = ConversationHistory(session_id="test-123")

        history.add_message(MessageRole.USER, "Message 1")
        history.add_message(MessageRole.USER, "Message 2")

        assert len(history.messages) == 2

        history.clear()

        assert len(history.messages) == 0


class TestSessionState:
    """Tests for SessionState model."""

    def test_create_session_state(self):
        """Test creating session state."""
        history = ConversationHistory(session_id="test-123")
        state = SessionState(
            session_id="test-123",
            thread_id="thread-123",
            conversation_history=history
        )

        assert state.session_id == "test-123"
        assert state.thread_id == "thread-123"
        assert state.document_ids == []
        assert state.pending_approval is None

    def test_add_document(self):
        """Test adding documents to session."""
        history = ConversationHistory(session_id="test-123")
        state = SessionState(
            session_id="test-123",
            thread_id="thread-123",
            conversation_history=history
        )

        state.add_document("doc1.pdf")
        state.add_document("doc2.pdf")
        state.add_document("doc1.pdf")  # Duplicate

        assert len(state.document_ids) == 2
        assert "doc1.pdf" in state.document_ids
        assert "doc2.pdf" in state.document_ids

    def test_request_approval(self):
        """Test requesting approval."""
        history = ConversationHistory(session_id="test-123")
        state = SessionState(
            session_id="test-123",
            thread_id="thread-123",
            conversation_history=history
        )

        action = {
            "action_id": "action-1",
            "type": "delete_document",
            "target": "doc1.pdf"
        }

        state.request_approval(action)

        assert state.has_pending_approval()
        assert state.pending_approval == action

    def test_approve_action(self):
        """Test approving an action."""
        history = ConversationHistory(session_id="test-123")
        state = SessionState(
            session_id="test-123",
            thread_id="thread-123",
            conversation_history=history
        )

        action = {"action_id": "action-1"}
        state.request_approval(action)

        state.approve_action("action-1")

        assert not state.has_pending_approval()
        assert "action-1" in state.approved_actions

    def test_update_activity(self):
        """Test updating activity timestamp."""
        history = ConversationHistory(session_id="test-123")
        state = SessionState(
            session_id="test-123",
            thread_id="thread-123",
            conversation_history=history
        )

        original_time = state.last_activity

        state.update_activity()

        assert state.last_activity >= original_time


@pytest.mark.asyncio
class TestSessionStore:
    """Tests for SessionStore class."""

    @pytest.fixture
    async def store(self, temp_test_dir):
        """Create a test session store."""
        db_path = temp_test_dir / "test_sessions.db"
        store = SessionStore(db_path=str(db_path))
        async with store:
            yield store

    async def test_create_session(self, store):
        """Test creating a new session."""
        state = await store.create_session("session-1")

        assert state.session_id == "session-1"
        assert state.thread_id == "thread_session-1"

    async def test_get_session(self, store):
        """Test retrieving a session."""
        await store.create_session("session-1")

        state = await store.get_session("session-1")

        assert state is not None
        assert state.session_id == "session-1"

    async def test_get_nonexistent_session(self, store):
        """Test retrieving non-existent session."""
        state = await store.get_session("nonexistent")

        assert state is None

    async def test_update_session(self, store):
        """Test updating session state."""
        state = await store.create_session("session-1")
        original_time = state.last_activity

        state.add_document("doc1.pdf")
        await store.update_session(state)

        retrieved = await store.get_session("session-1")
        assert len(retrieved.document_ids) == 1
        assert retrieved.last_activity >= original_time

    async def test_delete_session(self, store):
        """Test deleting a session."""
        await store.create_session("session-1")

        deleted = await store.delete_session("session-1")
        assert deleted is True

        state = await store.get_session("session-1")
        assert state is None

    async def test_add_message(self, store):
        """Test adding message to session."""
        await store.create_session("session-1")

        await store.add_message("session-1", MessageRole.USER, "Hello")
        await store.add_message("session-1", MessageRole.ASSISTANT, "Hi there!")

        history = await store.get_conversation_history("session-1")

        assert history is not None
        assert len(history.messages) == 2
        assert history.messages[0].content == "Hello"
        assert history.messages[1].content == "Hi there!"

    async def test_get_conversation_history_with_limit(self, store):
        """Test getting limited conversation history."""
        await store.create_session("session-1")

        # Add 10 messages
        for i in range(10):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            await store.add_message("session-1", role, f"Message {i}")

        history = await store.get_conversation_history("session-1", limit=3)

        assert len(history.messages) == 3
        assert history.messages[0].content == "Message 7"

    async def test_clear_conversation(self, store):
        """Test clearing conversation history."""
        await store.create_session("session-1")

        await store.add_message("session-1", MessageRole.USER, "Message 1")
        await store.add_message("session-1", MessageRole.USER, "Message 2")

        cleared = await store.clear_conversation("session-1")
        assert cleared is True

        history = await store.get_conversation_history("session-1")
        assert len(history.messages) == 0

    async def test_list_sessions(self, store):
        """Test listing all sessions."""
        await store.create_session("session-1")
        await store.create_session("session-2")
        await store.create_session("session-3")

        sessions = await store.list_sessions()

        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions
        assert "session-3" in sessions

    async def test_get_session_count(self, store):
        """Test getting session count."""
        await store.create_session("session-1")
        await store.create_session("session-2")

        count = await store.get_session_count()

        assert count == 2

    async def test_request_approval(self, store):
        """Test requesting approval via store."""
        await store.create_session("session-1")

        action = {
            "action_id": "action-1",
            "type": "delete",
            "target": "doc1.pdf"
        }

        await store.request_approval("session-1", action)

        state = await store.get_session("session-1")
        assert state.has_pending_approval()

    async def test_approve_action(self, store):
        """Test approving action via store."""
        await store.create_session("session-1")

        action = {"action_id": "action-1"}
        await store.request_approval("session-1", action)

        approved = await store.approve_action("session-1", "action-1")

        assert approved is True

        state = await store.get_session("session-1")
        assert not state.has_pending_approval()
        assert "action-1" in state.approved_actions

    async def test_has_pending_approval(self, store):
        """Test checking for pending approval."""
        await store.create_session("session-1")

        has_pending = await store.has_pending_approval("session-1")
        assert has_pending is False

        action = {"action_id": "action-1"}
        await store.request_approval("session-1", action)

        has_pending = await store.has_pending_approval("session-1")
        assert has_pending is True
