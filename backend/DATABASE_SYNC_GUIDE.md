# Database Sync Guide

## Problem: Same Database, Different Tables

If you and your friend share the same database but have different tables, you need to sync your migrations.

### Step 1: Check Current Migration Status

```bash
cd backend
python manage.py showmigrations
```

This shows which migrations have been applied (marked with [X]) and which haven't.

### Step 2: Check What Tables Exist in Database

Connect to your PostgreSQL database and check:

```sql
\dt
```

This lists all tables. Compare with your friend's tables.

### Step 3: Create Missing Migrations

If you have model changes that aren't in migrations:

```bash
python manage.py makemigrations
```

This creates new migration files for any model changes.

### Step 4: Apply Migrations

**Option A: Apply All Migrations (Recommended)**

```bash
python manage.py migrate
```

This applies all pending migrations.

**Option B: Fake Migrations (If Tables Already Exist)**

If your friend already created the tables but migrations aren't recorded:

```bash
# First, check which migrations need to be faked
python manage.py showmigrations

# Fake specific migrations (use with caution!)
python manage.py migrate --fake apps.users 0002_user_code_expires_at_user_email_verified_and_more
python manage.py migrate --fake apps.applications 0003_testrun
```

**⚠️ WARNING:** Only use `--fake` if the tables already exist in the database!

### Step 5: Check for Conflicts

If you get migration conflicts:

1. **Check migration files**: Compare your migration files with your friend's
2. **Merge migrations**: If needed, create a new migration that reconciles differences
3. **Reset migrations** (last resort): Only if you're both in development

### Step 6: Verify Tables Match

After migrations, verify:

```sql
-- In PostgreSQL
\dt
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

You should see:
- `users`
- `applications`
- `test_runs`
- `screenshots`
- Django auth tables (`auth_*`, `django_*`)

### Common Issues

1. **"No migrations to apply" but tables missing**:
   - Tables might be in a different schema
   - Check database connection settings
   - Verify you're connected to the correct database

2. **Migration conflicts**:
   - Both of you created migrations independently
   - One person should delete their migrations and run `makemigrations` again
   - Or manually merge migration files

3. **"Table already exists" error**:
   - Use `--fake` flag to mark migration as applied without running SQL
   - Or drop and recreate tables (development only!)

### Reset Everything (Development Only!)

If you're both in development and want to start fresh:

```bash
# ⚠️ WARNING: This deletes all data!
python manage.py flush
python manage.py migrate
```

### Best Practice

1. **One person creates migrations**: Designate one person to run `makemigrations`
2. **Everyone applies migrations**: Everyone runs `migrate` to sync
3. **Commit migration files**: Always commit migration files to git
4. **Don't edit applied migrations**: Once applied, don't modify migration files

