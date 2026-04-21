"""
Session Service
Handles session CRUD operations and orchestrator management.
"""

import asyncio
import uuid
from typing import Any, Dict, Optional

from src.core.state import SessionState, WorkflowLayer
from src.core.api_client import QwenAPIClient
from src.core.orchestrator import Orchestrator
from src.services.state_manager import StateManager


class SessionService:
    """
    Manages session lifecycle and coordinates with the orchestrator.
    """

    def __init__(self, api_client: QwenAPIClient, state_manager: StateManager):
        self.api_client = api_client
        self.state_manager = state_manager
        self.orchestrator = Orchestrator(api_client)
        self._active_sessions: Dict[str, SessionState] = {}

    def create_session(self, theme: str, constraints: str) -> SessionState:
        """Create a new hackathon session."""
        session_id = str(uuid.uuid4())[:8]

        state = SessionState(
            session_id=session_id,
            theme=theme,
            constraints=constraints,
        )

        # Save initial state
        self.state_manager.save(session_id, state.to_dict())
        self._active_sessions[session_id] = state

        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID."""
        # Check active sessions first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Try to load from storage
        data = self.state_manager.load(session_id)
        if data:
            state = SessionState.model_validate(data)
            self._active_sessions[session_id] = state
            return state

        return None

    def list_sessions(self) -> list:
        """List all session IDs."""
        return self.state_manager.list_sessions()

    async def start_workflow(self, session_id: str) -> SessionState:
        """Start the ideation workflow as a background task."""
        state = self.get_session(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        # Run ideation in background so API returns immediately
        asyncio.create_task(self._run_ideation_background(session_id, state))
        
        return state
    
    async def _run_ideation_background(self, session_id: str, state: SessionState):
        """Run the ideation workflow in the background."""
        try:
            result = await self.orchestrator.run_ideation(state)
            self.save_session(session_id)
            return result
        except Exception as e:
            state.set_error(f"Ideation failed: {str(e)}")
            self.save_session(session_id)
            raise

    async def select_idea(self, session_id: str, idea_id: int, feedback: Optional[str] = None) -> SessionState:
        """Handle idea selection at HITL 1 - runs in background."""
        state = self.get_session(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        # Find and store selected idea immediately so UI can show it
        selected = next((i for i in state.ideas if i.id == idea_id), None)
        if not selected:
            raise ValueError(f"Idea with id {idea_id} not found")
        
        state.selected_idea = selected
        state.user_feedback_1 = {"idea_id": idea_id, "feedback": feedback or ""}
        state.add_agent_message(
            agent="system", agent_name="System", emoji="✅", role="HITL",
            message=f"Selected idea #{idea_id}: '{selected.title}'. Starting development phase..."
        )
        state.resume()
        
        # Save state immediately so UI can see selected_idea
        self.save_session(session_id)
        
        # Run planning → building → critiquing in background
        asyncio.create_task(self._run_development_background(session_id, state))
        
        return state
    
    async def _run_development_background(self, session_id: str, state: SessionState):
        """Run the full development workflow in background."""
        try:
            result = await self.orchestrator.run_planning(state)
            self.save_session(session_id)
        except Exception as e:
            state.set_error(f"Planning failed: {str(e)}")
            self.save_session(session_id)
            raise

    async def approve_code(self, session_id: str, feedback: Optional[str] = None) -> SessionState:
        """Handle code approval at HITL 2."""
        state = self.get_session(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        return await self.orchestrator.handle_code_review(state, approved=True, feedback=feedback)

    async def request_changes(self, session_id: str, feedback: str) -> SessionState:
        """Handle code change request at HITL 2."""
        state = self.get_session(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        return await self.orchestrator.handle_code_review(state, approved=False, feedback=feedback)

    def save_session(self, session_id: str) -> bool:
        """Save current session state."""
        state = self._active_sessions.get(session_id)
        if state:
            return self.state_manager.save(session_id, state.to_dict())
        return False