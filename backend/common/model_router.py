"""
Centralized model routing for all OpenAI-powered features.

Models can be overridden via Django settings or environment variables:
- OPENAI_MODEL                 — universal override for all features
- SCREENSHOT_ANALYSIS_MODEL
- REPORT_GENERATION_MODEL
- ISSUE_ENHANCEMENT_MODEL
- TEST_CASE_GENERATION_MODEL
- TEST_CASE_REFINEMENT_MODEL
"""

import os
from django.conf import settings

_FALLBACK_MODEL = "gpt-4o"


def _get_model(setting_name: str, env_name: str) -> str:
    """
    Resolve model name from, in order of precedence:
    1) Django settings.<setting_name>  (feature-specific override)
    2) Environment variable <env_name>  (feature-specific override)
    3) Django settings.OPENAI_MODEL  (universal override)
    4) OPENAI_MODEL environment variable  (universal override)
    5) Hard-coded default (gpt-4o)
    """
    # Feature-specific Django setting
    value = getattr(settings, setting_name, None)
    if isinstance(value, str) and value.strip():
        return value.strip()

    # Feature-specific environment variable
    env_value = os.getenv(env_name)
    if env_value and env_value.strip():
        return env_value.strip()

    # Universal OPENAI_MODEL Django setting
    universal = getattr(settings, "OPENAI_MODEL", None)
    if isinstance(universal, str) and universal.strip():
        return universal.strip()

    # Universal OPENAI_MODEL environment variable
    universal_env = os.getenv("OPENAI_MODEL")
    if universal_env and universal_env.strip():
        return universal_env.strip()

    return _FALLBACK_MODEL


# Screenshot analysis — uses vision, benefits most from a stronger model
SCREENSHOT_ANALYSIS_MODEL = _get_model(
    "SCREENSHOT_ANALYSIS_MODEL",
    "SCREENSHOT_ANALYSIS_MODEL",
)

# Full test report generation (functional, accessibility, performance, regression)
REPORT_GENERATION_MODEL = _get_model(
    "REPORT_GENERATION_MODEL",
    "REPORT_GENERATION_MODEL",
)

# Plain-English rewriting of individual issue descriptions
ISSUE_ENHANCEMENT_MODEL = _get_model(
    "ISSUE_ENHANCEMENT_MODEL",
    "ISSUE_ENHANCEMENT_MODEL",
)

# Converts natural language prompts into structured Playwright test cases
TEST_CASE_GENERATION_MODEL = _get_model(
    "TEST_CASE_GENERATION_MODEL",
    "TEST_CASE_GENERATION_MODEL",
)

# Refines an existing test case based on user feedback
TEST_CASE_REFINEMENT_MODEL = _get_model(
    "TEST_CASE_REFINEMENT_MODEL",
    "TEST_CASE_REFINEMENT_MODEL",
)
