"""
Runner for executing AI-generated test cases.
"""
import logging
from typing import Any, Dict, List
try:
    from playwright.async_api import async_playwright, Locator, Page, TimeoutError as PlaywrightTimeoutError  # type: ignore[import-untyped]
except ImportError:
    raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install chromium")

from .screenshots import ScreenshotManager
from ..screenshot_annotator import ScreenshotAnnotator
from ..test_case_contract import ALLOWED_STEP_ACTIONS

logger = logging.getLogger(__name__)


class GeneratedTestRunner:
    """Runner for executing AI-generated test case steps."""
    
    def __init__(self):
        self.timeout = 30000  # 30 seconds per step
        self.viewport_width = 1920
        self.viewport_height = 1080
        self.annotator = ScreenshotAnnotator()
        self.screenshot_manager = ScreenshotManager(self.annotator)

    @staticmethod
    def _parse_wait_time(value: Any) -> int:
        """Parse an optional wait duration in milliseconds with safe defaults."""
        default_ms = 2000
        max_ms = 120000

        if value is None:
            return default_ms

        if isinstance(value, (int, float)):
            wait_ms = int(value)
        elif isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return default_ms
            try:
                wait_ms = int(stripped)
            except ValueError as exc:
                raise ValueError(f"Invalid wait duration: {value!r}") from exc
        else:
            raise ValueError(f"Invalid wait duration type: {type(value).__name__}")

        if wait_ms < 0:
            raise ValueError("Wait duration cannot be negative")

        return min(wait_ms, max_ms)

    async def _resolve_unique_visible_locator(self, page: Page, selector: Any, action: str) -> Locator:
        """Resolve a selector to exactly one visible element to avoid ambiguous AI-generated selectors."""
        if not isinstance(selector, str) or not selector.strip():
            raise ValueError(f"{action.capitalize()} action requires a non-empty selector")

        normalized_selector = selector.strip()
        locator = page.locator(normalized_selector)
        count = await locator.count()

        if count == 0:
            raise ValueError(f"Selector not found for {action}: {normalized_selector}")
        if count > 1:
            raise ValueError(
                f"Selector is ambiguous for {action}: {normalized_selector} matched {count} elements"
            )

        target = locator.first
        await target.wait_for(state='visible', timeout=self.timeout)
        return target
    
    async def run_test_case(
        self,
        url: str,
        test_type: str,
        steps: List[Dict],
    ) -> Dict:
        """
        Execute a generated test case with the given steps.
        
        Args:
            url: Base URL of the application
            test_type: Type of test being run
            steps: List of test steps to execute
            
        Returns:
            Test results dictionary
        """
        async with async_playwright() as p:
            self.screenshot_manager.reset()
            
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                ignore_https_errors=True,
            )
            page = await context.new_page()
            
            console_logs: List[Dict] = []
            issues: List[Dict] = []
            step_results: List[Dict] = []
            screenshots: List[str] = []
            
            # Collect console logs - track errors separately
            console_errors: List[Dict] = []
            console_warnings: List[Dict] = []
            
            def handle_console(msg):
                log_entry = {
                    'type': msg.type,
                    'text': msg.text,
                    'location': str(msg.location) if hasattr(msg, 'location') else None
                }
                console_logs.append(log_entry)
                
                # Track errors and warnings separately
                if msg.type == 'error':
                    console_errors.append(log_entry)
                elif msg.type == 'warning':
                    console_warnings.append(log_entry)
            
            page.on('console', handle_console)
            
            passed_steps = 0
            failed_steps = 0
            
            try:
                # Navigate to the initial URL
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                try:
                    await page.wait_for_load_state('load', timeout=5000)
                except PlaywrightTimeoutError:
                    logger.debug("Initial page 'load' state timed out; continuing")
                
                # Capture initial page screenshot
                try:
                    initial_screenshot = await page.screenshot(full_page=False)
                    initial_url = await self.screenshot_manager.upload_and_record(
                        initial_screenshot,
                        url,
                        'generated',
                        'initial_page',
                        None,
                        kind='initial_screenshot',
                    )
                    if initial_url:
                        screenshots.append(initial_url)
                except Exception as e:
                    logger.warning(f"Failed to capture initial screenshot: {e}")
                
                # Execute each step
                for step in steps:
                    step_result = await self._execute_step(page, step, url)
                    step_results.append(step_result)
                    
                    if step_result.get('passed'):
                        passed_steps += 1
                    else:
                        failed_steps += 1
                        # Add issue for failed step with screenshot attached
                        issues.append({
                            'severity': 'major',
                            'title': f"Step {step.get('order', '?')} failed: {step.get('action', 'unknown')}",
                            'description': step_result.get('error', 'Unknown error'),
                            'location': step.get('selector', 'N/A'),
                            'element_screenshot': step_result.get('screenshot_url'),  # Attach screenshot to issue
                        })
                    
                    # Collect all screenshots for gallery view
                    if step_result.get('screenshot_url'):
                        screenshots.append(step_result['screenshot_url'])
                
                # Process console errors as issues
                for error in console_errors:
                    error_text = error.get('text', '')
                    # Skip some common non-critical errors
                    if any(skip in error_text.lower() for skip in ['favicon', 'devtools']):
                        continue
                    issues.append({
                        'severity': 'major' if 'CORS' in error_text or 'TypeError' in error_text else 'minor',
                        'title': 'JavaScript Console Error',
                        'description': error_text[:500],  # Truncate long errors
                        'location': error.get('location', 'Console'),
                    })
                
                # Process console warnings as minor issues
                for warning in console_warnings:
                    warning_text = warning.get('text', '')
                    # Skip deprecation warnings and other non-critical ones
                    if any(skip in warning_text.lower() for skip in ['deprecated', 'devtools']):
                        continue
                    issues.append({
                        'severity': 'minor',
                        'title': 'JavaScript Console Warning',
                        'description': warning_text[:500],
                        'location': warning.get('location', 'Console'),
                    })
                
                # Calculate pass rate factoring in console errors
                total_steps = len(steps)
                step_pass_rate = round((passed_steps / total_steps) * 100) if total_steps > 0 else 100
                
                # Penalize for console errors (each error reduces pass rate)
                critical_console_errors = len([e for e in console_errors if 'CORS' in e.get('text', '') or 'TypeError' in e.get('text', '') or 'ReferenceError' in e.get('text', '')])
                minor_console_errors = len(console_errors) - critical_console_errors
                
                # Deduct points for errors: critical = -5%, minor = -2%
                error_penalty = (critical_console_errors * 5) + (minor_console_errors * 2)
                pass_rate = max(0, step_pass_rate - error_penalty)
                fail_rate = 100 - pass_rate
                
                # Determine overall status
                # Failed if: steps failed OR too many console errors OR pass rate below threshold
                has_critical_errors = critical_console_errors > 0
                has_step_failures = failed_steps > 0
                status = 'failed' if (has_step_failures or has_critical_errors or pass_rate < 70) else 'success'
                
                return {
                    'status': status,
                    'pass_rate': pass_rate,
                    'fail_rate': fail_rate,
                    'passed_steps': passed_steps,
                    'failed_steps': failed_steps,
                    'step_results': step_results,
                    'issues': issues,
                    'screenshots': screenshots,
                    'console_logs': console_logs,
                    'console_error_count': len(console_errors),
                    'console_warning_count': len(console_warnings),
                }
                
            except Exception as e:
                logger.error(f"Error running generated test case: {e}", exc_info=True)
                return {
                    'status': 'failed',
                    'pass_rate': 0,
                    'fail_rate': 100,
                    'passed_steps': passed_steps,
                    'failed_steps': failed_steps + 1,
                    'step_results': step_results,
                    'issues': [{
                        'severity': 'critical',
                        'title': 'Test execution error',
                        'description': str(e),
                        'location': url,
                    }],
                    'screenshots': screenshots,
                    'console_logs': console_logs,
                }
            finally:
                await context.close()
                await browser.close()
    
    async def _execute_step(self, page: Page, step: Dict, base_url: str) -> Dict:
        """
        Execute a single test step.
        
        Args:
            page: Playwright page object
            step: Step definition
            base_url: Base URL of the application
            
        Returns:
            Step result dictionary
        """
        action = str(step.get('action', '')).strip().lower()
        selector = step.get('selector')
        value = step.get('value')
        description = step.get('description', f"Execute {action}")
        
        result = {
            'order': step.get('order', 0),
            'action': action,
            'description': description,
            'passed': False,
            'error': None,
            'screenshot_url': None,
        }
        
        try:
            if action not in ALLOWED_STEP_ACTIONS:
                raise ValueError(f"Unknown action: {action}")

            if action == 'navigate':
                # Navigate to URL (can be relative or absolute)
                target_url = value if value else base_url
                if target_url and not target_url.startswith(('http://', 'https://')):
                    # Relative URL
                    target_url = f"{base_url.rstrip('/')}/{target_url.lstrip('/')}"
                await page.goto(target_url, wait_until='domcontentloaded', timeout=self.timeout)
                try:
                    await page.wait_for_load_state('load', timeout=5000)
                except PlaywrightTimeoutError:
                    logger.debug("Navigate step 'load' state timed out; continuing")
                result['passed'] = True
                
            elif action == 'click':
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.click(timeout=self.timeout)
                result['passed'] = True
                
            elif action == 'fill':
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.fill(str(value or ''), timeout=self.timeout)
                result['passed'] = True
                
            elif action == 'select':
                if value is None:
                    raise ValueError("Select action requires a value")
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.select_option(str(value), timeout=self.timeout)
                result['passed'] = True
                
            elif action == 'wait':
                if selector:
                    locator = page.locator(str(selector).strip()).first
                    await locator.wait_for(state='visible', timeout=self.timeout)
                else:
                    # Wait for a specific duration in ms (default 2000ms).
                    wait_time = self._parse_wait_time(value)
                    await page.wait_for_timeout(wait_time)
                result['passed'] = True
                
            elif action == 'assert':
                target = await self._resolve_unique_visible_locator(page, selector, action)
                if value is not None:
                    expected_text = str(value)
                    text_content = await target.text_content()
                    actual_text = text_content or ''
                    if expected_text.lower() in actual_text.lower():
                        result['passed'] = True
                    else:
                        result['error'] = f"Expected text '{expected_text}' not found. Got: '{actual_text}'"
                else:
                    result['passed'] = await target.is_visible()
                    if not result['passed']:
                        result['error'] = "Element is not visible"
                    
            elif action == 'check':
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.check(timeout=self.timeout)
                result['passed'] = True
                
            elif action == 'uncheck':
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.uncheck(timeout=self.timeout)
                result['passed'] = True
                
            elif action == 'hover':
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.hover(timeout=self.timeout)
                result['passed'] = True
                
            elif action == 'scroll':
                if selector:
                    target = await self._resolve_unique_visible_locator(page, selector, action)
                    await target.scroll_into_view_if_needed(timeout=self.timeout)
                else:
                    # Scroll to bottom of page
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                result['passed'] = True
                
            elif action == 'screenshot':
                # Capture a screenshot at this point
                try:
                    screenshot_bytes = await page.screenshot(full_page=False)
                    screenshot_url = await self.screenshot_manager.upload_and_record(
                        screenshot_bytes,
                        base_url,
                        'generated',
                        f"step_{step.get('order', 0)}",
                        None,
                        kind='step_screenshot',
                    )
                    result['screenshot_url'] = screenshot_url
                    result['passed'] = True
                except Exception as e:
                    logger.warning(f"Failed to capture screenshot: {e}")
                    result['passed'] = True  # Don't fail the step for screenshot issues
                    
            elif action == 'press':
                # Press a key
                key = str(value).strip() if value is not None else 'Enter'
                if selector:
                    target = await self._resolve_unique_visible_locator(page, selector, action)
                    await target.press(key, timeout=self.timeout)
                else:
                    await page.keyboard.press(key)
                result['passed'] = True
                
            elif action == 'type':
                # Type text with delays (more realistic typing)
                target = await self._resolve_unique_visible_locator(page, selector, action)
                await target.type(str(value or ''), delay=50, timeout=self.timeout)
                result['passed'] = True
                
        except PlaywrightTimeoutError as e:
            result['error'] = f"Timeout during {action} step on selector '{selector}'"
            logger.warning(f"Step timeout: {description} - {e}")
        except Exception as e:
            result['error'] = str(e)
            logger.warning(f"Step failed: {description} - {e}")
        
        # Capture screenshot on failure
        if not result['passed'] and not result.get('screenshot_url'):
            try:
                screenshot_bytes = await page.screenshot(full_page=False)
                screenshot_url = await self.screenshot_manager.upload_and_record(
                    screenshot_bytes,
                    base_url,
                    'generated',
                    f"step_{step.get('order', 0)}_error",
                    None,
                    kind='error_screenshot',
                    issue_title=description,
                )
                result['screenshot_url'] = screenshot_url
            except Exception:
                pass
        
        # Capture screenshot on success if no screenshot yet (for visual record)
        if result['passed'] and not result.get('screenshot_url'):
            try:
                screenshot_bytes = await page.screenshot(full_page=False)
                screenshot_url = await self.screenshot_manager.upload_and_record(
                    screenshot_bytes,
                    base_url,
                    'generated',
                    f"step_{step.get('order', 0)}",
                    None,
                    kind='step_screenshot',
                )
                result['screenshot_url'] = screenshot_url
            except Exception:
                pass
        
        return result
