'use client'

import type { GraphSummary } from '../../lib/types'

interface Props {
  summary: GraphSummary
  elapsed: number
  onOpenPreview?: (graph: GraphSummary) => void
}

export default function GraphCard({ summary, elapsed, onOpenPreview }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#3fb950]/10 border border-[#3fb950]/20 flex items-center justify-center">
            <span className="text-sm">🔗</span>
          </div>
          <div>
            <div className="text-sm font-medium text-[#e6edf3]">
              Project Graph
            </div>
            <div className="text-xs text-[#484f58]">
              All navigation pre-wired · {elapsed}s
            </div>
          </div>
        </div>
        {onOpenPreview && (
          <button
            onClick={() => onOpenPreview(summary)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#3fb950]/10 border border-[#3fb950]/20 text-[#3fb950] hover:bg-[#3fb950]/20 rounded-lg transition-colors font-mono"
          >
            Open Preview →
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-px bg-[#21262d] border-t border-[#21262d]">
        {[
          { label: 'Pages',       value: summary.total_pages,        icon: '📄', color: 'text-[#58a6ff]' },
          { label: 'Components',  value: summary.total_components,   icon: '🧩', color: 'text-[#a371f7]' },
          { label: 'API Routes',  value: summary.total_api_routes,   icon: '🔌', color: 'text-[#3fb950]' },
          { label: 'Data Models', value: summary.total_data_models || 0, icon: '🗄️', color: 'text-amber-400' },
        ].map(item => (
          <div key={item.label} className="bg-[#161b22] px-4 py-4 text-center">
            <div className="text-xl mb-1">{item.icon}</div>
            <div className={`text-2xl font-semibold mb-0.5 ${item.color}`}>
              {item.value}
            </div>
            <div className="text-xs text-[#484f58] font-mono">{item.label}</div>
          </div>
        ))}
      </div>

      <div className="px-4 py-2 bg-[#0d1117]">
        <p className="text-xs text-[#30363d] font-mono text-center">
          Zero broken links · Every module built from this map
        </p>
      </div>
    </div>
  )
}