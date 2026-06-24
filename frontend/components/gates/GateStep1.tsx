'use client'

interface Props {
  onAnswer: (val: string) => void
}

export default function GateStep1({ onAnswer }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-sm">
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        Getting started
      </div>
      <p className="text-xs text-[#484f58] mb-4">
        Helps agents track your progress across sessions
      </p>
      <p className="text-sm text-[#e6edf3] mb-4">
        What would you like to build today?
      </p>
      <button
        onClick={() => onAnswer('new')}
        className="w-full py-2.5 bg-[#f0b429] text-[#0d1117] rounded-lg text-sm font-semibold hover:bg-[#e0a419] transition-colors"
      >
        New Project
      </button>
    </div>
  )
}