// ─────────────────────────────────────────────
// Diagrams Card — renders Mermaid.js diagrams
// ─────────────────────────────────────────────

'use client'

import { useState, useRef, useEffect } from 'react'
import type { Diagram } from '../../lib/types'

interface Props {
  diagrams: Diagram[]
}

export default function DiagramsCard({ diagrams }: Props) {
  const [activeIdx, setActiveIdx] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || !diagrams[activeIdx]) return
    const render = async () => {
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
          themeVariables: {
            background: '#0d1117',
            primaryColor: '#1c2333',
            primaryTextColor: '#e6edf3',
            primaryBorderColor: '#30363d',
            lineColor: '#484f58',
            secondaryColor: '#161b22',
            tertiaryColor: '#21262d',
          },
        })
        const id = `mermaid-${activeIdx}-${Date.now()}`
        const { svg } = await mermaid.render(id, diagrams[activeIdx].mermaid_syntax)
        if (containerRef.current) containerRef.current.innerHTML = svg
      } catch {
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <pre style="font-size:10px;color:#484f58;padding:16px;white-space:pre-wrap;overflow:auto;background:#0d1117;border-radius:8px">${diagrams[activeIdx]?.mermaid_syntax}</pre>
          `
        }
      }
    }
    render()
  }, [activeIdx, diagrams])

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
        <div>
          <div className="text-xs font-mono text-[#a371f7] uppercase tracking-widest mb-0.5">
            Architecture Diagrams
          </div>
          <div className="text-xs text-[#484f58]">
            {diagrams.length} blueprints · click tabs to switch
          </div>
        </div>
        <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950]" />
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-[#21262d] px-3 py-2 gap-1.5 bg-[#0d1117]">
        {diagrams.map((d, i) => (
          <button
            key={i}
            onClick={() => setActiveIdx(i)}
            className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors font-mono ${
              i === activeIdx
                ? 'bg-[#f0b429] text-[#0d1117] font-semibold'
                : 'bg-[#161b22] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e]'
            }`}
          >
            {d.title}
          </button>
        ))}
      </div>

      {/* Diagram */}
      <div
        ref={containerRef}
        className="p-4 min-h-48 flex items-center justify-center overflow-auto bg-[#0d1117]"
        style={{ maxHeight: '400px' }}
      >
        <div className="text-xs text-[#30363d] font-mono">Rendering diagram...</div>
      </div>
    </div>
  )
}