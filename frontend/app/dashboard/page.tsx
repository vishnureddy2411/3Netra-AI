// ─────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────

'use client'

import React, { useState, useEffect, useRef } from 'react'
import {
  ClipboardList, BookOpen, Code2, Eye, FileText,
  TestTube2, Rocket, Search, X, Plus, ArrowUpRight,
  LayoutGrid, Clock, TrendingUp, CheckCircle2,
  ChevronRight, Trash2, ExternalLink, Cpu,
  Activity, AlertCircle,
} from 'lucide-react'

interface Project {
  id:                  string
  title:               string
  description:         string
  full_idea:           string
  target_role:         string
  purpose:             string
  tech_stack:          string[]
  overall_status:      string
  current_stage:       string
  progress_percentage: number
  created_at:          string
  updated_at:          string
}

const PIPELINE_STAGES = [
  { number: 6,  label: 'Planning', icon: <ClipboardList size={11} /> },
  { number: 7,  label: 'Quiz',     icon: <BookOpen      size={11} /> },
  { number: 8,  label: 'Code',     icon: <Code2         size={11} /> },
  { number: 9,  label: 'Preview',  icon: <Eye           size={11} /> },
  { number: 10, label: 'Career',   icon: <FileText      size={11} /> },
  { number: 11, label: 'QA',       icon: <TestTube2     size={11} /> },
  { number: 12, label: 'Deploy',   icon: <Rocket        size={11} /> },
]
const PRO_STAGES = [
  { number: 1, label: 'Analysis',     icon: <Activity     size={11} /> },
  { number: 2, label: 'Architecture', icon: <Cpu          size={11} /> },
  { number: 3, label: 'Code',         icon: <Code2        size={11} /> },
  { number: 4, label: 'Testing',      icon: <TestTube2    size={11} /> },
  { number: 5, label: 'Deploy',       icon: <Rocket       size={11} /> },
]

function getStages(purpose: string) {
  return purpose === 'professional' ? PRO_STAGES : PIPELINE_STAGES
}
const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string; ring: string }> = {
  pending:     { label: 'Pending',     color: 'text-[#8b949e] bg-[#21262d] border-[#30363d]',        dot: 'bg-[#484f58]',  ring: 'ring-[#30363d]'          },
  in_progress: { label: 'In Progress', color: 'text-amber-400 bg-amber-400/10 border-amber-400/20',  dot: 'bg-amber-400',  ring: 'ring-amber-400/30'       },
  completed:   { label: 'Completed',   color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20', dot: 'bg-emerald-400', ring: 'ring-emerald-400/30' },
  archived:    { label: 'Archived',    color: 'text-[#30363d] bg-[#161b22] border-[#21262d]',        dot: 'bg-[#30363d]',  ring: 'ring-[#21262d]'          },
}

const PURPOSE_LABELS: Record<string, string> = {
  job_hunt:     'Get Hired',
  learning:     'Learning',
  professional: 'Work Project',
  portfolio:    'Portfolio',
  startup:      'Startup',
}

// ── Animated counter ──────────────────────────────────────────────────────────

function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef<number>(0)

  useEffect(() => {
    const target   = value
    const duration = 800
    const start    = performance.now()
    const from     = ref.current

    const tick = (now: number) => {
      const elapsed  = now - start
      const progress = Math.min(elapsed / duration, 1)
      const ease     = 1 - Math.pow(1 - progress, 3)
      const current  = Math.round(from + (target - from) * ease)
      setDisplay(current)
      if (progress < 1) requestAnimationFrame(tick)
      else ref.current = target
    }
    requestAnimationFrame(tick)
  }, [value])

  return <>{display}{suffix}</>
}

// ── Project card ──────────────────────────────────────────────────────────────

function ProjectCard({ project, onDelete }: {
  project:  Project
  onDelete: () => void
}) {
  const [hovered,       setHovered]       = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [barWidth,      setBarWidth]      = useState(0)

  const status   = STATUS_CONFIG[project.overall_status] || STATUS_CONFIG.pending
  const progress = project.progress_percentage || 0

  useEffect(() => {
    const t = setTimeout(() => setBarWidth(progress), 300)
    return () => clearTimeout(t)
  }, [progress])

  const stages      = getStages(project.purpose)
  const stageIdx    = Math.floor((progress / 100) * stages.length)
  const activeStage = stages[Math.min(stageIdx, stages.length - 1)]

  const progressColor =
    progress === 100 ? '#3fb950' :
    progress >= 50   ? '#58a6ff' :
    progress > 0     ? '#f0b429' :
    '#30363d'

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative bg-[#161b22] border border-[#21262d] rounded-2xl overflow-hidden transition-all duration-300"
      style={{
        borderColor:    hovered ? '#30363d' : '#21262d',
        transform:      hovered ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow:      hovered ? '0 8px 32px rgba(0,0,0,0.4)' : 'none',
      }}
    >
      {/* Animated progress bar at top */}
      <div className="h-px w-full bg-[#21262d] overflow-hidden">
        <div
          className="h-full transition-all duration-1000 ease-out"
          style={{ width: `${barWidth}%`, backgroundColor: progressColor }}
        />
      </div>

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-[#e6edf3] leading-snug mb-1.5 line-clamp-1">
              {project.title}
            </h3>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full border font-mono ${status.color}`}>
                {status.label}
              </span>
              {project.target_role && (
                <span className="text-xs text-[#484f58] truncate max-w-24">
                  {project.target_role}
                </span>
              )}
              {project.purpose && PURPOSE_LABELS[project.purpose] && (
                <span className="text-xs font-mono text-[#30363d]">
                  {PURPOSE_LABELS[project.purpose]}
                </span>
              )}
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div
              className="text-xl font-bold font-mono transition-colors duration-300"
              style={{ color: progressColor }}
            >
              {progress}%
            </div>
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-[#484f58] leading-relaxed mb-4 line-clamp-2">
          {project.full_idea || project.description || 'No description'}
        </p>

        {/* Pipeline progress */}
        <div className="mb-4">
          <div className="flex items-center gap-0.5 mb-2">
            {getStages(project.purpose).map((stage, i) => {
              const stages2  = getStages(project.purpose)
              const stagePct = (i / stages2.length) * 100
              const isDone   = progress > stagePct + (100 / stages2.length)
              const isActive = progress >= stagePct && !isDone
              return (
                <div
                  key={stage.number}
                  title={stage.label}
                  className="flex-1 h-1 rounded-full transition-all duration-700"
                  style={{
                    backgroundColor: isDone ? '#3fb950' : isActive ? '#f0b429' : '#21262d',
                    transitionDelay:  `${i * 60}ms`,
                  }}
                />
              )
            })}
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[#30363d]">
              {activeStage?.icon}
              <span className="text-xs font-mono">{activeStage?.label}</span>
            </div>
            <div className="flex items-center gap-1 text-[#30363d]">
              <Clock size={10} />
              <span className="text-xs">{timeAgo(project.updated_at)}</span>
            </div>
          </div>
        </div>

        {/* Tech stack */}
        {project.tech_stack?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {project.tech_stack.slice(0, 3).map((tech, i) => (
              <span key={i}
                className="text-xs px-1.5 py-0.5 bg-[#0d1117] border border-[#21262d] text-[#484f58] rounded font-mono transition-colors hover:border-[#30363d] hover:text-[#8b949e]">
                {tech}
              </span>
            ))}
            {project.tech_stack.length > 3 && (
              <span className="text-xs px-1.5 py-0.5 bg-[#0d1117] border border-[#21262d] text-[#30363d] rounded font-mono">
                +{project.tech_stack.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        {!deleteConfirm ? (
          <div className="flex gap-2">
            {/* Resume — anchor tag */}
            <a
              href={`/?project=${project.id}`}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors text-xs group/btn"
            >
              Resume
              <ChevronRight size={12} className="group-hover/btn:translate-x-0.5 transition-transform" />
            </a>
            {/* View — anchor tag */}
            <a
              href={`/project/${project.id}`}
              className="flex items-center gap-1.5 px-3 py-2 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#484f58] rounded-lg transition-colors text-xs font-mono"
            >
              <ExternalLink size={11} />
              View
            </a>
            {/* Open in new tab */}
            <a
              href={`/project/${project.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center w-8 py-2 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#58a6ff] hover:border-[#58a6ff]/30 rounded-lg transition-colors"
              title="Open in new tab"
            >
              <ArrowUpRight size={12} />
            </a>
            {/* Delete */}
            <button
              onClick={() => setDeleteConfirm(true)}
              className="flex items-center justify-center w-8 py-2 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#f85149] hover:border-[#f85149]/30 rounded-lg transition-colors"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ) : (
          <div className="bg-[#2d1b1b] border border-[#f85149]/20 rounded-xl p-3">
            <p className="text-xs text-[#f85149] mb-2 leading-relaxed">
              Delete this project? All sessions and data will be removed.
            </p>
            <div className="flex gap-2">
              <button
                onClick={onDelete}
                className="flex-1 py-1.5 bg-[#f85149] text-white text-xs font-semibold rounded-lg hover:bg-[#e0403a] transition-colors"
              >
                Delete
              </button>
              <button
                onClick={() => setDeleteConfirm(false)}
                className="flex-1 py-1.5 bg-[#161b22] border border-[#30363d] text-[#484f58] text-xs rounded-lg hover:text-[#e6edf3] transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Time helper ───────────────────────────────────────────────────────────────

function timeAgo(dateStr: string) {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60)    return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [projects,     setProjects]     = useState<Project[]>([])
  const [filtered,     setFiltered]     = useState<Project[]>([])
  const [isLoading,    setIsLoading]    = useState(true)
  const [search,       setSearch]       = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [sortBy,       setSortBy]       = useState<'updated' | 'created' | 'progress'>('updated')
  const [mounted,      setMounted]      = useState(false)

  useEffect(() => {
    loadProjects()
    const t = setTimeout(() => setMounted(true), 100)
    return () => clearTimeout(t)
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
        p.target_role?.toLowerCase().includes(q) ||
        p.full_idea?.toLowerCase().includes(q) ||
        p.tech_stack?.some(t => t.toLowerCase().includes(q))
      )
    }
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
    try {
      const token = await getToken()
      await fetch(`http://localhost:8000/api/projects/${project.id}`, {
        method:  'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      loadProjects()
    } catch {
      alert('Delete failed. Please try again.')
    }
  }

  const stats = {
    total:       projects.length,
    active:      projects.filter(p => p.overall_status === 'in_progress').length,
    completed:   projects.filter(p => p.overall_status === 'completed').length,
    avgProgress: projects.length
      ? Math.round(projects.reduce((a, p) => a + (p.progress_percentage || 0), 0) / projects.length)
      : 0,
  }

  const FILTERS = [
    { id: 'all',         label: 'All',       count: projects.length,                                          icon: <LayoutGrid  size={11} /> },
    { id: 'in_progress', label: 'Active',    count: stats.active,                                             icon: <Activity    size={11} /> },
    { id: 'pending',     label: 'Pending',   count: projects.filter(p => p.overall_status === 'pending').length,   icon: <AlertCircle size={11} /> },
    { id: 'completed',   label: 'Completed', count: stats.completed,                                          icon: <CheckCircle2 size={11} /> },
  ]

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">

      {/* Header */}
      <div className="border-b border-[#21262d] sticky top-0 z-10 bg-[#0d1117]/95 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">

            {/* Left — nav */}
            <div className="flex items-center gap-4">
              <a
                href="/"
                className="flex items-center gap-1.5 text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors group"
              >
                <ChevronRight size={12} className="rotate-180 group-hover:-translate-x-0.5 transition-transform" />
                Home
              </a>
              <div className="w-px h-4 bg-[#21262d]" />
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
                  <span className="text-[#f0b429] text-xs font-bold">3</span>
                </div>
                <span className="text-sm font-semibold">
                  3Netra<span className="text-[#f0b429]">-AI</span>
                  <span className="text-[#484f58] font-normal ml-1.5 text-xs">/ Dashboard</span>
                </span>
              </div>
            </div>

            {/* Right — actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={loadProjects}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#161b22] border border-[#21262d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#30363d] rounded-lg transition-colors font-mono"
              >
                <Activity size={11} />
                Refresh
              </button>
              <a
                href="/"
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors"
              >
                <Plus size={12} />
                New Project
              </a>
            </div>
          </div>
        </div>
      </div>

      <div
        className="max-w-6xl mx-auto px-6 py-6 space-y-6 transition-all duration-500"
        style={{ opacity: mounted ? 1 : 0, transform: mounted ? 'none' : 'translateY(8px)' }}
      >

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total Projects', value: stats.total,       suffix: '',  color: '#e6edf3', icon: <LayoutGrid  size={16} />, border: '#30363d'       },
            { label: 'Active',         value: stats.active,      suffix: '',  color: '#f0b429', icon: <Activity    size={16} />, border: '#f0b429'       },
            { label: 'Completed',      value: stats.completed,   suffix: '',  color: '#3fb950', icon: <CheckCircle2 size={16} />, border: '#3fb950'      },
            { label: 'Avg Progress',   value: stats.avgProgress, suffix: '%', color: '#58a6ff', icon: <TrendingUp  size={16} />, border: '#58a6ff'       },
          ].map((stat, i) => (
            <div
              key={stat.label}
              className="bg-[#161b22] border border-[#21262d] rounded-xl p-4 transition-all duration-300 hover:border-[#30363d] group"
              style={{ transitionDelay: `${i * 60}ms` }}
            >
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                  style={{ backgroundColor: `${stat.color}15`, color: stat.color }}
                >
                  {stat.icon}
                </div>
                <div
                  className="w-1.5 h-1.5 rounded-full transition-all duration-300 group-hover:scale-125"
                  style={{ backgroundColor: stat.color }}
                />
              </div>
              <div
                className="text-2xl font-bold font-mono mb-0.5"
                style={{ color: stat.color }}
              >
                {isLoading ? '—' : <AnimatedNumber value={stat.value} suffix={stat.suffix} />}
              </div>
              <div className="text-xs text-[#484f58] font-mono">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 flex-wrap">

          {/* Search */}
          <div className="relative flex-1 min-w-52">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#484f58]" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search projects, roles, tech stack..."
              className="w-full bg-[#161b22] border border-[#21262d] rounded-lg pl-8 pr-8 py-2 text-xs text-[#e6edf3] placeholder-[#30363d] outline-none focus:border-[#30363d] transition-colors"
            />
            {search && (
              <button onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#e6edf3] transition-colors">
                <X size={11} />
              </button>
            )}
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-1 bg-[#161b22] border border-[#21262d] rounded-lg p-1">
            {FILTERS.map(f => (
              <button
                key={f.id}
                onClick={() => setActiveFilter(f.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-mono transition-all ${
                  activeFilter === f.id
                    ? 'bg-[#1c2333] text-[#e6edf3] shadow-sm'
                    : 'text-[#484f58] hover:text-[#8b949e]'
                }`}
              >
                <span className={activeFilter === f.id ? 'text-[#f0b429]' : ''}>
                  {f.icon}
                </span>
                {f.label}
                {f.count > 0 && (
                  <span className={`text-xs px-1 rounded ${
                    activeFilter === f.id
                      ? 'bg-[#f0b429]/20 text-[#f0b429]'
                      : 'text-[#30363d]'
                  }`}>
                    {f.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="relative">
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="appearance-none bg-[#161b22] border border-[#21262d] rounded-lg pl-3 pr-7 py-2 text-xs text-[#8b949e] outline-none font-mono cursor-pointer hover:border-[#30363d] transition-colors"
            >
              <option value="updated">Last updated</option>
              <option value="created">Date created</option>
              <option value="progress">Progress</option>
            </select>
            <ChevronRight size={10} className="absolute right-2 top-1/2 -translate-y-1/2 text-[#484f58] rotate-90 pointer-events-none" />
          </div>
        </div>

        {/* Project grid */}
        {isLoading ? (
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div
                key={i}
                className="h-64 bg-[#161b22] border border-[#21262d] rounded-2xl animate-pulse"
                style={{ animationDelay: `${i * 80}ms` }}
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#161b22] border border-[#21262d] flex items-center justify-center mb-4">
              <LayoutGrid size={24} className="text-[#30363d]" />
            </div>
            <p className="text-sm text-[#484f58] mb-1">
              {search ? 'No projects match your search' : 'No projects yet'}
            </p>
            <p className="text-xs text-[#30363d] mb-4">
              {search ? 'Try a different search term' : 'Start building your first project'}
            </p>
            {!search && (
              <a
                href="/"
                className="flex items-center gap-1.5 text-xs px-4 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors"
              >
                <Plus size={12} />
                New Project
              </a>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {filtered.map((project, i) => (
              <div
                key={project.id}
                className="transition-all duration-500"
                style={{
                  opacity:         mounted ? 1 : 0,
                  transform:       mounted ? 'none' : 'translateY(16px)',
                  transitionDelay: `${i * 50}ms`,
                }}
              >
                <ProjectCard
                  project={project}
                  onDelete={() => handleDelete(project)}
                />
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        {!isLoading && filtered.length > 0 && (
          <div className="flex items-center justify-between pt-2 border-t border-[#21262d]">
            <span className="text-xs text-[#30363d] font-mono">
              Showing {filtered.length} of {projects.length} projects
            </span>
            <div className="flex items-center gap-1.5 text-xs text-[#30363d]">
              <Cpu size={10} />
              <span className="font-mono">3Netra-AI</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}