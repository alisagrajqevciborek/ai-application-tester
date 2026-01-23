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
        return OpenAI(api_key=api_key)  # type: ignore[name-defined]
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
    
    try:
        # Build the prompt based on test type
        prompt = f"""Analyze this screenshot from a {test_type} test. 
        
Look for:
- Visual issues (layout problems, broken elements, misalignments)
- UI/UX problems (poor spacing, readability issues, accessibility concerns)
- Functional issues visible in the UI
- Any anomalies or errors displayed on the page

"""
        
        if issue_context:
            prompt += f"\nContext: {issue_context.get('title', 'Unknown issue')} - {issue_context.get('description', 'No description')}\n"
        
        prompt += "\nProvide a detailed analysis of what you see in the screenshot, focusing on any issues or problems. Be specific about what's wrong and where it appears."
        
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o for vision capabilities
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
            max_tokens=500,
            temperature=0.3  # Lower temperature for more focused analysis
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
    
    Args:
        issue: Issue dictionary with title, description, severity, location
        screenshot_url: Optional screenshot URL to analyze
        test_type: Type of test
        
    Returns:
        Enhanced issue dictionary with improved description
    """
    client = get_openai_client()
    if not client:
        return issue  # Return original issue if AI is not available
    
    try:
        # Build prompt for enhancing the issue description with concrete fix guidance
        prompt = f"""You are a senior QA engineer writing an actionable bug report based ONLY on the provided evidence.

Context:
- Test type: {test_type}
- Application/page: {issue.get('location', 'Unknown')}

Evidence (automated finding):
- Title: {issue.get('title', 'Unknown')}
- Severity: {issue.get('severity', 'unknown')}
- Description: {issue.get('description', 'No description')}

Task:
Rewrite the issue into a stronger, more detailed, developer-friendly bug report with FIX suggestions.

Rules:
- Do NOT speculate beyond the evidence. If something is uncertain, say "Evidence insufficient".
- Be specific and practical. Prefer concrete steps and checks.

Output format (markdown, exactly these headings):
**What happened (evidence):**
- ...

**Why it matters (impact):**
- ...

**Likely cause (hypothesis, if supported):**
- ...

**How to fix (concrete steps):**
- Step 1 ...
- Step 2 ...
- Step 3 ...

**How to verify the fix:**
- ...
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional QA engineer who writes clear, actionable bug reports."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=700,
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        if not content:
            return issue  # Return original if no content
        enhanced_description = content.strip()
        
        # If we have a screenshot, analyze it and add to description
        screenshot_analysis = None
        if screenshot_url:
            screenshot_analysis = analyze_screenshot_with_ai(screenshot_url, test_type, issue)
            if screenshot_analysis:
                enhanced_description += f"\n\n**Screenshot analysis (evidence):**\n{screenshot_analysis}"
        
        # Return enhanced issue
        enhanced_issue = issue.copy()
        enhanced_issue['description'] = enhanced_description
        enhanced_issue['ai_enhanced'] = True
        
        logger.info(f"Successfully enhanced issue description for: {issue.get('title')}")
        return enhanced_issue
        
    except Exception as e:
        logger.error(f"Error enhancing issue description: {e}", exc_info=True)
        return issue  # Return original issue on error


def generate_ai_report(
    test_results: Dict,
    application_name: str,
    application_url: str,
    test_type: str,
    screenshot_urls: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Generate an AI-enhanced test report.
    
    Args:
        test_results: Dictionary with pass_rate, fail_rate, status, issues
        application_name: Name of the application tested
        application_url: URL of the application
        test_type: Type of test performed
        screenshot_urls: List of screenshot URLs (optional)
        
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
        fail_rate = test_results.get('fail_rate', 100)
        status = test_results.get('status', 'failed')
        
        # Build comprehensive prompt using structured QA/UX analysis format
        prompt = f"""You are a senior QA engineer and UX analyst.

You are analyzing a web application that was tested automatically using browser automation.
You do NOT have direct access to the live application.
You must rely ONLY on the provided evidence.

────────────────────────
TEST CONTEXT
────────────────────────
Application Name: {application_name}
Application URL: {application_url}
Test Type: {test_type}
Test Status: {status}
Pass Rate: {pass_rate}%
Fail Rate: {fail_rate}%
Total Issues Found: {len(issues)}

────────────────────────
EVIDENCE PROVIDED
────────────────────────
"""
        
        if screenshot_urls:
            prompt += f"Screenshots Available: {len(screenshot_urls)} screenshot(s)\n"
            for idx, screenshot_url in enumerate(screenshot_urls, 1):
                prompt += f"  Screenshot {idx}: {screenshot_url}\n"
        
        if issues:
            prompt += "\nAutomated Test Findings:\n"
            for idx, issue in enumerate(issues, 1):
                prompt += f"  {idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown')}\n"
                prompt += f"     Description: {issue.get('description', 'No description')}\n"
                prompt += f"     Location: {issue.get('location', 'Unknown')}\n\n"
        
        prompt += """
────────────────────────
STEP 1 — CONTEXT UNDERSTANDING
────────────────────────
Based on the content, UI elements, terminology, navigation flow, and interactions visible in the evidence,
briefly determine what type of application this appears to be.

Explain your reasoning in 2–3 sentences.
Do not assume a domain unless the evidence supports it.

────────────────────────
STEP 2 — QUALITY PRIORITIES
────────────────────────
Based on the identified application context, determine which quality aspects are most important
for users of this system.

Consider (but do not limit yourself to):
- Usability and clarity
- Functional correctness
- Error handling and feedback
- Trust, safety, and reliability
- Accessibility and inclusiveness

Briefly explain which aspects you are prioritizing and why.

────────────────────────
STEP 3 — EVIDENCE-BASED ANALYSIS
────────────────────────
Analyze the application strictly using the provided evidence.

Evidence may include:
- Screenshots
- Console errors
- Network errors
- Navigation steps
- Visible UI states

Identify issues that could negatively impact a real user.
Only report issues that are directly supported by the evidence.
Do NOT speculate.

────────────────────────
STEP 4 — ISSUE CLASSIFICATION
────────────────────────
For each identified issue:
- Describe the issue clearly
- Reference the supporting evidence
- Classify its severity as one of:
  • Critical — blocks or seriously harms core usage
  • Moderate — degrades experience but does not block usage
  • Minor — cosmetic or low-impact issue
- Explain the potential user impact
- Provide a recommendation for improvement that includes concrete fix steps (and, if relevant, a brief code-level hint or the likely area to change)
- Include a short "How to verify the fix" checklist

────────────────────────
STEP 5 — ACCESSIBILITY & TRUST CHECK
────────────────────────
If applicable based on the context, assess:
- Visual clarity and readability
- Feedback and error messaging
- Consistency and predictability
- Signals of trust and professionalism

Only include points relevant to the identified application type.

────────────────────────
STEP 6 — FINAL SUMMARY
────────────────────────
Provide:
- A brief overall quality assessment
- The main strengths
- The most important risks or weaknesses

────────────────────────
OUTPUT FORMAT
────────────────────────
Return your response in the following structure:

Application Context:
- Identified type and reasoning

Quality Priorities:
- Key focus areas

Issues:
- [Severity] Issue title
  - Evidence:
  - Impact:
  - Recommendation (how to fix):
  - How to verify:

Accessibility & Trust:
- Observations (if applicable)

Overall Assessment:
- Summary"""

        # If screenshots are available, include them in the vision analysis
        messages_content = []
        
        if screenshot_urls:
            # Use vision model for screenshot analysis
            vision_prompt = prompt + "\n\nIMPORTANT: Analyze the provided screenshots carefully. Describe what you see in the UI, identify visual issues, and correlate them with the automated test findings. Use the screenshots as primary evidence for your analysis."
            
            messages_content.append({
                "type": "text",
                "text": vision_prompt
            })
            
            # Add all screenshots
            for screenshot_url in screenshot_urls[:5]:  # Limit to first 5 screenshots to avoid token limits
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
            model="gpt-4o",
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
            max_tokens=3500,  # More room for concrete fix suggestions
            temperature=0.2  # More focused, less fluffy
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
