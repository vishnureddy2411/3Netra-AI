// ─────────────────────────────────────────────
// New Session Card
// Appears after diagrams complete OR when
// message count hits MAX_SESSION_MESSAGES.
// Lets user start a fresh chat while keeping
// full project memory.
// ─────────────────────────────────────────────

'use client'

interface Props {
  reason: 'pipeline_complete' | 'message_limit'
  projectTitle: string
  messageCount: number
  onStartNewSession: () => void
  onContinue?: () => void
}

export default function NewSessionCard({
  reason,
  projectTitle,
  messageCount,
  onStartNewSession,
  onContinue,
}: Props) {
  const isPipelineComplete = reason === 'pipeline_complete'

  return (
    <div className={`border rounded-xl overflow-hidden max-w-2xl ${
      isPipelineComplete
        ? 'bg-[#1a2e1a] border-[#3fb950]/20'
        : 'bg-[#1c2333] border-[#58a6ff]/20'
    }`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#21262d]">
        <div className={`text-xs font-mono uppercase tracking-widest mb-0.5 ${
          isPipelineComplete ? 'text-[#3fb950]' : 'text-[#58a6ff]'
        }`}>
          {isPipelineComplete ? 'Stage Complete' : 'Chat Limit Reached'}
        </div>
        <p className="text-xs text-[#484f58]">
          {isPipelineComplete
            ? 'Planning stage finished — ready for the next stage'
            : `${messageCount} messages in this session — start fresh to avoid lag`
          }
        </p>
      </div>

      <div className="px-4 py-4 space-y-3">

        {/* Project context preserved */}
        <div className="bg-[#0d1117] border border-[#21262d] rounded-lg px-4 py-3">
          <div className="text-xs font-mono text-[#484f58] mb-2">
            Project memory preserved
          </div>
          <div className="space-y-1.5">
            {[
              'Tech stack and architecture decisions',
              'Expert council verdict and recommendations',
              'Generated diagrams and project graph',
              'All previous discussion context',
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-[#8b949e]">
                <span className="text-[#3fb950]/60">✓</span>
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* Project title */}
        <div className="text-xs text-[#484f58] font-mono truncate">
          Project: <span className="text-[#8b949e]">{projectTitle}</span>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={onStartNewSession}
            className={`flex-1 py-2.5 font-semibold rounded-lg text-sm transition-colors ${
              isPipelineComplete
                ? 'bg-[#3fb950] text-[#0d1117] hover:bg-[#3dba4e]'
                : 'bg-[#58a6ff] text-[#0d1117] hover:bg-[#4d9fee]'
            }`}
          >
            {isPipelineComplete ? 'Start Next Stage →' : 'Start New Chat →'}
          </button>
          {onContinue && (
            <button
              onClick={onContinue}
              className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] rounded-lg text-xs font-mono transition-colors"
            >
              Continue here
            </button>
          )}
        </div>
      </div>
    </div>
  )
}