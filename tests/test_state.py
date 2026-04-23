"""
Tests for SessionState and related Pydantic models.
Covers state transitions, message logging, and JSON serialization.
"""

import pytest
import json
from datetime import datetime

from src.core.state import (
    SessionState, WorkflowLayer, Idea, IdeaEvaluation, Milestone,
    CodeFile, CodeIssue, PitchNarrative, Slide, ScriptSection, AgentMessage
)


class TestIdeaModel:
    """Tests for the Idea Pydantic model."""

    def test_create_idea(self):
        """Test creating a valid Idea."""
        idea = Idea(
            id=1,
            title="Test Idea",
            description="A test project idea",
            key_features=["Feature 1", "Feature 2"],
            tech_stack=["FastAPI", "Streamlit"],
            innovation_score=8.5,
            target_users="Students"
        )
        assert idea.id == 1
        assert idea.title == "Test Idea"
        assert len(idea.key_features) == 2
        assert idea.innovation_score == 8.5

    def test_idea_validation_score(self):
        """Test innovation_score must be between 1 and 10."""
        with pytest.raises(Exception):
            Idea(
                id=1, title="Test", description="Test",
                innovation_score=11, target_users="Test"
            )
        
        with pytest.raises(Exception):
            Idea(
                id=1, title="Test", description="Test",
                innovation_score=0, target_users="Test"
            )

    def test_idea_to_dict(self):
        """Test Idea serialization to dictionary."""
        idea = Idea(
            id=1, title="Test", description="Test description",
            innovation_score=8.0, target_users="Test users"
        )
        data = idea.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == 1
        assert data["title"] == "Test"


class TestCodeFileModel:
    """Tests for the CodeFile Pydantic model."""

    def test_create_code_file(self):
        """Test creating a valid CodeFile."""
        code = CodeFile(
            filepath="main.py",
            description="Main application file",
            content='print("Hello World")',
            language="python"
        )
        assert code.filepath == "main.py"
        assert code.language == "python"
        assert 'print' in code.content

    def test_code_file_default_language(self):
        """Test default language is Python."""
        code = CodeFile(
            filepath="script.py",
            description="Script file",
            content="print('test')"
        )
        assert code.language == "python"


class TestPitchNarrative:
    """Tests for the PitchNarrative model."""

    def test_create_narrative(self):
        """Test creating a valid PitchNarrative."""
        narrative = PitchNarrative(
            problem="Test problem",
            solution="Test solution",
            demo_plan="Test demo",
            impact="Test impact",
            future_vision="Test future"
        )
        assert narrative.problem == "Test problem"
        assert narrative.solution == "Test solution"
        assert len(narrative.demo_plan) > 0


class TestSlide:
    """Tests for the Slide model."""

    def test_create_slide(self):
        """Test creating a valid Slide."""
        slide = Slide(
            slide_number=1,
            title="Test Title",
            subtitle="Test Subtitle",
            bullet_points=["Point 1", "Point 2"],
            visual_suggestion="Test visual",
            design_note="Test note"
        )
        assert slide.slide_number == 1
        assert len(slide.bullet_points) == 2

    def test_slide_empty_bullets(self):
        """Test slide with no bullet points."""
        slide = Slide(
            slide_number=1,
            title="Test",
            subtitle="Test subtitle",
            visual_suggestion="Test",
            design_note="Test"
        )
        assert slide.bullet_points == []


class TestSessionState:
    """Tests for the SessionState model."""

    def test_create_session_state(self):
        """Test creating a new session state."""
        state = SessionState(
            session_id="test-001",
            theme="AI for Education",
            constraints="48-hour hackathon"
        )
        assert state.session_id == "test-001"
        assert state.current_layer == WorkflowLayer.IDLE
        assert state.is_paused is False
        assert len(state.ideas) == 0
        assert len(state.agent_log) == 0

    def test_session_to_dict(self):
        """Test session state serialization."""
        state = SessionState(
            session_id="test-001",
            theme="Test Theme"
        )
        data = state.to_dict()
        assert isinstance(data, dict)
        assert data["session_id"] == "test-001"
        assert data["current_layer"] == "idle"

    def test_transition_to(self):
        """Test workflow layer transitions."""
        state = SessionState(session_id="test-001")
        assert state.current_layer == WorkflowLayer.IDLE
        
        state.transition_to(WorkflowLayer.IDEATION)
        assert state.current_layer == WorkflowLayer.IDEATION
        assert state.previous_layer == WorkflowLayer.IDLE

    def test_pause_for_hitl(self):
        """Test pausing for human-in-the-loop."""
        state = SessionState(session_id="test-001")
        assert state.is_paused is False
        
        state.pause_for_hitl("Select an idea")
        assert state.is_paused is True
        assert state.pause_reason == "Select an idea"

    def test_resume(self):
        """Test resuming after HITL."""
        state = SessionState(session_id="test-001")
        state.pause_for_hitl("Select an idea")
        assert state.is_paused is True
        
        state.resume()
        assert state.is_paused is False
        assert state.pause_reason == ""

    def test_set_error(self):
        """Test setting error state."""
        state = SessionState(session_id="test-001")
        state.set_error("API connection failed")
        assert state.current_layer == WorkflowLayer.ERROR
        assert state.error_message == "API connection failed"

    def test_add_agent_message(self):
        """Test adding agent messages to log."""
        state = SessionState(session_id="test-001")
        state.add_agent_message(
            agent="ideator",
            agent_name="สุรเดช",
            emoji="🧠",
            role="Creative Director",
            message="Here are some ideas!"
        )
        assert len(state.agent_log) == 1
        assert state.agent_log[0].agent == "ideator"
        assert state.agent_log[0].message == "Here are some ideas!"

    def test_add_agent_message_with_metadata(self):
        """Test adding agent message with metadata."""
        state = SessionState(session_id="test-001")
        state.add_agent_message(
            agent="judge",
            agent_name="วันเพ็ญ",
            emoji="⚖️",
            role="Pragmatic Lead",
            message="Evaluated ideas",
            metadata={"evaluation_count": 3}
        )
        assert state.agent_log[0].metadata["evaluation_count"] == 3

    def test_multiple_transitions(self):
        """Test multiple workflow transitions."""
        state = SessionState(session_id="test-001")
        
        state.transition_to(WorkflowLayer.IDEATION)
        state.transition_to(WorkflowLayer.JUDGING)
        state.transition_to(WorkflowLayer.HITL_1)
        
        assert state.current_layer == WorkflowLayer.HITL_1
        assert state.previous_layer == WorkflowLayer.JUDGING

    def test_updated_at_changes(self):
        """Test that updated_at changes on operations."""
        import time
        state = SessionState(session_id="test-001")
        original_time = state.updated_at
        
        time.sleep(0.01)
        state.add_agent_message(
            agent="test", agent_name="Test", emoji="🧪",
            role="Tester", message="Test"
        )
        assert state.updated_at > original_time


class TestWorkflowLayer:
    """Tests for the WorkflowLayer enum."""

    def test_all_layers_exist(self):
        """Test all expected workflow layers exist."""
        expected_layers = [
            "idle", "ideation", "judging", "hitl_1",
            "planning", "architecting", "building", "critiquing",
            "hitl_2", "pitching", "complete", "error"
        ]
        for layer in expected_layers:
            assert layer in [l.value for l in WorkflowLayer]

    def test_layer_values(self):
        """Test layer enum values."""
        assert WorkflowLayer.IDLE.value == "idle"
        assert WorkflowLayer.IDEATION.value == "ideation"
        assert WorkflowLayer.COMPLETE.value == "complete"
        assert WorkflowLayer.ERROR.value == "error"


class TestCodeIssue:
    """Tests for the CodeIssue model."""

    def test_create_code_issue(self):
        """Test creating a valid CodeIssue."""
        issue = CodeIssue(
            severity="high",
            file="main.py",
            line=42,
            description="Missing error handling",
            fix="Add try/except block"
        )
        assert issue.severity == "high"
        assert issue.line == 42

    def test_code_issue_default_line(self):
        """Test default line number is 0."""
        issue = CodeIssue(
            severity="low",
            file="utils.py",
            description="Typo in variable name",
            fix="Fix typo"
        )
        assert issue.line == 0


class TestIdeaEvaluation:
    """Tests for the IdeaEvaluation model."""

    def test_create_evaluation(self):
        """Test creating a valid IdeaEvaluation."""
        eval = IdeaEvaluation(
            idea_id=1,
            idea_title="Test Idea",
            scores={"feasibility": 8.0, "impact": 9.0},
            total_score=8.5,
            strengths=["Good concept"],
            risks=["Needs more research"],
            recommendation="Proceed"
        )
        assert eval.idea_id == 1
        assert eval.total_score == 8.5
        assert len(eval.strengths) == 1

    def test_evaluation_empty_scores(self):
        """Test evaluation with empty scores."""
        eval = IdeaEvaluation(
            idea_id=1,
            idea_title="Test",
            total_score=0.0,
            recommendation="Test"
        )
        assert eval.scores == {}
        assert eval.strengths == []
        assert eval.risks == []
