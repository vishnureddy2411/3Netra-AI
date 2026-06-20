// ─────────────────────────────────────────────
// Comparison Card — Flow 2 (user has idea)
// Shows user's idea vs agent suggestion
// with purpose-specific pros/cons
// ─────────────────────────────────────────────

'use client'

interface Props {
  projectId: string
  originalIdea: string
  pivotIdea: string
  originalPros: string[]
  originalCons: string[]
  suggestedPros: string[]
  suggestedCons: string[]
  skillsDemonstrated: string[]
  skillsLacking: string[]
  howSuggestionImproves: string[]
  recommendedStack: string[]
  summary: string
  onBuildOriginal: () => void
  onBuildSuggested: () => void
  onMoreAlternatives: () => void
  disabled: boolean
}

export default function ComparisonCard({
  projectId,
  originalIdea,
  pivotIdea,
  originalPros,
  originalCons,
  suggestedPros,
  suggestedCons,
  skillsDemonstrated = [],
  skillsLacking = [],
  howSuggestionImproves = [],
  recommendedStack = [],
  summary,
  onBuildOriginal,
  onBuildSuggested,
  onMoreAlternatives,
  disabled,
}: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">

      {/* Header */}
      <div className="px-4 py-3 border-b border-[#21262d]">
        <div className="text-xs font-mono text-amber-400 uppercase tracking-widest mb-0.5">
          Expert Analysis
        </div>
        <p className="text-xs text-[#484f58]">
          5 specialists reviewed your idea — choose your direction
        </p>
      </div>

      {/* Two column comparison */}
      <div className="grid grid-cols-2 gap-px bg-[#21262d]">

        {/* Left — user's idea */}
        <div className="bg-[#161b22] p-4 space-y-4">
          <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest">
            Your Idea
          </div>

          <p className="text-xs text-[#484f58] leading-relaxed bg-[#0d1117] rounded-lg px-3 py-2">
            {originalIdea.slice(0, 100)}
            {originalIdea.length > 100 ? '...' : ''}
          </p>

          {originalPros.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#3fb950]/60 mb-2">What works</div>
              <ul className="space-y-2">
                {originalPros.map((p, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                    <span className="text-[#3fb950]/50 mt-0.5 flex-shrink-0">+</span>{p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {originalCons.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#f85149]/50 mb-2">
                Why a hiring manager skips this
              </div>
              <ul className="space-y-2">
                {originalCons.map((c, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                    <span className="text-[#f85149]/50 mt-0.5 flex-shrink-0">−</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {skillsDemonstrated.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#58a6ff]/60 mb-2">
                Skills this project proves
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skillsDemonstrated.map((s, i) => (
                  <span key={i}
                    className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/15 rounded text-[#58a6ff]/70">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {skillsLacking.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#f85149]/40 mb-2">
                Skills missing for this role
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skillsLacking.map((s, i) => (
                  <span key={i}
                    className="text-xs px-2 py-0.5 bg-[#2d1b1b] border border-[#f85149]/15 rounded text-[#f85149]/50">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right — suggested direction */}
        <div className="bg-[#161b22] p-4 space-y-4">
          <div className="text-xs font-mono text-[#3fb950] uppercase tracking-widest">
            Stronger Approach ★
          </div>

          <p className="text-xs text-[#484f58] leading-relaxed bg-[#0d1117] rounded-lg px-3 py-2">
            {pivotIdea.slice(0, 100)}
            {pivotIdea.length > 100 ? '...' : ''}
          </p>

          {suggestedPros.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#3fb950]/60 mb-2">Why this is stronger</div>
              <ul className="space-y-2">
                {suggestedPros.map((p, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                    <span className="text-[#3fb950]/50 mt-0.5 flex-shrink-0">+</span>{p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {suggestedCons.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#484f58] mb-2">Honest downsides</div>
              <ul className="space-y-2">
                {suggestedCons.map((c, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                    <span className="text-[#484f58] mt-0.5 flex-shrink-0">−</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {howSuggestionImproves.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#a371f7]/60 mb-2">
                How this fixes your weaknesses
              </div>
              <ul className="space-y-2">
                {howSuggestionImproves.map((h, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                    <span className="text-[#a371f7]/50 mt-0.5 flex-shrink-0">→</span>{h}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recommendedStack.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#58a6ff]/60 mb-2">
                Recommended tech stack
              </div>
              <div className="flex flex-wrap gap-1.5">
                {recommendedStack.map((t, i) => (
                  <span key={i}
                    className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/20 rounded text-[#58a6ff]/80">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="px-4 py-3 border-t border-[#21262d] bg-[#0d1117]">
          <div className="text-xs font-mono text-[#484f58] mb-1">Takeaway</div>
          <p className="text-xs text-[#8b949e] leading-relaxed">{summary}</p>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-3 gap-2 p-4 border-t border-[#21262d]">
        <button
          onClick={onBuildOriginal}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-lg text-left hover:border-[#58a6ff]/40 hover:bg-[#1c2333] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#58a6ff] mb-1">BUILD ORIGINAL</div>
          <div className="text-xs text-[#484f58]">Proceed with your idea</div>
        </button>

        <button
          onClick={onBuildSuggested}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#3fb950]/20 rounded-lg text-left hover:border-[#3fb950]/50 hover:bg-[#1a2e1a] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#3fb950] mb-1">BUILD SUGGESTION ★</div>
          <div className="text-xs text-[#484f58]">Experts recommend this</div>
        </button>

        <button
          onClick={onMoreAlternatives}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-lg text-left hover:border-[#8b949e]/40 hover:bg-[#161b22] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#8b949e] mb-1">MORE OPTIONS</div>
          <div className="text-xs text-[#484f58]">Fresh alternatives</div>
        </button>
      </div>
    </div>
  )
}