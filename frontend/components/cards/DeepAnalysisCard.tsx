// ─────────────────────────────────────────────
// Deep Analysis Card
// Comprehensive portfolio analysis for Flow 2
// Shows: hiring impression, tech stack table,
// skills matrix, improved blueprint, scoring
// ─────────────────────────────────────────────

'use client'

import { useState } from 'react'
import type {
  DeepAnalysisResult,
  TechStackItem,
  SkillItem,
  ScoreItem,
} from '../../lib/types'

interface Props {
  analysis: DeepAnalysisResult
  originalIdea: string
  pivotIdea: string
  projectId: string
  onBuildOriginal: () => void
  onBuildImproved: () => void
  onMoreAlternatives: () => void
  disabled: boolean
}

// ── helpers ───────────────────────────────────

const riskColor = (r: string) =>
  r === 'low' ? 'text-[#3fb950]' :
  r === 'medium' ? 'text-amber-400' :
  'text-[#f85149]'

const strengthColor = (s: string) =>
  s === 'high' ? 'text-[#3fb950]' :
  s === 'medium' ? 'text-amber-400' :
  'text-[#484f58]'

const importanceColor = (i: string) =>
  i === 'critical' ? 'text-[#f85149]' :
  i === 'high' ? 'text-amber-400' :
  'text-[#484f58]'

const scoreColor = (s: number) =>
  s >= 7 ? 'text-[#3fb950]' :
  s >= 5 ? 'text-amber-400' :
  'text-[#f85149]'

const recommendationColor = (r: string) => {
  const map: Record<string, string> = {
    build: 'text-[#3fb950] bg-[#1a2e1a] border-[#3fb950]/20',
    improve: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    pivot: 'text-[#58a6ff] bg-[#1c2333] border-[#58a6ff]/20',
    abandon: 'text-[#f85149] bg-[#2d1b1b] border-[#f85149]/20',
  }
  return map[r.toLowerCase()] || 'text-[#8b949e] bg-[#161b22] border-[#30363d]'
}

// ── Section wrapper ───────────────────────────

function Section({ title, color = 'text-[#8b949e]', children }: {
  title: string
  color?: string
  children: React.ReactNode
}) {
  return (
    <div className="border-t border-[#21262d] px-4 py-4">
      <div className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title}
      </div>
      {children}
    </div>
  )
}

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
    { id: 'overview', label: 'Overview' },
    { id: 'stack', label: 'Tech Stack' },
    { id: 'skills', label: 'Skills' },
    { id: 'blueprint', label: 'Blueprint' },
    { id: 'verdict', label: 'Verdict' },
  ] as const

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">

      {/* Header */}
      <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs font-mono text-amber-400 uppercase tracking-widest">
            Deep Expert Analysis
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#484f58] font-mono">
              {analysis.elapsed_seconds}s
            </span>
            <div className={`text-xs font-mono px-2 py-0.5 rounded-full border ${
              recommendationColor(analysis.final_recommendation)
            }`}>
              {analysis.final_recommendation.toUpperCase()}
            </div>
          </div>
        </div>
        <p className="text-xs text-[#484f58]">
          5 specialists · role-specific · evidence-based · {analysis.idea_score}/100 role match
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#21262d] bg-[#0d1117] px-3 py-1.5 gap-1 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap font-mono transition-colors ${
              activeTab === tab.id
                ? 'bg-[#f0b429] text-[#0d1117] font-semibold'
                : 'text-[#484f58] hover:text-[#e6edf3] hover:bg-[#161b22]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW TAB ── */}
      {activeTab === 'overview' && (
        <div>
          {/* Hiring manager impression */}
          <Section title="Hiring Manager First Impression" color="text-amber-400/70">
            <div className="bg-[#0d1117] border border-[#21262d] rounded-lg px-4 py-3">
              <p className="text-sm text-[#8b949e] leading-relaxed">
                {analysis.hiring_manager_impression}
              </p>
            </div>
          </Section>

          {/* ML vs fullstack split */}
          <Section title="What counts as engineering signal vs generic web dev">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#1a2e1a] border border-[#3fb950]/15 rounded-lg p-3">
                <div className="text-xs font-mono text-[#3fb950]/60 mb-2">
                  Real engineering signal
                </div>
                <ul className="space-y-1.5">
                  {(analysis.ml_engineering_aspects || []).map((a, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                      <span className="text-[#3fb950]/50 mt-0.5 flex-shrink-0">✓</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bg-[#2d1b1b] border border-[#f85149]/15 rounded-lg p-3">
                <div className="text-xs font-mono text-[#f85149]/60 mb-2">
                  Generic web dev (not counted)
                </div>
                <ul className="space-y-1.5">
                  {(analysis.fullstack_aspects || []).map((a, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                      <span className="text-[#f85149]/50 mt-0.5 flex-shrink-0">−</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Section>
        </div>
      )}

      {/* ── TECH STACK TAB ── */}
      {activeTab === 'stack' && (
        <Section title="Technology Analysis — every tool justified" color="text-[#58a6ff]/70">
          <div className="space-y-2">
            {(analysis.tech_stack_analysis || []).map((item: TechStackItem, i: number) => (
              <div key={i}
                className={`bg-[#0d1117] border rounded-lg p-3 ${
                  item.mvp ? 'border-[#30363d]' : 'border-[#21262d] opacity-70'
                }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono font-semibold text-[#e6edf3]">
                      {item.tech}
                    </span>
                    {item.mvp && (
                      <span className="text-xs px-1.5 py-0.5 bg-[#1c2333] border border-[#58a6ff]/20 rounded text-[#58a6ff]/70 font-mono">
                        MVP
                      </span>
                    )}
                  </div>
                  <span className={`text-xs font-mono ${riskColor(item.risk)}`}>
                    {item.risk} risk
                  </span>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex gap-2">
                    <span className="text-[#484f58] w-20 flex-shrink-0">Why use</span>
                    <span className="text-[#8b949e] leading-relaxed">{item.why_use}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-[#484f58] w-20 flex-shrink-0">Proves</span>
                    <span className="text-[#3fb950]/80 leading-relaxed">{item.skill_proved}</span>
                  </div>
                  {item.alternative && item.alternative !== 'Best choice for this use case' && (
                    <div className="flex gap-2">
                      <span className="text-[#484f58] w-20 flex-shrink-0">Alternative</span>
                      <span className="text-amber-400/70 leading-relaxed">{item.alternative}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── SKILLS TAB ── */}
      {activeTab === 'skills' && (
        <div>
          <Section title="Skills this project demonstrates" color="text-[#3fb950]/70">
            <div className="space-y-2">
              {(analysis.skills_demonstrated || []).map((item: SkillItem, i: number) => (
                <div key={i} className="flex items-center justify-between bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2">
                  <span className="text-xs text-[#8b949e]">{item.skill}</span>
                  <span className={`text-xs font-mono ${strengthColor(item.strength || 'medium')}`}>
                    {item.strength || 'medium'}
                  </span>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Skills missing for this role — critical gaps" color="text-[#f85149]/60">
            <div className="space-y-2">
              {(analysis.skills_missing || []).map((item: SkillItem, i: number) => (
                <div key={i} className="flex items-center justify-between bg-[#2d1b1b] border border-[#f85149]/10 rounded-lg px-3 py-2">
                  <span className="text-xs text-[#8b949e]">{item.skill}</span>
                  <span className={`text-xs font-mono ${importanceColor(item.importance || 'high')}`}>
                    {item.importance || 'high'}
                  </span>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}

      {/* ── BLUEPRINT TAB ── */}
      {activeTab === 'blueprint' && analysis.improved_blueprint && (
        <div>
          <Section title="Improved project blueprint" color="text-[#a371f7]/70">
            {/* Title + description */}
            <div className="bg-[#0d1117] border border-[#a371f7]/20 rounded-lg px-4 py-3 mb-3">
              <div className="text-sm font-semibold text-[#e6edf3] mb-1">
                {analysis.improved_blueprint.title}
              </div>
              <p className="text-xs text-[#8b949e] leading-relaxed">
                {analysis.improved_blueprint.description}
              </p>
            </div>

            {/* Key improvements */}
            <div className="mb-3">
              <div className="text-xs font-mono text-[#a371f7]/50 mb-2">
                Key improvements over your original
              </div>
              <ul className="space-y-1.5">
                {analysis.improved_blueprint.key_improvements.map((k, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-[#8b949e] leading-relaxed">
                    <span className="text-[#a371f7]/50 mt-0.5 flex-shrink-0">→</span>
                    {k}
                  </li>
                ))}
              </ul>
            </div>

            {/* MVP features */}
            <div className="mb-3">
              <div className="text-xs font-mono text-[#484f58] mb-2">MVP scope</div>
              <div className="grid grid-cols-2 gap-1.5">
                {analysis.improved_blueprint.mvp_features.map((f, i) => (
                  <div key={i} className="bg-[#0d1117] border border-[#21262d] rounded-lg px-2.5 py-2 text-xs text-[#8b949e]">
                    {f}
                  </div>
                ))}
              </div>
            </div>

            {/* Stack */}
            <div className="mb-3">
              <div className="text-xs font-mono text-[#484f58] mb-2">Recommended stack</div>
              <div className="flex flex-wrap gap-1.5">
                {analysis.improved_blueprint.recommended_stack.map((t, i) => (
                  <span key={i}
                    className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/20 rounded text-[#58a6ff]/80">
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Evaluation */}
            <div className="mb-3">
              <div className="text-xs font-mono text-[#484f58] mb-2">Evaluation approach</div>
              <div className="bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2">
                <p className="text-xs text-[#8b949e] leading-relaxed">
                  {analysis.improved_blueprint.evaluation_approach}
                </p>
              </div>
            </div>

            {/* Timeline */}
            <div className="mb-3">
              <div className="text-xs font-mono text-[#484f58] mb-1">Estimated build time</div>
              <span className="text-sm text-[#e6edf3]">
                {analysis.improved_blueprint.estimated_weeks} weeks
              </span>
            </div>

            {/* Resume bullet */}
            <div>
              <div className="text-xs font-mono text-[#3fb950]/60 mb-2">
                Resume bullet point
              </div>
              <div className="bg-[#1a2e1a] border border-[#3fb950]/15 rounded-lg px-3 py-2">
                <p className="text-xs text-[#8b949e] leading-relaxed italic">
                  "{analysis.improved_blueprint.resume_bullet}"
                </p>
              </div>
            </div>
          </Section>
        </div>
      )}

      {/* ── VERDICT TAB ── */}
      {activeTab === 'verdict' && (
        <div>
          <Section title="Expert scoring — build, improve, pivot, or abandon" color="text-amber-400/70">
            <div className="space-y-2 mb-4">
              {(analysis.scoring || []).map((item: ScoreItem, i: number) => {
                // Safety clamp — score must always be 1-10
                const safeScore = Math.min(10, Math.max(1, Math.round(item.score)))
                return (
                  <div key={i} className="bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-3">
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

            {/* Final reasoning */}
            <div className="bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3">
              <div className="text-xs font-mono text-[#484f58] mb-2">Final reasoning</div>
              <p className="text-sm text-[#8b949e] leading-relaxed">
                {analysis.final_reasoning}
              </p>
            </div>
          </Section>
        </div>
      )}

      {/* Action buttons — always visible */}
      <div className="grid grid-cols-3 gap-2 p-4 border-t border-[#21262d]">
        <button
          onClick={onBuildOriginal}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-lg text-left hover:border-[#58a6ff]/40 hover:bg-[#1c2333] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#58a6ff] mb-1">BUILD ORIGINAL</div>
          <div className="text-xs text-[#484f58]">Your idea as-is</div>
        </button>

        <button
          onClick={onBuildImproved}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#3fb950]/20 rounded-lg text-left hover:border-[#3fb950]/50 hover:bg-[#1a2e1a] transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#3fb950] mb-1">BUILD IMPROVED ★</div>
          <div className="text-xs text-[#484f58]">Expert blueprint</div>
        </button>

        <button
          onClick={onMoreAlternatives}
          disabled={disabled}
          className="flex flex-col px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-lg text-left hover:border-[#8b949e]/40 transition-colors disabled:opacity-30"
        >
          <div className="text-xs font-mono text-[#8b949e] mb-1">MORE OPTIONS</div>
          <div className="text-xs text-[#484f58]">Fresh alternatives</div>
        </button>
      </div>
    </div>
  )
}