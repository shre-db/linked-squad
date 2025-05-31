__module_name__ = "utils"

import json
import logging
import re

logger = logging.getLogger(__name__)

def parse_llm_response(response):
    """
    Parse LLM response and extract JSON content.
    
    Args:
        response: The response from the LLM (can be string, dict, or object with .content attribute)
        
    Returns:
        dict: Parsed JSON object
        
    Raises:
        ValueError: If JSON parsing fails with detailed error message
    """
    original_response = response
    
    try:
        # Handle response objects with content attribute
        if hasattr(response, "content"):
            response = response.content
            
        # If it's already a dict, return it
        if isinstance(response, dict):
            return response
            
        # Convert to string if not already
        if not isinstance(response, str):
            response = str(response)
            
        response = response.strip()
        
        if not response:
            raise ValueError("Empty response from LLM")
        
        json_content = None
        
        # Handle ```json code blocks
        if "```json" in response:
            # Find the JSON block
            json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_content = json_match.group(1).strip()
            else:
                # Handle case where closing ``` is missing
                json_start = response.find("```json") + len("```json")
                json_content = response[json_start:].strip()
                # Remove any trailing ``` if present
                if json_content.endswith("```"):
                    json_content = json_content[:-3].strip()
                    
        # Handle generic ``` code blocks that might contain JSON
        elif response.startswith("```") and "```" in response[3:]:
            lines = response.split('\n')
            start_line = 1  # Skip the opening ```
            end_line = len(lines) - 1
            
            # Find the closing ```
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end_line = i
                    break
                    
            json_content = '\n'.join(lines[start_line:end_line]).strip()
            
        else:
            # Assume the entire response is JSON
            json_content = response
            
        if not json_content:
            raise ValueError("No JSON content found in response")
            
        # Try to parse the JSON
        try:
            parsed = json.loads(json_content)
            return parsed
        except json.JSONDecodeError as e:
            # Log the problematic JSON for debugging
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Problematic JSON content (first 500 chars): {json_content[:500]}")
            raise ValueError(f"Invalid JSON format: {e}. Content preview: {json_content[:100]}...")
            
    except ValueError:
        # Re-raise ValueError with original message
        raise
    except Exception as e:
        # Log the original response for debugging
        logger.error(f"Unexpected error parsing LLM response: {e}")
        logger.error(f"Original response type: {type(original_response)}")
        logger.error(f"Response content (first 500 chars): {str(original_response)[:500]}")
        raise ValueError(f"Failed to parse LLM response: {e}")

def validate_required_params(**kwargs):
    for param_name, param_value in kwargs.items():
        if param_value is None:
            raise ValueError(f"Required parameter '{param_name}' cannot be None")
        if isinstance(param_value, str) and not param_value.strip():
            raise ValueError(f"Required parameter '{param_name}' cannot be empty")
        if isinstance(param_value, dict) and not param_value:
            raise ValueError(f"Required parameter '{param_name}' cannot be empty")
