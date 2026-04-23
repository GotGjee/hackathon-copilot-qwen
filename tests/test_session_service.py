"""
Tests for the SessionService.
Covers session creation, retrieval, and management with mocked dependencies.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.session_service import SessionService
from src.core.state import SessionState, WorkflowLayer


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    return AsyncMock()


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    manager = MagicMock()
    manager.save = MagicMock(return_value=True)
    manager.load = MagicMock(return_value=None)
    manager.list_sessions = MagicMock(return_value=[])
    return manager


@pytest.fixture
def session_service(mock_api_client, mock_state_manager):
    """Create a SessionService with mocked dependencies."""
    return SessionService(api_client=mock_api_client, state_manager=mock_state_manager)


class TestSessionService:
    """Tests for SessionService."""

    def test_create_session(self, session_service, mock_state_manager):
        """Test creating a new session."""
        state = session_service.create_session("Test Theme", "Test Constraints")
        assert state is not None
        assert state.session_id is not None
        assert len(state.session_id) > 0
        assert state.theme == "Test Theme"
        assert state.constraints == "Test Constraints"
        assert mock_state_manager.save.called

    def test_get_session_from_active(self, session_service):
        """Test retrieving an active session."""
        state = session_service.create_session("Test Theme", "Test Constraints")
        result = session_service.get_session(state.session_id)
        assert result is not None
        assert result.session_id == state.session_id

    def test_get_session_from_storage(self, session_service, mock_state_manager):
        """Test retrieving a session from storage."""
        state_data = {
            "session_id": "stored-001",
            "theme": "Stored Theme",
            "constraints": "Stored Constraints",
            "current_layer": "idle",
            "is_paused": False,
            "ideas": [],
            "selected_idea": None,
            "evaluations": [],
            "milestones": [],
            "narrative": None,
            "slides": [],
            "script": [],
            "code_artifacts": {},
            "code_issues": [],
            "agent_log": [],
            "previous_layer": None,
            "error_message": "",
            "pause_reason": "",
            "refinement_count": 0,
            "updated_at": "2024-01-01T00:00:00"
        }
        mock_state_manager.load = MagicMock(return_value=state_data)
        result = session_service.get_session("stored-001")
        assert result is not None
        assert result.session_id == "stored-001"
        assert result.theme == "Stored Theme"

    def test_get_nonexistent_session(self, session_service, mock_state_manager):
        """Test retrieving a session that doesn't exist."""
        mock_state_manager.load = MagicMock(return_value=None)
        result = session_service.get_session("nonexistent-id")
        assert result is None

    def test_list_sessions(self, session_service, mock_state_manager):
        """Test listing sessions."""
        mock_state_manager.list_sessions = MagicMock(return_value=["sess-1", "sess-2"])
        result = session_service.list_sessions()
        assert result == ["sess-1", "sess-2"]

    def test_save_session(self, session_service, mock_state_manager):
        """Test saving session state."""
        state = session_service.create_session("Test Theme", "Test Constraints")
        result = session_service.save_session(state.session_id)
        assert result is True
        assert mock_state_manager.save.called

    def test_save_nonexistent_session(self, session_service):
        """Test saving a session that doesn't exist."""
        result = session_service.save_session("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_workflow_not_found(self, session_service, mock_state_manager):
        """Test starting workflow for non-existent session."""
        mock_state_manager.load = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await session_service.start_workflow("nonexistent-id")

    @pytest.mark.asyncio
    async def test_select_idea_not_found(self, session_service, mock_state_manager):
        """Test selecting an idea from non-existent session."""
        mock_state_manager.load = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await session_service.select_idea("nonexistent-id", 1)

    @pytest.mark.asyncio
    async def test_select_idea_invalid_id(self, session_service):
        """Test selecting an idea with invalid ID."""
        state = session_service.create_session("Test", "Constraints")
        with pytest.raises(ValueError, match="not found"):
            await session_service.select_idea(state.session_id, 999)

    @pytest.mark.asyncio
    async def test_approve_code_not_found(self, session_service, mock_state_manager):
        """Test approving code for non-existent session."""
        mock_state_manager.load = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await session_service.approve_code("nonexistent-id")

    @pytest.mark.asyncio
    async def test_request_changes_not_found(self, session_service, mock_state_manager):
        """Test requesting changes for non-existent session."""
        mock_state_manager.load = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await session_service.request_changes("nonexistent-id", "fix this")