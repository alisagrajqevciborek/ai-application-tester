"""
Browser automation service using Playwright for automated testing.
"""
from .runner import BrowserAutomationService, run_test_sync

__all__ = ['BrowserAutomationService', 'run_test_sync']
