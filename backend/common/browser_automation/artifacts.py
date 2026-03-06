"""
Artifact (trace/video) management.
"""
import os
import shutil
import tempfile
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ArtifactManager:
    """Manages trace/video artifacts."""
    
    def __init__(self):
        self._artifact_meta: List[Dict[str, Any]] = []
    
    def reset(self):
        """Reset per-run state."""
        self._artifact_meta = []
    
    def get_metadata(self) -> List[Dict[str, Any]]:
        """Get collected artifact metadata."""
        return self._artifact_meta
    
    def _record_artifact_meta(
        self,
        *,
        url: str,
        kind: str,
        note: Optional[str] = None,
    ) -> None:
        # Avoid duplicate artifacts in the same run payload.
        for artifact in self._artifact_meta:
            if artifact.get('url') == url and artifact.get('kind') == kind and artifact.get('note') == note:
                return
        self._artifact_meta.append({
            'url': url,
            'kind': kind,
            'note': note,
            'ai_summary': None,
            'ai_tags': [],
            'ai_suggestions': [],
        })
    
    async def upload_artifact_file(
        self,
        file_path: str,
        tested_url: str,
        test_type: str,
        artifact_kind: str,
    ) -> Optional[str]:
        """Upload a non-image artifact (trace/video) to Cloudinary as raw."""
        try:
            import cloudinary
            import cloudinary.uploader
            from django.conf import settings as django_settings
            import hashlib
            import time
            
            cloud_name = django_settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', '')
            api_key = django_settings.CLOUDINARY_STORAGE.get('API_KEY', '')
            api_secret = django_settings.CLOUDINARY_STORAGE.get('API_SECRET', '')
            
            if not cloud_name or not api_key or not api_secret:
                return None
            
            if not cloudinary.config().cloud_name:
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                )
            
            url_hash = hashlib.md5(tested_url.encode()).hexdigest()[:8]
            timestamp = int(time.time())
            public_id = f"test_artifacts/{test_type}_{artifact_kind}_{url_hash}_{timestamp}"
            
            result = cloudinary.uploader.upload(
                file_path,
                public_id=public_id,
                resource_type='raw',
                overwrite=False,
                tags=['ai-application-tester', 'test_artifact', test_type, artifact_kind],
                context={
                    'test_type': test_type,
                    'artifact_kind': artifact_kind,
                    'tested_url': tested_url,
                },
            )
            return result.get('secure_url') or result.get('url')
        except Exception:
            return None
    
    async def finalize_debug_artifacts(
        self,
        context,
        page,
        url: str,
        test_type: str,
        *,
        save_trace: bool,
        save_video: bool,
        video_path: Optional[str] = None,
    ) -> None:
        """Save/upload trace/video only when something is wrong."""
        # Trace
        if save_trace:
            trace_dir = tempfile.mkdtemp(prefix='pw-trace-')
            trace_path = os.path.join(trace_dir, 'trace.zip')
            try:
                await context.tracing.stop(path=trace_path)
                trace_url = await self.upload_artifact_file(trace_path, url, test_type, 'playwright_trace')
                if trace_url:
                    self._record_artifact_meta(url=trace_url, kind='playwright_trace')
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error saving trace: {e}")
            finally:
                shutil.rmtree(trace_dir, ignore_errors=True)
        else:
            try:
                await context.tracing.stop()
            except Exception:
                pass
        
        # Video - use provided path or try to get from page
        if save_video:
            try:
                video_file_path = video_path
                if not video_file_path and page.video:
                    video_file_path = await page.video.path()
                
                if video_file_path and os.path.exists(video_file_path):
                    video_url = await self.upload_artifact_file(video_file_path, url, test_type, 'playwright_video')
                    if video_url:
                        self._record_artifact_meta(url=video_url, kind='playwright_video')
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error saving video: {e}")
