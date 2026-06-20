from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from backend.services.rag import stream_query, ingest_documents, get_loaded_pdfs
from backend.schemas.models import SessionState
from pydantic import BaseModel
import tempfile
import os
import uuid

router = APIRouter()

sessions: dict[str, SessionState] = {}


class QueryRequest(BaseModel):
    query: str


class SessionResponse(BaseModel):
    session_id: str

@router.post("/session/create", response_model=SessionResponse)
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = SessionState()
    return SessionResponse(session_id=session_id)

@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = ingest_documents(tmp_path, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp_path)

@router.post("/session/{session_id}/query")
async def query(session_id: str, request: QueryRequest):
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(
        stream_query(request.query, session),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@router.get("/pdfs")
async def list_pdfs():
    return {"pdfs": get_loaded_pdfs()}
