'use client'

import { PURPOSE_OPTIONS } from '../../lib/constants'

interface Props {
  onAnswer: (val: string) => void
  onBack: () => void
}

export default function GateStep4({ onAnswer, onBack }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-sm">
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        Step 3 of 3
      </div>
      <p className="text-xs text-[#484f58] mb-4">
        This changes how every agent researches and evaluates your project.
        Job Role focuses on hiring signals. Portfolio on impression.
        Startup on market. Learning on skill building.
      </p>
      <p className="text-sm text-[#e6edf3] mb-4">
        What is the main purpose of this project?
      </p>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {PURPOSE_OPTIONS.map(opt => (
          <button
            key={opt.id}
            onClick={() => onAnswer(opt.id)}
            className="px-3 py-3 bg-[#0d1117] border border-[#30363d] rounded-xl text-left hover:border-[#f0b429]/30 hover:bg-[#161b22] transition-colors group"
          >
            <div className="text-base mb-1">{opt.icon}</div>
            <div className="text-sm font-medium text-[#e6edf3] group-hover:text-[#f0b429] transition-colors">
              {opt.label}
            </div>
            <div className="text-xs text-[#484f58]">{opt.desc}</div>
          </button>
        ))}
      </div>
      <button
        onClick={onBack}
        className="w-full py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
      >
        ← Back
      </button>
    </div>
  )
}