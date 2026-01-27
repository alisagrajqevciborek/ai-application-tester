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
        # Build the prompt based on test type
        prompt = f"""Analyze this screenshot from a {test_type} test. 
        
Look for:
- Visual issues (layout problems, broken elements, misalignments)
- UI/UX problems (poor spacing, readability issues, accessibility concerns)
- Functional issues visible in the UI
- Any anomalies or errors displayed on the page

"""
        
        if issue_context:
            prompt += f"\nContext: {issue_context.get('title', 'Unknown issue')}\n"
        
        prompt += "\nProvide a brief analysis (2-3 sentences) focusing on visible issues."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Changed from gpt-4o to reduce costs
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
            temperature=0.3
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
    # If OpenAI is not available/configured, fall back to deterministic templates.
    from common.issue_explanations import build_structured_issue_explanation

    client = get_openai_client()
    if not client:
        enhanced_issue = issue.copy()
        enhanced_issue['description'] = build_structured_issue_explanation(issue, test_type=test_type)
        enhanced_issue['ai_enhanced'] = False
        enhanced_issue['description_generated'] = True
        return enhanced_issue
    
    try:
        # Build rich context for AI
        screenshot_context = ""
        if screenshot_url:
            screenshot_context = f"\n\nScreenshot available: {screenshot_url}\nAnalyze the screenshot to understand the visual context. Describe what you see and how it relates to the problem."
        
        # Build detailed context for grouped issues
        grouped_context = ""
        if issue.get('is_grouped'):
            frequency = issue.get('frequency', 1)
            group_type = issue.get('group_type', 'Issue')
            resource_types = issue.get('resource_types', [])
            resource_urls = issue.get('resource_urls', [])
            error_types = issue.get('error_types', [])
            locations = issue.get('affected_locations', [])
            
            grouped_context = f"""
This is a GROUPED issue - it happened {frequency} time(s) across your website.

Issue Type: {group_type}
"""
            if resource_types:
                grouped_context += f"Resource Types Affected: {', '.join(resource_types)}\n"
            if resource_urls:
                grouped_context += f"Failed Resources ({len(resource_urls)}):\n"
                for url in resource_urls[:3]:
                    filename = url.split('/')[-1] if '/' in url else url
                    grouped_context += f"  - {filename}\n"
                if len(resource_urls) > 3:
                    grouped_context += f"  ... and {len(resource_urls) - 3} more\n"
            if error_types:
                grouped_context += f"Error Types: {', '.join(error_types)}\n"
            if locations:
                grouped_context += f"Affected Pages: {len(locations)} page(s)\n"
        
        prompt = f"""You are a helpful QA assistant explaining a website issue in simple, friendly language that anyone can understand.

Context:
- Test type: {test_type}
- Page/URL: {issue.get('location', 'Unknown')}
- Issue severity: {issue.get('severity', 'unknown')}
{grouped_context}

The Issue:
- Title: {issue.get('title', 'Unknown')}
- Description: {issue.get('description', 'No description')}
{screenshot_context}

Your Task:
COMPLETELY REWRITE the description in simple, friendly language. Do NOT just enhance it - replace the technical description with a clear, user-friendly explanation.

Requirements:
1. **What's wrong** - Explain in plain English what failed (e.g., "Your website tried to load 2 font files but couldn't")
2. **What visitors see** - Be specific about what users will experience (e.g., "Text appears in a different font than intended" or "Images show as broken")
3. **Why it matters** - Explain the impact in simple terms
4. **How to fix** - Provide clear, actionable steps

CRITICAL INSTRUCTIONS:
- IGNORE the technical description provided - it's just context for you
- Write a COMPLETELY NEW description from scratch
- Use everyday language - no technical terms unless you explain them
- For grouped issues, explain what type of files failed and what that means for visitors
- Be specific and concrete - avoid vague statements

Example of good explanation:
"Your website tried to load 2 custom font files, but they failed to load. This means visitors will see text in a default font instead of your custom font, which can make your website look different than you intended. This affects your brand consistency and can make the site look less professional."

Output format (markdown, be friendly and clear, max 600 words):

## What's Wrong?
[2-3 sentences in plain English. Example: "Your website tried to load 2 font files (alef-2c57b332.woff2 and BeatriceTRIAL-Regular.otf) but they failed to load due to a network error."]

## What This Means
[3-4 sentences explaining the real-world impact]
- **For visitors:** [Be very specific: "Text will appear in a fallback font (like Arial or Times New Roman) instead of your custom font. This makes your website look different from what you designed."]
- **For your business:** [Explain business impact: "This affects your brand consistency and can make your website look less professional or unfinished."]

## Suggested Fix
[Clear, step-by-step instructions]

1. [First step in plain language - be specific]
2. [Next step]
3. [Final step if needed]

[If screenshot is available, mention what you see: "In the screenshot, you can see..."]

## Quick Check
After fixing, you should see: [Specific thing to verify - be concrete]

Remember: Write as if explaining to someone who has never heard of fonts, network errors, or web development. Use analogies if helpful!"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Changed from gpt-4o to reduce costs
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly, helpful assistant who explains website problems in simple, everyday language. You write for non-technical users who need to understand what's wrong and how to fix it. Never use technical jargon unless absolutely necessary, and always explain what it means."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,  # Increased to allow for more detailed explanations
            temperature=0.3  # Slightly higher for more natural language
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
        fail_rate = test_results.get('fail_rate', 100)
        status = test_results.get('status', 'failed')
        
        # Only include critical/major issues in prompt to reduce tokens
        critical_issues = [i for i in issues if i.get('severity') in ['critical', 'major']]
        issues_to_analyze = critical_issues[:10]  # Limit to top 10 critical/major issues
        
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
Total Issues Found: {len(issues)} (analyzing top {len(issues_to_analyze)} critical/major)

────────────────────────
EVIDENCE PROVIDED
────────────────────────
"""
        
        # Limit screenshots to 2 most important
        if screenshot_urls:
            prompt += f"Screenshots Available: {len(screenshot_urls)} total (analyzing first 2)\n"
        
        # Truncate console logs to top 5
        console_logs_data = console_logs or test_results.get('console_logs', [])
        if console_logs_data:
            console_errors = [log for log in console_logs_data if log.get('type') == 'error'][:5]
            console_warnings = [log for log in console_logs_data if log.get('type') == 'warning'][:5]
            if console_errors or console_warnings:
                prompt += f"\nConsole Messages:\n"
                if console_errors:
                    prompt += f"  Errors ({len(console_errors)}):\n"
                    for error in console_errors:
                        error_text = error.get('text', 'Unknown error')
                        prompt += f"    - {error_text[:200]}\n"  # Truncate long messages
                if console_warnings:
                    prompt += f"  Warnings ({len(console_warnings)}):\n"
                    for warning in console_warnings:
                        warning_text = warning.get('text', 'Unknown warning')
                        prompt += f"    - {warning_text[:200]}\n"  # Truncate long messages
        
        # Truncate network failures to top 5
        network_failures_data = network_failures or test_results.get('network_failures', [])
        if network_failures_data:
            prompt += f"\nNetwork Failures (showing top 5):\n"
            for failure in network_failures_data[:5]:
                url = failure.get('url', 'Unknown URL')
                prompt += f"  - {url[:100]} (Status: {failure.get('status', 'Unknown')})\n"
        
        if issues_to_analyze:
            prompt += "\nCritical/Major Issues:\n"
            for idx, issue in enumerate(issues_to_analyze, 1):
                issue_desc = issue.get('description', 'No description')
                prompt += f"  {idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown')}\n"
                prompt += f"     {issue_desc[:150]}\n\n"  # Truncate descriptions
        
        prompt += """
────────────────────────
YOUR TASK: COMPREHENSIVE TECHNICAL ANALYSIS
────────────────────────
You are conducting a DEEP technical analysis of this web application. Your report must be:
1. **HIGHLY SPECIFIC** - Include exact code snippets, file types, and technical details
2. **ACTIONABLE** - Every issue must have concrete fix steps with code examples
3. **EVIDENCE-BASED** - Reference specific console errors, network failures, or test findings
4. **PRIORITIZED** - Focus on high-impact issues first
5. **CORRELATED** - Connect related issues to identify root causes

────────────────────────
ANALYSIS FRAMEWORK
────────────────────────

## STEP 1: Application Context & Technology Detection
Analyze the evidence to determine:
- **Application Type**: (e.g., SaaS dashboard, e-commerce, blog, marketing site)
- **Primary User Goals**: What are users trying to accomplish?
- **Technology Stack**: Based on console logs, network requests, and code patterns:
  * Frontend Framework: (React, Vue, Angular, vanilla JS, etc.)
  * Build Tool: (Webpack, Vite, Next.js, etc.)
  * CSS Framework: (Tailwind, Bootstrap, custom, etc.)
  * Backend Hints: (API patterns, server headers)
- **Evidence**: Cite specific console messages, network requests, or code patterns

## STEP 2: Critical Issues (Blockers & High-Impact)
For EACH critical issue, provide:

### Issue: [Clear, specific title]
**Severity**: CRITICAL
**Category**: [Performance | Functionality | Security | Accessibility]

**What's Broken**:
- [Specific description of the problem]

**Evidence**:
```
[Exact console error, network failure, or test finding]
```

**User Impact**:
- [How this affects real users - be specific]
- [Business impact if applicable]

**Root Cause Analysis**:
- [Technical explanation of why this is happening]
- [Likely code location or component]

**Fix Steps** (with code):
1. **[Action 1]**
   ```[language]
   // Before (problematic code)
   [show current code if known]
   
   // After (fixed code)
   [show corrected code]
   ```
   
2. **[Action 2]**
   ```[language]
   [specific code change]
   ```

3. **[Action 3]** - [Configuration or testing step]

**Verification**:
- [ ] [Specific test to confirm fix works]
- [ ] [Expected outcome after fix]

**Related Issues**: [List any related issues that might be caused by the same root problem]

---

## STEP 3: Performance Analysis (Core Web Vitals + Optimization)

### Performance Metrics Summary
| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| LCP | [X.X]s | <2.5s | ❌/✅ |
| CLS | [X.XX] | <0.1 | ❌/✅ |
| FID/TBT | [X]ms | <100ms | ❌/✅ |
| Page Load | [X.X]s | <3s | ❌/✅ |

### Performance Issue: [Specific metric problem]

**Current Performance**:
- [Metric]: [Current value] (Target: [Target value])

**Impact**:
- SEO: [How this affects search rankings]
- UX: [How this affects user experience]
- Conversion: [Potential impact on business metrics]

**Root Cause**:
- [What's causing the poor performance]
- [Specific resources or code patterns]

**Optimization Steps**:

1. **[Optimization technique]**
   ```html
   <!-- Example: Add preload for critical resources -->
   <link rel="preload" href="/critical-font.woff2" as="font" type="font/woff2" crossorigin>
   ```

2. **[Code-level optimization]**
   ```javascript
   // Before: Render-blocking script
   <script src="analytics.js"></script>
   
   // After: Async loading
   <script async src="analytics.js"></script>
   ```

3. **[Build/Config optimization]**
   ```javascript
   // webpack.config.js or vite.config.js
   optimization: {
     splitChunks: {
       chunks: 'all',
       maxSize: 244000, // 244KB chunks
     }
   }
   ```

**Expected Improvement**: [Metric] should improve from [X] to [Y]

**Resource Analysis**:
- Large Images: [List specific large images with sizes]
- JavaScript Bundles: [List bundles > 200KB]
- Render-Blocking Resources: [List specific files]

---

## STEP 4: Functional & UX Issues

[Same detailed format as Critical Issues, but for functional problems]

Include:
- Form validation issues with code fixes
- Navigation problems with specific solutions
- Interactive element failures with debugging steps
- Error handling gaps with try-catch examples

---

## STEP 5: Accessibility (WCAG Compliance)

### Accessibility Issue: [Specific problem]
**WCAG Violation**: [e.g., "WCAG 2.1 Level A - 1.1.1 Non-text Content"]
**Severity**: [Critical | Major | Minor]

**What's Inaccessible**:
- [Specific element or pattern that's inaccessible]

**Affected Users**:
- Screen reader users: [How they're affected]
- Keyboard-only users: [How they're affected]
- Users with [specific disability]: [Impact]

**Fix Steps**:

1. **Add ARIA attributes**
   ```html
   <!-- Before -->
   <button>×</button>
   
   <!-- After -->
   <button aria-label="Close dialog" aria-describedby="dialog-title">×</button>
   ```

2. **Use semantic HTML**
   ```html
   <!-- Before -->
   <div class="nav">...</div>
   
   <!-- After -->
   <nav aria-label="Main navigation">...</nav>
   ```

3. **Ensure keyboard navigation**
   ```javascript
   // Add keyboard event handlers
   element.addEventListener('keydown', (e) => {
     if (e.key === 'Enter' || e.key === ' ') {
       handleClick();
     }
   });
   ```

**Testing**:
- Test with NVDA/JAWS screen reader
- Test keyboard-only navigation (Tab, Enter, Escape)
- Use axe DevTools to verify fix

---

## STEP 6: Security & Best Practices

### Security Issue: [Specific vulnerability]

**Risk Level**: [Critical | High | Medium | Low]

**Vulnerability**:
- [What security risk exists]

**Potential Impact**:
- [What could happen if exploited]

**Fix Steps**:

1. **Add security headers**
   ```nginx
   # nginx configuration
   add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'";
   add_header X-Frame-Options "DENY";
   add_header X-Content-Type-Options "nosniff";
   ```

2. **Implement input sanitization**
   ```javascript
   // Sanitize user input
   function sanitizeInput(input) {
     return input.replace(/[<>]/g, '');
   }
   ```

---

## STEP 7: SEO Optimization

[List SEO issues with specific meta tag fixes, structured data examples, etc.]

---

## STEP 8: Issue Correlation & Root Cause Patterns

**Pattern 1: [Common root cause]**
- Related Issues: [List 3-5 issues caused by this]
- Root Cause: [Technical explanation]
- Consolidated Fix: [Single fix that addresses multiple issues]

**Pattern 2: [Another pattern]**
- [Same format]

**Dependency Graph**:
```
Fix A (missing CSS) → Fixes Issues 1, 3, 7
  ↓
Fix B (optimize images) → Fixes Issues 2, 4
  ↓
Fix C (add ARIA) → Fixes Issues 5, 6
```

**Recommended Fix Order**:
1. [Fix A] - Blocks [X] other fixes
2. [Fix B] - High impact, easy to implement
3. [Fix C] - Requires Fix A to be completed first

---

## STEP 9: Overall Assessment & Recommendations

### Quality Score: [X]/10
**Reasoning**: [2-3 sentences explaining the score]

### Strengths:
- ✅ [What's working well]
- ✅ [Another strength]

### Critical Risks (Fix Immediately):
1. 🔴 [Critical issue] - [Why it's urgent]
2. 🔴 [Another critical issue]

### Quick Wins (High Impact, Low Effort):
1. 🎯 [Easy fix with big impact] - Estimated time: [X minutes]
2. 🎯 [Another quick win]

### Long-term Priorities:
1. 📋 [Strategic improvement]
2. 📋 [Another long-term goal]

### Estimated Fix Time:
- Critical issues: [X hours]
- Major issues: [X hours]
- Minor issues: [X hours]
- **Total**: [X hours]

────────────────────────
OUTPUT FORMAT REQUIREMENTS
────────────────────────
- Use markdown formatting with headers, code blocks, tables
- Include actual code snippets for EVERY fix (not pseudocode)
- Reference specific line numbers when possible
- Use emojis for visual scanning (🔴 critical, ⚠️ warning, ✅ good, 🎯 quick win)
- Include "Before/After" code examples
- Cite evidence with ```code blocks```
- Create tables for metrics and comparisons
- Use checklists for verification steps

CRITICAL: Be SPECIFIC. "Optimize images" is too vague. Instead: "Convert hero.jpg (2.4MB) to WebP format and add width/height attributes: <img src='hero.webp' width='1200' height='800' alt='...'>"
"""

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
            model="gpt-4o",  # Keep gpt-4o for main report (most important)
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
            temperature=0.2
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
