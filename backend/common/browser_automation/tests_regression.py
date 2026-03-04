"""
Regression test suite.
"""
import logging
from typing import Dict, Optional, List
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def run_regression_tests(
    page: Page,
    url: str,
    screenshots_dir: Optional[str],
    console_logs: List[Dict],
    network_failures: List[Dict],
    issue_manager
) -> Dict:
    """Run regression tests - check for broken functionality."""
    issues = []
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: JavaScript errors
    js_errors = []
    def handle_page_error(error):
        js_errors.append(str(error))
    
    page.on('pageerror', handle_page_error)
    await page.wait_for_timeout(3000)
    
    if len(js_errors) == 0:
        tests_passed += 1
    else:
        tests_failed += 1
        for error in js_errors[:5]:
            await issue_manager.add_issue(
                issues, 'critical', 'JavaScript runtime error detected',
                f'Uncaught JavaScript error: {error}', url, page
            )
    
    # Test 2: Broken images
    try:
        images = await page.query_selector_all('img')
        broken_images = []
        for img in images[:20]:
            try:
                natural_width = await img.evaluate('el => el.naturalWidth')
                if natural_width == 0:
                    src = await img.get_attribute('src')
                    broken_images.append(src or 'unknown')
            except Exception as e:
                logger.debug(f"Error checking image naturalWidth: {e}")
                src = await img.get_attribute('src')
                broken_images.append(src or 'unknown')
        
        if len(broken_images) == 0:
            tests_passed += 1
        else:
            tests_failed += 1
            broken_img_elem = None
            for img in images[:20]:
                try:
                    natural_width = await img.evaluate('el => el.naturalWidth')
                    if natural_width == 0:
                        broken_img_elem = img
                        break
                except Exception as e:
                    logger.debug(f"Error re-checking broken image candidate: {e}")
                    continue
            
            await issue_manager.add_issue(
                issues, 'major', f'{len(broken_images)} broken image(s) found',
                f'Images failed to load: {", ".join(broken_images[:3])}{"..." if len(broken_images) > 3 else ""}',
                url, page, broken_img_elem
            )
    except Exception as e:
        logger.warning(f"Error checking images: {e}")
    
    # Test 3: Broken external links
    try:
        links = await page.query_selector_all('a[href^="http"]')
        broken_links = []
        for link in links[:10]:
            href = await link.get_attribute('href')
            if href and href.startswith('http'):
                for failure in network_failures:
                    if failure['url'] == href and failure['status'] == 404:
                        broken_links.append(href)
                        break
        
        if broken_links:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'major', f'{len(broken_links)} broken external link(s) found',
                f'External links returned 404: {", ".join(broken_links[:3])}{"..." if len(broken_links) > 3 else ""}',
                url, page
            )
    except Exception as e:
        logger.warning(f"Error checking external links: {e}")
    
    # Test 4: Console errors
    console_errors = [log for log in console_logs if log['type'] == 'error']
    if console_errors:
        tests_failed += 1
        for error in console_errors[:5]:
            log_idx = next((i for i, log in enumerate(console_logs) if log == error), None)
            await issue_manager.add_issue(
                issues, 'major', 'Console error in regression test',
                f"Console error: {error.get('text', 'Unknown')}",
                error.get('location', url), page,
                console_log_index=log_idx,
                console_logs=console_logs
            )
    
    # Test 5: Missing resources
    missing_resources = [f for f in network_failures if f['resource_type'] in ['stylesheet', 'script', 'font']]
    if missing_resources:
        tests_failed += 1
        resource_types = {}
        for res in missing_resources:
            res_type = res['resource_type']
            resource_types[res_type] = resource_types.get(res_type, 0) + 1
        
        for res_type, count in resource_types.items():
            severity = 'critical' if res_type == 'stylesheet' else 'major'
            await issue_manager.add_issue(
                issues, severity, f'{count} missing {res_type}(s)',
                f'Failed to load {count} {res_type} resource(s), which may break page functionality or styling.',
                url, page
            )
    
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
        'status': 'success' if fail_rate < 20 else 'failed',
        'issues': issues,
        'screenshots': []
    }
