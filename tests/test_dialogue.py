"""
Tests for Dialogue Loop Module.
Tests DialogueHistory, DialogueManager, and related functions.
"""

import pytest
from src.core.dialogue import DialogueTurn, DialogueHistory, DialogueManager, create_debate_prompt


class TestDialogueTurn:
    """Test DialogueTurn dataclass."""
    
    def test_create_dialogue_turn(self):
        """Test creating a basic dialogue turn."""
        turn = DialogueTurn(
            agent_type="ideator",
            agent_name="Sudet",
            emoji="🧠",
            role="Ideator",
            message="I think we should build an AI tutor",
            turn_number=1,
        )
        assert turn.agent_type == "ideator"
        assert turn.agent_name == "Sudet"
        assert turn.message == "I think we should build an AI tutor"
        assert turn.turn_number == 1
    
    def test_dialogue_turn_all_fields(self):
        """Test all fields are correctly set."""
        turn = DialogueTurn(
            agent_type="judge",
            agent_name="Wanphen",
            emoji="⚖️",
            role="Judge",
            message="Good idea but needs more analysis",
            turn_number=2,
        )
        assert turn.agent_type == "judge"
        assert turn.emoji == "⚖️"
        assert turn.role == "Judge"


class TestDialogueHistory:
    """Test DialogueHistory dataclass."""
    
    def test_create_empty_history(self):
        """Test creating empty dialogue history."""
        history = DialogueHistory(topic="Project Ideas")
        assert history.topic == "Project Ideas"
        assert len(history.turns) == 0
        assert history.is_complete is False
        assert history.get_last_message() is None
    
    def test_add_turn(self):
        """Test adding a turn to history."""
        history = DialogueHistory(topic="Ideas", max_turns=3)
        history.add_turn(
            agent_type="ideator",
            agent_name="Sudet",
            emoji="🧠",
            role="Ideator",
            message="Let's build AI tutor",
        )
        assert len(history.turns) == 1
        assert history.turns[0].message == "Let's build AI tutor"
        assert history.is_complete is False
    
    def test_auto_complete_at_max_turns(self):
        """Test dialogue auto-completes at max turns."""
        history = DialogueHistory(topic="Ideas", max_turns=2)
        history.add_turn("ideator", "Sudet", "🧠", "Ideator", "First idea")
        assert history.is_complete is False
        history.add_turn("judge", "Wanphen", "⚖️", "Judge", "Second idea")
        assert history.is_complete is True
    
    def test_get_formatted_history(self):
        """Test formatted history output."""
        history = DialogueHistory(topic="Test")
        history.add_turn("ideator", "Sudet", "🧠", "Ideator", "Idea 1")
        history.add_turn("judge", "Wanphen", "⚖️", "Judge", "Idea 2")
        
        formatted = history.get_formatted_history()
        assert "Test" in formatted
        assert "Sudet" in formatted
        assert "Wanphen" in formatted
        assert "Idea 1" in formatted
        assert "Idea 2" in formatted
    
    def test_get_messages_by_agent(self):
        """Test filtering messages by agent type."""
        history = DialogueHistory(topic="Test")
        history.add_turn("ideator", "Sudet", "🧠", "Ideator", "Idea A")
        history.add_turn("judge", "Wanphen", "⚖️", "Judge", "Review A")
        history.add_turn("ideator", "Sudet", "🧠", "Ideator", "Idea B")
        
        ideator_messages = history.get_messages_by_agent("ideator")
        assert len(ideator_messages) == 2
        assert "Idea A" in ideator_messages
        assert "Idea B" in ideator_messages
    
    def test_get_last_message(self):
        """Test getting last message."""
        history = DialogueHistory(topic="Test")
        history.add_turn("ideator", "Sudet", "🧠", "Ideator", "First")
        assert history.get_last_message() == "First"
        history.add_turn("judge", "Wanphen", "⚖️", "Judge", "Second")
        assert history.get_last_message() == "Second"


class TestDialogueManager:
    """Test DialogueManager class."""
    
    def test_start_dialogue(self):
        """Test starting a new dialogue."""
        manager = DialogueManager(max_turns=3)
        dialogue = manager.start_dialogue("test_1", "Project Ideas")
        assert dialogue.topic == "Project Ideas"
        assert dialogue.max_turns == 3
    
    def test_get_dialogue(self):
        """Test retrieving a dialogue."""
        manager = DialogueManager()
        manager.start_dialogue("test_1", "Ideas")
        dialogue = manager.get_dialogue("test_1")
        assert dialogue is not None
        assert dialogue.topic == "Ideas"
    
    def test_get_nonexistent_dialogue(self):
        """Test getting non-existent dialogue returns None."""
        manager = DialogueManager()
        dialogue = manager.get_dialogue("nonexistent")
        assert dialogue is None
    
    def test_complete_dialogue(self):
        """Test completing a dialogue."""
        manager = DialogueManager()
        manager.start_dialogue("test_1", "Ideas")
        summary = manager.complete_dialogue("test_1")
        assert summary is not None
        assert "Ideas" in summary
        
        dialogue: DialogueHistory | None = manager.get_dialogue("test_1")
        assert dialogue is not None
        assert dialogue.is_complete is True
    
    def test_complete_nonexistent_dialogue(self):
        """Test completing non-existent dialogue returns None."""
        manager = DialogueManager()
        summary = manager.complete_dialogue("nonexistent")
        assert summary is None
    
    def test_create_system_prompt_with_context(self):
        """Test creating system prompt with dialogue context."""
        manager = DialogueManager()
        dialogue = manager.start_dialogue("test_1", "Architecture Review")
        dialogue.add_turn("ideator", "Sudet", "🧠", "Ideator", "Let's use microservices")
        
        base_prompt = "You are a code reviewer."
        enhanced = manager.create_system_prompt_with_context(
            base_prompt, dialogue, "architect"
        )
        assert "Architecture Review" in enhanced
        assert "Sudet" in enhanced
        assert "microservices" in enhanced
        assert base_prompt in enhanced
    
    def test_create_user_prompt_with_feedback(self):
        """Test creating user prompt with feedback."""
        manager = DialogueManager()
        base_prompt = "Build a REST API"
        
        # Test without feedback
        prompt = manager.create_user_prompt_with_feedback(base_prompt)
        assert "Build a REST API" in prompt
        
        # Test with user feedback
        prompt = manager.create_user_prompt_with_feedback(
            base_prompt, user_feedback="Add authentication"
        )
        assert "Add authentication" in prompt
        assert "HUMAN FEEDBACK" in prompt
    
    def test_create_user_prompt_with_dialogue(self):
        """Test creating user prompt with dialogue context."""
        manager = DialogueManager()
        dialogue = manager.start_dialogue("test_1", "API Design")
        dialogue.add_turn("architect", "Pimjai", "🏗️", "Architect", "Use REST")
        
        prompt = manager.create_user_prompt_with_feedback(
            "Build the API", dialogue=dialogue
        )
        assert "TEAM DIALOGUE CONTEXT" in prompt
        assert "Use REST" in prompt
    
    def test_create_user_prompt_with_both(self):
        """Test creating user prompt with both dialogue and feedback."""
        manager = DialogueManager()
        dialogue = manager.start_dialogue("test_1", "API Design")
        dialogue.add_turn("architect", "Pimjai", "🏗️", "Architect", "Use GraphQL")
        
        prompt = manager.create_user_prompt_with_feedback(
            "Build the API",
            user_feedback="Make it simple",
            dialogue=dialogue,
        )
        assert "TEAM DIALOGUE CONTEXT" in prompt
        assert "HUMAN FEEDBACK" in prompt
        assert "Make it simple" in prompt
        assert "Use GraphQL" in prompt


class TestCreateDebatePrompt:
    """Test create_debate_prompt function."""
    
    def test_basic_debate_prompt(self):
        """Test creating a basic debate prompt."""
        messages = create_debate_prompt(
            topic="Tech Stack Selection",
            agent_type="architect",
            agent_name="Pimjai",
            emoji="🏗️",
            role="Architect",
            opposing_view="We should use Python",
            opposing_agent_name="Sudet",
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Pimjai" in messages[0]["content"]
        assert "Tech Stack Selection" in messages[0]["content"]
        assert "Python" in messages[1]["content"]
        assert "Sudet" in messages[1]["content"]
    
    def test_debate_prompt_with_user_feedback(self):
        """Test debate prompt with user feedback."""
        messages = create_debate_prompt(
            topic="Architecture",
            agent_type="architect",
            agent_name="Pimjai",
            emoji="🏗️",
            role="Architect",
            opposing_view="Monolith is better",
            opposing_agent_name="Sudet",
            user_feedback="Consider scalability",
        )
        assert "Consider scalability" in messages[1]["content"]
        assert "Human Feedback" in messages[1]["content"]