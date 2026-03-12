"""Conversation and session management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from karamba.memory import ConversationOrchestrator, SessionStore
from karamba.agents.router import AgentRouter
from api.dependencies import get_orchestrator, get_session_store, get_router


router = APIRouter()


class ConversationQueryRequest(BaseModel):
    """Request for a conversation query."""
    query: str
    document_ids: List[str] = []
    approved: bool = False


class ConversationQueryResponse(BaseModel):
    """Response from conversation query."""
    session_id: str
    answer: str
    phase_results: List[dict]
    citations: List[dict]
    requires_approval: bool = False
    pending_action: Optional[dict] = None
    # Agent routing information (for multi-agent system)
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    routing_confidence: Optional[float] = None
    routing_reasoning: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request to approve a pending action."""
    action_id: str


class ConversationMessageResponse(BaseModel):
    """Single message in conversation."""
    role: str
    content: str
    timestamp: str
    metadata: dict


class ConversationHistoryResponse(BaseModel):
    """Full conversation history."""
    session_id: str
    messages: List[ConversationMessageResponse]
    message_count: int


class SessionInfo(BaseModel):
    """Information about a session."""
    session_id: str
    title: str
    last_activity: str
    message_count: int
    document_count: int


class SessionListResponse(BaseModel):
    """List of sessions."""
    sessions: List[SessionInfo]
    total_count: int


@router.post("/{session_id}/query", response_model=ConversationQueryResponse)
async def query_conversation(
    session_id: str,
    request: ConversationQueryRequest,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator)
):
    """Query within a conversation session with automatic agent routing."""
    try:
        result = await orchestrator.query(
            session_id=session_id,
            query=request.query,
            document_ids=request.document_ids,
            approved=request.approved
        )

        return ConversationQueryResponse(
            session_id=session_id,
            answer=result.get("answer", ""),
            phase_results=result.get("phase_results", []),
            citations=result.get("citations", []),
            requires_approval=result.get("requires_approval", False),
            pending_action=result.get("pending_action"),
            agent_id=result.get("selected_agent_id"),
            agent_name=None,  # Will be populated from metadata if available
            routing_confidence=result.get("routing_confidence"),
            routing_reasoning=result.get("routing_reasoning")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/query/stream")
async def stream_query_conversation(
    session_id: str,
    query: str,
    approved: bool = False,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator)
):
    """Stream query execution with real-time phase updates via Server-Sent Events."""
    from loguru import logger

    logger.info(f"!!! ENDPOINT HIT: stream_query_conversation for session {session_id}")

    async def event_generator():
        try:
            logger.info(f"Starting SSE stream for session {session_id}, query: {query[:50]}")
            async for event in orchestrator.stream_query(
                session_id=session_id,
                query=query,
                document_ids=None,  # Use session documents
                approved=approved
            ):
                # Send event as Server-Sent Event
                sse_data = f"data: {json.dumps(event)}\n\n"
                logger.info(f"SSE: Sending event type={event.get('type')}, phase={event.get('phase_name', 'N/A')}")
                yield sse_data

        except Exception as e:
            # Send error event
            error_event = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )


@router.post("/{session_id}/approve", response_model=ConversationQueryResponse)
async def approve_action(
    session_id: str,
    request: ApprovalRequest,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator)
):
    """Approve a pending action and continue execution."""
    try:
        result = await orchestrator.approve_and_continue(
            session_id=session_id,
            action_id=request.action_id
        )

        return ConversationQueryResponse(
            session_id=session_id,
            answer=result.get("answer", ""),
            phase_results=result.get("phase_results", []),
            citations=result.get("citations", []),
            requires_approval=False
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/approve/stream")
async def stream_approve_action(
    session_id: str,
    action_id: str,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator)
):
    """Approve a pending action and stream execution with real-time phase updates."""
    async def event_generator():
        try:
            # Get the pending action to retrieve the original query
            session_state = await orchestrator.session_store.get_session(session_id)
            if not session_state or not session_state.pending_approval:
                error_event = {
                    "type": "error",
                    "error": "No pending approval found"
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return

            # Save the query before approving (approve_action clears pending_approval)
            query = session_state.pending_approval.get("query", "")

            # Mark as approved
            await orchestrator.session_store.approve_action(session_id, action_id)
            async for event in orchestrator.stream_query(
                session_id=session_id,
                query=query,
                document_ids=None,
                approved=True
            ):
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            error_event = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{session_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    limit: Optional[int] = None,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator)
):
    """Get conversation history for a session."""
    try:
        messages = await orchestrator.get_conversation(session_id, limit)

        if messages is None:
            raise HTTPException(status_code=404, detail="Session not found")

        return ConversationHistoryResponse(
            session_id=session_id,
            messages=[ConversationMessageResponse(**msg) for msg in messages],
            message_count=len(messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Delete a conversation session."""
    try:
        deleted = await store.delete_session(session_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": f"Session {session_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}/history")
async def clear_conversation_history(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Clear conversation history for a session."""
    try:
        cleared = await store.clear_conversation(session_id)

        if not cleared:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": f"Conversation history cleared for session {session_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    store: SessionStore = Depends(get_session_store)
):
    """List all active sessions with metadata."""
    try:
        sessions = await store.list_sessions()

        return SessionListResponse(
            sessions=[SessionInfo(**s) for s in sessions],
            total_count=len(sessions)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/status")
async def get_session_status(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Get session status including pending approvals."""
    try:
        state = await store.get_session(session_id)

        if not state:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session_id,
            "thread_id": state.thread_id,
            "message_count": state.conversation_history.get_message_count(),
            "document_count": len(state.document_ids),
            "has_pending_approval": state.has_pending_approval(),
            "pending_approval": state.pending_approval,
            "created_at": state.created_at.isoformat(),
            "last_activity": state.last_activity.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AgentInfoResponse(BaseModel):
    """Information about a specialist agent."""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    keywords: List[str]
    example_queries: List[str]


class AvailableAgentsResponse(BaseModel):
    """List of available specialist agents."""
    agents: List[AgentInfoResponse]
    total_count: int


@router.get("/agents", response_model=AvailableAgentsResponse)
async def get_available_agents(
    router_instance: AgentRouter = Depends(get_router)
):
    """Get information about all available specialist agents."""
    try:
        agents = router_instance.get_available_agents()

        return AvailableAgentsResponse(
            agents=[AgentInfoResponse(**agent) for agent in agents],
            total_count=len(agents)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
