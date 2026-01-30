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
        except:
            return "unknown"
    
    async def get_element_box(self, element) -> Optional[Dict]:
        """Get the bounding box for an element."""
        try:
            return await element.bounding_box()
        except:
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
        console_logs: Optional[List[Dict]] = None
    ):
        """Helper to add an issue with optional element metadata."""
        issue = {
            'severity': severity,
            'title': title,
            'description': description,
            'location': location
        }
        
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
        elif not issue.get('element_screenshot'):
            try:
                screenshot_bytes = await page.screenshot(full_page=False)
                screenshot_url = await self.screenshot_manager.upload_and_record(
                    screenshot_bytes,
                    location,
                    self.current_test_type or "automated",
                    f"issue_{severity}_{len(issues)}",
                    screenshots_dir,
                    kind='issue_viewport',
                    issue_title=title,
                )
                if screenshot_url:
                    issue['element_screenshot'] = screenshot_url
            except Exception as e:
                logger.warning(f"Failed to capture screenshot for issue: {e}")
        
        issues.append(issue)
