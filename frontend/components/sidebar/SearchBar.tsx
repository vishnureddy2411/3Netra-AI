'use client'

import { useState, useEffect } from 'react'
import ProjectCard from './ProjectCard'
import SearchBar from './SearchBar'
import FilterTabs from './FilterTabs'
import UserMenu from './UserMenu'
import { listProjects, listSessions } from '../../lib/projects'
import type { UserProject } from '../../lib/supabase'

interface Props {
  activeProjectId: string | null
  activeSessionId?: string | null
  onProjectSelect: (project: UserProject) => void
  onSessionSelect?: (project: UserProject, sessionId: string) => void
  onNewProject: () => void
  onSignOut: () => void
  role?: string
  purpose?: string
  isCollapsed: boolean
  onToggle: () => void
}

const STAGE_ICONS: Record<string, string> = {
  planning:        '📋',
  quiz:            '📚',
  code_gen:        '💻',
  preview:         '👁',
  career:          '📄',
  qa:              '🧪',
  deploy:          '🚀',
}

const STAGE_LABELS: Record<string, string> = {
  planning:        'Planning',
  quiz:            'Quiz',
  code_gen:        'Code Gen',
  preview:         'Preview',
  career:          'Career',
  qa:              'QA',
  deploy:          'Deploy',
}

export default function Sidebar({
  activeProjectId,
  activeSessionId,
  onProjectSelect,
  onSessionSelect,
  onNewProject,
  onSignOut,
  role,
  purpose,
  isCollapsed,
  onToggle,
}: Props) {
  const [projects,     setProjects]     = useState<UserProject[]>([])
  const [filtered,     setFiltered]     = useState<UserProject[]>([])
  const [search,       setSearch]       = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [isLoading,    setIsLoading]    = useState(true)
  const [expandedProjects, setExpandedProjects] = useState<Record<string, boolean>>({})
  const [projectSessions,  setProjectSessions]  = useState<Record<string, any[]>>({})
  const [loadingSessions,  setLoadingSessions]  = useState<Record<string, boolean>>({})

  useEffect(() => { loadProjects() }, [])

  useEffect(() => {
    // Auto-expand active project
    if (activeProjectId) {
      setExpandedProjects(prev => ({ ...prev, [activeProjectId]: true }))
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
        p.target_role?.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q)
      )
    }
    setFiltered(result)
  }, [projects, search, activeFilter])

  const loadProjects = async () => {
    setIsLoading(true)
    try {
      const data = await listProjects()
      setProjects(data)
    } catch {
      setProjects([])
    } finally {
      setIsLoading(false)
    }
  }

  const loadProjectSessions = async (projectId: string) => {
    if (projectSessions[projectId] || loadingSessions[projectId]) return
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

  const toggleProject = (projectId: string) => {
    const isExpanding = !expandedProjects[projectId]
    setExpandedProjects(prev => ({ ...prev, [projectId]: isExpanding }))
    if (isExpanding) loadProjectSessions(projectId)
  }

  const counts = projects.reduce((acc, p) => {
    acc[p.overall_status] = (acc[p.overall_status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const timeAgo = (dateStr: string) => {
    const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }

  // Collapsed sidebar
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
            <button key={p.id} onClick={() => onProjectSelect(p)} title={p.title}
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

  // Full sidebar
  return (
    <div className="flex flex-col h-full w-64 bg-[#0d1117] border-r border-[#21262d] flex-shrink-0">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
            <span className="text-[#f0b429] text-xs font-bold">3</span>
          </div>
          <span className="text-sm font-semibold text-[#e6edf3]">
            3Netra<span className="text-[#f0b429]">-AI</span>
          </span>
        </div>
        <button onClick={onToggle}
          className="text-[#484f58] hover:text-[#e6edf3] transition-colors text-sm w-6 h-6 flex items-center justify-center rounded hover:bg-[#161b22]"
          title="Collapse sidebar">
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
        <SearchBar value={search} onChange={setSearch} />
      </div>

      {/* Filter tabs */}
      <div className="px-3 py-2 border-b border-[#21262d]">
        <FilterTabs active={activeFilter} onChange={setActiveFilter} counts={counts} />
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {isLoading ? (
          <div className="space-y-2 px-1">
            {[1,2,3].map(i => (
              <div key={i} className="h-20 bg-[#161b22] border border-[#21262d] rounded-xl animate-pulse" />
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
          <div className="space-y-1">
            <div className="px-3 py-1">
              <span className="text-xs font-mono text-[#30363d] uppercase tracking-widest">
                My Projects
              </span>
            </div>

            {filtered.map(project => {
              const isActive   = project.id === activeProjectId
              const isExpanded = expandedProjects[project.id]
              const stages     = projectSessions[project.id] || []
              const isLoadingS = loadingSessions[project.id]

              return (
                <div key={project.id}>
                  {/* Project row */}
                  <div className={`flex items-center gap-1 rounded-xl transition-all ${
                    isActive ? 'bg-[#1c2333]' : 'hover:bg-[#161b22]'
                  }`}>
                    {/* Expand toggle */}
                    <button
                      onClick={() => toggleProject(project.id)}
                      className="w-6 h-6 flex items-center justify-center text-[#484f58] hover:text-[#e6edf3] transition-colors flex-shrink-0 ml-1 text-xs"
                    >
                      {isExpanded ? '▾' : '▸'}
                    </button>

                    {/* Project card */}
                    <button
                      onClick={() => onProjectSelect(project)}
                      className="flex-1 text-left py-2 pr-2 min-w-0"
                    >
                      <div className={`text-xs font-medium truncate ${
                        isActive ? 'text-[#e6edf3]' : 'text-[#8b949e] hover:text-[#e6edf3]'
                      } transition-colors`}>
                        {project.title}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <div className="flex-1 bg-[#21262d] rounded-full h-0.5">
                          <div
                            className={`h-0.5 rounded-full ${
                              project.progress_percentage === 100 ? 'bg-[#3fb950]' :
                              project.progress_percentage >= 50 ? 'bg-[#58a6ff]' :
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
                  </div>

                  {/* Sessions — shown when expanded */}
                  {isExpanded && (
                    <div className="ml-7 mb-1 space-y-0.5">
                      {isLoadingS ? (
                        <div className="px-3 py-2">
                          <div className="h-3 bg-[#21262d] rounded animate-pulse w-3/4" />
                        </div>
                      ) : stages.length === 0 ? (
                        <div className="px-3 py-1.5 text-xs text-[#30363d]">
                          No sessions yet
                        </div>
                      ) : (
                        stages.map(stage => (
                          <div key={stage.stage_number}>
                            {/* Stage label */}
                            <div className="px-3 py-1 text-xs font-mono text-[#30363d] uppercase tracking-widest">
                              {STAGE_ICONS[stage.stage_name] || '💬'} {STAGE_LABELS[stage.stage_name] || stage.stage_name}
                            </div>

                            {/* Sessions within stage */}
                            {stage.sessions.map((session: any) => (
                              <button
                                key={session.id}
                                onClick={() => onSessionSelect?.(project, session.id)}
                                className={`w-full text-left px-3 py-1.5 rounded-lg transition-colors group ${
                                  session.id === activeSessionId
                                    ? 'bg-[#1c2333] text-[#e6edf3]'
                                    : 'text-[#484f58] hover:text-[#e6edf3] hover:bg-[#161b22]'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="text-xs truncate">
                                    Session {session.session_number}
                                  </span>
                                  <div className="flex items-center gap-1.5 flex-shrink-0">
                                    <span className="text-xs text-[#30363d]">
                                      {session.message_count}msg
                                    </span>
                                    {session.status === 'active' && (
                                      <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950]" />
                                    )}
                                  </div>
                                </div>
                                <div className="text-xs text-[#30363d] mt-0.5">
                                  {timeAgo(session.created_at)}
                                </div>
                              </button>
                            ))}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* User menu at bottom */}
      <div className="border-t border-[#21262d] px-3 py-3">
        <UserMenu onSignOut={onSignOut} role={role} purpose={purpose} />
      </div>
    </div>
  )
}