"""
Browser automation service using Playwright for automated testing.
"""
import asyncio
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError  # type: ignore[import-untyped]
except ImportError:
    raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install chromium")
from typing import Dict, Optional
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class BrowserAutomationService:
    """Service for running automated browser tests using Playwright."""
    
    def __init__(self):
        self.timeout = 60000  # 60 seconds default timeout
        self.viewport_width = 1920
        self.viewport_height = 1080
        
    async def run_test(
        self,
        url: str,
        test_type: str,
        screenshots_dir: Optional[str] = None
    ) -> Dict:
        """
        Run automated tests on a given URL.
        
        Args:
            url: The URL to test
            test_type: Type of test (functional, regression, performance, accessibility)
            screenshots_dir: Optional directory to save screenshots
            
        Returns:
            Dictionary with test results including:
            - pass_rate: Percentage of tests passed
            - fail_rate: Percentage of tests failed
            - status: 'success' or 'failed'
            - issues: List of issues found
            - screenshots: List of screenshot paths
            - console_logs: List of console messages
            - network_requests: List of network request details
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            # Set up data collection before navigation
            console_logs = []
            network_requests = []
            network_failures = []
            
            # Collect console logs
            def handle_console(msg):
                console_logs.append({
                    'type': msg.type,
                    'text': msg.text,
                    'location': str(msg.location) if msg.location else None
                })
            
            page.on('console', handle_console)
            
            # Store main document response headers for security checks
            main_document_headers = {}
            
            # Collect network requests
            def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resource_type,
                    'headers': request.headers
                })
            
            def handle_response(response):
                if response.status >= 400:
                    network_failures.append({
                        'url': response.url,
                        'status': response.status,
                        'status_text': response.status_text,
                        'resource_type': response.request.resource_type
                    })
                # Store main document response headers for security header checks
                if response.request.resource_type == 'document' and response.url == url:
                    try:
                        main_document_headers.update(dict(response.headers))
                    except:
                        pass
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            try:
                # Navigate to the URL
                logger.info(f"Navigating to {url}")
                # Use 'domcontentloaded' for fastest loading, with longer timeout
                # This waits for HTML to be parsed, not all resources
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                except PlaywrightTimeoutError:
                    # If domcontentloaded times out, try with just navigation
                    logger.warning(f"domcontentloaded timed out for {url}, trying with 'commit'")
                    await page.goto(url, wait_until='commit', timeout=self.timeout)
                
                # Wait for page to fully load (CSS, images, JS execution)
                logger.info("Waiting for page to fully load...")
                try:
                    # Wait for 'load' event (all resources loaded)
                    await page.wait_for_load_state('load', timeout=30000)
                    logger.info("Page load state reached")
                except PlaywrightTimeoutError:
                    logger.warning("Page load state timed out, continuing anyway")
                
                # Wait for network to be idle (no requests for 500ms)
                # This ensures JavaScript has finished executing
                try:
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    logger.info("Network idle state reached")
                except PlaywrightTimeoutError:
                    logger.warning("Network idle timed out, waiting additional time for JS execution")
                    # If networkidle times out, wait a bit more for JS frameworks to render
                    await page.wait_for_timeout(3000)
                
                # Additional wait to ensure content is rendered (especially for React/Vue/Angular)
                await page.wait_for_timeout(2000)
                
                # Verify page has visible content before proceeding
                has_content = await page.evaluate('''() => {
                    const body = document.body;
                    if (!body) return false;
                    const text = body.innerText || body.textContent || '';
                    const hasText = text.trim().length > 0;
                    const hasVisibleElements = body.querySelector('*') !== null;
                    return hasText || hasVisibleElements;
                }''')
                
                if not has_content:
                    logger.warning("Page appears to have no visible content, waiting longer...")
                    await page.wait_for_timeout(5000)  # Wait 5 more seconds for JS frameworks
                
                # Run tests based on type
                if test_type == 'functional':
                    results = await self._run_functional_tests(page, url, screenshots_dir, console_logs, network_failures, main_document_headers)
                elif test_type == 'regression':
                    results = await self._run_regression_tests(page, url, screenshots_dir, console_logs, network_failures)
                elif test_type == 'performance':
                    results = await self._run_performance_tests(page, url, screenshots_dir, console_logs, network_requests)
                elif test_type == 'accessibility':
                    results = await self._run_accessibility_tests(page, url, screenshots_dir, console_logs)
                else:
                    # Default: run all tests
                    results = await self._run_all_tests(page, url, screenshots_dir, console_logs, network_failures, network_requests, main_document_headers)
                
                # Add collected data to results
                results['console_logs'] = console_logs
                results['network_requests'] = network_requests[:50]  # Limit to first 50
                results['network_failures'] = network_failures
                
                await browser.close()
                return results
                
            except PlaywrightTimeoutError as e:
                logger.error(f"Timeout error: {e}")
                await browser.close()
                return {
                    'pass_rate': 0,
                    'fail_rate': 100,
                    'status': 'failed',
                    'issues': [{'severity': 'critical', 'title': 'Page load timeout', 'description': str(e)}],
                    'screenshots': []
                }
            except Exception as e:
                logger.error(f"Error during test execution: {e}")
                await browser.close()
                return {
                    'pass_rate': 0,
                    'fail_rate': 100,
                    'status': 'failed',
                    'issues': [{'severity': 'critical', 'title': 'Test execution error', 'description': str(e)}],
                    'screenshots': []
                }
    
    async def _run_functional_tests(self, page: Page, url: str, screenshots_dir: Optional[str], console_logs: list, network_failures: list, main_document_headers: dict = None) -> Dict:
        """Run functional tests - check basic page functionality."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check if page loaded successfully
        try:
            title = await page.title()
            if title:
                tests_passed += 1
                # Check title length
                if len(title) > 60:
                    issues.append({
                        'severity': 'minor',
                        'title': 'Page title is too long',
                        'description': f'Page title is {len(title)} characters. Recommended: 50-60 characters for optimal SEO.',
                        'location': url
                    })
            else:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': 'Page title missing',
                    'description': 'The page does not have a title tag, which is required for SEO and browser tabs.',
                    'location': url
                })
        except Exception as e:
            tests_failed += 1
            issues.append({
                'severity': 'critical',
                'title': 'Failed to get page title',
                'description': str(e),
                'location': url
            })
        
        # Test 2: Check for main content
        try:
            main_content = await page.query_selector('main, [role="main"], body > div')
            if main_content:
                tests_passed += 1
            else:
                tests_failed += 1
                issues.append({
                    'severity': 'minor',
                    'title': 'No main content area found',
                    'description': 'The page does not have a clear main content area (main tag or [role="main"]).',
                    'location': url
                })
        except Exception as e:
            tests_failed += 1
        
        # Test 3: Check for links
        try:
            links = await page.query_selector_all('a[href]')
            if len(links) > 0:
                tests_passed += 1
                # Check for empty or placeholder links
                empty_links = 0
                for link in links[:20]:  # Check first 20
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if not href or href == '#' or (not text or text.strip() == ''):
                        empty_links += 1
                
                if empty_links > 0:
                    issues.append({
                        'severity': 'minor',
                        'title': f'{empty_links} empty or placeholder link(s) found',
                        'description': 'Some links have empty href attributes (#) or no visible text, which can confuse users.',
                        'location': url
                    })
            else:
                issues.append({
                    'severity': 'minor',
                    'title': 'No links found on page',
                    'description': 'The page does not contain any navigation links, which may limit user navigation.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking links: {e}")
        
        # Test 4: Check meta tags and SEO
        try:
            meta_description = await page.query_selector('meta[name="description"]')
            if not meta_description:
                issues.append({
                    'severity': 'minor',
                    'title': 'Meta description missing',
                    'description': 'The page is missing a meta description tag, which is important for SEO and social sharing.',
                    'location': url
                })
            else:
                desc_content = await meta_description.get_attribute('content')
                if desc_content:
                    if len(desc_content) > 160:
                        issues.append({
                            'severity': 'minor',
                            'title': 'Meta description is too long',
                            'description': f'Meta description is {len(desc_content)} characters. Recommended: 150-160 characters for optimal display in search results.',
                            'location': url
                        })
                    elif len(desc_content) < 50:
                        issues.append({
                            'severity': 'minor',
                            'title': 'Meta description is too short',
                            'description': f'Meta description is {len(desc_content)} characters. Recommended: 120-160 characters for better SEO.',
                            'location': url
                        })
            
            # Check Open Graph tags
            og_title = await page.query_selector('meta[property="og:title"]')
            og_description = await page.query_selector('meta[property="og:description"]')
            og_image = await page.query_selector('meta[property="og:image"]')
            
            if not og_title or not og_description:
                issues.append({
                    'severity': 'minor',
                    'title': 'Open Graph tags incomplete',
                    'description': 'Missing Open Graph tags (og:title, og:description) which are important for social media sharing previews.',
                    'location': url
                })
            
            # Check for structured data (JSON-LD)
            json_ld = await page.query_selector_all('script[type="application/ld+json"]')
            if len(json_ld) == 0:
                issues.append({
                    'severity': 'minor',
                    'title': 'Structured data (JSON-LD) missing',
                    'description': 'No structured data found. Adding JSON-LD schema markup can improve search engine understanding and rich results.',
                    'location': url
                })
            
            # Check canonical URL
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
        
        # Test 5: Check for forms
        try:
            forms = await page.query_selector_all('form')
            if len(forms) > 0:
                tests_passed += 1
                # Check form accessibility
                for form in forms[:5]:  # Check first 5 forms
                    form_id = await form.get_attribute('id')
                    form_name = await form.get_attribute('name')
                    if not form_id and not form_name:
                        issues.append({
                            'severity': 'minor',
                            'title': 'Form missing identifier',
                            'description': 'A form on the page lacks an id or name attribute, making it harder to reference.',
                            'location': url
                        })
                    
                    # Check for submit buttons
                    submit_buttons = await form.query_selector_all('button[type="submit"], input[type="submit"]')
                    if len(submit_buttons) == 0:
                        issues.append({
                            'severity': 'major',
                            'title': 'Form missing submit button',
                            'description': 'A form on the page does not have a visible submit button, which may prevent form submission.',
                            'location': url
                        })
        except Exception as e:
            logger.warning(f"Error checking forms: {e}")
        
        # Test 6: Check console errors and warnings
        console_errors = [log for log in console_logs if log['type'] == 'error']
        console_warnings = [log for log in console_logs if log['type'] == 'warning']
        
        if console_errors:
            tests_failed += 1
            for error in console_errors[:5]:  # Report first 5
                issues.append({
                    'severity': 'major',
                    'title': 'Console error detected',
                    'description': f"JavaScript console error: {error.get('text', 'Unknown error')}",
                    'location': error.get('location', url)
                })
        
        if console_warnings:
            for warning in console_warnings[:3]:  # Report first 3
                issues.append({
                    'severity': 'minor',
                    'title': 'Console warning detected',
                    'description': f"JavaScript console warning: {warning.get('text', 'Unknown warning')}",
                    'location': warning.get('location', url)
                })
        
        # Test 7: Check network failures
        if network_failures:
            tests_failed += 1
            for failure in network_failures[:5]:  # Report first 5
                issues.append({
                    'severity': 'major' if failure['status'] >= 500 else 'minor',
                    'title': f"Network request failed ({failure['status']})",
                    'description': f"Failed to load resource: {failure['url']} (Status: {failure['status']} {failure['status_text']})",
                    'location': failure['url']
                })
        
        # Test 8: Check security headers
        try:
            # Check HTTPS from URL
            if not url.startswith('https://'):
                issues.append({
                    'severity': 'major',
                    'title': 'Site not using HTTPS',
                    'description': 'The site is not using HTTPS, which is a security risk and can affect SEO rankings. Migrate to HTTPS.',
                    'location': url
                })
            
            # Check security headers from main document response
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
                    # Check if header exists (case-insensitive)
                    header_found = any(h.lower() == header.lower() for h in headers.keys())
                    if not header_found:
                        issues.append({
                            'severity': 'minor',
                            'title': f'Missing security header: {header}',
                            'description': description,
                            'location': url
                        })
        except Exception as e:
            logger.warning(f"Error checking security headers: {e}")
        
        # Test 9: Check responsive design
        try:
            viewport_meta = await page.query_selector('meta[name="viewport"]')
            if not viewport_meta:
                issues.append({
                    'severity': 'major',
                    'title': 'Viewport meta tag missing',
                    'description': 'Missing viewport meta tag, which is essential for responsive design on mobile devices. Add: <meta name="viewport" content="width=device-width, initial-scale=1">',
                    'location': url
                })
            else:
                viewport_content = await viewport_meta.get_attribute('content')
                if viewport_content and 'width=device-width' not in viewport_content:
                    issues.append({
                        'severity': 'minor',
                        'title': 'Viewport meta tag may be incomplete',
                        'description': f'Viewport meta tag content: {viewport_content}. Ensure it includes "width=device-width" for proper mobile rendering.',
                        'location': url
                    })
            
            # Check for mobile-friendly elements
            touch_targets = await page.query_selector_all('button, a, input, [role="button"]')
            small_touch_targets = 0
            for target in touch_targets[:20]:  # Check first 20
                try:
                    box = await target.bounding_box()
                    if box:
                        min_size = min(box['width'], box['height'])
                        if min_size < 44:  # 44x44px is minimum recommended touch target
                            small_touch_targets += 1
                except:
                    pass
            
            if small_touch_targets > 0:
                issues.append({
                    'severity': 'minor',
                    'title': f'{small_touch_targets} small touch target(s) found',
                    'description': f'{small_touch_targets} interactive element(s) are smaller than 44x44px, which can be difficult to tap on mobile devices.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking responsive design: {e}")
        
        # Test 10: Simulate user interactions
        try:
            # Try to find and interact with common elements
            buttons = await page.query_selector_all('button, [role="button"], input[type="submit"]')
            if len(buttons) > 0:
                # Try clicking the first button (if it's safe)
                first_button = buttons[0]
                button_text = await first_button.inner_text()
                if button_text and len(button_text.strip()) > 0:
                    # Check if button is visible and enabled
                    is_visible = await first_button.is_visible()
                    is_enabled = await first_button.is_enabled()
                    if not is_visible:
                        issues.append({
                            'severity': 'minor',
                            'title': 'Button not visible',
                            'description': f'Found a button that is not visible to users: "{button_text[:50]}"',
                            'location': url
                        })
                    if not is_enabled:
                        issues.append({
                            'severity': 'minor',
                            'title': 'Button disabled',
                            'description': f'Found a disabled button: "{button_text[:50]}"',
                            'location': url
                        })
            
            # Check form inputs
            inputs = await page.query_selector_all('input[type="text"], input[type="email"], textarea')
            for inp in inputs[:5]:  # Check first 5
                try:
                    is_visible = await inp.is_visible()
                    is_enabled = await inp.is_enabled()
                    placeholder = await inp.get_attribute('placeholder')
                    
                    if is_visible and is_enabled and not placeholder:
                        # Check if there's a label
                        inp_id = await inp.get_attribute('id')
                        if inp_id:
                            label = await page.query_selector(f'label[for="{inp_id}"]')
                            if not label:
                                issues.append({
                                    'severity': 'minor',
                                    'title': 'Input field missing label or placeholder',
                                    'description': 'An input field is missing both a label and placeholder text, which can confuse users.',
                                    'location': url
                                })
                except:
                    pass
        except Exception as e:
            logger.warning(f"Error simulating user interactions: {e}")
        
        # Take screenshot
        screenshot_path = await self._take_screenshot(page, url, 'functional', screenshots_dir)
        
        total_tests = tests_passed + tests_failed
        pass_rate = int((tests_passed / total_tests * 100)) if total_tests > 0 else 100
        fail_rate = 100 - pass_rate
        
        return {
            'pass_rate': pass_rate,
            'fail_rate': fail_rate,
            'status': 'success' if fail_rate < 30 else 'failed',
            'issues': issues,
            'screenshots': [screenshot_path] if screenshot_path else []
        }
    
    async def _run_regression_tests(self, page: Page, url: str, screenshots_dir: Optional[str], console_logs: list, network_failures: list) -> Dict:
        """Run regression tests - check for broken functionality."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check for JavaScript errors (page errors)
        js_errors = []
        def handle_page_error(error):
            js_errors.append(str(error))
        
        page.on('pageerror', handle_page_error)
        
        # Wait a bit for JS to execute
        await page.wait_for_timeout(3000)
        
        if len(js_errors) == 0:
            tests_passed += 1
        else:
            tests_failed += 1
            for error in js_errors[:5]:  # Report first 5 errors
                issues.append({
                    'severity': 'critical',
                    'title': 'JavaScript runtime error detected',
                    'description': f'Uncaught JavaScript error: {error}',
                    'location': url
                })
        
        # Test 2: Check for broken images
        try:
            images = await page.query_selector_all('img')
            broken_images = []
            for img in images[:20]:  # Check first 20 images
                try:
                    natural_width = await img.evaluate('el => el.naturalWidth')
                    if natural_width == 0:
                        src = await img.get_attribute('src')
                        broken_images.append(src or 'unknown')
                except:
                    src = await img.get_attribute('src')
                    broken_images.append(src or 'unknown')
            
            if len(broken_images) == 0:
                tests_passed += 1
            else:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': f'{len(broken_images)} broken image(s) found',
                    'description': f'Images failed to load: {", ".join(broken_images[:3])}{"..." if len(broken_images) > 3 else ""}',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking images: {e}")
        
        # Test 3: Check for broken external links (404s)
        try:
            links = await page.query_selector_all('a[href^="http"]')
            broken_links = []
            for link in links[:10]:  # Check first 10 external links
                href = await link.get_attribute('href')
                if href and href.startswith('http'):
                    # Check if this link resulted in a 404
                    for failure in network_failures:
                        if failure['url'] == href and failure['status'] == 404:
                            broken_links.append(href)
                            break
            
            if broken_links:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': f'{len(broken_links)} broken external link(s) found',
                    'description': f'External links returned 404: {", ".join(broken_links[:3])}{"..." if len(broken_links) > 3 else ""}',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking external links: {e}")
        
        # Test 4: Check for console errors
        console_errors = [log for log in console_logs if log['type'] == 'error']
        if console_errors:
            tests_failed += 1
            for error in console_errors[:5]:
                issues.append({
                    'severity': 'major',
                    'title': 'Console error in regression test',
                    'description': f"Console error: {error.get('text', 'Unknown')}",
                    'location': error.get('location', url)
                })
        
        # Test 5: Check for missing resources (CSS, JS, fonts)
        missing_resources = [f for f in network_failures if f['resource_type'] in ['stylesheet', 'script', 'font']]
        if missing_resources:
            tests_failed += 1
            resource_types = {}
            for res in missing_resources:
                res_type = res['resource_type']
                resource_types[res_type] = resource_types.get(res_type, 0) + 1
            
            for res_type, count in resource_types.items():
                issues.append({
                    'severity': 'critical' if res_type == 'stylesheet' else 'major',
                    'title': f'{count} missing {res_type}(s)',
                    'description': f'Failed to load {count} {res_type} resource(s), which may break page functionality or styling.',
                    'location': url
                })
        
        screenshot_path = await self._take_screenshot(page, url, 'regression', screenshots_dir)
        
        total_tests = tests_passed + tests_failed
        pass_rate = int((tests_passed / total_tests * 100)) if total_tests > 0 else 100
        fail_rate = 100 - pass_rate
        
        return {
            'pass_rate': pass_rate,
            'fail_rate': fail_rate,
            'status': 'success' if fail_rate < 20 else 'failed',
            'issues': issues,
            'screenshots': [screenshot_path] if screenshot_path else []
        }
    
    async def _run_performance_tests(self, page: Page, url: str, screenshots_dir: Optional[str], console_logs: list, network_requests: list) -> Dict:
        """Run performance tests - check page load time and performance metrics."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Measure page load time
        # Use 'load' instead of 'networkidle' to avoid long waits
        try:
            await page.wait_for_load_state('load', timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Page load state 'load' timed out, using current state")
        
        # Get performance metrics including Core Web Vitals
        performance_metrics = await page.evaluate('''() => {
            const perf = performance.timing;
            const nav = performance.navigation;
            
            // Core Web Vitals
            let lcp = 0;
            let cls = 0;
            let fid = 0;
            let tbt = 0;
            
            // Largest Contentful Paint (LCP)
            try {
                const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
                if (lcpEntries.length > 0) {
                    lcp = lcpEntries[lcpEntries.length - 1].renderTime || lcpEntries[lcpEntries.length - 1].loadTime || 0;
                }
            } catch (e) {}
            
            // Cumulative Layout Shift (CLS)
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
            
            // First Input Delay (FID) - approximate using PerformanceObserver if available
            try {
                const fidEntries = performance.getEntriesByType('first-input');
                if (fidEntries.length > 0) {
                    fid = fidEntries[0].processingStart - fidEntries[0].startTime;
                }
            } catch (e) {}
            
            // Total Blocking Time (TBT) - approximate from long tasks
            try {
                const longTasks = performance.getEntriesByType('longtask');
                let blockingTime = 0;
                longTasks.forEach(task => {
                    blockingTime += task.duration - 50; // Tasks >50ms contribute to TBT
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
            issues.append({
                'severity': 'major',
                'title': 'Slow page load time',
                'description': f'Page took {load_time_seconds:.2f} seconds to load, exceeding the 3-second threshold. This can significantly impact user experience and SEO.',
                'location': url
            })
        
        # Test 2: First Contentful Paint (FCP)
        if fcp > 0:
            if fcp > 3:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': 'Slow First Contentful Paint',
                    'description': f'First Contentful Paint is {fcp:.2f} seconds. Target: <1.8 seconds for good user experience. Consider optimizing critical rendering path, reducing render-blocking resources, and using resource hints.',
                    'location': url
                })
            elif fcp > 1.8:
                issues.append({
                    'severity': 'minor',
                    'title': 'First Contentful Paint could be improved',
                    'description': f'First Contentful Paint is {fcp:.2f} seconds. Target: <1.8 seconds. Consider preloading critical resources and minimizing render-blocking CSS.',
                    'location': url
                })
        
        # Test 3: Largest Contentful Paint (LCP) - Core Web Vital
        if lcp > 0:
            if lcp > 4:
                tests_failed += 1
                issues.append({
                    'severity': 'critical',
                    'title': 'Poor Largest Contentful Paint (LCP)',
                    'description': f'LCP is {lcp:.2f} seconds. Target: <2.5 seconds. This is a Core Web Vital affecting SEO. Optimize by: reducing server response time, eliminating render-blocking resources, optimizing images, and preloading key resources.',
                    'location': url
                })
            elif lcp > 2.5:
                issues.append({
                    'severity': 'major',
                    'title': 'Largest Contentful Paint needs improvement',
                    'description': f'LCP is {lcp:.2f} seconds. Target: <2.5 seconds for good user experience. Consider optimizing the largest element (image, video, or text block).',
                    'location': url
                })
        
        # Test 4: Cumulative Layout Shift (CLS) - Core Web Vital
        if cls > 0.25:
            tests_failed += 1
            issues.append({
                'severity': 'critical',
                'title': 'High Cumulative Layout Shift (CLS)',
                'description': f'CLS score is {cls:.3f}. Target: <0.1. This is a Core Web Vital affecting SEO. Fix by: setting size attributes on images/videos, avoiding inserting content above existing content, and using transform animations instead of layout-triggering properties.',
                'location': url
            })
        elif cls > 0.1:
            issues.append({
                'severity': 'major',
                'title': 'Cumulative Layout Shift needs improvement',
                'description': f'CLS score is {cls:.3f}. Target: <0.1. Layout shifts can frustrate users. Ensure images/videos have dimensions, avoid dynamically injected content, and use CSS transforms for animations.',
                'location': url
            })
        
        # Test 5: First Input Delay (FID) / Total Blocking Time (TBT) - Core Web Vital
        if fid > 0:
            if fid > 300:
                tests_failed += 1
                issues.append({
                    'severity': 'critical',
                    'title': 'High First Input Delay (FID)',
                    'description': f'FID is {fid:.0f}ms. Target: <100ms. This is a Core Web Vital. Reduce by: breaking up long tasks, optimizing JavaScript execution, and reducing main thread work.',
                    'location': url
                })
            elif fid > 100:
                issues.append({
                    'severity': 'major',
                    'title': 'First Input Delay could be improved',
                    'description': f'FID is {fid:.0f}ms. Target: <100ms. Optimize JavaScript execution and reduce main thread blocking.',
                    'location': url
                })
        
        if tbt > 0:
            if tbt > 600:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': 'High Total Blocking Time (TBT)',
                    'description': f'TBT is {tbt:.0f}ms. Target: <300ms. Long tasks block user interactions. Break up JavaScript execution, use code splitting, and defer non-critical scripts.',
                    'location': url
                })
            elif tbt > 300:
                issues.append({
                    'severity': 'minor',
                    'title': 'Total Blocking Time could be reduced',
                    'description': f'TBT is {tbt:.0f}ms. Target: <300ms. Consider optimizing JavaScript execution.',
                    'location': url
                })
        
        # Test 6: DOM Content Loaded
        if dom_content_loaded > 3:
            issues.append({
                'severity': 'minor',
                'title': 'Slow DOM Content Loaded',
                'description': f'DOM Content Loaded took {dom_content_loaded:.2f} seconds. This affects how quickly the page becomes interactive.',
                'location': url
            })
        
        # Test 7: Analyze resource sizes
        try:
            resource_sizes = await page.evaluate('''() => {
                const resources = performance.getEntriesByType('resource');
                const sizes = {
                    script: { count: 0, totalSize: 0 },
                    stylesheet: { count: 0, totalSize: 0 },
                    image: { count: 0, totalSize: 0 },
                    font: { count: 0, totalSize: 0 }
                };
                resources.forEach(res => {
                    const type = res.initiatorType;
                    if (type in sizes) {
                        sizes[type].count++;
                        sizes[type].totalSize += res.transferSize || 0;
                    }
                });
                return sizes;
            }''')
            
            # Check for large resources
            total_size_mb = sum(s['totalSize'] for s in resource_sizes.values()) / (1024 * 1024)
            if total_size_mb > 5:
                issues.append({
                    'severity': 'major',
                    'title': 'Large total page size',
                    'description': f'Total page size is {total_size_mb:.2f} MB. Target: <3 MB for fast loading, especially on mobile networks.',
                    'location': url
                })
            
            # Check for too many resources
            total_resources = sum(s['count'] for s in resource_sizes.values())
            if total_resources > 100:
                issues.append({
                    'severity': 'minor',
                    'title': 'High number of resources',
                    'description': f'Page loads {total_resources} resources. Consider bundling or combining resources to reduce HTTP requests.',
                    'location': url
                })
            
            # Check for large images
            if resource_sizes.get('image', {}).get('totalSize', 0) > 2 * 1024 * 1024:  # >2MB
                img_size_mb = resource_sizes['image']['totalSize'] / (1024 * 1024)
                issues.append({
                    'severity': 'minor',
                    'title': 'Large image files detected',
                    'description': f'Total image size is {img_size_mb:.2f} MB. Consider optimizing images (WebP, compression) to improve load times.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error analyzing resource sizes: {e}")
        
        # Test 8: Check for redirects
        redirect_count = performance_metrics.get('redirectCount', 0)
        if redirect_count > 0:
            issues.append({
                'severity': 'minor',
                'title': f'{redirect_count} redirect(s) detected',
                'description': f'Page has {redirect_count} redirect(s), which adds latency. Consider using direct URLs when possible.',
                'location': url
            })
        
        # Test 9: Check for slow network requests
        slow_requests = []
        for req in network_requests[:20]:  # Check first 20
            # This is a simplified check - in reality we'd need to track request/response times
            pass
        
        screenshot_path = await self._take_screenshot(page, url, 'performance', screenshots_dir)
        
        total_tests = tests_passed + tests_failed
        pass_rate = int((tests_passed / total_tests * 100)) if total_tests > 0 else 100
        fail_rate = 100 - pass_rate
        
        return {
            'pass_rate': pass_rate,
            'fail_rate': fail_rate,
            'status': 'success' if fail_rate < 30 else 'failed',
            'issues': issues,
            'screenshots': [screenshot_path] if screenshot_path else []
        }
    
    async def _run_accessibility_tests(self, page: Page, url: str, screenshots_dir: Optional[str], console_logs: list) -> Dict:
        """Run accessibility tests - check WCAG compliance."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check for alt text on images
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
                    issues.append({
                        'severity': 'major',
                        'title': f'{len(images_without_alt)} image(s) missing alt text',
                        'description': 'Images without alt text are not accessible to screen readers. Add descriptive alt attributes to all images.',
                        'location': url
                    })
                if images_with_empty_alt:
                    issues.append({
                        'severity': 'minor',
                        'title': f'{len(images_with_empty_alt)} image(s) with empty alt text',
                        'description': 'Images with empty alt attributes should be decorative. If they convey information, add descriptive alt text.',
                        'location': url
                    })
        except Exception as e:
            logger.warning(f"Error checking image alt text: {e}")
        
        # Test 2: Check for heading hierarchy
        try:
            headings = await page.query_selector_all('h1, h2, h3, h4, h5, h6')
            if len(headings) > 0:
                # Check if h1 exists
                h1 = await page.query_selector('h1')
                if h1:
                    tests_passed += 1
                    # Check for multiple h1s
                    h1_count = len(await page.query_selector_all('h1'))
                    if h1_count > 1:
                        issues.append({
                            'severity': 'minor',
                            'title': f'Multiple H1 headings found ({h1_count})',
                            'description': 'Pages should typically have only one H1 heading for proper document structure and SEO.',
                            'location': url
                        })
                else:
                    tests_failed += 1
                    issues.append({
                        'severity': 'major',
                        'title': 'Missing H1 heading',
                        'description': 'The page does not have an H1 heading, which is important for accessibility, SEO, and document structure.',
                        'location': url
                    })
                
                # Check heading hierarchy (skip levels)
                heading_levels = []
                for heading in headings[:20]:  # Check first 20
                    tag_name = await heading.evaluate('el => el.tagName.toLowerCase()')
                    level = int(tag_name[1])
                    heading_levels.append(level)
                
                # Check for skipped levels (e.g., h1 -> h3)
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
        
        # Test 3: Check for ARIA labels
        try:
            interactive_elements = await page.query_selector_all('button, input, select, textarea, a[href]')
            elements_without_labels = []
            for elem in interactive_elements[:30]:  # Check first 30
                aria_label = await elem.get_attribute('aria-label')
                aria_labelledby = await elem.get_attribute('aria-labelledby')
                id_attr = await elem.get_attribute('id')
                
                # Check if element has associated label
                tag_name = await elem.evaluate('el => el.tagName.toLowerCase()')
                if tag_name == 'input' or tag_name == 'textarea' or tag_name == 'select':
                    label = await page.query_selector(f'label[for="{id_attr}"]')
                    if not label and not aria_label and not aria_labelledby:
                        # Check if input is inside a label
                        parent_label = await elem.evaluate('el => el.closest("label")')
                        if not parent_label:
                            elements_without_labels.append(tag_name)
                elif tag_name == 'button' or (tag_name == 'a' and not aria_label):
                    # Buttons should have aria-label or visible text
                    text = await elem.inner_text()
                    if not text.strip() and not aria_label:
                        elements_without_labels.append(tag_name)
            
            if elements_without_labels:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': f'{len(elements_without_labels)} interactive element(s) missing labels',
                    'description': 'Interactive elements without labels are not accessible to screen readers. Add aria-label, aria-labelledby, or associate with <label> elements.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking ARIA labels: {e}")
        
        # Test 4: Check for form labels
        try:
            inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[type="password"], input[type="number"], textarea, select')
            inputs_without_labels = 0
            for inp in inputs[:20]:  # Check first 20
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
                    # Check if input is inside a label
                    parent_label = await inp.evaluate('el => el.closest("label")')
                    if parent_label:
                        has_label = True
                
                if not has_label and not aria_label and not aria_labelledby:
                    inputs_without_labels += 1
            
            if inputs_without_labels > 0:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': f'{inputs_without_labels} form field(s) missing labels',
                    'description': 'Form fields without labels are not accessible. Associate each input with a <label> element or use aria-label.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking form labels: {e}")
        
        # Test 5: Check for color contrast (basic check - can't fully test without image analysis)
        try:
            # Check for inline styles that might indicate poor contrast
            elements_with_color = await page.query_selector_all('[style*="color"], [style*="background"]')
            if len(elements_with_color) > 50:
                issues.append({
                    'severity': 'minor',
                    'title': 'Many inline color styles detected',
                    'description': 'Pages with many inline color styles may have contrast issues. Use CSS classes and ensure WCAG AA contrast ratios (4.5:1 for text).',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking color contrast hints: {e}")
        
        # Test 6: Check for keyboard navigation (tabindex)
        try:
            negative_tabindex = await page.query_selector_all('[tabindex="-1"]')
            if len(negative_tabindex) > 10:
                issues.append({
                    'severity': 'minor',
                    'title': 'Many elements with negative tabindex',
                    'description': f'{len(negative_tabindex)} elements have tabindex="-1", which removes them from keyboard navigation. Ensure this is intentional.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking tabindex: {e}")
        
        # Test 7: Check for lang attribute
        try:
            html_lang = await page.query_selector('html')
            if html_lang:
                lang = await html_lang.get_attribute('lang')
                if not lang:
                    issues.append({
                        'severity': 'minor',
                        'title': 'Missing lang attribute on HTML element',
                        'description': 'The <html> element should have a lang attribute to help screen readers pronounce content correctly.',
                        'location': url
                    })
        except Exception as e:
            logger.warning(f"Error checking lang attribute: {e}")
        
        screenshot_path = await self._take_screenshot(page, url, 'accessibility', screenshots_dir)
        
        total_tests = tests_passed + tests_failed
        pass_rate = int((tests_passed / total_tests * 100)) if total_tests > 0 else 100
        fail_rate = 100 - pass_rate
        
        return {
            'pass_rate': pass_rate,
            'fail_rate': fail_rate,
            'status': 'success' if fail_rate < 40 else 'failed',
            'issues': issues,
            'screenshots': [screenshot_path] if screenshot_path else []
        }
    
    async def _run_all_tests(self, page: Page, url: str, screenshots_dir: Optional[str], console_logs: list, network_failures: list, network_requests: list, main_document_headers: dict = None) -> Dict:
        """Run all test types."""
        functional_results = await self._run_functional_tests(page, url, screenshots_dir, console_logs, network_failures, main_document_headers)
        regression_results = await self._run_regression_tests(page, url, screenshots_dir, console_logs, network_failures)
        performance_results = await self._run_performance_tests(page, url, screenshots_dir, console_logs, network_requests)
        accessibility_results = await self._run_accessibility_tests(page, url, screenshots_dir, console_logs)
        
        # Combine results
        all_issues = (
            functional_results['issues'] +
            regression_results['issues'] +
            performance_results['issues'] +
            accessibility_results['issues']
        )
        
        all_screenshots = list(set(
            functional_results['screenshots'] +
            regression_results['screenshots'] +
            performance_results['screenshots'] +
            accessibility_results['screenshots']
        ))
        
        # Calculate average pass rate
        avg_pass_rate = (
            functional_results['pass_rate'] +
            regression_results['pass_rate'] +
            performance_results['pass_rate'] +
            accessibility_results['pass_rate']
        ) // 4
        
        avg_fail_rate = 100 - avg_pass_rate
        
        return {
            'pass_rate': avg_pass_rate,
            'fail_rate': avg_fail_rate,
            'status': 'success' if avg_fail_rate < 30 else 'failed',
            'issues': all_issues,
            'screenshots': all_screenshots
        }
    
    async def _take_screenshot(
        self,
        page: Page,
        url: str,
        test_type: str,
        screenshots_dir: Optional[str]
    ) -> Optional[str]:
        """Take a screenshot and upload to Cloudinary."""
        try:
            # Ensure page has rendered content before taking screenshot
            logger.info(f"Preparing to take screenshot for {test_type} test")
            
            # Wait for any remaining animations or lazy-loaded content
            await page.wait_for_timeout(1000)
            
            # Check if page has visible content
            has_visible_content = await page.evaluate('''() => {
                const body = document.body;
                if (!body) return false;
                
                // Check for visible text
                const text = body.innerText || body.textContent || '';
                const hasText = text.trim().length > 10;  // At least 10 characters
                
                // Check for visible elements (not just white space)
                const visibleElements = Array.from(body.querySelectorAll('*')).some(el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           rect.width > 0 && 
                           rect.height > 0;
                });
                
                return hasText || visibleElements;
            }''')
            
            if not has_visible_content:
                logger.warning("Page appears to have no visible content, waiting longer before screenshot...")
                # Wait for JavaScript frameworks to render (React, Vue, Angular, etc.)
                await page.wait_for_timeout(5000)
                
                # Try waiting for common content selectors
                try:
                    await page.wait_for_selector('body > *', timeout=5000, state='visible')
                except:
                    logger.warning("Could not find visible content, taking screenshot anyway")
            
            logger.info("Taking screenshot...")
            screenshot_bytes = await page.screenshot(full_page=True)
            
            # Upload to Cloudinary
            try:
                import cloudinary
                import cloudinary.uploader
                from django.conf import settings as django_settings
                
                # Get Cloudinary credentials
                cloud_name = django_settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', '')
                api_key = django_settings.CLOUDINARY_STORAGE.get('API_KEY', '')
                api_secret = django_settings.CLOUDINARY_STORAGE.get('API_SECRET', '')
                
                logger.info(f"Uploading screenshot to Cloudinary. Cloud name: {cloud_name}, API key: {api_key[:10] if api_key else 'None'}...")
                
                # Configure Cloudinary if not already configured
                if not cloudinary.config().cloud_name:
                    cloudinary.config(
                        cloud_name=cloud_name,
                        api_key=api_key,
                        api_secret=api_secret,
                    )
                
                # Generate a unique filename with timestamp for uniqueness
                import hashlib
                import time
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                timestamp = int(time.time())
                # Use a simple public_id without nested paths - Cloudinary will handle the folder
                public_id = f"test_screenshots/{test_type}_{url_hash}_{timestamp}"
                
                logger.info(f"Uploading screenshot with public_id: {public_id}")
                
                # Upload to Cloudinary
                from io import BytesIO
                result = cloudinary.uploader.upload(
                    BytesIO(screenshot_bytes),
                    public_id=public_id,
                    resource_type='image',
                    format='png',
                    overwrite=False,  # Don't overwrite existing images
                    tags=['ai-application-tester', 'test_screenshot', test_type],
                    context={
                        'test_type': test_type,
                        'tested_url': url,
                    },
                )
                
                cloudinary_url = result.get('secure_url') or result.get('url')
                logger.info(f"✓ Successfully uploaded screenshot to Cloudinary. URL: {cloudinary_url}")
                logger.info(f"Upload result keys: {list(result.keys())}")
                
                # Return the Cloudinary URL
                return cloudinary_url
                
            except ImportError:
                logger.warning("Cloudinary not installed, falling back to local storage")
                # Fallback to local storage if Cloudinary is not available
                media_root = getattr(settings, 'MEDIA_ROOT', None)
                if media_root:
                    os.makedirs(media_root, exist_ok=True)
                    filename = f"screenshot_{test_type}_{hash(url)}.png"
                    filepath = os.path.join(media_root, filename)
                    with open(filepath, 'wb') as f:
                        f.write(screenshot_bytes)
                    return filepath
                return None
            except Exception as e:
                logger.error(f"Error uploading screenshot to Cloudinary: {e}")
                # Fallback to local storage
                media_root = getattr(settings, 'MEDIA_ROOT', None)
                if media_root:
                    os.makedirs(media_root, exist_ok=True)
                    filename = f"screenshot_{test_type}_{hash(url)}.png"
                    filepath = os.path.join(media_root, filename)
                    with open(filepath, 'wb') as f:
                        f.write(screenshot_bytes)
                    return filepath
                return None
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None


def run_test_sync(url: str, test_type: str, screenshots_dir: Optional[str] = None) -> Dict:
    """
    Synchronous wrapper for running tests.
    This is used by Django views which are synchronous.
    """
    service = BrowserAutomationService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(service.run_test(url, test_type, screenshots_dir))
    finally:
        loop.close()

