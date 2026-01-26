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
        prompt = f"""You are a senior QA engineer writing a DETAILED, ACTIONABLE bug report.

Context:
- Test type: {test_type}
- Application/page: {issue.get('location', 'Unknown')}

Evidence (automated finding):
- Title: {issue.get('title', 'Unknown')}
- Severity: {issue.get('severity', 'unknown')}
- Description: {issue.get('description', 'No description')}

Task:
Transform this into a comprehensive, developer-friendly bug report with SPECIFIC fixes.

Requirements:
1. **Be SPECIFIC** - Include exact code snippets, not pseudocode
2. **Provide CONTEXT** - Explain why this matters
3. **Show CODE** - Include before/after examples
4. **Be ACTIONABLE** - Developers should know exactly what to do
5. **Include VERIFICATION** - How to test the fix works

Output format (markdown, use these exact headings):

## 🔍 What Happened (Evidence)
- [Specific description of what was found]
- [Any observable symptoms]

## 💥 Why It Matters (Impact)
- **User Impact**: [How this affects users]
- **Business Impact**: [SEO, conversion, accessibility, etc.]
- **Technical Debt**: [Long-term consequences if not fixed]

## 🔎 Root Cause (Analysis)
- **Likely Cause**: [Technical explanation]
- **Code Location**: [Where the problem likely exists]
- **Related Systems**: [What else might be affected]

## 🛠️ How to Fix (Concrete Steps with Code)

### Step 1: [Action description]
```[language]
// Before (current problematic code)
[show what's wrong]

// After (corrected code)
[show the fix]
```
**Why this works**: [Brief explanation]

### Step 2: [Next action]
```[language]
[code example]
```

### Step 3: [Final action]
[Configuration change, testing step, etc.]

## ✅ Verification Checklist
- [ ] [Specific test 1]
- [ ] [Specific test 2]
- [ ] [Expected outcome]

## 📚 Additional Resources
- [Link to relevant documentation if applicable]
- [Best practice reference]

CRITICAL: Include ACTUAL code snippets, not placeholders. Be as specific as possible."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional QA engineer who writes clear, actionable bug reports with specific code examples."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1500,  # Increased for detailed bug reports
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
            max_tokens=10000,  # Increased for comprehensive reports with code examples
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
