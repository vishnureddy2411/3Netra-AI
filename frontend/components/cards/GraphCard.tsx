'use client'

import type { GraphSummary } from '../../lib/types'

interface Props {
  summary: GraphSummary
  elapsed: number
}

export default function GraphCard({ summary, elapsed }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262d]">
        <div>
          <div className="text-xs font-mono text-[#3fb950] uppercase tracking-widest mb-0.5">
            Project Graph
          </div>
          <div className="text-xs text-[#484f58]">
            All navigation pre-wired · {elapsed}s
          </div>
        </div>
        <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950]" />
      </div>

      <div className="grid grid-cols-3 gap-px bg-[#21262d]">
        {[
          { label: 'Pages', value: summary.total_pages, icon: '📄', color: 'text-[#58a6ff]' },
          { label: 'Components', value: summary.total_components, icon: '🧩', color: 'text-[#a371f7]' },
          { label: 'API Routes', value: summary.total_api_routes, icon: '🔌', color: 'text-[#3fb950]' },
        ].map(item => (
          <div key={item.label} className="bg-[#161b22] px-4 py-5 text-center">
            <div className="text-2xl mb-2">{item.icon}</div>
            <div className={`text-2xl font-semibold mb-1 ${item.color}`}>
              {item.value}
            </div>
            <div className="text-xs text-[#484f58] font-mono">{item.label}</div>
          </div>
        ))}
      </div>

      <div className="px-4 py-3 border-t border-[#21262d] bg-[#0d1117]">
        <p className="text-xs text-[#30363d] font-mono">
          Zero broken links · Every module built from this map
        </p>
      </div>
    </div>
  )
}