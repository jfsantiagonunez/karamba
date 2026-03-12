"""WebSocket endpoint for streaming responses."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger
import json
import uuid

from karamba.core.agent import KarambaAgent
from karamba.core.models import AgentRequest
from api.dependencies import get_agent  # Changed import!


router = APIRouter()


@router.websocket("/agent/{session_id}")
async def websocket_agent(
    websocket: WebSocket,
    session_id: str,
    agent: KarambaAgent = Depends(get_agent)
):
    """WebSocket endpoint for streaming agent responses."""
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "query":
                query = message.get("query")
                document_ids = message.get("document_ids", [])
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "query_started",
                    "session_id": session_id
                })
                
                # Create request
                request = AgentRequest(
                    query=query,
                    session_id=session_id,
                    document_ids=document_ids
                )
                
                # Stream phase results
                async for phase_result in agent.query(request):
                    await websocket.send_json({
                        "type": "phase_result",
                        "phase": phase_result.phase_name,
                        "status": phase_result.status,
                        "output": phase_result.output,
                        "metadata": phase_result.metadata
                    })
                
                # Send completion
                await websocket.send_json({
                    "type": "query_complete",
                    "session_id": session_id
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()
