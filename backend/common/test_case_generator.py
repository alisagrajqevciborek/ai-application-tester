"""
AI-powered test case generator.

This module provides:
- Natural language to test case conversion
- Test case generation using OpenAI
- Structured test case output for Playwright execution
"""

import json
import logging
from typing import Dict, List, Optional
from .ai_helpers import get_openai_client

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
        return _generate_fallback_test_case(user_prompt, application_url, test_type)
    
    try:
        # Build system prompt
        system_prompt = """You are an expert QA engineer specializing in automated web testing with Playwright.

Your task is to convert natural language test descriptions into structured, executable test cases.

Test actions you can use:
- navigate: Go to a URL
- click: Click on an element (button, link, etc.)
- fill: Fill an input field
- select: Select an option from a dropdown
- wait: Wait for an element or condition
- assert: Verify something is true (element visible, text matches, etc.)
- check: Check a checkbox or radio button
- hover: Hover over an element
- scroll: Scroll to an element or position
- screenshot: Take a screenshot at this point

For selectors, prefer:
1. Data attributes (data-testid, data-cy)
2. IDs (#id)
3. CSS classes (.class)
4. Text content (text="Button text")
5. Role-based selectors (role="button")

Always provide:
- Clear, specific selectors
- Expected results for each step
- Error handling considerations
- Realistic test data
"""
        
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
        return existing_test_case
    
    try:
        system_prompt = """You are an expert QA engineer. Your task is to refine existing test cases based on user feedback.

You will receive:
1. An existing test case (JSON format)
2. A refinement request from the user

Apply the refinement and return the updated test case in the same JSON format.
Maintain all existing steps unless explicitly asked to remove them.
Add new steps where requested.
Modify steps if the user asks for changes.
"""
        
        user_prompt = f"""Existing Test Case:
{json.dumps(existing_test_case, indent=2)}

User Refinement Request: "{refinement_prompt}"

Apply the refinement and return the complete updated test case as JSON with the same structure.
Return ONLY the JSON, no markdown, no code blocks, no explanations.
"""
        
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
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            return existing_test_case
        
        refined = json.loads(content)
        logger.info("Successfully refined test case")
        return refined
        
    except Exception as e:
        logger.error(f"Error refining test case: {e}", exc_info=True)
        return existing_test_case
