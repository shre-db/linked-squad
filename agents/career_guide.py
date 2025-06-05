__module_name__ = "career_guide"

from backend.llm import get_chat_model
from backend.prompts.career_guidance import get_prompt
from .utils import parse_markdown_response, validate_required_params
from typing import Optional, Dict, Any

class CareerGuideAgent:
    def __init__(self):
        self.model = get_chat_model()
        self.prompt_template = get_prompt()

    def guide(self, user_query, profile_analysis_report, target_role, user_instructions: Optional[Dict[str, Any]] = None,
              conversation_context: Optional[str] = None) -> str:
        validate_required_params(
            user_query=user_query,
            profile_analysis_report=profile_analysis_report,
            target_role=target_role
        )
        try:
            # Extract instruction summary from structured data
            instruction_text = None
            if user_instructions and isinstance(user_instructions, dict):
                instruction_text = user_instructions.get('summary')
            elif user_instructions and isinstance(user_instructions, str):
                instruction_text = user_instructions
            
            # Build dynamic context for the prompt
            additional_context = ""
            if instruction_text:
                additional_context += f"\n\nSpecific user instructions: {instruction_text}"
            if conversation_context:
                additional_context += f"\n\nConversation context: {conversation_context}"
                
            prompt = self.prompt_template.format(
                user_query=user_query,
                profile_analysis_report=profile_analysis_report,
                target_role=target_role,
                additional_context=additional_context
            )
            response = self.model.invoke(prompt)
            print(f"\nCAREER GUIDE LLM RESPONSE:")
            print("=" * 80)
            print(response.content if hasattr(response, 'content') else str(response))
            print("=" * 80)
            return parse_markdown_response(response)
        except Exception as e:
            raise ValueError(f"Failed to generate career guidance: {e}")
