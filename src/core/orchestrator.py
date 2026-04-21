"""
Orchestrator Module
Manages workflow transitions between layers, handles HITL pauses,
and implements the loop-back logic for code refinement.
"""

from typing import Any, Dict, Optional
from datetime import datetime

from loguru import logger

from src.core.state import SessionState, WorkflowLayer
from src.core.api_client import QwenAPIClient
from src.core.json_parser import StructuredOutputParser


class Orchestrator:
    """
    Central orchestrator for the hackathon workflow.
    Manages state transitions, agent coordination, and HITL checkpoints.
    """

    def __init__(self, api_client: QwenAPIClient):
        self.api_client = api_client
        self.parser = StructuredOutputParser()

        # Define valid transitions for each state
        self.transitions: Dict[WorkflowLayer, list] = {
            WorkflowLayer.IDLE: [WorkflowLayer.IDEATION],
            WorkflowLayer.IDEATION: [WorkflowLayer.JUDGING],
            WorkflowLayer.JUDGING: [WorkflowLayer.HITL_1],
            WorkflowLayer.HITL_1: [WorkflowLayer.PLANNING],  # After human selects
            WorkflowLayer.PLANNING: [WorkflowLayer.ARCHITECTING],
            WorkflowLayer.ARCHITECTING: [WorkflowLayer.BUILDING],
            WorkflowLayer.BUILDING: [WorkflowLayer.CRITIQUING],
            WorkflowLayer.CRITIQUING: [WorkflowLayer.BUILDING, WorkflowLayer.HITL_2, WorkflowLayer.ARCHITECTING],
            WorkflowLayer.HITL_2: [WorkflowLayer.PITCHING],  # After human approves
            WorkflowLayer.PITCHING: [WorkflowLayer.COMPLETE],
            WorkflowLayer.COMPLETE: [],
            WorkflowLayer.ERROR: [WorkflowLayer.IDEATION, WorkflowLayer.PLANNING, WorkflowLayer.BUILDING],
        }

    def can_transition(self, state: SessionState, target: WorkflowLayer) -> bool:
        """Check if a transition is valid."""
        return target in self.transitions.get(state.current_layer, [])

    async def run_ideation(self, state: SessionState) -> SessionState:
        """Layer 1, Phase 1: Generate project ideas."""
        from src.agents.ideator import IdeatorAgent

        state.transition_to(WorkflowLayer.IDEATION)
        logger.info(f"Starting ideation for session {state.session_id}")

        try:
            agent = IdeatorAgent(self.api_client)
            result = await agent.generate_ideas(
                theme=state.theme,
                constraints=state.constraints,
            )

            # Store ideas in state
            state.ideas = result.ideas

            state.add_agent_message(
                agent="ideator",
                agent_name="Max",
                emoji="🧠",
                role="Creative Director",
                message=result.message,
            )

            # Move to judging
            state.transition_to(WorkflowLayer.JUDGING)
            return await self.run_judging(state)

        except Exception as e:
            logger.error(f"Ideation failed for session {state.session_id}: {e}")
            state.set_error(f"Ideation failed: {str(e)}")
            state.add_agent_message(
                agent="system",
                agent_name="System",
                emoji="❌",
                role="Error",
                message=f"Ideation failed: {str(e)}",
            )
            raise

    async def run_judging(self, state: SessionState) -> SessionState:
        """Layer 1, Phase 2: Evaluate and score ideas."""
        from src.agents.judge import JudgeAgent

        logger.info(f"Starting judging for session {state.session_id}")

        agent = JudgeAgent(self.api_client)
        result = await agent.evaluate_ideas(
            ideas=state.ideas,
            constraints=state.constraints,
        )

        # Store evaluations
        state.evaluations = result.evaluations

        state.add_agent_message(
            agent="judge",
            agent_name="Sarah",
            emoji="⚖️",
            role="Pragmatic Lead",
            message=f"Evaluated {len(result.evaluations)} ideas. Top pick: {result.ranking[0] if result.ranking else 'N/A'}",
        )

        # Pause for human selection (HITL 1)
        state.pause_for_hitl("Please review the scored ideas and select one to proceed.")
        state.transition_to(WorkflowLayer.HITL_1)
        return state

    async def handle_idea_selection(self, state: SessionState, idea_id: int, feedback: Optional[str] = None) -> SessionState:
        """Handle human selection at HITL 1."""
        if not state.is_paused or state.current_layer != WorkflowLayer.HITL_1:
            raise ValueError("Session is not waiting for idea selection")

        # Find and store selected idea
        selected = next((i for i in state.ideas if i.id == idea_id), None)
        if not selected:
            raise ValueError(f"Idea with id {idea_id} not found")

        state.selected_idea = selected
        state.user_feedback_1 = {"idea_id": idea_id, "feedback": feedback or ""}

        state.add_agent_message(
            agent="system",
            agent_name="System",
            emoji="⏸️",
            role="HITL",
            message=f"Human selected idea #{idea_id}: '{selected.title}'",
        )

        state.resume()
        return await self.run_planning(state)

    async def run_planning(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 1: Break down into milestones."""
        from src.agents.planner import PlannerAgent

        if not state.selected_idea:
            raise ValueError("No idea selected before planning")

        state.transition_to(WorkflowLayer.PLANNING)
        logger.info(f"Starting planning for session {state.session_id}")

        agent = PlannerAgent(self.api_client)
        result = await agent.create_milestones(
            title=state.selected_idea.title,
            description=state.selected_idea.description,
            key_features=state.selected_idea.key_features,
            constraints=state.constraints,
            tech_stack=state.selected_idea.tech_stack,
        )

        state.milestones = result.milestones

        state.add_agent_message(
            agent="planner",
            agent_name="Dave",
            emoji="📋",
            role="Project Manager",
            message=f"Created {len(result.milestones)} milestones. Total estimated: {result.total_hours}h",
        )

        return await self.run_architecting(state)

    async def run_architecting(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 2: Design technical architecture."""
        from src.agents.architect import ArchitectAgent

        state.transition_to(WorkflowLayer.ARCHITECTING)
        logger.info(f"Starting architecture for session {state.session_id}")

        agent = ArchitectAgent(self.api_client)
        result = await agent.design_architecture(
            title=state.selected_idea.title if state.selected_idea else "",
            description=state.selected_idea.description if state.selected_idea else "",
            key_features=state.selected_idea.key_features if state.selected_idea else [],
            constraints=state.constraints,
            tech_stack=state.selected_idea.tech_stack if state.selected_idea else [],
            milestones=state.milestones,
        )

        state.architecture = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result

        state.add_agent_message(
            agent="architect",
            agent_name="Luna",
            emoji="🏗️",
            role="Tech Lead",
            message="Architecture design complete!",
        )

        return await self.run_building(state)

    async def run_building(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 3: Generate code."""
        from src.agents.builder import BuilderAgent

        state.transition_to(WorkflowLayer.BUILDING)
        logger.info(f"Starting code generation for session {state.session_id}")

        agent = BuilderAgent(self.api_client)
        result = await agent.generate_code(
            title=state.selected_idea.title if state.selected_idea else "",
            architecture=state.architecture,
            files_list=[m.title for m in state.milestones],
            constraints=state.constraints,
        )

        # Store generated code files
        for file_data in result.code_files:
            state.code_artifacts[file_data["filepath"]] = {
                "content": file_data["content"],
                "description": file_data.get("description", ""),
            }

        state.add_agent_message(
            agent="builder",
            agent_name="Kai",
            emoji="🔨",
            role="Senior Developer",
            message=f"Generated {len(result.code_files)} files!",
        )

        return await self.run_critiquing(state)

    async def run_critiquing(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 4: Review code with Critic agent."""
        from src.agents.critic import CriticAgent

        state.transition_to(WorkflowLayer.CRITIQUING)
        logger.info(f"Starting code review for session {state.session_id}")

        agent = CriticAgent(self.api_client)
        result = await agent.review_code(
            code_artifacts=state.code_artifacts,
            requirements=f"Theme: {state.theme}, Constraints: {state.constraints}",
        )

        state.critic_report = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result

        if result.status == "approved":
            state.add_agent_message(
                agent="critic",
                agent_name="Rex",
                emoji="🔍",
                role="QA Lead",
                message="Code approved! No issues found.",
            )
            # Move to HITL 2 for human review
            state.pause_for_hitl("Code review passed. Please review the generated code.")
            state.transition_to(WorkflowLayer.HITL_2)
        else:
            state.add_agent_message(
                agent="critic",
                agent_name="Rex",
                emoji="🔍",
                role="QA Lead",
                message=f"Found {len(result.issues)} issues. Triggering refinement...",
            )

            # Check refinement limit
            state.refinement_count += 1
            if state.refinement_count >= state.max_refinements:
                state.add_agent_message(
                    agent="system",
                    agent_name="System",
                    emoji="⚠️",
                    role="System",
                    message="Max refinements reached. Proceeding to human review.",
                )
                state.pause_for_hitl("Max refinements reached. Please review the code.")
                state.transition_to(WorkflowLayer.HITL_2)
            else:
                # Loop back to building for refinement
                return await self.run_building(state)

        return state

    async def handle_code_review(self, state: SessionState, approved: bool, feedback: Optional[str] = None) -> SessionState:
        """Handle human review at HITL 2."""
        if not state.is_paused or state.current_layer != WorkflowLayer.HITL_2:
            raise ValueError("Session is not waiting for code review")

        if approved:
            state.add_agent_message(
                agent="system",
                agent_name="System",
                emoji="✅",
                role="HITL",
                message="Human approved the code!",
            )
        else:
            state.add_agent_message(
                agent="system",
                agent_name="System",
                emoji="❌",
                role="HITL",
                message=f"Human requested changes: {feedback or 'No feedback provided'}",
            )
            # Could loop back to building with feedback

        state.user_feedback_2 = {"approved": approved, "feedback": feedback or ""}
        state.resume()
        return await self.run_pitching(state)

    async def run_pitching(self, state: SessionState) -> SessionState:
        """Layer 3: Generate pitch materials."""
        from src.agents.pitch_strategist import PitchStrategistAgent
        from src.agents.slide_agent import SlideAgent
        from src.agents.script_agent import ScriptAgent

        state.transition_to(WorkflowLayer.PITCHING)
        logger.info(f"Starting pitch generation for session {state.session_id}")

        selected = state.selected_idea

        # Generate narrative
        pitch_agent = PitchStrategistAgent(self.api_client)
        narrative_result = await pitch_agent.create_narrative(
            title=selected.title if selected else "",
            description=selected.description if selected else "",
            key_features=selected.key_features if selected else [],
            target_users=selected.target_users if selected else "",
        )
        state.narrative = narrative_result

        state.add_agent_message(
            agent="pitch_strategist",
            agent_name="Nova",
            emoji="🎤",
            role="Storyteller",
            message="Narrative created!",
        )

        # Generate slides
        slide_agent = SlideAgent(self.api_client)
        slides_result = await slide_agent.create_slides(
            title=selected.title if selected else "",
            narrative=narrative_result,
        )
        state.slides = slides_result

        state.add_agent_message(
            agent="slide_agent",
            agent_name="Nova (Slides)",
            emoji="📊",
            role="Presentation Designer",
            message="Slide deck outline ready!",
        )

        # Generate script
        script_agent = ScriptAgent(self.api_client)
        script_result = await script_agent.create_script(
            title=selected.title if selected else "",
            slides=slides_result,
            narrative=narrative_result,
        )
        state.script = script_result

        state.add_agent_message(
            agent="script_agent",
            agent_name="Nova (Script)",
            emoji="🎙️",
            role="Speech Writer",
            message="Speaker script complete!",
        )

        state.transition_to(WorkflowLayer.COMPLETE)
        return state