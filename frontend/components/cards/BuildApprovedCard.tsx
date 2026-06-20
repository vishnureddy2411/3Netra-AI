// ─────────────────────────────────────────────
// Build Approved Card — shown when council
// verdict is BUILD (no pivot needed)
// ─────────────────────────────────────────────
'use client'

interface Props {
  projectId: string
  idea: string
  pros: string[]
  minorCons: string[]
  onBuild: () => void
  onMoreAlternatives?: () => void
  disabled: boolean
}

export default function BuildApprovedCard({
  projectId,
  idea,
  pros,
  minorCons,
  onBuild,
  onMoreAlternatives,
  disabled,
}: Props) {
  return (
    <div className="bg-[#1a2e1a] border border-[#2ea04326] rounded-xl overflow-hidden max-w-2xl">
      <div className="px-4 py-3 border-b border-[#2ea04320]">
        <div className="text-xs font-mono text-[#3fb950] uppercase tracking-widest mb-0.5">
          Expert Analysis — Approved
        </div>
        <p className="text-xs text-[#484f58]">
          5 specialists reviewed and approved your direction
        </p>
      </div>

      <div className="px-4 py-4 space-y-4">
        {pros.length > 0 && (
          <div>
            <div className="text-xs font-mono text-[#3fb950]/60 mb-2">
              What makes this strong
            </div>
            <ul className="space-y-2">
              {pros.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-[#8b949e] leading-relaxed">
                  <span className="text-[#3fb950]/70 mt-0.5 flex-shrink-0">✓</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}

        {minorCons.length > 0 && (
          <div>
            <div className="text-xs font-mono text-[#484f58] mb-2">
              Things to keep in mind
            </div>
            <ul className="space-y-2">
              {minorCons.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-[#484f58] leading-relaxed">
                  <span className="text-[#484f58] mt-0.5 flex-shrink-0">→</span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <button
            onClick={onBuild}
            disabled={disabled}
            className="flex-1 py-2.5 bg-[#3fb950] text-[#0d1117] font-semibold rounded-lg hover:bg-[#3dba4e] disabled:opacity-40 transition-colors text-sm"
          >
            Build It →
          </button>
          {onMoreAlternatives && (
            <button
              onClick={onMoreAlternatives}
              disabled={disabled}
              className="px-4 py-2.5 bg-[#161b22] border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#8b949e] rounded-lg transition-colors text-xs font-mono disabled:opacity-40"
            >
              More Options
            </button>
          )}
        </div>
      </div>
    </div>
  )
}