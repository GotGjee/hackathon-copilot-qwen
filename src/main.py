"""
Hackathon Copilot - FastAPI Application
Main entry point for the backend API.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import get_settings
from src.core.api_client import QwenAPIClient
from src.core.state import SessionState
from src.services.state_manager import StateManager
from src.services.session_service import SessionService
from src.services.export_service import ExportService


# Global services
api_client: Optional[QwenAPIClient] = None
state_manager: Optional[StateManager] = None
session_service: Optional[SessionService] = None
export_service: Optional[ExportService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global api_client, state_manager, session_service, export_service

    settings = get_settings()

    # Initialize services
    api_client = QwenAPIClient(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
        default_model=settings.default_model,
    )

    state_manager = StateManager(data_dir=settings.sessions_dir)
    session_service = SessionService(api_client=api_client, state_manager=state_manager)
    export_service = ExportService(export_dir=settings.exports_dir)

    yield

    # Cleanup
    if api_client:
        await api_client.close()


# Create FastAPI app
app = FastAPI(
    title="Hackathon Copilot",
    description="AI-powered multi-agent system for hackathon success",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class CreateSessionRequest(BaseModel):
    theme: str
    constraints: str


class SelectIdeaRequest(BaseModel):
    idea_id: int
    feedback: Optional[str] = None


class CodeReviewRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


# API Routes
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Hackathon Copilot API"}


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "api": "Hackathon Copilot",
        "version": "1.0.0",
        "status": "running",
    }


@app.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """Create a new hackathon session."""
    global session_service
    if not session_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        state = session_service.create_session(
            theme=request.theme,
            constraints=request.constraints,
        )
        return {
            "session_id": state.session_id,
            "status": state.current_layer.value,
            "message": "Session created. Starting ideation...",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time event streaming."""
    from src.core.events import broadcaster
    
    await websocket.accept()
    await broadcaster.connect(websocket, session_id)
    
    try:
        while True:
            # Keep connection alive, wait for messages from client
            data = await websocket.receive_text()
            # Client can send ping/pong or control messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket, session_id)
    except Exception:
        await broadcaster.disconnect(websocket, session_id)


@app.get("/sessions/{session_id}/events")
async def get_events(session_id: str, since_index: int = 0):
    """Get streaming events for a session via HTTP polling."""
    from src.core.events import broadcaster
    
    events = broadcaster.store.get_events(session_id, since_index)
    return {"events": events, "total": broadcaster.store.get_count(session_id)}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session status and state."""
    global session_service
    if not session_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    state = session_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": state.session_id,
        "theme": state.theme,
        "current_layer": state.current_layer.value,
        "is_paused": state.is_paused,
        "pause_reason": state.pause_reason,
        "ideas": [i.model_dump() for i in state.ideas],
        "ideas_count": len(state.ideas),
        "evaluations": [e.model_dump() for e in state.evaluations],
        "selected_idea": state.selected_idea.model_dump() if state.selected_idea else None,
        "agent_log": [m.model_dump() for m in state.agent_log[-20:]],
    }


@app.post("/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start the AI workflow for a session."""
    global session_service
    if not session_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        state = await session_service.start_workflow(session_id)
        return {
            "session_id": state.session_id,
            "current_layer": state.current_layer.value,
            "is_paused": state.is_paused,
            "ideas": [i.model_dump() for i in state.ideas],
            "message": "Ideation and judging complete. Please select an idea.",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Return detailed error for debugging
        raise HTTPException(status_code=500, detail={
            "error": type(e).__name__,
            "message": str(e),
            "hint": "Check API key, network connection, and that the Qwen API is accessible."
        })


@app.post("/sessions/{session_id}/select-idea")
async def select_idea(session_id: str, request: SelectIdeaRequest):
    """Select an idea at HITL checkpoint 1."""
    global session_service
    if not session_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        state = await session_service.select_idea(
            session_id=session_id,
            idea_id=request.idea_id,
            feedback=request.feedback,
        )
        return {
            "session_id": state.session_id,
            "current_layer": state.current_layer.value,
            "message": "Idea selected. Generating code...",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/review-code")
async def review_code(session_id: str, request: CodeReviewRequest):
    """Review code at HITL checkpoint 2."""
    global session_service
    if not session_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        if request.approved:
            state = await session_service.approve_code(session_id, request.feedback)
        else:
            state = await session_service.request_changes(session_id, request.feedback or "")

        return {
            "session_id": state.session_id,
            "current_layer": state.current_layer.value,
            "message": "Code review processed.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/export/code")
async def export_code(session_id: str):
    """Export generated code as ZIP."""
    global session_service, export_service
    if not session_service or not export_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    state = session_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if not state.code_artifacts:
        raise HTTPException(status_code=400, detail="No code artifacts to export")

    try:
        title = state.selected_idea.title if state.selected_idea else "project"
        filepath = export_service.export_code_zip(
            session_id=session_id,
            code_artifacts=state.code_artifacts,
            title=title,
        )
        return {"filepath": filepath, "message": "Code exported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/export/pitch")
async def export_pitch(session_id: str):
    """Export pitch materials."""
    global session_service, export_service
    if not session_service or not export_service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    state = session_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if not state.narrative:
        raise HTTPException(status_code=400, detail="No pitch materials available")

    try:
        title = state.selected_idea.title if state.selected_idea else "project"
        filepath = export_service.export_pitch_materials(
            session_id=session_id,
            narrative=state.narrative.model_dump() if state.narrative else {},
            slides=[s.model_dump() for s in state.slides],
            script=[s.model_dump() for s in state.script],
            title=title,
        )
        return {"filepath": filepath, "message": "Pitch materials exported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)