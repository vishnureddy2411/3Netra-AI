# Migration Architect

You are writing code that modifies an existing database. Every change must be backwards-compatible and reversible. A migration that breaks the running application is worse than no migration at all.

---

## The Core Rule

Never remove, rename, or change the type of a column in the same migration that adds a replacement.
Always: add first → deploy → migrate data → remove old → deploy again.

---

## Safe Operations (do these)

Adding a new nullable column:
```sql
ALTER TABLE users ADD COLUMN phone_number TEXT;
-- Safe: existing rows get NULL, app continues working
```

Adding a new table:
```sql
CREATE TABLE project_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Safe: no existing data affected
```

Adding an index (use CONCURRENTLY in production):
```sql
CREATE INDEX CONCURRENTLY idx_files_project_id ON files(project_id);
-- CONCURRENTLY prevents table lock — never omit this in production
```

---

## Dangerous Operations — How to Do Them Safely

### Renaming a column

WRONG (breaks running app immediately):
```sql
ALTER TABLE users RENAME COLUMN old_name TO new_name;
```

CORRECT (3-step process):
```sql
-- Step 1: Add new column
ALTER TABLE users ADD COLUMN new_name TEXT;

-- Step 2: Backfill data
UPDATE users SET new_name = old_name WHERE old_name IS NOT NULL;

-- Step 3: (After new code is deployed and old_name is no longer referenced)
ALTER TABLE users DROP COLUMN old_name;
```

### Changing column type

WRONG:
```sql
ALTER TABLE files ALTER COLUMN size TYPE BIGINT;
-- May fail on existing data, locks table
```

CORRECT:
```sql
ALTER TABLE files ADD COLUMN size_bytes BIGINT;
UPDATE files SET size_bytes = size::BIGINT;
-- Deploy new code using size_bytes
-- Then drop size column in next migration
```

---

## Migration File Format

Every migration is a numbered .sql file:

```
database/migrations/
  0001_initial_schema.sql
  0002_add_pgvector.sql
  0003_add_files_table.sql
  0004_add_skills_index.sql
```

Every file must include both up and down:
```sql
-- Migration: 0004_add_skills_index
-- Up
CREATE INDEX CONCURRENTLY idx_files_project_id ON files(project_id);

-- Down
DROP INDEX IF EXISTS idx_files_project_id;
```

---

## Before Running Any Migration

1. Take a Supabase point-in-time backup (Dashboard → Database → Backups)
2. Test the migration on a copy of the schema first
3. Verify rollback (Down migration) works before applying Up migration
4. Check if any existing queries will break with the new schema

---

## Supabase-Specific Rules

- RLS policies must be re-applied after table restructuring
- pgvector dimension changes require dropping and recreating the column (not ALTER)
- Foreign key constraints: add with NOT VALID first, then VALIDATE separately:

```sql
ALTER TABLE files ADD CONSTRAINT fk_project
    FOREIGN KEY (project_id) REFERENCES projects(id)
    NOT VALID;  -- doesn't scan existing rows

ALTER TABLE files VALIDATE CONSTRAINT fk_project;
-- Run this separately, during low-traffic period
```
