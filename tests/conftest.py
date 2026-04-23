"""
Shared pytest fixtures for Hackathon Copilot tests.
Provides reusable test data and mock objects across all test modules.
"""

import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.state import (
    SessionState, WorkflowLayer, Idea, IdeaEvaluation, Milestone,
    CodeFile, CodeIssue, PitchNarrative, Slide, ScriptSection, AgentMessage
)


# ============================================================
# State Management Fixtures
# ============================================================

@pytest.fixture
def sample_idea():
    """Create a sample project idea."""
    return Idea(
        id=1,
        title="AI Tutor",
        description="An AI-powered tutoring system for students",
        key_features=["Adaptive learning", "Multi-language support", "Progress tracking"],
        tech_stack=["FastAPI", "Streamlit", "scikit-learn"],
        innovation_score=8.5,
        target_users="Students and teachers"
    )


@pytest.fixture
def sample_ideas(sample_idea):
    """Create a list of sample ideas."""
    return [
        sample_idea,
        Idea(
            id=2,
            title="Code Review Bot",
            description="Automated code review with AI suggestions",
            key_features=["Code analysis", "Bug detection", "Style checking"],
            tech_stack=["FastAPI", "AST parser", "GitHub API"],
            innovation_score=7.5,
            target_users="Developers"
        ),
        Idea(
            id=3,
            title="Smart Scheduler",
            description="AI-powered meeting and task scheduler",
            key_features=["Auto-scheduling", "Priority management", "Time optimization"],
            tech_stack=["FastAPI", "Celery", "Redis"],
            innovation_score=6.5,
            target_users="Teams and organizations"
        )
    ]


@pytest.fixture
def sample_evaluation():
    """Create a sample idea evaluation."""
    return IdeaEvaluation(
        idea_id=1,
        idea_title="AI Tutor",
        scores={
            "feasibility": 8.0,
            "impact": 9.0,
            "technical_complexity": 6.0,
            "innovation": 8.0,
            "market_potential": 7.0
        },
        total_score=7.75,
        strengths=["Clear use case", "Scalable architecture"],
        risks=["Requires training data", "Competition exists"],
        recommendation="Strong candidate, proceed with development"
    )


@pytest.fixture
def sample_milestone():
    """Create a sample milestone."""
    return Milestone(
        id=1,
        title="Project Setup",
        description="Initialize project structure and dependencies",
        tasks=["Create FastAPI project", "Set up database", "Configure CI/CD"],
        estimated_hours=4,
        dependencies=[],
        deliverables=["Working project structure", "Database schema"]
    )


@pytest.fixture
def sample_code_file():
    """Create a sample code file artifact."""
    return CodeFile(
        filepath="main.py",
        description="FastAPI application entry point",
        content="""from fastapi import FastAPI

app = FastAPI(title="AI Tutor")

@app.get("/")
async def root():
    '''Root endpoint.'''
    return {"message": "Welcome to AI Tutor"}

@app.get("/health")
async def health():
    '''Health check endpoint.'''
    return {"status": "ok"}
""",
        language="python"
    )


@pytest.fixture
def sample_code_files(sample_code_file):
    """Create a dictionary of sample code files."""
    return {
        "main.py": sample_code_file,
        "models.py": CodeFile(
            filepath="models.py",
            description="Pydantic models for the application",
            content="""from pydantic import BaseModel

class User(BaseModel):
    '''User model.'''
    id: int
    name: str
    email: str

class ChatRequest(BaseModel):
    '''Chat request model.'''
    user_id: int
    message: str

class ChatResponse(BaseModel):
    '''Chat response model.'''
    response: str
    confidence: float
""",
            language="python"
        ),
        "requirements.txt": CodeFile(
            filepath="requirements.txt",
            description="Project dependencies",
            content="fastapi\nuvicorn\npydantic\n",
            language="text"
        )
    }


@pytest.fixture
def sample_narrative():
    """Create a sample pitch narrative."""
    return PitchNarrative(
        problem="Students struggle with personalized learning experiences",
        solution="An AI tutor that adapts to each student's learning style",
        demo_plan="Show the chatbot solving math problems with step-by-step explanations",
        impact="Can help millions of students learn more effectively",
        future_vision="Expand to all subjects and support more languages"
    )


@pytest.fixture
def sample_slides():
    """Create sample slide deck."""
    return [
        Slide(
            slide_number=1,
            title="AI Tutor",
            subtitle="Personalized Learning with AI",
            bullet_points=["Team: AI Innovators", "Hackathon 2024"],
            visual_suggestion="Clean title with gradient background",
            design_note="Use blue-orange gradient"
        ),
        Slide(
            slide_number=2,
            title="The Problem",
            subtitle="Students need personalized learning",
            bullet_points=[
                "One-size-fits-all education doesn't work",
                "Teachers can't give individual attention",
                "Students fall behind or get bored"
            ],
            visual_suggestion="Infographic showing learning gaps",
            design_note="Use statistics and icons"
        ),
        Slide(
            slide_number=3,
            title="Our Solution",
            subtitle="AI-Powered Adaptive Tutoring",
            bullet_points=[
                "Adapts to each student's pace",
                "Multi-language support",
                "Real-time progress tracking"
            ],
            visual_suggestion="Product screenshot with annotations",
            design_note="Show the chatbot interface"
        )
    ]


@pytest.fixture
def sample_script():
    """Create sample speaker script sections."""
    return [
        ScriptSection(
            slide_number=1,
            section="hook",
            text="Good morning! Did you know that 65% of students today will work in jobs that don't exist yet?",
            duration_seconds=30,
            tone="engaging",
            notes="Pause for effect, make eye contact"
        ),
        ScriptSection(
            slide_number=2,
            section="problem",
            text="And yet, our education system still uses a one-size-fits-all approach...",
            duration_seconds=60,
            tone="serious",
            notes="Show empathy, connect with audience"
        )
    ]


@pytest.fixture
def sample_agent_message():
    """Create a sample agent message."""
    return AgentMessage(
        agent="ideator",
        agent_name="สุรเดช",
        emoji="🧠",
        role="Creative Director",
        message="Here are some innovative ideas for this hackathon!",
        metadata={"idea_count": 3}
    )


@pytest.fixture
def new_session_state():
    """Create a fresh session state."""
    state = SessionState(
        session_id="test-session-001",
        theme="AI for Education",
        constraints="48-hour hackathon, must use free APIs"
    )
    return state


@pytest.fixture
def populated_session_state(sample_ideas, sample_narrative, sample_slides, sample_script, sample_code_files):
    """Create a fully populated session state (as if flow completed)."""
    state = SessionState(
        session_id="test-session-complete",
        theme="AI for Education",
        constraints="48-hour hackathon, must use free APIs",
        current_layer=WorkflowLayer.COMPLETE,
        ideas=sample_ideas,
        selected_idea=sample_ideas[0],
        narrative=sample_narrative,
        slides=sample_slides,
        script=sample_script,
        code_artifacts=sample_code_files
    )
    state.add_agent_message(
        agent="ideator",
        agent_name="สุรเดช",
        emoji="🧠",
        role="Creative Director",
        message="Generated 3 ideas for AI for Education theme"
    )
    state.add_agent_message(
        agent="judge",
        agent_name="วันเพ็ญ",
        emoji="⚖️",
        role="Pragmatic Lead",
        message="Evaluated all ideas, Idea 1 is the strongest candidate"
    )
    return state


# ============================================================
# Mock API Client Fixtures
# ============================================================

@pytest.fixture
def mock_api_response():
    """Sample mock API response."""
    return {
        "message": "Test response",
        "ideas": [
            {
                "id": 1,
                "title": "Test Idea",
                "description": "A test project idea",
                "key_features": ["Feature 1", "Feature 2"],
                "tech_stack": ["FastAPI", "Streamlit"],
                "innovation_score": 8.0,
                "target_users": "Test users"
            }
        ],
        "closing_message": "Test complete!"
    }


@pytest.fixture
def mock_qwen_client(mock_api_response):
    """Create a mock Qwen API client."""
    mock_client = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=json.dumps(mock_api_response))
    mock_client.close = AsyncMock()
    return mock_client


# ============================================================
# Mock Agent Fixtures
# ============================================================

@pytest.fixture
def mock_ideator_result(sample_ideas):
    """Mock result from Ideator agent."""
    return MagicMock(
        message="I've generated 3 innovative ideas!",
        ideas=sample_ideas,
        closing_message="Let me know which idea you prefer!"
    )


@pytest.fixture
def mock_judge_result(sample_ideas, sample_evaluation):
    """Mock result from Judge agent."""
    return MagicMock(
        message="I've evaluated all ideas systematically.",
        evaluations=[sample_evaluation],
        ranking=[1, 2, 3],
        closing_message="Idea 1 is the strongest candidate."
    )


@pytest.fixture
def mock_planner_result(sample_milestone):
    """Mock result from Planner agent."""
    return MagicMock(
        message="Here's the project plan!",
        milestones=[sample_milestone],
        total_hours=36,
        critical_path=[1, 2, 3],
        closing_message="Let's stick to this timeline!"
    )


@pytest.fixture
def mock_builder_result(sample_code_files):
    """Mock result from Builder agent."""
    code_files_list = list(sample_code_files.values())
    return MagicMock(
        message="Skeleton code generated successfully!",
        code_files=code_files_list,
        closing_message="Please review the skeleton structure."
    )


# ============================================================
# Directory Fixtures
# ============================================================

@pytest.fixture
def tmp_export_dir(tmp_path):
    """Create a temporary export directory."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return str(export_dir)


@pytest.fixture
def tmp_session_dir(tmp_path):
    """Create a temporary session data directory."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    return str(session_dir)


# ============================================================
# Async Test Helpers
# ============================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()