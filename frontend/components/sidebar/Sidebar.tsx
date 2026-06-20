// ─────────────────────────────────────────────
// Sidebar — ChatGPT-style project history
// Shows all user projects with status and progress
// ─────────────────────────────────────────────

'use client'

import { useState, useEffect } from 'react'
import ProjectCard from './ProjectCard'
import SearchBar from './SearchBar'
import FilterTabs from './FilterTabs'
import UserMenu from './UserMenu'
import { listProjects } from '../../lib/projects'
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
  const [projects,      setProjects]      = useState<UserProject[]>([])
  const [filtered,      setFiltered]      = useState<UserProject[]>([])
  const [search,        setSearch]        = useState('')
  const [activeFilter,  setActiveFilter]  = useState('all')
  const [isLoading,     setIsLoading]     = useState(true)

  // Load projects on mount
  useEffect(() => {
    const timer = setTimeout(() => loadProjects(), 500)
    return () => clearTimeout(timer)
  }, [])

  // Filter projects when search or filter changes
  useEffect(() => {
    let result = [...projects]

    // Apply status filter
    if (activeFilter !== 'all') {
      result = result.filter(p => p.overall_status === activeFilter)
    }

    // Apply search
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
      setIsLoading(false)
      return
    }
    setIsLoading(false)
  }

  // Count by status for filter tabs
  const counts = projects.reduce((acc, p) => {
    acc[p.overall_status] = (acc[p.overall_status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  // Collapsed sidebar — show only icons
  if (isCollapsed) {
    return (
      <div className="flex flex-col h-full w-14 bg-[#0d1117] border-r border-[#21262d]">
        {/* Toggle button */}
        <button
          onClick={onToggle}
          className="flex items-center justify-center h-14 border-b border-[#21262d] text-[#484f58] hover:text-[#e6edf3] transition-colors"
        >
          →
        </button>

        {/* New project */}
        <button
          onClick={onNewProject}
          className="flex items-center justify-center py-3 text-[#484f58] hover:text-[#f0b429] transition-colors"
          title="New Project"
        >
          +
        </button>

        {/* Project dots */}
        <div className="flex-1 overflow-y-auto py-2 space-y-2 px-2">
          {filtered.slice(0, 10).map(p => (
            <button
              key={p.id}
              onClick={() => onProjectSelect(p)}
              title={p.title}
              className={`w-10 h-10 rounded-lg border flex items-center justify-center text-xs font-bold transition-colors ${
                p.id === activeProjectId
                  ? 'bg-[#1c2333] border-[#58a6ff]/30 text-[#58a6ff]'
                  : 'bg-[#161b22] border-[#21262d] text-[#484f58] hover:text-[#e6edf3]'
              }`}
            >
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
        <button
          onClick={onToggle}
          className="text-[#484f58] hover:text-[#e6edf3] transition-colors text-sm w-6 h-6 flex items-center justify-center rounded hover:bg-[#161b22]"
          title="Collapse sidebar"
        >
          ←
        </button>
      </div>

      {/* New project button */}
      <div className="px-3 py-3 border-b border-[#21262d]">
        <button
          onClick={onNewProject}
          className="w-full flex items-center gap-2 px-3 py-2.5 bg-[#161b22] border border-[#30363d] rounded-xl text-sm text-[#8b949e] hover:text-[#e6edf3] hover:border-[#484f58] transition-colors group"
        >
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
        <FilterTabs
          active={activeFilter}
          onChange={setActiveFilter}
          counts={counts}
        />
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {isLoading ? (
          <div className="space-y-2 px-1">
            {[1, 2, 3].map(i => (
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
              <button
                onClick={onNewProject}
                className="text-xs text-[#f0b429] mt-2 hover:text-[#e0a419] transition-colors"
              >
                Start your first project →
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {/* Section label */}
            <div className="px-3 py-1">
              <span className="text-xs font-mono text-[#30363d] uppercase tracking-widest">
                My Projects
              </span>
            </div>
            {filtered.map(project => (
              <ProjectCard
                key={project.id}
                project={project}
                isActive={project.id === activeProjectId}
                onClick={() => onProjectSelect(project)}
              />
            ))}
          </div>
        )}
      </div>

      {/* User menu at bottom */}
      <div className="border-t border-[#21262d] px-3 py-3">
        <UserMenu
          onSignOut={onSignOut}
          role={role}
          purpose={purpose}
        />
      </div>
    </div>
  )
}