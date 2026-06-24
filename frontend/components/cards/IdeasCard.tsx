'use client'

import { useState } from 'react'
import { PURPOSE_OPTIONS, LEVEL_COLORS } from '../../lib/constants'
import type { ProjectIdea } from '../../lib/types'

// ─────────────────────────────────────────────
// Extended type for enriched ideas
// ─────────────────────────────────────────────

interface EnrichedIdea extends ProjectIdea {
  tech_stack_detail?:        Array<{ name: string; purpose: string }>
  hiring_manager_impression?: string
  engineering_signals?:       string[]
  generic_web_dev_excluded?:  string[]
  council_decision?:          string
  why_selected?:              string
  real_world_use_case?:       string
  portfolio_strength?:        string
  risk_weakness?:             string
  how_to_stand_out?:          string
}

// ─────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────

interface Props {
  ideas:               ProjectIdea[]
  purpose:             string
  role:                string
  onSelect:            (idea: ProjectIdea) => void
  onMoreAlternatives?: () => void
}

// ─────────────────────────────────────────────
// Tabs
// ─────────────────────────────────────────────

const TABS = ['Overview', 'Tech Stack', 'Skills', 'Blueprint', 'Verdict'] as const
type Tab = typeof TABS[number]

// ─────────────────────────────────────────────
// EnrichedIdeaCard — tabbed rich view
// ─────────────────────────────────────────────

function EnrichedIdeaCard({
  idea,
  onSelect,
}: {
  idea:     EnrichedIdea
  onSelect: () => void
}) {
  const [activeTab, setActiveTab] = useState<Tab>('Overview')

  return (
    <div className="bg-[#0d1117] border border-[#30363d] rounded-xl overflow-hidden">

      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-[#21262d]">
        <div className="flex items-start justify-between gap-3 mb-1.5">
          <span className="font-semibold text-[#e6edf3] text-sm leading-snug">
            {idea.title}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full border flex-shrink-0 font-mono ${
            LEVEL_COLORS[idea.level] || LEVEL_COLORS['Intermediate']
          }`}>
            {idea.level}
          </span>
        </div>
        <p className="text-xs text-[#484f58] leading-relaxed">{idea.one_liner}</p>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-[#21262d] bg-[#161b22] overflow-x-auto flex-shrink-0">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`text-xs px-3 py-2.5 whitespace-nowrap font-mono transition-colors flex-shrink-0 border-b-2 ${
              activeTab === tab
                ? 'text-[#f0b429] border-[#f0b429] bg-[#0d1117]'
                : 'text-[#484f58] border-transparent hover:text-[#8b949e]'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4 min-h-[220px]">

        {/* ── Overview ── */}
        {activeTab === 'Overview' && (
          <div className="space-y-4">

            {/* Hiring Manager First Impression */}
            {idea.hiring_manager_impression && (
              <div className="bg-[#161b22] border border-[#f0b429]/20 rounded-xl p-4">
                <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-2">
                  Hiring Manager First Impression
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">
                  {idea.hiring_manager_impression}
                </p>
              </div>
            )}

            {/* Real-world use case */}
            {idea.real_world_use_case && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1.5">
                  Real-World Use Case
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">
                  {idea.real_world_use_case}
                </p>
              </div>
            )}

            {/* Market gap */}
            {idea.market_gap && (
              <div className="bg-[#161b22] border border-[#21262d] rounded-lg px-3 py-2.5">
                <div className="text-xs font-mono text-[#30363d] mb-1">Problem it solves</div>
                <p className="text-xs text-[#484f58] leading-relaxed">{idea.market_gap}</p>
              </div>
            )}
          </div>
        )}

        {/* ── Tech Stack ── */}
        {activeTab === 'Tech Stack' && (
          <div className="space-y-3">
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">
              Selected Technologies
            </div>

            {idea.tech_stack_detail && idea.tech_stack_detail.length > 0 ? (
              <div className="space-y-2">
                {idea.tech_stack_detail.map((tech, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-[#161b22] rounded-lg border border-[#21262d]">
                    <span className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/20 rounded text-[#58a6ff]/80 font-mono flex-shrink-0 whitespace-nowrap">
                      {tech.name}
                    </span>
                    <p className="text-xs text-[#484f58] leading-relaxed">{tech.purpose}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {(idea.tech_stack || []).map((tech, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/15 rounded text-[#58a6ff]/70 font-mono">
                    {tech}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Skills ── */}
        {activeTab === 'Skills' && (
          <div className="space-y-5">

            {/* Engineering signals */}
            {idea.engineering_signals && idea.engineering_signals.length > 0 && (
              <div>
                <div className="text-xs font-mono text-[#3fb950] uppercase tracking-widest mb-2">
                  Real Engineering Signal
                </div>
                <div className="space-y-2">
                  {idea.engineering_signals.map((signal, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-[#3fb950] text-xs mt-0.5 flex-shrink-0">✓</span>
                      <span className="text-xs text-[#8b949e] leading-relaxed">{signal}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Generic excluded */}
            {idea.generic_web_dev_excluded && idea.generic_web_dev_excluded.length > 0 && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
                  Generic Web Dev — Not Counted as Signal
                </div>
                <div className="space-y-2">
                  {idea.generic_web_dev_excluded.map((item, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-[#30363d] text-xs mt-0.5 flex-shrink-0">−</span>
                      <span className="text-xs text-[#30363d] leading-relaxed">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Skills demonstrated */}
            {idea.skills_demonstrated && idea.skills_demonstrated.length > 0 && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
                  Skills Demonstrated
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {idea.skills_demonstrated.map((skill, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-[#161b22] border border-[#30363d] rounded text-[#484f58] font-mono">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Blueprint ── */}
        {activeTab === 'Blueprint' && (
          <div className="space-y-4">

            {/* How to stand out */}
            {idea.how_to_stand_out && (
              <div>
                <div className="text-xs font-mono text-[#a371f7] uppercase tracking-widest mb-2">
                  How to Make It Stand Out
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{idea.how_to_stand_out}</p>
              </div>
            )}

            {/* Council decision */}
            {idea.council_decision && (
              <div className="bg-[#161b22] border border-[#21262d] rounded-xl p-4">
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
                  Council Decision
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{idea.council_decision}</p>
              </div>
            )}

            {/* Why selected */}
            {idea.why_selected && (
              <div className="bg-[#1a2e1a] border border-[#3fb950]/20 rounded-lg px-3 py-2.5">
                <div className="text-xs font-mono text-[#3fb950] mb-1">Why This Won</div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{idea.why_selected}</p>
              </div>
            )}
          </div>
        )}

        {/* ── Verdict ── */}
        {activeTab === 'Verdict' && (
          <div className="space-y-4">

            {/* Portfolio strength */}
            {idea.portfolio_strength && (
              <div>
                <div className="text-xs font-mono text-[#58a6ff] uppercase tracking-widest mb-2">
                  Portfolio Strength
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{idea.portfolio_strength}</p>
              </div>
            )}

            {/* Risk */}
            {idea.risk_weakness && (
              <div className="bg-[#2d1b1b] border border-[#f85149]/20 rounded-xl p-4">
                <div className="text-xs font-mono text-[#f85149] uppercase tracking-widest mb-2">
                  Risk / Weakness
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{idea.risk_weakness}</p>
              </div>
            )}

            {/* Bottom line */}
            {idea.why_good && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1.5">
                  Bottom Line
                </div>
                <p className="text-xs text-[#484f58] leading-relaxed">{idea.why_good}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-[#21262d] bg-[#161b22]">
        <span className="text-xs text-[#30363d] font-mono">⏱ {idea.build_time}</span>
        <button
          onClick={onSelect}
          className="text-xs px-4 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors"
        >
          Build This →
        </button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// SimpleIdeaCard — alternatives flow fallback
// ─────────────────────────────────────────────

function SimpleIdeaCard({
  idea,
  onSelect,
}: {
  idea:     ProjectIdea
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className="w-full text-left bg-[#0d1117] border border-[#30363d] rounded-xl p-4 hover:border-[#f0b429]/30 hover:bg-[#161b22] transition-colors group"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="font-medium text-[#e6edf3] group-hover:text-[#f0b429] transition-colors text-sm">
          {idea.title}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full border flex-shrink-0 ${
          LEVEL_COLORS[idea.level] || LEVEL_COLORS['Intermediate']
        }`}>
          {idea.level}
        </span>
      </div>
      <p className="text-xs text-[#484f58] mb-3 leading-relaxed">{idea.one_liner}</p>

      {idea.market_gap && (
        <div className="bg-[#161b22] border border-[#21262d] rounded-lg px-3 py-2 mb-3">
          <div className="text-xs font-mono text-[#30363d] mb-1">Problem it solves</div>
          <p className="text-xs text-[#484f58] leading-relaxed">{idea.market_gap}</p>
        </div>
      )}

      {(idea as any).why_better_than_original && (
        <div className="bg-[#1a2e1a] border border-[#3fb950]/20 rounded-lg px-3 py-2 mb-3">
          <div className="text-xs font-mono text-[#3fb950] mb-1">Why better</div>
          <p className="text-xs text-[#484f58] leading-relaxed">
            {(idea as any).why_better_than_original}
          </p>
        </div>
      )}

      {idea.tech_stack && idea.tech_stack.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-mono text-[#30363d] mb-1.5">Tech stack</div>
          <div className="flex flex-wrap gap-1.5">
            {idea.tech_stack.map((tech, j) => (
              <span key={j} className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/15 rounded text-[#58a6ff]/70 font-mono">
                {tech}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-[#30363d] pt-2 border-t border-[#21262d]">
        <span>⏱ {idea.build_time}</span>
        <span className="text-[#f0b429]/30 group-hover:text-[#f0b429] transition-colors">Select →</span>
      </div>
    </button>
  )
}

// ─────────────────────────────────────────────
// Main export
// ─────────────────────────────────────────────

export default function IdeasCard({
  ideas,
  purpose,
  role,
  onSelect,
  onMoreAlternatives,
}: Props) {
  const purposeLabel = PURPOSE_OPTIONS.find(p => p.id === purpose)?.label || purpose
  const isEnriched   = ideas.length > 0 && !!(ideas[0] as EnrichedIdea).hiring_manager_impression

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">

      {/* Card header */}
      <div className="px-5 py-3 border-b border-[#21262d]">
        <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-0.5">
          {isEnriched ? 'Council-Approved Project Ideas' : 'Alternative Ideas'}
        </div>
        <p className="text-xs text-[#484f58]">
          {isEnriched
            ? `Silently analyzed and selected for ${purposeLabel}${role ? ` · ${role}` : ''} — one per level`
            : `Alternatives for ${purposeLabel}${role ? ` · ${role}` : ''} · Click one to start building`}
        </p>
      </div>

      {/* Ideas */}
      <div className="p-4 space-y-4">
        {ideas.map((idea, i) =>
          isEnriched ? (
            <EnrichedIdeaCard
              key={i}
              idea={idea as EnrichedIdea}
              onSelect={() => onSelect(idea)}
            />
          ) : (
            <SimpleIdeaCard
              key={i}
              idea={idea}
              onSelect={() => onSelect(idea)}
            />
          )
        )}
      </div>

      {onMoreAlternatives && (
        <div className="px-4 pb-4">
          <button
            onClick={onMoreAlternatives}
            className="w-full py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs font-mono text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
          >
            Show more alternatives →
          </button>
        </div>
      )}
    </div>
  )
}