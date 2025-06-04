__module_name__ = "router"

from backend.llm import get_chat_model
from backend.prompts.routing import get_prompt, get_post_processing_prompt, get_instruction_extraction_prompt
from .utils import parse_llm_response, validate_required_params
import json

class RoutingAgent:
    def __init__(self):
        self.model = get_chat_model()
        self.prompt_template = get_prompt()

    def route(self, state, conversation_history, user_input):
        validate_required_params(user_input=user_input)
        prompt = self.prompt_template.format(
            state=state,
            conversation_history=conversation_history,
            user_input=user_input
        )
        response = self.model.invoke(prompt)
        print(f"\n🧭 ROUTER LLM RESPONSE:")
        print("=" * 80)
        print(response.content if hasattr(response, 'content') else str(response))
        print("=" * 80)
        parsed_response = parse_llm_response(response)
        actions = {
            "CALL_ANALYZE", "CALL_REWRITE", "CALL_JOB_FIT", "CALL_GUIDE",
            "PROCESS_AGENT_OUTPUT", "RESPOND_DIRECTLY", "AWAIT_URL", "AWAIT_CONFIRMATION",
            "REQUEST_JOB_DESCRIPTION", "INVALID_INPUT", "INITIAL_WELCOME"
        }
        if parsed_response.get('current_router_action') not in actions:
            parsed_response['current_router_action'] = 'RESPOND_DIRECTLY'
        return parsed_response
    
    def extract_user_instructions(self, user_input, conversation_history, current_task="general"):
        """Extract specific user instructions using LLM-based analysis for robust intent understanding."""
        try:
            # Use the instruction extraction prompt template
            prompt_template = get_instruction_extraction_prompt()
            extraction_prompt = prompt_template.format(
                user_input=user_input,
                conversation_context=conversation_history or "No prior conversation",
                current_task=current_task
            )
            
            response = self.model.invoke(extraction_prompt)
            response_content = response.content if hasattr(response, 'content') else str(response)
            print(f"\n🔍 ROUTER INSTRUCTION EXTRACTION LLM RESPONSE:")
            print("=" * 80)
            print(response_content)
            print("=" * 80)
            
            # Parse the LLM response as JSON
            try:
                instruction_data = json.loads(response_content)
                
                # Validate the response structure
                if not isinstance(instruction_data, dict) or not instruction_data.get('has_specific_instructions', False):
                    return None
                
                # Build a comprehensive instruction summary
                instruction_parts = []
                
                if instruction_data.get('style_preferences'):
                    instruction_parts.append(f"Style: {', '.join(instruction_data['style_preferences'])}")
                
                if instruction_data.get('content_focus'):
                    instruction_parts.append(f"Focus on: {', '.join(instruction_data['content_focus'])}")
                
                if instruction_data.get('tone_adjustments'):
                    instruction_parts.append(f"Tone: {', '.join(instruction_data['tone_adjustments'])}")
                
                if instruction_data.get('length_requirements') and instruction_data['length_requirements'] != "standard":
                    instruction_parts.append(f"Length: {instruction_data['length_requirements']}")
                
                if instruction_data.get('exclusions'):
                    instruction_parts.append(f"Avoid: {', '.join(instruction_data['exclusions'])}")
                
                if instruction_data.get('target_audience'):
                    instruction_parts.append(f"Target: {instruction_data['target_audience']}")
                
                if instruction_data.get('customization_context'):
                    instruction_parts.append(f"Context: {instruction_data['customization_context']}")
                
                # Return structured instructions if any were found
                if instruction_parts:
                    return {
                        'summary': '; '.join(instruction_parts),
                        'raw_data': instruction_data,
                        'confidence': instruction_data.get('confidence_score', 0.0)
                    }
                
                return None
                
            except json.JSONDecodeError:
                # If JSON parsing fails, fall back to extracting key phrases from the response
                if "has_specific_instructions" in response_content.lower() and "true" in response_content.lower():
                    return {
                        'summary': f"User instructions detected: {user_input[:100]}...",
                        'raw_data': {'fallback': True},
                        'confidence': 0.5
                    }
                return None
                
        except Exception as e:
            # Fallback to basic keyword detection if LLM fails
            return self._fallback_instruction_extraction(user_input)
    
    def _fallback_instruction_extraction(self, user_input):
        """Fallback method for instruction extraction if LLM approach fails."""
        instruction_keywords = [
            "make it", "focus on", "emphasize", "highlight", "shorter", "longer", 
            "concise", "detailed", "technical", "creative", "professional", 
            "specific to", "tailor for", "customize", "adapt", "modify"
        ]
        
        user_lower = user_input.lower()
        detected_instructions = []
        
        for keyword in instruction_keywords:
            if keyword in user_lower:
                start = user_lower.find(keyword)
                end = min(start + 50, len(user_input))
                instruction_snippet = user_input[start:end].strip()
                detected_instructions.append(instruction_snippet)
        
        if detected_instructions:
            return {
                'summary': '; '.join(detected_instructions),
                'raw_data': {'fallback': True, 'keywords': detected_instructions},
                'confidence': 0.3
            }
        
        return None
    
    def process_agent_output(self, agent_output, agent_type, conversation_context, user_instructions):
        """Process and contextualize agent output for user presentation."""
        try:
            # Extract instruction summary from structured data
            instruction_text = None
            if user_instructions and isinstance(user_instructions, dict):
                instruction_text = user_instructions.get('summary')
            elif user_instructions and isinstance(user_instructions, str):
                instruction_text = user_instructions
            
            # Use the prompt template from routing prompts module
            prompt_template = get_post_processing_prompt()
            processing_prompt = prompt_template.format(
                agent_type=agent_type,
                agent_output=agent_output,
                conversation_context=conversation_context,
                user_instructions=instruction_text or "None"
            )
            
            response = self.model.invoke(processing_prompt)
            print(f"\n📝 ROUTER OUTPUT PROCESSING LLM RESPONSE:")
            print("=" * 80)
            print(response.content if hasattr(response, 'content') else str(response))
            print("=" * 80)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"I've completed the {agent_type} analysis. The detailed results are available, and I'm ready to help you with next steps. What would you like to explore further?"