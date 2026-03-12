"""Document management endpoints."""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from pathlib import Path
from typing import List, Optional
import shutil

from karamba.core.agent import KarambaAgent
from karamba.memory import SessionStore
from api.dependencies import get_agent, get_session_store


router = APIRouter()

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    agent: KarambaAgent = Depends(get_agent),
    session_store: SessionStore = Depends(get_session_store)
):
    """Upload and ingest a document, optionally associating it with a session."""
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ingest document
        document_id = await agent.ingest_document(file_path)

        # Associate document with session if session_id provided
        if session_id:
            session_state = await session_store.get_session(session_id)
            if not session_state:
                # Create session if it doesn't exist
                session_state = await session_store.create_session(session_id)

            # Add document to session's document list
            if document_id not in session_state.document_ids:
                session_state.document_ids.append(document_id)
                await session_store.update_session(session_state)

        return {
            "document_id": document_id,
            "filename": file.filename,
            "status": "ingested",
            "session_id": session_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    agent: KarambaAgent = Depends(get_agent)
):
    """Delete a document."""
    try:
        agent.delete_document(document_id)
        return {"status": "deleted", "document_id": document_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_documents(
    session_id: Optional[str] = None,
    agent: KarambaAgent = Depends(get_agent),
    session_store: SessionStore = Depends(get_session_store)
):
    """List all uploaded documents, optionally filtered by session."""
    stats = agent.get_document_stats()

    # List files in upload directory
    files = [
        {
            "filename": f.name,
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime
        }
        for f in UPLOAD_DIR.iterdir()
        if f.is_file()
    ]

    # Get all sessions to find document-session mappings
    all_sessions = await session_store.list_sessions()

    # Build a map of document_id -> list of sessions
    doc_to_sessions = {}
    for session_info in all_sessions:
        session_state = await session_store.get_session(session_info["session_id"])
        if session_state:
            for doc_id in session_state.document_ids:
                if doc_id not in doc_to_sessions:
                    doc_to_sessions[doc_id] = []
                doc_to_sessions[doc_id].append({
                    "session_id": session_info["session_id"],
                    "title": session_info.get("title", "Untitled Chat")
                })

    # Add session info to each file
    for file in files:
        file["linked_sessions"] = doc_to_sessions.get(file["filename"], [])

    # If session_id provided, filter by session documents
    if session_id:
        session_state = await session_store.get_session(session_id)
        if session_state:
            session_doc_ids = set(session_state.document_ids)
            # Filter files to only those in this session
            files = [f for f in files if f["filename"] in session_doc_ids]
            return {
                "documents": files,
                "stats": stats,
                "session_id": session_id,
                "document_count": len(files)
            }

    return {
        "documents": files,
        "stats": stats
    }


@router.get("/session/{session_id}")
async def get_session_documents(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store)
):
    """Get all documents associated with a specific session."""
    session_state = await session_store.get_session(session_id)

    if not session_state:
        raise HTTPException(status_code=404, detail="Session not found")

    # List files that match session document IDs
    session_files = []
    for doc_id in session_state.document_ids:
        file_path = UPLOAD_DIR / doc_id
        if file_path.exists():
            session_files.append({
                "filename": doc_id,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            })

    return {
        "session_id": session_id,
        "documents": session_files,
        "document_count": len(session_files)
    }