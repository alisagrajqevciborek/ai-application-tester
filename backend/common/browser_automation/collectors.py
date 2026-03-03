"""
Console and network data collection.
"""
import logging
from typing import List, Dict, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


def setup_console_collector(
    page: Page,
    url: str,
    test_type: str,
    console_logs: List[Dict],
    screenshot_manager,
    screenshots_dir: Optional[str],
) -> None:
    """Set up console log collection with screenshot capture for errors/warnings."""
    async def handle_console(msg):
        log_entry = {
            'type': msg.type,
            'text': msg.text,
            'location': str(msg.location) if msg.location else None
        }
        console_logs.append(log_entry)
        
        if msg.type in ['error', 'warning']:
            try:
                screenshot_bytes = await page.screenshot(full_page=False)
                element = None
                
                error_selectors = [
                    '[role="alert"]',
                    '.error:visible',
                    '.alert:visible',
                    '[class*="error"]:visible',
                    '[class*="warning"]:visible'
                ]
                
                for selector in error_selectors:
                    try:
                        found = await page.query_selector(selector)
                        if found and await found.is_visible():
                            element = found
                            break
                    except:
                        continue
                
                if element:
                    try:
                        box = await element.bounding_box()
                        if box:
                            annotated_bytes = screenshot_manager.annotator.annotate_screenshot(
                                screenshot_bytes,
                                element_box=box,
                                label=f"Console {msg.type}",
                                crop_to_element=True
                            )
                            screenshot_url = await screenshot_manager.upload_and_record(
                                annotated_bytes,
                                url,
                                test_type,
                                f"console_{msg.type}_{len(console_logs)-1}",
                                screenshots_dir,
                                kind=f"console_{msg.type}",
                            )
                        else:
                            screenshot_url = await screenshot_manager.upload_and_record(
                                screenshot_bytes,
                                url,
                                test_type,
                                f"console_{msg.type}_{len(console_logs)-1}",
                                screenshots_dir,
                                kind=f"console_{msg.type}",
                            )
                    except:
                        screenshot_url = await screenshot_manager.upload_and_record(
                            screenshot_bytes,
                            url,
                            test_type,
                            f"console_{msg.type}_{len(console_logs)-1}",
                            screenshots_dir,
                            kind=f"console_{msg.type}",
                        )
                else:
                    screenshot_url = await screenshot_manager.upload_and_record(
                        screenshot_bytes,
                        url,
                        test_type,
                        f"console_{msg.type}_{len(console_logs)-1}",
                        screenshots_dir,
                        kind=f"console_{msg.type}",
                    )
                
                if screenshot_url:
                    log_entry['screenshot'] = screenshot_url
            except Exception as e:
                logger.warning(f"Failed to capture screenshot for console {msg.type}: {e}")
    
    page.on('console', handle_console)
    
    def handle_page_error(error):
        console_logs.append({
            'type': 'error',
            'text': f"Uncaught Exception: {str(error)}",
            'location': getattr(error, 'stack', None) or url
        })
    
    page.on('pageerror', handle_page_error)


def setup_network_collector(
    page: Page,
    network_requests: List[Dict],
    network_failures: List[Dict],
    main_document_headers: Dict,
    url: str,
) -> None:
    """Set up network request/response collection."""
    def handle_request(request):
        network_requests.append({
            'url': request.url,
            'method': request.method,
            'resource_type': request.resource_type,
            'headers': request.headers
        })
    
    # 401 (Unauthorized) and 403 (Forbidden) are access-control responses,
    # not broken resources. Some servers also return 404 for protected paths
    # to avoid disclosing their existence — those are excluded too.
    ACCESS_RESTRICTED_STATUSES = {401, 403}

    def handle_response(response):
        if response.status >= 400 and response.status not in ACCESS_RESTRICTED_STATUSES:
            network_failures.append({
                'url': response.url,
                'status': response.status,
                'status_text': response.status_text,
                'resource_type': response.request.resource_type
            })
        if response.request.resource_type == 'document' and response.url == url:
            try:
                main_document_headers.update(dict(response.headers))
            except:
                pass
    
    page.on('request', handle_request)
    page.on('response', handle_response)
