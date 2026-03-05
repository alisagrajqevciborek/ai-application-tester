"""
Centralized AI prompt templates for consistent, versioned AI interactions.

This module provides:
- Versioned prompt templates
- Test-type specific prompts
- Structured prompt builders
"""

from typing import Dict, List, Optional

# Version tracking for prompts
PROMPT_VERSION = "1.0.0"


class AIPrompts:
    """Centralized prompt templates for AI operations."""
    
    @staticmethod
    def screenshot_analysis_prompt(test_type: str, issue_context: Optional[Dict] = None) -> str:
        """Generate prompt for screenshot analysis."""
        base_prompt = f"""Analyze this screenshot from a {test_type} test. 
        
Look for:
- Visual issues (layout problems, broken elements, misalignments)
- UI/UX problems (poor spacing, readability issues, accessibility concerns)
- Functional issues visible in the UI
- Any anomalies or errors displayed on the page

"""
        
        if issue_context:
            base_prompt += f"\nContext: {issue_context.get('title', 'Unknown issue')}\n"
        
        base_prompt += "\nProvide a brief analysis (2-3 sentences) focusing on visible issues."
        
        return base_prompt
    
    @staticmethod
    def issue_enhancement_system_prompt() -> str:
        """System prompt for issue description enhancement."""
        return """You are a friendly, helpful assistant who explains website problems in simple, everyday language. You write for non-technical users who need to understand what's wrong and how to fix it. Never use technical jargon unless absolutely necessary, and always explain what it means."""
    
    @staticmethod
    def issue_enhancement_user_prompt(
        issue: Dict,
        test_type: str,
        screenshot_url: Optional[str] = None
    ) -> str:
        """Generate prompt for enhancing issue descriptions."""
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

        return prompt
    
    @staticmethod
    def report_generation_prompt(
        test_results: Dict,
        application_name: str,
        application_url: str,
        test_type: str,
        issues_to_analyze: List[Dict],
        console_logs_data: Optional[List] = None,
        network_failures_data: Optional[List] = None,
        screenshot_urls: Optional[List[str]] = None
    ) -> str:
        """Generate comprehensive prompt for AI report generation."""
        issues = test_results.get('issues', [])
        pass_rate = test_results.get('pass_rate', 0)
        fail_rate = test_results.get('fail_rate', 100)
        status = test_results.get('status', 'failed')
        
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
You are conducting a test-type specific technical analysis. Your report must be tailored to the test type.

"""
        # Add test-type specific sections
        prompt += AIPrompts._get_test_type_specific_instructions(test_type)
        
        return prompt
    
    @staticmethod
    def _get_test_type_specific_instructions(test_type: str) -> str:
        """Get test-type specific analysis instructions."""
        instructions = {
            "functional": """
## FUNCTIONAL TESTING FOCUS

Analyze from a functional correctness perspective:

### 1. Feature Completeness
- What features were tested?
- What passed/failed?
- Any critical user flows broken?

### 2. Issue Analysis
For each critical issue:
- **What broke**: Specific feature/functionality that failed
- **User impact**: What users can't do
- **Repro steps**: Exact steps to reproduce
- **Expected vs Actual**: What should happen vs what happened
- **Fix suggestion**: Code-level fix with examples

### 3. Test Coverage Recommendations
- What wasn't tested that should be?
- Edge cases to add
- Regression risks
""",
            "accessibility": """
## ACCESSIBILITY TESTING FOCUS

Analyze from a WCAG 2.1 AA compliance perspective:

### 1. Violations by WCAG Principle
Group issues by: Perceivable, Operable, Understandable, Robust

### 2. Assistive Technology Impact
For each issue explain:
- **Screen reader impact**: How it affects screen reader users
- **Keyboard navigation**: What keyboard users experience
- **Visual impairments**: Impact on low vision/color blind users
- **WCAG level**: A, AA, or AAA violation
- **Fix with ARIA**: Specific ARIA attributes/roles needed

### 3. Priority Matrix
- Critical blockers for assistive tech
- Quick wins (easy fixes, high impact)
- Long-term improvements
""",
            "performance": """
## PERFORMANCE TESTING FOCUS

Analyze from a Core Web Vitals & speed perspective:

### 1. Metrics Analysis
Report on:
- **LCP (Largest Contentful Paint)**: Target <2.5s
- **FID (First Input Delay)**: Target <100ms
- **CLS (Cumulative Layout Shift)**: Target <0.1
- **Page Load Time**: Target <3s
- **Time to Interactive**: Target <3.8s

### 2. Resource Analysis
Identify bottlenecks:
- Large resources (>500KB)
- Blocking resources
- Render-blocking CSS/JS
- Slow third-party scripts
- Unoptimized images

### 3. Optimization Roadmap
Prioritized fixes:
- **Quick wins**: Compression, caching, CDN
- **Code splitting**: Lazy load recommendations
- **Image optimization**: WebP, responsive images
- **Critical path**: What to inline/defer
""",
            "regression": """
## REGRESSION TESTING FOCUS

Analyze from a stability & compatibility perspective:

### 1. Regression Detection
- What previously worked but now fails?
- New issues vs known issues
- Severity of regressions

### 2. Root Cause Analysis
For each regression:
- **What changed**: Recent code/config changes
- **Impact scope**: What else might be affected
- **Rollback recommendation**: Should this be reverted?
- **Fix priority**: How urgent is this?

### 3. Stability Recommendations
- Flaky tests to investigate
- Areas needing better coverage
- High-risk code patterns
"""
        }
        
        return instructions.get(test_type, instructions["functional"])
    
    @staticmethod
    def test_case_generation_system_prompt() -> str:
        """System prompt for test case generation."""
        return """You are an expert QA engineer specializing in automated web testing with Playwright.

Your task is to convert natural language test descriptions into structured, executable test cases.

If the requested feature/workflow clearly does not exist on the target website, return a non-executable response by setting:
- generation_status: "feature_not_found"
- unavailable_reason: concise human-readable reason
- steps: []

Otherwise, set generation_status to "ready" and provide executable steps.

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
- screenshot: Take a screenshot at this point"""
    
    @staticmethod
    def test_case_refinement_system_prompt() -> str:
        """System prompt for test case refinement."""
        return """You are an expert QA engineer. Your task is to refine existing test cases based on user feedback.

CRITICAL REQUIREMENTS:
1. You MUST preserve the entire JSON structure
2. You MUST include ALL existing steps from the original test case unless explicitly asked to remove them
3. When adding new steps, INSERT them at the appropriate position (not at the end)
4. Ensure step order numbers (order field) are sequential from 1 to N
5. Each step MUST have: order, action, selector, value, description, expected_result
6. Return ONLY valid JSON - no markdown, no code blocks, no explanations

Steps actions: navigate, click, fill, select, wait, assert, check, uncheck, hover, scroll, screenshot, press, type

Always maintain the same test type, tags, estimated_duration, and overall structure unless specifically requested to change them."""


def get_test_type_persona(test_type: str) -> str:
    """Get the appropriate AI persona description for a test type."""
    personas = {
        "functional": "a QA engineer focused on feature correctness and user workflows",
        "accessibility": "an accessibility specialist familiar with WCAG 2.1 and assistive technologies",
        "performance": "a performance engineer focused on Core Web Vitals and optimization",
        "regression": "a QA lead focused on stability and preventing regressions",
        "broken_links": "a web infrastructure specialist focused on link integrity",
        "authentication": "a security-aware QA engineer focused on auth flows"
    }
    return personas.get(test_type, "a QA engineer")
