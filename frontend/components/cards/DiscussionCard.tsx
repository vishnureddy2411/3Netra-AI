// ─────────────────────────────────────────────
// Discussion Card
// Multi-turn conversation loop where user
// can ask any doubt about their selected project.
// Agent answers with role-specific guidance.
// User explicitly confirms readiness to proceed.
// ─────────────────────────────────────────────

'use client'

import { useState, useRef, useEffect } from 'react'
import type { SelectedProject, DiscussionTurn } from '../../lib/types'

interface Props {
  selectedProject: SelectedProject
  history: DiscussionTurn[]
  onSend: (message: string, currentHistory: DiscussionTurn[]) => Promise<void>
  onProceed: () => void
  isLoading: boolean
  disabled: boolean
}

export default function DiscussionCard({
  selectedProject,
  history,
  onSend,
  onProceed,
  isLoading,
  disabled,
}: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const text = input.trim()
    setInput('')
    await onSend(text, history)
  }

  // Quick doubt suggestions
  const QUICK_DOUBTS = [
    'Is this project too common?',
    'Can I complete this in time?',
    'Is this the right difficulty for me?',
    'What makes this stand out to hiring managers?',
    'What are the biggest risks?',
    'Can I simplify the scope?',
  ]

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">

      {/* Header */}
      <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
        <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-0.5">
          Project Discussion
        </div>
        <p className="text-xs text-[#484f58]">
          Discussing: <span className="text-[#8b949e]">{selectedProject.title}</span>
          {' · '}Ask anything before committing
        </p>
      </div>

      {/* Discussion history */}
      <div className="px-4 py-3 space-y-3 max-h-80 overflow-y-auto">

        {/* Initial mentor message */}
        {history.length === 0 && (
          <div className="flex items-start gap-2">
            <div className="w-5 h-5 rounded-full bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-[#f0b429] text-xs font-bold">3</span>
            </div>
            <div className="bg-[#0d1117] border border-[#21262d] rounded-xl rounded-tl-sm px-3 py-2.5 flex-1">
              <p className="text-xs text-[#8b949e] leading-relaxed">
                You selected <span className="text-[#e6edf3] font-medium">{selectedProject.title}</span>.
                What questions do you have before we move to diagrams?
                I can help you evaluate whether this is the right project for your {selectedProject.level?.toLowerCase()} level
                and your target role.
              </p>
            </div>
          </div>
        )}

        {/* Conversation history */}
        {history.map((turn, i) => (
          <div key={i} className={`flex items-start gap-2 ${turn.role === 'user' ? 'flex-row-reverse' : ''}`}>
            {turn.role === 'mentor' && (
              <div className="w-5 h-5 rounded-full bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-[#f0b429] text-xs font-bold">3</span>
              </div>
            )}
            <div className={`rounded-xl px-3 py-2.5 max-w-xs ${
              turn.role === 'user'
                ? 'bg-[#1c2333] border border-[#30363d] rounded-tr-sm'
                : 'bg-[#0d1117] border border-[#21262d] rounded-tl-sm flex-1'
            }`}>
              <p className="text-xs text-[#8b949e] leading-relaxed whitespace-pre-wrap">
                {turn.content}
              </p>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-start gap-2">
            <div className="w-5 h-5 rounded-full bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-[#f0b429] text-xs font-bold">3</span>
            </div>
            <div className="bg-[#0d1117] border border-[#21262d] rounded-xl rounded-tl-sm px-3 py-2.5">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i}
                    style={{ animationDelay: `${i * 0.2}s` }}
                    className="w-1.5 h-1.5 rounded-full bg-[#f0b429] animate-pulse"
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Quick doubt suggestions — only show if no history yet */}
      {history.length === 0 && (
        <div className="px-4 py-3 border-t border-[#21262d]">
          <div className="text-xs font-mono text-[#30363d] mb-2">Common questions</div>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_DOUBTS.map((doubt, i) => (
              <button
                key={i}
                onClick={() => setInput(doubt)}
                className="text-xs px-2.5 py-1 bg-[#0d1117] border border-[#21262d] rounded-lg text-[#484f58] hover:text-[#e6edf3] hover:border-[#30363d] transition-colors"
              >
                {doubt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Proceed button — visible after at least one exchange */}
      {history.length >= 2 && (
        <div className="px-4 py-3 border-t border-[#21262d]">
          <button
            onClick={onProceed}
            disabled={disabled || isLoading}
            className="w-full py-2.5 bg-[#1a2e1a] border border-[#3fb950]/25 rounded-lg text-sm font-semibold text-[#3fb950] hover:border-[#3fb950]/50 hover:bg-[#1a2e1a] transition-colors disabled:opacity-30"
          >
            I am ready — generate architecture diagrams →
          </button>
        </div>
      )}

      {/* Input */}
      <div className="px-4 pb-4 border-t border-[#21262d] pt-3">
        <div className="flex gap-2 bg-[#0d1117] border border-[#21262d] rounded-xl px-3 py-2 focus-within:border-[#30363d] transition-colors">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleSend()
            }}
            placeholder="Ask any doubt about this project..."
            disabled={isLoading || disabled}
            className="flex-1 bg-transparent text-sm text-[#e6edf3] placeholder-[#484f58] outline-none disabled:opacity-40"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || disabled}
            className="px-3 py-1 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-xs hover:bg-[#e0a419] disabled:opacity-30 transition-colors"
          >
            Ask
          </button>
        </div>
      </div>
    </div>
  )
}