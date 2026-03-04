"""
Centralized model routing for all OpenAI-powered features.

Models can be overridden via Django settings or environment variables:
- SCREENSHOT_ANALYSIS_MODEL
- REPORT_GENERATION_MODEL
- ISSUE_ENHANCEMENT_MODEL
- TEST_CASE_GENERATION_MODEL
- TEST_CASE_REFINEMENT_MODEL
"""

import os
from django.conf import settings


def _get_model(setting_name: str, env_name: str, default: str) -> str:
    """
    Resolve model name from, in order of precedence:
    1) Django settings.<setting_name>
    2) Environment variable <env_name>
    3) Provided default
    """
    # Prefer explicit Django setting
    value = getattr(settings, setting_name, None)
    if isinstance(value, str) and value.strip():
        return value.strip()

    # Then fall back to environment variable
    env_value = os.getenv(env_name)
    if env_value and env_value.strip():
        return env_value.strip()

    # Finally, use hard-coded default
    return default


# Screenshot analysis — uses vision, benefits most from a stronger model
SCREENSHOT_ANALYSIS_MODEL = _get_model(
    "SCREENSHOT_ANALYSIS_MODEL",
    "SCREENSHOT_ANALYSIS_MODEL",
    default="gpt-5",
)

# Full test report generation (functional, accessibility, performance, regression)
REPORT_GENERATION_MODEL = _get_model(
    "REPORT_GENERATION_MODEL",
    "REPORT_GENERATION_MODEL",
    default="gpt-4o",
)

# Plain-English rewriting of individual issue descriptions
ISSUE_ENHANCEMENT_MODEL = _get_model(
    "ISSUE_ENHANCEMENT_MODEL",
    "ISSUE_ENHANCEMENT_MODEL",
    default="gpt-4o-mini",
)

# Converts natural language prompts into structured Playwright test cases
TEST_CASE_GENERATION_MODEL = _get_model(
    "TEST_CASE_GENERATION_MODEL",
    "TEST_CASE_GENERATION_MODEL",
    default="gpt-4o-mini",
)

# Refines an existing test case based on user feedback
TEST_CASE_REFINEMENT_MODEL = _get_model(
    "TEST_CASE_REFINEMENT_MODEL",
    "TEST_CASE_REFINEMENT_MODEL",
    default="gpt-4o-mini",
)
