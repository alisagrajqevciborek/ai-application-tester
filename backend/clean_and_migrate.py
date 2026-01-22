"""
Clean database and reapply migrations properly.
This will delete orphaned data and recreate tables correctly.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def clean_and_migrate():
    """Clean orphaned data and prepare for migrations."""
    with connection.cursor() as cursor:
        print("[INFO] Checking database state...")
        
        # Check if applications table exists and has data
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'applications'
            );
        """)
        apps_exists = cursor.fetchone()[0]
        
        if apps_exists:
            # Check if owner column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'applications'
                    AND column_name = 'owner_id'
                );
            """)
            owner_col_exists = cursor.fetchone()[0]
            
            if not owner_col_exists:
                # Table exists but owner column doesn't - delete orphaned data
                print("[WARNING] Applications table exists without owner column")
                print("[INFO] Deleting all applications (they will be recreated)...")
                cursor.execute("DELETE FROM applications")
                print(f"[SUCCESS] Deleted {cursor.rowcount} applications")
        
        # Check for test_runs and screenshots
        for table in ['test_runs', 'screenshots']:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            """)
            if cursor.fetchone()[0]:
                print(f"[INFO] Deleting data from {table}...")
                cursor.execute(f"DELETE FROM {table}")
                print(f"[SUCCESS] Deleted {cursor.rowcount} rows from {table}")
        
        print("\n[INFO] Database cleaned. Now run migrations:")
        print("  python manage.py migrate")
        return True

if __name__ == '__main__':
    clean_and_migrate()




