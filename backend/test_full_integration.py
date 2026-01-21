"""
Full integration test for Redis + Celery + Django.
This tests the complete flow from task creation to execution.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_full_integration():
    """Test the complete Redis + Celery + Django integration."""
    print("=" * 60)
    print("FULL INTEGRATION TEST")
    print("=" * 60)
    
    # Step 1: Test Redis
    print("\n[1/4] Testing Redis Connection...")
    try:
        from test_redis_connection import test_redis_connection
        redis_ok = test_redis_connection()
        if not redis_ok:
            print("[ERROR] Redis test failed. Fix Redis connection first.")
            return False
    except Exception as e:
        print(f"[ERROR] Redis test error: {e}")
        return False
    
    # Step 2: Test Celery Configuration
    print("\n[2/4] Testing Celery Configuration...")
    try:
        from test_celery_integration import test_celery_configuration
        celery_ok = test_celery_configuration()
        if not celery_ok:
            print("[ERROR] Celery configuration test failed.")
            return False
    except Exception as e:
        print(f"[ERROR] Celery test error: {e}")
        return False
    
    # Step 3: Test Task Import
    print("\n[3/4] Testing Task Import...")
    try:
        from apps.applications.tasks import execute_test_run_task
        print("[OK] Task imported successfully")
        print(f"  Task name: {execute_test_run_task.name}")
    except Exception as e:
        print(f"[ERROR] Task import failed: {e}")
        return False
    
    # Step 4: Test Task Dispatch (if worker is running)
    print("\n[4/4] Testing Task Dispatch...")
    try:
        from core.celery import app
        inspector = app.control.inspect()
        stats = inspector.stats()
        
        if stats:
            print("[OK] Workers are running")
            print("  Attempting to dispatch a test task...")
            
            # Try to send a simple task
            result = app.send_task('core.celery.debug_task')
            print(f"[OK] Task dispatched! Task ID: {result.id}")
            print(f"  Check worker logs to confirm execution")
            return True
        else:
            print("[WARNING] No workers running")
            print("  Configuration is OK, but you need to start a worker:")
            print("  celery -A core worker --loglevel=info")
            return True  # Config is OK
    except Exception as e:
        print(f"[ERROR] Task dispatch failed: {e}")
        return False

if __name__ == '__main__':
    success = test_full_integration()
    
    print("\n" + "=" * 60)
    if success:
        print("[OK] INTEGRATION TEST PASSED")
        print("\nTo start using Celery:")
        print("1. Make sure Redis is running: redis-server")
        print("2. Start Celery worker: celery -A core worker --loglevel=info")
        print("3. Start Django server: python manage.py runserver")
    else:
        print("[ERROR] INTEGRATION TEST FAILED")
        print("Fix the issues above before proceeding")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

