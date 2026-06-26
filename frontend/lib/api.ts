// ─────────────────────────────────────────────
// All API calls for 3Netra-AI frontend
// ─────────────────────────────────────────────

import { API } from './constants'
import { supabase } from './supabase'
import type { IntakeData, Verdict, SelectedProject, DiscussionTurn } from './types'

// ── Auth helper ───────────────────────────────
// Grabs the current Supabase session token.
// Always call this before any authenticated request.

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession()
  const base: Record<string, string> = { 'Content-Type': 'application/json' }
  if (session?.access_token) {
    base['Authorization'] = `Bearer ${session.access_token}`
  }
  return base
}

// ── Generic helpers ───────────────────────────

export async function apiPost(endpoint: string, body: object) {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API}/${endpoint}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(err.error || `${endpoint} failed`)
  }
  return res.json()
}

export async function apiGet(endpoint: string) {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API}/${endpoint}`, { headers })
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
  return apiPost('council', {
    project_id: projectId,
    idea,
    intake: {
      role:             intake.role || 'Software Engineer',
      purpose:          intake.purpose || 'portfolio',
      original_message: intake.originalMessage || '',
    },
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

export async function runDiagrams(mcpProjectId: string, dbProjectId: string, idea: string) {
  return apiPost('diagrams', { project_id: mcpProjectId, db_project_id: dbProjectId, idea })
}

// ── Project graph ─────────────────────────────

export async function runProjectGraph(mcpProjectId: string, dbProjectId: string, idea: string) {
  return apiPost('project-graph', { project_id: mcpProjectId, db_project_id: dbProjectId, idea })
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

// ── Professional Council ──────────────────────

export async function runProCouncil(
  projectId: string,
  task: string,
  role: string,
) {
  return apiPost('pro-council', {
    project_id: projectId,
    task,
    role,
  })
}

// ── Workflow ──────────────────────────────────

export async function startWorkflow(
  projectId: string,
  idea: string,
  role: string,
  purpose: string,
  approvedVerdict?: object,
) {
  return apiPost('workflow/start', {
    project_id:       projectId,
    idea,
    role,
    purpose,
    approved_verdict: approvedVerdict,
  })
}

export async function executeWorkflowStage(
  projectId:        string,
  stage:            string,
  idea:             string,
  role:             string,
  purpose:          string,
  approvedDecisions: object = {},
) {
  return apiPost('workflow/stage', {
    project_id:         projectId,
    stage,
    idea,
    role,
    purpose,
    approved_decisions: approvedDecisions,
  })
}

export async function approveWorkflowStage(
  projectId:    string,
  currentStage: string,
  stageOutput:  object = {},
) {
  return apiPost('workflow/approve', {
    project_id:    projectId,
    current_stage: currentStage,
    stage_output:  stageOutput,
  })
}

export async function rejectWorkflowStage(
  projectId:        string,
  currentStage:     string,
  idea:             string,
  role:             string,
  purpose:          string,
  feedback:         string,
  approvedDecisions: object = {},
) {
  return apiPost('workflow/reject', {
    project_id:         projectId,
    current_stage:      currentStage,
    idea,
    role,
    purpose,
    feedback,
    approved_decisions: approvedDecisions,
  })
}

export async function getWorkflowStatus(projectId: string) {
  return apiGet(`workflow/status/${projectId}`)
}

// ── Quiz ──────────────────────────────────────

export async function startQuiz(
  projectId:    string,
  idea:         string,
  role:         string,
  projectGraph: object,
  diagrams:     object[],
) {
  return apiPost('quiz/start', { project_id: projectId, idea, role, project_graph: projectGraph, diagrams })
}

export async function submitQuizAnswer(
  projectId:    string,
  idea:         string,
  role:         string,
  question:     object,
  userAnswer:   string,
  projectGraph: object,
) {
  return apiPost('quiz/answer', { project_id: projectId, idea, role, question, user_answer: userAnswer, project_graph: projectGraph })
}

export async function getNextQuizRound(
  projectId:      string,
  idea:           string,
  role:           string,
  projectGraph:   object,
  diagrams:       object[],
  roundNumber:    number,
  askedQuestions: string[],
) {
  return apiPost('quiz/next', { project_id: projectId, idea, role, project_graph: projectGraph, diagrams, round_number: roundNumber, asked_questions: askedQuestions })
}

export async function summarizeQuizRound(
  projectId:   string,
  questions:   object[],
  evaluations: object[],
  roundNumber: number,
  idea:        string,
  role:        string,
) {
  return apiPost('quiz/summarize', { project_id: projectId, questions, evaluations, round_number: roundNumber, idea, role })
}

export async function completeQuiz(
  projectId: string,
  allGaps:   string[],
  allRounds: object[],
  idea:      string,
  role:      string,
) {
  return apiPost('quiz/complete', { project_id: projectId, all_gaps: allGaps, all_rounds: allRounds, idea, role })
}

// ── Conversational Chat Agent ─────────────────────────────────────────────────

export async function sendChatMessage(
  projectId: string,
  message:   string,
  history:   { role: string; content: string }[],
  intake:    IntakeData,
  userType:  string,
  stage?:    string,
  sessionId?: string,
) {
  return apiPost('chat', {
    project_id: projectId,
    message,
    history,
    role:       intake.role || 'Software Engineer',
    purpose:    intake.purpose || 'portfolio',
    user_type:  userType,
    stage:      stage || '',
    session_id: sessionId || '',
  })
}
// ── Project Briefing ──────────────────────────────────────────────────────────

export async function getProjectBriefing(
  projectId: string,
  role:       string,
  purpose:    string,
  userType:   string,
) {
  return apiPost('chat/briefing', {
    project_id: projectId,
    role,
    purpose,
    user_type:  userType,
  })
}

// ── Stage Memory ──────────────────────────────────────────────────────────────

export async function getStageMemory(
  projectId: string,
  stageName: string,
) {
  return apiGet(`projects/${projectId}/stages/${stageName}/memory`)
}

export async function saveStageMemory(
  projectId: string,
  stageName: string,
  memory: {
    approved_decisions: string[]
    rejected_ideas:     string[]
    pending_questions:  string[]
    important_context:  string
    tech_stack:         string[]
    summary:            string
  },
) {
  return apiPost(`projects/${projectId}/stages/${stageName}/memory`, memory)
}