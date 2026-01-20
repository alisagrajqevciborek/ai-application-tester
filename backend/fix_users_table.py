"""
Script to check and create the users table if it's missing.
Run this if you're missing the users table in your database.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def check_users_table():
    """Check if users table exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        exists = cursor.fetchone()[0]
        return exists

def main():
    print("Checking for users table...")
    
    if check_users_table():
        print("[OK] Users table exists!")
        print("\nChecking migration status...")
        execute_from_command_line(['manage.py', 'showmigrations', 'users'])
    else:
        print("[ERROR] Users table is missing!")
        print("\nAttempting to create it...")
        print("Running migration: users 0001_initial")
        
        # Unfake and reapply the migration
        try:
            # First, mark the migration as not applied
            execute_from_command_line(['manage.py', 'migrate', 'users', '0001_initial', '--fake'])
            print("Marked migration as not applied.")
        except:
            pass
        
        # Now apply it for real
        try:
            execute_from_command_line(['manage.py', 'migrate', 'users', '0001_initial'])
            print("[OK] Users table created!")
        except Exception as e:
            print(f"[ERROR] Error creating table: {e}")
            print("\nTrying alternative approach...")
            print("Run this manually:")
            print("  python manage.py migrate users zero")
            print("  python manage.py migrate users")
            return
        
        # Apply subsequent migrations
        print("\nApplying remaining user migrations...")
        execute_from_command_line(['manage.py', 'migrate', 'users'])
        
        # Verify
        if check_users_table():
            print("\n[SUCCESS] Users table now exists!")
        else:
            print("\n[ERROR] Table still missing. Check database connection and permissions.")

if __name__ == '__main__':
    main()

