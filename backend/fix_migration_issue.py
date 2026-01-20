"""
Fix migration issue where applications table has null owner_id values.
This script will either delete orphaned applications or assign them to a default user.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def fix_orphaned_applications():
    """Fix applications with null owner_id."""
    with connection.cursor() as cursor:
        # Check if applications table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'applications'
            );
        """)
        if not cursor.fetchone()[0]:
            print("[INFO] Applications table doesn't exist yet. No fix needed.")
            return True
        
        # Check for null owners
        cursor.execute("SELECT COUNT(*) FROM applications WHERE owner_id IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count == 0:
            print("[INFO] No applications with null owners. All good!")
            return True
        
        print(f"[WARNING] Found {null_count} applications with null owner_id")
        print("[INFO] Deleting orphaned applications...")
        
        # Delete applications with null owners
        cursor.execute("DELETE FROM applications WHERE owner_id IS NULL")
        deleted = cursor.rowcount
        
        print(f"[SUCCESS] Deleted {deleted} orphaned applications")
        return True

if __name__ == '__main__':
    fix_orphaned_applications()

