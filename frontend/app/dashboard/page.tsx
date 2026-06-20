// ─────────────────────────────────────────────
// Dashboard — My Projects page
// Shows all user projects with filters
// ─────────────────────────────────────────────

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { listProjects, STATUS_COLORS, STATUS_LABELS, STAGE_LABELS, timeAgo } from '../../lib/projects'
import { getSession, signOut } from '../../lib/auth'
import type { UserProject } from '../../lib/supabase'

const FILTERS = [
  { id: 'all',         label: 'All Projects' },
  { id: 'in_progress', label: 'Active'        },
  { id: 'pending',     label: 'Pending'       },
  { id: 'completed',   label: 'Completed'     },
  { id: 'archived',    label: 'Archived'      },
]

export default function DashboardPage() {
  const router = useRouter()
  const [projects,     setProjects]     = useState<UserProject[]>([])
  const [filtered,     setFiltered]     = useState<UserProject[]>([])
  const [activeFilter, setActiveFilter] = useState('all')
  const [search,       setSearch]       = useState('')
  const [isLoading,    setIsLoading]    = useState(true)
  const [user,         setUser]         = useState<{ email: string; name: string } | null>(null)

  useEffect(() => {
    getSession().then(session => {
      if (!session) { router.replace('/auth'); return }
      setUser({
        email: session.user.email || '',
        name:  session.user.user_metadata?.full_name || session.user.email?.split('@')[0] || 'User',
      })
      loadProjects()
    }).catch(() => router.replace('/auth'))
  }, [])

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
  }, [projects, activeFilter, search])

  const loadProjects = async () => {
    setIsLoading(true)
    try {
      const data = await listProjects()
      setProjects(data)
    } finally {
      setIsLoading(false)
    }
  }

  const counts = projects.reduce((acc, p) => {
    acc[p.overall_status] = (acc[p.overall_status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const handleSignOut = async () => {
    await signOut()
    router.replace('/auth')
  }

  const progressColor = (p: number) =>
    p === 100 ? 'bg-[#3fb950]' :
    p >= 50   ? 'bg-[#58a6ff]' :
    p >= 20   ? 'bg-amber-400' :
    'bg-[#30363d]'

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">

      {/* Header */}
      <header className="border-b border-[#21262d] px-6 py-4 flex items-center justify-between sticky top-0 bg-[#0d1117]/95 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div className="w-7 h-7 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
              <span className="text-[#f0b429] text-sm font-bold">3</span>
            </div>
            <span className="text-sm font-semibold">
              3Netra<span className="text-[#f0b429]">-AI</span>
            </span>
          </button>
          <span className="text-[#30363d]">/</span>
          <span className="text-sm text-[#8b949e]">My Projects</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#161b22] border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#484f58] rounded-lg transition-colors font-mono"
          >
            <span className="text-[#f0b429]">+</span> New Project
          </button>
          <button
            onClick={handleSignOut}
            className="text-xs px-3 py-1.5 bg-[#161b22] border border-[#30363d] text-[#484f58] hover:text-[#f85149] hover:border-[#f85149]/30 rounded-lg transition-colors font-mono"
          >
            Sign Out
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">

        {/* Page title */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold mb-1">My Projects</h1>
          <p className="text-sm text-[#484f58]">
            {user?.name && `Welcome back, ${user.name.split(' ')[0]}.`}
            {' '}{projects.length} project{projects.length !== 1 ? 's' : ''} total.
          </p>
        </div>

        {/* Search + filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          {/* Search */}
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#484f58] text-sm">🔍</span>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search projects..."
              className="w-full bg-[#161b22] border border-[#30363d] rounded-lg pl-9 pr-4 py-2 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none focus:border-[#484f58] transition-colors"
            />
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1.5 flex-wrap">
            {FILTERS.map(f => (
              <button
                key={f.id}
                onClick={() => setActiveFilter(f.id)}
                className={`px-3 py-2 rounded-lg text-xs font-mono transition-colors ${
                  activeFilter === f.id
                    ? 'bg-[#1c2333] border border-[#58a6ff]/30 text-[#58a6ff]'
                    : 'bg-[#161b22] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3]'
                }`}
              >
                {f.label}
                {f.id !== 'all' && counts[f.id] ? (
                  <span className="ml-1.5 text-[#30363d]">{counts[f.id]}</span>
                ) : f.id === 'all' && projects.length > 0 ? (
                  <span className="ml-1.5 text-[#30363d]">{projects.length}</span>
                ) : null}
              </button>
            ))}
          </div>
        </div>

        {/* Project grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-48 bg-[#161b22] border border-[#21262d] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="text-5xl mb-4">🗂️</div>
            <h2 className="text-lg font-medium text-[#8b949e] mb-2">
              {search ? 'No projects match your search' : 'No projects yet'}
            </h2>
            <p className="text-sm text-[#484f58] mb-6">
              {search
                ? 'Try a different search term'
                : 'Start a new project to see it here'
              }
            </p>
            {!search && (
              <button
                onClick={() => router.push('/')}
                className="px-4 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors text-sm"
              >
                + Start New Project
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(project => {
              const progress    = project.progress_percentage || 0
              const statusColor = STATUS_COLORS[project.overall_status] || STATUS_COLORS.pending
              const statusLabel = STATUS_LABELS[project.overall_status] || 'Pending'
              const stageLabel  = STAGE_LABELS[project.current_stage] || project.current_stage

              return (
                <div
                  key={project.id}
                  className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden hover:border-[#484f58] transition-colors group"
                >
                  {/* Card header */}
                  <div className="px-4 pt-4 pb-3 border-b border-[#21262d]">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h3 className="text-sm font-medium text-[#e6edf3] line-clamp-2 leading-relaxed">
                        {project.title}
                      </h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full border flex-shrink-0 font-mono ${statusColor}`}>
                        {project.overall_status === 'in_progress' ? 'Active' : statusLabel}
                      </span>
                    </div>
                    {project.target_role && (
                      <p className="text-xs text-[#484f58]">{project.target_role}</p>
                    )}
                  </div>

                  {/* Progress */}
                  <div className="px-4 py-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs text-[#484f58] font-mono">{stageLabel}</span>
                      <span className="text-xs text-[#484f58] font-mono">{progress}%</span>
                    </div>
                    <div className="w-full bg-[#21262d] rounded-full h-1.5 mb-3">
                      <div
                        className={`h-1.5 rounded-full transition-all ${progressColor(progress)}`}
                        style={{ width: `${progress}%` }}
                      />
                    </div>

                    {/* Tech stack */}
                    {project.tech_stack && project.tech_stack.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-3">
                        {project.tech_stack.slice(0, 3).map((t: string, i: number) => (
                          <span key={i}
                            className="text-xs px-1.5 py-0.5 bg-[#1c2333] border border-[#58a6ff]/10 rounded text-[#58a6ff]/60">
                            {t}
                          </span>
                        ))}
                        {project.tech_stack.length > 3 && (
                          <span className="text-xs text-[#30363d]">
                            +{project.tech_stack.length - 3}
                          </span>
                        )}
                      </div>
                    )}

                    <div className="text-xs text-[#30363d]">
                      Updated {timeAgo(project.updated_at)}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="px-4 pb-4 flex gap-2">
                    <button
                      onClick={() => router.push(`/?project=${project.id}`)}
                      className="flex-1 py-2 bg-[#1c2333] border border-[#58a6ff]/20 rounded-lg text-xs font-mono text-[#58a6ff] hover:border-[#58a6ff]/40 hover:bg-[#1c2333] transition-colors"
                    >
                      Continue →
                    </button>
                    <button
                      onClick={() => router.push(`/?project=${project.id}&view=details`)}
                      className="px-3 py-2 bg-[#161b22] border border-[#30363d] rounded-lg text-xs font-mono text-[#484f58] hover:text-[#e6edf3] hover:border-[#484f58] transition-colors"
                    >
                      Details
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}