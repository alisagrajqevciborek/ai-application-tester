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
        self.timeout = 30000  # 30 seconds default timeout
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
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            try:
                # Navigate to the URL
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until='networkidle', timeout=self.timeout)
                
                # Wait a bit for page to fully load
                await page.wait_for_timeout(2000)
                
                # Run tests based on type
                if test_type == 'functional':
                    results = await self._run_functional_tests(page, url, screenshots_dir)
                elif test_type == 'regression':
                    results = await self._run_regression_tests(page, url, screenshots_dir)
                elif test_type == 'performance':
                    results = await self._run_performance_tests(page, url, screenshots_dir)
                elif test_type == 'accessibility':
                    results = await self._run_accessibility_tests(page, url, screenshots_dir)
                else:
                    # Default: run all tests
                    results = await self._run_all_tests(page, url, screenshots_dir)
                
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
    
    async def _run_functional_tests(self, page: Page, url: str, screenshots_dir: Optional[str]) -> Dict:
        """Run functional tests - check basic page functionality."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check if page loaded successfully
        try:
            title = await page.title()
            if title:
                tests_passed += 1
            else:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': 'Page title missing',
                    'description': 'The page does not have a title tag.',
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
                    'description': 'The page does not have a clear main content area.',
                    'location': url
                })
        except Exception as e:
            tests_failed += 1
        
        # Test 3: Check for links
        try:
            links = await page.query_selector_all('a[href]')
            if len(links) > 0:
                tests_passed += 1
            else:
                issues.append({
                    'severity': 'minor',
                    'title': 'No links found on page',
                    'description': 'The page does not contain any navigation links.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking links: {e}")
        
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
    
    async def _run_regression_tests(self, page: Page, url: str, screenshots_dir: Optional[str]) -> Dict:
        """Run regression tests - check for broken functionality."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check for JavaScript errors
        js_errors = []
        page.on('pageerror', lambda error: js_errors.append(str(error)))
        
        # Wait a bit for JS to execute
        await page.wait_for_timeout(3000)
        
        if len(js_errors) == 0:
            tests_passed += 1
        else:
            tests_failed += 1
            for error in js_errors[:5]:  # Report first 5 errors
                issues.append({
                    'severity': 'critical',
                    'title': 'JavaScript error detected',
                    'description': error,
                    'location': url
                })
        
        # Test 2: Check for broken images
        try:
            images = await page.query_selector_all('img')
            broken_images = 0
            for img in images[:10]:  # Check first 10 images
                try:
                    natural_width = await img.evaluate('el => el.naturalWidth')
                    if natural_width == 0:
                        broken_images += 1
                except:
                    broken_images += 1
            
            if broken_images == 0:
                tests_passed += 1
            else:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': f'{broken_images} broken image(s) found',
                    'description': 'Some images on the page failed to load.',
                    'location': url
                })
        except Exception as e:
            logger.warning(f"Error checking images: {e}")
        
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
    
    async def _run_performance_tests(self, page: Page, url: str, screenshots_dir: Optional[str]) -> Dict:
        """Run performance tests - check page load time and performance metrics."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Measure page load time
        await page.wait_for_load_state('networkidle')
        load_time = await page.evaluate('() => performance.timing.loadEventEnd - performance.timing.navigationStart')
        
        # Convert to seconds
        load_time_seconds = load_time / 1000 if load_time else 0
        
        # Test 1: Page load time
        if load_time_seconds < 3:
            tests_passed += 1
        elif load_time_seconds < 5:
            tests_passed += 1
            issues.append({
                'severity': 'minor',
                'title': 'Page load time is acceptable but could be improved',
                'description': f'Page loaded in {load_time_seconds:.2f} seconds.',
                'location': url
            })
        else:
            tests_failed += 1
            issues.append({
                'severity': 'major',
                'title': 'Slow page load time',
                'description': f'Page took {load_time_seconds:.2f} seconds to load, exceeding the 3-second threshold.',
                'location': url
            })
        
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
    
    async def _run_accessibility_tests(self, page: Page, url: str, screenshots_dir: Optional[str]) -> Dict:
        """Run accessibility tests - check WCAG compliance."""
        issues = []
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check for alt text on images
        try:
            images = await page.query_selector_all('img')
            images_without_alt = []
            for img in images:
                alt = await img.get_attribute('alt')
                if alt is None:
                    images_without_alt.append(img)
            
            if len(images_without_alt) == 0:
                tests_passed += 1
            else:
                tests_failed += 1
                issues.append({
                    'severity': 'major',
                    'title': f'{len(images_without_alt)} image(s) missing alt text',
                    'description': 'Images without alt text are not accessible to screen readers.',
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
                else:
                    tests_failed += 1
                    issues.append({
                        'severity': 'major',
                        'title': 'Missing H1 heading',
                        'description': 'The page does not have an H1 heading, which is important for accessibility and SEO.',
                        'location': url
                    })
        except Exception:
            pass
        
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
    
    async def _run_all_tests(self, page: Page, url: str, screenshots_dir: Optional[str]) -> Dict:
        """Run all test types."""
        functional_results = await self._run_functional_tests(page, url, screenshots_dir)
        regression_results = await self._run_regression_tests(page, url, screenshots_dir)
        performance_results = await self._run_performance_tests(page, url, screenshots_dir)
        accessibility_results = await self._run_accessibility_tests(page, url, screenshots_dir)
        
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
            screenshot_bytes = await page.screenshot(full_page=True)
            
            # Upload to Cloudinary
            try:
                import cloudinary
                import cloudinary.uploader
                from django.conf import settings as django_settings
                
                # Configure Cloudinary if not already configured
                if not cloudinary.config().cloud_name:
                    cloudinary.config(
                        cloud_name=django_settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', ''),
                        api_key=django_settings.CLOUDINARY_STORAGE.get('API_KEY', ''),
                        api_secret=django_settings.CLOUDINARY_STORAGE.get('API_SECRET', ''),
                    )
                
                # Generate a unique filename
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"screenshots/{test_type}_{url_hash}"
                
                # Upload to Cloudinary
                from io import BytesIO
                result = cloudinary.uploader.upload(
                    BytesIO(screenshot_bytes),
                    folder='test_screenshots',
                    public_id=filename,
                    resource_type='image',
                    format='png'
                )
                
                # Return the Cloudinary URL
                return result.get('secure_url') or result.get('url')
                
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

