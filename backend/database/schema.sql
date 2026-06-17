-- ============================================================
-- 3Netra-AI — Supabase Database Schema
-- Run this in: supabase.com → Project → SQL Editor → New Query
-- Run in this exact order — tables reference each other
-- ============================================================

-- Enable pgvector extension (run this first)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users (linked to Supabase Auth) ───────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Projects ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name            TEXT,
    idea            TEXT NOT NULL,
    target_role     TEXT,
    status          TEXT DEFAULT 'research'
                    CHECK(status IN ('research','council','diagrams','quiz','building','career','complete')),
    verdict         JSONB,                      -- ChairmanVerdict JSON
    project_graph   JSONB,                      -- pre-wired route map
    role_match_score INTEGER,
    tech_stack      TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Diagrams ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagrams (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    diagram_type    TEXT NOT NULL,              -- "system_architecture", "erd", etc.
    mermaid_syntax  TEXT NOT NULL,
    approved        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Build Modules ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS build_modules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    module_name     TEXT NOT NULL,
    module_type     TEXT,                       -- "auth", "rag_pipeline", etc.
    status          TEXT DEFAULT 'pending'
                    CHECK(status IN ('pending','in_progress','approved','fix_requested','rebuild')),
    files_written   TEXT[],
    exports         JSONB,
    api_endpoints   JSONB,
    fix_request     TEXT,
    build_order     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Generated Files ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generated_files (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    module_id       UUID REFERENCES build_modules(id) ON DELETE CASCADE,
    file_path       TEXT NOT NULL,
    content         TEXT NOT NULL,
    language        TEXT,                       -- "typescript", "python", etc.
    exports         TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Preview Screenshots ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS previews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    module_id       UUID REFERENCES build_modules(id) ON DELETE CASCADE,
    screenshot_url  TEXT,                       -- Supabase Storage URL
    annotations     JSONB,                      -- numbered callouts from Haiku
    playwright_log  JSONB,                      -- interactions recorded
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Decision Memory (+ embeddings for semantic recall) ────────
CREATE TABLE IF NOT EXISTS decisions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    session_id      TEXT,
    what            TEXT NOT NULL,
    why             TEXT NOT NULL,
    node_type       TEXT NOT NULL
                    CHECK(node_type IN (
                        'chairman_verdict','adr','quiz_gap',
                        'correction','v2_feature','architecture_decision'
                    )),
    gap_concept     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Decision Embeddings (for semantic recall) ─────────────────
CREATE TABLE IF NOT EXISTS decision_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id     UUID REFERENCES decisions(id) ON DELETE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    embedding       vector(384)                 -- all-MiniLM-L6-v2, 384 dim, NEVER change
);

-- ── Career Artifacts ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS career_artifacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    artifact_type   TEXT CHECK(artifact_type IN (
                        'readme','linkedin_post','resume_bullets',
                        'verdict_pdf','onboarding_md','pr_description'
                    )),
    content         TEXT,
    file_url        TEXT,                       -- Supabase Storage URL for PDFs/docs
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Session Cost Tracking ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    session_id      TEXT,
    agent_name      TEXT,
    model           TEXT,
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    cached          BOOLEAN DEFAULT FALSE,
    cost_usd        NUMERIC(10, 6),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_projects_user        ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_diagrams_project     ON diagrams(project_id);
CREATE INDEX IF NOT EXISTS idx_modules_project      ON build_modules(project_id);
CREATE INDEX IF NOT EXISTS idx_modules_status       ON build_modules(status);
CREATE INDEX IF NOT EXISTS idx_files_project        ON generated_files(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_project    ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_type       ON decisions(node_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_project   ON decision_embeddings(project_id);
CREATE INDEX IF NOT EXISTS idx_cost_project         ON cost_events(project_id);

-- ── pgvector IVFFlat index for fast similarity search ─────────
-- Run AFTER inserting first 100+ rows for best performance
-- CREATE INDEX ON decision_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- ── Supabase RPC: semantic recall function ────────────────────
CREATE OR REPLACE FUNCTION recall_decisions(
    query_embedding vector(384),
    project_id_filter UUID,
    match_count INT DEFAULT 3,
    match_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    id UUID,
    what TEXT,
    why TEXT,
    node_type TEXT,
    gap_concept TEXT,
    created_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.what,
        d.why,
        d.node_type,
        d.gap_concept,
        d.created_at,
        1 - (de.embedding <=> query_embedding) AS similarity
    FROM decisions d
    JOIN decision_embeddings de ON d.id = de.decision_id
    WHERE
        d.project_id = project_id_filter
        AND 1 - (de.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- ── Storage bucket for screenshots and PDFs ───────────────────
-- Run this separately in Supabase Storage dashboard:
-- Create bucket: "3netra-assets" (public: false)
-- Or via SQL:
INSERT INTO storage.buckets (id, name, public)
VALUES ('3netra-assets', '3netra-assets', false)
ON CONFLICT DO NOTHING;
