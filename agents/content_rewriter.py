__module_name__ = "content_rewriter"

from backend.llm import get_chat_model
from backend.prompts.content_rewriting import get_prompt
from .utils import parse_llm_response, validate_required_params
from typing import Dict, Optional, Any

class ContentRewriterAgent:
    def __init__(self):
        self.model = get_chat_model()
        self.prompt_template = get_prompt()

    def rewrite(self, current_content: dict, profile_analysis_report: dict, target_role: Optional[str] = None, 
                user_instructions: Optional[Dict[str, Any]] = None, conversation_context: Optional[str] = None) -> Dict[str, any]:
        validate_required_params(
            current_content=current_content,
            profile_analysis_report=profile_analysis_report
        )
        
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
            current_linkedin_content=current_content,
            profile_analysis_report=profile_analysis_report,
            target_role=target_role or "the same role",
            additional_context=additional_context
        )
        response = self.model.invoke(prompt)
        print(f"\n✍️ CONTENT REWRITER LLM RESPONSE:")
        print("=" * 80)
        print(response.content if hasattr(response, 'content') else str(response))
        print("=" * 80)
        return parse_llm_response(response)
