"""
Performance test suite.
"""
import logging
from typing import Dict, Optional, List
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


async def run_performance_tests(
    page: Page,
    url: str,
    screenshots_dir: Optional[str],
    console_logs: List[Dict],
    network_requests: List[Dict],
    issue_manager
) -> Dict:
    """Run performance tests - check page load time and performance metrics."""
    issues = []
    tests_passed = 0
    tests_failed = 0
    
    try:
        await page.wait_for_load_state('load', timeout=30000)
    except PlaywrightTimeoutError:
        logger.warning("Page load state 'load' timed out, using current state")
    
    performance_metrics = await page.evaluate('''() => {
        const perf = performance.timing;
        const nav = performance.navigation;
        
        let lcp = 0;
        let cls = 0;
        let fid = 0;
        let tbt = 0;
        
        try {
            const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
            if (lcpEntries.length > 0) {
                lcp = lcpEntries[lcpEntries.length - 1].renderTime || lcpEntries[lcpEntries.length - 1].loadTime || 0;
            }
        } catch (e) {}
        
        try {
            let clsValue = 0;
            const clsEntries = performance.getEntriesByType('layout-shift');
            clsEntries.forEach(entry => {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                }
            });
            cls = clsValue;
        } catch (e) {}
        
        try {
            const fidEntries = performance.getEntriesByType('first-input');
            if (fidEntries.length > 0) {
                fid = fidEntries[0].processingStart - fidEntries[0].startTime;
            }
        } catch (e) {}
        
        try {
            const longTasks = performance.getEntriesByType('longtask');
            let blockingTime = 0;
            longTasks.forEach(task => {
                blockingTime += task.duration - 50;
            });
            tbt = blockingTime;
        } catch (e) {}
        
        return {
            loadTime: perf.loadEventEnd - perf.navigationStart,
            domContentLoaded: perf.domContentLoadedEventEnd - perf.navigationStart,
            firstPaint: performance.getEntriesByType('paint').find(p => p.name === 'first-paint')?.startTime || 0,
            firstContentfulPaint: performance.getEntriesByType('paint').find(p => p.name === 'first-contentful-paint')?.startTime || 0,
            domInteractive: perf.domInteractive - perf.navigationStart,
            redirectCount: nav.redirectCount,
            lcp: lcp,
            cls: cls,
            fid: fid,
            tbt: tbt
        };
    }''')
    
    load_time_seconds = (performance_metrics.get('loadTime', 0) or 0) / 1000
    dom_content_loaded = (performance_metrics.get('domContentLoaded', 0) or 0) / 1000
    fcp = (performance_metrics.get('firstContentfulPaint', 0) or 0) / 1000
    lcp = (performance_metrics.get('lcp', 0) or 0) / 1000
    cls = performance_metrics.get('cls', 0) or 0
    fid = performance_metrics.get('fid', 0) or 0
    tbt = (performance_metrics.get('tbt', 0) or 0) / 1000
    
    # Test 1: Page load time
    if load_time_seconds < 3:
        tests_passed += 1
    elif load_time_seconds < 5:
        tests_passed += 1
        issues.append({
            'severity': 'minor',
            'title': 'Page load time is acceptable but could be improved',
            'description': f'Page loaded in {load_time_seconds:.2f} seconds. Target: <3 seconds for optimal user experience.',
            'location': url
        })
    else:
        tests_failed += 1
        await issue_manager.add_issue(
            issues, 'major', 'Slow page load time',
            f'Page took {load_time_seconds:.2f} seconds to load, exceeding the 3-second threshold. This can significantly impact user experience and SEO.',
            url, page
        )
    
    # Test 2: FCP
    if fcp > 0:
        if fcp > 3:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'major', 'Slow First Contentful Paint',
                f'First Contentful Paint is {fcp:.2f} seconds. Target: <1.8 seconds for good user experience.',
                url, page
            )
        elif fcp > 1.8:
            await issue_manager.add_issue(
                issues, 'minor', 'First Contentful Paint could be improved',
                f'First Contentful Paint is {fcp:.2f} seconds. Target: <1.8 seconds.',
                url, page
            )
    
    # Test 3: LCP
    if lcp > 0:
        if lcp > 4:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'critical', 'Poor Largest Contentful Paint (LCP)',
                f'LCP is {lcp:.2f} seconds. Target: <2.5 seconds. This is a Core Web Vital affecting SEO.',
                url, page
            )
        elif lcp > 2.5:
            await issue_manager.add_issue(
                issues, 'major', 'Largest Contentful Paint needs improvement',
                f'LCP is {lcp:.2f} seconds. Target: <2.5 seconds for good user experience.',
                url, page
            )
    
    # Test 4: CLS
    if cls > 0.25:
        tests_failed += 1
        await issue_manager.add_issue(
            issues, 'critical', 'High Cumulative Layout Shift (CLS)',
            f'CLS score is {cls:.3f}. Target: <0.1. This is a Core Web Vital affecting SEO.',
            url, page
        )
    elif cls > 0.1:
        await issue_manager.add_issue(
            issues, 'major', 'Cumulative Layout Shift needs improvement',
            f'CLS score is {cls:.3f}. Target: <0.1. Layout shifts can frustrate users.',
            url, page
        )
    
    # Test 5: FID/TBT
    if fid > 0:
        if fid > 300:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'critical', 'High First Input Delay (FID)',
                f'FID is {fid:.0f}ms. Target: <100ms. This is a Core Web Vital.',
                url, page
            )
        elif fid > 100:
            await issue_manager.add_issue(
                issues, 'major', 'First Input Delay could be improved',
                f'FID is {fid:.0f}ms. Target: <100ms.',
                url, page
            )
    
    if tbt > 0:
        if tbt > 600:
            tests_failed += 1
            await issue_manager.add_issue(
                issues, 'major', 'High Total Blocking Time (TBT)',
                f'TBT is {tbt:.0f}ms. Target: <300ms. Long tasks block user interactions.',
                url, page
            )
        elif tbt > 300:
            await issue_manager.add_issue(
                issues, 'minor', 'Total Blocking Time could be reduced',
                f'TBT is {tbt:.0f}ms. Target: <300ms.',
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
        'status': 'success' if fail_rate < 30 else 'failed',
        'issues': issues,
        'screenshots': []
    }
