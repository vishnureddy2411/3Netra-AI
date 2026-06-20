// ─────────────────────────────────────────────
// Filter Tabs — filter projects by status
// ─────────────────────────────────────────────

'use client'

interface Props {
  active: string
  onChange: (val: string) => void
  counts: Record<string, number>
}

const FILTERS = [
  { id: 'all',         label: 'All'      },
  { id: 'in_progress', label: 'Active'   },
  { id: 'pending',     label: 'Pending'  },
  { id: 'completed',   label: 'Done'     },
  { id: 'archived',    label: 'Archived' },
]

export default function FilterTabs({ active, onChange, counts }: Props) {
  return (
    <div className="flex flex-wrap gap-1">
      {FILTERS.map(filter => {
        const count = filter.id === 'all'
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : counts[filter.id] || 0

        const isActive = active === filter.id

        return (
          <button
            key={filter.id}
            onClick={() => onChange(filter.id)}
            className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-mono transition-colors ${
              isActive
                ? 'bg-[#1c2333] border border-[#58a6ff]/30 text-[#58a6ff]'
                : 'text-[#484f58] hover:text-[#8b949e] hover:bg-[#161b22]'
            }`}
          >
            {filter.label}
            {count > 0 && (
              <span className={`text-xs px-1 rounded ${
                isActive ? 'text-[#58a6ff]/70' : 'text-[#30363d]'
              }`}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}