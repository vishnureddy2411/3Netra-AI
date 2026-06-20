'use client'

import { useState } from 'react'

interface Props {
  onAnswer: (val: string) => void
  onBack: () => void
}

export default function GateStep2({ onAnswer, onBack }: Props) {
  const [val, setVal] = useState('')

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-sm">
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        Step 1 of 3
      </div>
      <p className="text-xs text-[#484f58] mb-4">
        Role calibrates every agent — research targets, advice tone,
        and project suggestions all adjust to what employers actually want
      </p>
      <p className="text-sm text-[#e6edf3] mb-3">
        What role are you targeting?
      </p>
      <input
        type="text"
        value={val}
        onChange={e => setVal(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && val.trim()) onAnswer(val) }}
        placeholder="e.g. Data Engineer, ML Engineer, Backend Engineer..."
        autoFocus
        className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none focus:border-[#f0b429]/30 transition-colors mb-3"
      />
      <div className="flex gap-2">
        <button
          onClick={onBack}
          className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={() => onAnswer(val)}
          disabled={!val.trim()}
          className="flex-1 py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm disabled:opacity-30 hover:bg-[#e0a419] transition-colors"
        >
          Next →
        </button>
        <button
          onClick={() => onAnswer('')}
          className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#484f58] hover:text-[#e6edf3] transition-colors"
        >
          Skip
        </button>
      </div>
    </div>
  )
}