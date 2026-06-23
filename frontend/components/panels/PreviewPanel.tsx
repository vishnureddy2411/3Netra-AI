'use client'

import { useState, useEffect, useRef } from 'react'
import type { Diagram } from '../../lib/types'

interface DiagramPreview {
  type: 'diagrams'
  diagrams: Diagram[]
  activeIndex?: number
}

interface DownloadPreview {
  type: 'download'
  filename: string
  content: string
  mimeType: string
  label: string
}

interface GraphPreview {
  type: 'graph'
  summary: {
    total_pages: number
    total_components: number
    total_api_routes: number
    total_data_models?: number
  }
  graph?: any
}

type PreviewContent = DiagramPreview | DownloadPreview | GraphPreview

interface Props {
  content: PreviewContent | null
  onClose: () => void
}

export default function PreviewPanel({ content, onClose }: Props) {
 const [activeIdx,   setActiveIdx]   = useState(0)
  const [graphTab,    setGraphTab]    = useState<'pages' | 'components' | 'routes' | 'models'>('pages')
  const containerRef                  = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (content?.type === 'diagrams') {
      setActiveIdx(content.activeIndex || 0)
    }
  }, [content])

  useEffect(() => {
    if (content?.type !== 'diagrams' || !containerRef.current) return
    const diagram = content.diagrams[activeIdx]
    if (!diagram) return

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
        const id = `preview-mermaid-${activeIdx}-${Date.now()}`
        const { svg } = await mermaid.render(id, diagram.mermaid_syntax)
        if (containerRef.current) containerRef.current.innerHTML = svg
      } catch {
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <pre style="font-size:10px;color:#484f58;padding:16px;white-space:pre-wrap;overflow:auto;">${diagram.mermaid_syntax}</pre>
          `
        }
      }
    }
    render()
  }, [activeIdx, content])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  if (!content) return null

  const handleDownloadSVG = () => {
    if (content.type !== 'diagrams') return
    const svgEl = containerRef.current?.querySelector('svg')
    if (!svgEl) return
    const svgData = new XMLSerializer().serializeToString(svgEl)
    const blob    = new Blob([svgData], { type: 'image/svg+xml' })
    const url     = URL.createObjectURL(blob)
    const a       = document.createElement('a')
    a.href        = url
    a.download    = `${content.diagrams[activeIdx]?.title || 'diagram'}.svg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleDownloadAll = () => {
    if (content.type !== 'diagrams') return
    const allContent = content.diagrams.map(d =>
      `# ${d.title}\n\n\`\`\`mermaid\n${d.mermaid_syntax}\n\`\`\``
    ).join('\n\n---\n\n')
    const blob = new Blob([allContent], { type: 'text/markdown' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = 'all-diagrams.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleDownloadFile = () => {
    if (content.type !== 'download') return
    const blob = new Blob([content.content], { type: content.mimeType })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = content.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getTitle = () => {
    if (content.type === 'diagrams') return 'Architecture Diagrams'
    if (content.type === 'graph')    return 'Project Graph'
    return 'Preview'
  }

  const getSubtitle = () => {
    if (content.type === 'diagrams') return `${content.diagrams.length} blueprints`
    if (content.type === 'graph')    return `${content.summary.total_pages} pages · ${content.summary.total_api_routes} routes`
    if (content.type === 'download') return content.label
    return ''
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-[480px] bg-[#161b22] border-l border-[#30363d] z-50 flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
          <div>
            <div className="text-xs font-mono text-[#a371f7] uppercase tracking-widest mb-0.5">
              {getTitle()}
            </div>
            <div className="text-xs text-[#484f58]">{getSubtitle()}</div>
          </div>
          <div className="flex items-center gap-2">
            {content.type === 'diagrams' && (
              <>
                <button onClick={handleDownloadSVG}
                  className="text-xs px-2.5 py-1.5 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] rounded-lg transition-colors font-mono">
                  ↓ SVG
                </button>
                <button onClick={handleDownloadAll}
                  className="text-xs px-2.5 py-1.5 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] rounded-lg transition-colors font-mono">
                  ↓ All
                </button>
              </>
            )}
            {content.type === 'download' && (
              <button onClick={handleDownloadFile}
                className="text-xs px-2.5 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors">
                ↓ Download
              </button>
            )}
            <button onClick={onClose}
              className="w-7 h-7 flex items-center justify-center text-[#484f58] hover:text-[#e6edf3] hover:bg-[#21262d] rounded-lg transition-colors text-sm">
              ✕
            </button>
          </div>
        </div>

        {/* Diagram tabs */}
        {content.type === 'diagrams' && (
          <div className="flex overflow-x-auto border-b border-[#21262d] px-3 py-2 gap-1.5 bg-[#0d1117] flex-shrink-0">
            {content.diagrams.map((d, i) => (
              <button key={i} onClick={() => setActiveIdx(i)}
                className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors font-mono ${
                  i === activeIdx
                    ? 'bg-[#f0b429] text-[#0d1117] font-semibold'
                    : 'bg-[#161b22] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3]'
                }`}>
                {d.title}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto bg-[#0d1117]">

          {/* Diagrams */}
          {content.type === 'diagrams' && (
            <div ref={containerRef} className="p-4 min-h-full flex items-start justify-center">
              <div className="text-xs text-[#30363d] font-mono">Rendering...</div>
            </div>
          )}

          {/* Graph */}
          {content.type === 'graph' && (
            <div className="p-4 space-y-4">
              {/* Stats */}
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: 'Pages',      value: content.summary.total_pages,        icon: '📄', color: 'text-[#58a6ff]', tab: 'pages'      },
                  { label: 'Components', value: content.summary.total_components,   icon: '🧩', color: 'text-[#a371f7]', tab: 'components' },
                  { label: 'Routes',     value: content.summary.total_api_routes,   icon: '🔌', color: 'text-[#3fb950]', tab: 'routes'     },
                  { label: 'Models',     value: content.summary.total_data_models || 0, icon: '🗄️', color: 'text-amber-400', tab: 'models' },
                ].map(item => (
                  <button
                    key={item.label}
                    onClick={() => setGraphTab(item.tab as any)}
                    className={`bg-[#161b22] border rounded-xl p-3 text-center transition-all ${
                      graphTab === item.tab
                        ? 'border-[#58a6ff]/30 bg-[#1c2333]'
                        : 'border-[#30363d] hover:border-[#484f58]'
                    }`}
                  >
                    <div className="text-lg mb-0.5">{item.icon}</div>
                    <div className={`text-xl font-bold mb-0.5 ${item.color}`}>{item.value}</div>
                    <div className="text-xs text-[#484f58] font-mono">{item.label}</div>
                  </button>
                ))}
              </div>

              {/* Detail list */}
              {content.graph && (
                <div className="bg-[#0d1117] border border-[#21262d] rounded-xl overflow-hidden max-h-96 overflow-y-auto">
                  {graphTab === 'pages' && (
                    <div className="divide-y divide-[#21262d]">
                      {(content.graph.pages || []).map((page: any, i: number) => (
                        <div key={i} className="px-4 py-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-[#e6edf3]">{page.name}</span>
                            <span className="text-xs font-mono text-[#58a6ff]">{page.path}</span>
                          </div>
                          <p className="text-xs text-[#484f58] mb-1.5">{page.description}</p>
                          <div className="flex flex-wrap gap-1">
                            {(page.components || []).map((c: string, j: number) => (
                              <span key={j} className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] text-[#8b949e] rounded font-mono">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                      {(!content.graph.pages || content.graph.pages.length === 0) && (
                        <div className="px-4 py-6 text-center text-xs text-[#30363d]">No pages</div>
                      )}
                    </div>
                  )}

                  {graphTab === 'components' && (
                    <div className="divide-y divide-[#21262d]">
                      {(content.graph.shared_components || []).map((comp: any, i: number) => (
                        <div key={i} className="px-4 py-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-[#a371f7]">{comp.name}</span>
                            <span className="text-xs text-[#484f58]">
                              {(comp.used_by || []).length} pages
                            </span>
                          </div>
                          <p className="text-xs text-[#484f58] mb-1.5">{comp.description}</p>
                          <div className="flex flex-wrap gap-1">
                            {(comp.used_by || []).map((page: string, j: number) => (
                              <span key={j} className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] text-[#8b949e] rounded font-mono">
                                {page}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {graphTab === 'routes' && (
                    <div className="divide-y divide-[#21262d]">
                      {(content.graph.api_routes || []).map((route: any, i: number) => (
                        <div key={i} className="px-4 py-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                              route.method === 'GET'    ? 'bg-[#58a6ff]/10 text-[#58a6ff]'
                              : route.method === 'POST'   ? 'bg-[#3fb950]/10 text-[#3fb950]'
                              : route.method === 'PUT'    ? 'bg-amber-400/10 text-amber-400'
                              : route.method === 'DELETE' ? 'bg-[#f85149]/10 text-[#f85149]'
                              : 'bg-[#a371f7]/10 text-[#a371f7]'
                            }`}>
                              {route.method}
                            </span>
                            <span className="text-xs font-mono text-[#e6edf3]">{route.path}</span>
                            {route.auth_required && (
                              <span className="text-xs px-1 py-0.5 bg-amber-400/10 text-amber-400 rounded font-mono ml-auto">
                                auth
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-[#484f58]">{route.description}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {graphTab === 'models' && (
                    <div className="divide-y divide-[#21262d]">
                      {(content.graph.data_models || []).map((model: any, i: number) => (
                        <div key={i} className="px-4 py-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-amber-400">{model.name}</span>
                            <span className="text-xs font-mono text-[#484f58]">{model.table}</span>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {(model.key_fields || []).map((field: string, j: number) => (
                              <span key={j} className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] text-[#8b949e] rounded font-mono">
                                {field}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {!content.graph && (
                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4">
                  <p className="text-xs text-[#8b949e] leading-relaxed text-center">
                    {content.summary.total_pages} pages · {content.summary.total_api_routes} routes · {content.summary.total_components} components
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Download */}
          {content.type === 'download' && (
            <div className="p-4">
              <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 mb-4">
                <div className="text-sm font-medium text-[#e6edf3] mb-1">{content.filename}</div>
                <div className="text-xs text-[#484f58] mb-3">{content.mimeType}</div>
                <button onClick={handleDownloadFile}
                  className="w-full py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors text-sm">
                  ↓ Download {content.filename}
                </button>
              </div>
              <div className="bg-[#0d1117] border border-[#21262d] rounded-lg p-4">
                <div className="text-xs font-mono text-[#484f58] mb-2 uppercase tracking-widest">Preview</div>
                <pre className="text-xs text-[#8b949e] whitespace-pre-wrap leading-relaxed overflow-auto max-h-96">
                  {content.content.slice(0, 2000)}
                  {content.content.length > 2000 ? '\n\n... (truncated)' : ''}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[#21262d] bg-[#0d1117]">
          <p className="text-xs text-[#30363d] font-mono">Press Esc to close</p>
        </div>
      </div>
    </>
  )
}