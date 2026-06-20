// ─────────────────────────────────────────────
// All TypeScript types for 3Netra-AI frontend
// ─────────────────────────────────────────────

export interface Verdict {
  verdict: 'BUILD' | 'PIVOT' | 'ABANDON'
  verdict_reasoning: string
  role_match_score: number
  v1_scope: string[]
  recommended_stack: string[]
  estimated_build_time: string
  career_value: string
  pivot_suggestion: string | null
  top_risks: string[]
}

export interface Diagram {
  diagram_type: string
  title: string
  mermaid_syntax: string
}

export interface GraphSummary {
  total_pages: number
  total_components: number
  total_api_routes: number
}

export interface ProjectIdea {
  title: string
  one_liner: string
  why_good: string
  why_better_than_original?: string
  skills_demonstrated: string[]
  tech_stack: string[]
  level: string
  build_time: string
  market_gap: string
}

export interface IntakeData {
  purpose: string
  role: string
  originalMessage: string
}

export interface GateData {
  project_type: string
  role: string
  idea: string
  purpose: string
}

// ── Selected project for confirmation gate ────

export interface SelectedProject {
  title: string
  description: string
  techStack: string[]
  level: string
  buildTime: string
  skillsDemonstrated: string[]
  risks: string[]
  portfolioValue: string
  fullIdea: string
  projectId: string
}

// ── Discussion turn ───────────────────────────

export interface DiscussionTurn {
  role: 'user' | 'mentor'
  content: string
}

// ── Deep Analysis types ───────────────────────

export interface TechStackItem {
  tech: string
  why_use: string
  skill_proved: string
  risk: string
  alternative: string
  mvp: boolean
}

export interface SkillItem {
  skill: string
  strength?: string
  importance?: string
}

export interface ScoreItem {
  option: string
  score: number
  reason: string
}

export interface ImprovedBlueprint {
  title: string
  description: string
  key_improvements: string[]
  mvp_features: string[]
  recommended_stack: string[]
  evaluation_approach: string
  estimated_weeks: number
  resume_bullet: string
}

export interface DeepAnalysisResult {
  idea_score: number
  hiring_manager_impression: string
  ml_engineering_aspects: string[]
  fullstack_aspects: string[]
  tech_stack_analysis: TechStackItem[]
  skills_demonstrated: SkillItem[]
  skills_missing: SkillItem[]
  improved_blueprint: ImprovedBlueprint
  scoring: ScoreItem[]
  final_recommendation: string
  final_reasoning: string
  elapsed_seconds: number
}

// ── All message types ─────────────────────────

export type MessageContent =
  | { type: 'user'; text: string }
  | { type: 'thinking'; stage: string; message: string }
  | { type: 'ideas'; ideas: ProjectIdea[]; purpose: string; role: string }
  | {
      type: 'alternatives'
      ideas: ProjectIdea[]
      purpose: string
      role: string
      originalIdea: string
    }
  | {
      type: 'comparison'
      projectId: string
      originalIdea: string
      pivotIdea: string
      originalPros: string[]
      originalCons: string[]
      suggestedPros: string[]
      suggestedCons: string[]
      skillsDemonstrated: string[]
      skillsLacking: string[]
      howSuggestionImproves: string[]
      recommendedStack: string[]
      summary: string
      verdict: Verdict
      deepAnalysis: DeepAnalysisResult | null
    }
  | {
      type: 'build_approved'
      projectId: string
      idea: string
      pros: string[]
      minorCons: string[]
      verdict: Verdict
      deepAnalysis: DeepAnalysisResult | null
    }
  | {
      type: 'confirmation_gate'
      selectedProject: SelectedProject
    }
  | {
      type: 'discussion'
      selectedProject: SelectedProject
      history: DiscussionTurn[]
    }
  | { type: 'chosen'; choice: string }
  | { type: 'diagrams'; diagrams: Diagram[] }
  | { type: 'graph'; summary: GraphSummary; elapsed: number }
  | { type: 'complete'; projectId: string }
  | { type: 'error'; message: string }

export interface Message {
  id: string
  content: MessageContent
}