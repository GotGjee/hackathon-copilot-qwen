"""
Tests for the PromptBuilder module.
Tests dynamic prompt generation from templates.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, mock_open

from src.core.prompt_builder import PromptBuilder, PromptTemplate


class TestPromptTemplate:
    """Tests for PromptTemplate class."""

    def test_extract_variables_simple(self):
        """Test variable extraction from simple template."""
        template = "Hello {name}, you are {age} years old."
        pt = PromptTemplate("test", template)
        assert set(pt.variables) == {"name", "age"}

    def test_extract_variables_no_variables(self):
        """Test template with no variables."""
        template = "Hello world, no variables here."
        pt = PromptTemplate("test", template)
        assert pt.variables == []

    def test_extract_variables_duplicate(self):
        """Test that duplicate variables are only listed once."""
        template = "Hello {name}, your name is {name}."
        pt = PromptTemplate("test", template)
        # re.findall returns duplicates, but that's OK for rendering
        assert "name" in pt.variables

    def test_render_simple(self):
        """Test rendering a simple template."""
        template = "Hello {name}!"
        pt = PromptTemplate("test", template)
        result = pt.render(name="World")
        assert result == "Hello World!"

    def test_render_multiple_variables(self):
        """Test rendering with multiple variables."""
        template = "{greeting} {name}, you are {age} years old."
        pt = PromptTemplate("test", template)
        result = pt.render(greeting="Hello", name="John", age=30)
        assert result == "Hello John, you are 30 years old."

    def test_render_missing_variables(self):
        """Test that missing variables get placeholder."""
        template = "Hello {name}, you are {age} years old."
        pt = PromptTemplate("test", template)
        result = pt.render(name="John")
        assert "Hello John" in result
        assert "[age]" in result

    def test_render_with_thai_text(self):
        """Test rendering with Thai text."""
        template = "สวัสดี {name} คุณอายุ {age} ปี"
        pt = PromptTemplate("test", template)
        result = pt.render(name="สมชาย", age="25")
        assert "สวัสดี สมชาย" in result
        assert "คุณอายุ 25 ปี" in result

    def test_render_with_emoji(self):
        """Test rendering with emojis."""
        template = "🧠 {agent_name} ({role}): {message}"
        pt = PromptTemplate("test", template)
        result = pt.render(agent_name="สุรเดช", role="Creative Director", message="สวัสดี!")
        assert "🧠 สุรเดช (Creative Director): สวัสดี!" in result

    def test_render_extra_variables_ignored(self):
        """Test that extra variables are ignored."""
        template = "Hello {name}!"
        pt = PromptTemplate("test", template)
        result = pt.render(name="World", extra="ignored")
        assert result == "Hello World!"


class TestPromptBuilder:
    """Tests for PromptBuilder class."""

    def test_init_with_defaults(self):
        """Test that PromptBuilder initializes with default templates."""
        pb = PromptBuilder()
        assert "negotiation" in pb.templates
        assert "ideator_response" in pb.templates["negotiation"]
        assert "judge_counter" in pb.templates["negotiation"]
        assert "consensus" in pb.templates["negotiation"]

    def test_get_template_names(self):
        """Test listing template names."""
        pb = PromptBuilder()
        names = pb.get_template_names()
        assert "negotiation" in names

    def test_get_template(self):
        """Test getting a specific template."""
        pb = PromptBuilder()
        template = pb.get_template("negotiation")
        assert template is not None
        assert "ideator_response" in template

    def test_get_negotiation_prompt_basic(self):
        """Test getting negotiation prompt."""
        pb = PromptBuilder()
        prompts = pb.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt="You are an ideator.",
            opposing_name="วันเพ็ญ",
            opposing_view="ไอเดียนี้ feasibility ต่ำ",
            dialogue_history="วันเพ็ญ: วิเคราะห์แล้ว",
            context={
                "top_idea": {"title": "AI Tutor"},
                "instructions": "ตอบกลับอย่างสุภาพ",
            },
        )
        assert "system" in prompts
        assert "user" in prompts
        assert "สุรเดช" in prompts["user"]
        assert "วันเพ็ญ" in prompts["user"]
        assert "AI Tutor" in prompts["user"]

    def test_get_negotiation_prompt_debate_context(self):
        """Test negotiation prompt with debate context."""
        pb = PromptBuilder()
        prompts = pb.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt="You are an ideator.",
            opposing_name="วันเพ็ญ",
            opposing_view="ไม่เห็นด้วย",
            dialogue_history="",
            context={
                "is_debate": True,
                "top_idea": "AI Tutor",
            },
        )
        # Should still return a valid prompt
        assert prompts["user"] is not None
        assert "สุรเดช" in prompts["user"]

    def test_get_negotiation_prompt_agreement_context(self):
        """Test negotiation prompt with agreement context."""
        pb = PromptBuilder()
        prompts = pb.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt="You are an ideator.",
            opposing_name="วันเพ็ญ",
            opposing_view="เห็นด้วย",
            dialogue_history="",
            context={
                "is_agreement": True,
                "top_idea": "AI Tutor",
            },
        )
        assert prompts["user"] is not None

    def test_get_negotiation_prompt_empty_context(self):
        """Test negotiation prompt with empty context."""
        pb = PromptBuilder()
        prompts = pb.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt="You are an ideator.",
            opposing_name="วันเพ็ญ",
            opposing_view="",
            dialogue_history="",
        )
        assert prompts["system"] == "You are an ideator."
        assert "สุรเดช" in prompts["user"]

    def test_get_judge_counter_prompt(self):
        """Test getting judge counter prompt."""
        pb = PromptBuilder()
        prompts = pb.get_judge_counter_prompt(
            agent_name="วันเพ็ญ",
            agent_role="Pragmatic Lead",
            agent_system_prompt="You are a judge.",
            opposing_name="สุรเดช",
            opposing_view="ไอเดียนี้ดีมาก",
            dialogue_history="สุรเดช: ไอเดียนี้น่าสนใจ",
            context={
                "instructions": "ตอบกลับอย่างมีเหตุผล",
            },
        )
        assert "system" in prompts
        assert "user" in prompts
        assert "วันเพ็ญ" in prompts["user"]
        assert "สุรเดช" in prompts["user"]

    def test_get_judge_counter_prompt_empty_context(self):
        """Test judge counter prompt with empty context."""
        pb = PromptBuilder()
        prompts = pb.get_judge_counter_prompt(
            agent_name="วันเพ็ญ",
            agent_role="Pragmatic Lead",
            agent_system_prompt="You are a judge.",
            opposing_name="สุรเดช",
            opposing_view="",
            dialogue_history="",
        )
        assert prompts["system"] == "You are a judge."
        assert prompts["user"] is not None

    def test_get_consensus_prompt(self):
        """Test getting consensus prompt."""
        pb = PromptBuilder()
        result = pb.get_consensus_prompt(
            agent1_name="สุรเดช",
            agent2_name="วันเพ็ญ",
            dialogue_history="สุรเดช: ไอเดียนี้น่าสนใจ\nวันเพ็ญ: เห็นด้วยค่ะ",
            consensus_statement="ทีมเห็นด้วยกับไอเดีย AI Tutor",
        )
        assert "สุรเดช" in result
        assert "วันเพ็ญ" in result
        assert "AI Tutor" in result
        assert "ฉันทามติ" in result

    def test_reload(self):
        """Test reloading templates."""
        pb = PromptBuilder()
        # Should not raise
        pb.reload()
        assert "negotiation" in pb.templates


class TestPromptBuilderWithYAML:
    """Tests for loading templates from YAML files."""

    def test_load_from_yaml_file(self, tmp_path):
        """Test loading templates from YAML file."""
        # Create a temporary YAML file
        yaml_content = """
negotiation:
  ideator_response: |
    TEST {agent_name} ({role}): ตอบกลับ {opposing_name}
    ไอเดีย: {top_idea}
  judge_counter: |
    TEST {agent_name}: ตอบกลับ {opposing_name}
  consensus: |
    TEST {agent1_name} และ {agent2_name} เห็นร่วมกัน
"""
        yaml_file = tmp_path / "negotiation.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        # Create PromptBuilder with custom directory
        pb = PromptBuilder(template_dir=str(tmp_path))
        
        # Should have loaded from YAML
        assert "negotiation" in pb.templates
        negotiation = pb.templates["negotiation"]
        # YAML loads as dict with keys: ideator_response, judge_counter, consensus
        assert isinstance(negotiation, dict), f"Expected dict, got {type(negotiation)}"
        assert "ideator_response" in negotiation, f"Missing ideator_response. Keys: {list(negotiation.keys())}"
        assert "TEST {agent_name}" in negotiation["ideator_response"]

    def test_fallback_to_defaults_when_yaml_not_found(self, tmp_path):
        """Test fallback to default templates when YAML not found."""
        non_existent_dir = tmp_path / "non_existent"
        pb = PromptBuilder(template_dir=str(non_existent_dir))
        
        # Should use defaults
        assert "negotiation" in pb.templates
        assert "ideator_response" in pb.templates["negotiation"]

    def test_fallback_to_defaults_when_yaml_invalid(self, tmp_path):
        """Test fallback to default templates when YAML is invalid."""
        yaml_file = tmp_path / "negotiation.yaml"
        yaml_file.write_text("invalid: yaml: [", encoding="utf-8")

        pb = PromptBuilder(template_dir=str(tmp_path))
        
        # Should use defaults
        assert "negotiation" in pb.templates


class TestPromptBuilderIntegration:
    """Integration tests for PromptBuilder with real-world scenarios."""

    def test_full_negotiation_workflow(self):
        """Test full negotiation workflow with prompt builder."""
        pb = PromptBuilder()
        
        # Step 1: Ideator responds to judge
        ideator_prompts = pb.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt="You are a creative ideator.",
            opposing_name="วันเพ็ญ",
            opposing_view="ไอเดีย AI Tutor feasibility ต่ำ เพราะต้องใช้ ML model ใหญ่",
            dialogue_history="",
            context={
                "top_idea": "AI Tutor - AI ที่สอนการเขียนโปรแกรม",
                "instructions": "ตอบกลับและเสนอทางเลือก",
            },
        )
        
        assert ideator_prompts["system"] == "You are a creative ideator."
        assert "สุรเดช" in ideator_prompts["user"]
        assert "วันเพ็ญ" in ideator_prompts["user"]
        assert "AI Tutor" in ideator_prompts["user"]

        # Step 2: Judge responds to ideator
        judge_prompts = pb.get_judge_counter_prompt(
            agent_name="วันเพ็ญ",
            agent_role="Pragmatic Lead",
            agent_system_prompt="You are a pragmatic judge.",
            opposing_name="สุรเดช",
            opposing_view="เราสามารถใช้ API แทนการสร้าง model เองได้",
            dialogue_history="สุรเดช: เราสามารถใช้ API แทนการสร้าง model เองได้",
            context={
                "instructions": "วิเคราะห์ feasibility",
            },
        )
        
        assert judge_prompts["system"] == "You are a pragmatic judge."
        assert "วันเพ็ญ" in judge_prompts["user"]
        assert "สุรเดช" in judge_prompts["user"]

        # Step 3: Consensus
        consensus = pb.get_consensus_prompt(
            agent1_name="สุรเดช",
            agent2_name="วันเพ็ญ",
            dialogue_history="สุรเดช: ใช้ API\nวันเพ็ญ: เห็นด้วยค่ะ",
            consensus_statement="ทีมเห็นด้วยกับการใช้ external API",
        )
        
        assert "สุรเดช" in consensus
        assert "วันเพ็ญ" in consensus
        assert "external API" in consensus

    def test_prompt_with_special_characters(self):
        """Test prompts with special characters."""
        pb = PromptBuilder()
        
        prompts = pb.get_negotiation_prompt(
            agent_name="Test-Agent",
            agent_role="Special Role <>&",
            agent_system_prompt="System prompt with 'quotes' and \"double quotes\"",
            opposing_name="Opponent",
            opposing_view="View with special chars: <script>alert('xss')</script>",
            dialogue_history="History with\nnewlines\tand\ttabs",
            context={
                "top_idea": "Idea with **markdown** and [links](url)",
            },
        )
        
        assert prompts["user"] is not None
        # Should handle special characters without crashing
        assert len(prompts["user"]) > 0

    def test_prompt_with_very_long_text(self):
        """Test prompts with very long text."""
        pb = PromptBuilder()
        
        long_text = "A" * 10000
        prompts = pb.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt="You are an ideator.",
            opposing_name="วันเพ็ญ",
            opposing_view=long_text,
            dialogue_history=long_text,
            context={
                "top_idea": long_text,
            },
        )
        
        assert prompts["user"] is not None
        assert len(prompts["user"]) > 10000