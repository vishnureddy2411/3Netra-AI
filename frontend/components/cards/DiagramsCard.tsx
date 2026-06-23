'use client'

import type { Diagram } from '../../lib/types'

interface Props {
  diagrams: Diagram[]
  onOpenPreview?: (diagrams: Diagram[], activeIndex: number) => void
}

export default function DiagramsCard({ diagrams, onOpenPreview }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#a371f7]/10 border border-[#a371f7]/20 flex items-center justify-center">
            <span className="text-sm">📐</span>
          </div>
          <div>
            <div className="text-sm font-medium text-[#e6edf3]">
              Architecture Diagrams
            </div>
            <div className="text-xs text-[#484f58]">
              {diagrams.length} blueprints generated
            </div>
          </div>
        </div>
        {onOpenPreview && (
          <button
            onClick={() => onOpenPreview(diagrams, 0)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#a371f7]/10 border border-[#a371f7]/20 text-[#a371f7] hover:bg-[#a371f7]/20 rounded-lg transition-colors font-mono"
          >
            Open Preview →
          </button>
        )}
      </div>

      {/* Diagram tabs preview */}
      <div className="px-4 pb-4">
        <div className="flex flex-wrap gap-1.5">
          {diagrams.map((d, i) => (
            <button
              key={i}
              onClick={() => onOpenPreview?.(diagrams, i)}
              className="text-xs px-2.5 py-1 bg-[#0d1117] border border-[#21262d] rounded-lg text-[#484f58] hover:text-[#e6edf3] hover:border-[#30363d] transition-colors font-mono"
            >
              {d.title}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}