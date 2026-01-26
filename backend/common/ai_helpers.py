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
        prompt = f"""You are a senior QA engineer, UX analyst, and web performance expert with 10+ years of experience.

You are analyzing a web application that was tested automatically using browser automation (Playwright).
You do NOT have direct access to the live application.
You must rely ONLY on the provided evidence (screenshots, console logs, network data, automated findings).

CRITICAL INSTRUCTIONS:
1. Be SPECIFIC and ACTIONABLE - every recommendation must include concrete steps
2. Reference EVIDENCE - cite specific console errors, network failures, or automated findings
3. Prioritize by USER IMPACT - focus on issues that affect real users
4. Provide CODE-LEVEL HINTS when possible - suggest specific fixes (e.g., "Add aria-label to button", "Set width/height on images")
5. Be TECHNICAL but ACCESSIBLE - explain why issues matter and how to fix them
6. CORRELATE findings - connect console errors with network failures, performance issues with resource sizes
7. DO NOT speculate - only report what the evidence supports
8. If screenshots are provided, ANALYZE THEM CAREFULLY - describe what you see, identify visual issues

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
        
        # Add console logs
        console_logs = test_results.get('console_logs', [])
        if console_logs:
            console_errors = [log for log in console_logs if log.get('type') == 'error']
            console_warnings = [log for log in console_logs if log.get('type') == 'warning']
            if console_errors or console_warnings:
                prompt += f"\nConsole Messages:\n"
                if console_errors:
                    prompt += f"  Errors ({len(console_errors)}):\n"
                    for error in console_errors[:10]:  # First 10 errors
                        prompt += f"    - {error.get('text', 'Unknown error')}\n"
                if console_warnings:
                    prompt += f"  Warnings ({len(console_warnings)}):\n"
                    for warning in console_warnings[:10]:  # First 10 warnings
                        prompt += f"    - {warning.get('text', 'Unknown warning')}\n"
        
        # Add network failures
        network_failures = test_results.get('network_failures', [])
        if network_failures:
            prompt += f"\nNetwork Failures ({len(network_failures)}):\n"
            for failure in network_failures[:10]:  # First 10 failures
                prompt += f"  - {failure.get('url', 'Unknown URL')} (Status: {failure.get('status', 'Unknown')} {failure.get('status_text', '')})\n"
                prompt += f"    Resource Type: {failure.get('resource_type', 'unknown')}\n"
        
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
Based on the screenshots, console logs, network requests, and automated findings, determine:
1. What type of application this is (e.g., e-commerce, SaaS dashboard, blog, portfolio, etc.)
2. The primary user goals (what are users trying to accomplish?)
3. The technology stack hints (React/Vue/Angular, CMS, etc.) based on console logs and network requests

Explain your reasoning in 2–3 sentences, citing specific evidence.

────────────────────────
STEP 2 — CRITICAL ISSUES ANALYSIS
────────────────────────
Identify and analyze CRITICAL issues first - these block core functionality or create security risks.

For each critical issue:
1. **What's broken?** - Clear description
2. **Evidence** - Specific console error, network failure, or automated finding
3. **User impact** - How does this affect real users? (e.g., "Users cannot submit forms", "Page fails to load on mobile")
4. **Root cause** - What's likely causing this? (e.g., "Missing error handling", "CORS issue", "JavaScript error")
5. **Fix steps** - Concrete, actionable steps:
   - Code-level changes (e.g., "Add try-catch around fetch()", "Set image dimensions")
   - Configuration changes (e.g., "Add CORS headers", "Enable HTTPS")
   - Testing steps (e.g., "Test in Chrome DevTools", "Verify in mobile viewport")
6. **Verification** - How to confirm the fix works

────────────────────────
STEP 3 — PERFORMANCE & CORE WEB VITALS
────────────────────────
Analyze performance issues, especially Core Web Vitals (LCP, CLS, FID).

For performance issues:
1. **Metric** - What metric is poor? (e.g., "LCP is 4.2s", "CLS is 0.25")
2. **Impact** - Why this matters (SEO, user experience, conversion)
3. **Root cause** - What's causing it? (e.g., "Large unoptimized images", "Render-blocking CSS", "Too many network requests")
4. **Fix steps** - Specific optimizations:
   - Image optimization (e.g., "Convert to WebP", "Add width/height attributes", "Use srcset")
   - Code splitting (e.g., "Lazy load non-critical JS", "Split vendor bundles")
   - Resource hints (e.g., "Add preload for critical fonts", "Use rel=preconnect for external domains")
5. **Expected improvement** - What should the metric be after fix?

────────────────────────
STEP 4 — FUNCTIONAL & USER EXPERIENCE ISSUES
────────────────────────
Analyze issues that affect functionality and user experience.

For each issue:
1. **What's wrong?** - Clear description
2. **Evidence** - Screenshot observation, console log, or automated finding
3. **User impact** - How does this frustrate or confuse users?
4. **Fix steps** - Specific changes:
   - HTML/CSS changes (e.g., "Add aria-label", "Increase touch target size to 44x44px")
   - JavaScript fixes (e.g., "Add error handling", "Fix event listener")
   - UX improvements (e.g., "Add loading states", "Improve error messages")
5. **Verification** - How to test the fix

────────────────────────
STEP 5 — ACCESSIBILITY & INCLUSIVENESS
────────────────────────
Analyze accessibility issues that affect users with disabilities.

For each accessibility issue:
1. **What's inaccessible?** - Clear description
2. **WCAG violation** - Which guideline is violated? (e.g., "WCAG 2.1 Level A: Missing alt text")
3. **User impact** - How does this affect screen reader users, keyboard users, etc.?
4. **Fix steps** - Specific accessibility improvements:
   - ARIA attributes (e.g., "Add aria-label='Close dialog'", "Use aria-describedby for error messages")
   - Semantic HTML (e.g., "Use <nav> for navigation", "Add <main> landmark")
   - Keyboard navigation (e.g., "Ensure focus order is logical", "Add visible focus indicators")
5. **Testing** - How to test with screen readers or keyboard-only navigation

────────────────────────
STEP 6 — SECURITY & BEST PRACTICES
────────────────────────
Analyze security issues and best practice violations.

For each security/best practice issue:
1. **What's the risk?** - Clear description
2. **Evidence** - Missing header, insecure connection, etc.
3. **Impact** - What could happen? (e.g., "XSS vulnerability", "Clickjacking risk")
4. **Fix steps** - Specific security improvements:
   - Headers (e.g., "Add Content-Security-Policy", "Set X-Frame-Options: DENY")
   - HTTPS (e.g., "Migrate to HTTPS", "Enable HSTS")
   - Code practices (e.g., "Sanitize user input", "Use parameterized queries")

────────────────────────
STEP 7 — SEO & DISCOVERABILITY
────────────────────────
Analyze SEO issues that affect search engine visibility.

For each SEO issue:
1. **What's missing?** - Clear description
2. **Impact** - How does this affect search rankings?
3. **Fix steps** - Specific SEO improvements:
   - Meta tags (e.g., "Add og:image", "Set canonical URL")
   - Structured data (e.g., "Add JSON-LD schema", "Implement breadcrumb markup")
   - Technical SEO (e.g., "Fix broken links", "Optimize page speed")

────────────────────────
STEP 8 — CORRELATION & PATTERNS
────────────────────────
Look for patterns and correlations in the evidence:
- Do console errors correlate with network failures?
- Are performance issues caused by specific resources?
- Are multiple issues pointing to the same root cause?

Identify these patterns and provide consolidated recommendations.

────────────────────────
STEP 9 — OVERALL ASSESSMENT
────────────────────────
Provide a comprehensive summary:
1. **Overall Quality Score** - Rate 1-10 with reasoning
2. **Main Strengths** - What's working well?
3. **Critical Risks** - What must be fixed immediately?
4. **Quick Wins** - What can be fixed easily for big impact?
5. **Long-term Improvements** - What should be prioritized next?

────────────────────────
OUTPUT FORMAT
────────────────────────
Return your response in this EXACT structure (use markdown formatting):

# Application Analysis Report

## Application Context
[2-3 sentences describing the app type and user goals, with evidence]

## Critical Issues (Must Fix Immediately)
### [Issue Title] - [Severity]
- **Evidence:** [Specific console error, network failure, or finding]
- **User Impact:** [How this affects users]
- **Root Cause:** [What's causing this]
- **Fix Steps:**
  1. [Specific step 1]
  2. [Specific step 2]
  3. [Specific step 3]
- **Code Hint:** [If applicable, specific code change]
- **Verification:** [How to test the fix]

[Repeat for each critical issue]

## Performance Issues
### [Performance Issue Title]
- **Metric:** [Specific metric and value]
- **Impact:** [Why this matters]
- **Root Cause:** [What's causing poor performance]
- **Optimization Steps:**
  1. [Specific optimization]
  2. [Specific optimization]
- **Expected Improvement:** [Target metric after fix]

[Repeat for each performance issue]

## Functional & UX Issues
[Same format as Critical Issues]

## Accessibility Issues
[Same format, include WCAG guideline]

## Security & Best Practices
[Same format]

## SEO Issues
[Same format]

## Patterns & Correlations
[Describe any patterns found in the evidence]

## Overall Assessment
- **Quality Score:** [1-10] - [Reasoning]
- **Main Strengths:** [What's working well]
- **Critical Risks:** [What must be fixed]
- **Quick Wins:** [Easy fixes with big impact]
- **Long-term Priorities:** [What to focus on next]

────────────────────────
IMPORTANT REMINDERS
────────────────────────
- Be SPECIFIC - "Add aria-label" not "improve accessibility"
- Reference EVIDENCE - cite console errors, network failures, screenshots
- Provide ACTIONABLE steps - developers should know exactly what to do
- Prioritize USER IMPACT - focus on what affects real users
- Include CODE HINTS when possible - specific HTML/CSS/JS changes
- DO NOT speculate - only report what evidence supports"""

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
