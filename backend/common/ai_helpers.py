"""
AI integration module for enhanced test reporting and analysis.

This module provides:
- OpenAI API client configuration
- Enhanced report generation using AI
- Screenshot analysis using vision models
- Issue description enhancement
"""

import logging
import os
from typing import Dict, List, Optional
from django.conf import settings
from .ai_prompts import AIPrompts
from .model_router import (
    SCREENSHOT_ANALYSIS_MODEL,
    REPORT_GENERATION_MODEL,
    ISSUE_ENHANCEMENT_MODEL,
)

logger = logging.getLogger(__name__)

# Try to import OpenAI, but handle gracefully if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. AI features will be disabled.")


def get_openai_client() -> Optional['OpenAI']:  # type: ignore[name-defined]
    """
    Get OpenAI client instance.
    
    Returns:
        OpenAI client if API key is configured, None otherwise
    """
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        logger.warning("OpenAI API key not configured. AI features will be disabled.")
        return None
    
    try:
        # Use a conservative default timeout; individual calls can still override.
        client = OpenAI(api_key=api_key, timeout=20)  # type: ignore[name-defined]
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None


def analyze_screenshot_with_ai(
    screenshot_url: str,
    test_type: str,
    issue_context: Optional[Dict] = None
) -> Optional[str]:
    """
    Analyze a screenshot using OpenAI Vision API to identify issues.
    OPTIMIZED: Only use for critical/major issues, uses cheaper model.
    
    Args:
        screenshot_url: URL of the screenshot to analyze
        test_type: Type of test (functional, regression, performance, accessibility)
        issue_context: Optional context about the issue found
        
    Returns:
        AI-generated analysis of the screenshot, or None if analysis fails
    """
    client = get_openai_client()
    if not client:
        return None
    
    # Only analyze screenshots for critical/major issues to reduce costs
    if issue_context and issue_context.get('severity') not in ['critical', 'major']:
        return None
    
    try:
        # Use centralized prompt from ai_prompts module
        prompt = AIPrompts.screenshot_analysis_prompt(test_type, issue_context)
        
        response = client.chat.completions.create(
            model=SCREENSHOT_ANALYSIS_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": screenshot_url
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,  # Reduced from 500
            temperature=0.3,
            timeout=30,
        )
        
        analysis = response.choices[0].message.content
        logger.info(f"Successfully analyzed screenshot with AI")
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing screenshot with AI: {e}", exc_info=True)
        return None


def enhance_issue_description(
    issue: Dict,
    screenshot_url: Optional[str] = None,
    test_type: str = "functional"
) -> Dict:
    """
    Enhance an issue description using AI analysis.
    OPTIMIZED: Uses cheaper model, skips screenshot analysis to reduce costs.
    
    Args:
        issue: Issue dictionary with title, description, severity, location
        screenshot_url: Optional screenshot URL to analyze (ignored for cost optimization)
        test_type: Type of test
        
    Returns:
        Enhanced issue dictionary with improved description
    """
    # Always provide a user-friendly, structured explanation.
    # Prefer deterministic templates as they're faster and more reliable.
    # Use AI only for complex grouped issues or when explicitly needed.
    from common.issue_explanations import build_structured_issue_explanation

    # Check if we should use deterministic explanation (preferred for most cases)
    is_complex_grouped = issue.get('is_grouped') and issue.get('frequency', 1) > 3
    client = get_openai_client()
    
    # Use deterministic explanation for simple cases (faster, more cost-effective)
    if not client or not is_complex_grouped:
        enhanced_issue = issue.copy()
        enhanced_issue['description'] = build_structured_issue_explanation(issue, test_type=test_type)
        enhanced_issue['ai_enhanced'] = False
        enhanced_issue['description_generated'] = True
        return enhanced_issue
    
    try:
        # Use centralized prompt from ai_prompts module
        prompt = AIPrompts.issue_enhancement_user_prompt(issue, test_type, screenshot_url)

        response = client.chat.completions.create(
            model=ISSUE_ENHANCEMENT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": AIPrompts.issue_enhancement_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,  # Increased to allow for more detailed explanations
            temperature=0.3,  # Slightly higher for more natural language
            timeout=40,
        )
        
        content = response.choices[0].message.content
        if not content:
            enhanced_issue = issue.copy()
            enhanced_issue['description'] = build_structured_issue_explanation(issue, test_type=test_type)
            enhanced_issue['ai_enhanced'] = False
            enhanced_issue['description_generated'] = True
            return enhanced_issue
        
        # The AI response should be the complete, user-friendly description
        # It should replace the technical description entirely
        enhanced_description = content.strip()
        
        # SKIP screenshot analysis to save costs (most expensive operation)
        # Screenshots are analyzed in the main report anyway
        
        # Return enhanced issue - COMPLETELY replace the description
        enhanced_issue = issue.copy()
        enhanced_issue['description'] = enhanced_description  # This replaces the technical description
        enhanced_issue['ai_enhanced'] = True
        enhanced_issue['description_generated'] = True
        
        logger.info(f"Successfully enhanced issue description for: {issue.get('title')}")
        return enhanced_issue
        
    except Exception as e:
        logger.error(f"Error enhancing issue description: {e}", exc_info=True)
        enhanced_issue = issue.copy()
        enhanced_issue['description'] = build_structured_issue_explanation(issue, test_type=test_type)
        enhanced_issue['ai_enhanced'] = False
        enhanced_issue['description_generated'] = True
        return enhanced_issue


def generate_ai_report(
    test_results: Dict,
    application_name: str,
    application_url: str,
    test_type: str,
    screenshot_urls: Optional[List[str]] = None,
    console_logs: Optional[List] = None,
    network_failures: Optional[List] = None,
    network_requests: Optional[List] = None
) -> Dict[str, str]:
    """
    Generate an AI-enhanced test report.
    OPTIMIZED: Reduced tokens, limited screenshots, truncated data.
    
    Args:
        test_results: Dictionary with pass_rate, fail_rate, status, issues
        application_name: Name of the application tested
        application_url: URL of the application
        test_type: Type of test performed
        screenshot_urls: List of screenshot URLs (optional)
        console_logs: List of console logs (optional)
        network_failures: List of network failures (optional)
        network_requests: List of network requests (optional)
        
    Returns:
        Dictionary with 'summary' and 'detailed_report' keys
    """
    client = get_openai_client()
    if not client:
        # Fallback to basic report generation
        return _generate_basic_report(test_results, application_name, application_url, test_type)
    
    try:
        issues = test_results.get('issues', [])
        pass_rate = test_results.get('pass_rate', 0)
        status = test_results.get('status', 'failed')
        
        # Only include critical/major issues in prompt to reduce tokens
        critical_issues = [i for i in issues if i.get('severity') in ['critical', 'major']]
        issues_to_analyze = critical_issues[:10]  # Limit to top 10 critical/major issues
        
        # Get console logs and network failures
        console_logs_data = console_logs or test_results.get('console_logs', [])
        network_failures_data = network_failures or test_results.get('network_failures', [])
        
        # Use centralized prompt from ai_prompts module
        prompt = AIPrompts.report_generation_prompt(
            test_results=test_results,
            application_name=application_name,
            application_url=application_url,
            test_type=test_type,
            issues_to_analyze=issues_to_analyze,
            console_logs_data=console_logs_data,
            network_failures_data=network_failures_data,
            screenshot_urls=screenshot_urls
        )

        # If screenshots are available, include them in the vision analysis
        messages_content = []
        
        # Limit to 2 screenshots max (most expensive part)
        screenshots_to_analyze = screenshot_urls[:2] if screenshot_urls else []
        
        if screenshots_to_analyze:
            # Use vision model for screenshot analysis
            vision_prompt = prompt + "\n\nIMPORTANT: Analyze the provided screenshots carefully. Describe what you see in the UI, identify visual issues, and correlate them with the automated test findings. Use the screenshots as primary evidence for your analysis."
            
            messages_content.append({
                "type": "text",
                "text": vision_prompt
            })
            
            # Add limited screenshots
            for screenshot_url in screenshots_to_analyze:
                messages_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": screenshot_url
                    }
                })
        else:
            messages_content.append({
                "type": "text",
                "text": prompt
            })
        
        response = client.chat.completions.create(
            model=REPORT_GENERATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior QA engineer and UX analyst with expertise in web application testing, accessibility, and user experience design. You provide thorough, evidence-based analysis."
                },
                {
                    "role": "user",
                    "content": messages_content
                }
            ],
            max_tokens=4000,  # Reduced from 10000 for cost optimization
            temperature=0.2,
            timeout=60,
        )
        
        ai_response = response.choices[0].message.content
        
        # Parse the structured response
        summary = ""
        detailed_report = ""
        
        if ai_response:
            # Extract summary from "Overall Assessment" section
            if "Overall Assessment:" in ai_response:
                assessment_parts = ai_response.split("Overall Assessment:")
                if len(assessment_parts) > 1:
                    summary = assessment_parts[1].strip()
                    # Take first 2-3 sentences for summary
                    sentences = summary.split('. ')
                    summary = '. '.join(sentences[:3])
                    if not summary.endswith('.'):
                        summary += '.'
            
            # Use the full AI response as detailed report
            detailed_report = ai_response
            
            # If no summary extracted, create one from the assessment
            if not summary:
                summary = f"Test suite completed with {pass_rate}% pass rate. {'All tests passed.' if status == 'success' else f'{len(issues)} issue(s) found requiring attention.'}"
        else:
            # Fallback if no response
            summary = f"Test suite completed with {pass_rate}% pass rate. {'All tests passed.' if status == 'success' else f'{len(issues)} issue(s) found.'}"
            detailed_report = ""
        
        # Append complete automated test findings for reference
        if issues:
            detailed_report += "\n\n" + "="*60 + "\n"
            detailed_report += "AUTOMATED TEST FINDINGS (REFERENCE)\n"
            detailed_report += "="*60 + "\n\n"
            detailed_report += "The following issues were detected by automated browser testing:\n\n"
            
            for idx, issue in enumerate(issues, 1):
                detailed_report += f"{idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown issue')}\n"
                detailed_report += f"   Description: {issue.get('description', 'No description')}\n"
                detailed_report += f"   Location: {issue.get('location', 'Unknown')}\n"
                if idx < len(issues):
                    detailed_report += "\n"
        
        logger.info(f"Successfully generated AI-enhanced report for {application_name}")
        
        return {
            'summary': summary,
            'detailed_report': detailed_report
        }
        
    except Exception as e:
        logger.error(f"Error generating AI report: {e}", exc_info=True)
        # Fallback to basic report
        return _generate_basic_report(test_results, application_name, application_url, test_type)


def _generate_basic_report(
    test_results: Dict,
    application_name: str,
    application_url: str,
    test_type: str
) -> Dict[str, str]:
    """
    Generate a basic report without AI (fallback).
    
    Args:
        test_results: Dictionary with test results
        application_name: Name of the application
        application_url: URL of the application
        test_type: Type of test
        
    Returns:
        Dictionary with 'summary' and 'detailed_report' keys
    """
    issues = test_results.get('issues', [])
    pass_rate = test_results.get('pass_rate', 0)
    fail_rate = test_results.get('fail_rate', 100)
    status = test_results.get('status', 'failed')
    
    if status == 'success':
        summary = f"Test suite completed successfully with {pass_rate}% pass rate. All critical user flows were validated."
    else:
        critical_count = sum(1 for issue in issues if issue.get('severity') == 'critical')
        major_count = sum(1 for issue in issues if issue.get('severity') == 'major')
        summary = f"Test suite encountered {fail_rate}% failures. {critical_count} critical and {major_count} major issues found."
    
    detailed_report = f"Test execution completed for {application_name} ({application_url}).\n\n"
    detailed_report += f"Test Type: {test_type}\n"
    detailed_report += f"Status: {status}\n"
    detailed_report += f"Pass Rate: {pass_rate}%\n"
    detailed_report += f"Fail Rate: {fail_rate}%\n\n"
    
    if issues:
        detailed_report += "Issues Found:\n"
        for idx, issue in enumerate(issues, 1):
            detailed_report += f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown issue')}\n"
            detailed_report += f"   Description: {issue.get('description', 'No description')}\n"
            detailed_report += f"   Location: {issue.get('location', 'Unknown')}\n"
    else:
        detailed_report += "No issues found during testing.\n"
    
    return {
        'summary': summary,
        'detailed_report': detailed_report
    }
