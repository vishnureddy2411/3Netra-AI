-- ============================================================
-- 3Netra-AI — Row Level Security Policies
-- Run AFTER schema.sql in Supabase SQL Editor
-- 
-- RLS = users can only see their own data
-- Without RLS: any user could read any project
-- With RLS: automatic per-user isolation, no auth middleware needed
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE profiles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects        ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagrams        ENABLE ROW LEVEL SECURITY;
ALTER TABLE build_modules   ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE previews        ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_events     ENABLE ROW LEVEL SECURITY;

-- ── profiles ──────────────────────────────────────────────────
CREATE POLICY "Users see own profile"
    ON profiles FOR ALL
    USING (auth.uid() = id);

-- ── projects ──────────────────────────────────────────────────
CREATE POLICY "Users see own projects"
    ON projects FOR ALL
    USING (auth.uid() = user_id);

-- ── All other tables: access via project ownership ────────────
CREATE POLICY "Via project ownership - diagrams"
    ON diagrams FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - modules"
    ON build_modules FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - files"
    ON generated_files FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - previews"
    ON previews FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - decisions"
    ON decisions FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - embeddings"
    ON decision_embeddings FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - career"
    ON career_artifacts FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

CREATE POLICY "Via project ownership - cost"
    ON cost_events FOR ALL
    USING (project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
    ));

-- ── Verify RLS works ──────────────────────────────────────────
-- Test as anon (should return 0 rows):
-- SELECT * FROM projects;  → must return empty, not an error
-- Test as authenticated user with their own project:
-- SELECT * FROM projects WHERE id = 'their-project-id';  → must return 1 row
