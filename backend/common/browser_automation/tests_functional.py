"""
Functional test suite.
"""
import logging
from typing import Dict, Optional, List
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def run_functional_tests(
    page: Page,
    url: str,
    screenshots_dir: Optional[str],
    console_logs: List[Dict],
    network_failures: List[Dict],
    main_document_headers: Dict,
    issue_manager
) -> Dict:
    """Run functional tests - check basic page functionality."""
    issues = []
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Page title
    try:
        title = await page.title()
        if title:
            tests_passed += 1
            if len(title) > 60:
                await issue_manager.add_issue(
                    issues, 'minor', 'Page title is too long',
                    f'Page title is {len(title)} characters. Recommended: 50-60 characters for optimal SEO.',
                    url, page
                )
        else:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'major', 'Page title missing',
                'The page does not have a title tag, which is required for SEO and browser tabs.',
                url, page
            )
    except Exception as e:
        tests_failed += 1
        await issue_manager.add_issue(
            issues, 'critical', 'Failed to get page title',
            str(e), url, page
        )
    
    # Test 2: Main content
    try:
        main_content = await page.query_selector('main, [role="main"], body > div')
        if main_content:
            tests_passed += 1
        else:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'minor', 'No main content area found',
                'The page does not have a clear main content area (main tag or [role="main"]).',
                url, page
            )
    except Exception:
        tests_failed += 1
    
    # Test 3: Links
    try:
        links = await page.query_selector_all('a[href]')
        if len(links) > 0:
            tests_passed += 1
            empty_links = 0
            for link in links[:20]:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                if not href or href == '#' or (not text or text.strip() == ''):
                    empty_links += 1
            
            if empty_links > 0:
                await issue_manager.add_issue(
                    issues, 'minor', f'{empty_links} empty or placeholder link(s) found',
                    'Some links have empty href attributes (#) or no visible text, which can confuse users.',
                    url, page
                )
        else:
            await issue_manager.add_issue(
                issues, 'minor', 'No links found on page',
                'The page does not contain any navigation links, which may limit user navigation.',
                url, page
            )
    except Exception as e:
        logger.warning(f"Error checking links: {e}")
    
    # Test 4: Meta tags
    try:
        meta_description = await page.query_selector('meta[name="description"]')
        if not meta_description:
            await issue_manager.add_issue(
                issues, 'minor', 'Meta description missing',
                'The page is missing a meta description tag, which is important for SEO and social sharing.',
                url, page
            )
        else:
            desc_content = await meta_description.get_attribute('content')
            if desc_content:
                if len(desc_content) > 160:
                    await issue_manager.add_issue(
                        issues, 'minor', 'Meta description is too long',
                        f'Meta description is {len(desc_content)} characters. Recommended: 150-160 characters for optimal display in search results.',
                        url, page, meta_description
                    )
                elif len(desc_content) < 50:
                    await issue_manager.add_issue(
                        issues, 'minor', 'Meta description is too short',
                        f'Meta description is {len(desc_content)} characters. Recommended: 120-160 characters for better SEO.',
                        url, page, meta_description
                    )
        
        og_title = await page.query_selector('meta[property="og:title"]')
        og_description = await page.query_selector('meta[property="og:description"]')
        if not og_title or not og_description:
            issues.append({
                'severity': 'minor',
                'title': 'Open Graph tags incomplete',
                'description': 'Missing Open Graph tags (og:title, og:description) which are important for social media sharing previews.',
                'location': url
            })
        
        json_ld = await page.query_selector_all('script[type="application/ld+json"]')
        if len(json_ld) == 0:
            issues.append({
                'severity': 'minor',
                'title': 'Structured data (JSON-LD) missing',
                'description': 'No structured data found. Adding JSON-LD schema markup can improve search engine understanding and rich results.',
                'location': url
            })
        
        canonical = await page.query_selector('link[rel="canonical"]')
        if not canonical:
            issues.append({
                'severity': 'minor',
                'title': 'Canonical URL missing',
                'description': 'Missing canonical URL tag, which helps prevent duplicate content issues in SEO.',
                'location': url
            })
    except Exception as e:
        logger.warning(f"Error checking meta tags: {e}")
    
    # Test 5: Forms
    try:
        forms = await page.query_selector_all('form')
        if len(forms) > 0:
            tests_passed += 1
            for form in forms[:5]:
                form_id = await form.get_attribute('id')
                form_name = await form.get_attribute('name')
                if not form_id and not form_name:
                    await issue_manager.add_issue(
                        issues, 'minor', 'Form missing identifier',
                        'A form on the page lacks an id or name attribute, making it harder to reference.',
                        url, page, form
                    )
                
                submit_buttons = await form.query_selector_all('button[type="submit"], input[type="submit"]')
                if len(submit_buttons) == 0:
                    await issue_manager.add_issue(
                        issues, 'major', 'Form missing submit button',
                        'A form on the page does not have a visible submit button, which may prevent form submission.',
                        url, page, form
                    )
    except Exception as e:
        logger.warning(f"Error checking forms: {e}")
    
    # Test 6: Console errors/warnings
    console_errors = [log for log in console_logs if log['type'] == 'error']
    console_warnings = [log for log in console_logs if log['type'] == 'warning']
    
    if console_errors:
        tests_failed += 1
        for error in console_errors[:5]:
            log_idx = next((i for i, log in enumerate(console_logs) if log == error), None)
            await issue_manager.add_issue(
                issues, 'major', 'Console error detected',
                f"JavaScript console error: {error.get('text', 'Unknown error')}",
                error.get('location', url), page,
                console_log_index=log_idx,
                console_logs=console_logs
            )
    
    if console_warnings:
        for warning in console_warnings[:3]:
            log_idx = next((i for i, log in enumerate(console_logs) if log == warning), None)
            await issue_manager.add_issue(
                issues, 'minor', 'Console warning detected',
                f"JavaScript console warning: {warning.get('text', 'Unknown warning')}",
                warning.get('location', url), page,
                console_log_index=log_idx,
                console_logs=console_logs
            )
    
    # Test 7: Network failures
    # Exclude 401/403 — these are access-controlled resources, not broken ones.
    reportable_failures = [f for f in network_failures if f['status'] not in (401, 403)]
    if reportable_failures:
        tests_failed += 1
        for failure in reportable_failures[:5]:
            severity = 'major' if failure['status'] >= 500 else 'minor'
            await issue_manager.add_issue(
                issues, severity, f"Network request failed ({failure['status']})",
                f"Failed to load resource: {failure['url']} (Status: {failure['status']} {failure['status_text']})",
                failure['url'], page
            )
    
    # Test 8: Security headers
    try:
        if not url.startswith('https://'):
            await issue_manager.add_issue(
                issues, 'major', 'Site not using HTTPS',
                'The site is not using HTTPS, which is a security risk and can affect SEO rankings. Migrate to HTTPS.',
                url, page
            )
        
        if main_document_headers:
            headers = main_document_headers
            security_headers = {
                'strict-transport-security': 'HSTS header missing - helps prevent man-in-the-middle attacks. Add: Strict-Transport-Security: max-age=31536000; includeSubDomains',
                'x-content-type-options': 'X-Content-Type-Options header missing - prevents MIME type sniffing. Add: X-Content-Type-Options: nosniff',
                'x-frame-options': 'X-Frame-Options header missing - helps prevent clickjacking attacks. Add: X-Frame-Options: DENY or SAMEORIGIN',
                'content-security-policy': 'Content-Security-Policy header missing - helps prevent XSS and injection attacks. Add appropriate CSP policy.',
                'referrer-policy': 'Referrer-Policy header missing - controls referrer information sent. Add: Referrer-Policy: strict-origin-when-cross-origin'
            }
            
            for header, description in security_headers.items():
                header_found = any(h.lower() == header.lower() for h in headers.keys())
                if not header_found:
                    await issue_manager.add_issue(
                        issues, 'minor', f'Missing security header: {header}',
                        description, url, page
                    )
    except Exception as e:
        logger.warning(f"Error checking security headers: {e}")
    
    # Test 9: Responsive design
    try:
        viewport_meta = await page.query_selector('meta[name="viewport"]')
        if not viewport_meta:
            await issue_manager.add_issue(
                issues, 'major', 'Viewport meta tag missing',
                'Missing viewport meta tag, which is essential for responsive design on mobile devices. Add: <meta name="viewport" content="width=device-width, initial-scale=1">',
                url, page
            )
        else:
            viewport_content = await viewport_meta.get_attribute('content')
            if viewport_content and 'width=device-width' not in viewport_content:
                await issue_manager.add_issue(
                    issues, 'minor', 'Viewport meta tag may be incomplete',
                    f'Viewport meta tag content: {viewport_content}. Ensure it includes "width=device-width" for proper mobile rendering.',
                    url, page, viewport_meta
                )
        
        touch_targets = await page.query_selector_all('button, a, input, [role="button"]')
        small_touch_targets = 0
        for target in touch_targets[:20]:
            try:
                box = await target.bounding_box()
                if box:
                    min_size = min(box['width'], box['height'])
                    if min_size < 44:
                        small_touch_targets += 1
            except Exception as e:
                logger.debug(f"Error checking touch target size: {e}")
                continue
        
        if small_touch_targets > 0:
            issues.append({
                'severity': 'minor',
                'title': f'{small_touch_targets} small touch target(s) found',
                'description': f'{small_touch_targets} interactive element(s) are smaller than 44x44px, which can be difficult to tap on mobile devices.',
                'location': url
            })
    except Exception as e:
        logger.warning(f"Error checking responsive design: {e}")
    
    # Calculate pass rate
    issue_penalty = 0
    for issue in issues:
        severity = issue.get('severity', 'minor')
        if severity == 'critical':
            issue_penalty += 3
        elif severity == 'major':
            issue_penalty += 2
        elif severity == 'minor':
            issue_penalty += 0.5
    
    total_tests = tests_passed + tests_failed
    total_points = total_tests + issue_penalty
    pass_rate = round(tests_passed / total_points * 100) if total_points > 0 else 100
    fail_rate = 100 - pass_rate
    
    return {
        'pass_rate': pass_rate,
        'fail_rate': fail_rate,
        'status': 'success' if fail_rate < 30 else 'failed',
        'issues': issues,
        'screenshots': []
    }
