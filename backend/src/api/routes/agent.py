"""Agent execution endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

from karamba.core.agent import KarambaAgent
from karamba.core.models import AgentRequest, AgentResponse, PhaseResult
from api.dependencies import get_agent  # Changed import!


router = APIRouter()


class QueryRequest(BaseModel):
    """Request to query the agent."""
    query: str
    document_ids: List[str] = []
    session_id: str = None


class QueryResponse(BaseModel):
    """Response from query."""
    answer: str
    phase_results: List[dict]
    citations: List[dict]
    session_id: str


@router.post("/query", response_model=QueryResponse)
async def query_agent(
    request: QueryRequest,
    agent: KarambaAgent = Depends(get_agent)
):
    """Query the agent with a question."""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create agent request
        agent_request = AgentRequest(
            query=request.query,
            session_id=session_id,
            document_ids=request.document_ids
        )
        
        # Get answer
        response = await agent.answer_question(agent_request)
        
        return QueryResponse(
            answer=response.answer,
            phase_results=[r.model_dump() for r in response.phase_results],
            citations=response.citations,
            session_id=session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(agent: KarambaAgent = Depends(get_agent)):
    """Get agent statistics."""
    return agent.get_document_stats()