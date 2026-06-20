-- ─────────────────────────────────────────────
-- 3Netra-AI Schema V2
-- User project storage and progress tracking
-- Run this in Supabase SQL Editor
-- ─────────────────────────────────────────────

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────
-- PROJECTS TABLE
-- Main project storage — one row per project
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_role VARCHAR(100),
    purpose VARCHAR(50) DEFAULT 'portfolio',
    difficulty_level VARCHAR(50),
    estimated_duration VARCHAR(100),

    overall_status VARCHAR(50) DEFAULT 'pending',
    current_stage VARCHAR(100) DEFAULT 'project_selected',
    progress_percentage INT DEFAULT 0,

    tech_stack JSONB DEFAULT '[]',
    risks JSONB DEFAULT '[]',
    portfolio_value TEXT,
    full_idea TEXT,

    -- AI generated data
    deep_analysis JSONB,
    verdict JSONB,
    advisor_outputs JSONB DEFAULT '[]',

    -- Internal tracking
    internal_project_id VARCHAR(255),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- PROJECT STAGES TABLE
-- Tracks each stage of project completion
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    stage_name VARCHAR(100) NOT NULL,
    stage_status VARCHAR(50) DEFAULT 'pending',

    input_data JSONB,
    output_data JSONB,

    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- PROJECT DISCUSSIONS TABLE
-- Saves all doubt/clarification conversations
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_discussions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    user_question TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    discussion_status VARCHAR(50) DEFAULT 'open',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- PROJECT DIAGRAMS TABLE
-- Saves generated architecture diagrams
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_diagrams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    diagram_type VARCHAR(100) NOT NULL,
    diagram_title VARCHAR(255),
    diagram_content TEXT,
    diagram_format VARCHAR(50) DEFAULT 'mermaid',
    file_url TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- PROJECT ARTIFACTS TABLE
-- Saves generated outputs: README, resume bullets, etc.
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    artifact_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    content TEXT,
    file_url TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- PROJECT VERSIONS TABLE
-- Tracks major project changes over time
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    version_number INT NOT NULL DEFAULT 1,
    version_title VARCHAR(255),
    project_snapshot JSONB NOT NULL,
    change_summary TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- CHAT HISTORY TABLE
-- Saves conversation history per project (ChatGPT style)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    role VARCHAR(20) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- INDEXES for performance
-- ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_user_projects_user_id
    ON user_projects(user_id);

CREATE INDEX IF NOT EXISTS idx_user_projects_status
    ON user_projects(overall_status);

CREATE INDEX IF NOT EXISTS idx_user_projects_updated
    ON user_projects(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_project_stages_project_id
    ON project_stages(project_id);

CREATE INDEX IF NOT EXISTS idx_project_discussions_project_id
    ON project_discussions(project_id);

CREATE INDEX IF NOT EXISTS idx_project_diagrams_project_id
    ON project_diagrams(project_id);

CREATE INDEX IF NOT EXISTS idx_project_artifacts_project_id
    ON project_artifacts(project_id);

CREATE INDEX IF NOT EXISTS idx_chat_history_project_id
    ON project_chat_history(project_id);

CREATE INDEX IF NOT EXISTS idx_chat_history_user_id
    ON project_chat_history(user_id);

-- ─────────────────────────────────────────────
-- ROW LEVEL SECURITY
-- Users can only access their own data
-- ─────────────────────────────────────────────

ALTER TABLE user_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_discussions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_diagrams ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_chat_history ENABLE ROW LEVEL SECURITY;

-- user_projects policies
CREATE POLICY "Users view own projects"
    ON user_projects FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users create own projects"
    ON user_projects FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own projects"
    ON user_projects FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users delete own projects"
    ON user_projects FOR DELETE
    USING (auth.uid() = user_id);

-- project_stages policies
CREATE POLICY "Users view own stages"
    ON project_stages FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_stages.project_id
        AND user_projects.user_id = auth.uid()
    ));

CREATE POLICY "Users create own stages"
    ON project_stages FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_stages.project_id
        AND user_projects.user_id = auth.uid()
    ));

CREATE POLICY "Users update own stages"
    ON project_stages FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_stages.project_id
        AND user_projects.user_id = auth.uid()
    ));

-- project_discussions policies
CREATE POLICY "Users view own discussions"
    ON project_discussions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_discussions.project_id
        AND user_projects.user_id = auth.uid()
    ));

CREATE POLICY "Users create own discussions"
    ON project_discussions FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_discussions.project_id
        AND user_projects.user_id = auth.uid()
    ));

-- project_diagrams policies
CREATE POLICY "Users view own diagrams"
    ON project_diagrams FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_diagrams.project_id
        AND user_projects.user_id = auth.uid()
    ));

CREATE POLICY "Users create own diagrams"
    ON project_diagrams FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_diagrams.project_id
        AND user_projects.user_id = auth.uid()
    ));

-- project_artifacts policies
CREATE POLICY "Users view own artifacts"
    ON project_artifacts FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_artifacts.project_id
        AND user_projects.user_id = auth.uid()
    ));

CREATE POLICY "Users create own artifacts"
    ON project_artifacts FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_artifacts.project_id
        AND user_projects.user_id = auth.uid()
    ));

-- project_versions policies
CREATE POLICY "Users view own versions"
    ON project_versions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_versions.project_id
        AND user_projects.user_id = auth.uid()
    ));

CREATE POLICY "Users create own versions"
    ON project_versions FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM user_projects
        WHERE user_projects.id = project_versions.project_id
        AND user_projects.user_id = auth.uid()
    ));

-- project_chat_history policies
CREATE POLICY "Users view own chat history"
    ON project_chat_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users create own chat history"
    ON project_chat_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────
-- AUTO UPDATE updated_at TRIGGER
-- ─────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_projects_updated_at
    BEFORE UPDATE ON user_projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_project_diagrams_updated_at
    BEFORE UPDATE ON project_diagrams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_project_artifacts_updated_at
    BEFORE UPDATE ON project_artifacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();