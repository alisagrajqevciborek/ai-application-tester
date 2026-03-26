"""
Issue handling and element utilities.
"""
import logging
from typing import Optional, Dict, List, Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class IssueManager:
    """Manages issue creation with screenshots."""
    
    def __init__(self, screenshot_manager, annotator, current_test_type: str):
        self.screenshot_manager = screenshot_manager
        self.annotator = annotator
        self.current_test_type = current_test_type
        self.artifact_manager: Optional[Any] = None  # Will be set by runner
    
    async def get_element_selector(self, element) -> str:
        """Get a unique CSS selector for an element."""
        try:
            return await element.evaluate('''el => {
                if (!(el instanceof Element)) return 'unknown';
                const path = [];
                while (el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.nodeName.toLowerCase();
                    if (el.id) {
                        selector += '#' + el.id;
                        path.unshift(selector);
                        break;
                    } else {
                        let sibling = el;
                        let nth = 1;
                        while (sibling = sibling.previousElementSibling) {
                            if (sibling.nodeName.toLowerCase() == selector) nth++;
                        }
                        if (nth != 1) selector += ":nth-of-type(" + nth + ")";
                    }
                    path.unshift(selector);
                    el = el.parentNode;
                }
                return path.join(" > ");
            }''')
        except Exception as e:
            logger.debug(f"Failed to compute element selector: {e}")
            return "unknown"
    
    async def get_element_box(self, element) -> Optional[Dict]:
        """Get the bounding box for an element."""
        try:
            return await element.bounding_box()
        except Exception as e:
            logger.debug(f"Failed to get element bounding box: {e}")
            return None
    
    async def capture_annotated_issue_screenshot(
        self,
        page: Page,
        url: str,
        test_type: str,
        issue: Dict,
        element,
        screenshots_dir: Optional[str]
    ) -> Optional[str]:
        """Capture an annotated and cropped screenshot for a specific issue."""
        try:
            screenshot_bytes = await page.screenshot(full_page=False)
            box = await self.get_element_box(element)
            if not box:
                return None
            
            annotated_bytes = self.annotator.annotate_screenshot(
                screenshot_bytes,
                element_box=box,
                label=issue.get('title', 'Issue'),
                crop_to_element=True
            )
            
            return await self.screenshot_manager.upload_and_record(
                annotated_bytes,
                url,
                test_type,
                "issue_highlight",
                screenshots_dir,
                kind='issue_annotated',
                issue_title=issue.get('title'),
                selector=issue.get('selector'),
            )
        except Exception as e:
            logger.error(f"Error capturing annotated issue screenshot: {e}")
            return None
    
    async def add_issue(
        self,
        issues: List[Dict],
        severity: str,
        title: str,
        description: str,
        location: str,
        page: Page,
        element=None,
        screenshots_dir: Optional[str] = None,
        console_log_index: Optional[int] = None,
        console_logs: Optional[List[Dict]] = None,
    ):
        """Helper to add an issue with optional element metadata."""
        issue = {
            'severity': severity,
            'title': title,
            'description': description,
            'location': location
        }
        
        # Capture before/after screenshots for this specific issue (if artifact_manager is available).
        # These are primarily useful for visually inspectable issues where the page actually changes.
        if self.artifact_manager and element:
            try:
                logger.info(f"Capturing before/after screenshots for issue: {title}")
                
                # Before screenshot (viewport) - state before issue
                before_bytes = await page.screenshot(full_page=False)
                before_url = await self.screenshot_manager.upload_to_cloudinary(
                    before_bytes, location, self.current_test_type or "automated", f"before_issue_{len(issues)}", screenshots_dir
                )
                if before_url:
                    self.artifact_manager._record_artifact_meta(
                        url=before_url,
                        kind='before_step',
                        note=f"Before issue: {title}",
                    )
                    issue['before_screenshot'] = before_url
                    logger.info(f"Before screenshot for issue captured: {before_url}")
                
                # After screenshot (full page) - showing the issue
                after_bytes = await page.screenshot(full_page=True)
                after_url = await self.screenshot_manager.upload_to_cloudinary(
                    after_bytes, location, self.current_test_type or "automated", f"after_issue_{len(issues)}", screenshots_dir
                )
                if after_url:
                    self.artifact_manager._record_artifact_meta(
                        url=after_url,
                        kind='after_step',
                        note=f"After issue: {title}",
                    )
                    issue['after_screenshot'] = after_url
                    logger.info(f"After screenshot for issue captured: {after_url}")
            except Exception as e:
                logger.warning(f"Error capturing before/after for issue: {e}", exc_info=True)
        
        if console_log_index is not None and console_logs and console_log_index < len(console_logs):
            log_entry = console_logs[console_log_index]
            if log_entry.get('screenshot'):
                issue['context_screenshot'] = log_entry['screenshot']
                if not element:
                    issue['element_screenshot'] = log_entry['screenshot']
        
        if element:
            selector = await self.get_element_selector(element)
            issue['selector'] = selector
            
            if not issue.get('element_screenshot'):
                try:
                    element_bytes = await element.screenshot()
                    element_url = await self.screenshot_manager.upload_and_record(
                        element_bytes,
                        location,
                        self.current_test_type or "automated",
                        f"issue_element_{severity}_{len(issues)}",
                        screenshots_dir,
                        kind='issue_element',
                        issue_title=title,
                        selector=selector,
                    )
                    if element_url:
                        issue['element_screenshot'] = element_url
                        issue['element_only_screenshot'] = element_url
                except Exception:
                    pass
            
            try:
                annotated_url = await self.capture_annotated_issue_screenshot(
                    page, location, self.current_test_type or "automated", issue, element, screenshots_dir
                )
                if annotated_url:
                    issue['annotated_screenshot'] = annotated_url
                    if not issue.get('element_screenshot'):
                        issue['element_screenshot'] = annotated_url
            except Exception:
                pass

        # Always try to attach at least one screenshot per issue for UI usefulness.
        # Prefer element/annotated screenshots when available; otherwise attach a
        # reference viewport screenshot captured at the time the issue is recorded.
        if (
            not issue.get('element_screenshot')
            and not issue.get('annotated_screenshot')
            and not issue.get('before_screenshot')
            and not issue.get('after_screenshot')
            and not issue.get('context_screenshot')
            and not issue.get('reference_screenshot')
        ):
            try:
                ref_bytes = await page.screenshot(full_page=False)
                ref_url = await self.screenshot_manager.upload_and_record(
                    ref_bytes,
                    location,
                    self.current_test_type or "automated",
                    f"issue_reference_{severity}_{len(issues)}",
                    screenshots_dir,
                    kind='issue_reference',
                    issue_title=title,
                    selector=issue.get('selector'),
                )
                if ref_url:
                    issue['reference_screenshot'] = ref_url
            except Exception:
                pass
        
        issues.append(issue)
