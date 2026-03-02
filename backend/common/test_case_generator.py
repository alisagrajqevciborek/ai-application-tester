"""
AI-powered test case generator.

This module provides:
- Natural language to test case conversion
- Test case generation using OpenAI
- Structured test case output for Playwright execution
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from .ai_helpers import get_openai_client
from .ai_prompts import AIPrompts

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✓ Loaded .env from: {env_path}")
else:
    load_dotenv(override=True)
    print(f"✗ .env not found at: {env_path}, trying current directory")

# Debug: Check if key is loaded
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"✓ OPENAI_API_KEY loaded: {api_key[:20]}...")
else:
    print("✗ OPENAI_API_KEY not found in environment")

logger = logging.getLogger(__name__)


def generate_test_case_from_prompt(
    user_prompt: str,
    application_url: str,
    test_type: str = "functional",
    application_name: Optional[str] = None,
    context: Optional[Dict] = None
) -> Dict:
    """
    Generate a test case based on user's natural language description.
    
    Args:
        user_prompt: Natural language description of what to test
                     (e.g., "Test the login form with invalid credentials")
        application_url: URL of the application to test
        test_type: Type of test (functional, regression, performance, accessibility)
        application_name: Optional name of the application
        context: Optional additional context (e.g., existing test cases, app structure)
        
    Returns:
        Dictionary with test case structure:
        {
            "name": "Test case name",
            "description": "What this test does",
            "test_type": "functional",
            "steps": [
                {
                    "order": 1,
                    "action": "navigate|click|fill|wait|assert|check",
                    "selector": "CSS selector or text",
                    "value": "Value to input (if applicable)",
                    "description": "What this step does",
                    "expected_result": "What should happen"
                }
            ],
            "expected_results": "Overall expected outcome",
            "tags": ["tag1", "tag2"],
            "estimated_duration": "X minutes"
        }
    """
    client = get_openai_client()
    if not client:
        logger.warning("OpenAI client not available. Cannot generate test case.")
        print("✗ OpenAI client is None - using fallback")
        return _generate_fallback_test_case(user_prompt, application_url, test_type)
    
    print("✓ OpenAI client created successfully")
    
    try:
        # Use centralized system prompt
        system_prompt = AIPrompts.test_case_generation_system_prompt()
        
        # Build user prompt with context
        user_prompt_full = f"""Generate a test case for the following request:

User Request: "{user_prompt}"

Application URL: {application_url}
Test Type: {test_type}
"""
        
        if application_name:
            user_prompt_full += f"Application Name: {application_name}\n"
        
        if context:
            user_prompt_full += f"\nAdditional Context:\n{json.dumps(context, indent=2)}\n"
        
        user_prompt_full += """
Generate a complete, executable test case that can be run with Playwright browser automation.

Return ONLY valid JSON with this exact structure:
{
    "name": "Descriptive test case name",
    "description": "Clear description of what this test verifies",
    "test_type": "functional",
    "steps": [
        {
            "order": 1,
            "action": "navigate",
            "selector": null,
            "value": "https://example.com/login",
            "description": "Navigate to login page",
            "expected_result": "Login page loads successfully"
        },
        {
            "order": 2,
            "action": "fill",
            "selector": "#email",
            "value": "test@example.com",
            "description": "Enter email address",
            "expected_result": "Email field is filled with test@example.com"
        },
        {
            "order": 3,
            "action": "fill",
            "selector": "#password",
            "value": "wrongpassword",
            "description": "Enter incorrect password",
            "expected_result": "Password field is filled"
        },
        {
            "order": 4,
            "action": "click",
            "selector": "button[type='submit']",
            "value": null,
            "description": "Click submit button",
            "expected_result": "Submit button is clicked"
        },
        {
            "order": 5,
            "action": "wait",
            "selector": ".error-message",
            "value": null,
            "description": "Wait for error message to appear",
            "expected_result": "Error message is visible"
        },
        {
            "order": 6,
            "action": "assert",
            "selector": ".error-message",
            "value": "Invalid credentials",
            "description": "Verify error message text",
            "expected_result": "Error message contains 'Invalid credentials'"
        }
    ],
    "expected_results": "User should see an error message indicating invalid credentials",
    "tags": ["login", "authentication", "error-handling"],
    "estimated_duration": "2 minutes"
}

Important:
- Use realistic selectors (prefer IDs, data attributes, or semantic selectors)
- Include wait steps before assertions to handle async operations
- Provide clear expected results for each step
- Make test data realistic but clearly test data (e.g., test@example.com)
- Ensure steps are in logical order
- Include error scenarios if relevant
- Return ONLY the JSON, no markdown, no code blocks, no explanations
"""
        
        logger.info(f"Generating test case for prompt: {user_prompt[:100]}...")
        
        response = client.chat.completions.create(
            model="gpt-4o",  # Use same model as report generator for consistency
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt_full
                }
            ],
            max_tokens=2000,
            temperature=0.3,  # Lower temperature for more consistent, structured output
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from OpenAI, using fallback")
            return _generate_fallback_test_case(user_prompt, application_url, test_type)
        
        # Parse JSON response
        try:
            test_case = json.loads(content)
            
            # Validate structure
            if not isinstance(test_case, dict):
                raise ValueError("Response is not a dictionary")
            
            if "steps" not in test_case:
                raise ValueError("Missing 'steps' in response")
            
            if not isinstance(test_case["steps"], list):
                raise ValueError("'steps' must be a list")
            
            # Ensure all required fields are present
            test_case.setdefault("name", f"Test: {user_prompt[:50]}")
            test_case.setdefault("description", user_prompt)
            test_case.setdefault("test_type", test_type)
            test_case.setdefault("expected_results", "Test completes successfully")
            test_case.setdefault("tags", [])
            test_case.setdefault("estimated_duration", "5 minutes")
            
            # Validate and normalize steps
            normalized_steps = []
            for idx, step in enumerate(test_case["steps"], start=1):
                if not isinstance(step, dict):
                    continue
                
                normalized_step = {
                    "order": step.get("order", idx),
                    "action": step.get("action", "wait"),
                    "selector": step.get("selector"),
                    "value": step.get("value"),
                    "description": step.get("description", f"Step {idx}"),
                    "expected_result": step.get("expected_result", step.get("expected_results", "Step completes"))
                }
                normalized_steps.append(normalized_step)
            
            test_case["steps"] = normalized_steps
            
            logger.info(f"Successfully generated test case with {len(normalized_steps)} steps")
            return test_case
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {content[:500]}")
            return _generate_fallback_test_case(user_prompt, application_url, test_type)
        except Exception as e:
            logger.error(f"Error processing test case: {e}", exc_info=True)
            return _generate_fallback_test_case(user_prompt, application_url, test_type)
            
    except Exception as e:
        logger.error(f"Error generating test case: {e}", exc_info=True)
        return _generate_fallback_test_case(user_prompt, application_url, test_type)


def _generate_fallback_test_case(
    user_prompt: str,
    application_url: str,
    test_type: str
) -> Dict:
    """
    Generate a basic fallback test case when AI is unavailable.
    
    Args:
        user_prompt: User's test description
        application_url: Application URL
        test_type: Test type
        
    Returns:
        Basic test case structure
    """
    return {
        "name": f"Test: {user_prompt[:50]}",
        "description": user_prompt,
        "test_type": test_type,
        "steps": [
            {
                "order": 1,
                "action": "navigate",
                "selector": None,
                "value": application_url,
                "description": f"Navigate to {application_url}",
                "expected_result": "Page loads successfully"
            },
            {
                "order": 2,
                "action": "wait",
                "selector": "body",
                "value": None,
                "description": "Wait for page to load",
                "expected_result": "Page is fully loaded"
            },
            {
                "order": 3,
                "action": "assert",
                "selector": "body",
                "value": None,
                "description": "Verify page content is visible",
                "expected_result": "Page content is visible"
            }
        ],
        "expected_results": "Basic navigation and page load verification",
        "tags": ["fallback", "basic"],
        "estimated_duration": "1 minute",
        "ai_generated": False,
        "fallback": True
    }


def refine_test_case(
    existing_test_case: Dict,
    refinement_prompt: str
) -> Dict:
    """
    Refine an existing test case based on user feedback.
    
    Args:
        existing_test_case: Existing test case structure
        refinement_prompt: User's refinement request
                          (e.g., "Add a step to check error message", "Remove step 3")
        
    Returns:
        Refined test case
    """
    client = get_openai_client()
    if not client:
        logger.warning("OpenAI client not available. Cannot refine test case.")
        # Return the original test case unchanged if AI is not available
        return existing_test_case
    
    # Validate input test case
    if not _validate_test_case_schema(existing_test_case):
        logger.error("Invalid test case schema provided for refinement")
        return existing_test_case
    
    try:
        # Use centralized system prompt
        system_prompt = AIPrompts.test_case_refinement_system_prompt()
        
        user_prompt = f"""Original Test Case:
{json.dumps(existing_test_case, indent=2)}

User Request for Refinement: "{refinement_prompt}"

IMPORTANT:
- Apply the requested changes
- Ensure all steps are properly ordered and numbered sequentially
- Return the COMPLETE updated test case with ALL fields
- Return ONLY the JSON object, no explanation or markdown
- Make sure the JSON is valid and can be parsed
"""
        
        logger.info(f"Refining test case with prompt: {refinement_prompt}")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=3000,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from OpenAI when refining")
            return existing_test_case
        
        logger.info(f"Raw response from OpenAI: {content[:200]}...")
        
        refined = json.loads(content)
        
        # Validate the refined test case has required fields
        if not _validate_test_case_schema(refined):
            logger.warning("Refined test case failed validation, returning original")
            return existing_test_case
        
        # Ensure steps are properly ordered
        if 'steps' in refined and isinstance(refined['steps'], list):
            for idx, step in enumerate(refined['steps'], 1):
                if 'order' not in step:
                    step['order'] = idx
                # Validate each step has required fields
                if not _validate_step_schema(step):
                    logger.warning(f"Step {idx} failed validation, returning original test case")
                    return existing_test_case
        
        logger.info(f"Successfully refined test case with {len(refined.get('steps', []))} steps")
        return refined
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error when refining: {e}")
        return existing_test_case
    except Exception as e:
        logger.error(f"Error refining test case: {e}", exc_info=True)
        return existing_test_case


def _validate_test_case_schema(test_case: Dict) -> bool:
    """
    Validate that a test case has all required fields and correct structure.
    
    Args:
        test_case: Test case dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['name', 'description', 'steps', 'expected_results']
    
    # Check required fields exist
    for field in required_fields:
        if field not in test_case:
            logger.warning(f"Missing required field in test case: {field}")
            return False
    
    # Validate steps is a list
    if not isinstance(test_case['steps'], list):
        logger.warning("'steps' field must be a list")
        return False
    
    # Validate steps are not empty
    if len(test_case['steps']) == 0:
        logger.warning("Test case must have at least one step")
        return False
    
    # Validate each step
    for idx, step in enumerate(test_case['steps']):
        if not _validate_step_schema(step):
            logger.warning(f"Step {idx + 1} failed validation")
            return False
    
    return True


def _validate_step_schema(step: Dict) -> bool:
    """
    Validate that a test step has all required fields.
    
    Args:
        step: Step dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['order', 'action', 'description', 'expected_result']
    
    # Check required fields exist
    for field in required_fields:
        if field not in step:
            logger.warning(f"Missing required field in step: {field}")
            return False
    
    # Validate action is one of the allowed actions
    allowed_actions = [
        'navigate', 'click', 'fill', 'select', 'wait', 'assert', 
        'check', 'uncheck', 'hover', 'scroll', 'screenshot', 'press', 'type'
    ]
    
    if step['action'] not in allowed_actions:
        logger.warning(f"Invalid action in step: {step['action']}")
        return False
    
    # Validate order is a positive integer
    if not isinstance(step['order'], int) or step['order'] < 1:
        logger.warning(f"Invalid order in step: {step['order']}")
        return False
    
    return True
