// ─────────────────────────────────────────────
// Project storage helpers
// All project CRUD operations with auth
// ─────────────────────────────────────────────

import { authPost, authGet } from './auth'
import type { SelectedProject, DeepAnalysisResult } from './types'
import type { UserProject } from './supabase'

const API = 'http://localhost:8000/api'

// ── Create project ────────────────────────────

export async function createProject(
  selectedProject: SelectedProject,
  role: string,
  purpose: string,
  verdict?: any,
  deepAnalysis?: DeepAnalysisResult | null,
  advisorOutputs?: any[],
): Promise<UserProject | null> {
  try {
    console.log('Creating project:', selectedProject.title, '| role:', role, '| purpose:', purpose)
    const result = await authPost(`${API}/projects`, {
      title:                selectedProject.title,
      description:          selectedProject.description,
      target_role:          role,
      purpose,
      difficulty_level:     selectedProject.level,
      estimated_duration:   selectedProject.buildTime,
      tech_stack:           selectedProject.techStack || [],
      risks:                selectedProject.risks || [],
      portfolio_value:      selectedProject.portfolioValue || '',
      full_idea:            selectedProject.fullIdea,
      deep_analysis:        deepAnalysis || {},
      verdict:              verdict || {},
      advisor_outputs:      advisorOutputs || [],
      internal_project_id:  selectedProject.projectId || '',
    })
    return result.project || null
  } catch (err) {
    console.error('Failed to create project:', err)
    return null
  }
}

// ── List projects ─────────────────────────────

export async function listProjects(
  status?: string,
): Promise<UserProject[]> {
  try {
    const url = status && status !== 'all'
      ? `${API}/projects?status=${status}`
      : `${API}/projects`
    const result = await authGet(url)
    return result.projects || []
  } catch (err) {
    console.error('Failed to list projects:', err)
    return []
  }
}

// ── Get single project ────────────────────────

export async function getProject(
  projectId: string,
): Promise<UserProject | null> {
  try {
    const result = await authGet(`${API}/projects/${projectId}`)
    return result.project || null
  } catch (err) {
    console.error('Failed to get project:', err)
    return null
  }
}

// ── Update project stage ──────────────────────

export async function updateProjectStage(
  projectId: string,
  stageName: string,
  outputData: any = {},
): Promise<boolean> {
  try {
    await authPost(`${API}/projects/${projectId}/stage`, {
      stage_name:   stageName,
      stage_status: 'completed',
      output_data:  outputData,
    })
    return true
  } catch (err) {
    console.error('Failed to update stage:', err)
    return false
  }
}

// ── Save chat message ─────────────────────────

export async function saveChatMessage(
  projectId: string,
  role: 'user' | 'agent',
  contentType: string,
  content: any,
): Promise<boolean> {
  try {
    await authPost(`${API}/projects/history`, {
      project_id:   projectId,
      role,
      content_type: contentType,
      content,
    })
    return true
  } catch (err) {
    console.error('Failed to save message:', err)
    return false
  }
}

// ── Get chat history ──────────────────────────

export async function getChatHistory(projectId: string): Promise<any[]> {
  try {
    const result = await authGet(`${API}/projects/${projectId}/history`)
    return result.history || []
  } catch (err) {
    console.error('Failed to get history:', err)
    return []
  }
}

// ── Archive project ───────────────────────────

export async function archiveProject(projectId: string): Promise<boolean> {
  try {
    await authPost(`${API}/projects/${projectId}`, {
      overall_status: 'archived',
    })
    return true
  } catch (err) {
    console.error('Failed to archive project:', err)
    return false
  }
}

// ── Progress helpers ──────────────────────────

export const STATUS_COLORS: Record<string, string> = {
  pending:     'text-[#484f58] bg-[#161b22] border-[#30363d]',
  in_progress: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  completed:   'text-[#3fb950] bg-[#1a2e1a] border-[#3fb950]/20',
  archived:    'text-[#30363d] bg-[#0d1117] border-[#21262d]',
}

export const STATUS_LABELS: Record<string, string> = {
  pending:     'Pending',
  in_progress: 'In Progress',
  completed:   'Completed',
  archived:    'Archived',
}

export const STAGE_LABELS: Record<string, string> = {
  project_selected:    'Project Selected',
  confirmation_gate:   'Confirmation',
  discussion:          'Discussion',
  diagram_creation:    'Diagrams',
  implementation_plan: 'Implementation',
  readme_generation:   'README',
  resume_generation:   'Resume',
  completed:           'Completed',
}

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now  = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diff < 60)   return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return date.toLocaleDateString()
}

// ── Session management ────────────────────────

const API_BASE = 'http://localhost:8000/api'

export async function createSession(
  projectId: string,
  stageNumber: number = 6,
  stageName: string = 'planning',
  title?: string,
): Promise<any | null> {
  try {
    const result = await authPost(`${API_BASE}/projects/${projectId}/sessions`, {
      stage_number: stageNumber,
      stage_name:   stageName,
      title:        title || `${stageName.replace('_', ' ')} Session`,
    })
    return result.session || null
  } catch (err) {
    console.error('Failed to create session:', err)
    return null
  }
}

export async function listSessions(projectId: string): Promise<any[]> {
  try {
    const result = await authGet(`${API_BASE}/projects/${projectId}/sessions`)
    return result.stages || []
  } catch (err) {
    console.error('Failed to list sessions:', err)
    return []
  }
}

export async function saveSessionMessage(
  projectId: string,
  sessionId: string,
  role: 'user' | 'agent',
  contentType: string,
  content: any,
): Promise<boolean> {
  try {
    await authPost(
      `${API_BASE}/projects/${projectId}/sessions/${sessionId}/messages`,
      { role, content_type: contentType, content }
    )
    return true
  } catch (err) {
    console.error('Failed to save session message:', err)
    return false
  }
}

export async function getSessionMessages(
  projectId: string,
  sessionId: string,
): Promise<any[]> {
  try {
    const result = await authGet(
      `${API_BASE}/projects/${projectId}/sessions/${sessionId}/messages`
    )
    return result.messages || []
  } catch (err) {
    console.error('Failed to get session messages:', err)
    return []
  }
}

// Message types that should NOT be saved
// thinking cards are temporary loading indicators
export const SKIP_SAVE_TYPES = ['thinking']

// Max messages before showing "Start New Chat" banner
export const MAX_SESSION_MESSAGES = 50

export async function deleteProject(projectId: string): Promise<boolean> {
  try {
    const { getSession } = await import('./auth')
    const session = await getSession()
    const token   = session?.access_token || ''
    const res     = await fetch(`${API_BASE}/projects/${projectId}`, {
      method:  'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await res.json()
    return data.success === true
  } catch (err) {
    console.error('Failed to delete project:', err)
    return false
  }
}