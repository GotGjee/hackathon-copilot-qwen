"""
Prompt Builder Module
Dynamic prompt generation from YAML templates.
Cool factor: Agents can now adapt their prompts based on context!
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from loguru import logger


class PromptTemplate:
    """Represents a prompt template with variables."""
    
    def __init__(self, name: str, template: str, variables: list | None = None):
        self.name = name
        self.template = template
        self.variables = variables or self._extract_variables()
    
    def _extract_variables(self) -> list:
        """Extract {variable} names from template."""
        import re
        return re.findall(r'\{(\w+)\}', self.template)
    
    def render(self, **kwargs) -> str:
        """Render template with given variables."""
        # Filter out unused variables
        filtered = {k: v for k, v in kwargs.items() if k in self.variables}
        try:
            return self.template.format(**filtered)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in template {self.name}")
            # Fill missing with placeholder
            for var in self.variables:
                if var not in filtered:
                    filtered[var] = f"[{var}]"
            return self.template.format(**filtered)


class PromptBuilder:
    """
    Dynamic prompt generation system.
    
    Instead of hardcoding prompts in orchestrator.py,
    this class loads templates from YAML and builds prompts on-the-fly.
    
    Cool feature: Context-aware prompt selection!
    - If agents disagree → use debate template
    - If agents agree → use consensus template
    - If agent needs to defend → use defense template
    """
    
    # Default negotiation templates (fallback if YAML not found)
    DEFAULT_TEMPLATES = {
        "negotiation": {
            "ideator_response": """🧠 {agent_name} ({role}): {opposing_name} วิเคราะห์ได้เฉียบขาดมาก!

แต่ฉันอยากแสดงมุมมองเพิ่มเติม...

🎯 ไอเดียที่ {opposing_name} แนะนำเป็นอันดับ 1:
{top_idea}

📝 บทสนทนาก่อนหน้านี้:
{dialogue_history}

กรุณาตอบกลับ {opposing_name} โดย:
{instructions}""",
            
            "judge_counter": """⚖️ {agent_name} ({role}): {opposing_name} เสนอประเด็นน่าสนใจ...

📝 บทสนทนาล่าสุด:
{dialogue_history}

กรุณาตอบกลับ {opposing_name} โดย:
{instructions}""",
            
            "consensus": """🤝 บทสรุปการ negotiate:

{agent1_name} และ {agent2_name} ได้แลกเปลี่ยนมุมมองกันแล้ว:

{dialogue_history}

✅ ฉันทามติ: {consensus_statement}"""
        }
    }
    
    def __init__(self, template_dir: str = "prompts"):
        self.templates: Dict[str, Any] = {}
        self._load_templates(template_dir)
    
    def _load_templates(self, template_dir: str):
        """Load prompt templates from YAML files."""
        # Load defaults first
        self.templates = self.DEFAULT_TEMPLATES.copy()
        
        # Try to load from files (override defaults)
        negotiation_path = os.path.join(template_dir, "negotiation.yaml")
        if os.path.exists(negotiation_path):
            try:
                with open(negotiation_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    # Handle both top-level key and direct content
                    if isinstance(loaded, dict):
                        if "negotiation" in loaded:
                            self.templates["negotiation"] = loaded["negotiation"]
                        else:
                            self.templates["negotiation"] = loaded
                logger.info(f"Loaded negotiation templates from {negotiation_path}")
            except Exception as e:
                logger.warning(f"Failed to load negotiation templates: {e}")
                logger.info("Using default templates")
    
    def get_negotiation_prompt(
        self,
        agent_name: str,
        agent_role: str,
        agent_system_prompt: str,
        opposing_name: str,
        opposing_view: str,
        dialogue_history: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Build negotiation prompt dynamically.
        
        Returns dict with 'system' and 'user' keys for API call.
        """
        context = context or {}
        negotiation_templates = self.templates.get("negotiation", {})
        
        # Context-aware template selection (COOL!)
        if context.get("is_debate", False):
            template_str = negotiation_templates.get(
                "debate", 
                negotiation_templates.get("ideator_response", self.DEFAULT_TEMPLATES["negotiation"]["ideator_response"])
            )
        elif context.get("is_agreement", False):
            template_str = negotiation_templates.get(
                "agreement",
                negotiation_templates.get("ideator_response", self.DEFAULT_TEMPLATES["negotiation"]["ideator_response"])
            )
        else:
            template_str = negotiation_templates.get(
                "ideator_response",
                self.DEFAULT_TEMPLATES["negotiation"]["ideator_response"]
            )
        
        # Build prompt
        prompt = PromptTemplate("negotiation", template_str)
        user_content = prompt.render(
            agent_name=agent_name,
            role=agent_role,
            opposing_name=opposing_name,
            opposing_view=opposing_view,
            dialogue_history=dialogue_history,
            top_idea=context.get("top_idea", "N/A"),
            instructions=context.get(
                "instructions",
                "1. เห็นด้วยหรือไม่เห็นด้วย พร้อมเหตุผล\n"
                "2. เสนอไอเดียที่ปรับปรุงตาม feedback\n"
                "3. ถ้า disagree ต้องอธิบายว่าทำไม และเสนอทางเลือก\n"
                "4. ตอบเป็นภาษาไทย + English technical terms"
            ),
        )
        
        return {
            "system": agent_system_prompt,
            "user": user_content,
        }
    
    def get_judge_counter_prompt(
        self,
        agent_name: str,
        agent_role: str,
        agent_system_prompt: str,
        opposing_name: str,
        opposing_view: str,
        dialogue_history: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Build judge counter-response prompt."""
        context = context or {}
        negotiation_templates = self.templates.get("negotiation", {})
        
        template_str = negotiation_templates.get(
            "judge_counter",
            self.DEFAULT_TEMPLATES["negotiation"]["judge_counter"]
        )
        
        prompt = PromptTemplate("judge_counter", template_str)
        user_content = prompt.render(
            agent_name=agent_name,
            role=agent_role,
            opposing_name=opposing_name,
            opposing_view=opposing_view,
            dialogue_history=dialogue_history,
            instructions=context.get(
                "instructions",
                "1. รับฟังประเด็นที่เสนอ\n"
                "2. เห็นด้วยหรือไม่เห็นด้วย พร้อมเหตุผลเชิงตรรกะ\n"
                "3. ถ้า disagree ให้เสนอ alternative ที่ realistic\n"
                "4. สรุปว่าไอเดียไหนควรไปต่อ และทำไม\n"
                "5. ตอบเป็นภาษาไทย + English technical terms"
            ),
        )
        
        return {
            "system": agent_system_prompt,
            "user": user_content,
        }
    
    def get_consensus_prompt(
        self,
        agent1_name: str,
        agent2_name: str,
        dialogue_history: str,
        consensus_statement: str,
    ) -> str:
        """Build consensus/closing prompt."""
        negotiation_templates = self.templates.get("negotiation", {})
        
        template_str = negotiation_templates.get(
            "consensus",
            self.DEFAULT_TEMPLATES["negotiation"]["consensus"]
        )
        
        prompt = PromptTemplate("consensus", template_str)
        return prompt.render(
            agent1_name=agent1_name,
            agent2_name=agent2_name,
            dialogue_history=dialogue_history,
            consensus_statement=consensus_statement,
        )
    
    def get_template_names(self) -> list:
        """List available template names."""
        return list(self.templates.keys())
    
    def get_template(self, name: str) -> Optional[Dict]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def reload(self, template_dir: str = "prompts"):
        """Reload templates from files (useful for live editing)."""
        self._load_templates(template_dir)
        logger.info("Templates reloaded")