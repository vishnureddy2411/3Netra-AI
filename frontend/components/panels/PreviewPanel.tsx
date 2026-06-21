// ─────────────────────────────────────────────
// Preview Panel
// Opens on right side when user clicks diagram
// or any downloadable content.
// Closes with X button or clicking backdrop.
// ─────────────────────────────────────────────

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

type PreviewContent = DiagramPreview | DownloadPreview

interface Props {
  content: PreviewContent | null
  onClose: () => void
}

export default function PreviewPanel({ content, onClose }: Props) {
  const [activeIdx,   setActiveIdx]   = useState(0)
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
            background:        '#0d1117',
            primaryColor:      '#1c2333',
            primaryTextColor:  '#e6edf3',
            primaryBorderColor:'#30363d',
            lineColor:         '#484f58',
            secondaryColor:    '#161b22',
            tertiaryColor:     '#21262d',
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

  // Close on Escape
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

  return (
    <>
      {/* Backdrop — click to close */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-[480px] bg-[#161b22] border-l border-[#30363d] z-50 flex flex-col shadow-2xl">

        {/* Panel header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
          <div>
            <div className="text-xs font-mono text-[#a371f7] uppercase tracking-widest mb-0.5">
              {content.type === 'diagrams' ? 'Architecture Diagrams' : 'Preview'}
            </div>
            <div className="text-xs text-[#484f58]">
              {content.type === 'diagrams'
                ? `${content.diagrams.length} blueprints`
                : content.label
              }
            </div>
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
          {content.type === 'diagrams' ? (
            <div
              ref={containerRef}
              className="p-4 min-h-full flex items-start justify-center"
            >
              <div className="text-xs text-[#30363d] font-mono">Rendering...</div>
            </div>
          ) : (
            <div className="p-4">
              {/* Download preview */}
              <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 mb-4">
                <div className="text-sm font-medium text-[#e6edf3] mb-1">
                  {content.filename}
                </div>
                <div className="text-xs text-[#484f58] mb-3">
                  {content.mimeType}
                </div>
                <button onClick={handleDownloadFile}
                  className="w-full py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors text-sm">
                  ↓ Download {content.filename}
                </button>
              </div>
              {/* Content preview */}
              <div className="bg-[#0d1117] border border-[#21262d] rounded-lg p-4">
                <div className="text-xs font-mono text-[#484f58] mb-2 uppercase tracking-widest">
                  Preview
                </div>
                <pre className="text-xs text-[#8b949e] whitespace-pre-wrap leading-relaxed overflow-auto max-h-96">
                  {content.content.slice(0, 2000)}
                  {content.content.length > 2000 ? '\n\n... (truncated)' : ''}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Keyboard hint */}
        <div className="px-4 py-2 border-t border-[#21262d] bg-[#0d1117]">
          <p className="text-xs text-[#30363d] font-mono">Press Esc to close</p>
        </div>
      </div>
    </>
  )
}