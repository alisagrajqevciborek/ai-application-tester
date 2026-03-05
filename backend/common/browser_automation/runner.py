"""
Main browser automation runner - orchestrates test execution.
"""
import asyncio
import os
import shutil
import tempfile
import logging
from typing import Dict, Optional, List
try:
    from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError  # type: ignore[import-untyped]
except ImportError:
    raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install chromium")

from .screenshots import ScreenshotManager
from .artifacts import ArtifactManager
from .issues import IssueManager
from .collectors import setup_console_collector, setup_network_collector
from ..screenshot_annotator import ScreenshotAnnotator

logger = logging.getLogger(__name__)


class BrowserAutomationService:
    """Service for running automated browser tests using Playwright."""
    
    def __init__(self):
        self.timeout = 120000  # Increased to 120 seconds (2 minutes)
        self.viewport_width = 1920
        self.viewport_height = 1080
        self.annotator = ScreenshotAnnotator()
        self.screenshot_manager = ScreenshotManager(self.annotator)
        self.artifact_manager = ArtifactManager()
        self._current_test_type: str = ""
    
    async def run_test(
        self,
        url: str,
        test_type: str,
        screenshots_dir: Optional[str] = None,
        check_broken_links: bool = False,
        check_auth: bool = False,
        auth_credentials: Optional[Dict] = None,
        skip_runtime_checks: bool = False,
    ) -> Dict:
        """Run automated tests on a given URL."""
        async with async_playwright() as p:
            # Reset per-run state
            self.screenshot_manager.reset()
            self.artifact_manager.reset()
            self._current_test_type = test_type
            issue_manager = IssueManager(self.screenshot_manager, self.annotator, test_type)
            issue_manager.artifact_manager = self.artifact_manager  # Give access to artifact manager
            
            record_video = os.getenv('PLAYWRIGHT_RECORD_VIDEO', '1') == '1'
            video_dir: Optional[str] = None
            if record_video:
                video_dir = tempfile.mkdtemp(prefix='pw-video-')
            
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                ignore_https_errors=True,
                record_video_dir=video_dir,
                record_video_size={'width': self.viewport_width, 'height': self.viewport_height} if record_video else None,
            )
            page = await context.new_page()
            
            try:
                await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            except Exception:
                pass
            
            console_logs = []
            network_requests = []
            network_failures = []
            main_document_headers = {}
            
            setup_console_collector(page, url, test_type, console_logs, self.screenshot_manager, screenshots_dir)
            setup_network_collector(page, network_requests, network_failures, main_document_headers, url)
            
            try:
                logger.info(f"Navigating to {url}")
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                except PlaywrightTimeoutError:
                    logger.warning(f"domcontentloaded timed out for {url}, trying with 'commit'")
                    await page.goto(url, wait_until='commit', timeout=self.timeout)
                
                logger.info("Waiting for page to fully load...")
                # Wait for load state with timeout - don't block if it takes too long
                try:
                    await page.wait_for_load_state('load', timeout=20000)  # Reduced from 30000
                except PlaywrightTimeoutError:
                    logger.warning("Page load state timed out, continuing anyway")
                
                # Skip networkidle - it can hang on pages with continuous network activity
                # Instead, just wait a reasonable amount of time for JS to execute
                logger.info("Waiting for JavaScript execution...")
                await page.wait_for_timeout(3000)  # Reduced from 5000 to 3 seconds
                
                # Check if page has content (quick check)
                has_content = await page.evaluate('''() => {
                    const body = document.body;
                    if (!body) return false;
                    const text = body.innerText || body.textContent || '';
                    const hasText = text.trim().length > 0;
                    const hasVisibleElements = body.querySelector('*') !== null;
                    return hasText || hasVisibleElements;
                }''')
                
                if not has_content:
                    logger.warning("Page appears to have no visible content, waiting a bit more...")
                    await page.wait_for_timeout(2000)  # Reduced from 3000
                
                # Always capture baseline screenshot
                try:
                    baseline_bytes = await page.screenshot(full_page=True)
                    await self.screenshot_manager.upload_and_record(
                        baseline_bytes,
                        url,
                        test_type,
                        'baseline_fullpage',
                        screenshots_dir,
                        kind='baseline_fullpage',
                    )
                except Exception as e:
                    logger.warning(f"Failed to capture baseline screenshot: {e}")
                
                # Import and run test suites
                from . import tests_functional, tests_regression, tests_performance, tests_accessibility
                
                if test_type == 'functional':
                    results = await tests_functional.run_functional_tests(
                        page, url, screenshots_dir, console_logs, network_failures,
                        main_document_headers or {}, issue_manager,
                        skip_runtime_checks=skip_runtime_checks,
                    )
                elif test_type == 'regression':
                    results = await tests_regression.run_regression_tests(
                        page, url, screenshots_dir, console_logs, network_failures, issue_manager,
                        skip_runtime_checks=skip_runtime_checks,
                    )
                elif test_type == 'performance':
                    results = await tests_performance.run_performance_tests(
                        page, url, screenshots_dir, console_logs, network_requests, issue_manager
                    )
                elif test_type == 'accessibility':
                    results = await tests_accessibility.run_accessibility_tests(
                        page, url, screenshots_dir, console_logs, issue_manager
                    )
                elif test_type in ('broken_links', 'authentication'):
                    # broken_links / authentication are add-on checks that run on
                    # top of a functional baseline.  The runner executes functional
                    # tests and the add-on flags (check_broken_links / check_auth)
                    # are handled further below.
                    #
                    # NOTE: "general" is no longer handled here — it is dispatched
                    # as parallel Celery steps in execute_test_run_task().
                    results = await tests_functional.run_functional_tests(
                        page, url, screenshots_dir, console_logs, network_failures,
                        main_document_headers or {}, issue_manager,
                        skip_runtime_checks=skip_runtime_checks,
                    )
                else:
                    logger.warning(f"Unknown test_type={test_type!r}; defaulting to functional suite")
                    results = await tests_functional.run_functional_tests(
                        page, url, screenshots_dir, console_logs, network_failures,
                        main_document_headers or {}, issue_manager,
                        skip_runtime_checks=skip_runtime_checks,
                    )
                
                issues = results.get('issues', [])
                
                if check_broken_links:
                    from .helpers import check_broken_links as check_broken_links_func
                    await check_broken_links_func(page, url, issues)
                
                if check_auth and auth_credentials:
                    from .helpers import test_authentication
                    await test_authentication(page, url, issues, auth_credentials)
                
                if check_broken_links or check_auth:
                    total_major_issues = len([i for i in issues if i.get('severity') in ['critical', 'major']])
                    if total_major_issues > 0:
                        new_pass_rate = max(0, results.get('pass_rate', 100) - (total_major_issues * 5))
                        results['pass_rate'] = new_pass_rate
                        results['fail_rate'] = 100 - new_pass_rate
                        results['status'] = 'failed' if new_pass_rate < 70 else 'success'
                
                results['issues'] = issues
                
                issues_exist = bool(issues)
                is_failed = results.get('status') == 'failed'
                something_wrong = issues_exist or is_failed
                
                # Extra screenshots when needed
                try:
                    needs_extra = (test_type == 'accessibility') or issues_exist
                    if needs_extra:
                        await self._capture_extra_screenshots(page, url, test_type, screenshots_dir)
                except Exception:
                    pass
                
                # Always capture before/after screenshots at the end of test run
                logger.info("Capturing before/after screenshots...")
                try:
                    await self._capture_failure_screenshots(page, url, test_type, screenshots_dir, step_name='test_completion')
                    logger.info("Before/after screenshots captured successfully")
                except Exception as e:
                    logger.error(f"Error capturing before/after screenshots: {e}", exc_info=True)
                
                if something_wrong:
                    try:
                        after_run_bytes = await page.screenshot(full_page=True)
                        await self.screenshot_manager.upload_and_record(
                            after_run_bytes,
                            url,
                            test_type,
                            'after_run_fullpage',
                            screenshots_dir,
                            kind='after_run_fullpage',
                        )
                    except Exception:
                        pass
                
                # Get video path before closing (if video recording is enabled)
                video_path_to_save: Optional[str] = None
                if record_video and something_wrong:
                    try:
                        if page.video:
                            video_path = await page.video.path()
                            video_path_to_save = str(video_path) if video_path else None
                    except Exception as e:
                        logger.warning(f"Error getting video path before close: {e}")
                
                # Close page (this finalizes the video file)
                try:
                    await page.close()
                except Exception:
                    pass
                
                # Now save artifacts (trace and video)
                try:
                    await self.artifact_manager.finalize_debug_artifacts(
                        context,
                        page,
                        url,
                        test_type,
                        save_trace=something_wrong,
                        save_video=something_wrong and record_video,
                        video_path=video_path_to_save,
                    )
                except Exception as e:
                    logger.warning(f"Error finalizing artifacts: {e}")
                
                results['console_logs'] = console_logs
                results['network_requests'] = network_requests[:50]
                results['network_failures'] = network_failures
                results['screenshots_meta'] = self.screenshot_manager.get_metadata()
                
                # Get artifacts and log them for debugging
                artifacts_meta = self.artifact_manager.get_metadata()
                results['artifacts'] = artifacts_meta
                logger.info(f"Total artifacts collected: {len(artifacts_meta)}")
                for idx, artifact in enumerate(artifacts_meta):
                    logger.info(f"Artifact {idx+1}: kind={artifact.get('kind')}, url={artifact.get('url', '')[:80]}..., note={artifact.get('note')}")
                
                meta_urls = [m.get('url') for m in self.screenshot_manager.get_metadata() if m.get('url')]
                existing = results.get('screenshots') if isinstance(results.get('screenshots'), list) else []
                seen = set()
                merged: List[str] = []
                for u in (existing or []) + meta_urls:
                    if not u or u in seen:
                        continue
                    seen.add(u)
                    merged.append(u)
                results['screenshots'] = merged
                
                results['ai_summary'] = None
                results['ai_tags'] = []
                results['ai_suggestions'] = []
                
                try:
                    await context.close()
                except Exception:
                    pass
                
                await browser.close()
                
                if video_dir:
                    shutil.rmtree(video_dir, ignore_errors=True)
                
                return results
                
            except PlaywrightTimeoutError as e:
                logger.error(f"Timeout error: {e}")
                try:
                    await self._capture_failure_screenshots(page, url, test_type, screenshots_dir, step_name='timeout')
                except Exception:
                    pass
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await self.artifact_manager.finalize_debug_artifacts(
                        context, page, url, test_type, save_trace=True, save_video=record_video
                    )
                except Exception:
                    pass
                result = {
                    'pass_rate': 0,
                    'fail_rate': 100,
                    'status': 'failed',
                    'issues': [{'severity': 'critical', 'title': 'Page load timeout', 'description': str(e)}],
                    'screenshots': [m.get('url') for m in self.screenshot_manager.get_metadata() if m.get('url')],
                    'screenshots_meta': self.screenshot_manager.get_metadata(),
                    'artifacts': self.artifact_manager.get_metadata(),
                    'ai_summary': None,
                    'ai_tags': [],
                    'ai_suggestions': [],
                }
                try:
                    await context.close()
                except Exception:
                    pass
                await browser.close()
                if video_dir:
                    shutil.rmtree(video_dir, ignore_errors=True)
                return result
            except Exception as e:
                logger.error(f"Error during test execution: {e}")
                try:
                    await self._capture_failure_screenshots(page, url, test_type, screenshots_dir, step_name='exception')
                except Exception:
                    pass
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await self.artifact_manager.finalize_debug_artifacts(
                        context, page, url, test_type, save_trace=True, save_video=record_video
                    )
                except Exception:
                    pass
                result = {
                    'pass_rate': 0,
                    'fail_rate': 100,
                    'status': 'failed',
                    'issues': [{'severity': 'critical', 'title': 'Test execution error', 'description': str(e)}],
                    'screenshots': [m.get('url') for m in self.screenshot_manager.get_metadata() if m.get('url')],
                    'screenshots_meta': self.screenshot_manager.get_metadata(),
                    'artifacts': self.artifact_manager.get_metadata(),
                    'ai_summary': None,
                    'ai_tags': [],
                    'ai_suggestions': [],
                }
                try:
                    await context.close()
                except Exception:
                    pass
                await browser.close()
                if video_dir:
                    shutil.rmtree(video_dir, ignore_errors=True)
                return result
    
    async def _capture_extra_screenshots(
        self,
        page: Page,
        url: str,
        test_type: str,
        screenshots_dir: Optional[str],
    ) -> None:
        """Capture extra screenshots when something is wrong."""
        viewport_bytes = await page.screenshot(full_page=False)
        await self.screenshot_manager.upload_and_record(
            viewport_bytes, url, test_type, 'extra_viewport', screenshots_dir, kind='extra_viewport'
        )
        
        try:
            page_height = await page.evaluate('document.body.scrollHeight')
            if page_height and page_height > self.viewport_height * 1.5:
                await page.evaluate(f'window.scrollTo(0, {int(page_height) // 2})')
                scrolled_bytes = await page.screenshot(full_page=False)
                await self.screenshot_manager.upload_and_record(
                    scrolled_bytes, url, test_type, 'extra_scrolled', screenshots_dir, kind='extra_scrolled'
                )
        except Exception:
            pass
        finally:
            try:
                await page.evaluate('window.scrollTo(0, 0)')
            except Exception:
                pass
        
        fullpage_bytes = await page.screenshot(full_page=True)
        await self.screenshot_manager.upload_and_record(
            fullpage_bytes, url, test_type, 'extra_fullpage', screenshots_dir, kind='extra_fullpage'
        )
    
    async def _capture_failure_screenshots(
        self,
        page: Page,
        url: str,
        test_type: str,
        screenshots_dir: Optional[str],
        *,
        step_name: str,
    ) -> None:
        """Capture before/after screenshots and save as artifacts."""
        logger.info(f"Capturing before screenshot for step: {step_name}")
        try:
            before_bytes = await page.screenshot(full_page=False)
            before_url = await self.screenshot_manager.upload_to_cloudinary(
                before_bytes, url, test_type, f"before_{step_name}", screenshots_dir
            )
            if before_url:
                logger.info(f"Before screenshot uploaded: {before_url}")
                self.artifact_manager._record_artifact_meta(
                    url=before_url,
                    kind='before_step',
                    note=f"Before {step_name}",
                )
            else:
                logger.warning("Before screenshot upload returned None")
        except Exception as e:
            logger.error(f"Error capturing/uploading before screenshot: {e}", exc_info=True)
        
        logger.info(f"Capturing after screenshot for step: {step_name}")
        try:
            after_bytes = await page.screenshot(full_page=True)
            after_url = await self.screenshot_manager.upload_to_cloudinary(
                after_bytes, url, test_type, f"after_{step_name}", screenshots_dir
            )
            if after_url:
                logger.info(f"After screenshot uploaded: {after_url}")
                self.artifact_manager._record_artifact_meta(
                    url=after_url,
                    kind='after_step',
                    note=f"After {step_name}",
                )
            else:
                logger.warning("After screenshot upload returned None")
        except Exception as e:
            logger.error(f"Error capturing/uploading after screenshot: {e}", exc_info=True)


def run_test_sync(url: str, test_type: str, screenshots_dir: Optional[str] = None) -> Dict:
    """Synchronous wrapper for running tests."""
    service = BrowserAutomationService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(service.run_test(url, test_type, screenshots_dir))
    finally:
        loop.close()
