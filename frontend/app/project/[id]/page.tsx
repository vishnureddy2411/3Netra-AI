'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

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
  verdict: any
  deep_analysis: any
}

interface Session {
  id: string
  stage_name: string
  stage_number: number
  session_number: number
  message_count: number
  status: string
  created_at: string
}

interface Stage {
  stage_number: number
  stage_name: string
  sessions: Session[]
}

interface GraphData {
  pages: any[]
  shared_components: any[]
  api_routes: any[]
  data_models: any[]
  tech_decisions: any
  navigation_structure: any
}

interface Diagram {
  diagram_type: string
  title: string
  mermaid_syntax: string
}

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const PIPELINE_STAGES = [
  { number: 6,  name: 'planning',  label: 'Planning',        icon: '📋', description: 'Research, expert council, architecture diagrams, project graph' },
  { number: 7,  name: 'quiz',      label: 'Quiz',            icon: '📚', description: 'Role-specific knowledge check and gap analysis' },
  { number: 8,  name: 'code_gen',  label: 'Code Generation', icon: '💻', description: 'Full project code generated from architecture graph' },
  { number: 9,  name: 'preview',   label: 'Live Preview',    icon: '👁',  description: 'Running application preview with screenshots' },
  { number: 10, name: 'career',    label: 'Career Output',   icon: '📄', description: 'Resume bullets, LinkedIn post, README, interview story' },
  { number: 11, name: 'qa',        label: 'QA + Testing',    icon: '🧪', description: 'Test suite generated and executed' },
  { number: 12, name: 'deploy',    label: 'Deploy',          icon: '🚀', description: 'Production deployment with monitoring' },
]

const STATUS_COLORS: Record<string, string> = {
  pending:     'bg-[#30363d] text-[#8b949e]',
  in_progress: 'bg-amber-400/20 text-amber-400',
  completed:   'bg-[#3fb950]/20 text-[#3fb950]',
  archived:    'bg-[#21262d] text-[#484f58]',
}

const DIAGRAM_LABELS: Record<string, string> = {
  system_architecture:     'System Architecture',
  database_schema:         'Database Schema',
  api_contracts:           'API Contracts',
  authentication_flow:     'Authentication Flow',
  deployment_architecture: 'Deployment Architecture',
}

function timeAgo(dateStr: string) {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60)    return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

// ─────────────────────────────────────────────
// MermaidRenderer — same logic as PreviewPanel
// ─────────────────────────────────────────────

function MermaidRenderer({ syntax, uid }: { syntax: string; uid: string }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || !syntax) return

    const render = async () => {
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
          themeVariables: {
            background:         '#0d1117',
            primaryColor:       '#1c2333',
            primaryTextColor:   '#e6edf3',
            primaryBorderColor: '#30363d',
            lineColor:          '#484f58',
            secondaryColor:     '#161b22',
            tertiaryColor:      '#21262d',
          },
        })
        const renderId = `mermaid-${uid}-${Date.now()}`
        const { svg } = await mermaid.render(renderId, syntax)
        if (containerRef.current) {
          containerRef.current.innerHTML = svg
          // Make SVG fill container width
          const svgEl = containerRef.current.querySelector('svg')
          if (svgEl) {
            svgEl.style.width  = '100%'
            svgEl.style.height = 'auto'
          }
        }
      } catch {
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <pre style="font-size:10px;color:#484f58;padding:16px;white-space:pre-wrap;overflow:auto;line-height:1.6;">${syntax}</pre>
          `
        }
      }
    }

    render()
  }, [syntax, uid])

  return (
    <div
      ref={containerRef}
      className="p-4 min-h-[200px] flex items-start justify-center bg-[#0d1117] overflow-auto"
    >
      <div className="text-xs text-[#30363d] font-mono animate-pulse">Rendering diagram...</div>
    </div>
  )
}

// ─────────────────────────────────────────────
// DiagramCard — renders SVG + code tab + download
// ─────────────────────────────────────────────

function DiagramCard({ diagram, index }: { diagram: Diagram; index: number }) {
  const [view,     setView]     = useState<'diagram' | 'code'>('diagram')
  const [expanded, setExpanded] = useState(true)

  const label = DIAGRAM_LABELS[diagram.diagram_type] || diagram.title || diagram.diagram_type

  const downloadSVG = () => {
    const svgEl = document.querySelector(`#diagram-container-${index} svg`) as SVGElement
    if (!svgEl) return
    const svgData = new XMLSerializer().serializeToString(svgEl)
    const blob    = new Blob([svgData], { type: 'image/svg+xml' })
    const url     = URL.createObjectURL(blob)
    const a       = document.createElement('a')
    a.href        = url
    a.download    = `${diagram.diagram_type}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadMd = () => {
    const content = `# ${label}\n\n\`\`\`mermaid\n${diagram.mermaid_syntax}\n\`\`\``
    const blob    = new Blob([content], { type: 'text/markdown' })
    const url     = URL.createObjectURL(blob)
    const a       = document.createElement('a')
    a.href        = url
    a.download    = `${diagram.diagram_type}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bg-[#161b22] border border-[#21262d] rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-left flex-1"
        >
          <span className="text-xs font-mono text-[#a371f7] bg-[#a371f7]/10 px-2 py-0.5 rounded">
            {diagram.diagram_type}
          </span>
          <span className="text-sm font-medium text-[#e6edf3]">{label}</span>
          <span className="text-xs text-[#30363d] ml-auto">{expanded ? '▲' : '▼'}</span>
        </button>

        {expanded && (
          <div className="flex items-center gap-2 ml-4">
            {/* View toggle */}
            <div className="flex bg-[#0d1117] border border-[#30363d] rounded-lg overflow-hidden">
              <button
                onClick={() => setView('diagram')}
                className={`text-xs px-2.5 py-1 transition-colors font-mono ${
                  view === 'diagram'
                    ? 'bg-[#f0b429] text-[#0d1117] font-semibold'
                    : 'text-[#484f58] hover:text-[#e6edf3]'
                }`}
              >
                Diagram
              </button>
              <button
                onClick={() => setView('code')}
                className={`text-xs px-2.5 py-1 transition-colors font-mono ${
                  view === 'code'
                    ? 'bg-[#f0b429] text-[#0d1117] font-semibold'
                    : 'text-[#484f58] hover:text-[#e6edf3]'
                }`}
              >
                Code
              </button>
            </div>
            {/* Downloads */}
            <button
              onClick={downloadSVG}
              className="text-xs px-2.5 py-1 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] rounded-lg transition-colors font-mono"
            >
              ↓ SVG
            </button>
            <button
              onClick={downloadMd}
              className="text-xs px-2.5 py-1 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] rounded-lg transition-colors font-mono"
            >
              ↓ .md
            </button>
          </div>
        )}
      </div>

      {/* Body */}
      {expanded && (
        <div id={`diagram-container-${index}`}>
          {view === 'diagram' ? (
            <MermaidRenderer
              syntax={diagram.mermaid_syntax}
              uid={`${index}-${diagram.diagram_type}`}
            />
          ) : (
            <pre className="p-4 text-xs text-[#8b949e] overflow-x-auto font-mono leading-relaxed bg-[#0d1117] max-h-80 overflow-y-auto">
              {diagram.mermaid_syntax}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// Download all diagrams
// ─────────────────────────────────────────────

function downloadAllDiagrams(diagrams: Diagram[], projectTitle: string) {
  const sections = diagrams.map(d => {
    const label = DIAGRAM_LABELS[d.diagram_type] || d.title || d.diagram_type
    return `## ${label}\n\n\`\`\`mermaid\n${d.mermaid_syntax}\n\`\`\``
  })
  const content = `# ${projectTitle} — Architecture Diagrams\n\n${sections.join('\n\n---\n\n')}`
  const blob    = new Blob([content], { type: 'text/markdown' })
  const url     = URL.createObjectURL(blob)
  const a       = document.createElement('a')
  a.href        = url
  a.download    = 'architecture-diagrams.md'
  a.click()
  URL.revokeObjectURL(url)
}

// ─────────────────────────────────────────────
// PipelineTimeline
// ─────────────────────────────────────────────

function PipelineTimeline({ project, stages }: { project: Project; stages: Stage[] }) {
  const currentStageNum = stages.length > 0
    ? Math.max(...stages.map(s => s.stage_number))
    : 6

  return (
    <div className="space-y-3">
      {PIPELINE_STAGES.map((stage, i) => {
        const stageData    = stages.find(s => s.stage_number === stage.number)
        const isCompleted  = stageData !== undefined
        const isActive     = stage.number === currentStageNum
        const isLocked     = stage.number > currentStageNum && !isCompleted
        const sessionCount = stageData?.sessions.length || 0

        return (
          <div key={stage.number} className="flex gap-4">
            <div className="flex flex-col items-center flex-shrink-0">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-base border-2 transition-all ${
                isCompleted ? 'bg-[#3fb950]/10 border-[#3fb950]/40 text-[#3fb950]'
                : isActive   ? 'bg-amber-400/10 border-amber-400/40 text-amber-400'
                : 'bg-[#161b22] border-[#21262d] text-[#30363d]'
              }`}>
                {isCompleted ? '✓' : stage.icon}
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <div className={`w-0.5 h-full min-h-[24px] mt-1 ${isCompleted ? 'bg-[#3fb950]/30' : 'bg-[#21262d]'}`} />
              )}
            </div>
            <div className={`flex-1 pb-4 ${isLocked ? 'opacity-40' : ''}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${
                    isCompleted ? 'text-[#e6edf3]' : isActive ? 'text-amber-400' : 'text-[#484f58]'
                  }`}>
                    Stage {stage.number} — {stage.label}
                  </span>
                  {isActive && (
                    <span className="text-xs px-2 py-0.5 bg-amber-400/10 text-amber-400 border border-amber-400/20 rounded-full">Current</span>
                  )}
                  {isLocked && (
                    <span className="text-xs px-2 py-0.5 bg-[#161b22] text-[#30363d] border border-[#21262d] rounded-full">Locked</span>
                  )}
                </div>
                {sessionCount > 0 && (
                  <span className="text-xs text-[#484f58] font-mono">{sessionCount} session{sessionCount !== 1 ? 's' : ''}</span>
                )}
              </div>
              <p className="text-xs text-[#484f58] leading-relaxed">{stage.description}</p>
              {stageData && stageData.sessions.length > 0 && (
                <div className="flex gap-1.5 mt-2 flex-wrap">
                  {stageData.sessions.map(session => (
                    <span key={session.id} className="text-xs px-2 py-0.5 bg-[#161b22] border border-[#21262d] text-[#484f58] rounded-lg font-mono">
                      Session {session.session_number} · {session.message_count}msg
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─────────────────────────────────────────────
// GraphViewer
// ─────────────────────────────────────────────

function GraphViewer({ graph }: { graph: GraphData }) {
  const [activeTab, setActiveTab] = useState<'pages' | 'components' | 'routes' | 'models'>('pages')

  const tabs = [
    { id: 'pages',      label: 'Pages',       count: graph.pages?.length || 0,             color: 'text-[#58a6ff]' },
    { id: 'components', label: 'Components',  count: graph.shared_components?.length || 0, color: 'text-[#a371f7]' },
    { id: 'routes',     label: 'API Routes',  count: graph.api_routes?.length || 0,         color: 'text-[#3fb950]' },
    { id: 'models',     label: 'Data Models', count: graph.data_models?.length || 0,        color: 'text-amber-400' },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {tabs.map(tab => (
          <button key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`bg-[#161b22] border rounded-xl p-3 text-center transition-all ${
              activeTab === tab.id ? 'border-[#58a6ff]/30 bg-[#1c2333]' : 'border-[#21262d] hover:border-[#30363d]'
            }`}>
            <div className={`text-2xl font-bold mb-0.5 ${tab.color}`}>{tab.count}</div>
            <div className="text-xs text-[#484f58] font-mono">{tab.label}</div>
          </button>
        ))}
      </div>

      <div className="bg-[#0d1117] border border-[#21262d] rounded-xl overflow-hidden">
        {activeTab === 'pages' && (
          <div className="divide-y divide-[#21262d]">
            {(graph.pages || []).map((page, i) => (
              <div key={i} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-[#e6edf3]">{page.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-[#58a6ff]">{page.path}</span>
                    {page.auth_required && <span className="text-xs px-1.5 py-0.5 bg-amber-400/10 text-amber-400 border border-amber-400/20 rounded font-mono">auth</span>}
                  </div>
                </div>
                <p className="text-xs text-[#484f58] mb-2">{page.description}</p>
                <div className="flex flex-wrap gap-1">
                  {(page.components || []).map((c: string, j: number) => (
                    <span key={j} className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] text-[#8b949e] rounded font-mono">{c}</span>
                  ))}
                </div>
                {(page.api_calls || []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {page.api_calls.map((call: string, j: number) => (
                      <span key={j} className="text-xs px-1.5 py-0.5 bg-[#3fb950]/5 border border-[#3fb950]/20 text-[#3fb950]/70 rounded font-mono">{call}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {(!graph.pages || graph.pages.length === 0) && <div className="px-4 py-8 text-center text-xs text-[#30363d]">No pages in graph</div>}
          </div>
        )}

        {activeTab === 'components' && (
          <div className="divide-y divide-[#21262d]">
            {(graph.shared_components || []).map((comp, i) => (
              <div key={i} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-[#a371f7]">{comp.name}</span>
                  <span className="text-xs text-[#484f58]">used by {(comp.used_by || []).length} page{(comp.used_by || []).length !== 1 ? 's' : ''}</span>
                </div>
                <p className="text-xs text-[#484f58] mb-2">{comp.description}</p>
                <div className="flex flex-wrap gap-1">
                  {(comp.used_by || []).map((page: string, j: number) => (
                    <span key={j} className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] text-[#8b949e] rounded font-mono">{page}</span>
                  ))}
                </div>
              </div>
            ))}
            {(!graph.shared_components || graph.shared_components.length === 0) && <div className="px-4 py-8 text-center text-xs text-[#30363d]">No components</div>}
          </div>
        )}

        {activeTab === 'routes' && (
          <div className="divide-y divide-[#21262d]">
            {(graph.api_routes || []).map((route, i) => (
              <div key={i} className="px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                    route.method === 'GET'    ? 'bg-[#58a6ff]/10 text-[#58a6ff]'
                    : route.method === 'POST'   ? 'bg-[#3fb950]/10 text-[#3fb950]'
                    : route.method === 'PUT'    ? 'bg-amber-400/10 text-amber-400'
                    : route.method === 'DELETE' ? 'bg-[#f85149]/10 text-[#f85149]'
                    : 'bg-[#a371f7]/10 text-[#a371f7]'
                  }`}>{route.method}</span>
                  <span className="text-sm font-mono text-[#e6edf3]">{route.path}</span>
                  {route.auth_required && <span className="text-xs px-1.5 py-0.5 bg-amber-400/10 text-amber-400 border border-amber-400/20 rounded font-mono ml-auto">auth</span>}
                </div>
                <p className="text-xs text-[#484f58] mb-1">{route.description}</p>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {route.input  && <div className="text-xs"><span className="text-[#30363d] font-mono">Input: </span><span className="text-[#8b949e]">{route.input}</span></div>}
                  {route.output && <div className="text-xs"><span className="text-[#30363d] font-mono">Output: </span><span className="text-[#8b949e]">{route.output}</span></div>}
                </div>
              </div>
            ))}
            {(!graph.api_routes || graph.api_routes.length === 0) && <div className="px-4 py-8 text-center text-xs text-[#30363d]">No API routes</div>}
          </div>
        )}

        {activeTab === 'models' && (
          <div className="divide-y divide-[#21262d]">
            {(graph.data_models || []).map((model, i) => (
              <div key={i} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-amber-400">{model.name}</span>
                  <span className="text-xs font-mono text-[#484f58]">{model.table}</span>
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  {(model.key_fields || []).map((field: string, j: number) => (
                    <span key={j} className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] text-[#8b949e] rounded font-mono">{field}</span>
                  ))}
                </div>
                {(model.relationships || []).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {model.relationships.map((rel: string, j: number) => (
                      <span key={j} className="text-xs px-1.5 py-0.5 bg-amber-400/5 border border-amber-400/20 text-amber-400/70 rounded font-mono">{rel}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {(!graph.data_models || graph.data_models.length === 0) && <div className="px-4 py-8 text-center text-xs text-[#30363d]">No data models</div>}
          </div>
        )}
      </div>

      {graph.tech_decisions && (
        <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-4">
          <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">Tech Decisions</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(graph.tech_decisions).map(([key, value]) => (
              typeof value === 'string' && (
                <div key={key}>
                  <div className="text-xs text-[#30363d] font-mono mb-0.5 capitalize">{key}</div>
                  <div className="text-xs text-[#8b949e]">{value as string}</div>
                </div>
              )
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────

export default function ProjectPage() {
  const params = useParams()
  const router = useRouter()
  const id     = params?.id as string

  const [project,   setProject]   = useState<Project | null>(null)
  const [stages,    setStages]    = useState<Stage[]>([])
  const [graph,     setGraph]     = useState<GraphData | null>(null)
  const [diagrams,  setDiagrams]  = useState<Diagram[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'architecture' | 'sessions' | 'manage'>('overview')
  const [isLoading, setIsLoading] = useState(true)
  const [error,     setError]     = useState<string | null>(null)

  useEffect(() => { if (id) loadProject() }, [id])

  const getToken = async () => {
    const { getSession } = await import('../../../lib/auth')
    const session = await getSession()
    return session?.access_token || ''
  }

  const loadProject = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const token = await getToken()

      const pRes = await fetch(`http://localhost:8000/api/projects/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!pRes.ok) throw new Error('Project not found')
      setProject((await pRes.json()).project)

      const sRes = await fetch(`http://localhost:8000/api/projects/${id}/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (sRes.ok) setStages((await sRes.json()).stages || [])

      const aRes = await fetch(`http://localhost:8000/api/projects/${id}/artifacts`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (aRes.ok) {
        const aData = await aRes.json()
        if (aData.artifacts?.project_graph) setGraph(aData.artifacts.project_graph.content)
        if (aData.artifacts?.diagrams)      setDiagrams(aData.artifacts.diagrams.content || [])
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load project')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Delete "${project?.title}"? This cannot be undone.`)) return
    try {
      const token = await getToken()
      await fetch(`http://localhost:8000/api/projects/${id}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      })
      router.push('/')
    } catch { alert('Delete failed.') }
  }

  const handleArchive = async () => {
    if (!confirm('Archive this project?')) return
    try {
      const token = await getToken()
      await fetch(`http://localhost:8000/api/projects/${id}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ overall_status: 'archived' }),
      })
      loadProject()
    } catch { alert('Archive failed.') }
  }

  if (isLoading) return (
    <div className="flex items-center justify-center h-screen bg-[#0d1117]">
      <div className="text-center">
        <div className="flex gap-1 justify-center mb-3">
          {[0,1,2].map(i => <div key={i} style={{ animationDelay: `${i*0.2}s` }} className="w-2 h-2 rounded-full bg-[#f0b429] animate-pulse" />)}
        </div>
        <p className="text-xs text-[#484f58] font-mono">Loading project...</p>
      </div>
    </div>
  )

  if (error || !project) return (
    <div className="flex items-center justify-center h-screen bg-[#0d1117]">
      <div className="text-center">
        <p className="text-sm text-[#f85149] mb-4">{error || 'Project not found'}</p>
        <button onClick={() => router.push('/')} className="text-xs px-4 py-2 bg-[#161b22] border border-[#30363d] text-[#8b949e] rounded-lg hover:text-[#e6edf3] transition-colors">← Back</button>
      </div>
    </div>
  )

  const TABS = [
    { id: 'overview',     label: 'Overview',     icon: '📊' },
    { id: 'architecture', label: 'Architecture', icon: '🏗️' },
    { id: 'sessions',     label: 'Sessions',     icon: '💬' },
    { id: 'manage',       label: 'Manage',       icon: '⚙️' },
  ]

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <div className="border-b border-[#21262d] bg-[#0d1117]/95 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={() => router.push('/')} className="text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors">← Back</button>
              <div className="w-px h-4 bg-[#21262d]" />
              <div>
                <h1 className="text-sm font-semibold text-[#e6edf3] truncate max-w-md">{project.title}</h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${STATUS_COLORS[project.overall_status] || STATUS_COLORS.pending}`}>
                    {project.overall_status}
                  </span>
                  <span className="text-xs text-[#484f58]">{project.target_role}</span>
                  <span className="text-xs text-[#30363d]">·</span>
                  <span className="text-xs text-[#484f58] capitalize">{project.purpose}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-24 bg-[#21262d] rounded-full h-1.5">
                  <div className={`h-1.5 rounded-full transition-all ${
                    project.progress_percentage === 100 ? 'bg-[#3fb950]' : project.progress_percentage >= 50 ? 'bg-[#58a6ff]' : 'bg-amber-400'
                  }`} style={{ width: `${project.progress_percentage || 0}%` }} />
                </div>
                <span className="text-xs text-[#484f58] font-mono">{project.progress_percentage || 0}%</span>
              </div>
              <button onClick={() => router.push(`/?project=${project.id}`)}
                className="text-xs px-3 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors">
                Resume →
              </button>
            </div>
          </div>
          <div className="flex gap-1 mt-4">
            {TABS.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                  activeTab === tab.id
                    ? 'bg-[#1c2333] text-[#e6edf3] border border-[#30363d]'
                    : 'text-[#484f58] hover:text-[#8b949e] hover:bg-[#161b22]'
                }`}>
                <span>{tab.icon}</span>{tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6">

        {/* Overview */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-2 space-y-6">
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-5">
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">Project</div>
                <p className="text-sm text-[#8b949e] leading-relaxed mb-4">{project.full_idea || project.description}</p>
                {project.tech_stack && project.tech_stack.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {project.tech_stack.map((tech, i) => (
                      <span key={i} className="text-xs px-2 py-1 bg-[#0d1117] border border-[#21262d] text-[#8b949e] rounded-lg font-mono">{tech}</span>
                    ))}
                  </div>
                )}
              </div>
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-5">
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-4">Pipeline</div>
                <PipelineTimeline project={project} stages={stages} />
              </div>
            </div>
            <div className="space-y-4">
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-4">
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">Stats</div>
                <div className="space-y-3">
                  {[
                    ['Sessions',    stages.reduce((acc, s) => acc + s.sessions.length, 0)],
                    ['Stages done', `${stages.length}/${PIPELINE_STAGES.length}`],
                    ['Diagrams',    diagrams.length],
                    ['Created',     timeAgo(project.created_at)],
                    ['Last active', timeAgo(project.updated_at)],
                  ].map(([label, value]) => (
                    <div key={label as string} className="flex justify-between">
                      <span className="text-xs text-[#484f58]">{label}</span>
                      <span className="text-xs text-[#e6edf3] font-mono">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              {project.verdict && (
                <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-4">
                  <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">Council Verdict</div>
                  <div className={`text-sm font-semibold mb-2 ${
                    project.verdict.verdict === 'BUILD' ? 'text-[#3fb950]' : project.verdict.verdict === 'REDESIGN' ? 'text-amber-400' : 'text-[#f85149]'
                  }`}>{project.verdict.verdict}</div>
                  <p className="text-xs text-[#484f58] leading-relaxed mb-3">
                    {project.verdict.verdict_reasoning?.slice(0, 200)}{project.verdict.verdict_reasoning?.length > 200 ? '...' : ''}
                  </p>
                  {project.verdict.confidence_score && (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-[#21262d] rounded-full h-1">
                        <div className="h-1 rounded-full bg-[#58a6ff]" style={{ width: `${project.verdict.confidence_score}%` }} />
                      </div>
                      <span className="text-xs text-[#484f58] font-mono">{project.verdict.confidence_score}%</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Architecture */}
        {activeTab === 'architecture' && (
          <div className="space-y-8">

            {/* Diagrams */}
            {diagrams.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest">
                    Architecture Diagrams — {diagrams.length} blueprints
                  </div>
                  <button
                    onClick={() => downloadAllDiagrams(diagrams, project.title)}
                    className="text-xs px-3 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors"
                  >
                    ↓ Download All
                  </button>
                </div>
                <div className="space-y-4">
                  {diagrams.map((diagram, i) => (
                    <DiagramCard key={i} diagram={diagram} index={i} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-8 text-center">
                <div className="text-3xl mb-3">📐</div>
                <p className="text-sm text-[#484f58] mb-1">No diagrams generated yet</p>
                <p className="text-xs text-[#30363d]">Complete the planning stage to generate architecture diagrams</p>
                <button onClick={() => router.push(`/?project=${project.id}`)}
                  className="mt-4 text-xs px-4 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors">
                  Go to Planning →
                </button>
              </div>
            )}

            {/* Divider */}
            {diagrams.length > 0 && graph && (
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-[#21262d]" />
                <span className="text-xs font-mono text-[#30363d] uppercase tracking-widest">Project Graph</span>
                <div className="flex-1 h-px bg-[#21262d]" />
              </div>
            )}

            {/* Graph */}
            {graph ? (
              <GraphViewer graph={graph} />
            ) : (
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-8 text-center">
                <div className="text-3xl mb-3">🏗️</div>
                <p className="text-sm text-[#484f58] mb-1">Architecture graph not generated yet</p>
                <p className="text-xs text-[#30363d]">Complete the planning stage to generate the project graph</p>
                <button onClick={() => router.push(`/?project=${project.id}`)}
                  className="mt-4 text-xs px-4 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors">
                  Go to Planning →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Sessions */}
        {activeTab === 'sessions' && (
          <div className="space-y-4">
            {stages.length === 0 ? (
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-12 text-center">
                <div className="text-4xl mb-4">💬</div>
                <p className="text-sm text-[#484f58]">No sessions yet</p>
              </div>
            ) : (
              stages.map(stage => (
                <div key={stage.stage_number} className="bg-[#161b22] border border-[#21262d] rounded-xl overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#21262d] flex items-center gap-2">
                    <span className="text-sm">{PIPELINE_STAGES.find(p => p.number === stage.stage_number)?.icon || '💬'}</span>
                    <span className="text-sm font-medium text-[#e6edf3]">
                      Stage {stage.stage_number} — {PIPELINE_STAGES.find(p => p.number === stage.stage_number)?.label || stage.stage_name}
                    </span>
                    <span className="text-xs text-[#484f58] ml-auto font-mono">{stage.sessions.length} session{stage.sessions.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="divide-y divide-[#21262d]">
                    {stage.sessions.map(session => (
                      <div key={session.id}
                        className="px-4 py-3 flex items-center justify-between hover:bg-[#0d1117] transition-colors cursor-pointer"
                        onClick={() => router.push(`/?project=${project.id}&session=${session.id}`)}>
                        <div className="flex items-center gap-3">
                          {session.status === 'active' && <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950]" />}
                          <div>
                            <div className="text-xs font-medium text-[#e6edf3]">Session {session.session_number}</div>
                            <div className="text-xs text-[#484f58]">{timeAgo(session.created_at)} · {session.message_count} messages</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded font-mono ${session.status === 'active' ? 'bg-[#3fb950]/10 text-[#3fb950]' : 'bg-[#21262d] text-[#484f58]'}`}>
                            {session.status}
                          </span>
                          <span className="text-[#484f58] text-xs">→</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Manage */}
        {activeTab === 'manage' && (
          <div className="max-w-xl space-y-4">
            <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-5">
              <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-4">Project Details</div>
              <div className="space-y-3">
                {[
                  ['Title',      project.title],
                  ['Role',       project.target_role],
                  ['Purpose',    project.purpose],
                  ['Project ID', project.id],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="text-xs text-[#484f58] mb-1">{label}</div>
                    <div className={`text-sm text-[#e6edf3] ${label === 'Project ID' ? 'text-xs font-mono text-[#484f58]' : ''}`}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-5">
              <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-4">Actions</div>
              <div className="space-y-3">
                <button onClick={() => router.push(`/?project=${project.id}`)}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-[#0d1117] border border-[#30363d] rounded-lg hover:border-[#484f58] transition-colors text-left">
                  <span>▶️</span>
                  <div><div className="text-sm text-[#e6edf3]">Resume Project</div><div className="text-xs text-[#484f58]">Continue where you left off</div></div>
                </button>
                <button onClick={handleArchive}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-[#0d1117] border border-[#30363d] rounded-lg hover:border-[#484f58] transition-colors text-left">
                  <span>📦</span>
                  <div><div className="text-sm text-[#e6edf3]">Archive Project</div><div className="text-xs text-[#484f58]">Hide from active projects</div></div>
                </button>
              </div>
            </div>
            <div className="bg-[#2d1b1b] border border-[#f85149]/20 rounded-xl p-5">
              <div className="text-xs font-mono text-[#f85149] uppercase tracking-widest mb-4">Danger Zone</div>
              <button onClick={handleDelete}
                className="w-full flex items-center gap-3 px-4 py-3 bg-[#0d1117] border border-[#f85149]/20 rounded-lg hover:bg-[#f85149]/5 transition-colors text-left">
                <span>🗑️</span>
                <div><div className="text-sm text-[#f85149]">Delete Project</div><div className="text-xs text-[#484f58]">Permanently delete all data. Cannot be undone.</div></div>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}