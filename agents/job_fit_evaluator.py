__module_name__ = "job_fit_evaluator"

from backend.llm import get_chat_model
from backend.prompts.job_fit import get_prompt
from .utils import parse_markdown_response, validate_required_params
from typing import Optional, Dict, Any

class JobFitEvaluatorAgent:
    def __init__(self):
        self.model = get_chat_model()
        self.prompt_template = get_prompt()

    def evaluate_fit(self, profile_analysis_report, job_description, user_instructions: Optional[Dict[str, Any]] = None, 
                     conversation_context: Optional[str] = None) -> str:
        validate_required_params(
            profile_analysis_report=profile_analysis_report,
            job_description=job_description
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
            profile_analysis_report=profile_analysis_report,
            target_job_description=job_description,
            additional_context=additional_context
        )
        response = self.model.invoke(prompt)
        print(f"\n📊 JOB FIT EVALUATOR LLM RESPONSE:")
        print("=" * 80)
        print(response.content if hasattr(response, 'content') else str(response))
        print("=" * 80)
        return parse_markdown_response(response)
