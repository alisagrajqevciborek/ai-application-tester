"""
Screenshot capture and upload functionality.
"""
import os
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
from ..screenshot_annotator import ScreenshotAnnotator

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Manages screenshot capture, upload, and metadata tracking."""
    
    def __init__(self, annotator: ScreenshotAnnotator):
        self.annotator = annotator
        self._screenshot_meta: List[Dict[str, Any]] = []
        self.viewport_height = 1080
    
    def reset(self):
        """Reset per-run state."""
        self._screenshot_meta = []
    
    def get_metadata(self) -> List[Dict[str, Any]]:
        """Get collected screenshot metadata."""
        return self._screenshot_meta
    
    def _record_screenshot_meta(
        self,
        *,
        url: str,
        kind: str,
        issue_title: Optional[str] = None,
        selector: Optional[str] = None,
    ) -> None:
        self._screenshot_meta.append({
            'url': url,
            'kind': kind,
            'issue_title': issue_title,
            'selector': selector,
            'ai_summary': None,
            'ai_tags': [],
            'ai_suggestions': [],
        })
    
    async def upload_and_record(
        self,
        screenshot_bytes: bytes,
        tested_url: str,
        test_type: str,
        screenshot_type: str,
        screenshots_dir: Optional[str],
        *,
        kind: str,
        issue_title: Optional[str] = None,
        selector: Optional[str] = None,
    ) -> Optional[str]:
        """Upload screenshot and record metadata."""
        screenshot_url = await self.upload_to_cloudinary(
            screenshot_bytes,
            tested_url,
            test_type,
            screenshot_type,
            screenshots_dir,
        )
        if screenshot_url:
            self._record_screenshot_meta(
                url=screenshot_url,
                kind=kind,
                issue_title=issue_title,
                selector=selector,
            )
        return screenshot_url
    
    async def upload_to_cloudinary(
        self,
        screenshot_bytes: bytes,
        url: str,
        test_type: str,
        screenshot_type: str,
        screenshots_dir: Optional[str]
    ) -> Optional[str]:
        """Upload a screenshot to Cloudinary."""
        try:
            import cloudinary
            import cloudinary.uploader
            from django.conf import settings as django_settings
            from io import BytesIO
            import hashlib
            import time
            
            cloud_name = django_settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', '')
            api_key = django_settings.CLOUDINARY_STORAGE.get('API_KEY', '')
            api_secret = django_settings.CLOUDINARY_STORAGE.get('API_SECRET', '')
            
            if not cloudinary.config().cloud_name:
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                )
            
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = int(time.time())
            public_id = f"test_screenshots/{test_type}_{screenshot_type}_{url_hash}_{timestamp}"
            
            result = cloudinary.uploader.upload(
                BytesIO(screenshot_bytes),
                public_id=public_id,
                resource_type='image',
                format='png',
                overwrite=False,
                tags=['ai-application-tester', 'test_screenshot', test_type, screenshot_type],
                context={
                    'test_type': test_type,
                    'screenshot_type': screenshot_type,
                    'tested_url': url,
                },
            )
            
            return result.get('secure_url') or result.get('url')
        except ImportError:
            logger.warning("Cloudinary not installed, falling back to local storage")
            return self._save_locally(screenshot_bytes, url, test_type, screenshot_type, screenshots_dir)
        except Exception as e:
            logger.error(f"Error uploading screenshot to Cloudinary: {e}")
            return self._save_locally(screenshot_bytes, url, test_type, screenshot_type, screenshots_dir)
    
    def _save_locally(
        self,
        screenshot_bytes: bytes,
        url: str,
        test_type: str,
        screenshot_type: str,
        screenshots_dir: Optional[str]
    ) -> Optional[str]:
        """Save screenshot to local filesystem as fallback."""
        try:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root:
                os.makedirs(media_root, exist_ok=True)
                filename = f"screenshot_{test_type}_{screenshot_type}_{hash(url)}.png"
                filepath = os.path.join(media_root, filename)
                with open(filepath, 'wb') as f:
                    f.write(screenshot_bytes)
                return filepath
            return None
        except Exception as e:
            logger.error(f"Error saving screenshot locally: {e}")
            return None
