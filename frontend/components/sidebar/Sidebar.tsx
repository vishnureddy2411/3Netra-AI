// ─────────────────────────────────────────────
// Sidebar — ChatGPT-style project history
// ─────────────────────────────────────────────

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  ClipboardList, BookOpen, Code2, Eye, FileText,
  TestTube2, Rocket, MessageSquare,
} from 'lucide-react'
import UserMenu from './UserMenu'
import { listProjects, listSessions, deleteProject } from '../../lib/projects'
import type { UserProject } from '../../lib/supabase'

interface Props {
  activeProjectId:  string | null
  activeSessionId?: string | null
  onProjectSelect:  (project: UserProject) => void
  onSessionSelect?: (project: UserProject, sessionId: string) => void
  onNewStageChat?:  (project: UserProject, stageName: string) => void
  onNewProject:     () => void
  onSignOut:        () => void
  role?:            string
  purpose?:         string
  isCollapsed:      boolean
  onToggle:         () => void
  refreshTrigger?:  number
}

const STAGE_ICONS: Record<string, React.ReactNode> = {
  planning: <ClipboardList size={12} />,
  quiz:     <BookOpen      size={12} />,
  code_gen: <Code2         size={12} />,
  preview:  <Eye           size={12} />,
  career:   <FileText      size={12} />,
  qa:       <TestTube2     size={12} />,
  deploy:   <Rocket        size={12} />,
}

const STAGE_LABELS: Record<string, string> = {
  planning: 'Planning',
  quiz:     'Quiz',
  code_gen: 'Code Gen',
  preview:  'Preview',
  career:   'Career',
  qa:       'QA',
  deploy:   'Deploy',
}

const STATUS_COLORS: Record<string, string> = {
  pending:     'text-[#484f58] bg-[#161b22] border-[#30363d]',
  in_progress: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  completed:   'text-[#3fb950] bg-[#1a2e1a] border-[#3fb950]/20',
  archived:    'text-[#30363d] bg-[#0d1117] border-[#21262d]',
}

function timeAgo(dateStr: string) {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60)    return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function Sidebar({
  activeProjectId,
  activeSessionId,
  onProjectSelect,
  onSessionSelect,
  onNewStageChat,
  onNewProject,
  onSignOut,
  role,
  purpose,
  isCollapsed,
  onToggle,
  refreshTrigger,
}: Props) {
  const [projects,        setProjects]        = useState<UserProject[]>([])
  const [filtered,        setFiltered]        = useState<UserProject[]>([])
  const [search,          setSearch]          = useState('')
  const [activeFilter,    setActiveFilter]    = useState('all')
  const [isLoading,       setIsLoading]       = useState(true)
  const [expandedProject, setExpandedProject] = useState<string | null>(null)
  const [projectSessions, setProjectSessions] = useState<Record<string, any[]>>({})
  const [loadingSessions, setLoadingSessions] = useState<Record<string, boolean>>({})
  const [deleteConfirm,   setDeleteConfirm]   = useState<string | null>(null)

  const loadProjects = useCallback(async () => {
    try {
      const data = await listProjects()
      setProjects(data)
    } catch {
      setProjects([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { loadProjects() }, [loadProjects])

  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) loadProjects()
  }, [refreshTrigger, loadProjects])

  useEffect(() => {
    if (activeProjectId) {
      setExpandedProject(activeProjectId)
      loadProjectSessions(activeProjectId)
    }
  }, [activeProjectId])

  useEffect(() => {
    let result = [...projects]
    if (activeFilter !== 'all') {
      result = result.filter(p => p.overall_status === activeFilter)
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(p =>
        p.title.toLowerCase().includes(q) ||
        p.target_role?.toLowerCase().includes(q)
      )
    }
    setFiltered(result)
  }, [projects, search, activeFilter])

  const loadProjectSessions = async (projectId: string) => {
    if (loadingSessions[projectId]) return
    setLoadingSessions(prev => ({ ...prev, [projectId]: true }))
    try {
      const stages = await listSessions(projectId)
      setProjectSessions(prev => ({ ...prev, [projectId]: stages }))
    } catch {
      setProjectSessions(prev => ({ ...prev, [projectId]: [] }))
    } finally {
      setLoadingSessions(prev => ({ ...prev, [projectId]: false }))
    }
  }

  const handleProjectClick = (project: UserProject) => {
    if (expandedProject === project.id) {
      setExpandedProject(null)
    } else {
      setExpandedProject(project.id)
      loadProjectSessions(project.id)
    }
  }

  const counts = projects.reduce((acc, p) => {
    acc[p.overall_status] = (acc[p.overall_status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const FILTERS = [
    { id: 'all',         label: 'All'      },
    { id: 'in_progress', label: 'Active'   },
    { id: 'pending',     label: 'Pending'  },
    { id: 'completed',   label: 'Done'     },
    { id: 'archived',    label: 'Archived' },
  ]

  // ── Collapsed sidebar ─────────────────────────────────────────────────────

  if (isCollapsed) {
    return (
      <div className="flex flex-col h-full w-14 bg-[#0d1117] border-r border-[#21262d] flex-shrink-0">
        <button onClick={onToggle}
          className="flex items-center justify-center h-14 border-b border-[#21262d] text-[#484f58] hover:text-[#e6edf3] transition-colors text-lg">
          →
        </button>
        <button onClick={onNewProject}
          className="flex items-center justify-center py-3 text-[#484f58] hover:text-[#f0b429] transition-colors text-xl"
          title="New Project">
          +
        </button>
        <div className="flex-1 overflow-y-auto py-2 space-y-2 px-2">
          {filtered.slice(0, 10).map(p => (
            <button
              key={p.id}
              onClick={() => handleProjectClick(p)}
              title={p.title}
              className={`w-10 h-10 rounded-lg border flex items-center justify-center text-xs font-bold transition-colors ${
                p.id === activeProjectId
                  ? 'bg-[#1c2333] border-[#58a6ff]/30 text-[#58a6ff]'
                  : 'bg-[#161b22] border-[#21262d] text-[#484f58] hover:text-[#e6edf3]'
              }`}>
              {p.title.slice(0, 2).toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // ── Full sidebar ──────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full w-64 bg-[#0d1117] border-r border-[#21262d] flex-shrink-0">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
        <a href="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="w-6 h-6 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
            <span className="text-[#f0b429] text-xs font-bold">3</span>
          </div>
          <span className="text-sm font-semibold text-[#e6edf3]">
            3Netra<span className="text-[#f0b429]">-AI</span>
          </span>
        </a>
        <button onClick={onToggle}
          className="text-[#484f58] hover:text-[#e6edf3] transition-colors text-sm w-6 h-6 flex items-center justify-center rounded hover:bg-[#161b22]">
          ←
        </button>
      </div>

      {/* New project button */}
      <div className="px-3 py-3 border-b border-[#21262d]">
        <button onClick={onNewProject}
          className="w-full flex items-center gap-2 px-3 py-2.5 bg-[#161b22] border border-[#30363d] rounded-xl text-sm text-[#8b949e] hover:text-[#e6edf3] hover:border-[#484f58] transition-colors group">
          <span className="text-[#f0b429] group-hover:scale-110 transition-transform">+</span>
          <span>New Project</span>
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-[#21262d]">
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#484f58] text-xs">🔍</span>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full bg-[#0d1117] border border-[#21262d] rounded-lg pl-8 pr-3 py-2 text-xs text-[#e6edf3] placeholder-[#30363d] outline-none focus:border-[#30363d] transition-colors"
          />
          {search && (
            <button onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#e6edf3] text-xs">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="px-3 py-2 border-b border-[#21262d]">
        <div className="flex flex-wrap gap-1">
          {FILTERS.map(f => {
            const count = f.id === 'all' ? projects.length : counts[f.id] || 0
            return (
              <button key={f.id} onClick={() => setActiveFilter(f.id)}
                className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-mono transition-colors ${
                  activeFilter === f.id
                    ? 'bg-[#1c2333] border border-[#58a6ff]/30 text-[#58a6ff]'
                    : 'text-[#484f58] hover:text-[#8b949e] hover:bg-[#161b22]'
                }`}>
                {f.label}
                {count > 0 && (
                  <span className={`text-xs ${activeFilter === f.id ? 'text-[#58a6ff]/70' : 'text-[#30363d]'}`}>
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {isLoading ? (
          <div className="space-y-2 px-1">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-[#161b22] border border-[#21262d] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-center px-4">
            <div className="text-2xl mb-2">🗂️</div>
            <p className="text-xs text-[#30363d]">
              {search ? 'No projects match your search' : 'No projects yet'}
            </p>
            {!search && (
              <button onClick={onNewProject}
                className="text-xs text-[#f0b429] mt-2 hover:text-[#e0a419] transition-colors">
                Start your first project →
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-0.5">
            <div className="px-3 py-1.5">
              <span className="text-xs font-mono text-[#30363d] uppercase tracking-widest">
                My Projects
              </span>
            </div>

            {filtered.map(project => {
              const isActive    = project.id === activeProjectId
              const isExpanded  = expandedProject === project.id
              const stages      = projectSessions[project.id] || []
              const isLoadingS  = loadingSessions[project.id]
              const statusColor = STATUS_COLORS[project.overall_status] || STATUS_COLORS.pending

              return (
                <div key={project.id}>

                  {/* Project row */}
                  <div className={`flex items-center gap-1 rounded-xl transition-all group ${
                    isActive ? 'bg-[#1c2333]' : 'hover:bg-[#161b22]'
                  }`}>
                    <button
                      onClick={() => handleProjectClick(project)}
                      className="flex-1 text-left px-3 py-2.5 min-w-0"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className={`text-xs font-semibold truncate flex-1 ${
                          isActive ? 'text-[#e6edf3]' : 'text-[#c9d1d9]'
                        }`}>
                          {project.title}
                        </span>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span className={`text-xs px-1.5 py-0.5 rounded-full border font-mono ${statusColor}`}>
                            {project.overall_status === 'in_progress' ? 'Active' :
                             project.overall_status.charAt(0).toUpperCase() + project.overall_status.slice(1)}
                          </span>
                          <span className="text-[#484f58] text-xs">
                            {isExpanded ? '▾' : '▸'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-[#21262d] rounded-full h-0.5">
                          <div
                            className={`h-0.5 rounded-full ${
                              project.progress_percentage === 100 ? 'bg-[#3fb950]' :
                              project.progress_percentage >= 50  ? 'bg-[#58a6ff]' :
                              'bg-amber-400'
                            }`}
                            style={{ width: `${project.progress_percentage || 0}%` }}
                          />
                        </div>
                        <span className="text-xs text-[#30363d] flex-shrink-0">
                          {timeAgo(project.updated_at)}
                        </span>
                      </div>
                    </button>

                    {/* Action buttons — visible on hover */}
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 mr-1 transition-all">
                      {/* Open project page in new tab */}
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          window.open(`/project/${project.id}`, '_blank', 'noopener,noreferrer')
                        }}
                        className="w-6 h-6 flex items-center justify-center text-[#484f58] hover:text-[#58a6ff] hover:bg-[#1c2333] rounded transition-all"
                        title="Open project in new tab"
                      >
                        ↗
                      </button>
                      {/* Delete */}
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          setDeleteConfirm(deleteConfirm === project.id ? null : project.id)
                        }}
                        className="w-6 h-6 flex items-center justify-center text-[#484f58] hover:text-[#f85149] hover:bg-[#2d1b1b] rounded transition-all"
                        title="Delete project"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* Delete confirmation */}
                  {deleteConfirm === project.id && (
                    <div className="mx-2 mb-1 bg-[#2d1b1b] border border-[#f85149]/20 rounded-xl p-3">
                      <p className="text-xs text-[#f85149] mb-2 leading-relaxed">
                        Delete <span className="font-semibold">"{project.title}"</span>?
                        All sessions will be removed. This cannot be undone.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={async e => {
                            e.stopPropagation()
                            const ok = await deleteProject(project.id)
                            if (ok) { setDeleteConfirm(null); loadProjects() }
                          }}
                          className="flex-1 py-1.5 bg-[#f85149] text-white text-xs font-semibold rounded-lg hover:bg-[#e0403a] transition-colors"
                        >
                          Delete
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); setDeleteConfirm(null) }}
                          className="flex-1 py-1.5 bg-[#161b22] border border-[#30363d] text-[#484f58] text-xs rounded-lg hover:text-[#e6edf3] transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Sessions panel */}
                  {isExpanded && (
                    <div className="ml-3 mr-1 mb-1 bg-[#0d1117] border border-[#21262d] rounded-xl overflow-hidden">
                      {isLoadingS ? (
                        <div className="px-3 py-3 space-y-2">
                          {[1, 2].map(i => (
                            <div key={i} className="h-8 bg-[#161b22] rounded animate-pulse" />
                          ))}
                        </div>
                      ) : stages.length === 0 ? (
                        <div className="px-3 py-3 text-xs text-[#30363d] text-center">
                          No sessions yet
                        </div>
                      ) : (
                        <div className="py-1">
                          {stages.map((stage: any) => (
                            <div key={stage.stage_number}>

                              {/* Stage label — folder header with New Chat button */}
                              <div className="px-3 py-1.5 flex items-center justify-between gap-1.5 group/stage">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[#484f58] flex items-center">
                                    {STAGE_ICONS[stage.stage_name] || <MessageSquare size={12} />}
                                  </span>
                                  <span className="text-xs font-mono text-[#30363d] uppercase tracking-widest">
                                    {STAGE_LABELS[stage.stage_name] || stage.stage_name}
                                  </span>
                                </div>
                                <button
                                  onClick={e => {
                                    e.stopPropagation()
                                    onNewStageChat?.(project, stage.stage_name)
                                  }}
                                  className="opacity-0 group-hover/stage:opacity-100 flex items-center gap-0.5 px-1.5 py-0.5 bg-[#f0b429]/10 border border-[#f0b429]/20 text-[#f0b429] hover:bg-[#f0b429]/20 rounded text-xs font-mono transition-all"
                                  title={`New chat in ${STAGE_LABELS[stage.stage_name] || stage.stage_name}`}
                                >
                                  + New
                                </button>
                              </div>

                              {/* Session items */}
                              {stage.sessions.map((session: any) => {
                                const isActiveSession = session.id === activeSessionId
                                return (
                                  <div
                                    key={session.id}
                                    className={`group/session flex items-center transition-colors hover:bg-[#161b22] ${
                                      isActiveSession ? 'bg-[#161b22]' : ''
                                    }`}
                                  >
                                    {/* Session click — loads read-only view in main page */}
                                    <button
                                      onClick={e => {
                                        e.stopPropagation()
                                        onSessionSelect?.(project, session.id)
                                      }}
                                      className="flex-1 text-left px-3 py-2"
                                    >
                                      <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                          {session.status === 'active' && (
                                            <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950] flex-shrink-0" />
                                          )}
                                          <span className={`text-xs truncate ${
                                            isActiveSession ? 'text-[#e6edf3]' : 'text-[#8b949e]'
                                          }`}>
                                            {session.title || `Session ${session.session_number}`}
                                          </span>
                                        </div>
                                        <span className="text-xs text-[#30363d] flex-shrink-0 ml-2">
                                          {session.message_count}msg
                                        </span>
                                      </div>
                                      <div className="text-xs text-[#30363d] mt-0.5 pl-3">
                                        {timeAgo(session.created_at)}
                                      </div>
                                    </button>

                                    {/* Open session in new tab — uses window.open to prevent page refresh */}
                                    <button
                                      onClick={e => {
                                        e.stopPropagation()
                                        e.preventDefault()
                                        window.open(
                                          `/?project=${project.id}&viewSession=${session.id}`,
                                          '_blank',
                                          'noopener,noreferrer'
                                        )
                                      }}
                                      className="opacity-0 group-hover/session:opacity-100 w-6 h-6 flex items-center justify-center text-[#30363d] hover:text-[#58a6ff] transition-all mr-1 flex-shrink-0"
                                      title="Open session in new tab for reference"
                                    >
                                      ↗
                                    </button>
                                  </div>
                                )
                              })}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Resume project footer */}
                      <div className="border-t border-[#21262d] px-3 py-2">
                        <button
                          onClick={e => {
                            e.stopPropagation()
                            window.location.href = `/?project=${project.id}`
                          }}
                          className="w-full flex items-center justify-center gap-1.5 py-1.5 text-xs text-[#484f58] hover:text-[#f0b429] hover:bg-[#161b22] rounded-lg transition-colors font-mono"
                        >
                          Resume Project →
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* User menu */}
      <div className="border-t border-[#21262d] px-3 py-3">
        <UserMenu onSignOut={onSignOut} role={role} purpose={purpose} />
      </div>
    </div>
  )
}