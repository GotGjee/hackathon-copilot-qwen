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
from src.core.events import (
    emit_agent_thinking, emit_agent_message, 
    emit_phase_start, emit_phase_complete, emit_error
)


def _save_state(state: SessionState):
    """Save state to disk after each phase."""
    try:
        from src.services.state_manager import StateManager
        sm = StateManager()
        sm.save(state.session_id, state.to_dict())
    except Exception as e:
        logger.warning(f"Failed to save state: {e}")


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
        """Layer 1, Phase 1: Generate project ideas with dialogue."""
        from src.agents.ideator import IdeatorAgent

        state.transition_to(WorkflowLayer.IDEATION)
        logger.info(f"Starting ideation for session {state.session_id}")
        
        # Emit streaming events
        await emit_phase_start(state.session_id, "ideation", "🧠 สุรเดชกำลัง brainstorming ideas...")
        await emit_agent_thinking(
            state.session_id, "ideator", "สุรเดช", "🧠", "Creative Director",
            "Brainstorming creative concepts for your theme...", "ideation"
        )

        try:
            agent = IdeatorAgent(self.api_client)
            result = await agent.generate_ideas(
                theme=state.theme,
                constraints=state.constraints,
            )

            # Store ideas in state
            state.ideas = result.ideas

            # Max presents ideas with personality
            max_presentation = result.message
            await emit_agent_message(
                state.session_id, "ideator", "สุรเดช", "🧠", "Creative Director",
                max_presentation, "ideation", {"ideas_count": len(result.ideas)}
            )
            
            state.add_agent_message(
                agent="ideator",
                agent_name="สุรเดช",
                emoji="🧠",
                role="Creative Director",
                message=max_presentation,
            )

            # Show each idea from สุรเดช's perspective
            for idea in state.ideas:
                max_idea_msg = f"💡 **ความคิดที่ {idea.id}: {idea.title}**\n\n{idea.description}\n\n🛠️ Tech Stack: {', '.join(idea.tech_stack)}\n👥 สำหรับ: {idea.target_users}\n⭐ คะแนน innovation: {idea.innovation_score}/10"
                await emit_agent_message(
                    state.session_id, "ideator", "สุรเดช", "🧠", "Creative Director",
                    max_idea_msg, "ideation"
                )
                state.add_agent_message(
                    agent="ideator",
                    agent_name="สุรเดช",
                    emoji="🧠",
                    role="Creative Director",
                    message=max_idea_msg,
                )

            # สุรเดช's closing
            await emit_agent_message(
                state.session_id, "ideator", "สุรเดช", "🧠", "Creative Director",
                result.closing_message, "ideation"
            )
            state.add_agent_message(
                agent="ideator",
                agent_name="สุรเดช",
                emoji="🧠",
                role="Creative Director",
                message=result.closing_message,
            )

            # Move to judging (with dialogue)
            state.transition_to(WorkflowLayer.JUDGING)
            _save_state(state)
            return await self.run_judging_with_dialogue(state)

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

    async def run_judging_with_dialogue(self, state: SessionState) -> SessionState:
        """Layer 1, Phase 2: Evaluate and score ideas with NEGOTIATION dialogue between agents.
        
        COOL FEATURE: Uses PromptBuilder for dynamic prompt generation!
        Instead of hardcoding prompts, prompts are built from templates.
        """
        from src.agents.judge import JudgeAgent
        from src.agents.ideator import IdeatorAgent
        from src.core.dialogue import DialogueManager, DialogueHistory
        from src.core.prompt_builder import PromptBuilder

        logger.info(f"Starting NEGOTIATION dialogue for session {state.session_id}")
        
        # Initialize PromptBuilder (COOL!)
        prompt_builder = PromptBuilder()
        
        # Phase start
        await emit_phase_start(state.session_id, "judging", "⚖️ เริ่มต้นการ negotiate ระหว่างสุรเดชและวันเพ็ญ...")

        # === ROUND 1: วันเพ็ญ evaluates ===
        await emit_agent_thinking(
            state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
            "Analyzing feasibility and scoring each idea...", "judging"
        )

        judge_agent = JudgeAgent(self.api_client)
        result = await judge_agent.evaluate_ideas(
            ideas=state.ideas,
            constraints=state.constraints,
        )
        state.evaluations = result.evaluations

        # วันเพ็ญ presents evaluation
        wanphen_opening = f"⚖️ **วันเพ็ญ (Pragmatic Lead): เริ่มวิเคราะห์แล้วค่ะ**\n\n"
        wanphen_opening += f"พี่วิเคราะห์ไอเดียทั้งหมด {len(state.ideas)} ไอเดีย ตามเกณฑ์ 5 ด้าน:\n"
        wanphen_opening += f"• Feasibility (ความเป็นไปได้): 25%\n"
        wanphen_opening += f"• Impact (ผลกระทบ): 25%\n"
        wanphen_opening += f"• Technical Complexity: 20%\n"
        wanphen_opening += f"• Innovation: 15%\n"
        wanphen_opening += f"• Market Potential: 15%\n\n"
        wanphen_opening += f"มาดูผลการวิเคราะห์กันค่ะ..."
        
        await emit_agent_message(
            state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
            wanphen_opening, "judging"
        )
        state.add_agent_message(
            agent="judge", agent_name="วันเพ็ญ", emoji="⚖️", role="Pragmatic Lead",
            message=wanphen_opening,
        )

        # Day phen critiques each idea
        for evaluation in state.evaluations:
            critique_msg = f"📊 **วันเพ็ญวิเคราะห์: {evaluation.idea_title}**\n\n"
            critique_msg += f"📈 **คะแนนรวม:** {evaluation.total_score}/10\n"
            critique_msg += f"✅ **จุดแข็ง:**\n"
            for s in evaluation.strengths:
                critique_msg += f"• {s}\n"
            critique_msg += f"\n⚠️ **ความเสี่ยง:**\n"
            for r in evaluation.risks:
                critique_msg += f"• {r}\n"
            critique_msg += f"\n💬 **คำแนะนำ:** {evaluation.recommendation}"
            
            await emit_agent_message(
                state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
                critique_msg, "judging"
            )
            state.add_agent_message(
                agent="judge", agent_name="วันเพ็ญ", emoji="⚖️", role="Pragmatic Lead",
                message=critique_msg,
            )

        # วันเพ็ญ's ranking
        ranking_msg = f"🏆 **อันดับที่วันเพ็ญแนะนำ:**\n"
        for i, idea_id in enumerate(result.ranking, 1):
            idea = next((idea for idea in state.ideas if idea.id == idea_id), None)
            if idea:
                ranking_msg += f"{i}. {idea.title}"
                if i == 1:
                    ranking_msg += " ⭐ **แนะนำ!**"
                ranking_msg += "\n"
        
        await emit_agent_message(
            state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
            ranking_msg, "judging"
        )
        state.add_agent_message(
            agent="judge", agent_name="วันเพ็ญ", emoji="⚖️", role="Pragmatic Lead",
            message=ranking_msg,
        )

        # === NEGOTIATION: Start dialogue loop ===
        dialogue_manager = DialogueManager(max_turns=3)
        dialogue = dialogue_manager.start_dialogue(
            dialogue_id=f"negotiation_{state.session_id}",
            topic=f"Negotiating the best idea for: {state.theme}"
        )

        # === ROUND 2: สุรเดช responds to วันเพ็ญ's ranking ===
        await emit_phase_start(state.session_id, "judging", "🧠 สุรเดชตอบกลับวันเพ็ญ...")
        
        ideator_agent = IdeatorAgent(self.api_client)
        
        top_idea_id = result.ranking[0] if result.ranking else None
        top_idea = next((idea for idea in state.ideas if idea.id == top_idea_id), None) if top_idea_id else None
        
        await emit_agent_thinking(
            state.session_id, "ideator", "สุรเดช", "🧠", "Creative Director",
            "Responding to วันเพ็ญ's evaluation with negotiation...", "judging"
        )

        # COOL: Use PromptBuilder instead of hardcode!
        sudet_prompts = prompt_builder.get_negotiation_prompt(
            agent_name="สุรเดช",
            agent_role="Creative Director",
            agent_system_prompt=ideator_agent.prompt_template.get("system_prompt", ""),
            opposing_name="วันเพ็ญ",
            opposing_view=result.message,
            dialogue_history=dialogue.get_formatted_history() if dialogue.turns else "",
            context={
                "top_idea": top_idea.model_dump() if top_idea else "N/A",
                "instructions": (
                    "1. เห็นด้วยหรือไม่เห็นด้วย พร้อมเหตุผล\n"
                    "2. เสนอไอเดียที่ปรับปรุงตาม feedback วันเพ็ญ\n"
                    "3. ถ้า disagree ต้องอธิบายว่าทำไม และเสนอทางเลือก\n"
                    "4. ตอบเป็นภาษาไทย + English technical terms"
                ),
            },
        )

        sudet_response = await ideator_agent.api_client.chat_completion(
            messages=[
                {"role": "system", "content": sudet_prompts["system"]},
                {"role": "user", "content": sudet_prompts["user"]},
            ],
            model=ideator_agent.model,
            temperature=ideator_agent.temperature,
            max_tokens=ideator_agent.max_tokens,
        )

        # Add to dialogue
        dialogue.add_turn(
            agent_type="ideator", agent_name="สุรเดช", emoji="🧠",
            role="Creative Director", message=sudet_response
        )

        await emit_agent_message(
            state.session_id, "ideator", "สุรเดช", "🧠", "Creative Director",
            f"💬 **สุรเดชตอบกลับวันเพ็ญ:**\n\n{sudet_response}",
            "judging"
        )
        state.add_agent_message(
            agent="ideator", agent_name="สุรเดช", emoji="🧠", role="Creative Director",
            message=f"💬 **สุรเดชตอบกลับวันเพ็ญ:**\n\n{sudet_response}",
        )

        # === ROUND 3: วันเพ็ญ responds to สุรเดช ===
        await emit_phase_start(state.session_id, "judging", "⚖️ วันเพ็ญตอบกลับสุรเดช...")
        
        await emit_agent_thinking(
            state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
            "Responding to Sudet's counter-arguments...", "judging"
        )

        # COOL: Use PromptBuilder for judge counter too!
        wanphen_prompts = prompt_builder.get_judge_counter_prompt(
            agent_name="วันเพ็ญ",
            agent_role="Pragmatic Lead",
            agent_system_prompt=judge_agent.prompt_template.get("system_prompt", ""),
            opposing_name="สุรเดช",
            opposing_view=sudet_response,
            dialogue_history=dialogue.get_formatted_history(),
            context={
                "instructions": (
                    "1. รับฟังประเด็นที่สุรเดชเสนอ\n"
                    "2. เห็นด้วยหรือไม่เห็นด้วย พร้อมเหตุผลเชิงตรรกะ\n"
                    "3. ถ้า disagree ให้เสนอ alternative ที่ realistic\n"
                    "4. สรุปว่าไอเดียไหนควรไปต่อ และทำไม\n"
                    "5. ตอบเป็นภาษาไทย + English technical terms"
                ),
            },
        )

        wanphen_counter_response = await judge_agent.api_client.chat_completion(
            messages=[
                {"role": "system", "content": wanphen_prompts["system"]},
                {"role": "user", "content": wanphen_prompts["user"]},
            ],
            model=judge_agent.model,
            temperature=judge_agent.temperature,
            max_tokens=judge_agent.max_tokens,
        )

        # Add to dialogue
        dialogue.add_turn(
            agent_type="judge", agent_name="วันเพ็ญ", emoji="⚖️",
            role="Pragmatic Lead", message=wanphen_counter_response
        )

        await emit_agent_message(
            state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
            f"💬 **วันเพ็ญตอบกลับสุรเดช:**\n\n{wanphen_counter_response}",
            "judging"
        )
        state.add_agent_message(
            agent="judge", agent_name="วันเพ็ญ", emoji="⚖️", role="Pragmatic Lead",
            message=f"💬 **วันเพ็ญตอบกลับสุรเดช:**\n\n{wanphen_counter_response}",
        )

        # === ROUND 4: Final consensus ===
        await emit_phase_start(state.session_id, "judging", "🤝 หาฉันทามติร่วมกัน...")
        
        # COOL: Use PromptBuilder for consensus!
        consensus_statement = f"ทีมเห็นด้วยกับไอเดียที่วันเพ็ญแนะนำเป็นอันดับ 1"
        if top_idea:
            consensus_statement += f": **{top_idea.title}**"
        consensus_statement += f"\n\nโดยทั้งสองฝ่ายเห็นร่วมกันว่าสามารถพัฒนาเป็น MVP ได้ภายในเวลาที่กำหนด"

        consensus_msg = prompt_builder.get_consensus_prompt(
            agent1_name="สุรเดช",
            agent2_name="วันเพ็ญ",
            dialogue_history=dialogue.get_formatted_history(),
            consensus_statement=consensus_statement,
        )

        await emit_agent_message(
            state.session_id, "judge", "วันเพ็ญ", "⚖️", "Pragmatic Lead",
            f"🤝 **บทสรุปการ negotiate:**\n\n{consensus_msg}",
            "judging"
        )
        state.add_agent_message(
            agent="judge", agent_name="วันเพ็ญ", emoji="⚖️", role="Pragmatic Lead",
            message=f"🤝 **บทสรุปการ negotiate:**\n\n{consensus_msg}",
        )

        await emit_phase_complete(state.session_id, "judging")

        # Pause for human selection (HITL 1)
        state.pause_for_hitl("Agents have negotiated and reached consensus. Please review and select an idea.")
        state.transition_to(WorkflowLayer.HITL_1)
        _save_state(state)
        return state

    async def run_judging(self, state: SessionState) -> SessionState:
        """Layer 1, Phase 2: Evaluate and score ideas."""
        from src.agents.judge import JudgeAgent

        logger.info(f"Starting judging for session {state.session_id}")
        
        # Emit streaming events
        await emit_phase_start(state.session_id, "judging", "⚖️ Sarah is evaluating ideas...")
        await emit_agent_thinking(
            state.session_id, "judge", "Sarah", "⚖️", "Pragmatic Lead",
            "Analyzing feasibility and scoring each idea...", "judging"
        )

        agent = JudgeAgent(self.api_client)
        result = await agent.evaluate_ideas(
            ideas=state.ideas,
            constraints=state.constraints,
        )

        # Store evaluations
        state.evaluations = result.evaluations

        await emit_agent_message(
            state.session_id, "judge", "Sarah", "⚖️", "Pragmatic Lead",
            f"Evaluated {len(result.evaluations)} ideas. Top pick: {result.ranking[0] if result.ranking else 'N/A'}",
            "judging", {"ranking": result.ranking}
        )
        await emit_phase_complete(state.session_id, "judging")

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
        """Layer 2, Phase 1: Break down into milestones with dialogue."""
        from src.agents.planner import PlannerAgent

        if not state.selected_idea:
            raise ValueError("No idea selected before planning")

        state.transition_to(WorkflowLayer.PLANNING)
        logger.info(f"Starting planning for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "planning", "📋 สมศักดิ์กำลัง creating milestones...")
        
        # สมศักดิ์ thinking
        await emit_agent_thinking(
            state.session_id, "planner", "สมศักดิ์", "📋", "Project Manager",
            "Breaking down the project into manageable milestones...", "planning"
        )

        agent = PlannerAgent(self.api_client)
        result = await agent.create_milestones(
            title=state.selected_idea.title,
            description=state.selected_idea.description,
            key_features=state.selected_idea.key_features,
            constraints=state.constraints,
            tech_stack=state.selected_idea.tech_stack,
        )

        state.milestones = result.milestones

        # สมศักดิ์ presents milestones
        dave_msg = f"📋 **สมศักดิ์ (PM): ออกแบบ Milestones เรียบร้อย!**\n\n"
        dave_msg += f"ผมแบ่งโปรเจกต์ **{state.selected_idea.title}** ออกเป็น {len(result.milestones)} milestones:\n\n"
        for i, m in enumerate(result.milestones, 1):
            dave_msg += f"{i}. **{m.title}** - {m.description} ({m.estimated_hours}h)\n"
        dave_msg += f"\n⏱️ **เวลารวมโดยประมาณ:** {result.total_hours} ชั่วโมง"
        
        await emit_agent_message(
            state.session_id, "planner", "สมศักดิ์", "📋", "Project Manager",
            dave_msg, "planning"
        )
        state.add_agent_message(
            agent="planner",
            agent_name="สมศักดิ์",
            emoji="📋",
            role="Project Manager",
            message=dave_msg,
        )

        # พิมพ์ใจ responds to สมศักดิ์'s plan
        await emit_agent_thinking(
            state.session_id, "architect", "พิมพ์ใจ", "🏗️", "Tech Lead",
            "Reviewing the milestones and preparing architecture...", "planning"
        )
        
        luna_response = f"💬 **พิมพ์ใจตอบกลับสมศักดิ์:**\n\n"
        luna_response += f"แผนงานดีมากค่ะสมศักดิ์! พี่เห็นว่า milestones ครอบคลุมทุกด้าน\n"
        luna_response += f"พี่จะออกแบบ architecture ให้รองรับฟีเจอร์ทั้งหมด\n"
        luna_response += f"จากนั้นจะส่งต่อให้ธนภัทรพัฒนาต่อทันที!"
        
        await emit_agent_message(
            state.session_id, "architect", "พิมพ์ใจ", "🏗️", "Tech Lead",
            luna_response, "planning"
        )
        state.add_agent_message(
            agent="architect",
            agent_name="พิมพ์ใจ",
            emoji="🏗️",
            role="Tech Lead",
            message=luna_response,
        )

        await emit_phase_complete(state.session_id, "planning")
        _save_state(state)

        return await self.run_architecting(state)

    async def run_architecting(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 2: Design technical architecture with dialogue."""
        from src.agents.architect import ArchitectAgent

        state.transition_to(WorkflowLayer.ARCHITECTING)
        logger.info(f"Starting architecture for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "architecting", "🏗️ พิมพ์ใจกำลัง designing the architecture...")
        
        # พิมพ์ใจ thinking
        await emit_agent_thinking(
            state.session_id, "architect", "พิมพ์ใจ", "🏗️", "Tech Lead",
            "Designing the system architecture and file structure...", "architecting"
        )

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

        # พิมพ์ใจ presents architecture
        luna_msg = f"🏗️ **พิมพ์ใจ (Tech Lead): ออกแบบ Architecture เรียบร้อย!**\n\n"
        luna_msg += f"พี่ออกแบบระบบสำหรับ **{state.selected_idea.title if state.selected_idea else 'N/A'}**\n\n"
        luna_msg += f"📁 **โครงสร้างโปรเจกต์:**\n"
        for f in list(result.file_structure.keys())[:10]:
            luna_msg += f"  {f}\n"
        luna_msg += f"\n🏛️ **Design Decisions:**\n"
        for d in result.design_decisions[:3]:
            luna_msg += f"• {d}\n"
        luna_msg += f"\n🔌 **APIs:** {len(result.api_endpoints)} endpoints"
        luna_msg += f"\n📦 **Tech Stack:** {', '.join([t.get('name', str(t)) for t in result.tech_stack[:5]])}"
        if result.data_models:
            luna_msg += f"\n📊 **Data Models:** {', '.join([m.get('name', str(m)) for m in result.data_models[:3]])}"
        luna_msg += f"\n\nพร้อมส่งต่อให้ธนภัทรพัฒนาแล้วค่ะ!"
        
        await emit_agent_message(
            state.session_id, "architect", "พิมพ์ใจ", "🏗️", "Tech Lead",
            luna_msg, "architecting"
        )
        state.add_agent_message(
            agent="architect",
            agent_name="พิมพ์ใจ",
            emoji="🏗️",
            role="Tech Lead",
            message=luna_msg,
        )

        # ธนภัทร responds to พิมพ์ใจ
        await emit_agent_thinking(
            state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
            "Responding to พิมพ์ใจ's architecture...", "architecting"
        )
        
        kai_response = f"💬 **ธนภัทรตอบกลับพิมพ์ใจ:**\n\n"
        kai_response += f"ออกแบบได้เยี่ยมมากครับพิมพ์ใจ! ผมชอบ design pattern ที่เลือกใช้\n"
        kai_response += f"โครงสร้างชัดเจน เข้าใจง่าย ผมพร้อมเริ่มเขียนโค้ดแล้ว!\n"
        kai_response += f"ขอเวลาสักครู่นะครับ แล้วจะส่งให้วิชัยตรวจสอบต่อไป!"
        
        await emit_agent_message(
            state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
            kai_response, "architecting"
        )
        state.add_agent_message(
            agent="builder",
            agent_name="ธนภัทร",
            emoji="🔨",
            role="Senior Developer",
            message=kai_response,
        )

        await emit_phase_complete(state.session_id, "architecting")
        _save_state(state)

        return await self.run_building(state)

    async def run_building(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 3: Generate code with dialogue."""
        from src.agents.builder import BuilderAgent

        state.transition_to(WorkflowLayer.BUILDING)
        logger.info(f"Starting code generation for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "building", "🔨 ธนภัทรกำลัง writing the code...")
        
        # ธนภัทร thinking
        await emit_agent_thinking(
            state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
            "Generating code files based on the architecture...", "building"
        )

        agent = BuilderAgent(self.api_client)
        result = await agent.generate_code(
            title=state.selected_idea.title if state.selected_idea else "",
            architecture=state.architecture,
            files_list=[m.title for m in state.milestones],
            constraints=state.constraints + "\n\nIMPORTANT: Generate SKELETON code with TODO comments, not complete implementations. Create ALL necessary files based on the architecture. No file limit - include README.md for participants.",
        )

        # Store generated code files
        from src.core.state import CodeFile
        for file_data in result.code_files:
            state.code_artifacts[file_data.filepath] = CodeFile(
                filepath=file_data.filepath,
                description=file_data.description,
                content=file_data.content,
                language=file_data.language,
            )

        # ธนภัทร presents his work
        kai_msg = f"🔨 **ธนภัทร (Developer): สร้าง Skeleton Code เรียบร้อย!**\n\n"
        kai_msg += f"ผมสร้างโครงโปรเจกต์ **{state.selected_idea.title if state.selected_idea else 'N/A'}** เรียบร้อย\n\n"
        kai_msg += f"📁 **ไฟล์ที่สร้าง:** {len(result.code_files)} ไฟล์\n\n"
        kai_msg += f"📄 **ไฟล์สำคัญ:**\n"
        for f in result.code_files[:8]:
            kai_msg += f"• `{f.filepath}`\n"
        kai_msg += f"\n✅ **Tech stack:** {', '.join(state.selected_idea.tech_stack if state.selected_idea else [])}\n"
        kai_msg += f"\nผมสร้าง **skeleton code** พร้อม TODO comments ให้แล้ว\n"
        kai_msg += f"คุณสามารถเริ่มพัฒนาต่อได้ทันที โดยดู TODO ในแต่ละไฟล์\n"
        kai_msg += f"พร้อมส่งให้วิชัยทำ code review แล้วครับ!"
        
        await emit_agent_message(
            state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
            kai_msg, "building"
        )
        state.add_agent_message(
            agent="builder",
            agent_name="ธนภัทร",
            emoji="🔨",
            role="Senior Developer",
            message=kai_msg,
        )

        await emit_phase_complete(state.session_id, "building")
        _save_state(state)

        return await self.run_critiquing(state)

    async def run_critiquing(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 4: Review code with Critic agent and dialogue."""
        from src.agents.critic import CriticAgent

        state.transition_to(WorkflowLayer.CRITIQUING)
        logger.info(f"Starting code review for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "critiquing", "🔍 วิชัยกำลัง reviewing the code...")
        
        # วิชัย thinking
        await emit_agent_thinking(
            state.session_id, "critic", "วิชัย", "🔍", "QA Lead",
            "Analyzing code quality, security, and best practices...", "critiquing"
        )

        agent = CriticAgent(self.api_client)
        result = await agent.review_code(
            code_artifacts=state.code_artifacts,
            requirements=f"Theme: {state.theme}, Constraints: {state.constraints}",
        )

        state.critic_report = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result

        if result.status == "approved":
            # วิชัย presents approval with details
            rex_msg = f"✅ **วิชัย: Skeleton Code Review Approved!**\n\n"
            rex_msg += f"โครง skeleton ผ่านการตรวจสอบแล้ว! ไม่มีปัญหาสำคัญ\n"
            rex_msg += f"\n📊 **คะแนนคุณภาพ:** ผ่านมาตรฐาน"
            if result.issues:
                rex_msg += f"\n\n💡 **ข้อเสนอแนะเพิ่มเติม:**\n"
                for issue in result.issues[:3]:
                    rex_msg += f"• {issue}\n"
            
            await emit_agent_message(
                state.session_id, "critic", "วิชัย", "🔍", "QA Lead",
                rex_msg, "critiquing"
            )
            state.add_agent_message(
                agent="critic",
                agent_name="วิชัย",
                emoji="🔍",
                role="QA Lead",
                message=rex_msg,
            )

            # ธนภัทร responds to approval
            await emit_agent_thinking(
                state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
                "Responding to วิชัย's review...", "critiquing"
            )
            
            kai_response = f"💬 **ธนภัทรตอบกลับวิชัย:**\n\n"
            kai_response += f"ขอบคุณที่ตรวจสอบครับวิชัย! ผมดีใจที่โค้ดผ่าน QA\n"
            kai_response += f"ผมเขียนโค้ดโดยคำนึงถึง best practices และ clean code\n"
            kai_response += f"ถ้ามีข้อเสนอแนะเพิ่มเติม ผมพร้อมนำไปปรับปรุงครับ!"
            
            await emit_agent_message(
                state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
                kai_response, "critiquing"
            )
            state.add_agent_message(
                agent="builder",
                agent_name="ธนภัทร",
                emoji="🔨",
                role="Senior Developer",
                message=kai_response,
            )

            await emit_phase_complete(state.session_id, "critiquing")
            
            # Move to HITL 2 for human review
            state.pause_for_hitl("Code review passed. Please review the generated code.")
            state.transition_to(WorkflowLayer.HITL_2)
            _save_state(state)
        else:
            # วิชัย presents issues with details
            rex_msg = f"❌ **วิชัย: พบปัญหา {len(result.issues)} จุดใน Skeleton**\n\n"
            rex_msg += f"🔴 **ปัญหาที่พบ:**\n"
            for i, issue in enumerate(result.issues[:5], 1):
                rex_msg += f"{i}. {issue}\n"
            rex_msg += f"\n⚠️ ผมแนะนำให้กลับไปแก้ skeleton ครับธนภัทร"
            
            await emit_agent_message(
                state.session_id, "critic", "วิชัย", "🔍", "QA Lead",
                rex_msg, "critiquing"
            )
            state.add_agent_message(
                agent="critic",
                agent_name="วิชัย",
                emoji="🔍",
                role="QA Lead",
                message=rex_msg,
            )

            # ธนภัทร responds to criticism
            await emit_agent_thinking(
                state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
                "Responding to วิชัย's critique...", "critiquing"
            )
            
            kai_response = f"💬 **ธนภัทรตอบกลับวิชัย:**\n\n"
            kai_response += f"รับทราบครับวิชัย! ขอบคุณที่ชี้มา ผมจะกลับไปแก้ไขประเด็นที่พบ\n"
            if result.issues:
                kai_response += f"\nผมจะจัดการปัญหาเหล่านี้:\n"
                for issue in result.issues[:3]:
                    kai_response += f"• {issue}\n"
            kai_response += f"\nผมจะรีบแก้ไขและส่งให้ตรวจสอบอีกครั้งครับ!"
            
            await emit_agent_message(
                state.session_id, "builder", "ธนภัทร", "🔨", "Senior Developer",
                kai_response, "critiquing"
            )
            state.add_agent_message(
                agent="builder",
                agent_name="ธนภัทร",
                emoji="🔨",
                role="Senior Developer",
                message=kai_response,
            )

            # Check refinement limit
            state.refinement_count += 1
            if state.refinement_count >= state.max_refinements:
                await emit_agent_message(
                    state.session_id, "system", "System", "⚠️", "System",
                    "Max refinements reached. Proceeding to human review.", "critiquing"
                )
                
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
                await emit_agent_message(
                    state.session_id, "system", "System", "🔄", "System",
                    f"Refinement cycle {state.refinement_count}/{state.max_refinements}. Rebuilding...", "critiquing"
                )
                return await self.run_building(state)

        return state

    async def handle_code_review(self, state: SessionState, approved: bool, feedback: Optional[str] = None) -> SessionState:
        """Handle human review at HITL 2."""
        if not state.is_paused or state.current_layer != WorkflowLayer.HITL_2:
            raise ValueError("Session is not waiting for code review")

        if approved:
            # Confirmation message handled in frontend for proper ordering in chat
            pass
        else:
            state.add_agent_message(
                agent="system",
                agent_name="System",
                emoji="❌",
                role="HITL",
                message=f"Human requested changes: {feedback}",
            )
            # Could loop back to building with feedback

        state.user_feedback_2 = {"approved": approved, "feedback": feedback or ""}
        state.resume()
        result = await self.run_pitching(state)
        _save_state(result)
        return result

    async def run_pitching(self, state: SessionState) -> SessionState:
        """Layer 3: Generate pitch materials with dialogue."""
        from src.agents.pitch_strategist import PitchStrategistAgent
        from src.agents.slide_agent import SlideAgent
        from src.agents.script_agent import ScriptAgent

        state.transition_to(WorkflowLayer.PITCHING)
        logger.info(f"Starting pitch generation for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "pitching", "🎤 อรุณีกำลัง preparing the pitch...")

        selected = state.selected_idea

        # Step 1: อรุณี (Storyteller) creates narrative
        await emit_agent_thinking(
            state.session_id, "pitch_strategist", "อรุณี", "🎤", "Storyteller",
            "Crafting the perfect narrative for your project...", "pitching"
        )
        pitch_agent = PitchStrategistAgent(self.api_client)
        narrative_result = await pitch_agent.create_narrative(
            title=selected.title if selected else "",
            description=selected.description if selected else "",
            key_features=selected.key_features if selected else [],
            target_users=selected.target_users if selected else "",
        )
        state.narrative = narrative_result

        # อรุณี presents narrative
        nova_narrative_msg = f"🎤 **อรุณี (Storyteller): สร้างเรื่องเล่าเรียบร้อยแล้ว!**\n\n"
        nova_narrative_msg += f"พี่ได้ออกแบบ story สำหรับโปรเจกต์ **{selected.title if selected else 'N/A'}**\n"
        nova_narrative_msg += f"โดยเน้นสร้าง emotional impact และ clear value proposition\n"
        nova_narrative_msg += f"พร้อมส่งต่อให้ทีมทำ slides แล้วค่ะ!"
        
        await emit_agent_message(
            state.session_id, "pitch_strategist", "อรุณี", "🎤", "Storyteller",
            nova_narrative_msg, "pitching"
        )
        state.add_agent_message(
            agent="pitch_strategist",
            agent_name="อรุณี",
            emoji="🎤",
            role="Storyteller",
            message=nova_narrative_msg,
        )

        # Step 2: อรุณี (Slides) responds to อรุณี (Storyteller)
        await emit_agent_thinking(
            state.session_id, "slide_agent", "อรุณี (Slides)", "📊", "Presentation Designer",
            "Designing the slide deck layout based on อรุณี's narrative...", "pitching"
        )
        slide_agent = SlideAgent(self.api_client)
        slides_result = await slide_agent.create_slides(
            title=selected.title if selected else "",
            narrative=narrative_result,
        )
        state.slides = slides_result.slides

        # Slides อรุณี responds to Storyteller อรุณี
        slides_nova_msg = f"💬 **อรุณี (Slides) ตอบกลับอรุณี (Storyteller):**\n\n"
        slides_nova_msg += f"เรื่องเล่าเยี่ยมมากค่ะ! พี่ออกแบบ slide deck ให้แล้ว {len(slides_result.slides)} slides\n"
        if slides_result.color_palette:
            slides_nova_msg += f"🎨 Color theme: Primary {slides_result.color_palette.primary_color}\n"
        if slides_result.font_style:
            slides_nova_msg += f"📝 Font: {slides_result.font_style.title_font} + {slides_result.font_style.body_font}\n"
        slides_nova_msg += f"แต่ละ slide ถูกจัด layout ให้สวยงามและสื่อสารได้ชัดเจน\n"
        slides_nova_msg += f"พร้อมส่งต่อให้ Speech Writer แล้วค่ะ!"
        
        await emit_agent_message(
            state.session_id, "slide_agent", "อรุณี (Slides)", "📊", "Presentation Designer",
            slides_nova_msg, "pitching"
        )
        state.add_agent_message(
            agent="slide_agent",
            agent_name="อรุณี (Slides)",
            emoji="📊",
            role="Presentation Designer",
            message=slides_nova_msg,
        )

        # Step 3: อรุณี (Script) responds to both
        await emit_agent_thinking(
            state.session_id, "script_agent", "อรุณี (Script)", "🎙️", "Speech Writer",
            "Writing the speaker script based on slides and narrative...", "pitching"
        )
        script_agent = ScriptAgent(self.api_client)
        script_result = await script_agent.create_script(
            title=selected.title if selected else "",
            slides=slides_result.slides,
            narrative=narrative_result,
        )
        state.script = script_result

        # Script อรุณี responds
        script_sections = script_result if isinstance(script_result, list) else (script_result.sections if hasattr(script_result, 'sections') else [])
        script_nova_msg = f"💬 **อรุณี (Script) ตอบกลับทีม:**\n\n"
        script_nova_msg += f"ได้รับ slides และ narrative แล้วค่ะ! พี่เขียน speaker script ให้แล้ว {len(script_sections)} sections\n"
        script_nova_msg += f"script ถูกออกแบบให้กระชับ น่าสนใจ และ fit กับเวลา pitch\n"
        script_nova_msg += f"**ทีมอรุณีพร้อมแล้วค่ะ! ขอให้ pitch ออกมาดีที่สุด!** 🎤"
        
        await emit_agent_message(
            state.session_id, "script_agent", "อรุณี (Script)", "🎙️", "Speech Writer",
            script_nova_msg, "pitching"
        )
        state.add_agent_message(
            agent="script_agent",
            agent_name="อรุณี (Script)",
            emoji="🎙️",
            role="Speech Writer",
            message=script_nova_msg,
        )

        # Final: All อรุณี wrap up
        wrapup_msg = f"🎉 **ทีมอรุณี เสร็จสมบูรณ์!**\n\n"
        wrapup_msg += f"✅ Storyteller: สร้าง narrative\n"
        wrapup_msg += f"✅ Presentation Designer: ออกแบบ slides\n"
        wrapup_msg += f"✅ Speech Writer: เขียน script\n\n"
        wrapup_msg += f"พร้อม pitch แล้ว! ลุยเลยทีม! 🚀"
        
        await emit_agent_message(
            state.session_id, "pitch_strategist", "อรุณี", "🎤", "Storyteller",
            wrapup_msg, "pitching"
        )
        state.add_agent_message(
            agent="pitch_strategist",
            agent_name="อรุณี",
            emoji="🎤",
            role="Storyteller",
            message=wrapup_msg,
        )

        await emit_phase_complete(state.session_id, "pitching")

        state.transition_to(WorkflowLayer.COMPLETE)
        _save_state(state)
        return state
