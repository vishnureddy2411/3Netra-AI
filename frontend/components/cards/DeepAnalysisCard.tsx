'use client'

import { useState } from 'react'
import type {
  DeepAnalysisResult,
  TechStackItem,
  SkillItem,
  ScoreItem,
} from '../../lib/types'

interface Props {
  analysis:           DeepAnalysisResult
  originalIdea:       string
  pivotIdea:          string
  projectId:          string
  onBuildOriginal:    () => void
  onBuildImproved:    () => void
  onMoreAlternatives: () => void
  disabled:           boolean
}

// ── Helpers ───────────────────────────────────

const riskColor = (r: string) =>
  r === 'low'    ? 'text-[#3fb950]' :
  r === 'medium' ? 'text-amber-400'  :
  'text-[#f85149]'

const strengthColor = (s: string) =>
  s === 'high'   ? 'text-[#3fb950]' :
  s === 'medium' ? 'text-amber-400'  :
  'text-[#484f58]'

const importanceColor = (i: string) =>
  i === 'critical' ? 'text-[#f85149]' :
  i === 'high'     ? 'text-amber-400'  :
  'text-[#484f58]'

const scoreColor = (s: number) =>
  s >= 7 ? 'text-[#3fb950]' :
  s >= 5 ? 'text-amber-400'  :
  'text-[#f85149]'

const recommendationColor = (r: string | undefined) => {
  if (!r) return 'text-[#8b949e] bg-[#161b22] border-[#30363d]'
  const map: Record<string, string> = {
    build:   'text-[#3fb950] bg-[#1a2e1a] border-[#3fb950]/20',
    improve: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    pivot:   'text-[#58a6ff] bg-[#1c2333] border-[#58a6ff]/20',
    abandon: 'text-[#f85149] bg-[#2d1b1b] border-[#f85149]/20',
  }
  return map[r.toLowerCase()] || 'text-[#8b949e] bg-[#161b22] border-[#30363d]'
}

// ─────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────

export default function DeepAnalysisCard({
  analysis,
  originalIdea,
  pivotIdea,
  projectId,
  onBuildOriginal,
  onBuildImproved,
  onMoreAlternatives,
  disabled,
}: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'stack' | 'skills' | 'blueprint' | 'verdict'>('overview')

  const tabs = [
    { id: 'overview',   label: 'Overview'   },
    { id: 'stack',      label: 'Tech Stack' },
    { id: 'skills',     label: 'Skills'     },
    { id: 'blueprint',  label: 'Blueprint'  },
    { id: 'verdict',    label: 'Verdict'    },
  ] as const

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">

      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs font-mono text-amber-400 uppercase tracking-widest">
            Deep Expert Analysis
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#484f58] font-mono">{analysis.elapsed_seconds}s</span>
            <div className={`text-xs font-mono px-2 py-0.5 rounded-full border ${recommendationColor(analysis.final_recommendation)}`}>
              {(analysis.final_recommendation || 'improve').toUpperCase()}
            </div>
          </div>
        </div>
        <p className="text-xs text-[#484f58]">
          5 specialists · role-specific · evidence-based · adversarial council review
        </p>
      </div>

      {/* ── Tab bar ── */}
      <div className="flex border-b border-[#21262d] bg-[#161b22] overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-xs px-3 py-2.5 whitespace-nowrap font-mono transition-colors flex-shrink-0 border-b-2 ${
              activeTab === tab.id
                ? 'text-[#f0b429] border-[#f0b429] bg-[#0d1117]'
                : 'text-[#484f58] border-transparent hover:text-[#8b949e]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ── */}
      {activeTab === 'overview' && (
        <div className="p-4 space-y-5">

          {/* Hiring Manager First Impression */}
          <div className="bg-[#161b22] border border-[#f0b429]/20 rounded-xl p-4">
            <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-2">
              Hiring Manager First Impression
            </div>
            <p className="text-xs text-[#8b949e] leading-relaxed">
              {analysis.hiring_manager_impression}
            </p>
          </div>

          {/* Engineering signal vs generic */}
          <div>
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">
              What Counts as Engineering Signal vs Generic Web Dev
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs font-mono text-[#3fb950] mb-2">Real engineering signal</div>
                <div className="space-y-2">
                  {(analysis.ml_engineering_aspects || []).map((a, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-[#3fb950] text-xs mt-0.5 flex-shrink-0">✓</span>
                      <span className="text-xs text-[#8b949e] leading-relaxed">{a}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-[#484f58] mb-2">Generic web dev (not counted)</div>
                <div className="space-y-2">
                  {(analysis.fullstack_aspects || []).map((a, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-[#30363d] text-xs mt-0.5 flex-shrink-0">−</span>
                      <span className="text-xs text-[#30363d] leading-relaxed">{a}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TECH STACK ── */}
      {activeTab === 'stack' && (
        <div className="p-4 space-y-3">
          <div className="text-xs font-mono text-[#58a6ff] uppercase tracking-widest mb-3">
            Technology Analysis — Every Tool Justified
          </div>
          {(analysis.tech_stack_analysis || []).map((item: TechStackItem, i: number) => (
            <div key={i} className={`bg-[#0d1117] border rounded-xl p-3 ${
              item.mvp ? 'border-[#30363d]' : 'border-[#21262d] opacity-70'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono font-semibold text-[#e6edf3]">{item.tech}</span>
                  {item.mvp && (
                    <span className="text-xs px-1.5 py-0.5 bg-[#1c2333] border border-[#58a6ff]/20 rounded text-[#58a6ff]/70 font-mono">
                      MVP
                    </span>
                  )}
                </div>
                <span className={`text-xs font-mono ${riskColor(item.risk)}`}>{item.risk} risk</span>
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex gap-2">
                  <span className="text-[#484f58] w-20 flex-shrink-0 font-mono">Why use</span>
                  <span className="text-[#8b949e] leading-relaxed">{item.why_use}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-[#484f58] w-20 flex-shrink-0 font-mono">Proves</span>
                  <span className="text-[#3fb950]/80 leading-relaxed">{item.skill_proved}</span>
                </div>
                {item.alternative && item.alternative !== 'Best choice for this use case' && (
                  <div className="flex gap-2">
                    <span className="text-[#484f58] w-20 flex-shrink-0 font-mono">Alt</span>
                    <span className="text-amber-400/70 leading-relaxed">{item.alternative}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── SKILLS ── */}
      {activeTab === 'skills' && (
        <div className="p-4 space-y-5">

          <div>
            <div className="text-xs font-mono text-[#3fb950] uppercase tracking-widest mb-3">
              Skills This Project Demonstrates
            </div>
            <div className="space-y-2">
              {(analysis.skills_demonstrated || []).map((item: SkillItem, i: number) => (
                <div key={i} className="flex items-center justify-between bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[#3fb950] text-xs">✓</span>
                    <span className="text-xs text-[#8b949e]">{item.skill}</span>
                  </div>
                  <span className={`text-xs font-mono ${strengthColor(item.strength || 'medium')}`}>
                    {item.strength || 'medium'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs font-mono text-[#f85149] uppercase tracking-widest mb-3">
              Skills Missing for This Role — Critical Gaps
            </div>
            <div className="space-y-2">
              {(analysis.skills_missing || []).map((item: SkillItem, i: number) => (
                <div key={i} className="flex items-center justify-between bg-[#2d1b1b] border border-[#f85149]/10 rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[#f85149] text-xs">−</span>
                    <span className="text-xs text-[#8b949e]">{item.skill}</span>
                  </div>
                  <span className={`text-xs font-mono ${importanceColor(item.importance || 'high')}`}>
                    {item.importance || 'high'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── BLUEPRINT ── */}
      {activeTab === 'blueprint' && analysis.improved_blueprint && (
        <div className="p-4 space-y-4">
          <div className="text-xs font-mono text-[#a371f7] uppercase tracking-widest mb-1">
            Improved Project Blueprint
          </div>

          <div className="bg-[#161b22] border border-[#a371f7]/20 rounded-xl p-4">
            <div className="text-sm font-semibold text-[#e6edf3] mb-1">
              {analysis.improved_blueprint.title}
            </div>
            <p className="text-xs text-[#8b949e] leading-relaxed">
              {analysis.improved_blueprint.description}
            </p>
          </div>

          <div>
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
              Key Improvements
            </div>
            <div className="space-y-1.5">
              {analysis.improved_blueprint.key_improvements.map((k, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-[#a371f7] text-xs mt-0.5 flex-shrink-0">→</span>
                  <span className="text-xs text-[#8b949e] leading-relaxed">{k}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
              MVP Scope
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {analysis.improved_blueprint.mvp_features.map((f, i) => (
                <div key={i} className="bg-[#0d1117] border border-[#21262d] rounded-lg px-2.5 py-2 text-xs text-[#8b949e]">
                  {f}
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
              Recommended Stack
            </div>
            <div className="flex flex-wrap gap-1.5">
              {analysis.improved_blueprint.recommended_stack.map((t, i) => (
                <span key={i} className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/20 rounded text-[#58a6ff]/80 font-mono">
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
              Evaluation Approach
            </div>
            <div className="bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2">
              <p className="text-xs text-[#8b949e] leading-relaxed">
                {analysis.improved_blueprint.evaluation_approach}
              </p>
            </div>
          </div>

          <div>
            <div className="text-xs font-mono text-[#3fb950] uppercase tracking-widest mb-2">
              Resume Bullet Point
            </div>
            <div className="bg-[#1a2e1a] border border-[#3fb950]/15 rounded-xl px-4 py-3">
              <p className="text-xs text-[#8b949e] leading-relaxed italic">
                "{analysis.improved_blueprint.resume_bullet}"
              </p>
            </div>
          </div>

          <div>
            <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1">
              Estimated Build Time
            </div>
            <span className="text-sm text-[#e6edf3] font-mono">
              {analysis.improved_blueprint.estimated_weeks} weeks
            </span>
          </div>
        </div>
      )}

      {/* ── VERDICT ── */}
      {activeTab === 'verdict' && (
        <div className="p-4 space-y-4">
          <div className="text-xs font-mono text-amber-400 uppercase tracking-widest mb-1">
            Expert Scoring — Build, Improve, Pivot, or Abandon
          </div>

          <div className="space-y-2">
            {(analysis.scoring || []).map((item: ScoreItem, i: number) => {
              const safeScore = Math.min(10, Math.max(1, Math.round(item.score)))
              return (
                <div key={i} className="bg-[#0d1117] border border-[#21262d] rounded-xl px-4 py-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-mono text-[#e6edf3]">{item.option}</span>
                    <div className="flex items-center gap-2">
                      <div className="flex gap-0.5">
                        {Array.from({ length: 10 }).map((_, j) => (
                          <div key={j} className={`w-1.5 h-3 rounded-sm ${
                            j < safeScore
                              ? safeScore >= 7 ? 'bg-[#3fb950]'
                              : safeScore >= 5 ? 'bg-amber-400'
                              : 'bg-[#f85149]'
                              : 'bg-[#21262d]'
                          }`} />
                        ))}
                      </div>
                      <span className={`text-sm font-semibold font-mono ${scoreColor(safeScore)}`}>
                        {safeScore}/10
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-[#484f58] leading-relaxed">{item.reason}</p>
                </div>
              )
            })}
          </div>

          <div className="bg-[#161b22] border border-[#f0b429]/20 rounded-xl p-4">
            <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-2">
              Final Reasoning
            </div>
            <p className="text-xs text-[#8b949e] leading-relaxed">
              {analysis.final_reasoning}
            </p>
          </div>
        </div>
      )}

      {/* ── Action buttons ── */}
      <div className="grid grid-cols-3 gap-2 p-4 border-t border-[#21262d]">
        <button
          onClick={onBuildOriginal}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-xl text-left hover:border-[#58a6ff]/40 hover:bg-[#1c2333] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#58a6ff] mb-1">BUILD ORIGINAL</div>
          <div className="text-xs text-[#484f58]">Your idea as-is</div>
        </button>

        <button
          onClick={onBuildImproved}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#3fb950]/20 rounded-xl text-left hover:border-[#3fb950]/50 hover:bg-[#1a2e1a] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#3fb950] mb-1">BUILD IMPROVED ★</div>
          <div className="text-xs text-[#484f58]">Expert blueprint</div>
        </button>

        <button
          onClick={onMoreAlternatives}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-xl text-left hover:border-[#8b949e]/40 transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#8b949e] mb-1">MORE OPTIONS</div>
          <div className="text-xs text-[#484f58]">Fresh alternatives</div>
        </button>
      </div>
    </div>
  )
}