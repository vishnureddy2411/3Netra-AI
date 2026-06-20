// ─────────────────────────────────────────────
// All API calls for 3Netra-AI frontend
// ─────────────────────────────────────────────

import { API } from './constants'
import type { IntakeData, Verdict, SelectedProject, DiscussionTurn } from './types'

// ── Generic helpers ───────────────────────────

export async function apiPost(endpoint: string, body: object) {
  const res = await fetch(`${API}/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(err.error || `${endpoint} failed`)
  }
  return res.json()
}

export async function apiGet(endpoint: string) {
  const res = await fetch(`${API}/${endpoint}`)
  if (!res.ok) throw new Error(`${endpoint} failed`)
  return res.json()
}

// ── Research ──────────────────────────────────

export async function runResearch(idea: string, intake: IntakeData) {
  const { PURPOSE_OPTIONS } = await import('./constants')
  const purposeOption = PURPOSE_OPTIONS.find(p => p.id === intake.purpose)
  return apiPost('research', {
    idea,
    target_role: intake.role || 'Software Engineer',
    purpose: intake.purpose,
    purpose_focus: purposeOption?.research_focus || '',
  })
}

// ── Council ───────────────────────────────────

export async function runCouncil(
  projectId: string,
  idea: string,
  intake: IntakeData,
) {
  const { PURPOSE_OPTIONS } = await import('./constants')
  const purposeOption = PURPOSE_OPTIONS.find(p => p.id === intake.purpose)
  return apiPost('council', {
    project_id: projectId,
    idea,
    target_role: intake.role || 'Software Engineer',
    purpose: intake.purpose,
    purpose_lens: purposeOption?.council_lens || '',
  })
}

// ── Deep Analysis ─────────────────────────────

export async function runDeepAnalysis(
  originalIdea: string,
  intake: IntakeData,
  verdict: Verdict,
  advisorOutputs: object[],
  researchSummary: string = '',
) {
  return apiPost('deep-analysis', {
    original_idea: originalIdea,
    role: intake.role || 'Software Engineer',
    purpose: intake.purpose,
    verdict,
    advisor_outputs: advisorOutputs,
    research_summary: researchSummary,
  })
}

// ── Reframe ───────────────────────────────────

export async function runReframe(
  originalIdea: string,
  verdict: Verdict,
  intake: IntakeData,
) {
  return apiPost('reframe', {
    original_idea: originalIdea,
    pivot_suggestion: verdict.pivot_suggestion || '',
    verdict: verdict.verdict,
    verdict_reasoning: verdict.verdict_reasoning,
    top_risks: verdict.top_risks,
    v1_scope: verdict.v1_scope,
    recommended_stack: verdict.recommended_stack || [],
    role: intake.role || 'Software Engineer',
    purpose: intake.purpose,
  })
}

// ── Ideas ─────────────────────────────────────

export async function runIdeas(
  context: string,
  intake: IntakeData,
  researchContext: string = '',
  verdictContext: string = '',
) {
  return apiPost('ideas', {
    role: intake.role,
    purpose: intake.purpose,
    context,
    research_context: researchContext,
    verdict_context: verdictContext,
  })
}

// ── Alternative ideas ─────────────────────────

export async function runAlternativeIdeas(
  originalIdea: string,
  originalCons: string[],
  intake: IntakeData,
) {
  return apiPost('ideas', {
    role: intake.role,
    purpose: intake.purpose,
    context: intake.role || '',
    original_idea: originalIdea,
    original_problems: originalCons.join('. '),
    show_why_better: true,
  })
}

// ── Discussion ────────────────────────────────

export async function runDiscussion(
  selectedProject: SelectedProject,
  userMessage: string,
  history: DiscussionTurn[],
  intake: IntakeData,
) {
  return apiPost('discuss', {
    selected_project: selectedProject,
    user_message: userMessage,
    discussion_history: history,
    role: intake.role || 'Software Engineer',
    purpose: intake.purpose,
  })
}

// ── Diagrams ──────────────────────────────────

export async function runDiagrams(projectId: string, idea: string) {
  return apiPost('diagrams', { project_id: projectId, idea })
}

// ── Project graph ─────────────────────────────

export async function runProjectGraph(projectId: string, idea: string) {
  return apiPost('project-graph', { project_id: projectId, idea })
}

// ── Session ───────────────────────────────────

export async function getLastSession() {
  return apiGet('session/last')
}

// ── Enriched idea builder ─────────────────────

export function buildEnrichedIdea(idea: string, intake: IntakeData): string {
  const purposeLabel = ['portfolio', 'startup', 'learning'].includes(intake.purpose)
    ? intake.purpose
    : intake.purpose
  return [
    idea,
    intake.purpose ? `Purpose: ${purposeLabel}` : '',
    intake.role ? `Target role: ${intake.role}` : '',
  ]
    .filter(Boolean)
    .join('. ')
}

// ── Build selected project object ─────────────
// Converts different project formats into SelectedProject

export function buildSelectedProject(
  projectId: string,
  title: string,
  description: string,
  techStack: string[],
  level: string,
  buildTime: string,
  skillsDemonstrated: string[],
  risks: string[],
  portfolioValue: string,
  fullIdea: string,
): import('./types').SelectedProject {
  return {
    title,
    description,
    techStack,
    level,
    buildTime,
    skillsDemonstrated,
    risks,
    portfolioValue,
    fullIdea,
    projectId,
  }
}