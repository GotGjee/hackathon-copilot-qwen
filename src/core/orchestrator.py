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
        await emit_phase_start(state.session_id, "ideation", "🧠 Max is brainstorming ideas...")
        await emit_agent_thinking(
            state.session_id, "ideator", "Max", "🧠", "Creative Director",
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
                state.session_id, "ideator", "Max", "🧠", "Creative Director",
                max_presentation, "ideation", {"ideas_count": len(result.ideas)}
            )
            
            state.add_agent_message(
                agent="ideator",
                agent_name="Max",
                emoji="🧠",
                role="Creative Director",
                message=max_presentation,
            )

            # Show each idea from Max's perspective
            for idea in state.ideas:
                max_idea_msg = f"💡 **ความคิดที่ {idea.id}: {idea.title}**\n\n{idea.description}\n\n🛠️ Tech Stack: {', '.join(idea.tech_stack)}\n👥 สำหรับ: {idea.target_users}\n⭐ คะแนน innovation: {idea.innovation_score}/10"
                await emit_agent_message(
                    state.session_id, "ideator", "Max", "🧠", "Creative Director",
                    max_idea_msg, "ideation"
                )
                state.add_agent_message(
                    agent="ideator",
                    agent_name="Max",
                    emoji="🧠",
                    role="Creative Director",
                    message=max_idea_msg,
                )

            # Max's closing
            await emit_agent_message(
                state.session_id, "ideator", "Max", "🧠", "Creative Director",
                result.closing_message, "ideation"
            )
            state.add_agent_message(
                agent="ideator",
                agent_name="Max",
                emoji="🧠",
                role="Creative Director",
                message=result.closing_message,
            )

            # Move to judging (with dialogue)
            state.transition_to(WorkflowLayer.JUDGING)
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
        """Layer 1, Phase 2: Evaluate and score ideas with dialogue between Max and Sarah."""
        from src.agents.judge import JudgeAgent

        logger.info(f"Starting judging with dialogue for session {state.session_id}")
        
        # Phase start
        await emit_phase_start(state.session_id, "judging", "⚖️ Sarah is evaluating ideas...")
        
        # Step 1: Sarah thinking
        await emit_agent_thinking(
            state.session_id, "judge", "Sarah", "⚖️", "Pragmatic Lead",
            "Analyzing feasibility and scoring each idea...", "judging"
        )

        # Step 2: Sarah evaluates
        agent = JudgeAgent(self.api_client)
        result = await agent.evaluate_ideas(
            ideas=state.ideas,
            constraints=state.constraints,
        )

        # Store evaluations
        state.evaluations = result.evaluations

        # Step 3: Sarah presents her evaluation with dialogue
        sarah_opening = result.message
        await emit_agent_message(
            state.session_id, "judge", "Sarah", "⚖️", "Pragmatic Lead",
            sarah_opening, "judging"
        )
        state.add_agent_message(
            agent="judge",
            agent_name="Sarah",
            emoji="⚖️",
            role="Pragmatic Lead",
            message=sarah_opening,
        )

        # Step 4: Sarah critiques each idea
        for evaluation in state.evaluations:
            critique_msg = f"📊 **วิจารณ์ของ Sarah สำหรับ: {evaluation.idea_title}**\n\n"
            critique_msg += f"✅ **จุดแข็ง:**\n"
            for s in evaluation.strengths:
                critique_msg += f"• {s}\n"
            critique_msg += f"\n⚠️ **ความเสี่ยง:**\n"
            for r in evaluation.risks:
                critique_msg += f"• {r}\n"
            critique_msg += f"\n📈 **คะแนนรวม:** {evaluation.total_score}/10\n"
            critique_msg += f"💬 **คำแนะนำ:** {evaluation.recommendation}"
            
            await emit_agent_message(
                state.session_id, "judge", "Sarah", "⚖️", "Pragmatic Lead",
                critique_msg, "judging"
            )
            state.add_agent_message(
                agent="judge",
                agent_name="Sarah",
                emoji="⚖️",
                role="Pragmatic Lead",
                message=critique_msg,
            )

        # Step 5: Sarah's ranking
        ranking_msg = f"🏆 **การจัดอันดับของ Sarah:**\n"
        for i, idea_id in enumerate(result.ranking, 1):
            idea = next((idea for idea in state.ideas if idea.id == idea_id), None)
            if idea:
                ranking_msg += f"{i}. {idea.title}\n"
        
        await emit_agent_message(
            state.session_id, "judge", "Sarah", "⚖️", "Pragmatic Lead",
            ranking_msg, "judging"
        )
        state.add_agent_message(
            agent="judge",
            agent_name="Sarah",
            emoji="⚖️",
            role="Pragmatic Lead",
            message=ranking_msg,
        )

        # Step 6: Max responds to Sarah's critique
        await emit_agent_thinking(
            state.session_id, "ideator", "Max", "🧠", "Creative Director",
            "Responding to Sarah's evaluation...", "judging"
        )
        
        max_response = f"💬 **Max ตอบกลับ Sarah:**\n\n"
        max_response += f"Sarah วิเคราะห์ได้เฉียบขาดมาก! ผมเห็นด้วยกับประเด็นเรื่องความเสี่ยง\n\n"
        
        # Add Max's defense for top idea
        top_idea_id = result.ranking[0] if result.ranking else None
        if top_idea_id:
            top_idea = next((idea for idea in state.ideas if idea.id == top_idea_id), None)
            if top_idea:
                max_response += f"สำหรับ **{top_idea.title}** ผมคิดว่าเราสามารถจัดการความเสี่ยงได้โดย:\n"
                max_response += f"• ใช้ MVP scope ที่เล็กที่สุด\n"
                max_response += f"• โฟกัสที่ core feature ก่อน\n\n"
        
        max_response += f"ขอให้ทีมช่วยพิจารณาไอเดียที่ Sarah แนะนำเป็นอันดับแรกนะครับ!"
        
        await emit_agent_message(
            state.session_id, "ideator", "Max", "🧠", "Creative Director",
            max_response, "judging"
        )
        state.add_agent_message(
            agent="ideator",
            agent_name="Max",
            emoji="🧠",
            role="Creative Director",
            message=max_response,
        )

        await emit_phase_complete(state.session_id, "judging")

        # Pause for human selection (HITL 1)
        state.pause_for_hitl("Please review the scored ideas and select one to proceed.")
        state.transition_to(WorkflowLayer.HITL_1)
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
        
        await emit_phase_start(state.session_id, "planning", "📋 Dave is creating milestones...")
        
        # Dave thinking
        await emit_agent_thinking(
            state.session_id, "planner", "Dave", "📋", "Project Manager",
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

        # Dave presents milestones
        dave_msg = f"📋 **Dave (PM): ออกแบบ Milestones เรียบร้อย!**\n\n"
        dave_msg += f"ผมแบ่งโปรเจกต์ **{state.selected_idea.title}** ออกเป็น {len(result.milestones)} milestones:\n\n"
        for i, m in enumerate(result.milestones, 1):
            dave_msg += f"{i}. **{m.title}** - {m.description} ({m.estimated_hours}h)\n"
        dave_msg += f"\n⏱️ **เวลารวมโดยประมาณ:** {result.total_hours} ชั่วโมง"
        
        await emit_agent_message(
            state.session_id, "planner", "Dave", "📋", "Project Manager",
            dave_msg, "planning"
        )
        state.add_agent_message(
            agent="planner",
            agent_name="Dave",
            emoji="📋",
            role="Project Manager",
            message=dave_msg,
        )

        # Luna responds to Dave's plan
        await emit_agent_thinking(
            state.session_id, "architect", "Luna", "🏗️", "Tech Lead",
            "Reviewing the milestones and preparing architecture...", "planning"
        )
        
        luna_response = f"💬 **Luna ตอบกลับ Dave:**\n\n"
        luna_response += f"แผนงานดีมากครับ Dave! ผมเห็นว่า milestones ครอบคลุมทุกด้าน\n"
        luna_response += f"ผมจะออกแบบ architecture ให้รองรับฟีเจอร์ทั้งหมด\n"
        luna_response += f"จากนั้นจะส่งต่อให้ Kai พัฒนาต่อทันที!"
        
        await emit_agent_message(
            state.session_id, "architect", "Luna", "🏗️", "Tech Lead",
            luna_response, "planning"
        )
        state.add_agent_message(
            agent="architect",
            agent_name="Luna",
            emoji="🏗️",
            role="Tech Lead",
            message=luna_response,
        )

        await emit_phase_complete(state.session_id, "planning")

        return await self.run_architecting(state)

    async def run_architecting(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 2: Design technical architecture with dialogue."""
        from src.agents.architect import ArchitectAgent

        state.transition_to(WorkflowLayer.ARCHITECTING)
        logger.info(f"Starting architecture for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "architecting", "🏗️ Luna is designing the architecture...")
        
        # Luna thinking
        await emit_agent_thinking(
            state.session_id, "architect", "Luna", "🏗️", "Tech Lead",
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

        # Luna presents architecture
        luna_msg = f"🏗️ **Luna (Tech Lead): ออกแบบ Architecture เรียบร้อย!**\n\n"
        luna_msg += f"ผมออกแบบระบบสำหรับ **{state.selected_idea.title if state.selected_idea else 'N/A'}**\n\n"
        luna_msg += f"📁 **โครงสร้างโปรเจกต์:**\n"
        for f in list(result.file_structure.keys())[:10]:
            luna_msg += f"  {f}\n"
        luna_msg += f"\n🏛️ **รูปแบบ:** {result.design_pattern}"
        luna_msg += f"\n📊 **Database:** {result.database_schema}"
        luna_msg += f"\n🔌 **APIs:** {len(result.api_endpoints)} endpoints"
        luna_msg += f"\n📦 **Dependencies:** {', '.join(result.dependencies[:5])}"
        luna_msg += f"\n\nพร้อมส่งต่อให้ Kai พัฒนาแล้วครับ!"
        
        await emit_agent_message(
            state.session_id, "architect", "Luna", "🏗️", "Tech Lead",
            luna_msg, "architecting"
        )
        state.add_agent_message(
            agent="architect",
            agent_name="Luna",
            emoji="🏗️",
            role="Tech Lead",
            message=luna_msg,
        )

        # Kai responds to Luna
        await emit_agent_thinking(
            state.session_id, "builder", "Kai", "🔨", "Senior Developer",
            "Responding to Luna's architecture...", "architecting"
        )
        
        kai_response = f"💬 **Kai ตอบกลับ Luna:**\n\n"
        kai_response += f"ออกแบบได้เยี่ยมมากครับ Luna! ผมชอบ design pattern ที่เลือกใช้\n"
        kai_response += f"โครงสร้างชัดเจน เข้าใจง่าย ผมพร้อมเริ่มเขียนโค้ดแล้ว!\n"
        kai_response += f"ขอเวลาสักครู่นะครับ แล้วจะส่งให้ Rex ตรวจสอบต่อไป!"
        
        await emit_agent_message(
            state.session_id, "builder", "Kai", "🔨", "Senior Developer",
            kai_response, "architecting"
        )
        state.add_agent_message(
            agent="builder",
            agent_name="Kai",
            emoji="🔨",
            role="Senior Developer",
            message=kai_response,
        )

        await emit_phase_complete(state.session_id, "architecting")

        return await self.run_building(state)

    async def run_building(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 3: Generate code with dialogue."""
        from src.agents.builder import BuilderAgent

        state.transition_to(WorkflowLayer.BUILDING)
        logger.info(f"Starting code generation for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "building", "🔨 Kai is writing the code...")
        
        # Kai thinking
        await emit_agent_thinking(
            state.session_id, "builder", "Kai", "🔨", "Senior Developer",
            "Generating code files based on the architecture...", "building"
        )

        agent = BuilderAgent(self.api_client)
        result = await agent.generate_code(
            title=state.selected_idea.title if state.selected_idea else "",
            architecture=state.architecture,
            files_list=[m.title for m in state.milestones],
            constraints=state.constraints,
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

        # Kai presents his work
        kai_msg = f"🔨 **Kai (Developer): เขียนโค้ดเสร็จแล้ว!**\n\n"
        kai_msg += f"ผมสร้างโปรเจกต์ **{state.selected_idea.title if state.selected_idea else 'N/A'}** เรียบร้อย\n\n"
        kai_msg += f"📁 **ไฟล์ที่สร้าง:** {len(result.code_files)} ไฟล์\n\n"
        kai_msg += f"📄 **ไฟล์สำคัญ:**\n"
        for f in result.code_files[:8]:
            kai_msg += f"• `{f.filepath}`\n"
        kai_msg += f"\n✅ **Tech stack:** {', '.join(state.selected_idea.tech_stack if state.selected_idea else [])}\n"
        kai_msg += f"\nโค้ดทุกอย่างเขียนตาม architecture ที่ Luna ออกแบบไว้\n"
        kai_msg += f"พร้อมส่งให้ Rex ทำ code review แล้วครับ!"
        
        await emit_agent_message(
            state.session_id, "builder", "Kai", "🔨", "Senior Developer",
            kai_msg, "building"
        )
        state.add_agent_message(
            agent="builder",
            agent_name="Kai",
            emoji="🔨",
            role="Senior Developer",
            message=kai_msg,
        )

        await emit_phase_complete(state.session_id, "building")

        return await self.run_critiquing(state)

    async def run_critiquing(self, state: SessionState) -> SessionState:
        """Layer 2, Phase 4: Review code with Critic agent and dialogue."""
        from src.agents.critic import CriticAgent

        state.transition_to(WorkflowLayer.CRITIQUING)
        logger.info(f"Starting code review for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "critiquing", "🔍 Rex is reviewing the code...")
        
        # Rex thinking
        await emit_agent_thinking(
            state.session_id, "critic", "Rex", "🔍", "QA Lead",
            "Analyzing code quality, security, and best practices...", "critiquing"
        )

        agent = CriticAgent(self.api_client)
        result = await agent.review_code(
            code_artifacts=state.code_artifacts,
            requirements=f"Theme: {state.theme}, Constraints: {state.constraints}",
        )

        state.critic_report = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result

        if result.status == "approved":
            # Rex presents approval with details
            rex_msg = f"✅ **Rex: Code Review Approved!**\n\n"
            rex_msg += f"โค้ดผ่านการตรวจสอบแล้ว! ไม่มีปัญหาสำคัญ\n"
            rex_msg += f"\n📊 **คะแนนคุณภาพ:** ผ่านมาตรฐาน"
            if result.issues:
                rex_msg += f"\n\n💡 **ข้อเสนอแนะเพิ่มเติม:**\n"
                for issue in result.issues[:3]:
                    rex_msg += f"• {issue}\n"
            
            await emit_agent_message(
                state.session_id, "critic", "Rex", "🔍", "QA Lead",
                rex_msg, "critiquing"
            )
            state.add_agent_message(
                agent="critic",
                agent_name="Rex",
                emoji="🔍",
                role="QA Lead",
                message=rex_msg,
            )

            # Kai responds to approval
            await emit_agent_thinking(
                state.session_id, "builder", "Kai", "🔨", "Senior Developer",
                "Responding to Rex's review...", "critiquing"
            )
            
            kai_response = f"💬 **Kai ตอบกลับ Rex:**\n\n"
            kai_response += f"ขอบคุณที่ตรวจสอบครับ Rex! ผมดีใจที่โค้ดผ่าน QA\n"
            kai_response += f"ผมเขียนโค้ดโดยคำนึงถึง best practices และ clean code\n"
            kai_response += f"ถ้ามีข้อเสนอแนะเพิ่มเติม ผมพร้อมนำไปปรับปรุงครับ!"
            
            await emit_agent_message(
                state.session_id, "builder", "Kai", "🔨", "Senior Developer",
                kai_response, "critiquing"
            )
            state.add_agent_message(
                agent="builder",
                agent_name="Kai",
                emoji="🔨",
                role="Senior Developer",
                message=kai_response,
            )

            await emit_phase_complete(state.session_id, "critiquing")
            
            # Move to HITL 2 for human review
            state.pause_for_hitl("Code review passed. Please review the generated code.")
            state.transition_to(WorkflowLayer.HITL_2)
        else:
            # Rex presents issues with details
            rex_msg = f"❌ **Rex: พบปัญหา {len(result.issues)} จุด**\n\n"
            rex_msg += f"🔴 **ปัญหาที่พบ:**\n"
            for i, issue in enumerate(result.issues[:5], 1):
                rex_msg += f"{i}. {issue}\n"
            rex_msg += f"\n⚠️ ผมแนะนำให้กลับไปแก้ไขโค้ดครับ Kai"
            
            await emit_agent_message(
                state.session_id, "critic", "Rex", "🔍", "QA Lead",
                rex_msg, "critiquing"
            )
            state.add_agent_message(
                agent="critic",
                agent_name="Rex",
                emoji="🔍",
                role="QA Lead",
                message=rex_msg,
            )

            # Kai responds to criticism
            await emit_agent_thinking(
                state.session_id, "builder", "Kai", "🔨", "Senior Developer",
                "Responding to Rex's critique...", "critiquing"
            )
            
            kai_response = f"💬 **Kai ตอบกลับ Rex:**\n\n"
            kai_response += f"รับทราบครับ Rex! ขอบคุณที่ชี้มา ผมจะกลับไปแก้ไขประเด็นที่พบ\n"
            if result.issues:
                kai_response += f"\nผมจะจัดการปัญหาเหล่านี้:\n"
                for issue in result.issues[:3]:
                    kai_response += f"• {issue}\n"
            kai_response += f"\nผมจะรีบแก้ไขและส่งให้ตรวจสอบอีกครั้งครับ!"
            
            await emit_agent_message(
                state.session_id, "builder", "Kai", "🔨", "Senior Developer",
                kai_response, "critiquing"
            )
            state.add_agent_message(
                agent="builder",
                agent_name="Kai",
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
        return await self.run_pitching(state)

    async def run_pitching(self, state: SessionState) -> SessionState:
        """Layer 3: Generate pitch materials with dialogue."""
        from src.agents.pitch_strategist import PitchStrategistAgent
        from src.agents.slide_agent import SlideAgent
        from src.agents.script_agent import ScriptAgent

        state.transition_to(WorkflowLayer.PITCHING)
        logger.info(f"Starting pitch generation for session {state.session_id}")
        
        await emit_phase_start(state.session_id, "pitching", "🎤 Nova is preparing the pitch...")

        selected = state.selected_idea

        # Step 1: Nova (Storyteller) creates narrative
        await emit_agent_thinking(
            state.session_id, "pitch_strategist", "Nova", "🎤", "Storyteller",
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

        # Nova presents narrative
        nova_narrative_msg = f"🎤 **Nova (Storyteller): สร้างเรื่องเล่าเรียบร้อยแล้ว!**\n\n"
        nova_narrative_msg += f"ผมได้ออกแบบ story สำหรับโปรเจกต์ **{selected.title if selected else 'N/A'}**\n"
        nova_narrative_msg += f"โดยเน้นสร้าง emotional impact และ clear value proposition\n"
        nova_narrative_msg += f"พร้อมส่งต่อให้ทีมทำ slides แล้วครับ!"
        
        await emit_agent_message(
            state.session_id, "pitch_strategist", "Nova", "🎤", "Storyteller",
            nova_narrative_msg, "pitching"
        )
        state.add_agent_message(
            agent="pitch_strategist",
            agent_name="Nova",
            emoji="🎤",
            role="Storyteller",
            message=nova_narrative_msg,
        )

        # Step 2: Nova (Slides) responds to Nova (Storyteller)
        await emit_agent_thinking(
            state.session_id, "slide_agent", "Nova (Slides)", "📊", "Presentation Designer",
            "Designing the slide deck layout based on Nova's narrative...", "pitching"
        )
        slide_agent = SlideAgent(self.api_client)
        slides_result = await slide_agent.create_slides(
            title=selected.title if selected else "",
            narrative=narrative_result,
        )
        state.slides = slides_result

        # Slides Nova responds to Storyteller Nova
        slides_nova_msg = f"💬 **Nova (Slides) ตอบกลับ Nova (Storyteller):**\n\n"
        slides_nova_msg += f"เรื่องเล่าเยี่ยมมากครับ! ผมออกแบบ slide deck ให้แล้ว {len(slides_result.slides) if hasattr(slides_result, 'slides') else 'N/A'} slides\n"
        slides_nova_msg += f"แต่ละ slide ถูกจัด layout ให้สวยงามและสื่อสารได้ชัดเจน\n"
        slides_nova_msg += f"พร้อมส่งต่อให้ Speech Writer แล้วครับ!"
        
        await emit_agent_message(
            state.session_id, "slide_agent", "Nova (Slides)", "📊", "Presentation Designer",
            slides_nova_msg, "pitching"
        )
        state.add_agent_message(
            agent="slide_agent",
            agent_name="Nova (Slides)",
            emoji="📊",
            role="Presentation Designer",
            message=slides_nova_msg,
        )

        # Step 3: Nova (Script) responds to both
        await emit_agent_thinking(
            state.session_id, "script_agent", "Nova (Script)", "🎙️", "Speech Writer",
            "Writing the speaker script based on slides and narrative...", "pitching"
        )
        script_agent = ScriptAgent(self.api_client)
        script_result = await script_agent.create_script(
            title=selected.title if selected else "",
            slides=slides_result,
            narrative=narrative_result,
        )
        state.script = script_result

        # Script Nova responds
        script_nova_msg = f"💬 **Nova (Script) ตอบกลับทีม:**\n\n"
        script_nova_msg += f"ได้รับ slides และ narrative แล้วครับ! ผมเขียน speaker script ให้แล้ว {len(script_result.sections) if hasattr(script_result, 'sections') else 'N/A'} sections\n"
        script_nova_msg += f"script ถูกออกแบบให้กระชับ น่าสนใจ และ fit กับเวลา pitch\n"
        script_nova_msg += f"**ทีม Nova พร้อมแล้วครับ! ขอให้ pitch ออกมาดีที่สุด!** 🎤"
        
        await emit_agent_message(
            state.session_id, "script_agent", "Nova (Script)", "🎙️", "Speech Writer",
            script_nova_msg, "pitching"
        )
        state.add_agent_message(
            agent="script_agent",
            agent_name="Nova (Script)",
            emoji="🎙️",
            role="Speech Writer",
            message=script_nova_msg,
        )

        # Final: All Nova wrap up
        wrapup_msg = f"🎉 **ทีม Nova เสร็จสมบูรณ์!**\n\n"
        wrapup_msg += f"✅ Storyteller: สร้าง narrative\n"
        wrapup_msg += f"✅ Presentation Designer: ออกแบบ slides\n"
        wrapup_msg += f"✅ Speech Writer: เขียน script\n\n"
        wrapup_msg += f"พร้อม pitch แล้ว! ลุยเลยทีม! 🚀"
        
        await emit_agent_message(
            state.session_id, "pitch_strategist", "Nova", "🎤", "Storyteller",
            wrapup_msg, "pitching"
        )
        state.add_agent_message(
            agent="pitch_strategist",
            agent_name="Nova",
            emoji="🎤",
            role="Storyteller",
            message=wrapup_msg,
        )

        await emit_phase_complete(state.session_id, "pitching")

        state.transition_to(WorkflowLayer.COMPLETE)
        return state
