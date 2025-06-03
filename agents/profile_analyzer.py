__module_name__ = "profile_analyzer"

from backend.llm import get_chat_model
from backend.prompts.profile_analysis import get_prompt
from .utils import parse_llm_response, validate_required_params
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ProfileAnalyzerAgent:
    def __init__(self):
        self.model = get_chat_model()
        self.prompt_template = get_prompt()

    def analyze(self, linkedin_profile_data: dict, user_instructions: Optional[Dict[str, Any]] = None, 
                conversation_context: Optional[str] = None) -> Dict[str, any]:
        validate_required_params(linkedin_profile_data=linkedin_profile_data)
        
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
            linkedin_profile_data=linkedin_profile_data,
            additional_context=additional_context
        )
        
        # Add retry logic for JSON parsing failures
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Profile analysis attempt {attempt + 1}/{max_retries + 1}")
                response = self.model.invoke(prompt)
                print(f"\n🤖 PROFILE ANALYZER LLM RESPONSE (Attempt {attempt + 1}):")
                print("=" * 80)
                print(response.content if hasattr(response, 'content') else str(response))
                print("=" * 80)
                result = parse_llm_response(response)
                
                # Validate the response structure
                required_fields = ['analysis_summary', 'strengths', 'improvement_opportunities', 
                                 'keyword_analysis', 'achievement_assessment', 'overall_score', 
                                 'priority_actions']
                
                for field in required_fields:
                    if field not in result:
                        raise ValueError(f"Missing required field: {field}")
                
                logger.info("Profile analysis completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Profile analysis attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    # Return a fallback response structure
                    logger.error("All profile analysis attempts failed, returning fallback response")
                    return {
                        "analysis_summary": "Analysis failed due to response parsing error. Please try again.",
                        "strengths": ["Unable to analyze - please retry"],
                        "improvement_opportunities": ["Unable to analyze - please retry"],
                        "keyword_analysis": {
                            "current_keywords": [],
                            "missing_keywords": [],
                            "optimization_strategy": "Analysis failed - please retry"
                        },
                        "achievement_assessment": {
                            "quantified_achievements": 0,
                            "total_achievements": 0,
                            "quantification_opportunities": []
                        },
                        "overall_score": 0,
                        "priority_actions": ["Please retry the analysis"],
                        "analysis_notes": f"Analysis failed: {str(e)}"
                    }
                else:
                    # Modify prompt for retry to be more explicit about JSON formatting
                    prompt += "\n\nIMPORTANT: This is a retry attempt. Please ensure your response is ONLY valid JSON with no extra text, comments, or formatting."
