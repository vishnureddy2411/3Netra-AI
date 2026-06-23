// ─────────────────────────────────────────────
// Dashboard — My Projects page
// Shows all user projects with filters
// ─────────────────────────────────────────────

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface Project {
  id: string
  title: string
  description: string
  full_idea: string
  target_role: string
  purpose: string
  tech_stack: string[]
  overall_status: string
  current_stage: string
  progress_percentage: number
  created_at: string
  updated_at: string
}

const PIPELINE_STAGES = [
  { number: 6,  label: 'Planning',    icon: '📋' },
  { number: 7,  label: 'Quiz',        icon: '📚' },
  { number: 8,  label: 'Code Gen',    icon: '💻' },
  { number: 9,  label: 'Preview',     icon: '👁'  },
  { number: 10, label: 'Career',      icon: '📄' },
  { number: 11, label: 'QA',          icon: '🧪' },
  { number: 12, label: 'Deploy',      icon: '🚀' },
]

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  pending:     { label: 'Pending',     color: 'bg-[#21262d] text-[#8b949e] border-[#30363d]',          dot: 'bg-[#484f58]'  },
  in_progress: { label: 'In Progress', color: 'bg-amber-400/10 text-amber-400 border-amber-400/20',    dot: 'bg-amber-400'  },
  completed:   { label: 'Completed',   color: 'bg-[#3fb950]/10 text-[#3fb950] border-[#3fb950]/20',    dot: 'bg-[#3fb950]'  },
  archived:    { label: 'Archived',    color: 'bg-[#161b22] text-[#30363d] border-[#21262d]',           dot: 'bg-[#30363d]'  },
}

const PURPOSE_LABELS: Record<string, string> = {
  portfolio: 'Portfolio',
  startup:   'Startup',
  learning:  'Learning',
}

function timeAgo(dateStr: string) {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60)    return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function ProjectCard({ project, onOpen, onResume, onDelete }: {
  project: Project
  onOpen:   () => void
  onResume: () => void
  onDelete: () => void
}) {
  const status   = STATUS_CONFIG[project.overall_status] || STATUS_CONFIG.pending
  const progress = project.progress_percentage || 0

  // Determine current stage from progress
  const stageIndex    = Math.floor((progress / 100) * PIPELINE_STAGES.length)
  const currentStage  = PIPELINE_STAGES[Math.min(stageIndex, PIPELINE_STAGES.length - 1)]

  return (
    <div className="bg-[#161b22] border border-[#21262d] rounded-2xl overflow-hidden hover:border-[#30363d] transition-all group">

      {/* Top bar — status indicator */}
      <div className={`h-0.5 w-full ${
        progress === 100 ? 'bg-[#3fb950]'
        : progress >= 50  ? 'bg-[#58a6ff]'
        : progress > 0    ? 'bg-amber-400'
        : 'bg-[#21262d]'
      }`} style={{ width: `${Math.max(progress, 3)}%` }} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-[#e6edf3] truncate mb-1">
              {project.title}
            </h3>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full border font-mono ${status.color}`}>
                {status.label}
              </span>
              <span className="text-xs text-[#484f58]">{project.target_role}</span>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-lg font-bold text-[#e6edf3]">{progress}%</div>
            <div className="text-xs text-[#484f58]">complete</div>
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-[#484f58] leading-relaxed mb-4 line-clamp-2">
          {project.full_idea || project.description || 'No description'}
        </p>

        {/* Pipeline mini progress */}
        <div className="mb-4">
          <div className="flex items-center gap-0.5 mb-1.5">
            {PIPELINE_STAGES.map((stage, i) => {
              const stagePct  = (i / PIPELINE_STAGES.length) * 100
              const isDone    = progress > stagePct + (100 / PIPELINE_STAGES.length)
              const isActive  = progress >= stagePct && !isDone
              return (
                <div key={stage.number}
                  title={stage.label}
                  className={`flex-1 h-1 rounded-full transition-all ${
                    isDone   ? 'bg-[#3fb950]'
                    : isActive ? 'bg-amber-400'
                    : 'bg-[#21262d]'
                  }`}
                />
              )
            })}
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#30363d] font-mono">
              {currentStage?.icon} {currentStage?.label}
            </span>
            <span className="text-xs text-[#30363d]">
              {timeAgo(project.updated_at)}
            </span>
          </div>
        </div>

        {/* Tech stack */}
        {project.tech_stack && project.tech_stack.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {project.tech_stack.slice(0, 4).map((tech, i) => (
              <span key={i}
                className="text-xs px-1.5 py-0.5 bg-[#0d1117] border border-[#21262d] text-[#484f58] rounded font-mono">
                {tech}
              </span>
            ))}
            {project.tech_stack.length > 4 && (
              <span className="text-xs px-1.5 py-0.5 bg-[#0d1117] border border-[#21262d] text-[#30363d] rounded font-mono">
                +{project.tech_stack.length - 4}
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button onClick={onResume}
            className="flex-1 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors text-xs">
            Resume →
          </button>
          <button onClick={onOpen}
            className="px-3 py-2 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#484f58] rounded-lg transition-colors text-xs font-mono">
            View
          </button>
          <button onClick={onDelete}
            className="px-3 py-2 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#f85149] hover:border-[#f85149]/30 rounded-lg transition-colors text-xs">
            ✕
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const router = useRouter()

  const [projects,     setProjects]     = useState<Project[]>([])
  const [filtered,     setFiltered]     = useState<Project[]>([])
  const [isLoading,    setIsLoading]    = useState(true)
  const [search,       setSearch]       = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [sortBy,       setSortBy]       = useState<'updated' | 'created' | 'progress'>('updated')

  useEffect(() => { loadProjects() }, [])

  useEffect(() => {
    let result = [...projects]

    // Filter
    if (activeFilter !== 'all') {
      result = result.filter(p => p.overall_status === activeFilter)
    }

    // Search
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(p =>
        p.title.toLowerCase().includes(q) ||
        p.target_role?.toLowerCase().includes(q) ||
        p.full_idea?.toLowerCase().includes(q) ||
        p.tech_stack?.some(t => t.toLowerCase().includes(q))
      )
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === 'updated')  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      if (sortBy === 'created')  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      if (sortBy === 'progress') return (b.progress_percentage || 0) - (a.progress_percentage || 0)
      return 0
    })

    setFiltered(result)
  }, [projects, search, activeFilter, sortBy])

  const getToken = async () => {
    const { getSession } = await import('../../lib/auth')
    const session = await getSession()
    return session?.access_token || ''
  }

  const loadProjects = async () => {
    setIsLoading(true)
    try {
      const token = await getToken()
      const res   = await fetch('http://localhost:8000/api/projects', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setProjects(data.projects || [])
      }
    } catch (e) {
      console.error('Failed to load projects:', e)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (project: Project) => {
    if (!confirm(`Delete "${project.title}"? This cannot be undone.`)) return
    try {
      const token = await getToken()
      await fetch(`http://localhost:8000/api/projects/${project.id}`, {
        method:  'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      loadProjects()
    } catch (e) {
      alert('Delete failed. Please try again.')
    }
  }

  // Stats
  const stats = {
    total:       projects.length,
    active:      projects.filter(p => p.overall_status === 'in_progress').length,
    completed:   projects.filter(p => p.overall_status === 'completed').length,
    avgProgress: projects.length
      ? Math.round(projects.reduce((a, p) => a + (p.progress_percentage || 0), 0) / projects.length)
      : 0,
  }

  const FILTERS = [
    { id: 'all',         label: 'All',         count: projects.length },
    { id: 'in_progress', label: 'Active',       count: stats.active },
    { id: 'pending',     label: 'Pending',      count: projects.filter(p => p.overall_status === 'pending').length },
    { id: 'completed',   label: 'Completed',    count: stats.completed },
    { id: 'archived',    label: 'Archived',     count: projects.filter(p => p.overall_status === 'archived').length },
  ]

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">

      {/* Header */}
      <div className="border-b border-[#21262d] sticky top-0 z-10 bg-[#0d1117]/95 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={() => router.push('/')}
                className="text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors">
                ← Home
              </button>
              <div className="w-px h-4 bg-[#21262d]" />
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
                  <span className="text-[#f0b429] text-xs font-bold">3</span>
                </div>
                <span className="text-sm font-semibold">
                  3Netra<span className="text-[#f0b429]">-AI</span>
                  <span className="text-[#484f58] font-normal ml-2">/ Dashboard</span>
                </span>
              </div>
            </div>
            <button onClick={() => router.push('/')}
              className="text-xs px-3 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors">
              + New Project
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total Projects', value: stats.total,       color: 'text-[#e6edf3]'  },
            { label: 'Active',         value: stats.active,      color: 'text-amber-400'  },
            { label: 'Completed',      value: stats.completed,   color: 'text-[#3fb950]'  },
            { label: 'Avg Progress',   value: `${stats.avgProgress}%`, color: 'text-[#58a6ff]' },
          ].map(stat => (
            <div key={stat.label}
              className="bg-[#161b22] border border-[#21262d] rounded-xl p-4">
              <div className={`text-2xl font-bold mb-1 ${stat.color}`}>{stat.value}</div>
              <div className="text-xs text-[#484f58] font-mono">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-48">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#484f58] text-xs">🔍</span>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search projects, roles, tech..."
              className="w-full bg-[#161b22] border border-[#21262d] rounded-lg pl-8 pr-3 py-2 text-xs text-[#e6edf3] placeholder-[#30363d] outline-none focus:border-[#30363d] transition-colors"
            />
            {search && (
              <button onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#e6edf3] text-xs">
                ✕
              </button>
            )}
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1">
            {FILTERS.map(f => (
              <button key={f.id}
                onClick={() => setActiveFilter(f.id)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                  activeFilter === f.id
                    ? 'bg-[#1c2333] border border-[#58a6ff]/30 text-[#58a6ff]'
                    : 'text-[#484f58] hover:text-[#8b949e] hover:bg-[#161b22]'
                }`}>
                {f.label}
                {f.count > 0 && (
                  <span className={`text-xs ${activeFilter === f.id ? 'text-[#58a6ff]/70' : 'text-[#30363d]'}`}>
                    {f.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as any)}
            className="bg-[#161b22] border border-[#21262d] rounded-lg px-3 py-1.5 text-xs text-[#8b949e] outline-none font-mono"
          >
            <option value="updated">Last updated</option>
            <option value="created">Date created</option>
            <option value="progress">Progress</option>
          </select>
        </div>

        {/* Project grid */}
        {isLoading ? (
          <div className="grid grid-cols-3 gap-4">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="h-64 bg-[#161b22] border border-[#21262d] rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="text-5xl mb-4">🗂️</div>
            <p className="text-sm text-[#484f58] mb-2">
              {search ? 'No projects match your search' : 'No projects yet'}
            </p>
            {!search && (
              <button onClick={() => router.push('/')}
                className="text-xs text-[#f0b429] hover:text-[#e0a419] transition-colors mt-2">
                Start your first project →
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {filtered.map(project => (
              <ProjectCard
                key={project.id}
                project={project}
                onOpen={()   => router.push(`/project/${project.id}`)}
                onResume={()  => router.push(`/?project=${project.id}`)}
                onDelete={()  => handleDelete(project)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}