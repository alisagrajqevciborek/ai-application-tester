"""
Accessibility test suite.
"""
import logging
from typing import Dict, Optional, List
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def run_accessibility_tests(
    page: Page,
    url: str,
    screenshots_dir: Optional[str],
    console_logs: List[Dict],
    issue_manager
) -> Dict:
    """Run accessibility tests - check WCAG compliance."""
    issues = []
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Image alt text
    try:
        images = await page.query_selector_all('img')
        images_without_alt = []
        images_with_empty_alt = []
        for img in images:
            alt = await img.get_attribute('alt')
            if alt is None:
                images_without_alt.append(img)
            elif alt.strip() == '':
                images_with_empty_alt.append(img)
        
        if len(images_without_alt) == 0 and len(images_with_empty_alt) == 0:
            tests_passed += 1
        else:
            tests_failed += 1
            if images_without_alt:
                await issue_manager.add_issue(
                    issues, 'major', f'{len(images_without_alt)} image(s) missing alt text',
                    'Images without alt text are not accessible to screen readers. Add descriptive alt attributes to all images.',
                    url, page, images_without_alt[0]
                )
            if images_with_empty_alt:
                await issue_manager.add_issue(
                    issues, 'minor', f'{len(images_with_empty_alt)} image(s) with empty alt text',
                    'Images with empty alt attributes should be decorative. If they convey information, add descriptive alt text.',
                    url, page, images_with_empty_alt[0]
                )
    except Exception as e:
        logger.warning(f"Error checking image alt text: {e}")
    
    # Test 2: Heading hierarchy
    try:
        headings = await page.query_selector_all('h1, h2, h3, h4, h5, h6')
        if len(headings) > 0:
            h1 = await page.query_selector('h1')
            if h1:
                tests_passed += 1
                h1_count = len(await page.query_selector_all('h1'))
                if h1_count > 1:
                    await issue_manager.add_issue(
                        issues, 'minor', f'Multiple H1 headings found ({h1_count})',
                        'Pages should typically have only one H1 heading for proper document structure and SEO.',
                        url, page, h1
                    )
            else:
                tests_failed += 1
                await issue_manager.add_issue(
                    issues, 'major', 'Missing H1 heading',
                    'The page does not have an H1 heading, which is important for accessibility, SEO, and document structure.',
                    url, page
                )
            
            heading_levels = []
            for heading in headings[:20]:
                tag_name = await heading.evaluate('el => el.tagName.toLowerCase()')
                level = int(tag_name[1])
                heading_levels.append(level)
            
            for i in range(len(heading_levels) - 1):
                if heading_levels[i+1] - heading_levels[i] > 1:
                    issues.append({
                        'severity': 'minor',
                        'title': 'Heading hierarchy skipped',
                        'description': f'Heading levels jump from H{heading_levels[i]} to H{heading_levels[i+1]}, which can confuse screen reader users.',
                        'location': url
                    })
                    break
        else:
            tests_failed += 1
            issues.append({
                'severity': 'major',
                'title': 'No headings found',
                'description': 'The page has no heading elements, which makes it difficult for screen reader users to navigate.',
                'location': url
            })
    except Exception as e:
        logger.warning(f"Error checking heading hierarchy: {e}")
    
    # Test 3: ARIA labels
    try:
        interactive_elements = await page.query_selector_all('button, input, select, textarea, a[href]')
        elements_without_labels = []
        for elem in interactive_elements[:30]:
            aria_label = await elem.get_attribute('aria-label')
            aria_labelledby = await elem.get_attribute('aria-labelledby')
            id_attr = await elem.get_attribute('id')
            
            tag_name = await elem.evaluate('el => el.tagName.toLowerCase()')
            if tag_name == 'input' or tag_name == 'textarea' or tag_name == 'select':
                label = await page.query_selector(f'label[for="{id_attr}"]')
                if not label and not aria_label and not aria_labelledby:
                    parent_label = await elem.evaluate('el => el.closest("label")')
                    if not parent_label:
                        elements_without_labels.append(tag_name)
            elif tag_name == 'button' or (tag_name == 'a' and not aria_label):
                text = await elem.inner_text()
                if not text.strip() and not aria_label:
                    elements_without_labels.append(tag_name)
        
        if elements_without_labels:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'major', f'{len(elements_without_labels)} interactive element(s) missing labels',
                'Interactive elements without labels are not accessible to screen readers. Add aria-label, aria-labelledby, or associate with <label> elements.',
                url, page
            )
    except Exception as e:
        logger.warning(f"Error checking ARIA labels: {e}")
    
    # Test 4: Form labels
    try:
        inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[type="password"], input[type="number"], textarea, select')
        inputs_without_labels = 0
        for inp in inputs[:20]:
            inp_id = await inp.get_attribute('id')
            name = await inp.get_attribute('name')
            aria_label = await inp.get_attribute('aria-label')
            aria_labelledby = await inp.get_attribute('aria-labelledby')
            
            has_label = False
            if inp_id:
                label = await page.query_selector(f'label[for="{inp_id}"]')
                if label:
                    has_label = True
            
            if not has_label:
                parent_label = await inp.evaluate('el => el.closest("label")')
                if parent_label:
                    has_label = True
            
            if not has_label and not aria_label and not aria_labelledby:
                inputs_without_labels += 1
        
        if inputs_without_labels > 0:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'major', f'{inputs_without_labels} form field(s) missing labels',
                'Form fields without labels are not accessible. Associate each input with a <label> element or use aria-label.',
                url, page, inputs[0] if inputs else None
            )
    except Exception as e:
        logger.warning(f"Error checking form labels: {e}")
    
    # Test 5: Color contrast (basic check)
    try:
        elements_with_color = await page.query_selector_all('[style*="color"], [style*="background"]')
        if len(elements_with_color) > 50:
            await issue_manager.add_issue(
                issues, 'minor', 'Many inline color styles detected',
                'Pages with many inline color styles may have contrast issues. Use CSS classes and ensure WCAG AA contrast ratios (4.5:1 for text).',
                url, page
            )
    except Exception as e:
        logger.warning(f"Error checking color contrast hints: {e}")
    
    # Test 6: Keyboard navigation
    try:
        negative_tabindex = await page.query_selector_all('[tabindex="-1"]')
        if len(negative_tabindex) > 10:
            await issue_manager.add_issue(
                issues, 'minor', 'Many elements with negative tabindex',
                f'{len(negative_tabindex)} elements have tabindex="-1", which removes them from keyboard navigation. Ensure this is intentional.',
                url, page, negative_tabindex[0] if negative_tabindex else None
            )
    except Exception as e:
        logger.warning(f"Error checking tabindex: {e}")
    
    # Test 7: Lang attribute
    try:
        html_lang = await page.query_selector('html')
        if html_lang:
            lang = await html_lang.get_attribute('lang')
            if not lang:
                await issue_manager.add_issue(
                    issues, 'minor', 'Missing lang attribute on HTML element',
                    'The <html> element should have a lang attribute to help screen readers pronounce content correctly.',
                    url, page, html_lang
                )
    except Exception as e:
        logger.warning(f"Error checking lang attribute: {e}")
    
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
        'status': 'success' if fail_rate < 40 else 'failed',
        'issues': issues,
        'screenshots': []
    }
