// ─────────────────────────────────────────────
// Thinking Card — animated dots while agent runs
// ─────────────────────────────────────────────

'use client'

interface Props {
  stage: string
  message: string
}

export default function ThinkingCard({ stage, message }: Props) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-[#161b22] border border-[#30363d] rounded-xl">
      <div className="flex gap-1 flex-shrink-0">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            style={{ animationDelay: `${i * 0.2}s` }}
            className="w-1.5 h-1.5 rounded-full bg-[#f0b429] animate-pulse"
          />
        ))}
      </div>
      <div className="min-w-0">
        <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-0.5">
          {stage}
        </div>
        <div className="text-xs text-[#484f58] leading-relaxed truncate">
          {message}
        </div>
      </div>
    </div>
  )
}