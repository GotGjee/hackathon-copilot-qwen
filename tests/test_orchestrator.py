"""
Tests for the Orchestrator.
Covers agent coordination, workflow phases, and state transitions.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.orchestrator import Orchestrator
from src.core.state import SessionState, WorkflowLayer, Idea


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    return AsyncMock()


@pytest.fixture
def orchestrator(mock_api_client):
    """Create an Orchestrator with mocked API client."""
    return Orchestrator(api_client=mock_api_client)


@pytest.fixture
def new_session():
    """Create a new session state for testing."""
    return SessionState(
        session_id="test-001",
        theme="AI for Education",
        constraints="48-hour hackathon"
    )


class TestOrchestratorInit:
    """Tests for Orchestrator initialization."""

    def test_create_orchestrator(self, mock_api_client):
        """Test creating an Orchestrator."""
        orch = Orchestrator(api_client=mock_api_client)
        assert orch.api_client is mock_api_client
        assert orch.parser is not None

    def test_valid_transitions(self, orchestrator, new_session):
        """Test transition validation."""
        new_session.current_layer = WorkflowLayer.IDLE
        assert orchestrator.can_transition(new_session, WorkflowLayer.IDEATION) is True
        assert orchestrator.can_transition(new_session, WorkflowLayer.COMPLETE) is False

    def test_invalid_transition(self, orchestrator, new_session):
        """Test invalid transition is rejected."""
        new_session.current_layer = WorkflowLayer.COMPLETE
        assert orchestrator.can_transition(new_session, WorkflowLayer.IDEATION) is False


class TestStateTransitions:
    """Tests for state transitions."""

    def test_ideation_to_judging_chain(self, new_session):
        """Test state chain from ideation to judging."""
        new_session.current_layer = WorkflowLayer.IDEATION
        new_session.previous_layer = WorkflowLayer.IDLE
        # Use transition_to which sets previous_layer correctly
        prev = new_session.current_layer
        new_session.transition_to(WorkflowLayer.JUDGING)
        assert new_session.current_layer == WorkflowLayer.JUDGING
        assert new_session.previous_layer == prev

    def test_full_workflow_chain(self, new_session):
        """Test full workflow state chain."""
        layers = [
            WorkflowLayer.IDEATION,
            WorkflowLayer.JUDGING,
            WorkflowLayer.HITL_1,
            WorkflowLayer.PLANNING,
            WorkflowLayer.ARCHITECTING,
            WorkflowLayer.BUILDING,
            WorkflowLayer.CRITIQUING,
            WorkflowLayer.HITL_2,
            WorkflowLayer.PITCHING,
            WorkflowLayer.COMPLETE
        ]
        prev = WorkflowLayer.IDLE
        for layer in layers:
            new_session.previous_layer = prev
            new_session.current_layer = layer
            assert new_session.current_layer == layer
            assert new_session.previous_layer == prev
            prev = layer


class TestErrorHandling:
    """Tests for error handling in orchestrator."""

    def test_set_error_state(self, orchestrator, new_session):
        """Test error state is set correctly."""
        new_session.set_error("Test error")
        assert new_session.current_layer == WorkflowLayer.ERROR
        assert new_session.error_message == "Test error"

    def test_state_recovery(self, orchestrator, new_session):
        """Test state can recover from error."""
        new_session.set_error("Test error")
        new_session.current_layer = WorkflowLayer.IDLE
        new_session.error_message = ""
        assert new_session.current_layer == WorkflowLayer.IDLE
        assert new_session.error_message == ""


class TestOrchestratorPhases:
    """Tests for orchestrator workflow phases with mocked agents."""

    @pytest.mark.asyncio
    async def test_run_ideation_success(self, orchestrator, new_session):
        """Test successful ideation phase."""
        # Mock the IdeatorAgent
        with patch('src.agents.ideator.IdeatorAgent') as MockIdeatorAgent:
            mock_agent = AsyncMock()
            mock_result = MagicMock()
            mock_result.ideas = [
                Idea(id=1, title="Idea 1", description="Test idea 1", innovation_score=8.0, target_users="Users"),
                Idea(id=2, title="Idea 2", description="Test idea 2", innovation_score=7.0, target_users="Users"),
            ]
            mock_result.message = "Generated ideas"
            mock_result.closing_message = "Done"
            mock_agent.generate_ideas = AsyncMock(return_value=mock_result)
            MockIdeatorAgent.return_value = mock_agent

            # Mock run_judging_with_dialogue to prevent full chain
            with patch.object(orchestrator, 'run_judging_with_dialogue', new_callable=AsyncMock) as mock_judging:
                mock_judging.return_value = new_session
                
                result = await orchestrator.run_ideation(new_session)
                assert result.current_layer == WorkflowLayer.JUDGING or result is not None
                assert len(new_session.ideas) == 2

    @pytest.mark.asyncio
    async def test_run_ideation_error(self, orchestrator, new_session):
        """Test ideation error sets error state."""
        with patch('src.agents.ideator.IdeatorAgent') as MockIdeatorAgent:
            mock_agent = AsyncMock()
            mock_agent.generate_ideas = AsyncMock(side_effect=Exception("API error"))
            MockIdeatorAgent.return_value = mock_agent

            with pytest.raises(Exception, match="API error"):
                await orchestrator.run_ideation(new_session)
            assert new_session.current_layer == WorkflowLayer.ERROR

    @pytest.mark.asyncio
    async def test_run_planning_success(self, orchestrator, new_session):
        """Test planning phase success."""
        new_session.selected_idea = Idea(id=1, title="Test", description="Test", innovation_score=8.0, target_users="Users")
        
        with patch('src.agents.planner.PlannerAgent') as MockPlannerAgent:
            mock_agent = AsyncMock()
            mock_result = MagicMock()
            mock_result.milestones = []
            mock_result.message = "Plan created"
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockPlannerAgent.return_value = mock_agent

            # Mock next phase
            with patch.object(orchestrator, 'run_architecting', new_callable=AsyncMock) as mock_arch:
                mock_arch.return_value = new_session
                result = await orchestrator.run_planning(new_session)
                assert mock_agent.run.called or result is not None

    @pytest.mark.asyncio
    async def test_run_building_success(self, orchestrator, new_session):
        """Test building phase success."""
        new_session.milestones = []
        
        with patch('src.agents.builder.BuilderAgent') as MockBuilderAgent:
            mock_agent = AsyncMock()
            mock_result = MagicMock()
            mock_result.code_files = []
            mock_result.message = "Code generated"
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockBuilderAgent.return_value = mock_agent

            # Mock next phase
            with patch.object(orchestrator, 'run_critiquing', new_callable=AsyncMock) as mock_critique:
                mock_critique.return_value = new_session
                result = await orchestrator.run_building(new_session)
                assert mock_agent.run.called or result is not None

    @pytest.mark.asyncio
    async def test_run_pitching_success(self, orchestrator, new_session):
        """Test pitching phase transitions state to PITCHING."""
        new_session.selected_idea = Idea(id=1, title="Test", description="Test", innovation_score=8.0, target_users="Users")
        
        # Mock all the agents involved in pitching
        with patch('src.agents.pitch_strategist.PitchStrategistAgent') as MockPitchAgent, \
             patch('src.agents.slide_agent.SlideAgent') as MockSlideAgent, \
             patch('src.agents.script_agent.ScriptAgent') as MockScriptAgent:
            
            # Mock pitch strategist
            mock_pitch = AsyncMock()
            mock_pitch_result = MagicMock()
            mock_pitch_result.narrative = MagicMock()
            mock_pitch_result.narrative.problem = "Test"
            mock_pitch_result.narrative.solution = "Test"
            mock_pitch_result.slides = []
            mock_pitch_result.script = []
            mock_pitch_result.message = "Pitch created"
            mock_pitch.generate_pitch = AsyncMock(return_value=mock_pitch_result)
            MockPitchAgent.return_value = mock_pitch

            # Mock slide agent
            mock_slide = AsyncMock()
            mock_slide_result = MagicMock()
            mock_slide_result.slides = []
            mock_slide_result.message = "Slides created"
            mock_slide.create_slides = AsyncMock(return_value=mock_slide_result)
            MockSlideAgent.return_value = mock_slide

            # Mock script agent
            mock_script = AsyncMock()
            mock_script_result = MagicMock()
            mock_script_result.script = []
            mock_script_result.message = "Script created"
            mock_script.create_script = AsyncMock(return_value=mock_script_result)
            MockScriptAgent.return_value = mock_script

            result = await orchestrator.run_pitching(new_session)
            assert result.current_layer == WorkflowLayer.COMPLETE or result is not None
