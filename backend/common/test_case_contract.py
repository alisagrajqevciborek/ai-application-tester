"""Shared contract for AI-generated test case actions."""

from __future__ import annotations

from typing import Tuple


ALLOWED_STEP_ACTIONS: Tuple[str, ...] = (
    'navigate',
    'click',
    'fill',
    'select',
    'wait',
    'assert',
    'check',
    'uncheck',
    'hover',
    'scroll',
    'screenshot',
    'press',
    'type',
)


def actions_as_csv() -> str:
    """Return allowed actions as a comma-separated string."""
    return ', '.join(ALLOWED_STEP_ACTIONS)
