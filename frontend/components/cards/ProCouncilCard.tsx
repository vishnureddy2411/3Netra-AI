'use client'

import { useState } from 'react'

interface ExecutionPhase {
  phase:            number
  title:            string
  actions:          string[]
  estimated_effort: string
  success_criteria: string
}

interface AgentOutput {
  agent_name: string
  position:   string
  top_risk:   string
  confidence: number
  reasoning:  string
}

interface ProVerdictData {
  verdict:                string
  primary_recommendation: string
  executive_summary:      string
  execution_plan:         ExecutionPhase[]
  blocking_issues:        string[]
  conditions:             string[]
  key_tradeoffs:          string[]
  confidence_score:       number
  minority_dissent:       string | null
  clarifying_questions:   string[]
  first_action:           string
}

interface Props {
  verdict:          ProVerdictData
  agentOutputs:     AgentOutput[]
  task:             string
  projectId:        string
  role:             string
  resolvedContext?: string
  onStartBuilding:  () => void
  onResolveBlockers:(resolutions: string) => void
  disabled?:        boolean
}

const VERDICT_COLORS: Record<string, string> = {
  PROCEED:                 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  PROCEED_WITH_CONDITIONS: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  REDESIGN:                'text-orange-400 bg-orange-400/10 border-orange-400/20',
  BLOCK:                   'text-red-400 bg-red-400/10 border-red-400/20',
}

const AGENT_ICONS: Record<string, string> = {
  'Senior Architect':  '🏗',
  'Security Engineer': '🔒',
  'DevOps Engineer':   '🚀',
  'Backend Engineer':  '⚙️',
  'Tech Lead':         '👨‍💼',
}

const POSITION_COLORS: Record<string, string> = {
  PROCEED:  'text-emerald-400',
  REDESIGN: 'text-amber-400',
  BLOCK:    'text-red-400',
}

export default function ProCouncilCard({
  verdict,
  agentOutputs,
  task,
  role,
  resolvedContext,
  onStartBuilding,
  onResolveBlockers,
  disabled = false,
}: Props) {
  const [activeTab,       setActiveTab]       = useState<'plan' | 'agents' | 'risks'>('plan')
  const [showResolver,    setShowResolver]     = useState(false)
  const [resolutionText,  setResolutionText]   = useState('')

  const verdictKey   = verdict?.verdict || 'PROCEED'
  const verdictColor = VERDICT_COLORS[verdictKey] || VERDICT_COLORS.PROCEED
  const confidence   = verdict?.confidence_score || 0
  const blocking     = verdict?.blocking_issues || []
  const hasBlockers  = blocking.length > 0
  const canBuild     = verdictKey !== 'BLOCK'

  const tabs = [
    { id: 'plan',   label: 'Execution Plan'  },
    { id: 'agents', label: 'Agent Analysis'  },
    { id: 'risks',  label: 'Risks & Tradeoffs' },
  ] as const

  // Build placeholder from blockers so user knows what to answer
  const resolverPlaceholder = blocking
    .map((b, i) => `${i + 1}. ${b.slice(0, 80)}...`)
    .join('\n')

  const handleResolve = () => {
    if (!resolutionText.trim()) return
    onResolveBlockers(resolutionText.trim())
    setShowResolver(false)
    setResolutionText('')
  }

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden w-full">

      {/* Header */}
      <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs font-mono text-amber-400 uppercase tracking-widest">
            Professional Council
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#484f58] font-mono">{confidence}/10 confidence</span>
            <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${verdictColor}`}>
              {verdictKey.replace(/_/g, ' ')}
            </span>
          </div>
        </div>
        <p className="text-xs text-[#484f58]">
          5 specialists · enterprise analysis · execution-focused
        </p>
      </div>
      {/* Resolved assumptions banner */}
      {resolvedContext && (
        <div className="px-4 py-3 border-b border-[#21262d] bg-emerald-400/5">
          <div className="text-xs font-mono text-emerald-400 uppercase tracking-widest mb-2">
            ✓ Re-analyzed with Your Input
          </div>
          <p className="text-xs text-[#8b949e] leading-relaxed whitespace-pre-wrap">
            {resolvedContext}
          </p>
        </div>
      )}
      {/* Executive Summary */}
      <div className="px-4 py-3 border-b border-[#21262d]">
        <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">
          Executive Summary
        </div>
        <p className="text-sm text-[#e6edf3] leading-relaxed">
          {verdict?.executive_summary || verdict?.primary_recommendation || 'Analysis complete.'}
        </p>
        {verdict?.first_action && (
          <div className="mt-3 px-3 py-2 bg-amber-400/5 border border-amber-400/20 rounded-lg">
            <span className="text-xs font-mono text-amber-400">First Action → </span>
            <span className="text-xs text-[#e6edf3]">{verdict.first_action}</span>
          </div>
        )}
      </div>

      {/* Blocking issues */}
      {hasBlockers && (
        <div className="px-4 py-3 border-b border-[#21262d] bg-red-400/5">
          <div className="text-xs font-mono text-red-400 uppercase tracking-widest mb-2">
            ⛔ Blocking Issues — Resolve Before Building
          </div>
          <div className="space-y-1.5 mb-3">
            {blocking.map((issue, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-red-400 text-xs mt-0.5 flex-shrink-0">×</span>
                <p className="text-xs text-[#e6edf3] leading-relaxed">{issue}</p>
              </div>
            ))}
          </div>

          {/* Resolve inline */}
          {!showResolver ? (
            <button
              onClick={() => setShowResolver(true)}
              disabled={disabled}
              className="w-full py-2 bg-[#0d1117] border border-red-400/30 text-red-400 hover:border-red-400/60 hover:text-red-300 rounded-lg text-xs font-mono transition-colors disabled:opacity-30"
            >
              Answer Blocking Questions →
            </button>
          ) : (
            <div className="space-y-2">
              <div className="text-xs font-mono text-[#484f58] mb-1">
                Answer the blockers above so agents can re-analyze:
              </div>
              <textarea
                value={resolutionText}
                onChange={e => setResolutionText(e.target.value)}
                placeholder={
                  `Answer each blocker clearly. Example:\n${resolverPlaceholder}`
                }
                rows={5}
                autoFocus
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2.5 text-xs text-[#e6edf3] placeholder-[#30363d] outline-none focus:border-amber-400/30 transition-colors resize-none font-mono"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => { setShowResolver(false); setResolutionText('') }}
                  className="px-4 py-2 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] rounded-lg text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => onResolveBlockers(
                    "The user has no additional information to provide at this time. " +
                    "Make reasonable industry-standard assumptions for all blocking issues. " +
                    "Document each assumption clearly in the execution plan. " +
                    "Proceed with the best available information."
                  )}
                  disabled={disabled}
                  className="px-3 py-2 bg-[#0d1117] border border-amber-400/30 text-amber-400 hover:border-amber-400/60 rounded-lg text-xs transition-colors whitespace-nowrap"
                >
                  Let Agent Decide
                </button>
                <button
                  onClick={handleResolve}
                  disabled={!resolutionText.trim() || disabled}
                  className="flex-1 py-2 bg-amber-400 text-[#0d1117] font-semibold rounded-lg text-xs hover:bg-amber-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Submit Answers →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#21262d] px-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-xs font-mono py-2.5 mr-4 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-[#484f58] hover:text-[#8b949e]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-4 py-3 min-h-[180px]">

        {activeTab === 'plan' && (
          <div className="space-y-3">
            {(verdict?.execution_plan || []).length === 0 ? (
              <p className="text-xs text-[#484f58]">No execution plan generated.</p>
            ) : (
              verdict.execution_plan.map((phase, i) => (
                <div key={i} className="border border-[#21262d] rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-amber-400">Phase {phase.phase}</span>
                      <span className="text-sm font-medium text-[#e6edf3]">{phase.title}</span>
                    </div>
                    <span className="text-xs font-mono text-[#484f58] bg-[#0d1117] px-2 py-0.5 rounded">
                      {phase.estimated_effort}
                    </span>
                  </div>
                  <div className="space-y-1 mb-2">
                    {(phase.actions || []).map((action, j) => (
                      <div key={j} className="flex items-start gap-2">
                        <span className="text-emerald-400 text-xs mt-0.5 flex-shrink-0">→</span>
                        <p className="text-xs text-[#8b949e] leading-relaxed">{action}</p>
                      </div>
                    ))}
                  </div>
                  {phase.success_criteria && (
                    <div className="text-xs text-[#484f58] font-mono">
                      ✓ Done when: {phase.success_criteria}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="space-y-2">
            {(agentOutputs || []).map((agent, i) => (
              <div key={i} className="border border-[#21262d] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span>{AGENT_ICONS[agent.agent_name] || '👤'}</span>
                    <span className="text-xs font-mono text-[#e6edf3]">{agent.agent_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[#484f58]">{agent.confidence}/10</span>
                    <span className={`text-xs font-mono ${POSITION_COLORS[agent.position] || 'text-[#484f58]'}`}>
                      {agent.position}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-[#484f58] leading-relaxed mb-1.5">{agent.reasoning}</p>
                {agent.top_risk && (
                  <div className="text-xs font-mono text-amber-400/70">
                    Risk: {agent.top_risk}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'risks' && (
          <div className="space-y-3">
            {(verdict?.key_tradeoffs || []).length > 0 && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">Key Tradeoffs Accepted</div>
                {verdict.key_tradeoffs.map((t, i) => (
                  <div key={i} className="flex items-start gap-2 mb-1.5">
                    <span className="text-amber-400 text-xs mt-0.5 flex-shrink-0">⇄</span>
                    <p className="text-xs text-[#8b949e] leading-relaxed">{t}</p>
                  </div>
                ))}
              </div>
            )}
            {(verdict?.conditions || []).length > 0 && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">Conditions to Meet</div>
                {verdict.conditions.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 mb-1.5">
                    <span className="text-amber-400 text-xs mt-0.5 flex-shrink-0">!</span>
                    <p className="text-xs text-[#8b949e] leading-relaxed">{c}</p>
                  </div>
                ))}
              </div>
            )}
            {verdict?.minority_dissent && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">Minority Dissent</div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{verdict.minority_dissent}</p>
              </div>
            )}
            {(verdict?.clarifying_questions || []).length > 0 && (
              <div>
                <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-2">Open Questions</div>
                {verdict.clarifying_questions.map((q, i) => (
                  <div key={i} className="flex items-start gap-2 mb-1.5">
                    <span className="text-[#484f58] text-xs mt-0.5 flex-shrink-0">?</span>
                    <p className="text-xs text-[#8b949e] leading-relaxed">{q}</p>
                  </div>
                ))}
              </div>
            )}
            {!verdict?.key_tradeoffs?.length && !verdict?.conditions?.length &&
             !verdict?.minority_dissent && !verdict?.clarifying_questions?.length && (
              <p className="text-xs text-[#484f58]">No significant risks or tradeoffs identified.</p>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-[#21262d] bg-[#0d1117]">
        <div className="flex gap-2">
          {hasBlockers ? (
            <button
              onClick={() => setShowResolver(true)}
              disabled={disabled}
              className="flex-1 py-2.5 bg-[#0d1117] border border-amber-400/40 text-amber-400 hover:border-amber-400/70 rounded-lg text-sm font-semibold disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Answer Blocking Questions →
            </button>
          ) : (
            <button
              onClick={onStartBuilding}
              disabled={disabled}
              className="flex-1 py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm hover:bg-[#e0a419] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              → Start Building
            </button>
          )}
        </div>
        {verdictKey === 'PROCEED_WITH_CONDITIONS' && (
          <p className="text-xs text-amber-400/70 text-center mt-2 font-mono">
            Proceed with conditions — review requirements above before building
          </p>
        )}
      </div>
    </div>
  )
}