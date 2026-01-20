# Fix Missing Users Table

## Problem
You're missing the `users` table in your database compared to your friend, even though migrations show as applied.

## Solution

### Option 1: Reset and Reapply Migrations (Recommended)

This will recreate the users table from scratch:

```bash
cd backend

# Step 1: Unapply users migrations (this won't delete data if table doesn't exist)
python manage.py migrate users zero

# Step 2: Reapply all users migrations
python manage.py migrate users
```

### Option 2: Use the Fix Script

Run the automated fix script:

```bash
cd backend
python create_users_table.py
```

This will:
1. Check if the table exists
2. Create it if missing
3. Run migrations to add all fields

### Option 3: Manual SQL (If above don't work)

If the above methods don't work, you can manually create the table:

```bash
cd backend
python create_users_table.py
```

Or connect to PostgreSQL directly and run:

```sql
-- Check if table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'users'
);

-- If it doesn't exist, the create_users_table.py script will create it
```

### Option 4: Fake and Reapply (If table exists but migration says it doesn't)

If the table actually exists but Django thinks it doesn't:

```bash
# Mark migrations as applied without running SQL
python manage.py migrate users --fake

# Then apply any new migrations
python manage.py migrate users
```

## Verify

After running any of the above, verify the table exists:

```bash
python manage.py dbshell
```

Then in the PostgreSQL shell:
```sql
\dt users
SELECT * FROM users LIMIT 1;
```

Or use the check script:
```bash
python fix_users_table.py
```

## Common Issues

1. **"Table already exists" error**: The table might exist in a different schema. Check with:
   ```sql
   SELECT table_schema, table_name 
   FROM information_schema.tables 
   WHERE table_name = 'users';
   ```

2. **"Permission denied"**: Make sure your database user has CREATE TABLE permissions.

3. **"Migration conflicts"**: If you get migration conflicts, you may need to:
   ```bash
   python manage.py migrate users zero --fake
   python manage.py migrate users
   ```

## After Fixing

Once the table is created, you should be able to:
- Register new users
- Login with existing users
- See users in Django admin

