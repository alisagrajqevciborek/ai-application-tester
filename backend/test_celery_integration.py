"""
Test Celery integration and task execution.
Run this to verify Celery is properly configured and can execute tasks.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_celery_configuration():
    """Test Celery configuration."""
    print("=" * 60)
    print("CELERY CONFIGURATION TEST")
    print("=" * 60)
    
    try:
        from core.celery import app
        
        print(f"\n1. Celery App Configuration:")
        print(f"   App name: {app.main}")
        print(f"   Broker URL: {app.conf.broker_url}")
        print(f"   Result backend: {app.conf.result_backend}")
        print(f"   Task serializer: {app.conf.task_serializer}")
        print(f"   Result serializer: {app.conf.result_serializer}")
        print(f"   Timezone: {app.conf.timezone}")
        
        # Test broker connection
        print(f"\n2. Testing Broker Connection...")
        try:
            inspector = app.control.inspect()
            active_queues = inspector.active_queues()
            if active_queues:
                print(f"   [OK] Broker connection successful!")
                print(f"   Active workers: {len(active_queues)}")
                for worker, queues in active_queues.items():
                    print(f"     - {worker}: {len(queues)} queues")
            else:
                print(f"   [WARNING] Broker connection successful, but no workers running")
                print(f"   Start a worker with: celery -A core worker --loglevel=info")
        except Exception as e:
            print(f"   [ERROR] Broker connection failed: {e}")
            print(f"   Make sure Redis is running and accessible")
            return False
        
        # Test task discovery
        print(f"\n3. Testing Task Discovery...")
        registered_tasks = list(app.tasks.keys())
        print(f"   Registered tasks: {len(registered_tasks)}")
        
        # Look for our test execution task
        test_task_found = False
        for task_name in registered_tasks:
            if 'execute_test_run_task' in task_name:
                print(f"   [OK] Found: {task_name}")
                test_task_found = True
            elif 'debug_task' in task_name:
                print(f"   [OK] Found: {task_name}")
        
        if not test_task_found:
            print(f"   [WARNING] execute_test_run_task not found in registered tasks")
            print(f"   Available tasks:")
            for task in registered_tasks[:10]:  # Show first 10
                print(f"     - {task}")
        
        # Test sending a task (if worker is running)
        print(f"\n4. Testing Task Execution...")
        try:
            inspector = app.control.inspect()
            stats = inspector.stats()
            if stats:
                print(f"   [OK] Workers are running, testing task dispatch...")
                # Try to send the debug task
                result = app.send_task('core.celery.debug_task')
                print(f"   [OK] Task sent successfully! Task ID: {result.id}")
                print(f"   Check worker logs to see if task executed")
                return True
            else:
                print(f"   [WARNING] No workers running")
                print(f"   Start a worker with: celery -A core worker --loglevel=info")
                print(f"   Then tasks can be executed")
                return True  # Configuration is OK, just no worker
        except Exception as e:
            print(f"   [ERROR] Task dispatch failed: {e}")
            return False
        
    except ImportError as e:
        print(f"\n   [ERROR] Celery not properly configured!")
        print(f"   Error: {e}")
        print(f"   Make sure celery is installed: pip install celery")
        return False
    except Exception as e:
        print(f"\n   [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_worker_status():
    """Check if Celery workers are running."""
    print("\n" + "=" * 60)
    print("CELERY WORKER STATUS")
    print("=" * 60)
    
    try:
        from core.celery import app
        
        inspector = app.control.inspect()
        
        # Check active workers
        active = inspector.active()
        if active:
            print(f"\n[OK] Active Workers: {len(active)}")
            for worker, tasks in active.items():
                print(f"  - {worker}: {len(tasks)} active task(s)")
        else:
            print(f"\n[WARNING] No active workers found")
        
        # Check registered tasks
        registered = inspector.registered()
        if registered:
            print(f"\n[OK] Registered Tasks per Worker:")
            for worker, tasks in registered.items():
                print(f"  - {worker}: {len(tasks)} task(s)")
                # Show our task if found
                for task in tasks:
                    if 'execute_test_run_task' in task:
                        print(f"    [OK] {task}")
        else:
            print(f"\n[WARNING] No workers registered")
        
        # Check stats
        stats = inspector.stats()
        if stats:
            print(f"\n[OK] Worker Statistics:")
            for worker, stat in stats.items():
                print(f"  - {worker}:")
                print(f"    Pool: {stat.get('pool', {}).get('implementation', 'unknown')}")
                print(f"    Processes: {stat.get('pool', {}).get('processes', [])}")
        else:
            print(f"\n[WARNING] No worker statistics available")
            print(f"  Start a worker with: celery -A core worker --loglevel=info")
        
    except Exception as e:
        print(f"\n[ERROR] Error checking worker status: {e}")

if __name__ == '__main__':
    config_ok = test_celery_configuration()
    test_celery_worker_status()
    
    print("\n" + "=" * 60)
    if config_ok:
        print("[OK] SUMMARY: Celery configuration is OK")
        print("Next step: Start a Celery worker with:")
        print("  celery -A core worker --loglevel=info")
    else:
        print("[ERROR] SUMMARY: Celery configuration has issues")
        print("Check the errors above and fix them")
    print("=" * 60)
    
    sys.exit(0 if config_ok else 1)

