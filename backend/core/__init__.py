"""
This will make sure the app is always imported when
Django starts so that shared_task will use this app.
"""
try:
    from .celery import app as celery_app  # type: ignore
    __all__ = ('celery_app',)
except ImportError:
    # Celery is optional - Django can run without it
    celery_app = None  # type: ignore
    __all__ = ()
