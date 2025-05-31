__module_name__ = "handlers"

import json
from .state_schema import ProfileBotState
from agents.router import RoutingAgent
from agents.career_guide import CareerGuideAgent
from agents.content_rewriter import ContentRewriterAgent
from agents.job_fit_evaluator import JobFitEvaluatorAgent
from agents.profile_analyzer import ProfileAnalyzerAgent
from agents.utils import parse_llm_response
from backend.logger import log_agent_action, log_router_decision, log_error

routing_agent = RoutingAgent()
analyzer = ProfileAnalyzerAgent()
rewriter = ContentRewriterAgent()
evaluator = JobFitEvaluatorAgent()
guide = CareerGuideAgent()

def router_node(state: ProfileBotState) -> ProfileBotState:
    current_user_input_for_turn = state.user_input
    history_before_llm_response = list(state.conversation_history)
    if current_user_input_for_turn and (
        not history_before_llm_response or 
        history_before_llm_response[-1].get("role") != "user" or 
        history_before_llm_response[-1].get("content") != current_user_input_for_turn
    ):
        state.conversation_history.append({"role": "user", "content": current_user_input_for_turn})
        history_before_llm_response = list(state.conversation_history)
    
    conversation_history_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history_before_llm_response])
    state_json = state.model_dump_json(indent=2)
    
    # Extract user instructions for dynamic agent behavior
    if current_user_input_for_turn:
        extracted_instructions = routing_agent.extract_user_instructions(
            current_user_input_for_turn, 
            conversation_history_str
        )
        if extracted_instructions:
            state.current_user_instructions = extracted_instructions
            log_agent_action("router", "Extracted user instructions", 
                           {"instructions_confidence": extracted_instructions.get('confidence', 0)})
            
        # Build conversation context for continuity
        recent_messages = history_before_llm_response[-3:] if len(history_before_llm_response) >= 3 else history_before_llm_response
        state.conversation_context = "; ".join([f"{msg['role']}: {msg['content'][:100]}" for msg in recent_messages])
    
    try:
        routing_response = routing_agent.route(
            state=state_json,
            conversation_history=conversation_history_str,
            user_input=current_user_input_for_turn
        )
        
        # Log routing decision with key state information
        key_state_flags = {
            "is_profile_analyzed": state.is_profile_analyzed,
            "analysis_completed": state.analysis_completed,
            "rewrite_completed": state.rewrite_completed,
            "job_fit_completed": state.job_fit_completed,
            "awaiting_confirmation": state.awaiting_user_confirmation,
            "awaiting_job_desc": state.awaiting_job_description,
            "linkedin_url": bool(state.linkedin_url),
            "last_agent": state.last_agent_called
        }
        
        if isinstance(routing_response, dict):
            action = routing_response.get("current_router_action", "UNKNOWN")
            log_router_decision(action, current_user_input_for_turn or "", key_state_flags)
            
            # Track state changes
            state_changes = {}
            
            if "current_router_action" in routing_response:
                state.current_router_action = routing_response["current_router_action"]
                state_changes["current_router_action"] = routing_response["current_router_action"]
            if "current_bot_response" in routing_response:
                state.current_bot_response = routing_response["current_bot_response"]
                state_changes["current_bot_response"] = routing_response["current_bot_response"]
            if "linkedin_url" in routing_response and routing_response["linkedin_url"]:
                state.linkedin_url = routing_response["linkedin_url"]
                state_changes["linkedin_url"] = routing_response["linkedin_url"]
            if "is_profile_analyzed" in routing_response:
                state.is_profile_analyzed = routing_response["is_profile_analyzed"]
                state_changes["is_profile_analyzed"] = routing_response["is_profile_analyzed"]
            if "awaiting_user_confirmation" in routing_response:
                state.awaiting_user_confirmation = routing_response["awaiting_user_confirmation"]
                state_changes["awaiting_user_confirmation"] = routing_response["awaiting_user_confirmation"]
            if "awaiting_job_description" in routing_response:
                state.awaiting_job_description = routing_response["awaiting_job_description"]
                state_changes["awaiting_job_description"] = routing_response["awaiting_job_description"]
            if "proposed_next_action" in routing_response:
                state.proposed_next_action = routing_response["proposed_next_action"]
                state_changes["proposed_next_action"] = routing_response["proposed_next_action"]
            if "last_agent_called" in routing_response:
                last_agent_value = routing_response["last_agent_called"]
                if last_agent_value == "null" or last_agent_value is None:
                    state.last_agent_called = None
                else:
                    state.last_agent_called = last_agent_value
                state_changes["last_agent_called"] = state.last_agent_called
            # Handle new re-execution control flags
            if "user_requested_update" in routing_response:
                state.user_requested_update = routing_response["user_requested_update"]
                state_changes["user_requested_update"] = routing_response["user_requested_update"]
            
            # Log state changes if any occurred
            if state_changes:
                log_agent_action("router", "Updated state", state_changes)
        
        if (state.current_router_action == "CALL_JOB_FIT" and 
            current_user_input_for_turn and 
            not state.target_job_description):
            job_keywords = ["experience", "responsibilities", "qualifications", "requirements", 
                          "skills", "years", "education", "job summary", "salary", "benefits"]
            input_lower = current_user_input_for_turn.lower()
            keyword_count = sum(1 for keyword in job_keywords if keyword in input_lower)
            if keyword_count >= 3 or len(current_user_input_for_turn) > 200:
                state.target_job_description = current_user_input_for_turn
                log_agent_action("router", "Auto-detected job description", {"keyword_count": keyword_count})
        
        if state.current_bot_response and (
            not state.conversation_history or
            state.conversation_history[-1].get("role") != "assistant" or
            state.conversation_history[-1].get("content") != state.current_bot_response
        ):
            state.conversation_history.append({"role": "assistant", "content": state.current_bot_response})
        return state
        
    except ValueError as e:
        log_error("router", str(e), current_user_input_for_turn)
        state.current_router_action = "RESPOND_DIRECTLY"
        state.current_bot_response = "I apologize, I encountered an issue processing your request. Could you please rephrase?"
        state.error_message = f"Routing error: {str(e)}"
        state.conversation_history.append({"role": "assistant", "content": state.current_bot_response})
        return state
    except Exception as e:
        log_error("router", str(e), current_user_input_for_turn)
        state.current_router_action = "RESPOND_DIRECTLY"
        state.current_bot_response = "I apologize, but I encountered an internal error. Please try again or rephrase your request."
        state.error_message = str(e)
        state.conversation_history.append({"role": "assistant", "content": state.current_bot_response})
        return state

def analyze_node(state: ProfileBotState) -> ProfileBotState:
    log_agent_action("profile_analyzer", "Starting analysis", user_input=state.user_input)
    
    try:
        if not state.linkedin_data:
            error_msg = "No LinkedIn data available for analysis. Please provide a LinkedIn profile URL first."
            log_error("profile_analyzer", "Missing LinkedIn data")
            state.error_message = error_msg
            state.current_bot_response = error_msg
            state.current_router_action = "AWAIT_URL"
            return state
            
        # Pass dynamic instructions to the specialized agent
        result = analyzer.analyze(
            linkedin_profile_data=state.linkedin_data,
            user_instructions=state.current_user_instructions,
            conversation_context=state.conversation_context
        )
        
        # Validate that we got a proper result
        if not result or not isinstance(result, dict):
            error_msg = "Profile analysis failed to produce valid results. Please try again."
            log_error("profile_analyzer", f"Invalid analysis result: {type(result)}")
            state.error_message = error_msg
            state.current_bot_response = error_msg
            state.current_router_action = "RESPOND_DIRECTLY"
            return state
        
        # Log successful analysis
        state_changes = {
            "profile_analysis_report": True,
            "is_profile_analyzed": True,
            "analysis_completed": True,
            "last_agent_called": "analyze",
            "current_router_action": "PROCESS_AGENT_OUTPUT"
        }
        log_agent_action("profile_analyzer", "Analysis completed successfully", state_changes)
        
        # Store output for router processing instead of direct response
        state.pending_agent_output = result
        state.needs_output_processing = True
        state.profile_analysis_report = result
        state.is_profile_analyzed = True
        state.analysis_completed = True
        state.last_agent_called = "analyze"
        state.current_task_status = "Profile analysis completed"
        state.current_router_action = "PROCESS_AGENT_OUTPUT"
        
        # Reset update flag
        state.user_requested_update = False
        return state
        
    except ValueError as e:
        error_msg = f"Analysis parsing error: {str(e)}. The analysis may have returned invalid data format."
        log_error("profile_analyzer", f"Parsing error: {str(e)}")
        state.error_message = error_msg
        state.current_bot_response = "I encountered an issue parsing the analysis results. This might be due to an unexpected response format. Please try again."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state
    except Exception as e:
        error_msg = f"Unexpected analysis error: {str(e)}"
        log_error("profile_analyzer", f"Unexpected error: {str(e)}")
        state.error_message = error_msg
        state.current_bot_response = "I apologize, but I encountered an error during profile analysis. Please try again."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state

def rewrite_node(state: ProfileBotState) -> ProfileBotState:
    log_agent_action("content_rewriter", "Starting content rewrite", user_input=state.user_input)
    
    try:
        if not state.profile_analysis_report:
            error_msg = "Profile analysis required before content rewriting. Please analyze your profile first."
            log_error("content_rewriter", "Missing profile analysis report")
            state.error_message = error_msg
            state.current_bot_response = error_msg
            state.current_router_action = "CALL_ANALYZE"
            return state
            
        # Pass dynamic instructions to the specialized agent
        result = rewriter.rewrite(
            current_content=state.linkedin_data,
            profile_analysis_report=state.profile_analysis_report,
            target_role=state.target_role,
            user_instructions=state.current_user_instructions,
            conversation_context=state.conversation_context
        )
        
        # Log successful rewrite
        state_changes = {
            "content_rewrites_suggestions": True,
            "rewrite_completed": True,
            "last_agent_called": "rewrite",
            "current_router_action": "PROCESS_AGENT_OUTPUT"
        }
        log_agent_action("content_rewriter", "Content rewrite completed successfully", state_changes)
        
        # Store output for router processing instead of direct response
        state.pending_agent_output = result
        state.needs_output_processing = True
        state.content_rewrites_suggestions = result
        state.rewrite_completed = True
        state.last_agent_called = "rewrite"
        state.current_task_status = "Content rewrite suggestions generated"
        state.current_router_action = "PROCESS_AGENT_OUTPUT"
        
        # Reset update flag
        state.user_requested_update = False
        return state
        
    except ValueError as e:
        log_error("content_rewriter", str(e))
        state.error_message = f"Rewriting error: {str(e)}"
        state.current_bot_response = "I encountered an issue generating content suggestions. Please ensure your profile has been analyzed first."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state
    except Exception as e:
        log_error("content_rewriter", str(e))
        state.error_message = str(e)
        state.current_bot_response = "I apologize, but I encountered an error during content rewriting. Please try again."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state

def job_fit_node(state: ProfileBotState) -> ProfileBotState:
    log_agent_action("job_fit_evaluator", "Starting job fit evaluation", user_input=state.user_input)
    
    try:
        if not state.profile_analysis_report:
            error_msg = "Profile analysis required before job fit evaluation. Please analyze your profile first."
            log_error("job_fit_evaluator", "Missing profile analysis report")
            state.error_message = error_msg
            state.current_bot_response = error_msg
            state.current_router_action = "CALL_ANALYZE"
            return state
        if not state.target_job_description:
            error_msg = "Job description required for fit evaluation. Please provide a job description."
            log_error("job_fit_evaluator", "Missing job description")
            state.error_message = error_msg
            state.current_bot_response = error_msg
            state.current_router_action = "REQUEST_JOB_DESCRIPTION"
            state.awaiting_job_description = True
            return state
            
        # Pass dynamic instructions to the specialized agent
        result = evaluator.evaluate_fit(
            profile_analysis_report=state.profile_analysis_report,
            job_description=state.target_job_description,
            user_instructions=state.current_user_instructions,
            conversation_context=state.conversation_context
        )
        
        # Log successful evaluation
        state_changes = {
            "job_fit_evaluation_report": True,
            "job_fit_completed": True,
            "last_agent_called": "job_fit",
            "awaiting_job_description": False,
            "current_router_action": "PROCESS_AGENT_OUTPUT"
        }
        log_agent_action("job_fit_evaluator", "Job fit evaluation completed successfully", state_changes)
        
        # Store output for router processing instead of direct response
        state.pending_agent_output = result
        state.needs_output_processing = True
        state.job_fit_evaluation_report = result
        state.job_fit_completed = True
        state.last_agent_called = "job_fit"
        state.current_task_status = "Job fit evaluation completed"
        state.awaiting_job_description = False
        state.current_router_action = "PROCESS_AGENT_OUTPUT"
        
        # Reset update flag
        state.user_requested_update = False
        return state
        
    except ValueError as e:
        log_error("job_fit_evaluator", str(e))
        state.error_message = f"Job fit error: {str(e)}"
        state.current_bot_response = "I encountered an issue evaluating job fit. Please ensure both profile analysis and job description are available."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state
    except Exception as e:
        log_error("job_fit_evaluator", str(e))
        state.error_message = str(e)
        state.current_bot_response = "I apologize, but I encountered an error during job fit evaluation. Please try again."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state

def guide_node(state: ProfileBotState) -> ProfileBotState:
    log_agent_action("career_guide", "Starting career guidance", user_input=state.user_input)
    
    try:
        if not state.user_input:
            error_msg = "User query required for career guidance. Please ask a specific career question."
            log_error("career_guide", "Missing user query")
            state.error_message = error_msg
            state.current_bot_response = error_msg
            state.current_router_action = "RESPOND_DIRECTLY"
            return state
            
        # Pass dynamic instructions to the specialized agent
        result = guide.guide(
            user_query=state.user_input,
            profile_analysis_report=state.profile_analysis_report or {},
            target_role=state.target_role or "your desired role",
            user_instructions=state.current_user_instructions,
            conversation_context=state.conversation_context
        )
        
        # Log successful guidance
        state_changes = {
            "career_guidance_notes": True,
            "guidance_completed": True,
            "last_agent_called": "guide",
            "current_router_action": "PROCESS_AGENT_OUTPUT"
        }
        log_agent_action("career_guide", "Career guidance completed successfully", state_changes)
        
        # Store output for router processing instead of direct response
        state.pending_agent_output = result
        state.needs_output_processing = True
        state.career_guidance_notes = result
        state.guidance_completed = True
        state.last_agent_called = "guide"
        state.current_task_status = "Career guidance provided"
        state.current_router_action = "PROCESS_AGENT_OUTPUT"
        
        # Reset update flag
        state.user_requested_update = False
        return state
        
    except ValueError as e:
        log_error("career_guide", str(e))
        state.error_message = f"Career guidance error: {str(e)}"
        state.current_bot_response = "I encountered an issue providing career guidance. Please ask a specific career-related question."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state
    except Exception as e:
        log_error("career_guide", str(e))
        state.error_message = str(e)
        state.current_bot_response = "I apologize, but I encountered an error providing career guidance. Please try again."
        state.current_router_action = "RESPOND_DIRECTLY"
        return state

def process_agent_output_node(state: ProfileBotState) -> ProfileBotState:
    """Process and contextualize agent output through the router for user presentation."""
    log_agent_action("output_processor", "Starting agent output processing", 
                    {"agent_type": state.last_agent_called, "has_pending_output": bool(state.pending_agent_output)})
    
    try:
        if not state.pending_agent_output or not state.last_agent_called:
            log_error("output_processor", "Missing agent output or agent type")
            state.current_bot_response = "I don't have any agent output to process. Please try again."
            state.current_router_action = "RESPOND_DIRECTLY"
            return state
        
        # Use the router to process and contextualize the agent output
        processed_response = routing_agent.process_agent_output(
            agent_output=state.pending_agent_output,
            agent_type=state.last_agent_called,
            conversation_context=state.conversation_context,
            user_instructions=state.current_user_instructions
        )
        
        # Log successful processing
        state_changes = {
            "current_bot_response": True,
            "current_router_action": "RESPOND_DIRECTLY",
            "pending_agent_output": None,
            "needs_output_processing": False
        }
        log_agent_action("output_processor", "Agent output processed successfully", state_changes)
        
        # Set the processed response for user presentation
        state.current_bot_response = processed_response
        state.current_router_action = "RESPOND_DIRECTLY"
        
        # Clear processing flags
        state.pending_agent_output = None
        state.needs_output_processing = False
        
        # Add response to conversation history
        if state.current_bot_response and (
            not state.conversation_history or
            state.conversation_history[-1].get("role") != "assistant" or
            state.conversation_history[-1].get("content") != state.current_bot_response
        ):
            state.conversation_history.append({"role": "assistant", "content": state.current_bot_response})
        
        return state
        
    except Exception as e:
        log_error("output_processor", str(e))
        state.error_message = f"Output processing error: {str(e)}"
        state.current_bot_response = "I've completed the analysis. The detailed results are available, and I'm ready to help you with next steps. What would you like to explore further?"
        state.current_router_action = "RESPOND_DIRECTLY"
        state.pending_agent_output = None
        state.needs_output_processing = False
        return state
