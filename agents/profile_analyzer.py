__module_name__ = "profile_analyzer"

from backend.llm import get_chat_model
from backend.prompts.profile_analysis import get_prompt
from .utils import parse_markdown_response, validate_required_params
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ProfileAnalyzerAgent:
    def __init__(self):
        self.model = get_chat_model()
        self.prompt_template = get_prompt()

    def analyze(self, linkedin_profile_data: dict, user_instructions: Optional[Dict[str, Any]] = None, 
                conversation_context: Optional[str] = None) -> str:
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
        
        # Add retry logic for parsing failures
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Profile analysis attempt {attempt + 1}/{max_retries + 1}")
                response = self.model.invoke(prompt)
                print(f"\nPROFILE ANALYZER LLM RESPONSE (Attempt {attempt + 1}):")
                print("=" * 80)
                print(response.content if hasattr(response, 'content') else str(response))
                print("=" * 80)
                
                # Parse as markdown instead of JSON
                result = parse_markdown_response(response)
                
                logger.info("Profile analysis completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Profile analysis attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    # Return a fallback markdown response
                    logger.error("All profile analysis attempts failed, returning fallback response")
                    return """# LinkedIn Profile Analysis Report

## 📊 Analysis Summary
Analysis failed due to response parsing error. Please try again with a different approach or check your LinkedIn profile data.

## ✅ Key Strengths
- Unable to analyze - please retry the analysis

## 🎯 Areas for Improvement
### Issue: Analysis Failed
**Recommendation:** Please try the analysis again or contact support if the issue persists.

## 🏆 Overall Profile Score: 0/100

## 🚀 Priority Actions
### Action 1: Retry Analysis
**Why:** The analysis could not be completed
**How:** Try submitting your request again
**Timeline:** Immediate

## 💡 Additional Insights
The analysis encountered an error. Please ensure your LinkedIn profile data is properly formatted and try again."""
                else:
                    # Modify prompt for retry to be more explicit about markdown formatting
                    prompt += "\n\nIMPORTANT: This is a retry attempt. Please ensure your response is in clean markdown format with proper headers and structure."
